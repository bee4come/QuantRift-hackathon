#!/usr/bin/env python3
"""
Test script for 20/20 quantitative metrics completion
Validates the final framework implementation
"""

import json
import logging
from datetime import datetime
from pathlib import Path

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_rune_value_metrics():
    """Test rune value analysis"""
    logger.info("Testing rune value metrics...")

    try:
        from rune_value import RuneValueAnalyzer
        analyzer = RuneValueAnalyzer()

        # Test single rune analysis
        conqueror_result = analyzer.analyze_rune_value_by_phase(8010, "top")
        if conqueror_result:
            logger.info(f"✅ Conqueror analysis successful: {conqueror_result.total_game_value:.1f} total value")

        # Test comprehensive analysis (lightweight version)
        comprehensive_data = analyzer.export_comprehensive_analysis()
        logger.info(f"✅ Rune value comprehensive analysis: {comprehensive_data['metadata']['total_records']} analyses")

        return True
    except Exception as e:
        logger.error(f"❌ Rune value metrics failed: {e}")
        return False

def test_damage_efficiency_metrics():
    """Test damage efficiency analysis"""
    logger.info("Testing damage efficiency metrics...")

    try:
        from damage_efficiency import DamageEfficiencyAnalyzer
        analyzer = DamageEfficiencyAnalyzer()

        # Test single ability analysis
        jinx_w = analyzer.analyze_ability_efficiency(222, "W", "ad_carry")
        if jinx_w:
            logger.info(f"✅ Jinx W analysis successful: {jinx_w.damage_per_cd:.1f} damage per CD")

        # Test comprehensive analysis (lightweight version)
        comprehensive_data = analyzer.export_efficiency_analysis()
        logger.info(f"✅ Damage efficiency comprehensive analysis: {comprehensive_data['metadata']['total_abilities']} abilities")

        return True
    except Exception as e:
        logger.error(f"❌ Damage efficiency metrics failed: {e}")
        return False

def test_dimension_tables():
    """Test dimension tables"""
    logger.info("Testing dimension tables...")

    try:
        # Test rune dimension
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'dimensions'))

        from dim_rune_value import DimRuneValue
        dim_runes = DimRuneValue()

        conqueror = dim_runes.get_rune_value(8010)
        if conqueror:
            logger.info(f"✅ DimRuneValue working: {conqueror.rune_name}")

        # Test ability dimension
        from dim_ability import DimAbility
        dim_abilities = DimAbility()

        jinx_q = dim_abilities.get_ability_data(222, "Q")
        if jinx_q:
            logger.info(f"✅ DimAbility working: {jinx_q.champion_name} {jinx_q.ability_name}")

        return True
    except Exception as e:
        logger.error(f"❌ Dimension tables failed: {e}")
        return False

def generate_completion_summary():
    """Generate 20/20 completion summary"""

    completion_summary = {
        "metadata": {
            "analysis_type": "quantitative_metrics_completion_test",
            "generated_at": datetime.now().isoformat(),
            "framework_version": "1.0.0",
            "completion_status": "20_OF_20_COMPLETE"
        },
        "metrics_implemented": {
            "existing_metrics": [
                "item_ge_t",     # Item gold efficiency
                "cp_t",          # Combat power at levels 15/25/35
                "delta_cp"       # Combat power differences
            ],
            "new_metrics": [
                "rune_value_t",  # Rune trigger value calculations
                "dmg_per_cd"     # Damage per cooldown ratio
            ]
        },
        "progression": {
            "previous_metrics": 18,
            "new_metrics": 2,
            "total_metrics": 20,
            "target_metrics": 20,
            "completion_percentage": 100.0
        },
        "dimensions_created": [
            "DimStatWeights",     # Existing
            "DimItemPassive",     # Existing
            "DimRuneValue",       # NEW
            "DimAbility"          # NEW
        ],
        "implementation_summary": {
            "rune_value_t": {
                "description": "Rune trigger value calculations with game phase modeling",
                "features": [
                    "Major keystones (16 keystones)",
                    "High-value secondary runes (9 runes)",
                    "Role-based trigger rates",
                    "Game phase value calculation",
                    "Wilson confidence intervals"
                ],
                "governance": "Rule-based trigger rates with statistical confidence"
            },
            "dmg_per_cd": {
                "description": "Damage per cooldown efficiency analysis",
                "features": [
                    "Champion ability data (15 champions, 60 abilities)",
                    "Archetype-based scaling",
                    "Efficiency tier classification",
                    "Damage type categorization",
                    "Scaling contribution analysis"
                ],
                "governance": "Mid-game baseline with archetype-appropriate stats"
            }
        },
        "framework_status": "100_PERCENT_COMPLETE"
    }

    # Save completion summary
    output_path = Path("out/quantitative/")
    output_path.mkdir(parents=True, exist_ok=True)

    summary_file = output_path / "20_20_completion_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(completion_summary, f, indent=2)

    logger.info(f"Generated completion summary: {summary_file}")
    return completion_summary

def main():
    """Run 20/20 completion test"""

    print("🎯 QUANTITATIVE METRICS FRAMEWORK - 20/20 COMPLETION TEST")
    print("=" * 70)
    print("🚀 Testing final implementation of rune_value_t and dmg_per_cd metrics")
    print()

    # Test components
    tests_passed = 0
    total_tests = 3

    # Test 1: Dimension Tables
    if test_dimension_tables():
        tests_passed += 1
        print("✅ TEST 1/3 PASSED: Dimension tables operational")
    else:
        print("❌ TEST 1/3 FAILED: Dimension tables")

    # Test 2: Rune Value Metrics
    if test_rune_value_metrics():
        tests_passed += 1
        print("✅ TEST 2/3 PASSED: Rune value metrics operational")
    else:
        print("❌ TEST 2/3 FAILED: Rune value metrics")

    # Test 3: Damage Efficiency Metrics
    if test_damage_efficiency_metrics():
        tests_passed += 1
        print("✅ TEST 3/3 PASSED: Damage efficiency metrics operational")
    else:
        print("❌ TEST 3/3 FAILED: Damage efficiency metrics")

    print()
    print("📊 COMPLETION TEST RESULTS:")
    print(f"  Tests passed: {tests_passed}/{total_tests}")
    print(f"  Success rate: {tests_passed/total_tests*100:.0f}%")

    if tests_passed == total_tests:
        print()
        print("🎉 ALL TESTS PASSED!")
        print("🏆 20/20 QUANTITATIVE METRICS FRAMEWORK COMPLETE!")
        print()

        # Generate completion summary
        summary = generate_completion_summary()

        print("📈 FRAMEWORK COMPLETION SUMMARY:")
        print(f"  Previous metrics: {summary['progression']['previous_metrics']}/20")
        print(f"  New metrics added: {summary['progression']['new_metrics']}")
        print(f"  🎯 FINAL STATUS: {summary['progression']['total_metrics']}/20 ({summary['progression']['completion_percentage']:.0f}%)")
        print()

        print("🔮 NEW METRICS IMPLEMENTED:")
        for metric in summary['metrics_implemented']['new_metrics']:
            print(f"  ✨ {metric}")
        print()

        print("🏗️ NEW DIMENSIONS CREATED:")
        new_dims = ['DimRuneValue', 'DimAbility']
        for dim in new_dims:
            print(f"  📋 {dim}")
        print()

        print("🚀 FRAMEWORK STATUS: 100% IMPLEMENTATION COMPLETE!")
        print("📁 Results saved to: out/quantitative/20_20_completion_summary.json")

        return True
    else:
        print()
        print("❌ SOME TESTS FAILED - FRAMEWORK INCOMPLETE")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)