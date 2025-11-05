#!/usr/bin/env python3
"""
Combat Power (cp_t) and Delta Combat Power (delta_cp) Metrics
Calculates combat power at levels 15/25/35 and comparative analysis
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import pandas as pd
import numpy as np
from scipy import stats

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'dimensions'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'transforms'))

from utils import format_output_precision, load_user_mode_config
from governance_framework import DataGovernanceFramework
from dim_item_passive import DimItemPassive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CombatPowerAnalyzer:
    """Analyzes combat power and comparative differences"""
    
    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize analyzer with configuration and dimension tables"""
        self.config = load_user_mode_config(config_path)
        self.governance = DataGovernanceFramework()
        
        # Initialize dimension tables
        self.item_passive = DimItemPassive()
        
        # Combat power weights (from user requirements)
        self.cp_weights = {
            "damage": 1.0,
            "survivability": 0.6,
            "crowd_control": 0.4,
            "mobility": 0.2
        }
        
        # Level breakpoints
        self.level_breakpoints = [15, 25, 35]  # Early, mid, late game
        
    def get_champion_base_stats(self, champion_id: int, level: int) -> Dict[str, float]:
        """
        Get champion base stats at given level
        This is a simplified implementation - in production would use champion data
        """
        # Simplified base stats scaling
        # In production, this would load from champion dimension table
        base_stats = {
            "base_attack_damage": 50 + (level - 1) * 3,
            "base_health": 500 + (level - 1) * 80,
            "base_armor": 20 + (level - 1) * 3,
            "base_magic_resistance": 30 + (level - 1) * 1.25,
            "base_attack_speed": 0.625 + (level - 1) * 0.02,
            "base_movement_speed": 325
        }
        
        return base_stats
        
    def calculate_combat_power_components(self, stats: Dict[str, float], level: int) -> Dict[str, float]:
        """Calculate the four combat power components from stats"""
        
        # Damage component (k_dmg = 1.0)
        damage = 0.0
        damage += stats.get("attack_damage", 0) * 1.0
        damage += stats.get("ability_power", 0) * 0.8
        damage += stats.get("attack_speed", 0) * 0.5  # AS as % value
        damage += stats.get("critical_strike_chance", 0) * 1.2  # Crit as % value
        damage += stats.get("lethality", 0) * 1.5
        damage += stats.get("magic_penetration", 0) * 1.5
        damage += stats.get("armor_penetration", 0) * 1.5  # % pen
        damage += stats.get("magic_penetration_percent", 0) * 1.5  # % pen
        
        # Survivability component (k_surv = 0.6)
        survivability = 0.0
        survivability += stats.get("health", 0) * 0.4
        survivability += stats.get("armor", 0) * 2.5
        survivability += stats.get("magic_resistance", 0) * 2.5
        survivability += stats.get("life_steal", 0) * 3.0  # LS as % value
        survivability += stats.get("omnivamp", 0) * 3.0  # Omnivamp as % value
        survivability += stats.get("health_regen", 0) * 1.0
        
        # Crowd control component (k_cc = 0.4)
        crowd_control = 0.0
        crowd_control += stats.get("ability_haste", 0) * 1.5
        crowd_control += stats.get("mana", 0) * 0.1  # Mana for spell casting
        crowd_control += stats.get("mana_regen", 0) * 0.5
        
        # Mobility component (k_mob = 0.2)
        mobility = 0.0
        mobility += stats.get("movement_speed", 0) * 2.0
        
        return {
            "damage": damage,
            "survivability": survivability,
            "crowd_control": crowd_control,
            "mobility": mobility
        }
        
    def calculate_total_combat_power(self, champion_id: int, item_build: List[int], level: int, patch_version: str = "14.1") -> Dict[str, Any]:
        """Calculate total combat power for champion + item build at given level"""
        
        # Get champion base stats
        base_stats = self.get_champion_base_stats(champion_id, level)
        
        # Combine stats from items
        total_stats = base_stats.copy()
        valid_items = []
        
        for item_id in item_build:
            item_stats = self.item_passive.get_item_stat_vector(item_id)
            if item_stats:
                valid_items.append(item_id)
                for stat, value in item_stats.items():
                    total_stats[stat] = total_stats.get(stat, 0) + value
                    
        # Calculate combat power components
        cp_components = self.calculate_combat_power_components(total_stats, level)
        
        # Apply weights and calculate total
        weighted_cp = {
            component: value * self.cp_weights[component] 
            for component, value in cp_components.items()
        }
        
        total_cp = sum(weighted_cp.values())
        
        # Determine governance tag
        governance_tag = self._determine_cp_governance_tag(len(valid_items), len(item_build), level)
        
        return {
            "champion_id": champion_id,
            "level": level,
            "item_build": item_build,
            "valid_items": valid_items,
            "total_stats": total_stats,
            "cp_components": cp_components,
            "weighted_cp": weighted_cp,
            "total_combat_power": total_cp,
            "governance_tag": governance_tag,
            "patch_version": patch_version
        }
        
    def _determine_cp_governance_tag(self, valid_items: int, total_items: int, level: int) -> str:
        """Determine governance quality for combat power calculation"""
        
        item_coverage = valid_items / total_items if total_items > 0 else 0
        
        # CONFIDENT: Good item coverage, reasonable level
        if item_coverage >= 0.8 and level >= 15:
            return "CONFIDENT"
        # CAUTION: Partial item coverage or early level
        elif item_coverage >= 0.5 and level >= 10:
            return "CAUTION"
        # CONTEXT: Poor coverage or very early level
        else:
            return "CONTEXT"
            
    def analyze_build_progression(self, champion_id: int, item_build: List[int], patch_version: str = "14.1") -> Dict[str, Any]:
        """Analyze combat power progression across all level breakpoints"""
        
        progression = {}
        
        for level in self.level_breakpoints:
            cp_data = self.calculate_total_combat_power(champion_id, item_build, level, patch_version)
            progression[f"level_{level}"] = cp_data
            
        # Calculate growth rates
        growth_rates = {}
        levels = self.level_breakpoints
        
        for i in range(1, len(levels)):
            prev_level = f"level_{levels[i-1]}"
            curr_level = f"level_{levels[i]}"
            
            prev_cp = progression[prev_level]["total_combat_power"]
            curr_cp = progression[curr_level]["total_combat_power"]
            
            growth_rate = (curr_cp - prev_cp) / prev_cp if prev_cp > 0 else 0
            growth_rates[f"{levels[i-1]}_to_{levels[i]}"] = growth_rate
            
        return {
            "champion_id": champion_id,
            "item_build": item_build,
            "progression": progression,
            "growth_rates": growth_rates,
            "patch_version": patch_version
        }
        
    def calculate_delta_combat_power(self, build_a: Dict[str, Any], build_b: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate combat power differences between two builds"""
        
        deltas = {}
        
        # Compare at each level
        for level in self.level_breakpoints:
            level_key = f"level_{level}"
            
            if level_key in build_a["progression"] and level_key in build_b["progression"]:
                cp_a = build_a["progression"][level_key]["total_combat_power"]
                cp_b = build_b["progression"][level_key]["total_combat_power"]
                
                delta = cp_a - cp_b
                delta_percent = (delta / cp_b * 100) if cp_b > 0 else 0
                
                deltas[level_key] = {
                    "absolute_delta": delta,
                    "percent_delta": delta_percent,
                    "build_a_cp": cp_a,
                    "build_b_cp": cp_b
                }
                
        # Calculate statistical significance using Wilson CI framework
        # Simplified implementation - in production would use more sophisticated analysis
        overall_delta = np.mean([d["absolute_delta"] for d in deltas.values()])
        overall_percent = np.mean([d["percent_delta"] for d in deltas.values()])
        
        # Determine governance tag based on delta magnitude and consistency
        governance_tag = self._determine_delta_governance_tag(deltas)
        
        return {
            "comparison": f"Build_A vs Build_B",
            "level_deltas": deltas,
            "overall_delta": float(overall_delta),
            "overall_percent_delta": float(overall_percent),
            "governance_tag": governance_tag,
            "significant_difference": bool(abs(overall_percent) > 5.0)  # >5% difference
        }
        
    def _determine_delta_governance_tag(self, deltas: Dict[str, Any]) -> str:
        """Determine governance quality for delta combat power"""
        
        if len(deltas) == 3:  # All levels calculated
            delta_consistency = np.std([d["percent_delta"] for d in deltas.values()])
            
            if delta_consistency < 10:  # Consistent deltas
                return "CONFIDENT"
            elif delta_consistency < 20:  # Moderately consistent
                return "CAUTION"
                
        return "CONTEXT"
        
    def export_combat_power_analysis(self, sample_builds: List[Tuple[int, List[int]]], 
                                   patch_version: str = "14.1", 
                                   output_dir: str = "out/quantitative/") -> Dict[str, Any]:
        """Analyze combat power for sample builds and export results"""
        
        # Analyze each build
        build_analyses = []
        
        for champion_id, item_build in sample_builds:
            analysis = self.analyze_build_progression(champion_id, item_build, patch_version)
            build_analyses.append(analysis)
            
        # Calculate delta combat power for build comparisons
        delta_analyses = []
        
        for i in range(len(build_analyses)):
            for j in range(i + 1, len(build_analyses)):
                delta = self.calculate_delta_combat_power(build_analyses[i], build_analyses[j])
                delta["build_a_champion"] = build_analyses[i]["champion_id"]
                delta["build_b_champion"] = build_analyses[j]["champion_id"]
                delta_analyses.append(delta)
                
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Prepare export data
        export_data = {
            "metadata": {
                "metric_types": ["cp_t", "delta_cp"],
                "description": "Combat power analysis at levels 15/25/35",
                "patch_version": patch_version,
                "record_count": len(build_analyses),
                "delta_count": len(delta_analyses),
                "generated_at": pd.Timestamp.now().isoformat(),
                "governance_enabled": True
            },
            "cp_weights": self.cp_weights,
            "level_breakpoints": self.level_breakpoints,
            "combat_power_analysis": build_analyses,
            "delta_combat_power": delta_analyses,
            "governance_distribution": self._analyze_cp_governance_distribution(build_analyses, delta_analyses)
        }
        
        # Save to files
        patch_suffix = f"_patch_{patch_version}" if patch_version != "14.1" else ""
        
        # Combat power file
        cp_file = output_path / f"combat_power_analysis{patch_suffix}.json"
        with open(cp_file, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Exported combat power analysis to {cp_file}")
        
        return export_data
        
    def _analyze_cp_governance_distribution(self, cp_analyses: List[Dict], delta_analyses: List[Dict]) -> Dict[str, Dict[str, int]]:
        """Analyze governance distribution for CP analyses"""
        
        cp_distribution = {"CONFIDENT": 0, "CAUTION": 0, "CONTEXT": 0}
        delta_distribution = {"CONFIDENT": 0, "CAUTION": 0, "CONTEXT": 0}
        
        # Analyze CP governance
        for analysis in cp_analyses:
            for level_key, level_data in analysis["progression"].items():
                tag = level_data.get("governance_tag", "CONTEXT")
                if tag in cp_distribution:
                    cp_distribution[tag] += 1
                    
        # Analyze delta governance
        for analysis in delta_analyses:
            tag = analysis.get("governance_tag", "CONTEXT")
            if tag in delta_distribution:
                delta_distribution[tag] += 1
                
        return {
            "combat_power": cp_distribution,
            "delta_combat_power": delta_distribution
        }


def main():
    """Demo usage of combat power analyzer"""
    analyzer = CombatPowerAnalyzer()
    
    print("⚔️ COMBAT POWER ANALYSIS")
    print("=" * 50)
    
    # Test sample builds
    sample_builds = [
        # (champion_id, [item_build])
        (1, [1055, 3031, 3078, 3006, 3142]),  # Sample ADC build
        (34, [1056, 3040, 3020, 3089, 3157]),  # Sample AP build  
        (12, [3869, 3190, 3107, 3111, 3158])   # Sample Support build
    ]
    
    print("\n📊 Sample Build Analysis:")
    
    for champion_id, item_build in sample_builds[:2]:  # Test first 2 builds
        print(f"\nChampion {champion_id} Build: {item_build}")
        
        # Analyze progression
        progression = analyzer.analyze_build_progression(champion_id, item_build)
        
        print("Combat Power Progression:")
        for level in analyzer.level_breakpoints:
            level_key = f"level_{level}"
            if level_key in progression["progression"]:
                cp_data = progression["progression"][level_key]
                total_cp = cp_data["total_combat_power"]
                components = cp_data["weighted_cp"]
                
                print(f"  Level {level}: {total_cp:.0f} CP")
                print(f"    Damage: {components['damage']:.0f}, Surv: {components['survivability']:.0f}")
                print(f"    CC: {components['crowd_control']:.0f}, Mobility: {components['mobility']:.0f}")
                print(f"    Governance: {cp_data['governance_tag']}")
                
        # Show growth rates
        print("Growth Rates:")
        for period, rate in progression["growth_rates"].items():
            print(f"  {period}: {rate:.1%}")
            
    # Run full analysis
    print("\n📈 Running Full Combat Power Analysis...")
    results = analyzer.export_combat_power_analysis(sample_builds)
    
    print(f"\n✅ ANALYSIS COMPLETE:")
    print(f"  ⚔️ Build analyses: {results['metadata']['record_count']}")
    print(f"  📊 Delta comparisons: {results['metadata']['delta_count']}")
    print(f"  🎯 Level breakpoints: {results['level_breakpoints']}")
    
    # Show governance quality
    gov_dist = results['governance_distribution']
    print(f"\n🏛️ DATA GOVERNANCE QUALITY:")
    
    for metric_type, distribution in gov_dist.items():
        total = sum(distribution.values())
        print(f"  {metric_type.upper()}:")
        for tag, count in distribution.items():
            percentage = count / total * 100 if total > 0 else 0
            print(f"    {tag}: {count} records ({percentage:.1f}%)")
            
    # Show sample delta analysis
    if results['delta_combat_power']:
        delta_sample = results['delta_combat_power'][0]
        print(f"\n🔄 SAMPLE DELTA ANALYSIS:")
        print(f"  Comparison: Champion {delta_sample['build_a_champion']} vs {delta_sample['build_b_champion']}")
        print(f"  Overall Delta: {delta_sample['overall_percent_delta']:.1f}%")
        print(f"  Significant: {delta_sample['significant_difference']}")
        
        for level_key, delta_data in delta_sample['level_deltas'].items():
            level = level_key.replace('level_', '')
            print(f"  Level {level}: {delta_data['percent_delta']:.1f}% delta")


if __name__ == "__main__":
    main()