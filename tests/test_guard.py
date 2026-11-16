"""测试 SqlGuard：§2.11 必补清单第一条。"""
from sqlpilot.guard.sql_guard import SqlGuard
from sqlpilot.schema.catalog import get_catalog

# 模块级建一个 guard 实例：文件加载时执行一次，所有测试共用（读 yaml 一次，省时间）
guard = SqlGuard(get_catalog())


def test_alias_column_hallucination():
    """防 §1.1 第 2 条：o.total_amount 必须被网关拦下，且不能被当成安全违规。"""
    # 1) 这条 SQL 里 o 是别名，total_amount 是幻觉列（实际是 amount）
    sql = "select o.total_amount from orders o"

    # 2) 让网关检查
    v = guard.validate(sql)

    # 3) 断言：拦下了，但没拒答
    assert v.passed is False, "列不存在，不该通过"
    assert v.blocked is False, "可恢复错误，不该被当成安全违规"
    assert v.observation is not None, "必须产出结构化观测"
    assert v.observation["kind"] == "UNKNOWN_COLUMN", "kind 必须是 UNKNOWN_COLUMN"
    assert v.observation['source'] == "guard", "必须由网关产生，不是 MySQL"

def test_system_schema():
    """防 §2.11 的 t.db vs t.name 坑：系统库必须 blocked，不能被当成幻觉表名。"""
    # 1) 这条 SQL 访问 MySQL 的系统库（用户无权）
    sql = "select * from mysql.user"

    # 2) 网关检查
    v = guard.validate(sql)

    # 3) 断言：拒答，且 reason 明确指出是系统库/跨库
    assert v.passed is False, "系统库不该通过"
    assert v.blocked is True, "这是安全违规，不是可恢复错误"
    assert v.observation is not None
    assert v.observation["kind"] == "BLOCKED", "安全违规的 kind 必须是 BLOCKED"
    assert v.reason == "SYSTEM_SCHEMA_OR_CROSS_DB", "reason 应该指出是系统库/跨库"

def test_unknown_table_hallucination():
    """防 §1.1 第 4 条：幻觉表名是可恢复，不是安全违规。"""
    # 1) 拼错的表名（裸表名，没有 db. 前缀）
    sql = "select * from ordres"

    # 2) 网关检查
    v = guard.validate(sql)

    # 3) 断言：拦下，但可恢复
    assert v.passed is False, "表不存在，不该通过"
    assert v.blocked is False, "拼错表名是可恢复，不是安全违规"
    assert v.observation is not None
    assert v.observation["kind"] == "UNKNOWN_TABLE", "kind 必须是 UNKNOWN_TABLE"
    assert v.observation["source"] == "guard", "必须由网关产生"

def test_cte():
    """防 §2.11 的 CTE 误杀坑：合法的 WITH 查询必须放行，且规范化 SQL 无注释。"""
    # 1) CTE 名 x 不是真表，但 x 内部用的是真表 orders
    sql = "with temp as (select * from orders) select * from temp"

    # 2) 网关检查
    v = guard.validate(sql)

    # 3) 断言：放行，且规范化 SQL 以 WITH 起头、不含任何注释
    assert v.passed is True, "合法 CTE 不该被拦"
    assert v.blocked is False, "合法 SQL 不是安全违规"
    assert v.normalized_sql is not None, "通过后必须有规范化 SQL"
    assert v.normalized_sql.strip().upper().startswith("WITH"), "规范化 SQL 应以 WITH 起头"
    assert "/*" not in v.normalized_sql, "规范化 SQL 不能含 /* 注释"
    assert "--" not in v.normalized_sql, "规范化 SQL 不能含 -- 注释"
    assert "#" not in v.normalized_sql, "规范化 SQL 不能含 # 注释"

def test_comment_bypass():
    """防 §2.11 第 0 步：SQL 里的注释必须被拦（注释是注入的经典绕过手段）。"""
    # 1) 带 -- 注释的 SQL
    sql = "select 1 --这是注释"

    # 2) 网关检查
    v = guard.validate(sql)

    # 3) 断言：拦下，reason 是 COMMENT_BYPASS
    assert v.passed is False, "带注释不该通过"
    assert v.blocked is True, "注释是安全违规，必须 blocked"
    assert v.observation is not None
    assert v.observation["kind"] == "BLOCKED"
    assert v.reason == "COMMENT_BYPASS", "reason 应该是 COMMENT_BYPASS"


def test_comment_inside_string_ok():
    """防误杀：字符串里的 -- 不是注释，不该被拦。"""
    # 1) -- 出现在字符串字面量里
    sql = "select * from orders where amount = '--299'"

    # 2) 网关检查
    v = guard.validate(sql)

    # 3) 断言：放行（字符串里的 -- 是数据，不是注释）
    assert v.passed is True, "字符串里的 -- 不该被当成注释"
    assert v.blocked is False

def test_blocked_contract():
    """§2.11 契约：任何 blocked=True 的分支，observation.kind 必须是 BLOCKED。

    防的是"代码写错而不自知"——blocked 标志和 observation 内容不同步。
    """
    blocked_sqls = [
        # 系统库 / 跨库
        "SELECT * FROM mysql.user",
        "SELECT * FROM otherdb.orders",
        # 注释绕过
        "SELECT 1 -- x",
        # 多语句
        "SELECT 1; DROP TABLE orders",
        # UNION
        "SELECT 1 UNION SELECT 2",
        # 危险函数
        "SELECT SLEEP(5)",
        "SELECT BENCHMARK(1000000, MD5('x'))",
        # DDL/DML
        "DROP TABLE orders",
        "INSERT INTO orders (order_id) VALUES (1)",
        "UPDATE orders SET status='paid'",
        # 系统变量
        "SELECT @@version",
    ]
    for sql in blocked_sqls:
        v = guard.validate(sql)
        assert v.blocked is True, f"应 blocked，但没拦: {sql}"
        assert v.observation is not None, f"blocked 但无 observation: {sql}"
        assert v.observation["kind"] == "BLOCKED", f"kind 必须是 BLOCKED: {sql}"

def test_unqualified_column():
    """§2.11 有意妥协：裸列（无表别名）跳过检查，不误伤派生列/表达式列。

    这条测试证明"跳过"是有意为之，不是 bug：
      - o.total_amount（有别名）会被拦
      - total_amount（裸列）会放行，交给 MySQL 兜底 1054
    """
    sql = "select total_amount from orders"

    v = guard.validate(sql)

    # 断言：裸列放行（网关不查）
    assert v.passed is True, "裸列有意跳过，应放行"
    assert v.blocked is False, "裸列不是安全违规"
    assert v.observation is None, "放行时无观测（observation 只在 failed 时产出）"


