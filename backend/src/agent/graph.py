"""Agent 工作流定义模块（已废弃，仅保留兼容）"""

from typing import AsyncGenerator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

# 旧的工作流已废弃，仅保留基础导入
# 剧本生成功能已移至 src/script/graph.py
from src.agent.state import AgentState
from src.core.logger import get_logger

logger = get_logger(__name__)


def create_agent_graph(with_memory: bool = True):
    """
    废弃：此工作流已不再使用。
    剧本生成功能已移至 src/script/graph.py
    """
    logger.warning("create_agent_graph 已废弃，请使用 src.script.graph.create_script_graph")

    # 创建一个空的工作流以避免运行时错误
    workflow = StateGraph(AgentState)
    workflow.set_entry_point("__end__")
    workflow.add_edge("__end__", END)

    if with_memory:
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    return workflow.compile()


def run_agent(**kwargs):
    """废弃：此函数已不再使用。"""
    logger.warning("run_agent 已废弃，请使用 src.script.graph.run_script_agent_stream")
    return {"error": "废弃接口，请使用剧本生成接口"}


async def run_agent_stream(**kwargs):
    """废弃：此函数已不再使用。"""
    logger.warning("run_agent_stream 已废弃，请使用 src.script.graph.run_script_agent_stream")
    yield {"type": "error", "error": "废弃接口，请使用剧本生成接口"}
