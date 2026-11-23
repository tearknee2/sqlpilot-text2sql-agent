"""FastAPI 端点（doc §10.2）。"""
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request

from sqlpilot.config import get_settings
from sqlpilot.schemas.request import QueryRequest
from sqlpilot.schemas.response import TraceStep, Metrics, QueryResponse, ResultTable
from sqlpilot.service import QueryService
from sqlpilot.tools.executor import MySqlExecutor

logger = logging.getLogger("sqlpilot.api")

app = FastAPI(title="SQLPilot", version="2.0")

# ---------------------------------------------------------------- 单机内存限流 (P1-6)
# 每 IP 每分钟最多 rate_limit_per_min 次请求（单 worker 内存计数；多 worker 需换 Redis）。
_RATE_WINDOW_S = 60
_rate_buckets: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(client_ip: str, limit_per_min: int) -> bool:
    """True=放行，False=超限。滑动窗口：只保留最近 60s 的请求时间戳。"""
    now = time.monotonic()
    q = _rate_buckets[client_ip]
    while q and now - q[0] > _RATE_WINDOW_S:
        q.popleft()
    if len(q) >= limit_per_min:
        return False
    q.append(now)
    return True


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """仅对 /api/v1/query 这类昂贵端点限流（health/schema 放行）。"""
    if request.url.path.startswith("/api/v1/query"):
        limit = get_settings().rate_limit_per_min
        ip = request.client.host if request.client else "unknown"
        if not _check_rate_limit(ip, limit):
            return _too_many_requests()
    return await call_next(request)


def _too_many_requests():
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"detail": "rate limit exceeded, retry later", "code": "RATE_LIMITED"},
    )


# ---------------------------------------------------------------- 端点
@app.get("/api/v1/health")
def health():
    """检查 DB 连通性。"""
    db_ok = MySqlExecutor().execute("SELECT 1")["ok"]
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}


@app.get("/api/v1/schema")
def get_schema():
    """返回当前 catalog 摘要（表数量 + 表名列表）。"""
    from sqlpilot.schema.catalog import get_catalog
    cat = get_catalog()
    return {"tables": len(cat.allowed_tables), "names": sorted(cat.allowed_tables)}


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
        raw = svc.query(req.question)
    except Exception as e:
        # P1-3：不把异常原文回给客户端（可能含连接串/路径）；详情记服务端日志。
        logger.exception("query failed: %s", e)
        raise HTTPException(status_code=500, detail="internal error, see server logs")

    exec_res = raw.get("exec_result")
    usage = raw.get("usage") or {}

    return QueryResponse(
        run_id=raw["run_id"],
        final_status=raw["final_status"],
        answer=raw.get("answer"),
        sql=raw.get("sql"),
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
        trace=[TraceStep(**t) for t in raw.get("trace", [])],
    )


@app.get("/api/v1/trace/{run_id}")
def get_trace(run_id: str):
    """读取指定的 run_id 的 trace 记录。"""
    from sqlpilot.observability.trace import replay
    records = replay(run_id)
    if not records:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"run_id": run_id, "trace": records}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
