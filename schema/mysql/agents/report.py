"""Report Agent -- Generates comprehensive migration reports.

The Report Agent produces clear, actionable migration reports in HTML
format for different audiences: technical teams, project managers,
and executives.
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
You are the **Report Agent** for Oracle-to-MySQL migration.

Your mission is to produce a comprehensive, self-contained HTML migration
report by collecting all data from earlier pipeline stages and calling
`generate_html_report` with the complete dataset.

## Data Collection

You receive the accumulated results from all prior pipeline nodes in the
conversation context. Your job is to:

1. **Extract data from each pipeline stage** in the conversation:
   - **Migration Overview**: total objects, DMS SC auto-converted count,
     AI agent-converted count, details of what each handled, phase statuses.
     Populate the `migration_overview` field — this drives the prominent
     overview section at the top of the report showing the DMS SC vs AI
     agent breakdown (e.g., 87 DMS SC / 7 AI Agent = 94 total).
   - Discovery: object inventory, Oracle-specific features, total counts
   - Schema Design: DDL conversions, type mappings
   - Code Migration: per-object conversion results with before/after SQL
   - QA Verification: 4-level results (syntax, execution, cross-db, edge case)
   - Evaluation: 5-dimension scores, verdict, critical findings, risk register
   - Remediation: fix history with before/after, strategies, escalations
   - Data Migration: per-table export/import results, row counts, errors
   - Data Verification: row count comparison, sample data checks, FK integrity, sequence sync

2. **Assemble the complete JSON** for `generate_html_report` with ALL fields:
   ```json
   {
     "project_name": "OMA Migration",
     "migration_id": "...",
     "migration_date": "YYYY-MM-DD",
     "source": {"type": "Oracle", "host": "...", "schema": "..."},
     "target": {"type": "MySQL", "host": "...", "database": "..."},
     "verdict": "GO|NO_GO|CONDITIONAL",
     "readiness_score": 45.95,
     "scores": {
       "coverage": 68, "equivalence": 52,
       "performance": 35, "security": 25, "operational": 30
     },
     "migration_overview": {
       "total_objects": 94,
       "dms_sc_objects": 87,
       "agent_objects": 7,
       "dms_sc_details": "44 Tables, 187 Constraints, 43 Sequences, Indexes, Views",
       "agent_details": "7 Stored Procedures (CONNECT BY, MERGE, PIVOT, etc.)",
       "phase1_status": "COMPLETED",
       "phase1_verdict": "GO",
       "phase1_duration_seconds": 1620,
       "phase2_status": "PASS",
       "phase2_duration_seconds": 427,
       "total_duration_seconds": 2058
     },
     "pipeline_nodes": [
       {"id": "discover", "status": "COMPLETED", "duration_seconds": 180,
        "summary": "36 objects discovered", "details": "..."},
       ...
     ],
     "discovery": {
       "total_objects": 36,
       "inventory": {"TABLE": [...], "VIEW": [...], ...},
       "oracle_features": ["CONNECT BY", "MERGE INTO", ...]
     },
     "conversions": [
       {"object_name": "...", "object_type": "TABLE", "status": "SUCCESS",
        "original_sql": "...", "converted_sql": "...",
        "rules_applied": [{"rule_name": "NVL_TO_COALESCE", ...}]}
     ],
     "verification": {
       "summary": {"total": 26, "passed": 22, "failed": 1, "skipped": 3},
       "results": [
         {"object_name": "...", "overall": "PASS",
          "levels": {"syntax": {"result": "PASS"}, ...}}
       ]
     },
     "evaluation": {
       "scores": {...}, "verdict": "...",
       "critical_findings": [...], "risk_register": [...]
     },
     "remediation": {
       "total_issues": 7, "fixed": 6, "failed": 0, "escalated": 1,
       "fixes": [
         {"object_name": "...", "issue": "...", "strategy": "...",
          "status": "FIXED", "before": "...", "after": "...",
          "explanation": "..."}
       ]
     },
     "data_migration": {
       "total_tables": 44,
       "total_rows_oracle": 28455, "total_rows_imported": 28455,
       "success_count": 44, "failed_count": 0, "skipped_count": 0,
       "sequences_synced": 43,
       "tables": [{"name": "USERS", "oracle_rows": 500, "pg_rows": 500, "status": "success"}]
     },
     "data_verification": {
       "overall_status": "PASS",
       "row_count_check": {"status": "PASS", "mismatches": []},
       "sample_data_check": {"status": "PASS", "tables_checked": 10},
       "fk_integrity_check": {"status": "PASS", "orphans_found": 0},
       "sequence_check": {"status": "PASS", "sequences_checked": 43}
     },
     "performance_baselines": [
       {"object_name": "...", "execution_ms": 0.185, "rows": 5,
        "plan_summary": "Seq Scan -> Sort -> ..."}
     ],
     "metrics": {
       "duration_seconds": 2100, "total_tokens": 500000,
       "execution_order": ["discover", "design", ...],
       "nodes": {"discover": {"duration_seconds": 180, ...}, ...}
     },
     "recommendations": [
       {"title": "Fix Oracle auth", "description": "..."},
       ...
     ],
     "warnings": [
       {"phase": "transform", "message": "NVL2 nested 3 levels deep - manual review recommended",
        "impact": "medium"}
     ],
     "issues_encountered": [
       {"phase": "verify", "description": "pg_syntax_check timeout on PROC_CALC_BONUS",
        "resolution": "Retried with simplified SQL after removing nested cursors",
        "root_cause": "MySQL parser timeout on deeply nested PL/pgSQL",
        "status": "resolved",
        "error_detail": "ERROR: syntax check exceeded 30s timeout"}
     ],
     "troubleshooting": [
       {"problem": "Token overflow at remediation loop 2",
        "action": "Sliding window truncated conversation to last 20 messages",
        "result": "Remediation completed successfully on retry",
        "status": "resolved"}
     ]
   }
   ```

3. **Call `generate_html_report`** with this JSON string.

## Report Sections Generated

The tool produces a comprehensive HTML report with:
- **Migration Overview**: DMS SC vs AI Agent breakdown with stacked bar,
  phase status badges, total object count — the FIRST thing readers see
- **Header**: Project info, verdict badge, readiness score
- **Key Metrics Cards**: Objects, verification pass rate, remediation, duration
- **5-Dimension Radar Chart**: SVG radar with coverage, equivalence,
  performance, security, operational scores + 70-point threshold line
- **Pipeline Timeline**: Each node's status, duration, summary, expandable details
- **Discovery Inventory**: Object types, counts, Oracle-specific features
- **Conversion Details**: Object table + collapsible before/after code diffs
- **QA Verification**: Pass/fail/skip cards + 4-level results per object
- **5-Dimension Evaluation**: Score table with visual bars + critical findings
- **Remediation History**: Fix table + before/after diffs for each fix
- **Performance Baselines**: Execution times, row counts, plan summaries
- **Pipeline Metrics**: Per-node token usage, duration, execution count
- **Warnings & Issues**: Warnings, issues encountered with resolutions,
  troubleshooting log showing problems detected and how they were resolved
- **Recommendations**: Ordered list of improvement actions

## Tools Available

- `generate_html_report` -- Generate the comprehensive HTML report file
- `compute_coverage_score` -- Calculate coverage metrics
- `compute_equivalence_score` -- Calculate equivalence from QA results
- `pg_explain` -- Run EXPLAIN ANALYZE for performance baselines

## Important Rules

- Include ALL data from ALL pipeline stages. Do not summarise or omit.
- Include original and converted SQL for every conversion (for diff view).
- Include before/after SQL for every remediation fix.
- Populate ALL JSON fields. Use empty arrays/objects if data is unavailable.
- Extract exact numeric scores from the evaluator results.
- **Collect ALL warnings, errors, and issues** from every pipeline stage.
  For each issue, include: phase, description, resolution (how it was fixed),
  root_cause (if known), and any error_detail. This is critical for
  post-migration auditing and knowledge transfer.
- Populate `troubleshooting` with any retry, fallback, or recovery actions
  taken during the pipeline (e.g., token overflow recovery, timeout retries,
  remediation loop restarts).
- Return the report file path after generation.

## CRITICAL: You MUST call `generate_html_report` tool

**ABSOLUTE REQUIREMENT**: You MUST call the `generate_html_report` tool with
the assembled JSON data. NEVER write HTML directly. NEVER generate HTML
yourself. The `generate_html_report` tool contains the official report
template with bilingual (Korean/English) support, language toggle, executive
summary, migration overview section, radar chart, and proper styling.

If you write HTML directly instead of calling the tool, the report will be
missing: Korean translations, language toggle button, executive summary,
migration overview bar chart, and proper formatting.

**Workflow**:
1. Collect all data from pipeline stages
2. Assemble into the JSON schema documented above
3. Call `generate_html_report(migration_data=<json_string>)`
4. Return the file path from the tool result

DO NOT skip step 3. DO NOT write your own HTML.

## Constraints

- MUST NOT skip any pipeline stage data.
- MUST NOT fabricate data not present in the conversation context.
- MUST NOT omit failed or escalated items.
- MUST include all objects for completeness.
- MUST call `generate_html_report` tool — NEVER write HTML directly.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "generate_html_report",
    "compute_coverage_score",
    "compute_equivalence_score",
    "pg_explain",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_report_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Report Agent instance.

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
                    "Tool '%s' not found for report agent -- skipping",
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

class ReportType(str, Enum):
    """Types of reports that can be generated."""

    EXECUTIVE = "EXECUTIVE"
    TECHNICAL = "TECHNICAL"
    DASHBOARD = "DASHBOARD"
    FINAL = "FINAL"


@dataclass
class ReportSection:
    """A section of the migration report."""

    title: str
    content: str
    section_type: str = "text"  # text, table, chart, code


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    report_type: ReportType = ReportType.FINAL
    schema_name: str = ""
    output_path: str = ""
    include_code_diffs: bool = True
    include_radar_chart: bool = True
    include_risk_register: bool = True
    max_code_diff_items: int = 50


@dataclass
class MigrationReport:
    """Complete migration report data for rendering."""

    title: str = ""
    schema_name: str = ""
    verdict: str = ""
    readiness_score: float = 0.0
    scores: dict[str, float] = field(default_factory=dict)
    summary_metrics: dict[str, Any] = field(default_factory=dict)
    sections: list[ReportSection] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)
    object_details: list[dict[str, Any]] = field(default_factory=list)
    code_diffs: list[dict[str, Any]] = field(default_factory=list)
    generated_html: str = ""
    output_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "schema_name": self.schema_name,
            "verdict": self.verdict,
            "readiness_score": self.readiness_score,
            "scores": self.scores,
            "summary_metrics": self.summary_metrics,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "section_type": s.section_type,
                }
                for s in self.sections
            ],
            "risks": self.risks,
            "object_count": len(self.object_details),
            "code_diff_count": len(self.code_diffs),
            "output_path": self.output_path,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Report assembly helpers
# ---------------------------------------------------------------------------

def assemble_report_data(
    discovery_report: dict[str, Any],
    evaluation_result: dict[str, Any],
    qa_report: dict[str, Any],
    transform_results: list[dict[str, Any]] | None = None,
    remediation_log: dict[str, Any] | None = None,
) -> MigrationReport:
    """Assemble a MigrationReport from all pipeline outputs.

    This function collects data from all upstream agents and organises
    it into a structure suitable for the Report Agent to render.

    Args:
        discovery_report: Output from Discovery Agent.
        evaluation_result: Output from Evaluator Agent.
        qa_report: Output from QA Verifier Agent.
        transform_results: Optional list of transform results.
        remediation_log: Optional output from Remediation Agent.

    Returns:
        A populated MigrationReport.
    """
    report = MigrationReport()

    # Basic metadata
    metadata = discovery_report.get("metadata", {})
    report.schema_name = metadata.get("schema", "Unknown")
    report.title = f"Oracle Migration Report -- {report.schema_name}"

    # Evaluation scores
    report.verdict = evaluation_result.get("verdict", "NO_GO")
    report.readiness_score = evaluation_result.get("readiness_score", 0.0)
    report.scores = evaluation_result.get("scores", {})

    # Summary metrics
    complexity_summary = discovery_report.get("complexity_summary", {})
    qa_summary = qa_report.get("summary", {})
    total_objects = metadata.get("total_objects", 0)

    report.summary_metrics = {
        "total_objects": total_objects,
        "successfully_migrated": qa_summary.get("passed", 0),
        "failed": qa_summary.get("failed", 0),
        "skipped": qa_summary.get("skipped", 0),
        "complexity_distribution": complexity_summary,
    }

    if remediation_log:
        report.summary_metrics["remediation"] = {
            "fixed": remediation_log.get("fixed", 0),
            "escalated": remediation_log.get("escalated", 0),
        }

    # Risks from evaluation
    report.risks = evaluation_result.get("risk_register", [])

    # Object details from QA results
    report.object_details = qa_report.get("results", [])

    # Code diffs from transform results
    if transform_results:
        for tr in transform_results:
            if tr.get("original_sql") and tr.get("converted_sql"):
                report.code_diffs.append({
                    "object_id": tr.get("object_id", ""),
                    "status": tr.get("status", ""),
                    "original": tr.get("original_sql", ""),
                    "converted": tr.get("converted_sql", ""),
                    "transformations": tr.get("transformations_applied", []),
                })

    return report


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------

def parse_report_result(agent_output: str) -> MigrationReport:
    """Parse the Report Agent output.

    The Report Agent primarily returns the path to the generated HTML file.
    It may also return structured metadata about the report.
    """
    report = MigrationReport()

    # The agent might return JSON with metadata + path
    try:
        data = json.loads(agent_output)
        report.output_path = data.get("output_path", "")
        report.generated_html = data.get("html", "")
    except json.JSONDecodeError:
        # If not JSON, the output might be the HTML itself or a file path
        if agent_output.strip().startswith("<!DOCTYPE") or agent_output.strip().startswith("<html"):
            report.generated_html = agent_output
        else:
            report.output_path = agent_output.strip()

    return report


def build_report_task(
    report_data: MigrationReport,
    report_type: ReportType = ReportType.FINAL,
    output_path: str = "",
) -> str:
    """Build the user prompt sent to the Report Agent.

    Args:
        report_data: Assembled report data from all pipeline stages.
        report_type: Type of report to generate.
        output_path: Path where the HTML report should be saved.

    Returns:
        A formatted task string for the agent.
    """
    parts = [
        f"Generate a {report_type.value} migration report.",
        "",
        f"Schema: {report_data.schema_name}",
        f"Verdict: {report_data.verdict}",
        f"Readiness Score: {report_data.readiness_score}%",
        "",
        "Report Data:",
        f"```json\n{report_data.to_json()}\n```",
        "",
        "Requirements:",
        "1. Generate self-contained HTML (inline CSS, no external dependencies).",
        "2. Include a verdict banner with colour coding (green=GO, yellow=CONDITIONAL, red=NO_GO).",
        "3. Include a summary metrics section with key numbers.",
        "4. Include a 5-dimension score section (radar chart if possible using SVG).",
        "5. Include an object status table with pass/fail indicators.",
        "6. Include a risk register section.",
    ]

    if report_type in (ReportType.TECHNICAL, ReportType.FINAL):
        parts.extend([
            "7. Include before/after code diffs for converted SQL.",
            "8. Include transformation details per object.",
        ])

    if output_path:
        parts.extend([
            "",
            f"Save the report to: {output_path}",
        ])

    parts.extend([
        "",
        "Return the file path and report metadata as JSON.",
    ])

    return "\n".join(parts)
