"""ChampionRecommendationAgent - Recommendation Tools"""

import json
from pathlib import Path
from typing import Dict, Any, List
from src.analytics import ChampionSimilarityCalculator, MetaTierClassifier
from src.utils.id_mappings import get_champion_name


def analyze_champion_pool(packs_dir: str, time_range: str = None) -> Dict[str, Any]:
    """分析玩家英雄池特征"""
    from datetime import datetime, timedelta
    
    packs_dir = Path(packs_dir)
    
    # Calculate time filter if needed
    cutoff_timestamp = None
    if time_range == "2024-01-01":
        cutoff_timestamp = datetime(2024, 1, 1).timestamp()
    elif time_range == "past-365":
        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()
    
    pack_files = sorted(packs_dir.glob("pack_*.json"))

    # 聚合所有英雄数据
    champion_stats = {}
    for pack_file in pack_files:
        with open(pack_file, 'r') as f:
            pack_data = json.load(f)
            
            # Apply time range filter if specified
            if cutoff_timestamp and "generation_timestamp" in pack_data:
                pack_timestamp = pack_data["generation_timestamp"]
                # If timestamp is string, convert to timestamp
                if isinstance(pack_timestamp, str):
                    pack_timestamp = datetime.fromisoformat(pack_timestamp.replace('Z', '+00:00')).timestamp()
                
                # Skip if before cutoff
                if pack_timestamp < cutoff_timestamp:
                    continue
            
            for cr in pack_data.get("by_cr", []):
                champ_id = cr["champ_id"]
                if champ_id not in champion_stats:
                    champion_stats[champ_id] = {"games": 0, "wins": 0, "roles": set()}
                champion_stats[champ_id]["games"] += cr["games"]
                champion_stats[champ_id]["wins"] += cr["wins"]
                champion_stats[champ_id]["roles"].add(cr["role"])

    # 识别核心英雄
    core_champions = []
    for champ_id, stats in champion_stats.items():
        if stats["games"] >= 20:  # 核心英雄标准：20+场
            wr = stats["wins"] / stats["games"]
            core_champions.append({
                "champion_id": champ_id,
                "champion_name": get_champion_name(champ_id),
                "games": stats["games"],
                "winrate": round(wr, 3),
                "roles": list(stats["roles"])
            })

    return {
        "total_champions": len(champion_stats),
        "core_champions": sorted(core_champions, key=lambda x: x["games"], reverse=True)
    }


