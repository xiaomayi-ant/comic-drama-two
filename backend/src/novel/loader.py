"""从 SQLite 数据库加载小说数据"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# 数据库路径
QIDIAN_DB_PATH = "/Users/sumoer/Desktop/playbook/qidian-spider/novels.db"


def load_novel_from_qidian(novel_title: str) -> Optional[Dict]:
    """
    从 qidian-spider 数据库加载完整小说

    Args:
        novel_title: 小说名称，e.g. "诡秘之主"

    Returns:
        {
            "title": "诡秘之主",
            "author": "宁宁",
            "chapters": [
                {
                    "chapter_num": 1,
                    "chapter_name": "诡秘侵袭",
                    "content": "..."
                },
                ...
            ]
        }
        如果小说不存在，返回 None
    """

    db_path = Path(QIDIAN_DB_PATH)

    # 验证数据库文件存在
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {QIDIAN_DB_PATH}")
        raise FileNotFoundError(f"SQLite 数据库不存在: {QIDIAN_DB_PATH}")

    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # 使用 Row 对象便于访问列名
        cursor = conn.cursor()

        # 首先查询小说信息
        cursor.execute(
            """
            SELECT id, name, author
            FROM books
            WHERE name = ?
            LIMIT 1
            """,
            (novel_title,)
        )

        book_row = cursor.fetchone()

        if not book_row:
            logger.warning(f"小说不存在: {novel_title}")
            conn.close()
            return None

        book_id = book_row["id"]
        book_title = book_row["name"]
        book_author = book_row["author"]

        logger.info(f"找到小说: {book_title} (作者: {book_author})")

        # 查询所有章节
        cursor.execute(
            """
            SELECT chapter_num, chapter_name, content
            FROM chapters
            WHERE book_id = ?
            ORDER BY chapter_num
            """,
            (book_id,)
        )

        chapters = []
        for row in cursor.fetchall():
            chapter = {
                "chapter_num": row["chapter_num"],
                "chapter_name": row["chapter_name"],
                "content": row["content"]
            }
            chapters.append(chapter)

        logger.info(f"加载了 {len(chapters)} 个章节")

        conn.close()

        # 组织返回数据
        result = {
            "title": book_title,
            "author": book_author,
            "chapters": chapters
        }

        return result

    except sqlite3.Error as e:
        logger.error(f"数据库查询错误: {e}")
        raise
    except Exception as e:
        logger.error(f"加载小说时出错: {e}")
        raise


def list_available_novels() -> List[str]:
    """
    列出数据库中所有可用的小说名称

    Returns:
        小说名称列表
    """

    db_path = Path(QIDIAN_DB_PATH)

    if not db_path.exists():
        logger.error(f"数据库文件不存在: {QIDIAN_DB_PATH}")
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM books ORDER BY name")

        novels = [row["name"] for row in cursor.fetchall()]

        conn.close()

        logger.info(f"数据库中有 {len(novels)} 部小说")

        return novels

    except sqlite3.Error as e:
        logger.error(f"数据库查询错误: {e}")
        return []
    except Exception as e:
        logger.error(f"列出小说时出错: {e}")
        return []


def get_novel_info(novel_title: str) -> Optional[Dict]:
    """
    获取小说的基本信息（不加载内容，性能更好）

    Returns:
        {
            "title": "...",
            "author": "...",
            "chapter_count": 100,
            "total_words": 500000
        }
    """

    db_path = Path(QIDIAN_DB_PATH)

    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT b.id, b.name, b.author,
                   COUNT(c.id) as chapter_count,
                   COALESCE(SUM(LENGTH(c.content)), 0) as total_words
            FROM books b
            LEFT JOIN chapters c ON b.id = c.book_id
            WHERE b.name = ?
            GROUP BY b.id
            """,
            (novel_title,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "title": row["name"],
            "author": row["author"],
            "chapter_count": row["chapter_count"],
            "total_words": row["total_words"]
        }

    except Exception as e:
        logger.error(f"获取小说信息时出错: {e}")
        return None


# 快速测试
if __name__ == "__main__":
    import sys
    from src.core.logger import setup_logger

    test_logger = setup_logger("loader.test", log_level="DEBUG")

    novels = list_available_novels()
    test_logger.info("=== 可用的小说 ===")
    for novel in novels[:5]:
        test_logger.info("  - %s", novel)
    if len(novels) > 5:
        test_logger.info("  ... 和其他 %d 部小说", len(novels) - 5)

    if novels:
        test_novel = novels[0]
        test_logger.info("=== 尝试加载: %s ===", test_novel)

        info = get_novel_info(test_novel)
        if info:
            test_logger.info("标题: %s", info['title'])
            test_logger.info("作者: %s", info['author'])
            test_logger.info("章数: %d", info['chapter_count'])
            test_logger.info("总字数: %d", info['total_words'])

        data = load_novel_from_qidian(test_novel)
        if data:
            test_logger.info("成功加载小说: %s, 章节数: %d", data['title'], len(data['chapters']))
            if data['chapters']:
                first_chapter = data['chapters'][0]
                test_logger.info("第一章: %s, 内容长度: %d 字", first_chapter['chapter_name'], len(first_chapter['content']))
        else:
            test_logger.error("无法加载小说")
