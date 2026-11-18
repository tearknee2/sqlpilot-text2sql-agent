from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

'''

设计 E03：一道"多表 JOIN"层的题。

题目：每个城市各有多少笔已支付订单？

这道题的价值（为什么选它）：

需要 orders JOIN stores（orders.store_id → stores.store_id）

需要脏数据清洗（status='PAID ' 带空格，必须用 LOWER(TRIM(status))='paid'）

是 D4 retriever 验证过的题，已知能召回 orders + stores
'''
c = EvalCase(
    id="E03",
    question="每个城市各有多少笔已支付订单？",
    layer="多表JOIN",
    difficulty="medium",
    split="dev",
    gt_sql=(
        "select s.city, count(*) as order_count "
        "from orders o join stores s "
        "on o.store_id = s.store_id "
        "where lower(trim(o.status)) = 'paid' "
        "group by s.city"
    ),
    expect="result",
    tags=["join路径", "脏数据:status"],
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