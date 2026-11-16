"""D5 超时熔断验证（doc ADR-13 / §2.12）。

注意：这是集成测试，需要 Docker 里的 MySQL 正在运行（docker compose ps 显示 healthy）。
如果 MySQL 没起，这个测试会挂——这是预期行为，不是 bug。
"""
from sqlpilot.config import Settings
from sqlpilot.tools.executor import MySqlExecutor

def test_query_timeout():
    """SLEEP(10) 被 3s 会话超时截断 → 总耗时 < 5s。

    说明：
    - SLEEP 被 max_execution_time 截断后返回 0（MySQL 特殊行为），不抛 3024
    - 所以这条测试断言"耗时被截断"，不断言 errno=3024
    - 要验证 errno=3024 需要用重聚合查询，但单次测试要等 3s 且受机器影响，
      本测试选择"耗时截断"这个更可靠、更快的证据
    """
    import time
    ex = MySqlExecutor()          # 用 .env 里默认的 3s 超时
    t0 = time.monotonic()
    result = ex.execute("SELECT SLEEP(10)")
    elapsed = time.monotonic() - t0

    assert elapsed < 5, f"SLEEP(10) 应在 3s 左右被截断，实际 {elapsed:.2f}s"
    assert result["ok"] is True, "SLEEP 被截断返回 0，不是错误"


def test_errno_3024_mapping():
    """验证 errno=3024 被映射成 QUERY_TIMEOUT（不依赖真 MySQL）。"""
    from unittest.mock import MagicMock, patch
    import pymysql
    from sqlpilot.tools.executor import MySqlExecutor, ERRNO_KIND

    # 直接测映射表（最简单）
    assert ERRNO_KIND[3024] == "QUERY_TIMEOUT"

def test_query_timeout_is_terminal():
    """QUERY_TIMEOUT 是终止类错误：不重试。"""
    from sqlpilot.agent.errors import is_terminal
    assert is_terminal("QUERY_TIMEOUT") is True, "超时不该重试（重试还是超时）"