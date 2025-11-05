"""
AgentContext - Agent间消息传递与上下文共享

提供Agent间的数据共享、增量分析和避免重复计算的机制
Phase 4 Day 3: 新增缓存预热功能
"""

import json
import sys
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future


class AgentContext:
    """
    Agent执行上下文 (Phase 4: 优化内存管理)

    管理Agent间的数据共享和消息传递：
    - 存储每个Agent的执行结果
    - 提供统一的数据访问接口
    - 支持增量分析
    - 避免重复计算
    - LRU缓存管理（自动驱逐最久未使用数据）
    """

    def __init__(self, user_request: str, packs_dir: str, max_cache_size_mb: int = 500):
        """
        初始化Agent上下文

        Args:
            user_request: 原始用户请求
            packs_dir: Player Pack数据目录
            max_cache_size_mb: 最大缓存大小（MB），默认500MB
        """
        self.user_request = user_request
        self.packs_dir = packs_dir
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # Convert to bytes

        # Agent执行结果存储
        self._results: Dict[str, Dict[str, Any]] = {}

        # 执行顺序记录
        self._execution_order: List[str] = []

        # 共享数据缓存
        self._shared_cache: Dict[str, Any] = {}

        # 缓存元数据 (Phase 4: LRU tracking)
        self._cache_metadata: Dict[str, Dict[str, Any]] = {}

        # 元数据
        self._metadata = {
            "created_at": datetime.now().isoformat(),
            "total_agents_executed": 0,
            "cache_evictions": 0,  # Track eviction count
            "peak_cache_size_mb": 0.0  # Track peak memory usage
        }

        # 线程锁 (Phase 2 并行执行安全保护)
        self._lock = threading.Lock()

        # Phase 4 Day 3: 缓存预热相关
        self._preload_futures: Dict[str, Future] = {}  # 存储后台加载任务

    def add_agent_result(
        self,
        agent_name: str,
        data: Dict[str, Any],
        report: str,
        execution_time: float = 0.0
    ) -> None:
        """
        添加Agent执行结果 (线程安全)

        Args:
            agent_name: Agent名称
            data: Agent返回的结构化数据
            report: Agent生成的报告文本
            execution_time: 执行时间（秒）
        """
        with self._lock:
            self._results[agent_name] = {
                "data": data,
                "report": report,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

            self._execution_order.append(agent_name)
            self._metadata["total_agents_executed"] += 1

    def get_agent_result(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定Agent的执行结果

        Args:
            agent_name: Agent名称

        Returns:
            Agent结果字典，如果不存在返回None
        """
        return self._results.get(agent_name)

    def get_agent_data(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定Agent的数据部分

        Args:
            agent_name: Agent名称

        Returns:
            Agent数据字典，如果不存在返回None
        """
        result = self._results.get(agent_name)
        return result["data"] if result else None

    def get_agent_report(self, agent_name: str) -> Optional[str]:
        """
        获取指定Agent的报告文本

        Args:
            agent_name: Agent名称

        Returns:
            报告文本，如果不存在返回None
        """
        result = self._results.get(agent_name)
        return result["report"] if result else None

    def has_agent_result(self, agent_name: str) -> bool:
        """
        检查是否存在指定Agent的结果

        Args:
            agent_name: Agent名称

        Returns:
            是否存在结果
        """
        return agent_name in self._results

    def get_previous_agents(self) -> List[str]:
        """
        获取已执行的Agent列表（按执行顺序）

        Returns:
            Agent名称列表
        """
        return self._execution_order.copy()

    def set_shared_data(self, key: str, value: Any) -> None:
        """
        设置共享数据

        Args:
            key: 数据键
            value: 数据值
        """
        self._shared_cache[key] = value

    def add_shared_data(self, key: str, data: Any, summary: str = "") -> None:
        """
        添加共享数据（带元数据、LRU缓存管理）(线程安全)

        Phase 4 优化: 自动内存管理
        - 计算数据大小
        - 如果超出限制，驱逐最久未使用的数据
        - 追踪访问时间用于LRU

        Args:
            key: 数据键
            data: 数据值
            summary: 数据摘要描述（可选）
        """
        with self._lock:
            # 1. 计算数据大小（使用sys.getsizeof估算）
            data_size = sys.getsizeof(data)

            # 对于复杂对象（list, dict），递归计算
            if isinstance(data, (list, dict)):
                data_size = self._calculate_deep_size(data)

            # 2. 检查是否需要驱逐旧数据
            current_size = self._current_cache_size()
            while current_size + data_size > self.max_cache_size and self._shared_cache:
                evicted_key = self._evict_least_recently_used()
                if not evicted_key:
                    break  # 无法驱逐更多数据
                current_size = self._current_cache_size()

            # 3. 添加新数据
            self._shared_cache[key] = data
            self._cache_metadata[key] = {
                "size": data_size,
                "last_access": time.time(),
                "summary": summary,
                "access_count": 0
            }

            # 4. 更新峰值内存统计
            current_size_mb = self._current_cache_size() / (1024 * 1024)
            if current_size_mb > self._metadata["peak_cache_size_mb"]:
                self._metadata["peak_cache_size_mb"] = current_size_mb

            # 5. 保存summary到元数据
            if summary:
                self._metadata[f"{key}_summary"] = summary

    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """
        获取共享数据（Phase 4: 更新LRU访问时间）

        Args:
            key: 数据键
            default: 默认值

        Returns:
            数据值
        """
        # Update access time for LRU tracking
        if key in self._cache_metadata:
            with self._lock:
                self._cache_metadata[key]["last_access"] = time.time()
                self._cache_metadata[key]["access_count"] += 1

        return self._shared_cache.get(key, default)

    def has_shared_data(self, key: str) -> bool:
        """
        检查是否存在共享数据

        Args:
            key: 数据键

        Returns:
            是否存在
        """
        return key in self._shared_cache

    def _calculate_deep_size(self, obj: Any) -> int:
        """
        递归计算对象的深度大小（Phase 4 优化）

        Args:
            obj: 要计算的对象

        Returns:
            对象大小（字节）
        """
        size = sys.getsizeof(obj)

        if isinstance(obj, dict):
            size += sum(self._calculate_deep_size(k) + self._calculate_deep_size(v)
                       for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set)):
            size += sum(self._calculate_deep_size(item) for item in obj)

        return size

    def _current_cache_size(self) -> int:
        """
        计算当前缓存总大小（Phase 4 优化）

        Returns:
            缓存大小（字节）
        """
        return sum(meta["size"] for meta in self._cache_metadata.values())

    def _evict_least_recently_used(self) -> Optional[str]:
        """
        驱逐最久未使用的缓存项（Phase 4 优化）

        Returns:
            被驱逐的key，如果无法驱逐则返回None
        """
        if not self._cache_metadata:
            return None

        # 找到最久未访问的项
        lru_key = min(
            self._cache_metadata.items(),
            key=lambda x: x[1]["last_access"]
        )[0]

        # 驱逐该项
        if lru_key in self._shared_cache:
            evicted_size = self._cache_metadata[lru_key]["size"]
            del self._shared_cache[lru_key]
            del self._cache_metadata[lru_key]
            self._metadata["cache_evictions"] += 1

            # 可选：记录驱逐日志
            # print(f"⚠️  LRU Cache: 驱逐 '{lru_key}' ({evicted_size / 1024 / 1024:.2f} MB)")

            return lru_key

        return None

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息（Phase 4 新增）

        Returns:
            缓存统计数据
        """
        current_size_mb = self._current_cache_size() / (1024 * 1024)
        max_size_mb = self.max_cache_size / (1024 * 1024)

        return {
            "current_size_mb": round(current_size_mb, 2),
            "max_size_mb": round(max_size_mb, 2),
            "usage_percent": round((current_size_mb / max_size_mb) * 100, 1),
            "cached_items": len(self._shared_cache),
            "peak_size_mb": round(self._metadata["peak_cache_size_mb"], 2),
            "total_evictions": self._metadata["cache_evictions"],
            "items_detail": [
                {
                    "key": key,
                    "size_mb": round(meta["size"] / (1024 * 1024), 2),
                    "access_count": meta["access_count"],
                    "last_access_ago_sec": round(time.time() - meta["last_access"], 1)
                }
                for key, meta in self._cache_metadata.items()
            ]
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        获取上下文摘要 (线程安全)

        Returns:
            摘要信息
        """
        with self._lock:
            return {
                "user_request": self.user_request,
                "total_agents_executed": self._metadata["total_agents_executed"],
                "execution_order": self._execution_order.copy(),
                "agents_results": list(self._results.keys()),
                "shared_cache_keys": list(self._shared_cache.keys()),
                "created_at": self._metadata["created_at"]
            }

    def export_for_agent(self, target_agent: str) -> Dict[str, Any]:
        """
        导出供特定Agent使用的上下文信息

        Args:
            target_agent: 目标Agent名称

        Returns:
            精简的上下文信息
        """
        # 获取之前执行的Agents
        previous_agents = [a for a in self._execution_order if a != target_agent]

        # 构建精简的上下文
        context_for_agent = {
            "user_request": self.user_request,
            "previous_agents": previous_agents,
            "available_data": {}
        }

        # 添加之前Agents的关键数据摘要
        for agent_name in previous_agents:
            result = self._results.get(agent_name)
            if result:
                # 只提供数据摘要，不包括完整报告（减少token消耗）
                data = result["data"]
                context_for_agent["available_data"][agent_name] = {
                    "summary": self._extract_data_summary(agent_name, data),
                    "execution_time": result["execution_time"]
                }

        # 添加共享缓存
        if self._shared_cache:
            context_for_agent["shared_cache"] = self._shared_cache.copy()

        return context_for_agent

    def prewarm_cache(self, workflow_name: str) -> None:
        """
        缓存预热：在工作流开始前后台并行加载数据（Phase 4 Day 3）

        根据工作流类型，智能预测需要的数据并后台加载，
        当 Agent 需要时数据已经准备好。

        Args:
            workflow_name: 工作流名称

        使用示例:
            context = AgentContext("用户请求", "data/packs/player")
            context.prewarm_cache("comprehensive_profile")  # 后台开始加载
            # ... 执行其他初始化 ...
            # 当Agent需要时，数据已加载完成
        """
        from src.agents.shared.pack_data_loader import PackDataLoader

        # 定义不同工作流的数据需求
        workflow_requirements = {
            "quick_diagnosis": ["recent_5_packs"],
            "comprehensive_profile": ["all_packs"],
            "role_mastery": ["all_packs"],
            "seasonal_review": ["all_packs"],
        }

        requirements = workflow_requirements.get(workflow_name, [])

        if not requirements:
            return  # 无需预热

        print(f"🔄 缓存预热: {workflow_name} 工作流")

        # 创建后台加载任务
        executor = ThreadPoolExecutor(max_workers=1)

        for req in requirements:
            if req == "recent_5_packs":
                # 后台加载最近5个版本
                future = executor.submit(self._preload_recent_packs, 5)
                self._preload_futures["recent_packs"] = future
                print(f"   🔄 后台加载: 最近5个版本")

            elif req == "all_packs":
                # 后台加载所有版本（使用并行加载器）
                future = executor.submit(self._preload_all_packs)
                self._preload_futures["all_packs"] = future
                print(f"   🔄 后台加载: 所有版本")

        executor.shutdown(wait=False)  # 不等待，让任务在后台运行

    def _preload_recent_packs(self, n: int = 5):
        """后台加载最近N个版本"""
        from src.agents.shared.pack_data_loader import PackDataLoader

        try:
            loader = PackDataLoader(self.packs_dir)
            packs = loader.load_recent_n_parallel(n=n, max_workers=3)

            # 将加载的数据添加到缓存
            self.add_shared_data(
                key="recent_packs",
                data=list(packs.values()),
                summary=f"{len(packs)}个最近版本（预热加载）"
            )
            print(f"   ✅ 预热完成: recent_packs ({len(packs)} 个版本)")

        except Exception as e:
            print(f"   ⚠️  预热失败: recent_packs - {e}")

    def _preload_all_packs(self):
        """后台加载所有版本"""
        from src.agents.shared.pack_data_loader import PackDataLoader

        try:
            loader = PackDataLoader(self.packs_dir)
            packs = loader.load_all_parallel(max_workers=5)

            # 转换为列表格式（按patch排序）
            all_packs_list = [packs[patch] for patch in sorted(packs.keys())]

            # 将加载的数据添加到缓存
            self.add_shared_data(
                key="all_packs",
                data=all_packs_list,
                summary=f"{len(all_packs_list)}个版本（预热加载）"
            )
            print(f"   ✅ 预热完成: all_packs ({len(all_packs_list)} 个版本)")

        except Exception as e:
            print(f"   ⚠️  预热失败: all_packs - {e}")

    def wait_for_preload(self, key: str, timeout: float = 30.0) -> bool:
        """
        等待特定预热任务完成（Phase 4 Day 3）

        Args:
            key: 预热任务的key（如 "all_packs", "recent_packs"）
            timeout: 超时时间（秒），默认30秒

        Returns:
            是否成功完成

        使用示例:
            context.prewarm_cache("comprehensive_profile")
            # ... 做其他事情 ...
            if context.wait_for_preload("all_packs"):
                # 数据已准备好，可以使用
                packs = context.get_shared_data("all_packs")
        """
        future = self._preload_futures.get(key)

        if not future:
            # 没有预热任务，检查数据是否已在缓存中
            return self.has_shared_data(key)

        try:
            # 等待任务完成
            future.result(timeout=timeout)
            return True
        except Exception as e:
            print(f"⚠️  等待预热失败 ({key}): {e}")
            return False

    def get_or_wait_preload(self, key: str, default: Any = None, timeout: float = 30.0) -> Any:
        """
        获取预热数据，如果正在加载则等待完成（Phase 4 Day 3）

        这是最便利的方法，自动处理等待逻辑。

        Args:
            key: 数据key
            default: 默认值
            timeout: 等待超时（秒）

        Returns:
            数据值

        使用示例:
            context.prewarm_cache("comprehensive_profile")
            # ... Agent执行到需要数据的地方 ...
            all_packs = context.get_or_wait_preload("all_packs")  # 自动等待加载完成
        """
        # 如果数据已在缓存中，直接返回
        if self.has_shared_data(key):
            return self.get_shared_data(key, default)

        # 如果有预热任务，等待完成
        if key in self._preload_futures:
            success = self.wait_for_preload(key, timeout)
            if success:
                return self.get_shared_data(key, default)

        # 返回默认值
        return default

    def _extract_data_summary(self, agent_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取数据摘要（避免传递完整数据）

        Args:
            agent_name: Agent名称
            data: 完整数据

        Returns:
            数据摘要
        """
        summaries = {
            "annual_summary": lambda d: {
                "total_games": d.get("summary", {}).get("total_games", 0),
                "overall_winrate": d.get("summary", {}).get("overall_winrate", 0),
                "patches_analyzed": len(d.get("patches", [])),
                "top_champions": len(d.get("top_champions", []))
            },

            "weakness_analysis": lambda d: {
                "low_winrate_count": len(d.get("low_winrate_champions", [])),
                "weak_roles_count": len(d.get("weak_roles", [])),
                "patches_analyzed": d.get("total_patches_analyzed", 0)
            },

            "champion_recommendation": lambda d: {
                "recommendations_count": len(d.get("recommendations", [])),
                "core_champions_count": len(d.get("champion_pool", {}).get("core_champions", []))
            },

            "role_specialization": lambda d: {
                "role": d.get("role", "unknown"),
                "total_games": d.get("summary", {}).get("total_games", 0),
                "mastery_score": d.get("summary", {}).get("role_mastery_score", "N/A")
            },

            "multi_version": lambda d: {
                "total_patches": d.get("summary", {}).get("total_patches", 0),
                "unique_champions": d.get("summary", {}).get("unique_champion_roles", 0)
            }
        }

        # 使用专门的提取函数，如果没有则返回基本摘要
        extractor = summaries.get(agent_name, lambda d: {"has_data": True})

        try:
            return extractor(data)
        except Exception:
            return {"has_data": True, "error": "Failed to extract summary"}

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于序列化）

        Returns:
            完整的上下文数据
        """
        return {
            "user_request": self.user_request,
            "packs_dir": self.packs_dir,
            "results": self._results,
            "execution_order": self._execution_order,
            "shared_cache": self._shared_cache,
            "metadata": self._metadata
        }

    def save(self, output_path: str) -> None:
        """
        保存上下文到文件

        Args:
            output_path: 输出文件路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, input_path: str) -> 'AgentContext':
        """
        从文件加载上下文

        Args:
            input_path: 输入文件路径

        Returns:
            AgentContext实例
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        context = cls(
            user_request=data["user_request"],
            packs_dir=data["packs_dir"]
        )

        context._results = data["results"]
        context._execution_order = data["execution_order"]
        context._shared_cache = data["shared_cache"]
        context._metadata = data["metadata"]

        return context


def format_context_for_prompt(context: AgentContext, target_agent: str) -> str:
    """
    格式化上下文信息为LLM友好的文本

    Args:
        context: Agent上下文
        target_agent: 目标Agent名称

    Returns:
        格式化的文本
    """
    lines = [f"# Agent执行上下文\n"]

    # 用户请求
    lines.append(f"**原始用户请求**: {context.user_request}\n")

    # 已执行的Agents
    previous = context.get_previous_agents()
    if previous:
        lines.append(f"**已执行的Agents**: {', '.join(previous)}\n")

    # 上下文数据
    ctx_data = context.export_for_agent(target_agent)

    if ctx_data.get("available_data"):
        lines.append("## 可用的上下文数据\n")

        for agent_name, summary in ctx_data["available_data"].items():
            lines.append(f"### {agent_name}")
            summary_data = summary.get("summary", {})
            for key, value in summary_data.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

    # 共享缓存
    if ctx_data.get("shared_cache"):
        lines.append("## 共享数据缓存\n")
        for key, value in ctx_data["shared_cache"].items():
            lines.append(f"- **{key}**: {value}")

    return "\n".join(lines)
