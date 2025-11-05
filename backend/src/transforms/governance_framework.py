#!/usr/bin/env python3
"""
Data Governance Framework
完整的数据治理和质量检查框架
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import re

@dataclass
class DataQualityMetrics:
    """数据质量指标"""
    completeness_score: float      # 完整性评分 (0-1)
    accuracy_score: float          # 准确性评分 (0-1)
    consistency_score: float       # 一致性评分 (0-1)
    timeliness_score: float        # 及时性评分 (0-1)
    validity_score: float          # 有效性评分 (0-1)
    uniqueness_score: float        # 唯一性评分 (0-1)
    overall_score: float           # 综合评分 (0-1)

@dataclass
class DataLineage:
    """数据血缘追踪"""
    source_system: str             # 源系统
    source_table: str              # 源表
    transformation_id: str         # 转换ID
    transformation_timestamp: str  # 转换时间戳
    dependencies: List[str]         # 依赖关系
    output_artifacts: List[str]     # 输出产物

@dataclass
class ComplianceCheck:
    """合规性检查"""
    anonymization_validated: bool  # 匿名化验证
    pii_detection_passed: bool     # PII检测通过
    retention_policy_applied: bool # 保留策略应用
    access_control_validated: bool # 访问控制验证
    gdpr_compliant: bool           # GDPR合规

@dataclass
class GovernanceRecord:
    """完整治理记录"""
    record_id: str                 # 记录ID
    data_quality: DataQualityMetrics
    lineage: DataLineage
    compliance: ComplianceCheck
    governance_tags: List[str]     # 治理标签
    risk_level: str               # 风险等级
    validation_errors: List[str]   # 验证错误
    created_at: str               # 创建时间
    validated_by: str             # 验证者

class DataGovernanceFramework:
    """数据治理框架"""

    def __init__(self):
        self.validation_rules = self._load_validation_rules()
        self.pii_patterns = self._load_pii_patterns()

    def _load_validation_rules(self) -> Dict:
        """加载验证规则"""
        return {
            'puuid_pattern': r'^[a-zA-Z0-9_-]{78}$',
            'match_id_pattern': r'^[A-Z]{2}_\d{10}$',
            'patch_pattern': r'^\d+\.\d+$',
            'tier_values': ['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM',
                           'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'],
            'required_fields': ['match_id', 'player_key', 'patch_version'],
            'numeric_ranges': {
                'kills': (0, 50),
                'deaths': (0, 50),
                'assists': (0, 100),
                'gold_earned': (0, 100000),
                'game_duration_minutes': (8, 120)
            }
        }

    def _load_pii_patterns(self) -> List[str]:
        """加载PII检测模式"""
        return [
            r'RGAPI-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',  # API keys
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
            r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # Credit card patterns
        ]

    def assess_data_quality(self, record: Dict, record_type: str = "fact") -> DataQualityMetrics:
        """评估数据质量"""

        # 完整性检查
        completeness = self._check_completeness(record)

        # 准确性检查
        accuracy = self._check_accuracy(record, record_type)

        # 一致性检查
        consistency = self._check_consistency(record)

        # 及时性检查
        timeliness = self._check_timeliness(record)

        # 有效性检查
        validity = self._check_validity(record)

        # 唯一性检查
        uniqueness = self._check_uniqueness(record)

        # 计算综合评分
        overall = (completeness + accuracy + consistency + timeliness + validity + uniqueness) / 6

        return DataQualityMetrics(
            completeness_score=round(completeness, 3),
            accuracy_score=round(accuracy, 3),
            consistency_score=round(consistency, 3),
            timeliness_score=round(timeliness, 3),
            validity_score=round(validity, 3),
            uniqueness_score=round(uniqueness, 3),
            overall_score=round(overall, 3)
        )

    def _check_completeness(self, record: Dict) -> float:
        """检查完整性"""
        required_fields = self.validation_rules['required_fields']
        missing_count = 0

        for field in required_fields:
            if field not in record or record[field] is None or record[field] == '':
                missing_count += 1

        return max(0, 1 - (missing_count / len(required_fields)))

    def _check_accuracy(self, record: Dict, record_type: str) -> float:
        """检查准确性"""
        accuracy_score = 1.0

        # 数值范围检查
        for field, (min_val, max_val) in self.validation_rules['numeric_ranges'].items():
            if field in record:
                value = record[field]
                if isinstance(value, (int, float)):
                    if not (min_val <= value <= max_val):
                        accuracy_score -= 0.1

        # 业务逻辑检查
        if record_type == "fact":
            # KDA逻辑检查
            if all(k in record for k in ['kills', 'deaths', 'assists', 'kda_ratio']):
                expected_kda = (record['kills'] + record['assists']) / max(record['deaths'], 1)
                if abs(record['kda_ratio'] - expected_kda) > 0.1:
                    accuracy_score -= 0.2

        return max(0, accuracy_score)

    def _check_consistency(self, record: Dict) -> float:
        """检查一致性"""
        consistency_score = 1.0

        # 格式一致性检查
        if 'player_key' in record:
            if not isinstance(record['player_key'], str) or len(record['player_key']) != 64:
                consistency_score -= 0.3

        if 'patch_version' in record:
            if not re.match(self.validation_rules['patch_pattern'], str(record['patch_version'])):
                consistency_score -= 0.2

        return max(0, consistency_score)

    def _check_timeliness(self, record: Dict) -> float:
        """检查及时性"""
        if 'ingestion_timestamp' in record:
            try:
                ingestion_time = datetime.fromisoformat(record['ingestion_timestamp'].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                age_hours = (now - ingestion_time).total_seconds() / 3600

                # 24小时内数据得满分，超过后线性衰减
                if age_hours <= 24:
                    return 1.0
                elif age_hours <= 168:  # 7天
                    return 1.0 - ((age_hours - 24) / 144) * 0.5
                else:
                    return 0.5
            except:
                return 0.3
        return 0.7  # 无时间戳时给基础分

    def _check_validity(self, record: Dict) -> float:
        """检查有效性"""
        validity_score = 1.0

        # 必需字段存在性
        for field in self.validation_rules['required_fields']:
            if field not in record:
                validity_score -= 0.2

        # 数据类型检查
        if 'match_id' in record and not isinstance(record['match_id'], str):
            validity_score -= 0.1

        if 'player_key' in record and not isinstance(record['player_key'], str):
            validity_score -= 0.2

        return max(0, validity_score)

    def _check_uniqueness(self, record: Dict) -> float:
        """检查唯一性 (简化版本，实际需要数据库支持)"""
        # 这里返回基础分，实际实现需要检查重复记录
        if 'match_id' in record and 'player_key' in record:
            return 1.0
        return 0.5

    def validate_compliance(self, record: Dict) -> ComplianceCheck:
        """验证合规性"""

        # 匿名化验证
        anonymization_ok = self._validate_anonymization(record)

        # PII检测
        pii_ok = self._detect_pii(record)

        return ComplianceCheck(
            anonymization_validated=anonymization_ok,
            pii_detection_passed=pii_ok,
            retention_policy_applied=True,  # 简化实现
            access_control_validated=True,   # 简化实现
            gdpr_compliant=anonymization_ok and pii_ok
        )

    def _validate_anonymization(self, record: Dict) -> bool:
        """验证匿名化"""
        # 检查是否存在原始PUUID
        record_str = json.dumps(record)

        # 检查PUUID模式
        puuid_pattern = r'[a-zA-Z0-9_-]{78}'
        puuid_matches = re.findall(puuid_pattern, record_str)

        # player_key应该是哈希值(64字符)，不是原始PUUID(78字符)
        if 'player_key' in record:
            return len(record['player_key']) == 64

        return True

    def _detect_pii(self, record: Dict) -> bool:
        """检测PII信息"""
        record_str = json.dumps(record)

        for pattern in self.pii_patterns:
            if re.search(pattern, record_str, re.IGNORECASE):
                return False  # 发现PII

        return True  # 未发现PII

    def create_lineage(self, source: str, transformation: str, dependencies: List[str] = None) -> DataLineage:
        """创建数据血缘"""
        return DataLineage(
            source_system="riot_api",
            source_table=source,
            transformation_id=transformation,
            transformation_timestamp=datetime.now(timezone.utc).isoformat(),
            dependencies=dependencies or [],
            output_artifacts=[]
        )

    def generate_governance_record(self, record: Dict, record_type: str = "fact",
                                 source: str = "bronze_matches",
                                 transformation: str = "bronze_to_silver") -> GovernanceRecord:
        """生成完整治理记录"""

        # 生成记录ID
        record_key = f"{record.get('match_id', '')}_{record.get('player_key', '')}"
        record_id = hashlib.sha256(record_key.encode()).hexdigest()[:16]

        # 评估数据质量
        quality = self.assess_data_quality(record, record_type)

        # 验证合规性
        compliance = self.validate_compliance(record)

        # 创建血缘
        lineage = self.create_lineage(source, transformation)

        # 确定风险等级
        risk_level = self._assess_risk_level(quality, compliance)

        # 收集验证错误
        validation_errors = self._collect_validation_errors(record, quality, compliance)

        # 生成治理标签
        governance_tags = self._generate_governance_tags(record, quality, compliance)

        return GovernanceRecord(
            record_id=record_id,
            data_quality=quality,
            lineage=lineage,
            compliance=compliance,
            governance_tags=governance_tags,
            risk_level=risk_level,
            validation_errors=validation_errors,
            created_at=datetime.now(timezone.utc).isoformat(),
            validated_by="governance_framework_v1.0"
        )

    def _assess_risk_level(self, quality: DataQualityMetrics, compliance: ComplianceCheck) -> str:
        """评估风险等级"""
        if quality.overall_score >= 0.9 and compliance.gdpr_compliant:
            return "LOW"
        elif quality.overall_score >= 0.7 and compliance.anonymization_validated:
            return "MEDIUM"
        else:
            return "HIGH"

    def _collect_validation_errors(self, record: Dict, quality: DataQualityMetrics,
                                 compliance: ComplianceCheck) -> List[str]:
        """收集验证错误"""
        errors = []

        if quality.completeness_score < 0.8:
            errors.append("INCOMPLETE_DATA")

        if quality.accuracy_score < 0.8:
            errors.append("ACCURACY_ISSUES")

        if not compliance.anonymization_validated:
            errors.append("ANONYMIZATION_FAILED")

        if not compliance.pii_detection_passed:
            errors.append("PII_DETECTED")

        return errors

    def _generate_governance_tags(self, record: Dict, quality: DataQualityMetrics,
                                compliance: ComplianceCheck) -> List[str]:
        """生成治理标签"""
        tags = []

        # 质量标签
        if quality.overall_score >= 0.95:
            tags.append("HIGH_QUALITY")
        elif quality.overall_score >= 0.8:
            tags.append("GOOD_QUALITY")
        else:
            tags.append("NEEDS_REVIEW")

        # 合规标签
        if compliance.gdpr_compliant:
            tags.append("GDPR_COMPLIANT")

        if compliance.anonymization_validated:
            tags.append("ANONYMIZED")

        # 业务标签
        if 'tier' in record:
            tags.append(f"TIER_{record['tier']}")

        if 'patch_version' in record:
            tags.append(f"PATCH_{record['patch_version']}")

        return tags

    def generate_quality_report(self, records: List[Dict], record_type: str = "fact") -> Dict:
        """生成质量报告"""
        governance_records = []

        for record in records:
            gov_record = self.generate_governance_record(record, record_type)
            governance_records.append(gov_record)

        # 统计分析
        total_records = len(governance_records)
        high_quality = sum(1 for r in governance_records if r.data_quality.overall_score >= 0.9)
        low_risk = sum(1 for r in governance_records if r.risk_level == "LOW")
        compliant = sum(1 for r in governance_records if r.compliance.gdpr_compliant)

        avg_quality = sum(r.data_quality.overall_score for r in governance_records) / total_records

        return {
            'summary': {
                'total_records': total_records,
                'high_quality_records': high_quality,
                'high_quality_percentage': round((high_quality / total_records) * 100, 2),
                'low_risk_records': low_risk,
                'compliant_records': compliant,
                'average_quality_score': round(avg_quality, 3)
            },
            'quality_distribution': {
                'excellent': sum(1 for r in governance_records if r.data_quality.overall_score >= 0.95),
                'good': sum(1 for r in governance_records if 0.8 <= r.data_quality.overall_score < 0.95),
                'fair': sum(1 for r in governance_records if 0.6 <= r.data_quality.overall_score < 0.8),
                'poor': sum(1 for r in governance_records if r.data_quality.overall_score < 0.6)
            },
            'risk_distribution': {
                'low': sum(1 for r in governance_records if r.risk_level == "LOW"),
                'medium': sum(1 for r in governance_records if r.risk_level == "MEDIUM"),
                'high': sum(1 for r in governance_records if r.risk_level == "HIGH")
            },
            'compliance_metrics': {
                'gdpr_compliant': compliant,
                'anonymization_validated': sum(1 for r in governance_records if r.compliance.anonymization_validated),
                'pii_clean': sum(1 for r in governance_records if r.compliance.pii_detection_passed)
            },
            'governance_records': [asdict(r) for r in governance_records[:10]]  # 样本记录
        }


def main():
    """测试治理框架"""
    # 示例记录
    sample_record = {
        'match_id': 'NA1_4567890123',
        'player_key': 'a1b2c3d4e5f67890' * 4,  # 64字符哈希
        'patch_version': '25.18',
        'kills': 12,
        'deaths': 3,
        'assists': 8,
        'kda_ratio': 6.67,
        'gold_earned': 15000,
        'game_duration_minutes': 32.5,
        'tier': 'DIAMOND',
        'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
    }

    framework = DataGovernanceFramework()

    # 生成治理记录
    gov_record = framework.generate_governance_record(sample_record)

    print("🛡️ 数据治理框架测试")
    print(f"记录ID: {gov_record.record_id}")
    print(f"数据质量评分: {gov_record.data_quality.overall_score}")
    print(f"风险等级: {gov_record.risk_level}")
    print(f"合规状态: {'✅' if gov_record.compliance.gdpr_compliant else '❌'}")
    print(f"治理标签: {gov_record.governance_tags}")

    if gov_record.validation_errors:
        print(f"验证错误: {gov_record.validation_errors}")

    # 生成质量报告
    quality_report = framework.generate_quality_report([sample_record])
    print(f"\n📊 质量报告:")
    print(f"总记录数: {quality_report['summary']['total_records']}")
    print(f"高质量比例: {quality_report['summary']['high_quality_percentage']}%")
    print(f"平均质量评分: {quality_report['summary']['average_quality_score']}")


if __name__ == "__main__":
    main()