"""
Report Cache Manager
Caches generated analysis reports to avoid redundant LLM calls
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


class ReportCache:
    """Manages caching of agent analysis reports"""

    def __init__(self, cache_dir: Path = None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "report_cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(
        self,
        puuid: str,
        agent_id: str,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None,
        recent_count: Optional[int] = None,
        **kwargs  # For additional params like champion_id, role, etc.
    ) -> str:
        """
        Generate cache key based on request parameters

        Args:
            puuid: Player PUUID
            agent_id: Agent identifier (e.g., 'weakness-analysis')
            time_range: Time range filter
            queue_id: Queue type filter
            recent_count: Number of recent matches
            **kwargs: Additional parameters (champion_id, role, match_id, etc.)

        Returns:
            Cache key string
        """
        # Sort kwargs for consistent ordering
        sorted_kwargs = sorted(kwargs.items())

        # Create a deterministic string representation
        key_parts = [
            puuid,
            agent_id,
            str(time_range) if time_range else "all",
            str(queue_id) if queue_id is not None else "all",
            str(recent_count) if recent_count else "default"
        ]

        # Add additional params
        for k, v in sorted_kwargs:
            if v is not None:
                key_parts.append(f"{k}={v}")

        key_string = "_".join(key_parts)

        # Hash for shorter filename
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]

        return f"{agent_id}_{key_hash}"

    def _get_cache_path(self, puuid: str, cache_key: str) -> Path:
        """Get cache file path for a specific player and cache key"""
        player_cache_dir = self.cache_dir / puuid
        player_cache_dir.mkdir(parents=True, exist_ok=True)
        return player_cache_dir / f"{cache_key}.json"

    def _get_latest_match_id(self, packs_dir: Path) -> Optional[str]:
        """
        Get the latest match ID from player packs

        Args:
            packs_dir: Path to player_packs directory

        Returns:
            Latest match ID or None
        """
        try:
            # Find all pack files
            pack_files = sorted(packs_dir.glob("pack_*.json"))
            if not pack_files:
                return None

            # Read the most recent pack
            latest_pack = pack_files[-1]
            with open(latest_pack, 'r', encoding='utf-8') as f:
                pack_data = json.load(f)

            # Extract latest match ID from by_cr entries
            latest_match_id = None
            for cr in pack_data.get("by_cr", []):
                for match in cr.get("matches", []):
                    match_id = match.get("match_id")
                    if match_id:
                        if latest_match_id is None or match_id > latest_match_id:
                            latest_match_id = match_id

            return latest_match_id

        except Exception as e:
            print(f"⚠️ Error getting latest match ID: {e}")
            return None

    def get(
        self,
        puuid: str,
        agent_id: str,
        packs_dir: Path,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None,
        recent_count: Optional[int] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached report if valid

        Args:
            puuid: Player PUUID
            agent_id: Agent identifier
            packs_dir: Path to player packs directory (to check for new matches)
            time_range: Time range filter
            queue_id: Queue type filter
            recent_count: Number of recent matches
            **kwargs: Additional parameters

        Returns:
            Cached report data or None if cache miss/invalid
        """
        try:
            cache_key = self._get_cache_key(
                puuid, agent_id, time_range, queue_id, recent_count, **kwargs
            )
            cache_path = self._get_cache_path(puuid, cache_key)

            if not cache_path.exists():
                print(f"❌ Cache MISS: {cache_key} (file not found)")
                return None

            # Read cached data
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check if cache is still valid (no new matches)
            latest_match_id = self._get_latest_match_id(packs_dir)
            cached_match_id = cache_data.get("last_match_id")

            if latest_match_id and cached_match_id and latest_match_id != cached_match_id:
                print(f"❌ Cache INVALID: {cache_key} (new matches detected)")
                print(f"   Cached: {cached_match_id}, Latest: {latest_match_id}")
                return None

            print(f"✅ Cache HIT: {cache_key}")
            print(f"   Generated: {cache_data.get('generated_at')}")
            print(f"   Last match: {cached_match_id}")

            return cache_data

        except Exception as e:
            print(f"⚠️ Cache read error for {agent_id}: {e}")
            return None

    def set(
        self,
        puuid: str,
        agent_id: str,
        packs_dir: Path,
        report_content: str,
        analysis_data: Optional[Dict[str, Any]] = None,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None,
        recent_count: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Cache a generated report

        Args:
            puuid: Player PUUID
            agent_id: Agent identifier
            packs_dir: Path to player packs directory
            report_content: Generated report markdown
            analysis_data: Optional structured analysis data
            time_range: Time range filter
            queue_id: Queue type filter
            recent_count: Number of recent matches
            **kwargs: Additional parameters

        Returns:
            True if successfully cached, False otherwise
        """
        try:
            cache_key = self._get_cache_key(
                puuid, agent_id, time_range, queue_id, recent_count, **kwargs
            )
            cache_path = self._get_cache_path(puuid, cache_key)

            # Get latest match ID
            latest_match_id = self._get_latest_match_id(packs_dir)

            # Prepare cache data
            cache_data = {
                "cache_key": cache_key,
                "agent_id": agent_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "last_match_id": latest_match_id,
                "parameters": {
                    "time_range": time_range,
                    "queue_id": queue_id,
                    "recent_count": recent_count,
                    **kwargs
                },
                "report_content": report_content,
                "analysis_data": analysis_data
            }

            # Write to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            print(f"💾 Cache SAVED: {cache_key}")
            print(f"   Path: {cache_path}")
            print(f"   Last match: {latest_match_id}")

            return True

        except Exception as e:
            print(f"⚠️ Cache write error for {agent_id}: {e}")
            return False

    def invalidate(self, puuid: str, agent_id: Optional[str] = None) -> int:
        """
        Invalidate cache for a player

        Args:
            puuid: Player PUUID
            agent_id: Optional specific agent to invalidate (if None, invalidate all)

        Returns:
            Number of cache files deleted
        """
        try:
            player_cache_dir = self.cache_dir / puuid
            if not player_cache_dir.exists():
                return 0

            count = 0
            if agent_id:
                # Invalidate specific agent caches
                pattern = f"{agent_id}_*.json"
                for cache_file in player_cache_dir.glob(pattern):
                    cache_file.unlink()
                    count += 1
            else:
                # Invalidate all caches for this player
                for cache_file in player_cache_dir.glob("*.json"):
                    cache_file.unlink()
                    count += 1

            print(f"🗑️  Invalidated {count} cache entries for {puuid}")
            return count

        except Exception as e:
            print(f"⚠️ Cache invalidation error: {e}")
            return 0

    def get_stats(self, puuid: str) -> Dict[str, Any]:
        """
        Get cache statistics for a player

        Args:
            puuid: Player PUUID

        Returns:
            Cache statistics
        """
        try:
            player_cache_dir = self.cache_dir / puuid
            if not player_cache_dir.exists():
                return {"total_cached_reports": 0, "agents": []}

            cache_files = list(player_cache_dir.glob("*.json"))
            agents = {}

            for cache_file in cache_files:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    agent_id = cache_data.get("agent_id", "unknown")
                    if agent_id not in agents:
                        agents[agent_id] = 0
                    agents[agent_id] += 1

            return {
                "total_cached_reports": len(cache_files),
                "agents": [{"agent_id": k, "count": v} for k, v in agents.items()]
            }

        except Exception as e:
            print(f"⚠️ Cache stats error: {e}")
            return {"total_cached_reports": 0, "agents": [], "error": str(e)}


# Global cache instance
report_cache = ReportCache()
