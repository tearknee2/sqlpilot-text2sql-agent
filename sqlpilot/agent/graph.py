"""LangGraph version of the agent loop (doc §2.5).

Behavior MUST match loop_fallback.py:
  step_count=10, sql_attempts=2, retry_count=1, llm_calls=4,
  two validate_sql steps, first one UNKNOWN_COLUMN before hitting DB.

Nodes return dicts (partial state updates), never mutate state in place.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph

from sqlpilot.agent.errors import TERMINAL_KINDS, needs_relink as _needs_relink
from sqlpilot.agent.loop_fallback import _budget_ok, _init_state
from sqlpilot.agent.prompts import (
    GEN_SQL_SYSTEM, REFLECT_SYSTEM, SUMMARIZE_SYSTEM,
    gen_sql_user, reflect_user, summarize_user,
)
from sqlpilot.agent.state import AgentState
from sqlpilot.config import get_settings
from sqlpilot.guard.sql_guard import SqlGuard
from sqlpilot.observability.trace import TraceWriter
from sqlpilot.schema.catalog import get_catalog
from sqlpilot.schema.retriever import get_retriever
from sqlpilot.tools.executor import MySqlExecutor


class GraphNodes:
    """All node functions + routing functions, bound to dependencies."""

    def __init__(self, llm, executor=None, guard=None, retriever=None,
                 trace_dir=None, settings=None):
        self.s = settings or get_settings()
        self.llm = llm
        self.executor = executor or MySqlExecutor(self.s)
        self.catalog = get_catalog()
        self.guard = guard or SqlGuard(self.catalog, max_rows=self.s.sql_max_rows)
        self.retriever = retriever or get_retriever()
        self.trace_dir = trace_dir
        self.tw: TraceWriter | None = None   # set per run()

    # ---------------------------------------------------------------- helpers
    def _step(self, state, node, summary, payload=None, error=None):
        step = state.get("step_count", 0) + 1
        rec = self.tw.write(
            step, node, summary, payload=payload, error=error,
            usage={"prompt_tokens": state["usage"]["prompt_tokens"],
                   "completion_tokens": state["usage"]["completion_tokens"]},
        )
        return step, rec

    def _trace(self, state, rec):
        return state.get("trace", []) + [rec]

    def _sync_usage(self, state) -> dict:
        return {"usage": {
            "prompt_tokens": getattr(self.llm, "prompt_tokens", 0),
            "completion_tokens": getattr(self.llm, "completion_tokens", 0),
            "llm_calls": getattr(self.llm, "llm_calls", 0),
        }}

    # ---------------------------------------------------------------- nodes
    def retrieve_schema(self, state: AgentState) -> dict:
        tables = self.retriever.retrieve(state["question"])
        ctx = self.catalog.render_schema_context(tables)
        step, rec = self._step(state, "retrieve_schema", f"selected={tables}")
        return {"step_count": step, "selected_tables": tables,
                "schema_context": ctx, "trace": self._trace(state, rec)}

    def generate_sql(self, state: AgentState) -> dict:
        attempts = state.get("sql_attempts", 0) + 1
        user = gen_sql_user(
            state["schema_context"], state["question"],
            error=state.get("error"), reflect_hint=state.get("reflect_hint"),
            prev_sql=state.get("sql"),
        )
        resp = self.llm.chat_json(GEN_SQL_SYSTEM, user)
        sql = "" if resp.get("action") == "refuse" else (resp.get("sql") or "").strip()
        step, rec = self._step(state, "generate_sql", f"attempt={attempts}",
                               payload={"sql": sql[:160]})
        out = {"step_count": step, "sql_attempts": attempts, "sql": sql,
               "sql_history": state.get("sql_history", []) + [sql],
               "trace": self._trace(state, rec)}
        out.update(self._sync_usage(state))
        if not sql:
            out["failure_reason"] = "NO_SQL"
        return out

    def validate_sql(self, state: AgentState) -> dict:
        v = self.guard.validate(state["sql"])
        summary = "pass" if v.passed else (v.reason or "recover")
        step, rec = self._step(state, "validate_sql", summary, error=v.observation)
        out = {"step_count": step, "passed": v.passed, "blocked": v.blocked,
               "normalized_sql": v.normalized_sql, "trace": self._trace(state, rec)}
        if v.observation:
            out["error"] = v.observation
        if v.blocked:
            out["failure_reason"] = "SQL_BLOCKED"
        return out

    def check_budget(self, state: AgentState) -> dict:
        ok = _budget_ok(state, self.s)
        new_retry = state.get("retry_count", 0) + (1 if ok else 0)
        step, rec = self._step(state, "check_budget", f"retry={new_retry}")
        out = {"step_count": step, "retry_count": new_retry, "budget_ok": ok,
               "trace": self._trace(state, rec)}
        if not ok:
            out["failure_reason"] = "MAX_RETRY_EXCEEDED"
        return out

    def reflect(self, state: AgentState) -> dict:
        err = state.get("error") or {}
        user = reflect_user(state["sql"], err.get("kind", "OTHER"), err.get("message", ""))
        try:
            resp = self.llm.chat_json(REFLECT_SYSTEM, user)
        except Exception:
            resp = {"hint": f"修复 {err.get('kind')}"}
        hint = resp.get("hint") or resp.get("diagnosis") or ""
        relink = _needs_relink(err.get("kind", "OTHER"))
        step, rec = self._step(state, "reflect", hint[:100],
                               payload={"kind": err.get("kind"), "relink": relink})
        out = {"step_count": step, "reflect_hint": hint, "need_relink": relink,
               "trace": self._trace(state, rec)}
        out.update(self._sync_usage(state))
        return out

    def execute_sql(self, state: AgentState) -> dict:
        result = self.executor.execute(state["normalized_sql"] or state["sql"])
        step, rec = self._step(
            state, "execute_sql",
            f"ok={result['ok']} rows={result['row_count']} trunc={result['truncated']}",
            error=result["error"],
        )
        out = {"step_count": step, "exec_result": result, "trace": self._trace(state, rec)}
        if not result["ok"]:
            out["error"] = result["error"]
        return out

    def summarize(self, state: AgentState) -> dict:
        empty = (state.get("exec_result") or {}).get("row_count", 0) == 0
        user = summarize_user(state["question"], state["sql"],
                              state.get("exec_result"), empty=empty)
        try:
            resp = self.llm.chat_json(SUMMARIZE_SYSTEM, user)
            answer = resp.get("answer") or "查询完成。"
        except Exception:
            answer = "未查到符合条件的数据。" if empty else "查询完成。"
        summary = "EMPTY_RESULT" if empty else answer[:100]
        step, rec = self._step(state, "summarize", summary)
        out = {"step_count": step, "answer": answer, "final_status": "success",
               "trace": self._trace(state, rec)}
        out.update(self._sync_usage(state))
        return out

    def refuse(self, state: AgentState) -> dict:
        reason = state.get("failure_reason") or "UNKNOWN"
        refused = reason in ("SQL_BLOCKED", "NO_SQL", "NO_RELINK", "UNANSWERABLE")
        status = "refused" if refused else "failed"
        if refused:
            answer = f"无法回答：{reason}。已检索表：{state.get('selected_tables')}"
        else:
            answer = f"查询失败：{reason}"
        step, rec = self._step(state, "refuse", f"{status}:{reason}")
        return {"step_count": step, "final_status": status,
                "answer": answer, "trace": self._trace(state, rec)}

    # ---------------------------------------------------------------- routers
    @staticmethod
    def route_gen(state: AgentState) -> str:
        return "empty" if not state.get("sql") else "ok"

    @staticmethod
    def route_guard(state: AgentState) -> str:
        if state.get("blocked"):
            return "block"
        if not state.get("passed"):
            return "recover"
        return "pass"

    @staticmethod
    def route_exec(state: AgentState) -> str:
        res = state.get("exec_result") or {}
        if res.get("ok"):
            return "success"
        err = state.get("error") or {}
        if err.get("kind") in TERMINAL_KINDS:
            return "give_up"
        return "retry"

    @staticmethod
    def route_budget(state: AgentState) -> str:
        return "reflect" if state.get("budget_ok") else "refuse"

    @staticmethod
    def route_reflect(state: AgentState) -> str:
        return "relink" if state.get("need_relink") else "regenerate"


def build_graph(nodes: GraphNodes):
    b = StateGraph(AgentState)
    for name in ("retrieve_schema", "generate_sql", "validate_sql", "check_budget",
                 "reflect", "execute_sql", "summarize", "refuse"):
        b.add_node(name, getattr(nodes, name))

    b.add_edge(START, "retrieve_schema")
    b.add_edge("retrieve_schema", "generate_sql")
    b.add_conditional_edges("generate_sql", nodes.route_gen,
                            {"ok": "validate_sql", "empty": "refuse"})
    b.add_conditional_edges("validate_sql", nodes.route_guard,
                            {"pass": "execute_sql", "recover": "check_budget",
                             "block": "refuse"})
    b.add_conditional_edges("execute_sql", nodes.route_exec,
                            {"success": "summarize", "retry": "check_budget",
                             "give_up": "refuse"})
    b.add_conditional_edges("check_budget", nodes.route_budget,
                            {"reflect": "reflect", "refuse": "refuse"})
    b.add_conditional_edges("reflect", nodes.route_reflect,
                            {"relink": "retrieve_schema", "regenerate": "generate_sql"})
    b.add_edge("summarize", END)
    b.add_edge("refuse", END)
    return b.compile()


class QueryGraph:
    """Entry point that mirrors QueryLoop.run(question) from loop_fallback."""

    def __init__(self, llm, **kwargs):
        self.nodes = GraphNodes(llm, **kwargs)
        self.graph = build_graph(self.nodes)

    def run(self, question: str) -> dict[str, Any]:
        state = _init_state(question)
        self.nodes.tw = TraceWriter(state["run_id"], trace_dir=self.nodes.trace_dir)
        out = self.graph.invoke(state)
        return {
            "run_id": out["run_id"],
            "final_status": out["final_status"],
            "answer": out["answer"],
            "sql": out["sql"],
            "exec_result": out.get("exec_result"),
            "failure_reason": out.get("failure_reason"),
            "step_count": out["step_count"],
            "sql_attempts": out["sql_attempts"],
            "retry_count": out["retry_count"],
            "llm_calls": out["usage"]["llm_calls"],
            "usage": out["usage"],
            "trace": out["trace"],
        }


# ------------------------------------------------------------------ demo
if __name__ == "__main__":
    from sqlpilot.llm.client import FakeLLM

    fake = FakeLLM([
        {"action": "sql",
         "sql": ("SELECT s.store_name, SUM(o.total_amount) AS sales "
                 "FROM orders o JOIN stores s ON o.store_id = s.store_id "
                 "WHERE LOWER(TRIM(o.status)) = 'paid' "
                 "GROUP BY s.store_name ORDER BY sales DESC LIMIT 3"),
         "thinking": "初版"},
        {"diagnosis": "orders 表没有 total_amount 列", "hint": "改用 orders.amount"},
        {"action": "sql",
         "sql": ("SELECT s.store_name, SUM(o.amount) AS sales "
                 "FROM orders o JOIN stores s ON o.store_id = s.store_id "
                 "WHERE LOWER(TRIM(o.status)) = 'paid' "
                 "GROUP BY s.store_name ORDER BY sales DESC LIMIT 3"),
         "thinking": "已修正"},
        {"answer": "2024 年销售额前三的门店：上海南京路店、北京朝阳店、深圳南山店。"},
    ])

    g = QueryGraph(llm=fake)
    r = g.run("2024年各门店的已支付销售额前三名是哪些？")

    print(f"run_id:      {r['run_id']}")
    print(f"status:      {r['final_status']}")
    print(f"step_count:  {r['step_count']}")
    print(f"sql_attempts:{r['sql_attempts']}")
    print(f"retry_count: {r['retry_count']}")
    print(f"llm_calls:   {r['llm_calls']}")
    print(f"answer:      {r['answer']}")
    print("\n=== trace ===")
    for rec in r["trace"]:
        kind = rec["error"]["kind"] if rec.get("error") else ""
        print(f"  [{rec['step']:2d}] {rec['node']:18s} {rec['summary'][:55]:55s} {kind}")