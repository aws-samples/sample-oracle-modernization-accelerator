"""Chat Assistant Agent -- Natural Language Interface for OMA.

A conversational agent that can answer questions about the Oracle-to-PostgreSQL
migration, query both databases, analyze MyBatis mappers, and explain conversion
patterns. Acts as the "brain" behind the web UI's chat interface.
"""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the OMA Chat Assistant -- an expert AI for Oracle-to-PostgreSQL database migration.

You have access to tools that let you:
1. **Query Oracle** (oracle_query, oracle_get_ddl, oracle_get_object_list, etc.)
2. **Query PostgreSQL** (pg_query, pg_explain, pg_syntax_check, etc.)
3. **Analyze MyBatis XML** (mybatis_extract_sqls, mybatis_scan_directory, mybatis_validate_xml)
4. **Look up conversion patterns** (oracle_to_pg_reference, search_conversion_knowledge)
5. **Assess migration complexity** (apply_static_rules, compute_coverage_score, compute_equivalence_score)

Guidelines:
- Answer in the same language as the user's question (Korean or English).
- Use tools proactively to provide accurate, data-driven answers.
- When asked about SQL conversion, show both Oracle and PostgreSQL versions.
- For schema questions, query the actual database rather than guessing.
- Be concise but thorough. Use tables/lists for structured data.
- If you don't know something, say so rather than hallucinating.

The target Oracle schema and PostgreSQL database will be configured by environment variables.
"""

TOOL_NAMES = [
    "oracle_query",
    "oracle_get_ddl",
    "oracle_get_object_list",
    "oracle_get_source",
    "oracle_get_table_columns",
    "oracle_get_constraints",
    "oracle_get_indexes",
    "oracle_get_sequences",
    "pg_query",
    "pg_explain",
    "pg_syntax_check",
    "pg_get_column_type",
    "pg_get_table_list",
    "mybatis_extract_sqls",
    "mybatis_scan_directory",
    "mybatis_validate_xml",
    "apply_static_rules",
    "compute_coverage_score",
    "compute_equivalence_score",
    "oracle_to_pg_reference",
    "search_conversion_knowledge",
]


def create_chat_assistant_agent(
    model: Any,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create the Chat Assistant agent.

    Args:
        model: Bedrock model instance (Opus/Sonnet).
        tools: Dict of all available tools keyed by name.

    Returns:
        Configured Strands Agent for chat interaction.
    """
    agent_tools = []
    if tools:
        for name in TOOL_NAMES:
            if name in tools:
                agent_tools.append(tools[name])
            else:
                logger.warning("Chat assistant tool not found: %s", name)

    agent = Agent(
        model=model,
        tools=agent_tools,
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=SlidingWindowConversationManager(
            window_size=20,
            should_truncate_results=True,
        ),
    )

    logger.info("Chat assistant agent created with %d tools", len(agent_tools))
    return agent
