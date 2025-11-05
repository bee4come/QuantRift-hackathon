#!/usr/bin/env python3
"""
User-Mode治理前置检查器
在评分器之前强制执行治理红线，确保数据质量
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse

from .utils import (
    load_user_mode_config,
    apply_governance_tag,
    filter_by_governance,
    format_output_precision
)


class UserGovernanceChecker:
    """User-Mode治理检查器"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """初始化检查器"""
        self.config = load_user_mode_config(config_path)
        self.red_lines = self.config['governance']['red_lines']
        self.grading = self.config['governance']['evidence_grading']

    def check_governance(self, records: List[Dict[str, Any]],
                        current_patch: str = None) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        执行治理检查和分级

        Args:
            records: 输入记录列表
            current_patch: 当前patch（用于+1 buffer检查）

        Returns:
            (符合records, 被拒绝records, 检查报告)
        """
        print(f"🛡️ 开始治理检查，输入 {len(records)} 条记录")

        compliant_records = []
        rejected_records = []
        check_report = {
            'total_input': len(records),
            'passed_count': 0,
            'rejected_count': 0,
            'rejection_reasons': {},
            'grading_stats': {'CONFIDENT': 0, 'CAUTION': 0, 'CONTEXT': 0}
        }

        for record in records:
            # 执行红线检查
            passed, rejection_reason = self._check_red_lines(record, current_patch)

            if not passed:
                # 记录拒绝原因
                if rejection_reason not in check_report['rejection_reasons']:
                    check_report['rejection_reasons'][rejection_reason] = 0
                check_report['rejection_reasons'][rejection_reason] += 1

                rejected_records.append({
                    **record,
                    'rejection_reason': rejection_reason,
                    'governance_tag': 'REJECTED'
                })
                check_report['rejected_count'] += 1
                continue

            # 通过红线检查，进行证据分级
            governance_tag = apply_governance_tag(record, self.config)
            record['governance_tag'] = governance_tag

            compliant_records.append(record)
            check_report['passed_count'] += 1
            check_report['grading_stats'][governance_tag] += 1

        print(f"✅ 治理检查完成:")
        print(f"  通过: {check_report['passed_count']}")
        print(f"  拒绝: {check_report['rejected_count']}")
        print(f"  分级: {check_report['grading_stats']}")

        if check_report['rejection_reasons']:
            print(f"  拒绝原因: {check_report['rejection_reasons']}")

        return compliant_records, rejected_records, check_report

    def _check_red_lines(self, record: Dict[str, Any], current_patch: str = None) -> Tuple[bool, str]:
        """检查治理红线"""

        # 1. 检查coarse级别
        if self.red_lines['ban_coarse_evidence']:
            aggregation_level = record.get('aggregation_level', '')
            if 'coarse' in aggregation_level.lower():
                return False, "banned_coarse_level"

        # 2. 检查合成数据占比
        synthetic_share = record.get('synthetic_share', 0)
        if synthetic_share > self.red_lines['max_synthetic_share']:
            return False, f"synthetic_share_too_high_{synthetic_share:.3f}"

        # 3. 检查patch buffer（+1 patch防未来信息泄漏）
        if current_patch and self.red_lines['patch_buffer'] > 0:
            record_patch = record.get('patch_id', '')
            if self._is_future_patch(record_patch, current_patch):
                return False, f"future_patch_violation_{record_patch}_{current_patch}"

        # 4. 检查基本数据完整性
        required_fields = ['n', 'w', 'p_hat', 'ci']
        for field in required_fields:
            if field not in record or record[field] is None:
                return False, f"missing_field_{field}"

        # 5. 检查数值合理性
        n = record.get('n', 0)
        w = record.get('w', 0)
        p_hat = record.get('p_hat', 0)

        if n <= 0:
            return False, "invalid_sample_size"

        if w < 0 or w > n:
            return False, "invalid_win_count"

        if not (0 <= p_hat <= 1):
            return False, "invalid_probability"

        # 6. 检查CI合理性
        ci = record.get('ci', {})
        if not isinstance(ci, dict) or 'lo' not in ci or 'hi' not in ci:
            return False, "invalid_ci_format"

        ci_lo = ci.get('lo', 0)
        ci_hi = ci.get('hi', 1)

        if not (0 <= ci_lo <= ci_hi <= 1):
            return False, "invalid_ci_bounds"

        return True, ""

    def _is_future_patch(self, record_patch: str, current_patch: str) -> bool:
        """检查是否为未来patch（简单版本比较）"""
        try:
            # 简化的patch比较（假设格式为 "15.13.1"）
            record_parts = [int(x) for x in record_patch.split('.')]
            current_parts = [int(x) for x in current_patch.split('.')]

            # 比较主版本、次版本、修订版本
            for i in range(min(len(record_parts), len(current_parts))):
                if record_parts[i] > current_parts[i]:
                    return True
                elif record_parts[i] < current_parts[i]:
                    return False

            # 如果所有对比部分相等，较长版本号为新版本
            return len(record_parts) > len(current_parts)

        except (ValueError, AttributeError):
            # 无法解析版本号，谨慎起见认为是未来版本
            return True

    def filter_for_evidence(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤出可用作证据的记录（仅CONFIDENT和CAUTION）"""
        return filter_by_governance(records, allowed_tags=['CONFIDENT', 'CAUTION'], config=self.config)

    def filter_for_context(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤出仅用作上下文的记录（仅CONTEXT）"""
        return filter_by_governance(records, allowed_tags=['CONTEXT'], config=self.config)

    def generate_governance_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成治理汇总报告"""
        if not records:
            return {
                'total_records': 0,
                'governance_distribution': {},
                'quality_metrics': {},
                'compliance_rate': 0.0
            }

        df = pd.DataFrame(records)

        # 治理标签分布
        governance_dist = df['governance_tag'].value_counts().to_dict()

        # 质量指标
        confident_count = governance_dist.get('CONFIDENT', 0)
        caution_count = governance_dist.get('CAUTION', 0)
        context_count = governance_dist.get('CONTEXT', 0)
        evidence_count = confident_count + caution_count

        # 计算合规率
        total_count = len(df)
        compliance_rate = evidence_count / total_count if total_count > 0 else 0

        # 统计指标
        quality_metrics = {
            'evidence_count': evidence_count,
            'confident_ratio': confident_count / total_count if total_count > 0 else 0,
            'caution_ratio': caution_count / total_count if total_count > 0 else 0,
            'context_ratio': context_count / total_count if total_count > 0 else 0,
            'avg_sample_size': df['n'].mean() if 'n' in df.columns else 0,
            'avg_effective_n': df['effective_n'].mean() if 'effective_n' in df.columns else 0,
            'uses_prior_ratio': df['uses_prior'].mean() if 'uses_prior' in df.columns else 0
        }

        # 格式化输出
        for key, value in quality_metrics.items():
            if isinstance(value, float):
                quality_metrics[key] = format_output_precision(value, is_probability=True)

        summary = {
            'total_records': total_count,
            'governance_distribution': governance_dist,
            'quality_metrics': quality_metrics,
            'compliance_rate': format_output_precision(compliance_rate, is_probability=True)
        }

        return summary

    def save_governance_report(self, check_report: Dict[str, Any],
                              governance_summary: Dict[str, Any],
                              output_file: str = "data/user_mode/governance_report.json") -> str:
        """保存治理报告"""
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        combined_report = {
            'check_report': check_report,
            'governance_summary': governance_summary,
            'generated_at': pd.Timestamp.now().isoformat(),
            'config_summary': {
                'red_lines': self.red_lines,
                'grading_thresholds': self.grading
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_report, f, indent=2, ensure_ascii=False)

        print(f"📋 治理报告已保存: {output_file}")
        return str(output_file)


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="User-Mode治理检查")
    parser.add_argument("--input", required=True, help="输入记录文件")
    parser.add_argument("--output", default="data/user_mode", help="输出目录")
    parser.add_argument("--current-patch", help="当前patch（用于+1 buffer检查）")
    parser.add_argument("--evidence-only", action="store_true", help="仅输出证据级记录")
    args = parser.parse_args()

    # 加载数据
    print(f"📊 加载记录: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        if args.input.endswith('.jsonl'):
            records = [json.loads(line) for line in f if line.strip()]
        else:
            records = json.load(f)

    print(f"  发现 {len(records)} 条记录")

    # 执行治理检查
    checker = UserGovernanceChecker()
    compliant_records, rejected_records, check_report = checker.check_governance(
        records, args.current_patch
    )

    # 生成治理汇总
    governance_summary = checker.generate_governance_summary(compliant_records)

    # 保存结果
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存合规记录
    compliant_file = output_dir / "compliant_records.jsonl"
    with open(compliant_file, 'w', encoding='utf-8') as f:
        for record in compliant_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # 保存被拒绝记录
    rejected_file = output_dir / "rejected_records.jsonl"
    with open(rejected_file, 'w', encoding='utf-8') as f:
        for record in rejected_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # 保存治理报告
    report_file = checker.save_governance_report(check_report, governance_summary,
                                                output_dir / "governance_report.json")

    # 如果只要证据级记录
    if args.evidence_only:
        evidence_records = checker.filter_for_evidence(compliant_records)
        evidence_file = output_dir / "evidence_only.jsonl"
        with open(evidence_file, 'w', encoding='utf-8') as f:
            for record in evidence_records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"📋 证据记录: {len(evidence_records)} 条 → {evidence_file}")

    print(f"✅ 治理检查完成！")
    print(f"  合规记录: {len(compliant_records)} → {compliant_file}")
    print(f"  拒绝记录: {len(rejected_records)} → {rejected_file}")
    print(f"  治理报告: {report_file}")


if __name__ == "__main__":
    main()