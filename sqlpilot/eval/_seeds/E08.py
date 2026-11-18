from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E08",
    question="所有商品的平均售价是多少？",
    layer="脏数据",
    difficulty="medium",
    split="heldout",
    gt_sql="select avg(price) as avg_price from products",              # 选口径 A：AVG(price)
    expect="result",
    tolerance=0.01,           # 均价，精确到分 → 0.01
    tags=["price NULL", "AVG口径"],
    notes="陷阱：AVG(price) 内部是 SUM/COUNT(price)，分母只数 117 个非 NULL；"
          "若写成 SUM/COUNT(*) 分母变 120（含 3 个 NULL），结果偏小约 2.5%",             # 写清楚：AVG 忽略 3 个 NULL，口径 = 已定价商品
)

print("=== 题目 ===")
print(c.question)
print("=== GT SQL ===")
print(c.gt_sql)
print("=== 执行结果 ===")
r = MySqlExecutor().execute(c.gt_sql)
print("rows:", r["row_count"], "data:", r["rows"], "error:", r["error"])

# 陷阱：SUM/COUNT(*) 会把 3 个 NULL 算进分母
print("\n=== 对比：SUM(price)/COUNT(*)（模拟模型踩坑） ===")
bad_sql = "select sum(price) / count(*) as avg_price from products"
rb = MySqlExecutor().execute(bad_sql)
print("bad data:", rb["rows"])
diff = float(r["rows"][0][0]) - float(rb["rows"][0][0])
print(f"差: {diff:.4f}（占 {diff / float(r['rows'][0][0]) * 100:.2f}%）")

# 手动验证这个数字
r = MySqlExecutor().execute("SELECT SUM(price) AS s, COUNT(price) AS c1, COUNT(*) AS c2 FROM products")
print(r["rows"])   # 期望 [(Decimal('292611.83'), 117, 120)]