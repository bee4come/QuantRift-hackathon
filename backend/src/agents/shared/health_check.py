"""
Health Check System - Option A Day 3

生产级健康检查系统，提供：
- /health 端点 - 基本健康状态
- /ready 端点 - 就绪检查（Kubernetes readiness probe）
- 系统组件检查（LLM、数据目录、缓存、内存）
- HTTP 服务器集成
"""

import os
import time
import json
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler

from .structured_logger import get_logger
from .metrics_collector import get_metrics_collector


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CheckResult(Enum):
    """检查结果"""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class ComponentCheck:
    """组件检查结果"""
    component: str                    # 组件名称
    status: CheckResult               # 检查结果
    message: str                      # 状态消息
    response_time_ms: float          # 响应时间（毫秒）
    details: Dict[str, Any] = None   # 详细信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['status'] = self.status.value
        return result


class HealthChecker:
    """
    健康检查器

    执行系统组件健康检查
    """

    def __init__(self):
        """初始化健康检查器"""
        self.checks: Dict[str, Callable[[], ComponentCheck]] = {}
        self.logger = get_logger("HealthChecker", level="INFO")
        self.metrics = get_metrics_collector()

        # 注册默认检查项
        self._register_default_checks()

        self.logger.info("HealthChecker初始化")

    def _register_default_checks(self):
        """注册默认检查项"""
        self.register_check("system_resources", self._check_system_resources)
        self.register_check("data_directory", self._check_data_directory)
        self.register_check("metrics_collector", self._check_metrics_collector)

    def register_check(self, name: str, check_func: Callable[[], ComponentCheck]):
        """
        注册检查项

        Args:
            name: 检查项名称
            check_func: 检查函数（返回ComponentCheck）
        """
        self.checks[name] = check_func
        self.logger.info("健康检查项注册", check_name=name)

    def unregister_check(self, name: str):
        """移除检查项"""
        if name in self.checks:
            del self.checks[name]
            self.logger.info("健康检查项移除", check_name=name)

    def run_checks(self) -> Dict[str, ComponentCheck]:
        """
        运行所有检查

        Returns:
            Dict[str, ComponentCheck]: 检查结果映射
        """
        results = {}

        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = check_func()
                duration_ms = (time.time() - start_time) * 1000

                # 更新响应时间
                result.response_time_ms = duration_ms

                results[name] = result

                # 记录指标
                self.metrics.increment(
                    "health_checks_total",
                    labels={
                        "check": name,
                        "status": result.status.value
                    }
                )

                self.metrics.observe(
                    "health_check_duration_seconds",
                    duration_ms / 1000.0,
                    labels={"check": name}
                )

            except Exception as e:
                self.logger.error(
                    "健康检查执行失败",
                    check_name=name,
                    error=str(e)
                )

                results[name] = ComponentCheck(
                    component=name,
                    status=CheckResult.FAIL,
                    message=f"Check failed: {str(e)}",
                    response_time_ms=0
                )

        return results

    def get_overall_status(self, check_results: Dict[str, ComponentCheck]) -> HealthStatus:
        """
        获取整体健康状态

        Args:
            check_results: 检查结果

        Returns:
            HealthStatus: 整体状态
        """
        if not check_results:
            return HealthStatus.UNHEALTHY

        fail_count = sum(1 for r in check_results.values() if r.status == CheckResult.FAIL)
        warn_count = sum(1 for r in check_results.values() if r.status == CheckResult.WARN)

        if fail_count > 0:
            return HealthStatus.UNHEALTHY
        elif warn_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _check_system_resources(self) -> ComponentCheck:
        """检查系统资源（CPU、内存）"""
        try:
            import psutil

            # 更新系统指标
            self.metrics.update_system_metrics()

            # 获取CPU和内存
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 判断状态
            if cpu_percent > 90 or memory_percent > 90:
                status = CheckResult.FAIL
                message = f"High resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"
            elif cpu_percent > 75 or memory_percent > 75:
                status = CheckResult.WARN
                message = f"Elevated resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"
            else:
                status = CheckResult.PASS
                message = f"Normal resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"

            return ComponentCheck(
                component="system_resources",
                status=status,
                message=message,
                response_time_ms=0,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_used_mb": memory.used / (1024 ** 2),
                    "memory_available_mb": memory.available / (1024 ** 2)
                }
            )

        except Exception as e:
            return ComponentCheck(
                component="system_resources",
                status=CheckResult.FAIL,
                message=f"Failed to check system resources: {str(e)}",
                response_time_ms=0
            )

    def _check_data_directory(self) -> ComponentCheck:
        """检查数据目录可访问性"""
        try:
            # 检查关键数据目录
            data_dirs = [
                "data/gold/production",
                "data/silver/production",
                "logs"
            ]

            missing_dirs = []
            for dir_path in data_dirs:
                if not os.path.exists(dir_path):
                    missing_dirs.append(dir_path)

            if missing_dirs:
                return ComponentCheck(
                    component="data_directory",
                    status=CheckResult.WARN,
                    message=f"Missing directories: {', '.join(missing_dirs)}",
                    response_time_ms=0,
                    details={"missing_directories": missing_dirs}
                )
            else:
                return ComponentCheck(
                    component="data_directory",
                    status=CheckResult.PASS,
                    message="All data directories accessible",
                    response_time_ms=0,
                    details={"checked_directories": data_dirs}
                )

        except Exception as e:
            return ComponentCheck(
                component="data_directory",
                status=CheckResult.FAIL,
                message=f"Failed to check data directories: {str(e)}",
                response_time_ms=0
            )

    def _check_metrics_collector(self) -> ComponentCheck:
        """检查指标收集器状态"""
        try:
            # 获取指标摘要
            metrics = self.metrics.get_all_metrics()

            counter_count = len(metrics.get("counters", {}))
            gauge_count = len(metrics.get("gauges", {}))
            histogram_count = len(metrics.get("histograms", {}))

            return ComponentCheck(
                component="metrics_collector",
                status=CheckResult.PASS,
                message=f"Metrics collector operational: {counter_count} counters, {gauge_count} gauges, {histogram_count} histograms",
                response_time_ms=0,
                details={
                    "counter_count": counter_count,
                    "gauge_count": gauge_count,
                    "histogram_count": histogram_count
                }
            )

        except Exception as e:
            return ComponentCheck(
                component="metrics_collector",
                status=CheckResult.FAIL,
                message=f"Metrics collector check failed: {str(e)}",
                response_time_ms=0
            )


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    health_checker: Optional[HealthChecker] = None

    def do_GET(self):
        """处理 GET 请求"""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/ready":
            self._handle_ready()
        elif self.path == "/live":
            self._handle_liveness()
        else:
            self._send_error(404, "Not Found")

    def _handle_health(self):
        """处理 /health 端点"""
        try:
            # 运行所有检查
            check_results = self.health_checker.run_checks()
            overall_status = self.health_checker.get_overall_status(check_results)

            # 构造响应
            response = {
                "status": overall_status.value,
                "timestamp": time.time(),
                "checks": {
                    name: result.to_dict()
                    for name, result in check_results.items()
                }
            }

            # 根据状态设置HTTP状态码
            if overall_status == HealthStatus.HEALTHY:
                status_code = 200
            elif overall_status == HealthStatus.DEGRADED:
                status_code = 200  # 降级但仍可服务
            else:
                status_code = 503  # 不健康

            self._send_json_response(status_code, response)

        except Exception as e:
            self._send_error(500, f"Health check failed: {str(e)}")

    def _handle_ready(self):
        """
        处理 /ready 端点（Kubernetes readiness probe）

        就绪检查：是否准备好接受流量
        """
        try:
            # 运行关键检查
            check_results = self.health_checker.run_checks()
            overall_status = self.health_checker.get_overall_status(check_results)

            # 就绪判断：必须完全健康
            is_ready = (overall_status == HealthStatus.HEALTHY)

            response = {
                "ready": is_ready,
                "timestamp": time.time(),
                "status": overall_status.value,
                "checks": {
                    name: result.to_dict()
                    for name, result in check_results.items()
                }
            }

            # 就绪返回200，未就绪返回503
            status_code = 200 if is_ready else 503

            self._send_json_response(status_code, response)

        except Exception as e:
            self._send_error(500, f"Readiness check failed: {str(e)}")

    def _handle_liveness(self):
        """
        处理 /live 端点（Kubernetes liveness probe）

        存活检查：进程是否存活（简单检查）
        """
        try:
            response = {
                "alive": True,
                "timestamp": time.time()
            }

            self._send_json_response(200, response)

        except Exception as e:
            self._send_error(500, f"Liveness check failed: {str(e)}")

    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response_body = json.dumps(data, indent=2)
        self.wfile.write(response_body.encode('utf-8'))

    def _send_error(self, status_code: int, message: str):
        """发送错误响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        error_response = {
            "error": message,
            "status_code": status_code,
            "timestamp": time.time()
        }

        self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def log_message(self, format, *args):
        """禁用默认日志（使用我们的结构化日志）"""
        pass


class HealthCheckServer:
    """
    健康检查 HTTP 服务器

    提供 /health, /ready, /live 端点
    """

    def __init__(
        self,
        health_checker: HealthChecker,
        host: str = "0.0.0.0",
        port: int = 8001
    ):
        """
        初始化健康检查服务器

        Args:
            health_checker: 健康检查器实例
            host: 监听地址
            port: 监听端口
        """
        self.health_checker = health_checker
        self.host = host
        self.port = port

        # 设置处理器的健康检查器
        HealthCheckHandler.health_checker = health_checker

        # HTTP 服务器
        self.server = HTTPServer((host, port), HealthCheckHandler)

        self.thread: Optional[threading.Thread] = None
        self.running = False

        self.logger = get_logger("HealthCheckServer")
        self.logger.info("HealthCheckServer初始化",
                        host=host,
                        port=port)

    def start(self):
        """启动服务器（后台线程）"""
        if self.running:
            self.logger.warning("HealthCheckServer已在运行")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        self.logger.info("HealthCheckServer启动",
                        host=self.host,
                        port=self.port)

    def _run_server(self):
        """运行服务器循环"""
        try:
            self.server.serve_forever()
        except Exception as e:
            self.logger.error("HealthCheckServer运行错误", error=str(e))
            self.running = False

    def stop(self):
        """停止服务器"""
        if not self.running:
            return

        self.running = False
        self.server.shutdown()
        self.server.server_close()

        if self.thread:
            self.thread.join(timeout=5)

        self.logger.info("HealthCheckServer停止")


# 全局单例
_global_health_checker: Optional[HealthChecker] = None
_global_health_server: Optional[HealthCheckServer] = None
_checker_lock = threading.Lock()


def get_health_checker() -> HealthChecker:
    """获取全局健康检查器（单例）"""
    global _global_health_checker

    if _global_health_checker is None:
        with _checker_lock:
            if _global_health_checker is None:
                _global_health_checker = HealthChecker()

    return _global_health_checker


def start_health_check_server(host: str = "0.0.0.0", port: int = 8001) -> HealthCheckServer:
    """
    启动全局健康检查服务器（单例）

    Args:
        host: 监听地址
        port: 监听端口

    Returns:
        HealthCheckServer: 服务器实例

    Example:
        >>> from src.agents.shared.health_check import start_health_check_server
        >>> server = start_health_check_server(host="0.0.0.0", port=8001)
        >>> # 服务器在后台运行
        >>> # 访问 http://localhost:8001/health
        >>> # 访问 http://localhost:8001/ready
        >>> # 访问 http://localhost:8001/live
    """
    global _global_health_server

    if _global_health_server is None:
        with _checker_lock:
            if _global_health_server is None:
                checker = get_health_checker()
                _global_health_server = HealthCheckServer(checker, host, port)
                _global_health_server.start()

    return _global_health_server


def stop_health_check_server():
    """停止全局健康检查服务器"""
    global _global_health_server

    if _global_health_server is not None:
        _global_health_server.stop()
        _global_health_server = None
