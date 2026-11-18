from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E07",
    question="一共有多少个客户？",
    layer="脏数据",
    difficulty="medium",
    split="dev",
    gt_sql="select count(*) from customers",              # COUNT 应该用 customer_id 还是 customer_name？还是 COUNT(*)？
    expect="result",
    tolerance=0,           # COUNT 返回整数，容差多少？
    tags=["同名客户", "COUNT口径"],
    notes="错误的COUNT SQL,用 COUNT(DISTINCT customer_name)（这个写法在人眼看来合理，但实际漏算同名）",
)

print("=== 题目 ===")
print(c.question)
print("=== GT SQL ===")
print(c.gt_sql)
print("=== 执行结果 ===")
r = MySqlExecutor().execute(c.gt_sql)
print("rows:", r["row_count"])
print("data:", r["data"] if "data" in r else r["rows"])
print("error:", r["error"])

# ===== 陷阱验证：COUNT(DISTINCT customer_name) 会少多少 =====
print("\n=== 对比：COUNT(DISTINCT customer_name)（模拟模型踩坑） ===")
bad_sql = "select count(distinct customer_name) from customers"
rb = MySqlExecutor().execute(bad_sql)
print("bad data:", rb["rows"])
print("差:", int(r["rows"][0][0]) - int(rb["rows"][0][0]))