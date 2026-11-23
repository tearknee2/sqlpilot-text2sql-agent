"""冒烟测试：纠错链路端到端。

冒烟测试（smoke test）= "通上电看会不会冒烟"的最低限度检查：
只验证【核心链路没断】，不深入测每个分支。
本测试用 FakeLLM（假模型、不调真 API）+ FakeExecutor（不连真 DB）固定剧本，
确定性验证：generate(错SQL) → validate失败(UNKNOWN_COLUMN) → check_budget
→ reflect → generate(对SQL) → execute → 成功。

不依赖真实 LLM / MySQL，可在 CI 里几秒跑完。
如果哪天改 graph.py 把纠错链路改断了，这个测试会立刻红灯。
"""
from sqlpilot.agent.graph import QueryGraph
from sqlpilot.llm.client import FakeLLM


class FakeExecutor:
    """假执行器：不连数据库，固定返回成功空结果（不依赖 MySQL）。"""

    def execute(self, sql: str) -> dict:
        return {
            "ok": True,
            "columns": ["store_name", "sales"],
            "rows": [["上海南京路店", 2099359.39]],
            "row_count": 1,
            "truncated": False,
            "error": None,
            "latency_ms": 1,
        }


def test_correction_chain_smoke():
    """纠错链路冒烟：错误 SQL 触发 validate 失败 → reflect → 修正成功。"""
    fake = FakeLLM([
        # 第1次 generate_sql：故意用不存在的列 total_amount（应触发 UNKNOWN_COLUMN）
        {"action": "sql",
         "sql": ("SELECT s.store_name, SUM(o.total_amount) AS sales "
                 "FROM orders o JOIN stores s ON o.store_id = s.store_id "
                 "WHERE LOWER(TRIM(o.status)) = 'paid' "
                 "GROUP BY s.store_name ORDER BY sales DESC LIMIT 3"),
         "thinking": "初版（错列）"},
        # reflect：返回修复提示
        {"diagnosis": "orders 表没有 total_amount 列", "hint": "改用 orders.amount"},
        # 第2次 generate_sql：修正为 amount
        {"action": "sql",
         "sql": ("SELECT s.store_name, SUM(o.amount) AS sales "
                 "FROM orders o JOIN stores s ON o.store_id = s.store_id "
                 "WHERE LOWER(TRIM(o.status)) = 'paid' "
                 "GROUP BY s.store_name ORDER BY sales DESC LIMIT 3"),
         "thinking": "已修正"},
        # summarize：返回最终答案
        {"answer": "2024 年销售额前三的门店：上海南京路店、北京朝阳店、深圳南山店。"},
    ])

    g = QueryGraph(llm=fake, executor=FakeExecutor())
    r = g.run("2024年各门店的已支付销售额前三名是哪些？")

    # 冒烟断言：核心链路行为
    assert r["final_status"] == "success", f"应成功，实际 {r['final_status']}"
    assert r["retry_count"] == 1, f"应恰好重试1次，实际 {r['retry_count']}"
    assert r["sql_attempts"] == 2, f"应生成2次SQL，实际 {r['sql_attempts']}"
    assert "total_amount" not in (r["sql"] or ""), "最终SQL不应含错误列 total_amount"
    assert "amount" in (r["sql"] or ""), "最终SQL应改用 amount"

    # 链路节点断言：trace 里应出现 reflect（证明真的走了反思重试）
    nodes = [t["node"] for t in r["trace"]]
    assert "reflect" in nodes, f"trace 应含 reflect 节点，实际 {nodes}"
    assert nodes.count("generate_sql") == 2, f"应生成2次，实际 {nodes}"
