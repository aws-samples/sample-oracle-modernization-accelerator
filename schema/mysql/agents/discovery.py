"""Discovery Agent -- Analyses Oracle source systems and builds inventory.

The Discovery Agent is the first agent in the migration pipeline. It scans
the Oracle database and application source code to produce a comprehensive
inventory, dependency graph, and complexity assessment.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
You are the **Discovery & Triage Agent** for Oracle-to-MySQL database migration.

Your mission is to thoroughly analyse an Oracle database, run DMS Schema
Conversion for rule-based first-pass conversion, and produce a triaged
inventory that separates DMS-converted objects from those requiring AI
agent conversion.

## DMS SC First Architecture

You follow a **DMS SC First** strategy:
1. Run DMS Schema Conversion (rule-based engine) to convert ~95% of objects
2. Collect converted DDL + assessment from S3
3. Triage objects into two categories:
   - **dms_converted** (Simple complexity) -- apply DDL directly in the Design phase
   - **agent_required** (Medium/Complex complexity) -- need AI agent conversion

This dramatically reduces agent workload and ensures deterministic, repeatable
conversion for standard objects (tables, indexes, sequences, simple views).

## Execution Steps (MUST follow in order)

### Step 1: DMS Schema Conversion
- Call `dms_sc_run_conversion(schema=os.environ.get("ORACLE_SCHEMA", os.environ.get("ORACLE_USER", "oracle_schema")))` to trigger the DMS SC engine
- This exports converted DDL scripts and assessment report to S3
- Wait for completion (default timeout: 600s)

### Step 2: Collect Results
- Call `dms_sc_collect_results(schema=os.environ.get("ORACLE_SCHEMA", os.environ.get("ORACLE_USER", "oracle_schema")))` to download from S3
- This returns: DDL scripts, assessment CSV, and a triage split
- If DMS SC results are already in S3, skip Step 1

### Step 3: Oracle Metadata Discovery
- Query Oracle metadata for full inventory (ALL object types)
- Build dependency graph using `oracle_get_dependencies`
- Detect Oracle-specific features (CONNECT BY, MERGE, DBMS_*, etc.)

### Step 4: Application Code Analysis
- Scan MyBatis XML mappers and application code for embedded SQL
- Classify SQL statements by complexity

### Step 5: Triage & Complexity Assessment
- Cross-reference DMS SC assessment with Oracle metadata
- Final triage:
  | DMS SC Result | Complexity | Action                          |
  |---------------|------------|---------------------------------|
  | Converted OK  | Simple     | → dms_converted (apply DDL)     |
  | Partial/Fail  | Medium     | → agent_required (AI converts)  |
  | Failed        | Complex    | → agent_required (AI converts)  |
  | Not covered   | Any        | → agent_required (AI converts)  |

## Responsibilities

1. **Object Inventory** -- Extract ALL database objects:
   - Tables, Views, Materialized Views
   - Procedures, Functions, Packages (spec + body)
   - Triggers, Sequences, Types, Synonyms
   - DB Links, Directories, Contexts

2. **Oracle-Specific Feature Detection** -- Identify features requiring
   special handling during migration:
   - Hierarchical queries (CONNECT BY, START WITH)
   - MERGE statements
   - BULK COLLECT / FORALL
   - REF CURSOR, SYS_REFCURSOR
   - DBMS_* packages (DBMS_OUTPUT, DBMS_LOB, DBMS_SQL, DBMS_SCHEDULER, etc.)
   - UTL_* packages (UTL_FILE, UTL_HTTP, UTL_RAW, etc.)
   - Oracle-specific data types (XMLTYPE, SDO_GEOMETRY, ANYDATA)
   - Virtual Private Database (VPD) policies
   - Oracle Advanced Queuing (AQ)
   - Pipelined functions, Object types, Nested tables/VARRAYs

3. **Application Code Analysis** -- Parse application source code for
   embedded SQL:
   - MyBatis XML mapper files: extract <select>, <insert>, <update>,
     <delete>, <sql> fragments, <include> references
   - Java string literals containing SQL
   - Hibernate HQL/JPQL native queries
   - Spring JDBC templates

4. **Dependency Graph** -- Build a directed acyclic graph (DAG) of object
   dependencies using ALL_DEPENDENCIES and code-level references.
   Nodes = objects, Edges = dependency type (INSERT, SELECT, CALL, FK, etc.)

5. **Complexity Scoring** -- Score each object:
   | Score    | Criteria                                                  |
   |----------|-----------------------------------------------------------|
   | LOW      | Standard ANSI SQL, simple CRUD, basic data types          |
   | MEDIUM   | Oracle functions (NVL, DECODE), simple PL/SQL blocks      |
   | HIGH     | CONNECT BY, MERGE, dynamic SQL, package cross-references  |
   | CRITICAL | DBMS_* packages, object types, pipelined functions, VPD   |

## Tools Available

- `dms_sc_run_conversion` -- Run DMS Schema Conversion (rule-based engine)
- `dms_sc_collect_results` -- Collect converted DDL + assessment from S3
- `dms_sc_list_s3` -- List DMS SC S3 bucket contents (for debugging)
- `oracle_query` -- Execute read-only SQL on Oracle (metadata queries)
- `oracle_get_object_list` -- List objects by type in a schema
- `oracle_get_dependencies` -- Query ALL_DEPENDENCIES for a schema
- `oracle_get_constraints` -- Get constraint definitions
- `oracle_get_indexes` -- Get index definitions
- `oracle_get_sequences` -- Get sequence definitions
- `oracle_get_partitions` -- Get partition definitions
- `mybatis_scan_directory` -- Scan a directory tree for MyBatis XML mappers
- `dms_parse_assessment_csv` -- Parse DMS assessment CSV (legacy/fallback)
- `dms_get_failed_objects` -- Get failed objects from DMS assessment

## Output Format

Return a JSON document conforming to the DiscoveryReport schema:
```json
{
  "metadata": {"source_db": "...", "schema": "...", "scan_timestamp": "...", "total_objects": N},
  "inventory": {"tables": [...], "views": [...], ...},
  "oracle_features": {"connect_by": [...], "merge": [...], ...},
  "dependency_graph": {"nodes": [...], "edges": [...]},
  "application_sql": {"files_scanned": N, "sql_statements_found": N, "by_source": {...}},
  "mybatis_mappings": [...],
  "complexity_summary": {"LOW": N, "MEDIUM": N, "HIGH": N, "CRITICAL": N},
  "dms_sc_triage": {
    "dms_sc_status": "SUCCESS|PARTIAL|FAILED",
    "dms_converted": [{"object_name": "...", "type": "TABLE", "ddl_available": true}],
    "agent_required": [{"object_name": "...", "type": "PROCEDURE", "reason": "Complex: CONNECT BY"}],
    "dms_converted_count": N,
    "agent_required_count": N,
    "dms_ddl_scripts": [{"key": "...", "content": "...", "type": "TABLE"}]
  }
}
```

## Constraints

- You MUST run DMS SC first before Oracle metadata discovery.
- You MUST NOT modify any source code or database objects.
- You MUST NOT make assumptions about objects you cannot access -- mark them
  as UNKNOWN with a note.
- You MUST NOT skip objects because they appear simple.
- You MUST include the full DMS SC triage in your output so the Schema
  Architect knows which objects to apply directly vs design from scratch.
- Process systematically: DMS SC → Oracle metadata → code scan → dependency
  graph → complexity scoring → triage.
- Be thorough. Missing a single dependency can cause migration failures
  downstream.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "oracle_query",
    "oracle_get_object_list",
    "oracle_get_dependencies",
    "oracle_get_constraints",
    "oracle_get_indexes",
    "oracle_get_sequences",
    "oracle_get_partitions",
    "mybatis_scan_directory",
    "dms_parse_assessment_csv",
    "dms_get_failed_objects",
    "dms_sc_run_conversion",
    "dms_sc_collect_results",
    "dms_sc_list_s3",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_discovery_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Discovery Agent instance.

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
                    "Tool '%s' not found for discovery agent -- skipping",
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

class ComplexityLevel(str, Enum):
    """Migration complexity score for a database object."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ObjectEntry:
    """A single database object in the inventory."""

    name: str
    object_type: str
    schema: str
    complexity: ComplexityLevel = ComplexityLevel.LOW
    line_count: int = 0
    oracle_features: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class DependencyEdge:
    """A directed edge in the dependency graph."""

    from_object: str
    to_object: str
    dependency_type: str  # INSERT, SELECT, CALL, FK, NEXTVAL, etc.


