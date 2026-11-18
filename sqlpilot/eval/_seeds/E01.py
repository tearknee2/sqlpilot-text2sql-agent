from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E01",
    question="华东大区有哪些门店？列出门店名和城市",
    layer="单表筛选",
    difficulty="easy",
    split="dev",
    gt_sql="SELECT store_name, city FROM stores WHERE region = '华东'",
    expect="result",
    tags=["枚举"],
)


if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")