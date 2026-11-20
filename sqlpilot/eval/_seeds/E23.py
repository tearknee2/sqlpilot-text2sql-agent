from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E23", question="2024年上半年（1月到6月）注册的客户有多少人？",
    layer="时间条件", difficulty="medium", split="heldout",
    gt_sql="SELECT COUNT(*) AS c FROM customers WHERE register_date BETWEEN '2024-01-01' AND '2024-06-30'",
    expect="result", tolerance=0, tags=["时间", "BETWEEN"]
)


