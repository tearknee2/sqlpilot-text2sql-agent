"""HTTP 入参模型（doc §11.2）。"""
import re

from pydantic import BaseModel, Field, field_validator


class QueryOptions(BaseModel):
    # 注：max_retries 曾被定义但从未消费（重试次数由 settings.agent_max_retries 全局控制），
    # 为避免"看似可传实则无效"的坑，已移除。
    include_trace: bool = True


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    options: QueryOptions = Field(default_factory=QueryOptions)

    @field_validator("question")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = v.strip()
        # 匹配不可见的控制字符
        if not v or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", v):
            raise ValueError("question 含非法字符")
        return v