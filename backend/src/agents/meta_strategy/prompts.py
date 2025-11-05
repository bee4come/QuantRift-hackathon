"""
MetaStrategyAgent - Prompt Templates
元策略Agent的Prompt模板
"""

from typing import Dict, Any


def build_request_classification_prompt(user_request: str) -> Dict[str, str]:
    """
    构建请求分类Prompt

    Args:
        user_request: 用户原始请求

    Returns:
        包含system和user的prompt字典
    """
    system_prompt = """你是一个专业的用户意图分析专家，负责将用户的自然语言请求分类为预定义的分析类型。

请根据用户请求判断其属于以下哪种分析类型：

1. **comprehensive_analysis** (综合分析):
   - 触发词: "全面分析"、"整体评估"、"赛季总结"
   - 特征: 需要多维度全面了解玩家表现

2. **quick_diagnosis** (快速诊断):
   - 触发词: "问题在哪"、"最近怎么样"、"弱点"
   - 特征: 关注问题识别和近期表现

3. **champion_focus** (英雄相关):
   - 触发词: "某英雄掌握度"、"英雄池"、"推荐英雄"
   - 特征: 围绕英雄选择和精通度

4. **role_focus** (位置分析):
   - 触发词: "中单表现"、"打野水平"、"XX位置"
   - 特征: 聚焦特定位置的专精分析

5. **postgame_review** (赛后复盘):
   - 触发词: "刚才那局"、"复盘"、"上一场"
   - 特征: 单场比赛的详细分析

6. **comparison** (对比分析):
   - 触发词: "和xx比"、"同段位对比"
   - 特征: 与其他玩家或基准对比

请以JSON格式返回分类结果：
```json
{
    "request_type": "类型名称",
    "confidence": 0.0-1.0,
    "focus_areas": ["关键点1", "关键点2"],
    "priority": "high|medium|low"
}
```
"""

    user_prompt = f"""用户请求: {user_request}

请分析并分类该请求。"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }


def build_synthesis_prompt(
    user_request: str,
    strategy: Dict[str, Any],
    agent_results: Dict[str, Any]
) -> Dict[str, str]:
    """
    构建结果综合Prompt

    Args:
        user_request: 原始用户请求
        strategy: 执行策略信息
        agent_results: 各Agent的分析结果

    Returns:
        包含system和user的prompt字典
    """
    system_prompt = """你是一个专业的英雄联盟数据分析师和教练，负责综合多个专项分析结果，生成统一的、易于理解的报告。

你的任务是：
1. 整合来自不同Agent的分析结果
2. 识别关键洞察和行动建议
3. 生成结构化的综合报告
4. 确保报告专业、准确、可操作

报告应包含：
- **执行摘要**: 简明概括核心发现
- **关键洞察**: 从多个分析中提取的重要发现
- **综合建议**: 整合所有建议的行动计划
- **数据支撑**: 引用具体数据支持结论

使用Markdown格式，确保可读性和专业性。"""

    # 构建agent结果摘要
    results_summary = []
    for agent_name, result in agent_results.items():
        if isinstance(result, tuple) and len(result) >= 2:
            data, report = result[0], result[1]
            results_summary.append(f"## {agent_name}\n{report[:500]}...\n")
        else:
            results_summary.append(f"## {agent_name}\n{str(result)[:500]}...\n")

    user_prompt = f"""原始用户请求: {user_request}

执行策略: {strategy.get('request_type', 'unknown')}
调用的Agent: {', '.join(strategy.get('agents_invoked', []))}

各Agent分析结果:
{''.join(results_summary)}

请生成综合报告。"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }
