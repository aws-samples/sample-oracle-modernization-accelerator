"""Schema Architect Agent -- Designs PostgreSQL schema from Oracle DDL.

The Schema Architect Agent receives the Discovery Report and produces
PostgreSQL-compatible DDL with proper data type mappings, constraints,
indexes, and partitioning.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models.bedrock import BedrockModel

from common.orchestrator.context_budget import create_budget_monitor

logger = logging.getLogger(__name__)

# Reference tool name constant
_REF_TOOL = "oracle_to_pg_reference"


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the **Schema Architect Agent** for Oracle-to-PostgreSQL migration.

Your mission is to design PostgreSQL DDL ONLY for objects that DMS Schema
Conversion could not handle. DMS SC has already applied DDL to PostgreSQL
via `export_to_target` — you must NOT re-create objects that already exist.

## MANDATORY FIRST STEP (NON-NEGOTIABLE)

**BEFORE doing ANY conversion work, you MUST call:**

    dms_sc_verify_target(schema=os.environ.get("ORACLE_SCHEMA", os.environ.get("ORACLE_USER", "oracle_schema")))

This tool queries both Oracle and PostgreSQL databases and returns the
GROUND TRUTH of what exists vs what's missing. It returns:
- `pg_exists`: Objects already in PostgreSQL → DO NOT TOUCH
- `agent_required`: Objects missing from PostgreSQL → YOU MUST CONVERT THESE

**If you skip this step or convert objects not in `agent_required`, the
migration will fail.** The pipeline gate has already injected verified
triage data at the top of your input — cross-reference it with the tool output.

## DMS SC First Architecture

DMS Schema Conversion has already:
1. Imported Oracle metadata
2. Converted Oracle DDL to PostgreSQL DDL (rule-based)
3. Applied converted DDL directly to PostgreSQL (`export_to_target`)
4. Generated assessment report

Your role is to handle ONLY what DMS SC could not:
- Stored procedures/functions (PL/SQL → PL/pgSQL)
- Complex views with Oracle-specific syntax
- Objects that failed DMS SC conversion
- Any objects `dms_sc_verify_target` reports as MISSING_IN_PG

### Your Workflow:

**Step 1: Verify Target State (MANDATORY)**
- Call `dms_sc_verify_target(schema=os.environ.get("ORACLE_SCHEMA", os.environ.get("ORACLE_USER", "oracle_schema")))`
- Read the `agent_required` list — this is your ONLY work scope
- If `agent_required` is empty, skip to output (all done)

**Step 2: Convert Agent-Required Objects ONLY**
- For each object in `agent_required`:
  - Get Oracle DDL via `oracle_get_ddl`
  - Design PostgreSQL equivalent
  - Execute via `pg_execute_ddl` or validate via `pg_syntax_check`
- DO NOT touch objects in `pg_exists`

This hybrid approach ensures:
- ~95% of objects are converted deterministically by DMS SC (fast, repeatable)
- Only complex objects (stored procedures, CONNECT BY views, etc.) use AI

## Core Principles

- **Fidelity first**: The target schema must preserve all semantics of the
  source. Do not merge, split, or rename tables unless explicitly requested.
- **No data-model changes**: Preserve the logical data model exactly.
- **Document trade-offs**: Any lossy conversion (precision loss, behaviour
  difference) must be explicitly documented.
- **Trust DMS SC**: Do not re-convert objects that DMS SC successfully handled.
  Focus your effort on agent_required objects.

## Data Type Mapping Reference

| Oracle               | PostgreSQL            | Notes                            |
|----------------------|-----------------------|----------------------------------|
| NUMBER(p,s)          | NUMERIC(p,s)          | Exact precision preserved        |
| NUMBER(p,0) p<=4     | SMALLINT              | Performance optimisation          |
| NUMBER(p,0) p<=9     | INTEGER               | Performance optimisation          |
| NUMBER(p,0) p<=18    | BIGINT                | Performance optimisation          |
| NUMBER (no precision)| NUMERIC               | Arbitrary precision              |
| VARCHAR2(n)          | VARCHAR(n)            | Identical                        |
| NVARCHAR2(n)         | VARCHAR(n)            | PG uses UTF-8 natively           |
| CHAR(n)              | CHAR(n)               | Identical                        |
| CLOB                 | TEXT                  | PG TEXT is unbounded             |
| NCLOB                | TEXT                  | PG TEXT is unbounded             |
| BLOB                 | BYTEA                 | Or Large Object if >1 GB         |
| DATE                 | TIMESTAMP(0)          | Oracle DATE includes time!       |
| TIMESTAMP            | TIMESTAMP             | Identical                        |
| TIMESTAMP WITH TZ    | TIMESTAMPTZ           | Identical                        |
| RAW(n)               | BYTEA                 | Binary data                      |
| LONG                 | TEXT                  | Legacy type                      |
| LONG RAW             | BYTEA                 | Legacy type                      |
| XMLTYPE              | XML                   | PG native XML                    |
| SDO_GEOMETRY         | GEOMETRY (PostGIS)    | Requires PostGIS extension       |
| BOOLEAN (PL/SQL)     | BOOLEAN               | PG native                        |
| SYS_REFCURSOR        | REFCURSOR             | PG native                        |
| BINARY_FLOAT         | REAL                  | IEEE 754 single                  |
| BINARY_DOUBLE        | DOUBLE PRECISION      | IEEE 754 double                  |
| ROWID                | TEXT                  | No direct equivalent             |
| INTERVAL YEAR TO MONTH | INTERVAL            | PG interval is more general      |
| INTERVAL DAY TO SECOND | INTERVAL            | PG interval is more general      |

## Conversion Responsibilities (for agent_required objects ONLY)

1. **Tables**: Convert DDL preserving all columns, NOT NULL, DEFAULT values,
   CHECK constraints, PRIMARY KEY, UNIQUE constraints.

2. **Foreign Keys**: Preserve all FK relationships. Handle ON DELETE/UPDATE
   actions. Ensure referenced tables exist (respect dependency order).

3. **Indexes**: Convert Oracle indexes to PG equivalents.
   - B-Tree -> B-Tree (default)
   - Bitmap -> GIN (where appropriate)
   - Function-based -> Expression indexes
   - Reverse key -> hash index or standard B-Tree
   - Domain indexes -> GIN/GiST with appropriate operator class

4. **Sequences**: Convert Oracle sequences to PG sequences preserving
   START WITH, INCREMENT BY, MINVALUE, MAXVALUE, CACHE, CYCLE/NO CYCLE.
   Consider IDENTITY columns for simple auto-increment patterns.

5. **Partitioning**: Convert Oracle partitioning to PG native partitioning.
   - Range -> RANGE
   - List -> LIST
   - Hash -> HASH
   - Composite -> nested partitioning

6. **Views / Materialized Views**: Convert view definitions.
   Convert Oracle MVIEW refresh mechanisms to pg_cron or similar.

7. **Stored Procedures / Functions / Packages**: Convert PL/SQL to PL/pgSQL.
   This is typically the primary agent_required workload.

8. **Comments**: Preserve COMMENT ON TABLE/COLUMN statements.

## Self-Review (Reflection)

After generating DDL, you MUST self-review before outputting final results.
Use extended thinking to iterate:

1. **Generate** initial DDL from Oracle source
2. **Self-review checklist** — verify each item:
   - [ ] Data type precision: NUMBER(p,s) mapped correctly? No silent truncation?
   - [ ] FK references: All referenced tables/columns exist? Correct ON DELETE action?
   - [ ] Index strategy: Function-based indexes converted? Composite index column order preserved?
   - [ ] Sequence defaults: START WITH, INCREMENT BY, CACHE all preserved?
   - [ ] Constraint names: Unique, no Oracle length-limit naming collisions?
   - [ ] Dependency order: Tables created before FKs? Parent before child?
   - [ ] Oracle DATE → TIMESTAMP(0): Time component preserved?
   - [ ] Default values: SYSDATE → CURRENT_TIMESTAMP, USER → CURRENT_USER?
3. **Fix** any issues found in step 2
4. **Re-verify** — only output when ALL checklist items pass

## Reference Tool (CRITICAL)

You have access to `oracle_to_pg_reference` -- a comprehensive conversion
knowledge base. **ALWAYS call this tool BEFORE converting agent_required
objects** to ensure correct type mappings, function conversions, and DDL
patterns.

Usage examples:
- `oracle_to_pg_reference("data_types", "NUMBER")` -- Get NUMBER type mapping
- `oracle_to_pg_reference("ddl", "partition")` -- Get partitioning rules
- `oracle_to_pg_reference("ddl", "sequence")` -- Get sequence conversion rules
- `oracle_to_pg_reference("ddl", "constraint")` -- Get constraint rules
- `oracle_to_pg_reference("functions", "SYSDATE")` -- Get function mapping
- `oracle_to_pg_reference("aws_best_practices")` -- Get AWS migration pitfalls

Call this tool with relevant categories as you encounter Oracle constructs.
It provides AWS SCT/DMS-aligned conversion patterns.

## Tools Available

- `dms_sc_verify_target` -- **CALL FIRST**: Get ground truth of what exists in PG vs Oracle
- `dms_sc_apply_ddl` -- Apply DMS-converted DDL scripts to PostgreSQL (fallback)
- `dms_sc_collect_results` -- Collect DMS SC results from S3 (if needed)
- `oracle_get_ddl` -- Extract DDL for an Oracle object
- `oracle_get_table_columns` -- Get column definitions
- `oracle_get_constraints` -- Get constraint definitions
- `oracle_get_indexes` -- Get index definitions
- `oracle_get_sequences` -- Get sequence definitions
- `oracle_get_partitions` -- Get partition definitions
- `pg_execute_ddl` -- Execute DDL on PostgreSQL (for validation)
- `pg_syntax_check` -- Validate DDL syntax without executing
- `apply_static_rules` -- Apply regex-based static conversion rules
- `deploy_compat_library` -- Deploy Oracle compatibility functions
- `oracle_to_pg_reference` -- Look up conversion rules by category

## Output Format

Return a SchemaDesign containing:
- `dms_sc_applied`: Summary of DMS-converted DDL application results
- `agent_converted`: List of objects converted by AI agent
- `converted_ddls`: List of PostgreSQL DDL statements in dependency order
- `type_mapping`: JSON mapping of Oracle->PG type decisions
- `migration_notes`: List of notes about lossy conversions or special handling
- `index_strategy`: Index conversion decisions and rationale

## Constraints

- MUST call `dms_sc_verify_target` FIRST before any conversion work.
- MUST ONLY convert objects in the `agent_required` list from verify_target.
- MUST NOT re-create, alter, or touch objects in the `pg_exists` list.
- MUST NOT change the logical data model.
- MUST NOT assume data types without checking Oracle source.
- MUST NOT skip constraint or index conversion for agent_required objects.
- MUST generate DDL in correct dependency order (tables before FKs).
- If `agent_required` is empty, output confirmation and skip DDL design.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "dms_sc_verify_target",
    "dms_sc_apply_ddl",
    "dms_sc_collect_results",
    "oracle_get_ddl",
    "oracle_get_table_columns",
    "oracle_get_constraints",
    "oracle_get_indexes",
    "oracle_get_sequences",
    "oracle_get_partitions",
    "pg_execute_ddl",
    "pg_syntax_check",
    "apply_static_rules",
    "deploy_compat_library",
    _REF_TOOL,
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_schema_architect_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Schema Architect Agent instance.

    Args:
        model: BedrockModel instance to use.
        tools: Dict mapping tool name to callable.

    Returns:
        A configured Strands Agent instance.
    """
    budget_monitor = create_budget_monitor(
        budget_ratio=0.80,
        max_tool_result_tokens=50_000,
    )

    agent_tools: list = []
    if tools:
        for tool_name in TOOL_NAMES:
            if tool_name in tools:
                agent_tools.append(tools[tool_name])
            else:
                logger.warning(
                    "Tool '%s' not found for schema_architect agent -- skipping",
                    tool_name,
                )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=agent_tools if agent_tools else [],
        conversation_manager=SlidingWindowConversationManager(
            window_size=40,
            should_truncate_results=True,
        ),
    )

    agent._oma_budget_monitor = budget_monitor  # type: ignore[attr-defined]

    return agent


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TypeMapping:
    """A single Oracle -> PostgreSQL type mapping decision."""

    oracle_type: str
    pg_type: str
    notes: str = ""
    is_lossy: bool = False


