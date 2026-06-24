"""Remediation Agent -- Fixes failed conversions using error context.

The Remediation Agent is the self-healing mechanism of the migration
pipeline. It receives failed conversions from the QA Verifier and
Evaluator, applies fix strategies in priority order, and stores
successful fix patterns for future reuse.
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


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the **Remediation Agent** for Oracle-to-MySQL migration.

Your mission is to fix migration issues identified by the QA Verifier and
Evaluator agents. You are the self-healing mechanism of the migration
pipeline.

## Fix Strategy Priority (apply in order)

### 1. PATTERN_MATCH
- Check pattern memory for known fix patterns.
- If a matching pattern exists with success_rate > 0.8, apply immediately.
- This is the fastest path -- no LLM reasoning needed.

### 2. RECONVERT_STRICT
- Re-run the Code Migrator with strict mode enabled.
- Provide the specific error message as additional context.
- Useful when the original conversion missed a construct.

### 3. RECONVERT_WITH_ERROR
- Re-run conversion with the full error context:
  - Original Oracle SQL
  - Failed MySQL conversion
  - Exact error message from PG
  - Stack trace if available
- The error context often reveals the exact fix needed.

### 4. DEPENDENCY_REORDER
- If the error is "relation/function does not exist", the issue may be
  dependency ordering.
- Reorder the DDL execution sequence using the dependency graph.
- Re-execute in correct order.

### 5. ESCALATE
- After 3 failed attempts on the same object, STOP and escalate.
- Provide full context: original SQL, all attempted conversions,
  all error messages, analysis of why fixes failed.
- Mark the object as REQUIRES_HUMAN_REVIEW.

## Fix Pattern Categories

| Category          | Example Error                                      | Strategy          |
|-------------------|----------------------------------------------------|-------------------|
| SYNTAX            | "syntax error at or near..."                       | Parse position    |
| TYPE_MISMATCH     | "column X is of type integer but expression text"  | Add explicit CAST |
| NULL_BEHAVIOR     | Empty string treated as non-null in PG             | Add NULLIF        |
| DATE_FORMAT       | "date format not recognized"                       | Fix format string |
| FUNCTION_MISSING  | "function DECODE does not exist"                   | CASE expression   |
| SEQUENCE          | "currval not yet defined in this session"          | Restructure usage |
| CURSOR            | "cursor already open"                              | Add IF NOT FOUND  |
| PERMISSION        | "permission denied for table..."                   | GRANT statement   |

## For Each Fix (Reflection Loop)

1. **Diagnose**: Explain WHY the original transformation failed.
2. **Fix**: Make the MINIMAL change needed. Do not rewrite entire procedures.
3. **Self-verify (Reflection)**: Before submitting the fix:
   - Re-read the fixed SQL and mentally execute it against the error scenario
   - Check: Does this fix ONLY the reported issue without breaking other parts?
   - Check: Is the fix semantically equivalent to the Oracle original?
   - Check: Did the fix introduce any new Oracle-isms or PG anti-patterns?
   - If the fix looks wrong, iterate — do NOT submit a known-bad fix
4. **Verify**: Execute the fix via `pg_syntax_check` or `pg_execute_ddl` to confirm.
5. **Record**: If fix works, save the pattern for future use:
   ```json
   {
     "pattern_id": "FIX-YYYY-NNNN",
     "oracle_pattern": "...",
     "error_type": "...",
     "fix_applied": "...",
     "success_rate": 1.0,
     "applied_count": 1
   }
   ```

## Knowledge Lookup Strategy (3-tier)

When diagnosing and fixing errors:
1. **Static rules first**: Call `oracle_to_pg_reference` with the specific pattern
2. **RAG fallback**: If static rules don't cover the pattern, call
   `search_conversion_knowledge` for dynamic knowledge retrieval
3. **Learn**: After a successful fix, call `store_learned_pattern` to save the
   pattern for future runs (learning loop)

## Tools Available

- `oracle_get_ddl` -- Get original Oracle DDL for reference
- `oracle_get_source` -- Get Oracle PL/SQL source code
- `pg_execute_ddl` -- Execute corrected DDL on MySQL
- `pg_syntax_check` -- Validate syntax before execution
- `oracle_to_pg_reference` -- Look up conversion rules by category
- `search_conversion_knowledge` -- RAG search for patterns not in static rules
- `store_learned_pattern` -- Save successful fixes for future reuse

## Output Format

Return a RemediationLog:
```json
{
  "total_issues": N,
  "fixed": N,
  "failed": N,
  "escalated": N,
  "fixes": [
    {
      "object_id": "...",
      "issue": "...",
      "strategy_used": "pattern_match|reconvert_strict|...",
      "attempts": N,
      "status": "FIXED|FAILED|ESCALATED",
      "fix_details": {
        "before": "...",
        "after": "...",
        "explanation": "..."
      },
      "pattern_stored": true|false
    }
  ]
}
```

## Constraints

- MUST make minimal changes (do not rewrite entire procedures).
- MUST preserve all existing passing tests.
- MUST document every change with rationale.
- MUST respect the 3-attempt limit per object.
- MUST NOT change business logic to "make tests pass".
- MUST NOT introduce MySQL-specific features that break portability
  (unless the Oracle original already used Oracle-specific features).
- MUST NOT skip pattern storage for successful fixes.
- MUST NOT continue past 3 attempts without escalation.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "dms_sc_verify_target",
    "oracle_get_ddl",
    "oracle_get_source",
    "oracle_get_table_columns",
    "oracle_get_constraints",
    "pg_execute_ddl",
    "pg_syntax_check",
    "apply_static_rules",
    "oracle_to_pg_reference",
    "search_conversion_knowledge",
    "store_learned_pattern",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_remediation_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Remediation Agent instance.

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
                    "Tool '%s' not found for remediation agent -- skipping",
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

class RemediationStrategy(str, Enum):
    """Fix strategy in priority order."""

    PATTERN_MATCH = "pattern_match"
    RECONVERT_STRICT = "reconvert_strict"
    RECONVERT_WITH_ERROR = "reconvert_with_error"
    DEPENDENCY_REORDER = "dependency_reorder"
    ESCALATE = "escalate"


class FixStatus(str, Enum):
    """Status of a remediation attempt."""

    FIXED = "FIXED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


@dataclass
class FixPattern:
    """A reusable fix pattern stored in pattern memory."""

    pattern_id: str
    oracle_pattern: str
    error_type: str
    fix_applied: str
    success_rate: float = 1.0
    applied_count: int = 1
    first_seen: str = ""
    last_used: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "oracle_pattern": self.oracle_pattern,
            "error_type": self.error_type,
            "fix_applied": self.fix_applied,
            "success_rate": self.success_rate,
            "applied_count": self.applied_count,
            "first_seen": self.first_seen,
            "last_used": self.last_used,
        }


@dataclass
class FixDetail:
    """Details of a single fix applied to an object."""

    before: str = ""
    after: str = ""
    explanation: str = ""


@dataclass
class RemediationEntry:
    """Result of remediating a single failed object."""

    object_id: str
    issue: str
    strategy_used: RemediationStrategy = RemediationStrategy.ESCALATE
    attempts: int = 0
    status: FixStatus = FixStatus.FAILED
    fix_details: FixDetail = field(default_factory=FixDetail)
    pattern_stored: bool = False
    escalation_context: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "object_id": self.object_id,
            "issue": self.issue,
            "strategy_used": self.strategy_used.value,
            "attempts": self.attempts,
            "status": self.status.value,
            "fix_details": {
                "before": self.fix_details.before,
                "after": self.fix_details.after,
                "explanation": self.fix_details.explanation,
            },
            "pattern_stored": self.pattern_stored,
        }
        if self.status == FixStatus.ESCALATED:
            result["escalation_context"] = self.escalation_context
        return result


@dataclass
class RemediationLog:
    """Complete output of the Remediation Agent."""

    total_issues: int = 0
    fixed: int = 0
    failed: int = 0
    escalated: int = 0
    fixes: list[RemediationEntry] = field(default_factory=list)

    def add_entry(self, entry: RemediationEntry) -> None:
        self.fixes.append(entry)
        self.total_issues += 1
        if entry.status == FixStatus.FIXED:
            self.fixed += 1
        elif entry.status == FixStatus.ESCALATED:
            self.escalated += 1
        else:
            self.failed += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_issues": self.total_issues,
            "fixed": self.fixed,
            "failed": self.failed,
            "escalated": self.escalated,
            "fixes": [f.to_dict() for f in self.fixes],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

# Maps MySQL error patterns to fix categories
ERROR_PATTERN_CATEGORIES: dict[str, str] = {
    "syntax error": "SYNTAX",
    "type .* but expression is of type": "TYPE_MISMATCH",
    "function .* does not exist": "FUNCTION_MISSING",
    "relation .* does not exist": "DEPENDENCY",
    "column .* does not exist": "COLUMN_MISSING",
    "permission denied": "PERMISSION",
    "date/time field value out of range": "DATE_FORMAT",
    "invalid input syntax": "TYPE_MISMATCH",
    "currval .* not yet defined": "SEQUENCE",
    "cursor .* already open": "CURSOR",
    "division by zero": "LOGIC",
}

MAX_ATTEMPTS_PER_OBJECT = 3


def classify_error(error_message: str) -> str:
    """Classify a MySQL error message into a fix category.

    Args:
        error_message: The error message from MySQL.

    Returns:
        The error category string.
    """
    import re

    error_lower = error_message.lower()
    for pattern, category in ERROR_PATTERN_CATEGORIES.items():
        if re.search(pattern, error_lower):
            return category
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------

def parse_remediation_log(agent_output: str) -> RemediationLog:
    """Parse JSON output from the Remediation Agent."""
    log = RemediationLog()

    try:
        data = json.loads(agent_output)
    except json.JSONDecodeError:
        logger.warning("Could not parse Remediation Agent output as JSON")
        return log

    log.total_issues = data.get("total_issues", 0)
    log.fixed = data.get("fixed", 0)
    log.failed = data.get("failed", 0)
    log.escalated = data.get("escalated", 0)

    for fix_data in data.get("fixes", []):
        strategy_str = fix_data.get("strategy_used", "escalate")
        try:
            strategy = RemediationStrategy(strategy_str)
        except ValueError:
            strategy = RemediationStrategy.ESCALATE

        status_str = fix_data.get("status", "FAILED")
        try:
            status = FixStatus(status_str)
        except ValueError:
            status = FixStatus.FAILED

        fix_details_data = fix_data.get("fix_details", {})

        log.fixes.append(RemediationEntry(
            object_id=fix_data.get("object_id", ""),
            issue=fix_data.get("issue", ""),
            strategy_used=strategy,
            attempts=fix_data.get("attempts", 0),
            status=status,
            fix_details=FixDetail(
                before=fix_details_data.get("before", ""),
                after=fix_details_data.get("after", ""),
                explanation=fix_details_data.get("explanation", ""),
            ),
            pattern_stored=fix_data.get("pattern_stored", False),
            escalation_context=fix_data.get("escalation_context", ""),
        ))

    return log


def build_remediation_task(
    object_id: str,
    original_sql: str,
    converted_sql: str,
    error_message: str,
    attempt_number: int = 1,
    previous_attempts: list[dict[str, Any]] | None = None,
) -> str:
    """Build the user prompt for remediating a failed conversion.

    Args:
        object_id: Identifier for the failed object.
        original_sql: The original Oracle SQL.
        converted_sql: The failed MySQL conversion.
        error_message: The error from MySQL execution.
        attempt_number: Current attempt number (1-3).
        previous_attempts: Optional history of previous fix attempts.

    Returns:
        A formatted task string for the agent.
    """
    parts = [
        f"Fix the failed conversion for object '{object_id}'.",
        f"This is attempt {attempt_number} of {MAX_ATTEMPTS_PER_OBJECT}.",
        "",
        "Fix Strategy Priority:",
        "1. PATTERN_MATCH: Check pattern memory for known fixes.",
        "2. RECONVERT_STRICT: Re-convert with error context.",
        "3. RECONVERT_WITH_ERROR: Full error-guided reconversion.",
        "4. DEPENDENCY_REORDER: If dependency ordering issue.",
        "5. ESCALATE: After 3 failed attempts.",
        "",
        "Original Oracle SQL:",
        "```sql",
        original_sql,
        "```",
        "",
        "Failed MySQL Conversion:",
        "```sql",
        converted_sql,
        "```",
        "",
        "MySQL Error:",
        "```",
        error_message,
        "```",
    ]

    if previous_attempts:
        parts.extend([
            "",
            "Previous Attempts:",
            f"```json\n{json.dumps(previous_attempts, indent=2)}\n```",
        ])

    parts.extend([
        "",
        "Requirements:",
        "- Make MINIMAL changes to fix the specific error.",
        "- Do NOT rewrite the entire SQL.",
        "- Preserve business logic exactly.",
        "- If fix works, provide pattern for storage.",
        f"- If this is attempt {MAX_ATTEMPTS_PER_OBJECT}, ESCALATE with full context.",
        "",
        "Return the RemediationEntry as JSON.",
    ])

    return "\n".join(parts)
