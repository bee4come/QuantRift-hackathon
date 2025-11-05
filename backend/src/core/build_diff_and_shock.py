#!/usr/bin/env python3
"""
Shock v2 计算引擎
对版本间实体变化进行标准化冲击度量化
"""

import json
import numpy as np
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ShockComponent:
    """Shock 组件定义"""
    name: str
    weight: float
    z_score: float
    raw_delta: float
    usage_weight: float = 1.0

class ShockCalculatorV2:
    def __init__(self, config_path: str = "configs/shock_weights.yml"):
        """初始化 Shock v2 计算器"""
        self.config = self._load_config(config_path)
        self.theory_params = self._load_theory_params()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载 shock 权重配置"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()

    def _load_theory_params(self) -> Dict[str, Any]:
        """加载理论参数"""
        try:
            with open("configs/theory_params.yml", 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("theory_params.yml not found, using defaults")
            return self._get_default_theory_params()

    def _get_default_config(self) -> Dict[str, Any]:
        """默认 shock 权重配置"""
        return {
            "rune": {
                "adaptive_force": 0.3,
                "threshold_damage": 0.25,
                "scaling_factor": 0.2,
                "cooldown": 0.15,
                "tree_position": 0.1
            },
            "item": {
                "attack_damage": 0.2,
                "ability_power": 0.2,
                "health": 0.15,
                "armor": 0.1,
                "magic_resist": 0.1,
                "gold_efficiency": 0.15,
                "active_shield": 0.1
            },
            "skill": {
                "base_damage": 0.3,
                "ad_ratio": 0.25,
                "ap_ratio": 0.25,
                "cooldown": 0.1,
                "mana_cost": 0.1
            },
            "passive": {
                "movement_speed": 0.25,
                "attack_speed": 0.2,
                "damage_amplifier": 0.3,
                "duration": 0.15,
                "trigger_condition": 0.1
            },
            "champion": {
                "base_stats": 0.4,
                "stat_growth": 0.3,
                "kit_power": 0.2,
                "meta_position": 0.1
            }
        }

    def _get_default_theory_params(self) -> Dict[str, Any]:
        """默认理论参数"""
        return {
            "damage_calculation": {
                "base_ad_level_18": 100,
                "base_ap_level_18": 150,
                "typical_armor": 80,
                "typical_mr": 50,
                "crit_multiplier": 2.0
            },
            "gold_efficiency": {
                "ad_per_gold": 0.035,    # 每1金币的AD
                "ap_per_gold": 0.046,    # 每1金币的AP
                "health_per_gold": 0.38, # 每1金币的生命值
                "armor_per_gold": 0.05,  # 每1金币的护甲
                "mr_per_gold": 0.055     # 每1金币的魔抗
            },
            "utility_weights": {
                "cooldown_log_base": 1.5,  # CD效用对数底数
                "range_utility": 0.01,     # 每单位射程价值
                "duration_utility": 0.15   # 每秒持续时间价值
            }
        }

    def calculate_version_diff(self, patch_current: str, patch_previous: str,
                             entity_type: str) -> Dict[str, Dict[str, float]]:
        """计算版本间差异"""
        current_data = self._load_registry(patch_current, entity_type)
        previous_data = self._load_registry(patch_previous, entity_type)

        diffs = {}

        for entity_id in current_data:
            if entity_id in previous_data:
                entity_diff = self._calculate_entity_diff(
                    current_data[entity_id],
                    previous_data[entity_id],
                    entity_type
                )
                if entity_diff:  # 只保留有变化的实体
                    diffs[entity_id] = entity_diff

        return diffs

    def _load_registry(self, patch: str, entity_type: str) -> Dict[str, Any]:
        """加载注册表数据"""
        # 处理复数形式的目录名
        entity_dir_map = {
            "rune": "runes",
            "item": "items",
            "skill": "skills",
            "passive": "passives",
            "champion": "champions"
        }
        entity_dir = entity_dir_map.get(entity_type, entity_type)
        registry_path = f"registries/{entity_dir}/{patch}.json"
        try:
            with open(registry_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Registry file {registry_path} not found")
            return {}

    def _calculate_entity_diff(self, current: Dict[str, Any], previous: Dict[str, Any],
                             entity_type: str) -> Dict[str, float]:
        """计算单个实体的差异"""
        diffs = {}

        # 根据实体类型计算不同字段的差异
        if entity_type == "rune":
            diffs.update(self._diff_rune_fields(current, previous))
        elif entity_type == "item":
            diffs.update(self._diff_item_fields(current, previous))
        elif entity_type == "skill":
            diffs.update(self._diff_skill_fields(current, previous))
        elif entity_type == "passive":
            diffs.update(self._diff_passive_fields(current, previous))
        elif entity_type == "champion":
            diffs.update(self._diff_champion_fields(current, previous))

        return diffs

    def _diff_rune_fields(self, current: Dict, previous: Dict) -> Dict[str, float]:
        """计算符文字段差异"""
        diffs = {}

        # 自适应之力
        if "adaptive_force" in current and "adaptive_force" in previous:
            diffs["adaptive_force"] = self._percent_change(
                current["adaptive_force"], previous["adaptive_force"]
            )

        # 阈值伤害
        if "threshold_damage" in current and "threshold_damage" in previous:
            diffs["threshold_damage"] = self._percent_change(
                current["threshold_damage"], previous["threshold_damage"]
            )

        # 缩放因子
        if "scaling_factor" in current and "scaling_factor" in previous:
            diffs["scaling_factor"] = self._percent_change(
                current["scaling_factor"], previous["scaling_factor"]
            )

        # 冷却时间
        if "cooldown" in current and "cooldown" in previous:
            diffs["cooldown"] = self._cooldown_utility_change(
                current["cooldown"], previous["cooldown"]
            )

        return diffs

    def _diff_item_fields(self, current: Dict, previous: Dict) -> Dict[str, float]:
        """计算装备字段差异"""
        diffs = {}

        # 基础属性
        for stat in ["attack_damage", "ability_power", "health", "armor", "magic_resist"]:
            if stat in current and stat in previous:
                diffs[stat] = self._percent_change(current[stat], previous[stat])

        # 金币效率
        if "gold_cost" in current and "gold_cost" in previous:
            # 估算金币效率变化
            gold_eff_current = self._calculate_item_gold_efficiency(current)
            gold_eff_previous = self._calculate_item_gold_efficiency(previous)
            diffs["gold_efficiency"] = self._percent_change(gold_eff_current, gold_eff_previous)

        # 主动技能护盾
        if "active_shield" in current and "active_shield" in previous:
            diffs["active_shield"] = self._percent_change(
                current["active_shield"], previous["active_shield"]
            )

        return diffs

    def _diff_skill_fields(self, current: Dict, previous: Dict) -> Dict[str, float]:
        """计算技能字段差异"""
        diffs = {}

        # 基础伤害
        if "base_damage" in current and "base_damage" in previous:
            # 取最高等级的基础伤害
            current_dmg = current["base_damage"][-1] if isinstance(current["base_damage"], list) else current["base_damage"]
            previous_dmg = previous["base_damage"][-1] if isinstance(previous["base_damage"], list) else previous["base_damage"]
            diffs["base_damage"] = self._percent_change(current_dmg, previous_dmg)

        # AD/AP 缩放
        for ratio in ["ad_ratio", "ap_ratio"]:
            if ratio in current and ratio in previous:
                diffs[ratio] = self._percent_change(current[ratio], previous[ratio])

        # 冷却时间
        if "cooldown" in current and "cooldown" in previous:
            current_cd = current["cooldown"][0] if isinstance(current["cooldown"], list) else current["cooldown"]
            previous_cd = previous["cooldown"][0] if isinstance(previous["cooldown"], list) else previous["cooldown"]
            diffs["cooldown"] = self._cooldown_utility_change(current_cd, previous_cd)

        # 法力消耗
        if "mana_cost" in current and "mana_cost" in previous:
            current_cost = current["mana_cost"][0] if isinstance(current["mana_cost"], list) else current["mana_cost"]
            previous_cost = previous["mana_cost"][0] if isinstance(previous["mana_cost"], list) else previous["mana_cost"]
            diffs["mana_cost"] = self._percent_change(current_cost, previous_cost) * -1  # 消耗降低是正向

        return diffs

    def _diff_passive_fields(self, current: Dict, previous: Dict) -> Dict[str, float]:
        """计算被动技能字段差异"""
        diffs = {}

        # 移动速度
        if "movement_speed" in current and "movement_speed" in previous:
            diffs["movement_speed"] = self._percent_change(
                current["movement_speed"], previous["movement_speed"]
            )

        # 攻击速度
        if "attack_speed" in current and "attack_speed" in previous:
            diffs["attack_speed"] = self._percent_change(
                current["attack_speed"], previous["attack_speed"]
            )

        # 持续时间
        if "duration" in current and "duration" in previous:
            diffs["duration"] = self._percent_change(current["duration"], previous["duration"])

        return diffs

    def _diff_champion_fields(self, current: Dict, previous: Dict) -> Dict[str, float]:
        """计算英雄字段差异"""
        diffs = {}

        # 基础属性
        if "base_stats" in current and "base_stats" in previous:
            base_change = 0
            for stat in ["health", "attack_damage", "armor", "magic_resist"]:
                if stat in current["base_stats"] and stat in previous["base_stats"]:
                    base_change += self._percent_change(
                        current["base_stats"][stat], previous["base_stats"][stat]
                    )
            diffs["base_stats"] = base_change / 4  # 平均值

        # 成长属性
        if "stat_growth" in current and "stat_growth" in previous:
            growth_change = 0
            for stat in ["health_per_level", "ad_per_level"]:
                if stat in current["stat_growth"] and stat in previous["stat_growth"]:
                    growth_change += self._percent_change(
                        current["stat_growth"][stat], previous["stat_growth"][stat]
                    )
            diffs["stat_growth"] = growth_change / 2

        return diffs

    def calculate_shock_v2(self, entity_diffs: Dict[str, float], entity_type: str,
                          usage_weight: float = 1.0) -> Tuple[float, Dict[str, float]]:
        """计算 Shock v2 综合得分"""
        if entity_type not in self.config:
            logger.warning(f"No config for entity type: {entity_type}")
            return 0.0, {}

        weights = self.config[entity_type]
        components = {}
        weighted_z_scores = []

        # 计算各组件的 z-score
        for component_name, raw_delta in entity_diffs.items():
            if component_name in weights:
                # 标准化为 z-score (需要历史分布数据,这里用简化版本)
                z_score = self._standardize_delta(raw_delta, component_name, entity_type)

                # 应用权重
                weighted_z = z_score * weights[component_name] * usage_weight
                weighted_z_scores.append(weighted_z)

                components[component_name] = z_score

        # 综合 shock 得分
        shock_v2 = sum(weighted_z_scores)

        return shock_v2, components

    def _standardize_delta(self, delta: float, component: str, entity_type: str) -> float:
        """将原始变化标准化为 z-score"""
        # 简化版本：使用固定的标准化参数
        # 实际应该基于历史分布计算 MAD/MEDIAN

        standardization_params = {
            "rune": {"median": 0.0, "mad": 0.15},
            "item": {"median": 0.0, "mad": 0.12},
            "skill": {"median": 0.0, "mad": 0.18},
            "passive": {"median": 0.0, "mad": 0.20},
            "champion": {"median": 0.0, "mad": 0.10}
        }

        params = standardization_params.get(entity_type, {"median": 0.0, "mad": 0.15})

        # 使用 MAD (Median Absolute Deviation) 作为稳健的标准差估计
        z_score = (delta - params["median"]) / max(params["mad"], 0.01)

        # 限制极值
        return np.clip(z_score, -5.0, 5.0)

    def _percent_change(self, current: float, previous: float) -> float:
        """计算百分比变化"""
        if previous == 0:
            return 0.0 if current == 0 else 1.0
        return (current - previous) / abs(previous)

    def _cooldown_utility_change(self, current_cd: float, previous_cd: float) -> float:
        """计算冷却时间效用变化（对数效用）"""
        if previous_cd <= 0 or current_cd <= 0:
            return 0.0

        log_base = self.theory_params["utility_weights"]["cooldown_log_base"]

        # CD 降低是正向的，用负号表示
        utility_change = np.log(previous_cd / current_cd) / np.log(log_base)
        return utility_change

    def _calculate_item_gold_efficiency(self, item_data: Dict[str, Any]) -> float:
        """计算装备金币效率"""
        efficiency = 0.0
        gold_costs = self.theory_params["gold_efficiency"]

        for stat, value in item_data.items():
            if stat in gold_costs and isinstance(value, (int, float)):
                efficiency += value * gold_costs[stat]

        total_cost = item_data.get("gold_cost", 1)
        return efficiency / max(total_cost, 1)

def create_sample_registries():
    """创建样例注册表文件"""

    # 符文样例
    rune_data = {
        "8128": {  # 黑暗收割
            "name": "Dark Harvest",
            "adaptive_force": 8.0,
            "threshold_damage": 20.0,
            "scaling_factor": 0.25,
            "cooldown": 45.0,
            "tree": "DOMINATION",
            "position": "KEYSTONE"
        },
        "8143": {  # 电刑
            "name": "Electrocute",
            "adaptive_force": 10.0,
            "threshold_damage": 30.0,
            "scaling_factor": 0.40,
            "cooldown": 25.0,
            "tree": "DOMINATION",
            "position": "KEYSTONE"
        }
    }

    # 装备样例
    item_data = {
        "6692": {  # 日食
            "name": "Eclipse",
            "attack_damage": 55,
            "lethality": 12,
            "omnivamp": 8,
            "gold_cost": 3100,
            "active_shield": 180
        },
        "6691": {  # 德拉克萨的暮刃
            "name": "Duskblade of Draktharr",
            "attack_damage": 60,
            "lethality": 18,
            "ability_haste": 15,
            "gold_cost": 3100
        }
    }

    # 技能样例 (金克丝 Q)
    skill_data = {
        "150_Q": {
            "name": "Switcheroo!",
            "base_damage": [0, 0, 0, 0, 0],  # Q技能不是直接伤害
            "ad_ratio": 1.1,  # 火炮形态 AD 加成
            "range": [525, 600, 675, 750, 825],
            "mana_cost": [20, 20, 20, 20, 20],
            "cooldown": [0.9, 0.9, 0.9, 0.9, 0.9]
        }
    }

    # 保存到文件
    registries = [
        ("runes", rune_data),
        ("items", item_data),
        ("skills", skill_data)
    ]

    for entity_type, data in registries:
        for patch in ["14.18.1", "14.19.1"]:
            path = Path(f"registries/{entity_type}")
            path.mkdir(parents=True, exist_ok=True)

            # 对 14.19.1 制造一些变化
            if patch == "14.19.1":
                modified_data = data.copy()
                if entity_type == "runes":
                    # 黑暗收割 buff
                    modified_data["8128"]["adaptive_force"] = 9.0  # 8.0 -> 9.0
                    modified_data["8128"]["cooldown"] = 40.0      # 45.0 -> 40.0
                elif entity_type == "items":
                    # 日食 nerf
                    modified_data["6692"]["attack_damage"] = 50   # 55 -> 50
                    modified_data["6692"]["lethality"] = 10       # 12 -> 10
                data = modified_data

            with open(f"registries/{entity_type}/{patch}.json", 'w') as f:
                json.dump(data, f, indent=2)

    logger.info("Created sample registry files for patches 14.18.1 and 14.19.1")

def main():
    parser = argparse.ArgumentParser(description="Shock v2 计算工具")
    parser.add_argument("--patch", required=True, help="当前版本")
    parser.add_argument("--prev-patch", help="前一版本（默认自动推断）")
    parser.add_argument("--weights", default="configs/shock_weights.yml", help="权重配置文件")
    parser.add_argument("--entity-type", choices=["rune", "item", "skill", "passive", "champion"], help="实体类型")
    parser.add_argument("--create-samples", action="store_true", help="创建样例注册表")

    args = parser.parse_args()

    if args.create_samples:
        create_sample_registries()
        return

    calculator = ShockCalculatorV2(args.weights)

    # 自动推断前一版本
    prev_patch = args.prev_patch
    if not prev_patch:
        # 简化版本号递减
        parts = args.patch.split('.')
        if len(parts) >= 2:
            minor = int(parts[1])
            prev_patch = f"{parts[0]}.{minor-1}.1"

    logger.info(f"计算 Shock v2: {prev_patch} -> {args.patch}")

    # 处理所有实体类型或指定类型
    entity_types = [args.entity_type] if args.entity_type else ["rune", "item", "skill"]

    results = {}

    for entity_type in entity_types:
        logger.info(f"处理 {entity_type} 实体...")

        # 计算版本差异
        diffs = calculator.calculate_version_diff(args.patch, prev_patch, entity_type)

        # 计算 shock 得分
        entity_results = {}
        for entity_id, entity_diff in diffs.items():
            shock_v2, components = calculator.calculate_shock_v2(entity_diff, entity_type)

            entity_results[entity_id] = {
                "raw_diffs": entity_diff,
                "shock_v2": shock_v2,
                "shock_components": components
            }

        results[entity_type] = entity_results

        logger.info(f"{entity_type}: 处理了 {len(entity_results)} 个实体")

    # 保存结果
    output_path = f"registries/diff/{args.patch}.json"
    Path("registries/diff").mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Shock v2 结果已保存到: {output_path}")

    # 打印 Top 变化
    print(f"\n📊 Shock v2 Top 变化 ({prev_patch} -> {args.patch}):")
    for entity_type, entities in results.items():
        if entities:
            print(f"\n{entity_type.upper()}:")
            sorted_entities = sorted(entities.items(), key=lambda x: abs(x[1]["shock_v2"]), reverse=True)
            for entity_id, data in sorted_entities[:3]:
                shock = data["shock_v2"]
                sign = "📈" if shock > 0 else "📉"
                print(f"  {sign} {entity_id}: {shock:.2f}")

if __name__ == "__main__":
    main()