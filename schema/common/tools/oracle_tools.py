"""
Oracle Database MCP Tools

Tools for interacting with Oracle databases including DDL extraction,
dependency analysis, and metadata querying.
"""

import os
import json
from typing import Optional
import oracledb
from strands import tool


_oracle_secret_cache: dict | None = None
_oracle_admin_secret_cache: dict | None = None


def _get_oracle_secret() -> dict | None:
    """Load Oracle service credentials from Secrets Manager (cached)."""
    global _oracle_secret_cache
    if _oracle_secret_cache is not None:
        return _oracle_secret_cache
    try:
        import boto3
        region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")
        client = boto3.client("secretsmanager", region_name=region)
        val = client.get_secret_value(SecretId="oma-secret-oracle-service")
        _oracle_secret_cache = json.loads(val["SecretString"])
        return _oracle_secret_cache
    except Exception:
        pass
    _oracle_secret_cache = {}
    return _oracle_secret_cache


def _get_oracle_admin_secret() -> dict | None:
    """Load Oracle admin (system) credentials from Secrets Manager (cached)."""
    global _oracle_admin_secret_cache
    if _oracle_admin_secret_cache is not None:
        return _oracle_admin_secret_cache
    try:
        import boto3
        region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")
        client = boto3.client("secretsmanager", region_name=region)
        val = client.get_secret_value(SecretId="oma-secret-oracle-admin")
        _oracle_admin_secret_cache = json.loads(val["SecretString"])
        return _oracle_admin_secret_cache
    except Exception:
        pass
    _oracle_admin_secret_cache = {}
    return _oracle_admin_secret_cache


def _make_oracle_dsn(sm: dict) -> tuple:
    """Build DSN, user, password from env vars + secrets dict.

    Returns (dsn, user, password).
    """
    host = os.environ.get('ORACLE_HOST') or sm.get('host') or 'localhost'
    port = os.environ.get('ORACLE_PORT') or str(sm.get('port', '1521'))

    # Priority: env vars > Secrets Manager > empty
    # ORACLE_SERVICE_NAME takes highest priority for service_name connection.
    # ORACLE_SID is used as SID connection fallback.
    # Secret's 'sid' field is only used when NO env vars are set.
    env_service_name = os.environ.get('ORACLE_SERVICE_NAME', '')
    env_sid = os.environ.get('ORACLE_SID', '')
    sm_sid = sm.get('sid') or ''

    if env_service_name:
        dsn = oracledb.makedsn(host, port, service_name=env_service_name)
    elif env_sid:
        dsn = oracledb.makedsn(host, port, service_name=env_sid)
    elif sm_sid:
        dsn = oracledb.makedsn(host, port, service_name=sm_sid)
    else:
        raise ValueError(
            "Either ORACLE_SID or ORACLE_SERVICE_NAME must be set "
            "(env vars or Secrets Manager)"
        )

    return dsn


def get_oracle_connection():
    """
    Create Oracle database connection using service account (amzn).

    Priority: env vars (ORACLE_*) > Secrets Manager > defaults.
    """
    sm = _get_oracle_secret() or {}
    dsn = _make_oracle_dsn(sm)

    user = os.environ.get('ORACLE_USER') or sm.get('username')
    password = os.environ.get('ORACLE_PASSWORD') or sm.get('password')

    if not user or not password:
        raise ValueError(
            "Missing Oracle credentials. Set ORACLE_* env vars or configure Secrets Manager."
        )

    return oracledb.connect(user=user, password=password, dsn=dsn)


def get_oracle_admin_connection():
    """
    Create Oracle database connection using admin account (system).

    Used for DDL extraction (DBMS_METADATA) and privilege operations
    that require DBA-level access.
    """
    admin_sm = _get_oracle_admin_secret() or {}
    service_sm = _get_oracle_secret() or {}

    # Admin secret has its own host/port/sid, but fall back to service secret
    merged = {**service_sm, **{k: v for k, v in admin_sm.items() if v}}
    dsn = _make_oracle_dsn(merged)

    user = admin_sm.get('username') or 'system'
    password = admin_sm.get('password')

    if not password:
        raise ValueError(
            "Missing Oracle admin credentials. Configure oma-secret-oracle-admin in Secrets Manager."
        )

    return oracledb.connect(user=user, password=password, dsn=dsn)


