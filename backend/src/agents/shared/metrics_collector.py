"""
性能指标收集框架 - Option A Day 2

提供统一的指标收集接口，支持：
- 时间指标：工作流执行时间、Agent运行时间、LLM调用时间
- 资源指标：内存使用、CPU使用、磁盘I/O
- 业务指标：工作流成功率、Agent成功率、缓存命中率
- 指标聚合：p50/p90/p95/p99延迟

使用示例:
    collector = MetricsCollector()

    # 记录计数器
    collector.increment("workflow_executions_total", labels={"workflow": "role_mastery"})

    # 记录时间
    with collector.timer("workflow_duration", labels={"workflow": "role_mastery"}):
        run_workflow()

    # 记录资源使用
    collector.gauge("memory_usage_mb", memory_mb, labels={"component": "agent_context"})
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import statistics


@dataclass
class MetricValue:
    """单个指标值"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class CounterMetric:
    """计数器指标（只增不减）"""
    name: str
    help_text: str
    values: Dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def increment(self, labels: Dict[str, str], amount: float = 1.0):
        """增加计数"""
        label_key = self._labels_to_key(labels)
        self.values[label_key] += amount

    def get(self, labels: Dict[str, str]) -> float:
        """获取当前值"""
        label_key = self._labels_to_key(labels)
        return self.values.get(label_key, 0.0)

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """标签转换为键"""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


@dataclass
class GaugeMetric:
    """仪表盘指标（可增可减）"""
    name: str
    help_text: str
    values: Dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def set(self, labels: Dict[str, str], value: float):
        """设置值"""
        label_key = self._labels_to_key(labels)
        self.values[label_key] = value

    def increment(self, labels: Dict[str, str], amount: float = 1.0):
        """增加值"""
        label_key = self._labels_to_key(labels)
        self.values[label_key] += amount

    def decrement(self, labels: Dict[str, str], amount: float = 1.0):
        """减少值"""
        self.increment(labels, -amount)

    def get(self, labels: Dict[str, str]) -> float:
        """获取当前值"""
        label_key = self._labels_to_key(labels)
        return self.values.get(label_key, 0.0)

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


