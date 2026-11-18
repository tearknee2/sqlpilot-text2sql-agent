from sqlpilot.eval.models import EvalCase

c = EvalCase(
    id="E10",
    question="帮我查一下所有商品的颜色分布",
    layer="不可回答",
    difficulty="medium",
    split=None,              # 不可回答题不参与准确率统计，不留 split
    gt_sql=None,             # 没有 GT SQL
    expect="refuse",         # 期望拒答
    tags=["幻觉控制", "商品颜色"],
    notes="products 表存在，但没有 color 列；正确行为是 generate_sql 就返回 refuse，而不是生成 SELECT color 的 SQL 让 DB 报 1054",
)

if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    print(f"  expect: {c.expect}")
    print(f"  tags:   {c.tags}")