#!/usr/bin/env python3
"""
Enhanced Fact Table Transform with Governance
使用完整治理框架的增强事实表转换器
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
import hashlib
from dataclasses import dataclass, asdict

# Import our utility classes and governance framework
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.patch_mapper import PatchMapper
from utils.player_anonymizer import PlayerAnonymizer
from transforms.governance_framework import DataGovernanceFramework

@dataclass
class EnhancedFactMatchPerformance:
    """增强的比赛表现事实表 - 包含完整治理字段"""

    # 主键和外键
    match_performance_sk: str
    match_id: str
    player_key: str

    # 时间维度
    match_date: str
    patch_version: str
    game_duration_minutes: float

    # 比赛上下文
    region: str
    tier: str
    queue_type: str
    game_mode: str

    # 玩家表现指标 (基础统计)
    kills: int
    deaths: int
    assists: int
    kda_ratio: float
    kill_participation: float

    # 经济表现
    gold_earned: int
    gold_per_minute: float
    gold_spent: int

    # 伤害统计
    total_damage_dealt: int
    damage_to_champions: int
    damage_per_minute: float
    physical_damage: int
    magic_damage: int
    true_damage: int
    damage_taken: int
    damage_mitigated: int

    # 农兵和野怪
    cs_total: int
    cs_per_minute: float
    jungle_cs: int
    enemy_jungle_cs: int

    # 视野表现
    vision_score: int
    vision_score_per_minute: float
    wards_placed: int
    wards_killed: int
    control_wards: int

    # 团战和击杀
    double_kills: int
    triple_kills: int
    quadra_kills: int
    penta_kills: int
    killing_sprees: int
    largest_killing_spree: int

    # 目标控制
    turret_kills: int
    inhibitor_kills: int
    dragon_kills: int
    baron_kills: int
    objectives_stolen: int

    # 位置和英雄
    position: str
    champion_name: str
    champion_id: int
    champion_level: int

    # 符文和装备
    primary_rune_tree: str
    secondary_rune_tree: str
    keystone_rune: str
    final_items: str

    # 技能施放
    spell1_casts: int
    spell2_casts: int
    spell3_casts: int
    spell4_casts: int
    summoner1_casts: int
    summoner2_casts: int

    # 团队协作
    cc_time_dealt: float
    healing_done: int
    damage_shielded: int

    # 比赛结果
    win: bool
    team_id: int
    game_ended_early: bool
    surrender: bool

    # === 增强治理字段 ===
    # 数据质量指标
    data_quality_score: float
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    timeliness_score: float
    validity_score: float
    uniqueness_score: float

    # 合规性字段
    anonymization_validated: bool
    pii_detection_passed: bool
    gdpr_compliant: bool

    # 数据血缘
    source_system: str
    source_table: str
    transformation_id: str
    transformation_timestamp: str
    data_lineage: str  # JSON

    # 治理和风险
    governance_tags: str  # JSON array
    risk_level: str
    validation_errors: str  # JSON array
    governance_record_id: str

    # 审计字段
    created_at: str
    validated_by: str
    ingestion_timestamp: str


class EnhancedFactTransformer:
    """增强的事实表转换器 - 包含完整治理功能"""

    def __init__(self,
                 bronze_dir: str = "data/bronze/matches",
                 silver_dir: str = "data/silver/enhanced_facts",
                 patch_mappings_file: str = "data/patch_mappings.json"):

        self.bronze_dir = Path(bronze_dir)
        self.silver_dir = Path(silver_dir)
        self.silver_dir.mkdir(parents=True, exist_ok=True)

        # 初始化工具
        self.patch_mapper = PatchMapper(patch_mappings_file)
        self.anonymizer = PlayerAnonymizer()
        self.governance = DataGovernanceFramework()

        self.fact_records = []
        self.governance_summary = {
            'total_processed': 0,
            'high_quality_records': 0,
            'compliant_records': 0,
            'validation_errors_found': 0,
            'risk_distribution': {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
        }

        print("🛡️ 初始化增强事实表转换器(含完整治理)")

    def extract_and_transform(self):
        """提取和转换比赛数据为增强事实表记录"""
        print("🔄 转换比赛数据为增强事实表(含治理)...")

        total_matches = 0
        total_participants = 0

        for tier_dir in self.bronze_dir.iterdir():
            if not tier_dir.is_dir():
                continue

            tier_matches = 0
            tier_participants = 0

            print(f"  处理 {tier_dir.name} 段位...")

            for match_file in tier_dir.rglob("*.json"):
                try:
                    with open(match_file, 'r') as f:
                        match_data = json.load(f)

                    # 提取比赛信息
                    bronze_metadata = match_data.get('bronze_metadata', {})
                    raw_data = match_data.get('raw_data', {})
                    info = raw_data.get('info', {})

                    # 比赛基础信息
                    match_id = info.get('gameId', '')
                    if not match_id:
                        continue

                    # 获取patch版本
                    game_timestamp = info.get('gameCreation', 0)
                    patch_version = self.patch_mapper.get_patch_by_timestamp(game_timestamp)
                    if not patch_version:
                        continue

                    # 比赛上下文
                    game_duration = info.get('gameDuration', 0)
                    game_duration_minutes = game_duration / 60 if game_duration > 0 else 0

                    match_date = datetime.fromtimestamp(game_timestamp/1000, timezone.utc).date().isoformat()

                    # 处理每个参与者
                    participants = info.get('participants', [])
                    for participant in participants:
                        puuid = participant.get('puuid')
                        if not puuid:
                            continue

                        # 匿名化PUUID
                        player_key = self.anonymizer.anonymize_puuid(puuid)

                        # 创建增强事实表记录
                        enhanced_record = self._create_enhanced_fact_record(
                            participant, match_id, player_key,
                            patch_version, match_date, game_duration_minutes,
                            bronze_metadata, info
                        )

                        if enhanced_record:
                            self.fact_records.append(enhanced_record)
                            tier_participants += 1
                            total_participants += 1

                    tier_matches += 1
                    total_matches += 1

                except Exception as e:
                    print(f"    ⚠️ 处理文件失败 {match_file}: {e}")
                    continue

            print(f"    ✅ {tier_dir.name}: {tier_matches} 场比赛, {tier_participants} 条记录")

        print(f"✅ 增强事实表转换完成: {total_matches} 场比赛, {total_participants} 条记录")
        print(f"🛡️ 治理摘要: {self.governance_summary}")

    def _create_enhanced_fact_record(self, participant: Dict, match_id: str, player_key: str,
                                   patch_version: str, match_date: str, game_duration_minutes: float,
                                   bronze_metadata: Dict, info: Dict) -> EnhancedFactMatchPerformance:
        """创建单条增强事实表记录"""

        try:
            # 生成代理键
            match_performance_sk = hashlib.md5(
                f"{match_id}_{player_key}_{participant.get('participantId', 0)}".encode()
            ).hexdigest()

            # 创建基础记录数据
            base_record = {
                'match_id': str(match_id),
                'player_key': player_key,
                'patch_version': patch_version,
                'kills': participant.get('kills', 0),
                'deaths': participant.get('deaths', 0),
                'assists': participant.get('assists', 0),
                'gold_earned': participant.get('goldEarned', 0),
                'game_duration_minutes': game_duration_minutes,
                'tier': bronze_metadata.get('tier', 'unknown'),
                'ingestion_timestamp': bronze_metadata.get('ingestion_timestamp', '')
            }

            # === 使用治理框架生成完整治理记录 ===
            governance_record = self.governance.generate_governance_record(
                base_record,
                record_type="fact",
                source="bronze_matches",
                transformation="enhanced_fact_transform"
            )

            # 更新治理摘要统计
            self._update_governance_summary(governance_record)

            # === 构建完整的增强事实记录 ===

            # 基础统计
            kills = participant.get('kills', 0)
            deaths = participant.get('deaths', 0)
            assists = participant.get('assists', 0)
            kda_ratio = (kills + assists) / max(deaths, 1)

            # 经济统计
            gold_earned = participant.get('goldEarned', 0)
            gold_per_minute = gold_earned / max(game_duration_minutes, 1)

            # 伤害统计
            total_damage = participant.get('totalDamageDealtToChampions', 0)
            damage_per_minute = total_damage / max(game_duration_minutes, 1)

            # CS统计
            cs_total = participant.get('totalMinionsKilled', 0) + participant.get('neutralMinionsKilled', 0)
            cs_per_minute = cs_total / max(game_duration_minutes, 1)

            # 视野统计
            vision_score = participant.get('visionScore', 0)
            vision_score_per_minute = vision_score / max(game_duration_minutes, 1)

            # 击杀参与率计算
            team_id = participant.get('teamId', 0)
            kill_participation = 0.0  # 简化实现

            # 符文信息
            perks = participant.get('perks', {})
            styles = perks.get('styles', [])
            primary_style = styles[0] if len(styles) > 0 else {}
            secondary_style = styles[1] if len(styles) > 1 else {}

            primary_rune_tree = str(primary_style.get('style', 0))
            secondary_rune_tree = str(secondary_style.get('style', 0))

            # 主要符文（基石符文）
            primary_selections = primary_style.get('selections', [])
            keystone_rune = str(primary_selections[0].get('perk', 0)) if primary_selections else "0"

            # 最终装备
            final_items = [
                participant.get(f'item{i}', 0)
                for i in range(7)
                if participant.get(f'item{i}', 0) > 0
            ]

            return EnhancedFactMatchPerformance(
                # 主键和外键
                match_performance_sk=match_performance_sk,
                match_id=str(match_id),
                player_key=player_key,

                # 时间维度
                match_date=match_date,
                patch_version=patch_version,
                game_duration_minutes=round(game_duration_minutes, 1),

                # 比赛上下文
                region=bronze_metadata.get('region', 'unknown'),
                tier=bronze_metadata.get('tier', 'unknown'),
                queue_type=str(info.get('queueId', 0)),
                game_mode=info.get('gameMode', 'UNKNOWN'),

                # 玩家表现指标
                kills=kills,
                deaths=deaths,
                assists=assists,
                kda_ratio=round(kda_ratio, 2),
                kill_participation=round(kill_participation, 2),

                # 经济表现
                gold_earned=gold_earned,
                gold_per_minute=round(gold_per_minute, 1),
                gold_spent=participant.get('goldSpent', 0),

                # 伤害统计
                total_damage_dealt=participant.get('totalDamageDealt', 0),
                damage_to_champions=participant.get('totalDamageDealtToChampions', 0),
                damage_per_minute=round(damage_per_minute, 1),
                physical_damage=participant.get('physicalDamageDealtToChampions', 0),
                magic_damage=participant.get('magicDamageDealtToChampions', 0),
                true_damage=participant.get('trueDamageDealtToChampions', 0),
                damage_taken=participant.get('totalDamageTaken', 0),
                damage_mitigated=participant.get('damageSelfMitigated', 0),

                # 农兵和野怪
                cs_total=cs_total,
                cs_per_minute=round(cs_per_minute, 1),
                jungle_cs=participant.get('neutralMinionsKilled', 0),
                enemy_jungle_cs=participant.get('totalEnemyJungleMinionsKilled', 0),

                # 视野表现
                vision_score=vision_score,
                vision_score_per_minute=round(vision_score_per_minute, 1),
                wards_placed=participant.get('wardsPlaced', 0),
                wards_killed=participant.get('wardsKilled', 0),
                control_wards=participant.get('visionWardsBoughtInGame', 0),

                # 团战和击杀
                double_kills=participant.get('doubleKills', 0),
                triple_kills=participant.get('tripleKills', 0),
                quadra_kills=participant.get('quadraKills', 0),
                penta_kills=participant.get('pentaKills', 0),
                killing_sprees=participant.get('killingSprees', 0),
                largest_killing_spree=participant.get('largestKillingSpree', 0),

                # 目标控制
                turret_kills=participant.get('turretKills', 0),
                inhibitor_kills=participant.get('inhibitorKills', 0),
                dragon_kills=participant.get('dragonKills', 0),
                baron_kills=participant.get('baronKills', 0),
                objectives_stolen=participant.get('objectivesStolen', 0),

                # 位置和英雄
                position=participant.get('teamPosition', participant.get('individualPosition', 'UNKNOWN')),
                champion_name=participant.get('championName', 'Unknown'),
                champion_id=participant.get('championId', 0),
                champion_level=participant.get('champLevel', 0),

                # 符文和装备
                primary_rune_tree=primary_rune_tree,
                secondary_rune_tree=secondary_rune_tree,
                keystone_rune=keystone_rune,
                final_items=json.dumps(final_items),

                # 技能施放
                spell1_casts=participant.get('spell1Casts', 0),
                spell2_casts=participant.get('spell2Casts', 0),
                spell3_casts=participant.get('spell3Casts', 0),
                spell4_casts=participant.get('spell4Casts', 0),
                summoner1_casts=participant.get('summoner1Casts', 0),
                summoner2_casts=participant.get('summoner2Casts', 0),

                # 团队协作
                cc_time_dealt=participant.get('timeCCingOthers', 0) / 1000,
                healing_done=participant.get('totalHeal', 0),
                damage_shielded=participant.get('totalDamageShieldedOnTeammates', 0),

                # 比赛结果
                win=participant.get('win', False),
                team_id=participant.get('teamId', 0),
                game_ended_early=participant.get('gameEndedInEarlySurrender', False),
                surrender=participant.get('gameEndedInSurrender', False),

                # === 增强治理字段 ===
                # 数据质量指标
                data_quality_score=governance_record.data_quality.overall_score,
                completeness_score=governance_record.data_quality.completeness_score,
                accuracy_score=governance_record.data_quality.accuracy_score,
                consistency_score=governance_record.data_quality.consistency_score,
                timeliness_score=governance_record.data_quality.timeliness_score,
                validity_score=governance_record.data_quality.validity_score,
                uniqueness_score=governance_record.data_quality.uniqueness_score,

                # 合规性字段
                anonymization_validated=governance_record.compliance.anonymization_validated,
                pii_detection_passed=governance_record.compliance.pii_detection_passed,
                gdpr_compliant=governance_record.compliance.gdpr_compliant,

                # 数据血缘
                source_system=governance_record.lineage.source_system,
                source_table=governance_record.lineage.source_table,
                transformation_id=governance_record.lineage.transformation_id,
                transformation_timestamp=governance_record.lineage.transformation_timestamp,
                data_lineage=json.dumps(asdict(governance_record.lineage)),

                # 治理和风险
                governance_tags=json.dumps(governance_record.governance_tags),
                risk_level=governance_record.risk_level,
                validation_errors=json.dumps(governance_record.validation_errors),
                governance_record_id=governance_record.record_id,

                # 审计字段
                created_at=governance_record.created_at,
                validated_by=governance_record.validated_by,
                ingestion_timestamp=bronze_metadata.get('ingestion_timestamp', '')
            )

        except Exception as e:
            print(f"    ⚠️ 创建增强事实记录失败: {e}")
            return None

    def _update_governance_summary(self, governance_record):
        """更新治理摘要统计"""
        self.governance_summary['total_processed'] += 1

        if governance_record.data_quality.overall_score >= 0.9:
            self.governance_summary['high_quality_records'] += 1

        if governance_record.compliance.gdpr_compliant:
            self.governance_summary['compliant_records'] += 1

        if governance_record.validation_errors:
            self.governance_summary['validation_errors_found'] += 1

        # 风险分布统计
        self.governance_summary['risk_distribution'][governance_record.risk_level] += 1

    def save_enhanced_fact_table(self):
        """保存增强事实表到Silver层"""
        print("💾 保存增强事实表到Silver层...")

        if not self.fact_records:
            print("⚠️ 没有增强事实记录可保存")
            return

        # 按patch分区保存
        from collections import defaultdict
        patch_groups = defaultdict(list)

        for record in self.fact_records:
            patch_groups[record.patch_version].append(record)

        total_records = 0
        for patch_version, records in patch_groups.items():
            patch_file = self.silver_dir / f"enhanced_fact_match_performance_patch_{patch_version}.json"

            # 转换为字典格式
            records_data = [asdict(record) for record in records]

            # 添加元数据
            output_data = {
                'metadata': {
                    'table_name': 'enhanced_fact_match_performance',
                    'patch_version': patch_version,
                    'record_count': len(records),
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'schema_version': '2.0',
                    'governance_enabled': True
                },
                'governance_summary': self.governance_summary,
                'records': records_data
            }

            with open(patch_file, 'w') as f:
                json.dump(output_data, f, indent=2)

            print(f"  ✅ {patch_version}: {len(records)} 条记录 -> {patch_file}")
            total_records += len(records)

        # 保存完整治理报告
        governance_report = self.governance.generate_quality_report(
            [asdict(r) for r in self.fact_records[:100]],  # 样本检查
            record_type="enhanced_fact"
        )

        governance_file = self.silver_dir / "governance_quality_report.json"
        with open(governance_file, 'w') as f:
            json.dump(governance_report, f, indent=2)

        print(f"✅ 增强事实表保存完成: {total_records} 条记录, {len(patch_groups)} 个patch分区")
        print(f"🛡️ 治理报告: {governance_file}")

    def run_enhanced_transformation(self):
        """运行完整的增强事实表转换流程"""
        print("🚀 开始增强事实表转换(含完整治理)...")

        try:
            self.extract_and_transform()
            self.save_enhanced_fact_table()

            print("✅ 增强事实表转换完成!")

        except Exception as e:
            print(f"💥 增强事实表转换失败: {e}")
            raise


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Match Performance Fact Table with Governance")
    parser.add_argument("--bronze-dir", default="data/bronze/matches",
                       help="Bronze层数据目录")
    parser.add_argument("--silver-dir", default="data/silver/enhanced_facts",
                       help="Silver层输出目录")

    args = parser.parse_args()

    try:
        transformer = EnhancedFactTransformer(
            bronze_dir=args.bronze_dir,
            silver_dir=args.silver_dir
        )

        transformer.run_enhanced_transformation()
        return 0

    except Exception as e:
        print(f"💥 增强转换失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())