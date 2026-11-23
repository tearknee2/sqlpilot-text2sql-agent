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
import hashlib

from datetime import datetime

from sqlpilot.config import get_settings
from sqlpilot.eval.models import EvalCase
from sqlpilot.tools.executor import MySqlExecutor

DATASET_DIR = Path(__file__).resolve().parent / "dataset"
V1_PATH = DATASET_DIR / "v1.jsonl"

class FakeFullRetriever:
    """G0 消融用：不做检索，永远返回全量表。"""
    def __init__(self, catalog):
        self.catalog = catalog
    def retrieve(self, question: str, k: int | None = None) -> list[str]:
        return sorted(self.catalog.allowed_tables)

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

def write_report(results, cases, args, out_path: Path) -> None:
    """生成 markdown 评测报告（doc §4.5）。"""
    # ===== 压力集报告分支 =====
    if args.stress:
        total = len(results)
        triggered_count = sum(1 for r in results if r["triggered"])
        trigger_rate = triggered_count / total if total else 0.0
        # 挽回率：触发纠错且最终 success 的题数 / 触发纠错的题数
        rescued_count = sum(1 for r in results if r["triggered"] and r["final_status"] == "success")
        rescue_rate = (rescued_count / triggered_count) if triggered_count else None
        rescue_str = f"{rescue_rate:.1%}" if rescue_rate is not None else "N/A"
        rows = "\n".join(
            f"| {r.get('run', 1)} | {r['id']} | {'✅' if r['triggered'] else '❌'} | {r['retry_count']} | {r['final_status']} |"
            for r in results
        )
        md = f"""# SQLPilot 压力集报告

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 模式：压力集（--stress）／ 重复轮数：{args.runs}／ group：`{args.group}`

## 一、纠错触发率与挽回率

| 指标 | 值 |
|---|---|
| 触发纠错题数 / 总题数 | {triggered_count}/{total} |
| 触发率 | {trigger_rate:.1%} |
| 挽回题数 / 触发题数 | {rescued_count}/{triggered_count} |
| 挽回率 | {rescue_str} |

> 触发 = 该题在本轮 `retry_count > 0`（模型首次生成 SQL 被判失败并重试）。
> 挽回率 = 触发纠错且最终 status==success 的比例（纠错把错 SQL 救回来的比例）。

## 二、逐题触发矩阵

| Run | ID | 触发纠错 | retry_count | final_status |
|---|---|---|---|---|
{rows}

## 三、说明

压力集不含 gt_sql，不判对错，只验证"能否触发自纠错"。
"""
        out_path.write_text(md, encoding="utf-8")
        print(f"\n📄 压力集报告已写入 {out_path}")
        return

    # ===== 以下为主集原逻辑，不动 =====
    # 1) 数据集 sha256（冻结指纹）
    sha = hashlib.sha256(V1_PATH.read_bytes()).hexdigest()

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    accuracy = passed_count / total if total else 0.0
    one_case_pp = 100.0 / total if total else 0.0   # 小样本声明：1 题 ≈ ?pp

    # 2) 逐题矩阵
    matrix_rows = []
    for r, c in zip(results, cases):
        icon = "✅" if r["passed"] else "❌"
        matrix_rows.append(
            f"| {r['id']} | {c.layer} | {c.difficulty} | {icon} | {r['reason']} |"
        )
    matrix = "\n".join(matrix_rows)

    # 3) model 从 settings 拿
    from sqlpilot.config import get_settings
    s = get_settings()
    model_name = s.llm_model          # 提示：Settings 里哪个字段是模型名？

    # 4) 拼 markdown
    md = f"""# SQLPilot 评测报告

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> split：`{args.split}`
> model：`{model_name}` ／ PROMPT_VERSION：`v2.0-final` ／ dataset_sha256：`{sha[:16]}...`
> **小样本声明**：当前 {total} 道可评分题（目标 24，D8 补齐）；1 题 ≈ {one_case_pp:.1f}pp；不做显著性检验，结论以逐题矩阵为准。

## 一、执行准确率

| 指标 | 值 |
|---|---|
| passed / total | {passed_count}/{total} |
| accuracy | {accuracy:.1%} |

## 二、逐题矩阵（{args.split}）

| ID | layer | difficulty | passed | reason |
|---|---|---|---|---|
{matrix}

## 三、G0/G1 消融（D11 填充）

| 组 | 执行准确率 | 说明 |
|---|---|---|
| G0 Full-Schema | ⬜ 待填 | D11（全量表，无检索） |
| G1 +SchemaLink | ⬜ 待填 | D11（top-k，无纠错） |
| **G2 Full** | **{passed_count}/{total}** | **当前**（top-k + 纠错） |

## 四、翻转清单（D11 填）

⬜ 待填（需要 G0/G1/G2 三组数据对比）

## 五、压力集（D8 建 + D11 跑）

⬜ 待填（12 道压力题）

## 六、拒答 / 安全指标

⬜ 待填（当前 dev/heldout 无 refuse/blocked 题；D8 补完 24 道后统计）

## 七、badcase 汇总

（见逐题矩阵中 ❌ 的行；D11 做详细归因）
"""
    out_path.write_text(md, encoding="utf-8")
    print(f"\n📄 报告已写入 {out_path}")


