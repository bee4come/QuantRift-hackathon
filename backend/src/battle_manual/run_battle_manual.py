#!/usr/bin/env python3
"""
Battle Manual Execution Script

Main execution script for the comprehensive Battle Manual workflow.
Implements the complete 6-step quantitative analysis process for League of Legends data.

Usage:
    python run_battle_manual.py --patches 25.17,25.18,25.19 --validate --export-all
    python run_battle_manual.py --quick-test  # For testing with sample data
    python run_battle_manual.py --help
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

# Add core modules to path
sys.path.append(str(Path(__file__).parent / 'core'))

from battle_manual_processor import BattleManualProcessor
from core_metrics_engine import CoreMetricsEngine
from panels_export_engine import PanelsExportEngine
from validation_framework import BattleManualValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('battle_manual_execution.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Battle Manual - Comprehensive Quantitative Analysis Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --patches 25.17,25.18,25.19        # Process specific patches
  %(prog)s --validate --export-all            # Full validation and export
  %(prog)s --quick-test                       # Quick test with sample data
  %(prog)s --sql-only                         # Run DuckDB SQL analysis only
        """
    )
    
    # Core execution options
    parser.add_argument('--patches', type=str, 
                       help='Comma-separated list of patch versions (e.g., 25.17,25.18)')
    parser.add_argument('--config', type=str, default='../configs/user_mode_params.yml',
                       help='Path to configuration file')
    parser.add_argument('--silver-data', type=str, default='../data/silver/facts',
                       help='Path to Silver layer data directory')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory for results')
    
    # Workflow control
    parser.add_argument('--validate', action='store_true',
                       help='Run comprehensive validation before processing')
    parser.add_argument('--export-all', action='store_true',
                       help='Export all panels (entity, context, patch summary)')
    parser.add_argument('--sql-only', action='store_true',
                       help='Run DuckDB SQL analysis only')
    parser.add_argument('--quick-test', action='store_true',
                       help='Quick test with sample data')
    
    # Priority implementation control
    parser.add_argument('--priority', choices=['immediate', 'day_1', 'day_2', 'all'],
                       default='all', help='Priority level for metric implementation')
    
    # Advanced options
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip validation (for production runs)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be executed without running')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Display banner
    print_battle_manual_banner()
    
    try:
        if args.dry_run:
            run_dry_run(args)
        elif args.quick_test:
            run_quick_test(args)
        elif args.sql_only:
            run_sql_only(args)
        elif args.validate:
            run_validation_only(args)
        else:
            run_full_workflow(args)
            
    except Exception as e:
        logger.error(f"Battle Manual execution failed: {e}")
        sys.exit(1)


