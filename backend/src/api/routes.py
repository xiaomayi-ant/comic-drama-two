"""API 路由定义"""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.agent.graph import run_agent, run_agent_stream
from src.api.schemas import (
    ChatRequest,
    ConfigSubmitRequest,
    CopywritingRequest,
    CopywritingResponse,
    HealthResponse,
    NovelGenerationRequest,
    NovelGenerationResponse,
    NovelStreamEvent,
)
from src.novel.graph import run_novel_agent, run_novel_agent_stream
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
    
    工作流程（仿写优先版本）：
    1. 意图分析节点：判断用户意图（仿写/分析/聊天）
    2. 逆向工程节点：从参考口播中提取“可复用先验配置”（结构/风格/策略）
    3. 规划节点：在先验上做约束投影（时长/素材缺失/合规），产出 move_plan
    4. 写作节点：按 Ten-move schema 填充并渲染
    5. 规则验收节点：确定性检查（must_include/must_avoid/必选 moves 等），失败则回写作迭代
    6. 评测节点：LLM 评测与润色，通过或达到上限则输出
    """
    logger.info(f"收到文案生成请求, input_length={len(request.user_input)}")
    
    # 生成线程 ID
    thread_id = request.thread_id or str(uuid.uuid4())

    # v2 dual-mode:
    # - if new_product_specs is provided: transfer mode (cross-category / new product grounding)
    # - if not provided: imitate mode (same-product imitation; backend will best-effort auto-extract grounding)

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
            pipeline_version=request.pipeline_version,
            new_product_specs=request.new_product_specs,
            clean_room=request.clean_room,
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

    # v2 dual-mode: allow missing new_product_specs (imitate mode)

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
                pipeline_version=request.pipeline_version,
                new_product_specs=request.new_product_specs,
                clean_room=request.clean_room,
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


# ============================================================================
# 对话式配置 API 路由
# ============================================================================


STYLE_LABELS = {
    "realistic": "写实风",
    "anime": "动漫风",
    "3d": "3D动画",
    "pixel": "像素风",
}

RATIO_LABELS = {
    "16:9": "16:9横屏",
    "9:16": "9:16竖屏",
    "4:3": "4:3",
    "3:4": "3:4",
}


@router.post(
    "/chat",
    tags=["对话配置"],
    summary="发送对话消息",
    description="接收用户输入，返回配置表单（纯配置下发，不调用 LLM）",
)
async def chat(request: ChatRequest):
    """
    接收用户创作需求，返回配置表单供用户确认。
    纯配置下发，瞬时返回。
    """
    logger.info("收到对话请求, input_length=%d", len(request.user_input))

    thread_id = request.thread_id or str(uuid.uuid4())

    return {
        "type": "config_form",
        "data": {
            "thread_id": thread_id,
            "title": "创作配置确认",
            "fields": [
                {
                    "id": "target_duration",
                    "label": "1. 视频时长要求",
                    "options": [
                        {"label": "15秒内", "value": "15"},
                        {"label": "30秒内", "value": "30"},
                        {"label": "45秒内", "value": "45"},
                        {"label": "1分钟以上", "value": "60"},
                        {"label": "系统推荐时长", "value": "auto"},
                    ],
                    "default": "auto",
                },
                {
                    "id": "ratio",
                    "label": "2. 视频比例",
                    "options": [
                        {"label": "16:9横屏", "value": "16:9"},
                        {"label": "9:16竖屏", "value": "9:16"},
                        {"label": "4:3", "value": "4:3"},
                        {"label": "3:4", "value": "3:4"},
                    ],
                    "default": "16:9",
                },
                {
                    "id": "style",
                    "label": "3. 视频风格",
                    "options": [
                        {"label": "写实风", "value": "realistic"},
                        {"label": "动漫风", "value": "anime"},
                        {"label": "3D动画", "value": "3d"},
                        {"label": "像素风", "value": "pixel"},
                    ],
                    "default": "anime",
                },
                {
                    "id": "narrator",
                    "label": "4. 是否需要旁白",
                    "options": [
                        {"label": "需要旁白", "value": "yes"},
                        {"label": "不需要旁白", "value": "no"},
                    ],
                    "default": "yes",
                },
                {
                    "id": "mood",
                    "label": "5. 视频情绪基调",
                    "options": [
                        {"label": "史诗震撼", "value": "epic"},
                        {"label": "紧张刺激", "value": "intense"},
                        {"label": "怀旧感慨", "value": "nostalgic"},
                        {"label": "温馨感人", "value": "heartwarming"},
                    ],
                    "default": "heartwarming",
                },
            ],
        },
    }


@router.post(
    "/chat/submit",
    tags=["对话配置"],
    summary="提交配置并生成",
    description="接收用户配置选项，映射为 CopywritingRequest 参数并返回 SSE 流",
)
async def chat_submit(request: ConfigSubmitRequest):
    """
    接收配置表单提交，映射为 CopywritingRequest 参数，
    复用 run_agent_stream 返回 SSE 流。
    """
    logger.info(
        "收到配置提交, thread_id=%s, selections=%s",
        request.thread_id,
        request.selections,
    )

    # 映射 target_duration
    duration_val = request.selections.get("target_duration", "auto")
    target_duration_sec = None
    if duration_val != "auto":
        try:
            target_duration_sec = int(duration_val)
        except ValueError:
            pass

    # 映射 ratio + style → user_instructions
    ratio = request.selections.get("ratio", "16:9")
    style = request.selections.get("style", "anime")
    narrator = request.selections.get("narrator", "yes")
    mood = request.selections.get("mood", "heartwarming")
    
    ratio_label = RATIO_LABELS.get(ratio, ratio)
    style_label = STYLE_LABELS.get(style, style)
    
    # 构建剧本配置
    script_config = {
        "ratio": ratio_label,
        "style": style_label,
        "narrator": "需要旁白" if narrator == "yes" else "不需要旁白",
        "mood": mood,
        "duration": f"{target_duration_sec}秒" if target_duration_sec else "系统推荐",
    }
    
    user_instructions = f"视频比例：{ratio_label}，视频风格：{style_label}"

    if target_duration_sec:
        user_instructions += f"，目标时长约{target_duration_sec}秒"

    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流"""
        try:
            async for event in run_agent_stream(
                user_input=request.user_input,
                user_instructions=user_instructions,
                thread_id=request.thread_id,
                target_duration_sec=target_duration_sec,
                script_config=script_config,
            ):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            logger.exception("配置提交流式生成异常: %s", e)
            error_event = json.dumps(
                {"type": "error", "error": str(e)}, ensure_ascii=False
            )
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# 小说生成 API 路由
# ============================================================================


