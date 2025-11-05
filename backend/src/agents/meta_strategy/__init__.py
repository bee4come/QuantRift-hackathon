"""
MetaStrategyAgent - 元策略调度Agent

全局调度中枢，负责：
- 解析用户复杂请求
- 制定最优分析策略
- 协调多个专项Agent执行
- 综合多源分析结果
- 生成统一输出报告
- Agent间消息传递和上下文共享
"""

from .agent import MetaStrategyAgent, create_meta_strategy_agent
from .context import AgentContext, format_context_for_prompt

__all__ = [
    "MetaStrategyAgent",
    "create_meta_strategy_agent",
    "AgentContext",
    "format_context_for_prompt"
]
