"""
MetaStrategyAgent - Core Tools
元策略Agent的核心工具函数
"""

import json
import re
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from .context import AgentContext


# Agent注册表 - 映射agent名称到对应的类
def get_agent_registry() -> Dict[str, Any]:
    """
    获取Agent注册表（仅包含可用的Agents）

    Returns:
        agent名称到类的映射字典
    """
    registry = {}

    # 尝试导入每个Agent，如果失败则跳过
    try:
        from src.agents.player_analysis.annual_summary import AnnualSummaryAgent
        registry["annual_summary"] = AnnualSummaryAgent
    except ImportError:
        pass

    try:
        from src.agents.player_analysis.weakness_analysis import WeaknessAnalysisAgent
        registry["weakness_analysis"] = WeaknessAnalysisAgent
    except ImportError:
        pass

    try:
        from src.agents.player_analysis.champion_recommendation import ChampionRecommendationAgent
        registry["champion_recommendation"] = ChampionRecommendationAgent
    except ImportError:
        pass

    try:
        from src.agents.player_analysis.role_specialization import RoleSpecializationAgent
        registry["role_specialization"] = RoleSpecializationAgent
    except ImportError:
        pass

    try:
        from src.agents.player_analysis.champion_mastery import ChampionMasteryAgent
        registry["champion_mastery"] = ChampionMasteryAgent
    except ImportError:
        pass

    # MultiVersionAgent直接从agent.py导入（未在__init__.py导出）
    try:
        from src.agents.player_analysis.multi_version.agent import MultiVersionAgent
        registry["multi_version"] = MultiVersionAgent
    except ImportError:
        pass

    return registry


def parse_request_classification(
    llm_response: str
) -> Dict[str, Any]:
    """
    解析LLM返回的请求分类结果

    Args:
        llm_response: LLM生成的文本

    Returns:
        分类结果字典
    """
    # 尝试提取JSON块
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试直接解析整个响应
    try:
        return json.loads(llm_response)
    except json.JSONDecodeError:
        pass

    # 回退方案：返回默认分类
    return {
        "request_type": "comprehensive_analysis",
        "confidence": 0.5,
        "focus_areas": ["overall"],
        "priority": "medium"
    }


def determine_agent_workflow(
    request_type: str,
    focus_areas: List[str],
    packs_dir: str
) -> Dict[str, Any]:
    """
    根据请求类型确定Agent工作流

    Args:
        request_type: 请求类型
        focus_areas: 关注领域
        packs_dir: Player Pack数据目录

    Returns:
        工作流配置字典
    """
    workflows = {
        "comprehensive_analysis": {
            "agents": [
                {"name": "annual_summary", "args": {"packs_dir": packs_dir}},
                {"name": "weakness_analysis", "args": {"packs_dir": packs_dir, "recent_count": 5}},
                {"name": "champion_recommendation", "args": {"packs_dir": packs_dir}}
            ],
            "execution_mode": "sequential"
        },

        "quick_diagnosis": {
            "agents": [
                {"name": "weakness_analysis", "args": {"packs_dir": packs_dir, "recent_count": 3}}
            ],
            "execution_mode": "sequential"
        },

        "champion_focus": {
            "agents": [
                {"name": "champion_recommendation", "args": {"packs_dir": packs_dir}}
            ],
            "execution_mode": "sequential"
        },

        "role_focus": {
            "agents": [],  # 需要从focus_areas中提取具体位置
            "execution_mode": "sequential"
        },

        "postgame_review": {
            "agents": [],  # 需要PostgameReviewAgent (未实现)
            "execution_mode": "sequential"
        },

        "comparison": {
            "agents": [],  # 需要PeerComparisonAgent (未完成)
            "execution_mode": "sequential"
        }
    }

    workflow = workflows.get(request_type, workflows["comprehensive_analysis"])

    # 处理role_focus特殊情况
    if request_type == "role_focus" and focus_areas:
        # 尝试从focus_areas中提取位置
        role_keywords = {
            "上单": "TOP", "TOP": "TOP",
            "打野": "JUNGLE", "JUNGLE": "JUNGLE",
            "中单": "MIDDLE", "MIDDLE": "MIDDLE", "MID": "MIDDLE",
            "下路": "BOTTOM", "BOTTOM": "BOTTOM", "ADC": "BOTTOM",
            "辅助": "SUPPORT", "SUPPORT": "SUPPORT"
        }

        for area in focus_areas:
            for keyword, role in role_keywords.items():
                if keyword in area.upper():
                    workflow["agents"].append({
                        "name": "role_specialization",
                        "args": {"role": role, "packs_dir": packs_dir}
                    })
                    break

    return workflow


