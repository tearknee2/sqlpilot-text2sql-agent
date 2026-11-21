# ============ 基础镜像 ============
FROM python:3.11-slim

# ============ 环境设置 ============
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ============ 工作目录 ============
WORKDIR /app

# ============ 先装依赖（分层缓存）============
COPY requirements.txt .
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn \
    && pip install --no-cache-dir -r requirements.txt

# ============ 再复制代码 ============
COPY . .

# ============ 默认启动命令（可被 compose 覆盖）============
CMD ["python", "-m", "uvicorn", "sqlpilot.api:app", "--host", "0.0.0.0", "--port", "8000"]