def print_battle_manual_banner():
    """Print Battle Manual execution banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🎯 BATTLE MANUAL - QUANT ANALYSIS WORKFLOW               ║
║                                                                              ║
║  Comprehensive 6-Step Quantitative Analysis for League of Legends           ║
║                                                                              ║
║  📊 Input Layer: 107,570 Silver records across 3 patches                    ║
║  🎯 Unified Grain: Hero + Combo layer entity analysis                       ║
║  ⚡ Core 20 Metrics: Complete quantitative framework                         ║
║  🦆 DuckDB Processing: Production-grade SQL implementation                   ║
║  📋 Panel Export: Universal, interpretable, traceable results               ║
║  ✅ Validation: Comprehensive quality assurance                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_full_workflow(args):
    """Execute the complete Battle Manual workflow."""
    logger.info("🚀 Starting full Battle Manual workflow...")
    
    # Parse patches
    patches = parse_patches(args.patches)
    if not patches:
        patches = ['25.17', '25.18', '25.19']  # Default patches
        logger.info(f"Using default patches: {patches}")
    
    # Step 1: Validation (if requested)
    if not args.skip_validation:
        logger.info("🔍 Running pre-execution validation...")
        validator = BattleManualValidator()
        validation_results = validator.run_comprehensive_validation()
        
        if validation_results['battle_manual_validation']['overall_status'] != 'PASS':
            logger.error("❌ Validation failed. Aborting workflow.")
            print_validation_summary(validation_results)
            sys.exit(1)
        else:
            logger.info("✅ Validation passed. Proceeding with workflow.")
    
    # Step 2: Initialize Battle Manual Processor
    logger.info("🏗️ Initializing Battle Manual Processor...")
    processor = BattleManualProcessor(
        config_path=args.config,
        silver_data_path=args.silver_data,
        output_dir=args.output_dir
    )
    
    # Step 3: Execute Battle Manual workflow
    logger.info(f"⚡ Executing Battle Manual for patches: {patches}")
    workflow_results = processor.execute_battle_manual(patches)
    
    # Step 4: Export panels (if requested)
    if args.export_all:
        logger.info("📋 Exporting quantitative panels...")
        export_engine = PanelsExportEngine(args.output_dir)
        
        # Extract metrics results from workflow
        metrics_results = workflow_results.get('metrics_summary', {})
        match_data = {patch: processor.silver_data.get(patch, []) for patch in patches}
        
        panel_paths = export_engine.export_all_panels(metrics_results, match_data)
        workflow_results['panel_exports'] = panel_paths
    
    # Step 5: Generate final report
    final_report = generate_final_report(workflow_results, args)
    report_path = Path(args.output_dir) / 'battle_manual_execution_report.json'
    
    with open(report_path, 'w') as f:
        json.dump(final_report, f, indent=2, default=str)
    
    logger.info(f"✅ Battle Manual workflow completed successfully!")
    logger.info(f"📄 Final report saved to: {report_path}")
    
    print_success_summary(final_report)


def run_quick_test(args):
    """Run quick test with sample data."""
    logger.info("🚀 Running Battle Manual quick test...")
    
    # Generate sample data
    logger.info("📊 Generating sample test data...")
    
    # Initialize with minimal configuration
    processor = BattleManualProcessor(output_dir=args.output_dir)
    
    # Create sample Silver data
    sample_data = generate_sample_data()
    processor.silver_data = {'25.18': sample_data}
    
    # Run Core 20 metrics on sample data
    logger.info("⚡ Testing Core 20 metrics calculation...")
    metrics_engine = CoreMetricsEngine()
    metrics_results = metrics_engine.calculate_all_metrics(sample_data, '25.18')
    
    # Test panel export
    logger.info("📋 Testing panel export...")
    export_engine = PanelsExportEngine(args.output_dir)
    panel_paths = export_engine.export_all_panels(
        {'25.18': metrics_results}, 
        {'25.18': sample_data}
    )
    
    # Generate test report
    test_report = {
        'battle_manual_quick_test': {
            'status': 'SUCCESS',
            'test_timestamp': datetime.now(timezone.utc).isoformat(),
            'sample_data_records': len(sample_data),
            'metrics_calculated': sum(len(category) for category in metrics_results.values()),
            'panels_exported': len(panel_paths),
            'output_files': panel_paths
        }
    }
    
    report_path = Path(args.output_dir) / 'battle_manual_quick_test_report.json'
    with open(report_path, 'w') as f:
        json.dump(test_report, f, indent=2, default=str)
    
    logger.info("✅ Quick test completed successfully!")
    logger.info(f"📄 Test report: {report_path}")
    
    print("\n🎉 Battle Manual Quick Test Results:")
    print(f"   📊 Sample records processed: {len(sample_data)}")
    print(f"   ⚡ Metrics calculated: {sum(len(category) for category in metrics_results.values())}")
    print(f"   📋 Panels exported: {len(panel_paths)}")
    print(f"   📄 Report saved: {report_path}")


def run_sql_only(args):
    """Run DuckDB SQL analysis only."""
    logger.info("🦆 Running DuckDB SQL analysis only...")
    
    import duckdb
    import pandas as pd
    
    # Generate sample data for SQL testing
    sample_data = generate_sample_data()
    df = pd.DataFrame(sample_data)
    
    # Initialize DuckDB connection
    conn = duckdb.connect(':memory:')
    conn.register('fact_match_performance', df)
    
    # Load and execute SQL files
    sql_dir = Path(__file__).parent / 'sql'
    sql_files = ['hero_layer_analysis.sql', 'combo_layer_analysis.sql', 'combat_power_analysis.sql']
    
    sql_results = {}
    
    for sql_file in sql_files:
        sql_path = sql_dir / sql_file
        if sql_path.exists():
            logger.info(f"📝 Executing {sql_file}...")
            try:
                with open(sql_path, 'r') as f:
                    sql_query = f.read()
                    
                # Execute SQL and capture results
                result = conn.execute(sql_query).fetchall()
                sql_results[sql_file] = {
                    'status': 'SUCCESS',
                    'rows_returned': len(result),
                    'sample_results': result[:5] if result else []
                }
                logger.info(f"✅ {sql_file} executed successfully: {len(result)} rows")
                
            except Exception as e:
                sql_results[sql_file] = {
                    'status': 'ERROR', 
                    'error': str(e)
                }
                logger.error(f"❌ {sql_file} failed: {e}")
        else:
            logger.warning(f"⚠️ SQL file not found: {sql_path}")
    
    conn.close()
    
    # Save SQL results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    sql_report_path = output_dir / 'duckdb_sql_analysis_report.json'
    with open(sql_report_path, 'w') as f:
        json.dump({
            'duckdb_sql_analysis': {
                'execution_timestamp': datetime.now(timezone.utc).isoformat(),
                'sql_files_tested': len(sql_files),
                'successful_executions': len([r for r in sql_results.values() if r.get('status') == 'SUCCESS']),
                'total_rows_processed': len(sample_data),
                'results_by_file': sql_results
            }
        }, f, indent=2)
    
    logger.info(f"🦆 DuckDB SQL analysis completed!")
    logger.info(f"📄 SQL report saved: {sql_report_path}")


def run_validation_only(args):
    """Run comprehensive validation only."""
    logger.info("🔍 Running comprehensive validation...")
    
    validator = BattleManualValidator()
    validation_results = validator.run_comprehensive_validation()
    
    # Save validation report
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / 'battle_manual_validation_report.json'
    validator.export_validation_report(str(report_path))
    
    print_validation_summary(validation_results)
    
    if validation_results['battle_manual_validation']['overall_status'] == 'PASS':
        logger.info("✅ All validation tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some validation tests failed!")
        sys.exit(1)


def run_dry_run(args):
    """Show what would be executed without running."""
    logger.info("🔍 Battle Manual Dry Run - Showing execution plan...")
    
    patches = parse_patches(args.patches) or ['25.17', '25.18', '25.19']
    
    dry_run_plan = {
        'execution_plan': {
            'patches_to_process': patches,
            'priority_level': args.priority,
            'validation_enabled': not args.skip_validation,
            'export_all_panels': args.export_all,
            'sql_only_mode': args.sql_only,
            'configuration_file': args.config,
            'silver_data_path': args.silver_data,
            'output_directory': args.output_dir
        },
        'workflow_steps': [
            'Step 0: Input Layer Loading (Silver data + dimensions)',
            'Step 1: Unified Grain Establishment (hero + combo layers)',
            'Step 2: Core 20 Metrics Implementation',
            'Step 3: Calculation Order (batch processing)',
            'Step 4: DuckDB Implementation (SQL analysis)',
            'Step 5: Output Interpretation (insights generation)',
            'Step 6: Priority Export (quantitative panels)'
        ],
        'expected_outputs': [
            'entity_panel.jsonl (≤3k rows, CONFIDENT priority)',
            'context_panel.jsonl (research insights)',
            'patch_summary.jsonl (version comparison)',
            'battle_manual_workflow_summary.json',
            'panels_export_summary.json'
        ]
    }
    
    print("\n🔍 BATTLE MANUAL DRY RUN")
    print("=" * 50)
    print(f"📊 Patches to process: {patches}")
    print(f"🎯 Priority level: {args.priority}")
    print(f"✅ Validation: {'Enabled' if not args.skip_validation else 'Disabled'}")
    print(f"📋 Export panels: {'Yes' if args.export_all else 'No'}")
    print(f"📁 Output directory: {args.output_dir}")
    
    print(f"\n🚀 Workflow Steps:")
    for i, step in enumerate(dry_run_plan['workflow_steps'], 1):
        print(f"   {i}. {step}")
    
    print(f"\n📄 Expected Outputs:")
    for output in dry_run_plan['expected_outputs']:
        print(f"   - {output}")
    
    # Save dry run plan
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    plan_path = output_dir / 'battle_manual_dry_run_plan.json'
    with open(plan_path, 'w') as f:
        json.dump(dry_run_plan, f, indent=2)
    
    print(f"\n📋 Dry run plan saved: {plan_path}")
    print("\nTo execute this plan, run without --dry-run flag.")


def parse_patches(patches_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated patch string."""
    if not patches_str:
        return None
    return [p.strip() for p in patches_str.split(',')]


