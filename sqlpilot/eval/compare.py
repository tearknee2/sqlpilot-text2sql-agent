"""结果集等价判定（doc §4.4 / ADR-2）。"""
from decimal import Decimal


def normalize_value(v, tolerance: float):
    """把单个单元格值转成可比较、可哈希的标准形态。

    规则：
      - None 保持 None（SQL NULL 统一表示）
      - Decimal → float
      - 其他类型原样返回
      - float（含 Decimal 转来的）按 tolerance 量化到定点，便于哈希比较
    """
    if v is None:
        return None
    if isinstance(v, Decimal):
        v = float(v)                          # Decimal → float
    if isinstance(v, float):
        if tolerance == 0:
            return v
        # 量化：round(v / tolerance) * tolerance
        # 例如 tolerance=0.01, v=1283400.504 → round(128340050.4) * 0.01 = 1283400.50
        v = round(v / tolerance) * tolerance
    return v

def _align_columns(pred_result, gt_result, ignore_column_order):
    """按 gt 的列名重排 pred 的列。返回重排后的 rows，无法对齐时返回 None。"""
    if not ignore_column_order:
        return pred_result["rows"]   # 不忽略列序 → 按位置原样返回

    pred_cols = pred_result["columns"]
    gt_cols = gt_result["columns"]

    # 任意一边没有列名 → 无法按列名对齐，退回按位置
    if not pred_cols or not gt_cols:
        return pred_result["rows"]

    # 列名集合不同（比如 pred 少了一列）→ 无法对齐
    if set(pred_cols) != set(gt_cols):
        # 列名不同，但是列数相同——>按位置对齐（4.4不可识别时按位置对齐）
        if len(pred_cols) == len(gt_cols):
            return pred_result["rows"] # 按照原位置返回
        return None  # 列数不同-->无法对齐，判错

    # 按 gt 的列序，从 pred 里取对应列
    idx_map = {c: i for i, c in enumerate(pred_cols)}
    reorder = [idx_map[c] for c in gt_cols]
    return [[row[i] for i in reorder] for row in pred_result["rows"]]

from collections import Counter


def compare(pred_result, gt_result, gt_sql, tolerance=1e-6, ignore_column_order=True):
    """结果集等价判定（doc §4.4）。

    返回 (passed, reason)：
      - passed: bool
      - reason: 一段说明，D11 badcase 归因时用
    """
    pred_rows = pred_result["rows"]
    gt_rows = gt_result["rows"]

    # 1) 行数不同 → 直接不等
    if len(pred_rows) != len(gt_rows):
        return False, f"row_count_mismatch: {len(pred_rows)} vs {len(gt_rows)}"

    # 2) 列对齐
    aligned = _align_columns(pred_result, gt_result, ignore_column_order)
    if aligned is None:
        return False, "column_misalignment"

    # 3) 每个单元格 normalize_value
    pred_norm = [[normalize_value(v, tolerance) for v in row] for row in aligned]
    gt_norm   = [[normalize_value(v, tolerance) for v in row] for row in gt_rows]

    # 4) 判断 GT SQL 有无 ORDER BY
    has_order_by = "ORDER BY" in gt_sql.upper()

    # 5) 比较
    if has_order_by:
        # 保序：逐行比较
        passed = pred_norm == gt_norm
        return passed, "ordered_compare_ok" if passed else "ordered_mismatch"

    # 6) 忽略顺序：Counter 多重集比较
    #    注意：Counter 需要元素可哈希 → 每行先转 tuple
    pred_set = Counter(map(tuple, pred_norm))
    gt_set   = Counter(map(tuple, gt_norm))
    passed = pred_set == gt_set
    return passed, "multiset_compare_ok" if passed else "content_mismatch"


if __name__ == "__main__":
    cases = [
        (Decimal("18348.85"), 0.01),
        (18348.85, 0.01),
        (None, 0.01),
        (300, 0),
    ]
    for v, tol in cases:
        print(f"{v!r:30s} tol={tol}  →  {normalize_value(v, tol)!r}")

    # 测试 1：ORDER BY 保序，完全一致
    pred = {"columns": ["a", "b"], "rows": [[1, 10], [2, 20]]}
    gt   = {"columns": ["a", "b"], "rows": [[1, 10], [2, 20]]}
    print(compare(pred, gt, "SELECT a, b FROM t ORDER BY a"))
    # 期望：(True, 'ordered_compare_ok')

    # 测试 2：ORDER BY 保序，顺序错 → 不等
    pred = {"columns": ["a", "b"], "rows": [[2, 20], [1, 10]]}
    gt   = {"columns": ["a", "b"], "rows": [[1, 10], [2, 20]]}
    print(compare(pred, gt, "SELECT a, b FROM t ORDER BY a"))
    # 期望：(False, 'ordered_mismatch')

    # 测试 3：无 ORDER BY，顺序不同 → 相等
    pred = {"columns": ["a", "b"], "rows": [[2, 20], [1, 10]]}
    gt   = {"columns": ["a", "b"], "rows": [[1, 10], [2, 20]]}
    print(compare(pred, gt, "SELECT a, b FROM t"))
    # 期望：(True, 'multiset_compare_ok')

    # 测试 4：列序不同（ignore_column_order=True）→ 相等
    pred = {"columns": ["b", "a"], "rows": [[10, 1], [20, 2]]}
    gt   = {"columns": ["a", "b"], "rows": [[1, 10], [2, 20]]}
    print(compare(pred, gt, "SELECT a, b FROM t"))
    # 期望：(True, 'multiset_compare_ok')

    # 测试 5：浮点容差
    pred = {"columns": ["v"], "rows": [[18348.853]]}
    gt   = {"columns": ["v"], "rows": [[18348.85]]}
    print(compare(pred, gt, "SELECT v FROM t", tolerance=0.01))
    # 期望：(True, 'multiset_compare_ok')