"""小说生成 Agent 的工作流定义"""

import logging
from typing import AsyncGenerator, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.novel.state import NovelAgentState
from src.novel.nodes import (
    load_reference_node,
    plan_story_node,
    write_chapter_node,
    verify_fluency_node,
    finalize_node,
    should_revise_chapter,
    should_continue_chapters,
)
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


def create_novel_graph(with_memory: bool = True):
    """
    创建小说生成工作流

    工作流程：
    1. load_reference: 加载参考小说 + 提取 Move
    2. plan_story: 规划故事框架
    3. write_chapter: 逐章生成内容（循环）
    4. verify_fluency: 检查通顺性
    5. [条件] should_revise: 是否重新生成
    6. [条件] should_continue: 是否继续下一章
    7. finalize: 合并所有章节

    Args:
        with_memory: 是否启用记忆功能（会话持久化）

    Returns:
        编译后的 Agent 工作流
    """

    logger.info("创建小说生成工作流")

    # 创建状态图
    workflow = StateGraph(NovelAgentState)

    # ============================================================================
    # 添加节点
    # ============================================================================
    workflow.add_node("load_reference", load_reference_node)
    workflow.add_node("plan_story", plan_story_node)
    workflow.add_node("write_chapter", write_chapter_node)
    workflow.add_node("verify_fluency", verify_fluency_node)
    workflow.add_node("finalize", finalize_node)

    # 准备下一章的辅助节点
    def prepare_next_chapter_node(state: NovelAgentState) -> dict:
        """准备下一章的状态"""
        return {
            "current_chapter": state["current_chapter"] + 1,
            "chapters_completed": state["chapters_completed"] + 1,
            "chapter_texts": state["chapter_texts"] + [state["current_chapter_text"]],
            "chapter_iterations": 0,
        }

    workflow.add_node("prepare_next_chapter", prepare_next_chapter_node)

    # ============================================================================
    # 设置入口点
    # ============================================================================
    workflow.set_entry_point("load_reference")

    # ============================================================================
    # 添加边
    # ============================================================================

    # 主流程
    workflow.add_edge("load_reference", "plan_story")
    workflow.add_edge("plan_story", "write_chapter")
    workflow.add_edge("write_chapter", "verify_fluency")

    # 验证后的条件路由
    workflow.add_conditional_edges(
        "verify_fluency",
        should_revise_chapter,
        {
            "revise": "write_chapter",  # 重新生成这章
            "continue": "should_continue_chapters",  # 继续到章节决策
        },
    )

    # 章节决策
    def chapter_decision_router(state: NovelAgentState) -> str:
        """路由到下一步：继续下一章或完成"""
        return should_continue_chapters(state)

    # 添加章节决策节点（虚拟节点，只用于路由）
    workflow.add_node("should_continue_chapters", lambda state: state)

    workflow.add_conditional_edges(
        "should_continue_chapters",
        chapter_decision_router,
        {
            "next_chapter": "prepare_next_chapter",  # 继续下一章
            "finalize": "finalize",  # 所有章节完成
        },
    )

    # 准备下一章 → 写作下一章
    workflow.add_edge("prepare_next_chapter", "write_chapter")

    # 最终化 → 结束
    workflow.add_edge("finalize", END)

    # ============================================================================
    # 编译工作流
    # ============================================================================
    if with_memory:
        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)
        logger.info("✅ 工作流创建完成 (with memory)")
    else:
        graph = workflow.compile()
        logger.info("✅ 工作流创建完成 (without memory)")

    return graph


