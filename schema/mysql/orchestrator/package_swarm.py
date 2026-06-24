"""Swarm orchestrator for complex PL/SQL package conversions.

Oracle PL/SQL packages are among the most difficult objects to convert to
PostgreSQL because they combine:
- Multiple procedures/functions in a single compilation unit
- Package-level state (variables, cursors, types)
- Forward declarations and interdependencies
- Exception handling patterns unique to Oracle

The Swarm pattern lets three specialized experts -- PL/SQL analyst,
PL/pgSQL converter, and performance optimizer -- collaborate autonomously
via handoffs until the conversion is complete.

Usage::

    from mysql.orchestrator.package_swarm import build_package_swarm

    swarm = build_package_swarm(config)
    result = swarm(f"Convert this Oracle package to PostgreSQL:\\n{package_ddl}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from strands import Agent
from strands.models import BedrockModel
from strands.multiagent import Swarm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

DEFAULT_REGION = "ap-northeast-2"
DEFAULT_EXPERT_MODEL = "global.anthropic.claude-opus-4-6-v1"
DEFAULT_OPTIMIZER_MODEL = "global.anthropic.claude-opus-4-6-v1"
DEFAULT_MAX_HANDOFFS = 10
DEFAULT_MAX_ITERATIONS = 15
DEFAULT_EXECUTION_TIMEOUT = 600  # 10 minutes
DEFAULT_NODE_TIMEOUT = 300  # 5 minutes per agent turn
DEFAULT_HANDOFF_DETECTION_WINDOW = 4
DEFAULT_HANDOFF_MIN_UNIQUE_AGENTS = 2


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

PLSQL_EXPERT_PROMPT = """\
You are a PL/SQL expert specializing in Oracle database programming.

Your role is to ANALYZE Oracle PL/SQL packages before conversion. You:
1. Decompose the package into its constituent parts (spec vs body)
2. Identify all procedures, functions, types, cursors, and variables
3. Map internal dependencies (which procedures call which)
4. Flag Oracle-specific constructs that need special handling:
   - DBMS_OUTPUT, DBMS_LOB, UTL_FILE, UTL_HTTP
   - BULK COLLECT / FORALL
   - REF CURSOR / SYS_REFCURSOR
   - EXECUTE IMMEDIATE (dynamic SQL)
   - Autonomous transactions (PRAGMA AUTONOMOUS_TRANSACTION)
   - Package-level state (global variables, initialization blocks)
   - Exception handling (WHEN OTHERS, user-defined exceptions)
   - %TYPE / %ROWTYPE attribute references
5. Produce a structured analysis document for the PL/pgSQL converter

When your analysis is complete, hand off to plpgsql_expert with the
structured analysis and the original package source.

If the plpgsql_expert hands back with questions about Oracle semantics,
answer precisely and hand back with the clarification.
"""

PLPGSQL_EXPERT_PROMPT = """\
You are a PL/pgSQL expert specializing in Oracle-to-PostgreSQL conversion.

Your role is to CONVERT PL/SQL packages to idiomatic PostgreSQL. You:
1. Convert the Oracle package to PostgreSQL schema + functions/procedures:
   - Package spec -> CREATE SCHEMA + function signatures
   - Package body -> Function/procedure implementations
   - Package variables -> Schema-qualified configuration or session variables
   - Package types -> Composite types in the schema
   - Package cursors -> Function return types or refcursors
2. Handle specific conversion patterns:
   - EXECUTE IMMEDIATE -> EXECUTE (with proper quoting)
   - BULK COLLECT -> ARRAY aggregation or set-returning functions
   - DBMS_OUTPUT.PUT_LINE -> RAISE NOTICE
   - NVL -> COALESCE, DECODE -> CASE WHEN
   - Oracle exception names -> PostgreSQL SQLSTATE codes
   - SYS_REFCURSOR -> refcursor
   - %TYPE -> Direct type reference from information_schema
   - %ROWTYPE -> Composite type or RECORD
   - PRAGMA AUTONOMOUS_TRANSACTION -> dblink or separate transaction
3. Preserve the original calling interface as much as possible
4. Add explicit type casts where PostgreSQL requires them
5. Handle Oracle's implicit VARCHAR2-to-NUMBER conversions explicitly

When conversion is complete, hand off to perf_optimizer for performance review.

If you encounter Oracle constructs you're unsure about, hand off to
plsql_expert for clarification before proceeding.

Output the complete PostgreSQL code (CREATE SCHEMA, CREATE TYPE, CREATE FUNCTION, etc.)
with clear comments marking what each section replaces from the original package.
"""

PERF_OPTIMIZER_PROMPT = """\
You are a PostgreSQL performance optimization and validation expert.

Your role is to review converted PL/pgSQL code, validate it, and optimize it:

