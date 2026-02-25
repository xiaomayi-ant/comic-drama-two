"""Agent 工作流定义模块"""

from typing import AsyncGenerator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agent.nodes import (
    intent_analysis_node,
    breakdown_node,
    analysis_report_node,
    move_plan_node,
    proofread_node,
    reverse_engineer_node,
    route_by_intent,
    should_continue,
    simple_chat_node,
    should_proceed_after_verify,
    verify_node,
    writing_node,
)
from src.agent.nodes_v2 import (
    analyst_v2_node,
    creator_v2_node,
    entity_mapper_v2_node,
    normalizer_v2_node,
    preprocess_v2_node,
    qc_v2_node,
    should_proceed_after_qc,
)
from src.agent.state import AgentState, IntentType
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


def create_agent_graph(with_memory: bool = True):
    """
    创建文案写作助手 Agent 工作流
    
    工作流程（仿写优先版本）:
    1. intent_analysis: 分析用户意图
    2. 根据意图路由:
       - copy_writing: reverse_engineer → move_plan → writing → verify → proofread → (迭代或输出)
       - copy_analysis: breakdown → 直接输出分析结果
       - simple_chat: 直接 LLM 回复
    
    Args:
        with_memory: 是否启用记忆功能
    
    Returns:
        编译后的 Agent 工作流
    """
    logger.info("创建 Agent 工作流")
    
    # 创建状态图
    workflow = StateGraph(AgentState)
    
    # ============================================================
    # 添加节点
    # ============================================================
    workflow.add_node("intent_analysis", intent_analysis_node)
    workflow.add_node("breakdown", breakdown_node)
    workflow.add_node("analysis_report", analysis_report_node)
    workflow.add_node("reverse_engineer", reverse_engineer_node)
    workflow.add_node("move_plan", move_plan_node)
    workflow.add_node("writing", writing_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("proofread", proofread_node)
    workflow.add_node("simple_chat", simple_chat_node)

    # v2 pipeline nodes
    workflow.add_node("v2_preprocess", preprocess_v2_node)
    workflow.add_node("v2_analyst", analyst_v2_node)
    workflow.add_node("v2_normalizer", normalizer_v2_node)
    workflow.add_node("v2_entity_mapper", entity_mapper_v2_node)
    workflow.add_node("v2_creator", creator_v2_node)
    workflow.add_node("v2_qc", qc_v2_node)
    
    # 分析流程结束节点（将 breakdown 结果转为 final_copy）
    def analysis_output_node(state: AgentState) -> dict:
        """将文案分析结果作为最终输出"""
        breakdown_result = state.get("breakdown_result", {})
        import json
        analysis_text = json.dumps(breakdown_result, ensure_ascii=False, indent=2)
        return {"final_copy": f"【文案结构分析结果】\n\n{analysis_text}"}
    
    workflow.add_node("analysis_output", analysis_output_node)
    
    # ============================================================
    # 设置入口点
    # ============================================================
    workflow.set_entry_point("intent_analysis")
    
    # ============================================================
    # 添加边 - 意图路由
    # ============================================================
    # v1/v2 routing at entry
    def route_entry(state: AgentState) -> str:
        base = route_by_intent(state)
        if base != "copy_flow":
            return base
        pv = (state.get("pipeline_version") or "v1").lower().strip()
        return "copy_flow_v2" if pv == "v2" else "copy_flow"

    workflow.add_conditional_edges(
        "intent_analysis",
        route_entry,
        {
            "copy_flow": "reverse_engineer",
            "copy_flow_v2": "v2_preprocess",
            "analysis_flow": "breakdown",
            "chat_flow": "simple_chat",
        },
    )
    
    # ============================================================
    # 文案创作流程
    # ============================================================
    
    # breakdown 后根据意图决定下一步
    def route_after_breakdown(state: AgentState) -> str:
        intent_result = state.get("intent_result", {})
        intent = intent_result.get("intent", IntentType.COPY_WRITING.value)
        if intent == IntentType.COPY_ANALYSIS.value:
            return "to_analysis_output"
        # 文案创作流程：先走 analysis_report（汇入主流程）
        return "to_analysis_report"
    
    workflow.add_conditional_edges(
        "breakdown",
        route_after_breakdown,
        {
            "to_analysis_report": "analysis_report",
            "to_analysis_output": "analysis_output",
        },
    )

    # ============================================================
    # 仿写链路（prior-driven）
    # reverse_engineer(prior) → move_plan(projection) → writing(execution) → verify(rule checks) → proofread(llm)
    # ============================================================
    workflow.add_edge("reverse_engineer", "move_plan")
    workflow.add_edge("move_plan", "writing")
    workflow.add_edge("writing", "verify")
    
    # verify → 条件路由（规则不过直接回写作；过了再进入 LLM 评测）
    workflow.add_conditional_edges(
        "verify",
        should_proceed_after_verify,
        {
            "revise": "writing",
            "proceed": "proofread",
        },
    )

    # v2 chain
    workflow.add_edge("v2_preprocess", "v2_analyst")
    workflow.add_edge("v2_analyst", "v2_normalizer")
    workflow.add_edge("v2_normalizer", "v2_entity_mapper")
    workflow.add_edge("v2_entity_mapper", "v2_creator")
    workflow.add_edge("v2_creator", "v2_qc")
    workflow.add_conditional_edges(
        "v2_qc",
        should_proceed_after_qc,
        {
            "revise": "v2_creator",
            "proceed": "proofread",
        },
    )
    
    # 分析链路（保留，供未来扩展；当前 analysis_flow 直接输出 breakdown）
    workflow.add_edge("analysis_report", "reverse_engineer")
    
    # proofread → 条件路由
    workflow.add_conditional_edges(
        "proofread",
        should_continue,
        {
            "continue": "writing",  # 继续迭代
            "end": END,             # 结束
        },
    )
    
    # ============================================================
    # 其他流程终点
    # ============================================================
    workflow.add_edge("simple_chat", END)
    workflow.add_edge("analysis_output", END)
    
    # ============================================================
    # 编译工作流
    # ============================================================
    if with_memory:
        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)
        logger.info("Agent 工作流创建完成 (with memory)")
    else:
        graph = workflow.compile()
        logger.info("Agent 工作流创建完成 (without memory)")
    
    return graph


