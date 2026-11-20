from sqlpilot.eval.models import EvalCase
c = EvalCase(
    id="E27", question="一共有多少个商品已经维护了售价（price不为空）？",
    layer="脏数据", difficulty="easy", split="heldout",
    gt_sql="SELECT COUNT(*) AS c FROM products WHERE price IS NOT NULL",
    expect="result", tolerance=0, tags=["NULL", "COUNT"]
)