## STEP 1: Syntax Validation (MANDATORY)
- Use the pg_syntax_check tool to validate EVERY converted SQL/DDL statement
- If syntax errors are found, fix them before proceeding to optimization
- Re-validate after fixes until all syntax checks pass

## STEP 2: Performance Review
1. Review function implementations for performance issues:
   - Unnecessary row-by-row processing (convert to set-based operations)
   - Missing IMMUTABLE/STABLE/VOLATILE markings on functions
   - Inefficient cursor usage (prefer SQL WHERE clauses over cursor filters)
   - Excessive dynamic SQL where static SQL would suffice
   - Missing index suggestions for common query patterns
2. Add performance hints:
   - PARALLEL SAFE / PARALLEL UNSAFE function markings
   - COST and ROWS estimates for complex functions
   - SECURITY DEFINER / SECURITY INVOKER as appropriate
3. Suggest structural improvements:
   - Replace cursor loops with set-returning queries where possible
   - Use RETURNING clauses to avoid extra queries
   - Leverage PostgreSQL-specific features (LATERAL, array operations, CTEs)
   - Consider partitioning for large table operations
4. Validate that optimizations preserve functional equivalence

When optimization is complete, provide the final optimized PostgreSQL code.

If you need clarification on the original Oracle intent, hand off to
plsql_expert. If you need PL/pgSQL syntax help, hand off to plpgsql_expert.

