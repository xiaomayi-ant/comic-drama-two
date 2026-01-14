"""FastAPI 应用实例与配置"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("文案写作助手 API 服务启动")
    logger.info(f"模型: {settings.model_name}")
    yield
    logger.info("文案写作助手 API 服务关闭")


app = FastAPI(
    title="文案写作助手 API",
    description="基于 LangGraph 的口播文案写作助手 Agent",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 前端静态文件（最小 UI）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONT_DIR = PROJECT_ROOT / "fronter"
if FRONT_DIR.exists():
    app.mount(
        "/fronter",
        StaticFiles(directory=str(FRONT_DIR), html=True),
        name="fronter",
    )

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """根路径：直接返回最小前端页面"""
    index_file = FRONT_DIR / "f.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "name": "文案写作助手 API",
        "version": "0.1.0",
        "docs": "/docs",
        "hint": "前端目录缺失：请确认项目根目录下存在 fronter/f.html",
    }

