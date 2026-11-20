from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E18",
    question="2024年第一季度（1月到3月）的总订单数是多少？",
    layer="时间条件",
    difficulty="medium",
    split="dev",
    gt_sql="SELECT COUNT(*) AS c FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-03-31'",
    expect="result",
    tolerance=0,
    tags=["时间", "BETWEEN"],
)


if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")