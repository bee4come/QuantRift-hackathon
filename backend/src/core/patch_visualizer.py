#!/usr/bin/env python3
"""
Patch Visualization Module
Purpose: Generate visualizations and reports for patch impact analysis
Creates charts, tables, and formatted reports for patch comparison results
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime

# Set up matplotlib for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PatchVisualizer:
    """
    Patch Impact Visualization Engine
    Creates charts and reports for patch quantification analysis
    """

    def __init__(self, output_dir: str = "results/patch_analysis/"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_winrate_change_chart(self, winrate_changes: Dict[str, Dict[str, float]],
                                  patch_a: str, patch_b: str,
                                  top_n: int = 20) -> str:
        """Create bar chart showing champion winrate changes"""

        # Prepare data
        changes_list = []
        for champion_role, data in winrate_changes.items():
            champion, role = champion_role.split('_', 1)
            changes_list.append({
                'champion_role': f"{champion} ({role})",
                'winrate_change': data['absolute_change'],
                'winrate_before': data['winrate_before'],
                'winrate_after': data['winrate_after'],
                'sample_size': min(data['sample_size_before'], data['sample_size_after'])
            })

        # Sort by absolute change
        changes_list.sort(key=lambda x: abs(x['winrate_change']), reverse=True)

        # Take top N
        top_changes = changes_list[:top_n]

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 10))

        # Extract data for plotting
        champions = [item['champion_role'] for item in top_changes]
        changes = [item['winrate_change'] * 100 for item in top_changes]  # Convert to percentage
        colors = ['green' if change > 0 else 'red' for change in changes]

        # Create horizontal bar chart
        bars = ax.barh(champions, changes, color=colors, alpha=0.7)

        # Customize chart
        ax.set_xlabel('Winrate Change (%)', fontsize=12)
        ax.set_title(f'Champion Winrate Changes: {patch_a} → {patch_b}\n(Top {top_n} by magnitude)',
                    fontsize=14, fontweight='bold')
        ax.axvline(x=0, color='black', linestyle='-', alpha=0.3)

        # Add value labels on bars
        for i, (bar, change) in enumerate(zip(bars, changes)):
            ax.text(change + (0.1 if change > 0 else -0.1), i, f'{change:+.1f}%',
                   va='center', ha='left' if change > 0 else 'right', fontweight='bold')

        # Adjust layout
        plt.tight_layout()

        # Save chart
        output_path = self.output_dir / f"winrate_changes_{patch_a}_to_{patch_b}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Winrate change chart saved to {output_path}")
        return str(output_path)

    def create_meta_shift_overview(self, role_meta_changes: Dict[str, Dict[str, Any]],
                                 patch_a: str, patch_b: str) -> str:
        """Create overview chart of meta shifts by role"""

        # Prepare data
        roles = list(role_meta_changes.keys())
        winrate_changes = [role_meta_changes[role].get('avg_winrate_change', 0) * 100 for role in roles]
        diversity_changes = [role_meta_changes[role].get('diversity_change', 0) for role in roles]
        top_champ_changed = [role_meta_changes[role].get('top_champion_changed', False) for role in roles]

        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Average winrate changes by role
        bars1 = ax1.bar(roles, winrate_changes, color='skyblue', alpha=0.7)
        ax1.set_title('Average Winrate Change by Role', fontweight='bold')
        ax1.set_ylabel('Winrate Change (%)')
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)

        # Add value labels
        for bar, value in zip(bars1, winrate_changes):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height > 0 else -0.1),
                    f'{value:+.2f}%', ha='center', va='bottom' if height > 0 else 'top')

        # 2. Champion diversity changes
        colors2 = ['green' if x > 0 else 'red' if x < 0 else 'gray' for x in diversity_changes]
        bars2 = ax2.bar(roles, diversity_changes, color=colors2, alpha=0.7)
        ax2.set_title('Champion Diversity Change by Role', fontweight='bold')
        ax2.set_ylabel('Change in Viable Champions')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)

        # Add value labels
        for bar, value in zip(bars2, diversity_changes):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height > 0 else -0.1),
                    f'{value:+.0f}', ha='center', va='bottom' if height > 0 else 'top')

        # 3. Top champion changes
        changed_colors = ['orange' if changed else 'lightblue' for changed in top_champ_changed]
        ax3.bar(roles, [1 if changed else 0 for changed in top_champ_changed],
               color=changed_colors, alpha=0.7)
        ax3.set_title('Top Champion Changed by Role', fontweight='bold')
        ax3.set_ylabel('Top Champion Changed')
        ax3.set_ylim(-0.1, 1.1)
        ax3.set_yticks([0, 1])
        ax3.set_yticklabels(['No', 'Yes'])

        # 4. Meta summary table
        ax4.axis('off')
        table_data = []
        for role in roles:
            data = role_meta_changes[role]
            table_data.append([
                role,
                f"{data.get('avg_winrate_change', 0)*100:+.2f}%",
                f"{data.get('diversity_change', 0):+.0f}",
                data.get('top_champion_before', 'N/A'),
                data.get('top_champion_after', 'N/A')
            ])

        table = ax4.table(cellText=table_data,
                         colLabels=['Role', 'Avg WR Δ', 'Diversity Δ', 'Top Before', 'Top After'],
                         cellLoc='center', loc='center',
                         bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        ax4.set_title('Meta Changes Summary', fontweight='bold', pad=20)

        # Overall title
        fig.suptitle(f'Meta Shift Analysis: {patch_a} → {patch_b}',
                    fontsize=16, fontweight='bold', y=0.98)

        # Adjust layout
        plt.tight_layout()

        # Save chart
        output_path = self.output_dir / f"meta_shift_overview_{patch_a}_to_{patch_b}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Meta shift overview saved to {output_path}")
        return str(output_path)

    def create_pick_rate_comparison(self, pickrate_changes: Dict[str, Dict[str, float]],
                                  patch_a: str, patch_b: str, top_n: int = 15) -> str:
        """Create scatter plot showing pick rate vs winrate changes"""

        # Prepare data
        scatter_data = []
        for champion_role, data in pickrate_changes.items():
            champion, role = champion_role.split('_', 1)
            scatter_data.append({
                'champion': champion,
                'role': role,
                'pickrate_change': data['absolute_change'] * 100,  # Convert to percentage
                'pickrate_before': data['pickrate_before'] * 100,
                'pickrate_after': data['pickrate_after'] * 100
            })

        # Sort by absolute pick rate change
        scatter_data.sort(key=lambda x: abs(x['pickrate_change']), reverse=True)
        scatter_data = scatter_data[:top_n]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # 1. Pick rate changes bar chart
        champions = [f"{item['champion']} ({item['role']})" for item in scatter_data]
        changes = [item['pickrate_change'] for item in scatter_data]
        colors = ['green' if change > 0 else 'red' for change in changes]

        bars = ax1.barh(champions, changes, color=colors, alpha=0.7)
        ax1.set_xlabel('Pick Rate Change (%)', fontsize=12)
        ax1.set_title(f'Pick Rate Changes: {patch_a} → {patch_b}', fontweight='bold')
        ax1.axvline(x=0, color='black', linestyle='-', alpha=0.3)

        # Add value labels
        for i, (bar, change) in enumerate(zip(bars, changes)):
            ax1.text(change + (0.1 if change > 0 else -0.1), i, f'{change:+.1f}%',
                    va='center', ha='left' if change > 0 else 'right', fontweight='bold')

        # 2. Before vs After scatter plot
        before_rates = [item['pickrate_before'] for item in scatter_data]
        after_rates = [item['pickrate_after'] for item in scatter_data]

        ax2.scatter(before_rates, after_rates, alpha=0.7, s=100)

        # Add diagonal line for no change
        max_rate = max(max(before_rates), max(after_rates))
        ax2.plot([0, max_rate], [0, max_rate], 'r--', alpha=0.5, label='No Change')

        ax2.set_xlabel(f'Pick Rate Before ({patch_a}) %', fontsize=12)
        ax2.set_ylabel(f'Pick Rate After ({patch_b}) %', fontsize=12)
        ax2.set_title('Pick Rate: Before vs After', fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Annotate outliers
        for i, item in enumerate(scatter_data[:5]):  # Top 5 changes
            ax2.annotate(f"{item['champion']}\n({item['role']})",
                        (before_rates[i], after_rates[i]),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=8, alpha=0.8)

        plt.tight_layout()

        # Save chart
        output_path = self.output_dir / f"pickrate_comparison_{patch_a}_to_{patch_b}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Pick rate comparison saved to {output_path}")
        return str(output_path)

    def create_statistical_significance_summary(self, statistical_tests: Dict[str, Any],
                                              patch_a: str, patch_b: str) -> str:
        """Create summary of statistical significance tests"""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # 1. Overall test results
        overall_test = statistical_tests.get('overall_winrate_test', {})

        test_results = [
            ['Test Type', overall_test.get('test_type', 'N/A')],
            ['Statistic', f"{overall_test.get('statistic', 0):.3f}"],
            ['P-value', f"{overall_test.get('p_value', 1):.6f}"],
            ['Significant', 'Yes' if overall_test.get('significant', False) else 'No'],
            ['Interpretation', overall_test.get('interpretation', 'N/A')]
        ]

        ax1.axis('off')
        table1 = ax1.table(cellText=test_results,
                          colLabels=['Parameter', 'Value'],
                          cellLoc='left', loc='center',
                          bbox=[0, 0, 1, 1])
        table1.auto_set_font_size(False)
        table1.set_fontsize(11)
        table1.scale(1, 2)
        ax1.set_title(f'Overall Winrate Distribution Test\n{patch_a} vs {patch_b}',
                     fontweight='bold', pad=20)

        # 2. Champion-specific test summary
        champion_tests = statistical_tests.get('champion_tests', {})

        if champion_tests:
            p_values = [test['p_value'] for test in champion_tests.values()]
            significant_count = sum(1 for test in champion_tests.values() if test['significant'])

            # P-value distribution histogram
            ax2.hist(p_values, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax2.axvline(x=0.05, color='red', linestyle='--', alpha=0.7, label='α = 0.05')
            ax2.set_xlabel('P-value', fontsize=12)
            ax2.set_ylabel('Count', fontsize=12)
            ax2.set_title(f'Champion-Specific Test P-values\n{significant_count}/{len(champion_tests)} Significant',
                         fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'No champion-specific tests available',
                    ha='center', va='center', transform=ax2.transAxes, fontsize=14)
            ax2.set_title('Champion-Specific Tests', fontweight='bold')

        plt.tight_layout()

        # Save chart
        output_path = self.output_dir / f"statistical_tests_{patch_a}_to_{patch_b}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Statistical tests summary saved to {output_path}")
        return str(output_path)

    def generate_html_report(self, report_data: Dict[str, Any],
                           chart_paths: Dict[str, str]) -> str:
        """Generate comprehensive HTML report"""

        patch_a = report_data['patch_comparison']['patch_from']
        patch_b = report_data['patch_comparison']['patch_to']

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Patch Impact Analysis: {patch_a} → {patch_b}</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
        }}
        .executive-summary {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .metric-card {{
            display: inline-block;
            background-color: white;
            padding: 15px;
            margin: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            min-width: 200px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2980b9;
        }}
        .metric-label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .champion-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 15px 0;
        }}
        .champion-item {{
            background-color: #3498db;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 14px;
        }}
        .winner {{
            background-color: #27ae60;
        }}
        .loser {{
            background-color: #e74c3c;
        }}
        .chart-container {{
            text-align: center;
            margin: 20px 0;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .table-container {{
            overflow-x: auto;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .positive {{
            color: #27ae60;
            font-weight: bold;
        }}
        .negative {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .timestamp {{
            text-align: right;
            color: #7f8c8d;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 Patch Impact Analysis: {patch_a} → {patch_b}</h1>

        <div class="executive-summary">
            <h2>📊 Executive Summary</h2>
            <div class="metric-card">
                <div class="metric-value">{report_data['patch_comparison']['meta_shift_score']:.3f}</div>
                <div class="metric-label">Meta Shift Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report_data['executive_summary']['overall_meta_stability']}</div>
                <div class="metric-label">Meta Stability</div>
            </div>

            <h3>🏆 Top Winners</h3>
            <div class="champion-list">
        """

        # Add top winners
        for winner in report_data['executive_summary']['top_3_winners']:
            html_content += f'<span class="champion-item winner">{winner["champion_name"]} ({winner["role"]}) +{winner["winrate_change"]*100:.1f}%</span>'

        html_content += """
            </div>

            <h3>📉 Top Losers</h3>
            <div class="champion-list">
        """

        # Add top losers
        for loser in report_data['executive_summary']['top_3_losers']:
            html_content += f'<span class="champion-item loser">{loser["champion_name"]} ({loser["role"]}) {loser["winrate_change"]*100:+.1f}%</span>'

        html_content += """
            </div>
        </div>
        """

        # Add charts
        if 'winrate_changes' in chart_paths:
            html_content += f"""
        <h2>📈 Winrate Changes</h2>
        <div class="chart-container">
            <img src="{Path(chart_paths['winrate_changes']).name}" alt="Winrate Changes Chart">
        </div>
        """

        if 'meta_shift_overview' in chart_paths:
            html_content += f"""
        <h2>🔄 Meta Shift Overview</h2>
        <div class="chart-container">
            <img src="{Path(chart_paths['meta_shift_overview']).name}" alt="Meta Shift Overview">
        </div>
        """

        if 'pickrate_comparison' in chart_paths:
            html_content += f"""
        <h2>📊 Pick Rate Analysis</h2>
        <div class="chart-container">
            <img src="{Path(chart_paths['pickrate_comparison']).name}" alt="Pick Rate Comparison">
        </div>
        """

        if 'statistical_tests' in chart_paths:
            html_content += f"""
        <h2>🔬 Statistical Analysis</h2>
        <div class="chart-container">
            <img src="{Path(chart_paths['statistical_tests']).name}" alt="Statistical Tests">
        </div>
        """

        # Add methodology
        html_content += f"""
        <h2>🧪 Methodology</h2>
        <div class="table-container">
            <table>
                <tr>
                    <th>Component</th>
                    <th>Method</th>
                </tr>
                <tr>
                    <td>Confidence Intervals</td>
                    <td>{report_data['methodology']['confidence_intervals']}</td>
                </tr>
                <tr>
                    <td>Minimum Sample Size</td>
                    <td>{report_data['methodology']['minimum_sample_size']}</td>
                </tr>
                <tr>
                    <td>Meta Shift Metric</td>
                    <td>{report_data['methodology']['meta_shift_metric']}</td>
                </tr>
                <tr>
                    <td>Statistical Tests</td>
                    <td>{', '.join(report_data['methodology']['statistical_tests'])}</td>
                </tr>
            </table>
        </div>

        <div class="timestamp">
            Generated: {report_data['patch_comparison']['analysis_timestamp']}
        </div>
    </div>
</body>
</html>
        """

        # Save HTML report
        output_path = self.output_dir / f"patch_analysis_report_{patch_a}_to_{patch_b}.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"HTML report saved to {output_path}")
        return str(output_path)

    def create_comprehensive_visualization(self, comparison_result, patch_a: str, patch_b: str) -> Dict[str, str]:
        """Create all visualizations for a patch comparison"""
        chart_paths = {}

        # Create winrate changes chart
        chart_paths['winrate_changes'] = self.create_winrate_change_chart(
            comparison_result.champion_winrate_changes, patch_a, patch_b
        )

        # Create meta shift overview
        chart_paths['meta_shift_overview'] = self.create_meta_shift_overview(
            comparison_result.role_meta_changes, patch_a, patch_b
        )

        # Create pick rate comparison
        chart_paths['pickrate_comparison'] = self.create_pick_rate_comparison(
            comparison_result.pickrate_changes, patch_a, patch_b
        )

        # Create statistical tests summary
        chart_paths['statistical_tests'] = self.create_statistical_significance_summary(
            comparison_result.statistical_tests, patch_a, patch_b
        )

        return chart_paths