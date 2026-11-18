from sqlpilot.eval.models import EvalCase

c = EvalCase(
    id="E09",
    question="哪个供应商的供货金额最高？",
    layer="不可回答",
    difficulty="medium",
    split=None,              # 不可回答题不参与准确率统计，不留 split
    gt_sql=None,             # 没有 GT SQL
    expect="refuse",         # 期望拒答
    tags=["幻觉控制", "供应商"],
    notes="suppliers 表存在（D1 decoy 建了 DDL）但无数据；正确行为是拒答而不是生成 SQL",
)

if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    print(f"  expect: {c.expect}")
    print(f"  tags:   {c.tags}")