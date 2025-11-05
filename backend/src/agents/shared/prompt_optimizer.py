"""
Prompt Optimizer - Token 使用优化工具 (Phase 4 Day 2)

提供数据摘要和 Prompt 压缩功能，降低 LLM Token 消耗
"""

from typing import Dict, Any, List
import json


class PromptOptimizer:
    """
    Prompt 优化器 (Phase 4 Token 优化)

    核心功能:
    - 数据摘要：只传递关键统计，而非完整原始数据
    - 分段摘要：按类别组织数据，减少冗余
    - Token 估算：预测 prompt token 使用量

    预期效果: Token 使用降低 20-30%
    """

    @staticmethod
    def summarize_pack_data(pack_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pack 数据摘要（压缩版本）

        Args:
            pack_data: 完整的 Player-Pack 数据

        Returns:
            压缩的摘要数据
        """
        summary = {
            "patch": pack_data.get("patch", "unknown"),
            "total_games": pack_data.get("summary", {}).get("total_games", 0),
            "total_wins": pack_data.get("summary", {}).get("total_wins", 0),
            "winrate": pack_data.get("summary", {}).get("winrate", 0.0),
        }

        # Champion-Role 数据压缩（只保留前5个最多场次）
        by_cr = pack_data.get("by_cr", [])
        if by_cr:
            # 按游戏数排序
            sorted_cr = sorted(by_cr, key=lambda x: x.get("games", 0), reverse=True)
            top_cr = sorted_cr[:5]  # 只保留前5

            summary["top_champions"] = [
                {
                    "champ_id": cr.get("champ_id"),
                    "role": cr.get("role"),
                    "games": cr.get("games", 0),
                    "wins": cr.get("wins", 0),
                    "wr": cr.get("winrate", 0.0)
                }
                for cr in top_cr
            ]

        return summary

    @staticmethod
    def summarize_all_packs(all_packs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        所有 Pack 数据的聚合摘要

        Args:
            all_packs: Pack 数据列表

        Returns:
            聚合摘要数据
        """
        if not all_packs:
            return {}

        total_games = sum(pack.get("summary", {}).get("total_games", 0) for pack in all_packs)
        total_wins = sum(pack.get("summary", {}).get("total_wins", 0) for pack in all_packs)

        # 提取所有 champion-role 数据
        all_champions = set()
        champion_games = {}

        for pack in all_packs:
            for cr in pack.get("by_cr", []):
                champ_id = cr.get("champ_id")
                all_champions.add(champ_id)

                if champ_id not in champion_games:
                    champion_games[champ_id] = 0
                champion_games[champ_id] += cr.get("games", 0)

        # 找到最常使用的英雄（前10）
        top_champions = sorted(
            champion_games.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "patches_count": len(all_packs),
            "total_games": total_games,
            "total_wins": total_wins,
            "overall_winrate": total_wins / total_games if total_games > 0 else 0.0,
            "unique_champions": len(all_champions),
            "top_10_champions": [
                {"champ_id": champ_id, "games": games}
                for champ_id, games in top_champions
            ]
        }

    @staticmethod
    def format_compact_prompt(data_summary: Dict[str, Any], analysis_type: str = "general") -> str:
        """
        格式化为紧凑的 Prompt（优化 Token 使用）

        Args:
            data_summary: 数据摘要
            analysis_type: 分析类型（决定包含哪些字段）

        Returns:
            格式化的文本
        """
        lines = []

        if analysis_type == "annual_summary":
            # 年度总结：只包含关键统计
            lines.append(f"## 数据摘要")
            lines.append(f"版本数: {data_summary.get('patches_count', 0)}")
            lines.append(f"总局数: {data_summary.get('total_games', 0)}")
            lines.append(f"整体胜率: {data_summary.get('overall_winrate', 0):.1%}")
            lines.append(f"使用英雄: {data_summary.get('unique_champions', 0)}个")

            top_champs = data_summary.get('top_10_champions', [])
            if top_champs:
                lines.append(f"\n核心英雄池:")
                for champ in top_champs[:5]:
                    lines.append(f"  - ID{champ['champ_id']}: {champ['games']}场")

        elif analysis_type == "progress_tracker":
            # 进度追踪：关注趋势
            lines.append(f"## 近期表现")
            lines.append(f"统计周期: {data_summary.get('patches_count', 0)}个版本")
            lines.append(f"总局数: {data_summary.get('total_games', 0)}")
            lines.append(f"胜率: {data_summary.get('overall_winrate', 0):.1%}")

        elif analysis_type == "role_specialization":
            # 位置专精：关注 champion-role 组合
            lines.append(f"## 位置数据")
            lines.append(f"总局数: {data_summary.get('total_games', 0)}")
            lines.append(f"胜率: {data_summary.get('overall_winrate', 0):.1%}")

            top_champs = data_summary.get('top_champions', [])
            if top_champs:
                lines.append(f"\nTop Champions:")
                for cr in top_champs:
                    lines.append(
                        f"  - ID{cr['champ_id']} ({cr['role']}): "
                        f"{cr['games']}场, {cr['wr']:.1%}"
                    )

        return "\n".join(lines)

    @staticmethod
    def estimate_token_count(text: str) -> int:
        """
        估算文本的 Token 数量（粗略估算）

        使用简单规则：
        - 英文：约 4 字符 = 1 token
        - 中文：约 2 字符 = 1 token

        Args:
            text: 文本内容

        Returns:
            估算的 token 数量
        """
        # 简化估算：平均 3 字符 = 1 token
        return len(text) // 3

    @staticmethod
    def compare_prompt_sizes(original: str, optimized: str) -> Dict[str, Any]:
        """
        对比原始和优化后的 Prompt 大小

        Args:
            original: 原始 prompt
            optimized: 优化后 prompt

        Returns:
            对比统计
        """
        original_tokens = PromptOptimizer.estimate_token_count(original)
        optimized_tokens = PromptOptimizer.estimate_token_count(optimized)

        reduction = original_tokens - optimized_tokens
        reduction_percent = (reduction / original_tokens * 100) if original_tokens > 0 else 0

        return {
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "reduction_tokens": reduction,
            "reduction_percent": reduction_percent,
            "original_chars": len(original),
            "optimized_chars": len(optimized)
        }


# 使用示例（命令行测试）
def main():
    """命令行测试入口"""
    # 示例数据
    sample_pack = {
        "patch": "14.1",
        "summary": {
            "total_games": 150,
            "total_wins": 82,
            "winrate": 0.547
        },
        "by_cr": [
            {"champ_id": 92, "role": "TOP", "games": 50, "wins": 28, "winrate": 0.56},
            {"champ_id": 67, "role": "TOP", "games": 45, "wins": 24, "winrate": 0.533},
            {"champ_id": 157, "role": "MID", "games": 30, "wins": 18, "winrate": 0.6},
            {"champ_id": 64, "role": "JUNGLE", "games": 15, "wins": 8, "winrate": 0.533},
            {"champ_id": 11, "role": "JUNGLE", "games": 10, "wins": 4, "winrate": 0.4}
        ]
    }

    optimizer = PromptOptimizer()

    # 测试摘要
    print("=" * 60)
    print("Pack数据摘要测试")
    print("=" * 60)

    summary = optimizer.summarize_pack_data(sample_pack)
    print(f"\n原始数据大小: {len(json.dumps(sample_pack))} 字符")
    print(f"摘要数据大小: {len(json.dumps(summary))} 字符")
    print(f"压缩率: {(1 - len(json.dumps(summary)) / len(json.dumps(sample_pack))) * 100:.1f}%")

    # 测试格式化
    print("\n" + "=" * 60)
    print("Prompt 格式化测试")
    print("=" * 60)

    compact_prompt = optimizer.format_compact_prompt(summary, "role_specialization")
    print(f"\n{compact_prompt}")
    print(f"\nToken 估算: ~{optimizer.estimate_token_count(compact_prompt)} tokens")


if __name__ == "__main__":
    main()
