"""Constraint Manager - Drop and Recreate FK constraints"""

import logging
import os
import psycopg2

logger = logging.getLogger(__name__)


class ConstraintManager:
    """Manage PostgreSQL constraints for DMS Full Load."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str, schema: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self.saved_constraints = []
        self.backup_file = f"/tmp/constraints_{schema}.sql"

    def get_connection(self):
        """Get PostgreSQL connection."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )

    def drop_all_constraints(self) -> dict:
        """
        Drop all FK constraints and save DDL for recreation.

        Returns:
            dict: {
                "success": bool,
                "dropped_count": int,
                "saved_constraints": [str]
            }
        """
        logger.info("=" * 60)
        logger.info("Step 3: Dropping FK Constraints")
        logger.info("=" * 60)

        try:
            conn = self.get_connection()
            cur = conn.cursor()

            # Get all FK constraints using pg_catalog for accurate column mapping
            cur.execute(f"""
                SELECT
                    con.conname AS constraint_name,
                    n.nspname AS table_schema,
                    cl.relname AS table_name,
                    ARRAY_AGG(a.attname ORDER BY u.pos) AS columns,
                    nf.nspname AS foreign_table_schema,
                    clf.relname AS foreign_table_name,
                    ARRAY_AGG(af.attname ORDER BY u.pos) AS foreign_columns,
                    con.confupdtype,
                    con.confdeltype
                FROM pg_constraint con
                JOIN pg_class cl ON con.conrelid = cl.oid
                JOIN pg_namespace n ON cl.relnamespace = n.oid
                JOIN pg_class clf ON con.confrelid = clf.oid
                JOIN pg_namespace nf ON clf.relnamespace = nf.oid
                JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS u(attnum, pos) ON TRUE
                JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = u.attnum
                JOIN pg_attribute af ON af.attrelid = con.confrelid AND af.attnum = con.confkey[u.pos]
                WHERE con.contype = 'f'
                  AND n.nspname = %s
                GROUP BY con.conname, n.nspname, cl.relname, nf.nspname, clf.relname,
                         con.confupdtype, con.confdeltype
                ORDER BY cl.relname, con.conname
            """, (self.schema,))

            constraints = cur.fetchall()

            if not constraints:
                logger.info("No FK constraints found")
                cur.close()
                conn.close()
                return {
                    "success": True,
                    "dropped_count": 0,
                    "saved_constraints": []
                }

            logger.info("Found %d FK constraints", len(constraints))

            # Build constraint map (now columns are already aggregated)
            constraint_map = {}
            for row in constraints:
                (constraint_name, table_schema, table_name, columns,
                 foreign_table_schema, foreign_table_name, foreign_columns,
                 confupdtype, confdeltype) = row

                # Convert pg action codes to SQL syntax
                action_map = {
                    'a': 'NO_ACTION',
                    'r': 'RESTRICT',
                    'c': 'CASCADE',
                    'n': 'SET_NULL',
                    'd': 'SET_DEFAULT'
                }

                update_rule = action_map.get(confupdtype, 'NO_ACTION')
                delete_rule = action_map.get(confdeltype, 'NO_ACTION')

                key = (table_schema, table_name, constraint_name)
                constraint_map[key] = {
                    "table_schema": table_schema,
                    "table_name": table_name,
                    "constraint_name": constraint_name,
                    "columns": columns,  # Already a list
                    "foreign_table_schema": foreign_table_schema,
                    "foreign_table_name": foreign_table_name,
                    "foreign_columns": foreign_columns,  # Already a list
                    "update_rule": update_rule,
                    "delete_rule": delete_rule
                }

            # Generate DROP and CREATE statements
            self.saved_constraints = []

            for key, info in constraint_map.items():
                table_schema = info["table_schema"]
                table_name = info["table_name"]
                constraint_name = info["constraint_name"]
                columns = ", ".join(info["columns"])
                foreign_table_schema = info["foreign_table_schema"]
                foreign_table_name = info["foreign_table_name"]
                foreign_columns = ", ".join(info["foreign_columns"])
                on_update = info["update_rule"].replace(" ", "_")
                on_delete = info["delete_rule"].replace(" ", "_")

                # DROP statement
                drop_sql = f"ALTER TABLE {table_schema}.{table_name} DROP CONSTRAINT {constraint_name};"

                # CREATE statement
                create_sql = (
                    f"ALTER TABLE {table_schema}.{table_name} "
                    f"ADD CONSTRAINT {constraint_name} "
                    f"FOREIGN KEY ({columns}) "
                    f"REFERENCES {foreign_table_schema}.{foreign_table_name} ({foreign_columns})"
                )

                if on_update != "NO_ACTION":
                    create_sql += f" ON UPDATE {on_update}"
                if on_delete != "NO_ACTION":
                    create_sql += f" ON DELETE {on_delete}"

                create_sql += ";"

                self.saved_constraints.append(create_sql)

                # Execute DROP
                logger.info("Dropping: %s.%s.%s", table_schema, table_name, constraint_name)
                cur.execute(drop_sql)

            conn.commit()
            cur.close()
            conn.close()

            logger.info("✓ Dropped %d FK constraints", len(constraint_map))

            # Save to file for recovery
            try:
                with open(self.backup_file, 'w') as f:
                    f.write("-- FK Constraints Backup\n")
                    f.write(f"-- Schema: {self.schema}\n")
                    f.write(f"-- Dropped: {len(constraint_map)} constraints\n\n")
                    for sql in self.saved_constraints:
                        f.write(sql + "\n")
                logger.info("✓ Saved constraints to: %s", self.backup_file)
            except Exception as e:
                logger.warning("Failed to save constraints to file: %s", e)

            return {
                "success": True,
                "dropped_count": len(constraint_map),
                "saved_constraints": self.saved_constraints
            }

        except Exception as e:
            logger.exception("Failed to drop constraints")
            return {
                "success": False,
                "error": str(e)
            }

    def recreate_all_constraints(self) -> dict:
        """
        Recreate all saved FK constraints.

        Returns:
            dict: {
                "success": bool,
                "created_count": int,
                "failed": [str]
            }
        """
        logger.info("=" * 60)
        logger.info("Step 5: Recreating FK Constraints")
        logger.info("=" * 60)

        if not self.saved_constraints:
            # Try to load from backup file
            if os.path.exists(self.backup_file):
                logger.info("Loading constraints from backup file: %s", self.backup_file)
                try:
                    with open(self.backup_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('--'):
                                self.saved_constraints.append(line)
                    logger.info("Loaded %d constraints from backup", len(self.saved_constraints))
                except Exception as e:
                    logger.error("Failed to load backup file: %s", e)
                    return {
                        "success": False,
                        "error": f"No saved constraints and backup load failed: {e}"
                    }
            else:
                logger.warning("No saved constraints to recreate")
                return {
                    "success": True,
                    "created_count": 0,
                    "failed": []
                }

        try:
            conn = self.get_connection()
            cur = conn.cursor()

            created = 0
            failed = []

            for create_sql in self.saved_constraints:
                try:
                    logger.info("Creating constraint...")
                    cur.execute(create_sql)
                    conn.commit()
                    created += 1
                except Exception as e:
                    logger.warning("Failed to create constraint: %s", e)
                    failed.append(f"{create_sql} -- ERROR: {e}")
                    conn.rollback()

            cur.close()
            conn.close()

            logger.info("✓ Created %d constraints (%d failed)", created, len(failed))

            return {
                "success": True,
                "created_count": created,
                "failed": failed
            }

        except Exception as e:
            logger.exception("Failed to recreate constraints")
            return {
                "success": False,
                "error": str(e)
            }
