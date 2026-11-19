"""FastAPI 端点测试（doc §5 D8）。"""
from fastapi.testclient import TestClient
from sqlpilot.api import app

# TestClient 模拟浏览器发请求，不会真正启动 uvicorn 占用端口
client = TestClient(app)


def test_health():
    """健康检查：DB 必须连通。"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["db"] is True


def test_query_empty_question():
    """空问题：Pydantic 应该拦截并返回 422。"""
    resp = client.post("/api/v1/query", json={"question": ""})
    assert resp.status_code == 422


def test_query_max_retries_clamped():
    """参数越界：max_retries 传 5，应该被 Pydantic 拦截返回 422。"""
    resp = client.post("/api/v1/query", json={
        "question": "测试问题",
        "options": {"max_retries": 5}
    })
    assert resp.status_code == 422