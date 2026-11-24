# SQLPilot 面试白板题（手写用）

> 用途：面试时在白板/纸上手写，展示对 Agent 纠错循环和 AST 安全网关的理解。
> 对应代码：`sqlpilot/agent/loop_fallback.py`（纠错循环）、`sqlpilot/guard/sql_guard.py`（AST 网关）。

---

## 一、带预算的 Retry Loop（伪代码，15 行内）

```
state = {sql: "", retry: 0, err: None}
tables = retrieve(question)            # schema linking
sql = generate(tables, question)       # LLM 生成 SQL
while True:
    v = guard.validate(sql)            # AST 安全检查 + 列/表校验
    if v.blocked: return refuse("SQL_BLOCKED")
    if not v.passed:                   # 列不存在/语法错等可恢复错误
        err = v.observation
    else:
        res = execute(v.normalized_sql)
        if res.ok: return summarize(res)          # 成功
        err = res.error                            # 执行错误
    if err.kind in TERMINAL: return refuse(err.kind)   # 超时/截断等不重试
    if not budget_ok(state): return refuse("MAX_RETRY_EXCEEDED")  # 预算耗尽
    state.retry += 1
    hint, relink = reflect(err)        # LLM 反思错误原因
    if relink: tables = retrieve(question)         # 列/表错→重新检索
    sql = generate(tables, question, err=err, hint=hint)  # 带错误+提示重生成
```

**要点（面试可说）**：
- **两种失败都进纠错**：`validate` 失败（列/表/语法，还没查库）+ `execute` 失败（查库报错）——**校验失败和执行失败是两回事**。
- **预算控制**：`budget_ok` 检查 retry_count / sql_attempts / step / token / 时间，任一超限就放弃。
- **relink vs regenerate**：列/表名错→重新检索（relink）；其他错→直接重生成（regenerate）。

---

## 二、AST 安全网关的 5 个核心检查点

> 用 `sqlglot` 把 SQL 解析成 AST（抽象语法树），结构化检查——**不是字符串匹配（易被绕过）**。

| # | 检查点 | 拦什么 | 为什么 |
|---|---|---|---|
| 1 | **只允许 SELECT** | 非 SELECT（DDL: CREATE/DROP/ALTER；DML: INSERT/UPDATE/DELETE） | Text2SQL 只该查询，不该改表/改数据（会毁库） |
| 2 | **表白名单** | 非白名单表、系统库（mysql./information_schema）、跨库 | 防越权访问 |
| 3 | **危险函数** | SLEEP / BENCHMARK / LOAD_FILE 等 | 防拖库、防拒绝服务 |
| 4 | **注释/多语句** | `--` `/* */` `#` 注释、多条语句、`@@` 系统变量、UNION | 防注释绕过、防注入、防多语句攻击 |
| 5 | **LIMIT 收紧** | 大 LIMIT 收紧到 max_rows(200)、无 LIMIT 自动补 | 防全表大结果集拖垮服务（**注意：只限返回行数，不保证少扫描**） |

**要点（面试可说）**：
- **AST 优于正则**：`dr/**/op`、大小写、注释绕过，正则难防，AST 能精确识别"这条 SQL 到底是不是 SELECT、碰了哪些表"。
- **双保险**：网关（软件层）+ 只读数据库账号（数据库层只给 SELECT 权限）——就算网关漏了，DB 也拒绝。
- **LIMIT 只是"限制返回规模"，不是"防全表扫描"**（扫描量看索引/执行计划）——这是诚实的边界表述。

---

## 三、可能的追问 & 答法

- **Q：validate 失败 vs execute 失败区别？** A：validate 用 AST 静态校验（列/表/语法），**没查库就能拦**；execute 是查库后 DB 报错。两者都进同一个纠错循环，但错误来源不同。
- **Q：纠错能修什么、不能修什么？** A：能修"手滑型"（列名拼错、漏 join）；修不了"模型知识错误"（如用 MySQL 不存在的 PERCENTILE_CONT 算中位数，重试也错）和"静默语义错"（SQL 跑通但业务不对，DB 不报错、抓不到）。
- **Q：怎么防注入？** A：AST 校验（禁非 SELECT/多语句/危险函数/注释绕过）+ 只读账号 + LIMIT 收紧。
