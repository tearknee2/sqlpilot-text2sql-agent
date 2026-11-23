import sys
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlpilot.agent.graph import GraphNodes, build_graph
from sqlpilot.llm.client import LLMClient

nodes = GraphNodes(llm=LLMClient())
graph = build_graph(nodes)

mmd = graph.get_graph().draw_mermaid()
out_mmd = ROOT / "web" / "graph.mmd"
out_mmd.write_text(mmd, encoding="utf-8")
print("mermaid 源码已存:", out_mmd)

# 方案1：langgraph 自带渲染（清晰度不确定）
png_path = ROOT / "web" / "graph.png"
try:
    png = graph.get_graph().draw_mermaid_png()
    png_path.write_bytes(png)
    print("A: draw_mermaid_png OK:", len(png), "bytes")
except Exception as e:
    print("A 失败:", e)

# 方案2：mermaid.ink 在线渲染（更清晰，需要联网）
try:
    import base64, urllib.request
    # mermaid.ink 要求 base64(pako压缩)或直接 base64 源码；先用直接 base64
    b64 = base64.urlsafe_b64encode(mmd.encode("utf-8")).decode("ascii")
    url = "https://mermaid.ink/img/" + b64 + "?type=png"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=30).read()
    png_path.write_bytes(data)
    print("B: mermaid.ink OK:", len(data), "bytes -> 覆盖 graph.png")
except Exception as e:
    print("B 失败(不影响A):", e)