@router.post(
    "/novel/generate",
    response_model=NovelGenerationResponse,
    tags=["小说生成"],
    summary="生成小说/短故事",
    description="根据用户的故事概念和参考小说，生成完整的多章节故事",
)
async def generate_novel(request: NovelGenerationRequest):
    """
    生成小说/短故事（同步接口）

    工作流程：
    1. 加载参考小说 + 提取 Move Codebook
    2. 规划故事框架（章节数、标题、核心思想）
    3. 逐章生成内容
    4. 验证每章的流畅性
    5. 根据需要重新生成或继续下一章
    6. 合并所有章节为最终故事
    """
    logger.info(
        f"收到小说生成请求: "
        f"concept={request.user_input[:50]}..., "
        f"reference={request.reference_novel_title}, "
        f"chapters={request.target_chapters}"
    )

    # 生成线程 ID
    thread_id = request.thread_id or f"novel_{uuid.uuid4().hex[:8]}"

    try:
        result = await run_novel_agent(
            user_input=request.user_input,
            reference_novel_title=request.reference_novel_title,
            user_style=request.user_style,
            target_chapters=request.target_chapters,
            thread_id=thread_id,
        )

        if result["success"]:
            logger.info(
                f"小说生成成功: "
                f"title={result['story_title']}, "
                f"chapters={result['chapters_count']}, "
                f"iterations={result['iterations']}, "
                f"thread_id={thread_id}"
            )
        else:
            logger.warning(f"小说生成失败: {result.get('error')}")

        return NovelGenerationResponse(**result)

    except Exception as e:
        logger.exception(f"小说生成 API 处理异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/novel/generate/stream",
    tags=["小说生成"],
    summary="流式生成小说/短故事",
    description="流式返回小说生成过程，支持实时显示进度",
)
async def generate_novel_stream(request: NovelGenerationRequest):
    """
    流式生成小说/短故事

    返回 Server-Sent Events (SSE) 格式的流式响应：
    - type: node_start - 节点开始执行
    - type: node_end - 节点执行完成
    - type: progress - 章节生成进度
    - type: token - LLM 输出的 token（如有）
    - type: done - 生成完成
    - type: error - 发生错误
    """
    logger.info(
        f"收到流式小说生成请求: "
        f"concept={request.user_input[:50]}..., "
        f"reference={request.reference_novel_title}, "
        f"chapters={request.target_chapters}"
    )

    # 生成线程 ID
    thread_id = request.thread_id or f"novel_{uuid.uuid4().hex[:8]}"

    async def novel_event_generator() -> AsyncGenerator[str, None]:
        """生成小说生成的 SSE 事件流"""
        try:
            async for event in run_novel_agent_stream(
                user_input=request.user_input,
                reference_novel_title=request.reference_novel_title,
                user_style=request.user_style,
                target_chapters=request.target_chapters,
                thread_id=thread_id,
            ):
                # 格式化为 SSE
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
                logger.debug(f"发送事件: {event.get('type')}")

        except Exception as e:
            logger.exception(f"流式小说生成异常: {e}")
            error_event = json.dumps(
                {"type": "error", "error": str(e)}, ensure_ascii=False
            )
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        novel_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
