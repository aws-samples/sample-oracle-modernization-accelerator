"""Evaluator Agent -- 5-dimension quality assessment and Go/No-Go verdict.

The Evaluator Agent is the quality gatekeeper for the entire migration.
It scores the migration across 5 dimensions and produces a GO, CONDITIONAL,
or NO_GO verdict.
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
You are the **Evaluator Agent** -- the quality gatekeeper for the entire
Oracle-to-PostgreSQL migration.

While the QA Verifier checks "does each piece work correctly?", YOU judge
"is this migration ready for production?"

## 5-Dimension Evaluation

### 1. COVERAGE (Weight: 25%)
Score 0-100: What percentage of objects were successfully transformed?
- Count source objects vs successfully converted objects
- Check for orphaned objects in the dependency graph
- Include application SQL (MyBatis, Java, HQL) in coverage
- Deduct points for any CRITICAL-complexity objects that failed

### 2. EQUIVALENCE (Weight: 30%)
Score 0-100: Do transformed objects preserve business logic semantics?
- Cross-reference QA Verifier pass/fail rates
- Check for silent failures (objects that "pass" syntax but produce
  different results)
- Verify NULL handling: Oracle '' = NULL preserved?
- Verify date/time: Oracle DATE (with time) -> PG TIMESTAMP correct?
- Verify numeric precision: no silent truncation?
- Verify string comparison: case sensitivity aligned?
- Verify sort order: NLS_SORT vs PG collation?
- Verify transaction isolation alignment?

### 3. PERFORMANCE (Weight: 20%)
Score 0-100: Will the target system perform comparably?
- Compare EXPLAIN ANALYZE plans for top queries
- Check index utilisation (no unexpected full table scans)
- Verify partition pruning works on target
- Check bulk operation performance within 2x of source
- Assess connection pooling compatibility

### 4. SECURITY (Weight: 15%)
Score 0-100: Are security controls properly migrated?
- User/role mapping complete?
- GRANT statements converted?
- Row-Level Security (Oracle VPD -> PG RLS) converted?
- Column-level encryption handled?
- Application-level authentication compatible?

### 5. OPERATIONAL (Weight: 10%)
Score 0-100: Is the target system operationally ready?
- Monitoring queries converted?
- Backup/restore procedures documented?
- Rollback plan exists?
- Connection string migration plan?
- Alerting thresholds calibrated?

## Scoring Algorithm

```
readiness_score = (
    coverage * 0.25 +
    equivalence * 0.30 +
    performance * 0.20 +
    security * 0.15 +
    operational * 0.10
)
```

## Verdict Rules

| Condition                                    | Verdict     |
|----------------------------------------------|-------------|
| readiness_score >= 85 AND no CRITICAL fails  | GO          |
| readiness_score >= 70 AND < 85               | CONDITIONAL |
| readiness_score < 70 OR any CRITICAL fail    | NO_GO       |

- **GO** (>=85): Approve for production. Document minor risks.
- **CONDITIONAL** (70-84): Human review required. List specific risk items
  and conditions that must be met before proceeding.
- **NO_GO** (<70): Remediation required. Provide specific improvement plan
  with prioritised remediation targets.

## Tools Available

- `compute_coverage_score` -- Calculate coverage from inventory vs converted
- `compute_equivalence_score` -- Calculate equivalence from QA results

## Output Format

Return an EvaluationResult:
```json
{
  "timestamp": "...",
  "scores": {
    "coverage": N,
    "equivalence": N,
    "performance": N,
    "security": N,
    "operational": N
  },
  "readiness_score": N.N,
  "verdict": "GO|CONDITIONAL|NO_GO",
  "confidence": 0.0-1.0,
  "critical_findings": [...],
  "risk_register": [...],
  "remediation_targets": [
    {"object_id": "...", "issue": "...", "priority": "HIGH|MEDIUM|LOW",
     "estimated_effort": "...",
     "specific_fix": "At LINE 15, remove COMMIT inside BEGIN..END block and wrap with BEGIN...EXCEPTION WHEN OTHERS THEN RAISE",
     "root_cause": "Oracle autonomous transaction pattern not converted to PG savepoint pattern"}
  ]
}

## Actionable Remediation Guidance (Reflection)

When verdict is NO_GO or CONDITIONAL, you MUST provide SPECIFIC fix instructions
for each remediation target — not just "this object failed". The Remediation Agent
needs precise, actionable directives:

- BAD: "sp_process_order has errors"
- GOOD: "sp_process_order LINE 42: Replace `COMMIT` with savepoint pattern.
  LINE 58: Convert `DBMS_OUTPUT.PUT_LINE` to `RAISE NOTICE '%', msg`.
  LINE 73: Add `EXCEPTION WHEN OTHERS THEN` block around dynamic SQL."

Include:
- Exact line numbers or SQL fragments where the issue occurs
- The specific Oracle construct that was incorrectly converted
- The correct PostgreSQL replacement pattern
- Why the original conversion failed (root cause)
```

## CRITICAL: Pipeline Context

This evaluation happens BEFORE data migration. Data migration is handled by
a separate Data Migrator agent in the next pipeline stage.

Therefore:
- Do NOT penalize for "zero data migration" or "empty PG tables"
- Do NOT require data to be present for equivalence verification
- Focus on SCHEMA conversion quality: DDL, constraints, indexes, sequences, procedures
- Evaluate equivalence based on SYNTAX correctness and STRUCTURAL fidelity
- Performance scoring should be based on index strategy and query plan analysis,
  not on data-dependent benchmarks

## Verdict Rules (Adjusted for Schema-Only Phase)

| Condition                                    | Verdict     |
|----------------------------------------------|-------------|
| readiness_score >= 70 AND no CRITICAL fails  | GO          |
| readiness_score >= 50 AND < 70               | CONDITIONAL |
| readiness_score < 50 OR any CRITICAL fail    | NO_GO       |

- **GO** (>=70): Schema conversion approved. Proceed to data migration.
- **CONDITIONAL** (50-69): Minor issues exist but acceptable. Proceed with caution.
- **NO_GO** (<50): Serious schema issues. Remediation required.

## Constraints

- MUST base scores on EVIDENCE, not assumptions.
- MUST cross-reference QA results with discovery inventory for coverage gaps.
- MUST NOT penalize for missing data -- data migration is a later stage.
- MUST NOT inflate scores to appear positive.
- MUST NOT ignore edge cases or low-probability risks.
- MUST NOT issue GO verdict without checking all 5 dimensions.
- MUST NOT make subjective quality judgments without quantitative backing.
- Use extended thinking for complex scoring decisions to ensure transparency
  in your reasoning.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "compute_coverage_score",
    "compute_equivalence_score",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_evaluator_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Evaluator Agent instance.

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
                    "Tool '%s' not found for evaluator agent -- skipping",
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

class MigrationVerdict(str, Enum):
    """Final migration readiness verdict."""

    GO = "GO"
    CONDITIONAL = "CONDITIONAL"
    NO_GO = "NO_GO"


class RiskProbability(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskImpact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""

    dimension: str
    score: float  # 0-100
    weight: float
    findings: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass
class CriticalFinding:
    """A critical finding that may override the score-based verdict."""

    dimension: str
    finding: str
    impact: str
    recommendation: str
    severity: str = "CRITICAL"


@dataclass
class RiskEntry:
    """An entry in the risk register."""

    risk_id: str
    category: str
    description: str
    probability: RiskProbability
    impact: RiskImpact
    mitigation: str


@dataclass
class RemediationTarget:
    """A specific object or issue that needs remediation."""

    object_id: str
    issue: str
    priority: str  # HIGH, MEDIUM, LOW
    estimated_effort: str


@dataclass
class EvaluationResult:
    """Complete output of the Evaluator Agent."""

    timestamp: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    dimension_details: list[DimensionScore] = field(default_factory=list)
    readiness_score: float = 0.0
    verdict: MigrationVerdict = MigrationVerdict.NO_GO
    confidence: float = 0.0
    critical_findings: list[CriticalFinding] = field(default_factory=list)
    risk_register: list[RiskEntry] = field(default_factory=list)
    remediation_targets: list[RemediationTarget] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "scores": self.scores,
            "readiness_score": self.readiness_score,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "critical_findings": [
                {
                    "dimension": f.dimension,
                    "finding": f.finding,
                    "impact": f.impact,
                    "recommendation": f.recommendation,
                    "severity": f.severity,
                }
                for f in self.critical_findings
            ],
            "risk_register": [
                {
                    "id": r.risk_id,
                    "category": r.category,
                    "description": r.description,
                    "probability": r.probability.value,
                    "impact": r.impact.value,
                    "mitigation": r.mitigation,
                }
                for r in self.risk_register
            ],
            "remediation_targets": [
                {
                    "object_id": t.object_id,
                    "issue": t.issue,
                    "priority": t.priority,
                    "estimated_effort": t.estimated_effort,
                }
                for t in self.remediation_targets
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------------------------

# Dimension weights as defined in the specification
DIMENSION_WEIGHTS: dict[str, float] = {
    "coverage": 0.25,
    "equivalence": 0.30,
    "performance": 0.20,
    "security": 0.15,
    "operational": 0.10,
}


def calculate_readiness_score(scores: dict[str, float]) -> float:
    """Calculate weighted readiness score from dimension scores.

    Args:
        scores: Dict mapping dimension name to score (0-100).

    Returns:
        Weighted average score (0-100).
    """
    total = sum(
        scores.get(dim, 0.0) * weight
        for dim, weight in DIMENSION_WEIGHTS.items()
    )
    return round(total, 1)


def determine_verdict(
    score: float,
    critical_findings: list[CriticalFinding] | None = None,
) -> MigrationVerdict:
    """Determine migration verdict from score and critical findings.

    Rules:
    - Any CRITICAL severity finding -> NO_GO (overrides score)
    - score >= 85 -> GO
    - score >= 70 -> CONDITIONAL
    - score < 70 -> NO_GO

    Args:
        score: The weighted readiness score (0-100).
        critical_findings: Optional list of critical findings.

    Returns:
        The migration verdict.
    """
    if critical_findings:
        has_critical = any(
            f.severity == "CRITICAL" for f in critical_findings
        )
        if has_critical:
            return MigrationVerdict.NO_GO

    if score >= 85:
        return MigrationVerdict.GO
    if score >= 70:
        return MigrationVerdict.CONDITIONAL
    return MigrationVerdict.NO_GO


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------

def parse_evaluation_result(agent_output: str) -> EvaluationResult:
    """Parse JSON output from the Evaluator Agent."""
    result = EvaluationResult()

    try:
        data = json.loads(agent_output)
    except json.JSONDecodeError:
        logger.warning("Could not parse Evaluator output as JSON")
        return result

    result.timestamp = data.get("timestamp", "")
    result.scores = data.get("scores", {})
    result.readiness_score = data.get("readiness_score", 0.0)

    verdict_str = data.get("verdict", "NO_GO")
    try:
        result.verdict = MigrationVerdict(verdict_str)
    except ValueError:
        result.verdict = MigrationVerdict.NO_GO

    result.confidence = data.get("confidence", 0.0)

    for f_data in data.get("critical_findings", []):
        result.critical_findings.append(CriticalFinding(
            dimension=f_data.get("dimension", ""),
            finding=f_data.get("finding", ""),
            impact=f_data.get("impact", ""),
            recommendation=f_data.get("recommendation", ""),
            severity=f_data.get("severity", "CRITICAL"),
        ))

    for r_data in data.get("risk_register", []):
        result.risk_register.append(RiskEntry(
            risk_id=r_data.get("id", ""),
            category=r_data.get("category", ""),
            description=r_data.get("description", ""),
            probability=RiskProbability(r_data.get("probability", "MEDIUM")),
            impact=RiskImpact(r_data.get("impact", "MEDIUM")),
            mitigation=r_data.get("mitigation", ""),
        ))

    for t_data in data.get("remediation_targets", []):
        result.remediation_targets.append(RemediationTarget(
            object_id=t_data.get("object_id", ""),
            issue=t_data.get("issue", ""),
            priority=t_data.get("priority", "MEDIUM"),
            estimated_effort=t_data.get("estimated_effort", ""),
        ))

    return result


def build_evaluation_task(
    discovery_report_json: str,
    qa_report_json: str,
    transform_summary_json: str = "",
) -> str:
    """Build the user prompt sent to the Evaluator Agent.

    Args:
        discovery_report_json: JSON output from Discovery Agent.
        qa_report_json: JSON output from QA Verifier Agent.
        transform_summary_json: Optional summary from Code Migrator.

    Returns:
        A formatted task string for the agent.
    """
    parts = [
        "Evaluate the Oracle-to-PostgreSQL migration readiness.",
        "",
        "Score across 5 dimensions:",
        "1. COVERAGE (25%): Objects successfully transformed vs total.",
        "2. EQUIVALENCE (30%): Semantic correctness from QA results.",
        "3. PERFORMANCE (20%): Query plan comparison and benchmarks.",
        "4. SECURITY (15%): Permission and RLS migration completeness.",
        "5. OPERATIONAL (10%): Monitoring, backup, rollback readiness.",
        "",
        "Verdict rules:",
        "- GO (>=85, no CRITICAL failures): Approve for production.",
        "- CONDITIONAL (70-84): Human review required.",
        "- NO_GO (<70 or CRITICAL failure): Remediation required.",
        "",
        "Discovery Report:",
        f"```json\n{discovery_report_json}\n```",
        "",
        "QA Report:",
        f"```json\n{qa_report_json}\n```",
    ]

    if transform_summary_json:
        parts.extend([
            "",
            "Transform Summary:",
            f"```json\n{transform_summary_json}\n```",
        ])

    parts.extend([
        "",
        "Return the EvaluationResult as JSON.",
    ])

    return "\n".join(parts)
