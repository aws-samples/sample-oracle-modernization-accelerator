"""Agentic RAG tools for dynamic Oracle→PostgreSQL conversion knowledge retrieval.

Provides agents with the ability to search a knowledge base for conversion
patterns not covered by the static oracle_to_pg_reference rules. Uses
Amazon Bedrock Knowledge Base for retrieval when available, with fallback
to keyword-based search on a local knowledge index.

The learning loop:
1. Agent encounters unknown Oracle pattern
2. Static rules checked first (oracle_to_pg_reference)
3. If not found → RAG search via search_conversion_knowledge
4. If RAG finds a solution → agent applies it
5. On success → store_learned_pattern saves it for future static lookups
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError
from strands import tool

logger = logging.getLogger(__name__)

# Bedrock Knowledge Base ID (set via env or defaults to None for local fallback)
KB_ID = os.environ.get("OMA_KNOWLEDGE_BASE_ID")
KB_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")
MODEL_ARN = "arn:aws:bedrock:us-east-1::foundation-model/global.anthropic.claude-opus-4-6-v1"


# ---------------------------------------------------------------------------
# Local knowledge index (fallback when Bedrock KB is not configured)
# ---------------------------------------------------------------------------

_LOCAL_KNOWLEDGE: list[dict[str, str]] = [
    {
        "pattern": "CONNECT BY",
        "category": "hierarchical",
        "oracle": "SELECT ... FROM t START WITH condition CONNECT BY PRIOR parent = child",
        "postgresql": "WITH RECURSIVE cte AS (SELECT ... FROM t WHERE condition UNION ALL SELECT ... FROM t JOIN cte ON parent = child) SELECT * FROM cte",
        "notes": "CONNECT BY LEVEL for sequence generation: generate_series(1, N)",
    },
    {
        "pattern": "MERGE INTO",
        "category": "dml",
        "oracle": "MERGE INTO target USING source ON (condition) WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...",
        "postgresql": "INSERT INTO target SELECT ... FROM source ON CONFLICT (key) DO UPDATE SET ...",
        "notes": "PG 15+ supports MERGE natively. For older versions use INSERT...ON CONFLICT.",
    },
    {
        "pattern": "BULK COLLECT",
        "category": "plsql",
        "oracle": "SELECT col BULK COLLECT INTO v_array FROM t",
        "postgresql": "SELECT array_agg(col) INTO v_array FROM t",
        "notes": "Or use RETURN QUERY for set-returning functions.",
    },
    {
        "pattern": "FORALL",
        "category": "plsql",
        "oracle": "FORALL i IN v_array.FIRST..v_array.LAST INSERT INTO t VALUES(v_array(i))",
        "postgresql": "INSERT INTO t SELECT unnest(v_array)",
        "notes": "For UPDATE/DELETE, use standard FOR loop or unnest with lateral join.",
    },
    {
        "pattern": "DBMS_OUTPUT",
        "category": "plsql",
        "oracle": "DBMS_OUTPUT.PUT_LINE('message')",
        "postgresql": "RAISE NOTICE '%', 'message'",
        "notes": "RAISE levels: DEBUG, LOG, INFO, NOTICE, WARNING, EXCEPTION",
    },
    {
        "pattern": "DBMS_LOB",
        "category": "plsql",
        "oracle": "DBMS_LOB.GETLENGTH(clob_col), DBMS_LOB.SUBSTR(clob_col, len, pos)",
        "postgresql": "LENGTH(text_col), SUBSTRING(text_col FROM pos FOR len)",
        "notes": "PG TEXT is unbounded; no LOB management needed.",
    },
    {
        "pattern": "UTL_FILE",
        "category": "plsql",
        "oracle": "UTL_FILE.FOPEN, UTL_FILE.PUT_LINE, UTL_FILE.FCLOSE",
        "postgresql": "pg_read_file() for reading. For writing: use COPY TO or external scripts.",
        "notes": "PG has limited server-side file I/O. Consider moving file ops to application layer.",
    },
    {
        "pattern": "AUTONOMOUS_TRANSACTION",
        "category": "plsql",
        "oracle": "PRAGMA AUTONOMOUS_TRANSACTION; ... COMMIT;",
        "postgresql": "Use dblink for true autonomous transactions, or restructure into separate function call.",
        "notes": "PG has no autonomous transactions natively. dblink_exec() can simulate.",
    },
    {
        "pattern": "PIPELINED FUNCTION",
        "category": "plsql",
        "oracle": "CREATE FUNCTION f RETURN t PIPELINED IS BEGIN PIPE ROW(...); END;",
        "postgresql": "CREATE FUNCTION f() RETURNS SETOF t AS $$ BEGIN RETURN NEXT ...; END; $$ LANGUAGE plpgsql;",
        "notes": "Use RETURN NEXT or RETURN QUERY instead of PIPE ROW.",
    },
    {
        "pattern": "ROWNUM",
        "category": "sql",
        "oracle": "WHERE ROWNUM <= 10",
        "postgresql": "LIMIT 10 (at end of query)",
        "notes": "Complex ROWNUM patterns: use ROW_NUMBER() OVER() with CTE/subquery.",
    },
    {
        "pattern": "DECODE",
        "category": "functions",
        "oracle": "DECODE(expr, val1, result1, val2, result2, default)",
        "postgresql": "CASE WHEN expr = val1 THEN result1 WHEN expr = val2 THEN result2 ELSE default END",
        "notes": "DECODE treats NULL = NULL as true; CASE does not. Use IS NOT DISTINCT FROM for NULL-safe comparison.",
    },
    {
        "pattern": "NVL2",
        "category": "functions",
        "oracle": "NVL2(expr, not_null_result, null_result)",
        "postgresql": "CASE WHEN expr IS NOT NULL THEN not_null_result ELSE null_result END",
        "notes": "No direct PG equivalent. CASE WHEN is the standard pattern.",
    },
    {
        "pattern": "SYS_CONTEXT",
        "category": "functions",
        "oracle": "SYS_CONTEXT('USERENV', 'SESSION_USER')",
        "postgresql": "current_setting('session_authorization') or SESSION_USER",
        "notes": "Map SYS_CONTEXT attributes: SESSION_USER, IP_ADDRESS → inet_client_addr(), etc.",
    },
    {
        "pattern": "EMPTY_CLOB",
        "category": "functions",
        "oracle": "EMPTY_CLOB(), EMPTY_BLOB()",
        "postgresql": "'' (empty string) or ''::bytea",
        "notes": "Oracle uses LOB locators; PG uses direct values.",
    },
    {
        "pattern": "SEQUENCE.NEXTVAL",
        "category": "sequences",
        "oracle": "schema.SEQ_NAME.NEXTVAL",
        "postgresql": "nextval('seq_name')",
        "notes": "Always lowercase sequence names in PG. Remove schema prefix.",
    },
]


def _search_local(query: str, max_results: int = 5) -> list[dict]:
    """Search local knowledge index by keyword matching."""
    query_lower = query.lower()
    scored = []
    for entry in _LOCAL_KNOWLEDGE:
        score = 0
        for field in ["pattern", "category", "oracle", "notes"]:
            text = entry.get(field, "").lower()
            if query_lower in text:
                score += 10
            for word in query_lower.split():
                if word in text:
                    score += 1
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:max_results]]


# ---------------------------------------------------------------------------
# RAG tool (exposed to agents)
# ---------------------------------------------------------------------------

@tool
def search_conversion_knowledge(
    query: str,
    category: str = "",
    max_results: int = 5,
) -> str:
    """Search the Oracle→PostgreSQL conversion knowledge base.

    Use this when oracle_to_pg_reference doesn't have the answer for a specific
    Oracle construct. Searches Bedrock Knowledge Base (if configured) or falls
    back to a curated local index.

    Args:
        query: The Oracle pattern or error to search for (e.g., "CONNECT BY LEVEL",
               "DBMS_SCHEDULER", "autonomous transaction").
        category: Optional filter: "sql", "plsql", "functions", "ddl", "sequences".
        max_results: Number of results to return (default 5).

    Returns:
        JSON array of matching conversion patterns with oracle/postgresql examples.
    """
    results = []

    # Try Bedrock Knowledge Base first
    if KB_ID:
        try:
            client = boto3.client("bedrock-agent-runtime", region_name=KB_REGION)
            response = client.retrieve(
                knowledgeBaseId=KB_ID,
                retrievalQuery={"text": f"Oracle to PostgreSQL conversion: {query}"},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results,
                    }
                },
            )
            for result in response.get("retrievalResults", []):
                content = result.get("content", {}).get("text", "")
                score = result.get("score", 0)
                source = result.get("location", {}).get("s3Location", {}).get("uri", "")
                results.append({
                    "content": content,
                    "relevance_score": score,
                    "source": source,
                })
            if results:
                logger.info("Bedrock KB returned %d results for: %s", len(results), query)
                return json.dumps(results, indent=2)
        except ClientError as e:
            logger.warning("Bedrock KB query failed, falling back to local: %s", e)

    # Fallback: local knowledge index
    local_results = _search_local(query, max_results)
    if category:
        local_results = [r for r in local_results if r.get("category") == category] or local_results

    if not local_results:
        return json.dumps({
            "message": f"No conversion pattern found for '{query}'. "
                       "Try breaking down the Oracle construct into smaller parts.",
            "suggestion": "Check oracle_to_pg_reference with specific function/type names.",
        })

    logger.info("Local index returned %d results for: %s", len(local_results), query)
    return json.dumps(local_results, indent=2)


@tool
def store_learned_pattern(
    oracle_pattern: str,
    postgresql_equivalent: str,
    category: str,
    notes: str = "",
) -> str:
    """Store a newly learned conversion pattern for future RAG lookups.

    Call this AFTER successfully converting an Oracle pattern that wasn't in
    the static rules. This creates a learning loop: the pattern is stored in
    DynamoDB and added to the local index for immediate reuse.

    Args:
        oracle_pattern: The Oracle SQL/PL-SQL pattern (e.g., "DBMS_SCHEDULER.CREATE_JOB").
        postgresql_equivalent: The correct PostgreSQL conversion.
        category: Pattern category: "sql", "plsql", "functions", "ddl", "sequences".
        notes: Additional context or caveats about this conversion.

    Returns:
        Confirmation message.
    """
    import time

    # Add to local index immediately
    new_entry = {
        "pattern": oracle_pattern,
        "category": category,
        "oracle": oracle_pattern,
        "postgresql": postgresql_equivalent,
        "notes": notes,
    }
    _LOCAL_KNOWLEDGE.append(new_entry)

    # Persist to DynamoDB pattern memory
    try:
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
        table = dynamodb.Table("oma-pattern-memory")
        table.put_item(Item={
            "error_signature": f"RAG:{oracle_pattern}",
            "timestamp": int(time.time() * 1000),
            "pattern_type": category,
            "oracle_pattern": oracle_pattern,
            "postgresql_equivalent": postgresql_equivalent,
            "notes": notes,
            "source_database": "learned",
            "success_rate": 1,
            "usage_count": 1,
            "ttl": int(time.time()) + 86400 * 365,  # 1 year TTL
        })
        logger.info("Stored learned pattern: %s → %s", oracle_pattern, postgresql_equivalent[:50])
        return json.dumps({
            "status": "stored",
            "pattern": oracle_pattern,
            "message": "Pattern stored in DynamoDB and local index for future reuse.",
        })
    except ClientError as e:
        logger.warning("Failed to persist pattern to DynamoDB: %s", e)
        return json.dumps({
            "status": "partial",
            "pattern": oracle_pattern,
            "message": "Pattern added to local index but DynamoDB persistence failed.",
        })
