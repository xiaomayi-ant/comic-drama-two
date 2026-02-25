# ── Stage 1: build ──
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# 先复制依赖清单，利用 layer cache
COPY pyproject.toml uv.lock ./

# 安装依赖到 .venv（不装项目本身）
RUN uv sync --frozen --no-install-project

# 再复制项目源码并安装
COPY . .
RUN uv sync --frozen

# ── Stage 2: runtime ──
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# 从 builder 拷贝虚拟环境和项目文件
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/main.py /app/main.py

# 确保 .venv/bin 在 PATH 中
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 创建日志和数据目录
RUN mkdir -p /app/logs /app/outputs /app/data

EXPOSE 8000

CMD ["python", "main.py", "--serve"]
