import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlpilot.agent.graph import GraphNodes, build_graph
from sqlpilot.llm.client import LLMClient

nodes = GraphNodes(llm=LLMClient())
graph = build_graph(nodes)

# 输出到项目根的 web/ 目录（绝对路径，免受工作目录影响）
out = ROOT / "web" / "graph.png"
out.parent.mkdir(parents=True, exist_ok=True)

try:
    png: bytes = graph.get_graph().draw_mermaid_png()
    out.write_bytes(png)
    print("OK 已生成:", out, len(png), "bytes")
except Exception as e:
    # 渲染失败就退化为 mermaid 文本
    print("draw_mermaid_png 失败:", e, "\n改用 mermaid 文本...")
    mmd = graph.get_graph().draw_mermaid()
    mmd_path = ROOT / "web" / "graph.mmd"
    mmd_path.write_text(mmd, encoding="utf-8")
    print("OK 已生成 mermaid 文本:", mmd_path)
    print(mmd)