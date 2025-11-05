"""
Analytics Module
数据分析模块 - 提供可复用的分析类

用于生成玩家对比、英雄推荐等高级分析所需的辅助数据
"""

from .rank_baseline import RankBaselineGenerator
from .champion_similarity import ChampionSimilarityCalculator
from .meta_tier import MetaTierClassifier
from .power_curve import PowerCurveGenerator
from .counter_matrix import CounterMatrixCalculator, load_counter_matrix
from .composition_analyzer import CompositionAnalyzer
from .match_similarity import MatchSimilarityFinder
from .teammate_detector import FrequentTeammateDetector

__all__ = [
    'RankBaselineGenerator',
    'ChampionSimilarityCalculator',
    'MetaTierClassifier',
    'PowerCurveGenerator',
    'CounterMatrixCalculator',
    'load_counter_matrix',
    'CompositionAnalyzer',
    'MatchSimilarityFinder',
    'FrequentTeammateDetector'
]
