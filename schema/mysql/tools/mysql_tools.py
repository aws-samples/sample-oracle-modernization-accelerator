"""
MySQL Database MCP Tools

Tools for interacting with MySQL databases including DDL execution,
query validation, syntax checking, and metadata queries.
"""

import os
import json
import asyncio
import threading
from typing import Optional
import aiomysql
from strands import tool


_mysql_secret_cache: dict | None = None


def _run_async(coro):
    """Run an async coroutine safely, whether or not an event loop is running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're inside an already-running loop (e.g. Strands agent).
        # Run in a separate thread with its own event loop.
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


def _get_mysql_secret() -> dict | None:
    """Load MySQL credentials from Secrets Manager (cached)."""
    global _mysql_secret_cache
    if _mysql_secret_cache is not None:
        return _mysql_secret_cache
    try:
        import boto3
        region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")
        client = boto3.client("secretsmanager", region_name=region)
        val = client.get_secret_value(SecretId="oma-secret-mysql-service")
        _mysql_secret_cache = json.loads(val["SecretString"])
        return _mysql_secret_cache
    except Exception:
        pass
    _mysql_secret_cache = {}
    return _mysql_secret_cache


async def get_mysql_connection():
    """
    Create MySQL database connection.

    Priority: env vars (MYSQL_*) > Secrets Manager > defaults.
    """
    sm = _get_mysql_secret() or {}

    host = os.environ.get('MYSQL_HOST') or sm.get('host') or 'localhost'
    port = int(os.environ.get('MYSQL_PORT') or sm.get('port', '3306'))
    database = os.environ.get('MYSQL_DATABASE') or sm.get('dbname') or sm.get('database')
    user = os.environ.get('MYSQL_USER') or sm.get('username')
    password = os.environ.get('MYSQL_PASSWORD') or sm.get('password')

    if not all([database, user, password]):
        raise ValueError(
            "Missing MySQL credentials. Set MYSQL_* env vars or configure Secrets Manager."
        )

    conn = await aiomysql.connect(
        host=host,
        port=port,
        db=database,
        user=user,
        password=password,
        autocommit=False,
    )
    return conn


@tool
def mysql_execute_ddl(sql: str) -> str:
    """
    Execute DDL statement on MySQL database.

    Args:
        sql: DDL statement to execute (CREATE, ALTER, DROP, etc.)

    Returns:
        JSON string with execution result. Format:
        {
            "success": true,
            "message": "DDL executed successfully",
            "rows_affected": 0
        }

    Example:
        >>> mysql_execute_ddl("CREATE TABLE test (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100))")
    """
    async def _execute():
        conn = None
        try:
            conn = await get_mysql_connection()
            async with conn.cursor() as cursor:
                await cursor.execute(sql)
                await conn.commit()
                return json.dumps({
                    "success": True,
                    "message": "DDL executed successfully",
                    "rows_affected": cursor.rowcount
                })
        except Exception as e:
            if conn:
                await conn.rollback()
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            })
        finally:
            if conn:
                conn.close()

    return _run_async(_execute())


@tool
def mysql_query(sql: str) -> str:
    """
    Execute read-only SQL query on MySQL database.

    Args:
        sql: SELECT query to execute

    Returns:
        JSON string with query results. Format:
        {
            "success": true,
            "rows": [...],
            "row_count": N,
            "columns": [...]
        }

    Example:
        >>> mysql_query("SELECT * FROM users LIMIT 10")
    """
    async def _query():
        conn = None
        try:
            # Validate SQL is read-only
            sql_upper = sql.strip().upper()
            if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
                return json.dumps({
                    "success": False,
                    "error": "Only SELECT queries are allowed"
                })

            conn = await get_mysql_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql)
                rows = await cursor.fetchall()

                # Convert rows to list of dicts
                result_rows = [dict(row) for row in rows]
                columns = list(result_rows[0].keys()) if result_rows else []

                return json.dumps({
                    "success": True,
                    "rows": result_rows,
                    "row_count": len(result_rows),
                    "columns": columns
                }, default=str)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            })
        finally:
            if conn:
                conn.close()

    return _run_async(_query())


@tool
def mysql_explain(sql: str) -> str:
    """
    Run EXPLAIN on a query to get execution plan.

    Args:
        sql: Query to analyze

    Returns:
        JSON string with query plan. Format:
        {
            "success": true,
            "plan": [...]
        }

    Example:
        >>> mysql_explain("SELECT * FROM large_table WHERE id > 1000")
    """
    async def _explain():
        conn = None
        try:
            conn = await get_mysql_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # MySQL EXPLAIN FORMAT=JSON
                explain_sql = f"EXPLAIN FORMAT=JSON {sql}"
                await cursor.execute(explain_sql)
                result = await cursor.fetchone()

                # MySQL returns JSON as string in 'EXPLAIN' column
                plan = json.loads(result['EXPLAIN']) if result and 'EXPLAIN' in result else {}

                return json.dumps({
                    "success": True,
                    "plan": plan
                }, default=str)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            })
        finally:
            if conn:
                conn.close()

    return _run_async(_explain())


@tool
def mysql_syntax_check(sql: str) -> str:
    """
    Check SQL syntax without executing (using EXPLAIN for SELECT, or test execution in transaction).

    Args:
        sql: SQL statement to validate

    Returns:
        JSON string with validation result. Format:
        {
            "success": true,
            "valid": true,
            "message": "Syntax is valid"
        }

    Example:
        >>> mysql_syntax_check("CREATE TABLE test (id INT PRIMARY KEY)")
    """
    async def _syntax_check():
        conn = None
        try:
            conn = await get_mysql_connection()
            async with conn.cursor() as cursor:
                sql_upper = sql.strip().upper()

                if sql_upper.startswith('SELECT'):
                    # For SELECT, use EXPLAIN
                    await cursor.execute(f"EXPLAIN {sql}")
                else:
                    # For DDL/DML, execute in transaction and rollback
                    await conn.begin()
                    try:
                        await cursor.execute(sql)
                        await conn.rollback()
                    except Exception as e:
                        await conn.rollback()
                        return json.dumps({
                            "success": True,
                            "valid": False,
                            "error": str(e)
                        })

                return json.dumps({
                    "success": True,
                    "valid": True,
                    "message": "Syntax is valid"
                })
        except Exception as e:
            return json.dumps({
                "success": True,
                "valid": False,
                "error": str(e)
            })
        finally:
            if conn:
                conn.close()

    return _run_async(_syntax_check())


@tool
def mysql_get_column_type(table_name: str, column_name: str) -> str:
    """
    Get MySQL data type for a specific column.

    Args:
        table_name: Table name
        column_name: Column name

    Returns:
        JSON string with column type info
    """
    async def _get_type():
        conn = None
        try:
            conn = await get_mysql_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                    SELECT COLUMN_TYPE, DATA_TYPE, IS_NULLABLE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = %s
                    AND COLUMN_NAME = %s
                """
                await cursor.execute(query, (table_name, column_name))
                result = await cursor.fetchone()

                if result:
                    return json.dumps({
                        "success": True,
                        "column_type": result['COLUMN_TYPE'],
                        "data_type": result['DATA_TYPE'],
                        "nullable": result['IS_NULLABLE'] == 'YES'
                    })
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"Column {column_name} not found in table {table_name}"
                    })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        finally:
            if conn:
                conn.close()

    return _run_async(_get_type())


@tool
def mysql_get_table_list() -> str:
    """
    Get list of tables in current MySQL database.

    Returns:
        JSON string with table list
    """
    async def _get_tables():
        conn = None
        try:
            conn = await get_mysql_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                    SELECT TABLE_NAME, TABLE_TYPE, ENGINE
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                """
                await cursor.execute(query)
                tables = await cursor.fetchall()

                return json.dumps({
                    "success": True,
                    "tables": [dict(t) for t in tables],
                    "count": len(tables)
                }, default=str)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        finally:
            if conn:
                conn.close()

    return _run_async(_get_tables())


@tool
def mysql_sync_sequences() -> str:
    """
    MySQL uses AUTO_INCREMENT, not sequences. This is a no-op for compatibility.

    Returns:
        JSON string indicating AUTO_INCREMENT is used
    """
    return json.dumps({
        "success": True,
        "message": "MySQL uses AUTO_INCREMENT instead of sequences. No action needed.",
        "sequences_synced": 0
    })