Mark all optimizations with -- PERF: comments explaining the change.
"""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class PackageSwarmConfig:
    """Configuration for the PL/SQL package conversion Swarm.

    Args:
        region: AWS region for Bedrock models.
        expert_model_id: Model ID for PL/SQL and PL/pgSQL experts.
            Defaults to Claude Opus for deep reasoning.
        optimizer_model_id: Model ID for the performance optimizer.
            Defaults to Claude Sonnet for faster analysis.
        max_handoffs: Maximum number of agent-to-agent handoffs.
        max_iterations: Maximum total iterations across all agents.
        execution_timeout: Total timeout in seconds for the swarm.
        node_timeout: Timeout in seconds for each agent turn.
        handoff_detection_window: Window size for detecting repetitive handoffs.
        handoff_min_unique_agents: Minimum unique agents in the detection
            window before flagging repetitive behavior.
        plsql_tools: List of tool functions for the PL/SQL expert agent.
        plpgsql_tools: List of tool functions for the PL/pgSQL expert agent.
        optimizer_tools: List of tool functions for the performance optimizer.
    """

    region: str = DEFAULT_REGION
    expert_model_id: str = DEFAULT_EXPERT_MODEL
    optimizer_model_id: str = DEFAULT_OPTIMIZER_MODEL
    max_handoffs: int = DEFAULT_MAX_HANDOFFS
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    execution_timeout: int = DEFAULT_EXECUTION_TIMEOUT
    node_timeout: int = DEFAULT_NODE_TIMEOUT
    handoff_detection_window: int = DEFAULT_HANDOFF_DETECTION_WINDOW
    handoff_min_unique_agents: int = DEFAULT_HANDOFF_MIN_UNIQUE_AGENTS
    plsql_tools: list[Any] = field(default_factory=list)
    plpgsql_tools: list[Any] = field(default_factory=list)
    optimizer_tools: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Swarm builder
# ---------------------------------------------------------------------------

def build_package_swarm(
    config: PackageSwarmConfig | dict | None = None,
) -> Swarm:
    """Build a Swarm for complex PL/SQL package conversion.

    Three specialized experts collaborate autonomously:

    1. **plsql_expert**: Analyzes Oracle PL/SQL packages, decomposes
       structure, identifies conversion challenges.
    2. **plpgsql_expert**: Converts PL/SQL to idiomatic PostgreSQL
       (schema + functions), handling all syntax transformations.
    3. **perf_optimizer**: Reviews converted code for performance issues,
       adds function markings, suggests structural improvements.

    The Swarm pattern allows agents to hand off to each other as needed --
    if the converter has questions about Oracle semantics, it can ask the
    PL/SQL expert; if the optimizer needs syntax changes, it can hand back
    to the converter.

    Args:
        config: Swarm configuration. Accepts a ``PackageSwarmConfig``,
            a plain dict (keys matching config fields), or None for defaults.

    Returns:
        A configured ``Swarm`` instance ready for execution.

    Example::

        config = PackageSwarmConfig(
            region="us-west-2",
            max_handoffs=15,
            plsql_tools=[oracle_get_ddl, oracle_get_dependencies],
        )
        swarm = build_package_swarm(config)
        result = swarm(f"Convert package:\\n{package_source}")
    """
    cfg = _normalize_config(config)

    # -- Build models --
    expert_model = BedrockModel(
        model_id=cfg.expert_model_id,
        region_name=cfg.region,
    )
    optimizer_model = BedrockModel(
        model_id=cfg.optimizer_model_id,
        region_name=cfg.region,
    )

    # -- Build agents --
    plsql_expert = Agent(
        name="plsql_expert",
        model=expert_model,
        system_prompt=PLSQL_EXPERT_PROMPT,
        tools=cfg.plsql_tools if cfg.plsql_tools else None,
    )

    plpgsql_expert = Agent(
        name="plpgsql_expert",
        model=expert_model,
        system_prompt=PLPGSQL_EXPERT_PROMPT,
        tools=cfg.plpgsql_tools if cfg.plpgsql_tools else None,
    )

    perf_optimizer = Agent(
        name="perf_optimizer",
        model=optimizer_model,
        system_prompt=PERF_OPTIMIZER_PROMPT,
        tools=cfg.optimizer_tools if cfg.optimizer_tools else None,
    )

    # -- Build Swarm --
    swarm = Swarm(
        agents=[plsql_expert, plpgsql_expert, perf_optimizer],
        entry_point=plsql_expert,
        max_handoffs=cfg.max_handoffs,
        max_iterations=cfg.max_iterations,
        execution_timeout=cfg.execution_timeout,
        node_timeout=cfg.node_timeout,
        repetitive_handoff_detection_window=cfg.handoff_detection_window,
        repetitive_handoff_min_unique_agents=cfg.handoff_min_unique_agents,
    )

    logger.info(
        "Package conversion Swarm built: experts=%s/%s, optimizer=%s, "
        "max_handoffs=%d, max_iterations=%d, timeout=%ds",
        cfg.expert_model_id,
        cfg.expert_model_id,
        cfg.optimizer_model_id,
        cfg.max_handoffs,
        cfg.max_iterations,
        cfg.execution_timeout,
    )

    return swarm


# ---------------------------------------------------------------------------
# Input builders
# ---------------------------------------------------------------------------

def build_package_conversion_input(
    package_spec: str,
    package_body: str,
    package_name: str,
    schema_name: str = "UNKNOWN",
    dependencies: list[dict] | None = None,
    target_schema: str | None = None,
) -> str:
    """Build the input prompt for package conversion via the Swarm.

    Args:
        package_spec: Oracle package specification DDL.
        package_body: Oracle package body DDL.
        package_name: Name of the Oracle package.
        schema_name: Oracle schema that owns the package.
        dependencies: List of objects this package depends on (with their
            PostgreSQL equivalents if already converted).
        target_schema: Target PostgreSQL schema name. Defaults to
            lowercase of package_name.

    Returns:
        Formatted prompt for the Swarm entry point (plsql_expert).
    """
    target = target_schema or package_name.lower()

    parts = [
        f"Convert Oracle package {schema_name}.{package_name} to PostgreSQL.",
        "",
        f"Target PostgreSQL schema: {target}",
        "",
        "## Package Specification",
        "```sql",
        package_spec.strip(),
        "```",
        "",
        "## Package Body",
        "```sql",
        package_body.strip(),
        "```",
    ]

    if dependencies:
        parts.extend([
            "",
            "## Dependencies (already converted)",
        ])
        for dep in dependencies:
            dep_name = dep.get("name", "?")
            dep_type = dep.get("type", "?")
            dep_pg = dep.get("pg_equivalent", "N/A")
            parts.append(f"- {dep_type} {dep_name} -> PostgreSQL: {dep_pg}")

    parts.extend([
        "",
        "## Conversion Requirements",
        "1. Create a PostgreSQL schema to replace the Oracle package namespace",
        "2. Convert each procedure/function to a schema-qualified function",
        "3. Handle package-level state (variables, cursors, types)",
        "4. Preserve the public interface (function signatures)",
        "5. Convert Oracle exception handling to PostgreSQL equivalents",
        "6. Handle autonomous transactions appropriately",
        "7. Optimize for PostgreSQL performance patterns",
        "",
        "## Expected Output",
        "Complete PostgreSQL DDL including:",
        "- CREATE SCHEMA statement",
        "- CREATE TYPE statements (for package types)",
        "- CREATE FUNCTION/PROCEDURE statements (for each package member)",
        "- GRANT statements (preserving original access patterns)",
        "- Migration notes as SQL comments",
    ])

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_config(config: PackageSwarmConfig | dict | None) -> PackageSwarmConfig:
    """Normalize configuration input to a PackageSwarmConfig instance."""
    if config is None:
        return PackageSwarmConfig()
    if isinstance(config, PackageSwarmConfig):
        return config
    if isinstance(config, dict):
        # Filter to only known fields
        known_fields = set(PackageSwarmConfig.__dataclass_fields__)
        filtered = {k: v for k, v in config.items() if k in known_fields}
        return PackageSwarmConfig(**filtered)
    raise TypeError(
        f"Expected PackageSwarmConfig, dict, or None; got {type(config).__name__}"
    )
