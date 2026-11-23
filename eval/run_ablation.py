"""消融实验复现脚本：循环跑 N 次并对每组打印 平均准确率 + 观察范围(最低~最高)。

用法（项目根目录）：
    python eval/run_ablation.py                    # 默认: --split dev --runs 10 --groups G0,G1,G2
    python eval/run_ablation.py --runs 5
    python eval/run_ablation.py --groups G2 --split heldout

说明：
  - LLM 即使在 temperature=0 下也存在题级生成抖动，单次运行结果不完全可复现。
  - 本脚本通过"多次重复"给出观察范围（非统计学置信区间），如实呈现波动。
  - 每次运行复用 sqlpilot.eval.runner 的 cmd_run，与正式评测同一套逻辑。
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlpilot.eval import runner  # noqa: E402


def run_once(split: str, group: str) -> float | None:
    """跑一次指定组，返回准确率(0~100)；失败返回 None。"""
    args = argparse.Namespace(split=split, group=group, limit=0, out=None,
                              stress=False, runs=1)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            runner.cmd_run(args)
    except SystemExit:
        pass
    out = buf.getvalue()
    m = re.search(r"accuracy:\s*([\d.]+)%", out)
    return float(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="消融实验多次重复汇总")
    ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--runs", type=int, default=10, help="每组重复次数")
    ap.add_argument("--groups", default="G0,G1,G2", help="逗号分隔，如 G0,G1,G2")
    a = ap.parse_args()
    groups = [g.strip().upper() for g in a.groups.split(",") if g.strip()]

    print(f"\n消融复现：split={a.split}  runs={a.runs}  groups={groups}")
    print("（LLM 有生成抖动，下列为多次运行的观察范围，非统计学置信区间）\n")

    results: dict[str, list[float]] = {}
    for g in groups:
        accs: list[float] = []
        for i in range(1, a.runs + 1):
            acc = run_once(a.split, g)
            if acc is not None:
                accs.append(acc)
                print(f"  [{g}] run{i}: {acc:.2f}%")
        results[g] = accs

    print("\n" + "=" * 56)
    print(f"{'组':<6}{'平均':>10}{'最低':>10}{'最高':>10}{'样本':>8}")
    print("-" * 56)
    for g in groups:
        accs = results.get(g) or []
        if not accs:
            print(f"{g:<6}{'N/A':>10}")
            continue
        avg = sum(accs) / len(accs)
        print(f"{g:<6}{avg:>9.2f}%{min(accs):>9.2f}%{max(accs):>9.2f}%{len(accs):>7}")
    print("=" * 56)
    print("\n注：区间为 '最低%~最高%' 的观察范围；样本小(16题)且含 LLM 抖动，不做显著性断言。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
