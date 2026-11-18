from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E15",
    question="2024年销售额高于全部门店平均销售额的门店名称及其销售额",
    layer="子查询",
    difficulty="hard",
    split="dev",
    gt_sql=(
        "SELECT s.store_name, SUM(o.amount) AS sales FROM orders o "
        "JOIN stores s ON o.store_id = s.store_id "
        "WHERE o.order_date BETWEEN '2024-01-01' AND '2024-12-31' "
        "AND LOWER(TRIM(o.status)) = 'paid' "
        "GROUP BY s.store_id, s.store_name "
        "HAVING SUM(o.amount) > ("
        "  SELECT AVG(t.sales) FROM ("
        "    SELECT SUM(o2.amount) AS sales FROM orders o2 "
        "    WHERE o2.order_date BETWEEN '2024-01-01' AND '2024-12-31' "
        "    AND LOWER(TRIM(o2.status)) = 'paid' "
        "    GROUP BY o2.store_id"
        "  ) t"
        ") "
        "ORDER BY sales DESC"
    ),
    expect="result",
    tolerance=0.01,
    tags=["子查询", "HAVING", "标量子查询"],
    notes="GT 含 ORDER BY，D7 保序比较；考查 HAVING + 标量子查询",
)

if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")