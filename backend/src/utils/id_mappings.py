"""
ID Mappings - Champion, Item, Rune, and Summoner Spell Name Resolution

Provides ID-to-name mappings for all League of Legends entities with search functionality.
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
import duckdb


class IDMappings:
    """
    ID到名称映射管理器

    支持英雄、装备、符文、召唤师技能等所有实体的ID映射和搜索。

    Example:
        >>> mappings = IDMappings()
        >>> mappings.get_champion_name(92)  # "Riven"
        >>> mappings.get_item_name(3071)    # "Black Cleaver"
        >>> mappings.search_champions("riv")  # [{"id": 92, "name": "Riven"}]
    """

    def __init__(
        self,
        cache_dir: str = "data/static/mappings",
        patch_version: str = "14.23.1"  # Latest patch
    ):
        """
        Args:
            cache_dir: Directory to cache mapping data
            patch_version: Patch version to use for DDragon data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.patch_version = patch_version

        # Cache files
        self.champion_cache = self.cache_dir / "champions.json"
        self.item_cache = self.cache_dir / "items.json"
        self.rune_cache = self.cache_dir / "runes.json"
        self.summoner_cache = self.cache_dir / "summoners.json"

        # Load or fetch mappings
        self.champions = self._load_or_fetch_champions()
        self.items = self._load_or_fetch_items()
        self.runes = self._load_or_fetch_runes()
        self.summoners = self._load_or_fetch_summoners()

    def _load_or_fetch_champions(self) -> Dict[int, str]:
        """加载或获取英雄映射"""
        if self.champion_cache.exists():
            with open(self.champion_cache, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}

        # Fetch from DDragon
        print("📥 Fetching champion data from DDragon...")
        url = f"https://ddragon.leagueoflegends.com/cdn/{self.patch_version}/data/en_US/champion.json"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Build ID to name mapping
            mappings = {}
            for champ_data in data["data"].values():
                champ_id = int(champ_data["key"])
                champ_name = champ_data["name"]
                mappings[champ_id] = champ_name

            # Save to cache
            with open(self.champion_cache, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2)

            print(f"✅ Loaded {len(mappings)} champions")
            return mappings

        except Exception as e:
            print(f"⚠️ Failed to fetch champion data: {e}")
            return {}

    def _load_or_fetch_items(self) -> Dict[int, str]:
        """加载或获取装备映射"""
        if self.item_cache.exists():
            with open(self.item_cache, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}

        # Fetch from DDragon
        print("📥 Fetching item data from DDragon...")
        url = f"https://ddragon.leagueoflegends.com/cdn/{self.patch_version}/data/en_US/item.json"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Build ID to name mapping
            mappings = {}
            for item_id, item_data in data["data"].items():
                mappings[int(item_id)] = item_data["name"]

            # Save to cache
            with open(self.item_cache, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2)

            print(f"✅ Loaded {len(mappings)} items")
            return mappings

        except Exception as e:
            print(f"⚠️ Failed to fetch item data: {e}")
            return {}

    def _load_or_fetch_runes(self) -> Dict[int, str]:
        """加载或获取符文映射"""
        if self.rune_cache.exists():
            with open(self.rune_cache, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}

        # Fetch from DDragon
        print("📥 Fetching rune data from DDragon...")
        url = f"https://ddragon.leagueoflegends.com/cdn/{self.patch_version}/data/en_US/runesReforged.json"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Build ID to name mapping
            mappings = {}
            for tree in data:
                # Tree itself
                mappings[tree["id"]] = tree["name"]

                # Slots and runes
                for slot in tree["slots"]:
                    for rune in slot["runes"]:
                        mappings[rune["id"]] = rune["name"]

            # Save to cache
            with open(self.rune_cache, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2)

            print(f"✅ Loaded {len(mappings)} runes")
            return mappings

        except Exception as e:
            print(f"⚠️ Failed to fetch rune data: {e}")
            return {}

    def _load_or_fetch_summoners(self) -> Dict[int, str]:
        """加载或获取召唤师技能映射"""
        if self.summoner_cache.exists():
            with open(self.summoner_cache, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}

        # Fetch from DDragon
        print("📥 Fetching summoner spell data from DDragon...")
        url = f"https://ddragon.leagueoflegends.com/cdn/{self.patch_version}/data/en_US/summoner.json"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Build ID to name mapping
            mappings = {}
            for spell_data in data["data"].values():
                spell_id = int(spell_data["key"])
                spell_name = spell_data["name"]
                mappings[spell_id] = spell_name

            # Save to cache
            with open(self.summoner_cache, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2)

            print(f"✅ Loaded {len(mappings)} summoner spells")
            return mappings

        except Exception as e:
            print(f"⚠️ Failed to fetch summoner spell data: {e}")
            return {}

    # === Get Methods ===

    def get_champion_name(self, champion_id: int) -> str:
        """获取英雄名称"""
        return self.champions.get(champion_id, f"Champion {champion_id}")

    def get_item_name(self, item_id: int) -> str:
        """获取装备名称"""
        return self.items.get(item_id, f"Item {item_id}")

    def get_rune_name(self, rune_id: int) -> str:
        """获取符文名称"""
        return self.runes.get(rune_id, f"Rune {rune_id}")

    def get_summoner_name(self, summoner_id: int) -> str:
        """获取召唤师技能名称"""
        return self.summoners.get(summoner_id, f"Summoner {summoner_id}")

    # === Batch Get Methods ===

    def get_champion_names(self, champion_ids: List[int]) -> List[str]:
        """批量获取英雄名称"""
        return [self.get_champion_name(cid) for cid in champion_ids]

    def get_item_names(self, item_ids: List[int]) -> List[str]:
        """批量获取装备名称"""
        return [self.get_item_name(iid) for iid in item_ids]

    # === Search Methods ===

    def search_champions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索英雄

        Args:
            query: Search query (case-insensitive)
            limit: Maximum results to return

        Returns:
            List of {"id": int, "name": str} matches
        """
        query_lower = query.lower()
        results = []

        for champ_id, champ_name in self.champions.items():
            if query_lower in champ_name.lower():
                results.append({
                    "id": champ_id,
                    "name": champ_name
                })

        return results[:limit]

    def search_items(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索装备

        Args:
            query: Search query (case-insensitive)
            limit: Maximum results to return

        Returns:
            List of {"id": int, "name": str} matches
        """
        query_lower = query.lower()
        results = []

        for item_id, item_name in self.items.items():
            if query_lower in item_name.lower():
                results.append({
                    "id": item_id,
                    "name": item_name
                })

        return results[:limit]

    def search_runes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索符文"""
        query_lower = query.lower()
        results = []

        for rune_id, rune_name in self.runes.items():
            if query_lower in rune_name.lower():
                results.append({
                    "id": rune_id,
                    "name": rune_name
                })

        return results[:limit]

    def search_summoners(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索召唤师技能"""
        query_lower = query.lower()
        results = []

        for spell_id, spell_name in self.summoners.items():
            if query_lower in spell_name.lower():
                results.append({
                    "id": spell_id,
                    "name": spell_name
                })

        return results[:limit]

    # === Utility Methods ===

    def get_all_champions(self) -> Dict[int, str]:
        """获取所有英雄映射"""
        return self.champions.copy()

    def get_all_items(self) -> Dict[int, str]:
        """获取所有装备映射"""
        return self.items.copy()

    def get_all_runes(self) -> Dict[int, str]:
        """获取所有符文映射"""
        return self.runes.copy()

    def get_all_summoners(self) -> Dict[int, str]:
        """获取所有召唤师技能映射"""
        return self.summoners.copy()

    def refresh_all(self):
        """重新获取所有映射数据"""
        print("\n🔄 Refreshing all mappings...")

        # Delete cache files
        for cache_file in [self.champion_cache, self.item_cache,
                           self.rune_cache, self.summoner_cache]:
            if cache_file.exists():
                cache_file.unlink()

        # Re-fetch
        self.champions = self._load_or_fetch_champions()
        self.items = self._load_or_fetch_items()
        self.runes = self._load_or_fetch_runes()
        self.summoners = self._load_or_fetch_summoners()

        print("✅ All mappings refreshed")

    def get_stats(self) -> Dict[str, int]:
        """获取映射统计信息"""
        return {
            "champions": len(self.champions),
            "items": len(self.items),
            "runes": len(self.runes),
            "summoners": len(self.summoners)
        }


# Singleton instance
_global_mappings = None


def get_mappings() -> IDMappings:
    """获取全局映射实例（单例模式）"""
    global _global_mappings
    if _global_mappings is None:
        _global_mappings = IDMappings()
    return _global_mappings


def get_champion_name(champion_id: int) -> str:
    """快捷方法：获取英雄名称"""
    return get_mappings().get_champion_name(champion_id)


def get_item_name(item_id: int) -> str:
    """快捷方法：获取装备名称"""
    return get_mappings().get_item_name(item_id)


def search_champions(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """快捷方法：搜索英雄"""
    return get_mappings().search_champions(query, limit)


def search_items(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """快捷方法：搜索装备"""
    return get_mappings().search_items(query, limit)
