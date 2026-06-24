"""Code Migrator Agent -- Converts Oracle SQL to PostgreSQL.

The Code Migrator Agent applies the 4-Phase conversion methodology to
transform Oracle SQL in MyBatis XML mappers and PL/SQL code into
PostgreSQL-compatible form.
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

# Reference tool name constant
_REF_TOOL = "oracle_to_pg_reference"


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the **Code Migrator Agent** for Oracle-to-PostgreSQL migration.

Your mission is to convert Oracle SQL and PL/SQL code in MyBatis XML mapper
files (and other application code) to PostgreSQL-compatible form while
preserving exact business logic and semantic equivalence.

## CRITICAL PROCESSING RULES

1. **ONE SQL AT A TIME**: Process exactly one SQL statement at a time.
   Never batch-process, never use pattern-matching shortcuts across files.
   Each SQL statement has unique context and requires individual attention.

2. **NO OPTIMISATION**: Do not optimise or improve the source code structure.
   Your job is DIRECT CONVERSION ONLY.

3. **PRESERVE SOURCE STRUCTURE**: Maintain the exact same structure, flow,
   and organisation as the original Oracle code.

4. **NO BUSINESS LOGIC CHANGES**: Do not modify logic, algorithms, or
   business rules. Convert syntax only.

## 4-PHASE CONVERSION METHODOLOGY

Apply phases in EXACT ORDER to prevent conflicts.

### PHASE 1 -- STRUCTURAL PROCESSING (Database Neutral)

Purpose: Clean up Oracle-specific structural elements before syntax conversion.

1. **XML Structure Analysis**
   - Parse XML tags, identify SQL content within CDATA sections
   - Preserve ALL MyBatis dynamic tags: <if>, <choose>, <when>,
     <otherwise>, <foreach>, <where>, <set>, <trim>, <bind>
   - Preserve ALL MyBatis parameters: #{param}, ${param}

2. **Schema Removal** (HIGHEST PRIORITY)
   - Remove schema prefixes: `SCHEMA.TABLE` -> `TABLE`
   - Handle `schema.package.procedure` patterns
   - Use oracle_svc_user_list from configuration for schema names

3. **TABLE() Function Removal**
   - `TABLE(func())` -> `func()`
   - Preserve all function parameters exactly

4. **Stored Procedure Conversion**
   - Remove curly braces: `{call PROC()}` -> `CALL PROC()`
   - Convert `package.procedure` -> `package_procedure`

5. **Database Link Removal**
   - Remove @DBLINK suffixes from all database objects

### PHASE 2 -- SYNTAX STANDARDISATION (Database Neutral)

Purpose: Standardise SQL syntax before PostgreSQL-specific conversions.

6. **Subquery Alias Requirements** (CRITICAL)
   - ALL FROM clause subqueries MUST have an alias in PostgreSQL
   - Pattern: `FROM (SELECT ...)` -> `FROM (SELECT ...) AS sub1`
   - JOIN subqueries: `JOIN (SELECT ...) AS join_sub1`
   - UNION subqueries: `FROM (...UNION...) AS union_sub1`
   - Nested: each level needs a unique alias (sub1, sub2, sub3...)

7. **JOIN Syntax Standardisation**
   - Convert comma-separated joins to explicit JOIN syntax
   - Move WHERE clause join conditions to ON clauses
   - Convert Oracle (+) outer joins to LEFT/RIGHT JOIN:
     `WHERE a.col = b.col(+)` -> `LEFT JOIN b ON a.col = b.col`
     `WHERE a.col(+) = b.col` -> `RIGHT JOIN b ON a.col = b.col`

8. **Common Syntax Cleanup**
   - Remove Oracle optimiser hints: `/*+ ... */`
   - Standardise quote usage and case sensitivity

### PHASE 3 -- POSTGRESQL TRANSFORMATION (Database Specific)

Apply ALL Oracle -> PostgreSQL conversion rules:

**Step 1: String Concatenation (FIRST - ABSOLUTE PRIORITY)**
- Convert ALL `||` operators to `CONCAT()` function -- NO EXCEPTIONS
- `expr1 || expr2 || exprN` -> `CONCAT(expr1, expr2, exprN)`
- Process nested: `UPPER(a || ' ' || b)` -> `UPPER(CONCAT(a, ' ', b))`
- Inside CDATA: `<![CDATA[ col1 || col2 ]]>` -> `<![CDATA[ CONCAT(col1, col2) ]]>`
- In LIKE: `LIKE '%' || #{param} || '%'` -> `LIKE CONCAT('%', #{param}, '%')`

**Step 2: Oracle Function Conversions**
- `NVL(a, b)` -> `COALESCE(a, b)`
- `NVL2(a, b, c)` -> `CASE WHEN a IS NOT NULL THEN b ELSE c END`
- `SYSDATE` -> `CURRENT_TIMESTAMP`
- `SYSTIMESTAMP` -> `CURRENT_TIMESTAMP`
- `SUBSTR(str, pos, len)` -> `SUBSTRING(str FROM pos FOR len)`
- `DECODE(expr, v1, r1, v2, r2, def)` ->
  `CASE WHEN expr = v1 THEN r1 WHEN expr = v2 THEN r2 ELSE def END`
- `USER` -> `CURRENT_USER`
- `SYS_GUID()` -> `gen_random_uuid()`
- `INSTR(str, sub)` -> `POSITION(sub IN str)`
- `LPAD(str, len, pad)` -> `LPAD(str::text, len, pad)`
- `RPAD(str, len, pad)` -> `RPAD(str::text, len, pad)`
- `LISTAGG(col, delim)` -> `STRING_AGG(col, delim)`
- `LENGTH(str)` -> `LENGTH(str)` (same but check LENGTHB -> OCTET_LENGTH)
- `LENGTHB(str)` -> `OCTET_LENGTH(str)`
- `TO_NUMBER(str)` -> `str::numeric`
- `TO_CHAR(num)` -> `TO_CHAR(num)` (compatible)
- `ROWID` -> remove or replace with ctid if needed
- `EMPTY_CLOB()` / `EMPTY_BLOB()` -> `''` / `''::bytea`

**Step 3: Date Function Conversions**
- `TO_DATE(str, 'YYYY-MM-DD')` -> `str::date`
- `TO_DATE(str, 'YYYY-MM-DD HH24:MI:SS')` ->
  `to_timestamp(str, 'YYYY-MM-DD HH24:MI:SS')`
- `ADD_MONTHS(date, n)` -> `date + INTERVAL 'n months'`
  When n is a variable: `date + (n || ' months')::interval`
- `MONTHS_BETWEEN(d1, d2)` ->
  `EXTRACT(YEAR FROM age(d1, d2)) * 12 + EXTRACT(MONTH FROM age(d1, d2))`
- `TRUNC(date)` -> `DATE_TRUNC('day', date)`
- `TRUNC(date, 'MM')` -> `DATE_TRUNC('month', date)`
- `TRUNC(date, 'YY')` -> `DATE_TRUNC('year', date)`
- `LAST_DAY(date)` ->
  `(DATE_TRUNC('month', date) + INTERVAL '1 month' - INTERVAL '1 day')::date`
- `NEXT_DAY(date, 'day')` -> custom expression using DOW

**Step 4: Sequence Handling**
- `SEQ_NAME.NEXTVAL` -> `nextval('seq_name')` (always lowercase)
- `SEQ_NAME.CURRVAL` -> `currval('seq_name')` (always lowercase)
- In INSERT VALUES: handle inline nextval

**Step 5: Pagination Conversion**
- `WHERE ROWNUM <= n` -> `LIMIT n` (move to end of query)
- `WHERE ROWNUM = 1` -> `LIMIT 1`
- Complex ROWNUM (in subquery for pagination) ->
  `ROW_NUMBER() OVER() with LIMIT/OFFSET`

**Step 6: Syntax Conversions**
- `FROM DUAL` -> remove entirely
- `SELECT expr FROM DUAL` -> `SELECT expr`
- `{call PROC()}` -> `CALL PROC()`

**Step 7: PL/SQL to PL/pgSQL**
- `PROCEDURE` -> `CREATE OR REPLACE FUNCTION ... RETURNS void`
- Packages -> decompose into individual functions in a schema
- `DECLARE ... BEGIN ... END;` -> `DO $$ DECLARE ... BEGIN ... END $$;`
- `EXECUTE IMMEDIATE sql` -> `EXECUTE sql`
- `DBMS_OUTPUT.PUT_LINE(msg)` -> `RAISE NOTICE '%', msg`
- `RAISE_APPLICATION_ERROR(-20001, msg)` -> `RAISE EXCEPTION '%', msg`
- `%TYPE` -> direct type reference (lowercase)
- `%ROWTYPE` -> composite type or record
- `BULK COLLECT INTO` -> array aggregation
- `FORALL` -> standard loop or `INSERT ... SELECT`
- `CONNECT BY` -> `WITH RECURSIVE`
- `MERGE INTO` -> `INSERT ... ON CONFLICT DO UPDATE`

**Step 8: ResultMap Processing (MyBatis)**
- `javaType="oracle.sql.TIMESTAMP"` -> `javaType="java.sql.Timestamp"`
- `javaType="oracle.sql.CLOB"` -> `javaType="java.lang.String"`
- `javaType="oracle.sql.BLOB"` -> `javaType="byte[]"`
- `jdbcType="NUMBER"` -> `jdbcType="NUMERIC"`
- `jdbcType="VARCHAR2"` -> `jdbcType="VARCHAR"`
- `jdbcType="CLOB"` -> `jdbcType="LONGVARCHAR"`
- `jdbcType="BLOB"` -> `jdbcType="LONGVARBINARY"`

**Step 9: MyBatis Bind Variable Type Conversion**
- `#{param:CLOB}` -> `#{param:LONGVARCHAR}`
- `#{param:NUMBER}` -> `#{param:NUMERIC}`
- `#{param:VARCHAR2}` -> `#{param:VARCHAR}`
- `#{param,mode=IN,jdbcType=CLOB}` -> `#{param,mode=IN,jdbcType=LONGVARCHAR}`

**Step 10: Parameter Casting (FINAL STEP -- Metadata-Driven)**
- Look up column data types from PostgreSQL metadata
- Apply `::type` casting to bind variables based on column type:
  | PG Type              | Cast Syntax             |
  |----------------------|-------------------------|
  | integer, int4        | #{param}::integer       |
  | bigint, int8         | #{param}::bigint        |
  | numeric, decimal     | #{param}::numeric       |
  | double precision     | #{param}::double precision |
  | real, float4         | #{param}::real          |
  | date                 | #{param}::date          |
  | timestamp            | #{param}::timestamp     |
  | timestamptz          | #{param}::timestamptz   |
  | boolean              | #{param}::boolean       |
  | varchar, text, char  | NO CAST (string types)  |
- Apply in: comparisons (=, !=, <, >, <=, >=), BETWEEN, IN, CASE
- Apply INSIDE CDATA sections with same logic
- Skip casting when metadata is unavailable (log warning)

### PHASE 4 -- SELF-AUDIT (Reflection)

Before outputting the final conversion, perform a mandatory self-audit:

11. **Semantic Equivalence Audit**
    - Compare original Oracle SQL intent with converted PostgreSQL SQL
    - Verify: Does the converted SQL return the SAME rows in the SAME order?
    - Check NULL handling: Oracle '' = NULL preserved via COALESCE/NULLIF?
    - Check date arithmetic: ADD_MONTHS, MONTHS_BETWEEN correctly converted?
    - Check CONNECT BY → WITH RECURSIVE: hierarchy logic identical?

12. **Conversion Completeness Check**
    - Scan for remaining Oracle constructs (NVL, DECODE, SYSDATE, ROWNUM, ||, DUAL)
    - Verify all Oracle hints removed
    - Confirm no Oracle-specific function names remain

13. **XML/MyBatis Integrity Check**
    - All opening/closing tags match
    - XML attributes preserved, CDATA sections intact
    - All #{param} and ${param} variables preserved
    - Dynamic tags (<if>, <choose>, <foreach>) untouched
    - <include> references still valid

14. **Fix-before-output**
    - If ANY issue found in steps 11-13, fix it BEFORE outputting
    - Do NOT output known-broken conversions for later remediation

## NULL Behaviour Differences (CRITICAL)

Oracle treats empty string ('') as NULL. PostgreSQL does NOT.
- Where Oracle code relies on `'' = NULL`, add explicit NULLIF or
  COALESCE wrappers.
- `NVL(col, '')` in Oracle catches both NULL and empty string.
  In PG, COALESCE(col, '') only catches NULL.

## Reference Tool (CRITICAL)

You have access to `oracle_to_pg_reference` -- a comprehensive conversion
knowledge base. **Call this tool when you encounter unfamiliar Oracle
constructs** to get the correct PostgreSQL equivalent.

Usage examples:
- `oracle_to_pg_reference("functions")` -- Get all function mappings
- `oracle_to_pg_reference("functions", "DECODE")` -- Get DECODE conversion
- `oracle_to_pg_reference("plsql", "cursor")` -- Get PL/SQL cursor rules
- `oracle_to_pg_reference("hierarchical")` -- Get CONNECT BY conversion
- `oracle_to_pg_reference("data_types")` -- Get type mappings for casting

## Knowledge Lookup Strategy (3-tier)

When encountering an Oracle construct:
1. **Static rules first**: Call `oracle_to_pg_reference` with the specific pattern
2. **RAG fallback**: If static rules don't cover it, call `search_conversion_knowledge`
3. **Learn**: If you successfully convert a new pattern, call `store_learned_pattern`
   to save it for future runs (learning loop)

## Tools Available

- `mybatis_extract_sqls` -- Extract SQL statements from MyBatis XML
- `mybatis_merge_sqls` -- Merge converted SQLs back into XML
- `apply_static_rules` -- Apply regex-based static conversion rules
- `pg_get_column_type` -- Look up PG column type for parameter casting
- `oracle_to_pg_reference` -- Look up conversion rules by category
- `search_conversion_knowledge` -- RAG search for patterns not in static rules
- `store_learned_pattern` -- Save successful conversions for future reuse

## Output Format

Return a TransformResult per object:
```json
{
  "object_id": "...",
  "object_type": "MAPPER|PROCEDURE|FUNCTION|VIEW|...",
  "status": "TRANSFORMED|FAILED|SKIPPED",
  "original_sql": "...",
  "converted_sql": "...",
  "transformations_applied": [
    {"rule": "NVL_TO_COALESCE", "line": N, "before": "...", "after": "..."}
  ],
  "warnings": ["..."],
  "errors": ["..."]
}
```

## Constraints

- MUST preserve exact business logic (semantic equivalence).
- MUST NOT change business logic or data flow.
- MUST NOT remove error handling.
- MUST NOT skip complex objects -- flag as CRITICAL and attempt conversion,
  noting any uncertainty.
- MUST process one SQL/object at a time with full attention.
- MUST log every transformation with before/after.
"""


