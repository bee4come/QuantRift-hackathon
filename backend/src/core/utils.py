#!/usr/bin/env python3
"""
User-Mode 统一工具函数
提供row_id生成、schema验证、数据类型转换等核心功能
"""
import hashlib
import json
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import pandas as pd
import numpy as np


def load_user_mode_config(config_path: str = "configs/user_mode_params.yml") -> Dict[str, Any]:
    """加载User-Mode配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"User-Mode配置文件未找到: {config_path}")


def generate_row_id(patch_id: str, champion_id: int, role: str, queue: str,
                   aggregation_level: str = "", extra_context: str = "") -> str:
    """
    统一row_id生成器 - 所有模块必须使用此函数

    格式: {patch}_{champion}_{role}_{queue}#{hash8}

    Args:
        patch_id: 版本号，如 "15.13.1"
        champion_id: 英雄ID
        role: 位置，如 "mid"
        queue: 队列，如 "ranked_solo"
        aggregation_level: 聚合层级，可选
        extra_context: 额外上下文，可选

    Returns:
        唯一row_id字符串
    """
    # 基础组件
    base_components = [patch_id, str(champion_id), role, queue]

    # 添加可选组件
    if aggregation_level:
        base_components.append(aggregation_level)
    if extra_context:
        base_components.append(extra_context)

    # 生成基础ID
    base_id = "_".join(base_components)

    # 生成短hash避免冲突
    hash_input = f"{base_id}_{aggregation_level}_{extra_context}".encode('utf-8')
    short_hash = hashlib.sha256(hash_input).hexdigest()[:8]

    return f"{patch_id}_{champion_id}_{role}_{queue}#{short_hash}"


def validate_evidence_schema(record: Dict[str, Any],
                           config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    验证证据记录是否符合schema

    Args:
        record: 待验证的记录
        config: 配置字典，可选

    Returns:
        验证结果 {valid: bool, missing_fields: list, errors: list}
    """
    if config is None:
        config = load_user_mode_config()

    required_fields = config['evidence_schema']['required_fields']

    result = {
        'valid': True,
        'missing_fields': [],
        'errors': []
    }

    # 检查必填字段
    for field in required_fields:
        if field not in record:
            result['missing_fields'].append(field)
            result['valid'] = False

    # 类型检查
    if 'row_id' in record and not isinstance(record['row_id'], str):
        result['errors'].append("row_id must be string")
        result['valid'] = False

    if 'governance_tag' in record:
        valid_tags = ['CONFIDENT', 'CAUTION', 'CONTEXT']
        if record['governance_tag'] not in valid_tags:
            result['errors'].append(f"governance_tag must be one of {valid_tags}")
            result['valid'] = False

    if 'role' in record:
        valid_roles = ['top', 'jungle', 'mid', 'adc', 'support']
        if record['role'] not in valid_roles:
            result['errors'].append(f"role must be one of {valid_roles}")
            result['valid'] = False

    return result


def apply_governance_tag(record: Dict[str, Any],
                        config: Optional[Dict[str, Any]] = None) -> str:
    """
    应用治理分级标签

    Args:
        record: 证据记录
        config: 配置字典

    Returns:
        治理标签: CONFIDENT/CAUTION/CONTEXT
    """
    if config is None:
        config = load_user_mode_config()

    grading = config['governance']['evidence_grading']

    n = record.get('n', 0)
    effective_n = record.get('effective_n', 0)
    ci = record.get('ci', {})

    # CONFIDENT条件
    confident_n_ok = n >= grading['confident']['min_n']
    confident_en_ok = effective_n >= grading['confident']['or_effective_n']
    ci_excludes_zero = (ci.get('lo', 0) > 0) or (ci.get('hi', 0) < 0)

    if (confident_n_ok or confident_en_ok) and ci_excludes_zero:
        return 'CONFIDENT'

    # CAUTION条件
    caution_n_ok = (grading['caution']['min_n'] <= n <= grading['caution']['max_n'])
    caution_en_ok = (grading['caution']['or_effective_n_min'] <= effective_n <= grading['caution']['or_effective_n_max'])

    if caution_n_ok or caution_en_ok:
        return 'CAUTION'

    # 其余为CONTEXT
    return 'CONTEXT'