@dataclass
class HistogramMetric:
    """直方图指标（分布统计）"""
    name: str
    help_text: str
    buckets: List[float]  # 分桶边界
    observations: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    def observe(self, labels: Dict[str, str], value: float):
        """观察一个值"""
        label_key = self._labels_to_key(labels)
        self.observations[label_key].append(value)

    def get_buckets(self, labels: Dict[str, str]) -> Dict[float, int]:
        """获取分桶统计"""
        label_key = self._labels_to_key(labels)
        observations = self.observations.get(label_key, [])

        buckets = {}
        for bucket in self.buckets:
            count = sum(1 for v in observations if v <= bucket)
            buckets[bucket] = count

        # +Inf 桶（所有值）
        buckets[float('inf')] = len(observations)

        return buckets

    def get_stats(self, labels: Dict[str, str]) -> Dict[str, float]:
        """获取统计信息"""
        label_key = self._labels_to_key(labels)
        observations = self.observations.get(label_key, [])

        if not observations:
            return {
                "count": 0,
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0
            }

        return {
            "count": len(observations),
            "sum": sum(observations),
            "min": min(observations),
            "max": max(observations),
            "mean": statistics.mean(observations)
        }

    def get_percentiles(self, labels: Dict[str, str]) -> Dict[str, float]:
        """获取百分位数"""
        label_key = self._labels_to_key(labels)
        observations = self.observations.get(label_key, [])

        if not observations:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

        sorted_obs = sorted(observations)

        return {
            "p50": self._percentile(sorted_obs, 0.50),
            "p90": self._percentile(sorted_obs, 0.90),
            "p95": self._percentile(sorted_obs, 0.95),
            "p99": self._percentile(sorted_obs, 0.99)
        }

    def _percentile(self, sorted_values: List[float], p: float) -> float:
        """计算百分位数"""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class MetricsCollector:
    """
    统一指标收集器

    支持三种指标类型：
    - Counter: 计数器（只增不减）
    - Gauge: 仪表盘（可增可减）
    - Histogram: 直方图（分布统计）

    使用示例:
        collector = MetricsCollector()

        # 1. 计数器
        collector.increment("requests_total", labels={"endpoint": "/api/v1"})

        # 2. 仪表盘
        collector.gauge("active_connections", 42, labels={"server": "main"})

        # 3. 直方图（记录时间）
        with collector.timer("request_duration_seconds", labels={"endpoint": "/api/v1"}):
            process_request()

        # 4. 获取指标
        stats = collector.get_histogram_stats("request_duration_seconds", labels={"endpoint": "/api/v1"})
        print(f"p95 latency: {stats['percentiles']['p95']:.2f}s")
    """

    def __init__(self):
        """初始化指标收集器"""
        self.counters: Dict[str, CounterMetric] = {}
        self.gauges: Dict[str, GaugeMetric] = {}
        self.histograms: Dict[str, HistogramMetric] = {}

        self.lock = threading.Lock()

        # 默认直方图分桶（适用于时间类指标，单位：秒）
        self.default_time_buckets = [
            0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5,
            1.0, 2.5, 5.0, 10.0, 30.0, 60.0
        ]

        # 初始化系统资源指标
        self._init_system_metrics()

    def _init_system_metrics(self):
        """初始化系统资源指标"""
        # CPU 使用率
        self.register_gauge(
            "system_cpu_usage_percent",
            "System CPU usage percentage"
        )

        # 内存使用量
        self.register_gauge(
            "system_memory_usage_mb",
            "System memory usage in MB"
        )
        self.register_gauge(
            "system_memory_usage_percent",
            "System memory usage percentage"
        )

        # 进程内存使用量
        self.register_gauge(
            "process_memory_usage_mb",
            "Process memory usage in MB"
        )

    def register_counter(self, name: str, help_text: str):
        """注册计数器指标"""
        with self.lock:
            if name not in self.counters:
                self.counters[name] = CounterMetric(name, help_text)

    def register_gauge(self, name: str, help_text: str):
        """注册仪表盘指标"""
        with self.lock:
            if name not in self.gauges:
                self.gauges[name] = GaugeMetric(name, help_text)

    def register_histogram(
        self,
        name: str,
        help_text: str,
        buckets: Optional[List[float]] = None
    ):
        """注册直方图指标"""
        with self.lock:
            if name not in self.histograms:
                buckets = buckets or self.default_time_buckets
                self.histograms[name] = HistogramMetric(name, help_text, buckets)

    def increment(self, name: str, labels: Optional[Dict[str, str]] = None, amount: float = 1.0):
        """增加计数器"""
        labels = labels or {}

        with self.lock:
            if name not in self.counters:
                self.register_counter(name, f"Counter: {name}")

            self.counters[name].increment(labels, amount)

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表盘值"""
        labels = labels or {}

        with self.lock:
            if name not in self.gauges:
                self.register_gauge(name, f"Gauge: {name}")

            self.gauges[name].set(labels, value)

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """观察直方图值"""
        labels = labels or {}

        with self.lock:
            if name not in self.histograms:
                self.register_histogram(name, f"Histogram: {name}")

            self.histograms[name].observe(labels, value)

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """
        计时器上下文管理器

        使用示例:
            with collector.timer("operation_duration", labels={"op": "process"}):
                do_something()
        """
        return MetricsTimer(self, name, labels or {})

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """获取计数器值"""
        labels = labels or {}

        with self.lock:
            if name not in self.counters:
                return 0.0
            return self.counters[name].get(labels)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """获取仪表盘值"""
        labels = labels or {}

        with self.lock:
            if name not in self.gauges:
                return 0.0
            return self.gauges[name].get(labels)

    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """获取直方图统计"""
        labels = labels or {}

        with self.lock:
            if name not in self.histograms:
                return {}

            histogram = self.histograms[name]
            stats = histogram.get_stats(labels)
            percentiles = histogram.get_percentiles(labels)

            return {
                "stats": stats,
                "percentiles": percentiles
            }

    def update_system_metrics(self):
        """更新系统资源指标"""
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.gauge("system_cpu_usage_percent", cpu_percent)

        # 系统内存
        memory = psutil.virtual_memory()
        self.gauge("system_memory_usage_mb", memory.used / 1024 / 1024)
        self.gauge("system_memory_usage_percent", memory.percent)

        # 进程内存
        process = psutil.Process()
        process_memory_mb = process.memory_info().rss / 1024 / 1024
        self.gauge("process_memory_usage_mb", process_memory_mb)

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标（用于导出）"""
        with self.lock:
            return {
                "counters": {
                    name: {
                        "help": counter.help_text,
                        "values": dict(counter.values)
                    }
                    for name, counter in self.counters.items()
                },
                "gauges": {
                    name: {
                        "help": gauge.help_text,
                        "values": dict(gauge.values)
                    }
                    for name, gauge in self.gauges.items()
                },
                "histograms": {
                    name: {
                        "help": histogram.help_text,
                        "observations": {
                            k: list(v) for k, v in histogram.observations.items()
                        }
                    }
                    for name, histogram in self.histograms.items()
                }
            }


