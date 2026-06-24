"""State management helpers for OMA migration orchestration.

Provides serialization/deserialization of migration state, input builders
for graph nodes, verdict parsing utilities, and DynamoDB checkpoint
persistence for resumable pipelines.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

CHECKPOINT_TABLE = "oma-migration-state"
AWS_REGION = "ap-northeast-2"


# ---------------------------------------------------------------------------
# Verdict enum used by the Evaluator node
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    """Evaluation verdict returned by the evaluator node."""

    GO = "GO"
    NO_GO = "NO_GO"
    CONDITIONAL = "CONDITIONAL"


# ---------------------------------------------------------------------------
# Migration phase tracking
# ---------------------------------------------------------------------------

class MigrationPhase(str, Enum):
    """Tracks which pipeline phase is currently active."""

    PENDING = "PENDING"
    DISCOVERY = "DISCOVERY"
    DESIGN = "DESIGN"
    TRANSFORM = "TRANSFORM"
    VERIFY = "VERIFY"
    EVALUATE = "EVALUATE"
    REMEDIATE = "REMEDIATE"
    REPORT = "REPORT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# State serialization
# ---------------------------------------------------------------------------

def serialize_migration_state(graph_result: Any) -> dict:
    """Extract migration state from a Strands Graph result for persistence.

    Converts the graph execution result into a plain ``dict`` suitable for
    JSON storage (DynamoDB, Aurora, local file).

    Args:
        graph_result: The result object returned by ``Graph.__call__`` or
            ``Graph.stream_async``.

    Returns:
        A JSON-serialisable dict with execution metadata and per-node results.
    """
    state: dict[str, Any] = {
        "status": str(_safe_attr(graph_result, "status", "unknown")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nodes": {},
        "metrics": {},
        "execution_time": _safe_attr(graph_result, "execution_time", 0),
        "total_nodes": _safe_attr(graph_result, "total_nodes", 0),
        "completed_nodes": _safe_attr(graph_result, "completed_nodes", 0),
        "failed_nodes": _safe_attr(graph_result, "failed_nodes", 0),
    }

    # Per-node results (GraphResult.results is dict[str, NodeResult])
    node_results = _safe_attr(graph_result, "results", {})
    if isinstance(node_results, dict):
        for node_id, node_result in node_results.items():
            state["nodes"][node_id] = {
                "status": str(_safe_attr(node_result, "status", "unknown")),
                "result_summary": _truncate(str(_safe_attr(node_result, "result", "")), 2000),
                "token_usage": _extract_token_usage(node_result),
                "execution_time": _safe_attr(node_result, "execution_time", 0),
                "execution_count": _safe_attr(node_result, "execution_count", 0),
            }

    # Execution history (GraphResult.execution_order is list[GraphNode])
    execution_order = _safe_attr(graph_result, "execution_order", [])
    state["execution_order"] = []
    for node in execution_order:
        node_name = _safe_attr(node, "name", None) or _safe_attr(node, "node_id", str(node))
        state["execution_order"].append(str(node_name))

    # Accumulated metrics (total pipeline tokens)
    accumulated = _safe_attr(graph_result, "accumulated_usage", None)
    if accumulated is not None:
        total_usage = _extract_token_usage_raw(accumulated)
        state["metrics"]["total_tokens"] = (
            total_usage.get("input_tokens", 0) + total_usage.get("output_tokens", 0)
        )
        state["metrics"]["total_input_tokens"] = total_usage.get("input_tokens", 0)
        state["metrics"]["total_output_tokens"] = total_usage.get("output_tokens", 0)

    # Build per-node metrics for the report's token chart
    total_duration = _safe_attr(graph_result, "execution_time", 0)
    state["metrics"]["duration_seconds"] = total_duration / 1000 if total_duration > 1_000_000 else total_duration
    state["metrics"]["execution_order"] = state["execution_order"]
    state["metrics"]["nodes"] = {}
    for node_id, node_data in state["nodes"].items():
        token_usage = node_data.get("token_usage", {})
        state["metrics"]["nodes"][node_id] = {
            "input_tokens": token_usage.get("input_tokens", 0),
            "output_tokens": token_usage.get("output_tokens", 0),
            "duration_seconds": (node_data.get("execution_time", 0) / 1000
                                 if node_data.get("execution_time", 0) > 1_000_000
                                 else node_data.get("execution_time", 0)),
            "status": node_data.get("status", "unknown"),
            "execution_count": node_data.get("execution_count", 1),
        }

    return state


def deserialize_migration_state(data: dict) -> dict:
    """Restore migration state from a persisted dict.

    This is intentionally thin -- the dict format is the canonical
    representation.  The function validates required keys and returns
    a normalized copy.

    Args:
        data: Previously serialized state dict.

    Returns:
        Validated and normalized state dict.

    Raises:
        ValueError: If required keys are missing.
    """
    required_keys = ("migration_id", "status", "timestamp")
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Migration state missing required keys: {missing}")

    return {
        "migration_id": data["migration_id"],
        "status": data["status"],
        "timestamp": data["timestamp"],
        "nodes": data.get("nodes", {}),
        "execution_order": data.get("execution_order", []),
        "metrics": data.get("metrics", {}),
    }


# ---------------------------------------------------------------------------
# Input builders for graph nodes
# ---------------------------------------------------------------------------

def build_discovery_input(config: dict) -> str:
    """Build the initial prompt for the discovery node.

    Args:
        config: Migration configuration containing ``oracle_config``,
            ``pg_config``, and optional ``scope`` settings.

    Returns:
        A formatted prompt string for the discovery agent.
    """
    oracle = config.get("oracle_config", {})
    pg = config.get("pg_config", {})
    scope = config.get("scope", {})

    parts = [
        "Analyze the source Oracle database and produce a comprehensive discovery report.",
        "",
        "## Source Oracle Database",
        f"- Host: {oracle.get('host', 'N/A')}",
        f"- Schema: {oracle.get('schema', 'N/A')}",
        f"- SID/Service: {oracle.get('service', oracle.get('sid', 'N/A'))}",
        "",
        "## Target PostgreSQL Database",
        f"- Host: {pg.get('host', 'N/A')}",
        f"- Database: {pg.get('database', 'N/A')}",
        f"- Schema: {pg.get('target_schema', 'public')}",
    ]

    if scope:
        parts.extend([
            "",
            "## Scope",
            f"- Object types: {scope.get('object_types', 'ALL')}",
            f"- Include patterns: {scope.get('include', '*')}",
            f"- Exclude patterns: {scope.get('exclude', 'NONE')}",
        ])

    parts.extend([
        "",
        "## Required Outputs",
        "1. Object inventory (tables, views, indexes, sequences, procedures, packages, triggers)",
        "2. Dependency DAG between objects",
        "3. Complexity scoring per object (SIMPLE / MODERATE / COMPLEX)",
        "4. Oracle-specific patterns detected (CONNECT BY, MERGE, DECODE, etc.)",
        "5. Estimated conversion effort per object type",
    ])

    return "\n".join(parts)


def build_transform_input(discovery_report: dict, object_info: dict) -> str:
    """Build input prompt for the transform node from discovery results.

    Composes a detailed prompt that includes the object to convert, its
    dependencies, and relevant context from the discovery phase.

    Args:
        discovery_report: The full discovery report dict produced by the
            discovery node.
        object_info: A dict describing the specific object to transform,
            with keys like ``name``, ``type``, ``ddl``, ``complexity``.

    Returns:
        A formatted prompt string for the code migrator agent.
    """
    obj_name = object_info.get("name", "UNKNOWN")
    obj_type = object_info.get("type", "UNKNOWN")
    obj_ddl = object_info.get("ddl", "")
    complexity = object_info.get("complexity", "MODERATE")

    # Gather dependency context
    deps = object_info.get("dependencies", [])
    dep_context = ""
    if deps:
        dep_lines = [f"  - {d.get('name', '?')} ({d.get('type', '?')})" for d in deps]
        dep_context = "\n".join(dep_lines)

    # Gather Oracle patterns detected in this object
    patterns = object_info.get("oracle_patterns", [])
    pattern_context = ", ".join(patterns) if patterns else "None detected"

    # Schema context from discovery
    schema_name = discovery_report.get("schema", "UNKNOWN")
    total_objects = discovery_report.get("total_objects", "?")

    parts = [
        f"Convert the following Oracle {obj_type} to PostgreSQL.",
        "",
        f"## Object: {schema_name}.{obj_name}",
        f"- Type: {obj_type}",
        f"- Complexity: {complexity}",
        f"- Oracle patterns: {pattern_context}",
        "",
        "## Source DDL / SQL",
        "```sql",
        obj_ddl,
        "```",
    ]

    if dep_context:
        parts.extend([
            "",
            "## Dependencies (already converted)",
            dep_context,
        ])

    parts.extend([
        "",
        "## Conversion Rules",
        "1. Apply static rule mappings first (NVL->COALESCE, SYSDATE->CURRENT_TIMESTAMP, etc.)",
        "2. Convert Oracle-specific syntax to PostgreSQL equivalents",
        "3. Preserve functional equivalence -- output must produce identical results",
        "4. Add explicit type casts (::type) where PostgreSQL requires them",
        "5. Handle NULL behavior differences between Oracle and PostgreSQL",
        "",
        "## Output Format",
        "Return ONLY the converted PostgreSQL SQL/DDL, no explanations.",
    ])

    return "\n".join(parts)


def build_verify_input(
    original_sql: str,
    converted_sql: str,
    object_info: dict,
) -> str:
    """Build input prompt for the QA verification node.

    Args:
        original_sql: The original Oracle SQL/DDL.
        converted_sql: The converted PostgreSQL SQL/DDL.
        object_info: Metadata about the object being verified.

    Returns:
        A formatted prompt string for the QA verifier agent.
    """
    obj_name = object_info.get("name", "UNKNOWN")
    obj_type = object_info.get("type", "UNKNOWN")

    return "\n".join([
        f"Verify the conversion of Oracle {obj_type} '{obj_name}' to PostgreSQL.",
        "",
        "## Original Oracle SQL",
        "```sql",
        original_sql,
        "```",
        "",
        "## Converted PostgreSQL SQL",
        "```sql",
        converted_sql,
        "```",
        "",
        "## Verification Steps",
        "1. Syntax validation: Execute EXPLAIN on PostgreSQL to check syntax",
        "2. Semantic comparison: Compare Oracle and PostgreSQL execution results",
        "3. Edge cases: Test with NULL values, empty strings, boundary dates",
        "4. Performance check: Review EXPLAIN ANALYZE output for obvious issues",
        "",
        "## Output Format",
        "Return a JSON object with:",
        '- "status": "PASS" | "FAIL" | "WARNING"',
        '- "syntax_valid": true/false',
        '- "semantic_match": true/false',
        '- "issues": [list of found issues]',
        '- "suggestions": [list of improvement suggestions]',
    ])


def build_evaluate_input(verification_results: list[dict]) -> str:
    """Build input prompt for the evaluator node.

    Args:
        verification_results: List of verification result dicts from the
            QA verifier node.

    Returns:
        A formatted prompt for the evaluator agent.
    """
    total = len(verification_results)
    passed = sum(1 for v in verification_results if v.get("status") == "PASS")
    failed = sum(1 for v in verification_results if v.get("status") == "FAIL")
    warnings = sum(1 for v in verification_results if v.get("status") == "WARNING")

    failure_details = []
    for v in verification_results:
        if v.get("status") in ("FAIL", "WARNING"):
            failure_details.append(
                f"- {v.get('object_name', '?')}: {v.get('status')} -- "
                f"{'; '.join(v.get('issues', ['No details']))}"
            )

    parts = [
        "Evaluate the migration quality and provide a GO / NO_GO / CONDITIONAL verdict.",
        "",
        "## Summary Statistics",
        f"- Total objects verified: {total}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Warnings: {warnings}",
        f"- Pass rate: {(passed / total * 100) if total else 0:.1f}%",
    ]

    if failure_details:
        parts.extend([
            "",
            "## Failures and Warnings",
            *failure_details,
        ])

    parts.extend([
        "",
        "## 5-Dimension Scoring (score each 0-100)",
        "1. **Syntax Correctness**: All SQL parses without errors",
        "2. **Semantic Equivalence**: Results match Oracle execution",
        "3. **Performance Parity**: No significant performance regressions",
        "4. **Coverage Completeness**: All objects converted successfully",
        "5. **Edge Case Resilience**: NULL handling, boundary values correct",
        "",
        "## Verdict Criteria",
        "- **GO**: All dimensions >= 90, pass rate >= 95%",
        "- **CONDITIONAL**: All dimensions >= 70, pass rate >= 80%",
        "- **NO_GO**: Any dimension < 70 or pass rate < 80%",
        "",
        "## Output Format",
        "Return a JSON object with:",
        '- "verdict": "GO" | "NO_GO" | "CONDITIONAL"',
        '- "scores": {"syntax": N, "semantic": N, "performance": N, "coverage": N, "edge_cases": N}',
        '- "reasoning": "explanation"',
        '- "critical_findings": [{"id": "CF-001", "severity": "HIGH|MEDIUM|LOW", "title": "...", "description": "...", "mitigation": "..."}]',
        '- "remediation_targets": [list of objects needing fixes — include even for GO if HIGH severity findings exist]',
    ])

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Verdict parsing helpers
# ---------------------------------------------------------------------------

def parse_verdict(evaluate_result: Any) -> Verdict:
    """Parse the verdict from an evaluator node result.

    Attempts multiple strategies to extract the verdict string:
    1. If the result is a dict with a ``verdict`` key, use it directly.
    2. Search for GO/NO_GO/CONDITIONAL in the string representation.
    3. Default to NO_GO if parsing fails.

    Args:
        evaluate_result: The raw result from the evaluator node.

    Returns:
        A ``Verdict`` enum value.
    """
    if evaluate_result is None:
        return Verdict.NO_GO

    # Strategy 1: dict with 'verdict' key
    if isinstance(evaluate_result, dict):
        raw = evaluate_result.get("verdict", "")
        return _str_to_verdict(raw)

    # Strategy 2: try to parse JSON from string
    result_str = str(evaluate_result)
    try:
        parsed = json.loads(result_str)
        if isinstance(parsed, dict) and "verdict" in parsed:
            return _str_to_verdict(parsed["verdict"])
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to parse verdict JSON, falling back to keyword search: %s", exc)

    # Strategy 3: search for verdict keywords in text
    upper = result_str.upper()
    # Check NO_GO first since "GO" is a substring of "NO_GO"
    if "NO_GO" in upper:
        return Verdict.NO_GO
    if "CONDITIONAL" in upper:
        return Verdict.CONDITIONAL
    if '"GO"' in upper or "'GO'" in upper or "VERDICT: GO" in upper or ": GO" in upper:
        return Verdict.GO
    # Bare "GO" only if it appears as a standalone word
    if " GO " in f" {upper} ":
        return Verdict.GO

    logger.warning("Could not parse verdict from evaluate result, defaulting to NO_GO")
    return Verdict.NO_GO


def compute_state_hash(state_dict: dict) -> str:
    """Compute a deterministic hash of a migration state for change detection.

    Args:
        state_dict: The state dict to hash.

    Returns:
        A hex SHA-256 digest string.
    """
    canonical = json.dumps(state_dict, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# DynamoDB checkpoint persistence
# ---------------------------------------------------------------------------

def _get_dynamodb_table():
    """Get DynamoDB table resource for checkpointing."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(CHECKPOINT_TABLE)


