"""QueryService：API 与 eval 共用的查询入口（doc ADR-8）。"""
from typing import Any

from sqlpilot.agent.graph import QueryGraph
from sqlpilot.llm.client import LLMClient


class QueryService:
    def __init__(self):
        self.llm = LLMClient()
        self.graph = QueryGraph(llm=self.llm)

    def query(self, question: str) -> dict[str, Any]:
        """传入自然语言问题，返回 graph.run 的完整结果。"""
        return self.graph.run(question)