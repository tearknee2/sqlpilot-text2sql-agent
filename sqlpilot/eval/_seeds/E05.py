from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor
"""
"2024 年各门店的已支付销售额 Top3，只要已支付订单"

它是项目里最有代表性的题，因为同时考察：

多表 JOIN（orders JOIN stores）

聚合（SUM(amount)）

排序（ORDER BY sales DESC）

TopN（LIMIT 3）

脏数据清洗（LOWER(TRIM(status))='paid'）

时间条件（BETWEEN '2024-01-01' AND '2024-12-31'）

列幻觉风险（orders.amount 容易被幻觉成 total_amount）
"""
c = EvalCase(
    id="E05",
    question="2024年各门店的已支付销售额，从高到低取前三名",
    layer="排序TopN",
    difficulty="hard",
    split="dev",
    gt_sql=(
    "select s.store_name,sum(o.amount) as sales "
    "from orders o join stores s "
    "on o.store_id = s.store_id "
    "where o.order_date between '2024-01-01' and '2024-12-31' "
    "and lower(trim(o.status))='paid' "
    "group by s.store_name order by sales desc limit 3"
    ),              # 这是 D2 旗舰 demo 的 GT SQL，和 loop_fallback 里 FakeLLM 的答案一致
    expect="result",
    tolerance=0.01,           # 金额，精确到分 → 0.01
    ignore_column_order=True,
    tags=["多表JOIN", "TopN", "脏数据:status"],
    notes="GT SQL 含 ORDER BY，比对时保序（D7 compare.py 按 ORDER BY 判）",
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