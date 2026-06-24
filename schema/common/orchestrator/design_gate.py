"""Design Gate: Injects verified DMS SC triage into Schema Architect.

Before the pipeline runs, this module calls dms_sc_verify_target to get
GROUND TRUTH (Oracle vs PG comparison) and injects the result directly
into the Schema Architect's system prompt. This is a code-level enforcement
that the agent cannot bypass:

1. The system prompt explicitly lists which objects to convert and which to skip
2. The agent also has dms_sc_verify_target as a tool to re-verify at runtime
3. dms_sc_apply_ddl skips "already exists" errors (idempotent)

Three layers of enforcement:
- Layer 1: System prompt injection (this module) — agent starts with knowledge
- Layer 2: Tool-level verification (dms_sc_verify_target) — agent can re-check
- Layer 3: DDL idempotency (dms_sc_apply_ddl) — duplicates are harmless
"""

from __future__ import annotations

import json
import logging
from typing import Any

from strands import Agent

logger = logging.getLogger(__name__)


def inject_triage_into_agent(schema_architect: Agent, oracle_schema: str) -> None:
    """Inject verified triage data into Schema Architect's system prompt.

    Calls dms_sc_verify_target at pipeline build time and appends the
    ground-truth triage to the agent's system_prompt. This runs BEFORE
    the pipeline starts, so the agent has this context from its very
    first message.

    Also programmatically creates any missing TABLE objects, since the
    agent (LLM) is unreliable when agent_required contains many objects
    and may skip some tables due to context window limits.

    Args:
        schema_architect: The Schema Architect Agent instance.
        oracle_schema: Oracle schema name (e.g., "AMZN").
    """
    triage_json = _get_verified_triage(oracle_schema)

    if not triage_json:
        logger.warning(
            "Design gate: dms_sc_verify_target not available at build time. "
            "Agent will rely on runtime tool call."
        )
        return

    triage = json.loads(triage_json)
    agent_required = triage.get("agent_required", [])
    target_exists = triage.get("target_exists", triage.get("pg_exists", []))  # Backward compatibility
    summary = triage.get("summary", {})
    target_db = triage.get("target_db", "PostgreSQL")

    # ── Programmatic safety net: create missing TABLEs/SEQUENCEs ──
    # The agent (LLM) is unreliable with large agent_required lists.
    # Tables and sequences are deterministic conversions — handle them
    # programmatically so the agent can focus on stored procedures.
    auto_created = _auto_create_missing_objects(agent_required, oracle_schema)
    if auto_created:
        # Remove auto-created objects from agent_required
        auto_names = {obj["name"] for obj in auto_created}
        agent_required = [
            obj for obj in agent_required
            if obj["name"] not in auto_names
        ]
        # Update summary
        summary["auto_created_by_design_gate"] = len(auto_created)
        summary["needs_agent_conversion"] = len(agent_required)

    enforcement = _build_enforcement_block(agent_required, target_exists, summary, target_db)

    # Append enforcement to system prompt
    original_prompt = schema_architect.system_prompt or ""
    schema_architect.system_prompt = f"{original_prompt}\n\n{enforcement}"

    logger.info(
        "Design gate: injected triage into system prompt — "
        "%d in %s (skip), %d need agent conversion, %d auto-created "
        "(%.1f%% DMS SC coverage)",
        len(target_exists),
        target_db,
        len(agent_required),
        len(auto_created),
        summary.get("dms_sc_coverage_pct", 0),
    )


