from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E04",
    question="2024年6月的退款总额是多少？",
    layer="时间条件",
    difficulty="medium",
    split="heldout",
    gt_sql=(
    "select sum(refund_amount) as total_refund from returns "
    "where return_date between '2024-06-01' and '2024-06-30'"
    ),              # 提示：SELECT SUM(...) FROM returns WHERE return_date BETWEEN ... AND ...
    expect="result",
    tags=["时间", "SUM/边界"],
)

print("=== 题目 ===")
print(c.question)
print("=== GT SQL ===")
print(c.gt_sql)
print("=== 执行结果 ===")
r = MySqlExecutor().execute(c.gt_sql)
print("rows:", r["row_count"])
print("columns:", r["columns"])
print("data:", r["rows"])
print("truncated:", r["truncated"])
print("error:", r["error"])   # ← 加这一行

