"""API 请求/响应 Pydantic 模型"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class CopywritingRequest(BaseModel):
    """文案生成请求"""

    model_config = {"str_strip_whitespace": True}

    user_input: str = Field(
        ...,
        min_length=1,
        description="用户输入（参考文案或素材）",
    )
    user_instructions: Optional[str] = Field(
        default=None,
        description="用户额外指令",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="会话线程 ID（用于记忆）",
    )

    # 口播场景扩展（直播带货）
    target_duration_sec: Optional[int] = Field(
        default=None,
        ge=10,
        le=180,
        description="目标口播时长（秒），建议 30 或 60",
    )
    schema_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="可选：直接传入 Ten-move schema IR（中间层），则跳过模板生成",
    )

    # v2 pipeline controls
    pipeline_version: Optional[str] = Field(
        default="v1",
        description='可选：流水线版本，"v1"=Ten-move；"v2"=Skeleton v2（move_step4）',
    )
    clean_room: Optional[bool] = Field(
        default=False,
        description="v2 可选：Clean Room 模式（Creator 看不到 source_span/原文片段）",
    )
    new_product_specs: Optional[dict[str, Any]] = Field(
        default=None,
        description="v2 可选：新产品结构化事实（用于实体映射与事实锚定）。为空则进入 v2 仿写模式（同品类/同商品）；提供则进入 v2 迁移模式（跨品类/换商品）。建议包含 product_name/category/core_benefit/proof_points/offer 等",
    )

    debug_node_io: Optional[bool] = Field(
        default=None,
        description="可选：本次请求强制开启/关闭节点 IO 调试日志（优先于环境变量）",
    )
    debug_llm_io: Optional[bool] = Field(
        default=None,
        description="可选：本次请求强制开启/关闭 LLM 输入输出调试日志（优先于环境变量）",
    )


class CopywritingResponse(BaseModel):
    """文案生成响应"""

    success: bool = Field(default=True, description="是否成功")
    final_copy: Optional[str] = Field(default=None, description="最终文案")
    draft_copy: Optional[str] = Field(default=None, description="草稿文案")
    writing_meta: Optional[dict[str, Any]] = Field(
        default=None, description="写作节点元信息（解析模式/长度等）"
    )
    iteration_count: int = Field(default=0, description="迭代次数")
    intent_result: Optional[dict[str, Any]] = Field(
        default=None, description="意图分析结果"
    )
    breakdown_result: Optional[dict[str, Any]] = Field(
        default=None, description="文案拆解结果"
    )
    schema_ir: Optional[dict[str, Any]] = Field(
        default=None, description="Ten-move schema IR（填充后）"
    )
    # v2 artifacts (optional)
    preprocess_result: Optional[dict[str, Any]] = Field(default=None, description="v2 预处理产物")
    skeleton_v2: Optional[dict[str, Any]] = Field(default=None, description="v2 Skeleton IR（标准化后）")
    entity_mapping: Optional[dict[str, Any]] = Field(default=None, description="v2 实体槽位映射结果")
    qc_report: Optional[dict[str, Any]] = Field(default=None, description="v2 质检报告（用于回放/返工）")
    analysis_report: Optional[str] = Field(
        default=None, description="口播向结构分析报告"
    )
    reverse_config: Optional[dict[str, Any]] = Field(
        default=None, description="逆向工程产出（隐藏配置 JSON）"
    )
    move_plan: Optional[dict[str, Any]] = Field(
        default=None, description="动态 move 规划产出（用于解释本次结构选择）"
    )
    verification_result: Optional[dict[str, Any]] = Field(
        default=None, description="规则验收结果（用于控制迭代与解释失败原因）"
    )
    proofread_result: Optional[dict[str, Any]] = Field(
        default=None, description="评测结果"
    )
    artifact_paths: Optional[dict[str, Any]] = Field(
        default=None, description="落盘的产物路径"
    )
    error: Optional[str] = Field(default=None, description="错误信息")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(default="ok")
    version: str = Field(default="0.1.0")


class StreamEvent(BaseModel):
    """流式事件"""

    type: str = Field(description="事件类型: node_start, node_end, token, done, error")
    node: Optional[str] = Field(default=None, description="节点名称")
    content: Optional[str] = Field(default=None, description="token 内容")
    output: Optional[dict[str, Any]] = Field(default=None, description="节点输出")
    error: Optional[str] = Field(default=None, description="错误信息")


# ============================================================================
# 小说生成 API 模型
# ============================================================================


class NovelGenerationRequest(BaseModel):
    """小说/短故事生成请求"""

    model_config = {"str_strip_whitespace": True}

    user_input: str = Field(
        ...,
        min_length=5,
        description="故事概念或主题（e.g., '关于失去和重新开始的故事'）",
    )
    reference_novel_title: str = Field(
        ...,
        min_length=1,
        description="参考小说名称（e.g., '诡秘之主'）",
    )
    user_style: Optional[str] = Field(
        default=None,
        description="可选：故事风格要求（e.g., '温暖、治愈', '冒险、奇幻'）",
    )
    target_chapters: int = Field(
        default=5,
        ge=1,
        le=50,
        description="目标章数（默认5章，最多50章）",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="会话 ID（用于记忆和追踪）",
    )


class NovelGenerationResponse(BaseModel):
    """小说/短故事生成响应"""

    success: bool = Field(default=True, description="是否成功")
    story_title: Optional[str] = Field(default=None, description="生成的故事标题")
    final_story: Optional[str] = Field(default=None, description="最终的完整故事")
    chapters_count: int = Field(default=0, description="实际生成的章数")
    iterations: int = Field(default=0, description="总迭代次数")
    move_codebook: Optional[dict[str, Any]] = Field(
        default=None, description="提取的 Move Codebook"
    )
    story_ir: Optional[dict[str, Any]] = Field(
        default=None, description="故事规划 IR（中间表示）"
    )
    error: Optional[str] = Field(default=None, description="错误信息")


class ChatRequest(BaseModel):
    """对话请求（用于配置下发）"""

    model_config = {"str_strip_whitespace": True}

    user_input: str = Field(
        ...,
        min_length=1,
        description="用户输入的创作需求",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="会话线程 ID",
    )


class ConfigSubmitRequest(BaseModel):
    """配置表单提交请求"""

    model_config = {"str_strip_whitespace": True}

    thread_id: str = Field(
        ...,
        description="会话线程 ID",
    )
    user_input: str = Field(
        ...,
        min_length=1,
        description="用户原始输入",
    )
    selections: dict[str, str] = Field(
        ...,
        description="用户选择的配置项，如 {'target_duration': '30', 'ratio': '16:9', 'style': 'anime'}",
    )


class NovelStreamEvent(BaseModel):
    """小说生成流式事件"""

    type: str = Field(
        description="事件类型: node_start, node_end, progress, token, done, error"
    )
    node: Optional[str] = Field(default=None, description="节点名称")
    chapter: Optional[int] = Field(default=None, description="章节号（progress 事件用）")
    text_snippet: Optional[str] = Field(
        default=None, description="文本片段预览（progress 事件用）"
    )
    content: Optional[str] = Field(default=None, description="token 内容（token 事件用）")
    error: Optional[str] = Field(default=None, description="错误信息")
