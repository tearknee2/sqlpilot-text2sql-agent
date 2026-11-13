"""kind -> repair strategy dispatch table (doc §2.4 / ADR-5).

This module does NOT recompute `kind`. It only maps an already-decided kind
to deterministic repair flags. Routing by LLM is forbidden (ADR-5).
"""
from __future__ import annotations

from typing import Any

# kind -> {"relink": bool, "inject": str}
# relink=True => go back to retrieve_schema before regenerating.
REPAIR_STRATEGY: dict[str, dict[str, Any]] = {
    "UNKNOWN_COLUMN":  {"relink": True,  "inject": "候选列"},
    "UNKNOWN_TABLE":   {"relink": True,  "inject": "候选表"},
    "TYPE_MISMATCH":   {"relink": True,  "inject": "列类型与示例值"},
    "SYNTAX":          {"relink": False, "inject": "MySQL 1064 原文 + 上一条 SQL"},
    "OTHER":           {"relink": False, "inject": "通用反思"},
}

# Terminal kinds: no retry (doc §2.4).
TERMINAL_KINDS: set[str] = {"BLOCKED", "EMPTY_RESULT", "QUERY_TIMEOUT", "ROW_TRUNCATED"}

# Recoverable kinds: enter the correction loop.
RECOVERABLE_KINDS: set[str] = set(REPAIR_STRATEGY)


def needs_relink(kind: str) -> bool:
    return REPAIR_STRATEGY.get(kind, {}).get("relink", False)


def is_recoverable(kind: str) -> bool:
    return kind in RECOVERABLE_KINDS


def is_terminal(kind: str) -> bool:
    return kind in TERMINAL_KINDS