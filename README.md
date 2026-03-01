# Comic Drama — AI 短剧创作系统

基于 LangGraph + FastAPI + React 的 AI 短剧内容创作平台，涵盖**剧本生成 → 分镜拆解 → AIGC 图片/视频生成 → 视频合成**完整工作流。

## 系统架构

```
┌─────────────┐    ┌────────────────────┐    ┌──────────┐
│  React 前端  │───▶│  FastAPI 后端 API   │───▶│  MongoDB  │
│  (Vite)     │    │                    │    │  Qdrant   │
└─────────────┘    │  ┌──────────────┐  │    └──────────┘
                   │  │  LangGraph   │  │
                   │  │  Agent 工作流 │  │    ┌──────────┐
                   │  └──────────────┘  │───▶│  Redis    │
                   │                    │    └────┬─────┘
                   └────────────────────┘         │
                                            ┌─────▼─────┐
                                            │  Celery    │
                                            │  Worker    │
                                            └───────────┘
```

## 核心模块

| 模块 | 路径 | 说明 |
|------|------|------|
| **剧本生成 (Script)** | `backend/src/script/` | LangGraph 工作流，从用户配置生成结构化剧本 |
| **小说生成 (Novel)** | `backend/src/novel/` | 多章节故事生成，支持 Move Codebook 叙述结构 |
| **文案 Agent** | `backend/src/agent/` | 口播文案仿写 & 分析 |
| **分镜板 (Storyboard)** | `backend/src/storyboard/` | 分镜拆解、AIGC 图片/视频生成、视频合成 |
| **语义检索 (Retrieval)** | `backend/src/retrieval/` | Qdrant + MongoDB 混合检索 |
| **前端** | `frontend/` | React 19 + Tailwind CSS 4 交互界面 |

## 快速开始

### 前置条件

