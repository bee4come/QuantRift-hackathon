"""
Prometheus 指标导出器 - Option A Day 2

提供 HTTP 端点暴露 Prometheus 格式的指标

启动方式:
    python -m src.agents.shared.prometheus_exporter

或在代码中启动:
    from src.agents.shared.prometheus_exporter import start_metrics_server
    start_metrics_server(port=8000)

访问:
    http://localhost:8000/metrics
"""

import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
import threading

from .metrics_collector import get_metrics_collector


class PrometheusFormatter:
    """Prometheus 文本格式化器"""

    @staticmethod
    def format_metrics(metrics: Dict[str, Any]) -> str:
        """
        格式化指标为 Prometheus 文本格式

        Args:
            metrics: MetricsCollector.get_all_metrics() 返回的指标字典

        Returns:
            Prometheus 文本格式的指标
        """
        lines = []

        # 1. 格式化计数器
        for name, counter in metrics.get("counters", {}).items():
            lines.append(f"# HELP {name} {counter['help']}")
            lines.append(f"# TYPE {name} counter")

            for label_key, value in counter['values'].items():
                labels_str = PrometheusFormatter._format_labels(label_key)
                lines.append(f"{name}{{{labels_str}}} {value}")

        # 2. 格式化仪表盘
        for name, gauge in metrics.get("gauges", {}).items():
            lines.append(f"# HELP {name} {gauge['help']}")
            lines.append(f"# TYPE {name} gauge")

            for label_key, value in gauge['values'].items():
                labels_str = PrometheusFormatter._format_labels(label_key)
                lines.append(f"{name}{{{labels_str}}} {value}")

        # 3. 格式化直方图
        for name, histogram in metrics.get("histograms", {}).items():
            lines.append(f"# HELP {name} {histogram['help']}")
            lines.append(f"# TYPE {name} histogram")

            # 为每个标签组合生成直方图指标
            for label_key, observations in histogram['observations'].items():
                if not observations:
                    continue

                labels_str = PrometheusFormatter._format_labels(label_key)

                # 计算分桶
                sorted_obs = sorted(observations)
                buckets = [
                    0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5,
                    1.0, 2.5, 5.0, 10.0, 30.0, 60.0
                ]

                cumulative_count = 0
                for bucket in buckets:
                    count = sum(1 for v in sorted_obs if v <= bucket)
                    cumulative_count = count
                    lines.append(f"{name}_bucket{{le=\"{bucket}\",{labels_str}}} {count}")

                # +Inf 桶
                lines.append(f"{name}_bucket{{le=\"+Inf\",{labels_str}}} {len(observations)}")

                # 总和与计数
                total_sum = sum(observations)
                lines.append(f"{name}_sum{{{labels_str}}} {total_sum}")
                lines.append(f"{name}_count{{{labels_str}}} {len(observations)}")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_labels(label_key: str) -> str:
        """
        格式化标签为 Prometheus 格式

        Args:
            label_key: "key1=value1,key2=value2" 格式的字符串

        Returns:
            'key1="value1",key2="value2"' 格式的字符串
        """
        if not label_key:
            return ""

        pairs = label_key.split(",")
        formatted_pairs = []

        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                formatted_pairs.append(f'{key}="{value}"')

        return ",".join(formatted_pairs)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def do_GET(self):
        """处理 GET 请求"""
        if self.path == "/metrics":
            self._serve_metrics()
        elif self.path == "/health":
            self._serve_health()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _serve_metrics(self):
        """提供指标数据"""
        try:
            # 更新系统指标
            collector = get_metrics_collector()
            collector.update_system_metrics()

            # 获取所有指标
            metrics = collector.get_all_metrics()

            # 格式化为 Prometheus 文本
            prometheus_text = PrometheusFormatter.format_metrics(metrics)

            # 返回响应
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(prometheus_text.encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode('utf-8'))

    def _serve_health(self):
        """健康检查端点"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"healthy"}')

    def log_message(self, format, *args):
        """禁用默认日志（避免污染输出）"""
        pass


class MetricsServer:
    """
    Prometheus 指标服务器

    在后台线程中运行 HTTP 服务器，暴露 /metrics 端点

    使用示例:
        server = MetricsServer(port=8000)
        server.start()

        # 服务器运行中...

        server.stop()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """
        初始化指标服务器

        Args:
            host: 监听主机（默认 0.0.0.0，所有接口）
            port: 监听端口（默认 8000）
        """
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.running = False

    def start(self):
        """启动服务器（后台线程）"""
        if self.running:
            print(f"⚠️  Metrics server already running on {self.host}:{self.port}")
            return

        self.server = HTTPServer((self.host, self.port), MetricsHandler)
        self.running = True

        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        print(f"✅ Prometheus metrics server started on http://{self.host}:{self.port}/metrics")

    def _run_server(self):
        """运行服务器（在后台线程中）"""
        while self.running:
            self.server.handle_request()

    def stop(self):
        """停止服务器"""
        if not self.running:
            return

        self.running = False
        self.server.shutdown()
        self.thread.join(timeout=5)

        print(f"✅ Prometheus metrics server stopped")


# 全局服务器实例
_global_server: MetricsServer = None
_server_lock = threading.Lock()


def start_metrics_server(host: str = "0.0.0.0", port: int = 8000) -> MetricsServer:
    """
    启动全局指标服务器（单例模式）

    Args:
        host: 监听主机
        port: 监听端口

    Returns:
        MetricsServer实例
    """
    global _global_server

    with _server_lock:
        if _global_server is None:
            _global_server = MetricsServer(host, port)
            _global_server.start()

    return _global_server


def stop_metrics_server():
    """停止全局指标服务器"""
    global _global_server

    with _server_lock:
        if _global_server is not None:
            _global_server.stop()
            _global_server = None


# 命令行入口
def main():
    """主函数：启动指标服务器"""
    import argparse

    parser = argparse.ArgumentParser(description="Prometheus Metrics Exporter")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Listen port (default: 8000)")

    args = parser.parse_args()

    print("="*80)
    print("Prometheus Metrics Exporter")
    print("="*80)
    print(f"Listening on: http://{args.host}:{args.port}/metrics")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print("\nPress Ctrl+C to stop")
    print("="*80)

    # 启动服务器
    server = start_metrics_server(args.host, args.port)

    try:
        # 保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping server...")
        stop_metrics_server()
        print("✅ Server stopped")


if __name__ == "__main__":
    main()
