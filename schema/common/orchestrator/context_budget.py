"""Proactive token overflow prevention for OMA migration pipeline.

Monitors approximate conversation context size and takes preventive action
before hitting Bedrock's token limit (1M for Opus 4.6). This is Layer 0
of the token defense system -- acting BEFORE overflow occurs.

Defense layers:
  Layer 0: Proactive budget monitoring + tool output truncation (this module)
  Layer 1: SDK monkey-patch for Opus 4.6 error pattern (factory.py)
  Layer 2: Direct data transfer tool (data_transfer_tools.py)
  Layer 3: Phase separation with fresh agents (pipeline.py)

Usage:
    from common.orchestrator.context_budget import BudgetAwareConversationManager

    manager = BudgetAwareConversationManager(
        max_context_tokens=800_000,  # 80% of 1M limit
        max_tool_result_tokens=50_000,
    )
    agent = Agent(model=model, conversation_manager=manager, ...)
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Bedrock Opus 4.6 context window
BEDROCK_MAX_TOKENS = 1_000_000

# Safety margin: trigger preventive action at 80% of max
DEFAULT_BUDGET_RATIO = 0.80
DEFAULT_MAX_CONTEXT = int(BEDROCK_MAX_TOKENS * DEFAULT_BUDGET_RATIO)

# Maximum tokens for a single tool result before truncation
DEFAULT_MAX_TOOL_RESULT = 50_000

# Truncation message appended when output is cut
TRUNCATION_NOTICE = (
    "\n\n[OUTPUT TRUNCATED: Original output was {original_chars} chars "
    "(~{original_tokens:,} tokens). Truncated to {kept_chars} chars "
    "(~{kept_tokens:,} tokens) to prevent context overflow. "
    "Key data has been preserved.]"
)


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length.

    Uses a conservative ratio of ~3.5 characters per token for mixed
    English/Korean/SQL content. This is intentionally conservative
    (overestimates tokens) to leave safety margin.

    Args:
        text: Input text to estimate.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    return max(1, len(text) // 3)


def truncate_tool_output(
    output: str,
    max_tokens: int = DEFAULT_MAX_TOOL_RESULT,
    *,
    preserve_json_structure: bool = True,
) -> str:
    """Truncate a tool output to fit within token budget.

    Intelligently truncates by:
    1. If JSON: preserves opening/closing structure and key fields
    2. If SQL/code: preserves first and last sections
    3. Otherwise: simple head truncation with notice

    Args:
        output: Raw tool output string.
        max_tokens: Maximum tokens allowed for this output.
        preserve_json_structure: Try to keep JSON parseable after truncation.

    Returns:
        Truncated output string, or original if within budget.
    """
    estimated = estimate_tokens(output)
    if estimated <= max_tokens:
        return output

    max_chars = max_tokens * 3  # Reverse the estimation
    original_chars = len(output)
    original_tokens = estimated

    # For JSON-like output, try to preserve structure
    if preserve_json_structure and output.strip().startswith("{"):
        truncated = _truncate_json_like(output, max_chars)
    else:
        # Keep head portion
        truncated = output[:max_chars]
        # Try to end at a line boundary
        last_newline = truncated.rfind("\n")
        if last_newline > max_chars * 0.8:
            truncated = truncated[:last_newline]

    notice = TRUNCATION_NOTICE.format(
        original_chars=original_chars,
        original_tokens=original_tokens,
        kept_chars=len(truncated),
        kept_tokens=estimate_tokens(truncated),
    )

    logger.warning(
        "Tool output truncated: %d tokens -> %d tokens (max %d)",
        original_tokens, estimate_tokens(truncated), max_tokens,
    )

    return truncated + notice


def _truncate_json_like(text: str, max_chars: int) -> str:
    """Truncate JSON-like text while preserving structure.

    Keeps the first portion of the JSON and closes any open braces/brackets.
    """
    head = text[:max_chars]

    # Count unclosed braces/brackets
    open_braces = head.count("{") - head.count("}")
    open_brackets = head.count("[") - head.count("]")

    # Close any open structures
    closing = ""
    if open_brackets > 0:
        closing += "]" * open_brackets
    if open_braces > 0:
        closing += "}" * open_braces

    # Try to cut at a clean boundary (after a comma or closing brace)
    clean_cut = max(
        head.rfind(",\n"),
        head.rfind(","),
        head.rfind("}"),
        head.rfind("]"),
    )
    if clean_cut > max_chars * 0.7:
        head = head[:clean_cut + 1]
        # Recount after clean cut
        open_braces = head.count("{") - head.count("}")
        open_brackets = head.count("[") - head.count("]")
        closing = "]" * max(0, open_brackets) + "}" * max(0, open_braces)

    return head + closing


class ContextBudgetMonitor:
    """Tracks approximate token usage across an agent's conversation.

    Provides warnings when approaching the budget limit and can
    recommend actions (truncate, slide window, etc.).
    """

    def __init__(
        self,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT,
        max_tool_result_tokens: int = DEFAULT_MAX_TOOL_RESULT,
        warning_ratio: float = 0.70,
    ):
        self.max_context_tokens = max_context_tokens
        self.max_tool_result_tokens = max_tool_result_tokens
        self.warning_threshold = int(max_context_tokens * warning_ratio)
        self._estimated_total: int = 0
        self._message_count: int = 0

    def track_message(self, content: str) -> None:
        """Track a message added to the conversation."""
        tokens = estimate_tokens(content)
        self._estimated_total += tokens
        self._message_count += 1

        if self._estimated_total >= self.max_context_tokens:
            logger.error(
                "CONTEXT BUDGET EXCEEDED: ~%d tokens (limit: %d). "
                "Context reduction needed.",
                self._estimated_total, self.max_context_tokens,
            )
        elif self._estimated_total >= self.warning_threshold:
            logger.warning(
                "Context budget warning: ~%d/%d tokens (%.0f%%). "
                "%d messages in conversation.",
                self._estimated_total, self.max_context_tokens,
                self._estimated_total / self.max_context_tokens * 100,
                self._message_count,
            )

    def should_truncate_tool_result(self, result: str) -> bool:
        """Check if a tool result should be truncated."""
        return estimate_tokens(result) > self.max_tool_result_tokens

    def truncate_if_needed(self, result: str) -> str:
        """Truncate tool result if it exceeds the per-result budget."""
        if self.should_truncate_tool_result(result):
            return truncate_tool_output(result, self.max_tool_result_tokens)
        return result

    @property
    def estimated_tokens(self) -> int:
        return self._estimated_total

    @property
    def remaining_budget(self) -> int:
        return max(0, self.max_context_tokens - self._estimated_total)

    @property
    def usage_ratio(self) -> float:
        return self._estimated_total / self.max_context_tokens if self.max_context_tokens else 0

    def get_status(self) -> dict:
        """Return current budget status."""
        return {
            "estimated_tokens": self._estimated_total,
            "max_tokens": self.max_context_tokens,
            "remaining": self.remaining_budget,
            "usage_pct": round(self.usage_ratio * 100, 1),
            "messages": self._message_count,
            "status": (
                "critical" if self.usage_ratio >= 0.90
                else "warning" if self.usage_ratio >= 0.70
                else "ok"
            ),
        }


def create_budget_monitor(
    *,
    budget_ratio: float = DEFAULT_BUDGET_RATIO,
    max_tool_result_tokens: int = DEFAULT_MAX_TOOL_RESULT,
) -> ContextBudgetMonitor:
    """Create a context budget monitor with standard settings.

    Args:
        budget_ratio: Fraction of BEDROCK_MAX_TOKENS to use as budget.
        max_tool_result_tokens: Max tokens per tool result.

    Returns:
        Configured ContextBudgetMonitor.
    """
    return ContextBudgetMonitor(
        max_context_tokens=int(BEDROCK_MAX_TOKENS * budget_ratio),
        max_tool_result_tokens=max_tool_result_tokens,
    )
