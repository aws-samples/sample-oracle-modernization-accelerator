"""
Migration Analysis and Reporting MCP Tools

Tools for computing migration metrics, running comparative SQL tests,
and generating migration reports.
"""

import logging
import os
import json
import asyncio
import threading
import sys
from typing import Dict, List, Optional
from datetime import datetime
import oracledb
from strands import tool

logger = logging.getLogger(__name__)

# Determine target database from sys.path
_is_mysql = any('mysql' in p for p in sys.path)
_is_postgresql = any('postgresql' in p for p in sys.path)

if _is_mysql:
    import aiomysql
    _TARGET_DB_TYPE = "mysql"
elif _is_postgresql:
    import asyncpg
    _TARGET_DB_TYPE = "postgresql"
else:
    # Default to PostgreSQL for backward compatibility
    import asyncpg
    _TARGET_DB_TYPE = "postgresql"


async def _get_target_db_connection():
    """Get connection to target database (PostgreSQL or MySQL) based on environment."""
    if _TARGET_DB_TYPE == "mysql":
        conn = await aiomysql.connect(
            host=os.environ.get('OMA_MYSQL_HOST', 'localhost'),
            port=int(os.environ.get('OMA_MYSQL_PORT', '3306')),
            db=os.environ.get('OMA_MYSQL_DATABASE'),
            user=os.environ.get('OMA_MYSQL_USER'),
            password=os.environ.get('OMA_MYSQL_PASSWORD'),
            autocommit=False
        )
        return conn
    else:
        # PostgreSQL
        conn = await asyncpg.connect(
            host=os.environ.get('PGHOST', 'localhost'),
            port=int(os.environ.get('PGPORT', '5432')),
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD')
        )
        return conn