class MetricsTimer:
    """
    指标计时器上下文管理器

    使用示例:
        with MetricsTimer(collector, "operation_duration", {"op": "test"}):
            do_something()
    """

    def __init__(self, collector: MetricsCollector, name: str, labels: Dict[str, str]):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.collector.observe(self.name, duration, self.labels)
        return False


# 全局指标收集器实例（单例）
_global_collector: Optional[MetricsCollector] = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    获取全局指标收集器实例（单例模式）

    Returns:
        MetricsCollector实例
    """
    global _global_collector

    if _global_collector is None:
        with _collector_lock:
            if _global_collector is None:
                _global_collector = MetricsCollector()

    return _global_collector


# 预定义业务指标名称（便于统一管理）
class MetricNames:
    """标准指标名称"""

    # 工作流指标
    WORKFLOW_EXECUTIONS_TOTAL = "workflow_executions_total"
    WORKFLOW_DURATION_SECONDS = "workflow_duration_seconds"
    WORKFLOW_SUCCESS_TOTAL = "workflow_success_total"
    WORKFLOW_FAILURE_TOTAL = "workflow_failure_total"

    # Agent 指标
    AGENT_EXECUTIONS_TOTAL = "agent_executions_total"
    AGENT_DURATION_SECONDS = "agent_duration_seconds"
    AGENT_SUCCESS_TOTAL = "agent_success_total"
    AGENT_FAILURE_TOTAL = "agent_failure_total"

    # LLM 指标
    LLM_CALLS_TOTAL = "llm_calls_total"
    LLM_CALL_DURATION_SECONDS = "llm_call_duration_seconds"
    LLM_INPUT_TOKENS_TOTAL = "llm_input_tokens_total"
    LLM_OUTPUT_TOKENS_TOTAL = "llm_output_tokens_total"
    LLM_ERRORS_TOTAL = "llm_errors_total"

    # 数据加载指标
    DATA_LOAD_DURATION_SECONDS = "data_load_duration_seconds"
    DATA_LOAD_RECORDS_TOTAL = "data_load_records_total"
    DATA_LOAD_ERRORS_TOTAL = "data_load_errors_total"

    # 缓存指标
    CACHE_HITS_TOTAL = "cache_hits_total"
    CACHE_MISSES_TOTAL = "cache_misses_total"
    CACHE_SIZE_MB = "cache_size_mb"


# 使用示例（可删除）
def _example_usage():
    """示例代码"""
    # 获取全局收集器
    collector = get_metrics_collector()

    # 1. 计数器示例
    collector.increment(
        MetricNames.WORKFLOW_EXECUTIONS_TOTAL,
        labels={"workflow": "role_mastery"}
    )

    # 2. 仪表盘示例
    collector.gauge(
        MetricNames.CACHE_SIZE_MB,
        123.45,
        labels={"component": "agent_context"}
    )

    # 3. 直方图示例（计时器）
    with collector.timer(
        MetricNames.WORKFLOW_DURATION_SECONDS,
        labels={"workflow": "role_mastery"}
    ):
        time.sleep(0.1)  # 模拟工作流

    # 4. 获取统计信息
    stats = collector.get_histogram_stats(
        MetricNames.WORKFLOW_DURATION_SECONDS,
        labels={"workflow": "role_mastery"}
    )

    print(f"工作流统计: {stats}")

    # 5. 更新系统指标
    collector.update_system_metrics()
    cpu_usage = collector.get_gauge("system_cpu_usage_percent")
    print(f"CPU 使用率: {cpu_usage:.1f}%")


if __name__ == "__main__":
    _example_usage()
