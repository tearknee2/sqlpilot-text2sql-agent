from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E26", question="购买过“质量问题”退货商品的客户ID去重后有哪些？",
    layer="子查询", difficulty="hard", split="heldout",
    gt_sql="SELECT DISTINCT o.customer_id FROM orders o JOIN returns r ON o.order_id = r.order_id WHERE r.reason = '质量问题'",
    expect="result", tolerance=0, tags=["DISTINCT", "JOIN"]
)