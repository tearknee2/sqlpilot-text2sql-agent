from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor


c = EvalCase(
    id="E16",
    question="2024年购买过'数码'品类商品的客户中，其全部已支付订单数最多的前5名客户ID及订单数",
    layer="子查询",
    difficulty="hard",
    split="dev",
    gt_sql=(
        "WITH digital_buyers AS ("
        "  SELECT DISTINCT o.customer_id FROM orders o "
        "  JOIN order_items oi ON o.order_id = oi.order_id "
        "  JOIN products p ON oi.product_id = p.product_id "
        "  WHERE p.category = '数码' AND o.order_date BETWEEN '2024-01-01' AND '2024-12-31' "
        "  AND LOWER(TRIM(o.status)) = 'paid'"
        ") "
        "SELECT o.customer_id, COUNT(*) AS order_count FROM orders o "
        "WHERE o.customer_id IN (SELECT customer_id FROM digital_buyers) "
        "AND o.order_date BETWEEN '2024-01-01' AND '2024-12-31' "
        "AND LOWER(TRIM(o.status)) = 'paid' "
        "GROUP BY o.customer_id ORDER BY order_count DESC LIMIT 5"
    ),
    expect="result",
    tolerance=0,
    tags=["子查询", "CTE", "TopN", "口径:全部订单"],
    notes="题面已明确'其全部已支付订单数'（不限于数码品类）；GT 含 ORDER BY，D7 保序比较",
)


if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")