"""Graph hook handlers for monitoring and logging OMA migration execution.

Provides a ``MigrationHookProvider`` that attaches to Strands Graph events
to log node transitions, track timing/token metrics, and optionally push
real-time notifications over WebSocket.

Usage with Strands Graph::

    from common.orchestrator.hooks import MigrationHookProvider

    hooks = MigrationHookProvider(migration_id="mig-001")
    graph = build_migration_pipeline(agents)
    # Attach hooks before execution
    result = graph(prompt, hooks=hooks.as_hooks())
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from common.orchestrator.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metric collection
# ---------------------------------------------------------------------------

@dataclass
class NodeMetrics:
    """Accumulated metrics for a single graph node execution."""

    node_id: str
    start_time: float = 0.0
    end_time: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    status: str = "pending"
    error: str | None = None
    execution_count: int = 0

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 3)
        return 0.0

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "duration_seconds": self.duration_seconds,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "status": self.status,
            "error": self.error,
            "execution_count": self.execution_count,
        }


@dataclass
class PipelineMetrics:
    """Accumulated metrics for the entire pipeline execution."""

    migration_id: str
    start_time: float = 0.0
    end_time: float = 0.0
    nodes: dict[str, NodeMetrics] = field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    execution_order: list[str] = field(default_factory=list)
    remediation_loops: int = 0

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 3)
        return 0.0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def to_dict(self) -> dict:
        return {
            "migration_id": self.migration_id,
            "duration_seconds": self.duration_seconds,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "remediation_loops": self.remediation_loops,
            "execution_order": self.execution_order,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }


# ---------------------------------------------------------------------------
# Hook provider
# ---------------------------------------------------------------------------

class MigrationHookProvider:
    """Hook provider for monitoring Strands Graph execution.

    Logs node start/stop events, tracks timing and token metrics, and
    optionally sends WebSocket notifications for real-time dashboards.

    Args:
        migration_id: Unique identifier for this migration run.
        ws_notify: Optional async callback ``(migration_id, event_type, data) -> None``
            for pushing real-time notifications.
        on_phase_change: Optional sync callback ``(phase_name, status) -> None``
            invoked when pipeline moves between phases.
    """

    def __init__(
        self,
        migration_id: str,
        ws_notify: Callable[..., Any] | None = None,
        on_phase_change: Callable[[str, str], None] | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.migration_id = migration_id
        self._ws_notify = ws_notify
        self._on_phase_change = on_phase_change
        self._cost_tracker = cost_tracker
        self.metrics = PipelineMetrics(migration_id=migration_id)

    # ------------------------------------------------------------------
    # Hook handlers
    # ------------------------------------------------------------------

    def on_graph_start(self, event: Any) -> None:
        """Called when the graph begins execution."""
        self.metrics.start_time = time.monotonic()
        logger.info(
            "[%s] Pipeline started",
            self.migration_id,
        )
        self._notify("pipeline_start", {"migration_id": self.migration_id})

    def on_graph_end(self, event: Any) -> None:
        """Called when the graph completes execution (success or failure)."""
        self.metrics.end_time = time.monotonic()
        status = _safe_attr(event, "status", "unknown")
        logger.info(
            "[%s] Pipeline completed: status=%s, duration=%.1fs, tokens=%d",
            self.migration_id,
            status,
            self.metrics.duration_seconds,
            self.metrics.total_tokens,
        )
        self._notify("pipeline_end", {
            "migration_id": self.migration_id,
            "status": str(status),
            "duration_seconds": self.metrics.duration_seconds,
            "total_tokens": self.metrics.total_tokens,
        })

    def on_node_start(self, event: Any) -> None:
        """Called before a node begins execution (BeforeNodeCallEvent)."""
        node_id = _safe_attr(event, "node_id", "unknown")
        now = time.monotonic()

        if node_id not in self.metrics.nodes:
            self.metrics.nodes[node_id] = NodeMetrics(node_id=node_id)

        node = self.metrics.nodes[node_id]
        node.start_time = now
        node.status = "running"
        node.execution_count += 1

        # Track remediation loops
        if node_id == "remediate":
            self.metrics.remediation_loops += 1

        self.metrics.execution_order.append(node_id)

        logger.info(
            "[%s] Node '%s' started (execution #%d)",
            self.migration_id,
            node_id,
            node.execution_count,
        )

        if self._on_phase_change:
            try:
                self._on_phase_change(node_id, "started")
            except Exception:
                logger.debug("on_phase_change callback failed", exc_info=True)

        if self._cost_tracker:
            self._cost_tracker.node_start(node_id)

        self._notify("node_start", {
            "node_id": node_id,
            "execution_count": node.execution_count,
        })

    def on_node_end(self, event: Any) -> None:
        """Called after a node completes execution."""
        node_id = _safe_attr(event, "node_id", "unknown")
        now = time.monotonic()

        node = self.metrics.nodes.get(node_id)
        if node is None:
            node = NodeMetrics(node_id=node_id)
            self.metrics.nodes[node_id] = node

        node.end_time = now
        node_status = _safe_attr(event, "status", "completed")
        node.status = str(node_status)

        # Extract token usage from node result
        inp = 0
        out = 0
        node_result = _safe_attr(event, "node_result", None)
        if node_result is not None:
            usage = _safe_attr(node_result, "usage", None)
            if usage is None:
                usage = _safe_attr(node_result, "token_usage", None)
            if usage is not None:
                inp = _safe_int(usage, "input_tokens")
                out = _safe_int(usage, "output_tokens")
                node.input_tokens += inp
                node.output_tokens += out
                self.metrics.total_input_tokens += inp
                self.metrics.total_output_tokens += out

        # Feed cost tracker
        if self._cost_tracker:
            self._cost_tracker.node_end(node_id, tokens_in=inp, tokens_out=out)

        # Check for errors
        error = _safe_attr(event, "error", None)
        if error is not None:
            node.error = str(error)
            node.status = "error"

        logger.info(
            "[%s] Node '%s' completed: status=%s, duration=%.1fs, tokens=%d",
            self.migration_id,
            node_id,
            node.status,
            node.duration_seconds,
            node.input_tokens + node.output_tokens,
        )

        if self._on_phase_change:
            try:
                self._on_phase_change(node_id, node.status)
            except Exception:
                logger.debug("on_phase_change callback failed", exc_info=True)

        self._notify("node_end", {
            "node_id": node_id,
            "status": node.status,
            "duration_seconds": node.duration_seconds,
        })

    def on_node_error(self, event: Any) -> None:
        """Called when a node raises an unhandled exception."""
        node_id = _safe_attr(event, "node_id", "unknown")
        error = _safe_attr(event, "error", "Unknown error")

        node = self.metrics.nodes.get(node_id)
        if node is not None:
            node.end_time = time.monotonic()
            node.status = "error"
            node.error = str(error)

        logger.error(
            "[%s] Node '%s' error: %s",
            self.migration_id,
            node_id,
            error,
        )

        self._notify("node_error", {
            "node_id": node_id,
            "error": str(error),
        })

    def on_handoff(self, event: Any) -> None:
        """Called when execution transitions between nodes."""
        source = _safe_attr(event, "source_node", "?")
        target = _safe_attr(event, "target_node", "?")

        logger.info(
            "[%s] Handoff: %s -> %s",
            self.migration_id,
            source,
            target,
        )

        self._notify("handoff", {
            "source_node": str(source),
            "target_node": str(target),
        })

    # ------------------------------------------------------------------
    # Hook registration
    # ------------------------------------------------------------------

    def as_hooks(self) -> dict[str, Callable]:
        """Return a dict of hook name -> handler suitable for Strands Graph.

        The returned dict maps Strands Graph event names to handler methods.
        Attach these when building or running the graph.

        Returns:
            Dict of event handlers keyed by Strands event names.
        """
        return {
            "on_graph_start": self.on_graph_start,
            "on_graph_end": self.on_graph_end,
            "on_node_start": self.on_node_start,
            "on_node_end": self.on_node_end,
            "on_node_error": self.on_node_error,
            "on_handoff": self.on_handoff,
        }

    def get_metrics(self) -> dict:
        """Return current pipeline metrics as a plain dict."""
        return self.metrics.to_dict()

    def get_node_metrics(self, node_id: str) -> dict | None:
        """Return metrics for a specific node, or None if not found."""
        node = self.metrics.nodes.get(node_id)
        return node.to_dict() if node else None

    # ------------------------------------------------------------------
    # Notification helpers
    # ------------------------------------------------------------------

    def _notify(self, event_type: str, data: dict) -> None:
        """Send a WebSocket notification if a callback is configured."""
        if self._ws_notify is None:
            return
        try:
            self._ws_notify(self.migration_id, event_type, data)
        except Exception:
            logger.debug(
                "WebSocket notification failed for event '%s'",
                event_type,
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Get attribute or dict key safely."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _safe_int(obj: Any, key: str) -> int:
    """Extract an integer from an object attribute or dict key."""
    val = _safe_attr(obj, key, 0)
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# WebSocket bridge: sync hook → async emit_event
# ---------------------------------------------------------------------------

def create_ws_notify() -> Callable[..., None]:
    """Create a no-op ws_notify callback for CLI execution.

    Returns a callable ``(migration_id, event_type, data) -> None`` suitable
    for passing to ``MigrationHookProvider(ws_notify=...)``.

    CLI 모드에서는 WebSocket 서버가 없으므로 로그만 남깁니다.
    """

    def _ws_notify(migration_id: str, event_type: str, data: dict) -> None:
        logger.debug("ws_notify [%s] %s: %s", migration_id, event_type, data.get("node_id", ""))

    return _ws_notify
