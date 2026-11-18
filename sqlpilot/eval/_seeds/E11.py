from sqlpilot.eval.models import EvalCase

c = EvalCase(
    id="E11",
    question="帮我查一下所有员工的平均工资",
    layer="不可回答",
    difficulty="medium",
    split=None,              # 不可回答题不参与准确率统计，不留 split
    gt_sql=None,             # 没有 GT SQL
    expect="refuse",         # 期望拒答
    tags=["幻觉控制", "员工薪资"],
    notes="employees 表存在但是空表（0 行）；问平均工资会得到 NULL，业务上没有可回答的数据支撑；正确行为是拒答而不是给出 NULL 或 0",
)

if __name__ == "__main__":
    print(f"{c.id}: {c.question}")
    print(f"  expect: {c.expect}")
    print(f"  tags:   {c.tags}")