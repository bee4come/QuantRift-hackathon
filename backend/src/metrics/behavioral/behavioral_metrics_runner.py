#!/usr/bin/env python3
"""
Behavioral Metrics Runner
Unified interface for running all behavioral metrics analysis modules
"""

import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

# Import behavioral metrics modules
from .pick_attach_rates import PickAttachRateAnalyzer
from .synergy_analysis import ChampionSynergyAnalyzer  
from .rune_analysis import RunePageAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BehavioralMetricsRunner:
    """Unified runner for all behavioral metrics analysis"""
    
    def __init__(self, config_path: str = "configs/user_mode_params.yml", 
                 data_dir: str = "data/silver/enhanced_facts_test/",
                 output_dir: str = "out/behavioral/"):
        """Initialize runner with configuration"""
        self.config_path = config_path
        self.data_dir = data_dir
        self.output_dir = output_dir
        
        # Initialize analyzers
        self.pick_attach_analyzer = PickAttachRateAnalyzer(config_path)
        self.synergy_analyzer = ChampionSynergyAnalyzer(config_path)
        self.rune_analyzer = RunePageAnalyzer(config_path)
        
        # Track results
        self.results = {}
        
    def load_data(self) -> None:
        """Load silver layer data for all analyzers"""
        logger.info("Loading silver layer data for all analyzers...")
        
        try:
            self.pick_attach_analyzer.load_silver_data(self.data_dir)
            self.synergy_analyzer.load_silver_data(self.data_dir)
            self.rune_analyzer.load_silver_data(self.data_dir)
            logger.info("Successfully loaded data for all analyzers")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise
    
    def run_pick_attach_analysis(self, patch_version: str = None) -> Dict[str, Any]:
        """Run pick rate and attach rate analysis"""
        logger.info("Running pick rate and attach rate analysis...")
        
        try:
            results = self.pick_attach_analyzer.analyze_all(patch_version, self.output_dir)
            self.results['pick_attach'] = results
            
            logger.info(f"Generated {len(results['pick_rates'])} pick rate records")
            logger.info(f"Generated {len(results['attach_rates'])} attach rate records")
            
            return results
        except Exception as e:
            logger.error(f"Pick/attach analysis failed: {e}")
            raise
    
    def run_synergy_analysis(self, patch_version: str = None) -> Dict[str, Any]:
        """Run champion synergy analysis"""
        logger.info("Running champion synergy analysis...")
        
        try:
            results = self.synergy_analyzer.analyze_team_synergies(patch_version, self.output_dir)
            self.results['synergy'] = results
            
            logger.info(f"Generated {len(results['synergy_analysis'])} synergy records")
            
            return results
        except Exception as e:
            logger.error(f"Synergy analysis failed: {e}")
            raise
    
    def run_rune_analysis(self, patch_version: str = None) -> Dict[str, Any]:
        """Run rune page win rate analysis"""
        logger.info("Running rune page win rate analysis...")
        
        try:
            results = self.rune_analyzer.analyze_rune_performance(patch_version, self.output_dir)
            self.results['rune'] = results
            
            logger.info(f"Generated {len(results['keystone_winrates'])} keystone records")
            logger.info(f"Generated {len(results['rune_combinations'])} rune combination records")
            
            return results
        except Exception as e:
            logger.error(f"Rune analysis failed: {e}")
            raise
    
    def run_all_analysis(self, patch_version: str = None) -> Dict[str, Any]:
        """Run all behavioral metrics analysis"""
        logger.info("Starting comprehensive behavioral metrics analysis...")
        
        # Load data
        self.load_data()
        
        # Run all analyses
        pick_attach_results = self.run_pick_attach_analysis(patch_version)
        synergy_results = self.run_synergy_analysis(patch_version)
        rune_results = self.run_rune_analysis(patch_version)
        
        # Compile summary
        summary = {
            'total_records': {
                'pick_rates': len(pick_attach_results['pick_rates']),
                'attach_rates': len(pick_attach_results['attach_rates']),
                'synergy_analysis': len(synergy_results['synergy_analysis']),
                'keystone_winrates': len(rune_results['keystone_winrates']),
                'rune_combinations': len(rune_results['rune_combinations'])
            },
            'governance_distribution': self._analyze_governance_distribution(),
            'patch_coverage': patch_version or 'all_patches'
        }
        
        # Save comprehensive summary
        self._save_summary(summary, patch_version)
        
        logger.info("Behavioral metrics analysis completed successfully")
        return {
            'pick_attach': pick_attach_results,
            'synergy': synergy_results,
            'rune': rune_results,
            'summary': summary
        }
    
    def _analyze_governance_distribution(self) -> Dict[str, Dict[str, int]]:
        """Analyze governance tag distribution across all metrics"""
        governance_dist = {}
        
        for metric_type, metric_results in self.results.items():
            if isinstance(metric_results, dict):
                for sub_metric, records in metric_results.items():
                    if isinstance(records, list) and records:
                        dist = {'CONFIDENT': 0, 'CAUTION': 0, 'CONTEXT': 0}
                        for record in records:
                            tag = record.get('governance_tag', 'CONTEXT')
                            if tag in dist:
                                dist[tag] += 1
                        governance_dist[f"{metric_type}_{sub_metric}"] = dist
        
        return governance_dist
    
    def _save_summary(self, summary: Dict[str, Any], patch_version: str = None) -> None:
        """Save comprehensive analysis summary"""
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        patch_suffix = f"_patch_{patch_version}" if patch_version else "_all_patches"
        summary_file = output_path / f"behavioral_metrics_summary{patch_suffix}.json"
        
        with open(summary_file, 'w') as f:
            json.dump({
                'metadata': {
                    'analysis_type': 'behavioral_metrics_comprehensive',
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'patch_scope': patch_version or 'all_patches',
                    'modules_run': ['pick_attach_rates', 'synergy_analysis', 'rune_analysis']
                },
                'summary': summary
            }, f, indent=2)
        
        logger.info(f"Saved comprehensive summary to {summary_file}")
    
    def print_results_summary(self) -> None:
        """Print a formatted summary of results"""
        print("\n" + "="*80)
        print("BEHAVIORAL METRICS ANALYSIS SUMMARY")
        print("="*80)
        
        if 'pick_attach' in self.results:
            pick_attach = self.results['pick_attach']
            print(f"\n📊 PICK & ATTACH RATES:")
            print(f"   • Pick rates: {len(pick_attach['pick_rates'])} records")
            print(f"   • Attach rates: {len(pick_attach['attach_rates'])} records")
            
            # Show top pick rate
            if pick_attach['pick_rates']:
                top_pick = max(pick_attach['pick_rates'], key=lambda x: x['p_hat'])
                print(f"   • Top pick rate: {top_pick['champion_name']} ({top_pick['role']}) - {top_pick['p_hat']:.1%}")
        
        if 'synergy' in self.results:
            synergy = self.results['synergy']
            print(f"\n🤝 CHAMPION SYNERGIES:")
            print(f"   • Synergy records: {len(synergy['synergy_analysis'])} pairs")
            
            # Show strongest synergy and anti-synergy
            if synergy['synergy_analysis']:
                synergies = [r for r in synergy['synergy_analysis'] if r['synergy_type'] == 'synergy']
                anti_synergies = [r for r in synergy['synergy_analysis'] if r['synergy_type'] == 'anti_synergy']
                
                if synergies:
                    top_synergy = max(synergies, key=lambda x: x['synergy_strength'])
                    print(f"   • Strongest synergy: {top_synergy['champion_a_name']} + {top_synergy['champion_b_name']} "
                          f"(Log OR: {top_synergy['log_odds_ratio']:.2f})")
                
                if anti_synergies:
                    top_anti = max(anti_synergies, key=lambda x: x['synergy_strength'])
                    print(f"   • Strongest anti-synergy: {top_anti['champion_a_name']} + {top_anti['champion_b_name']} "
                          f"(Log OR: {top_anti['log_odds_ratio']:.2f})")
        
        if 'rune' in self.results:
            rune = self.results['rune']
            print(f"\n🎯 RUNE ANALYSIS:")
            print(f"   • Keystone records: {len(rune['keystone_winrates'])} combinations")
            print(f"   • Rune combo records: {len(rune['rune_combinations'])} combinations")
            
            # Show best performing runes
            if rune['keystone_winrates']:
                top_keystone = max(rune['keystone_winrates'], key=lambda x: x['winrate_delta'])
                print(f"   • Best keystone: {top_keystone['champion_name']} with {top_keystone['keystone_rune']} "
                      f"(+{top_keystone['winrate_delta']:.1%} WR)")
        
        print("\n" + "="*80)


