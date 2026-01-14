"""环境变量与配置管理模块"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类 - 从环境变量加载"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM 提供商选择：dashscope | openai
    llm_provider: str = Field(
        default="dashscope",
        description="LLM 提供商: dashscope (通义千问) 或 openai",
    )

    # 通义千问配置
    dashscope_api_key: str = Field(
        default="", description="DashScope API Key"
    )
    
    # OpenAI 配置
    openai_api_key: str = Field(
        default="", description="OpenAI API Key"
    )
    openai_base_url: str = Field(
        default="", description="OpenAI Base URL（可选，用于代理或兼容 API）"
    )
    
    # 模型配置（通用）
    model_name: str = Field(
        default="qwen-plus", description="模型名称（dashscope: qwen-plus / openai: gpt-4o-mini 等）"
    )
    model_temperature: float = Field(
        default=0.7, description="模型温度"
    )

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file_path: str = Field(
        default="logs/app.log", description="日志文件路径"
    )

    # API 配置
    api_host: str = Field(default="0.0.0.0", description="API 主机")
    api_port: int = Field(default=8000, description="API 端口")

    # Agent 配置
    max_iterations: int = Field(
        default=3, description="最大迭代次数"
    )

    # Move planner（动态步骤规划）
    enable_move_planner: bool = Field(
        default=True,
        description="是否启用 move_planner（让 LLM 动态选择/排序/融合 moves；关闭则使用固定裁剪）",
    )

    # 调试开关（开发环境建议开启，生产环境关闭）
    debug_node_io: bool = Field(
        default=False,
        description="是否打印节点输入/输出（开发用，生产建议关闭）",
    )
    debug_llm_io: bool = Field(
        default=False,
        description="是否打印 LLM 输入/输出原文（开发用，生产建议关闭）",
    )

    def ensure_api_keys_env(self) -> None:
        """确保 API Key 在环境变量中（LangChain 自动读取）"""
        # DashScope
        if not os.getenv("DASHSCOPE_API_KEY") and self.dashscope_api_key:
            os.environ["DASHSCOPE_API_KEY"] = self.dashscope_api_key
        # OpenAI
        if not os.getenv("OPENAI_API_KEY") and self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        if not os.getenv("OPENAI_BASE_URL") and self.openai_base_url:
            os.environ["OPENAI_BASE_URL"] = self.openai_base_url


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


def load_settings() -> Settings:
    """加载配置并确保环境变量设置"""
    settings = get_settings()
    settings.ensure_api_keys_env()
    return settings


# 模块级别的 settings 实例
settings = load_settings()