- Python 3.12+、[uv](https://github.com/astral-sh/uv) 包管理器
- Node.js 18+
- Redis 6+
- MongoDB（可选，语义检索用）
- Qdrant（可选，向量检索用）

### 1. 后端

```bash
cd backend

# 安装依赖
uv sync

# 复制并编辑环境变量
cp .env.example .env
# 编辑 .env 填入必要的 API Key

# 激活虚拟环境
source .venv/bin/activate

# 启动 API 服务
python main.py --serve
# 服务运行在 http://localhost:8000
```

### 2. 前端

```bash
cd frontend

npm install

# 开发模式
npm run dev
# 服务运行在 http://localhost:3000
```

### 3. Celery Worker（分镜/AIGC/视频合成任务必需）

```bash
# 确保 Redis 已启动
redis-server

# 在 backend 目录下启动 Worker
cd backend
source .venv/bin/activate

celery -A src.core.celery_app worker --loglevel=info
```

生产环境推荐：

```bash
celery -A src.core.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --pool=prefork \
  --prefetch-multiplier=1
```

可选 — 启动 Flower 任务监控面板：

```bash
celery -A src.core.celery_app flower --port=5555
# 访问 http://localhost:5555
```

## 环境变量

在 `backend/.env` 中配置（参考 `.env.example`）：

```env
# LLM 提供商：dashscope | openai
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_key
MODEL_NAME=qwen-plus

# API 服务
API_HOST=0.0.0.0
API_PORT=8000

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=false   # 设为 true 可同步执行（测试用）

# 数据库（语义检索）
MONGODB_URI=mongodb://admin:password@localhost:27017
QDRANT_HOST=localhost
QDRANT_PORT=6333

# AIGC（通义万相）
AIGC_IMAGE_MODEL=wanx2.1-t2i-turbo
AIGC_VIDEO_MODEL=wan2.1-i2v-plus

# 日志
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
```

## API 接口

启动后访问 Swagger 文档：http://localhost:8000/docs

### 主要端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 健康检查 |
| `POST` | `/api/v1/chat/submit` | 提交剧本生成配置（SSE 流式） |
| `POST` | `/api/v1/novel/generate` | 同步生成多章节小说 |
| `POST` | `/api/v1/novel/generate/stream` | 流式生成多章节小说 |
| `POST` | `/api/v1/storyboard/episodes` | 创建剧集 |
| `POST` | `/api/v1/storyboard/episodes/from-script` | 从剧本数据创建剧集 |
| `POST` | `/api/v1/storyboard/episodes/storyboards` | 触发分镜生成（异步） |
| `POST` | `/api/v1/storyboard/episodes/{id}/generate-aigc` | 触发 AIGC 生成（异步） |
| `POST` | `/api/v1/storyboard/videos/merge` | 触发视频合成（异步） |
| `GET` | `/api/v1/storyboard/tasks/{task_id}` | 查询异步任务状态 |

### Celery 异步任务

分镜板模块的耗时操作通过 Celery 异步执行：

| 任务 | 模块 | 说明 |
|------|------|------|
| `generate_storyboard_task` | `storyboard_tasks` | 根据剧集内容生成分镜 |
| `generate_aigc_task` | `aigc_tasks` | 文生图 + 图生视频（通义万相） |
| `merge_episode_videos_task` | `video_tasks` | 多片段视频合成（FFmpeg） |

调用流程：API 创建任务 → 返回 `task_id` → Celery Worker 后台执行 → 通过 `GET /tasks/{task_id}` 轮询状态。

## 项目结构

```
comic-drama-two/
├── backend/
│   ├── main.py                     # 入口（--serve 启动 API）
│   ├── pyproject.toml              # Python 依赖
│   ├── Dockerfile
│   ├── .env.example
│   └── src/
│       ├── api/
│       │   ├── server.py           # FastAPI 应用
│       │   ├── routes.py           # 通用路由
│       │   ├── storyboard_routes.py # 分镜板路由
│       │   └── schemas.py          # Pydantic 数据模型
│       ├── agent/                  # 文案 Agent（LangGraph）
│       ├── script/                 # 剧本生成（LangGraph）
│       ├── novel/                  # 小说生成（LangGraph）
│       ├── storyboard/
│       │   ├── tasks/              # Celery 任务定义
│       │   ├── services/           # 业务逻辑
│       │   ├── utils/              # FFmpeg 等工具
│       │   └── bridge.py           # 剧本 → 剧集转换
│       ├── retrieval/              # 语义检索（Qdrant + MongoDB）
│       └── core/
│           ├── config.py           # Pydantic Settings 配置
│           ├── celery_app.py       # Celery 实例
│           ├── database.py         # 数据库连接
│           └── logger.py           # 日志配置
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # 主应用
│   │   └── components/             # React 组件
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml              # Docker 编排
├── Caddyfile                       # Caddy 反向代理
├── DEPLOY.md                       # 部署指南
└── architecture_v0.1.md            # 架构设计文档
```

## Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

当前 `docker-compose.yml` 包含 backend、frontend、caddy 三个服务。如需在 Docker 中运行 Celery，需添加 Redis 和 Worker 服务：

```yaml
# 在 docker-compose.yml 的 services 下添加：
redis:
  image: redis:7-alpine
  container_name: writer2-redis
  ports:
    - "6379:6379"
  restart: unless-stopped
  networks:
    - writer2-network

celery-worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: writer2-celery
  command: celery -A src.core.celery_app worker --loglevel=info --concurrency=4
  env_file:
    - ./backend/.env
  environment:
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    - redis
  restart: unless-stopped
  networks:
    - writer2-network
```

## 技术栈

**后端**：Python 3.12 / FastAPI / LangGraph / Celery / SQLAlchemy / Pydantic

**前端**：React 19 / TypeScript / Vite / Tailwind CSS 4

**基础设施**：Redis / MongoDB / Qdrant / FFmpeg / Docker / Caddy

**LLM**：通义千问（DashScope）/ OpenAI 兼容接口

**AIGC**：通义万相（文生图 wanx2.1 / 图生视频 wan2.1）

## 开发命令速查

```bash
# 后端
cd backend && source .venv/bin/activate
python main.py --serve              # 启动 API
python main.py --test               # 运行文案 Agent 测试
celery -A src.core.celery_app worker --loglevel=info  # Celery Worker

# 前端
cd frontend
npm run dev                         # 开发服务器
npm run build                       # 构建生产版本
npm run lint                        # TypeScript 检查

# Docker
docker-compose up -d                # 启动全部服务
docker-compose down                 # 停止全部服务
```

---

最后更新：2026-03-01
