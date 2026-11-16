"""测试 agent/errors.py：kind → 修复策略的分派表。"""
from sqlpilot.agent.errors import needs_relink, is_recoverable, is_terminal


def test_needs_relink():
    """验证 needs_relink 的分派：3 个 True，2 个 False。"""
    cases = [
        # (kind, 期望的 needs_relink 返回值)
        ("UNKNOWN_COLUMN", True),
        ("UNKNOWN_TABLE", True),
        ("TYPE_MISMATCH", True),
        ("SYNTAX", False),
        ("OTHER", False),
    ]
    for kind, expected in cases:
        result = needs_relink(kind)
        assert result is expected, f"{kind} 应该是 {expected}，实际是 {result}"

def test_recoverable():
    """5 个可恢复 kind → True；4 个终止 kind → False（反向防误认）。"""
    recoverable = ["UNKNOWN_COLUMN", "UNKNOWN_TABLE", "SYNTAX", "TYPE_MISMATCH", "OTHER"]
    terminal = ["BLOCKED", "EMPTY_RESULT", "QUERY_TIMEOUT", "ROW_TRUNCATED"]

    # 正向：5 个可恢复的必须返回 True
    for k in recoverable:
        assert is_recoverable(k) is True, f"{k} 应该是可恢复"

    # 反向：4 个终止的必须返回 False（防止函数把所有 kind 都判成可恢复）
    for k in terminal:
        assert is_recoverable(k) is False, f"{k} 不该被当成可恢复"


def test_terminal():
    """4 个终止 kind → True；5 个可恢复 kind → False（反向防误认）。"""
    recoverable = ["UNKNOWN_COLUMN", "UNKNOWN_TABLE", "SYNTAX", "TYPE_MISMATCH", "OTHER"]
    terminal = ["BLOCKED", "EMPTY_RESULT", "QUERY_TIMEOUT", "ROW_TRUNCATED"]

    # 正向：4 个终止的必须返回 True
    for k in terminal:
        assert is_terminal(k) is True, f"{k} 应该是终止"

    # 反向：5 个可恢复的必须返回 False（防止函数把所有 kind 都判成终止）
    for k in recoverable:
        assert is_terminal(k) is False, f"{k} 不该被当成终止"