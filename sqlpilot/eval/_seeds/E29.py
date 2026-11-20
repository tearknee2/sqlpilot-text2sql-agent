from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E29", question="2024年销售额最高的前3个商品品类是什么？返回品类和销售额",
    layer="多表JOIN", difficulty="hard", split="dev",
    gt_sql="SELECT p.category, SUM(oi.qty * oi.unit_price * (1 - COALESCE(oi.discount, 0))) AS sales FROM order_items oi JOIN products p ON oi.product_id = p.product_id JOIN orders o ON oi.order_id = o.order_id WHERE o.order_date BETWEEN '2024-01-01' AND '2024-12-31' AND LOWER(TRIM(o.status)) = 'paid' GROUP BY p.category ORDER BY sales DESC LIMIT 3",
    expect="result", tolerance=0.01, tags=["三表JOIN", "TopN", "COALESCE"]
)