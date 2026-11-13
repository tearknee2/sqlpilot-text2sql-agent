"""SchemaRetriever: pick top-k tables for a question (doc ADR-6).

D2 minimal version: character-bigram overlap + keyword hints.
D4 will add synonyms.yaml (versioned) and refine scoring.
"""
from __future__ import annotations

import re
from functools import lru_cache

from sqlpilot.schema.catalog import SchemaCatalog, get_catalog

# D2 临时关键词映射；D4 会迁到 schema/synonyms.yaml 并版本化。
KEYWORD_HINTS: dict[str, list[str]] = {
    "销售额": ["orders"],
    "营业额": ["orders"],
    "订单": ["orders"],
    "已支付": ["orders"],
    "门店": ["stores"],
    "大区": ["stores"],
    "城市": ["stores", "customers"],
    "客户": ["customers"],
    "会员": ["customers"],
    "商品": ["products"],
    "品类": ["products"],
    "品牌": ["products"],
    "折扣": ["order_items"],
    "明细": ["order_items"],
    "退货": ["returns", "orders"],
    "退款": ["returns"],
}


def _bigrams(text: str) -> set[str]:
    text = re.sub(r"\s+", "", text.lower())
    if len(text) <= 1:
        return {text} if text else set()
    return {text[i : i + 2] for i in range(len(text) - 1)}


class SchemaRetriever:
    def __init__(self, catalog: SchemaCatalog | None = None, top_k: int = 5):
        self.catalog = catalog or get_catalog()
        self.top_k = top_k
        # Precompute a searchable "document" per table (table name + descriptions + enums)
        self._docs: dict[str, set[str]] = {}
        for name, t in self.catalog.tables.items():
            parts = [name, t.get("description", "")]
            for cname, c in t.get("columns", {}).items():
                parts.append(cname)
                parts.append(c.get("desc", ""))
                for e in c.get("enum") or []:
                    parts.append(str(e))
            self._docs[name] = _bigrams(" ".join(parts))

    def retrieve(self, question: str, k: int | None = None) -> list[str]:
        k = k or self.top_k
        q_grams = _bigrams(question)
        scores: dict[str, float] = {name: 0.0 for name in self._docs}

        # 1) bigram overlap
        for name, doc in self._docs.items():
            scores[name] += float(len(q_grams & doc))

        # 2) keyword hints (deterministic boost)
        for kw, targets in KEYWORD_HINTS.items():
            if kw in question:
                for t in targets:
                    if t in scores:
                        scores[t] += 5.0

        # 3) literal table-name mention
        for name in scores:
            if name.lower() in question.lower():
                scores[name] += 10.0

        ranked = sorted(
            ((s, n) for n, s in scores.items() if s > 0),
            key=lambda x: (-x[0], x[1]),   # score desc, then name asc (stable tie-break)
        )
        return [n for _, n in ranked[:k]]


@lru_cache
def get_retriever() -> SchemaRetriever:
    return SchemaRetriever()


if __name__ == "__main__":
    r = get_retriever()
    for q in [
        "2024年各门店的已支付销售额前三名是哪些？",
        "每个城市各有多少笔已支付订单？",
        "哪个品类的销售数量最多？",
        "哪个供应商的供货金额最高？",
    ]:
        print(f"Q: {q}\n  -> {r.retrieve(q)}\n")