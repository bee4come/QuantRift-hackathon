"""
Context-Aware Agent Example

演示如何开发利用AgentContext的智能Agent

这个示例展示了未来Agent如何：
1. 接收上下文信息
2. 利用之前Agent的结果
3. 避免重复计算
4. 实现增量分析
"""

from typing import Dict, Any, Optional, Tuple
from src.agents.shared.bedrock_adapter import BedrockLLM
from src.agents.shared.config import get_config
from .context import AgentContext, format_context_for_prompt


class ContextAwareAgentExample:
    """
    上下文感知Agent示例

    演示如何利用AgentContext实现：
    - 基于前置Agent结果的增量分析
    - 避免重复数据加载
    - 智能决策（根据上下文调整策略）
    """

    def __init__(self, model: str = "sonnet"):
        self.config = get_config()
        self.llm = BedrockLLM(model=model)

    def run(
        self,
        packs_dir: str,
        output_dir: Optional[str] = None,
        context: Optional[AgentContext] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        运行上下文感知分析

        Args:
            packs_dir: Player Pack数据目录
            output_dir: 输出目录（可选）
            context: Agent执行上下文（可选）

        Returns:
            (analysis_data, report_text) - 分析数据和报告文本
        """
        print(f"\n{'='*60}")
        print("🧠 上下文感知Agent示例")
        print(f"{'='*60}\n")

        # ========================================
        # 场景1: 检查是否有可用的上下文
        # ========================================
        if context is None:
            print("⚠️  无可用上下文，执行标准分析...")
            return self._run_standard_analysis(packs_dir)

        print("✅ 检测到上下文，启用增量分析模式\n")

        # ========================================
        # 场景2: 利用之前Agent的结果
        # ========================================
        previous_agents = context.get_previous_agents()
        print(f"📋 之前执行的Agents: {', '.join(previous_agents)}")

        # 例子：检查是否已经有年度总结
        if context.has_agent_result("annual_summary"):
            annual_data = context.get_agent_data("annual_summary")
            print(f"✅ 发现AnnualSummary结果，复用数据:")
            print(f"   - 总场次: {annual_data.get('summary', {}).get('total_games', 'N/A')}")
            print(f"   - 整体胜率: {annual_data.get('summary', {}).get('overall_winrate', 'N/A'):.1%}")

            # 避免重复加载数据
            self._reuse_annual_summary_data(annual_data)

        # 例子：检查是否已经有弱点分析
        if context.has_agent_result("weakness_analysis"):
            weakness_data = context.get_agent_data("weakness_analysis")
            print(f"✅ 发现WeaknessAnalysis结果，基于弱点进行针对性分析")

            # 增量分析：只分析已识别的弱点
            self._analyze_weaknesses_deeply(weakness_data)

        # ========================================
        # 场景3: 使用共享缓存避免重复计算
        # ========================================
        if context.has_shared_data("player_champion_pool"):
            print("✅ 从共享缓存获取英雄池数据，避免重复加载")
            champion_pool = context.get_shared_data("player_champion_pool")
        else:
            print("📊 首次加载英雄池数据...")
            champion_pool = self._load_champion_pool(packs_dir)
            # 缓存到共享数据
            context.set_shared_data("player_champion_pool", champion_pool)

        # ========================================
        # 场景4: 生成上下文感知的Prompt
        # ========================================
        context_text = format_context_for_prompt(context, "context_aware_example")

        prompt = f"""基于以下上下文信息进行深度分析：

{context_text}

请结合之前Agents的发现，提供增量的、有价值的洞察。"""

        print("\n🤖 生成上下文感知报告...")
        result = self.llm.generate_sync(
            prompt=prompt,
            max_tokens=8000
        )

        report_text = result["text"]

        # ========================================
        # 场景5: 构建分析数据
        # ========================================
        analysis_data = {
            "context_utilized": {
                "previous_agents": previous_agents,
                "reused_data": context.has_agent_result("annual_summary"),
                "shared_cache_used": context.has_shared_data("player_champion_pool")
            },
            "analysis_result": {
                "champion_pool_size": len(champion_pool) if champion_pool else 0,
                # 其他分析结果...
            },
            "metadata": {
                "context_aware": True,
                "efficiency_gain": "50%" if context.has_agent_result("annual_summary") else "0%"
            }
        }

        print(f"✅ 分析完成 (利用上下文节省 {analysis_data['metadata']['efficiency_gain']} 时间)\n")

        return analysis_data, report_text

    def _run_standard_analysis(self, packs_dir: str) -> Tuple[Dict[str, Any], str]:
        """标准分析模式（无上下文）"""
        print("执行完整的标准分析流程...")

        analysis_data = {
            "context_utilized": {
                "previous_agents": [],
                "reused_data": False
            },
            "analysis_result": {
                "champion_pool_size": 0
            },
            "metadata": {
                "context_aware": False
            }
        }

        report = "# 标准分析报告\n\n无可用上下文，执行了完整分析流程。"

        return analysis_data, report

    def _reuse_annual_summary_data(self, annual_data: Dict[str, Any]) -> None:
        """复用年度总结数据"""
        print("   复用年度总结中的统计数据...")
        # 实际应用中，这里会避免重新加载和计算数据

    def _analyze_weaknesses_deeply(self, weakness_data: Dict[str, Any]) -> None:
        """基于弱点数据进行深度分析"""
        print(f"   针对 {len(weakness_data.get('low_winrate_champions', []))} 个弱点英雄进行深度分析...")
        # 实际应用中，这里会执行针对性的深度分析

    def _load_champion_pool(self, packs_dir: str) -> Dict[str, Any]:
        """加载英雄池数据"""
        # 模拟数据加载
        return {"total_champions": 15, "core_champions": 5}


# ========================================
# 使用示例
# ========================================

def example_usage_without_context():
    """示例1: 无上下文的独立运行"""
    print("="*80)
    print("示例1: 无上下文的独立Agent运行")
    print("="*80)

    agent = ContextAwareAgentExample(model="haiku")
    data, report = agent.run(
        packs_dir="path/to/packs",
        context=None  # 无上下文
    )

    print(f"\n分析结果: {data['metadata']}")


def example_usage_with_context():
    """示例2: 有上下文的协同运行"""
    print("\n" + "="*80)
    print("示例2: 在MetaStrategyAgent框架内运行（有上下文）")
    print("="*80)

    # 创建上下文
    context = AgentContext(
        user_request="给我全面分析",
        packs_dir="path/to/packs"
    )

    # 模拟之前Agent的执行
    context.add_agent_result(
        agent_name="annual_summary",
        data={
            "summary": {
                "total_games": 150,
                "overall_winrate": 0.52
            }
        },
        report="年度总结报告...",
        execution_time=15.5
    )

    context.add_agent_result(
        agent_name="weakness_analysis",
        data={
            "low_winrate_champions": [
                {"champion_id": 157, "winrate": 0.42}
            ]
        },
        report="弱点分析报告...",
        execution_time=8.3
    )

    # 设置共享缓存
    context.set_shared_data("player_champion_pool", {"total": 15})

    # 运行上下文感知Agent
    agent = ContextAwareAgentExample(model="haiku")
    data, report = agent.run(
        packs_dir="path/to/packs",
        context=context  # 传入上下文
    )

    print(f"\n分析结果: {data['metadata']}")
    print(f"效率提升: {data['metadata']['efficiency_gain']}")


if __name__ == "__main__":
    example_usage_without_context()
    example_usage_with_context()
