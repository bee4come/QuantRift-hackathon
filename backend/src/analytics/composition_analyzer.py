"""
CompositionAnalyzer - Team Composition Analysis

Analyzes team compositions for balance, synergy, and strategic characteristics.
"""

from typing import Dict, Any, List
from collections import defaultdict


class CompositionAnalyzer:
    """
    阵容分析器

    分析团队阵容的角色覆盖、缩放模式、平衡性等特征。

    Example:
        >>> analyzer = CompositionAnalyzer(power_curves_data, counter_matrix_data)
        >>> composition = [
        ...     {"champion_id": 92, "role": "TOP"},
        ...     {"champion_id": 64, "role": "JUNGLE"},
        ...     ...
        ... ]
        >>> analysis = analyzer.analyze_composition(composition)
    """

    def __init__(
        self,
        power_curves_data: Dict[str, Any],
        counter_matrix_data: Dict[str, Any] = None
    ):
        """
        Args:
            power_curves_data: Power curves from PowerCurveGenerator
            counter_matrix_data: Counter matrix from CounterMatrixCalculator (optional)
        """
        self.power_curves = power_curves_data["champions"]
        self.counter_matrix = counter_matrix_data["champions"] if counter_matrix_data else {}

    def analyze_composition(
        self,
        composition: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析团队阵容

        Args:
            composition: Team composition
                [{"champion_id": 92, "role": "TOP"}, ...]

        Returns:
            {
                "role_coverage": {...},
                "scaling_pattern": {...},
                "balance_score": 0.85,
                "strengths": [...],
                "weaknesses": [...]
            }
        """
        # 1. Role coverage analysis
        role_coverage = self._analyze_role_coverage(composition)

        # 2. Scaling pattern analysis
        scaling_pattern = self._analyze_scaling_pattern(composition)

        # 3. Power distribution
        power_distribution = self._analyze_power_distribution(composition)

        # 4. Overall balance score
        balance_score = self._calculate_balance_score(
            role_coverage, scaling_pattern, power_distribution
        )

        # 5. Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(
            scaling_pattern, power_distribution, role_coverage
        )

        return {
            "role_coverage": role_coverage,
            "scaling_pattern": scaling_pattern,
            "power_distribution": power_distribution,
            "balance_score": round(balance_score, 2),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "composition": composition
        }

    def analyze_matchup(
        self,
        our_composition: List[Dict[str, Any]],
        enemy_composition: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析阵容对抗

        Args:
            our_composition: Our team composition
            enemy_composition: Enemy team composition

        Returns:
            {
                "our_analysis": {...},
                "enemy_analysis": {...},
                "lane_matchups": [...],
                "overall_advantage": 0.15
            }
        """
        our_analysis = self.analyze_composition(our_composition)
        enemy_analysis = self.analyze_composition(enemy_composition)

        # Analyze lane-by-lane matchups using counter matrix
        lane_matchups = self._analyze_lane_matchups(
            our_composition, enemy_composition
        )

        # Calculate overall team advantage
        overall_advantage = self._calculate_overall_advantage(
            lane_matchups, our_analysis, enemy_analysis
        )

        return {
            "our_analysis": our_analysis,
            "enemy_analysis": enemy_analysis,
            "lane_matchups": lane_matchups,
            "overall_advantage": round(overall_advantage, 2)
        }

    def _analyze_role_coverage(self, composition: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析角色覆盖度"""
        roles = [member["role"] for member in composition]
        expected_roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

        covered_roles = set(roles)
        missing_roles = set(expected_roles) - covered_roles
        duplicate_roles = [role for role in roles if roles.count(role) > 1]

        return {
            "covered": list(covered_roles),
            "missing": list(missing_roles),
            "duplicates": list(set(duplicate_roles)),
            "is_complete": len(missing_roles) == 0 and len(duplicate_roles) == 0
        }

    def _analyze_scaling_pattern(self, composition: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析缩放模式（前期/中期/后期强势）"""
        scaling_scores = {"early": 0, "mid": 0, "late": 0}
        champion_scalings = []

        for member in composition:
            champ_id = str(member["champion_id"])
            role = member["role"]

            if champ_id not in self.power_curves:
                continue

            champ_data = self.power_curves[champ_id]
            if role not in champ_data["roles"]:
                # Use first available role if exact role not found
                available_roles = list(champ_data["roles"].keys())
                if not available_roles:
                    continue
                role = available_roles[0]

            role_data = champ_data["roles"][role]

            # Classify based on power curve peaks
            early_power = role_data.get("early_power", 50)
            mid_power = role_data.get("mid_power", 50)
            late_power = role_data.get("late_power", 50)

            # Determine champion's strongest phase
            powers = {"early": early_power, "mid": mid_power, "late": late_power}
            strongest_phase = max(powers, key=powers.get)

            scaling_scores[strongest_phase] += 1
            champion_scalings.append({
                "champion_id": champ_id,
                "champion_name": champ_data["name"],
                "role": member["role"],
                "strongest_phase": strongest_phase,
                "powers": powers
            })

        # Determine team's overall scaling pattern
        if scaling_scores["late"] >= 3:
            pattern = "late_game"
            description = "后期阵容 - 需要拖到后期才能发挥实力"
        elif scaling_scores["early"] >= 3:
            pattern = "early_game"
            description = "前期阵容 - 需要在前期建立优势"
        elif scaling_scores["mid"] >= 3:
            pattern = "mid_game"
            description = "中期阵容 - 15-25分钟是强势期"
        else:
            pattern = "balanced"
            description = "均衡阵容 - 各阶段都有战力"

        return {
            "pattern": pattern,
            "description": description,
            "phase_distribution": scaling_scores,
            "champions": champion_scalings
        }

    def _analyze_power_distribution(self, composition: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析战力分布"""
        time_points = [0, 10, 20, 30, 40]
        power_by_time = defaultdict(list)

        for member in composition:
            champ_id = str(member["champion_id"])
            role = member["role"]

            if champ_id not in self.power_curves:
                continue

            champ_data = self.power_curves[champ_id]
            if role not in champ_data["roles"]:
                available_roles = list(champ_data["roles"].keys())
                if not available_roles:
                    continue
                role = available_roles[0]

            power_curve = champ_data["roles"][role]["power_curve"]

            for time in time_points:
                time_str = str(time)
                if time_str in power_curve:
                    power_by_time[time].append(power_curve[time_str])

        # Calculate average power at each time point
        avg_power = {}
        for time in time_points:
            if power_by_time[time]:
                avg_power[time] = round(sum(power_by_time[time]) / len(power_by_time[time]), 1)
            else:
                avg_power[time] = 50.0  # Default

        # Find peak time
        peak_time = max(avg_power, key=avg_power.get)

        return {
            "power_curve": avg_power,
            "peak_time": peak_time,
            "peak_power": avg_power[peak_time],
            "early_power": avg_power.get(10, 50),
            "mid_power": avg_power.get(20, 50),
            "late_power": avg_power.get(30, 50)
        }

    def _analyze_lane_matchups(
        self,
        our_composition: List[Dict[str, Any]],
        enemy_composition: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """分析分路对抗（使用克制关系矩阵）"""
        matchups = []

        # Match by role
        our_by_role = {m["role"]: m for m in our_composition}
        enemy_by_role = {m["role"]: m for m in enemy_composition}

        for role in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            if role not in our_by_role or role not in enemy_by_role:
                continue

            our_champ_id = str(our_by_role[role]["champion_id"])
            enemy_champ_id = str(enemy_by_role[role]["champion_id"])

            # Get winrate from counter matrix if available
            advantage = self._get_matchup_advantage(
                our_champ_id, enemy_champ_id, role
            )

            matchups.append({
                "role": role,
                "our_champion": our_champ_id,
                "enemy_champion": enemy_champ_id,
                "advantage": advantage,
                "assessment": self._assess_matchup(advantage)
            })

        return matchups

    def _get_matchup_advantage(
        self,
        our_champ_id: str,
        enemy_champ_id: str,
        role: str
    ) -> float:
        """获取对抗优势（从克制关系矩阵）"""
        if not self.counter_matrix:
            return 0.0  # No counter matrix available

        if our_champ_id not in self.counter_matrix:
            return 0.0

        our_champ_data = self.counter_matrix[our_champ_id]
        if role not in our_champ_data["roles"]:
            return 0.0

        matchup_stats = our_champ_data["roles"][role].get("matchup_stats", {})
        if enemy_champ_id not in matchup_stats:
            return 0.0

        # Convert winrate to advantage (-0.5 to +0.5)
        winrate = matchup_stats[enemy_champ_id]["winrate"]
        advantage = winrate - 0.5

        return round(advantage, 3)

    def _assess_matchup(self, advantage: float) -> str:
        """评估对抗优势等级"""
        if advantage >= 0.1:
            return "strong_advantage"
        elif advantage >= 0.05:
            return "slight_advantage"
        elif advantage <= -0.1:
            return "strong_disadvantage"
        elif advantage <= -0.05:
            return "slight_disadvantage"
        else:
            return "even"

    def _calculate_balance_score(
        self,
        role_coverage: Dict[str, Any],
        scaling_pattern: Dict[str, Any],
        power_distribution: Dict[str, Any]
    ) -> float:
        """计算阵容平衡分数 (0-1)"""
        score = 1.0

        # Role coverage penalty
        if not role_coverage["is_complete"]:
            score -= 0.3

        # Scaling pattern penalty (extreme patterns are risky)
        phase_dist = scaling_pattern["phase_distribution"]
        if max(phase_dist.values()) == 5:  # All 5 champions same phase
            score -= 0.2
        elif max(phase_dist.values()) == 4:  # 4 champions same phase
            score -= 0.1

        # Power curve consistency (less variance = more predictable)
        power_curve = power_distribution["power_curve"]
        power_values = list(power_curve.values())
        if len(power_values) > 1:
            power_variance = sum((p - sum(power_values)/len(power_values))**2 for p in power_values) / len(power_values)
            if power_variance > 100:  # High variance
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _identify_strengths_weaknesses(
        self,
        scaling_pattern: Dict[str, Any],
        power_distribution: Dict[str, Any],
        role_coverage: Dict[str, Any]
    ) -> tuple:
        """识别阵容优势和劣势"""
        strengths = []
        weaknesses = []

        # Role coverage
        if role_coverage["is_complete"]:
            strengths.append("完整的角色覆盖")
        else:
            if role_coverage["missing"]:
                weaknesses.append(f"缺少角色: {', '.join(role_coverage['missing'])}")
            if role_coverage["duplicates"]:
                weaknesses.append(f"重复角色: {', '.join(role_coverage['duplicates'])}")

        # Scaling pattern
        pattern = scaling_pattern["pattern"]
        if pattern == "late_game":
            strengths.append("后期战力强大")
            weaknesses.append("前期容易被压制")
        elif pattern == "early_game":
            strengths.append("前期节奏主导能力强")
            weaknesses.append("后期战力下降")
        elif pattern == "mid_game":
            strengths.append("中期团战能力突出")
        else:
            strengths.append("各阶段战力均衡")

        # Power distribution
        peak_time = power_distribution["peak_time"]
        if peak_time <= 10:
            strengths.append("前期爆发力强")
        elif peak_time >= 30:
            strengths.append("后期成长性好")

        return strengths, weaknesses

    def _calculate_overall_advantage(
        self,
        lane_matchups: List[Dict[str, Any]],
        our_analysis: Dict[str, Any],
        enemy_analysis: Dict[str, Any]
    ) -> float:
        """计算整体阵容优势"""
        # Lane matchup advantages
        if lane_matchups:
            lane_advantage = sum(m["advantage"] for m in lane_matchups) / len(lane_matchups)
        else:
            lane_advantage = 0.0

        # Balance score difference
        balance_diff = our_analysis["balance_score"] - enemy_analysis["balance_score"]

        # Combined advantage
        overall = lane_advantage + (balance_diff * 0.2)

        return overall
