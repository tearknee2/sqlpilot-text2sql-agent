"""SchemaRetriever: pick top-k tables for a question (doc ADR-6 / §5 D4).

Scoring:
  1) bigram overlap  (weak signal, weight 0.5)
  2) synonym boost   (strong signal, weight 10, from synonyms.yaml)
  3) exact table name mention (weight 20)
  4) OUT-OF-SCOPE filter: if no business synonym matched, return [].
     This is what makes 供应商 -> [] so D6 E10 (unanswerable) can be tested.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from sqlpilot.schema.catalog import SchemaCatalog, get_catalog

SYNONYMS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "schema" / "synonyms.yaml"
)


def _bigrams(text: str) -> set[str]:
    text = re.sub(r"\s+", "", text.lower())
    if len(text) <= 1:
        return {text} if text else set()
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _load_synonyms(path: Path | None = None) -> tuple[dict[str, list[str]], str]:
    p = path or SYNONYMS_PATH
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data["synonyms"], data["version"]


class SchemaRetriever:
    def __init__(self, catalog: SchemaCatalog | None = None, top_k: int = 5,
                 synonyms_path: Path | None = None):
        self.catalog = catalog or get_catalog()
        self.top_k = top_k
        self.synonyms, self.synonym_version = _load_synonyms(synonyms_path)
        # Precompute a searchable "document" per table (name + descriptions + enums)
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

        # OUT-OF-SCOPE gate: no business synonym matched => this question is
        # about something the DB doesn't cover (e.g. 供应商). Return [] so
        # downstream generate_sql refuses. This is D4's "供应商召回空" check.
        matched_synonyms = [s for s in self.synonyms if s in question]
        if not matched_synonyms:
            return []

        q_grams = _bigrams(question)
        scores: dict[str, float] = {name: 0.0 for name in self._docs}

        # 1) bigram overlap (weak)
        for name, doc in self._docs.items():
            scores[name] += 0.5 * len(q_grams & doc)

        # 2) synonym boost (strong)
        for syn in matched_synonyms:
            for target in self.synonyms[syn]:
                if target in scores:
                    scores[target] += 10.0

        # 3) exact table-name mention
        for name in scores:
            if name.lower() in question.lower():
                scores[name] += 20.0

        ranked = sorted(
            ((s, n) for n, s in scores.items() if s > 0),
            key=lambda x: (-x[0], x[1]),   # score desc, name asc for stable tie-break
        )
        return [n for _, n in ranked[:k]]


@lru_cache
def get_retriever() -> SchemaRetriever:
    return SchemaRetriever()


if __name__ == "__main__":
    r = get_retriever()
    print(f"SYNONYM_VERSION = {r.synonym_version}\n")
    cases = [
        ("2024年各门店的已支付销售额前三名是哪些？", "orders + stores"),
        ("每个城市各有多少笔已支付订单？",           "orders + stores"),
        ("哪个品类的销售数量最多？",                 "products + order_items"),
        ("哪个供应商的供货金额最高？",               "[] (out of scope)"),
    ]
    for q, expected in cases:
        got = r.retrieve(q)
        print(f"Q: {q}\n   expect: {expected}\n   got:    {got}\n")