def execute_agent_workflow(
    workflow: Dict[str, Any],
    agent_registry: Dict[str, Any],
    context: AgentContext,
    model: str = "haiku"
) -> Dict[str, Any]:
    """
    执行Agent工作流（支持上下文传递）

    Args:
        workflow: 工作流配置
        agent_registry: Agent注册表
        context: Agent执行上下文
        model: 使用的LLM模型

    Returns:
        各Agent的执行结果
    """
    results = {}
    execution_mode = workflow.get("execution_mode", "sequential")

    if execution_mode == "sequential":
        for agent_config in workflow.get("agents", []):
            agent_name = agent_config["name"]
            agent_args = agent_config.get("args", {})

            if agent_name not in agent_registry:
                print(f"⚠️  Agent '{agent_name}' 未在注册表中")
                continue

            try:
                # 实例化Agent
                agent_class = agent_registry[agent_name]
                agent = agent_class(model=model)

                # 执行Agent（记录执行时间）
                print(f"\n🎯 执行 {agent_name}...")
                start_time = time.time()

                result = agent.run(**agent_args)
                execution_time = time.time() - start_time

                # 解包结果
                if isinstance(result, tuple) and len(result) >= 2:
                    data, report = result[0], result[1]
                else:
                    data, report = result, str(result)

                # 添加到上下文
                context.add_agent_result(
                    agent_name=agent_name,
                    data=data,
                    report=report,
                    execution_time=execution_time
                )

                results[agent_name] = result

                print(f"✅ {agent_name} 完成 (耗时: {execution_time:.1f}秒)")

            except Exception as e:
                print(f"❌ Agent '{agent_name}' 执行失败: {e}")
                results[agent_name] = {"error": str(e)}

                # 添加错误到上下文
                context.add_agent_result(
                    agent_name=agent_name,
                    data={"error": str(e)},
                    report=f"Agent执行失败: {e}",
                    execution_time=0.0
                )

    # TODO: 实现并行执行模式
    elif execution_mode == "parallel":
        print("⚠️  并行执行模式尚未实现，回退到串行模式")
        return execute_agent_workflow(
            workflow={**workflow, "execution_mode": "sequential"},
            agent_registry=agent_registry,
            context=context,
            model=model
        )

    return results


def format_strategy_summary(
    request_type: str,
    agents_invoked: List[str],
    execution_mode: str
) -> str:
    """
    格式化策略摘要

    Args:
        request_type: 请求类型
        agents_invoked: 调用的Agent列表
        execution_mode: 执行模式

    Returns:
        格式化的摘要文本
    """
    type_names = {
        "comprehensive_analysis": "综合分析",
        "quick_diagnosis": "快速诊断",
        "champion_focus": "英雄相关分析",
        "role_focus": "位置专精分析",
        "postgame_review": "赛后复盘",
        "comparison": "对比分析"
    }

    mode_names = {
        "sequential": "串行执行",
        "parallel": "并行执行",
        "conditional": "条件执行"
    }

    lines = [
        f"**分析类型**: {type_names.get(request_type, request_type)}",
        f"**执行模式**: {mode_names.get(execution_mode, execution_mode)}",
        f"**调用Agent**: {', '.join(agents_invoked)}"
    ]

    return "\n".join(lines)
