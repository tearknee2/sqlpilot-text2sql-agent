from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E28", question="退货次数最多的前3个退货原因是什么？返回原因和次数",
    layer="排序TopN", difficulty="medium", split="heldout",
    gt_sql="SELECT reason, COUNT(*) AS c FROM returns GROUP BY reason ORDER BY c DESC LIMIT 3",
    expect="result", tolerance=0, tags=["TopN", "GROUP BY"]
)