def _auto_create_missing_objects(
    agent_required: list[dict],
    oracle_schema: str,
) -> list[dict]:
    """Programmatically create missing TABLEs and SEQUENCEs in PostgreSQL.

    The LLM agent is unreliable with large agent_required lists — it may
    skip tables due to context window limits or prioritize stored procedures.
    Tables and sequences are deterministic conversions that don't need AI.

    Strategy:
    1. Get Oracle DDL for each missing TABLE/SEQUENCE
    2. Apply static conversion rules (data type mapping, syntax fixes)
    3. Execute DDL on PostgreSQL
    4. Return list of successfully created objects

    Args:
        agent_required: Objects that need conversion (from dms_sc_verify_target).
        oracle_schema: Oracle schema name.

    Returns:
        List of dicts for successfully auto-created objects.
    """
    # Filter to TABLE and SEQUENCE types only — procedures need AI
    auto_targets = [
        obj for obj in agent_required
        if obj.get("type") in ("TABLE", "SEQUENCE")
    ]

    if not auto_targets:
        return []

    logger.info(
        "Design gate: auto-creating %d missing objects (TABLE/SEQUENCE) "
        "that DMS SC missed and agent might skip",
        len(auto_targets),
    )

    created = []

    # Import appropriate target DB tools based on environment or context
    try:
        from common.tools.oracle_tools import oracle_get_ddl
        from common.tools.analysis_tools import apply_static_rules

        # Try to determine target DB from context
        # Check if we're in postgresql or mysql directory context
        import os
        import sys

        # Check sys.path to determine which target DB tools to use
        is_mysql = any('mysql' in p for p in sys.path)
        is_postgresql = any('postgresql' in p for p in sys.path)

        if is_mysql:
            from mysql.tools.mysql_tools import mysql_execute_ddl as execute_ddl
        elif is_postgresql:
            from postgresql.tools.postgres_tools import pg_execute_ddl as execute_ddl
        else:
            # Default to PostgreSQL for backward compatibility
            from postgresql.tools.postgres_tools import pg_execute_ddl as execute_ddl

    except ImportError as e:
        logger.warning("Design gate: cannot auto-create — tools unavailable: %s", e)
        return []

    for obj in auto_targets:
        obj_name = obj["name"]
        obj_type = obj["type"]

        try:
            # 1. Get Oracle DDL
            ddl_json = oracle_get_ddl(
                object_name=obj_name,
                object_type=obj_type,
                schema=oracle_schema,
            )
            ddl_result = json.loads(ddl_json)
            if not ddl_result.get("success"):
                logger.warning(
                    "Design gate: could not get DDL for %s %s: %s",
                    obj_type, obj_name, ddl_result.get("error"),
                )
                continue

            oracle_ddl = ddl_result.get("ddl", "")
            if not oracle_ddl.strip():
                continue

            # 2. Apply static conversion rules (Oracle → PG)
            rules_json = apply_static_rules(sql=oracle_ddl)
            rules_result = json.loads(rules_json)
            if rules_result.get("success") and rules_result.get("converted"):
                pg_ddl = rules_result["converted"]
            else:
                # Basic fallback: lowercase, replace common patterns
                pg_ddl = oracle_ddl
                pg_ddl = pg_ddl.replace(f'"{oracle_schema}".', "")
                pg_ddl = pg_ddl.replace(f"{oracle_schema}.", "")

            # 3. Additional Oracle→PG fixups for DDL
            import re
            # Remove Oracle-specific storage clauses
            pg_ddl = re.sub(
                r'\s+(TABLESPACE|PCTFREE|PCTUSED|INITRANS|MAXTRANS|'
                r'STORAGE\s*\(.*?\)|LOGGING|NOCOMPRESS|SEGMENT\s+\w+|'
                r'ENABLE\s+ROW\s+MOVEMENT)',
                '', pg_ddl, flags=re.IGNORECASE | re.DOTALL,
            )
            # NUMBER → NUMERIC, VARCHAR2 → VARCHAR, etc.
            pg_ddl = re.sub(r'\bNUMBER\b', 'NUMERIC', pg_ddl, flags=re.IGNORECASE)
            pg_ddl = re.sub(r'\bVARCHAR2\b', 'VARCHAR', pg_ddl, flags=re.IGNORECASE)
            pg_ddl = re.sub(r'\bNVARCHAR2\b', 'VARCHAR', pg_ddl, flags=re.IGNORECASE)
            pg_ddl = re.sub(r'\bCLOB\b', 'TEXT', pg_ddl, flags=re.IGNORECASE)
            pg_ddl = re.sub(r'\bBLOB\b', 'BYTEA', pg_ddl, flags=re.IGNORECASE)
            pg_ddl = re.sub(r'\bRAW\s*\(\d+\)', 'BYTEA', pg_ddl, flags=re.IGNORECASE)
            pg_ddl = re.sub(r'\bLONG\s+RAW\b', 'BYTEA', pg_ddl, flags=re.IGNORECASE)
            pg_ddl = re.sub(r'\bLONG\b', 'TEXT', pg_ddl, flags=re.IGNORECASE)
            # Oracle DATE → TIMESTAMP(0)
            pg_ddl = re.sub(r'\bDATE\b(?!\s*_)', 'TIMESTAMP(0)', pg_ddl, flags=re.IGNORECASE)
            # SYSDATE → CURRENT_TIMESTAMP
            pg_ddl = re.sub(r'\bSYSDATE\b', 'CURRENT_TIMESTAMP', pg_ddl, flags=re.IGNORECASE)
            # Remove ENABLE constraints inline
            pg_ddl = re.sub(r'\s+ENABLE\s*$', '', pg_ddl, flags=re.MULTILINE | re.IGNORECASE)
            # BYTE/CHAR size semantics
            pg_ddl = re.sub(r'\s+(BYTE|CHAR)\s*\)', ')', pg_ddl, flags=re.IGNORECASE)

            # 4. Execute on PostgreSQL
            exec_json = execute_ddl(sql=pg_ddl)
            exec_result = json.loads(exec_json)

            if exec_result.get("success"):
                created.append({"name": obj_name, "type": obj_type, "status": "AUTO_CREATED"})
                logger.info(
                    "Design gate: auto-created %s %s in PostgreSQL",
                    obj_type, obj_name,
                )
            else:
                error = exec_result.get("error", "")
                if "already exists" in error.lower():
                    created.append({"name": obj_name, "type": obj_type, "status": "ALREADY_EXISTS"})
                    logger.info("Design gate: %s %s already exists (OK)", obj_type, obj_name)
                else:
                    logger.warning(
                        "Design gate: failed to create %s %s: %s",
                        obj_type, obj_name, error[:200],
                    )

        except Exception as e:
            logger.warning(
                "Design gate: auto-create failed for %s %s: %s",
                obj_type, obj_name, e,
            )

    logger.info(
        "Design gate: auto-created %d/%d missing objects",
        len(created), len(auto_targets),
    )
    return created


