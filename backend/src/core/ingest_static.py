#!/usr/bin/env python3
"""
静态数据摄入引擎
基于权威清单：DDragon + CDragon → 版本化静态底座
"""

import asyncio
import aiohttp
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StaticDataIngester:
    def __init__(self, config_path: str = "configs/data_sources.yml"):
        """初始化静态数据摄入器"""
        self.config = self._load_config(config_path)
        self.session = None

        # DDragon 基础 URL
        self.ddragon_base = "https://ddragon.leagueoflegends.com"

        # CDragon 基础 URL
        self.cdragon_base = "https://raw.communitydragon.org"

        # 支持的语言
        self.locale = "en_US"

        # 数据路径映射
        self.data_paths = {
            "versions": "/api/versions.json",
            "realms": "/realms/{region}.json",
            "champions": "/cdn/{version}/data/{locale}/champion.json",
            "champion_detail": "/cdn/{version}/data/{locale}/champion/{name}.json",
            "items": "/cdn/{version}/data/{locale}/item.json",
            "runes": "/cdn/{version}/data/{locale}/runesReforged.json",
            "summoner_spells": "/cdn/{version}/data/{locale}/summoner.json"
        }

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载数据源配置"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "regions": ["na1", "euw1", "kr"],
            "max_versions": 12,  # 最近12个版本
            "rate_limit": {
                "requests_per_second": 10,
                "concurrent_limit": 5
            },
            "retry": {
                "max_attempts": 3,
                "backoff_factor": 2.0
            },
            "concurrency": {
                "max_concurrent_requests": 5,
                "timeout_seconds": 30
            }
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        # 确保配置存在
        if not self.config:
            self.config = self._get_default_config()

        concurrent_limit = self.config.get("rate_limit", {}).get("concurrent_limit", 5)
        timeout_seconds = self.config.get("concurrency", {}).get("timeout_seconds", 30)

        connector = aiohttp.TCPConnector(limit=concurrent_limit)
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def fetch_json(self, url: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """获取 JSON 数据（带重试）"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate limited
                    wait_time = 2 ** retry_count
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    return await self.fetch_json(url, retry_count + 1)
                else:
                    logger.error(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            if retry_count < self.config["retry"]["max_attempts"]:
                wait_time = self.config["retry"]["backoff_factor"] ** retry_count
                logger.warning(f"Request failed: {e}, retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
                return await self.fetch_json(url, retry_count + 1)
            else:
                logger.error(f"Failed to fetch {url} after {retry_count} retries: {e}")
                return None

    async def get_versions(self) -> List[str]:
        """获取版本列表"""
        logger.info("Fetching version list from DDragon")
        url = f"{self.ddragon_base}{self.data_paths['versions']}"

        versions = await self.fetch_json(url)
        if not versions:
            raise RuntimeError("Failed to fetch version list")

        # 限制最新N个版本
        max_versions = self.config.get("max_versions", 12)
        recent_versions = versions[:max_versions]

        logger.info(f"Found {len(recent_versions)} recent versions: {recent_versions[:3]}...")
        return recent_versions

    async def get_realms(self, region: str = "na1") -> Dict[str, Any]:
        """获取区域信息"""
        logger.info(f"Fetching realm info for {region}")
        url = f"{self.ddragon_base}{self.data_paths['realms'].format(region=region)}"

        realms = await self.fetch_json(url)
        if not realms:
            logger.warning(f"Failed to fetch realms for {region}")
            return {}

        return realms

    async def fetch_ddragon_data(self, version: str, data_type: str) -> Optional[Dict[str, Any]]:
        """获取 DDragon 数据"""
        if data_type not in self.data_paths:
            logger.error(f"Unknown data type: {data_type}")
            return None

        url = f"{self.ddragon_base}{self.data_paths[data_type].format(version=version, locale=self.locale)}"
        logger.info(f"Fetching {data_type} for version {version}")

        return await self.fetch_json(url)

    async def fetch_cdragon_data(self, version: str, data_type: str) -> Optional[Dict[str, Any]]:
        """获取 CDragon 数据"""
        # CDragon 数据路径映射
        cdragon_paths = {
            "items": f"/{version}/plugins/rcp-be-lol-game-data/global/default/v1/items.json",
            "perks": f"/{version}/plugins/rcp-be-lol-game-data/global/default/v1/perks.json",
            "perk_styles": f"/{version}/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json",
            "champion_summary": f"/{version}/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json"
        }

        if data_type not in cdragon_paths:
            logger.warning(f"CDragon data type {data_type} not supported")
            return None

        # 对于 latest 使用 "latest"，其他使用版本号
        tag = "latest" if version == "latest" else version
        url = f"{self.cdragon_base}{cdragon_paths[data_type].format(version=tag)}"

        logger.info(f"Fetching CDragon {data_type} for version {version}")
        return await self.fetch_json(url)

    async def process_champion_details(self, version: str, champion_list: Dict[str, Any]) -> Dict[str, Any]:
        """获取英雄详细信息"""
        champion_details = {}

        if "data" not in champion_list:
            logger.warning(f"No champion data found for version {version}")
            return {}

        # 并发获取所有英雄详细信息
        tasks = []
        for champ_id, champ_info in champion_list["data"].items():
            champ_name = champ_info["id"]  # 英雄名称用于 URL
            url = f"{self.ddragon_base}/cdn/{version}/data/{self.locale}/champion/{champ_name}.json"
            tasks.append(self._fetch_champion_detail(champ_id, url))

        # 批量执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for champ_id, result in results:
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch details for champion {champ_id}: {result}")
            elif result:
                champion_details[champ_id] = result

        logger.info(f"Fetched details for {len(champion_details)} champions")
        return champion_details

    async def _fetch_champion_detail(self, champ_id: str, url: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """获取单个英雄详细信息"""
        data = await self.fetch_json(url)
        return champ_id, data

    def save_registry_data(self, version: str, data_type: str, data: Dict[str, Any], source: str = "ddragon"):
        """保存注册表数据"""
        # 创建目录
        if data_type == "champion_details":
            output_dir = Path(f"registries/champions")
        elif data_type == "champion_summary":
            output_dir = Path(f"registries/champions")
        elif data_type == "items" and source == "cdragon":
            output_dir = Path(f"registries/items_cdragon")
        elif data_type == "perks":
            output_dir = Path(f"registries/perks")
        else:
            # 标准映射
            type_mapping = {
                "champions": "champions",
                "items": "items",
                "runes": "runes",
                "summoner_spells": "summoner_spells"
            }
            output_dir = Path(f"registries/{type_mapping.get(data_type, data_type)}")

        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        output_file = output_dir / f"{version}.json"

        # 添加元数据
        registry_data = {
            "version": version,
            "data_type": data_type,
            "source": source,
            "fetched_at": datetime.utcnow().isoformat(),
            "data": data
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(registry_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {data_type} v{version} to {output_file}")

    async def ingest_version(self, version: str):
        """摄入单个版本的所有数据"""
        logger.info(f"Starting ingestion for version {version}")

        # 1. DDragon 主数据
        ddragon_tasks = [
            ("champions", self.fetch_ddragon_data(version, "champions")),
            ("items", self.fetch_ddragon_data(version, "items")),
            ("runes", self.fetch_ddragon_data(version, "runes")),
            ("summoner_spells", self.fetch_ddragon_data(version, "summoner_spells"))
        ]

        # 2. CDragon 补充数据
        cdragon_tasks = [
            ("items_cdragon", self.fetch_cdragon_data(version, "items")),
            ("perks", self.fetch_cdragon_data(version, "perks")),
            ("perk_styles", self.fetch_cdragon_data(version, "perk_styles")),
            ("champion_summary", self.fetch_cdragon_data(version, "champion_summary"))
        ]

        # 并发执行 DDragon 任务
        logger.info(f"Fetching DDragon data for version {version}")
        ddragon_results = await asyncio.gather(*[task for _, task in ddragon_tasks], return_exceptions=True)

        # 保存 DDragon 结果
        for (data_type, _), result in zip(ddragon_tasks, ddragon_results):
            if isinstance(result, Exception):
                logger.error(f"DDragon {data_type} failed: {result}")
            elif result:
                self.save_registry_data(version, data_type, result, "ddragon")

                # 获取英雄详细信息
                if data_type == "champions" and result:
                    champion_details = await self.process_champion_details(version, result)
                    if champion_details:
                        self.save_registry_data(version, "champion_details", champion_details, "ddragon")

        # 并发执行 CDragon 任务
        logger.info(f"Fetching CDragon data for version {version}")
        cdragon_results = await asyncio.gather(*[task for _, task in cdragon_tasks], return_exceptions=True)

        # 保存 CDragon 结果
        for (data_type, _), result in zip(cdragon_tasks, cdragon_results):
            if isinstance(result, Exception):
                logger.warning(f"CDragon {data_type} failed: {result}")
            elif result:
                self.save_registry_data(version, data_type, result, "cdragon")

        logger.info(f"Completed ingestion for version {version}")

    async def ingest_all_versions(self, versions: Optional[List[str]] = None):
        """摄入所有版本数据"""
        if not versions:
            versions = await self.get_versions()

        logger.info(f"Starting batch ingestion for {len(versions)} versions")

        # 顺序处理版本（避免过度并发）
        for version in versions:
            try:
                await self.ingest_version(version)
                # 版本间短暂间隔
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to ingest version {version}: {e}")
                continue

        logger.info("Completed batch ingestion")

    def create_version_mapping(self):
        """创建版本映射表"""
        mapping = {
            "versions": [],
            "latest_version": None,
            "version_timeline": {},
            "data_coverage": {}
        }

        # 扫描已保存的版本
        registries_path = Path("registries")
        if not registries_path.exists():
            logger.warning("No registries directory found")
            return mapping

        # 收集版本信息
        for entity_dir in registries_path.iterdir():
            if entity_dir.is_dir():
                entity_type = entity_dir.name
                mapping["data_coverage"][entity_type] = []

                for version_file in entity_dir.glob("*.json"):
                    version = version_file.stem
                    mapping["data_coverage"][entity_type].append(version)

                    if version not in mapping["versions"]:
                        mapping["versions"].append(version)

        # 排序版本
        mapping["versions"] = sorted(mapping["versions"], reverse=True)
        if mapping["versions"]:
            mapping["latest_version"] = mapping["versions"][0]

        # 保存映射
        mapping_file = Path("registries/version_mapping.json")
        with open(mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)

        logger.info(f"Created version mapping with {len(mapping['versions'])} versions")
        return mapping

async def main():
    parser = argparse.ArgumentParser(description="静态数据摄入工具")
    parser.add_argument("--patch", help="指定版本（不指定则获取最新版本）")
    parser.add_argument("--all", action="store_true", help="摄入所有支持的版本")
    parser.add_argument("--max-versions", type=int, default=12, help="最大版本数")
    parser.add_argument("--region", default="na1", help="区域")
    parser.add_argument("--mapping-only", action="store_true", help="仅创建版本映射")

    args = parser.parse_args()

    if args.mapping_only:
        ingester = StaticDataIngester()
        mapping = ingester.create_version_mapping()
        print(f"✅ Version mapping created: {len(mapping['versions'])} versions")
        return

    async with StaticDataIngester() as ingester:
        ingester.config["max_versions"] = args.max_versions

        try:
            if args.all:
                # 摄入所有版本
                await ingester.ingest_all_versions()
            elif args.patch:
                # 摄入指定版本
                await ingester.ingest_version(args.patch)
            else:
                # 摄入最新版本
                versions = await ingester.get_versions()
                if versions:
                    await ingester.ingest_version(versions[0])

            # 创建版本映射
            mapping = ingester.create_version_mapping()
            print(f"✅ Data ingestion completed. {len(mapping['versions'])} versions available.")

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return 1

    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))