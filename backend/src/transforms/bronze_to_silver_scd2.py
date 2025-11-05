#!/usr/bin/env python3
"""
Bronze to Silver Layer Transformation: SCD2 DimVersionedStats
将Bronze层原始比赛数据转换为Silver层SCD2维表结构
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import hashlib
from dataclasses import dataclass, asdict
from collections import defaultdict

# Import our utility classes
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.patch_mapper import PatchMapper
from utils.player_anonymizer import PlayerAnonymizer

@dataclass
class DimVersionedPlayerStats:
    """SCD2维表：版本化玩家统计"""

    # SCD2维度字段
    player_key: str  # 业务键 (匿名化PUUID)
    stats_sk: str    # 代理键 (surrogate key)

    # 版本控制字段
    patch_version: str
    effective_date: str
    expiry_date: Optional[str]
    is_current: bool
    version_number: int

    # 玩家标识
    puuid_hash: str
    summoner_name: str
    riot_id_game_name: str
    riot_id_tagline: str

    # 核心统计 - 累积值
    total_kills: int
    total_deaths: int
    total_assists: int
    total_gold_earned: int
    total_damage_dealt: int
    total_damage_taken: int
    total_healing_done: int
    total_vision_score: int
    total_cs: int  # creep score (minions killed)
    total_games: int
    total_wins: int

    # 平均值统计
    avg_kda_ratio: float
    avg_kill_participation: float
    avg_damage_per_minute: float
    avg_gold_per_minute: float
    avg_cs_per_minute: float
    avg_vision_score_per_minute: float

    # 位置偏好统计
    top_games: int
    jungle_games: int
    mid_games: int
    adc_games: int
    support_games: int
    most_played_position: str

    # 英雄统计
    unique_champions_played: int
    most_played_champion: str
    most_played_champion_games: int

    # 技能表现
    avg_skill_shots_hit: float
    avg_cc_time_dealt: float
    avg_objective_participation: float

    # 治理字段
    data_quality_score: float
    last_updated: str
    source_match_count: int
    governance_tags: str  # JSON array of tags

class BronzeToSilverSCD2Transformer:
    """Bronze到Silver层的SCD2转换器"""

    def __init__(self,
                 bronze_dir: str = "data/bronze/matches",
                 silver_dir: str = "data/silver/dimensions",
                 patch_mappings_file: str = "data/patch_mappings.json"):

        self.bronze_dir = Path(bronze_dir)
        self.silver_dir = Path(silver_dir)
        self.silver_dir.mkdir(parents=True, exist_ok=True)

        # 初始化工具
        self.patch_mapper = PatchMapper(patch_mappings_file)
        self.anonymizer = PlayerAnonymizer()

        # 内存中的聚合数据
        self.player_stats = defaultdict(lambda: defaultdict(list))  # player -> patch -> [stats]
        self.player_metadata = {}  # player -> latest metadata

        print("🔄 初始化Bronze->Silver SCD2转换器")

    def extract_bronze_data(self):
        """从Bronze层提取所有比赛数据"""
        print("📊 从Bronze层提取比赛数据...")

        total_matches = 0
        total_players = 0

        for tier_dir in self.bronze_dir.iterdir():
            if not tier_dir.is_dir():
                continue

            tier_matches = 0
            tier_players = set()

            print(f"  处理 {tier_dir.name} 段位...")

            for match_file in tier_dir.rglob("*.json"):
                try:
                    with open(match_file, 'r') as f:
                        match_data = json.load(f)

                    # 提取比赛信息
                    bronze_metadata = match_data.get('bronze_metadata', {})
                    raw_data = match_data.get('raw_data', {})
                    info = raw_data.get('info', {})

                    # 获取patch版本
                    game_timestamp = info.get('gameCreation', 0)
                    patch_version = self.patch_mapper.get_patch_by_timestamp(game_timestamp)
                    if not patch_version:
                        continue

                    # 处理每个参与者
                    participants = info.get('participants', [])
                    for participant in participants:
                        puuid = participant.get('puuid')
                        if not puuid:
                            continue

                        # 匿名化PUUID
                        player_key = self.anonymizer.anonymize_puuid(puuid)
                        tier_players.add(player_key)

                        # 提取玩家统计
                        player_stats = self._extract_player_stats(
                            participant, patch_version, bronze_metadata, info
                        )

                        # 添加到聚合数据
                        self.player_stats[player_key][patch_version].append(player_stats)

                        # 更新玩家元数据
                        self._update_player_metadata(player_key, participant)

                    tier_matches += 1
                    total_matches += 1

                except Exception as e:
                    print(f"    ⚠️ 处理文件失败 {match_file}: {e}")
                    continue

            print(f"    ✅ {tier_dir.name}: {tier_matches} 场比赛, {len(tier_players)} 个玩家")
            total_players += len(tier_players)

        print(f"✅ Bronze数据提取完成: {total_matches} 场比赛, {len(self.player_stats)} 个唯一玩家")

    def _extract_player_stats(self, participant: Dict, patch_version: str,
                            bronze_metadata: Dict, info: Dict) -> Dict:
        """从参与者数据中提取统计信息"""

        game_duration_minutes = info.get('gameDuration', 0) / 60

        return {
            'patch_version': patch_version,
            'game_timestamp': info.get('gameCreation', 0),
            'game_duration_minutes': game_duration_minutes,
            'tier': bronze_metadata.get('tier', 'unknown'),
            'quality_flag': bronze_metadata.get('quality_flag', 'UNKNOWN'),
            'governance_tag': bronze_metadata.get('governance_tag', 'UNTAGGED'),

            # 玩家标识
            'summoner_name': participant.get('summonerName', ''),
            'riot_id_game_name': participant.get('riotIdGameName', ''),
            'riot_id_tagline': participant.get('riotIdTagline', ''),

            # 基础统计
            'kills': participant.get('kills', 0),
            'deaths': participant.get('deaths', 0),
            'assists': participant.get('assists', 0),
            'gold_earned': participant.get('goldEarned', 0),
            'total_damage_dealt': participant.get('totalDamageDealtToChampions', 0),
            'total_damage_taken': participant.get('totalDamageTaken', 0),
            'total_heal': participant.get('totalHeal', 0),
            'vision_score': participant.get('visionScore', 0),
            'cs': participant.get('totalMinionsKilled', 0) + participant.get('neutralMinionsKilled', 0),
            'win': participant.get('win', False),

            # 位置和英雄
            'position': participant.get('teamPosition', participant.get('individualPosition', 'UNKNOWN')),
            'champion_name': participant.get('championName', ''),
            'champion_id': participant.get('championId', 0),

            # 技能统计
            'time_ccing_others': participant.get('timeCCingOthers', 0),
            'objective_damage': participant.get('damageDealtToObjectives', 0),
            'turret_damage': participant.get('damageDealtToTurrets', 0),
        }

    def _update_player_metadata(self, player_key: str, participant: Dict):
        """更新玩家元数据"""
        self.player_metadata[player_key] = {
            'latest_summoner_name': participant.get('summonerName', ''),
            'latest_riot_id_game_name': participant.get('riotIdGameName', ''),
            'latest_riot_id_tagline': participant.get('riotIdTagline', ''),
            'last_seen': datetime.now(timezone.utc).isoformat()
        }

    def aggregate_player_stats(self):
        """聚合玩家统计数据"""
        print("🧮 聚合玩家统计数据...")

        self.aggregated_stats = {}

        for player_key, patches_data in self.player_stats.items():
            self.aggregated_stats[player_key] = {}

            for patch_version, games_list in patches_data.items():
                if not games_list:
                    continue

                # 聚合该玩家在该patch的所有比赛数据
                aggregated = self._aggregate_patch_stats(games_list)
                self.aggregated_stats[player_key][patch_version] = aggregated

        print(f"✅ 聚合完成: {len(self.aggregated_stats)} 个玩家的统计数据")

    def _aggregate_patch_stats(self, games_list: List[Dict]) -> DimVersionedPlayerStats:
        """聚合单个玩家在单个patch的统计数据"""

        if not games_list:
            return None

        # 基础累积统计
        total_games = len(games_list)
        total_wins = sum(1 for game in games_list if game['win'])
        total_kills = sum(game['kills'] for game in games_list)
        total_deaths = sum(game['deaths'] for game in games_list)
        total_assists = sum(game['assists'] for game in games_list)
        total_gold = sum(game['gold_earned'] for game in games_list)
        total_damage_dealt = sum(game['total_damage_dealt'] for game in games_list)
        total_damage_taken = sum(game['total_damage_taken'] for game in games_list)
        total_healing = sum(game['total_heal'] for game in games_list)
        total_vision = sum(game['vision_score'] for game in games_list)
        total_cs = sum(game['cs'] for game in games_list)
        total_cc_time = sum(game['time_ccing_others'] for game in games_list)
        total_objective_damage = sum(game['objective_damage'] for game in games_list)

        # 计算总游戏时间
        total_game_minutes = sum(game['game_duration_minutes'] for game in games_list)

        # 位置统计
        position_counts = defaultdict(int)
        for game in games_list:
            position = game['position']
            if position and position != 'UNKNOWN':
                position_counts[position] += 1

        most_played_position = max(position_counts.items(), key=lambda x: x[1])[0] if position_counts else 'UNKNOWN'

        # 英雄统计
        champion_counts = defaultdict(int)
        for game in games_list:
            champion = game['champion_name']
            if champion:
                champion_counts[champion] += 1

        most_played_champion = max(champion_counts.items(), key=lambda x: x[1])[0] if champion_counts else 'UNKNOWN'
        most_played_champion_games = champion_counts[most_played_champion] if champion_counts else 0
        unique_champions = len(champion_counts)

        # 计算平均值和比率
        avg_kda = (total_kills + total_assists) / max(total_deaths, 1)
        avg_damage_per_min = total_damage_dealt / max(total_game_minutes, 1)
        avg_gold_per_min = total_gold / max(total_game_minutes, 1)
        avg_cs_per_min = total_cs / max(total_game_minutes, 1)
        avg_vision_per_min = total_vision / max(total_game_minutes, 1)
        avg_cc_time = total_cc_time / max(total_games, 1)

        # 计算击杀参与率 (需要团队数据，这里用简化版本)
        avg_kill_participation = (total_kills + total_assists) / max(total_games, 1)

        # 目标参与度
        avg_objective_participation = total_objective_damage / max(total_game_minutes, 1)

        # 数据质量评分
        quality_scores = [1.0 if game['quality_flag'] == 'PASS' else 0.5 for game in games_list]
        data_quality_score = sum(quality_scores) / len(quality_scores)

        # 治理标签
        governance_tags = list(set(game['governance_tag'] for game in games_list))

        # 获取第一场比赛的基础信息
        first_game = games_list[0]
        patch_version = first_game['patch_version']

        # 生成代理键
        player_key = f"player_{hash(str(games_list[0]))}_patch_{patch_version}"  # 临时，需要实际的player_key
        stats_sk = hashlib.md5(f"{player_key}_{patch_version}".encode()).hexdigest()

        return DimVersionedPlayerStats(
            player_key=player_key,
            stats_sk=stats_sk,
            patch_version=patch_version,
            effective_date=datetime.fromtimestamp(first_game['game_timestamp']/1000, timezone.utc).date().isoformat(),
            expiry_date=None,  # 将在SCD2处理中设置
            is_current=True,   # 将在SCD2处理中设置
            version_number=1,  # 将在SCD2处理中设置

            puuid_hash=player_key,  # 实际应该是匿名化的PUUID
            summoner_name=first_game['summoner_name'],
            riot_id_game_name=first_game['riot_id_game_name'],
            riot_id_tagline=first_game['riot_id_tagline'],

            total_kills=total_kills,
            total_deaths=total_deaths,
            total_assists=total_assists,
            total_gold_earned=total_gold,
            total_damage_dealt=total_damage_dealt,
            total_damage_taken=total_damage_taken,
            total_healing_done=total_healing,
            total_vision_score=total_vision,
            total_cs=total_cs,
            total_games=total_games,
            total_wins=total_wins,

            avg_kda_ratio=round(avg_kda, 2),
            avg_kill_participation=round(avg_kill_participation, 2),
            avg_damage_per_minute=round(avg_damage_per_min, 1),
            avg_gold_per_minute=round(avg_gold_per_min, 1),
            avg_cs_per_minute=round(avg_cs_per_min, 1),
            avg_vision_score_per_minute=round(avg_vision_per_min, 1),

            top_games=position_counts.get('TOP', 0),
            jungle_games=position_counts.get('JUNGLE', 0),
            mid_games=position_counts.get('MIDDLE', 0),
            adc_games=position_counts.get('BOTTOM', 0),
            support_games=position_counts.get('UTILITY', 0),
            most_played_position=most_played_position,

            unique_champions_played=unique_champions,
            most_played_champion=most_played_champion,
            most_played_champion_games=most_played_champion_games,

            avg_skill_shots_hit=0.0,  # 需要从challenges数据计算
            avg_cc_time_dealt=round(avg_cc_time, 1),
            avg_objective_participation=round(avg_objective_participation, 1),

            data_quality_score=round(data_quality_score, 2),
            last_updated=datetime.now(timezone.utc).isoformat(),
            source_match_count=total_games,
            governance_tags=json.dumps(governance_tags)
        )

    def apply_scd2_logic(self):
        """应用SCD2逻辑，处理版本控制"""
        print("🔄 应用SCD2版本控制逻辑...")

        self.scd2_records = []

        for player_key, patches_data in self.aggregated_stats.items():
            if not patches_data:
                continue

            # 按patch版本排序
            sorted_patches = sorted(patches_data.keys(),
                                  key=lambda x: self.patch_mapper.get_patch_info(x)['timestamp'] if self.patch_mapper.get_patch_info(x) else 0)

            for i, patch_version in enumerate(sorted_patches):
                stats_record = patches_data[patch_version]
                if not stats_record:
                    continue

                # 更新SCD2字段
                stats_record.player_key = player_key
                stats_record.version_number = i + 1
                stats_record.is_current = (i == len(sorted_patches) - 1)

                # 设置expiry_date
                if i < len(sorted_patches) - 1:
                    next_patch = sorted_patches[i + 1]
                    next_patch_info = self.patch_mapper.get_patch_info(next_patch)
                    if next_patch_info:
                        stats_record.expiry_date = datetime.fromtimestamp(
                            next_patch_info['timestamp']/1000, timezone.utc
                        ).date().isoformat()

                # 重新生成代理键
                stats_record.stats_sk = hashlib.md5(
                    f"{player_key}_{patch_version}_{stats_record.version_number}".encode()
                ).hexdigest()

                self.scd2_records.append(stats_record)

        print(f"✅ SCD2处理完成: {len(self.scd2_records)} 条版本化记录")

    def save_silver_layer(self):
        """保存到Silver层"""
        print("💾 保存到Silver层...")

        # 创建输出目录
        dim_stats_dir = self.silver_dir / "dim_versioned_player_stats"
        dim_stats_dir.mkdir(parents=True, exist_ok=True)

        # 按patch分区保存
        patch_groups = defaultdict(list)
        for record in self.scd2_records:
            patch_groups[record.patch_version].append(record)

        total_records = 0
        for patch_version, records in patch_groups.items():
            patch_file = dim_stats_dir / f"patch_{patch_version}.json"

            # 转换为字典格式
            records_data = [asdict(record) for record in records]

            # 添加元数据
            output_data = {
                'metadata': {
                    'patch_version': patch_version,
                    'record_count': len(records),
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'schema_version': '1.0',
                    'data_type': 'dim_versioned_player_stats'
                },
                'records': records_data
            }

            with open(patch_file, 'w') as f:
                json.dump(output_data, f, indent=2)

            print(f"  ✅ {patch_version}: {len(records)} 条记录 -> {patch_file}")
            total_records += len(records)

        # 保存转换摘要
        summary = {
            'transformation_summary': {
                'source_layer': 'bronze',
                'target_layer': 'silver',
                'transformation_type': 'scd2_dim_versioned_stats',
                'total_players': len(self.aggregated_stats),
                'total_records': total_records,
                'patches_processed': len(patch_groups),
                'transformation_timestamp': datetime.now(timezone.utc).isoformat()
            },
            'quality_metrics': {
                'avg_data_quality_score': sum(r.data_quality_score for r in self.scd2_records) / len(self.scd2_records),
                'records_with_high_quality': sum(1 for r in self.scd2_records if r.data_quality_score >= 0.9),
                'unique_players': len(set(r.player_key for r in self.scd2_records))
            }
        }

        summary_file = self.silver_dir / "transformation_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"✅ Silver层保存完成: {total_records} 条记录, {len(patch_groups)} 个patch分区")

    def run_transformation(self):
        """运行完整的转换流程"""
        print("🚀 开始Bronze->Silver SCD2转换...")

        try:
            self.extract_bronze_data()
            self.aggregate_player_stats()
            self.apply_scd2_logic()
            self.save_silver_layer()

            print("✅ Bronze->Silver SCD2转换完成!")

        except Exception as e:
            print(f"💥 转换失败: {e}")
            raise


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bronze to Silver SCD2 Transformation")
    parser.add_argument("--bronze-dir", default="data/bronze/matches",
                       help="Bronze层数据目录")
    parser.add_argument("--silver-dir", default="data/silver/dimensions",
                       help="Silver层输出目录")
    parser.add_argument("--patch-mappings", default="data/patch_mappings.json",
                       help="Patch映射文件")

    args = parser.parse_args()

    try:
        transformer = BronzeToSilverSCD2Transformer(
            bronze_dir=args.bronze_dir,
            silver_dir=args.silver_dir,
            patch_mappings_file=args.patch_mappings
        )

        transformer.run_transformation()
        return 0

    except Exception as e:
        print(f"💥 转换失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())