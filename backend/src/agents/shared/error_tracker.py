"""
Error Tracking System - Option A Day 3

生产级错误跟踪系统，提供：
- 异常捕获与堆栈跟踪
- 错误分类（LLM/数据/系统/未知）
- 错误聚合与去重
- 错误上下文保存
- 与日志和指标系统集成
"""

import traceback
import hashlib
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import threading
from functools import wraps

from .structured_logger import get_logger
from .metrics_collector import get_metrics_collector, MetricNames


class ErrorCategory(Enum):
    """错误分类"""
    LLM = "llm"                    # LLM 调用错误
    DATA = "data"                  # 数据加载/处理错误
    SYSTEM = "system"              # 系统资源错误
    VALIDATION = "validation"      # 数据验证错误
    CONFIGURATION = "configuration"  # 配置错误
    NETWORK = "network"            # 网络错误
    UNKNOWN = "unknown"            # 未知错误


class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"  # 致命错误，需要立即处理
    HIGH = "high"          # 高危错误，影响主要功能
    MEDIUM = "medium"      # 中等错误，影响部分功能
    LOW = "low"            # 低危错误，轻微影响


@dataclass
class ErrorContext:
    """错误上下文信息"""
    workflow_id: Optional[str] = None
    request_id: Optional[str] = None
    agent_name: Optional[str] = None
    operation: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # 请求参数（脱敏后）
    request_params: Dict[str, Any] = field(default_factory=dict)

    # 状态快照
    state_snapshot: Dict[str, Any] = field(default_factory=dict)

    # 额外元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """错误记录"""
    error_id: str                        # 错误唯一ID（hash）
    error_type: str                      # 错误类型名称
    error_message: str                   # 错误消息
    category: ErrorCategory              # 错误分类
    severity: ErrorSeverity              # 严重程度

    # 堆栈跟踪
    stack_trace: str                     # 完整堆栈
    stack_trace_hash: str                # 堆栈哈希（用于去重）

    # 时间信息
    first_seen: float                    # 首次出现时间
    last_seen: float                     # 最后出现时间
    occurrence_count: int = 1            # 出现次数

    # 上下文
    context: Optional[ErrorContext] = None

    # 额外信息
    resolved: bool = False               # 是否已解决
    resolution_notes: Optional[str] = None  # 解决备注

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['category'] = self.category.value
        result['severity'] = self.severity.value
        if self.context:
            result['context'] = asdict(self.context)
        return result


