"""小说生成 Agent 状态定义"""

from typing import TypedDict, Optional, Annotated, Union
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class NovelAgentState(TypedDict):
    """小说生成 Agent 状态 - 最小化实用版本"""

    # ============ 用户输入 ============
    user_input: str  # 故事概念，e.g. "关于失去和重新开始"
    user_style: Optional[str]  # 可选的风格要求
    target_chapters: int  # 目标章数，默认 5

    # ============ 参考数据 (从 SQLite 加载) ============
    reference_novel_title: str  # 参考小说的名称，e.g. "诡秘之主"
    reference_novel_data: Optional[dict]  # 参考小说的完整内容

    # ============ Move 和 IR (LLM 生成) ============
    move_codebook: Optional[dict]  # 从参考小说提取的 Move 结构
    move_codebook_id: Optional[str]  # Move Codebook 数据库 ID

    story_ir: Optional[dict]  # 新故事的 IR（规划）
    story_ir_id: Optional[str]  # Story IR 数据库 ID

    # ============ 生成进度 ============
    current_chapter: int  # 当前在生成第几章 (1-indexed)
    chapters_completed: int  # 已完成的章数

    # ============ 已生成内容 ============
    chapter_texts: list[str]  # [chapter_1_text, chapter_2_text, ...]

    # ============ 当前章节 ============
    current_chapter_text: Optional[str]  # 当前生成的章节文本
    fluency_check: Optional[dict]  # 通顺性检查结果

    # ============ 元数据 ============
    iteration_count: int  # 总迭代次数
    chapter_iterations: int  # 当前章节的迭代次数
    messages: Annotated[list[BaseMessage], add_messages]  # 对话历史
    error: Optional[str]  # 错误信息

    # ============ 最终输出 ============
    final_story: Optional[str]  # 完整的生成故事
