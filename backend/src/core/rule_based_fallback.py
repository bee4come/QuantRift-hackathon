#!/usr/bin/env python3
"""
Rule-based降级模板生成器
当Bedrock异常或证据不足时的备用方案
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse

from .utils import (
    load_user_mode_config,
    format_output_precision,
    safe_float_convert,
    safe_int_convert
)


class RuleBasedFallback:
    """Rule-based降级系统"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """初始化降级系统"""
        self.config = load_user_mode_config(config_path)
        self.fallback_templates = self._load_fallback_templates()

    def _load_fallback_templates(self) -> Dict[str, Any]:
        """加载降级模板"""
        return {
            "observation_card": {
                "type": "observation_only",
                "title": "数据观察卡",
                "description": "基于现有证据的观察性分析，不提供行动建议",
                "min_evidence_threshold": 5,
                "sections": ["evidence_summary", "patterns", "data_gaps"]
            },
            "rule_based_card": {
                "type": "rule_based_advice",
                "title": "基础教练卡",
                "description": "基于规则和CONFIDENT证据的基础建议",
                "min_confident_threshold": 2,
                "sections": ["strengths", "improvements", "evidence_citations"]
            },
            "insufficient_data_card": {
                "type": "insufficient_data",
                "title": "数据不足提示",
                "description": "指导用户如何获得更多有效数据",
                "sections": ["current_status", "requirements", "recommendations"]
            }
        }

    def generate_fallback_card(self, evidence_records: List[Dict[str, Any]],
                              fallback_reason: str = "bedrock_failure") -> Dict[str, Any]:
        """
        生成降级卡片

        Args:
            evidence_records: 证据记录列表
            fallback_reason: 降级原因 (bedrock_failure, insufficient_evidence, cost_limit)

        Returns:
            降级卡片数据
        """
        print(f"🛡️ 触发降级: {fallback_reason}, 证据记录: {len(evidence_records)}")

        # 分析证据质量
        evidence_analysis = self._analyze_evidence_quality(evidence_records)

        # 选择降级策略
        fallback_strategy = self._select_fallback_strategy(evidence_analysis, fallback_reason)

        # 生成对应卡片
        if fallback_strategy == "insufficient_data":
            return self._generate_insufficient_data_card(evidence_analysis)
        elif fallback_strategy == "observation_only":
            return self._generate_observation_card(evidence_records, evidence_analysis)
        elif fallback_strategy == "rule_based":
            return self._generate_rule_based_card(evidence_records, evidence_analysis)
        else:
            return self._generate_error_card(fallback_reason)

    def _analyze_evidence_quality(self, evidence_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析证据质量"""
        if not evidence_records:
            return {
                "total_count": 0,
                "confident_count": 0,
                "caution_count": 0,
                "context_count": 0,
                "confident_ratio": 0.0,
                "avg_sample_size": 0,
                "coverage": {},
                "quality_level": "insufficient"
            }

        df = pd.DataFrame(evidence_records)

        # 治理标签统计
        governance_counts = df['governance_tag'].value_counts().to_dict()
        confident_count = governance_counts.get('CONFIDENT', 0)
        caution_count = governance_counts.get('CAUTION', 0)
        context_count = governance_counts.get('CONTEXT', 0)
        total_count = len(df)

        # 样本量统计
        avg_sample_size = df['n'].mean() if 'n' in df.columns else 0
        avg_effective_n = df['effective_n'].mean() if 'effective_n' in df.columns else 0

        # 覆盖度分析
        coverage = self._analyze_coverage(df)

        # 质量等级判定
        quality_level = self._determine_quality_level(confident_count, caution_count, total_count)

        return {
            "total_count": total_count,
            "confident_count": confident_count,
            "caution_count": caution_count,
            "context_count": context_count,
            "confident_ratio": confident_count / total_count if total_count > 0 else 0,
            "caution_ratio": caution_count / total_count if total_count > 0 else 0,
            "avg_sample_size": format_output_precision(avg_sample_size),
            "avg_effective_n": format_output_precision(avg_effective_n),
            "coverage": coverage,
            "quality_level": quality_level
        }

    def _analyze_coverage(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据覆盖度"""
        coverage = {
            "patch_coverage": [],
            "role_coverage": [],
            "champion_coverage": [],
            "queue_coverage": []
        }

        if 'patch_id' in df.columns:
            coverage["patch_coverage"] = df['patch_id'].unique().tolist()

        if 'role' in df.columns:
            coverage["role_coverage"] = df['role'].unique().tolist()

        if 'champion_id' in df.columns:
            coverage["champion_coverage"] = df['champion_id'].nunique()

        if 'queue' in df.columns:
            coverage["queue_coverage"] = df['queue'].unique().tolist()

        return coverage

    def _determine_quality_level(self, confident_count: int, caution_count: int, total_count: int) -> str:
        """判定证据质量等级"""
        if total_count < 5:
            return "insufficient"
        elif confident_count >= 10:
            return "high"
        elif confident_count >= 3 or (confident_count + caution_count) >= 8:
            return "medium"
        elif confident_count >= 1 or caution_count >= 3:
            return "low"
        else:
            return "insufficient"

    def _select_fallback_strategy(self, evidence_analysis: Dict[str, Any],
                                 fallback_reason: str) -> str:
        """选择降级策略"""
        quality_level = evidence_analysis["quality_level"]
        confident_count = evidence_analysis["confident_count"]
        total_count = evidence_analysis["total_count"]

        # 证据不足 -> 数据不足卡
        if quality_level == "insufficient" or total_count < 5:
            return "insufficient_data"

        # 有足够CONFIDENT证据 -> Rule-based建议
        elif confident_count >= 2 and quality_level in ["high", "medium"]:
            return "rule_based"

        # 证据质量一般 -> 观察卡
        else:
            return "observation_only"

    def _generate_insufficient_data_card(self, evidence_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成数据不足卡片"""
        current_count = evidence_analysis["total_count"]
        confident_count = evidence_analysis["confident_count"]

        # 计算缺口
        min_total_needed = 20
        min_confident_needed = 3

        total_gap = max(0, min_total_needed - current_count)
        confident_gap = max(0, min_confident_needed - confident_count)

        return {
            "card_type": "insufficient_data",
            "status": "data_insufficient",
            "title": "数据积累中 - 继续比赛获得更准确分析",
            "summary": f"当前数据量不足以生成可靠的教练建议。已收集 {current_count} 条记录，需要更多比赛数据。",

            "current_status": {
                "total_matches_analyzed": current_count,
                "confident_evidence": confident_count,
                "data_quality": evidence_analysis["quality_level"],
                "coverage": evidence_analysis["coverage"]
            },

            "requirements": {
                "total_matches_needed": min_total_needed,
                "confident_evidence_needed": min_confident_needed,
                "remaining_gap": {
                    "total_matches": total_gap,
                    "confident_evidence": confident_gap
                }
            },

            "recommendations": {
                "immediate_actions": [
                    f"继续进行排位赛，目标增加 {total_gap} 场比赛",
                    "专注于熟练英雄，提高胜率以获得更多CONFIDENT级证据",
                    "尽量避免尝试新英雄，保持表现稳定性"
                ],
                "data_quality_tips": [
                    "单英雄至少进行5场比赛才能获得可靠分析",
                    "每个位置至少需要3-5场比赛数据",
                    "连续几个patch的数据更有助于趋势分析"
                ],
                "estimated_time": self._estimate_completion_time(total_gap)
            },

            "next_analysis_threshold": {
                "matches": min_total_needed,
                "estimated_confident_evidence": self._estimate_confident_evidence(min_total_needed),
                "trigger_condition": "数据达到阈值后将自动触发完整分析"
            },

            "fallback_info": {
                "reason": "insufficient_evidence",
                "generated_at": datetime.utcnow().isoformat(),
                "version": "rule_based_v1.0"
            }
        }

    def _generate_observation_card(self, evidence_records: List[Dict[str, Any]],
                                  evidence_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成观察卡片"""

        # 提取关键观察
        observations = self._extract_key_observations(evidence_records)

        # 生成模式识别
        patterns = self._identify_patterns(evidence_records)

        return {
            "card_type": "observation_only",
            "status": "observation_mode",
            "title": "数据观察报告 - 模式识别分析",
            "summary": f"基于 {evidence_analysis['total_count']} 条证据的观察性分析。当前数据质量：{evidence_analysis['quality_level']}。",

            "evidence_summary": {
                "total_records": evidence_analysis["total_count"],
                "confident_evidence": evidence_analysis["confident_count"],
                "caution_evidence": evidence_analysis["caution_count"],
                "coverage_analysis": evidence_analysis["coverage"],
                "data_quality_metrics": {
                    "confident_ratio": format_output_precision(evidence_analysis["confident_ratio"], is_probability=True),
                    "avg_sample_size": evidence_analysis["avg_sample_size"],
                    "avg_effective_n": evidence_analysis["avg_effective_n"]
                }
            },

            "key_observations": observations,

            "identified_patterns": patterns,

            "data_gaps": {
                "missing_coverage": self._identify_data_gaps(evidence_analysis["coverage"]),
                "low_confidence_areas": self._identify_low_confidence_areas(evidence_records),
                "recommendations_for_more_data": [
                    "增加样本量不足的英雄/位置组合的比赛",
                    "在当前patch继续积累数据以提高置信度",
                    "保持稳定表现以获得更多CONFIDENT级证据"
                ]
            },

            "limitations": {
                "why_no_advice": "当前证据质量不足以支持具体的行动建议",
                "confidence_threshold": "需要至少2条CONFIDENT级证据才能给出行动建议",
                "next_steps": "继续积累数据，达到阈值后将提供具体的改进建议"
            },

            "fallback_info": {
                "reason": "observation_only",
                "generated_at": datetime.utcnow().isoformat(),
                "version": "rule_based_v1.0"
            }
        }

    def _generate_rule_based_card(self, evidence_records: List[Dict[str, Any]],
                                 evidence_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成基于规则的教练卡片"""

        # 过滤出CONFIDENT证据
        confident_records = [r for r in evidence_records if r.get('governance_tag') == 'CONFIDENT']

        # 识别优势
        strengths = self._identify_rule_based_strengths(confident_records)

        # 识别改进点
        improvements = self._identify_rule_based_improvements(evidence_records)

        # 生成基础建议
        recommendations = self._generate_rule_based_recommendations(confident_records, improvements)

        return {
            "card_type": "rule_based_advice",
            "status": "basic_recommendations",
            "title": "基础教练建议 - 基于高置信度证据",
            "summary": f"基于 {len(confident_records)} 条CONFIDENT级证据生成的基础建议。",

            "evidence_foundation": {
                "confident_evidence_count": len(confident_records),
                "total_evidence_count": len(evidence_records),
                "confidence_ratio": format_output_precision(len(confident_records) / len(evidence_records), is_probability=True),
                "analysis_scope": evidence_analysis["coverage"]
            },

            "identified_strengths": strengths,

            "improvement_areas": improvements,

            "basic_recommendations": recommendations,

            "evidence_citations": self._generate_evidence_citations(confident_records),

            "limitations": {
                "scope": "基于规则生成，未使用AI深度分析",
                "evidence_requirement": "仅基于CONFIDENT级证据",
                "upgrade_condition": "Bedrock服务恢复后将提供更详细的AI分析"
            },

            "fallback_info": {
                "reason": "rule_based_fallback",
                "generated_at": datetime.utcnow().isoformat(),
                "version": "rule_based_v1.0",
                "ai_service_status": "degraded"
            }
        }

    def _extract_key_observations(self, evidence_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取关键观察"""
        observations = []

        if not evidence_records:
            return observations

        df = pd.DataFrame(evidence_records)

        # 胜率观察
        if 'p_hat' in df.columns:
            avg_winrate = df['p_hat'].mean()
            observations.append({
                "type": "winrate_analysis",
                "finding": f"平均胜率: {format_output_precision(avg_winrate, is_probability=True)}",
                "confidence": "medium",
                "details": {
                    "sample_size": len(df),
                    "range": f"{df['p_hat'].min():.3f} - {df['p_hat'].max():.3f}"
                }
            })

        # 角色分布观察
        if 'role' in df.columns:
            role_dist = df['role'].value_counts()
            primary_role = role_dist.index[0] if len(role_dist) > 0 else "unknown"
            observations.append({
                "type": "role_distribution",
                "finding": f"主要位置: {primary_role} ({role_dist.iloc[0]}场)",
                "confidence": "high",
                "details": role_dist.to_dict()
            })

        # 英雄多样性观察
        if 'champion_id' in df.columns:
            unique_champions = df['champion_id'].nunique()
            total_games = len(df)
            diversity_score = unique_champions / total_games
            observations.append({
                "type": "champion_diversity",
                "finding": f"英雄池多样性: {unique_champions}个英雄，多样性评分: {format_output_precision(diversity_score)}",
                "confidence": "high",
                "details": {
                    "unique_champions": unique_champions,
                    "total_games": total_games,
                    "diversity_score": diversity_score
                }
            })

        return observations

    def _identify_patterns(self, evidence_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别数据模式"""
        patterns = []

        if not evidence_records:
            return patterns

        df = pd.DataFrame(evidence_records)

        # CI宽度模式
        if 'ci' in df.columns:
            ci_widths = []
            for ci in df['ci']:
                if isinstance(ci, dict) and 'lo' in ci and 'hi' in ci:
                    width = ci['hi'] - ci['lo']
                    ci_widths.append(width)

            if ci_widths:
                avg_ci_width = sum(ci_widths) / len(ci_widths)
                patterns.append({
                    "type": "confidence_pattern",
                    "pattern": "置信区间宽度分析",
                    "finding": f"平均CI宽度: {format_output_precision(avg_ci_width)}",
                    "interpretation": "CI越窄表示估计越可靠" if avg_ci_width < 0.3 else "CI较宽，需要更多数据提高可靠性"
                })

        # Patch分布模式
        if 'patch_id' in df.columns:
            patch_dist = df['patch_id'].value_counts()
            patterns.append({
                "type": "temporal_pattern",
                "pattern": "版本分布",
                "finding": f"覆盖 {len(patch_dist)} 个版本，主要版本: {patch_dist.index[0]}",
                "interpretation": "多版本数据有助于识别英雄强度变化趋势"
            })

        return patterns

    def _identify_rule_based_strengths(self, confident_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于规则识别优势"""
        strengths = []

        if not confident_records:
            return strengths

        # 高胜率表现
        high_winrate_records = [r for r in confident_records if r.get('p_hat', 0) > 0.55]
        if high_winrate_records:
            avg_winrate = sum(r['p_hat'] for r in high_winrate_records) / len(high_winrate_records)
            strengths.append({
                "area": "高胜率表现",
                "description": f"{len(high_winrate_records)}个英雄/位置组合显示出优异表现",
                "metric": f"平均胜率: {format_output_precision(avg_winrate, is_probability=True)}",
                "supporting_evidence": len(high_winrate_records),
                "confidence": "high"
            })

        # 稳定性表现
        stable_records = [r for r in confident_records if r.get('ci', {}).get('hi', 1) - r.get('ci', {}).get('lo', 0) < 0.25]
        if stable_records:
            strengths.append({
                "area": "表现稳定性",
                "description": f"{len(stable_records)}个组合显示稳定的表现",
                "metric": "置信区间较窄，表现可预测",
                "supporting_evidence": len(stable_records),
                "confidence": "medium"
            })

        return strengths

    def _identify_rule_based_improvements(self, evidence_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于规则识别改进点"""
        improvements = []

        if not evidence_records:
            return improvements

        df = pd.DataFrame(evidence_records)

        # 低胜率区域
        low_winrate_records = df[df['p_hat'] < 0.45] if 'p_hat' in df.columns else pd.DataFrame()
        if not low_winrate_records.empty:
            improvements.append({
                "area": "胜率改进",
                "issue": f"{len(low_winrate_records)}个英雄/位置组合胜率偏低",
                "target_metric": "胜率 < 45%",
                "priority": "high",
                "evidence_count": len(low_winrate_records)
            })

        # 数据不足区域
        low_sample_records = df[df['n'] < 10] if 'n' in df.columns else pd.DataFrame()
        if not low_sample_records.empty:
            improvements.append({
                "area": "数据积累",
                "issue": f"{len(low_sample_records)}个组合样本量不足",
                "target_metric": "样本量 < 10",
                "priority": "medium",
                "evidence_count": len(low_sample_records)
            })

        return improvements

    def _generate_rule_based_recommendations(self, confident_records: List[Dict[str, Any]],
                                           improvements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成基于规则的建议"""
        recommendations = []

        # 优势放大建议
        if confident_records:
            high_winrate_records = [r for r in confident_records if r.get('p_hat', 0) > 0.55]
            if high_winrate_records:
                best_combo = max(high_winrate_records, key=lambda x: x.get('p_hat', 0))
                recommendations.append({
                    "type": "leverage_strength",
                    "priority": "high",
                    "title": "发挥优势组合",
                    "description": f"继续使用表现优异的英雄/位置组合",
                    "specific_action": f"优先选择 {best_combo.get('champion_id', 'unknown')} 在 {best_combo.get('role', 'unknown')} 位置",
                    "supporting_evidence": {
                        "row_id": best_combo.get('row_id', ''),
                        "winrate": format_output_precision(best_combo.get('p_hat', 0), is_probability=True),
                        "sample_size": best_combo.get('n', 0),
                        "confidence_level": "CONFIDENT"
                    }
                })

        # 改进建议
        for improvement in improvements[:2]:  # 只取前2个改进点
            if improvement["area"] == "胜率改进":
                recommendations.append({
                    "type": "improve_performance",
                    "priority": "medium",
                    "title": "改进低表现组合",
                    "description": "重点提升胜率偏低的英雄/位置组合",
                    "specific_action": "通过练习、观看回放或暂时避免使用这些组合",
                    "supporting_evidence": {
                        "affected_combinations": improvement["evidence_count"],
                        "threshold": "胜率 < 45%"
                    }
                })

        # 数据积累建议
        if any(imp["area"] == "数据积累" for imp in improvements):
            recommendations.append({
                "type": "data_collection",
                "priority": "low",
                "title": "增加数据样本",
                "description": "为样本量不足的组合增加更多比赛数据",
                "specific_action": "每个英雄/位置组合至少进行10场比赛以获得可靠分析",
                "supporting_evidence": {
                    "min_sample_requirement": 10,
                    "current_insufficient_combinations": sum(1 for imp in improvements if imp["area"] == "数据积累")
                }
            })

        return recommendations

    def _generate_evidence_citations(self, confident_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成证据引用"""
        citations = []

        for record in confident_records[:5]:  # 只显示前5条
            citation = {
                "row_id": record.get('row_id', ''),
                "champion_id": record.get('champion_id', 0),
                "role": record.get('role', ''),
                "patch_id": record.get('patch_id', ''),
                "sample_size": record.get('n', 0),
                "effective_n": format_output_precision(record.get('effective_n', 0)),
                "winrate": format_output_precision(record.get('p_hat', 0), is_probability=True),
                "confidence_interval": {
                    "lower": format_output_precision(record.get('ci', {}).get('lo', 0), is_probability=True),
                    "upper": format_output_precision(record.get('ci', {}).get('hi', 1), is_probability=True)
                },
                "uses_prior": record.get('uses_prior', False),
                "governance_tag": record.get('governance_tag', ''),
                "synthetic_share": format_output_precision(record.get('synthetic_share', 0), is_probability=True)
            }
            citations.append(citation)

        return citations

    def _generate_error_card(self, fallback_reason: str) -> Dict[str, Any]:
        """生成错误卡片"""
        return {
            "card_type": "error",
            "status": "system_error",
            "title": "服务暂时不可用",
            "summary": "分析服务遇到技术问题，请稍后重试。",
            "error_info": {
                "reason": fallback_reason,
                "timestamp": datetime.utcnow().isoformat(),
                "support_contact": "技术支持团队正在处理此问题"
            },
            "fallback_info": {
                "reason": "system_error",
                "generated_at": datetime.utcnow().isoformat(),
                "version": "rule_based_v1.0"
            }
        }

    def _identify_data_gaps(self, coverage: Dict[str, Any]) -> List[str]:
        """识别数据缺口"""
        gaps = []

        # 检查角色覆盖
        role_coverage = coverage.get("role_coverage", [])
        all_roles = ["top", "jungle", "mid", "adc", "support"]
        missing_roles = [role for role in all_roles if role not in role_coverage]
        if missing_roles:
            gaps.append(f"缺少位置数据: {', '.join(missing_roles)}")

        # 检查版本覆盖
        patch_coverage = coverage.get("patch_coverage", [])
        if len(patch_coverage) < 2:
            gaps.append("版本覆盖不足，建议涵盖多个patch数据")

        # 检查英雄多样性
        champion_count = coverage.get("champion_coverage", 0)
        if champion_count < 5:
            gaps.append(f"英雄池偏窄，仅有 {champion_count} 个英雄")

        return gaps

    def _identify_low_confidence_areas(self, evidence_records: List[Dict[str, Any]]) -> List[str]:
        """识别低置信度区域"""
        low_confidence_areas = []

        context_records = [r for r in evidence_records if r.get('governance_tag') == 'CONTEXT']
        if context_records:
            low_confidence_areas.append(f"{len(context_records)}条记录置信度较低（CONTEXT级）")

        wide_ci_records = [r for r in evidence_records
                          if isinstance(r.get('ci', {}), dict) and
                          (r['ci'].get('hi', 1) - r['ci'].get('lo', 0)) > 0.4]
        if wide_ci_records:
            low_confidence_areas.append(f"{len(wide_ci_records)}条记录置信区间过宽")

        return low_confidence_areas

    def _estimate_completion_time(self, remaining_matches: int) -> str:
        """估算完成时间"""
        if remaining_matches <= 0:
            return "数据已足够"
        elif remaining_matches <= 10:
            return "约1-2周（每天2-3场）"
        elif remaining_matches <= 30:
            return "约2-4周（每天2-3场）"
        else:
            return "约1-2个月（每天2-3场）"

    def _estimate_confident_evidence(self, total_matches: int) -> int:
        """估算可获得的CONFIDENT证据数"""
        # 基于经验：约30-40%的记录能达到CONFIDENT级
        return max(1, int(total_matches * 0.35))


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="Rule-based降级卡片生成")
    parser.add_argument("--input", required=True, help="输入证据文件")
    parser.add_argument("--output", default="data/user_mode", help="输出目录")
    parser.add_argument("--fallback-reason",
                       choices=["bedrock_failure", "insufficient_evidence", "cost_limit"],
                       default="bedrock_failure", help="降级原因")
    args = parser.parse_args()

    # 加载数据
    print(f"📊 加载证据记录: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        if args.input.endswith('.jsonl'):
            evidence_records = [json.loads(line) for line in f if line.strip()]
        else:
            evidence_records = json.load(f)

    print(f"  发现 {len(evidence_records)} 条证据记录")

    # 生成降级卡片
    fallback = RuleBasedFallback()
    fallback_card = fallback.generate_fallback_card(evidence_records, args.fallback_reason)

    # 保存结果
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    card_file = output_dir / f"fallback_card_{args.fallback_reason}.json"
    with open(card_file, 'w', encoding='utf-8') as f:
        json.dump(fallback_card, f, indent=2, ensure_ascii=False)

    print(f"✅ 降级卡片已生成: {card_file}")
    print(f"  卡片类型: {fallback_card['card_type']}")
    print(f"  状态: {fallback_card['status']}")


if __name__ == "__main__":
    main()