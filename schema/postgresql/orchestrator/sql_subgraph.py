"""Nested Graph for individual SQL statement transform-validate-fix loop.

Each SQL statement (extracted from MyBatis XML or standalone DDL) passes
through a three-node subgraph:

    transform_sql  -->  validate_sql  --(ok)-->  [END]
                            |
                        (error)
                            |
                            v
                        fix_sql  -->  validate_sql  (retry loop)

The subgraph caps retry attempts via ``max_node_executions`` to prevent
infinite fix loops.  It can be embedded as a node inside the main
migration Graph or invoked standalone for batch SQL processing.

Usage::

    from postgresql.orchestrator.sql_subgraph import build_sql_transform_subgraph

    subgraph = build_sql_transform_subgraph(
        transformer_agent=transformer,
        validator_agent=validator,
        fixer_agent=fixer,
    )
    result = subgraph("Convert: SELECT NVL(col, 0) FROM dual")
"""

from __future__ import annotations

import json
import logging
from typing import Any

from strands import Agent
from strands.multiagent import GraphBuilder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

DEFAULT_MAX_FIX_ATTEMPTS = 5
DEFAULT_NODE_TIMEOUT = 120  # seconds per node
DEFAULT_TOTAL_TIMEOUT = 600  # seconds for entire subgraph


# ---------------------------------------------------------------------------
# Condition functions
# ---------------------------------------------------------------------------

def _has_validation_error(state: Any) -> bool:
    """Check whether the validate_sql node reported errors.

    Examines the validate_sql node result for error indicators. Handles
    multiple output formats:
    - JSON with ``status: "FAIL"`` or ``syntax_valid: false``
    - Plain text containing "ERROR", "FAIL", or "syntax error"
    - A result object with a ``status`` attribute

    Args:
        state: The Strands Graph state object with a ``results`` dict.

    Returns:
        True if validation errors were detected, False otherwise.
    """
    validate_result = _get_node_result(state, "validate_sql")
    if validate_result is None:
        # No result yet -- should not happen, but treat as error
        logger.warning("validate_sql result is None; treating as error")
        return True

    result_str = str(validate_result)

    # Strategy 1: Parse JSON result
    try:
        parsed = json.loads(result_str)
        if isinstance(parsed, dict):
            status = parsed.get("status", "").upper()
            if status in ("FAIL", "ERROR"):
                return True
            if parsed.get("syntax_valid") is False:
                return True
            if status == "PASS":
                return False
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to parse validation result JSON, falling back to keyword search: %s", exc)

    # Strategy 2: Search for error keywords in text
    upper = result_str.upper()
    error_indicators = [
        "ERROR",
        "FAIL",
        "SYNTAX ERROR",
        "INVALID",
        "EXCEPTION",
        "DOES NOT EXIST",
        "UNDEFINED",
    ]
    for indicator in error_indicators:
        if indicator in upper:
            # Exclude false positives from instructions/prompts
            if f'"{indicator}"' not in upper and f"'{indicator}'" not in upper:
                return True

    # Strategy 3: Check result object status attribute
    status_attr = _safe_attr(validate_result, "status", None)
    if status_attr is not None:
        status_upper = str(status_attr).upper()
        if status_upper in ("FAIL", "ERROR", "FAILED"):
            return True

    return False


def _validation_passed(state: Any) -> bool:
    """Inverse of ``_has_validation_error`` -- returns True when SQL is valid.

    Used as the condition for the validate_sql -> [END] edge.
    """
    return not _has_validation_error(state)


# ---------------------------------------------------------------------------
# Subgraph builder
# ---------------------------------------------------------------------------