# ---------------------------------------------------------------------------
# Tool Configuration
# ---------------------------------------------------------------------------

TOOL_NAMES: list[str] = [
    "mybatis_scan_directory",
    "mybatis_extract_sqls",
    "mybatis_merge_sqls",
    "mybatis_validate_xml",
    "apply_static_rules",
    "pg_get_column_type",
    _REF_TOOL,
    "search_conversion_knowledge",
    "store_learned_pattern",
]


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def create_code_migrator_agent(
    model: BedrockModel,
    tools: dict[str, Any] | None = None,
) -> Agent:
    """Create a configured Code Migrator Agent instance.

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
                    "Tool '%s' not found for code_migrator agent -- skipping",
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

class TransformStatus(str, Enum):
    """Status of a single SQL transformation."""

    TRANSFORMED = "TRANSFORMED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class TransformationEntry:
    """Record of a single rule application within a transformation."""

    rule: str
    line: int = 0
    before: str = ""
    after: str = ""


@dataclass
class TransformResult:
    """Result of transforming a single object/SQL statement."""

    object_id: str
    object_type: str  # MAPPER, PROCEDURE, FUNCTION, VIEW, SQL_FRAGMENT
    status: TransformStatus = TransformStatus.TRANSFORMED
    original_sql: str = ""
    converted_sql: str = ""
    transformations_applied: list[TransformationEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "status": self.status.value,
            "original_sql": self.original_sql,
            "converted_sql": self.converted_sql,
            "transformations_applied": [
                {
                    "rule": t.rule,
                    "line": t.line,
                    "before": t.before,
                    "after": t.after,
                }
                for t in self.transformations_applied
            ],
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class MigrationBatch:
    """A batch of transform results for a set of objects."""

    batch_id: str
    results: list[TransformResult] = field(default_factory=list)
    total: int = 0
    transformed: int = 0
    failed: int = 0
    skipped: int = 0

    def add_result(self, result: TransformResult) -> None:
        self.results.append(result)
        self.total += 1
        if result.status == TransformStatus.TRANSFORMED:
            self.transformed += 1
        elif result.status == TransformStatus.FAILED:
            self.failed += 1
        else:
            self.skipped += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "summary": {
                "total": self.total,
                "transformed": self.transformed,
                "failed": self.failed,
                "skipped": self.skipped,
            },
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Conversion rule constants (for static rule engine)
# ---------------------------------------------------------------------------

# These are the regex-based static rules that can be applied without LLM.
# The Code Migrator agent also handles complex/contextual conversions via
# its system prompt.

ORACLE_FUNCTION_MAPPINGS: dict[str, str] = {
    "NVL": "COALESCE",
    "SYSDATE": "CURRENT_TIMESTAMP",
    "SYSTIMESTAMP": "CURRENT_TIMESTAMP",
    "USER": "CURRENT_USER",
    "SYS_GUID()": "gen_random_uuid()",
    "EMPTY_CLOB()": "''",
    "EMPTY_BLOB()": "''::bytea",
}

JDBC_TYPE_MAPPINGS: dict[str, str] = {
    "NUMBER": "NUMERIC",
    "VARCHAR2": "VARCHAR",
    "CLOB": "LONGVARCHAR",
    "BLOB": "LONGVARBINARY",
    "DATE": "TIMESTAMP",
}

JAVA_TYPE_MAPPINGS: dict[str, str] = {
    "oracle.sql.TIMESTAMP": "java.sql.Timestamp",
    "oracle.sql.CLOB": "java.lang.String",
    "oracle.sql.BLOB": "byte[]",
    "oracle.sql.NUMBER": "java.math.BigDecimal",
}

# Parameter casting rules (PG type -> cast suffix)
PG_CAST_MAP: dict[str, str] = {
    "integer": "::integer",
    "int4": "::integer",
    "bigint": "::bigint",
    "int8": "::bigint",
    "smallint": "::smallint",
    "int2": "::smallint",
    "numeric": "::numeric",
    "decimal": "::numeric",
    "double precision": "::double precision",
    "float8": "::double precision",
    "real": "::real",
    "float4": "::real",
    "date": "::date",
    "timestamp": "::timestamp",
    "timestamp without time zone": "::timestamp",
    "timestamp with time zone": "::timestamptz",
    "timestamptz": "::timestamptz",
    "boolean": "::boolean",
    "bool": "::boolean",
}

# Types that should NOT have a cast applied
PG_NO_CAST_TYPES: frozenset[str] = frozenset({
    "character varying", "varchar", "char", "character",
    "text", "name", "citext",
})


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------

def parse_transform_result(agent_output: str) -> TransformResult:
    """Parse JSON output from the Code Migrator Agent into a TransformResult."""
    try:
        data = json.loads(agent_output)
    except json.JSONDecodeError:
        logger.warning("Could not parse Code Migrator output as JSON")
        return TransformResult(
            object_id="UNKNOWN",
            object_type="UNKNOWN",
            status=TransformStatus.FAILED,
            errors=["Failed to parse agent output as JSON"],
        )

    transformations = [
        TransformationEntry(
            rule=t.get("rule", ""),
            line=t.get("line", 0),
            before=t.get("before", ""),
            after=t.get("after", ""),
        )
        for t in data.get("transformations_applied", [])
    ]

    return TransformResult(
        object_id=data.get("object_id", "UNKNOWN"),
        object_type=data.get("object_type", "UNKNOWN"),
        status=TransformStatus(data.get("status", "FAILED")),
        original_sql=data.get("original_sql", ""),
        converted_sql=data.get("converted_sql", ""),
        transformations_applied=transformations,
        warnings=data.get("warnings", []),
        errors=data.get("errors", []),
    )


def build_transform_task(
    object_id: str,
    object_type: str,
    sql_content: str,
    schema_context: str = "",
    metadata_hint: str = "",
) -> str:
    """Build the user prompt for a single SQL transformation.

    Args:
        object_id: Identifier for the SQL object (e.g., mapper ID).
        object_type: Type of object (MAPPER, PROCEDURE, etc.).
        sql_content: The Oracle SQL content to convert.
        schema_context: Optional schema/type mapping context.
        metadata_hint: Optional PG column metadata for parameter casting.

    Returns:
        A formatted task string for the agent.
    """
    parts = [
        f"Convert the following Oracle {object_type} to PostgreSQL.",
        f"Object ID: {object_id}",
        "",
        "Apply the complete 4-Phase conversion methodology:",
        "  Phase 1: Structural Processing (schema removal, TABLE(), stored procs, DB links)",
        "  Phase 2: Syntax Standardisation (subquery aliases, JOIN syntax, hint removal)",
        "  Phase 3: PostgreSQL Transformation (all function/syntax mappings + parameter casting)",
        "  Phase 4: Final Validation (XML integrity, completeness check, MyBatis check)",
        "",
        "Oracle SQL:",
        "```",
        sql_content,
        "```",
    ]

    if schema_context:
        parts.extend([
            "",
            "Schema Context (type mappings):",
            schema_context,
        ])

    if metadata_hint:
        parts.extend([
            "",
            "PostgreSQL Column Metadata (for parameter casting):",
            metadata_hint,
        ])

    parts.extend([
        "",
        "Return the TransformResult as JSON.",
    ])

    return "\n".join(parts)