def load_champion_data() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    加载英雄相似度和Meta层级数据（自动生成如果不存在）

    Returns:
        (similarity_data, meta_data)
    """
    project_root = Path(__file__).parent.parent.parent.parent.parent
    similarity_file = project_root / "data/baselines/champion_similarity.json"
    meta_file = project_root / "data/baselines/meta_tiers.json"
    gold_parquet = project_root / "data/gold/parquet/fact_match_performance.parquet"

    # 检查并生成相似度数据
    if not similarity_file.exists():
        print(f"⚠️  英雄相似度数据不存在，正在从Gold layer自动生成...")

        if not gold_parquet.exists():
            print(f"❌ Gold layer数据不存在: {gold_parquet}")
            return {}, {}

        try:
            calculator = ChampionSimilarityCalculator(
                parquet_path=str(gold_parquet),
                min_games=50
            )
            calculator.save(output_path=str(similarity_file), top_k=10)
            print(f"✅ 英雄相似度数据已生成: {similarity_file}")
        except Exception as e:
            print(f"❌ 生成英雄相似度数据失败: {e}")
            return {}, {}

    # 检查并生成Meta层级数据
    if not meta_file.exists():
        print(f"⚠️  Meta层级数据不存在，正在从Gold layer自动生成...")

        if not gold_parquet.exists():
            print(f"❌ Gold layer数据不存在: {gold_parquet}")
            return {}, {}

        try:
            classifier = MetaTierClassifier(
                parquet_path=str(gold_parquet),
                min_games=50
            )
            classifier.save(output_path=str(meta_file), include_role_tiers=False)
            print(f"✅ Meta层级数据已生成: {meta_file}")
        except Exception as e:
            print(f"❌ 生成Meta层级数据失败: {e}")
            return {}, {}

    # 读取数据
    with open(similarity_file, 'r', encoding='utf-8') as f:
        similarity_data = json.load(f)

    with open(meta_file, 'r', encoding='utf-8') as f:
        meta_data = json.load(f)

    return similarity_data, meta_data


def generate_recommendations(champion_pool: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    生成英雄推荐（基于相似度和Meta数据）

    推荐逻辑：
    1. 基于玩家核心英雄，找相似但未掌握的英雄
    2. 优先推荐Meta层级高的英雄
    3. 结合风格匹配度排序
    """
    core_champs = champion_pool["core_champions"]

    if not core_champs:
        return []

    # 加载相似度和Meta数据
    similarity_data, meta_data = load_champion_data()

    if not similarity_data or not meta_data:
        print("⚠️  缺少推荐所需数据，返回空推荐列表")
        return []

    # 获取玩家已掌握的英雄ID集合
    mastered_ids = {c["champion_id"] for c in core_champs}

    # 构建Meta层级评分映射（S=5, A=4, B=3, C=2, D=1）
    tier_scores = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    champion_tiers = {}
    for tier, champions in meta_data.items():
        if tier in tier_scores:
            for champ in champions:
                champion_tiers[champ["champion_id"]] = {
                    "tier": tier,
                    "tier_score": tier_scores[tier],
                    "winrate": champ.get("winrate", 0.5),
                    "meta_score": champ.get("meta_score", 0.5)
                }

    # 收集候选推荐
    candidates = []
    for core_champ in core_champs[:3]:  # 只基于前3个核心英雄
        champ_id = str(core_champ["champion_id"])

        if champ_id not in similarity_data.get("top_similar", {}):
            continue

        # 获取相似英雄
        similar_champions = similarity_data["top_similar"][champ_id]

        for similar in similar_champions:
            similar_id = similar["champion_id"]

            # 跳过已掌握的英雄
            if similar_id in mastered_ids:
                continue

            # 获取Meta信息
            meta_info = champion_tiers.get(similar_id, {
                "tier": "C",
                "tier_score": 2,
                "winrate": 0.5,
                "meta_score": 0.5
            })

            # 综合评分 = 相似度40% + Meta评分30% + 层级30%
            综合评分 = (
                similar["similarity_score"] * 0.4 +
                meta_info["meta_score"] * 0.3 +
                (meta_info["tier_score"] / 5) * 0.3
            )

            candidates.append({
                "champion_id": similar_id,
                "champion_name": similar["champion_name"],
                "based_on": similarity_data["champions"][champ_id],
                "similarity_score": similar["similarity_score"],
                "meta_tier": meta_info["tier"],
                "综合评分": 综合评分,
                "reason": f"与您擅长的{similarity_data['champions'][champ_id]}风格相似 (相似度{similar['similarity_score']:.2f})",
                "meta_info": meta_info
            })

    # 去重并排序
    seen = set()
    unique_candidates = []
    for cand in sorted(candidates, key=lambda x: x["综合评分"], reverse=True):
        if cand["champion_id"] not in seen:
            seen.add(cand["champion_id"])
            unique_candidates.append(cand)

    # 返回Top 5
    recommendations = []
    for i, cand in enumerate(unique_candidates[:5], 1):
        recommendations.append({
            "champion_id": cand["champion_id"],
            "champion_name": cand["champion_name"],
            "reason": cand["reason"],
            "meta_tier": cand["meta_tier"],
            "similarity_score": round(cand["similarity_score"], 3),
            "综合评分": round(cand["综合评分"], 3),
            "priority": i
        })

    return recommendations


def format_analysis_for_prompt(champion_pool: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> str:
    """格式化推荐数据"""
    lines = ["# 英雄推荐分析数据\n"]

    lines.append(f"**英雄池规模**: {champion_pool['total_champions']}个英雄")
    lines.append(f"**核心英雄**: {len(champion_pool['core_champions'])}个\n")

    if champion_pool["core_champions"]:
        lines.append("## 核心英雄")
        for champ in champion_pool["core_champions"][:5]:
            lines.append(f"- **{champ['champion_name']} (ID: {champ['champion_id']})**: {champ['games']}场, "
                        f"{champ['winrate']:.1%}胜率, 位置: {', '.join(champ['roles'])}")
        lines.append("")

    if recommendations:
        lines.append("## 推荐英雄 (基于相似度和Meta数据)")
        for rec in recommendations:
            lines.append(f"\n### {rec['priority']}. {rec['champion_name']} (英雄ID: {rec['champion_id']})")
            lines.append(f"- **Meta层级**: {rec['meta_tier']}")
            lines.append(f"- **相似度评分**: {rec['similarity_score']:.2f}")
            lines.append(f"- **综合评分**: {rec['综合评分']:.2f}")
            lines.append(f"- **推荐理由**: {rec['reason']}")
    else:
        lines.append("\n## 暂无推荐")
        lines.append("需要更多核心英雄数据或无可推荐英雄")

    return "\n".join(lines)
