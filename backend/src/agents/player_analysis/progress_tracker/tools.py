"""ProgressTrackerAgent - Progress Tracking Tools"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from src.core.statistical_utils import wilson_ci_tuple as wilson_confidence_interval


def load_recent_packs(packs_dir: str, window_size: int = 10) -> Dict[str, Any]:
    """加载最近N个版本的packs"""
    packs_dir = Path(packs_dir)
    pack_files = sorted(packs_dir.glob("pack_*.json"))[-window_size:]

    packs = {}
    for pack_file in pack_files:
        with open(pack_file, 'r') as f:
            pack = json.load(f)
            packs[pack["patch"]] = pack
    return packs


def analyze_progress(recent_packs: Dict[str, Any]) -> Dict[str, Any]:
    """分析进步趋势（前半 vs 后半对比）"""
    patches = sorted(recent_packs.keys())
    mid = len(patches) // 2

    early_patches = patches[:mid]
    late_patches = patches[mid:]

    def aggregate_stats(patch_list):
        total_games = total_wins = 0
        for patch in patch_list:
            pack = recent_packs[patch]
            for cr in pack.get("by_cr", []):
                total_games += cr["games"]
                total_wins += cr["wins"]
        wr = total_wins / total_games if total_games > 0 else 0
        ci_lo, ci_hi = wilson_confidence_interval(total_wins, total_games)
        return {"games": total_games, "wins": total_wins, "winrate": wr, "ci_lo": ci_lo, "ci_hi": ci_hi}

    early = aggregate_stats(early_patches)
    late = aggregate_stats(late_patches)

    improvement = late["winrate"] - early["winrate"]
    trend = "improving" if improvement > 0.03 else ("declining" if improvement < -0.03 else "stable")

    return {
        "early_half": early,
        "late_half": late,
        "improvement": round(improvement, 3),
        "trend": trend,
        "total_patches": len(patches),
        "patches_analyzed": {"early": early_patches, "late": late_patches}
    }


def format_analysis_for_prompt(analysis: Dict[str, Any]) -> str:
    """格式化分析数据"""
    early = analysis["early_half"]
    late = analysis["late_half"]

    return f"""# 进步追踪分析数据

**总版本数**: {analysis['total_patches']}
**整体趋势**: {analysis['trend']}
**进步幅度**: {analysis['improvement']:+.1%}

## 早期阶段 (前 {len(analysis['patches_analyzed']['early'])} 个版本)
- 游戏数: {early['games']}
- 胜率: {early['winrate']:.1%} (CI: {early['ci_lo']:.1%} - {early['ci_hi']:.1%})

## 后期阶段 (后 {len(analysis['patches_analyzed']['late'])} 个版本)
- 游戏数: {late['games']}
- 胜率: {late['winrate']:.1%} (CI: {late['ci_lo']:.1%} - {late['ci_hi']:.1%})

**对比**: 后期相比早期胜率变化 {analysis['improvement']:+.1%}
"""