async def run_novel_agent(
    user_input: str,
    reference_novel_title: str,
    user_style: Optional[str] = None,
    target_chapters: int = 5,
    thread_id: str = "default",
) -> dict:
    """
    同步运行小说生成 Agent

    Args:
        user_input: 故事概念，e.g. "关于失去和重新开始"
        reference_novel_title: 参考小说的名称，e.g. "诡秘之主"
        user_style: 可选的风格要求
        target_chapters: 目标章数，默认 5
        thread_id: 会话 ID，用于记忆管理

    Returns:
        {
            "success": True/False,
            "story_title": "...",
            "final_story": "...",
            "chapters_count": 5,
            "iterations": 15,
            "error": "..."
        }
    """

    logger.info(f"运行小说 Agent, thread_id={thread_id}")
    logger.info(f"参考小说: {reference_novel_title}, 目标章数: {target_chapters}")

    # 创建 Graph
    graph = create_novel_graph(with_memory=True)

    # 初始化状态
    initial_state: NovelAgentState = {
        "user_input": user_input,
        "user_style": user_style,
        "target_chapters": target_chapters,
        "reference_novel_title": reference_novel_title,
        "reference_novel_data": None,
        "move_codebook": None,
        "move_codebook_id": None,
        "story_ir": None,
        "story_ir_id": None,
        "current_chapter": 0,
        "chapters_completed": 0,
        "chapter_texts": [],
        "current_chapter_text": None,
        "fluency_check": None,
        "iteration_count": 0,
        "chapter_iterations": 0,
        "messages": [],
        "error": None,
        "final_story": None,
    }

    # 配置
    recursion_limit = max(100, target_chapters * 20)  # 为每章预留足够的迭代空间
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }

    # 执行工作流
    try:
        final_state = await graph.ainvoke(initial_state, config)

        logger.info("✅ Agent 执行完成")

        return {
            "success": True,
            "story_title": final_state.get("story_ir", {}).get("story_title"),
            "final_story": final_state.get("final_story"),
            "chapters_count": final_state.get("chapters_completed", 0),
            "iterations": final_state.get("iteration_count", 0),
            "error": None,
        }

    except Exception as e:
        logger.exception(f"Agent 执行失败: {e}")
        return {
            "success": False,
            "story_title": None,
            "final_story": None,
            "chapters_count": 0,
            "iterations": 0,
            "error": str(e),
        }


async def run_novel_agent_stream(
    user_input: str,
    reference_novel_title: str,
    user_style: Optional[str] = None,
    target_chapters: int = 5,
    thread_id: str = "default",
) -> AsyncGenerator[dict, None]:
    """
    流式运行小说生成 Agent

    Yields:
        {
            "type": "node_start" | "node_end" | "progress" | "done" | "error",
            "node": "node_name",
            "content": "...",
            "chapter": 1,
            ...
        }
    """

    logger.info(f"流式运行小说 Agent, thread_id={thread_id}")

    graph = create_novel_graph(with_memory=True)

    initial_state: NovelAgentState = {
        "user_input": user_input,
        "user_style": user_style,
        "target_chapters": target_chapters,
        "reference_novel_title": reference_novel_title,
        "reference_novel_data": None,
        "move_codebook": None,
        "move_codebook_id": None,
        "story_ir": None,
        "story_ir_id": None,
        "current_chapter": 0,
        "chapters_completed": 0,
        "chapter_texts": [],
        "current_chapter_text": None,
        "fluency_check": None,
        "iteration_count": 0,
        "chapter_iterations": 0,
        "messages": [],
        "error": None,
        "final_story": None,
    }

    recursion_limit = max(100, target_chapters * 20)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }

    try:
        # 流式执行
        async for event in graph.astream_events(initial_state, config, version="v2"):
            event_kind = event.get("event")
            node_name = event.get("name", "")

            # 节点开始
            if event_kind == "on_chain_start" and node_name:
                yield {
                    "type": "node_start",
                    "node": node_name,
                }

            # 节点完成
            elif event_kind == "on_chain_end" and node_name:
                output = event.get("data", {}).get("output", {})

                # 如果是写作节点，报告进度
                if node_name == "write_chapter" and "current_chapter_text" in output:
                    yield {
                        "type": "progress",
                        "node": node_name,
                        "chapter": output.get("current_chapter", 0),
                        "text_snippet": output["current_chapter_text"][:200],
                    }
                else:
                    yield {
                        "type": "node_end",
                        "node": node_name,
                    }

            # LLM 流式输出（如果有）
            elif event_kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {
                        "type": "token",
                        "content": chunk.content,
                    }

        # 完成
        yield {"type": "done"}

    except Exception as e:
        logger.exception(f"流式执行失败: {e}")
        yield {
            "type": "error",
            "error": str(e),
        }


# ============================================================================
# 调试和可视化
# ============================================================================

def visualize_graph():
    """可视化工作流图（用于调试）"""
    graph = create_novel_graph(with_memory=False)

    try:
        mermaid = graph.get_graph().draw_mermaid()
        logger.info("\n工作流图表：\n%s", mermaid)
    except Exception as e:
        logger.warning(f"无法生成图表: {e}")
        logger.info("""
工作流结构：

load_reference
    ↓
plan_story
    ↓
write_chapter ← prepare_next_chapter
    ↓
verify_fluency
    ├─ [not fluent & iterations < 2] → write_chapter (重新生成)
    └─ [fluent or iterations >= 2] → chapter_decision
                                         ├─ [current < total] → prepare_next_chapter
                                         └─ [current >= total] → finalize
                                              ↓
                                              END
        """)


if __name__ == "__main__":
    # 测试用途
    visualize_graph()
