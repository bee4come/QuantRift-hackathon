#!/usr/bin/env python3
"""
Damage per Cooldown Analysis (dmg_per_cd)
Calculates damage efficiency metrics for champion abilities
"""

import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'dimensions'))

from utils import generate_row_id, format_output_precision
from statistical_utils import wilson_confidence_interval
from dim_ability import DimAbility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DamageEfficiencyResult:
    """Single ability damage efficiency result"""
    champion_id: int
    champion_name: str
    ability_key: str
    ability_name: str
    base_damage: float
    total_damage: float  # With scaling
    cooldown: float
    damage_per_cd: float
    damage_type: str
    ability_type: str
    efficiency_tier: str  # "S", "A", "B", "C", "D"
    patch_version: str
    governance_tag: str
    confidence_interval: Tuple[float, float]
    scaling_contribution: float  # % damage from scaling
    notes: str

class DamageEfficiencyAnalyzer:
    """Analyzes damage per cooldown efficiency for champion abilities"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize with ability dimension data"""
        self.config_path = config_path
        self.dim_abilities = DimAbility()

        # Standard stat assumptions for mid-game (level 9)
        self.standard_stats = {
            "ad_carry": {"bonus_ad": 90, "ap": 20, "level": 9},
            "ap_carry": {"bonus_ad": 30, "ap": 120, "level": 9},
            "assassin": {"bonus_ad": 110, "ap": 40, "level": 9},
            "tank": {"bonus_ad": 50, "ap": 30, "level": 9},
            "support": {"bonus_ad": 25, "ap": 80, "level": 9}
        }

        # Efficiency tier thresholds (damage per second of cooldown)
        self.efficiency_tiers = {
            "S": 50.0,   # Elite efficiency
            "A": 35.0,   # High efficiency
            "B": 25.0,   # Good efficiency
            "C": 15.0,   # Average efficiency
            "D": 0.0     # Below average
        }

    def analyze_ability_efficiency(self, champion_id: int, ability_key: str,
                                 archetype: str = "ad_carry",
                                 patch_version: str = "14.1") -> Optional[DamageEfficiencyResult]:
        """Analyze damage efficiency for a single ability"""
        ability = self.dim_abilities.get_ability_data(champion_id, ability_key, patch_version)
        if not ability:
            return None

        # Skip non-damage abilities
        if ability.ability_type not in ["damage", "mixed"]:
            return None

        # Get appropriate stats for archetype
        stats = self.standard_stats.get(archetype, self.standard_stats["ad_carry"])

        # Calculate total damage with scaling
        total_damage = ability.base_damage
        scaling_damage = 0.0

        if ability.ad_ratio > 0:
            ad_scaling = ability.ad_ratio * stats["bonus_ad"]
            scaling_damage += ad_scaling
            total_damage += ad_scaling

            if ability.ap_ratio > 0:
                ap_scaling = ability.ap_ratio * stats["ap"]
                scaling_damage += ap_scaling
                total_damage += ap_scaling

            # Calculate damage per cooldown
            if ability.cooldown == 0:
                # Special case for toggle abilities or passives
                damage_per_cd = 0.0
                governance_tag = "CONTEXT"
                confidence = (0.0, 0.0)
            else:
                damage_per_cd = total_damage / ability.cooldown
                # High confidence for damage abilities with reasonable cooldowns
                governance_tag = "CONFIDENT" if damage_per_cd > 10 else "CAUTION"

        # Calculate scaling contribution percentage
        scaling_contribution = (scaling_damage / max(total_damage, 1.0)) * 100

        # Calculate confidence interval
        if governance_tag == "CONFIDENT":
            _, ci_lower, ci_upper = wilson_confidence_interval(85, 100)
            confidence = (ci_lower, ci_upper)
        else:
            _, ci_lower, ci_upper = wilson_confidence_interval(70, 100)
            confidence = (ci_lower, ci_upper)

        # Determine efficiency tier
        efficiency_tier = self._calculate_efficiency_tier(damage_per_cd)

        return DamageEfficiencyResult(
            champion_id=ability.champion_id,
            champion_name=ability.champion_name,
            ability_key=ability.ability_key,
            ability_name=ability.ability_name,
            base_damage=ability.base_damage,
            total_damage=total_damage,
            cooldown=ability.cooldown,
            damage_per_cd=damage_per_cd,
            damage_type=ability.damage_type,
            ability_type=ability.ability_type,
            efficiency_tier=efficiency_tier,
            patch_version=patch_version,
            governance_tag=governance_tag,
            confidence_interval=confidence,
            scaling_contribution=scaling_contribution,
            notes=f"Archetype: {archetype}, {ability.notes or 'No notes'}"
        )

    def analyze_champion_efficiency(self, champion_id: int, archetype: str = "ad_carry",
                                  patch_version: str = "14.1") -> List[DamageEfficiencyResult]:
        """Analyze all damage abilities for a champion"""
        abilities = self.dim_abilities.get_damage_abilities_for_champion(champion_id, patch_version)
        results = []

        for ability in abilities:
            result = self.analyze_ability_efficiency(
                champion_id, ability.ability_key, archetype, patch_version
            )
            if result:
                results.append(result)

        # Sort by damage per cooldown (descending)
        return sorted(results, key=lambda x: x.damage_per_cd, reverse=True)

    def analyze_multiple_champions(self, champion_archetypes: List[Tuple[int, str]],
                                 patch_version: str = "14.1") -> List[DamageEfficiencyResult]:
        """Analyze multiple champions with their archetypes"""
        all_results = []

        for champion_id, archetype in champion_archetypes:
            champion_results = self.analyze_champion_efficiency(champion_id, archetype, patch_version)
            all_results.extend(champion_results)

        # Sort by damage per cooldown globally
        return sorted(all_results, key=lambda x: x.damage_per_cd, reverse=True)

    def export_efficiency_analysis(self, champion_archetypes: List[Tuple[int, str]] = None,
                                 patch_version: str = "14.1",
                                 output_dir: str = "out/quantitative/") -> Dict[str, Any]:
        """Export comprehensive damage efficiency analysis"""
        if champion_archetypes is None:
            # Default high-frequency champions from attach_rate analysis
            champion_archetypes = [
                (222, "ad_carry"),   # Jinx
                (51, "ad_carry"),    # Caitlyn
                (22, "ad_carry"),    # Ashe
                (157, "assassin"),   # Yasuo
                (81, "ad_carry"),    # Ezreal
                (67, "ad_carry"),    # Vayne
                (134, "ap_carry"),   # Syndra
                (26, "support"),     # Zillean
                (25, "support"),     # Morgana
                (117, "support"),    # Lulu
                (64, "assassin"),    # Lee Sin
                (86, "tank"),        # Garen
                (122, "tank"),       # Darius
                (145, "ad_carry"),   # Kai'Sa
                (12, "tank")         # Alistar
            ]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Analyze all champions
        all_results = self.analyze_multiple_champions(champion_archetypes, patch_version)

        # Compile statistics
        governance_dist = {"CONFIDENT": 0, "CAUTION": 0, "CONTEXT": 0}
        tier_dist = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        archetype_stats = {}

        for result in all_results:
            governance_dist[result.governance_tag] += 1
            tier_dist[result.efficiency_tier] += 1

            # Track archetype performance
            if result.notes and "Archetype:" in result.notes:
                archetype = result.notes.split("Archetype: ")[1].split(",")[0]
                if archetype not in archetype_stats:
                    archetype_stats[archetype] = {"count": 0, "avg_efficiency": 0, "abilities": []}
                archetype_stats[archetype]["count"] += 1
                archetype_stats[archetype]["abilities"].append(result.damage_per_cd)

        # Calculate archetype averages
        for archetype in archetype_stats:
            abilities = archetype_stats[archetype]["abilities"]
            archetype_stats[archetype]["avg_efficiency"] = np.mean(abilities) if abilities else 0

        # Find top performers
        top_abilities = all_results[:10]  # Top 10 most efficient
        top_champions = self._get_top_champions_by_avg_efficiency(all_results)

        # Create export data
        export_data = {
            "metadata": {
                "analysis_type": "damage_per_cooldown",
                "patch_version": patch_version,
                "generated_at": datetime.now().isoformat(),
                "total_abilities": len(all_results),
                "champions_analyzed": len(champion_archetypes),
                "archetypes": list(archetype_stats.keys())
            },
            "summary": {
                "total_abilities_analyzed": len(all_results),
                "governance_distribution": governance_dist,
                "efficiency_tier_distribution": tier_dist,
                "archetype_performance": archetype_stats,
                "avg_damage_per_cd": np.mean([r.damage_per_cd for r in all_results]) if all_results else 0,
                "top_ability": {
                    "name": f"{top_abilities[0].champion_name} {top_abilities[0].ability_key}" if top_abilities else None,
                    "efficiency": top_abilities[0].damage_per_cd if top_abilities else 0
                },
                "most_efficient_champion": top_champions[0] if top_champions else None
            },
            "ability_efficiency_results": self._convert_results_to_export(all_results),
            "governance_distribution": governance_dist
        }

        # Save to file
        output_file = output_path / f"damage_efficiency_patch_{patch_version}.json"
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported damage efficiency analysis: {len(all_results)} abilities to {output_file}")
        return export_data

    def _calculate_efficiency_tier(self, damage_per_cd: float) -> str:
        """Calculate efficiency tier based on damage per cooldown"""
        for tier, threshold in self.efficiency_tiers.items():
            if damage_per_cd >= threshold:
                return tier
        return "D"

    def _get_top_champions_by_avg_efficiency(self, results: List[DamageEfficiencyResult]) -> List[Dict[str, Any]]:
        """Get champions ranked by average ability efficiency"""
        champion_efficiency = {}

        for result in results:
            champion_name = result.champion_name
            if champion_name not in champion_efficiency:
                champion_efficiency[champion_name] = {"abilities": [], "champion_id": result.champion_id}
            champion_efficiency[champion_name]["abilities"].append(result.damage_per_cd)

        # Calculate averages and sort
        champion_rankings = []
        for champion_name, data in champion_efficiency.items():
            avg_efficiency = np.mean(data["abilities"])
            champion_rankings.append({
                "champion_name": champion_name,
                "champion_id": data["champion_id"],
                "avg_damage_per_cd": avg_efficiency,
                "ability_count": len(data["abilities"])
            })

        return sorted(champion_rankings, key=lambda x: x["avg_damage_per_cd"], reverse=True)

    def _convert_results_to_export(self, results: List[DamageEfficiencyResult]) -> List[Dict[str, Any]]:
        """Convert analysis results to export format"""
        export_results = []

        for result in results:
            record = {
                "row_id": f"dmg_efficiency_{result.champion_id}_{result.ability_key}_{result.patch_version}",
                "champion_id": result.champion_id,
                "champion_name": result.champion_name,
                "ability_key": result.ability_key,
                "ability_name": result.ability_name,
                "base_damage": round(result.base_damage, 3),
                "total_damage": round(result.total_damage, 3),
                "cooldown": round(result.cooldown, 3),
                "damage_per_cd": round(result.damage_per_cd, 3),
                "damage_type": result.damage_type,
                "ability_type": result.ability_type,
                "efficiency_tier": result.efficiency_tier,
                "patch_version": result.patch_version,
                "governance_tag": result.governance_tag,
                "confidence_lower": round(result.confidence_interval[0], 3),
                "confidence_upper": round(result.confidence_interval[1], 3),
                "scaling_contribution_pct": round(result.scaling_contribution, 3),
                "notes": result.notes
            }
            export_results.append(record)

        return export_results

