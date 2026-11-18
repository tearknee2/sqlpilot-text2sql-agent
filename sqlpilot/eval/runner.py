"""评测引擎 CLI（doc §4.7）。

子命令：
  validate  检查评测集本身（GT SQL 可执行、expect 字段合法）
  run       跑评测（强制 --split，D8 再实现）
  badcases  badcase 归因（D11 再实现）
"""
import argparse
import json
import sys
from pathlib import Path

from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

DATASET_DIR = Path(__file__).resolve().parent / "dataset"
V1_PATH = DATASET_DIR / "v1.jsonl"


def load_cases(path: Path) -> list[EvalCase]:
    """读 JSONL，每行构造 EvalCase。"""
    cases = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            cases.append(EvalCase(**data))
    return cases


def cmd_validate(args) -> int:
    """检查评测集：可评分题 GT SQL 可执行；不可评分题无 gt_sql。"""
    cases = load_cases(V1_PATH)
    print(f"加载 {len(cases)} 道题 from {V1_PATH}")
    print()

    ex = MySqlExecutor()
    errors = 0

    for c in cases:
        # 1) 字段合法性
        if c.expect == "result":
            if not c.gt_sql:
                print(f"❌ {c.id}: expect=result 但缺 gt_sql")
                errors += 1
                continue
            if not c.split:
                print(f"❌ {c.id}: expect=result 但缺 split")
                errors += 1
                continue
            # 2) GT SQL 可执行
            r = ex.execute(c.gt_sql)
            if r["error"]:
                print(f"❌ {c.id}: GT SQL 执行失败: {r['error']['kind']}")
                errors += 1
            else:
                print(f"✅ {c.id:4s} rows={r['row_count']:3d}  {c.question[:30]}")

        elif c.expect in ("refuse", "blocked"):
            if c.gt_sql:
                print(f"❌ {c.id}: expect={c.expect} 不该有 gt_sql")
                errors += 1
            elif c.split:
                print(f"❌ {c.id}: expect={c.expect} 不该有 split")
                errors += 1
            else:
                print(f"✅ {c.id:4s} {c.expect:8s}  {c.question[:30]}")

        else:
            print(f"❌ {c.id}: 未知 expect={c.expect}")
            errors += 1

    print()
    if errors:
        print(f"❌ {errors} 道题有错误")
        return 1
    print(f"✅ 全部 {len(cases)} 道题通过校验")
    return 0

def cmd_run(args) -> int:
    """跑评测：强制 --split，逐题跑 agent + 判等，统计准确率。"""
    # Step 1: 强制 --split（D7 DoD）
    if not args.split:
        print("❌ run 必须带 --split dev 或 --split heldout")
        return 1

    # Step 2: 读题 + 过滤 split
    all_cases = load_cases(V1_PATH)
    cases = [c for c in all_cases if c.split == args.split]
    if args.limit:
        cases = cases[: args.limit]

    if not cases:
        print(f"❌ split={args.split} 下没有题")
        return 1

    print(f"split={args.split}  limit={args.limit or '∞'}  共 {len(cases)} 道题")

    # Step 3: 建 agent + executor
    from sqlpilot.agent.graph import QueryGraph
    from sqlpilot.llm.client import LLMClient
    from sqlpilot.eval.compare import compare

    llm = LLMClient()
    graph = QueryGraph(llm=llm)
    ex = MySqlExecutor()

    # Step 4: 逐题跑
    results = []
    for c in cases:
        print(f"\n--- {c.id} | {c.question[:40]} ---")
        agent_out = graph.run(c.question)
        pred_sql = (agent_out.get("sql") or "").strip()
        final_status = agent_out["final_status"]
        failure_reason = agent_out.get("failure_reason")
        print(f"  final_status: {final_status}")
        print(f"  pred_sql: {pred_sql or '(空)'}")
        print(f"  gt_sql:   {c.gt_sql or '(无)'}")

        # Step 4a: 按 expect 判对错
        if c.expect == "result":
            if not pred_sql:
                passed, reason = False, "no_sql"
            else:
                pred_result = ex.execute(pred_sql)
                if pred_result["error"]:
                    passed, reason = False, f"pred_sql_error:{pred_result['error']['kind']}"
                else:
                    gt_result = ex.execute(c.gt_sql)
                    passed, reason = compare(pred_result, gt_result, c.gt_sql, c.tolerance, c.ignore_column_order)    # 调 compare

        elif c.expect == "refuse":
            # 必须 final_status=refused 且 sql 为空
            passed = final_status=="refused" and not pred_sql
            reason = "refuse_ok" if passed else f"expected_refuse_got_{final_status}_sql_len_{len(pred_sql)}"

        else:  # blocked
            # 必须 final_status=refused 且 failure_reason=SQL_BLOCKED
            passed = final_status=="refused" and failure_reason == "SQL_BLOCKED"
            reason = "blocked_ok" if passed else f"expected_blocked_got_{failure_reason}"

        print(f"  passed: {passed}  reason: {reason}")
        results.append({"id": c.id, "passed": passed, "reason": reason})

    # Step 5: 汇总
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    accuracy = passed_count / total     # 准确率公式
    print(f"\n=== 汇总 ===")
    print(f"passed: {passed_count}/{total}  accuracy: {accuracy:.1%}")
    return 0 if passed_count == total else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="sqlpilot.eval")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="检查评测集")
    p_val.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="跑评测")
    p_run.add_argument("--split", choices=["dev", "heldout"], required=False)
    p_run.add_argument("--limit", type=int, default=0)
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())