def generate_sample_data():
    """Generate sample data for testing."""
    import numpy as np
    
    champions = ['Jinx', 'Azir', 'Graves', 'Garen', 'Thresh']
    roles = ['ADC', 'MID', 'JUNGLE', 'TOP', 'SUPPORT']
    
    sample_data = []
    for i in range(100):
        sample_data.append({
            'match_id': f'sample_match_{i}',
            'participant_id': f'participant_{i}',
            'patch_version': '25.18',
            'champion': champions[i % len(champions)],
            'role': roles[i % len(roles)],
            'win': 1 if np.random.random() > 0.5 else 0,
            'kills': np.random.randint(0, 15),
            'deaths': np.random.randint(0, 10),
            'assists': np.random.randint(0, 20),
            'game_duration_minutes': np.random.randint(20, 50),
            'total_damage_to_champions': np.random.randint(10000, 50000),
            'quality_score': 0.9,
            'item_0': 'Infinity Edge',
            'item_1': 'Phantom Dancer', 
            'item_2': 'Bloodthirster',
            'keystone_rune': 'Conqueror',
            'primary_rune_tree': 'Precision',
            'spell_1': 'Flash',
            'spell_2': 'Heal'
        })
    
    return sample_data


def generate_final_report(workflow_results: dict, args) -> dict:
    """Generate final execution report."""
    return {
        'battle_manual_execution_report': {
            'version': '1.0',
            'execution_timestamp': datetime.now(timezone.utc).isoformat(),
            'execution_parameters': {
                'patches_processed': args.patches,
                'priority_level': args.priority,
                'validation_enabled': not args.skip_validation,
                'export_all_panels': args.export_all,
                'output_directory': args.output_dir
            },
            'workflow_results': workflow_results,
            'execution_status': 'SUCCESS',
            'battle_manual_version': '1.0'
        }
    }


