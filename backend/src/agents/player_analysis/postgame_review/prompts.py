"""
Postgame Review Prompts
赛后复盘 Agent 的 Prompt 模板
"""

from typing import Dict, Any
import json


def build_narrative_prompt(review: Dict[str, Any]) -> str:
    """
    构建LLM增强叙述的Prompt

    Args:
        review: 规则引擎生成的诊断结果

    Returns:
        完整的LLM提示词
    """
    issues_summary = {
        '对线期': review['lane_phase']['issues'],
        '目标控制': review['objective_phase']['issues'],
        '出装节奏': review['build_timing']['issues'],
        '团战表现': review['teamfight']['issues']
    }

    prompt = f"""你是一名资深的英雄联盟教练。基于以下量化诊断结果，为玩家生成一份简洁、专业的赛后复盘报告。

**比赛基本信息**:
- 英雄: {review['champion']} ({review['role']})
- 结果: {review['result']}
- 时长: {review['game_duration'] // 60}分{review['game_duration'] % 60}秒
- 综合评分: {review['overall_score']['grade']} ({review['overall_score']['score']}分)

**诊断问题汇总**:
{json.dumps(issues_summary, indent=2, ensure_ascii=False)}

**要求**:
1. 用2-3句话总结本局表现（突出优势和核心问题）
2. 针对每个维度的问题，给出1-2条具体改进建议
3. 语气专业但不苛刻，鼓励性和建设性相结合
4. 总字数控制在300-500字

请直接输出复盘报告，不需要额外的标题或格式。
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
