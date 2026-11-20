from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E21",
    question="客单价（平均每个订单的金额）高于1000元的门店有哪些？返回门店名称",
    layer="子查询",
    difficulty="hard",
    split="dev",
    gt_sql="SELECT s.store_name FROM stores s JOIN orders o ON s.store_id = o.store_id WHERE LOWER(TRIM(o.status))='paid' GROUP BY s.store_name HAVING AVG(o.amount) > 1000",
    expect="result",
    tolerance=0,
    tags=["HAVING", "AVG"],
)


if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")