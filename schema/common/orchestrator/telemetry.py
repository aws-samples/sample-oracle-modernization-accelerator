"""OpenTelemetry instrumentation for OMA migration pipeline.

Provides tracing, metrics, and logging integration with AWS X-Ray
via OpenTelemetry SDK. Tracks per-agent execution time, token usage,
tool call counts, and pipeline progress.

Usage:
    from common.orchestrator.telemetry import init_telemetry, trace_node

    init_telemetry()

    with trace_node("discover", migration_id="mig-123"):
        result = discovery_agent(prompt)

Traces are exported to AWS X-Ray via the OTLP exporter.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry; gracefully degrade if not installed
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    logger.info("OpenTelemetry not installed; telemetry disabled. pip install opentelemetry-sdk opentelemetry-exporter-otlp")

# Module-level tracer and meter
_tracer = None
_meter = None

# Metrics instruments
_node_duration_histogram = None
_token_counter = None
_tool_call_counter = None
_pipeline_status_counter = None


def init_telemetry(
    service_name: str = "oma-migration",
    otlp_endpoint: str | None = None,
) -> bool:
    """Initialize OpenTelemetry tracing and metrics.

    Args:
        service_name: Service name for traces/metrics.
        otlp_endpoint: OTLP gRPC endpoint. Defaults to AWS X-Ray daemon
            or localhost:4317.

    Returns:
        True if telemetry was initialized, False if OTel is not available.
    """
    global _tracer, _meter
    global _node_duration_histogram, _token_counter, _tool_call_counter, _pipeline_status_counter

    if not _OTEL_AVAILABLE:
        return False

    endpoint = otlp_endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")

    resource = Resource.create({
        "service.name": service_name,
        "service.version": "2.0",
        "deployment.environment": os.environ.get("OMA_ENV", "development"),
        "cloud.provider": "aws",
        "cloud.region": os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2"),
    })

    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer("oma.pipeline", "2.0")

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True),
        export_interval_millis=30000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter("oma.pipeline", "2.0")

    # Create metric instruments
    _node_duration_histogram = _meter.create_histogram(
        "oma.node.duration",
        unit="s",
        description="Duration of each pipeline node execution",
    )
    _token_counter = _meter.create_counter(
        "oma.tokens.total",
        unit="tokens",
        description="Total tokens consumed by agent",
    )
    _tool_call_counter = _meter.create_counter(
        "oma.tool_calls.total",
        unit="calls",
        description="Total tool calls made by agents",
    )
    _pipeline_status_counter = _meter.create_counter(
        "oma.pipeline.status",
        description="Pipeline completion status counts",
    )

    logger.info("OpenTelemetry initialized: endpoint=%s, service=%s", endpoint, service_name)
    return True


@contextmanager
def trace_node(
    node_name: str,
    *,
    migration_id: str = "",
    phase: str = "schema",
    agent_name: str = "",
) -> Generator[dict, None, None]:
    """Context manager that creates a trace span for a pipeline node.

    Records node execution time and allows adding custom attributes.

    Args:
        node_name: Name of the graph node (e.g., "discover", "design").
        migration_id: Migration run identifier.
        phase: Pipeline phase ("schema" or "data").
        agent_name: Name of the agent executing this node.

    Yields:
        Dict for collecting metrics (add "tokens_in", "tokens_out", "tool_calls").
    """
    metrics_bag: dict[str, Any] = {
        "tokens_in": 0,
        "tokens_out": 0,
        "tool_calls": 0,
    }

    if _tracer:
        with _tracer.start_as_current_span(
            f"oma.node.{node_name}",
            attributes={
                "oma.migration_id": migration_id,
                "oma.phase": phase,
                "oma.node_name": node_name,
                "oma.agent_name": agent_name,
            },
        ) as span:
            start = time.monotonic()
            try:
                yield metrics_bag
                span.set_status(trace.StatusCode.OK)
            except Exception as exc:
                span.set_status(trace.StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
            finally:
                duration = time.monotonic() - start
                span.set_attribute("oma.duration_seconds", duration)
                span.set_attribute("oma.tokens_in", metrics_bag.get("tokens_in", 0))
                span.set_attribute("oma.tokens_out", metrics_bag.get("tokens_out", 0))
                span.set_attribute("oma.tool_calls", metrics_bag.get("tool_calls", 0))

                # Record metrics
                attrs = {"node": node_name, "phase": phase}
                if _node_duration_histogram:
                    _node_duration_histogram.record(duration, attrs)
                if _token_counter:
                    _token_counter.add(
                        metrics_bag.get("tokens_in", 0) + metrics_bag.get("tokens_out", 0),
                        attrs,
                    )
                if _tool_call_counter:
                    _tool_call_counter.add(metrics_bag.get("tool_calls", 0), attrs)
    else:
        # OTel not available; just yield metrics bag for compatibility
        start = time.monotonic()
        yield metrics_bag
        duration = time.monotonic() - start
        logger.info(
            "[%s] Node '%s' completed in %.1fs (tokens: %d in, %d out, %d tool calls)",
            migration_id, node_name, duration,
            metrics_bag.get("tokens_in", 0),
            metrics_bag.get("tokens_out", 0),
            metrics_bag.get("tool_calls", 0),
        )


def record_pipeline_status(migration_id: str, status: str, phase: str = "schema") -> None:
    """Record pipeline completion status as a metric.

    Args:
        migration_id: Migration run identifier.
        status: Final status ("completed", "failed", "resumed").
        phase: Pipeline phase.
    """
    if _pipeline_status_counter:
        _pipeline_status_counter.add(1, {"status": status, "phase": phase})
    logger.info("[%s] Pipeline %s: status=%s", migration_id, phase, status)
