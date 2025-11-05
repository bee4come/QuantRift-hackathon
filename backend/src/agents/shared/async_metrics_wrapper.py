"""
Non-blocking Metrics Wrapper - Fix for metrics threading deadlock

This wrapper provides async, fire-and-forget metrics operations that never block
the calling thread. All metrics operations are queued and processed by a background
worker thread.

Key improvements:
1. Non-blocking: All operations return immediately, never waiting for locks
2. Queue-based: Uses thread-safe queue instead of locks for coordination
3. Timeout protection: Background worker has timeout protection
4. Graceful degradation: If queue is full, operations are dropped (not blocked)

Usage:
    from async_metrics_wrapper import AsyncMetricsWrapper

    metrics = AsyncMetricsWrapper()

    # These return immediately, never block
    metrics.increment("counter_name", labels={"key": "value"})
    metrics.observe("histogram_name", 1.23, labels={"key": "value"})
"""

import queue
import threading
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MetricOperation(Enum):
    """Types of metric operations"""
    INCREMENT = "increment"
    OBSERVE = "observe"
    GAUGE = "gauge"


@dataclass
class MetricCommand:
    """A metric operation command to be executed"""
    operation: MetricOperation
    name: str
    value: float
    labels: Dict[str, str]


class AsyncMetricsWrapper:
    """
    Non-blocking async wrapper for MetricsCollector

    All operations are queued and processed by a background worker thread.
    Operations never block the caller, providing fire-and-forget semantics.

    Architecture:
    1. Caller thread: Puts command in queue (non-blocking with timeout)
    2. Worker thread: Processes commands from queue and calls actual metrics
    3. If queue is full: Command is dropped (logged but never blocks)
    """

    def __init__(self, max_queue_size: int = 10000, queue_timeout: float = 0.001):
        """
        Initialize async metrics wrapper

        Args:
            max_queue_size: Maximum commands in queue (prevents memory growth)
            queue_timeout: Max time to wait when queueing (seconds, very short)
        """
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.queue_timeout = queue_timeout
        self.worker_thread = None
        self.running = False
        self.dropped_count = 0

        # Lazy initialization - only import and create actual collector when needed
        self._collector = None
        self._collector_lock = threading.Lock()

    def start(self):
        """Start the background worker thread"""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """Stop the background worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)

    def _get_collector(self):
        """Lazy-load the actual metrics collector (only in worker thread)"""
        if self._collector is None:
            with self._collector_lock:
                if self._collector is None:
                    try:
                        from .metrics_collector import get_metrics_collector
                        self._collector = get_metrics_collector()
                    except Exception as e:
                        # If metrics collector fails to initialize, use no-op
                        print(f"Warning: Failed to initialize metrics collector: {e}")
                        self._collector = None
        return self._collector

    def _worker(self):
        """
        Background worker thread that processes metric commands

        This runs in a separate thread and is the only place that actually
        calls the underlying metrics collector (which may use locks).
        """
        while self.running:
            try:
                # Wait for command with timeout (allows clean shutdown)
                command = self.queue.get(timeout=0.1)

                # Get collector (lazy initialization)
                collector = self._get_collector()
                if collector is None:
                    continue

                # Execute the metric operation
                try:
                    if command.operation == MetricOperation.INCREMENT:
                        collector.increment(
                            command.name,
                            labels=command.labels,
                            amount=command.value
                        )
                    elif command.operation == MetricOperation.OBSERVE:
                        collector.observe(
                            command.name,
                            command.value,
                            labels=command.labels
                        )
                    elif command.operation == MetricOperation.GAUGE:
                        collector.gauge(
                            command.name,
                            command.value,
                            labels=command.labels
                        )
                except Exception as e:
                    # Never let metric errors crash the worker
                    pass

                # Mark task as done
                self.queue.task_done()

            except queue.Empty:
                # No commands available, loop continues
                continue
            except Exception as e:
                # Worker should never crash
                continue

    def _enqueue(self, command: MetricCommand) -> bool:
        """
        Enqueue a metric command (non-blocking)

        Args:
            command: The metric command to execute

        Returns:
            True if queued, False if dropped (queue full or timeout)
        """
        # Ensure worker is running
        if not self.running:
            self.start()

        try:
            # Try to queue with very short timeout (never block caller)
            self.queue.put(command, block=True, timeout=self.queue_timeout)
            return True
        except queue.Full:
            # Queue is full, drop this metric (fire-and-forget semantics)
            self.dropped_count += 1
            return False
        except Exception:
            # Any other error, also drop
            self.dropped_count += 1
            return False

    def increment(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        amount: float = 1.0
    ):
        """
        Increment a counter metric (non-blocking, fire-and-forget)

        Args:
            name: Metric name
            labels: Label dictionary
            amount: Amount to increment
        """
        command = MetricCommand(
            operation=MetricOperation.INCREMENT,
            name=name,
            value=amount,
            labels=labels or {}
        )
        self._enqueue(command)

    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Observe a histogram value (non-blocking, fire-and-forget)

        Args:
            name: Metric name
            value: Observed value
            labels: Label dictionary
        """
        command = MetricCommand(
            operation=MetricOperation.OBSERVE,
            name=name,
            value=value,
            labels=labels or {}
        )
        self._enqueue(command)

    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Set a gauge metric value (non-blocking, fire-and-forget)

        Args:
            name: Metric name
            value: Gauge value
            labels: Label dictionary
        """
        command = MetricCommand(
            operation=MetricOperation.GAUGE,
            name=name,
            value=value,
            labels=labels or {}
        )
        self._enqueue(command)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get wrapper statistics

        Returns:
            Dictionary with queue size, dropped count, etc.
        """
        return {
            "queue_size": self.queue.qsize(),
            "dropped_count": self.dropped_count,
            "running": self.running
        }


# Global singleton instance
_global_async_metrics: Optional[AsyncMetricsWrapper] = None
_global_lock = threading.Lock()


def get_async_metrics() -> AsyncMetricsWrapper:
    """
    Get global async metrics wrapper instance (singleton)

    Returns:
        AsyncMetricsWrapper instance
    """
    global _global_async_metrics

    if _global_async_metrics is None:
        with _global_lock:
            if _global_async_metrics is None:
                _global_async_metrics = AsyncMetricsWrapper()
                _global_async_metrics.start()

    return _global_async_metrics


# Example usage
if __name__ == "__main__":
    import time

    print("Testing AsyncMetricsWrapper...")

    metrics = get_async_metrics()

    # These should return immediately, never block
    start = time.time()
    for i in range(1000):
        metrics.increment("test_counter", labels={"test": "value"})
        metrics.observe("test_histogram", i * 0.1, labels={"test": "value"})
    end = time.time()

    print(f"1000 operations completed in {(end - start) * 1000:.2f}ms")
    print(f"Stats: {metrics.get_stats()}")

    # Wait for worker to process
    time.sleep(0.5)

    print(f"Final stats: {metrics.get_stats()}")
    metrics.stop()
