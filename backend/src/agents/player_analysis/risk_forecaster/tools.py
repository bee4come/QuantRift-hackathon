"""
RiskForecasterAgent - Data Processing Tools

Core functions for power curve calculation and risk forecasting.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from src.utils.id_mappings import get_champion_name


def load_power_curves(baselines_path: str = "data/baselines/power_curves.json") -> Dict[str, Any]:
    """
    加载战力曲线基线数据

    Args:
        baselines_path: Path to power_curves.json

    Returns:
        Power curves data with auto-generation if missing
    """
    baseline_file = Path(baselines_path)

    # Auto-generate if missing
    if not baseline_file.exists():
        print(f"⚠️  战力曲线数据不存在，正在自动生成...")

        from src.analytics import PowerCurveGenerator

        gold_parquet = Path("data/gold/parquet/fact_match_performance.parquet")
        if not gold_parquet.exists():
            raise FileNotFoundError(f"❌ Gold layer数据不存在: {gold_parquet}")

        generator = PowerCurveGenerator(parquet_path=str(gold_parquet), min_games_per_segment=15)
        generator.save(output_path=baselines_path)
        print(f"✅ 战力曲线数据已生成: {baselines_path}")

    with open(baseline_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_team_power_curve(
    composition: List[Dict[str, Any]],
    power_curves_data: Dict[str, Any]
) -> Dict[int, float]:
    """
    计算团队在不同时间点的整体战力

    Args:
        composition: Team composition [{"champion_id": 92, "role": "TOP"}, ...]
        power_curves_data: Power curves baseline data

    Returns:
        {0: 45.2, 5: 48.7, 10: 55.3, ...} - Power at each time point
    """
    champions_data = power_curves_data["champions"]

    # Time points to calculate (every 5 minutes)
    time_points = [0, 5, 10, 15, 20, 25, 30, 35, 40]
    team_curve = {}

    for time_point in time_points:
        total_power = 0
        valid_champions = 0

        for member in composition:
            champ_id = str(member["champion_id"])
            role = member["role"]

            # Get champion data
            if champ_id not in champions_data:
                print(f"⚠️  Champion {champ_id} not found, using default power 50")
                total_power += 50
                valid_champions += 1
                continue

            champ_data = champions_data[champ_id]

            # Get role data
            if role not in champ_data["roles"]:
                # Try to use any available role
                available_roles = list(champ_data["roles"].keys())
                if available_roles:
                    role = available_roles[0]
                    print(f"⚠️  Role {member['role']} not found for champion {champ_id}, using {role}")
                else:
                    print(f"⚠️  No role data for champion {champ_id}, using default power 50")
                    total_power += 50
                    valid_champions += 1
                    continue

            role_data = champ_data["roles"][role]
            power_curve = role_data["power_curve"]

            # Get power at this time point
            time_str = str(time_point)
            if time_str in power_curve:
                power = power_curve[time_str]
            else:
                # Interpolate if exact time not found
                power = interpolate_power(power_curve, time_point)

            total_power += power
            valid_champions += 1

        # Average power
        team_curve[time_point] = round(total_power / valid_champions, 1) if valid_champions > 0 else 50.0

    return team_curve


def interpolate_power(power_curve: Dict[str, float], target_time: int) -> float:
    """
    线性插值获取特定时间点的战力

    Args:
        power_curve: Power curve data
        target_time: Target time in minutes

    Returns:
        Interpolated power value
    """
    # Convert keys to int and sort
    times = sorted([int(t) for t in power_curve.keys()])

    if target_time <= times[0]:
        return power_curve[str(times[0])]
    if target_time >= times[-1]:
        return power_curve[str(times[-1])]

    # Find surrounding points
    for i in range(len(times) - 1):
        t1, t2 = times[i], times[i + 1]
        if t1 <= target_time <= t2:
            p1 = power_curve[str(t1)]
            p2 = power_curve[str(t2)]
            ratio = (target_time - t1) / (t2 - t1)
            return p1 + (p2 - p1) * ratio

    return 50.0  # Fallback


def identify_key_moments(
    our_curve: Dict[int, float],
    enemy_curve: Dict[int, float]
) -> List[Dict[str, Any]]:
    """
    识别关键时间节点（战力反转点、强势期等）

    Args:
        our_curve: Our team power curve
        enemy_curve: Enemy team power curve

    Returns:
        List of key moments with type and message
    """
    key_moments = []
    time_points = sorted(our_curve.keys())

    # Find power crossover points
    for i in range(len(time_points) - 1):
        t_now = time_points[i]
        t_next = time_points[i + 1]

        our_now, our_next = our_curve[t_now], our_curve[t_next]
        enemy_now, enemy_next = enemy_curve[t_now], enemy_curve[t_next]

        # Check for power spike (we overtake enemy)
        if our_now <= enemy_now and our_next > enemy_next:
            key_moments.append({
                'time': t_next,
                'type': 'power_spike',
                'our_power': our_next,
                'enemy_power': enemy_next,
                'advantage': round(our_next - enemy_next, 1),
                'message': f'{t_next}分钟我方战力反超（+{round(our_next - enemy_next, 1)}）'
            })

        # Check for power loss (enemy overtakes us)
        if our_now > enemy_now and our_next <= enemy_next:
            key_moments.append({
                'time': t_next,
                'type': 'power_loss',
                'our_power': our_next,
                'enemy_power': enemy_next,
                'disadvantage': round(enemy_next - our_next, 1),
                'message': f'{t_next}分钟敌方战力反超（-{round(enemy_next - our_next, 1)}）'
            })

    # Identify advantage windows (3+ consecutive time points where we lead)
    for i in range(len(time_points) - 2):
        t1, t2, t3 = time_points[i], time_points[i + 1], time_points[i + 2]

        if (our_curve[t1] > enemy_curve[t1] and
            our_curve[t2] > enemy_curve[t2] and
            our_curve[t3] > enemy_curve[t3]):

            avg_advantage = (
                (our_curve[t1] - enemy_curve[t1]) +
                (our_curve[t2] - enemy_curve[t2]) +
                (our_curve[t3] - enemy_curve[t3])
            ) / 3

            # Only add if not already reported
            if not any(m['type'] == 'advantage_window' and m['time'] == t1 for m in key_moments):
                key_moments.append({
                    'time': t1,
                    'type': 'advantage_window',
                    'duration': f'{t1}-{t3}分钟',
                    'avg_advantage': round(avg_advantage, 1),
                    'message': f'{t1}-{t3}分钟是我方强势期（平均+{round(avg_advantage, 1)}战力）'
                })

    return key_moments


def generate_tactical_recommendations(
    our_curve: Dict[int, float],
    enemy_curve: Dict[int, float],
    key_moments: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    基于战力曲线生成战术建议

    Args:
        our_curve: Our team power curve
        enemy_curve: Enemy team power curve
        key_moments: Key moments identified

    Returns:
        Recommendations by game phase
    """
    recommendations = {}

    # Early game (0-15min)
    early_our = sum([our_curve[t] for t in [0, 5, 10, 15]]) / 4
    early_enemy = sum([enemy_curve[t] for t in [0, 5, 10, 15]]) / 4
    early_diff = early_our - early_enemy

    if early_diff > 5:
        recommendations['early_game'] = f"✅ 前期优势（+{round(early_diff, 1)}）：主动找机会，压制对方发育"
    elif early_diff < -5:
        recommendations['early_game'] = f"⚠️ 前期劣势（{round(early_diff, 1)}）：稳健发育，避免过度激进，等待强势期"
    else:
        recommendations['early_game'] = "⚖️ 前期势均力敌：正常对线，寻找局部优势"

    # Mid game (15-25min)
    mid_our = sum([our_curve[t] for t in [15, 20, 25]]) / 3
    mid_enemy = sum([enemy_curve[t] for t in [15, 20, 25]]) / 3
    mid_diff = mid_our - mid_enemy

    if mid_diff > 5:
        recommendations['mid_game'] = f"🔥 中期强势期（+{round(mid_diff, 1)}）：主动控龙、逼团、入侵野区"
    elif mid_diff < -5:
        recommendations['mid_game'] = f"⚠️ 中期劣势（{round(mid_diff, 1)}）：避战发育，保护视野，等待后期"
    else:
        recommendations['mid_game'] = "⚖️ 中期相对均衡：运营拉扯，抓对方失误"

    # Late game (25min+)
    late_our = sum([our_curve[t] for t in [25, 30, 35, 40]]) / 4
    late_enemy = sum([enemy_curve[t] for t in [25, 30, 35, 40]]) / 4
    late_diff = late_our - late_enemy

    if late_diff > 5:
        recommendations['late_game'] = f"✅ 后期优势（+{round(late_diff, 1)}）：拖到后期，大龙团战有优势"
    elif late_diff < -5:
        recommendations['late_game'] = f"❌ 后期劣势（{round(late_diff, 1)}）：务必在25分钟前建立优势，避免拖后期"
    else:
        recommendations['late_game'] = "⚖️ 后期双方都有机会：运营决定胜负"

    # Overall strategy
    if early_diff > 0 and mid_diff > 0 and late_diff < 0:
        recommendations['overall'] = "⚡ 雪球型阵容：前中期必须建立优势，不能拖后期"
    elif early_diff < 0 and late_diff > 0:
        recommendations['overall'] = "🐢 后期阵容：前期稳住，后期接管比赛"
    elif mid_diff > 5:
        recommendations['overall'] = "⏰ 中期爆发阵容：15-25分钟是关键窗口期"
    else:
        recommendations['overall'] = "⚖️ 均衡阵容：发挥个人实力，抓对方失误"

    return recommendations


