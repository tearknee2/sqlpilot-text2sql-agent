from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E20",
    question="已取消（cancelled）的订单总金额是多少？",
    layer="脏数据",
    difficulty="medium",
    split="dev",
    gt_sql="SELECT SUM(amount) AS s FROM orders WHERE LOWER(TRIM(status)) = 'cancelled'",
    expect="result",
    tolerance=0.01,
    tags=["脏数据", "COALESCE"],
)


if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")