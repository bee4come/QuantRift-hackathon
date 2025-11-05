"""
Riot API Client - Handles all Riot Games API interactions
Multi-key rotation support for production rate limiting
Per-endpoint rate limiting for optimal API utilization
"""
import asyncio
from collections import deque
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote
import json
import os
from dotenv import load_dotenv
from .endpoint_rate_limiter import EndpointRateLimiter

load_dotenv()

# Simple logger fallback
try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class RiotAPIError(Exception):
    """Custom exception for Riot API errors"""
    def __init__(self, status_code: int, message: str, response_data: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data or {}
        super().__init__(f"Riot API Error {status_code}: {message}")


class RateLimiter:
    """Sliding-window rate limiter for Riot API requests"""

    def __init__(self, rate_limits: Optional[List[Tuple[int, int]]] = None):
        """
        Create limiter with (max_requests, window_seconds) tuples.

        Default uses production API limits (most restrictive across endpoints):
        - match-v5: 2000 req/10s
        - account-v1: 1000 req/60s
        - summoner-v4: 1600 req/60s

        Using conservative 90% of limits: 1800 req/10s, 1440 req/60s

        ⚡ Optimization: Increased 60s window from 900 to 1440 (90% of 1600, Summoner API limit)
        This allows batch fetching of 600+ matches without hitting 60s bottleneck
        """
        # Production limits (90% of official to be safe)
        self.rate_limits = rate_limits or [(1800, 10), (1440, 60)]

        # Maintain independent timestamp deques per window for fast eviction
        self._windows = [deque() for _ in self.rate_limits]
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire rate limit permission respecting all configured windows."""
        while True:
            async with self._lock:
                now = datetime.utcnow()
                sleep_durations: List[float] = []

                for idx, (max_requests, window_seconds) in enumerate(self.rate_limits):
                    window = self._windows[idx]
                    cutoff = now - timedelta(seconds=window_seconds)

                    # Drop timestamps outside the active window
                    while window and window[0] <= cutoff:
                        window.popleft()

                    if len(window) >= max_requests:
                        oldest = window[0]
                        remaining = window_seconds - (now - oldest).total_seconds()
                        if remaining > 0:
                            sleep_durations.append(remaining)

                if not sleep_durations:
                    for window in self._windows:
                        window.append(now)
                    return

                sleep_time = max(sleep_durations)

            # Sleep outside of the lock to avoid blocking other waiters
            await asyncio.sleep(sleep_time)


class RiotAPIClient:
    """
    Riot API Client with comprehensive endpoint coverage:
    - Account API (PUUID resolution)
    - Summoner API (player profiles)
    - Match API (match history and details)
    - League API (ranked information)
    - Rate limiting and error handling
    """

    # Regional routing
    PLATFORM_HOSTS = {
        "br1": "br1.api.riotgames.com",
        "eun1": "eun1.api.riotgames.com",
        "euw1": "euw1.api.riotgames.com",
        "jp1": "jp1.api.riotgames.com",
        "kr": "kr.api.riotgames.com",
        "la1": "la1.api.riotgames.com",
        "la2": "la2.api.riotgames.com",
        "na1": "na1.api.riotgames.com",
        "oc1": "oc1.api.riotgames.com",
        "tr1": "tr1.api.riotgames.com",
        "ru": "ru.api.riotgames.com",
        "ph2": "ph2.api.riotgames.com",
        "sg2": "sg2.api.riotgames.com",
        "th2": "th2.api.riotgames.com",
        "tw2": "tw2.api.riotgames.com",
        "vn2": "vn2.api.riotgames.com",
    }

    REGIONAL_HOSTS = {
        "americas": "americas.api.riotgames.com",
        "asia": "asia.api.riotgames.com",
        "europe": "europe.api.riotgames.com",
        "sea": "sea.api.riotgames.com",
    }

    # Platform to region mapping
    PLATFORM_TO_REGION = {
        "br1": "americas", "la1": "americas", "la2": "americas", "na1": "americas",
        "kr": "asia", "jp1": "asia",
        "eun1": "europe", "euw1": "europe", "tr1": "europe", "ru": "europe",
        "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea",
    }

    def __init__(self, api_key: str = None, default_region: str = "na1", rate_limit_enabled: bool = True):
        # Multi-key rotation support
        if api_key:
            self.api_keys = [api_key]
        else:
            # Multi-key rotation strategy:
            # - Account/Summoner API: Use PRIMARY key only (PUUID is per-key encrypted)
            # - Match API: Can use ALL keys (Match ID is global, riotIdGameName/tagline are plaintext)

            # ⚡ 启用4个不重复的API key轮换，提升速率限制（1800→7200 req/10s）
            # Load all available keys (excluding RIOT_API_KEY to avoid duplication)
            all_keys = [
                os.getenv('RIOT_API_KEY_PRIMARY'),
                os.getenv('RIOT_API_KEY_SECONDARY'),
                os.getenv('RIOT_API_KEY_ALT'),
                os.getenv('RIOT_API_KEY_TERTIARY'),
            ]
            all_keys_filtered = [key for key in all_keys if key]

            # ✅ 使用4个不重复的API keys进行轮换
            self.api_keys = all_keys_filtered

            # Primary key for Account/Summoner API (must be consistent for PUUID)
            self.primary_key = self.api_keys[0] if self.api_keys else None

        if not self.api_keys:
            raise ValueError("No Riot API keys found")

        self.default_region = default_region
        self.current_key_index = 0

        logger.info(f"Riot API client initialized with {len(self.api_keys)} API key(s)")

        # Per-endpoint rate limiter (每个API endpoint独立限速，每个key独立配额)
        if rate_limit_enabled:
            self.endpoint_rate_limiter = EndpointRateLimiter(num_api_keys=len(self.api_keys))
        else:
            self.endpoint_rate_limiter = None

        # HTTP session
        self.session = None

        # Request timeout
        self.timeout = aiohttp.ClientTimeout(total=30)

    def _get_next_api_key(self) -> str:
        """Get next API key in rotation"""
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key

    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            # ⚡ 优化：增加连接池大小以支持高并发
            # 默认100连接不够用，增加到500
            connector = aiohttp.TCPConnector(
                limit=500,  # 总连接数上限
                limit_per_host=200,  # 单个host连接数上限
                ttl_dns_cache=300  # DNS缓存5分钟
            )

            # ⚡ 自动检测并使用代理（如果环境变量中有配置）
            # 优先使用http_proxy（Python 3.10的aiohttp不支持HTTPS proxy的TLS in TLS）
            proxy_url = None
            for proxy_var in ['http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY']:
                proxy_url = os.environ.get(proxy_var)
                if proxy_url:
                    logger.info(f"检测到代理配置 {proxy_var}={proxy_url}")
                    break

            # 保存proxy_url供请求时使用
            self.proxy_url = proxy_url

            # Don't set X-Riot-Token in session headers - set per request
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                trust_env=False,  # ⚡ 手动管理代理（避免Python 3.10的HTTPS proxy问题）
                headers={
                    "Accept": "application/json",
                    "User-Agent": "RiftRewind/1.0"
                }
            )

            if proxy_url:
                logger.info(f"✅ Riot API将通过代理访问: {proxy_url}")
            else:
                logger.info("ℹ️  未检测到代理，将直连Riot API")

        # Test API key validity with first key
        try:
            test_url = f"https://{self.PLATFORM_HOSTS[self.default_region]}/lol/status/v4/platform-data"
            await self._make_request("GET", test_url)
            logger.info(f"Riot API client initialized successfully with {len(self.api_keys)} key(s)")
        except Exception as e:
            logger.error(f"Failed to initialize Riot API client: {e}")
            raise

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _make_request(self, method: str, url: str, use_primary_key: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with per-endpoint rate limiting and error handling

        Args:
            use_primary_key: If True, always use primary_key (for Account/Summoner API where PUUID must be consistent)
                           If False, rotate through all available keys (for Match API where Match ID is global)
        """
        import time
        request_start = time.time()

        if not self.session:
            await self.initialize()

        # Apply per-endpoint rate limiting
        if self.endpoint_rate_limiter:
            rate_limit_start = time.time()
            await self.endpoint_rate_limiter.acquire(url)
            rate_limit_duration = time.time() - rate_limit_start
            if rate_limit_duration > 5:
                print(f"⏱️  Rate limiter等待了 {rate_limit_duration:.1f}秒")

        # Get API key: use primary key for PUUID-based APIs, rotate for Match API
        if use_primary_key and hasattr(self, 'primary_key'):
            api_key = self.primary_key
        else:
            api_key = self._get_next_api_key()

        # Add API key to headers
        headers = kwargs.get('headers', {})
        headers['X-Riot-Token'] = api_key
        kwargs['headers'] = headers

        # ⚡ 添加代理支持（如果配置了代理）
        if hasattr(self, 'proxy_url') and self.proxy_url:
            kwargs['proxy'] = self.proxy_url

        try:
            http_start = time.time()
            async with self.session.request(method, url, **kwargs) as response:
                http_duration = time.time() - http_start
                total_duration = time.time() - request_start
                if total_duration > 5:
                    print(f"🐌 慢请求: HTTP {http_duration:.1f}s, 总计 {total_duration:.1f}s - {url[:80]}")
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    logger.debug(f"Resource not found: {url}")
                    return None
                elif response.status == 429:
                    # Rate limited - get retry after header
                    retry_after = response.headers.get("Retry-After", "1")
                    await asyncio.sleep(int(retry_after))
                    return await self._make_request(method, url, **kwargs)
                else:
                    response_text = await response.text()
                    raise RiotAPIError(
                        status_code=response.status,
                        message=f"API request failed: {response_text}",
                        response_data={"url": url, "response": response_text}
                    )

        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}, url: {url}")
            raise RiotAPIError(500, f"HTTP client error: {str(e)}")

    # Account API (Regional routing)
    async def get_account_by_riot_id(self, game_name: str, tag_line: str, region: str = "americas") -> Optional[Dict[str, Any]]:
        """Get account by Riot ID (game name + tag line)

        IMPORTANT: Always uses primary_key because PUUID is per-key encrypted
        """
        host = self.REGIONAL_HOSTS.get(region, self.REGIONAL_HOSTS["americas"])
        encoded_game_name = quote(game_name)
        encoded_tag_line = quote(tag_line)

        url = f"https://{host}/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"

        return await self._make_request("GET", url, use_primary_key=True)

    async def get_account_by_puuid(self, puuid: str, region: str = "americas") -> Optional[Dict[str, Any]]:
        """Get account by PUUID

        IMPORTANT: Always uses primary_key because PUUID is per-key encrypted
        """
        host = self.REGIONAL_HOSTS.get(region, self.REGIONAL_HOSTS["americas"])
        url = f"https://{host}/riot/account/v1/accounts/by-puuid/{puuid}"

        return await self._make_request("GET", url, use_primary_key=True)

    # Summoner API (Platform routing)
    async def get_summoner_by_puuid(self, puuid: str, platform: str = None) -> Optional[Dict[str, Any]]:
        """Get summoner by PUUID

        IMPORTANT: Always uses primary_key because PUUID is per-key encrypted
        """
        platform = platform or self.default_region
        host = self.PLATFORM_HOSTS.get(platform.lower())

        if not host:
            raise ValueError(f"Unknown platform: {platform}")

        url = f"https://{host}/lol/summoner/v4/summoners/by-puuid/{puuid}"

        return await self._make_request("GET", url, use_primary_key=True)

    async def get_summoner_by_summoner_id(self, summoner_id: str, platform: str = None) -> Optional[Dict[str, Any]]:
        """Get summoner by summoner ID"""
        platform = platform or self.default_region
        host = self.PLATFORM_HOSTS.get(platform.lower())

        if not host:
            raise ValueError(f"Unknown platform: {platform}")

        url = f"https://{host}/lol/summoner/v4/summoners/{summoner_id}"

        return await self._make_request("GET", url)

    # Match API (Regional routing)
    async def get_match_history(
        self,
        puuid: str,
        count: int = 20,
        queue_id: Optional[int] = None,
        start: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        platform: str = None
    ) -> Optional[List[str]]:
        """Get match history (list of match IDs)

        IMPORTANT: Always uses primary_key because URL contains PUUID which is per-key encrypted
        """
        # Determine region from platform
        platform = platform or self.default_region
        region = self.PLATFORM_TO_REGION.get(platform.lower(), "americas")
        host = self.REGIONAL_HOSTS[region]

        url = f"https://{host}/lol/match/v5/matches/by-puuid/{puuid}/ids"

        params = {"count": min(count, 100)}  # API limit
        if queue_id is not None:
            params["queue"] = queue_id
        if start is not None:
            params["start"] = start
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        return await self._make_request("GET", url, params=params, use_primary_key=True)

    async def get_match_details(self, match_id: str, region: str = "americas") -> Optional[Dict[str, Any]]:
        """Get detailed match information"""
        host = self.REGIONAL_HOSTS.get(region, self.REGIONAL_HOSTS["americas"])
        url = f"https://{host}/lol/match/v5/matches/{match_id}"

        return await self._make_request("GET", url)

    async def get_match_timeline(self, match_id: str, region: str = "americas") -> Optional[Dict[str, Any]]:
        """Get match timeline"""
        host = self.REGIONAL_HOSTS.get(region, self.REGIONAL_HOSTS["americas"])
        url = f"https://{host}/lol/match/v5/matches/{match_id}/timeline"

        return await self._make_request("GET", url)

    # League API (Platform routing)
    async def get_league_entries_by_summoner(self, summoner_id: str, platform: str = None) -> Optional[List[Dict[str, Any]]]:
        """Get ranked league entries for summoner"""
        platform = platform or self.default_region
        host = self.PLATFORM_HOSTS.get(platform.lower())

        if not host:
            raise ValueError(f"Unknown platform: {platform}")

        url = f"https://{host}/lol/league/v4/entries/by-summoner/{summoner_id}"

        return await self._make_request("GET", url)

    async def get_challenger_league(self, queue: str = "RANKED_SOLO_5x5", platform: str = None) -> Optional[Dict[str, Any]]:
        """Get challenger league"""
        platform = platform or self.default_region
        host = self.PLATFORM_HOSTS.get(platform.lower())

        if not host:
            raise ValueError(f"Unknown platform: {platform}")

        url = f"https://{host}/lol/league/v4/challengerleagues/by-queue/{queue}"

        return await self._make_request("GET", url)

    async def get_grandmaster_league(self, queue: str = "RANKED_SOLO_5x5", platform: str = None) -> Optional[Dict[str, Any]]:
        """Get grandmaster league"""
        platform = platform or self.default_region
        host = self.PLATFORM_HOSTS.get(platform.lower())

        if not host:
            raise ValueError(f"Unknown platform: {platform}")

        url = f"https://{host}/lol/league/v4/grandmasterleagues/by-queue/{queue}"

        return await self._make_request("GET", url)

    async def get_master_league(self, queue: str = "RANKED_SOLO_5x5", platform: str = None) -> Optional[Dict[str, Any]]:
        """Get master league"""
        platform = platform or self.default_region
        host = self.PLATFORM_HOSTS.get(platform.lower())

        if not host:
            raise ValueError(f"Unknown platform: {platform}")

        url = f"https://{host}/lol/league/v4/masterleagues/by-queue/{queue}"

        return await self._make_request("GET", url)

    # Data Dragon (Static data)
    async def get_champion_data(self, version: str = "14.22.1", language: str = "en_US") -> Optional[Dict[str, Any]]:
        """Get champion data from Data Dragon"""
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{language}/champion.json"

        return await self._make_request("GET", url)

    async def get_item_data(self, version: str = "14.22.1", language: str = "en_US") -> Optional[Dict[str, Any]]:
        """Get item data from Data Dragon"""
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{language}/item.json"

        return await self._make_request("GET", url)

    async def get_summoner_spell_data(self, version: str = "14.22.1", language: str = "en_US") -> Optional[Dict[str, Any]]:
        """Get summoner spell data from Data Dragon"""
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{language}/summoner.json"

        return await self._make_request("GET", url)

    async def get_versions(self) -> Optional[List[str]]:
        """Get available Data Dragon versions"""
        url = "https://ddragon.leagueoflegends.com/api/versions.json"

        return await self._make_request("GET", url)

    # Utility methods
    def get_region_from_platform(self, platform: str) -> str:
        """Get regional routing from platform"""
        return self.PLATFORM_TO_REGION.get(platform.lower(), "americas")

    async def validate_riot_id(self, game_name: str, tag_line: str, region: str = "americas") -> bool:
        """Validate if a Riot ID exists"""
        account = await self.get_account_by_riot_id(game_name, tag_line, region)
        return account is not None

    async def get_summoner_full_data(self, game_name: str, tag_line: str, platform: str = None) -> Optional[Dict[str, Any]]:
        """Get complete summoner data including account and league info"""
        platform = platform or self.default_region
        region = self.get_region_from_platform(platform)

        try:
            # Get account data
            account = await self.get_account_by_riot_id(game_name, tag_line, region)
            if not account:
                return None

            # Get summoner data
            summoner = await self.get_summoner_by_puuid(account["puuid"], platform)
            if not summoner:
                return None

            # Get ranked data
            league_entries = await self.get_league_entries_by_summoner(summoner["id"], platform)

            return {
                "account": account,
                "summoner": summoner,
                "ranked": league_entries or [],
                "platform": platform,
                "region": region
            }

        except Exception as e:
            logger.error("Error getting full summoner data", error=str(e))
            return None


# Global singleton instance
riot_client = RiotAPIClient()