@tool
def oracle_query(sql: str, schema: str = "") -> str:
    """
    Execute read-only SQL query on Oracle database.

    Args:
        sql: SELECT query to execute (must be read-only)
        schema: Optional schema name to set as current schema

    Returns:
        JSON string with query results. Format:
        {
            "success": true,
            "rows": [...],
            "row_count": N,
            "columns": [...]
        }

    Example:
        >>> oracle_query("SELECT * FROM user_tables WHERE rownum <= 10", "SCOTT")
    """
    try:
        # Validate SQL is read-only
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
            return json.dumps({
                "success": False,
                "error": "Only SELECT queries are allowed"
            })

        conn = get_oracle_connection()
        cursor = conn.cursor()

        # Set schema if provided
        if schema:
            cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")

        # Execute query
        cursor.execute(sql)

        # Fetch results
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "rows": rows,
            "row_count": len(rows),
            "columns": columns
        }, default=str)  # Handle dates/decimals

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def oracle_get_ddl(object_type: str, object_name: str, schema: str) -> str:
    """
    Extract DDL for a database object using DBMS_METADATA.GET_DDL.

    Args:
        object_type: Type of object (TABLE, VIEW, PROCEDURE, FUNCTION, PACKAGE, etc.)
        object_name: Name of the object
        schema: Schema containing the object

    Returns:
        JSON string with DDL or error. Format:
        {
            "success": true,
            "ddl": "CREATE TABLE ...",
            "object_type": "TABLE",
            "object_name": "EMPLOYEES",
            "schema": "HR"
        }

    Example:
        >>> oracle_get_ddl("TABLE", "EMPLOYEES", "HR")
    """
    try:
        # Use admin (system) account for DBMS_METADATA access
        conn = get_oracle_admin_connection()
        cursor = conn.cursor()

        # Set transformation parameters for cleaner DDL
        transform_params = [
            "DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'STORAGE', FALSE)",
            "DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'TABLESPACE', FALSE)",
            "DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'SEGMENT_ATTRIBUTES', FALSE)",
            "DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'SQLTERMINATOR', TRUE)",
            "DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'PRETTY', TRUE)"
        ]

        for param in transform_params:
            cursor.execute(f"BEGIN {param}; END;")

        # Get DDL
        obj_type_upper = object_type.upper()

        # Handle special cases
        if obj_type_upper == 'PACKAGE':
            # Get both spec and body
            ddl_query = """
                SELECT DBMS_METADATA.GET_DDL('PACKAGE_SPEC', :name, :schema) ||
                       CHR(10) || CHR(10) ||
                       DBMS_METADATA.GET_DDL('PACKAGE_BODY', :name, :schema) AS ddl
                FROM DUAL
            """
        elif obj_type_upper == 'TYPE':
            ddl_query = """
                SELECT DBMS_METADATA.GET_DDL('TYPE_SPEC', :name, :schema) ||
                       CHR(10) || CHR(10) ||
                       DBMS_METADATA.GET_DDL('TYPE_BODY', :name, :schema) AS ddl
                FROM DUAL
            """
        else:
            ddl_query = """
                SELECT DBMS_METADATA.GET_DDL(:obj_type, :name, :schema) AS ddl
                FROM DUAL
            """
            cursor.execute(ddl_query, obj_type=obj_type_upper, name=object_name.upper(), schema=schema.upper())
            result = cursor.fetchone()

            if result:
                # Read LOB BEFORE closing connection (LOB requires active conn)
                ddl_text = result[0].read() if hasattr(result[0], 'read') else str(result[0])
                cursor.close()
                conn.close()
                return json.dumps({
                    "success": True,
                    "ddl": ddl_text,
                    "object_type": object_type,
                    "object_name": object_name,
                    "schema": schema
                })
            else:
                cursor.close()
                conn.close()
                return json.dumps({
                    "success": False,
                    "error": f"Object {schema}.{object_name} of type {object_type} not found"
                })

        # For PACKAGE and TYPE (with body)
        cursor.execute(ddl_query, name=object_name.upper(), schema=schema.upper())
        result = cursor.fetchone()

        if result:
            # Read LOB BEFORE closing connection
            ddl_text = result[0].read() if hasattr(result[0], 'read') else str(result[0])
            cursor.close()
            conn.close()
            return json.dumps({
                "success": True,
                "ddl": ddl_text,
                "object_type": object_type,
                "object_name": object_name,
                "schema": schema
            })
        else:
            cursor.close()
            conn.close()
            return json.dumps({
                "success": False,
                "error": f"Object {schema}.{object_name} of type {object_type} not found"
            })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def oracle_get_dependencies(schema: str) -> str:
    """
    Get object dependency graph from ALL_DEPENDENCIES.

    Args:
        schema: Schema name to analyze

    Returns:
        JSON string with dependency graph. Format:
        {
            "success": true,
            "dependencies": [
                {
                    "owner": "HR",
                    "name": "PROC_A",
                    "type": "PROCEDURE",
                    "referenced_owner": "HR",
                    "referenced_name": "TABLE_B",
                    "referenced_type": "TABLE"
                },
                ...
            ]
        }

    Example:
        >>> oracle_get_dependencies("HR")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                owner,
                name,
                type,
                referenced_owner,
                referenced_name,
                referenced_type
            FROM all_dependencies
            WHERE owner = :schema
            ORDER BY name, referenced_name
        """

        cursor.execute(query, schema=schema.upper())

        columns = [desc[0].lower() for desc in cursor.description]
        dependencies = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "dependencies": dependencies,
            "count": len(dependencies)
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def oracle_get_object_list(schema: str) -> str:
    """
    List all objects in schema with type, name, and status.

    Args:
        schema: Schema name

    Returns:
        JSON string with object list. Format:
        {
            "success": true,
            "objects": [
                {
                    "object_name": "EMPLOYEES",
                    "object_type": "TABLE",
                    "status": "VALID",
                    "created": "2024-01-01T00:00:00",
                    "last_ddl_time": "2024-03-01T00:00:00"
                },
                ...
            ]
        }

    Example:
        >>> oracle_get_object_list("HR")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                object_name,
                object_type,
                status,
                created,
                last_ddl_time
            FROM all_objects
            WHERE owner = :schema
            ORDER BY object_type, object_name
        """

        cursor.execute(query, schema=schema.upper())

        columns = [desc[0].lower() for desc in cursor.description]
        objects = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        # Group by type for summary
        type_counts = {}
        for obj in objects:
            obj_type = obj['object_type']
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

        return json.dumps({
            "success": True,
            "objects": objects,
            "total_count": len(objects),
            "type_counts": type_counts
        }, default=str)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def oracle_get_source(object_type: str, object_name: str, schema: str) -> str:
    """
    Get PL/SQL source code from ALL_SOURCE.

    Args:
        object_type: Type (PROCEDURE, FUNCTION, PACKAGE, PACKAGE BODY, TYPE, TYPE BODY, TRIGGER)
        object_name: Name of the object
        schema: Schema name

    Returns:
        JSON string with source code. Format:
        {
            "success": true,
            "source": "CREATE OR REPLACE PROCEDURE ...",
            "line_count": 150
        }

    Example:
        >>> oracle_get_source("PROCEDURE", "UPDATE_SALARY", "HR")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT text
            FROM all_source
            WHERE owner = :schema
              AND name = :name
              AND type = :obj_type
            ORDER BY line
        """

        cursor.execute(
            query,
            schema=schema.upper(),
            name=object_name.upper(),
            obj_type=object_type.upper()
        )

        lines = [row[0] for row in cursor.fetchall()]
        source_code = ''.join(lines)

        cursor.close()
        conn.close()

        if source_code:
            return json.dumps({
                "success": True,
                "source": source_code,
                "line_count": len(lines),
                "object_type": object_type,
                "object_name": object_name,
                "schema": schema
            })
        else:
            return json.dumps({
                "success": False,
                "error": f"No source found for {schema}.{object_name} of type {object_type}"
            })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def oracle_get_table_columns(table_name: str, schema: str) -> str:
    """
    Get column definitions from ALL_TAB_COLUMNS.

    Args:
        table_name: Table name
        schema: Schema name

    Returns:
        JSON string with column metadata. Format:
        {
            "success": true,
            "columns": [
                {
                    "column_name": "EMPLOYEE_ID",
                    "data_type": "NUMBER",
                    "data_length": 22,
                    "data_precision": 6,
                    "data_scale": 0,
                    "nullable": "N",
                    "column_id": 1,
                    "data_default": null
                },
                ...
            ]
        }

    Example:
        >>> oracle_get_table_columns("EMPLOYEES", "HR")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                column_name,
                data_type,
                data_length,
                data_precision,
                data_scale,
                nullable,
                column_id,
                data_default
            FROM all_tab_columns
            WHERE owner = :schema
              AND table_name = :table_name
            ORDER BY column_id
        """

        cursor.execute(query, schema=schema.upper(), table_name=table_name.upper())

        columns_def = [desc[0].lower() for desc in cursor.description]
        columns = [dict(zip(columns_def, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "table_name": table_name,
            "schema": schema,
            "columns": columns,
            "column_count": len(columns)
        }, default=str)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def oracle_get_constraints(schema: str, table_name: str = "") -> str:
    """
    Get constraints (PK, FK, UNIQUE, CHECK) from ALL_CONSTRAINTS/ALL_CONS_COLUMNS.

    Args:
        schema: Schema name
        table_name: Optional table name to filter (empty = all tables)

    Returns:
        JSON string with constraint details including columns, referenced tables/columns.

    Example:
        >>> oracle_get_constraints("HR", "EMPLOYEES")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                c.constraint_name,
                c.constraint_type,
                c.table_name,
                c.search_condition,
                c.r_constraint_name,
                c.delete_rule,
                c.status,
                r.table_name AS r_table_name,
                r.owner AS r_owner,
                LISTAGG(cc.column_name, ', ') WITHIN GROUP (ORDER BY cc.position) AS columns,
                LISTAGG(rc.column_name, ', ') WITHIN GROUP (ORDER BY rc.position) AS r_columns
            FROM all_constraints c
            LEFT JOIN all_cons_columns cc
                ON cc.owner = c.owner AND cc.constraint_name = c.constraint_name
            LEFT JOIN all_constraints r
                ON r.owner = c.r_owner AND r.constraint_name = c.r_constraint_name
            LEFT JOIN all_cons_columns rc
                ON rc.owner = r.owner AND rc.constraint_name = r.constraint_name
            WHERE c.owner = :schema
        """
        params = {"schema": schema.upper()}

        if table_name:
            query += " AND c.table_name = :table_name"
            params["table_name"] = table_name.upper()

        query += """
            GROUP BY c.constraint_name, c.constraint_type, c.table_name,
                     c.search_condition, c.r_constraint_name, c.delete_rule,
                     c.status, r.table_name, r.owner
            ORDER BY c.table_name, c.constraint_type, c.constraint_name
        """

        cursor.execute(query, params)
        columns = [desc[0].lower() for desc in cursor.description]
        constraints = []
        for row in cursor.fetchall():
            d = dict(zip(columns, row))
            if d.get("search_condition") and hasattr(d["search_condition"], "read"):
                d["search_condition"] = d["search_condition"].read()
            constraints.append(d)

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "constraints": constraints,
            "count": len(constraints)
        }, default=str)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def oracle_get_indexes(schema: str, table_name: str = "") -> str:
    """
    Get index definitions from ALL_INDEXES/ALL_IND_COLUMNS.

    Args:
        schema: Schema name
        table_name: Optional table name to filter

    Returns:
        JSON string with index details including columns, uniqueness, type.

    Example:
        >>> oracle_get_indexes("HR", "EMPLOYEES")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                i.index_name,
                i.table_name,
                i.uniqueness,
                i.index_type,
                i.status,
                i.partitioned,
                LISTAGG(ic.column_name, ', ') WITHIN GROUP (ORDER BY ic.column_position) AS columns,
                LISTAGG(
                    CASE WHEN ic.descend = 'DESC' THEN ic.column_name || ' DESC'
                         ELSE ic.column_name END,
                    ', '
                ) WITHIN GROUP (ORDER BY ic.column_position) AS columns_with_order
            FROM all_indexes i
            JOIN all_ind_columns ic
                ON ic.index_owner = i.owner AND ic.index_name = i.index_name
            WHERE i.owner = :schema
        """
        params = {"schema": schema.upper()}

        if table_name:
            query += " AND i.table_name = :table_name"
            params["table_name"] = table_name.upper()

        query += """
            GROUP BY i.index_name, i.table_name, i.uniqueness,
                     i.index_type, i.status, i.partitioned
            ORDER BY i.table_name, i.index_name
        """

        cursor.execute(query, params)
        columns = [desc[0].lower() for desc in cursor.description]
        indexes = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "indexes": indexes,
            "count": len(indexes)
        }, default=str)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def oracle_get_sequences(schema: str) -> str:
    """
    Get sequence definitions from ALL_SEQUENCES.

    Args:
        schema: Schema name

    Returns:
        JSON string with sequence details (name, min/max, increment, cache, cycle).

    Example:
        >>> oracle_get_sequences("HR")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                sequence_name,
                min_value,
                max_value,
                increment_by,
                cache_size,
                cycle_flag,
                order_flag,
                last_number
            FROM all_sequences
            WHERE sequence_owner = :schema
            ORDER BY sequence_name
        """

        cursor.execute(query, schema=schema.upper())
        columns = [desc[0].lower() for desc in cursor.description]
        sequences = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "sequences": sequences,
            "count": len(sequences)
        }, default=str)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def oracle_get_partitions(schema: str, table_name: str = "") -> str:
    """
    Get partition information from ALL_PART_TABLES/ALL_TAB_PARTITIONS.

    Args:
        schema: Schema name
        table_name: Optional table name to filter

    Returns:
        JSON string with partition metadata (type, columns, partitions list).

    Example:
        >>> oracle_get_partitions("HR", "SALES")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                pt.table_name,
                pt.partitioning_type,
                pt.subpartitioning_type,
                pt.partition_count,
                LISTAGG(pk.column_name, ', ') WITHIN GROUP (ORDER BY pk.column_position) AS partition_keys
            FROM all_part_tables pt
            JOIN all_part_key_columns pk
                ON pk.owner = pt.owner AND pk.name = pt.table_name
            WHERE pt.owner = :schema
        """
        params = {"schema": schema.upper()}

        if table_name:
            query += " AND pt.table_name = :table_name"
            params["table_name"] = table_name.upper()

        query += """
            GROUP BY pt.table_name, pt.partitioning_type,
                     pt.subpartitioning_type, pt.partition_count
            ORDER BY pt.table_name
        """

        cursor.execute(query, params)
        columns = [desc[0].lower() for desc in cursor.description]
        tables = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for tbl in tables:
            part_query = """
                SELECT
                    partition_name,
                    partition_position,
                    high_value,
                    num_rows,
                    tablespace_name
                FROM all_tab_partitions
                WHERE table_owner = :schema AND table_name = :tname
                ORDER BY partition_position
            """
            cursor.execute(part_query, schema=schema.upper(), tname=tbl["table_name"])
            pcols = [desc[0].lower() for desc in cursor.description]
            parts = []
            for row in cursor.fetchall():
                d = dict(zip(pcols, row))
                if d.get("high_value") and hasattr(d["high_value"], "read"):
                    d["high_value"] = d["high_value"].read()
                parts.append(d)
            tbl["partitions"] = parts

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "partitioned_tables": tables,
            "count": len(tables)
        }, default=str)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def oracle_export_table_data(table_name: str, schema: str, batch_size: int = 1000) -> str:
    """
    Export all rows from an Oracle table as JSON for migration to PostgreSQL.

    Args:
        table_name: Table name to export
        schema: Schema name
        batch_size: Fetch array size (default 1000)

    Returns:
        JSON string with table data including columns and rows arrays.

    Example:
        >>> oracle_export_table_data("USERS", "AMZN")
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")

        cursor.arraysize = batch_size
        cursor.execute(f"SELECT * FROM {schema}.{table_name}")
        columns = [desc[0] for desc in cursor.description]

        all_rows = []
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                all_rows.append([
                    v.read() if hasattr(v, 'read') else v
                    for v in row
                ])

        cursor.close()
        conn.close()

        return json.dumps({
            "success": True,
            "table_name": table_name.upper(),
            "schema": schema.upper(),
            "columns": columns,
            "rows": all_rows,
            "row_count": len(all_rows),
        }, default=str)

    except Exception as e:
        return json.dumps({
            "success": False,
            "table_name": table_name,
            "error": str(e),
        })
