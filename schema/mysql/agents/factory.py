"""Agent Factory -- Creates all 9 OMA agents with correct models and tools.

Each agent module defines its own system prompt, tool configuration, and
create function following the official Strands SDK pattern. The factory
orchestrates model creation and delegates agent instantiation to each module.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from botocore.config import Config as BotoConfig
from strands import Agent
from strands.models import BedrockModel
from strands.models.bedrock import BEDROCK_CONTEXT_WINDOW_OVERFLOW_MESSAGES

from mysql.agents.discovery import create_discovery_agent, TOOL_NAMES as DISCOVERY_TOOLS
from mysql.agents.schema_architect import create_schema_architect_agent, TOOL_NAMES as SCHEMA_ARCHITECT_TOOLS
from mysql.agents.code_migrator import create_code_migrator_agent, TOOL_NAMES as CODE_MIGRATOR_TOOLS
from mysql.agents.qa_verifier import create_qa_verifier_agent, TOOL_NAMES as QA_VERIFIER_TOOLS
from mysql.agents.evaluator import create_evaluator_agent, TOOL_NAMES as EVALUATOR_TOOLS
from mysql.agents.remediation import create_remediation_agent, TOOL_NAMES as REMEDIATION_TOOLS
from mysql.agents.report import create_report_agent, TOOL_NAMES as REPORT_TOOLS
from mysql.agents.data_migrator import create_data_migrator_agent, TOOL_NAMES as DATA_MIGRATOR_TOOLS
from mysql.agents.data_verifier import create_data_verifier_agent, TOOL_NAMES as DATA_VERIFIER_TOOLS
from mysql.agents.chat_assistant import create_chat_assistant_agent, TOOL_NAMES as CHAT_ASSISTANT_TOOLS

# ---------------------------------------------------------------------------
# Patch: Strands SDK doesn't recognise Opus 4.6's overflow error format
# "prompt is too long: N tokens > M maximum" -- without this patch,
# ContextWindowOverflowException is never raised and auto-recovery
# (truncate tool results / slide window) never triggers.
# ---------------------------------------------------------------------------
_OPUS_OVERFLOW_MSG = "prompt is too long"
if _OPUS_OVERFLOW_MSG not in BEDROCK_CONTEXT_WINDOW_OVERFLOW_MESSAGES:
    BEDROCK_CONTEXT_WINDOW_OVERFLOW_MESSAGES.append(_OPUS_OVERFLOW_MSG)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BedrockConfig:
    """Bedrock-specific configuration."""

    region: str = "ap-northeast-2"
    opus_model_id: str = "global.anthropic.claude-opus-4-6-v1"
    sonnet_model_id: str = "global.anthropic.claude-opus-4-6-v1"
    haiku_model_id: str = "global.anthropic.claude-opus-4-6-v1"


@dataclass
class OMAConfig:
    """Top-level OMA configuration."""

    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    oracle_schema: str = ""
    source_path: str = ""
    max_remediation_attempts: int = 3
    enable_extended_thinking: bool = True


# ---------------------------------------------------------------------------
# Tool protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ToolCallable(Protocol):
    """Protocol for tool functions compatible with Strands @tool."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

def _create_models(config: OMAConfig) -> dict[str, BedrockModel]:
    """Create Bedrock model instances for each tier.

    Returns:
        Dict mapping tier name to BedrockModel instance.
    """
    # Increase read timeout to 10 minutes to handle large responses
    boto_config = BotoConfig(read_timeout=600, connect_timeout=10, retries={"max_attempts": 3})

    return {
        "opus": BedrockModel(
            model_id=config.bedrock.opus_model_id,
            region_name=config.bedrock.region,
            boto_client_config=boto_config,
        ),
        "sonnet": BedrockModel(
            model_id=config.bedrock.sonnet_model_id,
            region_name=config.bedrock.region,
            boto_client_config=boto_config,
        ),
        "haiku": BedrockModel(
            model_id=config.bedrock.haiku_model_id,
            region_name=config.bedrock.region,
            boto_client_config=boto_config,
        ),
    }


# ---------------------------------------------------------------------------
# Agent creator registry
# ---------------------------------------------------------------------------

