#!/usr/bin/env python3
"""
Champion Similarity Calculator
英雄相似度计算模块

基于多维统计特征计算英雄之间的相似度矩阵
"""

import duckdb
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChampionSimilarityCalculator:
    """英雄相似度计算器"""

    # 用于计算相似度的特征维度
    FEATURE_COLUMNS = [
        'avg_kills', 'avg_deaths', 'avg_assists',
        'avg_kda_ratio',
        'avg_cs_per_minute',
        'avg_gold_per_minute',
        'avg_damage_per_minute',
        'avg_damage_taken',
        'avg_vision_score_per_minute',
        'avg_turret_kills',
        'avg_dragon_kills',
        'avg_baron_kills',
    ]

    def __init__(
        self,
        parquet_path: str,
        min_games: int = 50
    ):
        """
        初始化英雄相似度计算器

        Args:
            parquet_path: Gold layer Parquet文件路径
            min_games: 计算相似度所需的最小游戏场次
        """
        self.parquet_path = Path(parquet_path)
        self.min_games = min_games

        if not self.parquet_path.exists():
            raise FileNotFoundError(f"Parquet文件不存在: {parquet_path}")

    def _extract_champion_features(self) -> Tuple[Dict[int, str], np.ndarray]:
        """
        从Parquet文件提取英雄特征向量

        Returns:
            (champion_id_to_name映射, 特征矩阵)
        """
        logger.info(f"📊 正在从 {self.parquet_path} 提取英雄特征...")

        conn = duckdb.connect(":memory:")

        # 聚合每个英雄的统计数据
        feature_list = ', '.join([f'AVG({col.replace("avg_", "")}) as {col}'
                                   for col in self.FEATURE_COLUMNS])

        query = f"""
        SELECT
            champion_id,
            champion_name,
            COUNT(*) as total_games,
            {feature_list}
        FROM read_parquet(?)
        WHERE champion_id IS NOT NULL
        GROUP BY champion_id, champion_name
        HAVING COUNT(*) >= ?
        ORDER BY champion_id
        """

        result = conn.execute(query, [str(self.parquet_path), self.min_games]).fetchall()
        conn.close()

        if not result:
            raise ValueError(f"没有找到满足最小游戏场次({self.min_games})的英雄数据")

        # 构建champion_id映射和特征矩阵
        champion_mapping = {}
        features = []

        for row in result:
            champion_id = row[0]
            champion_name = row[1]
            # total_games = row[2]
            feature_vector = row[3:]  # 从第4列开始是特征

            champion_mapping[champion_id] = champion_name
            features.append(feature_vector)

        features_array = np.array(features, dtype=float)

        logger.info(f"✅ 提取了 {len(champion_mapping)} 个英雄的特征向量")

        return champion_mapping, features_array

    def calculate_similarity_matrix(self) -> Dict[str, Any]:
        """
        计算英雄相似度矩阵

        Returns:
            相似度矩阵数据，格式：
            {
                "champions": {champion_id: champion_name},
                "similarity_matrix": [[sim_00, sim_01, ...], ...],
                "top_similar": {champion_id: [(similar_id, score), ...]}
            }
        """
        # 提取特征
        champion_mapping, features = self._extract_champion_features()

        # 标准化特征（Z-score normalization）
        logger.info("🔄 正在标准化特征向量...")
        scaler = StandardScaler()
        features_normalized = scaler.fit_transform(features)

        # 计算余弦相似度矩阵
        logger.info("🔄 正在计算余弦相似度矩阵...")
        similarity_matrix = cosine_similarity(features_normalized)

        # 将对角线设为0（英雄与自己的相似度不考虑）
        np.fill_diagonal(similarity_matrix, 0)

        logger.info(f"✅ 成功计算 {len(champion_mapping)}×{len(champion_mapping)} 相似度矩阵")

        return {
            "champions": champion_mapping,
            "similarity_matrix": similarity_matrix.tolist(),
            "feature_columns": self.FEATURE_COLUMNS
        }

    def get_top_similar(
        self,
        similarity_data: Dict[str, Any],
        top_k: int = 5
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        获取每个英雄最相似的Top-K英雄

        Args:
            similarity_data: calculate_similarity_matrix返回的数据
            top_k: 返回前K个最相似的英雄

        Returns:
            {champion_id: [(similar_champion_id, similarity_score), ...]}
        """
        logger.info(f"🔄 正在计算每个英雄的Top-{top_k}相似英雄...")

        champions = similarity_data["champions"]
        similarity_matrix = np.array(similarity_data["similarity_matrix"])

        champion_ids = list(champions.keys())
        top_similar = {}

        for i, champion_id in enumerate(champion_ids):
            # 获取当前英雄与其他所有英雄的相似度
            similarities = similarity_matrix[i]

            # 获取Top-K最高的相似度索引
            top_indices = np.argsort(similarities)[::-1][:top_k]

            # 构建(相似英雄ID, 相似度分数)列表
            top_similar[champion_id] = [
                (champion_ids[idx], round(float(similarities[idx]), 4))
                for idx in top_indices
            ]

        logger.info(f"✅ 成功计算所有英雄的Top-{top_k}相似英雄")

        return top_similar

    def save(self, output_path: str, top_k: int = 10) -> None:
        """
        计算并保存英雄相似度数据到JSON文件

        Args:
            output_path: 输出文件路径
            top_k: 保存每个英雄的Top-K相似英雄
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 计算相似度矩阵
        similarity_data = self.calculate_similarity_matrix()

        # 计算Top-K相似英雄
        top_similar = self.get_top_similar(similarity_data, top_k=top_k)

        # 准备输出数据（不包含完整矩阵，只保存Top-K）
        output_data = {
            "champions": similarity_data["champions"],
            "feature_columns": similarity_data["feature_columns"],
            "top_similar": {
                str(champ_id): [
                    {
                        "champion_id": sim_id,
                        "champion_name": similarity_data["champions"][sim_id],
                        "similarity_score": score
                    }
                    for sim_id, score in similar_list
                ]
                for champ_id, similar_list in top_similar.items()
            },
            "metadata": {
                "min_games": self.min_games,
                "total_champions": len(similarity_data["champions"]),
                "top_k": top_k
            }
        }

        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 英雄相似度数据已保存到: {output_file}")

        # 打印摘要
        self._print_summary(output_data, top_k=5)

    def _print_summary(self, data: Dict[str, Any], top_k: int = 5) -> None:
        """打印相似度计算摘要"""
        print("\n" + "="*80)
        print("英雄相似度计算摘要")
        print("="*80)
        print(f"总英雄数: {data['metadata']['total_champions']}")
        print(f"最小游戏场次: {data['metadata']['min_games']}")
        print(f"特征维度: {len(data['feature_columns'])}")
        print("\n示例 - 前3个英雄的Top-{} 相似英雄:".format(top_k))
        print("-"*80)

        for i, (champ_id, similar_list) in enumerate(list(data['top_similar'].items())[:3]):
            champ_name = data['champions'][int(champ_id)]
            print(f"\n{champ_name} (ID: {champ_id}):")
            for rank, similar in enumerate(similar_list[:top_k], 1):
                print(f"  {rank}. {similar['champion_name']:<20} (相似度: {similar['similarity_score']:.3f})")

        print("\n" + "="*80 + "\n")
