#!/usr/bin/env python3
"""
NUMBER Type Optimizer - Analyze Oracle NUMBER columns and optimize PostgreSQL types

After DMS SC creates tables, this tool:
1. Scans all Oracle NUMBER columns
2. Analyzes actual data (min, max, scale)
3. Determines optimal PostgreSQL type (SMALLINT, INTEGER, BIGINT, NUMERIC)
4. Generates and executes ALTER TABLE statements

Run this AFTER DMS SC and BEFORE Full Load for best results.
"""

import json
import logging
import os
import sys
from typing import List, Dict, Tuple

# Add parent paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'schema', 'common', 'tools'))

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import pymysql
except ImportError:
    pymysql = None

logger = logging.getLogger(__name__)


class NumberTypeOptimizer:
    """Optimize Oracle NUMBER to PostgreSQL type mappings.

    Also optimizes PostgreSQL DOUBLE PRECISION and BIGINT columns
    that came from Oracle NUMBER.
    """

    def __init__(self, oracle_schema: str, target_config: dict):
        self.oracle_schema = oracle_schema.upper()
        self.target_config = target_config
        self.target_db_type = target_config.get('db_type', 'postgres')  # 'postgres' or 'mysql'
        self.analysis_results = []

        # Types to optimize per database
        if self.target_db_type == 'mysql':
            self.numeric_types = ['bigint', 'double', 'decimal', 'int', 'tinyint', 'smallint']
        else:
            self.numeric_types = ['bigint', 'double precision', 'numeric', 'integer', 'smallint']

    def get_oracle_connection(self):
        """Get Oracle connection."""
        try:
            import oracledb
            return oracledb.connect(
                user=os.environ.get("ORACLE_USER"),
                password=os.environ.get("ORACLE_PASSWORD"),
                host=os.environ.get("ORACLE_HOST"),
                port=int(os.environ.get("ORACLE_PORT", 1521)),
                service_name=os.environ.get("ORACLE_SID")
            )
        except ImportError:
            logger.error("oracledb module not available")
            return None

    def get_target_connection(self):
        """Get target database connection (PostgreSQL or MySQL)."""
        if self.target_db_type == 'mysql':
            if not pymysql:
                raise ImportError("pymysql module not available")
            return pymysql.connect(
                host=self.target_config['host'],
                port=self.target_config['port'],
                database=self.target_config['database'],
                user=self.target_config['user'],
                password=self.target_config['password'],
                charset='utf8mb4'
            )
        else:
            if not psycopg2:
                raise ImportError("psycopg2 module not available")
            return psycopg2.connect(
                host=self.target_config['host'],
                port=self.target_config['port'],
                database=self.target_config['database'],
                user=self.target_config['user'],
                password=self.target_config['password']
            )

    def fix_all_integer_number_to_numeric(self) -> List[Dict]:
        """
        Fix ALL NUMBER columns that DMS SC converted to BIGINT/INTEGER.

        Optimized logic (reverse approach):
        1. PostgreSQL에서 BIGINT/INTEGER/SMALLINT/DOUBLE PRECISION 컬럼 전체 조회 (1번 쿼리)
        2. Oracle에서 해당 컬럼들이 NUMBER(scale=0)인지 확인 (1번 쿼리)
        3. 메모리에서 매칭 (빠름)

        Total: 2번 쿼리 (기존 N+1번 대비 엄청 빠름)
        """
        logger.info("=" * 60)
        logger.info("Fixing ALL Oracle NUMBER columns converted to INTEGER types...")
        logger.info("=" * 60)

        # Step 1: PostgreSQL에서 BIGINT/INTEGER 컬럼 전체 조회
        target_conn = self.get_target_connection()
        cur = target_conn.cursor()

        cur.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s
              AND data_type IN ('bigint', 'integer', 'smallint', 'double precision')
            ORDER BY table_name, column_name
        """, (self.target_config['schema'],))

        pg_integer_columns = cur.fetchall()
        cur.close()
        target_conn.close()

        logger.info("Found %d PostgreSQL INTEGER-type columns", len(pg_integer_columns))

        if not pg_integer_columns:
            return []

        # Step 2: Oracle에서 NUMBER(scale=0) 컬럼 전체 조회
        oracle_conn = self.get_oracle_connection()
        if not oracle_conn:
            logger.error("Cannot connect to Oracle")
            return []

        ora_cur = oracle_conn.cursor()

        ora_cur.execute("""
            SELECT
                c.table_name,
                c.column_name,
                c.data_type,
                c.data_precision,
                c.data_scale,
                CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM all_tab_columns c
            LEFT JOIN (
                SELECT acc.table_name, acc.column_name
                FROM all_constraints ac
                JOIN all_cons_columns acc
                    ON ac.constraint_name = acc.constraint_name
                    AND ac.owner = acc.owner
                WHERE ac.constraint_type = 'P'
                  AND ac.owner = :schema
            ) pk ON c.table_name = pk.table_name
                AND c.column_name = pk.column_name
            WHERE c.owner = :schema
              AND c.data_type = 'NUMBER'
              AND (c.data_scale = 0 OR c.data_scale IS NULL)
            ORDER BY c.table_name, c.column_name
        """, schema=self.oracle_schema)

        oracle_numbers = ora_cur.fetchall()
        ora_cur.close()
        oracle_conn.close()

        logger.info("Found %d Oracle NUMBER(scale=0) columns", len(oracle_numbers))

        # Step 3: 메모리에서 매칭 (빠름)
        # Oracle 컬럼을 dict로 변환
        oracle_map = {}
        for table_name, column_name, data_type, data_precision, data_scale, is_pk in oracle_numbers:
            key = (table_name.lower(), column_name.lower())
            oracle_map[key] = {
                'data_type': data_type,
                'data_precision': data_precision,
                'data_scale': data_scale,
                'is_pk': is_pk
            }

        # PostgreSQL 컬럼과 매칭
        results = []
        for table_name, column_name, pg_type in pg_integer_columns:
            key = (table_name, column_name)

            if key in oracle_map:
                oracle_info = oracle_map[key]
                data_precision = oracle_info['data_precision']
                data_scale = oracle_info['data_scale']
                is_pk = oracle_info['is_pk']

                # Recommend NUMERIC with Oracle precision
                if data_precision:
                    recommended = f"NUMERIC({data_precision},0)"
                else:
                    recommended = "NUMERIC(38,0)"

                results.append({
                    'table_name': table_name,
                    'column_name': column_name,
                    'current_type': pg_type,
                    'oracle_type': 'NUMBER',
                    'oracle_precision': data_precision,
                    'oracle_scale': data_scale,
                    'recommended_type': recommended,
                    'reason': f"Oracle NUMBER {'(PK)' if is_pk else ''} - DMS Full Load requires NUMERIC"
                })

        logger.info("=" * 60)
        logger.info("Found %d columns to fix (matched from both sides)", len(results))
        logger.info("=" * 60)

        self.analysis_results = results
        return results

    def fix_pk_number_to_numeric(self) -> List[Dict]:
        """
        Fix PK NUMBER columns that DMS SC converted to BIGINT/INTEGER.

        Oracle-based logic:
        1. Find Oracle PK columns with NUMBER type (scale=0 or NULL)
        2. Check if PostgreSQL converted them to BIGINT/INTEGER
        3. Convert back to NUMERIC(precision, 0) for DMS Full Load compatibility

        DMS Full Load extracts Oracle NUMBER as "123.0000000000" format,
        which is incompatible with BIGINT/INTEGER.
        """
        logger.info("=" * 60)
        logger.info("Fixing Oracle PK NUMBER columns...")
        logger.info("=" * 60)

        oracle_conn = self.get_oracle_connection()
        if not oracle_conn:
            logger.error("Cannot connect to Oracle")
            return []

        ora_cur = oracle_conn.cursor()

        # Find Oracle PK NUMBER columns (scale=0 or NULL - integer type)
        ora_cur.execute("""
            SELECT
                c.table_name,
                c.column_name,
                c.data_type,
                c.data_precision,
                c.data_scale
            FROM all_tab_columns c
            JOIN (
                SELECT acc.table_name, acc.column_name
                FROM all_constraints ac
                JOIN all_cons_columns acc
                    ON ac.constraint_name = acc.constraint_name
                    AND ac.owner = acc.owner
                WHERE ac.constraint_type = 'P'
                  AND ac.owner = :schema
            ) pk ON c.table_name = pk.table_name
                AND c.column_name = pk.column_name
            WHERE c.owner = :schema
              AND c.data_type = 'NUMBER'
              AND (c.data_scale = 0 OR c.data_scale IS NULL)
            ORDER BY c.table_name, c.column_name
        """, schema=self.oracle_schema)

        oracle_pk_numbers = ora_cur.fetchall()
        ora_cur.close()
        oracle_conn.close()

        logger.info("Found %d Oracle PK NUMBER(scale=0) columns", len(oracle_pk_numbers))

        if not oracle_pk_numbers:
            return []

        # Check PostgreSQL types for these columns
        target_conn = self.get_target_connection()
        cur = target_conn.cursor()

        results = []
        for table_name, column_name, data_type, data_precision, data_scale in oracle_pk_numbers:
            try:
                cur.execute("""
                    SELECT data_type, numeric_precision, numeric_scale
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                      AND column_name = %s
                """, (self.target_config['schema'], table_name.lower(), column_name.lower()))

                pg_row = cur.fetchone()
                if pg_row:
                    pg_type = pg_row[0]

                    # Only fix if PostgreSQL type is BIGINT/INTEGER/SMALLINT
                    if pg_type in ('bigint', 'integer', 'smallint', 'double precision'):
                        # Recommend NUMERIC with Oracle precision
                        if data_precision:
                            recommended = f"NUMERIC({data_precision},0)"
                        else:
                            recommended = "NUMERIC(38,0)"

                        results.append({
                            'table_name': table_name.lower(),
                            'column_name': column_name.lower(),
                            'current_type': pg_type,
                            'oracle_type': 'NUMBER',
                            'oracle_precision': data_precision,
                            'oracle_scale': data_scale,
                            'recommended_type': recommended,
                            'reason': 'Oracle PK NUMBER - DMS Full Load requires NUMERIC'
                        })

                        logger.info("Found: %s.%s (Oracle NUMBER(%s,0) → PG %s → Fix to %s)",
                                   table_name, column_name, data_precision or 38,
                                   pg_type.upper(), recommended)
            except Exception as e:
                logger.warning("Failed to check %s.%s: %s", table_name, column_name, e)
                continue

        cur.close()
        target_conn.close()

        logger.info("=" * 60)
        logger.info("Found %d PK columns to fix", len(results))
        logger.info("=" * 60)

        self.analysis_results = results
        return results

    def analyze_oracle_numbers(self) -> List[Dict]:
        """
        Analyze all Oracle NUMBER columns.

        Returns list of:
        {
            'table_name': str,
            'column_name': str,
            'data_type': 'NUMBER',
            'data_precision': int or None,
            'data_scale': int or None,
            'nullable': bool,
            'is_pk': bool,
            'is_fk': bool,
            'min_value': decimal or None,
            'max_value': decimal or None,
            'has_decimals': bool,
            'row_count': int,
            'recommended_type': str
        }
        """
        logger.info("=" * 60)
        logger.info("Analyzing Oracle NUMBER columns...")
        logger.info("=" * 60)

        oracle_conn = self.get_oracle_connection()
        if not oracle_conn:
            logger.error("Cannot connect to Oracle")
            return []

        cur = oracle_conn.cursor()

        # Get all NUMBER columns with metadata
        cur.execute("""
            SELECT
                c.table_name,
                c.column_name,
                c.data_type,
                c.data_precision,
                c.data_scale,
                c.nullable,
                CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk,
                CASE WHEN fk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_fk
            FROM all_tab_columns c
            LEFT JOIN (
                SELECT acc.table_name, acc.column_name
                FROM all_constraints ac
                JOIN all_cons_columns acc ON ac.constraint_name = acc.constraint_name
                    AND ac.owner = acc.owner
                WHERE ac.constraint_type = 'P'
                  AND ac.owner = :schema
            ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
            LEFT JOIN (
                SELECT acc.table_name, acc.column_name
                FROM all_constraints ac
                JOIN all_cons_columns acc ON ac.constraint_name = acc.constraint_name
                    AND ac.owner = acc.owner
                WHERE ac.constraint_type = 'R'
                  AND ac.owner = :schema
            ) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
            WHERE c.owner = :schema
              AND c.data_type = 'NUMBER'
            ORDER BY c.table_name, c.column_id
        """, schema=self.oracle_schema)

        columns = cur.fetchall()
        logger.info("Found %d NUMBER columns", len(columns))

        # Group by table for efficient batch analysis
        from collections import defaultdict
        columns_by_table = defaultdict(list)
        for col in columns:
            table_name = col[0]
            columns_by_table[table_name].append(col)

        logger.info("Analyzing %d tables...", len(columns_by_table))

        results = []
        table_num = 0
        for table_name, table_columns in columns_by_table.items():
            table_num += 1
            logger.info("[%d/%d] Analyzing table %s (%d NUMBER columns)...",
                       table_num, len(columns_by_table), table_name, len(table_columns))

            # Get row count once per table
            try:
                cur.execute(f"SELECT COUNT(*) FROM {self.oracle_schema}.{table_name}")
                row_count = cur.fetchone()[0]
            except Exception as e:
                logger.warning("Failed to get row count for %s: %s", table_name, e)
                continue

            # Build dynamic query to analyze all NUMBER columns at once
            if row_count == 0:
                # Empty table - skip data analysis
                for col in table_columns:
                    (_, column_name, data_type, data_precision, data_scale,
                     nullable, is_pk, is_fk) = col

                    recommended_type = self._recommend_target_type(
                        data_precision, data_scale, None, None, False,
                        bool(is_pk), bool(is_fk), row_count
                    )

                    results.append({
                        'table_name': table_name.lower(),
                        'column_name': column_name.lower(),
                        'data_type': data_type,
                        'data_precision': data_precision,
                        'data_scale': data_scale,
                        'nullable': nullable == 'Y',
                        'is_pk': bool(is_pk),
                        'is_fk': bool(is_fk),
                        'min_value': None,
                        'max_value': None,
                        'has_decimals': False,
                        'row_count': row_count,
                        'recommended_type': recommended_type
                    })
            else:
                # Build single query for all columns
                select_parts = []
                for col in table_columns:
                    column_name = col[1]
                    select_parts.append(f"MIN({column_name}) as min_{column_name}")
                    select_parts.append(f"MAX({column_name}) as max_{column_name}")
                    select_parts.append(f"CASE WHEN COUNT({column_name}) = COUNT(CASE WHEN MOD({column_name}, 1) = 0 THEN 1 END) THEN 0 ELSE 1 END as dec_{column_name}")

                try:
                    query = f"SELECT {', '.join(select_parts)} FROM {self.oracle_schema}.{table_name}"
                    cur.execute(query)
                    result = cur.fetchone()

                    # Process results for each column
                    for idx, col in enumerate(table_columns):
                        (_, column_name, data_type, data_precision, data_scale,
                         nullable, is_pk, is_fk) = col

                        min_val = result[idx * 3]
                        max_val = result[idx * 3 + 1]
                        has_decimals = result[idx * 3 + 2]

                        recommended_type = self._recommend_target_type(
                            data_precision, data_scale, min_val, max_val, has_decimals,
                            bool(is_pk), bool(is_fk), row_count
                        )

                        results.append({
                            'table_name': table_name.lower(),
                            'column_name': column_name.lower(),
                            'data_type': data_type,
                            'data_precision': data_precision,
                            'data_scale': data_scale,
                            'nullable': nullable == 'Y',
                            'is_pk': bool(is_pk),
                            'is_fk': bool(is_fk),
                            'min_value': float(min_val) if min_val is not None else None,
                            'max_value': float(max_val) if max_val is not None else None,
                            'has_decimals': bool(has_decimals),
                            'row_count': row_count,
                            'recommended_type': recommended_type
                        })
                except Exception as e:
                    logger.warning("Failed to analyze table %s: %s", table_name, e)
                    continue

        cur.close()
        oracle_conn.close()

        self.analysis_results = results
        return results

    def _recommend_target_type(self, data_precision, data_scale, min_val, max_val,
                                has_decimals, is_pk, is_fk, row_count) -> str:
        """
        Recommend optimal target database type based on analysis.

        PostgreSQL logic:
        - If has_decimals or data_scale > 0: NUMERIC(p,s)
        - If fits in SMALLINT: SMALLINT
        - If fits in INTEGER: INTEGER
        - If fits in BIGINT: BIGINT
        - Otherwise: NUMERIC

        MySQL logic:
        - If has_decimals or data_scale > 0: DECIMAL(p,s)
        - If fits in TINYINT: TINYINT
        - If fits in SMALLINT: SMALLINT
        - If fits in INT: INT
        - If fits in BIGINT: BIGINT
        - Otherwise: DECIMAL
        """
        is_mysql = self.target_db_type == 'mysql'
        decimal_type = "DECIMAL" if is_mysql else "NUMERIC"

        # If explicit scale, use DECIMAL/NUMERIC
        if data_scale is not None and data_scale > 0:
            precision = data_precision if data_precision else 38
            return f"{decimal_type}({precision},{data_scale})"

        # If has decimal values, use DECIMAL/NUMERIC
        if has_decimals:
            precision = data_precision if data_precision else 38
            scale = data_scale if data_scale is not None else 10
            return f"{decimal_type}({precision},{scale})"

        # Integer types - check range
        if min_val is None or max_val is None:
            # No data - use safe default
            if is_pk or is_fk:
                return "BIGINT"
            else:
                return "INT" if is_mysql else "INTEGER"

        # TINYINT (MySQL only): -128 to 127 / 0 to 255
        if is_mysql and min_val >= -128 and max_val <= 127:
            return "TINYINT"

        # SMALLINT: -32768 to 32767
        if min_val >= -32768 and max_val <= 32767:
            return "SMALLINT"

        # INTEGER/INT: -2147483648 to 2147483647
        if min_val >= -2147483648 and max_val <= 2147483647:
            return "INT" if is_mysql else "INTEGER"

        # BIGINT: -9223372036854775808 to 9223372036854775807
        if min_val >= -9223372036854775808 and max_val <= 9223372036854775807:
            return "BIGINT"

        # Too large for BIGINT
        precision = data_precision if data_precision else 38
        return f"{decimal_type}({precision},0)"

    def generate_alter_statements(self) -> List[str]:
        """
        Generate ALTER TABLE statements to change types.

        Returns list of SQL statements.
        """
        if not self.analysis_results:
            logger.warning("No analysis results available")
            return []

        logger.info("=" * 60)
        logger.info("Generating ALTER TABLE statements...")
        logger.info("=" * 60)

        # Get current PostgreSQL types
        pg_conn = self.get_target_connection()
        cur = pg_conn.cursor()

        cur.execute("""
            SELECT table_name, column_name,
                   CASE
                       WHEN data_type = 'numeric' THEN
                           'NUMERIC(' || COALESCE(numeric_precision::text, '38') ||
                           ',' || COALESCE(numeric_scale::text, '0') || ')'
                       ELSE UPPER(data_type)
                   END as full_type
            FROM information_schema.columns
            WHERE table_schema = %s
        """, (self.target_config['schema'],))

        current_types = {}
        for row in cur.fetchall():
            table_name, column_name, full_type = row
            current_types[(table_name, column_name)] = full_type

        cur.close()
        pg_conn.close()

        # Generate ALTER statements
        alter_statements = []
        changes = []

        for result in self.analysis_results:
            table_name = result['table_name']
            column_name = result['column_name']
            recommended_type = result['recommended_type']

            current_type = current_types.get((table_name, column_name))

            if not current_type:
                logger.warning("Column not found in PostgreSQL: %s.%s", table_name, column_name)
                continue

            # Normalize types for comparison
            current_normalized = current_type.replace(' ', '').upper()
            recommended_normalized = recommended_type.replace(' ', '').upper()

            if current_normalized != recommended_normalized:
                alter_sql = (
                    f"ALTER TABLE {self.target_config['schema']}.{table_name} "
                    f"ALTER COLUMN {column_name} TYPE {recommended_type} "
                    f"USING {column_name}::{recommended_type};"
                )
                alter_statements.append(alter_sql)

                changes.append({
                    'table': table_name,
                    'column': column_name,
                    'from': current_type,
                    'to': recommended_type,
                    'reason': self._get_change_reason(result)
                })

        logger.info("Generated %d ALTER statements (%d columns unchanged)",
                   len(alter_statements), len(self.analysis_results) - len(alter_statements))

        for change in changes[:10]:  # Show first 10
            logger.info("  %s.%s: %s → %s (%s)",
                       change['table'], change['column'],
                       change['from'], change['to'], change['reason'])

        if len(changes) > 10:
            logger.info("  ... and %d more changes", len(changes) - 10)

        return alter_statements

    def _get_change_reason(self, result: Dict) -> str:
        """Get human-readable reason for type change."""
        # If reason is already provided (from fix_pk_number_to_numeric), use it
        if 'reason' in result:
            return result['reason']

        # Otherwise, derive from analysis results (from analyze_oracle_numbers)
        if result.get('has_decimals'):
            return "has decimal values"
        if result.get('is_pk'):
            return "PK"
        if result.get('is_fk'):
            return "FK"
        if result.get('max_value') and result['max_value'] <= 32767:
            return "fits in SMALLINT"
        if result.get('max_value') and result['max_value'] <= 2147483647:
            return "fits in INTEGER"
        return "integer range"

    def apply_optimizations(self, alter_statements: List[str]) -> Dict:
        """
        Apply ALTER TABLE statements to PostgreSQL.

        Returns:
            dict: {
                "success": bool,
                "applied_count": int,
                "failed_count": int,
                "failed": [str]
            }
        """
        if not alter_statements:
            logger.info("No type changes needed")
            return {
                "success": True,
                "applied_count": 0,
                "failed_count": 0,
                "failed": []
            }

        logger.info("=" * 60)
        logger.info("Applying type optimizations...")
        logger.info("=" * 60)

        pg_conn = self.get_target_connection()
        cur = pg_conn.cursor()

        applied = 0
        failed = []

        for i, alter_sql in enumerate(alter_statements):
            logger.info("[%d/%d] Applying: %s", i + 1, len(alter_statements),
                       alter_sql[:80] + "..." if len(alter_sql) > 80 else alter_sql)

            try:
                cur.execute(alter_sql)
                pg_conn.commit()
                applied += 1
            except Exception as e:
                pg_conn.rollback()  # Rollback first to clean transaction state
                error_msg = str(e).lower()

                # IDENTITY column 에러 처리
                if "identity column type must be" in error_msg:
                    # ALTER TABLE table ALTER COLUMN col TYPE NUMERIC... 에서 table, col 추출
                    import re
                    match = re.search(r'ALTER TABLE (\S+)\.(\S+) ALTER COLUMN (\S+) TYPE', alter_sql)
                    if match:
                        schema, table, column = match.groups()
                        logger.info("  Retrying with IDENTITY drop...")

                        try:
                            # New clean transaction for IDENTITY drop
                            cur.execute(f"ALTER TABLE {schema}.{table} ALTER COLUMN {column} DROP IDENTITY IF EXISTS")
                            pg_conn.commit()

                            # Another clean transaction for type change
                            cur.execute(alter_sql)
                            pg_conn.commit()
                            applied += 1
                            logger.info("  ✓ Success (after dropping IDENTITY)")
                            continue
                        except Exception as e2:
                            logger.warning("  Failed even after dropping IDENTITY: %s", e2)
                            failed.append(f"{alter_sql} -- ERROR: {e2}")
                            pg_conn.rollback()
                            continue

                logger.warning("Failed: %s", e)
                failed.append(f"{alter_sql} -- ERROR: {e}")

        cur.close()
        pg_conn.close()

        logger.info("✓ Applied %d type changes (%d failed)", applied, len(failed))

        return {
            "success": True,
            "applied_count": applied,
            "failed_count": len(failed),
            "failed": failed
        }

    def save_report(self, output_file: str = "/tmp/number_type_optimization_report.json"):
        """Save analysis report to JSON file."""
        report = {
            "oracle_schema": self.oracle_schema,
            "total_columns": len(self.analysis_results),
            "columns": self.analysis_results
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info("✓ Saved report to: %s", output_file)


def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True, help="Oracle schema name")
    parser.add_argument("--apply", action="store_true", help="Apply optimizations (default: dry-run)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # PostgreSQL config from environment
    pg_config = {
        'host': os.environ.get('PGHOST'),
        'port': int(os.environ.get('PGPORT', 5432)),
        'database': os.environ.get('PGDATABASE'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD'),
        'schema': os.environ.get('PGSCHEMA', args.schema.lower())
    }

    optimizer = NumberTypeOptimizer(args.schema, pg_config)

    # Step 1: Analyze Oracle NUMBER columns
    results = optimizer.analyze_oracle_numbers()

    if not results:
        logger.error("No NUMBER columns found or analysis failed")
        return 1

    # Step 2: Generate ALTER statements
    alter_statements = optimizer.generate_alter_statements()

    # Step 3: Save report
    optimizer.save_report()

    # Step 4: Apply if requested
    if args.apply:
        result = optimizer.apply_optimizations(alter_statements)
        if result['failed']:
            logger.warning("Some optimizations failed:")
            for fail in result['failed'][:5]:
                logger.warning("  %s", fail[:150])
    else:
        logger.info("=" * 60)
        logger.info("DRY RUN - No changes applied")
        logger.info("=" * 60)
        logger.info("To apply optimizations, run with --apply flag")
        logger.info("Review report: /tmp/number_type_optimization_report.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
