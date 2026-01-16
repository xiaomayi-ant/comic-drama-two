"""Agent 状态定义模块"""

from enum import Enum
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class IntentType(str, Enum):
    """用户意图类型"""
    COPY_WRITING = "copy_writing"      # 文案仿写/创作
    COPY_ANALYSIS = "copy_analysis"    # 文案分析
    SIMPLE_CHAT = "simple_chat"        # 普通聊天


class IntentResult(BaseModel):
    """意图分析结果模型"""

    model_config = {"frozen": False, "str_strip_whitespace": True}

    intent: IntentType = Field(
        default=IntentType.SIMPLE_CHAT,
        description="识别的意图类型"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="意图置信度"
    )
    extracted_topic: Optional[str] = Field(
        default=None,
        description="提取的主题/关键词"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="意图判断理由"
    )


class BreakdownResult(BaseModel):
    """文案拆解结果模型"""

    model_config = {"frozen": False, "str_strip_whitespace": True}

    raw_json: dict = Field(default_factory=dict, description="原始解析JSON")
    is_valid_copy: bool = Field(default=False, description="是否为有效文案结构")
    structure_type: Optional[str] = Field(default=None, description="识别的结构类型")
    summary: Optional[str] = Field(default=None, description="结构性原因总结")


class ProofreadResult(BaseModel):
    """评测结果模型"""

    model_config = {"frozen": False, "str_strip_whitespace": True}

    is_passed: bool = Field(default=False, description="是否通过评测")
    feedback: str = Field(default="", description="反馈建议")
    refined_copy: Optional[str] = Field(default=None, description="润色后的文案")
    quality_score: float = Field(default=0.0, ge=0.0, le=10.0, description="质量评分")


class AgentState(TypedDict):
    """
    Agent 工作流状态定义
    
    状态流转（仿写优先版本）:
    1. user_input → intent_analysis_node → intent_result
    2. 根据 intent 路由:
       - copy_writing: reverse_engineer(prior) → move_plan(projection) → writing → verify → proofread → (迭代或输出)
       - copy_analysis: breakdown → 直接输出分析结果
       - simple_chat: 直接 LLM 回复
    """

    # 用户原始输入
    user_input: str

    # 用户额外指令（可选，用于指导写作方向）
    user_instructions: Optional[str]

    # 意图分析结果
    intent_result: Optional[dict]

    # 解析节点输出 - 结构化分析结果
    breakdown_result: Optional[dict]

    # Ten-move schema IR（规划/中间层）
    schema_ir: Optional[dict]

    # 面向口播的分析报告（analysis chain）
    analysis_report: Optional[str]

    # 逆向工程输出（learning chain）
    reverse_config: Optional[dict]

    # Move 规划输出（dynamic planning）
    move_plan: Optional[dict]

    # 规则验收输出（deterministic verification）
    verification_result: Optional[dict]

    # 写作节点输出 - 生成的文案草稿
    draft_copy: Optional[str]

    # 写作节点元信息（解析模式/长度等）
    writing_meta: Optional[dict]

    # 评测节点输出 - 评测结果
    proofread_result: Optional[dict]

    # 最终输出文案
    final_copy: Optional[str]

    # 落盘的产物路径
    artifact_paths: Optional[dict]

    # 迭代计数器
    iteration_count: int

    # 对话历史（用于 memory）
    messages: Annotated[list[BaseMessage], add_messages]

    # 错误信息（用于异常处理）
    error: Optional[str]
