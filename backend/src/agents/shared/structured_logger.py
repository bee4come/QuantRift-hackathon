"""
结构化日志系统 - Option A Day 1

提供统一的JSON结构化日志输出，支持：
- 上下文传播（request_id, workflow_id, agent_name）
- 日志级别配置
- 敏感信息脱敏
- 性能指标记录

使用示例:
    logger = StructuredLogger("MetaStrategyAgent")
    logger.info("工作流开始", workflow_name="role_mastery", params={"role": "TOP"})
    logger.error("LLM调用失败", error=str(e), request_id=req_id)
"""

import json
import logging
import time
import re
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import threading

# 线程本地存储，用于上下文传播
_context = threading.local()


class SensitiveDataFilter:
    """敏感数据脱敏过滤器"""

    # 敏感字段模式
    SENSITIVE_PATTERNS = [
        r'api[_-]?key',
        r'secret',
        r'password',
        r'token',
        r'auth',
        r'credential',
        r'access[_-]?key'
    ]

    @classmethod
    def mask(cls, data: Any) -> Any:
        """
        递归脱敏数据

        Args:
            data: 原始数据（dict, list, str等）

        Returns:
            脱敏后的数据
        """
        if isinstance(data, dict):
            return {k: cls._mask_value(k, v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.mask(item) for item in data]
        else:
            return data

    @classmethod
    def _mask_value(cls, key: str, value: Any) -> Any:
        """脱敏单个键值对"""
        # 检查key是否匹配敏感模式
        key_lower = key.lower()
        is_sensitive = any(re.search(pattern, key_lower) for pattern in cls.SENSITIVE_PATTERNS)

        if is_sensitive:
            if isinstance(value, str):
                if len(value) <= 8:
                    return "***"
                else:
                    # 保留前4位和后4位
                    return f"{value[:4]}...{value[-4:]}"
            else:
                return "***"
        else:
            # 递归处理嵌套结构
            return cls.mask(value)


class LogContext:
    """日志上下文管理"""

    @staticmethod
    def set(key: str, value: Any):
        """设置上下文变量"""
        if not hasattr(_context, 'data'):
            _context.data = {}
        _context.data[key] = value

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        if not hasattr(_context, 'data'):
            return default
        return _context.data.get(key, default)

    @staticmethod
    def clear():
        """清除上下文"""
        if hasattr(_context, 'data'):
            _context.data.clear()

    @staticmethod
    def get_all() -> Dict[str, Any]:
        """获取所有上下文"""
        if not hasattr(_context, 'data'):
            return {}
        return _context.data.copy()


class StructuredLogger:
    """
    结构化日志记录器

    使用示例:
        # 创建logger
        logger = StructuredLogger("MyAgent")

        # 设置上下文（在工作流开始时）
        LogContext.set("workflow_id", "wf_12345")
        LogContext.set("request_id", "req_67890")

        # 记录日志
        logger.info("处理开始", user="player123")
        logger.error("处理失败", error="超时", duration_ms=5000)

        # 清除上下文
        LogContext.clear()
    """

    def __init__(
        self,
        name: str,
        level: str = "INFO",
        log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_masking: bool = True
    ):
        """
        初始化结构化日志记录器

        Args:
            name: 日志记录器名称（通常是Agent名称）
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            log_file: 日志文件路径（可选）
            enable_console: 是否输出到控制台
            enable_masking: 是否启用敏感数据脱敏
        """
        self.name = name
        self.enable_masking = enable_masking

        # 创建Python标准logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers.clear()  # 清除已有handlers

        # 控制台输出
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(console_handler)

        # 文件输出
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(file_handler)

    def _format_log_entry(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> str:
        """
        格式化日志条目为JSON

        Args:
            level: 日志级别
            message: 日志消息
            **kwargs: 额外的日志字段

        Returns:
            JSON格式的日志字符串
        """
        # 基础字段
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "message": message
        }

        # 添加上下文（request_id, workflow_id等）
        context = LogContext.get_all()
        if context:
            entry["context"] = context

        # 添加额外字段
        if kwargs:
            # 脱敏处理
            if self.enable_masking:
                kwargs = SensitiveDataFilter.mask(kwargs)

            entry["data"] = kwargs

        return json.dumps(entry, ensure_ascii=False)

    def debug(self, message: str, **kwargs):
        """DEBUG级别日志"""
        log_entry = self._format_log_entry("DEBUG", message, **kwargs)
        self.logger.debug(log_entry)

    def info(self, message: str, **kwargs):
        """INFO级别日志"""
        log_entry = self._format_log_entry("INFO", message, **kwargs)
        self.logger.info(log_entry)

    def warning(self, message: str, **kwargs):
        """WARNING级别日志"""
        log_entry = self._format_log_entry("WARNING", message, **kwargs)
        self.logger.warning(log_entry)

    def error(self, message: str, **kwargs):
        """ERROR级别日志"""
        log_entry = self._format_log_entry("ERROR", message, **kwargs)
        self.logger.error(log_entry)

    def critical(self, message: str, **kwargs):
        """CRITICAL级别日志"""
        log_entry = self._format_log_entry("CRITICAL", message, **kwargs)
        self.logger.critical(log_entry)

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **kwargs
    ):
        """
        记录性能指标

        Args:
            operation: 操作名称
            duration_ms: 执行时间（毫秒）
            success: 是否成功
            **kwargs: 额外的性能数据
        """
        level = "INFO" if success else "WARNING"

        perf_data = {
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            **kwargs
        }

        log_entry = self._format_log_entry(
            level,
            f"性能指标: {operation}",
            **perf_data
        )

        if success:
            self.logger.info(log_entry)
        else:
            self.logger.warning(log_entry)


