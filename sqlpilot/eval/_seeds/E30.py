from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E30", question="哪些门店的已支付订单数低于所有门店的平均订单数？返回门店名称",
    layer="子查询", difficulty="hard", split="dev",
    gt_sql="SELECT s.store_name FROM stores s JOIN orders o ON s.store_id = o.store_id WHERE LOWER(TRIM(o.status)) = 'paid' GROUP BY s.store_name HAVING COUNT(*) < (SELECT AVG(cnt) FROM (SELECT COUNT(*) AS cnt FROM orders WHERE LOWER(TRIM(status)) = 'paid' GROUP BY store_id) t)",
    expect="result", tolerance=0, tags=["标量子查询", "HAVING", "AVG"]
)