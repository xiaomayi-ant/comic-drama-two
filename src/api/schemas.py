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
