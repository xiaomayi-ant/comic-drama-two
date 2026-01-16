# syntax=docker/dockerfile:1

# ==========================================
# Stage 1: 构建前端
# ==========================================
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:20-alpine AS frontend-builder

WORKDIR /frontend

# 设置 npm 镜像源
RUN npm config set registry https://registry.npmmirror.com

# 复制前端依赖文件
COPY frontend/package.json frontend/package-lock.json ./

# 安装前端依赖
RUN npm ci

# 复制前端源代码
COPY frontend/ .

# 构建前端（输出到 dist/）
RUN npm run build

# ==========================================
# Stage 2: 构建后端 + 部署
# ==========================================
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_CACHE_DIR=/root/.cache/uv \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    LOG_DIR=/app/logs \
    OUTPUT_DIR=/app/outputs

WORKDIR /app

# 配置国内镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 使用阿里云 pip 源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip config set global.timeout 60 && \
    pip config set global.retries 5

# 复制项目依赖文件
COPY pyproject.toml ./

# 安装 uv 并创建虚拟环境
RUN pip install --upgrade pip && \
    pip install uvicorn && \
    pip install uv

# 使用 uv 安装 Python 依赖
RUN /bin/bash -c "uv venv && source .venv/bin/activate && UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple && uv pip install -e ."

# 复制后端源代码
COPY src/ ./src/
COPY main.py ./

# 从前端构建阶段复制构建产物到 fronter/ 目录
# （根据 server.py 的配置，前端静态文件需要在 fronter/ 目录）
COPY --from=frontend-builder /frontend/dist ./fronter

# 创建必要的目录
RUN mkdir -p ${LOG_DIR} ${OUTPUT_DIR}

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]