def print_validation_summary(validation_results: dict):
    """Print validation summary."""
    summary = validation_results['battle_manual_validation']['summary']
    
    print(f"\n🔍 VALIDATION SUMMARY")
    print("=" * 40)
    print(f"📊 Total Categories: {summary['total_validation_categories']}")
    print(f"✅ Passed: {summary['passed_categories']}")
    print(f"❌ Failed: {summary['failed_categories']}")
    print(f"📈 Success Rate: {summary['success_rate']:.1%}")
    print(f"🎯 Overall Status: {summary['overall_status']}")
    
    if summary['failed_categories_list']:
        print(f"\n❌ Failed Categories:")
        for category in summary['failed_categories_list']:
            print(f"   - {category}")


def print_success_summary(final_report: dict):
    """Print execution success summary."""
    workflow = final_report['battle_manual_execution_report']['workflow_results']
    
    print(f"\n🎉 BATTLE MANUAL EXECUTION SUCCESS")
    print("=" * 45)
    print(f"⏱️  Execution Time: {workflow.get('processing_stats', {}).get('duration_seconds', 0):.1f}s")
    print(f"📊 Records Processed: {workflow.get('processing_stats', {}).get('records_processed', 0)}")
    print(f"📋 Panels Generated: {workflow.get('processing_stats', {}).get('panels_generated', 0)}")
    print(f"🎯 Workflow Status: {workflow.get('workflow_completion_status', 'UNKNOWN')}")
    
    if 'panel_exports' in workflow:
        print(f"\n📋 Panel Export Files:")
        for panel_type, path in workflow['panel_exports'].items():
            print(f"   - {panel_type}: {path}")


if __name__ == "__main__":
    main()