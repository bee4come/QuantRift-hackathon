"""
Player Analysis Agent Suite
玩家分析 Agent 套件
"""

import sys
from pathlib import Path
# Add project root to path for test_agents imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from .multi_version.agent import MultiVersionAgent
from .detailed_analysis.agent import DetailedAnalysisAgent
from .version_comparison.agent import VersionComparisonAgent
from .postgame_review.agent import PostgameReviewAgent
from .annual_summary.agent import AnnualSummaryAgent
from .champion_mastery.agent import ChampionMasteryAgent
from .role_specialization.agent import RoleSpecializationAgent
from .progress_tracker.agent import ProgressTrackerAgent
from .weakness_analysis.agent import WeaknessAnalysisAgent
from .peer_comparison.agent import PeerComparisonAgent
from .champion_recommendation.agent import ChampionRecommendationAgent

__all__ = [
    'MultiVersionAgent',
    'DetailedAnalysisAgent',
    'VersionComparisonAgent',
    'PostgameReviewAgent',
    'AnnualSummaryAgent',
    'ChampionMasteryAgent',
    'RoleSpecializationAgent',
    'ProgressTrackerAgent',
    'WeaknessAnalysisAgent',
    'PeerComparisonAgent',
    'ChampionRecommendationAgent'
]