def format_analysis_for_prompt(analysis: Dict[str, Any]) -> str:
    """
    格式化分析数据为LLM友好的文本

    Args:
        analysis: Complete analysis data

    Returns:
        Formatted text for LLM prompt
    """
    lines = []

    lines.append("# 对局风险预警分析数据\n")

    # Display team compositions with champion names
    lines.append("## 阵容信息\n")

    lines.append("**我方阵容**:")
    for member in analysis.get('our_composition', []):
        champ_id = member['champion_id']
        role = member['role']
        champ_name = get_champion_name(champ_id)
        lines.append(f"- {role}: {champ_name} (ID: {champ_id})")

    lines.append("\n**敌方阵容**:")
    for member in analysis.get('enemy_composition', []):
        champ_id = member['champion_id']
        role = member['role']
        champ_name = get_champion_name(champ_id)
        lines.append(f"- {role}: {champ_name} (ID: {champ_id})")

    lines.append("")

    # Power curves comparison
    lines.append("## 战力曲线对比\n")
    lines.append("| 时间 | 我方战力 | 敌方战力 | 差值 | 优势方 |")
    lines.append("|------|---------|---------|------|--------|")

    for time_point in sorted(analysis['power_curves']['our_team'].keys()):
        our_power = analysis['power_curves']['our_team'][time_point]
        enemy_power = analysis['power_curves']['enemy_team'][time_point]
        diff = our_power - enemy_power
        advantage = "我方" if diff > 0 else ("敌方" if diff < 0 else "均衡")

        lines.append(f"| {time_point}分 | {our_power} | {enemy_power} | {diff:+.1f} | {advantage} |")

    lines.append("")

    # Key moments
    if analysis['key_moments']:
        lines.append("## 关键时间节点\n")
        for moment in analysis['key_moments']:
            lines.append(f"- **{moment['message']}**")
        lines.append("")

    # Recommendations
    lines.append("## 战术建议\n")
    for phase, recommendation in analysis['recommendations'].items():
        phase_name = {
            'early_game': '前期 (0-15分钟)',
            'mid_game': '中期 (15-25分钟)',
            'late_game': '后期 (25分钟+)',
            'overall': '整体策略'
        }.get(phase, phase)
        lines.append(f"**{phase_name}**: {recommendation}\n")

    return "\n".join(lines)


def analyze_composition_matchup(
    our_composition: List[Dict[str, Any]],
    enemy_composition: List[Dict[str, Any]],
    power_curves_path: str = "data/baselines/power_curves.json"
) -> Dict[str, Any]:
    """
    完整的阵容对局分析

    Args:
        our_composition: Our team composition
        enemy_composition: Enemy team composition
        power_curves_path: Path to power curves data

    Returns:
        Complete analysis with curves, moments, and recommendations
    """
    # Load power curves
    power_curves_data = load_power_curves(power_curves_path)

    # Calculate team power curves
    our_curve = calculate_team_power_curve(our_composition, power_curves_data)
    enemy_curve = calculate_team_power_curve(enemy_composition, power_curves_data)

    # Identify key moments
    key_moments = identify_key_moments(our_curve, enemy_curve)

    # Generate recommendations
    recommendations = generate_tactical_recommendations(our_curve, enemy_curve, key_moments)

    return {
        'our_composition': our_composition,
        'enemy_composition': enemy_composition,
        'power_curves': {
            'our_team': our_curve,
            'enemy_team': enemy_curve
        },
        'key_moments': key_moments,
        'recommendations': recommendations
    }