def _convert_floats(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj


def _convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values back to float after DynamoDB read."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    return obj


def save_checkpoint(
    migration_id: str,
    node_name: str,
    invocation_state: dict,
    *,
    phase: str = "schema",
    status: str = "in_progress",
) -> None:
    """Save a checkpoint after a node completes.

    Writes the current invocation_state and completed node info to DynamoDB
    so the pipeline can be resumed from this point.

    Args:
        migration_id: Unique migration run identifier.
        node_name: Name of the node that just completed.
        invocation_state: The shared invocation state dict.
        phase: Pipeline phase ("schema" or "data").
        status: Checkpoint status ("in_progress", "completed", "failed").
    """
    table = _get_dynamodb_table()
    now = time.time()

    # Build execution history from invocation state
    completed_nodes = invocation_state.get("_completed_nodes", [])
    if node_name not in completed_nodes:
        completed_nodes.append(node_name)
        invocation_state["_completed_nodes"] = completed_nodes

    # Serialize invocation state (remove non-serializable items)
    safe_state = {}
    for k, v in invocation_state.items():
        try:
            json.dumps(v, default=str)
            safe_state[k] = v
        except (TypeError, ValueError):
            safe_state[k] = str(v)

    item = _convert_floats({
        "migration_id": migration_id,
        "checkpoint_timestamp": Decimal(str(int(now * 1000))),
        "node_name": node_name,
        "phase": phase,
        "status": status,
        "completed_nodes": completed_nodes,
        "invocation_state": json.dumps(safe_state, default=str),
        "last_updated": Decimal(str(int(now * 1000))),
        "ttl": int(now) + 86400 * 7,  # 7 day TTL
    })

    try:
        table.put_item(Item=item)
        logger.info(
            "[%s] Checkpoint saved: node=%s, phase=%s, completed=%s",
            migration_id, node_name, phase, completed_nodes,
        )
    except ClientError as e:
        logger.error("[%s] Failed to save checkpoint: %s", migration_id, e)


def load_latest_checkpoint(migration_id: str) -> dict | None:
    """Load the most recent checkpoint for a migration.

    Queries DynamoDB for all checkpoints with the given migration_id
    and returns the one with the latest timestamp.

    Args:
        migration_id: The migration run identifier to resume.

    Returns:
        Dict with checkpoint data, or None if no checkpoint found.
        Keys: migration_id, node_name, phase, status, completed_nodes,
              invocation_state (parsed dict).
    """
    table = _get_dynamodb_table()

    try:
        response = table.query(
            KeyConditionExpression="migration_id = :mid",
            ExpressionAttributeValues={":mid": migration_id},
            ScanIndexForward=False,  # Latest first
            Limit=1,
        )

        items = response.get("Items", [])
        if not items:
            logger.warning("[%s] No checkpoint found", migration_id)
            return None

        item = _convert_decimals(items[0])

        # Parse invocation_state back from JSON string
        raw_state = item.get("invocation_state", "{}")
        if isinstance(raw_state, str):
            item["invocation_state"] = json.loads(raw_state)

        logger.info(
            "[%s] Checkpoint loaded: node=%s, phase=%s, completed=%s",
            migration_id,
            item.get("node_name"),
            item.get("phase"),
            item.get("completed_nodes", []),
        )
        return item

    except ClientError as e:
        logger.error("[%s] Failed to load checkpoint: %s", migration_id, e)
        return None


def get_resume_entry_point(checkpoint: dict) -> str | None:
    """Determine which node to resume from based on checkpoint data.

    Returns the name of the NEXT node to execute (the one after the
    last completed node).

    Args:
        checkpoint: Checkpoint dict from load_latest_checkpoint().

    Returns:
        Node name to resume from, or None if pipeline was completed.
    """
    SCHEMA_NODE_ORDER = ["discover", "design", "transform", "verify", "evaluate", "remediate", "report"]
    DATA_NODE_ORDER = ["data_migrate", "data_verify"]

    phase = checkpoint.get("phase", "schema")
    last_node = checkpoint.get("node_name", "")
    status = checkpoint.get("status", "")

    if status == "completed":
        return None

    node_order = SCHEMA_NODE_ORDER if phase == "schema" else DATA_NODE_ORDER

    if last_node in node_order:
        idx = node_order.index(last_node)
        if idx + 1 < len(node_order):
            next_node = node_order[idx + 1]
            logger.info("[%s] Resume entry point: %s (after %s)",
                       checkpoint.get("migration_id"), next_node, last_node)
            return next_node

    # If last node was evaluate and verdict was NO_GO, resume at remediate
    if last_node == "evaluate":
        completed = checkpoint.get("completed_nodes", [])
        loop_count = completed.count("remediate")
        if loop_count < 3:
            return "remediate"
        return "report"

    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _str_to_verdict(raw: str) -> Verdict:
    """Convert a raw string to a Verdict enum by keyword matching."""
    cleaned = str(raw).strip().upper()
    try:
        return Verdict(cleaned)
    except ValueError:
        if "NO_GO" in cleaned or "NOGO" in cleaned:
            return Verdict.NO_GO
        if "CONDITIONAL" in cleaned:
            return Verdict.CONDITIONAL
        if "GO" in cleaned:
            return Verdict.GO
        return Verdict.NO_GO


def _safe_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute or dict key from an object."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, appending '...' if truncated."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _extract_token_usage(node_result: Any) -> dict:
    """Extract token usage from a node result object.

    Strands SDK NodeResult stores tokens in ``accumulated_usage``
    as a ``Usage`` dataclass with camelCase fields:
    ``inputTokens``, ``outputTokens``, ``totalTokens``.
    """
    # Try accumulated_usage first (Strands SDK NodeResult / GraphResult)
    usage = _safe_attr(node_result, "accumulated_usage", None)
    if usage is None:
        usage = _safe_attr(node_result, "usage", None)
    if usage is None:
        usage = _safe_attr(node_result, "token_usage", None)
    return _extract_token_usage_raw(usage)


def _extract_token_usage_raw(usage: Any) -> dict:
    """Extract token counts from a usage object or dict.

    Handles both camelCase (Strands SDK ``Usage``) and snake_case
    (plain dict) field names.
    """
    if usage is None:
        return {}
    if isinstance(usage, dict):
        inp = usage.get("input_tokens", 0) or usage.get("inputTokens", 0)
        out = usage.get("output_tokens", 0) or usage.get("outputTokens", 0)
        return {"input_tokens": inp, "output_tokens": out}
    # Strands Usage dataclass uses camelCase: inputTokens, outputTokens
    inp = getattr(usage, "inputTokens", 0) or getattr(usage, "input_tokens", 0)
    out = getattr(usage, "outputTokens", 0) or getattr(usage, "output_tokens", 0)
    return {"input_tokens": inp, "output_tokens": out}
