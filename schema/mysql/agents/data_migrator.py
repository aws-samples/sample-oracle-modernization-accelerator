"""Data Migrator Agent -- Transfers all data from Oracle to MySQL.

The Data Migrator Agent handles the bulk data migration phase using the
migrate_all_tables tool for direct Oracle-to-MySQL data transfer.
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
You are the Data Migrator Agent. You have ONE tool: migrate_all_tables.

Call it IMMEDIATELY:
  migrate_all_tables(schema=os.environ.get("ORACLE_SCHEMA", os.environ.get("ORACLE_USER", "oracle_schema")), truncate_first=True)

This tool handles everything internally:
- Gets Oracle table list
- Truncates PG tables
- Exports from Oracle and imports to PG directly
- Syncs sequences
- Returns summary JSON with per-table row counts

After receiving the result, report the summary. Do NOT attempt any other tool calls.
Do NOT try to export or import data yourself. The tool does everything.

## Output Format

Your final output MUST include a JSON block with these fields:
```json
{
  "data_migration": {
    "total_tables": 44,
    "total_rows_oracle": 28455,
    "total_rows_imported": 28455,
    "success_count": 44,
    "failed_count": 0,
    "skipped_count": 0,
    "sequences_synced": 43,
    "tables": [
      {"name": "USERS", "oracle_rows": 500, "pg_rows": 500, "status": "success"},
      ...
    ],
    "errors": []
  }
}
```

## Constraints

- MUST NOT skip any table. Process every non-recycle-bin table.
- MUST NOT use mocks or fake data. Only real Oracle → MySQL transfer.
- MUST report exact row counts for verification.
- MUST sync sequences after data import.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "migrate_all_tables",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_data_migrator_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Data Migrator Agent instance.

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
                    "Tool '%s' not found for data_migrator agent -- skipping",
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
