"""
文案写作助手 Agent - 项目入口

使用方式:
    # 命令行测试
    python main.py
    
    # 启动 API 服务
    python main.py --serve
"""

import argparse
import sys

from src.core.config import load_settings
from src.core.logger import get_logger

# 加载配置（确保环境变量设置）
settings = load_settings()
logger = get_logger(__name__)


def test_agent():
    """本地测试 Agent 功能"""
    from src.agent.graph import run_agent
    
    logger.info("=" * 50)
    logger.info("文案写作助手 Agent 测试")
    logger.info("=" * 50)
    
    # 测试用例：一段参考文案
    test_input = """
    你有没有发现，现在做内容越来越难了？
    辛辛苦苦写的文案，发出去没人看；
    精心策划的选题，数据惨不忍睹。
    
    其实问题不在于你不够努力，
    而是你还在用"写作文"的方式写文案。
    
    口播文案的核心是什么？是"说"，不是"写"。
    让人听得懂、愿意听、听完想行动。
    
    今天我就分享一个简单的框架，
    帮你把文案变成真正能说的话。
    想学的扣1，我私发你。
    """
    
    test_instructions = "请帮我仿写一段类似风格的口播文案，主题是AI工具提效"
    
    logger.info(f"输入文案:\n{test_input}")
    logger.info(f"写作指令: {test_instructions}")
    logger.info("-" * 50)
    
    # 运行 Agent
    result = run_agent(
        user_input=test_input,
        user_instructions=test_instructions,
        thread_id="test-001",
    )
    
    if result["success"]:
        logger.info("✅ Agent 执行成功")
        logger.info(f"迭代次数: {result['iteration_count']}")
        
        # 显示意图分析结果
        if result.get("intent_result"):
            ir = result["intent_result"]
            logger.info("-" * 50)
            logger.info(f"【意图分析】类型: {ir.get('intent')}, 置信度: {ir.get('confidence')}")
            logger.info(f"【意图理由】{ir.get('reasoning')}")
        
        logger.info("-" * 50)
        logger.info("【最终文案】")
        logger.info(result["final_copy"])
        
        if result.get("proofread_result"):
            pr = result["proofread_result"]
            logger.info("-" * 50)
            logger.info(f"【评测结果】通过: {pr.get('is_passed')}, 评分: {pr.get('quality_score')}")
            logger.info(f"【评测反馈】{pr.get('feedback')}")
    else:
        logger.error(f"❌ Agent 执行失败: {result.get('error')}")
    
    return result


def test_chat():
    """测试简单聊天功能"""
    from src.agent.graph import run_agent
    
    logger.info("=" * 50)
    logger.info("简单聊天测试")
    logger.info("=" * 50)
    
    test_input = "你好，请问什么是口播文案？"
    
    logger.info(f"用户输入: {test_input}")
    logger.info("-" * 50)
    
    result = run_agent(
        user_input=test_input,
        thread_id="chat-001",
    )
    
    if result["success"]:
        logger.info("✅ 聊天回复成功")
        if result.get("intent_result"):
            logger.info(f"【意图】{result['intent_result'].get('intent')}")
        logger.info(f"【回复】{result['final_copy']}")
    else:
        logger.error(f"❌ 聊天失败: {result.get('error')}")
    
    return result


def test_analysis():
    """测试文案分析功能"""
    from src.agent.graph import run_agent
    
    logger.info("=" * 50)
    logger.info("文案分析测试")
    logger.info("=" * 50)
    
    test_input = """
    你有没有发现，现在做内容越来越难了？
    辛辛苦苦写的文案，发出去没人看；
    精心策划的选题，数据惨不忍睹。
    """
    
    test_instructions = "帮我分析一下这段文案的结构"
    
    logger.info(f"输入文案:\n{test_input}")
    logger.info(f"指令: {test_instructions}")
    logger.info("-" * 50)
    
    result = run_agent(
        user_input=test_input,
        user_instructions=test_instructions,
        thread_id="analysis-001",
    )
    
    if result["success"]:
        logger.info("✅ 分析成功")
        if result.get("intent_result"):
            logger.info(f"【意图】{result['intent_result'].get('intent')}")
        logger.info(f"【分析结果】\n{result['final_copy']}")
    else:
        logger.error(f"❌ 分析失败: {result.get('error')}")
    
    return result


def start_server():
    """启动 FastAPI 服务"""
    import uvicorn
    from src.api.server import app
    
    logger.info(f"启动 API 服务: {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="文案写作助手 Agent")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="启动 FastAPI 服务",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="运行文案创作测试",
    )
    parser.add_argument(
        "--test-chat",
        action="store_true",
        help="运行聊天测试",
    )
    parser.add_argument(
        "--test-analysis",
        action="store_true",
        help="运行文案分析测试",
    )
    
    args = parser.parse_args()
    
    if args.serve:
        start_server()
    elif args.test_chat:
        test_chat()
    elif args.test_analysis:
        test_analysis()
    elif args.test:
        test_agent()
    else:
        # 默认运行所有测试
        test_agent()


if __name__ == "__main__":
    main()