@dataclass
class ConvertedDDL:
    """A single converted DDL statement."""

    object_name: str
    object_type: str
    oracle_ddl: str
    pg_ddl: str
    status: str = "CONVERTED"  # CONVERTED | FAILED | NEEDS_REVIEW
    warnings: list[str] = field(default_factory=list)


@dataclass
class MigrationNote:
    """A note about a conversion decision or trade-off."""

    object_name: str
    category: str  # TYPE_MAPPING | CONSTRAINT | INDEX | PARTITION | GENERAL
    description: str
    severity: str = "INFO"  # INFO | WARNING | CRITICAL


@dataclass
class SchemaDesign:
    """Complete output of the Schema Architect Agent."""

    converted_ddls: list[ConvertedDDL] = field(default_factory=list)
    type_mapping: list[TypeMapping] = field(default_factory=list)
    migration_notes: list[MigrationNote] = field(default_factory=list)
    index_strategy: list[dict[str, Any]] = field(default_factory=list)
    execution_order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "converted_ddls": [
                {
                    "object_name": d.object_name,
                    "object_type": d.object_type,
                    "oracle_ddl": d.oracle_ddl,
                    "pg_ddl": d.pg_ddl,
                    "status": d.status,
                    "warnings": d.warnings,
                }
                for d in self.converted_ddls
            ],
            "type_mapping": [
                {
                    "oracle_type": t.oracle_type,
                    "pg_type": t.pg_type,
                    "notes": t.notes,
                    "is_lossy": t.is_lossy,
                }
                for t in self.type_mapping
            ],
            "migration_notes": [
                {
                    "object_name": n.object_name,
                    "category": n.category,
                    "description": n.description,
                    "severity": n.severity,
                }
                for n in self.migration_notes
            ],
            "index_strategy": self.index_strategy,
            "execution_order": self.execution_order,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def get_ddl_script(self) -> str:
        """Return all converted DDLs as a single executable SQL script.

        DDLs are returned in execution_order if specified, otherwise
        in the order they were added.
        """
        if self.execution_order:
            ddl_map = {d.object_name: d for d in self.converted_ddls}
            ordered = [
                ddl_map[name]
                for name in self.execution_order
                if name in ddl_map
            ]
        else:
            ordered = self.converted_ddls

        parts: list[str] = []
        for ddl in ordered:
            if ddl.status == "CONVERTED":
                parts.append(f"-- {ddl.object_type}: {ddl.object_name}")
                parts.append(ddl.pg_ddl)
                parts.append("")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Standard type mapping reference
