"""LLM 扩写子查询层 3 道题，逐条验证 GT SQL。"""
import json
from sqlpilot.agent.prompts import EVAL_EXPAND_SYSTEM
from sqlpilot.llm.client import LLMClient
from sqlpilot.schema.catalog import get_catalog
from sqlpilot.tools.executor import MySqlExecutor

# 1) 拿 schema 摘要（只给业务表，不给 decoy）
cat = get_catalog()
business_tables = ["orders", "stores", "customers", "products", "order_items", "returns"]
schema_text = cat.render_schema_context(business_tables)

# 2) 3 道种子题作为示例（让 LLM 理解口径风格）
seed_examples = [
    {"question": "2024年各门店的已支付销售额，从高到低取前三名",
     "sql": "select s.store_name, sum(o.amount) as sales from orders o join stores s on o.store_id = s.store_id where o.order_date between '2024-01-01' and '2024-12-31' and lower(trim(o.status)) = 'paid' group by s.store_name order by sales desc limit 3"},
    {"question": "每个城市各有多少笔已支付订单？",
     "sql": "select s.city, count(*) as order_count from orders o join stores s on o.store_id = s.store_id where lower(trim(o.status)) = 'paid' group by s.city"},
    {"question": "所有订单明细的商品金额合计是多少？",
     "sql": "select sum(qty * unit_price * (1 - coalesce(discount, 0))) as total_amount from order_items"},
]

# 3) 组装 user prompt
user = f"""<schema>
{schema_text}
</schema>

<种子题示例>
{json.dumps(seed_examples, ensure_ascii=False, indent=2)}
</种子题示例>

<任务>
layer: 子查询/复杂
生成数量: 5道
生成要求: 
(考察点：HAVING 聚合后过滤、IN 子查询、EXISTS、标量子查询、WITH CTE。
禁止用 UNION（网关两周内不支持）。)
</任务>"""

print("=== 调用 DeepSeek 生成候选 ===")
llm = LLMClient()
resp = llm.chat_json(EVAL_EXPAND_SYSTEM, user)

# resp 应该是一个 list，但有些模型会包成 {"items": [...]}，做兼容
candidates = resp if isinstance(resp, list) else resp.get("items") or resp.get("candidates") or []

print(f"生成候选: {len(candidates)} 道\n")

# 4) 逐条验证 GT SQL
ex = MySqlExecutor()
for i, cand in enumerate(candidates, 1):
    sql = cand.get("sql", "")
    q = cand.get("question", "")
    print(f"--- 候选 {i} ---")
    print(f"  题目: {q}")
    print(f"  SQL:  {sql}")
    r = ex.execute(sql)
    if r["error"]:
        print(f"  ❌ 执行失败: {r['error']['kind']}: {r['error']['message'][:80]}")
    else:
        print(f"  ✅ rows={r['row_count']}  columns={r['columns']}")
        print(f"     data={r['rows'][:3]}{'...' if r['row_count'] > 3 else ''}")
    print()