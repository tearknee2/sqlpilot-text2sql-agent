from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E24", question="2024年每个月的已支付订单总金额是多少？按月排序",
    layer="聚合分组", difficulty="hard", split="heldout",
    gt_sql="SELECT DATE_FORMAT(order_date, '%Y-%m') AS month, SUM(amount) AS total FROM orders WHERE LOWER(TRIM(status)) = 'paid' GROUP BY month ORDER BY month",
    expect="result", tolerance=0.01, tags=["时间", "DATE_FORMAT", "脏数据"]
)