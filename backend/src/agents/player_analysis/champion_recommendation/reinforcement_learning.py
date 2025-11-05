"""
Champion Recommendation Reinforcement Learning Module

使用Thompson Sampling (Contextual Bandit)进行英雄推荐的强化学习

核心思想：
- 每个英雄有一个Beta分布(alpha, beta)表示推荐质量的不确定性
- 推荐时从Beta分布采样，平衡探索(exploration)和利用(exploitation)
- 收集反馈后更新Beta分布参数

适用场景：
- 玩家接受推荐并游玩：根据胜负更新
- 玩家拒绝推荐：轻微负反馈
- 玩家自然游玩推荐英雄：强正反馈
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ChampionBanditState:
    """单个英雄的Bandit状态"""
    champion_id: int
    champion_name: str
    alpha: float  # Beta分布参数：成功次数 + 1
    beta: float   # Beta分布参数：失败次数 + 1
    total_recommendations: int  # 总推荐次数
    total_accepted: int  # 被接受次数
    total_wins: int  # 推荐后胜利次数
    total_losses: int  # 推荐后失败次数
    last_updated: str  # 最后更新时间

    @property
    def expected_value(self) -> float:
        """期望值（均值）"""
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty(self) -> float:
        """不确定性（标准差）"""
        n = self.alpha + self.beta
        return np.sqrt(self.alpha * self.beta / (n * n * (n + 1)))

    @property
    def acceptance_rate(self) -> float:
        """接受率"""
        if self.total_recommendations == 0:
            return 0.0
        return self.total_accepted / self.total_recommendations

    @property
    def win_rate(self) -> float:
        """推荐后胜率"""
        total_games = self.total_wins + self.total_losses
        if total_games == 0:
            return 0.5  # 默认50%
        return self.total_wins / total_games


class ThompsonSamplingRecommender:
    """Thompson Sampling 推荐系统"""

    def __init__(
        self,
        state_file: Optional[str] = None,
        alpha_prior: float = 1.0,
        beta_prior: float = 1.0,
        exploration_bonus: float = 0.1
    ):
        """
        初始化Thompson Sampling推荐器

        Args:
            state_file: 状态文件路径（用于持久化）
            alpha_prior: Alpha先验值（成功先验）
            beta_prior: Beta先验值（失败先验）
            exploration_bonus: 探索奖励系数（鼓励尝试不确定的选项）
        """
        self.state_file = Path(state_file) if state_file else None
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior
        self.exploration_bonus = exploration_bonus

        # 英雄Bandit状态
        self.champion_states: Dict[int, ChampionBanditState] = {}

        # 加载已有状态
        if self.state_file and self.state_file.exists():
            self.load_state()

    def get_or_create_state(self, champion_id: int, champion_name: str) -> ChampionBanditState:
        """获取或创建英雄状态"""
        if champion_id not in self.champion_states:
            self.champion_states[champion_id] = ChampionBanditState(
                champion_id=champion_id,
                champion_name=champion_name,
                alpha=self.alpha_prior,
                beta=self.beta_prior,
                total_recommendations=0,
                total_accepted=0,
                total_wins=0,
                total_losses=0,
                last_updated=datetime.now().isoformat()
            )
        return self.champion_states[champion_id]

    def thompson_sample(self, champion_id: int, champion_name: str) -> float:
        """
        从Beta分布采样

        Returns:
            采样值（0-1之间，代表该英雄的预期推荐质量）
        """
        state = self.get_or_create_state(champion_id, champion_name)
        sample = np.random.beta(state.alpha, state.beta)

        # 添加探索奖励（不确定性越高，奖励越大）
        uncertainty_bonus = state.uncertainty * self.exploration_bonus

        return sample + uncertainty_bonus

    def rank_recommendations(
        self,
        candidates: List[Dict[str, Any]],
        base_scores: Optional[Dict[int, float]] = None,
        bandit_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        使用Thompson Sampling对推荐候选进行排序

        Args:
            candidates: 候选英雄列表（来自静态推荐系统）
            base_scores: 基础评分字典 {champion_id: score}
            bandit_weight: Bandit评分权重（0-1），剩余权重给base_scores

        Returns:
            重新排序后的推荐列表
        """
        if not candidates:
            return []

        # 为每个候选计算综合评分
        scored_candidates = []
        for cand in candidates:
            champ_id = cand["champion_id"]
            champ_name = cand.get("champion_name", f"Champion_{champ_id}")

            # Thompson Sampling采样值
            ts_score = self.thompson_sample(champ_id, champ_name)

            # 基础评分（如果提供）
            base_score = base_scores.get(champ_id, 0.5) if base_scores else 0.5

            # 综合评分
            final_score = bandit_weight * ts_score + (1 - bandit_weight) * base_score

            # 添加到候选
            scored_candidates.append({
                **cand,
                "ts_sample": round(ts_score, 4),
                "base_score": round(base_score, 4),
                "rl_final_score": round(final_score, 4),
                "bandit_state": {
                    "alpha": self.champion_states[champ_id].alpha if champ_id in self.champion_states else self.alpha_prior,
                    "beta": self.champion_states[champ_id].beta if champ_id in self.champion_states else self.beta_prior,
                    "expected_value": self.champion_states[champ_id].expected_value if champ_id in self.champion_states else 0.5,
                    "uncertainty": self.champion_states[champ_id].uncertainty if champ_id in self.champion_states else 0.5
                }
            })

        # 按rl_final_score降序排序
        scored_candidates.sort(key=lambda x: x["rl_final_score"], reverse=True)

        return scored_candidates

    def update_feedback(
        self,
        champion_id: int,
        champion_name: str,
        feedback_type: str,
        outcome: Optional[str] = None
    ):
        """
        更新英雄反馈

        Args:
            champion_id: 英雄ID
            champion_name: 英雄名称
            feedback_type: 反馈类型
                - "recommended": 推荐给用户
                - "accepted": 用户接受推荐
                - "rejected": 用户拒绝推荐
            outcome: 游戏结果（仅当feedback_type="accepted"时）
                - "win": 胜利
                - "loss": 失败
                - None: 尚未完成游戏
        """
        state = self.get_or_create_state(champion_id, champion_name)

        if feedback_type == "recommended":
            state.total_recommendations += 1

        elif feedback_type == "accepted":
            state.total_accepted += 1

            if outcome == "win":
                state.total_wins += 1
                state.alpha += 1.0  # 强正反馈
                print(f"  ✅ {champion_name} 推荐被接受并胜利，alpha += 1.0")

            elif outcome == "loss":
                state.total_losses += 1
                state.beta += 0.5  # 弱负反馈（失败也是学习）
                print(f"  ❌ {champion_name} 推荐被接受但失败，beta += 0.5")

            else:
                # 接受但尚未完成游戏
                state.alpha += 0.3  # 轻微正反馈（接受本身是信号）
                print(f"  🎯 {champion_name} 推荐被接受，alpha += 0.3")

        elif feedback_type == "rejected":
            state.beta += 0.2  # 轻微负反馈
            print(f"  ⏭️  {champion_name} 推荐被拒绝，beta += 0.2")

        state.last_updated = datetime.now().isoformat()

        # 保存状态
        if self.state_file:
            self.save_state()

    def batch_update_from_history(
        self,
        recommendation_history: List[Dict[str, Any]]
    ):
        """
        从历史推荐记录批量更新

        Args:
            recommendation_history: 推荐历史列表
                [
                    {
                        "champion_id": 92,
                        "champion_name": "Riven",
                        "recommended_at": "2025-10-11T10:00:00",
                        "accepted": true,
                        "outcome": "win"
                    },
                    ...
                ]
        """
        print(f"\n🔄 从历史记录批量更新 ({len(recommendation_history)}条)")

        for record in recommendation_history:
            champ_id = record["champion_id"]
            champ_name = record.get("champion_name", f"Champion_{champ_id}")

            # 标记为推荐
            self.update_feedback(champ_id, champ_name, "recommended")

            # 处理接受/拒绝
            if record.get("accepted", False):
                outcome = record.get("outcome", None)
                self.update_feedback(champ_id, champ_name, "accepted", outcome)
            else:
                self.update_feedback(champ_id, champ_name, "rejected")

        print(f"✅ 批量更新完成")

    def get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        if not self.champion_states:
            return {
                "total_champions": 0,
                "total_recommendations": 0,
                "total_accepted": 0,
                "global_acceptance_rate": 0.0
            }

        total_recs = sum(s.total_recommendations for s in self.champion_states.values())
        total_accepted = sum(s.total_accepted for s in self.champion_states.values())

        return {
            "total_champions": len(self.champion_states),
            "total_recommendations": total_recs,
            "total_accepted": total_accepted,
            "global_acceptance_rate": total_accepted / total_recs if total_recs > 0 else 0.0,
            "top_champions": [
                {
                    "champion_id": state.champion_id,
                    "champion_name": state.champion_name,
                    "expected_value": round(state.expected_value, 3),
                    "uncertainty": round(state.uncertainty, 3),
                    "total_recommendations": state.total_recommendations,
                    "acceptance_rate": round(state.acceptance_rate, 3),
                    "win_rate": round(state.win_rate, 3)
                }
                for state in sorted(
                    self.champion_states.values(),
                    key=lambda s: s.expected_value,
                    reverse=True
                )[:10]
            ]
        }

    def save_state(self):
        """保存状态到文件"""
        if not self.state_file:
            return

        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        state_data = {
            "config": {
                "alpha_prior": self.alpha_prior,
                "beta_prior": self.beta_prior,
                "exploration_bonus": self.exploration_bonus
            },
            "champion_states": {
                str(champ_id): asdict(state)
                for champ_id, state in self.champion_states.items()
            },
            "summary": self.get_state_summary(),
            "last_saved": datetime.now().isoformat()
        }

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

    def load_state(self):
        """从文件加载状态"""
        if not self.state_file or not self.state_file.exists():
            return

        with open(self.state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        # 加载配置
        config = state_data.get("config", {})
        self.alpha_prior = config.get("alpha_prior", self.alpha_prior)
        self.beta_prior = config.get("beta_prior", self.beta_prior)
        self.exploration_bonus = config.get("exploration_bonus", self.exploration_bonus)

        # 加载英雄状态
        champion_states_data = state_data.get("champion_states", {})
        for champ_id_str, state_dict in champion_states_data.items():
            champ_id = int(champ_id_str)
            self.champion_states[champ_id] = ChampionBanditState(**state_dict)

        print(f"✅ 加载RL状态: {len(self.champion_states)}个英雄, "
              f"{state_data['summary']['total_recommendations']}次推荐")


def create_default_recommender(project_root: Optional[Path] = None) -> ThompsonSamplingRecommender:
    """
    创建默认的Thompson Sampling推荐器

    Args:
        project_root: 项目根目录（用于定位state文件）

    Returns:
        ThompsonSamplingRecommender实例
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent.parent.parent

    state_file = project_root / "data/baselines/champion_recommendation_rl_state.json"

    return ThompsonSamplingRecommender(
        state_file=str(state_file),
        alpha_prior=1.0,  # 中性先验（对所有英雄一视同仁）
        beta_prior=1.0,
        exploration_bonus=0.1  # 10%探索奖励
    )
