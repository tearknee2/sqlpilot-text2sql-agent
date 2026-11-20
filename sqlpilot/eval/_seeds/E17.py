from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E17",
    question="银卡会员总共有多少人？",
    layer="单表筛选",
    difficulty="easy",
    split="dev",
    gt_sql="SELECT COUNT(*) AS c FROM customers WHERE member_level = '银卡'",
    expect="result",
    tolerance=0,
    tags=["枚举", "COUNT"],
)



if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")