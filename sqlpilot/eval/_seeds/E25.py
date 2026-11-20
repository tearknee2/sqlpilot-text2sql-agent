from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E25", question="2024年“食品”品类的商品销售件数总和是多少？",
    layer="多表JOIN", difficulty="hard", split="heldout",
    gt_sql="SELECT SUM(oi.qty) AS s FROM order_items oi JOIN products p ON oi.product_id = p.product_id JOIN orders o ON oi.order_id = o.order_id WHERE p.category = '食品' AND LOWER(TRIM(o.status)) = 'paid'",
    expect="result", tolerance=0, tags=["多表JOIN", "脏数据"]
)