"""小说生成系统的 Prompt 模板"""

# ============================================================================
# Move 提取 Prompt
# ============================================================================

MOVE_EXTRACTION_PROMPT = """
你是一个故事结构分析师。分析以下小说，提取其底层的"Move"结构（叙述单元）。

【小说内容】
{novel_content}

【任务】
1. 将故事分解为 5-10 个"叙述单元"（Move），每个 Move 代表一个微观修辞意图
2. 对每个 Move 识别：
   - 名称（e.g., setup, introduce_character, create_conflict 等）
   - 描述（这个 Move 的作用是什么？）
   - 涉及的章节
   - 核心想法（1-2 句话说这部分讲什么）
   - 估计字数范围
   - 情感节奏（3-5 个词描述这部分的情感变化）

3. 识别整体的故事框架（三幕结构？英雄之旅？其他模式？）

4. 分析故事的节奏分配（开篇占多少、上升占多少、高潮占多少等）

【输出格式】（只输出 JSON，不要其他文字）
{{
    "moves": [
        {{
            "move_id": 1,
            "name": "setup",
            "description": "建立故事的世界和氛围",
            "chapters": [1],
            "core_idea": "在一个疲惫的清晨，主角开始了新的一天",
            "estimated_words": {{
                "min": 300,
                "max": 500
            }},
            "emotional_beats": ["calm", "quiet", "introspection"]
        }},
        {{
            "move_id": 2,
            "name": "introduce_character",
            "description": "引入一个改变故事的人物",
            "chapters": [2],
            "core_idea": "主角在便利店遇见了一个特殊的人",
            "estimated_words": {{
                "min": 400,
                "max": 600
            }},
            "emotional_beats": ["surprise", "curiosity", "intrigue"]
        }}
    ],
    "story_framework": "三幕结构：日常 → 相遇与冲突 → 变化与成长",
    "pacing": {{
        "setup": 0.15,
        "rising_action": 0.50,
        "climax": 0.20,
        "resolution": 0.15
    }}
}}
"""

# ============================================================================
# 故事规划 Prompt
# ============================================================================

STORY_PLAN_PROMPT = """
你是一位故事规划师。基于用户的故事概念和参考小说的 Move 结构，规划一个新故事。

【用户的故事概念】
{user_input}

【用户的风格要求】
{user_style}

【参考的 Move 结构】
{move_codebook}

【任务】
为这个故事规划 {target_chapters} 个章节。每个章节应该包括：
1. 章节标题
2. 核心想法（1-2 句话说这章的核心内容）
3. 建议字数（基于 Move 的估计字数）
4. 这章应该参考的 Move（从参考库选择 1-2 个）

【约束条件】
- 不要复制参考小说，要原创
- 尊重用户的风格要求
- 总字数应该在 {target_word_count} ± 20% 的范围

【输出格式】（只输出 JSON，不要其他文字）
{{
    "story_title": "新故事的标题",
    "story_concept": "故事的核心概念（1-2句话）",
    "chapters": [
        {{
            "chapter_id": 1,
            "title": "章节标题",
            "core_idea": "这章讲什么（1-2句话）",
            "target_word_count": 400,
            "reference_moves": ["setup"],
            "notes": "可选的生成提示"
        }},
        {{
            "chapter_id": 2,
            "title": "章节标题",
            "core_idea": "...",
            "target_word_count": 450,
            "reference_moves": ["introduce_character", "create_conflict"],
            "notes": ""
        }}
    ]
}}
"""

# ============================================================================
# 章节写作 Prompt
# ============================================================================

CHAPTER_WRITING_PROMPT = """
你是一位小说作家。基于章节规划和参考 Move 的叙述方式，写作这一章。

【故事信息】
标题：{story_title}
概念：{story_concept}
用户风格：{user_style}

【前文摘要】
{previous_context}

【本章规划】
标题：{chapter_title}
核心：{chapter_core_idea}
字数：{chapter_target_words}

【参考的 Move 模式】
{reference_moves_guide}

【写作要求】
1. 字数在 {chapter_target_words} ± 50 字
2. 语句要通顺自然，易于阅读
3. 与前文连贯一致（如果有前文）
4. 参考 Move 的叙述方式，但要原创表达，不要生硬套用
5. 保持故事的节奏和情感

【生成本章内容】

"""

# ============================================================================
# 通顺性检查 Prompt
# ============================================================================

FLUENCY_CHECK_PROMPT = """
你是一位文案编辑。检查以下文本的语句通顺性和表达质量。

【需要检查的文本】
{chapter_text}

【检查标准】
1. 语法错误（有吗？具体是什么？）
2. 表述生硬或不自然的地方（有吗？）
3. 逻辑不通的地方（有吗？）
4. 段落之间的衔接（流畅吗？）
5. 总体的可读性评分（1-10 分）

不需要检查：内容创意深度、细节完整性等。只关注"通顺性"。

【输出格式】（只输出 JSON，不要其他文字）
{{
    "is_fluent": true,
    "issues": [],
    "score": 8.5,
    "suggestions": "总体写得很流畅，保持这个水准。"
}}

或者：

{{
    "is_fluent": false,
    "issues": [
        "第2段'他走到便利店'之后突然切换到'她坐在椅子上'，主语转换没有过渡",
        "第4段'非常非常很'重复用词，建议改为'非常'"
    ],
    "score": 6.5,
    "suggestions": "建议调整主语转换，并精简重复词汇。"
}}
"""

# ============================================================================
# 辅助函数
# ============================================================================

def format_move_codebook_for_prompt(move_codebook: dict) -> str:
    """将 Move Codebook 格式化为可读的 Prompt 内容"""
    if not move_codebook or "moves" not in move_codebook:
        return "（无参考 Move 库）"

    result = []
    for move in move_codebook.get("moves", []):
        result.append(f"""
Move {move['move_id']}: {move['name']}
  - 描述: {move['description']}
  - 估计字数: {move['estimated_words']['min']}-{move['estimated_words']['max']}
  - 情感节奏: {', '.join(move['emotional_beats'])}
  - 核心想法: {move['core_idea']}
""")

    return "".join(result)


def format_reference_moves_for_prompt(move_names: list, move_codebook: dict) -> str:
    """将参考的 Move 列表格式化为 Prompt 内容"""
    if not move_codebook or "moves" not in move_codebook:
        return "（无参考 Move）"

    moves_dict = {m["name"]: m for m in move_codebook.get("moves", [])}

    result = []
    for move_name in move_names:
        if move_name in moves_dict:
            move = moves_dict[move_name]
            result.append(f"""
【{move_name}】
描述: {move['description']}
情感节奏: {', '.join(move['emotional_beats'])}
例子: {move['core_idea']}
建议字数: {move['estimated_words']['min']}-{move['estimated_words']['max']}
""")

    return "".join(result) if result else "（找不到对应的 Move）"
