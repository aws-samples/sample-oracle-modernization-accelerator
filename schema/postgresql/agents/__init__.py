"""OMA Agents -- 9 specialised Strands Agents for Oracle-to-PostgreSQL migration.

Each agent module follows the official Strands SDK pattern: it imports
``from strands import Agent``, defines its own system prompt, tool list,
and ``create_*_agent()`` factory function.

Agent Ensemble:
    1. Discovery Agent       -- Source system analysis, DMS SC triage
    2. Schema Architect Agent -- PostgreSQL schema design
    3. Code Migrator Agent   -- Oracle SQL to PostgreSQL conversion
    4. QA Verifier Agent     -- Functional correctness verification
    5. Evaluator Agent       -- 5-dimension quality assessment
    6. Remediation Agent     -- Automated fix for failed conversions
    7. Report Agent          -- Migration report generation
    8. Data Migrator Agent   -- Bulk data transfer
    9. Data Verifier Agent   -- Data integrity verification
"""

from postgresql.agents.code_migrator import (
    MigrationBatch,
    TransformResult,
    TransformStatus,
    build_transform_task,
    create_code_migrator_agent,
    parse_transform_result,
)
from postgresql.agents.data_migrator import (
    create_data_migrator_agent,
)
from postgresql.agents.data_verifier import (
    create_data_verifier_agent,
)
from postgresql.agents.discovery import (
    ComplexityLevel,
    DependencyGraph,
    DiscoveryReport,
    MyBatisMapping,
    ObjectEntry,
    build_discovery_task,
    create_discovery_agent,
    parse_discovery_report,
    score_complexity,
)
from postgresql.agents.evaluator import (
    CriticalFinding,
    DimensionScore,
    EvaluationResult,
    MigrationVerdict,
    RemediationTarget,
    RiskEntry,
    build_evaluation_task,
    calculate_readiness_score,
    create_evaluator_agent,
    determine_verdict,
    parse_evaluation_result,
)
from postgresql.agents.factory import (
    AGENT_SPECS,
    BedrockConfig,
    OMAConfig,
    create_agent,
    create_agents,
    get_agent_info,
)
from postgresql.agents.qa_verifier import (
    LevelResult,
    ObjectQAResult,
    QAReport,
    VerificationLevel,
    VerificationResult,
    build_qa_task,
    create_qa_verifier_agent,
    parse_qa_report,
)
from postgresql.agents.remediation import (
    FixDetail,
    FixPattern,
    FixStatus,
    RemediationEntry,
    RemediationLog,
    RemediationStrategy,
    build_remediation_task,
    classify_error,
    create_remediation_agent,
    parse_remediation_log,
)
from postgresql.agents.report import (
    MigrationReport,
    ReportConfig,
    ReportType,
    assemble_report_data,
    build_report_task,
    create_report_agent,
    parse_report_result,
)
from postgresql.agents.schema_architect import (
    ConvertedDDL,
    MigrationNote,
    SchemaDesign,
    TypeMapping,
    build_schema_task,
    create_schema_architect_agent,
    map_oracle_number,
    parse_schema_design,
)

__all__ = [
    # Discovery
    "ComplexityLevel",
    "DependencyGraph",
    "DiscoveryReport",
    "MyBatisMapping",
    "ObjectEntry",
    "build_discovery_task",
    "create_discovery_agent",
    "parse_discovery_report",
    "score_complexity",
    # Schema Architect
    "ConvertedDDL",
    "MigrationNote",
    "SchemaDesign",
    "TypeMapping",
    "build_schema_task",
    "create_schema_architect_agent",
    "map_oracle_number",
    "parse_schema_design",
    # Code Migrator
    "MigrationBatch",
    "TransformResult",
    "TransformStatus",
    "build_transform_task",
    "create_code_migrator_agent",
    "parse_transform_result",
    # QA Verifier
    "LevelResult",
    "ObjectQAResult",
    "QAReport",
    "VerificationLevel",
    "VerificationResult",
    "build_qa_task",
    "create_qa_verifier_agent",
    "parse_qa_report",
    # Evaluator
    "CriticalFinding",
    "DimensionScore",
    "EvaluationResult",
    "MigrationVerdict",
    "RemediationTarget",
    "RiskEntry",
    "build_evaluation_task",
    "calculate_readiness_score",
    "create_evaluator_agent",
    "determine_verdict",
    "parse_evaluation_result",
    # Remediation
    "FixDetail",
    "FixPattern",
    "FixStatus",
    "RemediationEntry",
    "RemediationLog",
    "RemediationStrategy",
    "build_remediation_task",
    "classify_error",
    "create_remediation_agent",
    "parse_remediation_log",
    # Report
    "MigrationReport",
    "ReportConfig",
    "ReportType",
    "assemble_report_data",
    "build_report_task",
    "create_report_agent",
    "parse_report_result",
    # Data Migrator
    "create_data_migrator_agent",
    # Data Verifier
    "create_data_verifier_agent",
    # Factory
    "AGENT_SPECS",
    "BedrockConfig",
    "OMAConfig",
    "create_agent",
    "create_agents",
    "get_agent_info",
]
