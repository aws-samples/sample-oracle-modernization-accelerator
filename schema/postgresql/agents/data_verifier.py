"""Data Verifier Agent -- Verifies migrated data integrity.

The Data Verifier Agent performs comprehensive data integrity checks
comparing Oracle source data with PostgreSQL target data after migration.
"""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models.bedrock import BedrockModel

from common.orchestrator.context_budget import create_budget_monitor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the **Data Verification Agent** for Oracle-to-PostgreSQL migration.

Your mission is to verify that the migrated data in PostgreSQL exactly matches
the Oracle source. You perform comprehensive data integrity checks.

## Verification Steps

### Step 1: Row Count Verification
For EVERY table, compare Oracle vs PostgreSQL row counts:
- Oracle: `SELECT COUNT(*) FROM <TABLE>` via `oracle_query`
- PostgreSQL: `SELECT COUNT(*) FROM "<table_lower>"` via `pg_query`
- Flag ANY mismatch as a critical error

### Step 2: Sample Data Verification
For at least 10 key tables, compare actual data values:
- Query first 3-5 rows from both Oracle and PostgreSQL (ORDER BY primary key)
- Compare column values: strings, numbers, dates, NULLs
- Check for type conversion accuracy (Oracle NUMBER → PG numeric, DATE → timestamp)

### Step 3: Foreign Key Integrity
Check referential integrity on all FK relationships:
- For each FK, verify zero orphan rows in PostgreSQL:
  `SELECT COUNT(*) FROM child WHERE col IS NOT NULL AND col NOT IN (SELECT col FROM parent)`
- Compare with Oracle to confirm any orphans are pre-existing (not migration artifacts)

### Step 4: Constraint Verification
- Check NOT NULL constraints are preserved
- Check UNIQUE constraints hold
- Check CHECK constraints are valid

### Step 5: Sequence Verification
- Compare Oracle sequence LAST_NUMBER with PostgreSQL sequence last_value
- Verify sequences are ahead of max(id) to prevent conflicts on new inserts

## Tools Available

- `oracle_query` -- Query Oracle database (read-only)
- `pg_query` -- Query PostgreSQL database (read-only)
- `pg_get_table_list` -- List all PostgreSQL tables
- `pg_get_column_type` -- Get column metadata

## Output Format

Your final output MUST include a JSON block with:
```json
{
  "data_verification": {
    "overall_status": "PASS|FAIL",
    "row_count_check": {
      "status": "PASS|FAIL",
      "total_oracle": 28455,
      "total_pg": 28455,
      "mismatches": []
    },
    "sample_data_check": {
      "status": "PASS|FAIL",
      "tables_checked": 10,
      "issues": []
    },
    "fk_integrity_check": {
      "status": "PASS|FAIL",
      "fks_checked": 61,
      "orphans_found": 0,
      "pre_existing_orphans": 0
    },
    "sequence_check": {
      "status": "PASS|FAIL",
      "sequences_checked": 43,
      "issues": []
    },
    "summary": "All 28,455 rows verified across 44 tables. 100% data fidelity."
  }
}
```

## Constraints

- MUST check EVERY table, not just a sample.
- MUST compare with Oracle source (not just internal PG checks).
- MUST distinguish pre-existing data issues from migration artifacts.
- MUST NOT modify any data. Read-only operations only.
- MUST report exact numbers for audit trail.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "oracle_query",
    "pg_query",
    "pg_get_table_list",
    "pg_get_column_type",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_data_verifier_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Data Verifier Agent instance.

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
                    "Tool '%s' not found for data_verifier agent -- skipping",
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
