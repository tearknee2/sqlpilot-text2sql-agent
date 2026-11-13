"""SchemaCatalog: load schema_catalog.yaml, expose structured access (doc §9.4).

ADR-12: render_schema_context() is the SAME template for G0 (all 30 tables)
and G1 (top-k). The only variable between groups is which table names are passed.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# 外层 schema/schema_catalog.yaml（数据文件，不是内层包）
CATALOG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "schema" / "schema_catalog.yaml"
)


class SchemaCatalog:
    def __init__(self, path: Path = CATALOG_PATH):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.version: int = raw["version"]
        self.database: str = raw["database"]
        self.tables: dict[str, dict[str, Any]] = raw["tables"]
        # Derived indices (computed once at load time)
        self.allowed_tables: set[str] = set(self.tables)
        self.columns_by_table: dict[str, set[str]] = {
            name: set(t.get("columns", {})) for name, t in self.tables.items()
        }

    def render_schema_context(self, table_names: list[str]) -> str:
        """Render the schema block for the prompt. Same template for G0 and G1."""
        lines: list[str] = []
        for name in table_names:
            t = self.tables.get(name)
            if not t:
                continue
            lines.append(f"### {name}")
            if t.get("description"):
                lines.append(f"描述: {t['description']}")
            if t.get("row_count_hint"):
                lines.append(f"约 {t['row_count_hint']} 行")
            lines.append("列:")
            for cname, c in t.get("columns", {}).items():
                bits = [f"  - {cname} ({c.get('type', '?')})"]
                if c.get("desc"):
                    bits.append(f": {c['desc']}")
                if c.get("enum"):
                    bits.append(f" 枚举={c['enum']}")
                if c.get("note"):
                    bits.append(f" [注意] {c['note']}")
                lines.append("".join(bits))
            if t.get("join_paths"):
                lines.append("关联: " + "; ".join(t["join_paths"]))
            if t.get("pitfalls"):
                lines.append("口径/陷阱:")
                for p in t["pitfalls"]:
                    lines.append(f"  * {p}")
            lines.append("")
        return "\n".join(lines).strip()


@lru_cache
def get_catalog() -> SchemaCatalog:
    return SchemaCatalog()