def _run_async(coro):
    """Run an async coroutine safely, whether or not an event loop is running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        result = [None]
        exception = [None]

        def _thread_target():
            try:
                result[0] = asyncio.run(coro)
            except Exception as e:
                exception[0] = e

        t = threading.Thread(target=_thread_target)
        t.start()
        t.join()
        if exception[0] is not None:
            raise exception[0]
        return result[0]
    else:
        return asyncio.run(coro)

from common.rules.rule_engine import RuleEngine


@tool
def apply_static_rules(oracle_sql: str) -> str:
    """
    Apply static Oracle-to-PostgreSQL transformation rules to SQL.

    Converts Oracle-specific functions, syntax, and data types to PostgreSQL
    equivalents using deterministic rule-based mappings. Handles:
    - String concatenation (|| -> CONCAT)
    - Function mappings (NVL->COALESCE, SYSDATE->CURRENT_TIMESTAMP, etc.)
    - Syntax conversions (FROM DUAL removal, ROWNUM->LIMIT, etc.)
    - Sequence syntax (seq.NEXTVAL -> nextval('seq'))

    Args:
        oracle_sql: The Oracle SQL text to transform

    Returns:
        JSON string with transformation results. Format:
        {
            "success": true,
            "original_sql": "SELECT NVL(x,0) FROM DUAL",
            "transformed_sql": "SELECT COALESCE(x,0)",
            "rules_applied": [{"rule_name": "NVL", "original": "NVL(", "transformed": "COALESCE("}],
            "rules_applied_count": 1,
            "complexity": "SIMPLE",
            "remaining_oracle_patterns": []
        }

    Example:
        >>> apply_static_rules("SELECT NVL(salary, 0) FROM employees")
    """
    try:
        engine = RuleEngine()
        transformed_sql, applied_rules = engine.apply_static_rules(oracle_sql)

        complexity = engine.assess_complexity(oracle_sql)
        remaining = engine.detect_remaining_oracle_patterns(transformed_sql)

        rules_list = [
            {
                "rule_name": r.rule_name,
                "rule_type": r.rule_type,
                "original": r.original,
                "transformed": r.transformed,
            }
            for r in applied_rules
        ]

        return json.dumps({
            "success": True,
            "original_sql": oracle_sql,
            "transformed_sql": transformed_sql,
            "rules_applied": rules_list,
            "rules_applied_count": len(rules_list),
            "complexity": complexity.value,
            "remaining_oracle_patterns": remaining,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })


@tool
def compute_coverage_score(total_objects: int, converted_objects: int, failed_objects: int) -> str:
    """
    Compute migration coverage score.

    Coverage formula:
        coverage = (converted_objects / total_objects) * 100

    Args:
        total_objects: Total number of objects to migrate
        converted_objects: Number of successfully converted objects
        failed_objects: Number of objects that failed conversion

    Returns:
        JSON string with coverage metrics. Format:
        {
            "success": true,
            "total_objects": 150,
            "converted_objects": 120,
            "failed_objects": 30,
            "coverage_percentage": 80.0,
            "conversion_rate": 0.8,
            "grade": "B+"
        }

    Example:
        >>> compute_coverage_score(150, 120, 30)
    """
    try:
        if total_objects <= 0:
            return json.dumps({
                "success": False,
                "error": "total_objects must be greater than 0"
            })

        coverage_percentage = (converted_objects / total_objects) * 100
        conversion_rate = converted_objects / total_objects

        # Assign grade
        if coverage_percentage >= 95:
            grade = "A+"
        elif coverage_percentage >= 90:
            grade = "A"
        elif coverage_percentage >= 85:
            grade = "A-"
        elif coverage_percentage >= 80:
            grade = "B+"
        elif coverage_percentage >= 75:
            grade = "B"
        elif coverage_percentage >= 70:
            grade = "B-"
        elif coverage_percentage >= 65:
            grade = "C+"
        elif coverage_percentage >= 60:
            grade = "C"
        else:
            grade = "F"

        return json.dumps({
            "success": True,
            "total_objects": total_objects,
            "converted_objects": converted_objects,
            "failed_objects": failed_objects,
            "coverage_percentage": round(coverage_percentage, 2),
            "conversion_rate": round(conversion_rate, 4),
            "grade": grade
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool
def compute_equivalence_score(test_results: str) -> str:
    """
    Compute semantic equivalence score from QA test results.

    Args:
        test_results: JSON string with test results in format:
            [
                {"test_id": "test_1", "passed": true, "oracle_result": [...], "pg_result": [...]},
                {"test_id": "test_2", "passed": false, "error": "..."},
                ...
            ]

    Returns:
        JSON string with equivalence metrics. Format:
        {
            "success": true,
            "total_tests": 50,
            "passed_tests": 45,
            "failed_tests": 5,
            "equivalence_percentage": 90.0,
            "grade": "A"
        }

    Example:
        >>> compute_equivalence_score('[{"test_id": "t1", "passed": true}, ...]')
    """
    try:
        tests = json.loads(test_results)

        if not isinstance(tests, list):
            return json.dumps({
                "success": False,
                "error": "test_results must be a JSON array"
            })

        total_tests = len(tests)
        if total_tests == 0:
            return json.dumps({
                "success": False,
                "error": "No tests provided"
            })

        passed_tests = sum(1 for test in tests if test.get("passed", False))
        failed_tests = total_tests - passed_tests

        equivalence_percentage = (passed_tests / total_tests) * 100

        # Assign grade
        if equivalence_percentage >= 95:
            grade = "A+"
        elif equivalence_percentage >= 90:
            grade = "A"
        elif equivalence_percentage >= 85:
            grade = "A-"
        elif equivalence_percentage >= 80:
            grade = "B+"
        elif equivalence_percentage >= 75:
            grade = "B"
        elif equivalence_percentage >= 70:
            grade = "B-"
        elif equivalence_percentage >= 65:
            grade = "C+"
        elif equivalence_percentage >= 60:
            grade = "C"
        else:
            grade = "F"

        return json.dumps({
            "success": True,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "equivalence_percentage": round(equivalence_percentage, 2),
            "grade": grade
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool
def execute_sql_comparison(oracle_sql: str, pg_sql: str, bind_vars: str) -> str:
    """
    Execute SQL on both Oracle and PostgreSQL, compare results for semantic equivalence.

    Args:
        oracle_sql: SQL query for Oracle
        pg_sql: Converted SQL query for PostgreSQL
        bind_vars: JSON string with bind variables in format:
            {"var1": "value1", "var2": 123, ...}

    Returns:
        JSON string with comparison results. Format:
        {
            "success": true,
            "equivalent": true,
            "oracle_result": {"rows": [...], "row_count": 5},
            "pg_result": {"rows": [...], "row_count": 5},
            "differences": []
        }

    Example:
        >>> execute_sql_comparison(
        ...     "SELECT * FROM emp WHERE empno = :id",
        ...     "SELECT * FROM emp WHERE empno = $1",
        ...     '{"id": 7369}'
        ... )
    """
    async def _compare():
        try:
            # Parse bind variables
            try:
                bind_dict = json.loads(bind_vars) if bind_vars else {}
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid bind_vars JSON: {str(e)}"
                })

            # Execute on Oracle
            oracle_result = None
            try:
                ora_host = os.environ.get('ORACLE_HOST')
                ora_port = os.environ.get('ORACLE_PORT', '1521')
                ora_service = os.environ.get('ORACLE_SERVICE_NAME')
                ora_sid = os.environ.get('ORACLE_SID')

                if ora_service:
                    dsn = oracledb.makedsn(ora_host, ora_port, service_name=ora_service)
                elif ora_sid:
                    dsn = oracledb.makedsn(ora_host, ora_port, sid=ora_sid)
                else:
                    return json.dumps({
                        "success": False,
                        "error": "Neither ORACLE_SERVICE_NAME nor ORACLE_SID is set"
                    })

                oracle_conn = oracledb.connect(
                    user=os.environ.get('ORACLE_USER'),
                    password=os.environ.get('ORACLE_PASSWORD'),
                    dsn=dsn,
                )
                cursor = oracle_conn.cursor()

                # Convert bind vars for Oracle
                cursor.execute(oracle_sql, bind_dict)
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

                oracle_result = {
                    "rows": rows,
                    "row_count": len(rows),
                    "columns": columns
                }

                cursor.close()
                oracle_conn.close()

            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Oracle execution failed: {str(e)}"
                })

            # Execute on target database
            target_result = None
            try:
                target_conn = await _get_target_db_connection()

                if _TARGET_DB_TYPE == "mysql":
                    # MySQL uses ? placeholders and cursor
                    async with target_conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute(pg_sql, list(bind_dict.values()))
                        target_rows = await cursor.fetchall()

                    rows = [dict(row) for row in target_rows]
                    columns = list(rows[0].keys()) if rows else []
                    target_conn.close()
                else:
                    # PostgreSQL uses $1, $2 placeholders
                    bind_values = list(bind_dict.values())
                    target_rows = await target_conn.fetch(pg_sql, *bind_values)

                    rows = [dict(row) for row in target_rows]
                    columns = list(rows[0].keys()) if rows else []
                    await target_conn.close()

                target_result = {
                    "rows": rows,
                    "row_count": len(rows),
                    "columns": columns
                }

            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Target database execution failed: {str(e)}"
                })

            # Compare results
            differences = []

            # Check row counts
            if oracle_result["row_count"] != target_result["row_count"]:
                differences.append({
                    "type": "row_count_mismatch",
                    "oracle": oracle_result["row_count"],
                    "target": target_result["row_count"]
                })

            # Check column names (case-insensitive)
            oracle_cols = [c.upper() for c in oracle_result["columns"]]
            target_cols = [c.upper() for c in target_result["columns"]]

            if set(oracle_cols) != set(target_cols):
                differences.append({
                    "type": "column_mismatch",
                    "oracle_columns": oracle_result["columns"],
                    "target_columns": target_result["columns"]
                })

            # Compare row data
            for i, (oracle_row, target_row) in enumerate(zip(oracle_result["rows"], target_result["rows"])):
                for col in oracle_result["columns"]:
                    oracle_val = str(oracle_row.get(col, ''))
                    target_val = str(target_row.get(col, ''))

                    if oracle_val != target_val:
                        differences.append({
                            "type": "value_mismatch",
                            "row": i,
                            "column": col,
                            "oracle_value": oracle_val,
                            "target_value": target_val
                        })

            equivalent = len(differences) == 0

            return json.dumps({
                "success": True,
                "equivalent": equivalent,
                "oracle_result": oracle_result,
                "pg_result": pg_result,
                "differences": differences,
                "difference_count": len(differences)
            }, default=str)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            })

    return _run_async(_compare())


@tool
def generate_bind_variables(sql: str, schema: str) -> str:
    """
    Auto-generate test bind variables based on SQL and schema metadata.

    Analyzes the SQL to find bind variable placeholders and queries the schema
    to generate realistic test values.

    Args:
        sql: SQL query with bind variables
        schema: Schema name to query for sample data

    Returns:
        JSON string with generated bind variables. Format:
        {
            "success": true,
            "bind_variables": {
                "empno": 7369,
                "deptno": 10,
                "ename": "SMITH"
            },
            "sql_with_values": "SELECT * FROM emp WHERE empno = 7369"
        }

    Example:
        >>> generate_bind_variables("SELECT * FROM emp WHERE empno = :empno", "HR")
    """
    try:
        # Extract bind variable names from SQL
        # Oracle style: :var_name
        # PostgreSQL style: $1, $2, etc.

        import re

        oracle_bind_pattern = r':(\w+)'
        pg_bind_pattern = r'\$(\d+)'

        oracle_vars = re.findall(oracle_bind_pattern, sql)
        pg_vars = re.findall(pg_bind_pattern, sql)

        if not oracle_vars and not pg_vars:
            return json.dumps({
                "success": False,
                "error": "No bind variables found in SQL"
            })

        # For now, generate simple default values based on naming conventions
        bind_variables = {}

        for var in oracle_vars:
            var_lower = var.lower()

            if 'id' in var_lower or 'no' in var_lower or 'num' in var_lower:
                bind_variables[var] = 1
            elif 'date' in var_lower or 'time' in var_lower:
                bind_variables[var] = "2024-01-01"
            elif 'name' in var_lower:
                bind_variables[var] = "TEST"
            elif 'flag' in var_lower or 'status' in var_lower:
                bind_variables[var] = "Y"
            else:
                bind_variables[var] = "VALUE"

        # Create SQL with substituted values
        sql_with_values = sql
        for var, value in bind_variables.items():
            if isinstance(value, str):
                sql_with_values = sql_with_values.replace(f":{var}", f"'{value}'")
            else:
                sql_with_values = sql_with_values.replace(f":{var}", str(value))

        return json.dumps({
            "success": True,
            "bind_variables": bind_variables,
            "sql_with_values": sql_with_values,
            "variable_count": len(bind_variables)
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool
def generate_html_report(migration_data: str) -> str:
    """
    Generate comprehensive HTML migration report with all pipeline details.

    Produces a self-contained HTML report covering all pipeline stages including
    data migration and data verification:
    - Executive summary with verdict badge and key metric cards
    - 5-dimension radar chart (SVG) with threshold line
    - Pipeline execution timeline with node-by-node progress
    - Source discovery and object inventory
    - Conversion details with side-by-side Oracle/PostgreSQL diffs
    - QA verification results (4-level: syntax, execution, cross-DB, edge case)
    - 5-dimension evaluation with weighted scores and bar visualizations
    - Remediation history with before/after diffs
    - Data migration results (per-table row counts, success/failure)
    - Data verification results (FK integrity, sequence sync, sample data)
    - Token usage visualization (per-node bar chart)
    - Performance baselines
    - Risk register and recommendations

    Args:
        migration_data: JSON string with full migration pipeline data including
            data_migration and data_verification sections.

    Returns:
        JSON string with report generation result:
        {"success": true, "report_path": "...", "report_size": 12345,
         "report_filename": "...", "sections_generated": [...]}
    """
    try:
        try:
            data = json.loads(migration_data)
        except Exception as e:
            return json.dumps({"success": False, "error": f"Invalid JSON: {e}"})

        project_name = data.get("project_name", "OMA Migration")
        migration_id = data.get("migration_id", "N/A")
        migration_date = data.get("migration_date", datetime.now().strftime("%Y-%m-%d"))
        source = data.get("source", {})
        target = data.get("target", {})
        verdict = data.get("verdict", "N/A")
        readiness_score = data.get("readiness_score", 0)
        scores = data.get("scores", {})
        pipeline_nodes = data.get("pipeline_nodes", [])
        discovery = data.get("discovery", {})
        conversions = data.get("conversions", [])
        verification = data.get("verification", {})
        evaluation = data.get("evaluation", {})
        remediation = data.get("remediation", {})
        data_migration = data.get("data_migration", {})
        data_verification = data.get("data_verification", {})
        perf_baselines = data.get("performance_baselines", [])
        metrics = data.get("metrics", {})
        migration_overview = data.get("migration_overview", {})

        sections_generated = []

        # --- Helper: escape HTML ---
        def esc(text: str) -> str:
            return (str(text).replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))

        # --- Verdict colour ---
        verdict_upper = str(verdict).upper()
        if verdict_upper == "GO":
            verdict_color, verdict_bg = "#22c55e", "rgba(34,197,94,0.15)"
        elif verdict_upper == "CONDITIONAL":
            verdict_color, verdict_bg = "#eab308", "rgba(234,179,8,0.15)"
        else:
            verdict_color, verdict_bg = "#ef4444", "rgba(239,68,68,0.15)"

        # --- Build HTML ---
        html = []
        html.append(f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(project_name)} - Migration Report</title>
<style>
:root {{
  --primary: #3b82f6; --primary-dark: #2563eb; --accent: #60a5fa;
  --go: #22c55e; --nogo: #ef4444; --cond: #eab308; --skip: #64748b;
  --bg: #0f172a; --card: #1e293b; --card2: #283548;
  --text: #e2e8f0; --muted: #94a3b8;
  --border: #334155; --code-bg: #0c1222; --code-text: #e2e8f0;
  --shadow: 0 1px 3px rgba(0,0,0,0.3), 0 4px 12px rgba(0,0,0,0.2);
  --shadow-lg: 0 4px 20px rgba(0,0,0,0.3), 0 8px 32px rgba(0,0,0,0.25);
  --mono: 'SF Mono','Fira Code','Cascadia Code',monospace;
  --sans: -apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.7;
  max-width: 1440px; margin: 0 auto; padding: 32px;
  font-size: 15px;
}}
h1 {{ font-size: 2.2em; font-weight: 800; letter-spacing: -0.02em; }}
h2 {{
  font-size: 1.35em; font-weight: 700; color: var(--text);
  margin-bottom: 20px; padding-bottom: 12px;
  border-bottom: 2px solid var(--primary); letter-spacing: -0.01em;
  display: flex; align-items: center; gap: 10px;
}}
h2::before {{ font-size: 0.8em; opacity: 0.6; }}
h3 {{ font-size: 1.05em; font-weight: 600; color: var(--text); margin: 20px 0 10px; }}

/* Navigation */
.nav {{
  position: sticky; top: 0; z-index: 100; background: rgba(255,255,255,0.95);
  backdrop-filter: blur(8px); border-bottom: 1px solid var(--border);
  padding: 12px 24px; margin: -32px -32px 24px; border-radius: 0;
  display: flex; gap: 6px; overflow-x: auto; flex-wrap: wrap;
}}
.nav a {{
  text-decoration: none; font-size: 0.82em; font-weight: 500; color: var(--muted);
  padding: 6px 14px; border-radius: 8px; white-space: nowrap;
  transition: all 0.15s;
}}
.nav a:hover {{ color: var(--primary-dark); background: #f1f5f9; }}

/* Header */
.header {{
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #6b21a8 100%);
  color: #fff; padding: 48px; border-radius: 20px; margin-bottom: 28px;
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 24px; box-shadow: var(--shadow-lg);
  position: relative; overflow: hidden;
}}
.header::before {{
  content: ''; position: absolute; top: -50%; right: -20%; width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
  pointer-events: none;
}}
.header-left {{ position: relative; z-index: 1; }}
.header-left h1 {{ margin-bottom: 12px; text-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.header-left p {{ opacity: 0.9; font-size: 0.92em; line-height: 1.8; }}
.verdict-badge {{
  font-size: 2.8em; font-weight: 900; padding: 20px 40px;
  border-radius: 16px; text-align: center; line-height: 1.2;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; z-index: 1;
}}
.verdict-badge small {{ display: block; font-size: 0.32em; font-weight: 500; opacity: 0.85; margin-top: 4px; }}

/* Cards grid */
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }}
.card {{
  background: var(--card); padding: 24px; border-radius: 16px;
  box-shadow: var(--shadow); border-left: 4px solid var(--primary);
  transition: transform 0.15s, box-shadow 0.15s;
}}
.card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-lg); }}
.card-value {{ font-size: 2.2em; font-weight: 800; color: var(--primary); letter-spacing: -0.02em; }}
.card-label {{ font-size: 0.78em; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; margin-bottom: 6px; }}
.card-detail {{ font-size: 0.85em; color: var(--muted); margin-top: 6px; }}

/* Section */
.section {{
  background: var(--card); padding: 32px; border-radius: 16px;
  box-shadow: var(--shadow); margin-bottom: 24px;
}}

/* Table */
table {{ width: 100%; border-collapse: collapse; font-size: 0.88em; }}
th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }}
th {{
  background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.8em;
  text-transform: uppercase; letter-spacing: 0.8px; position: sticky; top: 0;
}}
tr:hover {{ background: #f8fafc; }}
tbody tr {{ transition: background 0.1s; }}

/* Status badges */
.badge {{
  display: inline-block; padding: 4px 12px; border-radius: 24px;
  font-size: 0.75em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
}}
.badge-pass {{ background: #ecfdf5; color: var(--go); }}
.badge-fail {{ background: #fef2f2; color: var(--nogo); }}
.badge-skip {{ background: #f9fafb; color: var(--skip); }}
.badge-fixed {{ background: #eff6ff; color: #2563eb; }}
.badge-escalated {{ background: #fffbeb; color: var(--cond); }}
.badge-completed {{ background: #ecfdf5; color: var(--go); }}
.badge-success {{ background: #ecfdf5; color: var(--go); }}
.badge-warning {{ background: #fffbeb; color: var(--cond); }}

/* Code block */
.code-block {{
  background: var(--code-bg); color: var(--code-text);
  padding: 18px 20px; border-radius: 12px; overflow-x: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.82em; line-height: 1.6; white-space: pre-wrap; word-break: break-word;
  margin: 10px 0; border: 1px solid #334155;
}}

/* Diff */
.diff-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 10px 0; }}
.diff-panel {{ border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }}
.diff-header {{ padding: 10px 16px; font-size: 0.82em; font-weight: 700; letter-spacing: 0.5px; }}
.diff-oracle .diff-header {{ background: #fff7ed; color: #c2410c; }}
.diff-pg .diff-header {{ background: #f0fdf4; color: #15803d; }}
.diff-panel .code-block {{ border-radius: 0; margin: 0; max-height: 320px; overflow-y: auto; border: none; }}

/* Radar chart */
.radar-container {{ display: flex; justify-content: center; padding: 24px 0; }}

/* Timeline */
.timeline {{ position: relative; padding: 20px 0; }}
.timeline-item {{
  display: flex; align-items: flex-start; gap: 16px; margin-bottom: 12px;
  padding: 16px 20px; background: #f8fafc; border-radius: 12px;
  border-left: 4px solid var(--primary); transition: background 0.15s;
}}
.timeline-item:hover {{ background: #f1f5f9; }}
.timeline-item.status-error {{ border-left-color: var(--nogo); background: #fef2f2; }}
.timeline-num {{
  width: 36px; height: 36px; border-radius: 50%; background: var(--primary);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.85em; flex-shrink: 0;
}}
.timeline-item.status-error .timeline-num {{ background: var(--nogo); }}
.timeline-body {{ flex: 1; }}
.timeline-title {{ font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }}
.timeline-meta {{ font-size: 0.82em; color: var(--muted); }}
.timeline-detail {{ font-size: 0.88em; margin-top: 6px; color: #334155; }}

/* Collapsible */
details {{ margin: 10px 0; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
details summary {{
  cursor: pointer; font-weight: 600; padding: 12px 16px; font-size: 0.92em;
  list-style: none; display: flex; align-items: center; gap: 8px;
  background: #f8fafc; transition: background 0.15s;
}}
details summary:hover {{ background: #f1f5f9; }}
details summary::before {{ content: "\\25B6"; font-size: 0.65em; transition: transform 0.2s; color: var(--muted); }}
details[open] summary::before {{ transform: rotate(90deg); }}
details[open] summary {{ border-bottom: 1px solid var(--border); }}
details > :not(summary) {{ padding: 0 16px; }}

/* Progress bar */
.progress-bar {{
  height: 8px; border-radius: 4px; background: #e2e8f0; overflow: hidden; margin: 4px 0;
}}
.progress-fill {{
  height: 100%; border-radius: 4px; transition: width 0.6s ease;
}}

/* Token bar chart */
.token-bar {{
  display: flex; align-items: center; gap: 8px; margin: 4px 0;
}}
.token-bar-label {{ font-size: 0.82em; width: 100px; text-align: right; font-weight: 500; }}
.token-bar-track {{ flex: 1; height: 24px; background: #f1f5f9; border-radius: 6px; overflow: hidden; position: relative; }}
.token-bar-fill {{ height: 100%; border-radius: 6px; display: flex; align-items: center; padding: 0 8px; font-size: 0.72em; font-weight: 600; color: #fff; min-width: fit-content; }}

/* Data table with row highlighting */
.data-table tr.row-success {{ background: #f0fdf4; }}
.data-table tr.row-fail {{ background: #fef2f2; }}
.data-table tr.row-mismatch {{ background: #fffbeb; }}

/* Two-column layout */
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}

/* Footer */
.footer {{
  text-align: center; padding: 32px; color: var(--muted); font-size: 0.82em;
  border-top: 1px solid var(--border); margin-top: 16px;
}}

/* Print */
@media print {{
  body {{ max-width: none; padding: 12px; font-size: 12px; }}
  .nav {{ display: none; }}
  .section {{ break-inside: avoid; box-shadow: none; border: 1px solid #ddd; padding: 16px; }}
  .header {{ background: #333 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; padding: 24px; }}
  .card {{ box-shadow: none; border: 1px solid #ddd; }}
  details {{ border: none; }}
  details[open] summary {{ border-bottom: 1px solid #ddd; }}
}}

/* Responsive */
@media (max-width: 768px) {{
  body {{ padding: 16px; }}
  .header {{ flex-direction: column; text-align: center; padding: 28px; }}
  .diff-container {{ grid-template-columns: 1fr; }}
  .cards {{ grid-template-columns: 1fr 1fr; }}
  .two-col {{ grid-template-columns: 1fr; }}
  .nav {{ margin: -16px -16px 16px; padding: 8px 12px; }}
}}

/* Language toggle */
.lang-toggle {{
  position: fixed; top: 16px; right: 24px; z-index: 200;
  display: flex; background: rgba(255,255,255,0.95); border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.12); overflow: hidden; border: 1px solid var(--border);
  backdrop-filter: blur(8px);
}}
.lang-btn {{
  padding: 8px 16px; font-size: 0.82em; font-weight: 600;
  cursor: pointer; border: none; background: transparent; color: var(--muted);
  transition: all 0.15s; white-space: nowrap;
}}
.lang-btn.active {{ background: var(--primary); color: #fff; }}
.lang-btn:hover:not(.active) {{ background: #f1f5f9; }}

/* Executive summary */
.exec-summary {{
  background: var(--card); padding: 32px; border-radius: 16px;
  box-shadow: var(--shadow); margin-bottom: 24px;
  border-left: 6px solid var(--primary);
}}
.exec-summary .verdict-meaning {{
  font-size: 1.15em; font-weight: 600; color: var(--text);
  margin: 16px 0 12px; padding: 16px 20px; border-radius: 12px;
}}
.exec-summary .verdict-meaning.go {{ background: #ecfdf5; border-left: 4px solid var(--go); }}
.exec-summary .verdict-meaning.nogo {{ background: #fef2f2; border-left: 4px solid var(--nogo); }}
.exec-summary .verdict-meaning.cond {{ background: #fffbeb; border-left: 4px solid var(--cond); }}
.exec-summary .key-findings {{ margin-top: 16px; }}
.exec-summary .key-findings li {{ margin-bottom: 8px; line-height: 1.6; }}
/* === Dark Theme Overrides === */
body {{ font-family: var(--sans); padding: 16px 24px; }}
.header {{ background: linear-gradient(135deg, #1e3a8a 0%, #312e81 50%, #1e1b4b 100%); }}
.header::before {{ background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 60%); }}
.nav {{ background: rgba(15,23,42,0.95); border-bottom-color: var(--border); }}
.nav a:hover {{ color: var(--accent); background: rgba(255,255,255,0.05); }}
th {{ background: var(--card2); color: var(--muted); }}
tr:hover {{ background: rgba(255,255,255,0.03); }}
.badge-pass,.badge-completed,.badge-success {{ background: rgba(34,197,94,0.15); color: var(--go); }}
.badge-fail {{ background: rgba(239,68,68,0.15); color: var(--nogo); }}
.badge-skip {{ background: rgba(148,163,184,0.1); color: var(--skip); }}
.badge-fixed {{ background: rgba(59,130,246,0.15); color: var(--accent); }}
.badge-escalated,.badge-warning {{ background: rgba(234,179,8,0.15); color: var(--cond); }}
.timeline-item {{ background: var(--card2); }}
.timeline-item:hover {{ background: rgba(255,255,255,0.05); }}
.timeline-item.status-error {{ background: rgba(239,68,68,0.1); }}
details {{ border-color: var(--border); }}
details summary {{ background: var(--card2); }}
details summary:hover {{ background: rgba(255,255,255,0.05); }}
details[open] summary {{ border-bottom-color: var(--border); }}
.progress-bar {{ background: rgba(255,255,255,0.1); }}
.token-bar-track {{ background: rgba(255,255,255,0.05); }}
.data-table tr.row-success {{ background: rgba(34,197,94,0.08); }}
.data-table tr.row-fail {{ background: rgba(239,68,68,0.08); }}
.data-table tr.row-mismatch {{ background: rgba(234,179,8,0.08); }}
.diff-oracle .diff-header {{ background: rgba(249,115,22,0.15); color: #fb923c; }}
.diff-pg .diff-header {{ background: rgba(34,197,94,0.15); color: #34d399; }}
.diff-panel .code-block {{ border: none; }}
.lang-toggle {{ background: rgba(30,41,59,0.95); border-color: var(--border); }}
.lang-btn {{ color: var(--muted); }}
.lang-btn:hover:not(.active) {{ background: rgba(255,255,255,0.05); }}
.exec-summary .verdict-meaning.go {{ background: rgba(34,197,94,0.1); }}
.exec-summary .verdict-meaning.nogo {{ background: rgba(239,68,68,0.1); }}
.exec-summary .verdict-meaning.cond {{ background: rgba(234,179,8,0.1); }}
.code-block {{ background: var(--code-bg); border-color: var(--border); }}
.footer {{ color: var(--muted); border-top-color: var(--border); }}
/* Inline style overrides for dark theme */
[style*="background:#f8fafc"] {{ background: var(--card2) !important; }}
[style*="background: #f8fafc"] {{ background: var(--card2) !important; }}
[style*="background:#f1f5f9"] {{ background: var(--border) !important; }}
[style*="background:#f0fdf4"] {{ background: rgba(34,197,94,0.1) !important; }}
[style*="background:#fef2f2"] {{ background: rgba(239,68,68,0.1) !important; }}
[style*="background:#fffbeb"] {{ background: rgba(234,179,8,0.1) !important; }}
[style*="background:#ecfdf5"] {{ background: rgba(34,197,94,0.1) !important; }}
[style*="background:#eff6ff"] {{ background: rgba(59,130,246,0.1) !important; }}
[style*="background:#eee"] {{ background: rgba(255,255,255,0.05) !important; }}
[style*="background: #eee"] {{ background: rgba(255,255,255,0.05) !important; }}
[style*="color:#166534"] {{ color: var(--go) !important; }}
[style*="color:#991b1b"] {{ color: var(--nogo) !important; }}
[style*="color:#92400e"] {{ color: var(--cond) !important; }}
/* === Tab Layout === */
.tabs {{ display: flex; gap: 2px; background: var(--card); border-radius: 10px 10px 0 0; padding: 4px 4px 0; border: 1px solid var(--border); border-bottom: none; margin-top: 16px; }}
.tab-btn {{ padding: 10px 24px; background: transparent; border: none; color: var(--muted); font-size: 13px; font-weight: 600; cursor: pointer; border-radius: 8px 8px 0 0; transition: all .2s; font-family: inherit; }}
.tab-btn:hover {{ color: var(--text); background: rgba(255,255,255,.05); }}
.tab-btn.active {{ color: var(--accent); background: var(--bg); border-bottom: 2px solid var(--primary); }}
.tab-content {{ display: none; padding: 20px 0; min-height: 400px; }}
.tab-content.active {{ display: block; }}
/* Print override for dark theme */
@media print {{
  body {{ background: #fff !important; color: #000 !important; }}
  .section {{ background: #fff !important; box-shadow: none; border: 1px solid #ddd; }}
  .header {{ background: #333 !important; }}
  .card {{ background: #fff !important; box-shadow: none; border: 1px solid #ddd; }}
  .tabs {{ display: none; }}
  .tab-content {{ display: block !important; }}
  th {{ background: #f5f5f5 !important; color: #333 !important; }}
  .code-block {{ background: #f5f5f5 !important; color: #000 !important; }}
}}
</style>
<script>
function setLang(lang) {{
  document.querySelectorAll('[data-ko]').forEach(el => {{
    el.textContent = el.getAttribute('data-' + lang);
  }});
  document.querySelectorAll('[data-ko-html]').forEach(el => {{
    el.innerHTML = el.getAttribute('data-' + lang + '-html');
  }});
  document.querySelectorAll('.lang-btn').forEach(b => {{
    b.classList.toggle('active', b.dataset.lang === lang);
  }});
  document.documentElement.lang = lang === 'ko' ? 'ko' : 'en';
  document.querySelectorAll('.ko-only').forEach(el => {{ el.style.display = lang === 'ko' ? '' : 'none'; }});
  document.querySelectorAll('.en-only').forEach(el => {{ el.style.display = lang === 'en' ? '' : 'none'; }});
  // Update tab button labels
  document.querySelectorAll('.tab-btn [data-ko]').forEach(el => {{
    el.textContent = el.getAttribute('data-' + lang);
  }});
}}
function switchTab(tabId) {{
  document.querySelectorAll('.tab-content').forEach(function(c) {{ c.classList.remove('active'); }});
  document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
  var el = document.getElementById('tab-' + tabId);
  if (el) el.classList.add('active');
  var btn = document.querySelector('.tab-btn[data-tab="' + tabId + '"]');
  if (btn) btn.classList.add('active');
}}
</script>
</head>
<body>
""")

        # === LANGUAGE TOGGLE ===
        html.append("""
<div class="lang-toggle">
  <button class="lang-btn active" data-lang="ko" onclick="setLang('ko')">한국어</button>
  <button class="lang-btn" data-lang="en" onclick="setLang('en')">English</button>
</div>
""")

        # === HEADER ===
        html.append(f"""
<div class="header">
  <div class="header-left">
    <div style="display:inline-block;padding:4px 14px;background:rgba(255,255,255,0.15);border-radius:6px;font-size:0.75em;font-weight:700;letter-spacing:1px;margin-bottom:8px">PHASE 1</div>
    <h1>{esc(project_name)}</h1>
    <p class="ko-only">Phase 1: 스키마 마이그레이션 리포트</p>
    <p class="en-only" style="display:none">Phase 1: Schema Migration Report</p>
    <p><span data-ko="마이그레이션 ID" data-en="Migration ID">마이그레이션 ID</span>: {esc(migration_id)}</p>
    <p><span data-ko="생성일" data-en="Generated">생성일</span>: {esc(migration_date)}</p>
    <p><span data-ko="소스" data-en="Source">소스</span>: {esc(source.get('type', 'Oracle'))} {esc(source.get('schema', ''))} @ {esc(source.get('host', 'N/A'))}</p>
    <p><span data-ko="타겟" data-en="Target">타겟</span>: {esc(target.get('type', 'PostgreSQL'))} {esc(target.get('database', ''))} @ {esc(target.get('host', 'N/A'))}</p>
  </div>
  <div class="verdict-badge" style="background:{verdict_bg}; color:{verdict_color};">
    {esc(verdict_upper)}
    <small><span data-ko="준비도 점수" data-en="Readiness Score">준비도 점수</span>: {readiness_score:.1f}/100</small>
  </div>
</div>
""")
        sections_generated.append("header")

        # === TABS ===
        html.append("""
<div class="tabs">
  <button class="tab-btn active" data-tab="overview" onclick="switchTab('overview')"><span data-ko="변환 현황" data-en="Overview">변환 현황</span></button>
  <button class="tab-btn" data-tab="objects" onclick="switchTab('objects')"><span data-ko="오브젝트" data-en="Objects">오브젝트</span></button>
  <button class="tab-btn" data-tab="data" onclick="switchTab('data')"><span data-ko="데이터" data-en="Data">데이터</span></button>
  <button class="tab-btn" data-tab="log" onclick="switchTab('log')"><span data-ko="로그" data-en="Log">로그</span></button>
</div>
""")
        html.append('<div class="tab-content active" id="tab-overview">')

        # === MIGRATION OVERVIEW (DMS SC + AI Agent breakdown) ===
        if migration_overview:
            mo_total = migration_overview.get("total_objects", 0)
            mo_dms = migration_overview.get("dms_sc_objects", 0)
            mo_agent = migration_overview.get("agent_objects", 0)
            mo_dms_pct = (mo_dms / mo_total * 100) if mo_total else 0
            mo_agent_pct = (mo_agent / mo_total * 100) if mo_total else 0
            mo_dms_details = migration_overview.get("dms_sc_details", "")
            mo_agent_details = migration_overview.get("agent_details", "")
            mo_p1_status = migration_overview.get("phase1_status", "")
            mo_p1_verdict = migration_overview.get("phase1_verdict", "")
            mo_p2_status = migration_overview.get("phase2_status", "")
            mo_p1_dur = migration_overview.get("phase1_duration_seconds", 0)
            mo_p2_dur = migration_overview.get("phase2_duration_seconds", 0)
            mo_total_dur = migration_overview.get("total_duration_seconds", 0)

            p1_badge = "badge-pass" if mo_p1_status.upper() in ("COMPLETED", "GO") else "badge-fail"
            p2_badge = "badge-pass" if mo_p2_status.upper() in ("PASS", "COMPLETED") else "badge-fail"
            v_badge = "badge-pass" if mo_p1_verdict.upper() == "GO" else "badge-warning" if mo_p1_verdict.upper() == "CONDITIONAL" else "badge-fail"

            html.append(f"""
<div class="section" id="overview" style="border-left:6px solid var(--primary);position:relative;overflow:hidden">
  <div style="position:absolute;top:0;right:0;width:200px;height:200px;background:radial-gradient(circle,rgba(102,126,234,0.06) 0%,transparent 70%);pointer-events:none"></div>
  <h2 data-ko="전체 변환 현황" data-en="Migration Overview">전체 변환 현황</h2>

  <!-- Total count hero -->
  <div style="text-align:center;margin:8px 0 24px">
    <div style="font-size:3.2em;font-weight:900;color:var(--primary);letter-spacing:-0.03em">{mo_total}</div>
    <div style="font-size:1.05em;color:var(--muted);font-weight:600" data-ko="전체 오브젝트 — 100% 변환 완료" data-en="Total Objects — 100% Converted">전체 오브젝트 — 100% 변환 완료</div>
  </div>

  <!-- Stacked bar -->
  <div style="height:36px;border-radius:10px;overflow:hidden;display:flex;margin-bottom:24px;box-shadow:inset 0 1px 3px rgba(0,0,0,0.1)">
    <div style="width:{mo_dms_pct:.1f}%;background:linear-gradient(135deg,#667eea,#4a5ecc);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:0.85em">
      DMS SC {mo_dms_pct:.1f}%
    </div>
    <div style="width:{mo_agent_pct:.1f}%;background:linear-gradient(135deg,#764ba2,#6b21a8);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:0.85em">
      AI {mo_agent_pct:.1f}%
    </div>
  </div>

  <!-- Two cards: DMS SC vs AI Agent -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px">
    <div class="card" style="border-left-color:#667eea;margin:0">
      <div class="card-label" data-ko="DMS SC 규칙 기반 자동 변환" data-en="DMS SC Rules-Based Auto-Conversion">DMS SC 규칙 기반 자동 변환</div>
      <div class="card-value" style="color:#667eea">{mo_dms}<span style="font-size:0.4em;color:var(--muted);margin-left:8px">({mo_dms_pct:.1f}%)</span></div>
      <div class="card-detail">{esc(mo_dms_details)}</div>
    </div>
    <div class="card" style="border-left-color:#764ba2;margin:0">
      <div class="card-label" data-ko="AI 에이전트 변환 (Opus 4.6)" data-en="AI Agent Conversion (Opus 4.6)">AI 에이전트 변환 (Opus 4.6)</div>
      <div class="card-value" style="color:#764ba2">{mo_agent}<span style="font-size:0.4em;color:var(--muted);margin-left:8px">({mo_agent_pct:.1f}%)</span></div>
      <div class="card-detail">{esc(mo_agent_details)}</div>
    </div>
  </div>

  <!-- Phase status row -->
  <div style="display:flex;gap:16px;flex-wrap:wrap">
    <div style="flex:1;min-width:200px;padding:16px 20px;background:#f8fafc;border-radius:12px;display:flex;align-items:center;gap:12px">
      <span style="font-size:1.5em">1</span>
      <div>
        <div style="font-weight:700;font-size:0.92em"><span data-ko="Phase 1: 스키마 마이그레이션" data-en="Phase 1: Schema Migration">Phase 1: 스키마 마이그레이션</span></div>
        <div style="font-size:0.82em;color:var(--muted)"><span class="badge {p1_badge}">{esc(mo_p1_status)}</span> <span class="badge {v_badge}">{esc(mo_p1_verdict)}</span>{f' &mdash; {mo_p1_dur/60:.0f}min' if mo_p1_dur else ''}</div>
      </div>
    </div>
    <div style="flex:1;min-width:200px;padding:16px 20px;background:#f8fafc;border-radius:12px;display:flex;align-items:center;gap:12px">
      <span style="font-size:1.5em">2</span>
      <div>
        <div style="font-weight:700;font-size:0.92em"><span data-ko="Phase 2: 데이터 이관 & 검증" data-en="Phase 2: Data Migration & Verification">Phase 2: 데이터 이관 & 검증</span></div>
        <div style="font-size:0.82em;color:var(--muted)"><span class="badge {p2_badge}">{esc(mo_p2_status)}</span>{f' &mdash; {mo_p2_dur/60:.0f}min' if mo_p2_dur else ''}</div>
      </div>
    </div>
    {f'<div style="display:flex;align-items:center;padding:0 12px;font-size:0.88em;color:var(--muted)"><span data-ko="총 소요 시간" data-en="Total Duration">총 소요 시간</span>: <strong style="margin-left:6px">{mo_total_dur/60:.0f}min</strong></div>' if mo_total_dur else ''}
  </div>
</div>
""")
            sections_generated.append("migration_overview")

        # === EXECUTIVE SUMMARY (KO/EN bilingual) ===
        verif_summary_exec = verification.get("summary", {})
        vp = verif_summary_exec.get("passed", 0)
        vt = verif_summary_exec.get("total", 0)
        vf = verif_summary_exec.get("failed", 0)
        rem_f_exec = remediation.get("fixed", 0)
        rem_t_exec = remediation.get("total_issues", 0)
        rem_esc = remediation.get("escalated", 0)
        cov_s = scores.get("coverage", 0)
        eqv_s = scores.get("equivalence", 0)
        crit_findings = evaluation.get("critical_findings", [])
        n_crit = len(crit_findings) if isinstance(crit_findings, list) else 0

        # Determine verdict meaning
        if verdict_upper == "GO":
            verdict_cls = "go"
            verdict_ko = "마이그레이션을 진행해도 됩니다. 모든 핵심 검증을 통과했으며, 잔여 이슈는 운영 중 후속 조치로 처리 가능합니다."
            verdict_en = "Migration is cleared to proceed. All critical validations passed. Remaining items can be addressed post-migration."
        elif verdict_upper == "CONDITIONAL":
            verdict_cls = "cond"
            verdict_ko = "조건부 승인 — 아래 필수 조치 항목을 해결한 후 진행할 수 있습니다. 에스컬레이션된 이슈에 대한 수동 검토가 필요합니다."
            verdict_en = "Conditional approval — proceed after resolving the mandatory action items below. Manual review required for escalated issues."
        else:
            verdict_cls = "nogo"
            verdict_ko = "마이그레이션을 진행할 수 없습니다. 심각한 품질 이슈가 발견되어 추가 보정 및 재평가가 필요합니다."
            verdict_en = "Migration cannot proceed. Critical quality issues found — additional remediation and re-evaluation required."

        html.append(f"""
<div class="exec-summary section" id="exec-summary">
  <h2 data-ko="Executive Summary — 마이그레이션 판정" data-en="Executive Summary — Migration Verdict">Executive Summary — 마이그레이션 판정</h2>
  <div class="verdict-meaning {verdict_cls}">
    <span class="ko-only">{esc(verdict_ko)}</span>
    <span class="en-only" style="display:none">{esc(verdict_en)}</span>
  </div>
  <div class="key-findings">
    <h3 data-ko="핵심 수치 요약" data-en="Key Numbers at a Glance">핵심 수치 요약</h3>
    <table style="font-size:0.92em">
      <tbody>
        <tr><td style="width:220px;font-weight:600" data-ko="최종 판정" data-en="Final Verdict">최종 판정</td>
            <td><span class="badge badge-{'pass' if verdict_upper == 'GO' else 'fail' if verdict_upper == 'NO_GO' else 'warning'}" style="font-size:1em">{esc(verdict_upper)}</span> &mdash; <strong>{readiness_score:.1f}/100</strong></td></tr>
        <tr><td style="font-weight:600" data-ko="검증 통과율" data-en="Verification Pass Rate">검증 통과율</td>
            <td><strong>{vp}/{vt}</strong> {'(' + f'{vp/vt*100:.0f}%' + ')' if vt else ''}{f' &mdash; <span style="color:var(--nogo)">{vf} failed</span>' if vf else ''}</td></tr>
        <tr><td style="font-weight:600" data-ko="자동 보정" data-en="Auto-Remediation">자동 보정</td>
            <td><strong>{rem_f_exec}/{rem_t_exec}</strong> <span data-ko="수정 완료" data-en="fixed">수정 완료</span>{f', <span style="color:var(--cond)">{rem_esc} escalated</span>' if rem_esc else ''}</td></tr>
        <tr><td style="font-weight:600" data-ko="Coverage / Equivalence" data-en="Coverage / Equivalence">Coverage / Equivalence</td>
            <td><strong>{cov_s}</strong> / <strong>{eqv_s}</strong> <span style="color:var(--muted)">(70+ {"="} threshold)</span></td></tr>
        <tr><td style="font-weight:600" data-ko="Critical Findings" data-en="Critical Findings">Critical Findings</td>
            <td><strong>{n_crit}</strong> <span data-ko="건" data-en="item(s)">건</span></td></tr>
      </tbody>
    </table>""")

        # Add critical findings list if any
        if crit_findings:
            html.append('<h3 style="margin-top:20px;color:var(--nogo)" data-ko="주의 필요 항목" data-en="Action Required">주의 필요 항목</h3><ol class="key-findings">')
            for cf in crit_findings[:5]:
                if isinstance(cf, dict):
                    title = cf.get("title", cf.get("finding", str(cf)))
                    html.append(f'<li>{esc(title)}</li>')
                else:
                    html.append(f'<li>{esc(str(cf))}</li>')
            html.append('</ol>')

        # Add escalated items if any
        esc_items = [f for f in remediation.get("fixes", []) if isinstance(f, dict) and f.get("status", "").upper() == "ESCALATED"]
        if esc_items:
            html.append(f'<h3 style="margin-top:16px;color:var(--cond)" data-ko="수동 조치 필요 ({len(esc_items)}건)" data-en="Manual Action Required ({len(esc_items)} items)">수동 조치 필요 ({len(esc_items)}건)</h3><ul>')
            for ei in esc_items[:5]:
                html.append(f'<li><strong>{esc(ei.get("object_name", ""))}</strong>: {esc(ei.get("issue", "")[:200])}</li>')
            html.append('</ul>')

        html.append('</div></div>')
        sections_generated.append("executive_summary")

        # === KEY METRICS CARDS ===
        total_duration = metrics.get("duration_seconds", 0)
        total_tokens = metrics.get("total_tokens", 0)
        total_objects = discovery.get("total_objects", 0)
        verif_summary = verification.get("summary", {})
        rem_fixed = remediation.get("fixed", 0)
        rem_total = remediation.get("total_issues", 0)
        dm_tables = data_migration.get("total_tables", 0)
        dm_rows = data_migration.get("total_rows_imported", data_migration.get("total_rows_oracle", 0))
        dm_success = data_migration.get("success_count", 0)
        dm_failed = data_migration.get("failed_count", 0)

        html.append(f"""
<div class="cards" id="metrics">
  <div class="card">
    <div class="card-label" data-ko="소스 오브젝트" data-en="Source Objects">소스 오브젝트</div>
    <div class="card-value">{total_objects}</div>
    <div class="card-detail" data-ko="Oracle 스키마 오브젝트" data-en="Oracle schema objects">Oracle 스키마 오브젝트</div>
  </div>
  <div class="card">
    <div class="card-label" data-ko="검증" data-en="Verification">검증</div>
    <div class="card-value">{verif_summary.get('passed', 0)}/{verif_summary.get('total', 0)}</div>
    <div class="card-detail" data-ko="통과 / 전체 테스트" data-en="Passed / Total tests">통과 / 전체 테스트</div>
  </div>
  <div class="card">
    <div class="card-label" data-ko="자동 보정" data-en="Remediation">자동 보정</div>
    <div class="card-value">{rem_fixed}/{rem_total}</div>
    <div class="card-detail" data-ko="자동 수정된 이슈" data-en="Auto-fixed issues">자동 수정된 이슈</div>
  </div>
  <div class="card" style="border-left-color:{'var(--go)' if dm_failed == 0 and dm_tables > 0 else 'var(--nogo)' if dm_failed > 0 else 'var(--skip)'}">
    <div class="card-label" data-ko="데이터 이관" data-en="Data Migrated">데이터 이관</div>
    <div class="card-value">{dm_rows:,}</div>
    <div class="card-detail">{dm_tables} <span data-ko="테이블" data-en="tables">테이블</span>, {dm_success} <span data-ko="성공" data-en="success">성공</span></div>
  </div>
  <div class="card">
    <div class="card-label" data-ko="소요 시간" data-en="Duration">소요 시간</div>
    <div class="card-value">{total_duration / 60:.0f}m</div>
    <div class="card-detail">{total_tokens:,} <span data-ko="토큰" data-en="tokens">토큰</span></div>
  </div>
  <div class="card">
    <div class="card-label" data-ko="준비도" data-en="Readiness">준비도</div>
    <div class="card-value" style="color:{verdict_color}">{readiness_score:.1f}</div>
    <div class="card-detail" data-ko="점수 / 100" data-en="Score / 100">점수 / 100</div>
  </div>
</div>
""")
        sections_generated.append("key_metrics")

        # === 5-DIMENSION RADAR CHART (SVG) ===
        cov = scores.get("coverage", 0)
        eqv = scores.get("equivalence", 0)
        perf = scores.get("performance", 0)
        sec = scores.get("security", 0)
        ops = scores.get("operational", 0)

        if any([cov, eqv, perf, sec, ops]):
            html.append(_build_radar_chart_svg(cov, eqv, perf, sec, ops, section_id="radar"))
            sections_generated.append("radar_chart")

        html.append('</div>')  # close tab-overview
        html.append('<div class="tab-content" id="tab-objects">')

        # === PIPELINE TIMELINE ===
        if pipeline_nodes:
            html.append('<div class="section" id="timeline"><h2 data-ko="파이프라인 실행 타임라인" data-en="Pipeline Execution Timeline">파이프라인 실행 타임라인</h2>')
            html.append('<div class="timeline">')
            for i, node in enumerate(pipeline_nodes, 1):
                node_id = node.get("id", "unknown")
                node_status = node.get("status", "UNKNOWN")
                duration = node.get("duration_seconds", 0)
                summary = node.get("summary", "")
                details = node.get("details", "")
                status_cls = "status-error" if "FAIL" in node_status.upper() or "ERROR" in node_status.upper() else ""
                badge_cls = "badge-completed" if node_status.upper() == "COMPLETED" else "badge-fail" if "FAIL" in node_status.upper() else "badge-skip"

                html.append(f"""
<div class="timeline-item {status_cls}">
  <div class="timeline-num">{i}</div>
  <div class="timeline-body">
    <div class="timeline-title">{esc(node_id)} <span class="badge {badge_cls}">{esc(node_status)}</span></div>
    <div class="timeline-meta">{duration:.0f}s ({duration/60:.1f}m)</div>
    <div class="timeline-detail">{esc(summary)}</div>
""")
                if details:
                    html.append(f"""    <details><summary><span data-ko="상세" data-en="Details">상세</span></summary>
    <div class="code-block">{esc(str(details)[:3000])}</div>
    </details>""")
                html.append('  </div>\n</div>')
            html.append('</div></div>')
            sections_generated.append("pipeline_timeline")

        # === DISCOVERY: OBJECT INVENTORY ===
        inventory = discovery.get("inventory", {})
        if inventory or total_objects:
            html.append('<div class="section" id="discovery"><h2 data-ko="소스 디스커버리 — 오브젝트 인벤토리" data-en="Source Discovery — Object Inventory">소스 디스커버리 — 오브젝트 인벤토리</h2>')
            oracle_features = discovery.get("oracle_features", [])
            if oracle_features:
                html.append(f'<p><strong><span data-ko="감지된 Oracle 전용 기능" data-en="Oracle-specific features detected">감지된 Oracle 전용 기능</span>:</strong> {esc(", ".join(oracle_features) if isinstance(oracle_features, list) else str(oracle_features))}</p>')

            if isinstance(inventory, dict) and inventory:
                html.append('<table><thead><tr><th data-ko="오브젝트 유형" data-en="Object Type">오브젝트 유형</th><th data-ko="개수" data-en="Count">개수</th><th data-ko="오브젝트" data-en="Objects">오브젝트</th></tr></thead><tbody>')
                for obj_type, obj_list in sorted(inventory.items()):
                    if isinstance(obj_list, list):
                        names = ", ".join(str(o.get("name", o) if isinstance(o, dict) else o) for o in obj_list[:10])
                        if len(obj_list) > 10:
                            names += f" ... (+{len(obj_list)-10} more)"
                        html.append(f'<tr><td><strong>{esc(obj_type)}</strong></td><td>{len(obj_list)}</td><td>{esc(names)}</td></tr>')
                    else:
                        html.append(f'<tr><td><strong>{esc(obj_type)}</strong></td><td>{esc(str(obj_list))}</td><td></td></tr>')
                html.append('</tbody></table>')
            html.append('</div>')
            sections_generated.append("discovery_inventory")

        # === CONVERSION DETAILS (with diffs) ===
        if conversions:
            html.append('<div class="section" id="conversions"><h2 data-ko="변환 상세" data-en="Conversion Details">변환 상세</h2>')
            success_count = sum(1 for c in conversions if c.get("status", "").upper() in ("SUCCESS", "TRANSFORMED"))
            fail_count = sum(1 for c in conversions if c.get("status", "").upper() in ("FAIL", "FAILED"))
            html.append(f'<p><span data-ko="전체" data-en="Total">전체</span>: {len(conversions)} <span data-ko="오브젝트" data-en="objects">오브젝트</span> &mdash; <span style="color:var(--go)">{success_count} <span data-ko="성공" data-en="success">성공</span></span>, <span style="color:var(--nogo)">{fail_count} <span data-ko="실패" data-en="failed">실패</span></span></p>')

            html.append('<table><thead><tr><th data-ko="오브젝트" data-en="Object">오브젝트</th><th data-ko="유형" data-en="Type">유형</th><th data-ko="상태" data-en="Status">상태</th><th data-ko="적용된 규칙" data-en="Rules Applied">적용된 규칙</th></tr></thead><tbody>')
            for conv in conversions:
                obj_name = conv.get("object_name", "N/A")
                obj_type = conv.get("object_type", "N/A")
                status = conv.get("status", "N/A")
                rules = conv.get("rules_applied", [])
                rules_count = len(rules) if isinstance(rules, list) else 0
                badge_cls = "badge-pass" if status.upper() in ("SUCCESS", "TRANSFORMED") else "badge-fail"
                html.append(f'<tr><td>{esc(obj_name)}</td><td>{esc(obj_type)}</td><td><span class="badge {badge_cls}">{esc(status)}</span></td><td>{rules_count}</td></tr>')
            html.append('</tbody></table>')

            # Show diffs for up to 20 conversions
            shown_diffs = [c for c in conversions if c.get("original_sql") and c.get("converted_sql")][:20]
            if shown_diffs:
                html.append('<h3 data-ko="코드 변환 비교" data-en="Code Conversion Diffs">코드 변환 비교</h3>')
                for conv in shown_diffs:
                    obj_name = conv.get("object_name", "N/A")
                    obj_type = conv.get("object_type", "")
                    rules = conv.get("rules_applied", [])
                    rules_str = ", ".join(
                        r.get("rule_name", r.get("rule", str(r))) if isinstance(r, dict) else str(r)
                        for r in (rules[:8] if isinstance(rules, list) else [])
                    )
                    html.append(f"""
<details>
<summary>{esc(obj_name)} ({esc(obj_type)}){f' &mdash; <span data-ko="적용 규칙" data-en="Rules">적용 규칙</span>: {esc(rules_str)}' if rules_str else ''}</summary>
<div class="diff-container">
  <div class="diff-panel diff-oracle"><div class="diff-header" data-ko="Oracle (원본)" data-en="Oracle (Original)">Oracle (원본)</div>
    <div class="code-block">{esc(str(conv.get("original_sql", ""))[:5000])}</div>
  </div>
  <div class="diff-panel diff-pg"><div class="diff-header" data-ko="PostgreSQL (변환됨)" data-en="PostgreSQL (Converted)">PostgreSQL (변환됨)</div>
    <div class="code-block">{esc(str(conv.get("converted_sql", ""))[:5000])}</div>
  </div>
</div>
</details>""")
            html.append('</div>')
            sections_generated.append("conversion_details")

        # === QA VERIFICATION RESULTS ===
        verif_results = verification.get("results", [])
        if verif_results or verif_summary:
            html.append('<div class="section" id="verification"><h2 data-ko="QA 검증 결과" data-en="QA Verification Results">QA 검증 결과</h2>')
            if verif_summary:
                total_v = verif_summary.get("total", 0)
                passed_v = verif_summary.get("passed", 0)
                failed_v = verif_summary.get("failed", 0)
                skipped_v = verif_summary.get("skipped", 0)
                pass_pct = (passed_v / total_v * 100) if total_v else 0
                html.append(f"""
<div class="cards" style="margin-bottom:16px">
  <div class="card" style="border-left-color:var(--go)"><div class="card-label" data-ko="통과" data-en="Passed">통과</div><div class="card-value" style="color:var(--go)">{passed_v}</div></div>
  <div class="card" style="border-left-color:var(--nogo)"><div class="card-label" data-ko="실패" data-en="Failed">실패</div><div class="card-value" style="color:var(--nogo)">{failed_v}</div></div>
  <div class="card" style="border-left-color:var(--skip)"><div class="card-label" data-ko="건너뜀" data-en="Skipped">건너뜀</div><div class="card-value" style="color:var(--skip)">{skipped_v}</div></div>
  <div class="card" style="border-left-color:var(--primary)"><div class="card-label" data-ko="통과율" data-en="Pass Rate">통과율</div><div class="card-value">{pass_pct:.1f}%</div></div>
</div>""")

            if verif_results:
                html.append('<table><thead><tr><th data-ko="오브젝트" data-en="Object">오브젝트</th><th data-ko="구문" data-en="Syntax">구문</th><th data-ko="실행" data-en="Execution">실행</th><th data-ko="교차 DB" data-en="Cross-DB">교차 DB</th><th data-ko="엣지 케이스" data-en="Edge Case">엣지 케이스</th><th data-ko="종합" data-en="Overall">종합</th><th data-ko="비고" data-en="Notes">비고</th></tr></thead><tbody>')
                for vr in verif_results:
                    obj_name = vr.get("object_name", vr.get("object_id", "N/A"))
                    levels = vr.get("levels", {})
                    overall = vr.get("overall", "N/A")
                    notes = vr.get("root_cause", vr.get("suggested_fix", ""))

                    def _level_badge(level_data):
                        if isinstance(level_data, dict):
                            r = level_data.get("result", "N/A")
                        elif isinstance(level_data, str):
                            r = level_data
                        else:
                            r = "N/A"
                        cls = "badge-pass" if r.upper() == "PASS" else "badge-fail" if r.upper() == "FAIL" else "badge-skip"
                        return f'<span class="badge {cls}">{esc(r)}</span>'

                    overall_cls = "badge-pass" if overall.upper() == "PASS" else "badge-fail" if overall.upper() == "FAIL" else "badge-skip"
                    html.append(f'<tr><td>{esc(obj_name)}</td>'
                                f'<td>{_level_badge(levels.get("syntax", "N/A"))}</td>'
                                f'<td>{_level_badge(levels.get("execution", "N/A"))}</td>'
                                f'<td>{_level_badge(levels.get("result_comparison", levels.get("cross_db", "N/A")))}</td>'
                                f'<td>{_level_badge(levels.get("edge_case", "N/A"))}</td>'
                                f'<td><span class="badge {overall_cls}">{esc(overall)}</span></td>'
                                f'<td style="font-size:0.85em">{esc(str(notes)[:200])}</td></tr>')
                html.append('</tbody></table>')
            html.append('</div>')
            sections_generated.append("verification_results")

        # === 5-DIMENSION EVALUATION ===
        eval_data = evaluation or {}
        if eval_data.get("scores") or scores:
            eval_scores = eval_data.get("scores", scores)
            html.append('<div class="section" id="evaluation"><h2 data-ko="5차원 품질 평가" data-en="5-Dimension Quality Evaluation">5차원 품질 평가</h2>')
            html.append('<table><thead><tr><th data-ko="차원" data-en="Dimension">차원</th><th data-ko="비중" data-en="Weight">비중</th><th data-ko="점수" data-en="Score">점수</th><th data-ko="가중" data-en="Weighted">가중</th><th data-ko="바" data-en="Bar">바</th></tr></thead><tbody>')
            dims = [
                ("커버리지", "Coverage", 0.25, eval_scores.get("coverage", cov)),
                ("동등성", "Equivalence", 0.30, eval_scores.get("equivalence", eqv)),
                ("성능", "Performance", 0.20, eval_scores.get("performance", perf)),
                ("보안", "Security", 0.15, eval_scores.get("security", sec)),
                ("운영", "Operational", 0.10, eval_scores.get("operational", ops)),
            ]
            for dim_ko, dim_en, weight, score in dims:
                weighted = score * weight
                bar_color = "var(--go)" if score >= 70 else "var(--cond)" if score >= 50 else "var(--nogo)"
                html.append(f'<tr><td><strong data-ko="{dim_ko}" data-en="{dim_en}">{dim_ko}</strong></td><td>{weight*100:.0f}%</td><td>{score}</td><td>{weighted:.1f}</td>'
                            f'<td><div style="background:#eee;border-radius:4px;height:20px;width:200px;position:relative">'
                            f'<div style="background:{bar_color};height:100%;width:{min(score,100)}%;border-radius:4px"></div></div></td></tr>')
            total_weighted = sum(s * w for _, _, w, s in dims)
            html.append(f'<tr style="font-weight:700;border-top:2px solid var(--primary)"><td data-ko="합계" data-en="Total">합계</td><td>100%</td><td></td><td>{total_weighted:.1f}</td><td></td></tr>')
            html.append('</tbody></table>')

            # Critical findings
            findings = eval_data.get("critical_findings", [])
            if findings:
                html.append('<h3 data-ko="치명적 발견사항" data-en="Critical Findings">치명적 발견사항</h3><table><thead><tr><th>ID</th><th data-ko="차원" data-en="Dimension">차원</th><th data-ko="발견사항" data-en="Finding">발견사항</th><th data-ko="심각도" data-en="Severity">심각도</th></tr></thead><tbody>')
                for f in findings:
                    if isinstance(f, dict):
                        html.append(f'<tr><td>{esc(f.get("id", ""))}</td><td>{esc(f.get("dimension", ""))}</td><td>{esc(f.get("title", f.get("finding", str(f))))}</td>'
                                    f'<td><span class="badge badge-fail">{esc(f.get("severity", ""))}</span></td></tr>')
                    else:
                        html.append(f'<tr><td></td><td></td><td>{esc(str(f))}</td><td></td></tr>')
                html.append('</tbody></table>')

            # Risk register
            risks = eval_data.get("risk_register", [])
            if risks:
                html.append('<h3 data-ko="리스크 레지스터" data-en="Risk Register">리스크 레지스터</h3><table><thead><tr><th data-ko="리스크" data-en="Risk">리스크</th><th data-ko="영향도" data-en="Impact">영향도</th><th data-ko="가능성" data-en="Likelihood">가능성</th><th data-ko="완화 방안" data-en="Mitigation">완화 방안</th></tr></thead><tbody>')
                for r in risks:
                    if isinstance(r, dict):
                        html.append(f'<tr><td>{esc(r.get("risk", str(r)))}</td><td>{esc(r.get("impact", ""))}</td>'
                                    f'<td>{esc(r.get("likelihood", ""))}</td><td>{esc(r.get("mitigation", ""))}</td></tr>')
                    else:
                        html.append(f'<tr><td>{esc(str(r))}</td><td></td><td></td><td></td></tr>')
                html.append('</tbody></table>')
            html.append('</div>')
            sections_generated.append("evaluation_scores")

        # === REMEDIATION HISTORY ===
        rem_fixes = remediation.get("fixes", [])
        if rem_fixes or rem_total:
            html.append('<div class="section" id="remediation"><h2 data-ko="자동 보정 이력" data-en="Remediation History">자동 보정 이력</h2>')
            html.append(f'<p><span data-ko="전체 이슈" data-en="Total Issues">전체 이슈</span>: {rem_total} &mdash; '
                        f'<span style="color:var(--go)"><span data-ko="수정됨" data-en="Fixed">수정됨</span>: {rem_fixed}</span>, '
                        f'<span data-ko="실패" data-en="Failed">실패</span>: {remediation.get("failed", 0)}, '
                        f'<span style="color:var(--cond)"><span data-ko="에스컬레이션" data-en="Escalated">에스컬레이션</span>: {remediation.get("escalated", 0)}</span></p>')

            if rem_fixes:
                html.append('<table><thead><tr><th>#</th><th data-ko="오브젝트" data-en="Object">오브젝트</th><th data-ko="이슈" data-en="Issue">이슈</th><th data-ko="전략" data-en="Strategy">전략</th><th data-ko="상태" data-en="Status">상태</th></tr></thead><tbody>')
                for i, fix in enumerate(rem_fixes, 1):
                    status = fix.get("status", "N/A")
                    badge_cls = "badge-fixed" if status.upper() == "FIXED" else "badge-escalated" if status.upper() == "ESCALATED" else "badge-fail"
                    html.append(f'<tr><td>{i}</td><td>{esc(fix.get("object_name", "N/A"))}</td>'
                                f'<td>{esc(fix.get("issue", "N/A"))}</td>'
                                f'<td>{esc(fix.get("strategy", fix.get("strategy_used", "N/A")))}</td>'
                                f'<td><span class="badge {badge_cls}">{esc(status)}</span></td></tr>')
                html.append('</tbody></table>')

                # Show before/after for fixes that have them
                shown_fixes = [f for f in rem_fixes if f.get("before") and f.get("after")][:10]
                if shown_fixes:
                    html.append('<h3 data-ko="수정 상세 (Before / After)" data-en="Fix Details (Before / After)">수정 상세 (Before / After)</h3>')
                    for fix in shown_fixes:
                        obj_name = fix.get("object_name", "N/A")
                        explanation = fix.get("explanation", fix.get("fix_details", {}).get("explanation", ""))
                        html.append(f"""
<details>
<summary>{esc(obj_name)} &mdash; {esc(fix.get("issue", ""))}</summary>
{f'<p style="color:var(--muted);margin:8px 0">{esc(explanation)}</p>' if explanation else ''}
<div class="diff-container">
  <div class="diff-panel diff-oracle"><div class="diff-header" data-ko="변경 전 (실패)" data-en="Before (Failed)">변경 전 (실패)</div>
    <div class="code-block">{esc(str(fix.get("before", ""))[:3000])}</div>
  </div>
  <div class="diff-panel diff-pg"><div class="diff-header" data-ko="변경 후 (수정됨)" data-en="After (Fixed)">변경 후 (수정됨)</div>
    <div class="code-block">{esc(str(fix.get("after", ""))[:3000])}</div>
  </div>
</div>
</details>""")
            html.append('</div>')
            sections_generated.append("remediation_history")

        html.append('</div>')  # close tab-objects
        html.append('<div class="tab-content" id="tab-data">')

        # === DATA MIGRATION RESULTS ===
        dm_tables_list = data_migration.get("tables", [])
        if dm_tables or dm_tables_list:
            html.append(f'<div class="section" id="data-migration"><h2 data-ko="데이터 이관 결과" data-en="Data Migration Results">데이터 이관 결과</h2>')
            dm_seqs = data_migration.get("sequences_synced", 0)
            dm_oracle_total = data_migration.get("total_rows_oracle", 0)
            dm_pg_total = data_migration.get("total_rows_imported", 0)
            dm_fidelity = (dm_pg_total / dm_oracle_total * 100) if dm_oracle_total > 0 else 0

            html.append(f"""
<div class="cards" style="margin-bottom:20px">
  <div class="card" style="border-left-color:var(--go)">
    <div class="card-label" data-ko="테이블" data-en="Tables">테이블</div>
    <div class="card-value">{dm_tables}</div>
    <div class="card-detail"><span data-ko="{dm_success}개 성공, {dm_failed}개 실패" data-en="{dm_success} success, {dm_failed} failed">{dm_success}개 성공, {dm_failed}개 실패</span></div>
  </div>
  <div class="card" style="border-left-color:var(--primary)">
    <div class="card-label" data-ko="Oracle 행 수" data-en="Oracle Rows">Oracle 행 수</div>
    <div class="card-value">{dm_oracle_total:,}</div>
    <div class="card-detail" data-ko="소스 합계" data-en="Source total">소스 합계</div>
  </div>
  <div class="card" style="border-left-color:var(--primary)">
    <div class="card-label" data-ko="PG 행 수" data-en="PG Rows">PG 행 수</div>
    <div class="card-value">{dm_pg_total:,}</div>
    <div class="card-detail" data-ko="타겟 합계" data-en="Target total">타겟 합계</div>
  </div>
  <div class="card" style="border-left-color:{'var(--go)' if dm_fidelity >= 100 else 'var(--nogo)'}">
    <div class="card-label" data-ko="데이터 정합성" data-en="Data Fidelity">데이터 정합성</div>
    <div class="card-value">{dm_fidelity:.1f}%</div>
    <div class="card-detail"><span data-ko="{dm_seqs}개 시퀀스 동기화" data-en="{dm_seqs} sequences synced">{dm_seqs}개 시퀀스 동기화</span></div>
  </div>
</div>""")

            if dm_tables_list:
                html.append('<table class="data-table"><thead><tr><th data-ko="테이블" data-en="Table">테이블</th><th data-ko="Oracle 행 수" data-en="Oracle Rows">Oracle 행 수</th><th data-ko="PG 행 수" data-en="PG Rows">PG 행 수</th><th data-ko="일치" data-en="Match">일치</th><th data-ko="상태" data-en="Status">상태</th></tr></thead><tbody>')
                for tbl in dm_tables_list:
                    tbl_name = tbl.get("name", "N/A")
                    ora_rows = tbl.get("oracle_rows", 0)
                    pg_rows = tbl.get("pg_rows", 0)
                    status = tbl.get("status", "unknown")
                    match = ora_rows == pg_rows
                    row_cls = "row-success" if status == "success" and match else "row-fail" if status != "success" else "row-mismatch"
                    badge_cls = "badge-pass" if status == "success" else "badge-fail"
                    match_icon = "=" if match else "!="
                    html.append(f'<tr class="{row_cls}"><td>{esc(tbl_name)}</td>'
                                f'<td style="text-align:right">{ora_rows:,}</td>'
                                f'<td style="text-align:right">{pg_rows:,}</td>'
                                f'<td style="text-align:center;font-weight:600;color:{"var(--go)" if match else "var(--nogo)"}">{match_icon}</td>'
                                f'<td><span class="badge {badge_cls}">{esc(status)}</span></td></tr>')
                html.append('</tbody></table>')

            # Show errors if any
            dm_errors = data_migration.get("errors", [])
            if dm_errors:
                html.append('<h3 data-ko="이관 오류" data-en="Migration Errors">이관 오류</h3>')
                for err in dm_errors:
                    html.append(f'<div class="code-block" style="background:#fef2f2;color:#991b1b;border-color:#fecaca">{esc(str(err))}</div>')

            html.append('</div>')
            sections_generated.append("data_migration")

        # === DATA VERIFICATION RESULTS ===
        if data_verification:
            dv_status = data_verification.get("overall_status", "N/A")
            html.append(f'<div class="section" id="data-verification"><h2 data-ko="데이터 검증" data-en="Data Verification">데이터 검증</h2>')

            dv_row_check = data_verification.get("row_count_check", {})
            dv_sample = data_verification.get("sample_data_check", {})
            dv_fk = data_verification.get("fk_integrity_check", {})
            dv_seq = data_verification.get("sequence_check", {})

            def _dv_badge(check_data):
                st = check_data.get("status", "N/A") if isinstance(check_data, dict) else str(check_data)
                cls = "badge-pass" if st.upper() == "PASS" else "badge-fail" if st.upper() == "FAIL" else "badge-skip"
                return f'<span class="badge {cls}">{esc(st)}</span>'

            html.append(f"""
<div class="cards" style="margin-bottom:20px">
  <div class="card" style="border-left-color:{'var(--go)' if dv_status.upper() == 'PASS' else 'var(--nogo)'}">
    <div class="card-label" data-ko="종합" data-en="Overall">종합</div>
    <div class="card-value" style="color:{'var(--go)' if dv_status.upper() == 'PASS' else 'var(--nogo)'}; font-size:1.8em">{esc(dv_status)}</div>
  </div>
  <div class="card">
    <div class="card-label" data-ko="행 수 검증" data-en="Row Count Check">행 수 검증</div>
    <div class="card-value" style="font-size:1.2em">{_dv_badge(dv_row_check)}</div>
    <div class="card-detail">{dv_row_check.get('total_oracle', '?')} Oracle / {dv_row_check.get('total_pg', '?')} PG</div>
  </div>
  <div class="card">
    <div class="card-label" data-ko="FK 무결성" data-en="FK Integrity">FK 무결성</div>
    <div class="card-value" style="font-size:1.2em">{_dv_badge(dv_fk)}</div>
    <div class="card-detail"><span data-ko="{dv_fk.get('fks_checked', 0)}개 FK, {dv_fk.get('orphans_found', 0)}개 고아 레코드" data-en="{dv_fk.get('fks_checked', 0)} FKs, {dv_fk.get('orphans_found', 0)} orphans">{dv_fk.get('fks_checked', 0)}개 FK, {dv_fk.get('orphans_found', 0)}개 고아 레코드</span></div>
  </div>
  <div class="card">
    <div class="card-label" data-ko="시퀀스" data-en="Sequences">시퀀스</div>
    <div class="card-value" style="font-size:1.2em">{_dv_badge(dv_seq)}</div>
    <div class="card-detail"><span data-ko="{dv_seq.get('sequences_checked', 0)}개 확인" data-en="{dv_seq.get('sequences_checked', 0)} checked">{dv_seq.get('sequences_checked', 0)}개 확인</span></div>
  </div>
</div>""")

            # Row count mismatches
            mismatches = dv_row_check.get("mismatches", [])
            if mismatches:
                html.append('<h3 data-ko="행 수 불일치" data-en="Row Count Mismatches">행 수 불일치</h3>')
                html.append('<table><thead><tr><th data-ko="테이블" data-en="Table">테이블</th><th>Oracle</th><th>PostgreSQL</th><th data-ko="차이" data-en="Diff">차이</th></tr></thead><tbody>')
                for mm in mismatches:
                    if isinstance(mm, dict):
                        html.append(f'<tr class="row-mismatch"><td>{esc(mm.get("table", "N/A"))}</td>'
                                    f'<td>{mm.get("oracle", "?")}</td><td>{mm.get("pg", "?")}</td>'
                                    f'<td style="color:var(--nogo);font-weight:600">{mm.get("diff", "?")}</td></tr>')
                html.append('</tbody></table>')

            # Sample data issues
            sample_issues = dv_sample.get("issues", [])
            if sample_issues:
                html.append(f'<h3><span data-ko="샘플 데이터 이슈 ({dv_sample.get("tables_checked", 0)}개 테이블 검증)" data-en="Sample Data Issues ({dv_sample.get("tables_checked", 0)} tables checked)">샘플 데이터 이슈 ({dv_sample.get("tables_checked", 0)}개 테이블 검증)</span></h3>')
                for issue in sample_issues[:10]:
                    html.append(f'<div class="code-block" style="background:#fffbeb;color:#92400e;border-color:#fde68a">{esc(str(issue))}</div>')

            # Summary
            dv_summary = data_verification.get("summary", "")
            if dv_summary:
                html.append(f'<p style="margin-top:16px;padding:12px 16px;background:#f0fdf4;border-radius:8px;color:#166534;font-weight:500">{esc(dv_summary)}</p>')

            html.append('</div>')
            sections_generated.append("data_verification")

        # === PERFORMANCE BASELINES ===
        if perf_baselines:
            html.append('<div class="section" id="performance"><h2 data-ko="성능 베이스라인" data-en="Performance Baselines">성능 베이스라인</h2>')
            html.append('<table><thead><tr><th data-ko="오브젝트" data-en="Object">오브젝트</th><th data-ko="실행 시간 (ms)" data-en="Execution (ms)">실행 시간 (ms)</th><th data-ko="행 수" data-en="Rows">행 수</th><th data-ko="실행 계획 요약" data-en="Plan Summary">실행 계획 요약</th></tr></thead><tbody>')
            for pb in perf_baselines:
                html.append(f'<tr><td>{esc(pb.get("object_name", "N/A"))}</td>'
                            f'<td>{pb.get("execution_ms", 0):.3f}</td>'
                            f'<td>{pb.get("rows", 0)}</td>'
                            f'<td style="font-size:0.85em">{esc(str(pb.get("plan_summary", ""))[:200])}</td></tr>')
            html.append('</tbody></table></div>')
            sections_generated.append("performance_baselines")

        html.append('</div>')  # close tab-data
        html.append('<div class="tab-content" id="tab-log">')

        # === TOKEN USAGE BAR CHART + PIPELINE METRICS ===
        # Always show token section — even with partial or missing data
        node_metrics = metrics.get("nodes", {})
        metrics_total_tokens = metrics.get("total_tokens", 0)
        metrics_total_in = metrics.get("total_input_tokens", 0)
        metrics_total_out = metrics.get("total_output_tokens", 0)

        # Check if we have per-node token data (non-zero)
        has_per_node_tokens = False
        if node_metrics:
            for nm in node_metrics.values():
                if isinstance(nm, dict) and (nm.get("input_tokens", 0) + nm.get("output_tokens", 0)) > 0:
                    has_per_node_tokens = True
                    break

        html.append(f'<div class="section" id="tokens"><h2 data-ko="토큰 사용량" data-en="Token Usage">토큰 사용량</h2>')

        if has_per_node_tokens:
            exec_order = metrics.get("execution_order", [])
            sorted_nodes = sorted(node_metrics.items(), key=lambda x: exec_order.index(x[0]) if x[0] in exec_order else 99)

            total_in = 0
            total_out = 0
            node_token_data = []
            for node_id, nm in sorted_nodes:
                if isinstance(nm, dict):
                    inp = nm.get("input_tokens", 0)
                    out = nm.get("output_tokens", 0)
                    total_in += inp
                    total_out += out
                    node_token_data.append((node_id, inp, out, nm))

            max_tokens = max((inp + out for _, inp, out, _ in node_token_data), default=1) or 1

            html.append(f'<p style="color:var(--muted);margin-bottom:16px"><span data-ko="합계" data-en="Total">합계</span>: <strong>{total_in + total_out:,}</strong> <span data-ko="토큰" data-en="tokens">토큰</span> ({total_in:,} <span data-ko="입력" data-en="input">입력</span> + {total_out:,} <span data-ko="출력" data-en="output">출력</span>)</p>')

            bar_colors = ["#667eea", "#764ba2", "#6b21a8", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#8b5cf6", "#ec4899", "#14b8a6"]
            for idx, (node_id, inp, out, _) in enumerate(node_token_data):
                total_node = inp + out
                inp_pct = (inp / max_tokens * 100) if max_tokens else 0
                out_pct = (out / max_tokens * 100) if max_tokens else 0
                color = bar_colors[idx % len(bar_colors)]
                html.append(f"""
<div class="token-bar">
  <div class="token-bar-label">{esc(node_id)}</div>
  <div class="token-bar-track">
    <div style="display:flex;height:100%">
      <div class="token-bar-fill" style="width:{inp_pct:.1f}%;background:{color};opacity:0.85">{inp:,} in</div>
      <div class="token-bar-fill" style="width:{out_pct:.1f}%;background:{color};opacity:0.55">{out:,} out</div>
    </div>
  </div>
  <span style="font-size:0.78em;color:var(--muted);width:80px;text-align:right">{total_node:,}</span>
</div>""")

            html.append('<div style="margin-top:12px;display:flex;gap:16px;font-size:0.78em;color:var(--muted)">'
                        '<span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;background:#667eea;opacity:0.85;border-radius:2px;display:inline-block"></span> <span data-ko="입력" data-en="Input">입력</span></span>'
                        '<span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;background:#667eea;opacity:0.55;border-radius:2px;display:inline-block"></span> <span data-ko="출력" data-en="Output">출력</span></span>'
                        '</div>')
            sections_generated.append("token_usage_chart")

        elif metrics_total_tokens > 0:
            # We have total tokens but no per-node breakdown
            html.append(f"""
<div class="cards" style="margin-bottom:16px">
  <div class="card" style="border-left-color:var(--primary)">
    <div class="card-label" data-ko="총 토큰" data-en="Total Tokens">총 토큰</div>
    <div class="card-value">{metrics_total_tokens:,}</div>
    <div class="card-detail">{metrics_total_in:,} <span data-ko="입력" data-en="input">입력</span> + {metrics_total_out:,} <span data-ko="출력" data-en="output">출력</span></div>
  </div>
</div>
<p style="color:var(--muted);font-size:0.88em" data-ko="노드별 세부 토큰 데이터를 사용할 수 없습니다. Strands SDK가 per-node token usage를 지원하면 자동으로 표시됩니다." data-en="Per-node token breakdown not available. Will display automatically when Strands SDK supports per-node token usage reporting.">노드별 세부 토큰 데이터를 사용할 수 없습니다. Strands SDK가 per-node token usage를 지원하면 자동으로 표시됩니다.</p>""")
            sections_generated.append("token_usage_total_only")

        else:
            # No token data at all
            html.append(f"""
<p style="color:var(--muted);font-size:0.92em;padding:20px;text-align:center;background:#f8fafc;border-radius:12px" data-ko="토큰 사용량 데이터를 사용할 수 없습니다. 파이프라인에서 토큰 추적이 활성화되면 이 섹션에 노드별 상세 사용량이 표시됩니다." data-en="Token usage data not available. This section will display per-node usage details when token tracking is enabled in the pipeline.">토큰 사용량 데이터를 사용할 수 없습니다. 파이프라인에서 토큰 추적이 활성화되면 이 섹션에 노드별 상세 사용량이 표시됩니다.</p>""")
            sections_generated.append("token_usage_empty")

        html.append('</div>')

        # --- Pipeline Metrics Table (separate section) ---
        if node_metrics:
            exec_order_m = metrics.get("execution_order", [])
            sorted_nodes_m = sorted(node_metrics.items(), key=lambda x: exec_order_m.index(x[0]) if x[0] in exec_order_m else 99)
            html.append('<div class="section"><h2 data-ko="파이프라인 메트릭 (노드별 상세)" data-en="Pipeline Metrics (Per-Node Detail)">파이프라인 메트릭 (노드별 상세)</h2>')
            html.append('<table><thead><tr><th data-ko="노드" data-en="Node">노드</th><th data-ko="소요 시간 (초)" data-en="Duration (s)">소요 시간 (초)</th><th data-ko="입력 토큰" data-en="Input Tokens">입력 토큰</th><th data-ko="출력 토큰" data-en="Output Tokens">출력 토큰</th><th data-ko="상태" data-en="Status">상태</th><th data-ko="실행 횟수" data-en="Executions">실행 횟수</th></tr></thead><tbody>')
            pm_total_in = 0
            pm_total_out = 0
            for node_id, nm in sorted_nodes_m:
                if not isinstance(nm, dict):
                    continue
                dur = nm.get("duration_seconds", 0)
                inp = nm.get("input_tokens", 0)
                out = nm.get("output_tokens", 0)
                pm_total_in += inp
                pm_total_out += out
                st = nm.get("status", "N/A")
                ex_count = nm.get("execution_count", 1)
                badge_cls = "badge-completed" if st in ("completed", "COMPLETED") else "badge-fail"
                html.append(f'<tr><td><strong>{esc(node_id)}</strong></td><td>{dur:.1f}</td><td>{inp:,}</td><td>{out:,}</td>'
                            f'<td><span class="badge {badge_cls}">{esc(st)}</span></td><td>{ex_count}</td></tr>')
            html.append(f'<tr style="font-weight:700;border-top:2px solid var(--primary)">'
                        f'<td data-ko="합계" data-en="Total">합계</td><td>{total_duration:.1f}</td><td>{pm_total_in:,}</td><td>{pm_total_out:,}</td><td></td><td></td></tr>')
            html.append('</tbody></table></div>')
            sections_generated.append("pipeline_metrics")

        # === WARNINGS & ISSUES ENCOUNTERED ===
        warnings_list = data.get("warnings", [])
        issues_list = data.get("issues_encountered", [])
        troubleshooting = data.get("troubleshooting", [])
        if warnings_list or issues_list or troubleshooting:
            html.append('<div class="section" id="issues"><h2 data-ko="경고 및 발생 이슈" data-en="Warnings &amp; Issues Encountered">경고 및 발생 이슈</h2>')

            if warnings_list:
                html.append('<h3 data-ko="경고" data-en="Warnings">경고</h3>')
                html.append('<table><thead><tr><th>#</th><th data-ko="단계" data-en="Phase">단계</th><th data-ko="경고" data-en="Warning">경고</th><th data-ko="영향도" data-en="Impact">영향도</th></tr></thead><tbody>')
                for i, w in enumerate(warnings_list, 1):
                    if isinstance(w, dict):
                        html.append(f'<tr><td>{i}</td><td>{esc(w.get("phase", "N/A"))}</td>'
                                    f'<td>{esc(w.get("message", str(w)))}</td>'
                                    f'<td><span class="badge badge-warning">{esc(w.get("impact", "low"))}</span></td></tr>')
                    else:
                        html.append(f'<tr><td>{i}</td><td></td><td>{esc(str(w))}</td><td></td></tr>')
                html.append('</tbody></table>')

            if issues_list:
                html.append('<h3 data-ko="발생 이슈 및 해결" data-en="Issues Encountered &amp; Resolutions">발생 이슈 및 해결</h3>')
                for i, issue in enumerate(issues_list, 1):
                    if isinstance(issue, dict):
                        phase = issue.get("phase", "")
                        description = issue.get("description", issue.get("message", str(issue)))
                        resolution = issue.get("resolution", "")
                        status = issue.get("status", "resolved")
                        badge_cls = "badge-pass" if status.lower() == "resolved" else "badge-fail" if status.lower() == "unresolved" else "badge-warning"
                        html.append(f"""
<details>
<summary>#{i} [{esc(phase)}] {esc(description[:120])} <span class="badge {badge_cls}">{esc(status)}</span></summary>
<div style="padding:12px">
  <p><strong><span data-ko="설명" data-en="Description">설명</span>:</strong> {esc(description)}</p>
  {f'<p><strong><span data-ko="해결 방법" data-en="Resolution">해결 방법</span>:</strong> {esc(resolution)}</p>' if resolution else ''}
  {f'<p><strong><span data-ko="근본 원인" data-en="Root Cause">근본 원인</span>:</strong> {esc(issue.get("root_cause", ""))}</p>' if issue.get("root_cause") else ''}
  {f'<div class="code-block">{esc(str(issue.get("error_detail", ""))[:2000])}</div>' if issue.get("error_detail") else ''}
</div>
</details>""")
                    else:
                        html.append(f'<p style="padding:8px 12px;background:#fffbeb;border-radius:8px;margin:4px 0">#{i} {esc(str(issue))}</p>')

            if troubleshooting:
                html.append('<h3 data-ko="트러블슈팅 로그" data-en="Troubleshooting Log">트러블슈팅 로그</h3>')
                html.append('<div class="timeline">')
                for i, ts in enumerate(troubleshooting, 1):
                    if isinstance(ts, dict):
                        problem = ts.get("problem", str(ts))
                        action = ts.get("action", "")
                        result = ts.get("result", "")
                        ts_status = ts.get("status", "resolved")
                        status_cls = "" if ts_status.lower() == "resolved" else "status-error"
                        html.append(f"""
<div class="timeline-item {status_cls}">
  <div class="timeline-num">{i}</div>
  <div class="timeline-body">
    <div class="timeline-title">{esc(problem[:120])} <span class="badge {'badge-pass' if ts_status.lower() == 'resolved' else 'badge-fail'}">{esc(ts_status)}</span></div>
    {f'<div class="timeline-detail"><strong><span data-ko="조치" data-en="Action">조치</span>:</strong> {esc(action)}</div>' if action else ''}
    {f'<div class="timeline-detail"><strong><span data-ko="결과" data-en="Result">결과</span>:</strong> {esc(result)}</div>' if result else ''}
  </div>
</div>""")
                    else:
                        html.append(f'<div class="timeline-item"><div class="timeline-num">{i}</div>'
                                    f'<div class="timeline-body"><div class="timeline-detail">{esc(str(ts))}</div></div></div>')
                html.append('</div>')

            html.append('</div>')
            sections_generated.append("warnings_issues")

        # === RECOMMENDATIONS ===
        recommendations = data.get("recommendations", [])
        if recommendations:
            html.append('<div class="section"><h2 data-ko="권장 후속 조치" data-en="Recommendations">권장 후속 조치</h2><ol>')
            for rec in recommendations:
                if isinstance(rec, dict):
                    html.append(f'<li><strong>{esc(rec.get("title", ""))}</strong>: {esc(rec.get("description", str(rec)))}</li>')
                else:
                    html.append(f'<li>{esc(str(rec))}</li>')
            html.append('</ol></div>')
            sections_generated.append("recommendations")

        html.append('</div>')  # close tab-log

        # === FOOTER ===
        html.append(f"""
<div class="footer">
  <p class="ko-only">자동 생성 by <strong>OMA Agentic AI</strong> &mdash; Oracle Modernization Accelerator v2</p>
  <p class="en-only" style="display:none">Generated by <strong>OMA Agentic AI</strong> &mdash; Oracle Modernization Accelerator v2</p>
  <p>Migration ID: {esc(migration_id)} | {esc(migration_date)} | Phase 1: Schema Migration | Powered by Claude on Amazon Bedrock</p>
</div>
</body></html>
""")

        # --- Write to file ---
        report_dir = os.environ.get("OMA_REPORT_DIR", "./reports")
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"migration_report_{migration_id[:8]}_{timestamp}.html"
        report_path = os.path.join(report_dir, report_filename)

        html_content = "\n".join(html)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        report_size = os.path.getsize(report_path)

        # --- Upload to S3 ---
        s3_url = None
        s3_bucket = os.environ.get("OMA_REPORT_S3_BUCKET", "oma-YOUR_AWS_ACCOUNT_ID")
        s3_prefix = os.environ.get("OMA_REPORT_S3_PREFIX", "oma-report")
        try:
            import boto3
            s3_client = boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2"))
            s3_key = f"{s3_prefix}/{report_filename}"
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=html_content.encode("utf-8"),
                ContentType="text/html; charset=utf-8",
            )
            s3_url = f"s3://{s3_bucket}/{s3_key}"
            logger.info("Report uploaded to S3: %s", s3_url)
        except Exception as s3_err:
            logger.warning("Failed to upload report to S3: %s", s3_err)

        return json.dumps({
            "success": True,
            "report_path": os.path.abspath(report_path),
            "report_size": report_size,
            "report_filename": report_filename,
            "sections_generated": sections_generated,
            "s3_url": s3_url,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })


def _build_radar_chart_svg(
    coverage: float, equivalence: float, performance: float,
    security: float, operational: float,
    section_id: str = "",
) -> str:
    """Build an inline SVG radar chart for 5-dimension scores."""
    import math

    dims = [
        ("Coverage", "커버리지", coverage),
        ("Equivalence", "동등성", equivalence),
        ("Performance", "성능", performance),
        ("Security", "보안", security),
        ("Operational", "운영", operational),
    ]
    n = len(dims)
    cx, cy, r = 200, 200, 150
    angle_offset = -math.pi / 2  # Start from top

    def polar(value_pct, idx):
        angle = angle_offset + (2 * math.pi * idx / n)
        dist = r * (value_pct / 100)
        return cx + dist * math.cos(angle), cy + dist * math.sin(angle)

    # Grid lines
    grid_svg = []
    for pct in [20, 40, 60, 80, 100]:
        pts = " ".join(f"{polar(pct, i)[0]:.1f},{polar(pct, i)[1]:.1f}" for i in range(n))
        opacity = "0.3" if pct < 100 else "0.5"
        grid_svg.append(f'<polygon points="{pts}" fill="none" stroke="#475569" stroke-width="1" opacity="{opacity}"/>')
        if pct in (50, 100):
            grid_svg.append(f'<text x="{cx + 4}" y="{cy - r * pct / 100 + 4}" font-size="10" fill="#94a3b8">{pct}</text>')

    # Axis lines and labels
    axis_svg = []
    for i, (label_en, label_ko, val) in enumerate(dims):
        ex, ey = polar(100, i)
        axis_svg.append(f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#475569" stroke-width="1"/>')
        lx, ly = polar(115, i)
        anchor = "middle"
        if lx < cx - 10:
            anchor = "end"
        elif lx > cx + 10:
            anchor = "start"
        axis_svg.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="12" font-weight="600" '
                        f'fill="#e2e8f0" text-anchor="{anchor}" dominant-baseline="middle" '
                        f'data-ko="{label_ko} ({val:.0f})" data-en="{label_en} ({val:.0f})">{label_ko} ({val:.0f})</text>')

    # Data polygon
    data_pts = " ".join(f"{polar(v, i)[0]:.1f},{polar(v, i)[1]:.1f}" for i, (_, _, v) in enumerate(dims))

    # Data points
    dots_svg = []
    for i, (_, _, v) in enumerate(dims):
        dx, dy = polar(v, i)
        dots_svg.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="5" fill="#3b82f6" stroke="#0f172a" stroke-width="2"/>')

    # 70-point threshold line
    threshold_pts = " ".join(f"{polar(70, i)[0]:.1f},{polar(70, i)[1]:.1f}" for i in range(n))

    id_attr = f' id="{section_id}"' if section_id else ""
    svg = f"""
<div class="section"{id_attr}>
<h2 data-ko="5차원 품질 레이더" data-en="5-Dimension Quality Radar">5차원 품질 레이더</h2>
<div class="radar-container">
<svg width="420" height="420" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
  {''.join(grid_svg)}
  {''.join(axis_svg)}
  <polygon points="{threshold_pts}" fill="none" stroke="#ff9800" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.6"/>
  <polygon points="{data_pts}" fill="rgba(59,130,246,0.25)" stroke="#3b82f6" stroke-width="2.5"/>
  {''.join(dots_svg)}
</svg>
</div>
<p style="text-align:center;color:#94a3b8;font-size:0.85em" data-ko="주황색 점선 = 70점 임계선 (CONDITIONAL 최소 기준)" data-en="Dashed orange line = 70-point threshold (minimum for CONDITIONAL)">주황색 점선 = 70점 임계선 (CONDITIONAL 최소 기준)</p>
</div>
"""
    return svg


