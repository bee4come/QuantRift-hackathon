"""
LLM结果缓存系统 (Phase 1.3)

基于哈希的智能缓存，减少重复LLM调用，降低成本40-60%。
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import threading


class LLMCache:
    """
    LLM结果缓存管理器

    特性:
    - 基于prompt+system内容的SHA256哈希键
    - 可配置TTL过期时间
    - 内存+磁盘双层缓存
    - 缓存命中率统计
    - 线程安全
    - 自动清理过期缓存

    用法:
        cache = LLMCache(cache_dir="data/cache", ttl_hours=24)

        # 尝试从缓存获取
        cached = cache.get(prompt, system, model)
        if cached:
            return cached

        # 缓存未命中，调用LLM
        result = llm.generate(prompt, system=system)

        # 存储到缓存
        cache.set(prompt, system, model, result)
    """

    def __init__(
        self,
        cache_dir: str = "data/cache/llm",
        ttl_hours: int = 24,
        max_memory_items: int = 100,
        enable_disk_cache: bool = True
    ):
        """
        初始化缓存管理器

        Args:
            cache_dir: 磁盘缓存目录
            ttl_hours: 缓存有效期（小时）
            max_memory_items: 内存缓存最大条目数
            enable_disk_cache: 是否启用磁盘缓存
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.ttl_seconds = ttl_hours * 3600
        self.max_memory_items = max_memory_items
        self.enable_disk_cache = enable_disk_cache

        # 内存缓存 (LRU策略)
        self.memory_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.cache_access_order = []  # 用于LRU

        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "disk_reads": 0,
            "disk_writes": 0
        }

        # 线程锁
        self.lock = threading.Lock()

        # 创建缓存目录
        if self.enable_disk_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_hash(
        self,
        prompt: str,
        system: Optional[str],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        计算缓存键的哈希值

        Args:
            prompt: 用户prompt
            system: 系统prompt
            model: 模型ID
            temperature: 温度参数（影响结果）
            max_tokens: 最大token数（不影响结果，但影响截断）

        Returns:
            SHA256哈希字符串
        """
        # 组合所有影响结果的参数
        key_parts = [
            f"prompt:{prompt}",
            f"system:{system or ''}",
            f"model:{model}",
            f"temp:{temperature or 0.7}",  # 温度影响结果
        ]

        # max_tokens不影响结果内容（只影响截断），不包含在哈希中
        # 这允许不同max_tokens的相同查询共享缓存

        key_string = "||".join(key_parts)
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()

    def get(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = "haiku",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        从缓存获取LLM结果

        Args:
            prompt: 用户prompt
            system: 系统prompt
            model: 模型ID
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            缓存的结果dict或None（未命中）
        """
        with self.lock:
            cache_key = self._compute_hash(prompt, system, model, temperature, max_tokens)

            # 1. 检查内存缓存
            if cache_key in self.memory_cache:
                cached_data, cached_time = self.memory_cache[cache_key]

                # 检查是否过期
                if time.time() - cached_time < self.ttl_seconds:
                    # 更新访问顺序 (LRU)
                    if cache_key in self.cache_access_order:
                        self.cache_access_order.remove(cache_key)
                    self.cache_access_order.append(cache_key)

                    self.stats["hits"] += 1
                    return cached_data
                else:
                    # 过期，删除
                    del self.memory_cache[cache_key]
                    if cache_key in self.cache_access_order:
                        self.cache_access_order.remove(cache_key)

            # 2. 检查磁盘缓存
            if self.enable_disk_cache:
                cache_file = self.cache_dir / f"{cache_key}.json"
                if cache_file.exists():
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_entry = json.load(f)

                        # 检查是否过期
                        if time.time() - cache_entry["timestamp"] < self.ttl_seconds:
                            # 加载到内存缓存
                            self.memory_cache[cache_key] = (cache_entry["data"], cache_entry["timestamp"])
                            self.cache_access_order.append(cache_key)

                            # 内存缓存满了，移除最旧的
                            if len(self.memory_cache) > self.max_memory_items:
                                self._evict_lru()

                            self.stats["hits"] += 1
                            self.stats["disk_reads"] += 1
                            return cache_entry["data"]
                        else:
                            # 磁盘缓存也过期，删除文件
                            cache_file.unlink()
                    except Exception as e:
                        # 缓存损坏，忽略
                        pass

            # 缓存未命中
            self.stats["misses"] += 1
            return None

    def set(
        self,
        prompt: str,
        system: Optional[str],
        model: str,
        result: Dict[str, Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        存储LLM结果到缓存

        Args:
            prompt: 用户prompt
            system: 系统prompt
            model: 模型ID
            result: LLM结果dict
            temperature: 温度参数
            max_tokens: 最大token数
        """
        # Compute cache key and prepare data BEFORE acquiring lock
        cache_key = self._compute_hash(prompt, system, model, temperature, max_tokens)
        current_time = time.time()

        # Prepare disk cache entry BEFORE acquiring lock
        cache_entry = None
        cache_file = None
        if self.enable_disk_cache:
            cache_file = self.cache_dir / f"{cache_key}.json"
            cache_entry = {
                "data": result,
                "timestamp": current_time,
                "prompt_preview": prompt[:200],  # 前200字符用于调试
                "model": model,
                "created_at": datetime.now().isoformat()
            }

        # CRITICAL FIX: Only hold lock for memory operations, NOT disk I/O
        with self.lock:
            # 存储到内存缓存
            self.memory_cache[cache_key] = (result, current_time)
            self.cache_access_order.append(cache_key)

            # 内存缓存满了，移除最旧的
            if len(self.memory_cache) > self.max_memory_items:
                self._evict_lru()

            self.stats["sets"] += 1

        # CRITICAL FIX: Write to disk OUTSIDE the lock to prevent deadlock
        if self.enable_disk_cache and cache_entry and cache_file:
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_entry, f, ensure_ascii=False, indent=2)
                with self.lock:
                    self.stats["disk_writes"] += 1
            except Exception as e:
                # 磁盘写入失败，不影响功能
                pass

    def _evict_lru(self):
        """移除最近最少使用的缓存项 (LRU eviction)"""
        if not self.cache_access_order:
            return

        # 移除最旧的
        oldest_key = self.cache_access_order.pop(0)
        if oldest_key in self.memory_cache:
            del self.memory_cache[oldest_key]
            self.stats["evictions"] += 1

    def clear(self):
        """清空所有缓存"""
        with self.lock:
            # 清空内存缓存
            self.memory_cache.clear()
            self.cache_access_order.clear()

            # 清空磁盘缓存
            if self.enable_disk_cache:
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        cache_file.unlink()
                    except:
                        pass

            # 重置统计
            self.stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "evictions": 0,
                "disk_reads": 0,
                "disk_writes": 0
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计dict包含:
            - hits: 缓存命中次数
            - misses: 缓存未命中次数
            - hit_rate: 命中率 (0.0-1.0)
            - total_requests: 总请求数
            - memory_items: 内存缓存条目数
            - evictions: 缓存驱逐次数
            - disk_reads: 磁盘读取次数
            - disk_writes: 磁盘写入次数
        """
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0.0

            return {
                **self.stats,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                "memory_items": len(self.memory_cache),
                "cost_reduction": f"{hit_rate * 100:.1f}%"  # 假设每次命中节省100%成本
            }

    def cleanup_expired(self):
        """清理过期的缓存条目"""
        with self.lock:
            current_time = time.time()

            # 清理内存缓存
            expired_keys = [
                key for key, (_, timestamp) in self.memory_cache.items()
                if current_time - timestamp >= self.ttl_seconds
            ]

            for key in expired_keys:
                del self.memory_cache[key]
                if key in self.cache_access_order:
                    self.cache_access_order.remove(key)

            # 清理磁盘缓存
            if self.enable_disk_cache:
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        with open(cache_file, 'r') as f:
                            cache_entry = json.load(f)

                        if current_time - cache_entry["timestamp"] >= self.ttl_seconds:
                            cache_file.unlink()
                    except:
                        # 损坏的缓存文件，删除
                        try:
                            cache_file.unlink()
                        except:
                            pass


# 全局缓存实例（单例模式）
_global_cache: Optional[LLMCache] = None


def get_llm_cache(
    cache_dir: str = "data/cache/llm",
    ttl_hours: int = 24
) -> LLMCache:
    """
    获取全局LLM缓存实例（单例）

    Args:
        cache_dir: 缓存目录
        ttl_hours: 缓存有效期（小时）

    Returns:
        LLMCache实例
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = LLMCache(
            cache_dir=cache_dir,
            ttl_hours=ttl_hours
        )

    return _global_cache
