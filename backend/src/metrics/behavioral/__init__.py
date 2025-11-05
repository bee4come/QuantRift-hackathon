"""
Behavioral Metrics Package for League of Legends Analytics

This package provides behavioral metrics analysis modules:
- pick_attach_rates: Champion pick frequency and item attachment rates
- synergy_analysis: Champion co-occurrence and synergy analysis  
- rune_analysis: Rune page win rate analysis
- behavioral_metrics_runner: Unified runner for all behavioral metrics
"""

from .pick_attach_rates import PickAttachRateAnalyzer
from .synergy_analysis import ChampionSynergyAnalyzer
from .rune_analysis import RunePageAnalyzer
from .behavioral_metrics_runner import BehavioralMetricsRunner

__all__ = [
    'PickAttachRateAnalyzer',
    'ChampionSynergyAnalyzer', 
    'RunePageAnalyzer',
    'BehavioralMetricsRunner'
]