"""
Data Auto Fetcher - 数据自动拉取混入类

让Agent能够自动检测、拉取和处理所需数据
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from datetime import datetime


class DataAutoFetcher:
    """
    数据自动拉取混入类

    Agent继承此类后，可以自动：
    1. 检测数据是否存在
    2. 拉取缺失的数据
    3. 转换数据格式
    4. 推断参数

    Example:
        class MyAgent(DataAutoFetcher):
            def run(self, player_id: str = None, packs_dir: str = None, **kwargs):
                # 自动处理数据
                packs_dir, params = self._ensure_data(
                    player_id=player_id,
                    packs_dir=packs_dir,
                    required_format='packs'
                )

                # 使用数据进行分析
                ...
    """

    def __init__(self):
        # 从环境变量读取API keys
        self.api_keys = [
            os.getenv("RIOT_API_KEY"),
            os.getenv("RIOT_API_KEY_SECONDARY"),
            os.getenv("RIOT_API_KEY_TERTIARY"),
            os.getenv("RIOT_API_KEY_ALT")
        ]
        self.api_keys = [k for k in self.api_keys if k]
        self.current_api_key_index = 0

    def _ensure_data(
        self,
        player_id: Optional[str] = None,
        packs_dir: Optional[str] = None,
        matches_dir: Optional[str] = None,
        required_format: str = 'packs',
        region: str = 'na1',
        max_matches: int = 200,
        auto_fetch: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        确保数据存在，如果不存在则自动拉取

        Args:
            player_id: 玩家ID (格式: "GameName#TAG" 或 PUUID)
            packs_dir: Pack文件目录
            matches_dir: 原始match目录
            required_format: 需要的数据格式 ('packs', 'matches', 'both')
            region: 地区
            max_matches: 最多拉取对局数
            auto_fetch: 是否自动拉取（False则只检查）

        Returns:
            (data_dir, player_params) - 数据目录和玩家参数
        """
        print(f"\n🔍 数据依赖检查...")

        # 场景1: 提供了packs_dir且存在
        if packs_dir and Path(packs_dir).exists():
            pack_files = list(Path(packs_dir).glob('pack_*.json'))
            if pack_files:
                print(f"   ✅ 找到现有Pack数据: {len(pack_files)}个文件")
                params = self._analyze_packs(Path(packs_dir))
                return packs_dir, params

        # 场景2: 提供了matches_dir且存在，需要转换
        if matches_dir and Path(matches_dir).exists():
            match_files = list(Path(matches_dir).glob('*.json'))
            if match_files and required_format in ['packs', 'both']:
                print(f"   ⚠️ 找到原始match数据({len(match_files)}个)，但需要Pack格式")
                if auto_fetch:
                    # 自动转换
                    packs_dir = str(Path(matches_dir).parent / 'packs')
                    puuid = self._extract_puuid_from_matches(Path(matches_dir))
                    self._convert_matches_to_packs(Path(matches_dir), puuid, Path(packs_dir))
                    params = self._analyze_packs(Path(packs_dir))
                    return packs_dir, params

        # 场景3: 提供了player_id，需要从头拉取
        if player_id and auto_fetch:
            print(f"   ⚠️ 未找到数据，自动拉取: {player_id}")
            return self._fetch_all_data(player_id, region, max_matches, required_format)

        # 场景4: 无法自动处理
        raise ValueError(
            f"无法获取数据。请提供以下之一:\n"
            f"  1. packs_dir - 已存在的Pack数据目录\n"
            f"  2. matches_dir - 原始match数据目录\n"
            f"  3. player_id - 玩家ID (将自动拉取数据)\n"
            f"  设置 auto_fetch=True 启用自动拉取"
        )

    def _fetch_all_data(
        self,
        player_id: str,
        region: str,
        max_matches: int,
        required_format: str
    ) -> Tuple[str, Dict[str, Any]]:
        """完整的数据拉取流程"""
        print(f"\n🚀 开始自动数据拉取...")

        # 解析player_id
        if '#' in player_id:
            game_name, tag_line = player_id.split('#', 1)
            puuid = self._lookup_player(game_name, tag_line, region)
        else:
            puuid = player_id  # 假设直接提供了PUUID

        # 创建输出目录
        output_dir = Path(f"data/auto_fetch/{game_name}_{tag_line}")
        matches_dir = output_dir / "matches"
        packs_dir = output_dir / "packs"
        matches_dir.mkdir(parents=True, exist_ok=True)
        packs_dir.mkdir(parents=True, exist_ok=True)

        # 拉取对局数据
        match_ids = self._fetch_match_ids(puuid, region, max_matches)
        self._fetch_matches(match_ids, region, matches_dir)

        # 转换为Pack格式
        if required_format in ['packs', 'both']:
            self._convert_matches_to_packs(matches_dir, puuid, packs_dir)
            params = self._analyze_packs(packs_dir)
            return str(packs_dir), params
        else:
            return str(matches_dir), {}

    def _lookup_player(self, game_name: str, tag_line: str, region: str) -> str:
        """查询玩家PUUID"""
        print(f"   🔍 查询玩家: {game_name}#{tag_line}")

        cluster = self._get_cluster(region)
        url = f"https://{cluster}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

        data = self._api_request(url)
        if data and 'puuid' in data:
            print(f"      ✅ PUUID: {data['puuid']}")
            return data['puuid']
        else:
            raise ValueError(f"未找到玩家: {game_name}#{tag_line}")

    def _fetch_match_ids(self, puuid: str, region: str, count: int) -> List[str]:
        """拉取对局ID列表"""
        print(f"   📥 拉取对局列表 (最多{count}场)...")

        cluster = self._get_cluster(region)
        url = f"https://{cluster}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        url += f"?type=ranked&count={count}"

        match_ids = self._api_request(url)
        if match_ids:
            print(f"      ✅ 找到 {len(match_ids)} 场")
            return match_ids
        else:
            raise ValueError("未找到对局")

    def _fetch_matches(self, match_ids: List[str], region: str, output_dir: Path):
        """拉取对局详情"""
        print(f"   📥 拉取对局详情...")

        cluster = self._get_cluster(region)
        fetched = 0

        for i, match_id in enumerate(match_ids, 1):
            if i % 20 == 0:
                print(f"      进度: {i}/{len(match_ids)}")

            match_file = output_dir / f"{match_id}.json"
            if match_file.exists():
                fetched += 1
                continue

            url = f"https://{cluster}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            data = self._api_request(url)

            if data:
                with open(match_file, 'w') as f:
                    json.dump(data, f)
                fetched += 1

            time.sleep(0.05)

        print(f"      ✅ 成功 {fetched}/{len(match_ids)}")

    def _convert_matches_to_packs(self, matches_dir: Path, puuid: str, output_dir: Path):
        """转换match数据为Pack格式"""
        print(f"   🔄 转换为Pack格式...")

        # 按补丁分组
        matches_by_patch = {}

        for match_file in matches_dir.glob("*.json"):
            with open(match_file) as f:
                match = json.load(f)

            # 找到玩家数据
            player_data = None
            for p in match['info']['participants']:
                if p['puuid'] == puuid:
                    player_data = p
                    break

            if not player_data:
                continue

            # 提取补丁版本
            game_version = match['info']['gameVersion']
            patch = '.'.join(game_version.split('.')[:2])

            if patch not in matches_by_patch:
                matches_by_patch[patch] = []

            matches_by_patch[patch].append({
                'champion_id': player_data['championId'],
                'role': player_data['teamPosition'] or 'UNKNOWN',
                'win': player_data['win'],
                'kills': player_data['kills'],
                'deaths': player_data['deaths'],
                'assists': player_data['assists'],
                'damage': player_data['totalDamageDealtToChampions'],
                'gold': player_data['goldEarned'],
                'cs': player_data['totalMinionsKilled'] + player_data['neutralMinionsKilled']
            })

        # 生成Pack文件
        output_dir.mkdir(parents=True, exist_ok=True)

        for patch, matches in sorted(matches_by_patch.items()):
            by_cr = {}
            for match in matches:
                key = (match['champion_id'], match['role'])
                if key not in by_cr:
                    by_cr[key] = {
                        'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0,
                        'assists': 0, 'damage': 0, 'gold': 0, 'cs': 0
                    }

                stats = by_cr[key]
                stats['games'] += 1
                stats['wins'] += 1 if match['win'] else 0
                stats['kills'] += match['kills']
                stats['deaths'] += match['deaths']
                stats['assists'] += match['assists']
                stats['damage'] += match['damage']
                stats['gold'] += match['gold']
                stats['cs'] += match['cs']

            # 构建Pack数据
            pack_data = {
                'patch': patch,
                'total_games': len(matches),
                'generation_timestamp': datetime.now().isoformat(),
                'by_cr': []
            }

            for (champ_id, role), stats in by_cr.items():
                games = stats['games']
                wins = stats['wins']
                p_hat = wins / games

                # Wilson CI
                z = 1.96
                denom = 1 + z**2 / games
                center = p_hat + z**2 / (2 * games)
                margin = z * ((p_hat * (1 - p_hat) / games + z**2 / (4 * games**2)) ** 0.5)
                ci_lo = (center - margin) / denom
                ci_hi = (center + margin) / denom

                pack_data['by_cr'].append({
                    'champ_id': champ_id,
                    'role': role,
                    'games': games,
                    'wins': wins,
                    'losses': games - wins,
                    'p_hat': round(p_hat, 4),
                    'p_hat_ci': [round(ci_lo, 4), round(ci_hi, 4)],
                    'kda_adj': round((stats['kills'] + stats['assists']) / max(stats['deaths'], 1), 2),
                    'avg_damage': round(stats['damage'] / games, 1),
                    'avg_gold': round(stats['gold'] / games, 1),
                    'avg_cs': round(stats['cs'] / games, 1),
                    'governance_tag': 'CONFIDENT' if games >= 30 else ('CAUTION' if games >= 10 else 'CONTEXT'),
                    'effective_n': games
                })

            pack_file = output_dir / f"pack_{patch}.json"
            with open(pack_file, 'w') as f:
                json.dump(pack_data, f, indent=2)

        print(f"      ✅ 生成 {len(matches_by_patch)} 个Pack文件")

    def _analyze_packs(self, packs_dir: Path) -> Dict[str, Any]:
        """分析Pack数据，提取智能参数"""
        print(f"   🧠 智能参数推断...")

        champ_counter = Counter()
        role_counter = Counter()

        for pack_file in packs_dir.glob('pack_*.json'):
            with open(pack_file) as f:
                pack = json.load(f)

            for cr in pack['by_cr']:
                champ_counter[cr['champ_id']] += cr['games']
                role_counter[cr['role']] += cr['games']

        params = {
            'most_played_champion': champ_counter.most_common(1)[0][0] if champ_counter else None,
            'most_played_champion_games': champ_counter.most_common(1)[0][1] if champ_counter else 0,
            'top_3_champions': [c for c, _ in champ_counter.most_common(3)],
            'most_played_role': role_counter.most_common(1)[0][0] if role_counter else None,
            'most_played_role_games': role_counter.most_common(1)[0][1] if role_counter else 0,
            'all_roles': [r for r, _ in role_counter.most_common()],
            'all_champions': [c for c, _ in champ_counter.most_common()],
            'total_champions': len(champ_counter),
            'total_games': sum(champ_counter.values())
        }

        print(f"      ✅ 最常用英雄: {params['most_played_champion']} ({params['most_played_champion_games']}场)")
        print(f"      ✅ 最常用位置: {params['most_played_role']} ({params['most_played_role_games']}场)")

        return params

    def _extract_puuid_from_matches(self, matches_dir: Path) -> str:
        """从match文件中提取PUUID"""
        # 读取第一个match文件
        for match_file in matches_dir.glob("*.json"):
            with open(match_file) as f:
                match = json.load(f)
            # 假设第一个participant就是目标玩家（这是简化处理）
            # 实际应该通过其他方式确定
            return match['metadata']['participants'][0]

        raise ValueError("无法从match数据中提取PUUID")

    def _api_request(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """API请求（带重试）"""
        for attempt in range(max_retries):
            try:
                headers = {"X-Riot-Token": self._get_api_key()}
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 1))
                    time.sleep(retry_after)
                    continue
                else:
                    return None
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def _get_api_key(self) -> str:
        """轮换API密钥"""
        if not self.api_keys:
            raise ValueError("未设置Riot API密钥")

        key = self.api_keys[self.current_api_key_index]
        self.current_api_key_index = (self.current_api_key_index + 1) % len(self.api_keys)
        return key

    def _get_cluster(self, region: str) -> str:
        """获取地区集群"""
        clusters = {
            'na1': 'americas', 'br1': 'americas', 'la1': 'americas', 'la2': 'americas',
            'euw1': 'europe', 'eun1': 'europe', 'tr1': 'europe', 'ru': 'europe',
            'kr': 'asia', 'jp1': 'asia'
        }
        return clusters.get(region.lower(), 'americas')
