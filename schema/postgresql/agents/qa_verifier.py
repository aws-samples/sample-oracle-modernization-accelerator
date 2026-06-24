"""QA Verifier Agent -- Verifies transformed SQL produces identical results.

The QA Verifier Agent tests each converted SQL by executing it on both
Oracle and PostgreSQL databases and comparing results at multiple levels:
syntax, execution, result comparison, and edge cases.
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
You are the **QA Verifier Agent** for Oracle-to-PostgreSQL migration.

Your mission is to verify that transformed code produces identical results
to the original Oracle code. You are the quality gate that prevents
incorrect conversions from reaching production.

## Verification Levels

For each converted object, run ALL verification levels in order:

### Level 1: SYNTAX
- Parse the converted SQL on the target PostgreSQL database.
- Check for syntax errors, missing aliases, type mismatches.
- Use `pg_syntax_check` to validate without executing.

### Level 2: EXECUTION
- Execute the converted SQL/procedure with test parameters.
- Verify it runs without runtime errors (no missing functions,
  no type cast failures, no permission issues).

### Level 3: RESULT
- Execute both original (Oracle) and converted (PostgreSQL) versions
  with identical input parameters.
- Compare result sets row-by-row (ORDER-INDEPENDENT comparison).
- Check column count, column types, row count, and actual values.
- Pay special attention to:
  - DATE/TIMESTAMP formatting differences
  - Numeric precision (Oracle NUMBER vs PG NUMERIC)
  - NULL vs empty string handling
  - Sort order (Oracle NLS_SORT vs PG collation)

### Level 4: EDGE_CASE
- Generate edge case test data automatically:
  - NULL values in all nullable columns
  - Empty strings (critical for Oracle '' = NULL difference)
  - Boundary values (MAX_INT, very long strings, dates at epoch)
  - Special characters in string fields
  - Zero-row result sets
- Run comparison with edge case data.

## Reporting

For each object, report:
- **PASS**: All levels passed.
- **FAIL**: Which level failed + exact error + expected vs actual.
- **SKIP**: Cannot verify (with reason -- e.g., no test data, external dependency).

## Tools Available

- `execute_sql_comparison` -- Execute SQL on both Oracle and PG, compare results
- `generate_bind_variables` -- Auto-generate bind variables from schema metadata
- `pg_explain` -- Run EXPLAIN ANALYZE on PG query (for performance baseline)
- `pg_syntax_check` -- Validate SQL syntax without execution

## Output Format

Return a QAReport:
```json
{
  "summary": {"total": N, "passed": N, "failed": N, "skipped": N},
  "results": [
    {
      "object_id": "...",
      "levels": {
        "syntax": {"result": "PASS|FAIL", "detail": "..."},
        "execution": {"result": "PASS|FAIL", "detail": "..."},
        "result_comparison": {"result": "PASS|FAIL", "detail": "...",
          "oracle_rows": N, "pg_rows": N, "differences": [...]},
        "edge_case": {"result": "PASS|FAIL|SKIP", "detail": "..."}
      },
      "overall": "PASS|FAIL|SKIP",
      "root_cause": "...",
      "suggested_fix": "..."
    }
  ],
  "regression_suite": [...]
}
```

## Constraints

- You MUST NOT modify transformed code -- that is the Remediation Agent's job.
- You MUST NOT skip verification because something "looks correct".
- You MUST NOT approve partial results.
- You MUST test with representative data, not just empty tables.
- You MUST save passing tests as regression test suite for future use.
- Be precise in error reporting: include line numbers, expected vs actual
  values, and root cause analysis.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "execute_sql_comparison",
    "functional_test_sql",
    "generate_bind_variables",
    "mybatis_validate_xml",
    "pg_explain",
    "pg_syntax_check",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_qa_verifier_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured QA Verifier Agent instance.

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
                    "Tool '%s' not found for qa_verifier agent -- skipping",
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

class VerificationLevel(str, Enum):
    """Verification levels in order of depth."""

    SYNTAX = "SYNTAX"
    EXECUTION = "EXECUTION"
    RESULT = "RESULT"
    EDGE_CASE = "EDGE_CASE"


class VerificationResult(str, Enum):
    """Result of a single verification level."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class LevelResult:
    """Result for a single verification level."""

    level: VerificationLevel
    result: VerificationResult
    detail: str = ""
    oracle_rows: int | None = None
    pg_rows: int | None = None
    differences: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ObjectQAResult:
    """Complete QA result for a single converted object."""

    object_id: str
    levels: dict[str, LevelResult] = field(default_factory=dict)
    overall: VerificationResult = VerificationResult.SKIP
    root_cause: str = ""
    suggested_fix: str = ""

    def set_level_result(self, level_result: LevelResult) -> None:
        """Set a verification level result and update overall status."""
        self.levels[level_result.level.value.lower()] = level_result

        # Overall is FAIL if any level fails, PASS if all pass,
        # SKIP if any are skipped and none failed.
        has_fail = any(
            lr.result == VerificationResult.FAIL
            for lr in self.levels.values()
        )
        all_pass = all(
            lr.result == VerificationResult.PASS
            for lr in self.levels.values()
        )

        if has_fail:
            self.overall = VerificationResult.FAIL
        elif all_pass and len(self.levels) == len(VerificationLevel):
            self.overall = VerificationResult.PASS
        elif all_pass:
            self.overall = VerificationResult.PASS
        else:
            self.overall = VerificationResult.SKIP

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "levels": {
                name: {
                    "result": lr.result.value,
                    "detail": lr.detail,
                    **({"oracle_rows": lr.oracle_rows} if lr.oracle_rows is not None else {}),
                    **({"pg_rows": lr.pg_rows} if lr.pg_rows is not None else {}),
                    **({"differences": lr.differences} if lr.differences else {}),
                }
                for name, lr in self.levels.items()
            },
            "overall": self.overall.value,
            "root_cause": self.root_cause,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class QAReport:
    """Complete output of the QA Verifier Agent."""

    summary: dict[str, int] = field(default_factory=dict)
    results: list[ObjectQAResult] = field(default_factory=list)
    regression_suite: list[dict[str, Any]] = field(default_factory=list)

    def add_result(self, result: ObjectQAResult) -> None:
        self.results.append(result)
        self._update_summary()

    def _update_summary(self) -> None:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.overall == VerificationResult.PASS)
        failed = sum(1 for r in self.results if r.overall == VerificationResult.FAIL)
        skipped = sum(1 for r in self.results if r.overall == VerificationResult.SKIP)
        self.summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    def get_failed_objects(self) -> list[ObjectQAResult]:
        """Return all objects that failed verification."""
        return [r for r in self.results if r.overall == VerificationResult.FAIL]

    def to_dict(self) -> dict[str, Any]:
        self._update_summary()
        return {
            "summary": self.summary,
            "results": [r.to_dict() for r in self.results],
            "regression_suite": self.regression_suite,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------

def parse_qa_report(agent_output: str) -> QAReport:
    """Parse JSON output from the QA Verifier Agent."""
    report = QAReport()

    try:
        data = json.loads(agent_output)
    except json.JSONDecodeError:
        logger.warning("Could not parse QA Verifier output as JSON")
        return report

    report.summary = data.get("summary", {})

    for result_data in data.get("results", []):
        obj_result = ObjectQAResult(object_id=result_data.get("object_id", ""))

        for level_name, level_data in result_data.get("levels", {}).items():
            try:
                level_enum = VerificationLevel(level_name.upper())
            except ValueError:
                # Map common key names to enum values
                level_map = {
                    "syntax": VerificationLevel.SYNTAX,
                    "execution": VerificationLevel.EXECUTION,
                    "result_comparison": VerificationLevel.RESULT,
                    "result": VerificationLevel.RESULT,
                    "edge_case": VerificationLevel.EDGE_CASE,
                }
                level_enum = level_map.get(level_name.lower())
                if level_enum is None:
                    continue

            obj_result.set_level_result(LevelResult(
                level=level_enum,
                result=VerificationResult(level_data.get("result", "SKIP")),
                detail=level_data.get("detail", ""),
                oracle_rows=level_data.get("oracle_rows"),
                pg_rows=level_data.get("pg_rows"),
                differences=level_data.get("differences", []),
            ))

        obj_result.overall = VerificationResult(
            result_data.get("overall", "SKIP")
        )
        obj_result.root_cause = result_data.get("root_cause", "")
        obj_result.suggested_fix = result_data.get("suggested_fix", "")

        report.results.append(obj_result)

    report.regression_suite = data.get("regression_suite", [])

    return report


def build_qa_task(
    object_id: str,
    original_sql: str,
    converted_sql: str,
    bind_variables: dict[str, Any] | None = None,
) -> str:
    """Build the user prompt for QA verification of a single object.

    Args:
        object_id: Identifier for the object being verified.
        original_sql: The original Oracle SQL.
        converted_sql: The converted PostgreSQL SQL.
        bind_variables: Optional pre-generated bind variables for testing.

    Returns:
        A formatted task string for the agent.
    """
    parts = [
        f"Verify the conversion of object '{object_id}'.",
        "",
        "Run ALL verification levels:",
        "1. SYNTAX: Parse converted SQL on PostgreSQL.",
        "2. EXECUTION: Execute with test parameters.",
        "3. RESULT: Compare Oracle vs PostgreSQL results row-by-row.",
        "4. EDGE_CASE: Test with NULL, empty strings, boundary values.",
        "",
        "Original Oracle SQL:",
        "```sql",
        original_sql,
        "```",
        "",
        "Converted PostgreSQL SQL:",
        "```sql",
        converted_sql,
        "```",
    ]

    if bind_variables:
        parts.extend([
            "",
            "Pre-generated bind variables:",
            f"```json\n{json.dumps(bind_variables, indent=2)}\n```",
        ])

    parts.extend([
        "",
        "Return the QA result as JSON.",
    ])

    return "\n".join(parts)
