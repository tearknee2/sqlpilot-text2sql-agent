from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

# TODO 1: 填 split（这是可评分题，dev 还是 heldout？）
# TODO 2: 写 gt_sql（每个品类有多少个商品？）
# TODO 3: 填 tags（这题考察什么？）
c = EvalCase(
    id="E02",
    question="每个品类各有多少个商品？",
    layer="聚合分组",
    difficulty="easy",
    split="dev",
    gt_sql="select category,count(*) as product_count from products group by category",
    expect="result",
    tags=["枚举(4个品类)","分组"],
)

# 验证 GT SQL 真能跑
print("=== 题目 ===")
print(c.question)
print("=== GT SQL ===")
print(c.gt_sql)
print("=== 执行结果 ===")
r = MySqlExecutor().execute(c.gt_sql)
print("rows:", r["row_count"])
print("columns:", r["columns"])
print("data:", r["rows"])