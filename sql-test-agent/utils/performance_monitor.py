"""Performance monitoring utilities."""

import time
import psutil
from contextlib import contextmanager
from typing import Dict, Optional

from models.data_models import PerformanceMetrics
from .logger import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, float] = {}
        self.start_time: Optional[float] = None
        self.query_count = 0
        self.logger = get_logger(__name__)
    
    def start(self) -> None:
        """Start performance monitoring."""
        self.start_time = time.time()
        self.metrics = {
            "total_execution_time": 0.0,
            "database_connection_time": 0.0,
            "query_execution_time": 0.0,
            "comparison_time": 0.0,
            "transformation_time": 0.0,
            "llm_analysis_time": 0.0,
        }
        self.query_count = 0
        self.logger.info("performance_monitoring_started")
    
    @contextmanager
    def measure(self, operation: str):
        """
        Context manager to measure operation time.
        
        Args:
            operation: Name of the operation being measured
            
        Yields:
            None
        """
        start = time.time()
        try:
            yield
        finally:
            elapsed = (time.time() - start) * 1000  # Convert to milliseconds
            self.record_metric(operation, elapsed)
            self.logger.debug(
                "operation_measured",
                operation=operation,
                elapsed_ms=elapsed,
            )
    
    def record_metric(self, name: str, value: float) -> None:
        """
        Record a performance metric.
        
        Args:
            name: Metric name
            value: Metric value (in milliseconds)
        """
        if name not in self.metrics:
            self.metrics[name] = 0.0
        self.metrics[name] += value
    
    def increment_query_count(self) -> None:
        """Increment the query counter."""
        self.query_count += 1
    
    def get_memory_usage(self) -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Memory usage in megabytes
        """
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def get_metrics(self) -> PerformanceMetrics:
        """
        Get performance metrics summary.
        
        Returns:
            PerformanceMetrics object
        """
        if self.start_time is None:
            raise RuntimeError("Performance monitoring not started")
        
        total_time = time.time() - self.start_time
        
        return PerformanceMetrics(
            total_execution_time_seconds=total_time,
            average_query_time_ms=(
                self.metrics.get("query_execution_time", 0.0) / max(self.query_count, 1)
            ),
            database_connection_time_ms=self.metrics.get("database_connection_time", 0.0),
            comparison_time_ms=self.metrics.get("comparison_time", 0.0),
            transformation_time_ms=self.metrics.get("transformation_time", 0.0),
            llm_analysis_time_ms=self.metrics.get("llm_analysis_time", 0.0),
            queries_per_second=self.query_count / max(total_time, 0.001),
            memory_usage_mb=self.get_memory_usage(),
        )
    
    def log_metrics(self) -> None:
        """Log performance metrics."""
        metrics = self.get_metrics()
        self.logger.info(
            "performance_metrics",
            total_time_seconds=metrics.total_execution_time_seconds,
            avg_query_time_ms=metrics.average_query_time_ms,
            queries_per_second=metrics.queries_per_second,
            memory_usage_mb=metrics.memory_usage_mb,
        )