@dataclass
class DependencyGraph:
    """Directed acyclic graph of object dependencies."""

    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)

    def add_node(self, object_id: str, object_type: str, complexity: ComplexityLevel) -> None:
        self.nodes.append({
            "id": object_id,
            "type": object_type,
            "complexity": complexity.value,
        })

    def add_edge(self, from_obj: str, to_obj: str, dep_type: str) -> None:
        self.edges.append(DependencyEdge(
            from_object=from_obj,
            to_object=to_obj,
            dependency_type=dep_type,
        ))


@dataclass
class MyBatisMapping:
    """A MyBatis XML mapper file with extracted SQL information."""

    file_path: str
    namespace: str
    sql_count: int = 0
    sql_types: dict[str, int] = field(default_factory=dict)
    oracle_patterns_found: list[str] = field(default_factory=list)


@dataclass
class DiscoveryReport:
    """Complete output of the Discovery Agent."""

    metadata: dict[str, Any] = field(default_factory=dict)
    inventory: dict[str, list[ObjectEntry]] = field(default_factory=dict)
    oracle_features: dict[str, list[str]] = field(default_factory=dict)
    dependency_graph: DependencyGraph = field(default_factory=DependencyGraph)
    application_sql: dict[str, Any] = field(default_factory=dict)
    mybatis_mappings: list[MyBatisMapping] = field(default_factory=list)
    complexity_summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the report to a JSON-compatible dict."""
        return {
            "metadata": self.metadata,
            "inventory": {
                obj_type: [
                    {
                        "name": obj.name,
                        "object_type": obj.object_type,
                        "schema": obj.schema,
                        "complexity": obj.complexity.value,
                        "line_count": obj.line_count,
                        "oracle_features": obj.oracle_features,
                        "notes": obj.notes,
                    }
                    for obj in objects
                ]
                for obj_type, objects in self.inventory.items()
            },
            "oracle_features": self.oracle_features,
            "dependency_graph": {
                "nodes": self.dependency_graph.nodes,
                "edges": [
                    {
                        "from": e.from_object,
                        "to": e.to_object,
                        "type": e.dependency_type,
                    }
                    for e in self.dependency_graph.edges
                ],
            },
            "application_sql": self.application_sql,
            "mybatis_mappings": [
                {
                    "file_path": m.file_path,
                    "namespace": m.namespace,
                    "sql_count": m.sql_count,
                    "sql_types": m.sql_types,
                    "oracle_patterns_found": m.oracle_patterns_found,
                }
                for m in self.mybatis_mappings
            ],
            "complexity_summary": self.complexity_summary,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise the report to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helper: Complexity scoring rules
# ---------------------------------------------------------------------------

# Oracle features that determine complexity scoring
_CRITICAL_FEATURES = frozenset({
    "DBMS_OUTPUT", "DBMS_LOB", "DBMS_SQL", "DBMS_SCHEDULER", "DBMS_CRYPTO",
    "DBMS_XMLDOM", "DBMS_XMLPARSER", "DBMS_AQ", "DBMS_AQADM",
    "UTL_FILE", "UTL_HTTP", "UTL_RAW", "UTL_SMTP",
    "XMLTYPE", "SDO_GEOMETRY", "ANYDATA", "ANYTYPE",
    "PIPELINED", "OBJECT_TYPE", "NESTED_TABLE", "VARRAY",
    "VPD_POLICY", "ORACLE_AQ",
})

_HIGH_FEATURES = frozenset({
    "CONNECT_BY", "START_WITH", "MERGE", "DYNAMIC_SQL",
    "EXECUTE_IMMEDIATE", "BULK_COLLECT", "FORALL",
    "REF_CURSOR", "SYS_REFCURSOR",
    "PACKAGE_CROSS_REF", "AUTONOMOUS_TRANSACTION",
})

_MEDIUM_FEATURES = frozenset({
    "NVL", "NVL2", "DECODE", "ROWNUM",
    "TO_DATE", "TO_CHAR", "TO_NUMBER",
    "PLSQL_BLOCK", "CURSOR_DECLARATION",
    "EXCEPTION_HANDLER",
})


def score_complexity(oracle_features: list[str]) -> ComplexityLevel:
    """Determine complexity level from a list of Oracle features used."""
    feature_set = frozenset(f.upper() for f in oracle_features)

    if feature_set & _CRITICAL_FEATURES:
        return ComplexityLevel.CRITICAL
    if feature_set & _HIGH_FEATURES:
        return ComplexityLevel.HIGH
    if feature_set & _MEDIUM_FEATURES:
        return ComplexityLevel.MEDIUM
    return ComplexityLevel.LOW


# ---------------------------------------------------------------------------
# Result parsing helpers
# ---------------------------------------------------------------------------

def parse_discovery_report(agent_output: str) -> DiscoveryReport:
    """Parse the JSON output from the Discovery Agent into a DiscoveryReport.

    The agent returns a JSON string; this function converts it into our
    typed data model for use by downstream agents.
    """
    report = DiscoveryReport()

    try:
        data = json.loads(agent_output)
    except json.JSONDecodeError:
        logger.warning("Could not parse Discovery Agent output as JSON")
        return report

    # Metadata
    report.metadata = data.get("metadata", {})

    # Inventory
    raw_inventory = data.get("inventory", {})
    for obj_type, objects in raw_inventory.items():
        report.inventory[obj_type] = [
            ObjectEntry(
                name=obj.get("name", ""),
                object_type=obj.get("object_type", obj_type),
                schema=obj.get("schema", ""),
                complexity=ComplexityLevel(obj.get("complexity", "LOW")),
                line_count=obj.get("line_count", 0),
                oracle_features=obj.get("oracle_features", []),
                notes=obj.get("notes", ""),
            )
            for obj in objects
        ]

    # Oracle features
    report.oracle_features = data.get("oracle_features", {})

    # Dependency graph
    graph_data = data.get("dependency_graph", {})
    report.dependency_graph = DependencyGraph()
    for node in graph_data.get("nodes", []):
        report.dependency_graph.add_node(
            node["id"],
            node["type"],
            ComplexityLevel(node.get("complexity", "LOW")),
        )
    for edge in graph_data.get("edges", []):
        report.dependency_graph.add_edge(
            edge["from"],
            edge["to"],
            edge["type"],
        )

    # Application SQL stats
    report.application_sql = data.get("application_sql", {})

    # MyBatis mappings
    for m in data.get("mybatis_mappings", []):
        report.mybatis_mappings.append(MyBatisMapping(
            file_path=m.get("file_path", ""),
            namespace=m.get("namespace", ""),
            sql_count=m.get("sql_count", 0),
            sql_types=m.get("sql_types", {}),
            oracle_patterns_found=m.get("oracle_patterns_found", []),
        ))

    # Complexity summary
    report.complexity_summary = data.get("complexity_summary", {})

    return report


def build_discovery_task(
    schema: str,
    source_path: str | None = None,
) -> str:
    """Build the user prompt/task description sent to the Discovery Agent.

    Args:
        schema: Oracle schema name to analyse (e.g., "HR").
        source_path: Optional path to application source code directory.

    Returns:
        A formatted task string for the agent.
    """
    parts = [
        f"Analyse the Oracle schema '{schema}' completely.",
        "",
        "Tasks:",
        "1. Query ALL_OBJECTS to build complete object inventory.",
        "2. Query ALL_DEPENDENCIES to build the dependency graph.",
        "3. Identify all Oracle-specific features used.",
        "4. Score each object's migration complexity (LOW/MEDIUM/HIGH/CRITICAL).",
    ]

    if source_path:
        parts.extend([
            f"5. Scan application source code at '{source_path}' for embedded SQL.",
            "6. Parse MyBatis XML mappers and extract SQL statements.",
        ])

    parts.extend([
        "",
        "Return the complete DiscoveryReport as JSON.",
    ])

    return "\n".join(parts)