class ErrorClassifier:
    """错误分类器"""

    # 错误分类规则（基于异常类型和消息模式）
    CLASSIFICATION_RULES = {
        ErrorCategory.LLM: [
            "BedrockError", "LLMError", "ModelError", "TokenLimit",
            "bedrock", "llm", "model", "token", "anthropic"
        ],
        ErrorCategory.DATA: [
            "FileNotFoundError", "JSONDecodeError", "DataError",
            "ParsingError", "file not found", "invalid json", "data"
        ],
        ErrorCategory.SYSTEM: [
            "MemoryError", "OSError", "SystemError", "ResourceError",
            "memory", "disk", "cpu", "resource"
        ],
        ErrorCategory.VALIDATION: [
            "ValueError", "TypeError", "ValidationError",
            "invalid", "validation", "schema"
        ],
        ErrorCategory.CONFIGURATION: [
            "ConfigurationError", "ConfigError", "SettingsError",
            "config", "settings", "environment"
        ],
        ErrorCategory.NETWORK: [
            "ConnectionError", "TimeoutError", "NetworkError",
            "connection", "timeout", "network", "http", "api"
        ]
    }

    @classmethod
    def classify(cls, exception: Exception) -> ErrorCategory:
        """
        分类异常

        Args:
            exception: 异常对象

        Returns:
            ErrorCategory: 错误分类
        """
        error_type = type(exception).__name__
        error_message = str(exception).lower()

        # 优先匹配异常类型（更精确）
        for category, patterns in cls.CLASSIFICATION_RULES.items():
            for pattern in patterns:
                if pattern.lower() in error_type.lower():
                    return category

        # 再匹配消息内容
        for category, patterns in cls.CLASSIFICATION_RULES.items():
            for pattern in patterns:
                if pattern.lower() in error_message:
                    return category

        return ErrorCategory.UNKNOWN

    @classmethod
    def assess_severity(cls, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """
        评估错误严重程度

        Args:
            exception: 异常对象
            category: 错误分类

        Returns:
            ErrorSeverity: 严重程度
        """
        error_type = type(exception).__name__
        error_message = str(exception).lower()

        # CRITICAL 级别
        critical_patterns = [
            "MemoryError", "SystemError", "OutOfMemoryError",
            "critical", "fatal", "crash"
        ]
        for pattern in critical_patterns:
            if pattern.lower() in error_type.lower() or pattern.lower() in error_message:
                return ErrorSeverity.CRITICAL

        # HIGH 级别
        high_patterns = [
            "ConnectionError", "AuthenticationError", "PermissionError",
            "auth", "permission", "access denied"
        ]
        for pattern in high_patterns:
            if pattern.lower() in error_type.lower() or pattern.lower() in error_message:
                return ErrorSeverity.HIGH

        # LLM 和 DATA 错误通常为 MEDIUM
        if category in [ErrorCategory.LLM, ErrorCategory.DATA]:
            return ErrorSeverity.MEDIUM

        # 其他为 LOW
        return ErrorSeverity.LOW


class ErrorTracker:
    """
    错误跟踪器

    捕获、分类、聚合和存储错误信息
    """

    def __init__(self, max_errors: int = 10000, enable_deduplication: bool = True):
        """
        初始化错误跟踪器

        Args:
            max_errors: 最大存储错误数（超过则移除最旧的）
            enable_deduplication: 是否启用去重
        """
        self.max_errors = max_errors
        self.enable_deduplication = enable_deduplication

        # 错误存储（error_id -> ErrorRecord）
        self.errors: Dict[str, ErrorRecord] = {}

        # 错误哈希映射（用于快速去重查找）
        self.error_hashes: Dict[str, str] = {}  # hash -> error_id

        # 线程锁
        self.lock = threading.Lock()

        # 集成
        self.logger = get_logger("ErrorTracker", level="INFO")
        self.metrics = get_metrics_collector()

        self.logger.info("ErrorTracker初始化",
                        max_errors=max_errors,
                        enable_deduplication=enable_deduplication)

    def _generate_error_id(self, error_type: str, error_message: str,
                          stack_trace_hash: str) -> str:
        """
        生成错误唯一ID

        Args:
            error_type: 错误类型
            error_message: 错误消息
            stack_trace_hash: 堆栈哈希

        Returns:
            str: 错误ID
        """
        content = f"{error_type}:{error_message}:{stack_trace_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_stack_trace_hash(self, stack_trace: str) -> str:
        """
        生成堆栈跟踪哈希（用于去重）

        只保留关键帧信息（文件名、行号、函数名），忽略变量值

        Args:
            stack_trace: 完整堆栈跟踪

        Returns:
            str: 堆栈哈希
        """
        # 提取关键帧信息
        key_lines = []
        for line in stack_trace.split('\n'):
            # 保留 File "..." line N 的行
            if 'File "' in line and ', line ' in line:
                key_lines.append(line.strip())

        key_content = '\n'.join(key_lines)
        return hashlib.sha256(key_content.encode()).hexdigest()[:16]

    def capture_exception(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None
    ) -> str:
        """
        捕获异常

        Args:
            exception: 异常对象
            context: 错误上下文
            category: 强制指定分类（可选）
            severity: 强制指定严重程度（可选）

        Returns:
            str: 错误ID
        """
        # 获取堆栈跟踪
        stack_trace = traceback.format_exc()
        stack_trace_hash = self._generate_stack_trace_hash(stack_trace)

        # 分类错误
        if category is None:
            category = ErrorClassifier.classify(exception)

        if severity is None:
            severity = ErrorClassifier.assess_severity(exception, category)

        # 生成错误ID
        error_type = type(exception).__name__
        error_message = str(exception)
        error_id = self._generate_error_id(error_type, error_message, stack_trace_hash)

        with self.lock:
            # 检查是否已存在（去重）
            if self.enable_deduplication and error_id in self.errors:
                # 更新现有记录
                existing = self.errors[error_id]
                existing.occurrence_count += 1
                existing.last_seen = time.time()

                self.logger.debug("错误重复",
                                error_id=error_id,
                                error_type=error_type,
                                occurrence_count=existing.occurrence_count)

                # 更新指标
                self.metrics.increment(
                    "error_occurrences_total",
                    labels={
                        "category": category.value,
                        "severity": severity.value,
                        "error_type": error_type
                    }
                )

                return error_id

            # 创建新记录
            current_time = time.time()
            record = ErrorRecord(
                error_id=error_id,
                error_type=error_type,
                error_message=error_message,
                category=category,
                severity=severity,
                stack_trace=stack_trace,
                stack_trace_hash=stack_trace_hash,
                first_seen=current_time,
                last_seen=current_time,
                context=context
            )

            # 存储
            self.errors[error_id] = record
            self.error_hashes[stack_trace_hash] = error_id

            # 限制存储数量
            if len(self.errors) > self.max_errors:
                self._evict_oldest_error()

            # 日志记录
            self.logger.error(
                "错误捕获",
                error_id=error_id,
                error_type=error_type,
                error_message=error_message,
                category=category.value,
                severity=severity.value,
                context=asdict(context) if context else None
            )

            # 指标记录
            self.metrics.increment(
                "error_captures_total",
                labels={
                    "category": category.value,
                    "severity": severity.value,
                    "error_type": error_type
                }
            )

            # CRITICAL 错误特殊处理
            if severity == ErrorSeverity.CRITICAL:
                self.logger.error(
                    "⚠️ CRITICAL错误",
                    error_id=error_id,
                    error_type=error_type,
                    stack_trace=stack_trace
                )
                self.metrics.increment(
                    "critical_errors_total",
                    labels={"error_type": error_type}
                )

        return error_id

    def _evict_oldest_error(self):
        """移除最旧的错误（未解决的）"""
        oldest_id = None
        oldest_time = float('inf')

        for error_id, record in self.errors.items():
            if not record.resolved and record.first_seen < oldest_time:
                oldest_time = record.first_seen
                oldest_id = error_id

        if oldest_id:
            del self.errors[oldest_id]
            self.logger.debug("移除最旧错误", error_id=oldest_id)

    def get_error(self, error_id: str) -> Optional[ErrorRecord]:
        """获取错误记录"""
        with self.lock:
            return self.errors.get(error_id)

    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorRecord]:
        """按分类获取错误"""
        with self.lock:
            return [e for e in self.errors.values() if e.category == category]

    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[ErrorRecord]:
        """按严重程度获取错误"""
        with self.lock:
            return [e for e in self.errors.values() if e.severity == severity]

    def get_unresolved_errors(self) -> List[ErrorRecord]:
        """获取未解决的错误"""
        with self.lock:
            return [e for e in self.errors.values() if not e.resolved]

    def get_recent_errors(self, limit: int = 10) -> List[ErrorRecord]:
        """获取最近的错误"""
        with self.lock:
            sorted_errors = sorted(
                self.errors.values(),
                key=lambda e: e.last_seen,
                reverse=True
            )
            return sorted_errors[:limit]

    def mark_resolved(self, error_id: str, resolution_notes: Optional[str] = None):
        """标记错误已解决"""
        with self.lock:
            if error_id in self.errors:
                self.errors[error_id].resolved = True
                self.errors[error_id].resolution_notes = resolution_notes

                self.logger.info("错误已解决",
                               error_id=error_id,
                               resolution_notes=resolution_notes)

    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误统计摘要"""
        with self.lock:
            total = len(self.errors)
            unresolved = sum(1 for e in self.errors.values() if not e.resolved)

            by_category = {}
            by_severity = {}

            for error in self.errors.values():
                # 按分类统计
                cat = error.category.value
                by_category[cat] = by_category.get(cat, 0) + error.occurrence_count

                # 按严重程度统计
                sev = error.severity.value
                by_severity[sev] = by_severity.get(sev, 0) + error.occurrence_count

            return {
                "total_unique_errors": total,
                "unresolved_errors": unresolved,
                "resolved_errors": total - unresolved,
                "by_category": by_category,
                "by_severity": by_severity,
                "recent_errors": [
                    {
                        "error_id": e.error_id,
                        "error_type": e.error_type,
                        "category": e.category.value,
                        "severity": e.severity.value,
                        "occurrence_count": e.occurrence_count,
                        "last_seen": datetime.fromtimestamp(e.last_seen).isoformat()
                    }
                    for e in self.get_recent_errors(5)
                ]
            }

    def clear_resolved_errors(self):
        """清除已解决的错误"""
        with self.lock:
            resolved_ids = [
                error_id for error_id, record in self.errors.items()
                if record.resolved
            ]

            for error_id in resolved_ids:
                del self.errors[error_id]

            self.logger.info("清除已解决错误", count=len(resolved_ids))


# 全局单例
_global_error_tracker: Optional[ErrorTracker] = None
_tracker_lock = threading.Lock()


def get_error_tracker() -> ErrorTracker:
    """获取全局错误跟踪器（单例）"""
    global _global_error_tracker

    if _global_error_tracker is None:
        with _tracker_lock:
            if _global_error_tracker is None:
                _global_error_tracker = ErrorTracker()

    return _global_error_tracker


def track_errors(
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    context_factory: Optional[Callable[[], ErrorContext]] = None
):
    """
    装饰器：自动错误跟踪

    Args:
        category: 强制指定错误分类
        severity: 强制指定严重程度
        context_factory: 上下文工厂函数（返回ErrorContext）

    Example:
        @track_errors(category=ErrorCategory.LLM)
        def call_llm(prompt: str):
            # LLM 调用逻辑
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 构建上下文
                context = None
                if context_factory:
                    try:
                        context = context_factory()
                    except:
                        pass

                # 捕获错误
                tracker = get_error_tracker()
                error_id = tracker.capture_exception(
                    e,
                    context=context,
                    category=category,
                    severity=severity
                )

                # 重新抛出异常
                raise

        return wrapper
    return decorator
