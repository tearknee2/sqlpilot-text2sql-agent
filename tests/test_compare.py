from sqlpilot.eval.compare import compare


def test_float_tolerance():
    """陷阱 1：浮点容差。"""
    pred = {"columns": ["v"], "rows": [[18348.853]]}
    gt   = {"columns": ["v"], "rows": [[18348.85]]}
    passed, _ = compare(pred, gt, "SELECT v FROM t", tolerance=0.01)
    assert passed is True


def test_column_misalignment():
    """陷阱 2：忽略列名会把 SELECT a,SUM(b) 和 SELECT b,a 误判等价。"""
    # 文档 §4.4 原文警告的场景
    pred = {"columns": ["a", "sum_b"], "rows": [[1, 100]]}
    gt   = {"columns": ["sum_b", "a"], "rows": [[100, 1]]}
    passed, _ = compare(pred, gt, "SELECT a, SUM(b) AS sum_b FROM t", ignore_column_order=True)
    assert passed is True   # 按列名对齐后应该相等

def test_column_ignore_is_risky():
    """文档警告：数值巧合时，按位置比会误判等价。"""
    pred = {"columns": ["a", "sum_b"], "rows": [[100, 1]]}
    gt   = {"columns": ["sum_b", "a"], "rows": [[100, 1]]}

    # 错误做法：完全忽略列名，按位置比 → 误判为等价
    passed_wrong, _ = compare(pred, gt, "SELECT ...", ignore_column_order=False)
    assert passed_wrong is True   # ← 这就是坑

    # 正确做法：按列名映射 → 判不等
    passed_right, _ = compare(pred, gt, "SELECT ...", ignore_column_order=True)
    assert passed_right is False