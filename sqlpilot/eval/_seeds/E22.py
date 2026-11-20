from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E22",
    question="2024年下单次数超过15次的客户ID有哪些？",
    layer="子查询",
    difficulty="hard",
    split="dev",
    gt_sql="SELECT customer_id FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY customer_id HAVING COUNT(*) > 15",
    expect="result",
    tolerance=0,
    tags=["HAVING"],
)


if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")