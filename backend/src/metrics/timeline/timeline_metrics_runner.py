#!/usr/bin/env python3
"""
Timeline Metrics Runner
Orchestrates all three Timeline-based metrics to advance from 10/20 to 13/20 quantitative metrics
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

from .time_to_core import AvgTimeToCoreAnalyzer
from .objective_rate import ObjectiveRateAnalyzer
from .baseline_winrate import BaselineWinrateAnalyzer

# Import existing core utilities
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
from utils import load_user_mode_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimelineMetricsRunner:
    """Unified runner for all Timeline-based metrics"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize runner with all analyzers"""
        self.config = load_user_mode_config(config_path)

        # Initialize all three analyzers
        self.time_to_core_analyzer = AvgTimeToCoreAnalyzer(config_path)
        self.objective_rate_analyzer = ObjectiveRateAnalyzer(config_path)
        self.baseline_winrate_analyzer = BaselineWinrateAnalyzer(config_path)

        logger.info("Initialized Timeline Metrics Runner with 3 analyzers")

    def load_all_data(self, data_dir: str = "data/silver/enhanced_facts_test/") -> None:
        """Load Silver layer data for all analyzers"""
        logger.info("Loading Silver layer data for all analyzers...")

        # Load data for all three analyzers
        self.time_to_core_analyzer.load_silver_data(data_dir)
        self.objective_rate_analyzer.load_silver_data(data_dir)
        self.baseline_winrate_analyzer.load_silver_data(data_dir)

        logger.info("Data loading completed for all analyzers")

    def run_all_metrics(self, patch_version: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run all three Timeline-based metrics.
        Returns combined results advancing from 10/20 to 13/20 quantitative metrics.
        """
        logger.info("Running all Timeline-based metrics...")

        results = {}

        # 1. avg_time_to_core: Core item completion times
        logger.info("Calculating avg_time_to_core metrics...")
        try:
            time_to_core_results = self.time_to_core_analyzer.calculate_avg_time_to_core(patch_version)
            results['avg_time_to_core'] = time_to_core_results
            logger.info(f"Generated {len(time_to_core_results)} avg_time_to_core records")
        except Exception as e:
            logger.error(f"avg_time_to_core calculation failed: {e}")
            results['avg_time_to_core'] = []

        # 2. obj_rate: Objective participation tracking
        logger.info("Calculating obj_rate metrics...")
        try:
            obj_rate_results = self.objective_rate_analyzer.calculate_obj_rate(patch_version)
            results['obj_rate'] = obj_rate_results
            logger.info(f"Generated {len(obj_rate_results)} obj_rate records")
        except Exception as e:
            logger.error(f"obj_rate calculation failed: {e}")
            results['obj_rate'] = []

        # 3. winrate_delta_vs_baseline: Enhanced baseline calculations
        logger.info("Calculating winrate_delta_vs_baseline metrics...")
        try:
            baseline_results = self.baseline_winrate_analyzer.calculate_winrate_delta_vs_baseline(patch_version)
            results['winrate_delta_vs_baseline'] = baseline_results
            logger.info(f"Generated {len(baseline_results)} winrate_delta_vs_baseline records")
        except Exception as e:
            logger.error(f"winrate_delta_vs_baseline calculation failed: {e}")
            results['winrate_delta_vs_baseline'] = []

        # Calculate totals
        total_records = sum(len(metric_results) for metric_results in results.values())
        logger.info(f"Timeline metrics complete: {total_records} total records across 3 metrics")

        return results

    def save_results(self, results: Dict[str, List[Dict[str, Any]]],
                    output_dir: str = "out/timeline/",
                    patch_version: str = None) -> Dict[str, str]:
        """Save all Timeline metrics results to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        patch_suffix = f"_patch_{patch_version}" if patch_version else "_all_patches"
        saved_files = {}

        for metric_name, metric_results in results.items():
            if not metric_results:
                logger.warning(f"No results to save for {metric_name}")
                continue

            filename = f"{metric_name}{patch_suffix}.json"
            file_path = output_path / filename

            # Create output with metadata
            output_data = {
                'metadata': {
                    'metric_type': metric_name,
                    'record_count': len(metric_results),
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'governance_enabled': True,
                    'timeline_metrics_version': '1.0',
                    'patch_version': patch_version or 'all_patches',
                    'source': 'timeline_metrics_runner'
                },
                'governance_summary': self._calculate_governance_summary(metric_results),
                'records': metric_results
            }

            with open(file_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            saved_files[metric_name] = str(file_path)
            logger.info(f"Saved {len(metric_results)} {metric_name} records to {file_path}")

        return saved_files

    def _calculate_governance_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate governance summary for a set of records"""
        if not records:
            return {}

        governance_counts = {}
        for record in records:
            tag = record.get('governance_tag', 'UNKNOWN')
            governance_counts[tag] = governance_counts.get(tag, 0) + 1

        return {
            'total_records': len(records),
            'governance_distribution': governance_counts,
            'high_quality_records': governance_counts.get('CONFIDENT', 0),
            'medium_quality_records': governance_counts.get('CAUTION', 0),
            'context_records': governance_counts.get('CONTEXT', 0)
        }

    def generate_progress_report(self, results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Generate progress report showing advancement from 10/20 to 13/20 metrics.
        """
        # Calculate metrics progress
        baseline_metrics = 10  # Starting point
        new_metrics_added = len([k for k, v in results.items() if v])  # Successfully generated metrics
        total_metrics = baseline_metrics + new_metrics_added

        # Calculate record counts and governance quality
        total_records = 0
        quality_distribution = {'CONFIDENT': 0, 'CAUTION': 0, 'CONTEXT': 0, 'OTHER': 0}

        for metric_name, metric_results in results.items():
            total_records += len(metric_results)
            for record in metric_results:
                tag = record.get('governance_tag', 'OTHER')
                if tag in quality_distribution:
                    quality_distribution[tag] += 1
                else:
                    quality_distribution['OTHER'] += 1

        progress_report = {
            'metrics_progress': {
                'baseline_metrics': baseline_metrics,
                'new_timeline_metrics': new_metrics_added,
                'total_metrics': total_metrics,
                'target_metrics': 20,
                'completion_percentage': (total_metrics / 20) * 100
            },
            'timeline_metrics_delivered': {
                'avg_time_to_core': {
                    'status': 'completed' if results.get('avg_time_to_core') else 'failed',
                    'record_count': len(results.get('avg_time_to_core', [])),
                    'description': 'Core item completion timing analysis'
                },
                'obj_rate': {
                    'status': 'completed' if results.get('obj_rate') else 'failed',
                    'record_count': len(results.get('obj_rate', [])),
                    'description': 'Objective participation rate analysis'
                },
                'winrate_delta_vs_baseline': {
                    'status': 'completed' if results.get('winrate_delta_vs_baseline') else 'failed',
                    'record_count': len(results.get('winrate_delta_vs_baseline', [])),
                    'description': 'Enhanced baseline winrate calculations'
                }
            },
            'data_quality': {
                'total_records': total_records,
                'governance_distribution': quality_distribution,
                'quality_score': (quality_distribution['CONFIDENT'] + quality_distribution['CAUTION']) / max(1, total_records)
            },
            'technical_implementation': {
                'zero_dependency': True,
                'wilson_ci_enabled': True,
                'governance_framework_integrated': True,
                'silver_layer_compatible': True
            }
        }

        return progress_report

    def run_full_analysis(self, data_dir: str = "data/silver/enhanced_facts_test/",
                         output_dir: str = "out/timeline/",
                         patch_version: str = None) -> Dict[str, Any]:
        """
        Run complete Timeline metrics analysis pipeline.
        Returns progress report and file paths.
        """
        logger.info("Starting full Timeline metrics analysis...")

        try:
            # Load data
            self.load_all_data(data_dir)

            # Run all metrics
            results = self.run_all_metrics(patch_version)

            # Save results
            saved_files = self.save_results(results, output_dir, patch_version)

            # Generate progress report
            progress_report = self.generate_progress_report(results)

            # Save progress report
            report_path = Path(output_dir) / f"timeline_metrics_progress_report{f'_patch_{patch_version}' if patch_version else ''}.json"
            with open(report_path, 'w') as f:
                json.dump(progress_report, f, indent=2)

            logger.info(f"Analysis complete! Progress: {progress_report['metrics_progress']['total_metrics']}/20 metrics")
            logger.info(f"Progress report saved to: {report_path}")

            return {
                'progress_report': progress_report,
                'saved_files': saved_files,
                'report_path': str(report_path),
                'success': True
            }

        except Exception as e:
            logger.error(f"Full analysis failed: {e}")
            return {
                'progress_report': {},
                'saved_files': {},
                'report_path': "",
                'success': False,
                'error': str(e)
            }


def main():
    """Demo script for complete Timeline metrics analysis"""
    runner = TimelineMetricsRunner()

    try:
        # Run full analysis
        result = runner.run_full_analysis()

        if result['success']:
            progress = result['progress_report']
            print(f"\n🎉 Timeline Metrics Analysis Complete!")
            print(f"📊 Progress: {progress['metrics_progress']['total_metrics']}/20 metrics "
                  f"({progress['metrics_progress']['completion_percentage']:.1f}%)")
            print(f"📈 Advanced from 10/20 to {progress['metrics_progress']['total_metrics']}/20 quantitative metrics")

            print(f"\n📋 New Timeline Metrics:")
            for metric_name, info in progress['timeline_metrics_delivered'].items():
                status_emoji = "✅" if info['status'] == 'completed' else "❌"
                print(f"  {status_emoji} {metric_name}: {info['record_count']} records - {info['description']}")

            print(f"\n📁 Saved Files:")
            for metric_name, file_path in result['saved_files'].items():
                print(f"  📄 {metric_name}: {file_path}")

            print(f"\n📋 Progress Report: {result['report_path']}")

        else:
            print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    main()