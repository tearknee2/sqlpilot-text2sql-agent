"""Print G0 vs G1 schema_context diff (doc §5 D4 DoD, §7 self-check #1).

Purpose: prove the ONLY variable between ablation groups is table count.
If this diff shows template/metadata differences, the ablation is invalid.
"""
from __future__ import annotations

from sqlpilot.schema.catalog import get_catalog
from sqlpilot.schema.retriever import get_retriever


def gen_diff(question: str = "2024年各门店的已支付销售额前三名是哪些？") -> None:
    cat = get_catalog()
    ret = get_retriever()

    g0_tables = sorted(cat.allowed_tables)               # all 30
    g1_tables = ret.retrieve(question)                    # top-k

    g0_ctx = cat.render_schema_context(g0_tables)
    g1_ctx = cat.render_schema_context(g1_tables)

    # Use char count as a proxy for token count (roughly proportional for CJK+ASCII mix)
    g0_chars, g1_chars = len(g0_ctx), len(g1_ctx)
    ratio = 1 - g1_chars / g0_chars if g0_chars else 0.0

    print(f"Question: {question}")
    print(f"SYNONYM_VERSION = {ret.synonym_version}")
    print(f"G0 (Full-Schema): {len(g0_tables)} tables, ~{g0_chars} chars")
    print(f"G1 (+SchemaLink): {len(g1_tables)} tables, ~{g1_chars} chars")
    print(f"Reduction:        {ratio:.1%}")
    print()
    print(f"Only in G0 ({len(set(g0_tables) - set(g1_tables))}): "
          f"{sorted(set(g0_tables) - set(g1_tables))}")
    print(f"Only in G1 ({len(set(g1_tables) - set(g0_tables))}): "
          f"{sorted(set(g1_tables) - set(g0_tables))}   ← MUST be empty")
    print(f"Shared:           {sorted(set(g0_tables) & set(g1_tables))}")
    print()
    # Sanity: first 200 chars of each, side by side, prove template is identical
    print("=== G0 head (200 chars) ===")
    print(g0_ctx[:200].replace("\n", " | "))
    print("\n=== G1 head (200 chars) ===")
    print(g1_ctx[:200].replace("\n", " | "))


if __name__ == "__main__":
    gen_diff()