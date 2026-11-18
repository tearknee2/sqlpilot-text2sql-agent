from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E06",
    question="所有订单明细的商品金额合计是多少？",
    layer="脏数据",
    difficulty="hard",
    split="dev",
    gt_sql=(
        "select sum(qty * unit_price * (1 - coalesce(discount, 0))) "
        "as total_amount from order_items"
    ),           # COALESCE(discount, 0)
    expect="result",
    tolerance=0.01,        # 金额，精确到分 → 0.01
    tags=["NULL折扣", "COALESCE/口径"],
    notes="陷阱：discount 约 30% 为 NULL，不写 COALESCE 会少算约 30% 的行",
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
print("error:", r["error"])

# ===== 陷阱验证：不带 COALESCE 会差多少 =====
print("\n=== 对比：不带 COALESCE（模拟模型踩坑） ===")
bad_sql = "select sum(qty * unit_price * (1 - discount)) as total_amount from order_items"
rb = MySqlExecutor().execute(bad_sql)
print("bad data:", rb["rows"])
if r["rows"] and rb["rows"] and r["rows"][0][0] is not None and rb["rows"][0][0] is not None:
    diff = float(r["rows"][0][0]) - float(rb["rows"][0][0] or 0)
    print(f"差: {diff:.2f}")