@tool
def deploy_compat_library(packages: str = "") -> str:
    """
    Deploy Oracle compatibility functions to the target database.

    PostgreSQL: Creates the oracle_compat schema and installs PG functions that emulate
                Oracle built-in packages (DBMS_OUTPUT, DBMS_LOB, DBMS_RANDOM, UTL_RAW, etc.).
    MySQL: Not yet implemented - MySQL has different compatibility requirements.

    This MUST be run before migrating PL/SQL code that references Oracle packages.

    Args:
        packages: Comma-separated list of packages to deploy (e.g., "DBMS_LOB,DBMS_RANDOM").
                  Empty string deploys ALL packages.

    Returns:
        JSON string with deployment results.

    Example:
        >>> deploy_compat_library("")  # Deploy all
        >>> deploy_compat_library("DBMS_LOB,DBMS_RANDOM")  # Deploy specific
    """
    async def _deploy():
        try:
            if _TARGET_DB_TYPE == "mysql":
                return {
                    "success": False,
                    "error": "MySQL compatibility library not yet implemented. "
                            "MySQL has different Oracle compatibility requirements. "
                            "Please refer to mysql/rules/oracle_compat_library.py (to be created)."
                }

            from common.rules.oracle_compat_library import (
                get_all_compat_ddl,
                get_compat_ddl,
                list_supported_packages,
                COMPAT_SCHEMA_DDL,
            )

            pg_conn = await asyncpg.connect(
                host=os.environ.get('PGHOST', 'localhost'),
                port=int(os.environ.get('PGPORT', '5432')),
                database=os.environ.get('PGDATABASE'),
                user=os.environ.get('PGUSER'),
                password=os.environ.get('PGPASSWORD'),
            )

            deployed = []
            errors = []

            if not packages or packages.strip() == "":
                # Deploy all
                ddl = get_all_compat_ddl()
                try:
                    await pg_conn.execute(ddl)
                    deployed = list_supported_packages()
                except Exception as e:
                    errors.append(f"Full deployment failed: {str(e)}")
            else:
                # Deploy schema first
                await pg_conn.execute(COMPAT_SCHEMA_DDL)

                # Deploy specific packages
                for pkg in packages.split(","):
                    pkg = pkg.strip().upper()
                    ddl = get_compat_ddl(pkg)
                    if ddl:
                        try:
                            await pg_conn.execute(ddl)
                            deployed.append(pkg)
                        except Exception as e:
                            errors.append(f"{pkg}: {str(e)}")
                    else:
                        errors.append(f"{pkg}: not supported")

            await pg_conn.close()

            return json.dumps({
                "success": len(errors) == 0,
                "deployed_packages": deployed,
                "deployed_count": len(deployed),
                "errors": errors,
                "supported_packages": list_supported_packages(),
            })

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            })

    return _run_async(_deploy())


