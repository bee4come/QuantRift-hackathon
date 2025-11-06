"""
Postgame Review Engine
赛后复盘规则引擎 - 量化诊断核心逻辑
"""

from typing import Dict, List, Any


class PostgameReviewEngine:
    """赛后复盘卡规则引擎"""

    def __init__(self, config: Dict[str, Any] = None):
        """初始化引擎"""
        self.config = config or {
            # 对线期阈值
            'cs10_percentile_threshold': 30,
            'golddiff10_threshold': -600,
            'first_back_min_gold': 1300,
            'first_back_max_time': 390,  # 6:30

            # 目标控制
            'objective_ward_window': 60,  # 目标前60秒

            # 出装节奏
            'core2_median_time': 18 * 60,  # 18分钟（秒）
            'core2_delay_threshold': 130,  # +2:10

            # 团战参与
            'teamfight_join_percentile': 30,
            'assist_share_threshold': 0.20
        }

    def generate_postgame_review(
        self,
        match_features: Dict[str, Any],
        timeline_features: Dict[str, Any],
        role_baseline: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成赛后复盘卡"""
        print("\n" + "="*60)
        print("🔍 赛后复盘卡 量化诊断")
        print("="*60)

        match_id = match_features['match_id']
        print(f"   Match ID: {match_id}")
        print(f"   英雄: {match_features['champion_name']} ({match_features['role']})")
        print(f"   结果: {'胜利' if match_features['win'] else '失败'}")

        # 规则库诊断
        lane_issues = self._diagnose_lane_phase(match_features, timeline_features, role_baseline)
        objective_issues = self._diagnose_objective_phase(match_features, timeline_features)
        build_issues = self._diagnose_build_timing(match_features, timeline_features)
        teamfight_issues = self._diagnose_teamfight(match_features, timeline_features)

        # 构建输出
        postgame_review = {
            'match_id': match_id,
            'champion': match_features['champion_name'],
            'role': match_features['role'],
            'result': 'WIN' if match_features['win'] else 'LOSS',
            'game_duration': match_features['game_duration'],
            'lane_phase': lane_issues,
            'objective_phase': objective_issues,
            'build_timing': build_issues,
            'teamfight': teamfight_issues,
            'overall_score': self._calculate_overall_score(
                lane_issues, objective_issues, build_issues, teamfight_issues
            )
        }

        print(f"✅ 赛后复盘卡生成完成")
        return postgame_review

    def _diagnose_lane_phase(
        self,
        match_features: Dict[str, Any],
        timeline_features: Dict[str, Any],
        role_baseline: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """诊断对线期（0-14min）"""
        print("\n🎯 诊断对线期")

        issues = []
        cs_at = timeline_features.get('cs_at', {})
        cs10 = cs_at.get('cs_10', 0)
        gold_curve = timeline_features.get('gold_curve', [])

        # 规则1: CS@10低于角色分位30
        if cs10 < 60:  # 简化阈值
            issues.append({
                'type': 'lane_pressure',
                'evidence': f"CS@10={cs10} < 角色p30",
                'action': "3:30~5:00 控线，提升补刀效率"
            })

        # 规则2: 金币差@10过大
        gold10 = next((g['gold'] for g in gold_curve if 9 <= g['min'] <= 11), 0)
        if gold10 < 3000:  # 简化阈值
            issues.append({
                'type': 'gold_deficit',
                'evidence': f"Gold@10={gold10}",
                'action': "提升对线压制或避免不利交换"
            })

        # 规则3: 回家效率低
        item_purchases = timeline_features.get('item_purchases', [])
        if item_purchases:
            first_major_item_time = next(
                (item.get('time') for item in item_purchases if item.get('item_id', 0) > 1000 and item.get('time') is not None),
                None
            )
            if first_major_item_time and first_major_item_time > 6.5:
                issues.append({
                    'type': 'back_timing',
                    'evidence': f"首件装备{first_major_item_time:.1f}分钟",
                    'action': "优化回家节奏，避免金币沉睡"
                })

        print(f"  发现 {len(issues)} 个对线问题")
        return {
            'cs10': cs10,
            'gold10': gold10,
            'issues': issues
        }

    def _diagnose_objective_phase(
        self,
        match_features: Dict[str, Any],
        timeline_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """诊断目标控制"""
        print("\n🐉 诊断目标控制")

        issues = []

        # 规则1: 小龙/先锋前视野布置
        ward_events = timeline_features.get('ward_events', [])
        wards_placed = len([w for w in ward_events if w['type'] == 'placed'])

        if wards_placed < 3:  # 简化阈值
            issues.append({
                'type': 'vision_control',
                'evidence': f"全场仅放{wards_placed}个眼",
                'action': "提升视野布置，尤其目标前60秒"
            })

        # 规则2: 目标参与率
        obj_participation = match_features.get('obj_participation', 0)
        if obj_participation == 0:
            issues.append({
                'type': 'objective_participation',
                'evidence': "未参与任何目标击杀",
                'action': "关注小龙/先锋刷新时间，及时支援"
            })

        print(f"  发现 {len(issues)} 个目标控制问题")
        return {
            'wards_placed': wards_placed,
            'obj_participation': obj_participation,
            'issues': issues
        }

    def _diagnose_build_timing(
        self,
        match_features: Dict[str, Any],
        timeline_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """诊断出装节奏"""
        print("\n🔨 诊断出装节奏")

        issues = []

        # 规则1: 核心二件成型时间
        time_to_core2 = timeline_features.get('time_to_core2', None)
        median_time = self.config['core2_median_time'] / 60  # 转分钟

        if time_to_core2 and time_to_core2 > median_time + 2:
            delta_vs_median = time_to_core2 - median_time
            issues.append({
                'type': 'slow_itemization',
                'evidence': f"Core2@{time_to_core2:.1f}min, 慢于中位+{delta_vs_median:.1f}min",
                'action': "提升打钱效率或优化回家时机"
            })

        # 规则2: 出装序列异常
        items = match_features.get('items', [])
        if len(items) < 3 and match_features['game_duration'] > 1200:  # 20分钟+
            issues.append({
                'type': 'incomplete_build',
                'evidence': f"20分钟后仅{len(items)}件装备",
                'action': "检查对线/打野效率，确保经济来源"
            })

        print(f"  发现 {len(issues)} 个出装问题")
        return {
            'core2_time': time_to_core2 if time_to_core2 else None,
            'items_count': len(items),
            'issues': issues
        }

    def _diagnose_teamfight(
        self,
        match_features: Dict[str, Any],
        timeline_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """诊断团战/参团"""
        print("\n⚔️  诊断团战表现")

        issues = []

        # 规则1: 参团率
        assists = match_features.get('assists', 0)
        kills = match_features.get('kills', 0)
        total_participation = kills + assists

        if total_participation < 5 and match_features['game_duration'] > 1200:
            issues.append({
                'type': 'low_participation',
                'evidence': f"KP={total_participation}，参团不足",
                'action': "中期多跟团，避免过度单带"
            })

        # 规则2: 死亡次数
        deaths = match_features.get('deaths', 0)
        if deaths > 7:
            issues.append({
                'type': 'excessive_deaths',
                'evidence': f"{deaths}次死亡",
                'action': "改善视野与站位，减少被抓"
            })

        print(f"  发现 {len(issues)} 个团战问题")
        return {
            'kda': match_features.get('kda_adj', 0),
            'kills': kills,
            'deaths': deaths,
            'assists': assists,
            'issues': issues
        }

    def _calculate_overall_score(
        self,
        lane: Dict,
        objective: Dict,
        build: Dict,
        teamfight: Dict
    ) -> Dict[str, Any]:
        """计算总体评分"""
        total_issues = (
            len(lane['issues']) +
            len(objective['issues']) +
            len(build['issues']) +
            len(teamfight['issues'])
        )

        # 简单评分：问题越少分数越高
        score = max(0, 100 - total_issues * 15)

        grade = 'A' if score >= 85 else 'B' if score >= 70 else 'C' if score >= 55 else 'D'

        return {
            'score': score,
            'grade': grade,
            'total_issues': total_issues
        }