def main():
    """Test damage efficiency analysis"""
    analyzer = DamageEfficiencyAnalyzer()

    # Test single ability analysis
    jinx_w = analyzer.analyze_ability_efficiency(222, "W", "ad_carry")
    if jinx_w:
        print(f"Jinx W analysis:")
        print(f"  Total damage: {jinx_w.total_damage:.1f}")
        print(f"  Damage per CD: {jinx_w.damage_per_cd:.1f}")
        print(f"  Efficiency tier: {jinx_w.efficiency_tier}")
        print(f"  Governance: {jinx_w.governance_tag}")

    # Test champion analysis
    jinx_abilities = analyzer.analyze_champion_efficiency(222, "ad_carry")
    print(f"\nJinx ability efficiency ranking:")
    for i, ability in enumerate(jinx_abilities):
        print(f"  {i+1}. {ability.ability_key} ({ability.ability_name}): {ability.damage_per_cd:.1f}")

    # Test export
    export_data = analyzer.export_efficiency_analysis()
    print(f"\nExported damage efficiency analysis:")
    print(f"  Total abilities: {export_data['metadata']['total_abilities']}")
    print(f"  Champions: {export_data['metadata']['champions_analyzed']}")
    print(f"  Top ability: {export_data['summary']['top_ability']['name']} ({export_data['summary']['top_ability']['efficiency']:.1f})")

if __name__ == "__main__":
    main()