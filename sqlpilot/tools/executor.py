"""MySqlExecutor: read-only, session-level 3s timeout, 200-row cap, structured errors.

Contract (doc §2.4 / §2.11 / §2.12):
- 3s timeout via `SET SESSION max_execution_time`, NOT via SQL hint.
- errno -> kind mapping written here once; never recomputed downstream.
- Truncation is NOT an error: success + truncated=True.
"""
from __future__ import annotations

import time
from typing import Any

import pymysql
from dbutils.pooled_db import PooledDB

from sqlpilot.config import get_settings

# errno -> kind (doc §2.4). Anything else -> OTHER.
ERRNO_KIND: dict[int, str] = {
    1054: "UNKNOWN_COLUMN",
    1146: "UNKNOWN_TABLE",
    1064: "SYNTAX",
    1366: "TYPE_MISMATCH",
    1411: "TYPE_MISMATCH",
    1292: "TYPE_MISMATCH",
    3024: "QUERY_TIMEOUT",
}


class MySqlExecutor:
    def __init__(self, settings=None):
        s = settings or get_settings()
        if not s.mysql_password:
            raise RuntimeError("MYSQL_PASSWORD 未配置，无法连接数据库")
        self.max_rows = s.sql_max_rows
        self.timeout_ms = int(s.sql_timeout_s * 1000)
        self._pool = PooledDB(
            creator=pymysql,
            maxconnections=5,
            mincached=1,
            blocking=True,
            host=s.mysql_host,
            port=s.mysql_port,
            user=s.mysql_user,
            password=s.mysql_password,
            database=s.mysql_database,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.Cursor,
        )

    def execute(self, sql: str) -> dict[str, Any]:
        """Run one SELECT. Always returns a dict; never raises on SQL errors."""
        t0 = time.monotonic()
        conn = None
        try:
            conn = self._pool.connection()
            with conn.cursor() as cur:
                # Session-level timeout, per connection (doc ADR-13).
                cur.execute(f"SET SESSION max_execution_time = {self.timeout_ms}")
                cur.execute(sql)
                cols = [d[0] for d in (cur.description or [])]
                # Fetch one extra row to detect truncation.
                raw = cur.fetchmany(self.max_rows + 1)
                truncated = len(raw) > self.max_rows
                rows = [list(r) for r in raw[: self.max_rows]]
            return {
                "ok": True,
                "columns": cols,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
                "error": None,
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }
        except pymysql.MySQLError as e:
            errno = e.args[0] if e.args else 0
            kind = ERRNO_KIND.get(errno, "OTHER")
            return {
                "ok": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
                "error": {
                    "errno": errno,
                    "message": str(e),
                    "kind": kind,
                    "source": "mysql",
                },
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }
        finally:
            if conn is not None:
                conn.close()   # returns to pool


if __name__ == "__main__":
    # Smoke test: python -m sqlpilot.tools.executor
    ex = MySqlExecutor()
    print("-- ok case --")
    print(ex.execute("SELECT store_id, store_name FROM stores LIMIT 3"))
    print("-- error case (unknown column) --")
    print(ex.execute("SELECT nope FROM stores LIMIT 1")["error"])