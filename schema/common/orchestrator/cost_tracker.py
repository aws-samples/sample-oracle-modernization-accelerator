"""Bedrock API Cost Tracker for OMA Migration Pipeline.

Tracks token usage per agent/node and converts to estimated USD cost
based on Bedrock pricing. Provides per-pipeline cost summary.

Usage:
    from common.orchestrator.cost_tracker import CostTracker

    tracker = CostTracker()
    tracker.record(node="discover", tokens_in=15000, tokens_out=3000)
    tracker.record(node="design", tokens_in=25000, tokens_out=8000)
    summary = tracker.summary()
    # {'total_cost_usd': 0.45, 'nodes': {...}, ...}
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Bedrock Pricing (per 1K tokens, USD) ──
# Source: https://aws.amazon.com/bedrock/pricing/
# Claude Opus 4.6 (us/eu cross-region inference)
PRICING = {
    "claude-opus-4-6": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5": {"input": 0.0008, "output": 0.004},
    # Fallback
    "default": {"input": 0.015, "output": 0.075},
}


@dataclass
class NodeCost:
    """Cost tracking for a single pipeline node."""
    node_name: str
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: int = 0
    duration_s: float = 0.0
    start_time: float = 0.0

    @property
    def cost_in(self) -> float:
        rate = PRICING.get("claude-opus-4-6", PRICING["default"])
        return self.tokens_in / 1000 * rate["input"]

    @property
    def cost_out(self) -> float:
        rate = PRICING.get("claude-opus-4-6", PRICING["default"])
        return self.tokens_out / 1000 * rate["output"]

    @property
    def total_cost(self) -> float:
        return self.cost_in + self.cost_out

    def to_dict(self) -> dict:
        return {
            "node": self.node_name,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tool_calls": self.tool_calls,
            "duration_s": round(self.duration_s, 1),
            "cost_input_usd": round(self.cost_in, 4),
            "cost_output_usd": round(self.cost_out, 4),
            "cost_total_usd": round(self.total_cost, 4),
        }


@dataclass
class CostTracker:
    """Tracks Bedrock API costs across the entire migration pipeline."""

    model_id: str = "claude-opus-4-6"
    nodes: dict[str, NodeCost] = field(default_factory=dict)
    _pipeline_start: float = field(default_factory=time.time)

    def record(
        self,
        node: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        tool_calls: int = 0,
        duration_s: float = 0.0,
    ) -> None:
        """Record token usage for a pipeline node."""
        if node not in self.nodes:
            self.nodes[node] = NodeCost(node_name=node)

        nc = self.nodes[node]
        nc.tokens_in += tokens_in
        nc.tokens_out += tokens_out
        nc.tool_calls += tool_calls
        nc.duration_s += duration_s

    def node_start(self, node: str) -> None:
        """Mark node execution start time."""
        if node not in self.nodes:
            self.nodes[node] = NodeCost(node_name=node)
        self.nodes[node].start_time = time.time()

    def node_end(self, node: str, tokens_in: int = 0, tokens_out: int = 0,
                 tool_calls: int = 0) -> None:
        """Mark node execution end, auto-calculate duration."""
        if node not in self.nodes:
            self.nodes[node] = NodeCost(node_name=node)
        nc = self.nodes[node]
        if nc.start_time > 0:
            nc.duration_s += time.time() - nc.start_time
            nc.start_time = 0
        nc.tokens_in += tokens_in
        nc.tokens_out += tokens_out
        nc.tool_calls += tool_calls

    @property
    def total_tokens_in(self) -> int:
        return sum(n.tokens_in for n in self.nodes.values())

    @property
    def total_tokens_out(self) -> int:
        return sum(n.tokens_out for n in self.nodes.values())

    @property
    def total_cost_usd(self) -> float:
        return sum(n.total_cost for n in self.nodes.values())

    @property
    def total_tool_calls(self) -> int:
        return sum(n.tool_calls for n in self.nodes.values())

    def summary(self) -> dict[str, Any]:
        """Generate cost summary for the entire pipeline run."""
        elapsed = time.time() - self._pipeline_start
        rate = PRICING.get(self.model_id, PRICING["default"])

        return {
            "model": self.model_id,
            "pricing_per_1k": rate,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_tokens": self.total_tokens_in + self.total_tokens_out,
            "total_tool_calls": self.total_tool_calls,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "pipeline_duration_s": round(elapsed, 1),
            "cost_per_minute_usd": round(
                self.total_cost_usd / (elapsed / 60) if elapsed > 60 else 0, 4
            ),
            "nodes": {
                name: nc.to_dict()
                for name, nc in sorted(self.nodes.items())
            },
        }

    def log_summary(self) -> None:
        """Log cost summary at INFO level."""
        s = self.summary()
        logger.info(
            "Pipeline cost summary: $%.4f USD "
            "(%d tokens in, %d tokens out, %d tool calls, %.1fs)",
            s["total_cost_usd"],
            s["total_tokens_in"],
            s["total_tokens_out"],
            s["total_tool_calls"],
            s["pipeline_duration_s"],
        )
        for name, nc in s["nodes"].items():
            logger.info(
                "  %s: $%.4f (in=%d, out=%d, tools=%d, %.1fs)",
                name, nc["cost_total_usd"],
                nc["tokens_in"], nc["tokens_out"],
                nc["tool_calls"], nc["duration_s"],
            )

    def format_report(self) -> str:
        """Format cost report as human-readable text."""
        s = self.summary()
        lines = [
            "=" * 60,
            "BEDROCK API COST REPORT",
            "=" * 60,
            f"Model: {s['model']}",
            f"Duration: {s['pipeline_duration_s']:.1f}s",
            f"Total tokens: {s['total_tokens']:,} "
            f"(in: {s['total_tokens_in']:,}, out: {s['total_tokens_out']:,})",
            f"Total tool calls: {s['total_tool_calls']}",
            f"Total cost: ${s['total_cost_usd']:.4f} USD",
            f"Cost/min: ${s['cost_per_minute_usd']:.4f} USD",
            "",
            f"{'Node':<20} {'In':>8} {'Out':>8} {'Tools':>6} {'Time':>7} {'Cost':>10}",
            "-" * 60,
        ]
        for name, nc in s["nodes"].items():
            lines.append(
                f"{name:<20} {nc['tokens_in']:>8,} {nc['tokens_out']:>8,} "
                f"{nc['tool_calls']:>6} {nc['duration_s']:>6.1f}s "
                f"${nc['cost_total_usd']:>8.4f}"
            )
        lines.extend(["=" * 60, ""])
        return "\n".join(lines)
