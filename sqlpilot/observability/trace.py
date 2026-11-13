"""Trace writer: append JSONL per run_id (doc §13.3)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

TRACE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "traces"


class TraceWriter:
    def __init__(self, run_id: str, trace_dir: Path | None = None):
        self.run_id = run_id
        self.dir = trace_dir or TRACE_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{run_id}.jsonl"
        self._t0 = time.monotonic()

    def write(
        self,
        step: int,
        node: str,
        summary: str,
        payload: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        usage: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Append one step; return the dict so the loop can also keep it in state.trace."""
        rec = {
            "run_id": self.run_id,
            "step": step,
            "node": node,
            "ts_ms": int((time.monotonic() - self._t0) * 1000),
            "summary": summary,
            "payload": payload or {},
            "error": error,
            "usage": usage or {"prompt_tokens": 0, "completion_tokens": 0},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec


def replay(run_id: str, trace_dir: Path | None = None) -> list[dict[str, Any]]:
    """Read back a run's trace for UI / debugging."""
    d = trace_dir or TRACE_DIR
    p = d / f"{run_id}.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]