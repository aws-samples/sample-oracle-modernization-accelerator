"""Main OMA migration Graph pipeline.

Orchestrates the end-to-end Oracle-to-PostgreSQL migration through a
deterministic DAG with conditional edges and a self-healing remediation loop:

    Discover -> Design -> Transform -> Verify -> Evaluate --[GO]--> DataMigrate -> DataVerify -> Report
                                        ^                    |
                                        |               [NO_GO/CONDITIONAL]
                                        |                    |
                                        +--- Remediate <-----+

The pipeline is built on top of **Strands SDK Graph** (``strands.multiagent.GraphBuilder``).
Each node wraps a specialized Strands ``Agent`` with its own model, tools, and
system prompt.

Usage::

    from common.orchestrator.pipeline import (
        build_migration_pipeline, build_app_migration_pipeline,
        run_migration, run_app_migration,
    )

    agents = {
        "discovery": discovery_agent,
        "schema_architect": schema_architect_agent,
        "code_migrator": code_migrator_agent,
        "qa_verifier": qa_verifier_agent,
        "evaluator": evaluator_agent,
        "remediation": remediation_agent,
        "report": report_agent,
    }

    graph = build_migration_pipeline(agents)
    result = run_migration(graph, config)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from strands import Agent
from strands.multiagent import GraphBuilder

from common.orchestrator.state import (
    MigrationPhase,
    Verdict,
    build_discovery_input,
    load_latest_checkpoint,
    get_resume_entry_point,
    parse_verdict,
    save_checkpoint,
    serialize_migration_state,
)
from common.orchestrator.telemetry import init_telemetry, record_pipeline_status
from common.orchestrator.design_gate import inject_triage_into_agent
from common.orchestrator.cost_tracker import CostTracker
from common.orchestrator.hooks import MigrationHookProvider, create_ws_notify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline configuration defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_NODE_EXECUTIONS = 20
DEFAULT_EXECUTION_TIMEOUT = 7200  # 2 hours total
DEFAULT_NODE_TIMEOUT = 1800  # 30 minutes per node
MAX_REMEDIATION_LOOPS = 3  # Safety limit for remediation cycles


# ---------------------------------------------------------------------------
# Condition functions for conditional edges
# ---------------------------------------------------------------------------

def _get_remediation_count(state: Any) -> int:
    """Get the current remediation loop count from state.

    Uses multiple strategies to count remediation loops:
    1. invocation_state._remediation_loop_count (if manually set)
    2. Count GraphNode objects with node_id=="remediate" in execution_order
    3. evaluate node execution_count - 1 (each re-evaluation = one loop)
    """
    # Try invocation_state first
    invocation_state = _safe_attr(state, "invocation_state", {})
    if isinstance(invocation_state, dict):
        count = invocation_state.get("_remediation_loop_count", 0)
        if count > 0:
            return count

    # Count 'remediate' in execution_order (GraphNode objects, not strings)
    execution_order = _safe_attr(state, "execution_order", [])
    if isinstance(execution_order, list) and execution_order:
        rem_count = 0
        for node in execution_order:
            # GraphNode objects have node_id attribute; also handle strings
            node_id = _safe_attr(node, "node_id", None) or str(node)
            if node_id == "remediate":
                rem_count += 1
        if rem_count > 0:
            return rem_count

    # Fallback: count evaluate executions (each after first = one loop)
    results = _safe_attr(state, "results", {})
    if isinstance(results, dict):
        eval_result = results.get("evaluate")
        if eval_result is not None:
            exec_count = _safe_attr(eval_result, "execution_count", 1)
            return max(0, exec_count - 1)

    return 0


def _has_high_severity_findings(evaluate_result: Any) -> bool:
    """Check if evaluate result contains HIGH severity critical findings.

    Even when verdict is GO, HIGH severity issues (dead code, missing PKs,
    security risks) should trigger one remediation pass to auto-fix them.

    Searches ALL text content from the evaluator agent, not just the last
    message, because critical_findings JSON is typically in an earlier
    message while the last message may be a summary.
    """
    if evaluate_result is None:
        return False

    # Build a comprehensive text representation from all available sources.
    # AgentResult.__str__() only returns the LAST message text, but
    # critical_findings is often in an earlier message.
    text_parts = []

    # 1. Direct dict
    if isinstance(evaluate_result, dict):
        findings = evaluate_result.get("critical_findings", [])
        for f in findings:
            if isinstance(f, dict) and f.get("severity", "").upper() == "HIGH":
                logger.info("HIGH severity finding (dict): %s", f.get("title", ""))
                return True
        # Also check string representation
        text_parts.append(json.dumps(evaluate_result, default=str))

    # 2. AgentResult — get ALL messages from the agent conversation
    if hasattr(evaluate_result, "message"):
        # Last message
        msg = evaluate_result.message
        if isinstance(msg, dict):
            for item in msg.get("content", []):
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])

    # 3. NodeResult wrapper — unwrap to AgentResult
    if hasattr(evaluate_result, "result"):
        inner = evaluate_result.result
        if hasattr(inner, "message"):
            msg = inner.message
            if isinstance(msg, dict):
                for item in msg.get("content", []):
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
        # Also try get_agent_results() for nested results
        if hasattr(evaluate_result, "get_agent_results"):
            for ar in evaluate_result.get_agent_results():
                text_parts.append(str(ar))

    # 4. Plain str() fallback
    if not text_parts:
        text_parts.append(str(evaluate_result))

    # Search all collected text for HIGH severity
    full_text = "\n".join(text_parts)

    # Quick keyword check first (covers all formats)
    if '"severity"' in full_text and '"HIGH"' in full_text:
        logger.info("HIGH severity finding detected via keyword search in evaluate result (%d chars)", len(full_text))
        return True

    # Also check for severity: HIGH without quotes (markdown format)
    if "severity" in full_text.lower() and "HIGH" in full_text:
        import re
        if re.search(r'severity["\s:]*HIGH', full_text, re.IGNORECASE):
            logger.info("HIGH severity finding detected via regex in evaluate result")
            return True

    logger.info("No HIGH severity findings detected in evaluate result (%d chars searched)", len(full_text))
    return False


def _check_high_severity_in_state(state: Any) -> bool:
    """Search graph state's evaluate node messages for HIGH severity findings.

    The graph state contains node objects with agent executors that hold
    the full conversation history. This searches through all messages
    from the evaluate agent, not just the final result.
    """
    try:
        # Strands Graph state has 'nodes' dict with GraphNode objects
        nodes = _safe_attr(state, "nodes", {})
        if isinstance(nodes, dict):
            eval_node = nodes.get("evaluate")
            if eval_node is not None:
                # GraphNode.executor is the Agent — check its messages
                executor = _safe_attr(eval_node, "executor", None)
                if executor and hasattr(executor, "messages"):
                    for msg in executor.messages:
                        if isinstance(msg, dict):
                            for item in msg.get("content", []):
                                if isinstance(item, dict) and "text" in item:
                                    text = item["text"]
                                    if '"severity"' in text and '"HIGH"' in text:
                                        logger.info(
                                            "HIGH severity found in evaluate agent messages"
                                        )
                                        return True

        # Also try execution_order for GraphNode objects
        execution_order = _safe_attr(state, "execution_order", [])
        for node in execution_order:
            node_id = _safe_attr(node, "node_id", "")
            if node_id == "evaluate":
                result = _safe_attr(node, "result", None)
                if result is not None:
                    result_str = str(result)
                    if '"severity"' in result_str and '"HIGH"' in result_str:
                        logger.info(
                            "HIGH severity found in evaluate node result from execution_order"
                        )
                        return True
    except Exception as e:
        logger.warning("Error checking HIGH severity in state: %s", e)

    return False


def _is_go_or_exhausted(state: Any) -> bool:
    """Check whether to proceed to report (skip remediation).

    Returns True if:
    - The evaluator returned GO verdict with NO high-severity findings, OR
    - GO verdict with high-severity findings but already remediated once, OR
    - The remediation loop limit has been reached (force proceed)

    Used as condition on ``evaluate -> report`` edge.
    """
    evaluate_result = _extract_evaluate_result(state)
    verdict = parse_verdict(evaluate_result)
    loop_count = _get_remediation_count(state)

    logger.info("Evaluate verdict: %s (remediation loop %d/%d)",
                verdict.value, loop_count, MAX_REMEDIATION_LOOPS)

    if loop_count >= MAX_REMEDIATION_LOOPS:
        logger.warning(
            "Remediation loop limit reached (%d/%d). Forcing proceed.",
            loop_count, MAX_REMEDIATION_LOOPS,
        )
        return True

    if verdict == Verdict.GO:
        # GO but has HIGH severity findings → run remediation once
        if loop_count == 0:
            # Try multiple sources for HIGH severity detection
            has_high = _has_high_severity_findings(evaluate_result)

            # Also check the full evaluate text from state if available
            if not has_high:
                has_high = _check_high_severity_in_state(state)

            if has_high:
                logger.info(
                    "GO verdict but HIGH severity findings detected — "
                    "running remediation once to auto-fix before report"
                )
                return False  # → go to remediate
        return True

    return False


def _should_remediate(state: Any) -> bool:
    """Check whether to enter remediation loop.

    Returns True if:
    - The verdict is NOT GO, AND the remediation loop limit NOT reached, OR
    - The verdict is GO but HIGH severity findings exist and not yet remediated

    Used as condition on ``evaluate -> remediate`` edge.
    """
    return not _is_go_or_exhausted(state)


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------

def build_migration_pipeline(
    agents: dict[str, Agent],
    *,
    oracle_schema: str = "AMZN",
    max_node_executions: int = DEFAULT_MAX_NODE_EXECUTIONS,
    execution_timeout: int = DEFAULT_EXECUTION_TIMEOUT,
    node_timeout: int = DEFAULT_NODE_TIMEOUT,
) -> Any:
    """Build the main OMA migration Graph pipeline.

    Constructs a Strands Graph with seven nodes connected by sequential
    and conditional edges. The evaluate node branches to either ``report``
    (on GO verdict) or ``remediate`` (on NO_GO/CONDITIONAL), with
    remediate looping back to verify for re-evaluation.

    Pipeline::

        discover -> design -> transform -> verify -> evaluate
                                            ^           |
                                            |      [GO] | [NO_GO/CONDITIONAL]
                                            |           v
                                        remediate    data_migrate -> data_verify -> report
                                            |
                                            v
                                          verify (loop back)

    Args:
        agents: Dict mapping role names to Strands Agent instances.
            Required keys: ``discovery``, ``schema_architect``,
            ``code_migrator``, ``qa_verifier``, ``evaluator``,
            ``remediation``, ``data_migrator``, ``data_verifier``,
            ``report``.
        max_node_executions: Maximum times any single node can execute.
            Prevents infinite loops. Defaults to 10.
        execution_timeout: Total pipeline timeout in seconds.
            Defaults to 3600 (1 hour).
        node_timeout: Per-node timeout in seconds. Defaults to 600.

    Returns:
        A compiled Strands Graph object.

    Raises:
        KeyError: If a required agent is missing from the dict.
        ValueError: If any agent value is None.
    """
    # Validate required agents
    required_agents = [
        "discovery",
        "schema_architect",
        "code_migrator",
        "qa_verifier",
        "evaluator",
        "remediation",
        "report",
    ]
    _validate_agents(agents, required_agents)

    builder = GraphBuilder()

    # ------------------------------------------------------------------
    # Add nodes (schema migration only; data pipeline is separate)
    # ------------------------------------------------------------------
    builder.add_node(agents["discovery"], "discover")

    # Inject verified triage into Schema Architect's system prompt.
    # This ensures the agent has ground-truth from PG before starting
    # any conversion — not just relying on Discovery agent's text output.
    inject_triage_into_agent(agents["schema_architect"], oracle_schema)
    builder.add_node(agents["schema_architect"], "design")

    builder.add_node(agents["code_migrator"], "transform")
    builder.add_node(agents["qa_verifier"], "verify")
    builder.add_node(agents["evaluator"], "evaluate")
    builder.add_node(agents["remediation"], "remediate")
    builder.add_node(agents["report"], "report")

    # ------------------------------------------------------------------
    # Sequential edges (main pipeline flow)
    # ------------------------------------------------------------------
    builder.add_edge("discover", "design")
    builder.add_edge("design", "transform")
    builder.add_edge("transform", "verify")
    builder.add_edge("verify", "evaluate")

    # ------------------------------------------------------------------
    # Conditional edges from evaluate
    # ------------------------------------------------------------------
    # GO or exhausted remediation -> report (schema migration complete)
    builder.add_edge("evaluate", "report", condition=_is_go_or_exhausted)

    # NO_GO / CONDITIONAL (with remaining attempts) -> remediate
    builder.add_edge("evaluate", "remediate", condition=_should_remediate)

    # ------------------------------------------------------------------
    # Remediation loop: remediate -> verify -> evaluate -> ...
    # ------------------------------------------------------------------
    builder.add_edge("remediate", "verify")

    # ------------------------------------------------------------------
    # Safety limits
    # ------------------------------------------------------------------
    builder.set_entry_point("discover")
    builder.set_max_node_executions(max_node_executions)
    builder.set_execution_timeout(execution_timeout)
    builder.set_node_timeout(node_timeout)

    # Reset state on revisit to avoid context bloat
    builder.reset_on_revisit("remediate")
    builder.reset_on_revisit("report")

    graph = builder.build()

    logger.info(
        "Schema pipeline built: nodes=%d, max_executions=%d, "
        "timeout=%ds, node_timeout=%ds",
        len(required_agents),
        max_node_executions,
        execution_timeout,
        node_timeout,
    )

    return graph


def build_data_pipeline(
    agents: dict[str, Agent],
    *,
    execution_timeout: int = 3600,
    node_timeout: int = 1800,
) -> Any:
    """Build a separate data migration + verification pipeline.

    This pipeline runs AFTER the schema migration pipeline completes.
    It has its own clean context to avoid token overflow from
    the schema migration conversation.

    Pipeline::

        data_migrate -> data_verify

    Args:
        agents: Dict with ``data_migrator`` and ``data_verifier`` agents.
        execution_timeout: Total timeout (default 1 hour).
        node_timeout: Per-node timeout (default 30 min).

    Returns:
        A compiled Strands Graph object.
    """
    required = ["data_migrator", "data_verifier"]
    _validate_agents(agents, required)

    builder = GraphBuilder()
    builder.add_node(agents["data_migrator"], "data_migrate")
    builder.add_node(agents["data_verifier"], "data_verify")

    builder.add_edge("data_migrate", "data_verify")

    builder.set_entry_point("data_migrate")
    builder.set_max_node_executions(5)
    builder.set_execution_timeout(execution_timeout)
    builder.set_node_timeout(node_timeout)

    graph = builder.build()
    logger.info("Data pipeline built: 2 nodes, timeout=%ds", execution_timeout)
    return graph


def build_app_qa_pipeline(
    agents: dict[str, Agent],
    *,
    max_node_executions: int = DEFAULT_MAX_NODE_EXECUTIONS,
    execution_timeout: int = DEFAULT_EXECUTION_TIMEOUT,
    node_timeout: int = DEFAULT_NODE_TIMEOUT,
) -> Any:
    """Build the QA pipeline for app migration (post-transform).

    Used after per-file transform completes. Runs verification,
    evaluation, optional remediation loop, and final report.

    Pipeline::

        verify -> evaluate --[GO]--> report
                    ^           |
                    |      [NO_GO/CONDITIONAL]
                    |           |
                  remediate <---+

    Args:
        agents: Dict with ``qa_verifier``, ``evaluator``,
            ``remediation``, ``report``.
        max_node_executions: Max node executions.
        execution_timeout: Total timeout in seconds.
        node_timeout: Per-node timeout in seconds.

    Returns:
        A compiled Strands Graph object.
    """
    required_agents = ["qa_verifier", "evaluator", "remediation", "report"]
    _validate_agents(agents, required_agents)

    builder = GraphBuilder()

    builder.add_node(agents["qa_verifier"], "verify")
    builder.add_node(agents["evaluator"], "evaluate")
    builder.add_node(agents["remediation"], "remediate")
    builder.add_node(agents["report"], "report")

    builder.add_edge("verify", "evaluate")
    builder.add_edge("evaluate", "report", condition=_is_go_or_exhausted)
    builder.add_edge("evaluate", "remediate", condition=_should_remediate)
    builder.add_edge("remediate", "verify")

    builder.set_entry_point("verify")
    builder.set_max_node_executions(max_node_executions)
    builder.set_execution_timeout(execution_timeout)
    builder.set_node_timeout(node_timeout)

    builder.reset_on_revisit("remediate")
    builder.reset_on_revisit("report")

    graph = builder.build()
    logger.info("App QA pipeline built: 4 nodes (verify→evaluate→remediate→report)")
    return graph


def _prescan_mappers(mapper_dir: str) -> list[dict]:
    """Pre-scan mapper directory and return file inventory."""
    from pathlib import Path

    mappers = []
    for xml_file in sorted(Path(mapper_dir).rglob("*.xml")):
        try:
            content = xml_file.read_text(encoding="utf-8")
            if "<mapper" not in content:
                continue
            sql_count = sum(
                content.count(f"<{tag} ")
                for tag in ("select", "insert", "update", "delete")
            )
            rel_path = str(xml_file.relative_to(mapper_dir))
            mappers.append({
                "file": xml_file.name,
                "path": str(xml_file),
                "rel_path": rel_path,
                "sql_count": sql_count,
            })
        except Exception:
            continue

    return mappers


def _transform_single_mapper(
    mapper: dict,
    output_dir: str,
    create_agent_fn: Any,
    migration_id: str,
    idx: int,
    total: int,
) -> dict:
    """Transform a single mapper file using a fresh Code Migrator agent.

    Creates a new agent instance per file to avoid token overflow.
    Each agent gets a focused prompt for just one file.

    Returns:
        Dict with transform result for this file.
    """
    source_path = mapper["path"]
    rel_path = mapper["rel_path"]
    output_path = f"{output_dir}/{rel_path}"
    file_name = mapper["file"]
    sql_count = mapper["sql_count"]

    logger.info(
        "[%s] Transform [%d/%d]: %s (%d SQLs)",
        migration_id, idx + 1, total, file_name, sql_count,
    )

    # Create fresh agent for this file
    agent = create_agent_fn()

    prompt = (
        f"## Convert ONE MyBatis Mapper: {file_name} (File {idx+1}/{total})\n\n"
        f"### Source\n`{source_path}`\n\n"
        f"### Output\n`{output_path}`\n\n"
        f"### Instructions\n"
        f"1. `mybatis_extract_sqls('{source_path}')` — extract all {sql_count} Oracle SQLs\n"
        f"2. Convert EACH SQL individually using 4-phase methodology:\n"
        f"   - Phase 1: Structural analysis\n"
        f"   - Phase 2: Syntax standardization\n"
        f"   - Phase 3: PG transformation\n"
        f"   - Phase 4: Self-audit\n"
        f"3. `mybatis_merge_sqls('{source_path}', converted_sqls_json, '{output_path}')` — write output\n"
        f"4. `mybatis_validate_xml('{output_path}')` — validate the output\n\n"
        f"### Key Oracle→PG Conversions\n"
        f"- NVL → COALESCE | SYSDATE → CURRENT_TIMESTAMP\n"
        f"- ROWNUM → ROW_NUMBER() OVER() or LIMIT\n"
        f"- (+) outer join → LEFT/RIGHT JOIN | DECODE → CASE WHEN\n"
        f"- ADD_MONTHS → + INTERVAL | MONTHS_BETWEEN → EXTRACT(EPOCH FROM age())/2592000\n"
        f"- TRUNC(date) → DATE_TRUNC | MEDIAN → PERCENTILE_CONT(0.5)\n"
        f"- TO_CHAR(date,'D') → EXTRACT(DOW FROM date)\n"
        f"- EXTRACT(...) returning float → add ::INTEGER cast\n\n"
        f"Report: converted SQL count, any issues found.\n"
    )

    start = time.time()
    try:
        result = agent(prompt)
        elapsed = time.time() - start

        # Extract text from result
        result_text = ""
        if hasattr(result, "message") and result.message:
            msg = result.message
            if isinstance(msg, dict):
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        result_text += block.get("text", "")
            elif hasattr(msg, "content"):
                for block in msg.content:
                    if hasattr(block, "text"):
                        result_text += block.text

        logger.info(
            "[%s] Transform [%d/%d]: %s done in %.1fs",
            migration_id, idx + 1, total, file_name, elapsed,
        )

        return {
            "file": file_name,
            "rel_path": rel_path,
            "status": "SUCCESS",
            "sql_count": sql_count,
            "elapsed": round(elapsed, 1),
            "output_path": output_path,
            "summary": result_text[:500] if result_text else "(no text output)",
        }

    except Exception as exc:
        elapsed = time.time() - start
        logger.error(
            "[%s] Transform [%d/%d]: %s FAILED: %s",
            migration_id, idx + 1, total, file_name, exc,
        )
        return {
            "file": file_name,
            "rel_path": rel_path,
            "status": "FAILED",
            "sql_count": sql_count,
            "elapsed": round(elapsed, 1),
            "error": str(exc),
        }


def run_app_migration(
    mapper_dir: str,
    output_dir: str,
    *,
    create_agent_fn: Any,
    qa_agents: dict[str, Agent],
    migration_id: str | None = None,
    execution_timeout: int = DEFAULT_EXECUTION_TIMEOUT,
    node_timeout: int = DEFAULT_NODE_TIMEOUT,
    progress_callback: Any | None = None,
) -> dict:
    """Execute the full app migration: per-file transform + QA pipeline.

    Architecture (same pattern as Phase 1 → Phase 2):
    - **Transform phase**: For-loop, one fresh Code Migrator agent per
      mapper file. Each agent gets clean context, no token overflow.
    - **QA phase**: Graph pipeline (verify → evaluate → [remediate] → report)
      with fresh agents receiving the aggregate transform results.

    Args:
        mapper_dir: Path to directory containing Oracle MyBatis XML mappers.
        output_dir: Path for converted PostgreSQL mapper output.
        create_agent_fn: Callable that returns a fresh Code Migrator agent.
            Called once per mapper file for token isolation.
        qa_agents: Dict with ``qa_verifier``, ``evaluator``,
            ``remediation``, ``report`` agents.
        migration_id: Unique run identifier.
        execution_timeout: Total QA pipeline timeout.
        node_timeout: Per-node timeout for QA pipeline.

    Returns:
        Serialized migration state dict with execution results.
    """
    if migration_id is None:
        migration_id = f"app-{int(time.time())}"

    init_telemetry()
    start_time = time.time()

    # ── Phase A: Pre-scan ──
    mappers = _prescan_mappers(mapper_dir)
    total_sqls = sum(m["sql_count"] for m in mappers)

    if not mappers:
        logger.error("[%s] No mapper files found in %s", migration_id, mapper_dir)
        return {
            "migration_id": migration_id,
            "type": "app_migration",
            "status": "FAILED",
            "error": f"No mapper files found in {mapper_dir}",
        }

    logger.info(
        "[%s] Pre-scan: %d mapper files, %d SQL statements",
        migration_id, len(mappers), total_sqls,
    )

    # ── Phase B: Per-file transform (fresh agent per file) ──
    logger.info("[%s] === TRANSFORM PHASE: %d files ===", migration_id, len(mappers))
    transform_results = []

    for idx, mapper in enumerate(mappers):
        # Report progress before starting each file
        if progress_callback:
            completed = sum(1 for r in transform_results if r["status"] == "SUCCESS")
            failed_so_far = sum(1 for r in transform_results if r["status"] == "FAILED")
            progress_callback({
                "phase": "transform",
                "progress": idx / len(mappers),
                "total_files": len(mappers),
                "succeeded_files": completed,
                "failed_files": failed_so_far,
                "total_sqls": total_sqls,
                "elapsed_seconds": round(time.time() - start_time, 1),
                "message": f"Transforming {mapper['file']} ({idx+1}/{len(mappers)})",
            })

        result = _transform_single_mapper(
            mapper, output_dir, create_agent_fn,
            migration_id, idx, len(mappers),
        )
        transform_results.append(result)

    succeeded = sum(1 for r in transform_results if r["status"] == "SUCCESS")
    failed = sum(1 for r in transform_results if r["status"] == "FAILED")
    transform_elapsed = time.time() - start_time

    logger.info(
        "[%s] Transform phase done: %d/%d succeeded, %d failed (%.1fs)",
        migration_id, succeeded, len(mappers), failed, transform_elapsed,
    )

    # Build summary for QA pipeline
    transform_summary_rows = "\n".join(
        f"| {i+1} | {r['file']} | {r['sql_count']} | {r['status']} | {r['elapsed']}s |"
        for i, r in enumerate(transform_results)
    )
    transform_summary = (
        f"## Transform Phase Results\n\n"
        f"| # | Mapper | SQLs | Status | Time |\n"
        f"|---|--------|------|--------|------|\n"
        f"{transform_summary_rows}\n\n"
        f"**Total**: {succeeded}/{len(mappers)} succeeded, {failed} failed, "
        f"{total_sqls} SQLs, {transform_elapsed:.1f}s\n\n"
        f"### Output Directory\n`{output_dir}`\n\n"
        f"### Source Directory\n`{mapper_dir}`\n\n"
    )

    # Report transform complete
    if progress_callback:
        progress_callback({
            "phase": "qa",
            "progress": 0.8,
            "total_files": len(mappers),
            "succeeded_files": succeeded,
            "failed_files": failed,
            "total_sqls": total_sqls,
            "elapsed_seconds": round(transform_elapsed, 1),
            "message": f"Transform complete ({succeeded}/{len(mappers)}). Starting QA verification...",
        })

    # ── Phase C: QA pipeline (verify → evaluate → remediate → report) ──
    logger.info("[%s] === QA PHASE ===", migration_id)

    qa_graph = build_app_qa_pipeline(
        qa_agents,
        execution_timeout=execution_timeout,
        node_timeout=node_timeout,
    )

    qa_input = (
        f"## App Migration QA: Verify {succeeded} converted MyBatis mapper files\n\n"
        f"{transform_summary}"
        f"### Verification Instructions\n"
        f"1. For each converted file in `{output_dir}`, validate:\n"
        f"   - XML structure: `mybatis_validate_xml(path)`\n"
        f"   - SQL syntax: `pg_syntax_check(sql)` for each SQL\n"
        f"   - Oracle→PG equivalence: check key conversions were applied\n"
        f"2. Report per-file and per-SQL verification results\n"
        f"3. Flag any remaining Oracle constructs (NVL, SYSDATE, ROWNUM, (+), DECODE)\n"
    )

    invocation_state = {
        "migration_id": migration_id,
        "mapper_dir": mapper_dir,
        "output_dir": output_dir,
        "total_mapper_count": len(mappers),
        "total_sql_count": total_sqls,
        "transform_results": {r["file"]: r for r in transform_results},
        "verification_results": {},
        "remediation_history": [],
        "_remediation_loop_count": 0,
        "_phase": "app_migration_qa",
        "_start_time": start_time,
        "_completed_nodes": ["transform"],
    }

    try:
        qa_result = qa_graph(
            qa_input,
            invocation_state=invocation_state,
        )

        serialized = serialize_migration_state(qa_result)
        serialized["migration_id"] = migration_id
        serialized["type"] = "app_migration"
        serialized["transform_phase"] = {
            "total_files": len(mappers),
            "succeeded": succeeded,
            "failed": failed,
            "total_sqls": total_sqls,
            "elapsed": round(transform_elapsed, 1),
            "files": transform_results,
        }

        # Prepend transform to execution order
        if "execution_order" in serialized:
            serialized["execution_order"] = ["transform"] + serialized["execution_order"]

        duration = time.time() - start_time
        serialized["total_duration_seconds"] = round(duration, 1)

        logger.info(
            "[%s] App migration completed: status=%s, duration=%.1fs",
            migration_id, serialized.get("status", "unknown"), duration,
        )

        save_checkpoint(
            migration_id, "report", invocation_state,
            phase="app", status="completed",
        )
        record_pipeline_status(migration_id, "completed", "app")

        return serialized

    except Exception as exc:
        logger.error("[%s] QA pipeline failed: %s", migration_id, exc, exc_info=True)

        duration = time.time() - start_time
        save_checkpoint(
            migration_id, "verify", invocation_state,
            phase="app", status="failed",
        )
        record_pipeline_status(migration_id, "failed", "app")

        return {
            "migration_id": migration_id,
            "type": "app_migration",
            "status": "FAILED",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "duration_seconds": round(duration, 1),
            "transform_phase": {
                "total_files": len(mappers),
                "succeeded": succeeded,
                "failed": failed,
                "files": transform_results,
            },
            "execution_order": ["transform"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


def build_parallel_data_pipeline(
    agents: dict[str, Agent],
    table_groups: list[list[str]],
    *,
    execution_timeout: int = 3600,
    node_timeout: int = 1800,
) -> Any:
    """Build a parallel data migration pipeline with fan-out/fan-in.

    Splits tables into groups (e.g., by FK dependency tiers) and migrates
    each group in parallel. Uses Strands Graph's native parallel execution:
    when a node has edges to multiple targets without conditions, they
    execute in parallel.

    Pipeline::

        prepare ──┬── migrate_group_0
                  ├── migrate_group_1  ──┬── verify_all
                  └── migrate_group_N  ──┘

    Args:
        agents: Dict with ``data_migrator`` and ``data_verifier`` agents.
        table_groups: List of table name lists, grouped by dependency tier.
            Tier 0 (no FKs) can run in parallel with Tier 1, etc.
        execution_timeout: Total timeout.
        node_timeout: Per-node timeout.

    Returns:
        A compiled Strands Graph object.
    """
    required = ["data_migrator", "data_verifier"]
    _validate_agents(agents, required)

    if len(table_groups) <= 1:
        logger.info("Only 1 table group, using sequential data pipeline")
        return build_data_pipeline(agents, execution_timeout=execution_timeout, node_timeout=node_timeout)

    builder = GraphBuilder()

    # Add fan-out nodes for each table group
    # Each group gets its own data_migrator agent to avoid context sharing
    group_nodes = []
    for i, group in enumerate(table_groups):
        node_name = f"migrate_group_{i}"
        builder.add_node(agents["data_migrator"], node_name)
        group_nodes.append(node_name)

    # Fan-in: all groups converge to single verification
    builder.add_node(agents["data_verifier"], "verify_all")

    # Entry point fans out to all groups (parallel execution)
    builder.set_entry_point(group_nodes[0])
    for i, node_name in enumerate(group_nodes):
        # Each group leads to verification
        builder.add_edge(node_name, "verify_all")
        # Fan-out: first node fans out to subsequent groups
        if i > 0:
            builder.add_edge(group_nodes[0], node_name)

    builder.set_max_node_executions(len(table_groups) + 2)
    builder.set_execution_timeout(execution_timeout)
    builder.set_node_timeout(node_timeout)

    graph = builder.build()
    logger.info(
        "Parallel data pipeline built: %d groups (%s tables total), timeout=%ds",
        len(table_groups),
        sum(len(g) for g in table_groups),
        execution_timeout,
    )
    return graph


# ---------------------------------------------------------------------------
# Pipeline execution helpers
# ---------------------------------------------------------------------------

def run_migration(
    graph: Any,
    config: dict,
    *,
    resume_from: str | None = None,
    invocation_state: dict | None = None,
) -> dict:
    """Execute the migration pipeline synchronously.

    Wraps the graph invocation with proper input construction, hook setup,
    state tracking, checkpoint persistence, and result serialization.

    Args:
        graph: Compiled Strands Graph from ``build_migration_pipeline``.
        config: Migration configuration dict with keys:
            - ``oracle_config``: Oracle connection settings
            - ``pg_config``: PostgreSQL connection settings
            - ``migration_id``: Unique run identifier
            - ``scope``: Optional scope filters
        resume_from: Optional migration_id to resume from a checkpoint.
            If provided, loads the last checkpoint and resumes from the
            next node after the last completed one.

    Returns:
        Serialized migration state dict with execution results and metrics.

    Raises:
        RuntimeError: If the pipeline fails with an unrecoverable error.
    """
    migration_id = config.get("migration_id", f"mig-{int(time.time())}")

    # Initialize telemetry (no-op if OpenTelemetry not installed)
    init_telemetry()

    # Initialize cost tracker
    cost_tracker = CostTracker()

    # Initialize hook provider (cost tracking + WebSocket events)
    hook_provider = MigrationHookProvider(
        migration_id=migration_id,
        ws_notify=create_ws_notify(),
        cost_tracker=cost_tracker,
    )

    # --- Resume from checkpoint ---
    checkpoint = None
    if resume_from:
        checkpoint = load_latest_checkpoint(resume_from)
        if checkpoint:
            migration_id = resume_from
            entry_point = get_resume_entry_point(checkpoint)
            if entry_point is None:
                logger.info("[%s] Pipeline already completed, nothing to resume", migration_id)
                return {"migration_id": migration_id, "status": "ALREADY_COMPLETED"}
            logger.info("[%s] Resuming from node: %s", migration_id, entry_point)
        else:
            logger.warning("[%s] No checkpoint found, starting fresh", resume_from)

    # Build discovery input prompt
    discovery_input = build_discovery_input(config)

    # Prepare invocation state (shared across all nodes)
    if checkpoint and checkpoint.get("invocation_state"):
        # Restore invocation state from checkpoint
        invocation_state = checkpoint["invocation_state"]
        invocation_state["_start_time"] = time.time()
        invocation_state["_resumed_from"] = checkpoint.get("node_name")
        invocation_state.setdefault("_completed_nodes", checkpoint.get("completed_nodes", []))
        logger.info("[%s] Restored invocation state from checkpoint", migration_id)
    elif invocation_state is not None:
        # Use externally provided invocation_state (for live progress tracking)
        invocation_state.setdefault("_start_time", time.time())
        invocation_state.setdefault("_completed_nodes", [])
        logger.info("[%s] Using external invocation state", migration_id)
    else:
        invocation_state = {
            "oracle_config": config.get("oracle_config", {}),
            "pg_config": config.get("pg_config", {}),
            "migration_id": migration_id,
            "scope": config.get("scope", {}),
            "transform_results": {},
            "verification_results": {},
            "remediation_history": [],
            "_remediation_loop_count": 0,
            "_phase": MigrationPhase.PENDING.value,
            "_start_time": time.time(),
            "_completed_nodes": [],
            "_cost_tracker": cost_tracker,
            "_hook_provider": hook_provider,
        }

    logger.info(
        "[%s] Starting migration pipeline: oracle=%s, pg=%s%s",
        migration_id,
        config.get("oracle_config", {}).get("host", "N/A"),
        config.get("pg_config", {}).get("host", "N/A"),
        f" (resumed)" if resume_from else "",
    )

    try:
        # Emit pipeline start event
        hook_provider.on_graph_start({"migration_id": migration_id})

        result = graph(
            discovery_input,
            invocation_state=invocation_state,
        )

        # Emit pipeline end event
        hook_provider.on_graph_end({"migration_id": migration_id, "status": "completed"})

        # Serialize result for persistence
        serialized = serialize_migration_state(result)
        serialized["migration_id"] = migration_id
        serialized["config"] = {
            "oracle_host": config.get("oracle_config", {}).get("host"),
            "oracle_schema": config.get("oracle_config", {}).get("schema"),
            "pg_host": config.get("pg_config", {}).get("host"),
            "pg_database": config.get("pg_config", {}).get("database"),
        }

        duration = time.time() - invocation_state["_start_time"]
        logger.info(
            "[%s] Pipeline completed: status=%s, duration=%.1fs",
            migration_id,
            serialized.get("status", "unknown"),
            duration,
        )

        # ── Cost tracking summary ──
        cost_tracker.log_summary()
        serialized["cost"] = cost_tracker.summary()

        # ── Ensure generate_html_report is called programmatically ──
        # The report agent may or may not have called the tool.
        # This guarantees the bilingual HTML report is always generated.
        _ensure_html_report(serialized, config, migration_id, duration)

        # Save final checkpoint
        save_checkpoint(
            migration_id, "report", invocation_state,
            phase="schema", status="completed",
        )
        record_pipeline_status(migration_id, "completed", "schema")

        return serialized

    except Exception as exc:
        hook_provider.on_graph_end({"migration_id": migration_id, "status": "failed", "error": str(exc)})
        logger.error(
            "[%s] Pipeline failed with error: %s",
            migration_id,
            exc,
            exc_info=True,
        )

        # Save failure checkpoint so we can resume
        last_completed = invocation_state.get("_completed_nodes", [])
        last_node = last_completed[-1] if last_completed else "unknown"
        save_checkpoint(
            migration_id, last_node, invocation_state,
            phase="schema", status="failed",
        )
        record_pipeline_status(migration_id, "failed", "schema")

        duration = time.time() - invocation_state["_start_time"]
        return {
            "migration_id": migration_id,
            "status": "FAILED",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "duration_seconds": round(duration, 1),
            "nodes": {},
            "execution_order": [],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "resumable": True,
        }


async def run_migration_async(
    graph: Any,
    config: dict,
) -> dict:
    """Execute the migration pipeline asynchronously.

    Args:
        graph: Compiled Strands Graph from ``build_migration_pipeline``.
        config: Migration configuration dict (same as ``run_migration``).

    Returns:
        Serialized migration state dict.
    """
    migration_id = config.get("migration_id", f"mig-{int(time.time())}")

    discovery_input = build_discovery_input(config)

    invocation_state = {
        "oracle_config": config.get("oracle_config", {}),
        "pg_config": config.get("pg_config", {}),
        "migration_id": migration_id,
        "scope": config.get("scope", {}),
        "transform_results": {},
        "verification_results": {},
        "remediation_history": [],
        "_remediation_loop_count": 0,
        "_phase": MigrationPhase.PENDING.value,
        "_start_time": time.time(),
    }

    logger.info("[%s] Starting async migration pipeline", migration_id)

    try:
        result = await graph.invoke_async(
            discovery_input,
            invocation_state=invocation_state,
        )

        serialized = serialize_migration_state(result)
        return serialized

    except Exception as exc:
        logger.error("[%s] Async pipeline failed: %s", migration_id, exc, exc_info=True)
        duration = time.time() - invocation_state["_start_time"]
        return {
            "migration_id": migration_id,
            "status": "FAILED",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "duration_seconds": round(duration, 1),
            "execution_order": [],
        }


# ---------------------------------------------------------------------------
# Pipeline introspection
# ---------------------------------------------------------------------------

def get_pipeline_info() -> dict:
    """Return static metadata about the pipeline structure.

    Useful for documentation, dashboards, and API responses.

    Returns:
        Dict describing pipeline nodes, edges, and configuration defaults.
    """
    return {
        "name": "OMA Migration Pipeline",
        "version": "2.0",
        "nodes": [
            {
                "id": "discover",
                "agent": "discovery",
                "description": "Analyze Oracle schema, build dependency DAG, score complexity",
                "model_tier": "opus",
            },
            {
                "id": "design",
                "agent": "schema_architect",
                "description": "Design PostgreSQL schema from Oracle DDL analysis",
                "model_tier": "opus",
            },
            {
                "id": "transform",
                "agent": "code_migrator",
                "description": "Convert Oracle SQL/PL-SQL to PostgreSQL",
                "model_tier": "opus",
            },
            {
                "id": "verify",
                "agent": "qa_verifier",
                "description": "Validate conversions via syntax check and execution comparison",
                "model_tier": "opus",
            },
            {
                "id": "evaluate",
                "agent": "evaluator",
                "description": "5-dimension scoring and GO/NO_GO/CONDITIONAL verdict",
                "model_tier": "opus",
            },
            {
                "id": "remediate",
                "agent": "remediation",
                "description": "Fix failed conversions using error context and pattern memory",
                "model_tier": "opus",
            },
            {
                "id": "data_migrate",
                "agent": "data_migrator",
                "description": "Transfer all data from Oracle to PostgreSQL table by table",
                "model_tier": "opus",
            },
            {
                "id": "data_verify",
                "agent": "data_verifier",
                "description": "Verify data integrity: row counts, sample data, FK integrity, sequences",
                "model_tier": "opus",
            },
            {
                "id": "report",
                "agent": "report",
                "description": "Generate migration report with radar charts and diff views",
                "model_tier": "opus",
            },
        ],
        "edges": [
            {"from": "discover", "to": "design", "type": "sequential"},
            {"from": "design", "to": "transform", "type": "sequential"},
            {"from": "transform", "to": "verify", "type": "sequential"},
            {"from": "verify", "to": "evaluate", "type": "sequential"},
            {"from": "evaluate", "to": "data_migrate", "type": "conditional", "condition": "GO"},
            {"from": "evaluate", "to": "remediate", "type": "conditional", "condition": "NO_GO | CONDITIONAL"},
            {"from": "data_migrate", "to": "data_verify", "type": "sequential"},
            {"from": "data_verify", "to": "report", "type": "sequential"},
            {"from": "remediate", "to": "verify", "type": "sequential", "note": "self-healing loop"},
        ],
        "defaults": {
            "max_node_executions": DEFAULT_MAX_NODE_EXECUTIONS,
            "execution_timeout": DEFAULT_EXECUTION_TIMEOUT,
            "node_timeout": DEFAULT_NODE_TIMEOUT,
            "max_remediation_loops": MAX_REMEDIATION_LOOPS,
        },
    }


# ---------------------------------------------------------------------------
# Programmatic report generation (guaranteed bilingual HTML report)
# ---------------------------------------------------------------------------

def _ensure_html_report(
    serialized: dict,
    config: dict,
    migration_id: str,
    duration: float,
) -> None:
    """Call generate_html_report programmatically after pipeline completion.

    The report agent (LLM) is unreliable at calling the tool — it sometimes
    writes HTML directly, losing bilingual support, language toggle, executive
    summary, and radar chart. This function guarantees the official report
    template is always used.
    """
    try:
        from common.tools.analysis_tools import generate_html_report

        # Build report data from pipeline state
        report_data = {
            "project_name": "OMA Migration",
            "migration_id": migration_id,
            "migration_date": time.strftime("%Y-%m-%d"),
            "source": {
                "type": "Oracle",
                "host": config.get("oracle_config", {}).get("host", ""),
                "schema": config.get("oracle_config", {}).get("schema", ""),
            },
            "target": {
                "type": "PostgreSQL",
                "host": config.get("pg_config", {}).get("host", ""),
                "database": config.get("pg_config", {}).get("database", ""),
            },
            "metrics": {
                "duration_seconds": round(duration, 1),
                "execution_order": serialized.get("execution_order", []),
            },
        }

        # Extract report data from the report node's agent output if available
        # The report agent collects detailed data; we merge it with our metadata
        nodes = serialized.get("nodes", {})
        report_node = nodes.get("report", {})

        # Try to extract structured data from the report agent's last message
        report_text = ""
        if isinstance(report_node, dict):
            report_text = report_node.get("result", "")
        elif hasattr(report_node, "result"):
            inner = report_node.result
            if hasattr(inner, "message") and isinstance(inner.message, dict):
                for item in inner.message.get("content", []):
                    if isinstance(item, dict) and "text" in item:
                        report_text += item["text"]

        # Try to parse JSON from report agent's output
        if isinstance(report_text, str) and report_text.strip():
            # Look for JSON block in the text
            import re
            json_match = re.search(r'\{[\s\S]*"verdict"[\s\S]*\}', report_text)
            if json_match:
                try:
                    agent_data = json.loads(json_match.group())
                    # Merge agent's detailed data with our metadata
                    report_data.update(agent_data)
                except (json.JSONDecodeError, ValueError):
                    pass

        # Ensure we have at minimum the verdict and scores from serialized state
        if "verdict" not in report_data:
            report_data["verdict"] = serialized.get("verdict", "CONDITIONAL")
        if "readiness_score" not in report_data:
            report_data["readiness_score"] = serialized.get("readiness_score", 0)

        result_json = generate_html_report(
            migration_data=json.dumps(report_data, default=str)
        )
        result = json.loads(result_json)

        if result.get("success"):
            logger.info(
                "[%s] Bilingual HTML report generated: %s",
                migration_id, result.get("report_path", ""),
            )
        else:
            logger.warning(
                "[%s] generate_html_report returned error: %s",
                migration_id, result.get("error", "unknown"),
            )

    except Exception as e:
        logger.warning(
            "[%s] Programmatic report generation failed (non-fatal): %s",
            migration_id, e,
        )


def ensure_combined_report(
    schema_result: dict,
    data_result: dict,
    config: dict,
    migration_id: str,
    total_duration: float,
    verification: dict | None = None,
) -> str | None:
    """Generate comprehensive Phase 1 + Phase 2 combined HTML report.

    Called after Phase 2 completes. Merges schema migration results,
    data migration results, and DB verification into a single report.

    Args:
        schema_result: Serialized Phase 1 (schema) pipeline result.
        data_result: Phase 2 data migration result (from migrate_all_tables).
        config: Migration configuration dict.
        migration_id: Unique run identifier.
        total_duration: Total elapsed seconds for both phases.
        verification: Optional output from verify_data_integrity().

    Returns:
        Path to generated HTML report, or None if generation failed.
    """
    try:
        from common.tools.analysis_tools import generate_html_report

        oracle_schema = config.get("oracle_config", {}).get("schema", "AMZN")

        # Build comprehensive report data
        report_data = {
            "project_name": f"OMA Migration — {oracle_schema}",
            "migration_id": migration_id,
            "migration_date": time.strftime("%Y-%m-%d"),
            "source": {
                "type": "Oracle",
                "host": config.get("oracle_config", {}).get("host", ""),
                "schema": oracle_schema,
                "service": config.get("oracle_config", {}).get("service", ""),
            },
            "target": {
                "type": "PostgreSQL (Aurora)",
                "host": config.get("pg_config", {}).get("host", ""),
                "database": config.get("pg_config", {}).get("database", ""),
                "target_schema": config.get("pg_config", {}).get("target_schema", oracle_schema.lower()),
            },
            "metrics": {
                "duration_seconds": round(total_duration, 1),
                "execution_order": schema_result.get("execution_order", []),
                "phase1_duration": schema_result.get("duration_seconds", 0),
            },
        }

        # Merge Phase 1 data from schema_result
        # Try to extract verdict, scores, etc. from the schema pipeline output
        if isinstance(schema_result, dict):
            for key in ("verdict", "readiness_score", "scores", "discovery",
                        "conversions", "verification", "evaluation",
                        "remediation", "pipeline_nodes", "performance_baselines"):
                if key in schema_result:
                    report_data[key] = schema_result[key]

            # Extract from nodes if available
            nodes = schema_result.get("nodes", {})
            for node_name, node_data in nodes.items():
                if isinstance(node_data, dict):
                    result_text = node_data.get("result", "")
                    if isinstance(result_text, str) and result_text.strip():
                        import re
                        json_match = re.search(r'\{[\s\S]*"verdict"[\s\S]*\}', result_text)
                        if json_match:
                            try:
                                agent_data = json.loads(json_match.group())
                                for k, v in agent_data.items():
                                    if k not in report_data:
                                        report_data[k] = v
                            except (json.JSONDecodeError, ValueError):
                                pass

        # Ensure verdict exists
        if "verdict" not in report_data:
            report_data["verdict"] = schema_result.get("status", "CONDITIONAL")
        if "readiness_score" not in report_data:
            report_data["readiness_score"] = 0

        # Add Phase 2 data migration results
        if verification and verification.get("success"):
            report_data["data_migration"] = verification.get("data_migration", {})
            report_data["data_verification"] = verification.get("data_verification", {})
        elif isinstance(data_result, dict):
            # Fallback: use raw Phase 2 output
            dm_details = data_result.get("details", [])
            tables_list = []
            for d in dm_details:
                tables_list.append({
                    "name": d.get("table_name", ""),
                    "oracle_rows": d.get("rows_exported", 0),
                    "pg_rows": d.get("rows_verified", d.get("rows_inserted", 0)),
                    "status": "success" if d.get("success") else "failed",
                })

            report_data["data_migration"] = {
                "total_tables": data_result.get("tables_total", 0),
                "success_count": data_result.get("tables_migrated", 0),
                "failed_count": data_result.get("tables_failed", 0),
                "total_rows_oracle": data_result.get("total_rows_exported", 0),
                "total_rows_imported": data_result.get("total_rows_verified",
                                                        data_result.get("total_rows_inserted", 0)),
                "sequences_synced": 0,
                "tables": tables_list,
            }

        # Add Phase 2 duration
        if isinstance(data_result, dict):
            report_data["metrics"]["phase2_duration"] = data_result.get("duration_seconds", 0)

        result_json = generate_html_report(
            migration_data=json.dumps(report_data, default=str)
        )
        result = json.loads(result_json)

        if result.get("success"):
            report_path = result.get("report_path", "")
            logger.info(
                "[%s] Combined Phase 1+2 report generated: %s (sections: %s)",
                migration_id, report_path,
                result.get("sections_generated", []),
            )
            return report_path
        else:
            logger.warning(
                "[%s] Combined report generation returned error: %s",
                migration_id, result.get("error", "unknown"),
            )
            return None

    except Exception as e:
        logger.warning(
            "[%s] Combined report generation failed (non-fatal): %s",
            migration_id, e,
        )
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_agents(agents: dict[str, Agent], required: list[str]) -> None:
    """Validate that all required agents are present and non-None."""
    missing = [name for name in required if name not in agents]
    if missing:
        raise KeyError(f"Missing required agents: {missing}")

    none_agents = [name for name in required if agents[name] is None]
    if none_agents:
        raise ValueError(f"Agents cannot be None: {none_agents}")


def _extract_evaluate_result(state: Any) -> Any:
    """Extract the raw result from the evaluate node in graph state.

    Handles multiple state formats (dict, object with attributes).
    """
    # Try results dict first
    results = _safe_attr(state, "results", {})
    if isinstance(results, dict):
        eval_result = results.get("evaluate")
        if eval_result is not None:
            # Unwrap result object if needed
            inner = _safe_attr(eval_result, "result", None)
            if inner is not None:
                return inner
            return eval_result

    # Try direct attribute access
    evaluate = _safe_attr(state, "evaluate", None)
    if evaluate is not None:
        return evaluate

    # Try node_results pattern
    node_results = _safe_attr(state, "node_results", {})
    if isinstance(node_results, dict) and "evaluate" in node_results:
        return node_results["evaluate"]

    logger.warning("Could not extract evaluate result from state")
    return None



def _safe_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Get attribute or dict key safely."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)
