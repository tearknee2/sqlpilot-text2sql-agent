"""Hand-written agent loop (doc §2.5, appendix A). Fallback for R1 (LangGraph stuck).

DoD (doc §5 D2): a `o.total_amount` request must produce this trace:
  retrieve → generate → validate(UNKNOWN_COLUMN) → check_budget → reflect
  → retrieve(relink) → generate → validate(pass) → execute → summarize
Total: 10 steps, sql_attempts=2, retry_count=1, llm_calls=4.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from sqlpilot.agent.errors import TERMINAL_KINDS, needs_relink as _needs_relink
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


def _init_state(question: str) -> AgentState:
    return {
        "run_id": uuid.uuid4().hex[:12],
        "question": question,
        "schema_context": "",
        "selected_tables": [],
        "sql": "",
        "sql_history": [],
        "sql_attempts": 0,
        "exec_result": None,
        "error": None,
        "reflect_hint": None,
        "need_relink": False,
        "retry_count": 0,
        "step_count": 0,
        "start_ts": time.monotonic(),
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "llm_calls": 0},
        "trace": [],
        "final_status": "failed",
        "answer": None,
        "failure_reason": None,
    }


def _budget_ok(state: AgentState, s) -> bool:
    u = state["usage"]
    return (
        state["retry_count"] < s.agent_max_retries
        and state["sql_attempts"] < s.agent_max_sql_attempts
        and state["step_count"] < s.agent_max_steps
        and u["prompt_tokens"] + u["completion_tokens"] < s.agent_token_budget
        and u["llm_calls"] < s.max_llm_calls
        and (time.monotonic() - state["start_ts"]) < s.agent_wallclock_timeout_s
    )


class QueryLoop:
    def __init__(self, llm, executor=None, guard=None, retriever=None,
                 trace_dir=None, settings=None):
        self.s = settings or get_settings()
        self.llm = llm
        self.executor = executor or MySqlExecutor(self.s)
        self.catalog = get_catalog()
        self.guard = guard or SqlGuard(self.catalog, max_rows=self.s.sql_max_rows)
        self.retriever = retriever or get_retriever()
        self.trace_dir = trace_dir

    def _step(self, state, tw, node, summary, payload=None, error=None):
        state["step_count"] += 1
        rec = tw.write(state["step_count"], node, summary,
                       payload=payload, error=error,
                       usage={"prompt_tokens": state["usage"]["prompt_tokens"],
                              "completion_tokens": state["usage"]["completion_tokens"]})
        state["trace"].append(rec)

    def _sync_usage(self, state):
        state["usage"]["prompt_tokens"] = getattr(self.llm, "prompt_tokens", 0)
        state["usage"]["completion_tokens"] = getattr(self.llm, "completion_tokens", 0)
        state["usage"]["llm_calls"] = getattr(self.llm, "llm_calls", 0)

    def _generate(self, state) -> str:
        user = gen_sql_user(
            state["schema_context"], state["question"],
            error=state["error"], reflect_hint=state["reflect_hint"],
            prev_sql=state["sql"],
        )
        resp = self.llm.chat_json(GEN_SQL_SYSTEM, user)
        self._sync_usage(state)
        if resp.get("action") == "refuse":
            return ""
        return (resp.get("sql") or "").strip()

    def _reflect(self, state, obs) -> tuple[str, bool]:
        user = reflect_user(state["sql"], obs["kind"], obs.get("message", ""))
        try:
            resp = self.llm.chat_json(REFLECT_SYSTEM, user)
        except Exception:
            resp = {"hint": f"修复 {obs['kind']}"}
        self._sync_usage(state)
        hint = resp.get("hint") or resp.get("diagnosis") or ""
        return hint, _needs_relink(obs["kind"])

    def _summarize(self, state, empty=False) -> str:
        user = summarize_user(state["question"], state["sql"], state["exec_result"], empty=empty)
        try:
            resp = self.llm.chat_json(SUMMARIZE_SYSTEM, user)
        except Exception:
            return "未查到符合条件的数据。" if empty else "查询完成。"
        self._sync_usage(state)
        return resp.get("answer") or "查询完成。"

    def run(self, question: str) -> dict[str, Any]:
        state = _init_state(question)
        tw = TraceWriter(state["run_id"], trace_dir=self.trace_dir)

        # Step 1: retrieve
        tables = self.retriever.retrieve(question)
        state["selected_tables"] = tables
        state["schema_context"] = self.catalog.render_schema_context(tables)
        self._step(state, tw, "retrieve_schema", f"selected={tables}")

        while True:
            # Guard: attempts
            if state["sql_attempts"] >= self.s.agent_max_sql_attempts:
                return self._finalize(state, tw, "failed", "MAX_SQL_ATTEMPTS")

            # generate
            state["sql_attempts"] += 1
            sql = self._generate(state)
            state["sql"] = sql
            state["sql_history"].append(sql)
            self._step(state, tw, "generate_sql",
                       f"attempt={state['sql_attempts']}",
                       payload={"sql": sql[:160]})
            if not sql:
                return self._finalize(state, tw, "refused", "NO_SQL")

            # validate
            v = self.guard.validate(sql)
            self._step(state, tw, "validate_sql",
                       "pass" if v.passed else (v.reason or "recover"),
                       error=v.observation)
            if v.blocked:
                return self._finalize(state, tw, "refused", "SQL_BLOCKED")

            if not v.passed:
                if not _budget_ok(state, self.s):
                    return self._finalize(state, tw, "failed", "MAX_RETRY_EXCEEDED")
                state["retry_count"] += 1
                self._step(state, tw, "check_budget", f"retry={state['retry_count']}")
                state["error"] = v.observation
                hint, relink = self._reflect(state, v.observation)
                state["reflect_hint"] = hint
                state["need_relink"] = relink
                self._step(state, tw, "reflect", hint[:100],
                           payload={"kind": v.observation["kind"], "relink": relink})
                if relink:
                    tables = self.retriever.retrieve(question)
                    state["selected_tables"] = tables
                    state["schema_context"] = self.catalog.render_schema_context(tables)
                    self._step(state, tw, "retrieve_schema", f"relink={tables}")
                continue

            # execute
            result = self.executor.execute(v.normalized_sql)
            self._step(state, tw, "execute_sql",
                       f"ok={result['ok']} rows={result['row_count']} trunc={result['truncated']}",
                       error=result["error"])
            if result["ok"]:
                state["exec_result"] = result
                state["final_status"] = "success"
                empty = result["row_count"] == 0
                state["answer"] = self._summarize(state, empty=empty)
                self._step(state, tw, "summarize",
                           ("EMPTY_RESULT" if empty else state["answer"][:100]))
                return self._snapshot(state)

            # mysql error
            err = result["error"]
            if err["kind"] in TERMINAL_KINDS:
                return self._finalize(state, tw, "failed", err["kind"])
            if not _budget_ok(state, self.s):
                return self._finalize(state, tw, "failed", "MAX_RETRY_EXCEEDED")
            state["retry_count"] += 1
            self._step(state, tw, "check_budget", f"retry={state['retry_count']}")
            state["error"] = err
            hint, relink = self._reflect(state, err)
            state["reflect_hint"] = hint
            state["need_relink"] = relink
            self._step(state, tw, "reflect", hint[:100],
                       payload={"kind": err["kind"], "relink": relink})
            if relink:
                tables = self.retriever.retrieve(question)
                state["selected_tables"] = tables
                state["schema_context"] = self.catalog.render_schema_context(tables)
                self._step(state, tw, "retrieve_schema", f"relink={tables}")

    def _finalize(self, state, tw, status, reason):
        state["final_status"] = status
        state["failure_reason"] = reason
        if status == "refused":
            state["answer"] = f"无法回答：{reason}。已检索表：{state['selected_tables']}"
        else:
            state["answer"] = f"查询失败：{reason}"
        self._step(state, tw, "finalize", f"{status}:{reason}")
        return self._snapshot(state)

    @staticmethod
    def _snapshot(state):
        return {
            "run_id": state["run_id"],
            "final_status": state["final_status"],
            "answer": state["answer"],
            "sql": state["sql"],
            "exec_result": state["exec_result"],
            "failure_reason": state["failure_reason"],
            "step_count": state["step_count"],
            "sql_attempts": state["sql_attempts"],
            "retry_count": state["retry_count"],
            "llm_calls": state["usage"]["llm_calls"],
            "usage": state["usage"],
            "trace": state["trace"],
        }


# ------------------------------------------------------------------ demo
if __name__ == "__main__":
    from sqlpilot.llm.client import FakeLLM

    fake = FakeLLM([
        # generate #1: hallucinated column total_amount
        {"action": "sql",
         "sql": ("SELECT s.store_name, SUM(o.total_amount) AS sales "
                 "FROM orders o JOIN stores s ON o.store_id = s.store_id "
                 "WHERE LOWER(TRIM(o.status)) = 'paid' "
                 "GROUP BY s.store_name ORDER BY sales DESC LIMIT 3"),
         "thinking": "初版"},
        # reflect
        {"diagnosis": "orders 表没有 total_amount 列", "hint": "改用 orders.amount"},
        # generate #2: corrected
        {"action": "sql",
         "sql": ("SELECT s.store_name, SUM(o.amount) AS sales "
                 "FROM orders o JOIN stores s ON o.store_id = s.store_id "
                 "WHERE LOWER(TRIM(o.status)) = 'paid' "
                 "GROUP BY s.store_name ORDER BY sales DESC LIMIT 3"),
         "thinking": "已修正"},
        # summarize
        {"answer": "2024 年销售额前三的门店：上海南京路店、北京朝阳店、深圳南山店。"},
    ])

    loop = QueryLoop(llm=fake)
    r = loop.run("2024年各门店的已支付销售额前三名是哪些？")

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