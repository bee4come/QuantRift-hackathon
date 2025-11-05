#!/usr/bin/env python3
"""
Automated Insight Detection System

Automatically identifies significant patterns, anomalies, and actionable insights
from player performance data without requiring LLM analysis.

This acts as a **pre-processing layer** that highlights key findings for both
users and LLM-based analysis, improving focus and reducing token usage.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InsightSeverity(Enum):
    """Severity levels for insights"""
    CRITICAL = "critical"      # Immediate action needed (e.g., 5-game losing streak)
    HIGH = "high"              # Significant issue (e.g., 30% winrate on main champion)
    MEDIUM = "medium"          # Notable pattern (e.g., worse performance on weekends)
    LOW = "low"                # Minor observation (e.g., slight CS improvement)
    INFO = "info"              # Informational (e.g., most played champion)


class InsightCategory(Enum):
    """Categories of insights"""
    PERFORMANCE_DECLINE = "performance_decline"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    CHAMPION_MASTERY = "champion_mastery"
    ROLE_EFFECTIVENESS = "role_effectiveness"
    STATISTICAL_ANOMALY = "statistical_anomaly"
    TREND_PATTERN = "trend_pattern"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    SURPRISE_INSIGHT = "surprise_insight"  # Surprise Discovery: Unexpected but valuable findings


@dataclass
class Insight:
    """
    Represents a single automated insight
    """
    id: str                          # Unique identifier
    category: InsightCategory        # Type of insight
    severity: InsightSeverity        # Importance level
    title: str                       # Short title (1 line)
    description: str                 # Detailed description (2-3 lines)
    evidence: Dict[str, Any]         # Supporting data
    recommendation: Optional[str]    # Actionable advice
    confidence: float                # Confidence score (0-1)
    priority_score: float            # Priority for ordering (0-100)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'evidence': self.evidence,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'priority_score': self.priority_score
        }


class InsightDetector:
    """
    Core automated insight detection engine

    Analyzes aggregated player data to identify:
    1. Statistical anomalies (outliers, deviations)
    2. Trend patterns (upward/downward, streaks)
    3. Benchmark comparisons (vs peer avg, vs own history)
    4. Behavioral patterns (time-of-day, champion pool)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize detector with configuration

        Args:
            config: Detection thresholds and parameters
        """
        self.config = config or self._default_config()
        self.insights = []

    def _default_config(self) -> Dict[str, Any]:
        """Default detection thresholds"""
        return {
            # Streak detection
            'losing_streak_critical': 5,
            'losing_streak_high': 3,
            'winning_streak_notable': 5,

            # Winrate thresholds
            'winrate_critical_low': 0.35,
            'winrate_high_low': 0.40,
            'winrate_excellent': 0.60,

            # Sample size minimums
            'min_games_champion': 5,
            'min_games_trend': 10,
            'min_games_comparison': 20,

            # Statistical thresholds
            'zscore_threshold': 2.0,  # 2 standard deviations
            'trend_significance': 0.05,  # p-value threshold

            # Confidence weights
            'confidence_weight_sample_size': 0.3,
            'confidence_weight_statistical': 0.4,
            'confidence_weight_magnitude': 0.3
        }

    def detect_insights(self, aggregated_data: Dict[str, Any]) -> List[Insight]:
        """
        Main entry point for insight detection

        Args:
            aggregated_data: Aggregated player statistics from agents

        Returns:
            List of detected insights, sorted by priority
        """
        self.insights = []

        # Run all detection methods
        self._detect_performance_decline(aggregated_data)
        self._detect_performance_improvement(aggregated_data)
        self._detect_champion_mastery_issues(aggregated_data)
        self._detect_role_effectiveness(aggregated_data)
        self._detect_statistical_anomalies(aggregated_data)
        self._detect_trend_patterns(aggregated_data)
        self._detect_behavioral_patterns(aggregated_data)
        self._detect_surprise_insights(aggregated_data)  # Surprise Discovery System

        # Sort by priority
        sorted_insights = sorted(self.insights, key=lambda x: x.priority_score, reverse=True)

        logger.info(f"Detected {len(sorted_insights)} insights across {len(set(i.category for i in sorted_insights))} categories")

        return sorted_insights

    def _detect_performance_decline(self, data: Dict[str, Any]) -> None:
        """Detect recent performance decline patterns"""

        # Check for losing streaks
        recent_results = data.get('recent_match_results', [])
        if len(recent_results) >= self.config['losing_streak_critical']:
            consecutive_losses = 0
            for result in recent_results:
                if not result.get('win', False):
                    consecutive_losses += 1
                else:
                    break

            if consecutive_losses >= self.config['losing_streak_critical']:
                self.insights.append(Insight(
                    id=f"decline_losing_streak_{consecutive_losses}",
                    category=InsightCategory.PERFORMANCE_DECLINE,
                    severity=InsightSeverity.CRITICAL,
                    title=f"🚨 {consecutive_losses}-Game Losing Streak Detected",
                    description=f"You've lost {consecutive_losses} consecutive games. This may indicate tilting, meta shifts, or playstyle issues requiring immediate attention.",
                    evidence={
                        'consecutive_losses': consecutive_losses,
                        'recent_results': recent_results[:consecutive_losses]
                    },
                    recommendation="Take a break (30+ minutes), review VODs of losses, or switch to normals/ARAM to reset mentally.",
                    confidence=0.95,
                    priority_score=95.0
                ))
            elif consecutive_losses >= self.config['losing_streak_high']:
                self.insights.append(Insight(
                    id=f"decline_losing_streak_{consecutive_losses}",
                    category=InsightCategory.PERFORMANCE_DECLINE,
                    severity=InsightSeverity.HIGH,
                    title=f"⚠️ {consecutive_losses}-Game Losing Streak",
                    description=f"Recent performance shows {consecutive_losses} consecutive losses. Consider adjusting strategy or taking a break.",
                    evidence={
                        'consecutive_losses': consecutive_losses,
                        'recent_results': recent_results[:consecutive_losses]
                    },
                    recommendation="Review recent games for common mistakes, consider champion pool adjustments.",
                    confidence=0.90,
                    priority_score=80.0
                ))

        # Check for winrate decline
        overall_wr = data.get('overall_winrate', 0.5)
        recent_wr = data.get('recent_winrate', 0.5)

        if overall_wr >= 0.50 and recent_wr < self.config['winrate_critical_low']:
            wr_decline = overall_wr - recent_wr
            self.insights.append(Insight(
                id="decline_winrate_drop",
                category=InsightCategory.PERFORMANCE_DECLINE,
                severity=InsightSeverity.HIGH,
                title=f"📉 Winrate Declined: {overall_wr:.1%} → {recent_wr:.1%}",
                description=f"Your recent winrate ({recent_wr:.1%}) is significantly below your historical average ({overall_wr:.1%}), a drop of {wr_decline:.1%}.",
                evidence={
                    'overall_winrate': overall_wr,
                    'recent_winrate': recent_wr,
                    'decline_magnitude': wr_decline
                },
                recommendation="Identify what changed: champion pool, playstyle, game time, or external factors.",
                confidence=0.85,
                priority_score=75.0
            ))

    def _detect_performance_improvement(self, data: Dict[str, Any]) -> None:
        """Detect positive performance trends"""

        # Check for winning streaks
        recent_results = data.get('recent_match_results', [])
        if len(recent_results) >= self.config['winning_streak_notable']:
            consecutive_wins = 0
            for result in recent_results:
                if result.get('win', False):
                    consecutive_wins += 1
                else:
                    break

            if consecutive_wins >= self.config['winning_streak_notable']:
                self.insights.append(Insight(
                    id=f"improvement_winning_streak_{consecutive_wins}",
                    category=InsightCategory.PERFORMANCE_IMPROVEMENT,
                    severity=InsightSeverity.MEDIUM,
                    title=f"🔥 {consecutive_wins}-Game Winning Streak!",
                    description=f"Excellent performance with {consecutive_wins} consecutive wins. Maintain momentum and avoid overconfidence.",
                    evidence={
                        'consecutive_wins': consecutive_wins,
                        'recent_results': recent_results[:consecutive_wins]
                    },
                    recommendation="Keep playing your current champions and maintain focus. Watch for signs of fatigue.",
                    confidence=0.92,
                    priority_score=70.0
                ))

        # Check for winrate improvement
        overall_wr = data.get('overall_winrate', 0.5)
        recent_wr = data.get('recent_winrate', 0.5)

        if recent_wr >= self.config['winrate_excellent'] and recent_wr > overall_wr:
            wr_improvement = recent_wr - overall_wr
            self.insights.append(Insight(
                id="improvement_winrate_rise",
                category=InsightCategory.PERFORMANCE_IMPROVEMENT,
                severity=InsightSeverity.MEDIUM,
                title=f"📈 Winrate Improved: {overall_wr:.1%} → {recent_wr:.1%}",
                description=f"Your recent winrate ({recent_wr:.1%}) is above your historical average ({overall_wr:.1%}), an improvement of {wr_improvement:.1%}.",
                evidence={
                    'overall_winrate': overall_wr,
                    'recent_winrate': recent_wr,
                    'improvement_magnitude': wr_improvement
                },
                recommendation="Analyze what changed positively: champion picks, playstyle adjustments, or external factors. Maintain these patterns.",
                confidence=0.80,
                priority_score=65.0
            ))

    def _detect_champion_mastery_issues(self, data: Dict[str, Any]) -> None:
        """Detect champion-specific performance issues"""

        champion_stats = data.get('champion_performance', {})

        for champion_name, stats in champion_stats.items():
            games_played = stats.get('games', 0)
            winrate = stats.get('winrate', 0.5)

            # Skip if insufficient data
            if games_played < self.config['min_games_champion']:
                continue

            # Check for low winrate on frequently played champions
            if games_played >= 10 and winrate < self.config['winrate_critical_low']:
                self.insights.append(Insight(
                    id=f"champion_low_wr_{champion_name}",
                    category=InsightCategory.CHAMPION_MASTERY,
                    severity=InsightSeverity.HIGH,
                    title=f"⚠️ Low Winrate on {champion_name}: {winrate:.1%}",
                    description=f"Despite {games_played} games, your winrate on {champion_name} is {winrate:.1%}, significantly below expected.",
                    evidence={
                        'champion': champion_name,
                        'games': games_played,
                        'winrate': winrate,
                        'kda': stats.get('kda', 0),
                        'avg_cs': stats.get('avg_cs', 0)
                    },
                    recommendation=f"Consider champion pool adjustment, watch high-elo {champion_name} VODs, or practice in normals.",
                    confidence=0.85,
                    priority_score=72.0
                ))

            # Check for excellent mastery
            elif games_played >= 20 and winrate >= self.config['winrate_excellent']:
                self.insights.append(Insight(
                    id=f"champion_high_wr_{champion_name}",
                    category=InsightCategory.CHAMPION_MASTERY,
                    severity=InsightSeverity.INFO,
                    title=f"⭐ Strong Performance on {champion_name}: {winrate:.1%}",
                    description=f"Excellent {winrate:.1%} winrate over {games_played} games on {champion_name}. This is a reliable pick for climbing.",
                    evidence={
                        'champion': champion_name,
                        'games': games_played,
                        'winrate': winrate,
                        'kda': stats.get('kda', 0)
                    },
                    recommendation=f"Prioritize {champion_name} in ranked. Consider expanding to similar champions.",
                    confidence=0.88,
                    priority_score=60.0
                ))

    def _detect_role_effectiveness(self, data: Dict[str, Any]) -> None:
        """Detect role-specific performance patterns"""

        role_stats = data.get('role_performance', {})

        if len(role_stats) < 2:
            return  # Need multiple roles for comparison

        # Find best and worst roles
        roles_by_wr = sorted(
            [(role, stats) for role, stats in role_stats.items() if stats.get('games', 0) >= self.config['min_games_champion']],
            key=lambda x: x[1].get('winrate', 0),
            reverse=True
        )

        if len(roles_by_wr) >= 2:
            best_role, best_stats = roles_by_wr[0]
            worst_role, worst_stats = roles_by_wr[-1]

            wr_gap = best_stats.get('winrate', 0) - worst_stats.get('winrate', 0)

            if wr_gap >= 0.15:  # 15%+ winrate difference
                self.insights.append(Insight(
                    id="role_effectiveness_gap",
                    category=InsightCategory.ROLE_EFFECTIVENESS,
                    severity=InsightSeverity.MEDIUM,
                    title=f"🎯 Role Performance Gap: {best_role} vs {worst_role}",
                    description=f"Your {best_role} winrate ({best_stats.get('winrate', 0):.1%}) is {wr_gap:.1%} higher than {worst_role} ({worst_stats.get('winrate', 0):.1%}).",
                    evidence={
                        'best_role': best_role,
                        'best_winrate': best_stats.get('winrate', 0),
                        'best_games': best_stats.get('games', 0),
                        'worst_role': worst_role,
                        'worst_winrate': worst_stats.get('winrate', 0),
                        'worst_games': worst_stats.get('games', 0),
                        'gap': wr_gap
                    },
                    recommendation=f"Focus on {best_role} for climbing. Consider role specialization or practice {worst_role} fundamentals.",
                    confidence=0.80,
                    priority_score=65.0
                ))

    def _detect_statistical_anomalies(self, data: Dict[str, Any]) -> None:
        """Detect statistical outliers in performance metrics"""

        # Check CS/min anomalies
        avg_cs_per_min = data.get('avg_cs_per_min', 0)
        expected_cs_by_role = {
            'top': 7.0,
            'jungle': 5.5,
            'mid': 7.5,
            'adc': 8.0,
            'support': 1.5
        }

        primary_role = data.get('primary_role', 'mid').lower()
        expected_cs = expected_cs_by_role.get(primary_role, 6.5)

        cs_deviation = (avg_cs_per_min - expected_cs) / expected_cs

        if cs_deviation < -0.25:  # 25% below expected
            self.insights.append(Insight(
                id="anomaly_low_cs",
                category=InsightCategory.STATISTICAL_ANOMALY,
                severity=InsightSeverity.MEDIUM,
                title=f"📊 CS/min Below Expected: {avg_cs_per_min:.1f}",
                description=f"Your CS/min ({avg_cs_per_min:.1f}) is {abs(cs_deviation):.1%} below expected for {primary_role} ({expected_cs:.1f}).",
                evidence={
                    'actual_cs_per_min': avg_cs_per_min,
                    'expected_cs_per_min': expected_cs,
                    'deviation': cs_deviation,
                    'role': primary_role
                },
                recommendation="Focus on wave management, practice CS drills, minimize roaming/fighting at expense of farm.",
                confidence=0.75,
                priority_score=55.0
            ))

        # Check KDA anomalies
        avg_kda = data.get('avg_kda', 2.0)

        if avg_kda < 1.5:
            self.insights.append(Insight(
                id="anomaly_low_kda",
                category=InsightCategory.STATISTICAL_ANOMALY,
                severity=InsightSeverity.HIGH,
                title=f"⚠️ Low KDA: {avg_kda:.2f}",
                description=f"Your average KDA ({avg_kda:.2f}) is below healthy levels, indicating frequent deaths or low kill participation.",
                evidence={
                    'avg_kda': avg_kda,
                    'avg_kills': data.get('avg_kills', 0),
                    'avg_deaths': data.get('avg_deaths', 0),
                    'avg_assists': data.get('avg_assists', 0)
                },
                recommendation="Focus on positioning, map awareness, and reducing unnecessary deaths. Prioritize survival over kills.",
                confidence=0.80,
                priority_score=68.0
            ))

    def _detect_trend_patterns(self, data: Dict[str, Any]) -> None:
        """Detect temporal trends in performance"""

        # Analyze recent game history for trends
        match_history = data.get('match_history', [])

        if len(match_history) < self.config['min_games_trend']:
            return

        # Extract winrates in chunks (e.g., first 10 vs last 10)
        chunk_size = min(10, len(match_history) // 2)
        recent_chunk = match_history[:chunk_size]
        older_chunk = match_history[-chunk_size:]

        recent_wr = sum(1 for m in recent_chunk if m.get('win', False)) / len(recent_chunk)
        older_wr = sum(1 for m in older_chunk if m.get('win', False)) / len(older_chunk)

        wr_trend = recent_wr - older_wr

        if wr_trend >= 0.15:  # 15%+ improvement
            self.insights.append(Insight(
                id="trend_improving",
                category=InsightCategory.TREND_PATTERN,
                severity=InsightSeverity.MEDIUM,
                title=f"📈 Improving Trend: {older_wr:.1%} → {recent_wr:.1%}",
                description=f"Your winrate has improved from {older_wr:.1%} (older games) to {recent_wr:.1%} (recent games), showing positive momentum.",
                evidence={
                    'older_winrate': older_wr,
                    'recent_winrate': recent_wr,
                    'improvement': wr_trend,
                    'games_analyzed': len(match_history)
                },
                recommendation="Maintain current approach and champion pool. Continue practicing fundamentals.",
                confidence=0.70,
                priority_score=60.0
            ))
        elif wr_trend <= -0.15:  # 15%+ decline
            self.insights.append(Insight(
                id="trend_declining",
                category=InsightCategory.TREND_PATTERN,
                severity=InsightSeverity.HIGH,
                title=f"📉 Declining Trend: {older_wr:.1%} → {recent_wr:.1%}",
                description=f"Your winrate has declined from {older_wr:.1%} (older games) to {recent_wr:.1%} (recent games), indicating worsening performance.",
                evidence={
                    'older_winrate': older_wr,
                    'recent_winrate': recent_wr,
                    'decline': wr_trend,
                    'games_analyzed': len(match_history)
                },
                recommendation="Review what changed: champion pool, playstyle, game time, mental state. Consider taking a break.",
                confidence=0.72,
                priority_score=73.0
            ))

    def _detect_behavioral_patterns(self, data: Dict[str, Any]) -> None:
        """Detect behavioral patterns affecting performance"""

        # Check champion pool diversity
        champion_stats = data.get('champion_performance', {})
        total_games = sum(stats.get('games', 0) for stats in champion_stats.values())

        if total_games >= self.config['min_games_comparison']:
            top_champion_games = max((stats.get('games', 0) for stats in champion_stats.values()), default=0)
            champion_concentration = top_champion_games / total_games if total_games > 0 else 0

            if champion_concentration < 0.30 and len(champion_stats) >= 10:
                # Too many different champions
                self.insights.append(Insight(
                    id="behavior_champion_pool_wide",
                    category=InsightCategory.BEHAVIORAL_PATTERN,
                    severity=InsightSeverity.MEDIUM,
                    title=f"🎲 Wide Champion Pool: {len(champion_stats)} champions",
                    description=f"You've played {len(champion_stats)} different champions with no clear main (top champion: {champion_concentration:.1%} of games). Consider specialization for climbing.",
                    evidence={
                        'total_champions': len(champion_stats),
                        'total_games': total_games,
                        'top_champion_share': champion_concentration
                    },
                    recommendation="Focus on 2-3 main champions for your primary role. Master before expanding pool.",
                    confidence=0.78,
                    priority_score=62.0
                ))
            elif champion_concentration >= 0.70:
                # Heavy one-trick
                top_champion = max(champion_stats.items(), key=lambda x: x[1].get('games', 0))[0]
                self.insights.append(Insight(
                    id="behavior_one_trick",
                    category=InsightCategory.BEHAVIORAL_PATTERN,
                    severity=InsightSeverity.INFO,
                    title=f"🎯 One-Trick: {champion_concentration:.1%} games on {top_champion}",
                    description=f"You're heavily specialized on {top_champion} ({champion_concentration:.1%} of games). Consider learning 1-2 backup picks for bans/counters.",
                    evidence={
                        'top_champion': top_champion,
                        'concentration': champion_concentration,
                        'total_games': total_games
                    },
                    recommendation="Learn 1-2 similar champions as backups for when your main is banned or countered.",
                    confidence=0.85,
                    priority_score=50.0
                ))

    def _detect_surprise_insights(self, data: Dict[str, Any]) -> None:
        """
        Surprise Insight Detection System

        Discovers unexpected but valuable patterns:
        1. Temporal patterns: Weekend vs weekday performance differences
        2. Off-meta champion talents: Low pick rate but high win rate
        3. Counter-intuitive advantages: Low KDA but high win rate (functional playstyle)
        4. Game duration advantages: Early game specialist vs late game master
        5. Off-role strength: Better performance in secondary roles
        6. Special scenario advantages: Comeback ability from behind
        """

        # 1. Temporal pattern detection (Weekend Warrior)
        temporal_stats = data.get('temporal_stats', {})
        if temporal_stats:
            weekend_wr = temporal_stats.get('weekend_winrate', 0)
            weekday_wr = temporal_stats.get('weekday_winrate', 0)
            weekend_games = temporal_stats.get('weekend_games', 0)
            weekday_games = temporal_stats.get('weekday_games', 0)

            # At least 20 games sample and weekend winrate 15%+ higher
            if weekend_games >= 20 and weekday_games >= 20 and weekend_wr > weekday_wr + 0.15:
                self.insights.append(Insight(
                    id="surprise_weekend_warrior",
                    category=InsightCategory.SURPRISE_INSIGHT,
                    severity=InsightSeverity.HIGH,
                    title=f"💎 Weekend Warrior: Rest day performance boost {weekend_wr:.1%} vs {weekday_wr:.1%}",
                    description=f"Surprise finding: Your weekend winrate ({weekend_wr:.1%}) is {(weekend_wr-weekday_wr):.1%} higher than weekdays ({weekday_wr:.1%}). This shows proper rest and mental state are crucial for your performance.",
                    evidence={
                        'weekend_winrate': weekend_wr,
                        'weekday_winrate': weekday_wr,
                        'weekend_games': weekend_games,
                        'weekday_games': weekday_games,
                        'performance_boost': weekend_wr - weekday_wr
                    },
                    recommendation="Prioritize ranked games on weekends, use weekdays for practice and learning. Ensure proper rest before every game.",
                    confidence=0.88,
                    priority_score=85.0
                ))

            # Reverse case: Stronger on weekdays (focused mode)
            elif weekend_games >= 20 and weekday_games >= 20 and weekday_wr > weekend_wr + 0.15:
                self.insights.append(Insight(
                    id="surprise_weekday_focused",
                    category=InsightCategory.SURPRISE_INSIGHT,
                    severity=InsightSeverity.MEDIUM,
                    title=f"💎 Focused Mode: Weekday performance more stable {weekday_wr:.1%} vs {weekend_wr:.1%}",
                    description=f"Interesting finding: Your weekday winrate ({weekday_wr:.1%}) is {(weekday_wr-weekend_wr):.1%} higher than weekends ({weekend_wr:.1%}). Possibly because you're more focused on weekdays, while weekends lead to over-relaxation.",
                    evidence={
                        'weekday_winrate': weekday_wr,
                        'weekend_winrate': weekend_wr,
                        'weekday_games': weekday_games,
                        'weekend_games': weekend_games
                    },
                    recommendation="Add warmup games before weekend ranked sessions to avoid performance drop from over-relaxation.",
                    confidence=0.85,
                    priority_score=75.0
                ))

        # 2. Off-meta champion talent detection (Hidden Main)
        champion_stats = data.get('champion_performance', {})
        global_pick_rates = data.get('global_champion_pick_rates', {})  # Need global data

        for champion_name, stats in champion_stats.items():
            games = stats.get('games', 0)
            winrate = stats.get('winrate', 0)

            # Get champion's global pick_rate (if available)
            global_pick_rate = global_pick_rates.get(champion_name, 0.05)  # Default 5%

            # Off-meta champion (global pick_rate < 3%) but high personal winrate (>55%) with sufficient sample
            if global_pick_rate < 0.03 and winrate > 0.55 and games >= 10:
                self.insights.append(Insight(
                    id=f"surprise_hidden_talent_{champion_name}",
                    category=InsightCategory.SURPRISE_INSIGHT,
                    severity=InsightSeverity.CRITICAL,
                    title=f"💎 Hidden Main: {champion_name} off-meta but strong {winrate:.1%}",
                    description=f"Surprise discovery: {champion_name} has only {global_pick_rate:.1%} global usage (off-meta), but your winrate is {winrate:.1%} ({games} games). This might be your talent champion!",
                    evidence={
                        'champion': champion_name,
                        'personal_winrate': winrate,
                        'games': games,
                        'global_pick_rate': global_pick_rate,
                        'kda': stats.get('kda', 0)
                    },
                    recommendation=f"Significantly increase {champion_name} usage frequency - this is your secret weapon. Opponents are unfamiliar with this champion, your experience advantage will be more evident.",
                    confidence=0.92,
                    priority_score=90.0
                ))

        # 3. Counter-intuitive advantage detection (Functional playstyle: Low KDA, high winrate)
        avg_kda = data.get('avg_kda', 2.0)
        overall_wr = data.get('overall_winrate', 0.5)
        total_games = data.get('total_games', 0)

        if total_games >= 30 and avg_kda < 2.5 and overall_wr > 0.52:
            self.insights.append(Insight(
                id="surprise_functional_playstyle",
                category=InsightCategory.SURPRISE_INSIGHT,
                severity=InsightSeverity.MEDIUM,
                title=f"💎 Functional Playstyle: Low KDA ({avg_kda:.2f}) high winrate ({overall_wr:.1%})",
                description=f"Unexpected pattern: Despite your KDA being only {avg_kda:.2f} (below average), your winrate reaches {overall_wr:.1%}. This shows you excel at sacrificial/functional playstyle, winning games through damage absorption, vision control, etc.",
                evidence={
                    'avg_kda': avg_kda,
                    'overall_winrate': overall_wr,
                    'total_games': total_games,
                    'avg_deaths': data.get('avg_deaths', 0)
                },
                recommendation="Don't over-focus on KDA, continue providing team utility. Tank/control champions may suit your style better.",
                confidence=0.82,
                priority_score=78.0
            ))

        # 4. Game duration advantage detection
        duration_stats = data.get('game_duration_stats', {})
        if duration_stats:
            short_wr = duration_stats.get('short_game_winrate', 0)  # <25 minutes
            long_wr = duration_stats.get('long_game_winrate', 0)    # >35 minutes
            short_games = duration_stats.get('short_games', 0)
            long_games = duration_stats.get('long_games', 0)

            # Early game specialist
            if short_games >= 15 and long_games >= 15 and short_wr > long_wr + 0.20:
                self.insights.append(Insight(
                    id="surprise_early_game_specialist",
                    category=InsightCategory.SURPRISE_INSIGHT,
                    severity=InsightSeverity.HIGH,
                    title=f"💎 Early Game Specialist: Short game winrate ({short_wr:.1%}) dominates long games ({long_wr:.1%})",
                    description=f"Hidden advantage: Your <25min short game winrate ({short_wr:.1%}) is {(short_wr-long_wr):.1%} higher than 35+min long games ({long_wr:.1%}). Your early tempo and snowballing ability far exceeds late game macro.",
                    evidence={
                        'short_game_winrate': short_wr,
                        'long_game_winrate': long_wr,
                        'short_games': short_games,
                        'long_games': long_games
                    },
                    recommendation="Pick early game champions (Irelia, Fiora, Nidalee, etc.), play aggressively, use early advantages to close games quickly. Avoid late game scalers.",
                    confidence=0.87,
                    priority_score=83.0
                ))

            # Late game master
            elif short_games >= 15 and long_games >= 15 and long_wr > short_wr + 0.20:
                self.insights.append(Insight(
                    id="surprise_late_game_specialist",
                    category=InsightCategory.SURPRISE_INSIGHT,
                    severity=InsightSeverity.HIGH,
                    title=f"💎 Late Game Master: Long game winrate ({long_wr:.1%}) far exceeds short games ({short_wr:.1%})",
                    description=f"Potential trait: Your 35+min long game winrate ({long_wr:.1%}) is {(long_wr-short_wr):.1%} higher than <25min short games ({short_wr:.1%}). Your teamfight decisions and late game macro are key to victory.",
                    evidence={
                        'long_game_winrate': long_wr,
                        'short_game_winrate': short_wr,
                        'long_games': long_games,
                        'short_games': short_games
                    },
                    recommendation="Pick late game carry champions (Vayne, Kassadin, Jinx, etc.), farm safely, avoid early fights, wait for late game teamfights to shine.",
                    confidence=0.87,
                    priority_score=83.0
                ))

        # 5. Off-role strength detection
        role_stats = data.get('role_performance', {})
        primary_role = data.get('primary_role', 'mid').lower()

        if len(role_stats) >= 2:
            # Find highest winrate among non-primary roles
            off_role_stats = [(role, stats) for role, stats in role_stats.items()
                             if role.lower() != primary_role and stats.get('games', 0) >= 15]

            if off_role_stats:
                best_off_role, best_stats = max(off_role_stats, key=lambda x: x[1].get('winrate', 0))
                primary_role_wr = role_stats.get(primary_role, {}).get('winrate', 0)
                off_role_wr = best_stats.get('winrate', 0)

                # Off-role winrate 15%+ higher than primary role
                if off_role_wr > primary_role_wr + 0.15 and best_stats.get('games', 0) >= 15:
                    self.insights.append(Insight(
                        id=f"surprise_off_role_strength_{best_off_role}",
                        category=InsightCategory.SURPRISE_INSIGHT,
                        severity=InsightSeverity.HIGH,
                        title=f"💎 Unexpected Strength: {best_off_role} off-role winrate ({off_role_wr:.1%}) exceeds main {primary_role} ({primary_role_wr:.1%})",
                        description=f"Stunning discovery: Your non-primary role {best_off_role} winrate ({off_role_wr:.1%}) is {(off_role_wr-primary_role_wr):.1%} higher than your main role {primary_role} ({primary_role_wr:.1%})! Your talent might lie elsewhere.",
                        evidence={
                            'off_role': best_off_role,
                            'off_role_winrate': off_role_wr,
                            'off_role_games': best_stats.get('games', 0),
                            'primary_role': primary_role,
                            'primary_role_winrate': primary_role_wr
                        },
                        recommendation=f"Seriously consider switching main role to {best_off_role}, or at least increase {best_off_role} game share. Talent matters more than practice.",
                        confidence=0.84,
                        priority_score=82.0
                    ))

        # 6. Comeback ability detection
        comeback_stats = data.get('comeback_stats', {})
        if comeback_stats:
            behind_at_15_wr = comeback_stats.get('behind_at_15_winrate', 0)
            behind_games = comeback_stats.get('behind_at_15_games', 0)
            avg_wr = data.get('overall_winrate', 0.5)

            # Behind at 15min but still have high comeback rate
            if behind_games >= 20 and behind_at_15_wr > 0.35 and behind_at_15_wr > avg_wr * 0.7:
                self.insights.append(Insight(
                    id="surprise_comeback_ability",
                    category=InsightCategory.SURPRISE_INSIGHT,
                    severity=InsightSeverity.MEDIUM,
                    title=f"💎 Comeback Master: Behind-game winrate {behind_at_15_wr:.1%} (15min deficit)",
                    description=f"Rare trait: Even when behind at 15 minutes, you still win {behind_at_15_wr:.1%} of games ({behind_games} games). Your mental resilience and late-game decisions are strengths.",
                    evidence={
                        'behind_at_15_winrate': behind_at_15_wr,
                        'behind_games': behind_games,
                        'overall_winrate': avg_wr
                    },
                    recommendation="Don't surrender easily - your comeback ability is above average. Pick late-game compositions, stay calm and wait for opportunities.",
                    confidence=0.80,
                    priority_score=76.0
                ))

    def generate_summary(self, insights: List[Insight]) -> Dict[str, Any]:
        """
        Generate a summary of detected insights

        Args:
            insights: List of detected insights

        Returns:
            Summary statistics and key findings
        """
        if not insights:
            return {
                'total_insights': 0,
                'by_severity': {},
                'by_category': {},
                'top_priorities': []
            }

        # Count by severity
        by_severity = {}
        for insight in insights:
            severity = insight.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # Count by category
        by_category = {}
        for insight in insights:
            category = insight.category.value
            by_category[category] = by_category.get(category, 0) + 1

        # Get top 5 priorities
        top_priorities = [
            {
                'title': insight.title,
                'severity': insight.severity.value,
                'priority_score': insight.priority_score
            }
            for insight in insights[:5]
        ]

        return {
            'total_insights': len(insights),
            'by_severity': by_severity,
            'by_category': by_category,
            'top_priorities': top_priorities,
            'critical_count': by_severity.get('critical', 0),
            'high_count': by_severity.get('high', 0)
        }


def main():
    """Demo usage of InsightDetector"""

    # Sample aggregated data
    sample_data = {
        'overall_winrate': 0.52,
        'recent_winrate': 0.38,
        'recent_match_results': [
            {'win': False, 'match_id': '1'},
            {'win': False, 'match_id': '2'},
            {'win': False, 'match_id': '3'},
            {'win': False, 'match_id': '4'},
            {'win': False, 'match_id': '5'},
        ],
        'champion_performance': {
            'Riven': {'games': 25, 'winrate': 0.32, 'kda': 2.1, 'avg_cs': 6.5},
            'Aatrox': {'games': 15, 'winrate': 0.60, 'kda': 3.2, 'avg_cs': 7.2},
            'Camille': {'games': 8, 'winrate': 0.50, 'kda': 2.8, 'avg_cs': 6.8},
        },
        'role_performance': {
            'top': {'games': 40, 'winrate': 0.50},
            'mid': {'games': 8, 'winrate': 0.25}
        },
        'avg_cs_per_min': 5.2,
        'avg_kda': 1.8,
        'avg_kills': 4.2,
        'avg_deaths': 6.5,
        'avg_assists': 7.1,
        'primary_role': 'top',
        'match_history': [
            {'win': False}, {'win': False}, {'win': False}, {'win': True},
            {'win': False}, {'win': True}, {'win': True}, {'win': False},
            {'win': True}, {'win': True}, {'win': True}, {'win': True},
        ]
    }

    # Detect insights
    detector = InsightDetector()
    insights = detector.detect_insights(sample_data)

    # Print results
    print(f"\n🔍 Detected {len(insights)} Insights\n")
    print("=" * 80)

    for i, insight in enumerate(insights[:10], 1):  # Show top 10
        print(f"\n{i}. [{insight.severity.value.upper()}] {insight.title}")
        print(f"   Priority: {insight.priority_score:.1f} | Confidence: {insight.confidence:.0%}")
        print(f"   {insight.description}")
        if insight.recommendation:
            print(f"   💡 Recommendation: {insight.recommendation}")

    # Print summary
    summary = detector.generate_summary(insights)
    print(f"\n" + "=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total: {summary['total_insights']} insights")
    print(f"   Critical: {summary['critical_count']} | High: {summary['high_count']}")
    print(f"   By category: {summary['by_category']}")


if __name__ == "__main__":
    main()
