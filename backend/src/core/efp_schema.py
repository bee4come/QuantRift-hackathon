#!/usr/bin/env python3
"""
EFP (Entity Feature Panel) 数据契约与 Schema 定义
支持符文/技能/被动/装备的统一量化面板
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

class EntityType(Enum):
    RUNE = "rune"
    SKILL = "skill"
    PASSIVE = "passive"
    ITEM = "item"
    CHAMPION = "champion"

class GovernanceTag(Enum):
    CONFIDENT = "CONFIDENT"  # n≥50 或 effective_n≥100 且 CI不跨0
    CAUTION = "CAUTION"      # n∈[20,50) 或 effective_n∈[50,100)
    CONTEXT = "CONTEXT"      # 其他情况

@dataclass
class EFPRow:
    """Entity Feature Panel 行定义"""

    # 统一主键
    patch_id: str                # e.g., "14.19.1"
    entity_type: EntityType      # rune/skill/passive/item/champion
    entity_id: str               # 实体ID (rune_id, item_id, champion_id)
    sub_id: Optional[str]        # 子ID (Q/W/E/R for skills, slot for runes)
    role: str                    # TOP/JUNGLE/MIDDLE/BOTTOM/UTILITY
    queue: str                   # RANKED_SOLO_5x5, RANKED_FLEX_SR
    tier: str                    # IRON,BRONZE,SILVER,GOLD,PLATINUM,DIAMOND,MASTER,GRANDMASTER,CHALLENGER

    # 使用面
    pick_rate: float             # 选取率
    attach_rate: float           # 随某英雄/套路绑定率
    avg_slots: float             # 装备格数/符文位平均值

    # 性能面
    p_hat: float                 # Beta-Binomial 后验均值
    ci_lo: float                 # 置信区间下限
    ci_hi: float                 # 置信区间上限
    winrate_delta_vs_baseline: float  # 相对基线胜率差
    kda_adj: float               # KDA 调整值
    obj_rate: float              # 大龙/先锋/塔参与率

    # 冲击面
    shock_v2: float              # Shock v2 综合得分
    shock_components: Dict[str, float]  # 组件得分 {value, scaling, cd, cost, gold_eff, etc.}

    # 上下文
    synergy_score: float         # 与X组合协同得分
    anti_score: float            # 被Y克制得分
    time_to_first: Optional[float]  # 首次购买/触发时间(分钟)

    # 样本统计
    n: int                       # 原始样本数
    effective_n: float           # 有效样本数(经先验收缩)
    uses_prior: bool             # 是否使用先验
    n0: float                    # 先验等效样本数
    w0: float                    # 先验权重
    decay: float                 # 时间衰减因子
    synthetic_share: float       # 合成数据占比

    # 治理
    aggregation_level: str       # coarse/standard/fine
    governance_tag: GovernanceTag # CONFIDENT/CAUTION/CONTEXT

    # 元数据
    row_id_hash: str             # 行唯一标识hash
    created_at: str              # 创建时间戳
    data_sources: List[str]      # 数据源清单

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, (list, dict)):
                result[key] = value
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EFPRow':
        """从字典创建实例"""
        # 转换枚举类型
        if 'entity_type' in data:
            data['entity_type'] = EntityType(data['entity_type'])
        if 'governance_tag' in data:
            data['governance_tag'] = GovernanceTag(data['governance_tag'])

        return cls(**data)

@dataclass
class PFPRow:
    """Player Feature Panel 行定义"""

    # 主键
    puuid: str                   # 玩家PUUID (hash8格式)
    patch_id: str                # 版本ID
    role: str                    # 主要角色
    queue: str                   # 主要队列

    # 实体使用统计
    entity_usage: Dict[str, Dict[str, Any]]  # {entity_id: {count, time_on_build, casts_QWER, etc.}}

    # 派生指标
    player_fit_scores: Dict[str, float]      # 每个实体的适配得分
    meta_alignment: float                    # 版本适应度
    learning_curve: Dict[str, float]         # 最近K场趋势 {entity_id: trend_slope}

    # 统计
    games_played: int            # 该patch游戏场次
    avg_performance: float       # 平均表现

    # 元数据
    row_id_hash: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

# EFP Schema 样例数据
SAMPLE_EFP_ROWS = [
    # 符文样例
    {
        "patch_id": "14.19.1",
        "entity_type": "rune",
        "entity_id": "8128",  # 黑暗收割
        "sub_id": "DOMINATION_KEYSTONE",
        "role": "JUNGLE",
        "queue": "RANKED_SOLO_5x5",
        "tier": "PLATINUM",
        "pick_rate": 0.234,
        "attach_rate": 0.789,
        "avg_slots": 1.0,
        "p_hat": 0.524,
        "ci_lo": 0.518,
        "ci_hi": 0.530,
        "winrate_delta_vs_baseline": 0.024,
        "kda_adj": 0.15,
        "obj_rate": 0.67,
        "shock_v2": 1.85,
        "shock_components": {
            "adaptive_force": 0.8,
            "threshold_damage": 1.2,
            "scaling_factor": 0.6,
            "cooldown": -0.1,
            "tree_position": 0.35
        },
        "synergy_score": 0.82,
        "anti_score": -0.15,
        "time_to_first": None,
        "n": 1247,
        "effective_n": 1156.8,
        "uses_prior": True,
        "n0": 45.0,
        "w0": 0.072,
        "decay": 0.85,
        "synthetic_share": 0.08,
        "aggregation_level": "standard",
        "governance_tag": "CONFIDENT",
        "row_id_hash": "hash8_1a2b3c4d",
        "created_at": "2024-09-28T10:15:30Z",
        "data_sources": ["match_timeline", "rune_registry"]
    },

    # 装备样例
    {
        "patch_id": "14.19.1",
        "entity_type": "item",
        "entity_id": "6692",  # 日食
        "sub_id": None,
        "role": "BOTTOM",
        "queue": "RANKED_SOLO_5x5",
        "tier": "DIAMOND",
        "pick_rate": 0.456,
        "attach_rate": 0.923,
        "avg_slots": 1.8,
        "p_hat": 0.548,
        "ci_lo": 0.541,
        "ci_hi": 0.555,
        "winrate_delta_vs_baseline": 0.048,
        "kda_adj": 0.23,
        "obj_rate": 0.71,
        "shock_v2": -0.65,
        "shock_components": {
            "attack_damage": -0.3,
            "lethality": -0.8,
            "omnivamp": 0.1,
            "gold_efficiency": -0.45,
            "active_shield": 0.8
        },
        "synergy_score": 0.91,
        "anti_score": -0.05,
        "time_to_first": 11.2,
        "n": 2841,
        "effective_n": 2763.4,
        "uses_prior": True,
        "n0": 32.0,
        "w0": 0.043,
        "decay": 0.88,
        "synthetic_share": 0.03,
        "aggregation_level": "standard",
        "governance_tag": "CONFIDENT",
        "row_id_hash": "hash8_2e3f4a5b",
        "created_at": "2024-09-28T10:16:45Z",
        "data_sources": ["match_timeline", "item_registry", "timeline_events"]
    },

    # 技能样例
    {
        "patch_id": "14.19.1",
        "entity_type": "skill",
        "entity_id": "150",  # 金克丝
        "sub_id": "Q",
        "role": "BOTTOM",
        "queue": "RANKED_SOLO_5x5",
        "tier": "GOLD",
        "pick_rate": 0.892,
        "attach_rate": 0.998,
        "avg_slots": 5.0,  # 技能等级
        "p_hat": 0.506,
        "ci_lo": 0.502,
        "ci_hi": 0.510,
        "winrate_delta_vs_baseline": 0.006,
        "kda_adj": 0.08,
        "obj_rate": 0.63,
        "shock_v2": 0.45,
        "shock_components": {
            "base_damage": 0.2,
            "ad_ratio": 0.3,
            "range": 0.5,
            "mana_cost": -0.1,
            "cooldown": 0.0
        },
        "synergy_score": 0.76,
        "anti_score": -0.08,
        "time_to_first": 1.0,  # 1级学会
        "n": 3567,
        "effective_n": 3491.2,
        "uses_prior": True,
        "n0": 28.0,
        "w0": 0.034,
        "decay": 0.90,
        "synthetic_share": 0.02,
        "aggregation_level": "standard",
        "governance_tag": "CONFIDENT",
        "row_id_hash": "hash8_3f4a5b6c",
        "created_at": "2024-09-28T10:17:20Z",
        "data_sources": ["match_timeline", "skill_registry", "level_events"]
    },

    # 被动技能样例
    {
        "patch_id": "14.19.1",
        "entity_type": "passive",
        "entity_id": "150",  # 金克丝被动
        "sub_id": "PASSIVE",
        "role": "BOTTOM",
        "queue": "RANKED_SOLO_5x5",
        "tier": "PLATINUM",
        "pick_rate": 0.892,  # 与英雄pick_rate相同
        "attach_rate": 1.000,
        "avg_slots": 1.0,
        "p_hat": 0.514,
        "ci_lo": 0.509,
        "ci_hi": 0.519,
        "winrate_delta_vs_baseline": 0.014,
        "kda_adj": 0.12,
        "obj_rate": 0.69,
        "shock_v2": 1.20,
        "shock_components": {
            "movement_speed": 1.5,
            "attack_speed": 0.8,
            "duration": 0.2,
            "trigger_condition": -0.3
        },
        "synergy_score": 0.88,
        "anti_score": -0.02,
        "time_to_first": 0.0,  # 游戏开始即有
        "n": 3567,
        "effective_n": 3491.2,
        "uses_prior": True,
        "n0": 28.0,
        "w0": 0.034,
        "decay": 0.90,
        "synthetic_share": 0.02,
        "aggregation_level": "standard",
        "governance_tag": "CONFIDENT",
        "row_id_hash": "hash8_4a5b6c7d",
        "created_at": "2024-09-28T10:18:00Z",
        "data_sources": ["match_timeline", "passive_registry"]
    },

    # 英雄样例
    {
        "patch_id": "14.19.1",
        "entity_type": "champion",
        "entity_id": "150",  # 金克丝
        "sub_id": None,
        "role": "BOTTOM",
        "queue": "RANKED_SOLO_5x5",
        "tier": "ALL",  # 英雄级别跨tier聚合
        "pick_rate": 0.124,
        "attach_rate": 0.783,  # 与bot位绑定率
        "avg_slots": 1.0,
        "p_hat": 0.512,
        "ci_lo": 0.509,
        "ci_hi": 0.515,
        "winrate_delta_vs_baseline": 0.012,
        "kda_adj": 0.09,
        "obj_rate": 0.65,
        "shock_v2": 0.85,
        "shock_components": {
            "base_stats": 0.3,
            "stat_growth": 0.2,
            "kit_power": 0.4,
            "meta_position": 0.1
        },
        "synergy_score": 0.79,
        "anti_score": -0.12,
        "time_to_first": 0.0,
        "n": 45672,
        "effective_n": 44891.3,
        "uses_prior": True,
        "n0": 15.0,
        "w0": 0.012,
        "decay": 0.92,
        "synthetic_share": 0.01,
        "aggregation_level": "standard",
        "governance_tag": "CONFIDENT",
        "row_id_hash": "hash8_5b6c7d8e",
        "created_at": "2024-09-28T10:19:15Z",
        "data_sources": ["match_timeline", "champion_registry", "stat_registry"]
    }
]

def validate_efp_row(row_data: Dict[str, Any]) -> List[str]:
    """验证 EFP 行数据完整性"""
    errors = []

    # 必填字段检查
    required_fields = [
        'patch_id', 'entity_type', 'entity_id', 'role', 'queue', 'tier',
        'pick_rate', 'p_hat', 'ci_lo', 'ci_hi', 'shock_v2', 'n', 'effective_n'
    ]

    for field in required_fields:
        if field not in row_data:
            errors.append(f"Missing required field: {field}")

    # 数值范围检查
    if 'pick_rate' in row_data and not (0 <= row_data['pick_rate'] <= 1):
        errors.append("pick_rate must be between 0 and 1")

    if 'synthetic_share' in row_data and not (0 <= row_data['synthetic_share'] <= 1):
        errors.append("synthetic_share must be between 0 and 1")

    if 'synthetic_share' in row_data and row_data['synthetic_share'] > 0.10:
        errors.append("synthetic_share exceeds 0.10 limit")

    # CI 一致性检查
    if all(k in row_data for k in ['ci_lo', 'ci_hi', 'p_hat']):
        if not (row_data['ci_lo'] <= row_data['p_hat'] <= row_data['ci_hi']):
            errors.append("p_hat not within confidence interval")

    return errors

def save_efp_samples():
    """保存 EFP 样例数据"""
    with open('results/efp_samples.jsonl', 'w') as f:
        for row_data in SAMPLE_EFP_ROWS:
            f.write(json.dumps(row_data, ensure_ascii=False) + '\n')

    logger.info(f"Saved {len(SAMPLE_EFP_ROWS)} EFP sample rows to results/efp_samples.jsonl")

if __name__ == "__main__":
    # 验证样例数据
    for i, row_data in enumerate(SAMPLE_EFP_ROWS):
        errors = validate_efp_row(row_data)
        if errors:
            print(f"Row {i} validation errors: {errors}")
        else:
            print(f"Row {i} ({row_data['entity_type']}-{row_data['entity_id']}): ✅ Valid")

    # 保存样例
    save_efp_samples()
    print(f"\n📊 EFP Schema 定义完成，包含 {len(SAMPLE_EFP_ROWS)} 个样例行")