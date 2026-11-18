"""评测集数据模型（doc §11.2 EvalCase）。"""
from typing import Literal

from pydantic import BaseModel, Field


Difficulty = Literal["easy", "medium", "hard"]
Layer = Literal[
    "单表筛选", "聚合分组", "多表JOIN", "时间条件",
    "排序TopN", "子查询", "脏数据", "不可回答", "安全注入",
]
Split = Literal["dev", "heldout"]


class EvalCase(BaseModel):
    id: str
    question: str
    layer: Layer
    difficulty: Difficulty
    split: Split | None = None     # 可评分题必填；不可回答/注入题留空
    gt_sql: str | None = None    # 不可回答/安全题为 None
    expect: Literal["result", "refuse", "blocked"]
    tolerance: float = 1e-6
    ignore_column_order: bool = True
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


if __name__ == "__main__":
    # smoke test：创建一个可评分题，确认模型能用
    c = EvalCase(
        id="E01",
        question="华东大区有哪些门店？列出门店名和城市",
        layer="单表筛选",
        difficulty="easy",
        split="dev",
        gt_sql="SELECT store_name, city FROM stores WHERE region = '华东'",
        expect="result",
        tags=["枚举"],
    )
    print(c.model_dump_json(indent=2))