# ---------------------------------------------------------------------------

ORACLE_TO_PG_TYPE_MAP: dict[str, str] = {
    # Numeric
    "NUMBER": "NUMERIC",
    "BINARY_FLOAT": "REAL",
    "BINARY_DOUBLE": "DOUBLE PRECISION",
    "FLOAT": "DOUBLE PRECISION",
    # String
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "CHAR": "CHAR",
    "NCHAR": "CHAR",
    "CLOB": "TEXT",
    "NCLOB": "TEXT",
    "LONG": "TEXT",
    # Binary
    "BLOB": "BYTEA",
    "RAW": "BYTEA",
    "LONG RAW": "BYTEA",
    # Date/Time
    "DATE": "TIMESTAMP(0)",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMPTZ",
    "TIMESTAMP WITH LOCAL TIME ZONE": "TIMESTAMPTZ",
    "INTERVAL YEAR TO MONTH": "INTERVAL",
    "INTERVAL DAY TO SECOND": "INTERVAL",
    # Special
    "XMLTYPE": "XML",
    "ROWID": "TEXT",
    "UROWID": "TEXT",
    "BOOLEAN": "BOOLEAN",
    "SYS_REFCURSOR": "REFCURSOR",
}


def map_oracle_number(precision: int | None, scale: int | None) -> str:
    """Map Oracle NUMBER(p,s) to the most appropriate PG type.

    Uses integer types for zero-scale numbers when precision allows,
    for better performance.
    """
    if precision is None:
        return "NUMERIC"

    if scale is None or scale == 0:
        if precision <= 4:
            return "SMALLINT"
        if precision <= 9:
            return "INTEGER"
        if precision <= 18:
            return "BIGINT"
        return f"NUMERIC({precision})"

    return f"NUMERIC({precision},{scale})"


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------

