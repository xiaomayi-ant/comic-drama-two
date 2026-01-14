"""日志配置模块 - 遵循项目日志规范"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


class ConsoleFormatter(logging.Formatter):
    """控制台格式化器 - 屏蔽堆栈信息"""

    def format(self, record: logging.LogRecord) -> str:
        # 保存原始 exc_info
        original_exc_info = record.exc_info
        # 屏蔽堆栈信息
        record.exc_info = None
        result = super().format(record)
        # 恢复原始 exc_info
        record.exc_info = original_exc_info
        return result


class FileFormatter(logging.Formatter):
    """文件格式化器 - 保留完整堆栈"""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file_path: str = "logs/app.log",
) -> logging.Logger:
    """
    配置并返回 Logger 实例
    
    Args:
        name: Logger 名称
        log_level: 日志级别
        log_file_path: 日志文件路径
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Logger 本身设为 DEBUG，由 Handler 控制

    # 控制台 Handler - INFO 及以上，无堆栈
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(
        ConsoleFormatter("%(asctime)s | %(levelname)-8s | %(message)s")
    )
    logger.addHandler(console_handler)

    # 文件 Handler - DEBUG 及以上，完整堆栈
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FileFormatter())
    logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取 Logger 实例的便捷方法
    
    Args:
        name: Logger 名称，默认使用调用模块的 __name__
    
    Returns:
        Logger 实例
    """
    from src.core.config import settings

    logger_name = name or __name__
    return setup_logger(
        logger_name,
        log_level=settings.log_level,
        log_file_path=settings.log_file_path,
    )

