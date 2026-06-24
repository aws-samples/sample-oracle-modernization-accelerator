#!/usr/bin/env python3
"""
Oracle Dictionary Generator
Extracts metadata and sample data from Oracle database schema
"""

import os
import sys
import json
import oracledb
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class OracleDictionary:
    """Oracle database dictionary manager"""

    def __init__(self, host: str, port: int, sid: str, user: str, password: str,
                 schema: str, conn_type: str = "service"):
        self.host = host
        self.port = port
        self.sid = sid
        self.user = user
        self.password = password
        self.schema = schema.upper()
        self.conn_type = conn_type
        self.connection = None
        self.dictionary = {}

    def connect(self):
        """Connect to Oracle database"""
        try:
            if self.conn_type == "service":
                dsn = f"{self.host}:{self.port}/{self.sid}"
            else:
                dsn = f"{self.host}:{self.port}/{self.sid}"

            self.connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=dsn
            )
            print(f"✓ Connected to Oracle: {self.user}@{self.host}:{self.port}/{self.sid}")
            return True
        except oracledb.Error as e:
            print(f"✗ Oracle connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from Oracle database"""
        if self.connection:
            self.connection.close()
            print("✓ Disconnected from Oracle")

    def get_tables(self) -> List[str]:
        """Get all tables in the schema"""
        query = """
            SELECT table_name
            FROM all_tables
            WHERE owner = :1
            ORDER BY table_name
        """
        cursor = self.connection.cursor()
        cursor.execute(query, [self.schema])
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """Get metadata for a specific table"""
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
            WHERE owner = :1 AND table_name = :2
            ORDER BY column_id
        """
        cursor = self.connection.cursor()
        cursor.execute(query, [self.schema, table_name])

        columns = []
        for row in cursor.fetchall():
            column = {
                "column_name": row[0],
                "data_type": row[1],
                "data_length": row[2],
                "data_precision": row[3],
                "data_scale": row[4],
                "nullable": row[5] == 'Y',
                "column_id": row[6],
                "default_value": row[7].strip() if row[7] else None
            }
            columns.append(column)

        cursor.close()
        return columns

    def get_primary_key(self, table_name: str) -> List[str]:
        """Get primary key columns for a table"""
        query = """
            SELECT acc.column_name
            FROM all_constraints ac
            JOIN all_cons_columns acc ON ac.constraint_name = acc.constraint_name
                AND ac.owner = acc.owner
            WHERE ac.owner = :1
                AND ac.table_name = :2
                AND ac.constraint_type = 'P'
            ORDER BY acc.position
        """
        cursor = self.connection.cursor()
        cursor.execute(query, [self.schema, table_name])
        pk_columns = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return pk_columns

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key constraints for a table"""
        query = """
            SELECT
                ac.constraint_name,
                acc.column_name,
                ac_ref.table_name as ref_table,
                acc_ref.column_name as ref_column
            FROM all_constraints ac
            JOIN all_cons_columns acc ON ac.constraint_name = acc.constraint_name
                AND ac.owner = acc.owner
            JOIN all_constraints ac_ref ON ac.r_constraint_name = ac_ref.constraint_name
                AND ac.r_owner = ac_ref.owner
            JOIN all_cons_columns acc_ref ON ac_ref.constraint_name = acc_ref.constraint_name
                AND ac_ref.owner = acc_ref.owner
                AND acc.position = acc_ref.position
            WHERE ac.owner = :1
                AND ac.table_name = :2
                AND ac.constraint_type = 'R'
            ORDER BY ac.constraint_name, acc.position
        """
        cursor = self.connection.cursor()
        cursor.execute(query, [self.schema, table_name])

        fk_dict = {}
        for row in cursor.fetchall():
            fk_name = row[0]
            if fk_name not in fk_dict:
                fk_dict[fk_name] = {
                    "constraint_name": fk_name,
                    "columns": [],
                    "referenced_table": row[2],
                    "referenced_columns": []
                }
            fk_dict[fk_name]["columns"].append(row[1])
            fk_dict[fk_name]["referenced_columns"].append(row[3])

        cursor.close()
        return list(fk_dict.values())

    def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a table"""
        query = """
            SELECT
                ai.index_name,
                ai.uniqueness,
                aic.column_name,
                aic.column_position
            FROM all_indexes ai
            JOIN all_ind_columns aic ON ai.index_name = aic.index_name
                AND ai.owner = aic.index_owner
            WHERE ai.owner = :1
                AND ai.table_name = :2
            ORDER BY ai.index_name, aic.column_position
        """
        cursor = self.connection.cursor()
        cursor.execute(query, [self.schema, table_name])

        idx_dict = {}
        for row in cursor.fetchall():
            idx_name = row[0]
            if idx_name not in idx_dict:
                idx_dict[idx_name] = {
                    "index_name": idx_name,
                    "unique": row[1] == 'UNIQUE',
                    "columns": []
                }
            idx_dict[idx_name]["columns"].append(row[2])

        cursor.close()
        return list(idx_dict.values())

    def get_sample_data(self, table_name: str, column_name: str, limit: int = 1) -> Any:
        """Get sample data for a specific column"""
        try:
            query = f"""
                SELECT {column_name}
                FROM {self.schema}.{table_name}
                WHERE {column_name} IS NOT NULL
                AND ROWNUM <= :1
            """
            cursor = self.connection.cursor()
            cursor.execute(query, [limit])
            result = cursor.fetchone()
            cursor.close()

            if result:
                value = result[0]
                if isinstance(value, (datetime,)):
                    return value.isoformat()
                elif isinstance(value, (bytes,)):
                    return f"<BLOB {len(value)} bytes>"
                else:
                    return str(value) if value is not None else None
            return None
        except oracledb.Error as e:
            return f"<Error: {str(e)[:100]}>"

    def get_table_row_count(self, table_name: str) -> int:
        """Get approximate row count for a table"""
        try:
            query = f"SELECT COUNT(*) FROM {self.schema}.{table_name}"
            cursor = self.connection.cursor()
            cursor.execute(query)
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except cx_Oracle.Error:
            return -1

    def get_table_comments(self, table_name: str) -> str:
        """Get table comments"""
        query = """
            SELECT comments
            FROM all_tab_comments
            WHERE owner = :1 AND table_name = :2
        """
        cursor = self.connection.cursor()
        cursor.execute(query, [self.schema, table_name])
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result and result[0] else None

    def get_column_comments(self, table_name: str) -> Dict[str, str]:
        """Get column comments for a table"""
        query = """
            SELECT column_name, comments
            FROM all_col_comments
            WHERE owner = :1 AND table_name = :2
        """
        cursor = self.connection.cursor()
        cursor.execute(query, [self.schema, table_name])
        comments = {row[0]: row[1] for row in cursor.fetchall() if row[1]}
        cursor.close()
        return comments

    def build_dictionary(self, sample_size: int = 1):
        """Build complete dictionary for all tables in schema"""
        print(f"\n=== Building Oracle Dictionary for schema: {self.schema} ===\n")

        tables = self.get_tables()
        print(f"Found {len(tables)} tables\n")

        self.dictionary = {
            "schema": self.schema,
            "generated_at": datetime.now().isoformat(),
            "table_count": len(tables),
            "tables": {}
        }

        for idx, table_name in enumerate(tables, 1):
            print(f"[{idx}/{len(tables)}] Processing {table_name}...")

            try:
                columns_meta = self.get_table_metadata(table_name)
                pk_columns = self.get_primary_key(table_name)
                row_count = self.get_table_row_count(table_name)
                table_comment = self.get_table_comments(table_name)
                column_comments = self.get_column_comments(table_name)

                # Add sample data to each column
                for col in columns_meta:
                    col["sample_value"] = self.get_sample_data(table_name, col["column_name"], sample_size)
                    col["comment"] = column_comments.get(col["column_name"])

                self.dictionary["tables"][table_name] = {
                    "table_name": table_name,
                    "row_count": row_count,
                    "comment": table_comment,
                    "columns": columns_meta,
                    "primary_key": pk_columns
                }

                print(f"  ✓ {len(columns_meta)} columns, {row_count} rows")

            except Exception as e:
                print(f"  ✗ Error processing {table_name}: {e}")
                self.dictionary["tables"][table_name] = {"error": str(e)}

        print(f"\n✓ Dictionary build complete: {len(self.dictionary['tables'])} tables processed")

    def save_dictionary(self, output_path: str):
        """Save dictionary to JSON file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.dictionary, f, indent=2, ensure_ascii=False)

        print(f"✓ Dictionary saved to: {output_file}")

    def load_dictionary(self, input_path: str):
        """Load dictionary from JSON file"""
        with open(input_path, 'r', encoding='utf-8') as f:
            self.dictionary = json.load(f)
        print(f"✓ Dictionary loaded from: {input_path}")

    def lookup(self, table_column: str) -> Optional[Dict[str, Any]]:
        """
        Lookup column information by table.column format

        Args:
            table_column: Format "TABLE_NAME.COLUMN_NAME"

        Returns:
            Dictionary with column info including sample_value and data_type
        """
        try:
            parts = table_column.split('.')
            if len(parts) != 2:
                return {
                    "error": "Invalid format. Use TABLE_NAME.COLUMN_NAME"
                }

            table_name, column_name = parts[0].upper(), parts[1].upper()

            if table_name not in self.dictionary.get("tables", {}):
                return {
                    "error": f"Table '{table_name}' not found in dictionary"
                }

            table_info = self.dictionary["tables"][table_name]

            if "error" in table_info:
                return {
                    "error": f"Table '{table_name}' has error: {table_info['error']}"
                }

            for column in table_info.get("columns", []):
                if column["column_name"] == column_name:
                    return {
                        "table_name": table_name,
                        "column_name": column_name,
                        "data_type": column["data_type"],
                        "data_length": column["data_length"],
                        "data_precision": column["data_precision"],
                        "data_scale": column["data_scale"],
                        "nullable": column["nullable"],
                        "sample_value": column["sample_value"],
                        "comment": column.get("comment"),
                        "is_primary_key": column_name in table_info.get("primary_key", [])
                    }

            return {
                "error": f"Column '{column_name}' not found in table '{table_name}'"
            }

        except Exception as e:
            return {
                "error": f"Lookup error: {str(e)}"
            }

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get full table information"""
        table_name = table_name.upper()
        if table_name in self.dictionary.get("tables", {}):
            return self.dictionary["tables"][table_name]
        return None


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Oracle Dictionary Generator')
    parser.add_argument('--build', action='store_true', help='Build dictionary from Oracle')
    parser.add_argument('--lookup', type=str, help='Lookup column info (TABLE.COLUMN)')
    parser.add_argument('--table', type=str, help='Get table info')
    parser.add_argument('--output', type=str, default='./output/oracle_dictionary.json',
                        help='Output JSON file path')
    parser.add_argument('--input', type=str, default='./output/oracle_dictionary.json',
                        help='Input JSON file path for lookup')
    parser.add_argument('--sample-size', type=int, default=1,
                        help='Number of sample rows per column')

    args = parser.parse_args()

    # Get all settings from environment variables
    oracle_dict = OracleDictionary(
        host=os.getenv('ORACLE_HOST'),
        port=int(os.getenv('ORACLE_PORT', '1521')),
        sid=os.getenv('ORACLE_SID'),
        user=os.getenv('ORACLE_USER'),
        password=os.getenv('ORACLE_PASSWORD'),
        schema=os.getenv('ORACLE_SCHEMA'),
        conn_type=os.getenv('ORACLE_CONN_TYPE', 'service')
    )

    if args.build:
        if oracle_dict.connect():
            try:
                oracle_dict.build_dictionary(sample_size=args.sample_size)
                oracle_dict.save_dictionary(args.output)
            finally:
                oracle_dict.disconnect()

    elif args.lookup or args.table:
        oracle_dict.load_dictionary(args.input)

        if args.lookup:
            result = oracle_dict.lookup(args.lookup)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        if args.table:
            result = oracle_dict.get_table_info(args.table)
            if result:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"Table '{args.table}' not found")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
