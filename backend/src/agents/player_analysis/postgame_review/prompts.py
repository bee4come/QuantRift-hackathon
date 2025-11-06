"""
Postgame Review Prompts
赛后复盘 Agent 的 Prompt 模板
"""

from typing import Dict, Any
import json


def build_narrative_prompt(review: Dict[str, Any]) -> str:
    """
    Build LLM narrative prompt for post-game review

    Args:
        review: Diagnostic results from rule engine

    Returns:
        Complete LLM prompt
    """
    issues_summary = {
        'Laning Phase': review['lane_phase']['issues'],
        'Objective Control': review['objective_phase']['issues'],
        'Build Timing': review['build_timing']['issues'],
        'Teamfight Performance': review['teamfight']['issues']
    }

    prompt = f"""You are an experienced League of Legends coach. Based on the following quantitative diagnostic results, generate a concise and professional post-game review report for the player.

**Match Information**:
- Champion: {review['champion']} ({review['role']})
- Result: {review['result']}
- Duration: {review['game_duration'] // 60}m {review['game_duration'] % 60}s
- Overall Grade: {review['overall_score']['grade']} ({review['overall_score']['score']}/100)

**Diagnostic Issues Summary**:
{json.dumps(issues_summary, indent=2, ensure_ascii=False)}

**Requirements**:
1. Summarize the match performance in 2-3 sentences (highlight strengths and core issues)
2. For each dimension's issues, provide 1-2 specific improvement suggestions
3. Use professional but not harsh tone, combine encouragement with constructive feedback
4. Keep total word count between 300-500 words

Please output the review report directly without additional titles or formatting.
"""
    return prompt


def build_detailed_analysis_prompt(review: Dict[str, Any]) -> str:
    """
    构建详细分析Prompt（用于更深入的LLM分析）

    Args:
        review: 规则引擎生成的诊断结果

    Returns:
        详细分析的LLM提示词
    """
    lane_stats = review['lane_phase']
    objective_stats = review['objective_phase']
    build_stats = review['build_timing']
    teamfight_stats = review['teamfight']

    prompt = f"""你是一名英雄联盟数据分析专家。基于以下量化诊断数据，生成一份详细的技术分析报告。

**比赛概览**:
- 英雄: {review['champion']} ({review['role']})
- 结果: {review['result']}
- 时长: {review['game_duration'] // 60}分{review['game_duration'] % 60}秒

**对线期数据**:
- CS@10: {lane_stats.get('cs10', 'N/A')}
- Gold@10: {lane_stats.get('gold10', 'N/A')}
- 发现问题: {len(lane_stats['issues'])}个

**目标控制数据**:
- 视野数: {objective_stats.get('wards_placed', 'N/A')}
- 目标参与: {objective_stats.get('obj_participation', 'N/A')}
- 发现问题: {len(objective_stats['issues'])}个

**出装数据**:
- 二件套时间: {build_stats.get('core2_time', 'N/A')}分钟
- 装备数量: {build_stats.get('items_count', 'N/A')}件
- 发现问题: {len(build_stats['issues'])}个

**团战数据**:
- KDA: {teamfight_stats.get('kda', 'N/A')}
- K/D/A: {teamfight_stats.get('kills', 0)}/{teamfight_stats.get('deaths', 0)}/{teamfight_stats.get('assists', 0)}
- 发现问题: {len(teamfight_stats['issues'])}个

**分析要求**:
1. 对每个维度进行深入的数据解读
2. 找出数据背后的根本原因（不仅仅是表面问题）
3. 提供可执行的改进方案，包括具体的游戏内操作建议
4. 根据英雄和位置特性，给出针对性的训练重点
5. 总字数控制在800-1200字

请以结构化的方式输出分析报告。
"""
    return prompt