def parse_schema_design(agent_output: str) -> SchemaDesign:
    """Parse JSON output from the Schema Architect Agent."""
    design = SchemaDesign()

    try:
        data = json.loads(agent_output)
    except json.JSONDecodeError:
        logger.warning("Could not parse Schema Architect output as JSON")
        return design

    for ddl_data in data.get("converted_ddls", []):
        design.converted_ddls.append(ConvertedDDL(
            object_name=ddl_data.get("object_name", ""),
            object_type=ddl_data.get("object_type", ""),
            oracle_ddl=ddl_data.get("oracle_ddl", ""),
            pg_ddl=ddl_data.get("pg_ddl", ""),
            status=ddl_data.get("status", "CONVERTED"),
            warnings=ddl_data.get("warnings", []),
        ))

    for tm_data in data.get("type_mapping", []):
        design.type_mapping.append(TypeMapping(
            oracle_type=tm_data.get("oracle_type", ""),
            pg_type=tm_data.get("pg_type", ""),
            notes=tm_data.get("notes", ""),
            is_lossy=tm_data.get("is_lossy", False),
        ))

    for note_data in data.get("migration_notes", []):
        design.migration_notes.append(MigrationNote(
            object_name=note_data.get("object_name", ""),
            category=note_data.get("category", "GENERAL"),
            description=note_data.get("description", ""),
            severity=note_data.get("severity", "INFO"),
        ))

    design.index_strategy = data.get("index_strategy", [])
    design.execution_order = data.get("execution_order", [])

    return design


def build_schema_task(discovery_report_json: str) -> str:
    """Build the user prompt sent to the Schema Architect Agent.

    Args:
        discovery_report_json: The JSON output from the Discovery Agent.

    Returns:
        A formatted task string for the agent.
    """
    return (
        "Design a PostgreSQL schema based on the following Oracle Discovery Report.\n"
        "\n"
        "Requirements:\n"
        "1. Convert ALL objects from the inventory to PostgreSQL DDL.\n"
        "2. Map every Oracle data type to the most appropriate PostgreSQL type.\n"
        "3. Preserve all constraints (PK, FK, UNIQUE, CHECK, NOT NULL, DEFAULT).\n"
        "4. Convert indexes with appropriate PG index types.\n"
        "5. Convert sequences preserving all attributes.\n"
        "6. Convert partitioning to PG native partitioning.\n"
        "7. Output DDLs in dependency order (tables before FKs).\n"
        "8. Document any lossy conversions in migration_notes.\n"
        "\n"
        "Use the Reflexion process: generate DDL, self-review, refine.\n"
        "\n"
        "Discovery Report:\n"
        f"{discovery_report_json}\n"
        "\n"
        "Return the complete SchemaDesign as JSON."
    )
