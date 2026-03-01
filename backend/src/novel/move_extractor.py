"""从参考小说中提取 Move 结构"""

import json
import logging
import uuid
from typing import Dict, Optional, Tuple
from src.core.config import settings
from src.novel.prompts import MOVE_EXTRACTION_PROMPT
from src.core.logger import get_logger

logger = get_logger(__name__)


async def extract_moves_from_novel(novel_data: Dict) -> Optional[Tuple[Dict, uuid.UUID]]:
    """
    从参考小说中提取 Move 结构

    Args:
        novel_data: 小说数据，格式为
            {
                "title": "...",
                "author": "...",
                "chapters": [...]
            }

    Returns:
        (Move Codebook, codebook_id) 元组，失败时返回 None
    """

    logger.info("开始提取小说 '%s' 的 Move 结构", novel_data['title'])

    novel_title = novel_data.get("title", "未知")
    novel_author = novel_data.get("author", "未知")

    novel_content = prepare_novel_content_for_analysis(novel_data)

    prompt = MOVE_EXTRACTION_PROMPT.format(novel_content=novel_content)

    try:
        from src.script.nodes import get_llm

        llm = get_llm()

        logger.debug("调用 LLM 提取 Move 结构...")
        response = llm.invoke(prompt)

        try:
            response_text = response.content if hasattr(response, "content") else str(response)

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end]
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end]

            move_codebook = json.loads(response_text.strip())

            moves = move_codebook.get('moves', [])
            move_names = [m.get('name') for m in moves]
            logger.info("成功提取 %d 个 Move: %s", len(moves), move_names)
            logger.debug("故事框架: %s", move_codebook.get('story_framework'))
            logger.debug("节奏分配: %s", move_codebook.get('pacing'))
            for m in moves:
                logger.debug("  Move %d: %s - %s (情感: %s)", 
                    m.get('move_id'), m.get('name'), m.get('description'), m.get('emotional_beats'))

            codebook_id = _save_move_codebook(novel_title, novel_author, move_codebook)
            logger.info("Move Codebook 已存储到数据库: %s", codebook_id)

            return move_codebook, codebook_id

        except json.JSONDecodeError as e:
            logger.error("LLM 响应不是有效的 JSON: %s", e)
            logger.error("响应内容: %s", response_text[:500])
            return None, None

    except Exception as e:
        logger.error("提取 Move 时出错: %s", e)
        return None, None


def _save_move_codebook(novel_title: str, novel_author: str, codebook: dict) -> uuid.UUID:
    """保存 Move Codebook 到数据库"""
    try:
        from src.core.database import get_database, save_move_codebook
        db = get_database()
        session = db.get_session()
        try:
            codebook_id = save_move_codebook(session, novel_title, novel_author, codebook)
            logger.debug("Move Codebook 已保存: %s", codebook_id)
            return codebook_id
        finally:
            session.close()
    except Exception as e:
        logger.warning("保存 Move Codebook 失败: %s", e)
        return uuid.uuid4()


def prepare_novel_content_for_analysis(novel_data: Dict, max_length: int = 10000) -> str:
    """
    为分析准备小说内容

    Args:
        novel_data: 小说数据
        max_length: 最大字数（避免 token 过多）

    Returns:
        格式化的小说内容
    """

    result = f"《{novel_data['title']}》 - 作者: {novel_data['author']}\n\n"

    total_chars = 0

    for chapter in novel_data["chapters"]:
        chapter_header = f"【{chapter['chapter_name']}】\n"
        chapter_content = chapter.get("content", "")[:1000]  # 每章最多 1000 字

        chapter_text = chapter_header + chapter_content + "\n\n"

        if total_chars + len(chapter_text) > max_length:
            # 如果超过最大长度，补充省略号并停止
            result += "... (省略部分章节) ...\n"
            break

        result += chapter_text
        total_chars += len(chapter_text)

    return result


def validate_move_codebook(codebook: Dict) -> bool:
    """
    验证 Move Codebook 的格式是否正确

    Args:
        codebook: 要验证的 codebook

    Returns:
        是否有效
    """

    if not isinstance(codebook, dict):
        logger.error("Move Codebook 必须是字典类型")
        return False

    if "moves" not in codebook:
        logger.error("Move Codebook 缺少 'moves' 字段")
        return False

    if not isinstance(codebook["moves"], list):
        logger.error("Move Codebook 的 'moves' 必须是列表")
        return False

    if len(codebook["moves"]) == 0:
        logger.error("Move Codebook 的 'moves' 不能为空")
        return False

    # 验证每个 move 的必要字段
    required_fields = ["move_id", "name", "description"]
    for i, move in enumerate(codebook["moves"]):
        for field in required_fields:
            if field not in move:
                logger.error(f"Move {i} 缺少字段 '{field}'")
                return False

    logger.info(f"✅ Move Codebook 验证通过，包含 {len(codebook['moves'])} 个 Move")

    return True


# 快速测试
if __name__ == "__main__":
    import asyncio
    from src.novel.loader import load_novel_from_qidian
    from src.core.logger import setup_logger

    test_logger = setup_logger("move_extractor.test", log_level="DEBUG")

    async def test():
        novel_data = load_novel_from_qidian("诡秘之主")

        if not novel_data:
            test_logger.error("无法加载小说")
            return

        test_logger.info("成功加载小说: %s, 章数: %d", novel_data['title'], len(novel_data['chapters']))

        test_logger.info("开始提取 Move 结构...")
        codebook = await extract_moves_from_novel(novel_data)

        if codebook:
            moves = codebook.get('moves', [])
            test_logger.info("成功提取 Move: %d 个, 故事框架: %s", len(moves), codebook.get('story_framework', '未知'))

            test_logger.info("前两个 Move:")
            for move in moves[:2]:
                test_logger.info("  Move %d: %s", move['move_id'], move['name'])
                test_logger.info("    描述: %s", move['description'])
                test_logger.info("    情感: %s", ', '.join(move.get('emotional_beats', [])))
        else:
            test_logger.error("提取 Move 失败")

    asyncio.run(test())
