"""Minimal LangGraph demo: 4 nodes, 1 conditional edge. No LLM, no DB.

Purpose: prove the 4 concepts (State / Node / Edge / Conditional Edge)
before migrating the real loop in graph.py.
"""
from typing import TypedDict

from langgraph.graph import END, StateGraph


class MiniState(TypedDict, total=False):
    question: str
    attempts: int
    max_attempts: int
    sql: str
    result: str
    trace: list[str]


def node_start(state: MiniState) -> dict:
    return {"trace": state.get("trace", []) + ["start"], "attempts": 0}


def node_generate(state: MiniState) -> dict:
    n = state.get("attempts", 0) + 1
    # 前两次故意写错，第三次写对
    sql = "SELECT total_amount FROM orders" if n < 3 else "SELECT amount FROM orders"
    return {
        "attempts": n,
        "sql": sql,
        "trace": state.get("trace", []) + [f"generate(#{n}): {sql}"],
    }


def node_validate(state: MiniState) -> dict:
    ok = "total_amount" not in state["sql"]
    return {"trace": state.get("trace", []) + [f"validate: {'pass' if ok else 'fail'}"]}


def node_execute(state: MiniState) -> dict:
    return {"result": "3 rows", "trace": state.get("trace", []) + ["execute"]}


def route_after_validate(state: MiniState) -> str:
    if "total_amount" in state["sql"]:
        if state["attempts"] < state["max_attempts"]:
            return "retry"
        return "give_up"
    return "pass"


def build_mini_graph():
    b = StateGraph(MiniState)
    b.add_node("start", node_start)
    b.add_node("generate", node_generate)
    b.add_node("validate", node_validate)
    b.add_node("execute", node_execute)
    b.add_node("give_up", lambda s: {"result": "gave up"})

    b.set_entry_point("start")
    b.add_edge("start", "generate")
    b.add_edge("generate", "validate")
    b.add_conditional_edges(
        "validate",
        route_after_validate,
        {"pass": "execute", "retry": "generate", "give_up": "give_up"},
    )
    b.add_edge("execute", END)
    b.add_edge("give_up", END)
    return b.compile()


if __name__ == "__main__":
    g = build_mini_graph()
    out = g.invoke({"question": "demo", "max_attempts": 3, "trace": []})
    print("attempts:", out["attempts"])
    print("result:  ", out["result"])
    print("trace:")
    for t in out["trace"]:
        print("  -", t)