def standardize_pfs_inputs(records: pd.DataFrame,
                          config: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    标准化PFS输入数据

    Args:
        records: 原始记录DataFrame
        config: 配置字典

    Returns:
        标准化后的DataFrame
    """
    if config is None:
        config = load_user_mode_config()

    df = records.copy()
    robust_config = config['pfs_scoring']['robustness']

    # 稳健缩尾
    winsor_lower = robust_config['winsorize_lower']
    winsor_upper = robust_config['winsorize_upper']

    if 'winrate_delta' in df.columns:
        df['winrate_delta'] = df['winrate_delta'].clip(
            lower=df['winrate_delta'].quantile(winsor_lower),
            upper=df['winrate_delta'].quantile(winsor_upper)
        )

    # 计算标准化分数
    if 'winrate_delta' in df.columns and 'ci' in df.columns:
        # 计算CI宽度
        df['ci_width'] = df['ci'].apply(lambda x: max(robust_config['min_ci_width'],
                                                     x.get('hi', 0) - x.get('lo', 0)))

        # 技能分标准化 (约当z分)
        df['z_skill'] = df['winrate_delta'] / (df['ci_width'] / 3.92)

        # 波动标准化
        median_ci_width = max(robust_config['min_median_ci'], df['ci_width'].median())
        df['z_volatility'] = df['ci_width'] / median_ci_width

    return df


def filter_by_governance(records: List[Dict[str, Any]],
                        allowed_tags: List[str] = ['CONFIDENT', 'CAUTION'],
                        config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    按治理标签过滤记录

    Args:
        records: 原始记录列表
        allowed_tags: 允许的治理标签
        config: 配置字典

    Returns:
        过滤后的记录列表
    """
    if config is None:
        config = load_user_mode_config()

    red_lines = config['governance']['red_lines']

    filtered_records = []

    for record in records:
        # 检查治理标签
        if record.get('governance_tag') not in allowed_tags:
            continue

        # 检查合成数据占比
        if record.get('synthetic_share', 0) > red_lines['max_synthetic_share']:
            continue

        # 检查coarse级别
        if red_lines['ban_coarse_evidence'] and 'coarse' in record.get('aggregation_level', ''):
            continue

        filtered_records.append(record)

    return filtered_records


def sort_and_limit_records(records: List[Dict[str, Any]],
                          max_rows: int = 400,
                          config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    按优先级排序并限制记录数量

    Args:
        records: 原始记录列表
        max_rows: 最大行数
        config: 配置字典

    Returns:
        排序并限制后的记录列表
    """
    if config is None:
        config = load_user_mode_config()

    df = pd.DataFrame(records)
    if df.empty:
        return []

    # 计算排序指标
    df['abs_winrate_delta'] = df['winrate_delta'].abs()
    df['pfs_score'] = df.get('pfs_score', 0)  # 如果已计算过PFS

    # 按复合优先级排序
    df_sorted = df.sort_values(
        ['abs_winrate_delta', 'pfs_score'],
        ascending=[False, False]
    )

    # 限制行数
    df_limited = df_sorted.head(max_rows)

    return df_limited.to_dict('records')


def calculate_ceiling_base_stats(records: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    计算Ceiling估算的基础统计

    Args:
        records: 证据记录列表

    Returns:
        基础统计字典
    """
    if not records:
        return {'avg_winrate': 0.5, 'avg_lp_per_win': 17, 'avg_lp_per_loss': 17}

    df = pd.DataFrame(records)

    stats = {
        'avg_winrate': df['p_hat'].mean() if 'p_hat' in df.columns else 0.5,
        'avg_lp_per_win': 17,  # 默认值，将从patch_summary中获取
        'avg_lp_per_loss': 17
    }

    return stats


def safe_float_convert(value: Any, default: float = 0.0) -> float:
    """安全浮点数转换"""
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_convert(value: Any, default: int = 0) -> int:
    """安全整数转换"""
    try:
        if pd.isna(value):
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def format_output_precision(value: Union[float, int],
                           is_probability: bool = False,
                           config: Optional[Dict[str, Any]] = None) -> float:
    """
    按配置精度格式化输出数值

    Args:
        value: 原始数值
        is_probability: 是否为概率值
        config: 配置字典

    Returns:
        格式化后的数值
    """
    if config is None:
        config = load_user_mode_config()

    precision_config = config['output_control']['precision']

    if is_probability:
        decimals = precision_config['probability_decimals']
    else:
        decimals = precision_config['float_decimals']

    return round(float(value), decimals)


def save_with_audit_trail(data: List[Dict[str, Any]],
                         filepath: str,
                         metadata: Dict[str, Any] = None) -> None:
    """
    保存数据并记录审计轨迹

    Args:
        data: 要保存的数据
        filepath: 文件路径
        metadata: 元数据信息
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # 保存主数据
    with open(filepath, 'w', encoding='utf-8') as f:
        for record in data:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # 保存审计信息
    audit_info = {
        'filepath': str(filepath),
        'record_count': len(data),
        'created_at': pd.Timestamp.now().isoformat(),
        'metadata': metadata or {}
    }

    audit_path = filepath.parent / f"{filepath.stem}_audit.json"
    with open(audit_path, 'w', encoding='utf-8') as f:
        json.dump(audit_info, f, indent=2, ensure_ascii=False)


# 导出核心函数
__all__ = [
    'load_user_mode_config',
    'generate_row_id',
    'validate_evidence_schema',
    'apply_governance_tag',
    'standardize_pfs_inputs',
    'filter_by_governance',
    'sort_and_limit_records',
    'calculate_ceiling_base_stats',
    'safe_float_convert',
    'safe_int_convert',
    'format_output_precision',
    'save_with_audit_trail'
]