def run_agent(
    user_input: str,
    user_instructions: str | None = None,
    thread_id: str = "default",
    target_duration_sec: int | None = None,
    schema_json: dict | None = None,
    pipeline_version: str | None = None,
    new_product_specs: dict | None = None,
    clean_room: bool | None = None,
) -> dict:
    """
    同步运行 Agent 工作流
    
    Args:
        user_input: 用户输入（参考文案或素材）
        user_instructions: 用户额外指令
        thread_id: 会话线程 ID（用于记忆）
    
    Returns:
        包含最终文案和中间结果的字典
    """
    logger.info(f"运行 Agent, thread_id={thread_id}")
    
    # 创建 Agent
    graph = create_agent_graph(with_memory=True)
    
    # 初始状态
    schema_ir = schema_json
    if schema_ir is not None and target_duration_sec is not None:
        # best-effort: align schema spoken constraints
        schema_ir = dict(schema_ir)
        sc = dict(schema_ir.get("spoken_constraints") or {})
        sc["target_duration_sec"] = target_duration_sec
        schema_ir["spoken_constraints"] = sc

    initial_state: AgentState = {
        "user_input": user_input,
        "user_instructions": user_instructions,
        "intent_result": None,
        "breakdown_result": None,
        "schema_ir": schema_ir,
        "pipeline_version": (pipeline_version or "v1"),
        "new_product_specs": new_product_specs,
        "clean_room": clean_room,
        "preprocess_result": None,
        "skeleton_v2": None,
        "entity_mapping": None,
        "qc_report": None,
        "analysis_report": None,
        "reverse_config": None,
        "move_plan": None,
        "verification_result": None,
        "draft_copy": None,
        "writing_meta": None,
        "proofread_result": None,
        "final_copy": None,
        "artifact_paths": None,
        "iteration_count": 0,
        "messages": [],
        "error": None,
        "script_config": None,
    }
    
    # 配置
    # NOTE: recursion_limit is a safety-net for graph loops. Keep it aligned with max_iterations
    # so we fail fast if something is wrong, instead of burning tokens forever.
    recursion_limit = max(25, int(getattr(settings, "max_iterations", 3) or 3) * 10)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }
    
    # 执行工作流
    try:
        final_state = graph.invoke(initial_state, config)
        
        logger.info("Agent 执行完成")
        
        return {
            "success": True,
            "final_copy": final_state.get("final_copy"),
            "draft_copy": final_state.get("draft_copy"),
            "intent_result": final_state.get("intent_result"),
            "breakdown_result": final_state.get("breakdown_result"),
            "schema_ir": final_state.get("schema_ir"),
            "preprocess_result": final_state.get("preprocess_result"),
            "skeleton_v2": final_state.get("skeleton_v2"),
            "entity_mapping": final_state.get("entity_mapping"),
            "qc_report": final_state.get("qc_report"),
            "analysis_report": final_state.get("analysis_report"),
            "reverse_config": final_state.get("reverse_config"),
            "move_plan": final_state.get("move_plan"),
            "verification_result": final_state.get("verification_result"),
            "proofread_result": final_state.get("proofread_result"),
            "writing_meta": final_state.get("writing_meta"),
            "artifact_paths": final_state.get("artifact_paths"),
            "iteration_count": final_state.get("iteration_count", 0),
            "error": final_state.get("error"),
        }
        
    except Exception as e:
        logger.exception(f"Agent 执行失败: {e}")
        return {
            "success": False,
            "final_copy": None,
            "error": str(e),
        }


