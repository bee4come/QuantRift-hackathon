"""
玩家数据管理器 - 异步准备和缓存Player-Pack数据

架构:
1. 用户搜索玩家后，后台立即开始拉取和计算所有agent需要的数据
2. 点击Agent卡片时，检查数据状态，等待准备完成后调用agent
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from enum import Enum

from .riot_client import riot_client
from src.core.statistical_utils import wilson_confidence_interval, winsorize
from src.utils.id_mappings import get_champion_name


class DataStatus(str, Enum):
    """数据准备状态"""
    NOT_STARTED = "not_started"
    FETCHING_MATCHES = "fetching_matches"
    FETCHING_TIMELINES = "fetching_timelines"
    CALCULATING_METRICS = "calculating_metrics"
    COMPLETED = "completed"
    FAILED = "failed"


class PlayerDataJob:
    """玩家数据准备任务"""

    def __init__(self, puuid: str, region: str, game_name: str, tag_line: str, days: int = 365):
        self.puuid = puuid
        self.region = region
        self.game_name = game_name
        self.tag_line = tag_line
        self.days = days  # 改为days而不是count
        self.status = DataStatus.NOT_STARTED
        self.progress = 0.0  # 0.0 - 1.0
        self.error: Optional[str] = None
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.player_pack: Optional[Dict[str, Any]] = None
        self.matches_data: List[Dict[str, Any]] = []  # 保存原始match数据
        self.timelines_data: List[Dict[str, Any]] = []  # 保存timeline数据供timeline_deep_dive使用

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "puuid": self.puuid,
            "region": self.region,
            "days": self.days,  # 改为days
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "has_data": self.player_pack is not None
        }


class PlayerDataManager:
    """
    玩家数据管理器

    职责:
    1. 异步拉取Riot API数据 (match + timeline)
    2. 计算metrics并生成Player-Pack格式数据
    3. 缓存结果供agent使用
    4. 提供数据状态查询接口
    """

    def __init__(self, cache_dir: Path = None):
        self.jobs: Dict[str, PlayerDataJob] = {}  # {puuid: PlayerDataJob}
        # 使用agent期望的目录结构
        self.cache_dir = cache_dir or Path("data/player_packs")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Boots item IDs (for time_to_core calculation)
        self.boots_ids = {1001, 3006, 3009, 3020, 3047, 3111, 3117, 3158}

        # ⚡ 并发控制：限制同时进行的API请求数量
        # 5个API key × 1800 req/10s = 9000 req/10s 理论上限
        # 但要考虑网络延迟，设置200并发比较合理
        self.semaphore = asyncio.Semaphore(200)

    async def prepare_player_data(
        self,
        puuid: str,
        region: str,
        game_name: str,
        tag_line: str,
        days: int = 365
    ) -> PlayerDataJob:
        """
        异步准备玩家数据

        Args:
            puuid: 玩家PUUID
            region: 服务器区域
            game_name: 游戏名称
            tag_line: 标签
            days: 拉取过去多少天的数据（默认365天）

        Returns:
            PlayerDataJob对象（后台继续处理）
        """
        # Check if there's an existing task for this player
        if puuid in self.jobs:
            job = self.jobs[puuid]
            # If task is in progress (not COMPLETED or FAILED), reuse it
            if job.status not in [DataStatus.COMPLETED, DataStatus.FAILED]:
                print(f"🔄 Task already in progress for {game_name}#{tag_line}, status: {job.status.value}")
                return job
            # If task completed with same time range within 1 minute, reuse cache
            elif (job.status == DataStatus.COMPLETED and
                  job.days == days and
                  job.completed_at and
                  (datetime.utcnow() - job.completed_at) < timedelta(minutes=1)):
                print(f"✅ Reusing recent cache for {game_name}#{tag_line} (completed {(datetime.utcnow() - job.completed_at).seconds}s ago)")
                return job

        # Create new task (always fetch latest match list from Riot API)
        print(f"🆕 Creating new data fetch task for {game_name}#{tag_line} (past {days} days)")
        job = PlayerDataJob(puuid, region, game_name, tag_line, days)
        self.jobs[puuid] = job

        # Start background task
        asyncio.create_task(self._fetch_and_calculate(job, game_name, tag_line))

        return job

    async def _fetch_and_calculate(self, job: PlayerDataJob, game_name: str, tag_line: str):
        """
        后台任务：拉取数据并计算metrics
        """
        try:
            print(f"\n🔄 Starting player data preparation: {game_name}#{tag_line}")
            print(f"   PUUID: {job.puuid[:30]}...")
            print(f"   Time range: Past {job.days} days")

            # 阶段1: 拉取match list (基于时间范围自动检测)
            job.status = DataStatus.FETCHING_MATCHES
            job.progress = 0.1

            match_ids = await self._fetch_all_match_ids(
                puuid=job.puuid,
                platform=job.region,
                days=job.days
            )

            if not match_ids:
                raise Exception(f"No matches found for {game_name}#{tag_line}")

            print(f"✅ Retrieved {len(match_ids)} matches")
            job.progress = 0.3

            # ⚡ 阶段2-A: 只拉取match details (pipeline优化第一阶段)
            job.status = DataStatus.FETCHING_MATCHES
            print(f"⚡ Pipeline optimization: Fetching matches first, timelines in background")

            matches_data = []

            # 🚀 分批并行处理matches
            batch_size = 50
            total_batches = (len(match_ids) + batch_size - 1) // batch_size

            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(match_ids))
                batch_match_ids = match_ids[start_idx:end_idx]

                import time
                batch_start = time.time()
                print(f"   📦 Batch {batch_idx + 1}/{total_batches}: Fetching {len(batch_match_ids)} matches...")

                # 并行拉取本批次的matches
                batch_tasks = [self._fetch_match(match_id, job.region) for match_id in batch_match_ids]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                batch_duration = time.time() - batch_start

                # 收集结果
                batch_success = 0
                for result in batch_results:
                    if isinstance(result, Exception):
                        print(f"      ⚠️  Skipping failed match: {result}")
                        continue
                    if result:
                        matches_data.append(result)
                        batch_success += 1

                print(f"      ✅ Batch successful {batch_success}/{len(batch_match_ids)} matches (took: {batch_duration:.1f}s)")

                # 更新进度（0.3-0.7区间）
                progress = 0.3 + (0.4 * (batch_idx + 1) / total_batches)
                job.progress = progress

            print(f"✅ Match fetch complete: {len(matches_data)} matches")
            job.progress = 0.7

            # 阶段3: 计算metrics并生成Player-Pack (使用默认time_to_core)
            job.status = DataStatus.CALCULATING_METRICS

            import time
            calc_start = time.time()
            print(f"\n⏱️  Starting metrics calculation (time_to_core using default values)...")

            player_packs = self._generate_player_pack(
                puuid=job.puuid,
                game_name=job.game_name,
                tag_line=job.tag_line,
                matches_data=matches_data,
                timelines_data=[]  # ⚡ 第一阶段不使用timeline
            )

            calc_duration = time.time() - calc_start
            print(f"⏱️  Calculation complete, took: {calc_duration:.2f} seconds")

            # ✅ 保存最新的pack到job.player_pack (用于前端显示)
            job.player_pack = player_packs[-1] if player_packs else {}
            job.matches_data = matches_data  # 💾 保存matches数据供timeline分析使用
            job.progress = 1.0
            job.status = DataStatus.COMPLETED
            job.completed_at = datetime.utcnow()

            # ✅ 保存到磁盘缓存 (agent期望的格式: packs_dir/{puuid}/pack_{patch}.json)
            player_dir = self.cache_dir / job.puuid
            player_dir.mkdir(parents=True, exist_ok=True)

            total_patches = len(player_packs)
            total_games = sum(pack['total_games'] for pack in player_packs)

            # ✅ 为每个patch保存单独文件
            for pack in player_packs:
                patch = pack['patch']
                cache_file = player_dir / f"pack_{patch}.json"

                # ✅ 只有当新数据 >= 现有数据时才覆盖（防止小count请求覆盖大数据集）
                should_save = True
                if cache_file.exists():
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            existing_pack = json.load(f)
                        existing_games = existing_pack.get('total_games', 0)
                        new_games = pack['total_games']

                        if new_games < existing_games:
                            should_save = False
                            print(f"⏭️  Skipping save pack_{patch}.json: Existing data more complete ({existing_games} games vs {new_games} games)")
                    except Exception as e:
                        print(f"⚠️  Cannot read existing pack_{patch}.json, will overwrite: {e}")

                if should_save:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(pack, f, indent=2, ensure_ascii=False)
                    print(f"✅ Saved pack_{patch}.json: {pack['total_games']} games")

            # Save matches_data to disk for Timeline Deep Dive
            matches_file = player_dir / "matches_data.json"
            try:
                with open(matches_file, 'w', encoding='utf-8') as f:
                    json.dump(matches_data, f, indent=2, ensure_ascii=False)
                print(f"✅ Saved matches_data.json: {len(matches_data)} match details")
            except Exception as e:
                print(f"⚠️  Failed to save matches_data.json: {e}")

            print(f"✅ Data preparation complete (phase 1): {game_name}#{tag_line}")
            print(f"   Total games: {total_games}")
            print(f"   Patches: {total_patches}")
            print(f"   Cache location: {player_dir}")
            print(f"   ⚡ 65% of agents can now use the data")

            # ⚡ 阶段2-B: 后台拉取timelines并更新time_to_core
            print(f"\n🔄 Starting background task: Fetching timelines...")
            asyncio.create_task(
                self._fetch_timelines_background(
                    match_ids=match_ids,
                    region=job.region,
                    puuid=job.puuid,
                    player_dir=player_dir
                )
            )

        except Exception as e:
            print(f"❌ Data preparation failed: {e}")
            job.status = DataStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()

    async def _fetch_all_match_ids(self, puuid: str, platform: str, days: int = 365) -> List[str]:
        """根据时间范围拉取所有match IDs，突破count限制

        Args:
            puuid: Player PUUID
            platform: Platform code (e.g., 'na1')
            days: 过去多少天（默认365天）

        Returns:
            List of match IDs within the time range
        """
        from datetime import datetime, timedelta

        # 计算时间范围（Unix时间戳，秒）
        end_time = int(datetime.utcnow().timestamp())
        start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp())

        print(f"   📅 Time range: Past {days} days")
        print(f"   🕐 Start: {datetime.fromtimestamp(start_time)}")
        print(f"   🕐 End: {datetime.fromtimestamp(end_time)}")

        all_match_ids = []
        start_index = 0
        batch_size = 100  # Riot API单次最多返回100场

        while True:
            print(f"   📥 Fetching matches {start_index}-{start_index + batch_size}...")

            # 使用时间范围查询
            batch = await riot_client.get_match_history(
                puuid=puuid,
                platform=platform,
                count=batch_size,
                start=start_index,
                start_time=start_time,  # 添加时间过滤
                end_time=end_time,
                queue_id=420  # Ranked Solo/Duo
            )

            if not batch or len(batch) == 0:
                # 没有更多比赛了
                print(f"   ✅ All available matches fetched: {len(all_match_ids)} matches")
                break

            all_match_ids.extend(batch)
            print(f"   ✅ Batch retrieved {len(batch)} matches, total {len(all_match_ids)} matches")

            # 如果返回数量少于请求数量，说明已经到末尾了
            if len(batch) < batch_size:
                print(f"   ℹ️  Reached end of player match history")
                break

            start_index += len(batch)

        return all_match_ids

    async def _fetch_match(self, match_id: str, platform: str):
        """只拉取单场match details (pipeline优化第一阶段)

        Args:
            match_id: Match ID
            platform: Platform code (e.g., 'na1'), will be converted to regional routing internally
        """
        try:
            # Convert platform to regional routing
            PLATFORM_TO_REGION = {
                "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
                "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
                "kr": "asia", "jp1": "asia",
                "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea",
            }
            region = PLATFORM_TO_REGION.get(platform.lower(), "americas")

            # ⚡ 使用信号量控制并发
            async with self.semaphore:
                match_data = await riot_client.get_match_details(match_id=match_id, region=region)
                return match_data

        except Exception as e:
            print(f"⚠️  Failed to fetch match {match_id}: {e}")
            return None

    async def _fetch_timeline(self, match_id: str, platform: str):
        """只拉取单场timeline (pipeline优化第二阶段)

        Args:
            match_id: Match ID
            platform: Platform code (e.g., 'na1'), will be converted to regional routing internally
        """
        try:
            # Convert platform to regional routing
            PLATFORM_TO_REGION = {
                "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
                "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
                "kr": "asia", "jp1": "asia",
                "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea",
            }
            region = PLATFORM_TO_REGION.get(platform.lower(), "americas")

            # ⚡ 使用信号量控制并发
            async with self.semaphore:
                timeline_data = await riot_client.get_match_timeline(match_id=match_id, region=region)
                return timeline_data

        except Exception as e:
            print(f"⚠️  Failed to fetch timeline {match_id}: {e}")
            return None

    def _generate_player_pack(
        self,
        puuid: str,
        game_name: str,
        tag_line: str,
        matches_data: List[Dict],
        timelines_data: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        从match和timeline数据生成Player-Pack

        Returns:
            {
                "puuid": str,
                "generation_timestamp": str,
                "total_games": int,
                "by_cr": [
                    {
                        "champ_id": int,
                        "role": str,
                        "games": int,
                        "wins": int,
                        "losses": int,
                        "p_hat": float,
                        "p_hat_ci": [lower, upper],
                        "kda_adj": float,
                        "obj_rate": float,
                        "cp_25": float,
                        "build_core": [item_ids],
                        "avg_time_to_core": float,
                        "rune_keystone": int,
                        "effective_n": int,
                        "governance_tag": str
                    }
                ]
            }
        """
        import time
        t0 = time.time()

        # 创建timeline映射
        timelines_map = {t['metadata']['matchId']: t for t in timelines_data}
        print(f"     ⏱️  Creating timeline mapping: {time.time()-t0:.3f}s")

        # ✅ 按(patch, champ_id, role)聚合数据
        patch_cr_data = defaultdict(lambda: defaultdict(list))

        # 📊 添加过滤统计
        filter_stats = {
            'total_matches': len(matches_data),
            'player_not_found': 0,
            'invalid_role': 0,
            'processed': 0
        }

        # 🔍 记录前3个被过滤的match（用于调试）
        filtered_matches_debug = []

        t1 = time.time()
        for match in matches_data:
            match_id = match['metadata']['matchId']
            timeline = timelines_map.get(match_id)

            # ✅ 提取patch版本
            game_version = match['info'].get('gameVersion', '0.0.0.0')
            patch = '.'.join(game_version.split('.')[:2])  # "15.1.123.456" → "15.1"

            # 🔄 改用gameName#tagLine匹配（更可靠）
            player_data = None
            for p in match['info']['participants']:
                # 同时支持PUUID和gameName#tagLine匹配
                puuid_match = p.get('puuid') == puuid
                # Case-insensitive name matching (Riot API may return different casing)
                name_match = (p.get('riotIdGameName', '').lower() == game_name.lower() and
                             p.get('riotIdTagline', '').lower() == tag_line.lower())

                if puuid_match or name_match:
                    player_data = p
                    break

            if not player_data:
                filter_stats['player_not_found'] += 1
                # 🔍 记录前3个被过滤的match用于调试
                if len(filtered_matches_debug) < 3:
                    filtered_matches_debug.append({
                        'match_id': match_id,
                        'reason': 'player_not_found',
                        'queue_id': match['info'].get('queueId'),
                        'target': f'{game_name}#{tag_line}',
                        'participants_names': [f"{p.get('riotIdGameName', '?')}#{p.get('riotIdTagline', '?')}"
                                              for p in match['info']['participants'][:3]]
                    })
                continue

            champ_id = player_data['championId']
            role = player_data['teamPosition']

            if not role or role == 'Invalid':
                filter_stats['invalid_role'] += 1
                continue

            # 提取单场统计
            game_stats = self._extract_game_stats(
                player_data=player_data,
                match_data=match,
                timeline_data=timeline
            )

            # ✅ 按(patch, champ_id, role)存储
            key = (champ_id, role)
            patch_cr_data[patch][key].append(game_stats)
            filter_stats['processed'] += 1

        print(f"     ⏱️  Data extraction loop ({len(matches_data)} matches): {time.time()-t1:.3f}s")
        print(f"     📊 Filter statistics:")
        print(f"        - Total matches: {filter_stats['total_matches']}")
        print(f"        - Player not found: {filter_stats['player_not_found']}")
        print(f"        - Invalid role: {filter_stats['invalid_role']}")
        print(f"        - ✅ Successfully processed: {filter_stats['processed']}")

        # 🔍 输出玩家匹配调试信息
        if filtered_matches_debug:
            print(f"     🔍 Debug: First {len(filtered_matches_debug)} filtered matches player name comparison:")
            print(f"        Target player: {game_name}#{tag_line}")
            for i, fm in enumerate(filtered_matches_debug, 1):
                print(f"        Match {i} (ID: {fm['match_id'][:20]}..., QueueID: {fm['queue_id']}):")
                print(f"          Participant sample: {fm['participants_names']}")

        # ✅ 为每个patch生成一个pack
        t2 = time.time()
        packs = []

        for patch, cr_data in sorted(patch_cr_data.items()):
            # 计算每个(champ_id, role)的聚合metrics
            by_cr = []

            for (champ_id, role), games_stats in cr_data.items():
                if not games_stats:
                    continue

                games = len(games_stats)
                wins = sum(1 for g in games_stats if g['win'])
                losses = games - wins

                # Win rate with Wilson CI
                p_hat = wins / games if games > 0 else 0.0
                _, ci_lower, ci_upper = wilson_confidence_interval(wins, games)

                # KDA adjusted (winsorized)
                kda_values = [g['kda_adj'] for g in games_stats]
                kda_winsorized = winsorize(kda_values)
                kda_adj = np.mean(kda_winsorized) if kda_winsorized else 0.0

                # Objective rate
                obj_rate = np.mean([g['obj_rate'] for g in games_stats])

                # Combat power at 25min
                cp_25 = np.mean([g['cp_25'] for g in games_stats])

                # Build core: most common items
                item_counts = defaultdict(int)
                for g in games_stats:
                    for item_id in g['items_at_25']:
                        item_counts[item_id] += 1
                build_core = sorted(item_counts.keys(), key=lambda x: item_counts[x], reverse=True)[:3]

                # Average time to core
                avg_time_to_core = np.mean([g['time_to_core'] for g in games_stats])

                # Most common rune keystone
                rune_counts = defaultdict(int)
                for g in games_stats:
                    rune_counts[g['rune_keystone']] += 1
                rune_keystone = max(rune_counts.keys(), key=lambda x: rune_counts[x]) if rune_counts else 0

                # Governance tag
                if games >= 100:
                    governance_tag = "CONFIDENT"
                elif games >= 30:
                    governance_tag = "CAUTION"
                else:
                    governance_tag = "CONTEXT"

                by_cr.append({
                    "champ_id": champ_id,
                    "role": role,
                    "games": games,
                    "wins": wins,
                    "losses": losses,
                    "p_hat": round(p_hat, 4),
                    "p_hat_ci": [round(ci_lower, 4), round(ci_upper, 4)],
                    "kda_adj": round(kda_adj, 2),
                    "obj_rate": round(obj_rate, 3),
                    "cp_25": round(cp_25, 1),
                    "build_core": build_core,
                    "avg_time_to_core": round(avg_time_to_core, 2),
                    "rune_keystone": rune_keystone,
                    "effective_n": games,
                    "governance_tag": governance_tag
                })

            # ✅ 创建该patch的pack
            pack = {
                "puuid": puuid,
                "patch": patch,  # ✅ 真实patch版本
                "generation_timestamp": datetime.utcnow().isoformat(),
                "total_games": sum(entry['games'] for entry in by_cr),
                "by_cr": by_cr
            }
            packs.append(pack)

        print(f"     ⏱️  Aggregation calculation + Pack generation: {time.time()-t2:.3f}s")

        return packs

    def _extract_game_stats(
        self,
        player_data: Dict,
        match_data: Dict,
        timeline_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """从单场比赛提取统计数据"""
        # Basic stats
        win = player_data['win']
        kills = player_data['kills']
        deaths = player_data['deaths']
        assists = player_data['assists']

        # KDA adjusted
        kda_adj = (kills + 0.7 * assists) / (deaths + 1)

        # Objective participation rate
        team_baron = player_data.get('challenges', {}).get('teamBaronKills', 1)
        obj_rate = (
            player_data.get('baronKills', 0) +
            player_data.get('dragonKills', 0) +
            player_data.get('turretKills', 0)
        ) / max(1, team_baron)

        # Combat power at 25min (proxy)
        game_duration_min = match_data['info']['gameDuration'] / 60.0
        gold_earned = player_data['goldEarned']
        cp_25 = (gold_earned / game_duration_min * 25) if game_duration_min > 0 else gold_earned

        # Items at end
        items_at_25 = [
            player_data.get(f'item{i}', 0)
            for i in range(6)
            if player_data.get(f'item{i}', 0) != 0
        ]

        # Time to core
        time_to_core = 30.0  # default
        if timeline_data:
            time_to_core = self._calculate_time_to_core(
                timeline_data,
                player_data['participantId']
            )

        # Rune keystone
        rune_keystone = player_data['perks']['styles'][0]['selections'][0]['perk']

        return {
            'win': win,
            'kills': kills,
            'deaths': deaths,
            'assists': assists,
            'kda_adj': kda_adj,
            'obj_rate': obj_rate,
            'cp_25': cp_25,
            'items_at_25': items_at_25,
            'time_to_core': time_to_core,
            'rune_keystone': rune_keystone,
            'game_duration': game_duration_min
        }

    def _calculate_time_to_core(self, timeline_data: Dict, participant_id: int) -> float:
        """计算time to core (minutes)"""
        core_items_found = []

        for frame in timeline_data.get('info', {}).get('frames', []):
            timestamp_min = frame['timestamp'] / 60000.0

            for event in frame.get('events', []):
                if event.get('type') == 'ITEM_PURCHASED' and event.get('participantId') == participant_id:
                    item_id = event.get('itemId', 0)

                    if item_id not in self.boots_ids and item_id > 2000:
                        if item_id not in [item['id'] for item in core_items_found]:
                            core_items_found.append({'id': item_id, 'time': timestamp_min})

                            if len(core_items_found) >= 2:
                                return core_items_found[1]['time']

        # 未找到2件核心装备
        if timeline_data['info']['frames']:
            return timeline_data['info']['frames'][-1]['timestamp'] / 60000.0
        return 30.0

    def get_status(self, puuid: str) -> Dict[str, Any]:
        """获取数据准备状态"""
        if puuid not in self.jobs:
            return {"status": DataStatus.NOT_STARTED}

        return self.jobs[puuid].to_dict()

    async def wait_for_data(self, puuid: str, timeout: int = 120) -> Optional[Dict[str, Any]]:
        """
        等待数据准备完成

        Args:
            puuid: 玩家PUUID
            timeout: 超时时间（秒）

        Returns:
            Player-Pack数据，或None（如果失败/超时）
        """
        if puuid not in self.jobs:
            return None

        job = self.jobs[puuid]

        # 如果已经完成，直接返回
        if job.status == DataStatus.COMPLETED and job.player_pack:
            return job.player_pack

        # 等待完成
        for _ in range(timeout):
            if job.status == DataStatus.COMPLETED:
                return job.player_pack
            elif job.status == DataStatus.FAILED:
                return None

            await asyncio.sleep(1)

        # 超时
        print(f"⚠️  Data wait timeout: {puuid}")
        return None

    def get_data(self, puuid: str) -> Optional[Dict[str, Any]]:
        """
        获取准备好的数据（同步，不等待）

        Returns:
            Player-Pack数据，或None
        """
        if puuid not in self.jobs:
            # 尝试从磁盘缓存加载
            cache_file = self.cache_dir / puuid / "pack_current.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None

        job = self.jobs[puuid]
        return job.player_pack if job.status == DataStatus.COMPLETED else None

    def get_packs_dir(self, puuid: str) -> Optional[str]:
        """
        获取player packs目录路径（给agent使用）

        Returns:
            packs_dir路径，或None
        """
        player_dir = self.cache_dir / puuid
        if player_dir.exists():
            return str(player_dir)
        return None

    def get_role_stats(self, puuid: str) -> List[Dict[str, Any]]:
        """
        从Player-Pack中提取role统计数据（优先从summary.json，否则聚合所有pack文件）

        Returns:
            [
                {"role": "TOP", "games": 10, "wins": 6, "win_rate": 60.0, "avg_kda": 3.5},
                ...
            ]
        """
        player_dir = self.cache_dir / puuid

        if not player_dir.exists():
            return []

        try:
            # 先尝试从summary.json读取
            summary_file = player_dir / "summary.json"
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                by_cr_data = summary.get("by_cr", [])
            else:
                # 如果summary不存在，从所有pack_*.json文件聚合
                by_cr_data = []
                pack_files = sorted(player_dir.glob("pack_*.json"))
                for pack_file in pack_files:
                    with open(pack_file, 'r', encoding='utf-8') as f:
                        pack = json.load(f)
                        by_cr_data.extend(pack.get("by_cr", []))

            if not by_cr_data:
                return []

            # 从 by_cr 聚合 role 统计
            role_stats_dict = defaultdict(lambda: {
                "games": 0,
                "wins": 0,
                "total_kda": 0.0
            })

            for cr in by_cr_data:
                role = cr.get("role", "UNKNOWN")
                role_stats_dict[role]["games"] += cr.get("games", 0)
                role_stats_dict[role]["wins"] += cr.get("wins", 0)

                # 使用 kda_adj * games 作为加权KDA
                if "kda_adj" in cr:
                    role_stats_dict[role]["total_kda"] += cr["kda_adj"] * cr.get("games", 0)

            # 转换为数组格式
            role_stats = []
            for role, stats in role_stats_dict.items():
                games = stats["games"]
                wins = stats["wins"]
                win_rate = (wins / games * 100) if games > 0 else 0
                avg_kda = (stats["total_kda"] / games) if games > 0 else 0

                role_stats.append({
                    "role": role,
                    "games": games,
                    "wins": wins,
                    "win_rate": round(win_rate, 1),
                    "avg_kda": round(avg_kda, 2)
                })

            # 按游戏数排序
            role_stats.sort(key=lambda x: x["games"], reverse=True)
            return role_stats

        except Exception as e:
            print(f"⚠️  Failed to get role stats: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_best_champions(self, puuid: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        从Player-Pack中提取最佳英雄数据（按游戏数排序）

        Returns:
            [
                {"champ_id": 202, "games": 50, "wins": 30, "win_rate": 60.0, "avg_kda": 3.5},
                ...
            ]
        """
        player_dir = self.cache_dir / puuid
        if not player_dir.exists():
            return []

        try:
            # 聚合所有pack文件中的champion数据
            champion_stats = defaultdict(lambda: {
                "games": 0,
                "wins": 0,
                "total_kda": 0.0
            })

            pack_files = sorted(player_dir.glob("pack_*.json"))
            for pack_file in pack_files:
                with open(pack_file, 'r', encoding='utf-8') as f:
                    pack = json.load(f)
                    by_cr_data = pack.get("by_cr", [])

                    for cr in by_cr_data:
                        champ_id = cr.get("champ_id")
                        if not champ_id:
                            continue

                        games = cr.get("games", 0)
                        wins = cr.get("wins", 0)
                        kda_adj = cr.get("kda_adj", 0)

                        champion_stats[champ_id]["games"] += games
                        champion_stats[champ_id]["wins"] += wins
                        champion_stats[champ_id]["total_kda"] += kda_adj * games

            # 转换为数组格式
            best_champions = []
            for champ_id, stats in champion_stats.items():
                games = stats["games"]
                wins = stats["wins"]
                win_rate = (wins / games * 100) if games > 0 else 0
                avg_kda = (stats["total_kda"] / games) if games > 0 else 0

                # 获取英雄名称
                champion_name = get_champion_name(champ_id)

                best_champions.append({
                    "champ_id": champ_id,
                    "name": champion_name,
                    "games": games,
                    "wins": wins,
                    "win_rate": round(win_rate, 1),
                    "avg_kda": round(avg_kda, 2)
                })

            # 按游戏数排序，返回前N个
            best_champions.sort(key=lambda x: x["games"], reverse=True)
            return best_champions[:limit]

        except Exception as e:
            print(f"⚠️  Failed to get best champions: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_recent_matches(self, puuid: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近的比赛列表（用于timeline分析）

        优先返回有timeline文件的matches

        Args:
            puuid: 玩家PUUID
            limit: 返回数量限制

        Returns:
            List[Dict]: 比赛信息列表
        """
        try:
            # 检查timeline目录，获取有timeline文件的match_ids
            player_dir = self.cache_dir / puuid
            timelines_dir = player_dir / "timelines"

            available_match_ids = set()
            if timelines_dir.exists():
                for timeline_file in timelines_dir.glob("*_timeline.json"):
                    match_id = timeline_file.stem.replace("_timeline", "")
                    available_match_ids.add(match_id)

            # Get matches data from job (memory) or matches_data.json (disk)
            job = self.jobs.get(puuid)
            matches_data = None

            if job and job.matches_data:
                # Use in-memory data if available
                matches_data = job.matches_data
            else:
                # Try to load from disk cache
                matches_file = player_dir / "matches_data.json"
                if matches_file.exists():
                    try:
                        with open(matches_file, 'r', encoding='utf-8') as f:
                            matches_data = json.load(f)
                        print(f"✅ Loaded matches_data.json from disk: {len(matches_data)} matches")
                    except Exception as e:
                        print(f"⚠️  Failed to load matches_data.json: {e}")

            # If no matches data available, return empty list
            if not matches_data:
                print(f"⚠️  No matches data available for {puuid}")
                return []

            # Convert to frontend format, only include matches with timeline files
            matches = []
            for match in matches_data:
                try:
                    # 提取基础信息
                    match_id = match['metadata']['matchId']

                    # 🔍 只返回有timeline文件的matches
                    if match_id not in available_match_ids:
                        continue

                    game_creation = match['info']['gameCreation']
                    game_duration = match['info']['gameDuration']

                    # 找到当前玩家的数据
                    participants = match['info']['participants']
                    player_data = None
                    for participant in participants:
                        if participant.get('puuid') == puuid:
                            player_data = participant
                            break

                    if not player_data:
                        continue

                    # 提取玩家数据
                    champion_id = player_data.get('championId', 0)
                    champion_name = get_champion_name(champion_id)
                    role = player_data.get('teamPosition', 'UNKNOWN')
                    win = player_data.get('win', False)
                    kills = player_data.get('kills', 0)
                    deaths = player_data.get('deaths', 0)
                    assists = player_data.get('assists', 0)

                    matches.append({
                        'match_id': match_id,
                        'game_creation': game_creation,
                        'game_duration': game_duration,
                        'champion_id': champion_id,
                        'champion_name': champion_name,
                        'role': role,
                        'win': win,
                        'kills': kills,
                        'deaths': deaths,
                        'assists': assists
                    })

                except Exception as e:
                    print(f"⚠️  Failed to parse match: {e}")
                    continue

            return matches

        except Exception as e:
            print(f"⚠️  Failed to get recent matches: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _fetch_timelines_background(
        self,
        match_ids: List[str],
        region: str,
        puuid: str,
        player_dir: Path
    ):
        """
        后台任务：拉取timelines并更新time_to_core

        这个任务在第一阶段完成后运行，不阻塞agent使用数据
        """
        try:
            import time
            bg_start = time.time()
            print(f"\n🔄 Background task started: Fetching {len(match_ids)} timelines")

            timelines_data = []

            # 分批拉取timelines
            batch_size = 50
            total_batches = (len(match_ids) + batch_size - 1) // batch_size

            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(match_ids))
                batch_match_ids = match_ids[start_idx:end_idx]

                batch_start = time.time()
                print(f"   📦 Background batch {batch_idx + 1}/{total_batches}: Fetching {len(batch_match_ids)} timelines...")

                # 并行拉取本批次的timelines
                batch_tasks = [self._fetch_timeline(match_id, region) for match_id in batch_match_ids]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                batch_duration = time.time() - batch_start

                # 收集结果
                batch_success = 0
                for result in batch_results:
                    if isinstance(result, Exception):
                        continue
                    if result:
                        timelines_data.append(result)
                        batch_success += 1

                print(f"      ✅ Background batch successful {batch_success}/{len(batch_match_ids)} timelines (took: {batch_duration:.1f}s)")

            bg_duration = time.time() - bg_start
            print(f"✅ Background timeline fetch complete: {len(timelines_data)} timelines (total time: {bg_duration:.1f}s)")

            # 保存timeline数据到job（供API使用）
            job = self.jobs.get(puuid)
            if job:
                job.timelines_data = timelines_data
                print(f"💾 Timeline data saved to job: {len(timelines_data)} timelines")

            # 保存timeline数据到磁盘（供timeline_deep_dive agent使用）
            timelines_dir = player_dir / "timelines"
            timelines_dir.mkdir(exist_ok=True)

            saved_count = 0
            skipped_count = 0  # 🛡️ 统计被过滤的timeline数量

            for timeline in timelines_data:
                try:
                    match_id = timeline['metadata']['matchId']
                    participants = timeline['metadata']['participants']

                    # 🛡️ 【关键验证】：只保存包含目标玩家的timeline
                    if puuid not in participants:
                        skipped_count += 1
                        print(f"⚠️  Skipping timeline {match_id}: Does not contain target player")
                        print(f"     Target PUUID: {puuid[:40]}...")
                        print(f"     First participant: {participants[0][:40]}...")
                        continue

                    # ✅ 验证通过，保存timeline
                    timeline_file = timelines_dir / f"{match_id}_timeline.json"
                    with open(timeline_file, 'w', encoding='utf-8') as f:
                        json.dump(timeline, f, indent=2, ensure_ascii=False)
                    saved_count += 1

                except Exception as e:
                    print(f"⚠️  Failed to save timeline: {e}")

            print(f"💾 Timeline files saved to disk: {saved_count}/{len(timelines_data)} timelines")
            if skipped_count > 0:
                print(f"🛡️ Data security: Filtered out {skipped_count} timelines not belonging to target player")

            # 更新player packs中的time_to_core
            print(f"🔄 Updating time_to_core...")
            await self._update_time_to_core(puuid, player_dir, timelines_data)
            print(f"✅ Background task complete, timeline_deep_dive agent can now use full data")

        except Exception as e:
            print(f"⚠️  Background timeline fetch failed (does not affect other agents): {e}")

    async def _update_time_to_core(
        self,
        puuid: str,
        player_dir: Path,
        timelines_data: List[Dict]
    ):
        """
        更新已保存的player packs，用真实的time_to_core替换默认值
        """
        try:
            # 创建timeline映射: match_id -> timeline_data
            timelines_map = {t['metadata']['matchId']: t for t in timelines_data}
            print(f"   📊 Available timeline data: {len(timelines_map)} timelines")

            # 从job中获取原始matches_data
            job = self.jobs.get(puuid)
            if not job or not job.matches_data:
                print(f"   ⚠️  Original match data not found, cannot update time_to_core")
                return

            matches_data = job.matches_data
            print(f"   📊 Available match data: {len(matches_data)} matches")

            # 为每场比赛计算真实的time_to_core
            match_time_to_core = {}  # {match_id: {participant_id: time_to_core}}

            for match_data in matches_data:
                match_id = match_data['metadata']['matchId']
                if match_id not in timelines_map:
                    continue  # 没有timeline数据，跳过

                timeline_data = timelines_map[match_id]

                # 为这场比赛的每个玩家计算time_to_core
                for participant in match_data['info']['participants']:
                    if participant['puuid'] != puuid:
                        continue  # 只处理目标玩家

                    participant_id = participant['participantId']
                    time_to_core = self._calculate_time_to_core(timeline_data, participant_id)

                    if match_id not in match_time_to_core:
                        match_time_to_core[match_id] = {}
                    match_time_to_core[match_id][participant_id] = time_to_core

            print(f"   ✅ Calculation complete: {len(match_time_to_core)} matches time_to_core")

            # 更新每个pack文件
            updated_packs = 0
            for pack_file in player_dir.glob("pack_*.json"):
                with open(pack_file, 'r', encoding='utf-8') as f:
                    pack = json.load(f)

                # 重新聚合time_to_core（按champion-role分组）
                cr_time_to_core = defaultdict(list)  # {(champ_id, role): [time_to_core_values]}

                for match_data in matches_data:
                    match_id = match_data['metadata']['matchId']
                    game_version = match_data['info']['gameVersion']
                    patch = '.'.join(game_version.split('.')[:2])

                    # 只处理当前pack的patch
                    if patch != pack['patch']:
                        continue

                    if match_id not in match_time_to_core:
                        continue

                    for participant in match_data['info']['participants']:
                        if participant['puuid'] != puuid:
                            continue

                        champ_id = participant['championId']
                        role = participant.get('teamPosition', 'UTILITY')
                        participant_id = participant['participantId']

                        if participant_id in match_time_to_core[match_id]:
                            time_to_core = match_time_to_core[match_id][participant_id]
                            cr_time_to_core[(champ_id, role)].append(time_to_core)

                # 更新pack中的avg_time_to_core
                modified = False
                for cr_entry in pack.get('by_cr', []):
                    champ_id = cr_entry['champ_id']
                    role = cr_entry['role']

                    if (champ_id, role) in cr_time_to_core:
                        times = cr_time_to_core[(champ_id, role)]
                        avg_time = np.mean(times)
                        old_time = cr_entry.get('avg_time_to_core', 30.0)
                        cr_entry['avg_time_to_core'] = round(avg_time, 2)

                        if abs(avg_time - old_time) > 0.1:  # 有实质性变化
                            modified = True

                # 如果有修改，保存pack文件
                if modified:
                    with open(pack_file, 'w', encoding='utf-8') as f:
                        json.dump(pack, f, indent=2, ensure_ascii=False)
                    updated_packs += 1
                    print(f"   ✅ Updated {pack_file.name}: avg_time_to_core updated")

            print(f"   ✅ Background update complete: {updated_packs} pack files updated")

        except Exception as e:
            print(f"⚠️  Failed to update time_to_core: {e}")
            import traceback
            traceback.print_exc()


# 全局单例
player_data_manager = PlayerDataManager()
