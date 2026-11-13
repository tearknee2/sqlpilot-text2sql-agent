"""LLM prompts (doc appendix C). PROMPT_VERSION is recorded in eval reports."""
from __future__ import annotations

PROMPT_VERSION = "v2.0"

GEN_SQL_SYSTEM = """你是 MySQL 8 数据分析师。严格规则：
1. 只能使用 <schema> 中出现过的表名与列名，禁止编造。
2. 只输出一条 SELECT 语句，禁止 DDL/DML、禁止多语句、禁止注释。
3. 日期用 BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'；枚举值必须取自 schema 的 enum。
4. 口径一律以 <schema> 中每张表的 pitfalls 为准，不得自行假设。
5. 若问题所需信息在 schema 中不存在，输出 {"action":"refuse","reason":"..."}。
6. 只输出 json，不要 markdown 代码块，不要解释。
输出格式：{"action":"sql"|"refuse","sql":"...","reason":"...","thinking":"不超过一句"}"""


REFLECT_SYSTEM = """你是 SQL 调试助手。根据结构化观测（来自网关或 MySQL，shape 相同）与上一条 SQL，
指出具体错误位置，给出一条最小修改建议。只输出 json：{"diagnosis":"...","hint":"..."}
不输出路由策略——修复动作由 kind 的确定性分派表决定。
禁止建议悄悄放宽 WHERE 条件。"""


SUMMARIZE_SYSTEM = """你是业务分析师。只能使用 <result> 中给定的数据作答，禁止引入结果集之外的任何数字或事实。
中文，2-4 句，先给结论再给关键数字。若结果为空，明确说明「未查到符合条件的数据」。
只输出 json：{"answer":"..."}"""


def gen_sql_user(schema_context: str, question: str,
                 error: dict | None = None,
                 reflect_hint: str | None = None,
                 prev_sql: str | None = None) -> str:
    u = f"<schema>\n{schema_context}\n</schema>\n<question>{question}</question>"
    if reflect_hint:
        k = (error or {}).get("kind", "?")
        m = (error or {}).get("message", "")[:300]
        u += f"\n<previous_error>{k}: {m}</previous_error>"
        u += f"\n<fix_hint>{reflect_hint}</fix_hint>"
        u += f"\n<previous_sql>{prev_sql}</previous_sql>"
        u += "\n请做最小修改，不要重写整个查询。"
    return u


def reflect_user(prev_sql: str, kind: str, message: str) -> str:
    return (
        f"<previous_sql>{prev_sql}</previous_sql>\n"
        f"<error_kind>{kind}</error_kind>\n"
        f"<error_message>{message[:300]}</error_message>"
    )


def summarize_user(question: str, sql: str, result: dict | None, empty: bool = False) -> str:
    if empty or not result:
        table_text = "（空结果集）"
    else:
        cols = result.get("columns", [])
        rows = result.get("rows", [])
        head = " | ".join(map(str, cols))
        body = "\n".join(" | ".join(map(str, r)) for r in rows[:20])
        table_text = f"{head}\n{body}"
        if result.get("truncated"):
            table_text += "\n（结果已截断，仅前 200 行）"
    return f"<question>{question}</question>\n<sql>{sql}</sql>\n<result>\n{table_text}\n</result>"