@tool
def functional_test_sql(
    oracle_sql: str,
    pg_sql: str,
    test_name: str = "",
    sample_limit: int = 100,
) -> str:
    """
    Run automated functional equivalence test between Oracle and PostgreSQL SQL.

    Unlike execute_sql_comparison which requires bind variables, this tool:
    1. Runs the Oracle SQL to get reference results
    2. Runs the PG SQL and compares
    3. Handles type coercion (DATE→TIMESTAMP, NUMBER→NUMERIC, etc.)
    4. Compares row counts, column names, and cell values
    5. Reports detailed per-row/per-column differences

    Both queries must be parameterless SELECT statements (or have defaults).
    The tool auto-limits results to sample_limit rows for performance.

    Args:
        oracle_sql: Oracle SELECT query (no bind params)
        pg_sql: PostgreSQL SELECT query (no bind params)
        test_name: Optional test identifier
        sample_limit: Max rows to compare (default 100)

    Returns:
        JSON with detailed comparison: equivalent, row_count, column_match,
        value_diffs, type_coercion_notes.

    Example:
        >>> functional_test_sql(
        ...     "SELECT empno, ename FROM emp ORDER BY empno",
        ...     "SELECT empno, ename FROM emp ORDER BY empno",
        ...     "emp_basic"
        ... )
    """
    async def _test():
        try:
            import re as _re
            from datetime import datetime as _dt, date as _date
            from decimal import Decimal as _Decimal

            # Add ROWNUM/LIMIT wrapper
            ora_sql = oracle_sql.rstrip().rstrip(';')
            pg_sql_clean = pg_sql.rstrip().rstrip(';')

            # Auto-limit Oracle
            if not _re.search(r'\bROWNUM\b', ora_sql, _re.IGNORECASE):
                ora_sql = f"SELECT * FROM ({ora_sql}) WHERE ROWNUM <= {sample_limit}"

            # Auto-limit PG
            if not _re.search(r'\bLIMIT\b', pg_sql_clean, _re.IGNORECASE):
                pg_sql_clean = f"{pg_sql_clean} LIMIT {sample_limit}"

            # --- Oracle execution ---
            ora_host = os.environ.get('ORACLE_HOST')
            ora_port = os.environ.get('ORACLE_PORT', '1521')
            ora_service = os.environ.get('ORACLE_SERVICE_NAME')
            ora_sid = os.environ.get('ORACLE_SID')

            if ora_service:
                dsn = oracledb.makedsn(ora_host, ora_port, service_name=ora_service)
            elif ora_sid:
                dsn = oracledb.makedsn(ora_host, ora_port, sid=ora_sid)
            else:
                return json.dumps({
                    "success": False, "error": "No Oracle SERVICE_NAME or SID configured"
                })

            oracle_conn = oracledb.connect(
                user=os.environ.get('ORACLE_USER'),
                password=os.environ.get('ORACLE_PASSWORD'),
                dsn=dsn,
            )
            cursor = oracle_conn.cursor()
            cursor.execute(ora_sql)
            ora_cols = [desc[0].upper() for desc in cursor.description]
            ora_rows = cursor.fetchall()
            cursor.close()
            oracle_conn.close()

            # --- Target DB execution ---
            target_conn = await _get_target_db_connection()

            if _TARGET_DB_TYPE == "mysql":
                async with target_conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(pg_sql_clean)
                    target_records = await cursor.fetchall()
                target_conn.close()
            else:
                target_records = await target_conn.fetch(pg_sql_clean)
                await target_conn.close()

            target_cols = [k.upper() for k in target_records[0].keys()] if target_records else []
            target_rows = [tuple(r.values()) for r in target_records]

            # --- Comparison ---
            diffs = []
            type_notes = []

            # Column comparison
            col_match = set(ora_cols) == set(target_cols)
            if not col_match:
                ora_only = set(ora_cols) - set(target_cols)
                target_only = set(target_cols) - set(ora_cols)
                if ora_only:
                    diffs.append({"type": "columns_oracle_only", "columns": list(ora_only)})
                if target_only:
                    diffs.append({"type": "columns_target_only", "columns": list(target_only)})

            # Row count
            row_match = len(ora_rows) == len(target_rows)
            if not row_match:
                diffs.append({
                    "type": "row_count",
                    "oracle": len(ora_rows),
                    "target": len(target_rows),
                })

            # Value comparison (up to min of both)
            def normalize(val):
                """Normalize value for cross-DB comparison."""
                if val is None:
                    return None
                if isinstance(val, (_dt, _date)):
                    return str(val)[:19]  # Truncate to second precision
                if isinstance(val, (_Decimal, float)):
                    # Compare as float with tolerance
                    return round(float(val), 6)
                return str(val).strip()

            compare_cols = list(set(ora_cols) & set(target_cols))
            # Build column index maps
            ora_idx = {c: i for i, c in enumerate(ora_cols)}
            target_idx = {c: i for i, c in enumerate(target_cols)}

            value_diffs = 0
            max_diffs_to_report = 20
            for row_i in range(min(len(ora_rows), len(target_rows))):
                for col in compare_cols:
                    ora_val = normalize(ora_rows[row_i][ora_idx[col]])
                    target_val = normalize(target_rows[row_i][target_idx[col]])
                    if ora_val != target_val:
                        value_diffs += 1
                        if value_diffs <= max_diffs_to_report:
                            diffs.append({
                                "type": "value",
                                "row": row_i,
                                "column": col,
                                "oracle": str(ora_val),
                                "target": str(target_val),
                            })

            equivalent = len(diffs) == 0
            total_cells = min(len(ora_rows), len(target_rows)) * len(compare_cols)
            accuracy = ((total_cells - value_diffs) / total_cells * 100) if total_cells > 0 else 0

            return json.dumps({
                "success": True,
                "test_name": test_name or "anonymous",
                "equivalent": equivalent,
                "accuracy_pct": round(accuracy, 2),
                "oracle_rows": len(ora_rows),
                "pg_rows": len(pg_rows),
                "oracle_columns": ora_cols,
                "pg_columns": pg_cols,
                "columns_match": col_match,
                "rows_match": row_match,
                "value_diffs": value_diffs,
                "differences": diffs,
                "type_notes": type_notes,
            }, default=str)

        except Exception as e:
            return json.dumps({
                "success": False,
                "test_name": test_name or "anonymous",
                "error": str(e),
                "error_type": type(e).__name__,
            })

    return _run_async(_test())
