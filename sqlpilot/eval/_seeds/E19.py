from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

c = EvalCase(
    id="E19",
    question="哪个品牌的商品总售价最高？返回品牌和总售价",
    layer="多表JOIN",
    difficulty="medium",
    split="dev",
    gt_sql="SELECT brand, SUM(price) AS total_price FROM products GROUP BY brand ORDER BY total_price DESC LIMIT 1",
    expect="result",
    tolerance=0.01,
    tags=["多表JOIN", "ORDER BY"],
)



if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    r = MySqlExecutor().execute(c.gt_sql)
    print(f"  rows: {r['row_count']} data: {r['rows']}")
    print(f"  error: {r['error']}")