class LogTimer:
    """
    性能计时上下文管理器

    使用示例:
        logger = StructuredLogger("MyAgent")

        with LogTimer(logger, "数据加载"):
            data = load_data()

        # 自动记录: "性能指标: 数据加载 duration_ms=1234.56"
    """

    def __init__(
        self,
        logger: StructuredLogger,
        operation: str,
        **kwargs
    ):
        """
        初始化计时器

        Args:
            logger: StructuredLogger实例
            operation: 操作名称
            **kwargs: 额外的上下文数据
        """
        self.logger = logger
        self.operation = operation
        self.extra_data = kwargs
        self.start_time = None
        self.success = True

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.success = False
            self.extra_data["error"] = str(exc_val)

        self.logger.log_performance(
            operation=self.operation,
            duration_ms=duration_ms,
            success=self.success,
            **self.extra_data
        )

        # 不抑制异常
        return False


# 全局logger实例缓存
_logger_cache: Dict[str, StructuredLogger] = {}


def get_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> StructuredLogger:
    """
    获取或创建logger实例（单例模式）

    Args:
        name: logger名称
        level: 日志级别
        log_file: 日志文件路径
        enable_console: 是否输出到控制台

    Returns:
        StructuredLogger实例
    """
    cache_key = f"{name}:{level}:{log_file}:{enable_console}"

    if cache_key not in _logger_cache:
        _logger_cache[cache_key] = StructuredLogger(
            name=name,
            level=level,
            log_file=log_file,
            enable_console=enable_console
        )

    return _logger_cache[cache_key]


# 使用示例（可删除）
def _example_usage():
    """示例代码"""
    # 创建logger
    logger = get_logger("ExampleAgent", level="DEBUG")

    # 设置上下文
    LogContext.set("workflow_id", "wf_12345")
    LogContext.set("request_id", "req_67890")

    # 记录基本日志
    logger.info("工作流开始", workflow_name="role_mastery")

    # 记录包含敏感数据的日志（自动脱敏）
    logger.info("API调用", api_key="sk-1234567890abcdef", region="us-west-2")

    # 使用性能计时器
    with LogTimer(logger, "数据加载", file_count=10):
        time.sleep(0.1)  # 模拟操作

    # 记录错误
    try:
        raise ValueError("测试错误")
    except Exception as e:
        logger.error("处理失败", error=str(e), error_type=type(e).__name__)

    # 清除上下文
    LogContext.clear()


if __name__ == "__main__":
    _example_usage()