def build_sql_transform_subgraph(
    transformer_agent: Agent,
    validator_agent: Agent,
    fixer_agent: Agent,
    *,
    max_fix_attempts: int = DEFAULT_MAX_FIX_ATTEMPTS,
    node_timeout: int = DEFAULT_NODE_TIMEOUT,
    total_timeout: int = DEFAULT_TOTAL_TIMEOUT,
) -> Any:
    """Build a nested Graph for individual SQL: transform -> validate -> [fix loop].

    The graph has three nodes:

    1. **transform_sql**: Converts Oracle SQL to PostgreSQL using static rules
       and LLM-based conversion.
    2. **validate_sql**: Checks the converted SQL for syntax errors and
       semantic correctness against PostgreSQL.
    3. **fix_sql**: Attempts to fix validation errors using error context,
       pattern memory lookup, and LLM re-conversion.

    After ``fix_sql``, control returns to ``validate_sql`` for re-verification.
    The loop is bounded by ``max_fix_attempts``.

    Args:
        transformer_agent: Strands Agent for SQL conversion.
        validator_agent: Strands Agent for SQL validation.
        fixer_agent: Strands Agent for fixing failed conversions.
        max_fix_attempts: Maximum number of fix-validate cycles before
            giving up. Defaults to 5.
        node_timeout: Timeout in seconds for each individual node.
            Defaults to 120.
        total_timeout: Timeout in seconds for the entire subgraph execution.
            Defaults to 600.

    Returns:
        A compiled Strands Graph object ready for execution.

    Example::

        subgraph = build_sql_transform_subgraph(
            transformer_agent=my_transformer,
            validator_agent=my_validator,
            fixer_agent=my_fixer,
            max_fix_attempts=3,
        )
        result = subgraph("Convert: SELECT SYSDATE FROM DUAL")
    """
    builder = GraphBuilder()

    # -- Nodes --
    builder.add_node(transformer_agent, "transform_sql")
    builder.add_node(validator_agent, "validate_sql")
    builder.add_node(fixer_agent, "fix_sql")

    # -- Edges --
    # transform -> validate (always)
    builder.add_edge("transform_sql", "validate_sql")

    # validate -> fix_sql (if errors detected)
    builder.add_edge(
        "validate_sql",
        "fix_sql",
        condition=_has_validation_error,
    )

    # validate -> [END] (if validation passed -- None target means end)
    # Some Strands versions use None as end sentinel; if not supported,
    # the graph terminates when no outgoing edge condition matches.

    # fix_sql -> validate_sql (retry loop)
    builder.add_edge("fix_sql", "validate_sql")

    # -- Safety limits --
    builder.set_entry_point("transform_sql")
    builder.set_max_node_executions(max_fix_attempts)
    builder.set_node_timeout(node_timeout)
    builder.set_execution_timeout(total_timeout)

    # Reset fixer state on each revisit to avoid stale context
    builder.reset_on_revisit("fix_sql")

    graph = builder.build()

    logger.info(
        "SQL transform subgraph built: max_fixes=%d, node_timeout=%ds, total_timeout=%ds",
        max_fix_attempts,
        node_timeout,
        total_timeout,
    )

    return graph


# ---------------------------------------------------------------------------
# Batch processing helper
# ---------------------------------------------------------------------------

def build_batch_sql_input(
    sql_statement: str,
    object_name: str,
    object_type: str = "SQL",
    context: dict | None = None,
) -> str:
    """Build an input prompt for a single SQL transformation through the subgraph.

    Args:
        sql_statement: The original Oracle SQL/DDL to convert.
        object_name: Identifier for this SQL (e.g., MyBatis mapper ID).
        object_type: Type of SQL object (SELECT, INSERT, DDL, etc.).
        context: Optional additional context (schema metadata, conversion
            rules, prior errors).

    Returns:
        Formatted prompt string for the transform_sql node.
    """
    parts = [
        f"Convert the following Oracle {object_type} to PostgreSQL.",
        f"Object: {object_name}",
        "",
        "## Oracle SQL",
        "```sql",
        sql_statement.strip(),
        "```",
    ]

    if context:
        if "schema_metadata" in context:
            parts.extend([
                "",
                "## Schema Metadata",
                str(context["schema_metadata"]),
            ])
        if "conversion_rules" in context:
            parts.extend([
                "",
                "## Applicable Conversion Rules",
                str(context["conversion_rules"]),
            ])
        if "prior_errors" in context:
            parts.extend([
                "",
                "## Prior Conversion Errors (avoid these)",
                str(context["prior_errors"]),
            ])

    parts.extend([
        "",
        "## Requirements",
        "- Output ONLY the converted PostgreSQL SQL",
        "- Preserve functional equivalence",
        "- Add explicit type casts where needed",
        "- Handle Oracle NULL behavior differences",
    ])

    return "\n".join(parts)


def build_fix_input(
    original_sql: str,
    converted_sql: str,
    validation_error: str,
    object_name: str,
    attempt_number: int,
) -> str:
    """Build an input prompt for the fix_sql node after validation failure.

    Args:
        original_sql: The original Oracle SQL.
        converted_sql: The PostgreSQL conversion that failed validation.
        validation_error: Error message from the validator.
        object_name: Identifier for this SQL object.
        attempt_number: Which fix attempt this is (for context).

    Returns:
        Formatted prompt string for the fix_sql node.
    """
    return "\n".join([
        f"Fix the failed PostgreSQL conversion for '{object_name}' (attempt #{attempt_number}).",
        "",
        "## Original Oracle SQL",
        "```sql",
        original_sql.strip(),
        "```",
        "",
        "## Failed PostgreSQL Conversion",
        "```sql",
        converted_sql.strip(),
        "```",
        "",
        "## Validation Error",
        "```",
        validation_error.strip(),
        "```",
        "",
        "## Instructions",
        "1. Analyze the error and identify the root cause",
        "2. Search pattern memory for known fixes for this error type",
        "3. Apply the fix and output the corrected PostgreSQL SQL",
        "4. If the fix succeeds, store the error->fix pattern for future use",
        "",
        "Output ONLY the corrected PostgreSQL SQL, no explanations.",
    ])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_node_result(state: Any, node_id: str) -> Any:
    """Extract the result of a specific node from graph state."""
    results = _safe_attr(state, "results", {})
    if isinstance(results, dict):
        node_result = results.get(node_id)
        if node_result is not None:
            # The result might be wrapped in a result object
            return _safe_attr(node_result, "result", node_result)
    return None


def _safe_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Get attribute or dict key safely."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)
