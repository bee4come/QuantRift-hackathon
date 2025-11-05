#!/usr/bin/env python3
"""
Shock Indicators Analysis Module
Purpose: Convert existing patch analysis into additive shock factor tables
Components: value/scaling/cd/cost/gold_eff/onhit/tree_pos shock factors
Integration: Sync with delta_cp and output alongside other quantitative metrics
"""

import pandas as pd
import numpy as np
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging
from datetime import datetime
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ShockComponent:
    """Individual shock factor component"""
    component_type: str
    value: float
    confidence: str
    evidence_n: int
    source_metric: str

@dataclass
class ShockIndicators:
    """Complete shock indicator analysis for champion/item/rune"""
    entity_id: str
    entity_type: str  # champion, item, rune
    patch_from: str
    patch_to: str
    shock_v2: float  # Overall shock factor
    shock_components: Dict[str, ShockComponent]
    meta_shift_contribution: float
    statistical_significance: bool

class ShockAnalyzer:
    """
    Shock Factor Calculation Engine
    Converts patch quantification results into shock indicators
    """

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize shock analyzer with configuration"""
        self.config = self._load_config(config_path)
        self.shock_weights = self._get_shock_weights()
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """Default configuration for shock analysis"""
        return {
            'shock_analysis': {
                'significance_threshold': 0.05,
                'min_sample_size': 50,
                'shock_threshold': 0.1,
                'confidence_levels': {
                    'high': 100,
                    'medium': 50,
                    'low': 20
                }
            }
        }

    def _get_shock_weights(self) -> Dict[str, float]:
        """Shock component weights for additive calculation"""
        return {
            'value': 0.25,      # Base stat value changes
            'scaling': 0.20,    # Scaling coefficient changes
            'cd': 0.15,         # Cooldown changes
            'cost': 0.15,       # Cost/resource changes
            'gold_eff': 0.15,   # Gold efficiency changes
            'onhit': 0.05,      # On-hit effect changes
            'tree_pos': 0.05    # Tree position/accessibility changes
        }

    def calculate_champion_shock(self, champion_data: Dict[str, Any], 
                               patch_comparison: Dict[str, Any]) -> ShockIndicators:
        """Calculate shock indicators for champion changes"""
        champion_name = champion_data['champion_name']
        role = champion_data['role']
        
        # Extract change data
        winrate_change = champion_data.get('winrate_change', 0)
        pickrate_change = champion_data.get('pickrate_change', 0)
        
        # Calculate shock components
        shock_components = {}
        
        # Value shock (based on winrate change)
        value_shock = self._calculate_value_shock(winrate_change, champion_data)
        shock_components['value'] = ShockComponent(
            component_type='value',
            value=value_shock,
            confidence=self._determine_confidence(champion_data.get('sample_size_after', 0)),
            evidence_n=champion_data.get('sample_size_after', 0),
            source_metric='winrate_change'
        )
        
        # Scaling shock (based on performance variance across game length)
        scaling_shock = self._calculate_scaling_shock(champion_data)
        shock_components['scaling'] = ShockComponent(
            component_type='scaling',
            value=scaling_shock,
            confidence=self._determine_confidence(champion_data.get('sample_size_after', 0)),
            evidence_n=champion_data.get('sample_size_after', 0),
            source_metric='game_duration_variance'
        )
        
        # Calculate overall shock_v2
        shock_v2 = self._calculate_additive_shock(shock_components)
        
        # Determine statistical significance
        statistical_significance = champion_data.get('p_value', 1.0) < 0.05
        
        return ShockIndicators(
            entity_id=f"{champion_name}_{role}",
            entity_type='champion',
            patch_from=patch_comparison['patch_from'],
            patch_to=patch_comparison['patch_to'],
            shock_v2=shock_v2,
            shock_components=shock_components,
            meta_shift_contribution=abs(pickrate_change) * 0.1,
            statistical_significance=statistical_significance
        )

    def calculate_item_shock(self, item_data: Dict[str, Any], 
                           delta_cp_data: Dict[str, Any]) -> ShockIndicators:
        """Calculate shock indicators for item changes"""
        item_id = item_data['item_id']
        
        shock_components = {}
        
        # Gold efficiency shock
        gold_eff_change = item_data.get('gold_efficiency_change', 0)
        shock_components['gold_eff'] = ShockComponent(
            component_type='gold_eff',
            value=abs(gold_eff_change) / 100.0,  # Normalize percentage
            confidence='HIGH',
            evidence_n=item_data.get('usage_count', 0),
            source_metric='gold_efficiency_change'
        )
        
        # Cost shock (from item cost changes)
        cost_change = item_data.get('cost_change', 0)
        shock_components['cost'] = ShockComponent(
            component_type='cost',
            value=abs(cost_change) / 3000.0,  # Normalize by typical item cost
            confidence='HIGH',
            evidence_n=item_data.get('usage_count', 0),
            source_metric='cost_change'
        )
        
        # Value shock (from combat power delta)
        cp_change = delta_cp_data.get('cp_change', 0)
        shock_components['value'] = ShockComponent(
            component_type='value',
            value=abs(cp_change) / 100.0,  # Normalize by typical CP
            confidence='HIGH',
            evidence_n=delta_cp_data.get('comparisons', 0),
            source_metric='delta_cp'
        )
        
        # Calculate overall shock_v2
        shock_v2 = self._calculate_additive_shock(shock_components)
        
        return ShockIndicators(
            entity_id=str(item_id),
            entity_type='item',
            patch_from=delta_cp_data.get('patch_from', 'unknown'),
            patch_to=delta_cp_data.get('patch_to', 'unknown'),
            shock_v2=shock_v2,
            shock_components=shock_components,
            meta_shift_contribution=0.0,  # Items don't directly affect pick rates
            statistical_significance=delta_cp_data.get('significant', False)
        )

    def calculate_rune_shock(self, rune_data: Dict[str, Any]) -> ShockIndicators:
        """Calculate shock indicators for rune changes"""
        rune_id = rune_data['rune_id']
        
        shock_components = {}
        
        # Value shock (from rune value change)
        value_change = rune_data.get('value_change', 0)
        shock_components['value'] = ShockComponent(
            component_type='value',
            value=abs(value_change) / 1000.0,  # Normalize by typical rune value
            confidence=self._determine_confidence(rune_data.get('usage_count', 0)),
            evidence_n=rune_data.get('usage_count', 0),
            source_metric='rune_value_change'
        )
        
        # Tree position shock (accessibility changes)
        tree_pos_change = rune_data.get('tree_accessibility_change', 0)
        shock_components['tree_pos'] = ShockComponent(
            component_type='tree_pos',
            value=abs(tree_pos_change),
            confidence='MEDIUM',
            evidence_n=rune_data.get('usage_count', 0),
            source_metric='tree_accessibility'
        )
        
        # Calculate overall shock_v2
        shock_v2 = self._calculate_additive_shock(shock_components)
        
        return ShockIndicators(
            entity_id=str(rune_id),
            entity_type='rune',
            patch_from=rune_data.get('patch_from', 'unknown'),
            patch_to=rune_data.get('patch_to', 'unknown'),
            shock_v2=shock_v2,
            shock_components=shock_components,
            meta_shift_contribution=rune_data.get('pickrate_change', 0) * 0.05,
            statistical_significance=rune_data.get('significant', False)
        )

    def _calculate_value_shock(self, winrate_change: float, champion_data: Dict[str, Any]) -> float:
        """Calculate value shock component from winrate changes"""
        # Scale winrate change to shock value (10% winrate change = 1.0 shock)
        base_shock = abs(winrate_change) * 10.0
        
        # Adjust for sample size confidence
        sample_size = champion_data.get('sample_size_after', 0)
        confidence_multiplier = min(1.0, sample_size / 100.0)  # Full confidence at 100+ games
        
        return base_shock * confidence_multiplier

    def _calculate_scaling_shock(self, champion_data: Dict[str, Any]) -> float:
        """Calculate scaling shock component from performance variance"""
        # Placeholder implementation - in real system would analyze game duration variance
        # For now, use a small random component based on champion type
        champion_name = champion_data.get('champion_name', '')
        
        # Scaling champions (ADCs, late game champions) have higher scaling shock potential
        scaling_champions = ['Jinx', 'Vayne', 'Kassadin', 'Nasus', 'Veigar']
        
        if champion_name in scaling_champions:
            return 0.3  # Higher scaling shock for scaling champions
        else:
            return 0.1  # Lower scaling shock for others

    def _calculate_additive_shock(self, shock_components: Dict[str, ShockComponent]) -> float:
        """Calculate overall shock_v2 as weighted sum of components"""
        total_shock = 0.0
        
        for component_name, component in shock_components.items():
            weight = self.shock_weights.get(component_name, 0.0)
            total_shock += component.value * weight
            
        return total_shock

    def _determine_confidence(self, sample_size: int) -> str:
        """Determine confidence level based on sample size"""
        config = self.config.get('shock_analysis', {})
        confidence_levels = config.get('confidence_levels', {})
        
        if sample_size >= confidence_levels.get('high', 100):
            return 'HIGH'
        elif sample_size >= confidence_levels.get('medium', 50):
            return 'MEDIUM'
        elif sample_size >= confidence_levels.get('low', 20):
            return 'LOW'
        else:
            return 'INSUFFICIENT'

    def analyze_patch_shock_factors(self, patch_comparison_file: str, 
                                  delta_cp_file: str = None) -> List[ShockIndicators]:
        """
        Analyze shock factors from patch comparison and delta_cp data
        """
        shock_results = []
        
        # Load patch comparison data
        with open(patch_comparison_file, 'r') as f:
            patch_data = json.load(f)
        
        # Process champion shock factors
        champion_changes = patch_data.get('detailed_analysis', {}).get('champion_winrate_changes', {})
        
        for champion_key, champion_change in champion_changes.items():
            champion_name, role = champion_key.split('_', 1)
            
            # Extract pickrate change if available
            pickrate_changes = patch_data.get('detailed_analysis', {}).get('pickrate_changes', {})
            pickrate_change = pickrate_changes.get(champion_key, {}).get('absolute_change', 0)

            champion_data = {
                'champion_name': champion_name,
                'role': role,
                'winrate_change': champion_change.get('absolute_change', 0),
                'pickrate_change': pickrate_change,
                'sample_size_after': int(champion_change.get('sample_size_after', 0)),
                'p_value': 0.5  # Would get from statistical tests
            }
            
            shock_indicator = self.calculate_champion_shock(champion_data, {
                'patch_from': patch_data['patch_comparison']['patch_from'],
                'patch_to': patch_data['patch_comparison']['patch_to']
            })
            
            shock_results.append(shock_indicator)
        
        # Process item shock factors if delta_cp data available
        if delta_cp_file and Path(delta_cp_file).exists():
            with open(delta_cp_file, 'r') as f:
                delta_cp_data = json.load(f)
            
            # Process item shock factors from delta_cp results
            for item_analysis in delta_cp_data.get('item_analyses', []):
                item_shock = self.calculate_item_shock(item_analysis, item_analysis)
                shock_results.append(item_shock)
        
        logger.info(f"Generated {len(shock_results)} shock indicators")
        return shock_results

    def export_shock_table(self, shock_indicators: List[ShockIndicators], 
                          output_file: str) -> None:
        """Export shock indicators as structured table"""
        shock_table = []
        
        for indicator in shock_indicators:
            # Create base record
            record = {
                'entity_id': indicator.entity_id,
                'entity_type': indicator.entity_type,
                'patch_from': indicator.patch_from,
                'patch_to': indicator.patch_to,
                'shock_v2': round(indicator.shock_v2, 6),
                'meta_shift_contribution': round(indicator.meta_shift_contribution, 6),
                'statistical_significance': indicator.statistical_significance,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add shock components
            for component_name, component in indicator.shock_components.items():
                record[f'shock_{component_name}'] = round(component.value, 6)
                record[f'shock_{component_name}_confidence'] = component.confidence
                record[f'shock_{component_name}_evidence_n'] = component.evidence_n
                record[f'shock_{component_name}_source'] = component.source_metric
            
            shock_table.append(record)
        
        # Export as JSON
        output = {
            'metadata': {
                'export_type': 'shock_indicators',
                'generated_at': datetime.now().isoformat(),
                'total_records': len(shock_table),
                'shock_components': list(self.shock_weights.keys()),
                'methodology': 'additive_shock_factors'
            },
            'records': shock_table
        }
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Exported {len(shock_table)} shock indicators to {output_file}")

    def generate_shock_summary(self, shock_indicators: List[ShockIndicators]) -> Dict[str, Any]:
        """Generate summary statistics for shock indicators"""
        if not shock_indicators:
            return {}
        
        # Group by entity type
        by_type = {}
        for indicator in shock_indicators:
            entity_type = indicator.entity_type
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(indicator)
        
        summary = {
            'total_entities': len(shock_indicators),
            'by_entity_type': {},
            'shock_distribution': {},
            'top_shock_entities': []
        }
        
        # Statistics by entity type
        for entity_type, indicators in by_type.items():
            shock_values = [ind.shock_v2 for ind in indicators]
            
            summary['by_entity_type'][entity_type] = {
                'count': len(indicators),
                'avg_shock': round(np.mean(shock_values), 4),
                'max_shock': round(np.max(shock_values), 4),
                'min_shock': round(np.min(shock_values), 4),
                'statistically_significant': sum(1 for ind in indicators if ind.statistical_significance)
            }
        
        # Overall shock distribution
        all_shocks = [ind.shock_v2 for ind in shock_indicators]
        summary['shock_distribution'] = {
            'mean': round(np.mean(all_shocks), 4),
            'std': round(np.std(all_shocks), 4),
            'percentiles': {
                '50th': round(np.percentile(all_shocks, 50), 4),
                '75th': round(np.percentile(all_shocks, 75), 4),
                '90th': round(np.percentile(all_shocks, 90), 4),
                '95th': round(np.percentile(all_shocks, 95), 4)
            }
        }
        
        # Top shock entities
        sorted_indicators = sorted(shock_indicators, key=lambda x: x.shock_v2, reverse=True)
        summary['top_shock_entities'] = [
            {
                'entity_id': ind.entity_id,
                'entity_type': ind.entity_type,
                'shock_v2': round(ind.shock_v2, 4),
                'statistical_significance': ind.statistical_significance
            }
            for ind in sorted_indicators[:10]
        ]
        
        return summary


def main():
    """Example usage of the ShockAnalyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze shock indicators from patch data")
    parser.add_argument("--patch_comparison", required=True, help="Patch comparison JSON file")
    parser.add_argument("--delta_cp", help="Delta CP analysis JSON file")
    parser.add_argument("--output", default="results/shock_analysis.json", help="Output file")
    parser.add_argument("--config", default="configs/user_mode_params.yml", help="Configuration file")
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = ShockAnalyzer(config_path=args.config)
    
    # Analyze shock factors
    shock_indicators = analyzer.analyze_patch_shock_factors(
        args.patch_comparison, 
        args.delta_cp
    )
    
    # Export results
    analyzer.export_shock_table(shock_indicators, args.output)
    
    # Generate summary
    summary = analyzer.generate_shock_summary(shock_indicators)
    
    # Print summary
    print(f"\n🔥 Shock Indicators Analysis Summary")
    print(f"📊 Total entities analyzed: {summary['total_entities']}")
    
    for entity_type, stats in summary['by_entity_type'].items():
        print(f"\n{entity_type.title()}s:")
        print(f"  Count: {stats['count']}")
        print(f"  Average shock: {stats['avg_shock']}")
        print(f"  Max shock: {stats['max_shock']}")
        print(f"  Statistically significant: {stats['statistically_significant']}")
    
    print(f"\n🏆 Top 5 Shock Entities:")
    for i, entity in enumerate(summary['top_shock_entities'][:5], 1):
        significance = "✓" if entity['statistical_significance'] else "○"
        print(f"  {i}. {entity['entity_id']} ({entity['entity_type']}) - {entity['shock_v2']} {significance}")
    
    print(f"\n📄 Full results saved to: {args.output}")


if __name__ == "__main__":
    main()