def main():
    """Main entry point with CLI support"""
    parser = argparse.ArgumentParser(description='Run behavioral metrics analysis')
    parser.add_argument('--patch', type=str, help='Specific patch version to analyze (e.g., 25.17)')
    parser.add_argument('--module', choices=['pick_attach', 'synergy', 'rune', 'all'], 
                       default='all', help='Which analysis module to run')
    parser.add_argument('--data-dir', type=str, default='data/silver/enhanced_facts_test/',
                       help='Silver layer data directory')
    parser.add_argument('--output-dir', type=str, default='out/behavioral/',
                       help='Output directory for results')
    parser.add_argument('--config', type=str, default='configs/user_mode_params.yml',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = BehavioralMetricsRunner(
        config_path=args.config,
        data_dir=args.data_dir,
        output_dir=args.output_dir
    )
    
    try:
        # Load data first
        runner.load_data()
        
        # Run specified analysis
        if args.module == 'all':
            results = runner.run_all_analysis(args.patch)
        elif args.module == 'pick_attach':
            results = runner.run_pick_attach_analysis(args.patch)
        elif args.module == 'synergy':
            results = runner.run_synergy_analysis(args.patch)
        elif args.module == 'rune':
            results = runner.run_rune_analysis(args.patch)
        
        # Print summary
        runner.print_results_summary()
        
        print(f"\n✅ Analysis completed successfully!")
        print(f"📁 Results saved to: {args.output_dir}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\n❌ Analysis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())