"""SqlGuard: deterministic AST-based safety gate (doc §2.11).

Contract:
- Security violation => blocked=True AND observation["kind"]=="BLOCKED" => refuse, no retry.
- Recoverable (unknown column / unknown table / syntax) =>
  passed=False, blocked=False, observation["kind"] in {...} => enters correction loop.
- LIMIT is tightened, never loosened. No optimizer hints. No comments in output.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp

from sqlpilot.guard.models import SqlValidation
from sqlpilot.schema.catalog import SchemaCatalog

SYSTEM_SCHEMAS = {"mysql", "information_schema", "performance_schema", "sys"}
FORBIDDEN_FUNCS = {
    "SLEEP", "BENCHMARK", "LOAD_FILE", "GET_LOCK", "RELEASE_LOCK",
    "SYS_EVAL", "SYSEVAL", "PG_SLEEP",
}
FORBIDDEN_NODES = (
    exp.Drop, exp.Delete, exp.Insert, exp.Update, exp.Command,
    exp.Into, exp.Attach, exp.Pragma,
)


def _has_comment_outside_literals(sql: str) -> bool:
    """True if a comment marker (--, #, /*) appears outside quoted literals."""
    in_single = in_double = in_backtick = False
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "'" and not (in_double or in_backtick):
            if in_single and i + 1 < n and sql[i + 1] == "'":
                i += 2
                continue
            in_single = not in_single
        elif c == '"' and not (in_single or in_backtick):
            in_double = not in_double
        elif c == "`" and not (in_single or in_double):
            in_backtick = not in_backtick
        elif not (in_single or in_double or in_backtick):
            if sql.startswith("--", i) or sql.startswith("/*", i):
                return True
            if c == "#":
                return True
        i += 1
    return False


def _ensure_limit(ast: exp.Select, max_rows: int) -> bool:
    """Tighten existing LIMIT or add one. Return True if we changed anything."""
    existing = ast.args.get("limit")
    if existing is not None:
        try:
            n = int(existing.expression.name)
            if n <= max_rows:
                return False
        except Exception:
            pass
    ast.limit(max_rows)
    return True


class SqlGuard:
    def __init__(self, catalog: SchemaCatalog, max_rows: int = 200):
        self.catalog = catalog
        self.max_rows = max_rows

    def validate(self, sql: str) -> SqlValidation:
        def observation(kind, message, errno=0, source="guard"):
            return {"errno": errno, "message": message, "kind": kind, "source": source}

        def recoverable(kind, message, errno=0):
            return SqlValidation(
                passed=False, blocked=False, reason=kind,
                observation=observation(kind, message, errno),
            )

        def blocked(reason):
            # blocked=True MUST pair with kind=="BLOCKED" (contract).
            return SqlValidation(
                passed=False, blocked=True, reason=reason,
                observation=observation("BLOCKED", reason),
            )

        # 0) comments / system variables
        if _has_comment_outside_literals(sql):
            return blocked("COMMENT_BYPASS")
        if "@@" in sql.upper():
            return blocked("SYSTEM_VARIABLE")

        # 1) parse
        try:
            exprs = [e for e in sqlglot.parse(sql, read="mysql") if e]
        except Exception as e:
            return recoverable("SYNTAX", f"PARSE_ERROR: {e}", errno=1064)
        if len(exprs) != 1:
            return blocked("MULTIPLE_STATEMENTS")
        ast = exprs[0]
        if not isinstance(ast, exp.Select):
            return blocked("NOT_SELECT_OR_UNION")
        if any(ast.find(f) is not None for f in FORBIDDEN_NODES):
            return blocked("FORBIDDEN_NODE")
        for f in ast.find_all(exp.Anonymous):
            if (f.name or "").upper() in FORBIDDEN_FUNCS:
                return blocked("FORBIDDEN_FUNCTION")

        # 2) system schema / cross-db — MUST read t.db, not t.name
        table_nodes = list(ast.find_all(exp.Table))
        for t in table_nodes:
            db = (t.db or "").lower()
            if db and (db in SYSTEM_SCHEMAS or db != self.catalog.database.lower()):
                return blocked("SYSTEM_SCHEMA_OR_CROSS_DB")

        # 3) table whitelist, after removing CTE names
        cte_names = {c.alias_or_name for c in ast.find_all(exp.CTE)}
        tables = {t.name for t in table_nodes} - cte_names
        if not tables:
            return blocked("NO_TABLE")
        unknown = tables - self.catalog.allowed_tables
        if unknown:
            return recoverable(
                "UNKNOWN_TABLE",
                f"未知表 {sorted(unknown)}; 候选表: {sorted(self.catalog.allowed_tables)}",
            )

        # 4) alias -> real table mapping (CRITICAL: without this, o.col is missed)
        known = self.catalog.columns_by_table
        alias2table: dict[str, str] = {}
        for t in table_nodes:
            if t.name in known:
                alias2table[t.name] = t.name
                alias = t.alias
                if alias:
                    alias2table[str(alias)] = t.name
        for col in ast.find_all(exp.Column):
            if col.name == "*":
                continue
            real = alias2table.get(col.table) if col.table else None
            if real is None:
                continue  # bare / CTE output / derived: skip, not our job
            if col.name not in known.get(real, set()):
                return recoverable(
                    "UNKNOWN_COLUMN",
                    f"Unknown column '{col.table}.{col.name}'; 候选列: {sorted(known[real])}",
                    errno=1054,
                )

        # 5) tighten LIMIT, emit zero-comment normalized SQL
        injected = _ensure_limit(ast, self.max_rows)
        return SqlValidation(
            passed=True,
            normalized_sql=ast.sql(dialect="mysql"),
            tables=sorted(tables),
            injected_limit=injected,
        )


if __name__ == "__main__":
    from sqlpilot.schema.catalog import get_catalog

    g = SqlGuard(get_catalog())
    cases = [
        ("SELECT store_id, store_name FROM stores LIMIT 3", "pass"),
        ("SELECT o.total_amount FROM orders o", "UNKNOWN_COLUMN"),
        ("SELECT * FROM ordres", "UNKNOWN_TABLE"),
        ("SELECT * FROM mysql.user", "BLOCKED"),
        ("SELECT * FROM otherdb.orders", "BLOCKED"),
        ("WITH x AS (SELECT store_id FROM orders) SELECT * FROM x", "pass"),
        ("SELECT 1 -- comment", "BLOCKED"),
        ("SELECT 1 UNION SELECT 2", "BLOCKED"),
        ("SELECT SLEEP(5)", "BLOCKED"),
        ("DROP TABLE orders", "BLOCKED"),
    ]
    for sql, expect in cases:
        v = g.validate(sql)
        if v.passed:
            kind = "pass"
        elif v.observation:
            kind = v.observation["kind"]
        else:
            kind = "?"
        ok = "OK  " if kind == expect else "FAIL"
        print(f"{ok} expect={expect:15s} got={kind:15s} | {sql[:60]}")
        if v.passed and v.normalized_sql:
            assert "--" not in v.normalized_sql and "/*" not in v.normalized_sql, \
                f"normalized SQL contains comment: {v.normalized_sql}"