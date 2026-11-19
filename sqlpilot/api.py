"""FastAPI 端点（doc §10.2）。"""
from fastapi import FastAPI
from sqlpilot.schemas.response import ErrorResponse  # 后面会用
from sqlpilot.tools.executor import MySqlExecutor

app = FastAPI(title="SQLPilot", version="2.0")


@app.get("/api/v1/health")
def health():
    """检查 DB / LLM 连通性。"""
    # TODO: 空 1 —— 怎么检查 DB 是否可用？
    # 提示：用 MySqlExecutor 执行 "SELECT 1"
    db_ok = MySqlExecutor().execute("SELECT 1")["ok"]

    return {"status": "ok" if db_ok else "degraded", "db": db_ok}


@app.get("/api/v1/schema")
def get_schema():
    """返回当前 catalog 摘要。"""
    from sqlpilot.schema.catalog import get_catalog
    cat = get_catalog()
    # TODO: 空 2 —— 返回什么？
    # 提示：返回表的数量 + 表名列表（不用返回完整列）
    return {"tables": len(cat.allowed_tables), "names": sorted(cat.allowed_tables)}


from fastapi import HTTPException
from sqlpilot.schemas.request import QueryRequest
from sqlpilot.schemas.response import QueryResponse, ResultTable, Metrics, TraceStep
from sqlpilot.service import QueryService

# 模块级实例化一次（懒加载，不占启动时间）
_service = None


def get_service():
    global _service
    if _service is None:
        _service = QueryService()
    return _service


@app.post("/api/v1/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """核心入口：接收自然语言问题，返回 SQL 结果与 Trace。"""
    svc = get_service()
    try:
        # 空 1：调用 QueryService 跑一次完整流程
        raw = svc.query(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 组装返回模型
    exec_res = raw.get("exec_result")
    usage = raw.get("usage") or {}

    return QueryResponse(
        run_id=raw["run_id"],
        final_status=raw["final_status"],
        answer=raw.get("answer"),
        sql=raw.get("sql"),
        # 空 2：如果 exec_res 不为空，把 dict 转成 ResultTable
        result=ResultTable(**exec_res) if exec_res else None,
        failure_reason=raw.get("failure_reason"),
        metrics=Metrics(
            retry_count=raw.get("retry_count", 0),
            step_count=raw.get("step_count", 0),
            sql_attempts=raw.get("sql_attempts", 0),
            llm_calls=usage.get("llm_calls", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        ),
        trace=[TraceStep( ** t) for t in raw.get("trace", [])]
        )


@app.get("/api/v1/trace/{run_id}")
def get_trace(run_id: str):
    """读取指定的 run_id 的 trace 记录。"""
    from sqlpilot.observability.trace import replay
    # 空 3：从 trace 目录中回放记录
    records = replay(run_id)
    if not records:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"run_id": run_id, "trace": records}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)