_AGENT_CREATORS: dict[str, tuple[Any, list[str]]] = {
    "discovery": (create_discovery_agent, DISCOVERY_TOOLS),
    "schema_architect": (create_schema_architect_agent, SCHEMA_ARCHITECT_TOOLS),
    "code_migrator": (create_code_migrator_agent, CODE_MIGRATOR_TOOLS),
    "qa_verifier": (create_qa_verifier_agent, QA_VERIFIER_TOOLS),
    "evaluator": (create_evaluator_agent, EVALUATOR_TOOLS),
    "remediation": (create_remediation_agent, REMEDIATION_TOOLS),
    "report": (create_report_agent, REPORT_TOOLS),
    "data_migrator": (create_data_migrator_agent, DATA_MIGRATOR_TOOLS),
    "data_verifier": (create_data_verifier_agent, DATA_VERIFIER_TOOLS),
    "chat_assistant": (create_chat_assistant_agent, CHAT_ASSISTANT_TOOLS),
}


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def create_agent(
    agent_name: str,
    config: OMAConfig,
    tools: dict[str, ToolCallable] | None = None,
    models: dict[str, BedrockModel] | None = None,
) -> Agent:
    """Create a single OMA agent by name.

    Args:
        agent_name: Name of the agent (e.g., "discovery", "code_migrator").
        config: OMA configuration.
        tools: Optional dict mapping tool name to callable. If not provided,
               the agent is created without tools (useful for testing).
        models: Optional pre-created model instances. If not provided,
                models are created from config.

    Returns:
        A configured Strands Agent instance.

    Raises:
        ValueError: If agent_name is not recognised.
    """
    if agent_name not in _AGENT_CREATORS:
        raise ValueError(
            f"Unknown agent: '{agent_name}'. "
            f"Valid agents: {sorted(_AGENT_CREATORS.keys())}"
        )

    if models is None:
        models = _create_models(config)

    creator_fn, _ = _AGENT_CREATORS[agent_name]

    # All agents currently use opus
    model = models["opus"]

    logger.info("Creating agent '%s' via module factory", agent_name)

    return creator_fn(model=model, tools=tools)


def create_agents(
    config: OMAConfig,
    tools: dict[str, ToolCallable] | None = None,
) -> dict[str, Agent]:
    """Create all 9 OMA agents with correct models and tools.

    This is the main entry point for initialising the full agent ensemble.
    Each agent is created by its own module's create function.

    Args:
        config: OMA configuration containing Bedrock settings.
        tools: Dict mapping tool name to callable. Tools are matched to
               agents by name. Missing tools are logged as warnings.

    Returns:
        Dict mapping agent name to configured Strands Agent instance.

    Example:
        ```python
        from mysql.agents.factory import create_agents, OMAConfig, BedrockConfig

        config = OMAConfig(
            bedrock=BedrockConfig(region="ap-northeast-2"),
            oracle_schema="HR",
        )

        # tools would be your actual MCP tool implementations
        tools = {
            "oracle_query": oracle_query_tool,
            "oracle_get_ddl": oracle_get_ddl_tool,
            # ... etc
        }

        agents = create_agents(config, tools)

        # Use individual agents
        discovery_result = agents["discovery"]("Analyse the HR schema")
        ```
    """
    models = _create_models(config)
    agents: dict[str, Agent] = {}

    # Resolve oracle schema from config or env var
    oracle_schema = (
        config.oracle_schema
        or os.environ.get("ORACLE_USER", "oracle_schema")
    ).upper()

    for agent_name, (creator_fn, _) in _AGENT_CREATORS.items():
        try:
            agents[agent_name] = creator_fn(model=models["opus"], tools=tools)
            # Replace hardcoded "oracle_schema" in system prompts with actual schema
            if oracle_schema != "oracle_schema" and hasattr(agents[agent_name], "system_prompt"):
                agents[agent_name].system_prompt = agents[agent_name].system_prompt.replace(
                    '"oracle_schema"', f'"{oracle_schema}"'
                ).replace(
                    "'oracle_schema'", f"'{oracle_schema}'"
                ).replace(
                    "schema oracle_schema", f"schema {oracle_schema}"
                ).replace(
                    "schema=oracle_schema", f"schema={oracle_schema}"
                )
            logger.info("Created agent '%s'", agent_name)
        except Exception:
            logger.exception("Failed to create agent '%s'", agent_name)
            raise

    logger.info(
        "Created %d agents: %s",
        len(agents),
        ", ".join(sorted(agents.keys())),
    )

    return agents


def get_agent_info() -> dict[str, dict[str, Any]]:
    """Return metadata about all registered agents.

    Useful for debugging and documentation.

    Returns:
        Dict mapping agent name to its specification metadata.
    """
    return {
        name: {
            "tool_count": len(tool_names),
            "tool_names": list(tool_names),
        }
        for name, (_, tool_names) in _AGENT_CREATORS.items()
    }


# Backward compatibility: AGENT_SPECS equivalent
AGENT_SPECS = {
    name: {"tool_names": list(tool_names)}
    for name, (_, tool_names) in _AGENT_CREATORS.items()
}