def cmd_run(args) -> int:
    """跑评测：强制 --split，逐题跑 agent + 判等，统计准确率。"""
    # Step 1: 强制 --split（D7 DoD）
    if not args.stress and not args.split:
        print("❌ 非压力集必须带 --split dev 或 --split heldout")
        return 1

    # Step 2: 读题 + 过滤 split
    if args.stress:
        stress_path = DATASET_DIR / "stress_v1.jsonl"  # 压力集路径
        all_cases = load_cases(stress_path)  # 压力集无 gt_sql
        cases = all_cases
    else:
        all_cases = load_cases(V1_PATH)
        cases = [c for c in all_cases if c.split == args.split]

    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        print("❌ 没有题目"); return 1

    print(f"split={args.split}  limit={args.limit or '∞'}  共 {len(cases)} 道题")

    # Step 3: 建 agent + executor
    from sqlpilot.agent.graph import QueryGraph
    from sqlpilot.llm.client import LLMClient
    from sqlpilot.eval.compare import compare
    llm = LLMClient()

    from sqlpilot.schema.catalog import get_catalog

    if args.group == "G0":
        # G0：全量表 → 注入假 retriever
        graph = QueryGraph(llm=llm, retriever=FakeFullRetriever(get_catalog()))
    elif args.group == "G1":
        # G1：无纠错 → 独立 settings 副本，max_retries=0
        s_copy = get_settings().model_copy(update={"agent_max_retries": 0})
        graph = QueryGraph(llm=llm, settings=s_copy)
    else:
        # G2：完整版
        graph = QueryGraph(llm=llm)


    ex = MySqlExecutor() if not args.stress else None

    # Step 4: 逐题跑
    results = []
    runs = args.runs if args.stress else 1        # 主集跑1遍，压力集跑args.runs遍

    for run_idx in range(runs):
        if args.stress:
            print(f"\n===== 压力集 第 {run_idx+1}/{runs} 轮 =====")
        for c in cases:
            print(f"\n--- {c.id} | {c.question[:40]} ---")
            agent_out = graph.run(c.question)
            pred_sql = (agent_out.get("sql") or "").strip()
            final_status = agent_out["final_status"]
            failure_reason = agent_out.get("failure_reason")
            retry_count = agent_out.get("retry_count", 0)
            print(f"  final_status: {final_status}  retry_count: {retry_count}")
            print(f"  pred_sql: {pred_sql or '(空)'}")

            # ===== 压力集：不判对错，只判"是否触发纠错(retry_count>0)" =====
            if args.stress:
                triggered = retry_count > 0
                results.append({"id": c.id, "retry_count": retry_count,
                                "final_status": final_status, "triggered": triggered,
                                "run": run_idx + 1})
                print(f"  triggered(纠错是否触发): {triggered}")
                continue

            # ===== 主集：原来的判分逻辑（result / refuse / blocked）=====
            print(f"  gt_sql:   {c.gt_sql or '(无)'}")
            if c.expect == "result":
                if not pred_sql:
                    passed, reason = False, "no_sql"
                else:
                    pred_result = ex.execute(pred_sql)
                    if pred_result["error"]:
                        passed, reason = False, f"pred_sql_error:{pred_result['error']['kind']}"
                    else:
                        gt_result = ex.execute(c.gt_sql)
                        passed, reason = compare(pred_result, gt_result, c.gt_sql, c.tolerance, c.ignore_column_order)
            elif c.expect == "refuse":
                passed = final_status == "refused" and not pred_sql
                reason = "refuse_ok" if passed else f"expected_refuse_got_{final_status}"
            else:  # blocked
                passed = final_status == "refused" and failure_reason == "SQL_BLOCKED"
                reason = "blocked_ok" if passed else f"expected_blocked_got_{failure_reason}"

            print(f"  passed: {passed}  reason: {reason}")
            results.append({"id": c.id, "passed": passed, "reason": reason})

    # Step 5: 汇总
    total = len(results)

    if args.stress:
        # ===== 压力集：统计"触发率"（retry_count>0 的题数）=====
        triggered_count = sum(1 for r in results if r["triggered"])
        trigger_rate = triggered_count / total if total else 0.0
        print("\n=== 压力集汇总 ===")
        print(f"总题数: {total}  触发纠错的题数: {triggered_count}  触发率: {trigger_rate:.1%}")
        print("逐题 trigger 情况:")
        for r in results:
            mark = "✅触发" if r["triggered"] else "❌未触发"
            print(f"  {r['id']}: {mark}  retry_count={r['retry_count']}  status={r['final_status']}")
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            write_report(results, cases, args, out_path)
        return 0
    else:
        # ===== 主集：原逻辑 =====
        passed_count = sum(1 for r in results if r["passed"])
        accuracy = passed_count / total     # 准确率公式
        print(f"\n=== 汇总 ===")
        print(f"passed: {passed_count}/{total}  accuracy: {accuracy:.1%}")
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            write_report(results, cases, args, out_path)
        return 0 if passed_count == total else 1

def main() -> int:
    parser = argparse.ArgumentParser(prog="sqlpilot.eval")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="检查评测集")
    p_val.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="跑评测")
    p_run.add_argument("--split", choices=["dev", "heldout"], required=False)
    p_run.add_argument("--limit", type=int, default=0)
    p_run.add_argument("--out", default=None, help="报告输出路径（如 eval/report.md）")
    p_run.add_argument("--group", choices=["G0", "G1", "G2"], default="G2")
    p_run.add_argument("--stress", action="store_true", help="跑压力集 stress_v1.jsonl")
    p_run.add_argument("--runs", type=int, default=1, help="重复跑几次（压力集用 2）")

    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())