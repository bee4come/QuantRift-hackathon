"""
Per-Endpoint Rate Limiter for Riot API
每个API endpoint有独立的速率限制，不共享限速窗口
"""
import asyncio
import re
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse


class EndpointRateLimiter:
    """
    Per-endpoint rate limiter with independent windows for each API endpoint.

    每个API endpoint维护独立的限速窗口，避免不同API之间互相影响。
    例如：match-v5的请求不会消耗summoner-v4的配额。
    """

    # Riot API官方速率限制配置 (使用90%作为安全边界)
    ENDPOINT_LIMITS = {
        # Champion API
        '/lol/platform/v3/champion-rotations': [(27, 10), (450, 600)],

        # Summoner API
        '/lol/summoner/v4/summoners/by-puuid/{encryptedPUUID}': [(1440, 60)],

        # League API
        '/lol/league/v4/challengerleagues/by-queue/{queue}': [(27, 10), (450, 600)],
        '/lol/league/v4/leagues/{leagueId}': [(450, 10)],
        '/lol/league/v4/masterleagues/by-queue/{queue}': [(27, 10), (450, 600)],
        '/lol/league/v4/grandmasterleagues/by-queue/{queue}': [(27, 10), (450, 600)],
        '/lol/league/v4/entries/{queue}/{tier}/{division}': [(45, 10)],
        '/lol/league/v4/entries/by-puuid/{encryptedPUUID}': [(18000, 10), (1080000, 600)],

        # League Exp API
        '/lol/league-exp/v4/entries/{queue}/{tier}/{division}': [(45, 10)],

        # Clash API
        '/lol/clash/v1/teams/{teamId}': [(180, 60)],
        '/lol/clash/v1/tournaments/{tournamentId}': [(9, 60)],
        '/lol/clash/v1/tournaments/by-team/{teamId}': [(180, 60)],
        '/lol/clash/v1/tournaments': [(9, 60)],
        '/lol/clash/v1/players/by-puuid/{puuid}': [(18000, 10), (1080000, 600)],

        # Account API
        '/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}': [(900, 60), (18000, 10), (1080000, 600)],
        '/riot/account/v1/accounts/by-puuid/{puuid}': [(900, 60), (18000, 10), (1080000, 600)],
        '/riot/account/v1/region/by-game/{game}/by-puuid/{puuid}': [(18000, 10), (1080000, 600)],

        # Status API
        '/lol/status/v4/platform-data': [(18000, 10), (1080000, 600)],

        # Match API (最常用，最重要的限速)
        # ⚡ 只使用10秒窗口，移除60秒限制以避免batch等待
        '/lol/match/v5/matches/{matchId}': [(1800, 10)],  # 2000的90%, 只有10s窗口
        '/lol/match/v5/matches/by-puuid/{puuid}/ids': [(1800, 10)],  # 2000的90%, 只有10s窗口
        '/lol/match/v5/matches/{matchId}/timeline': [(1800, 10)],  # 2000的90%, 只有10s窗口

        # Challenges API
        '/lol/challenges/v1/challenges/percentiles': [(18000, 10), (1080000, 600)],
        '/lol/challenges/v1/challenges/{challengeId}/leaderboards/by-level/{level}': [(18000, 10), (1080000, 600)],
        '/lol/challenges/v1/challenges/{challengeId}/percentiles': [(18000, 10), (1080000, 600)],
        '/lol/challenges/v1/challenges/{challengeId}/config': [(18000, 10), (1080000, 600)],
        '/lol/challenges/v1/player-data/{puuid}': [(18000, 10), (1080000, 600)],
        '/lol/challenges/v1/challenges/config': [(18000, 10), (1080000, 600)],

        # Champion Mastery API
        '/lol/champion-mastery/v4/champion-masteries/by-puuid/{encryptedPUUID}': [(18000, 10), (1080000, 600)],
        '/lol/champion-mastery/v4/champion-masteries/by-puuid/{encryptedPUUID}/by-champion/{championId}': [(18000, 10), (1080000, 600)],
        '/lol/champion-mastery/v4/scores/by-puuid/{encryptedPUUID}': [(18000, 10), (1080000, 600)],
        '/lol/champion-mastery/v4/champion-masteries/by-puuid/{encryptedPUUID}/top': [(18000, 10), (1080000, 600)],

        # Tournament Stub API
        '/lol/tournament-stub/v5/codes': [(18000, 10), (1080000, 600)],
        '/lol/tournament-stub/v5/lobby-events/by-code/{tournamentCode}': [(18000, 10), (1080000, 600)],
        '/lol/tournament-stub/v5/codes/{tournamentCode}': [(18000, 10), (1080000, 600)],
        '/lol/tournament-stub/v5/providers': [(18000, 10), (1080000, 600)],
        '/lol/tournament-stub/v5/tournaments': [(18000, 10), (1080000, 600)],

        # Spectator API
        '/lol/spectator/v5/active-games/by-summoner/{encryptedPUUID}': [(18000, 10), (1080000, 600)],
    }

    def __init__(self, num_api_keys: int = 1):
        """
        初始化per-endpoint限速器

        Args:
            num_api_keys: API key数量，每个key有独立的限速配额
        """
        self.num_api_keys = num_api_keys

        # 每个endpoint pattern的限速窗口
        # key: endpoint_pattern (e.g., "/lol/match/v5/matches/{matchId}")
        # value: list of deques for each rate limit window
        self._endpoint_windows: Dict[str, List[deque]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

        # ⚡ Match-v5 API: 每个API key一个独立的限速窗口
        # 4个keys = 4 × 2000 req/10s = 8000 req/10s 总配额
        self._match_v5_windows = [deque() for _ in range(num_api_keys)]  # 每个key一个窗口
        self._match_v5_locks = [asyncio.Lock() for _ in range(num_api_keys)]  # 每个key一个锁
        self._match_v5_key_index = 0  # 轮换使用的key index
        self._match_v5_rotation_lock = asyncio.Lock()  # 保护key轮换
        self._match_v5_endpoints = {
            '/lol/match/v5/matches/{matchId}',
            '/lol/match/v5/matches/by-puuid/{puuid}/ids',
            '/lol/match/v5/matches/{matchId}/timeline'
        }

    def _normalize_endpoint(self, url: str) -> str:
        """
        将实际URL标准化为endpoint pattern

        例如：
        - "https://americas.api.riotgames.com/lol/match/v5/matches/NA1_123456"
          -> "/lol/match/v5/matches/{matchId}"
        - "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/abc123"
          -> "/lol/summoner/v4/summoners/by-puuid/{encryptedPUUID}"
        """
        # 提取path部分
        parsed = urlparse(url)
        path = parsed.path

        # 匹配已知的endpoint patterns
        for pattern in self.ENDPOINT_LIMITS.keys():
            # 将pattern转换为正则表达式
            # 例如: "/lol/match/v5/matches/{matchId}" -> r"/lol/match/v5/matches/[^/]+"
            regex_pattern = pattern
            regex_pattern = regex_pattern.replace('{matchId}', '[^/]+')
            regex_pattern = regex_pattern.replace('{puuid}', '[^/]+')
            regex_pattern = regex_pattern.replace('{encryptedPUUID}', '[^/]+')
            regex_pattern = regex_pattern.replace('{gameName}', '[^/]+')
            regex_pattern = regex_pattern.replace('{tagLine}', '[^/]+')
            regex_pattern = regex_pattern.replace('{queue}', '[^/]+')
            regex_pattern = regex_pattern.replace('{tier}', '[^/]+')
            regex_pattern = regex_pattern.replace('{division}', '[^/]+')
            regex_pattern = regex_pattern.replace('{leagueId}', '[^/]+')
            regex_pattern = regex_pattern.replace('{teamId}', '[^/]+')
            regex_pattern = regex_pattern.replace('{tournamentId}', '[^/]+')
            regex_pattern = regex_pattern.replace('{tournamentCode}', '[^/]+')
            regex_pattern = regex_pattern.replace('{challengeId}', '[^/]+')
            regex_pattern = regex_pattern.replace('{level}', '[^/]+')
            regex_pattern = regex_pattern.replace('{championId}', '[^/]+')
            regex_pattern = regex_pattern.replace('{game}', '[^/]+')
            regex_pattern = f'^{regex_pattern}$'

            if re.match(regex_pattern, path):
                return pattern

        # 如果没有匹配到，返回通用限速 (最保守的match-v5限速)
        return '/lol/match/v5/matches/{matchId}'

    def _get_rate_limits(self, endpoint_pattern: str) -> List[Tuple[int, int]]:
        """获取endpoint的速率限制配置"""
        return self.ENDPOINT_LIMITS.get(endpoint_pattern, [(1800, 10)])  # 默认使用match-v5限速

    def _init_endpoint(self, endpoint_pattern: str):
        """初始化endpoint的限速窗口"""
        if endpoint_pattern not in self._endpoint_windows:
            rate_limits = self._get_rate_limits(endpoint_pattern)
            self._endpoint_windows[endpoint_pattern] = [deque() for _ in rate_limits]
            self._locks[endpoint_pattern] = asyncio.Lock()

    async def acquire(self, url: str):
        """
        为指定URL获取速率限制许可

        Args:
            url: 完整的API URL
        """
        endpoint_pattern = self._normalize_endpoint(url)

        # ⚡ Match-v5 API使用共享窗口
        if endpoint_pattern in self._match_v5_endpoints:
            return await self._acquire_match_v5()

        # 其他API使用独立窗口
        self._init_endpoint(endpoint_pattern)
        rate_limits = self._get_rate_limits(endpoint_pattern)
        windows = self._endpoint_windows[endpoint_pattern]
        lock = self._locks[endpoint_pattern]

        while True:
            async with lock:
                now = datetime.utcnow()
                sleep_durations: List[float] = []

                for idx, (max_requests, window_seconds) in enumerate(rate_limits):
                    window = windows[idx]
                    cutoff = now - timedelta(seconds=window_seconds)

                    # 清理过期的时间戳
                    while window and window[0] <= cutoff:
                        window.popleft()

                    # 检查是否达到限制
                    if len(window) >= max_requests:
                        oldest = window[0]
                        remaining = window_seconds - (now - oldest).total_seconds()
                        if remaining > 0:
                            sleep_durations.append(remaining)

                # 如果没有达到任何限制，记录本次请求并返回
                if not sleep_durations:
                    for window in windows:
                        window.append(now)
                    return

                # 需要等待最长的窗口
                sleep_time = max(sleep_durations)

            # 在锁外等待，避免阻塞其他请求
            await asyncio.sleep(sleep_time)

    async def _acquire_match_v5(self):
        """
        Match-v5 API轮换per-key限速窗口
        每个API key有独立的2000 req/10s配额
        4个keys = 4 × 2000 = 8000 req/10s 总配额
        """
        max_requests = 1800  # 90% of 2000 per key
        window_seconds = 10

        # 尝试所有keys，找到第一个可用的
        tried_keys = 0
        while tried_keys < self.num_api_keys:
            # 获取下一个key index (轮换)
            async with self._match_v5_rotation_lock:
                key_index = self._match_v5_key_index
                self._match_v5_key_index = (self._match_v5_key_index + 1) % self.num_api_keys

            # 尝试使用这个key的配额
            window = self._match_v5_windows[key_index]
            lock = self._match_v5_locks[key_index]

            async with lock:
                now = datetime.utcnow()
                cutoff = now - timedelta(seconds=window_seconds)

                # 清理过期的时间戳
                while window and window[0] <= cutoff:
                    window.popleft()

                # 检查是否达到限制
                if len(window) < max_requests:
                    # 这个key还有配额，使用它
                    window.append(now)
                    return

            # 这个key满了，尝试下一个
            tried_keys += 1

        # 所有keys都满了，等待最早的key恢复
        # 找到恢复最快的key
        min_wait_time = float('inf')
        for key_index in range(self.num_api_keys):
            window = self._match_v5_windows[key_index]
            lock = self._match_v5_locks[key_index]

            async with lock:
                if window:
                    oldest = window[0]
                    remaining = window_seconds - (datetime.utcnow() - oldest).total_seconds()
                    if remaining > 0 and remaining < min_wait_time:
                        min_wait_time = remaining

        # 等待最快恢复的key
        if min_wait_time < float('inf') and min_wait_time > 0:
            if min_wait_time > 5:  # 如果等待超过5秒，记录日志
                print(f"⏳ Rate limiter: 等待 {min_wait_time:.1f}秒 (所有{self.num_api_keys}个API keys都已满)")
            await asyncio.sleep(min_wait_time + 0.1)  # 加一点buffer
        else:
            await asyncio.sleep(0.1)  # 短暂等待后重试

        # 递归重试
        return await self._acquire_match_v5()

    def get_endpoint_status(self, url: str) -> Dict[str, any]:
        """
        获取endpoint的当前限速状态（用于调试）

        Returns:
            {
                'endpoint': str,
                'limits': [(max_req, window_sec), ...],
                'current_usage': [(used, max, window_sec), ...]
            }
        """
        endpoint_pattern = self._normalize_endpoint(url)
        self._init_endpoint(endpoint_pattern)

        rate_limits = self._get_rate_limits(endpoint_pattern)
        windows = self._endpoint_windows[endpoint_pattern]

        now = datetime.utcnow()
        usage = []

        for idx, (max_requests, window_seconds) in enumerate(rate_limits):
            window = windows[idx]
            cutoff = now - timedelta(seconds=window_seconds)

            # 清理过期的时间戳
            temp_window = deque([ts for ts in window if ts > cutoff])
            used = len(temp_window)

            usage.append((used, max_requests, window_seconds))

        return {
            'endpoint': endpoint_pattern,
            'limits': rate_limits,
            'current_usage': usage
        }
