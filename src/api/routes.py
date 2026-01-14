"""API 路由定义"""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.agent.graph import run_agent, run_agent_stream
from src.api.schemas import CopywritingRequest, CopywritingResponse, HealthResponse
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查接口"""
    return HealthResponse()


@router.post(
    "/generate",
    response_model=CopywritingResponse,
    tags=["文案生成"],
    summary="生成口播文案",
    description="根据用户输入的参考文案和指令，生成优质的口播文案",
)
async def generate_copywriting(request: CopywritingRequest):
    """
    生成口播文案（同步接口）
    
    工作流程：
    1. 意图分析节点：判断用户意图（文案创作/分析/聊天）
    2. 解析节点：分析用户输入的文案结构
    3. 写作节点：基于分析结果生成文案
    4. 评测节点：评估文案质量，不通过则迭代优化（最多3次）
    """
    logger.info(f"收到文案生成请求, input_length={len(request.user_input)}")
    
    # 生成线程 ID
    thread_id = request.thread_id or str(uuid.uuid4())

    # 目标时长：如果用户没写入指令，则补一条轻量提示，便于下游节点解析
    user_instructions = request.user_instructions
    if request.target_duration_sec and (not user_instructions or "秒" not in user_instructions):
        suffix = f"目标时长约{request.target_duration_sec}秒"
        user_instructions = (user_instructions + "\n" + suffix) if user_instructions else suffix
    
    try:
        # per-request debug override
        if request.debug_node_io is not None:
            settings.debug_node_io = request.debug_node_io
        if request.debug_llm_io is not None:
            settings.debug_llm_io = request.debug_llm_io

        result = run_agent(
            user_input=request.user_input,
            user_instructions=user_instructions,
            thread_id=thread_id,
            target_duration_sec=request.target_duration_sec,
            schema_json=request.schema_json,
        )
        
        if result["success"]:
            logger.info(f"文案生成成功, thread_id={thread_id}")
        else:
            logger.warning(f"文案生成失败: {result.get('error')}")
        
        return CopywritingResponse(**result)
        
    except Exception as e:
        logger.exception(f"API 处理异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/generate/stream",
    tags=["文案生成"],
    summary="流式生成口播文案",
    description="流式返回文案生成过程，支持实时显示",
)
async def generate_copywriting_stream(request: CopywritingRequest):
    """
    流式生成口播文案
    
    返回 Server-Sent Events (SSE) 格式的流式响应：
    - type: node_start - 节点开始执行
    - type: node_end - 节点执行完成
    - type: token - LLM 输出的 token
    - type: done - 生成完成
    - type: error - 发生错误
    """
    logger.info(f"收到流式文案生成请求, input_length={len(request.user_input)}")
    
    # 生成线程 ID
    thread_id = request.thread_id or str(uuid.uuid4())

    user_instructions = request.user_instructions
    if request.target_duration_sec and (not user_instructions or "秒" not in user_instructions):
        suffix = f"目标时长约{request.target_duration_sec}秒"
        user_instructions = (user_instructions + "\n" + suffix) if user_instructions else suffix
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流"""
        try:
            if request.debug_node_io is not None:
                settings.debug_node_io = request.debug_node_io
            if request.debug_llm_io is not None:
                settings.debug_llm_io = request.debug_llm_io

            async for event in run_agent_stream(
                user_input=request.user_input,
                user_instructions=user_instructions,
                thread_id=thread_id,
                target_duration_sec=request.target_duration_sec,
                schema_json=request.schema_json,
            ):
                # 格式化为 SSE
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
                
        except Exception as e:
            logger.exception(f"流式生成异常: {e}")
            error_event = json.dumps({"type": "error", "error": str(e)}, ensure_ascii=False)
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


@router.post(
    "/analyze",
    response_model=CopywritingResponse,
    tags=["文案分析"],
    summary="分析文案结构",
    description="仅执行解析节点，对文案进行结构化拆解分析",
)
async def analyze_copywriting(request: CopywritingRequest):
    """
    分析文案结构
    
    强制使用文案分析流程，返回结构化的分析结果
    """
    from src.agent.nodes import breakdown_node, intent_analysis_node
    from src.agent.state import AgentState, IntentType
    
    logger.info(f"收到文案分析请求, input_length={len(request.user_input)}")
    
    try:
        # 构建初始状态
        state: AgentState = {
            "user_input": request.user_input,
            "user_instructions": "请分析这段文案的结构",
            "intent_result": {
                "intent": IntentType.COPY_ANALYSIS.value,
                "confidence": 1.0,
                "reasoning": "用户请求分析",
            },
            "breakdown_result": None,
            "schema_ir": None,
            "analysis_report": None,
            "reverse_config": None,
            "draft_copy": None,
            "proofread_result": None,
            "final_copy": None,
            "artifact_paths": None,
            "iteration_count": 0,
            "messages": [],
            "error": None,
        }
        
        # 仅执行解析节点
        result = breakdown_node(state)
        
        return CopywritingResponse(
            success=True,
            breakdown_result=result.get("breakdown_result"),
            error=result.get("error"),
        )
        
    except Exception as e:
        logger.exception(f"分析接口处理异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
