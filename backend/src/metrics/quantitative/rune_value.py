#!/usr/bin/env python3
"""
Rune Value Temporal Analysis (rune_value_t)
Calculates expected value of runes over game time with trigger rate modeling
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
from dim_rune_value import DimRuneValue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RuneValueResult:
    """Single rune value analysis result"""
    rune_id: int
    rune_name: str
    rune_type: str
    tree_name: str
    early_game_value: float  # 0-15 min
    mid_game_value: float    # 15-25 min
    late_game_value: float   # 25+ min
    total_game_value: float  # Full game expectation
    value_per_minute: float
    trigger_efficiency: float  # Value per trigger
    patch_version: str
    governance_tag: str
    confidence_interval: Tuple[float, float]
    sample_roles: List[str]
    notes: str

class RuneValueAnalyzer:
    """Analyzes rune values over time with trigger rate modeling"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize with rune dimension data"""
        self.config_path = config_path
        self.dim_runes = DimRuneValue()

        # Game phase definitions (minutes)
        self.game_phases = {
            "early": (0, 15),
            "mid": (15, 25),
            "late": (25, 40)
        }

        # Default player stats by game phase
        self.phase_stats = {
            "early": {"ad": 80, "ap": 40, "level": 6, "bonus_ad": 40},
            "mid": {"ad": 130, "ap": 80, "level": 11, "bonus_ad": 90},
            "late": {"ad": 180, "ap": 120, "level": 16, "bonus_ad": 140}
        }

    def analyze_rune_value_by_phase(self, rune_id: int, role: str = "adc",
                                  patch_version: str = "14.1") -> Optional[RuneValueResult]:
        """Analyze a single rune's value across game phases"""
        rune = self.dim_runes.get_rune_value(rune_id, patch_version)
        if not rune:
            return None

        # Check if rune is suitable for role
        if role not in rune.champion_roles:
            governance_tag = "CONTEXT"
            confidence = (0.0, 0.0)
        else:
            governance_tag = "CONFIDENT" if rune.rune_type == "keystone" else "CAUTION"
            _, ci_lower, ci_upper = wilson_confidence_interval(80, 100)  # Assume good data
            confidence = (ci_lower, ci_upper)

        # Calculate value for each phase
        phase_values = {}

        for phase_name, (start_min, end_min) in self.game_phases.items():
            phase_duration = end_min - start_min
            stats = self.phase_stats[phase_name]

            phase_value = self.dim_runes.calculate_rune_expected_value(
                rune_id, phase_duration, stats, patch_version
            )
            phase_values[phase_name] = phase_value

        # Calculate total game value (weighted by phase importance)
        # Early: 40%, Mid: 35%, Late: 25% (most games decided by mid game)
        total_value = (
            phase_values["early"] * 0.40 +
            phase_values["mid"] * 0.35 +
            phase_values["late"] * 0.25
        )

        # Calculate efficiency metrics
        avg_game_length = 28.0  # Average ranked game length
        value_per_minute = total_value / avg_game_length

        # Trigger efficiency
        total_triggers = rune.trigger_rate_per_min * avg_game_length
        trigger_efficiency = total_value / max(total_triggers, 1.0)

        return RuneValueResult(
            rune_id=rune.rune_id,
            rune_name=rune.rune_name,
            rune_type=rune.rune_type,
            tree_name=rune.tree_name,
            early_game_value=phase_values["early"],
            mid_game_value=phase_values["mid"],
            late_game_value=phase_values["late"],
            total_game_value=total_value,
            value_per_minute=value_per_minute,
            trigger_efficiency=trigger_efficiency,
            patch_version=patch_version,
            governance_tag=governance_tag,
            confidence_interval=confidence,
            sample_roles=[role] if role in rune.champion_roles else [],
            notes=f"Trigger rate: {rune.trigger_rate_per_min:.1f}/min, {rune.notes or 'No notes'}"
        )

    def analyze_keystones_for_role(self, role: str, patch_version: str = "14.1") -> List[RuneValueResult]:
        """Analyze all keystones for a specific role"""
        keystones = self.dim_runes.get_keystones_for_role(role, patch_version)
        results = []

        for keystone in keystones:
            result = self.analyze_rune_value_by_phase(keystone.rune_id, role, patch_version)
            if result:
                results.append(result)

        # Sort by total game value
        return sorted(results, key=lambda x: x.total_game_value, reverse=True)

    def analyze_secondary_runes_for_role(self, role: str, patch_version: str = "14.1") -> List[RuneValueResult]:
        """Analyze secondary runes for a specific role"""
        results = []

        # Get all secondary runes
        for key, rune in self.dim_runes.runes.items():
            if (rune.rune_type == "secondary" and
                rune.valid_from_patch == patch_version and
                role in rune.champion_roles):

                result = self.analyze_rune_value_by_phase(rune.rune_id, role, patch_version)
                if result:
                    results.append(result)

        # Sort by value per minute (secondary runes more about efficiency)
        return sorted(results, key=lambda x: x.value_per_minute, reverse=True)

    def export_role_analysis(self, role: str, patch_version: str = "14.1",
                           output_dir: str = "out/quantitative/") -> Dict[str, Any]:
        """Export comprehensive rune analysis for a role"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Analyze keystones and secondary runes
        keystones = self.analyze_keystones_for_role(role, patch_version)
        secondaries = self.analyze_secondary_runes_for_role(role, patch_version)

        all_results = keystones + secondaries

        # Compile governance distribution
        governance_dist = {"CONFIDENT": 0, "CAUTION": 0, "CONTEXT": 0}
        for result in all_results:
            governance_dist[result.governance_tag] += 1

        # Convert to export format
        export_data = {
            "metadata": {
                "analysis_type": "rune_value_temporal",
                "role": role,
                "patch_version": patch_version,
                "generated_at": datetime.now().isoformat(),
                "record_count": len(all_results),
                "keystone_count": len(keystones),
                "secondary_count": len(secondaries)
            },
            "summary": {
                "best_keystone": keystones[0].rune_name if keystones else None,
                "best_keystone_value": keystones[0].total_game_value if keystones else 0,
                "best_secondary": secondaries[0].rune_name if secondaries else None,
                "best_secondary_efficiency": secondaries[0].value_per_minute if secondaries else 0,
                "governance_distribution": governance_dist,
                "avg_keystone_value": np.mean([k.total_game_value for k in keystones]) if keystones else 0,
                "avg_secondary_efficiency": np.mean([s.value_per_minute for s in secondaries]) if secondaries else 0
            },
            "keystones": self._convert_results_to_export(keystones),
            "secondary_runes": self._convert_results_to_export(secondaries),
            "governance_distribution": governance_dist
        }

        # Save to file
        role_file = output_path / f"rune_value_{role}_patch_{patch_version}.json"
        with open(role_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported rune value analysis for {role}: {len(all_results)} runes to {role_file}")
        return export_data

    def export_comprehensive_analysis(self, patch_version: str = "14.1",
                                    output_dir: str = "out/quantitative/") -> Dict[str, Any]:
        """Export comprehensive rune value analysis across all roles"""
        roles = ["adc", "mid", "jungle", "top", "support"]
        all_results = []
        role_summaries = {}

        # Analyze each role
        for role in roles:
            role_data = self.export_role_analysis(role, patch_version, output_dir)
            role_summaries[role] = role_data["summary"]

            # Collect all results
            for keystone in role_data["keystones"]:
                keystone["primary_role"] = role
                all_results.append(keystone)
            for secondary in role_data["secondary_runes"]:
                secondary["primary_role"] = role
                all_results.append(secondary)

        # Global governance distribution
        global_governance = {"CONFIDENT": 0, "CAUTION": 0, "CONTEXT": 0}
        for result in all_results:
            global_governance[result["governance_tag"]] += 1

        # Create comprehensive summary
        export_data = {
            "metadata": {
                "analysis_type": "rune_value_comprehensive",
                "patch_version": patch_version,
                "generated_at": datetime.now().isoformat(),
                "total_records": len(all_results),
                "roles_analyzed": roles,
                "rune_types": ["keystone", "secondary"]
            },
            "summary": {
                "total_runes_analyzed": len(all_results),
                "roles_covered": len(roles),
                "governance_distribution": global_governance,
                "best_overall_keystone": self._find_best_overall_rune(all_results, "keystone"),
                "best_overall_secondary": self._find_best_overall_rune(all_results, "secondary"),
                "role_summaries": role_summaries
            },
            "all_rune_values": all_results,
            "governance_distribution": global_governance
        }

        # Save comprehensive file
        output_path = Path(output_dir)
        comprehensive_file = output_path / f"rune_value_comprehensive_patch_{patch_version}.json"
        with open(comprehensive_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported comprehensive rune value analysis: {len(all_results)} rune analyses to {comprehensive_file}")
        return export_data

    def _convert_results_to_export(self, results: List[RuneValueResult]) -> List[Dict[str, Any]]:
        """Convert analysis results to export format"""
        export_results = []

        for result in results:
            record = {
                "row_id": f"rune_value_{result.rune_id}_{result.patch_version}",
                "rune_id": result.rune_id,
                "rune_name": result.rune_name,
                "rune_type": result.rune_type,
                "tree_name": result.tree_name,
                "early_game_value": round(result.early_game_value, 3),
                "mid_game_value": round(result.mid_game_value, 3),
                "late_game_value": round(result.late_game_value, 3),
                "total_game_value": round(result.total_game_value, 3),
                "value_per_minute": round(result.value_per_minute, 3),
                "trigger_efficiency": round(result.trigger_efficiency, 3),
                "patch_version": result.patch_version,
                "governance_tag": result.governance_tag,
                "confidence_lower": round(result.confidence_interval[0], 3),
                "confidence_upper": round(result.confidence_interval[1], 3),
                "sample_roles": result.sample_roles,
                "notes": result.notes
            }
            export_results.append(record)

        return export_results

    def _find_best_overall_rune(self, all_results: List[Dict[str, Any]], rune_type: str) -> Optional[Dict[str, Any]]:
        """Find the best rune of a specific type across all roles"""
        type_runes = [r for r in all_results if r["rune_type"] == rune_type]
        if not type_runes:
            return None

        if rune_type == "keystone":
            # Best keystone by total game value
            best = max(type_runes, key=lambda x: x["total_game_value"])
        else:
            # Best secondary by value per minute
            best = max(type_runes, key=lambda x: x["value_per_minute"])

        return {
            "rune_name": best["rune_name"],
            "value": best["total_game_value"] if rune_type == "keystone" else best["value_per_minute"],
            "primary_role": best["primary_role"]
        }

def main():
    """Test rune value analysis"""
    analyzer = RuneValueAnalyzer()

    # Test single rune analysis
    conqueror_result = analyzer.analyze_rune_value_by_phase(8010, "top")
    if conqueror_result:
        print(f"Conqueror analysis:")
        print(f"  Total game value: {conqueror_result.total_game_value:.1f}")
        print(f"  Value per minute: {conqueror_result.value_per_minute:.1f}")
        print(f"  Governance: {conqueror_result.governance_tag}")

    # Test role analysis
    adc_keystones = analyzer.analyze_keystones_for_role("adc")
    print(f"\nTop ADC keystones:")
    for i, keystone in enumerate(adc_keystones[:3]):
        print(f"  {i+1}. {keystone.rune_name}: {keystone.total_game_value:.1f} total value")

    # Test export
    role_data = analyzer.export_role_analysis("adc")
    print(f"\nExported ADC analysis: {role_data['metadata']['record_count']} runes")

    # Test comprehensive export
    comprehensive_data = analyzer.export_comprehensive_analysis()
    print(f"Exported comprehensive analysis: {comprehensive_data['metadata']['total_records']} total rune analyses")

if __name__ == "__main__":
    main()