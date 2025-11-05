#!/usr/bin/env python3
"""
PII脱敏处理器
确保敏感信息不泄漏到日志、Bedrock或外部系统
"""
import hashlib
import re
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd

from .utils import load_user_mode_config


class PIISanitizer:
    """PII脱敏处理器"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """初始化脱敏器"""
        self.config = load_user_mode_config(config_path)
        self.sanitization_rules = self._load_sanitization_rules()

    def _load_sanitization_rules(self) -> Dict[str, Any]:
        """加载脱敏规则"""
        return {
            # 标识符脱敏规则
            "identifiers": {
                "puuid": {
                    "action": "hash8",
                    "preserve_format": False,
                    "log_original": False
                },
                "match_id": {
                    "action": "hash8",
                    "preserve_format": False,
                    "log_original": False
                },
                "summoner_name": {
                    "action": "remove",
                    "replacement": "[REDACTED]"
                },
                "row_id": {
                    "action": "hash8",
                    "preserve_prefix": True  # 保留格式前缀
                }
            },

            # 英雄信息脱敏
            "champion_data": {
                "champion_name": {
                    "action": "replace_with_id",
                    "id_field": "champion_id"
                },
                "champion_id": {
                    "action": "keep",  # ID可以保留
                    "validate_range": [1, 999]
                }
            },

            # 位置信息（可保留）
            "game_context": {
                "role": {"action": "keep"},
                "queue": {"action": "keep"},
                "patch_id": {"action": "keep"}
            },

            # 数值数据脱敏
            "statistical_data": {
                "preserve_fields": [
                    "n", "w", "p_hat", "ci", "winrate_delta",
                    "stability", "effective_n", "pfs_score",
                    "governance_tag", "synthetic_share", "uses_prior"
                ],
                "round_precision": {
                    "probabilities": 4,
                    "scores": 6,
                    "counts": 0
                }
            },

            # IP地址和地理位置
            "network_info": {
                "ip_address": {
                    "action": "remove",
                    "replacement": "0.0.0.0"
                },
                "region": {
                    "action": "generalize",  # 保留大区域
                    "allowed_values": ["na1", "euw1", "kr", "jp1", "br1"]
                }
            }
        }

    def sanitize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        脱敏单条记录

        Args:
            record: 原始记录

        Returns:
            脱敏后的记录
        """
        sanitized = {}

        for field, value in record.items():
            sanitized_value = self._sanitize_field(field, value)
            if sanitized_value is not None:
                sanitized[field] = sanitized_value

        # 添加脱敏标记
        sanitized['_sanitized'] = True
        sanitized['_sanitization_timestamp'] = datetime.utcnow().isoformat()

        return sanitized

    def sanitize_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量脱敏记录

        Args:
            records: 原始记录列表

        Returns:
            脱敏后的记录列表
        """
        return [self.sanitize_record(record) for record in records]

    def sanitize_for_bedrock(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为Bedrock调用特别脱敏

        Args:
            data: 要发送给Bedrock的数据

        Returns:
            Bedrock安全的数据
        """
        # 递归脱敏所有字段
        sanitized = self._deep_sanitize(data)

        # 移除敏感字段
        sensitive_fields = [
            'puuid', 'summoner_name', 'match_id', 'account_id',
            'platform_id', 'ip_address', 'email'
        ]

        sanitized = self._remove_fields(sanitized, sensitive_fields)

        # 限制数据量 (Token控制)
        if isinstance(sanitized, dict) and 'records' in sanitized:
            records = sanitized['records']
            if len(records) > 100:  # 最多100条记录
                # 按重要性排序，保留Top-100
                sorted_records = sorted(
                    records,
                    key=lambda x: (
                        x.get('governance_tag') == 'CONFIDENT',
                        x.get('pfs_score', 0)
                    ),
                    reverse=True
                )
                sanitized['records'] = sorted_records[:100]

        return sanitized

    def sanitize_for_logging(self, data: Union[Dict, List, str]) -> Union[Dict, List, str]:
        """
        为日志记录脱敏

        Args:
            data: 要记录的数据

        Returns:
            日志安全的数据
        """
        if isinstance(data, str):
            return self._sanitize_string_for_log(data)
        elif isinstance(data, dict):
            return self._sanitize_dict_for_log(data)
        elif isinstance(data, list):
            return [self.sanitize_for_logging(item) for item in data]
        else:
            return data

    def _sanitize_field(self, field_name: str, value: Any) -> Any:
        """脱敏单个字段"""
        # 检查是否为敏感标识符
        if field_name in ['puuid', 'summoner_id', 'account_id']:
            return self._hash_identifier(str(value))

        elif field_name == 'match_id':
            return self._hash_identifier(str(value))

        elif field_name == 'row_id':
            return self._sanitize_row_id(str(value))

        elif field_name == 'summoner_name':
            return "[REDACTED]"

        elif field_name == 'champion_name':
            return None  # 移除，使用champion_id

        elif field_name in ['ip_address', 'platform_id']:
            return None  # 完全移除

        # 保留统计数据字段
        elif field_name in self.sanitization_rules['statistical_data']['preserve_fields']:
            return self._sanitize_statistical_value(field_name, value)

        # 保留游戏上下文字段
        elif field_name in ['role', 'queue', 'patch_id', 'champion_id']:
            return value

        # 其他字段默认保留
        else:
            return value

    def _sanitize_row_id(self, row_id: str) -> str:
        """脱敏row_id，保留格式前缀"""
        try:
            # row_id格式: {patch}_{champion}_{role}_{queue}#{hash8}
            if '#' in row_id:
                prefix, original_hash = row_id.rsplit('#', 1)
                new_hash = self._hash_identifier(row_id)
                return f"{prefix}#{new_hash}"
            else:
                return self._hash_identifier(row_id)
        except Exception:
            return self._hash_identifier(row_id)

    def _sanitize_statistical_value(self, field_name: str, value: Any) -> Any:
        """脱敏统计数值"""
        if value is None:
            return None

        try:
            # 概率类数值
            if field_name in ['p_hat', 'winrate_delta', 'stability', 'synthetic_share']:
                if isinstance(value, (int, float)):
                    return round(float(value), 4)

            # 评分类数值
            elif field_name in ['pfs_score']:
                if isinstance(value, (int, float)):
                    return round(float(value), 6)

            # 计数类数值
            elif field_name in ['n', 'w']:
                if isinstance(value, (int, float)):
                    return int(value)

            # 置信区间
            elif field_name == 'ci' and isinstance(value, dict):
                return {
                    'lo': round(float(value.get('lo', 0)), 4),
                    'hi': round(float(value.get('hi', 1)), 4)
                }

            # 其他数值
            else:
                return value

        except (ValueError, TypeError):
            return value

    def _hash_identifier(self, identifier: str, length: int = 8) -> str:
        """生成标识符hash"""
        if not identifier:
            return "00000000"[:length]

        hash_full = hashlib.sha256(identifier.encode('utf-8')).hexdigest()
        return hash_full[:length]

    def _deep_sanitize(self, data: Any) -> Any:
        """递归深度脱敏"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                sanitized_value = self._sanitize_field(key, value)
                if sanitized_value is not None:
                    if isinstance(sanitized_value, (dict, list)):
                        sanitized[key] = self._deep_sanitize(sanitized_value)
                    else:
                        sanitized[key] = sanitized_value
            return sanitized

        elif isinstance(data, list):
            return [self._deep_sanitize(item) for item in data]

        else:
            return data

    def _remove_fields(self, data: Dict[str, Any], fields_to_remove: List[str]) -> Dict[str, Any]:
        """移除敏感字段"""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if key not in fields_to_remove:
                if isinstance(value, dict):
                    sanitized[key] = self._remove_fields(value, fields_to_remove)
                elif isinstance(value, list):
                    sanitized[key] = [
                        self._remove_fields(item, fields_to_remove) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    sanitized[key] = value

        return sanitized

    def _sanitize_string_for_log(self, text: str) -> str:
        """脱敏日志字符串"""
        # 脱敏常见的敏感信息模式
        patterns = [
            # PUUID模式 (通常很长的字母数字字符串)
            (r'\b[A-Za-z0-9_-]{50,}\b', '[PUUID_REDACTED]'),

            # Match ID模式
            (r'\b[A-Za-z0-9]{10,20}_\d+\b', '[MATCH_ID_REDACTED]'),

            # IP地址
            (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]'),

            # 邮箱地址
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),

            # 可能的召唤师名称 (在引号中的名称)
            (r'"[A-Za-z0-9\s]{3,16}"', '"[SUMMONER_REDACTED]"'),
        ]

        sanitized_text = text
        for pattern, replacement in patterns:
            sanitized_text = re.sub(pattern, replacement, sanitized_text)

        return sanitized_text

    def _sanitize_dict_for_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏日志字典"""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            # 敏感字段直接脱敏
            if key in ['puuid', 'summoner_id', 'account_id', 'match_id']:
                sanitized[key] = f"[{key.upper()}_REDACTED]"
            elif key == 'summoner_name':
                sanitized[key] = "[SUMMONER_REDACTED]"
            elif key == 'ip_address':
                sanitized[key] = "[IP_REDACTED]"
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_string_for_log(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict_for_log(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict_for_log(item) if isinstance(item, dict)
                    else self._sanitize_string_for_log(str(item)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def generate_sanitization_report(self, original_data: Any, sanitized_data: Any) -> Dict[str, Any]:
        """生成脱敏报告"""
        report = {
            "sanitization_timestamp": datetime.utcnow().isoformat(),
            "sanitization_rules_version": "v1.0",
            "original_size": self._calculate_data_size(original_data),
            "sanitized_size": self._calculate_data_size(sanitized_data),
            "fields_processed": self._count_fields_processed(original_data, sanitized_data),
            "pii_fields_found": self._identify_pii_fields(original_data),
            "compliance_status": "compliant"
        }

        return report

    def _calculate_data_size(self, data: Any) -> Dict[str, int]:
        """计算数据大小"""
        if isinstance(data, dict):
            return {
                "field_count": len(data),
                "nested_objects": sum(1 for v in data.values() if isinstance(v, dict)),
                "list_count": sum(1 for v in data.values() if isinstance(v, list))
            }
        elif isinstance(data, list):
            return {
                "item_count": len(data),
                "dict_items": sum(1 for item in data if isinstance(item, dict))
            }
        else:
            return {"size": 1}

    def _count_fields_processed(self, original: Any, sanitized: Any) -> Dict[str, int]:
        """统计处理的字段"""
        def count_fields(data):
            if isinstance(data, dict):
                return len(data) + sum(count_fields(v) for v in data.values())
            elif isinstance(data, list):
                return sum(count_fields(item) for item in data)
            else:
                return 1

        return {
            "original_fields": count_fields(original),
            "sanitized_fields": count_fields(sanitized)
        }

    def _identify_pii_fields(self, data: Any) -> List[str]:
        """识别PII字段"""
        pii_fields = []

        def find_pii_in_dict(d, prefix=""):
            if not isinstance(d, dict):
                return

            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key

                if key in ['puuid', 'summoner_id', 'account_id', 'summoner_name', 'match_id', 'ip_address']:
                    pii_fields.append(full_key)
                elif isinstance(value, dict):
                    find_pii_in_dict(value, full_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            find_pii_in_dict(item, f"{full_key}[{i}]")

        if isinstance(data, dict):
            find_pii_in_dict(data)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    find_pii_in_dict(item, f"[{i}]")

        return list(set(pii_fields))

    def validate_sanitization(self, sanitized_data: Any) -> Dict[str, Any]:
        """验证脱敏完整性"""
        validation_result = {
            "is_compliant": True,
            "violations": [],
            "warnings": []
        }

        # 检查是否还有PII
        pii_found = self._identify_pii_fields(sanitized_data)
        if pii_found:
            validation_result["is_compliant"] = False
            validation_result["violations"].extend([f"PII field still present: {field}" for field in pii_found])

        # 检查字符串中的敏感信息
        text_violations = self._check_text_for_pii(sanitized_data)
        if text_violations:
            validation_result["warnings"].extend(text_violations)

        return validation_result

    def _check_text_for_pii(self, data: Any) -> List[str]:
        """检查文本中的PII"""
        violations = []

        def check_string(text: str, path: str = ""):
            if not isinstance(text, str):
                return

            # 检查可能的PUUID (长字符串)
            if re.search(r'\b[A-Za-z0-9_-]{50,}\b', text):
                violations.append(f"Possible PUUID in text at {path}")

            # 检查IP地址
            if re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text):
                violations.append(f"IP address found at {path}")

        def traverse(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if isinstance(value, str):
                        check_string(value, new_path)
                    else:
                        traverse(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    traverse(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                check_string(obj, path)

        traverse(data)
        return violations


def main():
    """测试接口"""
    import argparse

    parser = argparse.ArgumentParser(description="PII脱敏测试")
    parser.add_argument("--input", required=True, help="输入文件")
    parser.add_argument("--output", default="data/user_mode/sanitized", help="输出目录")
    parser.add_argument("--mode", choices=["record", "bedrock", "log"], default="record", help="脱敏模式")
    args = parser.parse_args()

    # 加载数据
    with open(args.input, 'r', encoding='utf-8') as f:
        if args.input.endswith('.jsonl'):
            data = [json.loads(line) for line in f if line.strip()]
        else:
            data = json.load(f)

    # 创建脱敏器
    sanitizer = PIISanitizer()

    # 执行脱敏
    if args.mode == "record":
        if isinstance(data, list):
            sanitized = sanitizer.sanitize_records(data)
        else:
            sanitized = sanitizer.sanitize_record(data)
    elif args.mode == "bedrock":
        sanitized = sanitizer.sanitize_for_bedrock(data)
    elif args.mode == "log":
        sanitized = sanitizer.sanitize_for_logging(data)

    # 生成报告
    report = sanitizer.generate_sanitization_report(data, sanitized)
    validation = sanitizer.validate_sanitization(sanitized)

    # 保存结果
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存脱敏数据
    output_file = output_dir / f"sanitized_{args.mode}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sanitized, f, indent=2, ensure_ascii=False)

    # 保存报告
    report_file = output_dir / f"sanitization_report_{args.mode}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "sanitization_report": report,
            "validation_result": validation
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ 脱敏完成: {output_file}")
    print(f"📊 报告: {report_file}")
    print(f"  合规状态: {'✅ 合规' if validation['is_compliant'] else '❌ 不合规'}")
    if validation['violations']:
        print(f"  违规项: {validation['violations']}")


if __name__ == "__main__":
    main()