async def run_agent_stream(
    user_input: str,
    user_instructions: str | None = None,
    thread_id: str = "default",
    target_duration_sec: int | None = None,
    schema_json: dict | None = None,
    pipeline_version: str | None = None,
    new_product_specs: dict | None = None,
    clean_room: bool | None = None,
    script_config: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """
    异步流式运行 Agent 工作流
    
    Args:
        user_input: 用户输入
        user_instructions: 用户额外指令
        thread_id: 会话线程 ID
    
    Yields:
        流式事件字典
    """
    logger.info(f"流式运行 Agent, thread_id={thread_id}")
    
    # 创建 Agent
    graph = create_agent_graph(with_memory=True)
    
    # 初始状态
    schema_ir = schema_json
    if schema_ir is not None and target_duration_sec is not None:
        schema_ir = dict(schema_ir)
        sc = dict(schema_ir.get("spoken_constraints") or {})
        sc["target_duration_sec"] = target_duration_sec
        schema_ir["spoken_constraints"] = sc

    initial_state: AgentState = {
        "user_input": user_input,
        "user_instructions": user_instructions,
        "intent_result": None,
        "breakdown_result": None,
        "schema_ir": schema_ir,
        "pipeline_version": (pipeline_version or "v1"),
        "new_product_specs": new_product_specs,
        "clean_room": clean_room,
        "preprocess_result": None,
        "skeleton_v2": None,
        "entity_mapping": None,
        "qc_report": None,
        "analysis_report": None,
        "reverse_config": None,
        "move_plan": None,
        "verification_result": None,
        "draft_copy": None,
        "writing_meta": None,
        "proofread_result": None,
        "final_copy": None,
        "artifact_paths": None,
        "iteration_count": 0,
        "messages": [],
        "error": None,
        "script_config": script_config,
    }
    
    # 配置
    recursion_limit = max(25, int(getattr(settings, "max_iterations", 3) or 3) * 10)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }
    
    try:
        # 跟踪最终产出（astream_events 不会写回 initial_state）
        final_copy = None
        draft_copy = None

        # 使用 astream_events 获取流式事件
        async for event in graph.astream_events(initial_state, config, version="v2"):
            event_kind = event.get("event")

            # 节点开始
            if event_kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name in [
                    "intent_analysis",
                    "breakdown",
                    "analysis_report",
                    "reverse_engineer",
                    "move_plan",
                    "writing",
                    "v2_preprocess",
                    "v2_analyst",
                    "v2_normalizer",
                    "v2_entity_mapper",
                    "v2_creator",
                    "v2_qc",
                    "proofread",
                    "simple_chat",
                ]:
                    yield {
                        "type": "node_start",
                        "node": node_name,
                    }

            # 节点结束
            elif event_kind == "on_chain_end":
                node_name = event.get("name", "")
                if node_name in [
                    "intent_analysis",
                    "breakdown",
                    "analysis_report",
                    "reverse_engineer",
                    "move_plan",
                    "writing",
                    "v2_preprocess",
                    "v2_analyst",
                    "v2_normalizer",
                    "v2_entity_mapper",
                    "v2_creator",
                    "v2_qc",
                    "proofread",
                    "simple_chat",
                ]:
                    output = event.get("data", {}).get("output", {})
                    # 从节点输出中捕获最终文案
                    if isinstance(output, dict):
                        if output.get("final_copy"):
                            final_copy = output["final_copy"]
                        if output.get("draft_copy"):
                            draft_copy = output["draft_copy"]
                    yield {
                        "type": "node_end",
                        "node": node_name,
                        "output": output,
                    }

            # LLM 流式输出
            elif event_kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {
                        "type": "token",
                        "content": chunk.content,
                    }

        # 完成，发送最终结果
        done_content = final_copy or draft_copy
        logger.info("流式完成, final_copy=%s, draft_copy=%s", bool(final_copy), bool(draft_copy))
        yield {"type": "done", "content": done_content}
        
    except Exception as e:
        logger.exception(f"流式执行失败: {e}")
        yield {
            "type": "error",
            "error": str(e),
        }
