"""Agent 测试用例"""

import pytest

from src.agent.state import AgentState, BreakdownResult, ProofreadResult


class TestState:
    """状态模型测试"""

    def test_breakdown_result_default(self):
        """测试 BreakdownResult 默认值"""
        result = BreakdownResult()
        assert result.raw_json == {}
        assert result.is_valid_copy is False
        assert result.structure_type is None

    def test_proofread_result_validation(self):
        """测试 ProofreadResult 字段验证"""
        result = ProofreadResult(
            is_passed=True,
            feedback="good",
            quality_score=8.5,
        )
        assert result.is_passed is True
        assert result.quality_score == 8.5

    def test_proofread_score_bounds(self):
        """测试评分边界"""
        # 正常范围
        result = ProofreadResult(quality_score=10.0)
        assert result.quality_score == 10.0

        result = ProofreadResult(quality_score=0.0)
        assert result.quality_score == 0.0


class TestNodes:
    """节点逻辑测试（需要 API Key）"""

    @pytest.mark.skip(reason="需要配置 API Key")
    def test_breakdown_node(self):
        """测试解析节点"""
        from src.agent.nodes import breakdown_node

        state: AgentState = {
            "user_input": "这是一段测试文案",
            "user_instructions": None,
            "breakdown_result": None,
            "draft_copy": None,
            "proofread_result": None,
            "final_copy": None,
            "iteration_count": 0,
            "messages": [],
            "error": None,
        }

        result = breakdown_node(state)
        assert "breakdown_result" in result


class TestGraph:
    """工作流测试"""

    def test_create_graph(self):
        """测试创建工作流"""
        from src.agent.graph import create_agent_graph

        graph = create_agent_graph(with_memory=False)
        assert graph is not None

    def test_state_has_verification_result_key(self):
        """轻量约束：新链路应包含 verification_result 字段（用于规则验收门控）。"""
        from src.agent.state import AgentState

        # TypedDict 运行时不强校验，但我们至少确保类型注解层面存在该 key
        annotations = getattr(AgentState, "__annotations__", {})
        assert "verification_result" in annotations