def _get_verified_triage(oracle_schema: str) -> str | None:
    """Call dms_sc_verify_target and return raw JSON, or None on failure."""
    try:
        from common.tools.dms_sc_tools import dms_sc_verify_target
        result = dms_sc_verify_target(schema=oracle_schema)
        parsed = json.loads(result)
        if parsed.get("success"):
            return result
        logger.warning("dms_sc_verify_target returned failure: %s", parsed.get("error"))
        return None
    except Exception as e:
        logger.error("Design gate: verify_target failed: %s", e)
        return None


def _build_enforcement_block(
    agent_required: list[dict],
    target_exists: list[dict],
    summary: dict,
    target_db: str = "PostgreSQL",
) -> str:
    """Build the enforcement text block appended to Schema Architect system prompt.

    This block is designed to be unambiguous and impossible to misinterpret:
    it explicitly lists what to convert and what to skip.
    """
    lines = [
        "",
        "=" * 70,
        "## VERIFIED DMS SC TRIAGE (CODE-ENFORCED AT PIPELINE BUILD TIME)",
        f"## Source: dms_sc_verify_target — actual Oracle vs {target_db} state",
        "=" * 70,
        "",
        f"DMS SC Coverage: {summary.get('dms_sc_coverage_pct', 0)}%",
        f"Already in {target_db}: {summary.get('already_in_target', summary.get('already_in_pg', 0))} objects",
        f"Needs agent conversion: {summary.get('needs_agent_conversion', 0)} objects",
        "",
    ]

    # Explicit SKIP list (abbreviated for token efficiency)
    if target_exists:
        skip_by_type: dict[str, list[str]] = {}
        for obj in target_exists:
            skip_by_type.setdefault(obj["type"], []).append(obj["name"])
        lines.append(f"### ALREADY IN {target_db.upper()} — DO NOT CONVERT:")
        for obj_type, names in sorted(skip_by_type.items()):
            lines.append(f"  {obj_type} ({len(names)}): {', '.join(sorted(names))}")
        lines.append("")

    # Explicit CONVERT list
    if agent_required:
        lines.append(f"### AGENT MUST CONVERT (missing from {target_db}):")
        for obj in agent_required:
            lines.append(f"  - {obj['type']} {obj['name']} (reason: {obj.get('reason', 'MISSING')})")
        lines.append("")
    else:
        lines.append(f"### ALL OBJECTS ALREADY IN {target_db.upper()}")
        lines.append("No DDL design needed. Confirm via dms_sc_verify_target and output summary.")
        lines.append("")

    lines.extend([
        "### ENFORCEMENT RULES:",
        "1. ONLY convert objects in 'AGENT MUST CONVERT' list above.",
        f"2. DO NOT touch objects in 'ALREADY IN {target_db.upper()}' list.",
        "3. Call dms_sc_verify_target(schema='SCHEMA_NAME') to re-verify at runtime.",
        "=" * 70,
    ])

    return "\n".join(lines)
