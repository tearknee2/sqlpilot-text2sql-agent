# web/streamlit_app.py
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# ============ 配置：在线 API 还是离线 demo ============
DEMO_OFFLINE = os.getenv("DEMO_OFFLINE_MODE", "false").lower() in ("1", "true", "yes")
API_URL = os.getenv("SQLPILOT_API_URL", "http://127.0.0.1:8000")
DEMO_TRACE_PATH = Path(__file__).resolve().parent / "demo_trace.json"

st.set_page_config(page_title="SQLPilot", layout="wide")
st.title("SQLPilot · 自纠错 Text2SQL Agent")

if DEMO_OFFLINE:
    st.info("🔌 离线演示模式（DEMO_OFFLINE_MODE=true）：展示预录结果，不调用后端。")

def call_api(question: str) -> dict:
    """在线：真实调后端。"""
    resp = httpx.post(
        f"{API_URL}/api/v1/query",
        json={"question": question},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()

def load_demo_trace() -> dict | None:
    """离线：读预录 JSON。"""
    if not DEMO_TRACE_PATH.exists():
        return None
    return json.loads(DEMO_TRACE_PATH.read_text(encoding="utf-8"))

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.header("提问")
    question = st.text_area(
        "请输入你的问题",
        placeholder="例如：2024年各门店的已支付销售额前三名是哪些？",
        height=120,
    )
    run_btn = st.button("查询", type="primary", use_container_width=True)

if run_btn:
    q = (question or "").strip()
    if not q:
        st.warning("请先输入一个问题")
    else:
        with st.spinner("Agent 正在思考、生成 SQL、执行…"):
            try:
                if DEMO_OFFLINE:
                    raw = load_demo_trace()
                    if raw is None:
                        st.error(f"离线模式缺少演示文件：{DEMO_TRACE_PATH}")
                else:
                    raw = call_api(q)
                if raw:
                    st.session_state.history.insert(0, raw)
            except httpx.ConnectError:
                st.error(f"连不上后端 API（{API_URL}）。请启动后端，或设 DEMO_OFFLINE_MODE=true 用离线演示。")
            except httpx.HTTPStatusError as e:
                st.error(f"后端返回错误 {e.response.status_code}：{e.response.text}")
            except Exception as e:
                st.error(f"查询出错：{e}")

for raw in st.session_state.history:
    st.divider()
    status = raw.get("final_status")
    if status == "success":
        st.success(raw.get("answer") or "（无答案）")
    else:
        st.error(f"[{status}] {raw.get('answer') or raw.get('failure_reason') or '查询失败'}")

    sql = raw.get("sql")
    if sql:
        st.markdown("**生成的 SQL**")
        st.code(sql, language="sql")

    exec_res = raw.get("result")
    if exec_res and exec_res.get("rows") is not None:
        st.markdown(f"**查询结果（{exec_res.get('row_count', 0)} 行）**")
        st.dataframe(pd.DataFrame(exec_res["rows"], columns=exec_res["columns"]))

    with st.expander("查看全链路 Trace"):
        for t in raw.get("trace", []):
            st.markdown(f"**[Step {t['step']}] {t['node']} : {t['summary']}**")
            if t.get("error"):
                st.error(f"error: {t['error']}")