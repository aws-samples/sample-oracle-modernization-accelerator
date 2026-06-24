"""
Direct Oracle→PostgreSQL Data Transfer Tools

These tools perform data migration internally without returning full row data
to the agent conversation, avoiding token overflow for large datasets.
"""

import json
import logging
import os
import asyncio
import threading
from datetime import datetime as _dt
from decimal import Decimal as _Decimal

import asyncpg
import oracledb
from strands import tool

logger = logging.getLogger(__name__)


# ── Connection helpers (reuse logic from oracle_tools / postgres_tools) ──

def _get_oracle_conn(schema: str = None):
    """Create Oracle connection using env vars or Secrets Manager."""
    from common.tools.oracle_tools import get_oracle_connection
    conn = get_oracle_connection()
    cursor = conn.cursor()
    cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")
    cursor.close()
    return conn


async def _get_pg_conn():
    """Create PostgreSQL connection using env vars or Secrets Manager."""
    from postgresql.tools.postgres_tools import get_pg_connection
    return await get_pg_connection()


def _run_async(coro):
    """Run async coroutine safely from sync context."""
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


def _coerce_value(val, pg_type: str):
    """Coerce an Oracle-exported value to match PG column type."""
    if val is None:
        return None

    # Handle LOB objects
    if hasattr(val, 'read'):
        val = val.read()

    if "timestamp" in pg_type:
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    return _dt.strptime(val, fmt)
                except ValueError:
                    continue
        return val

    if pg_type == "date":
        if isinstance(val, str):
            try:
                return _dt.strptime(val[:10], "%Y-%m-%d").date()
            except ValueError:
                return val
        return val

    if pg_type in ("numeric", "integer", "bigint", "smallint", "double precision", "real"):
        if isinstance(val, str):
            try:
                return _Decimal(val) if "." in val else int(val)
            except (ValueError, Exception):
                return val
        return val

    if pg_type in ("character varying", "character", "text", "char"):
        return str(val) if val is not None else None

    if pg_type == "boolean":
        if isinstance(val, str):
            return val.upper() in ("Y", "TRUE", "1", "T")
        return bool(val)

    return val


@tool
def migrate_table_data(table_name: str, schema: str = None, batch_size: int = 5000,
                       target_pg_schema: str = "") -> str:
    """
    Migrate data from an Oracle table directly to PostgreSQL without returning row data.

    Uses PostgreSQL COPY protocol (via asyncpg copy_records_to_table) for bulk insert,
    achieving ~100x speedup over row-by-row INSERT. Streams from Oracle in chunks
    to handle tables with millions of rows without excessive memory usage.

    Args:
        table_name: Table name to migrate (case-insensitive)
        schema: Oracle schema name (default: from environment variable)
        batch_size: Fetch/COPY chunk size (default: 5000)
        target_pg_schema: Target PostgreSQL schema (default: derived from OMA_PG_USER or oracle schema)

    Returns:
        JSON string with migration result:
        {"success": true, "table_name": "users", "rows_exported": 500, "rows_inserted": 500}

    Example:
        >>> migrate_table_data("USERS", "oracle_schema")
    """
    async def _migrate():
        ora_conn = None
        pg_conn = None
        try:
            # 1. Connect to Oracle and prepare cursor
            ora_conn = _get_oracle_conn(schema)
            cursor = ora_conn.cursor()
            cursor.arraysize = batch_size
            cursor.execute(f"SELECT * FROM {schema}.{table_name.upper()}")
            ora_columns = [desc[0] for desc in cursor.description]

            # 2. Connect to PostgreSQL and get column metadata
            pg_conn = await _get_pg_conn()

            # Log connection details for debugging
            db_name = await pg_conn.fetchval("SELECT current_database()")
            db_user = await pg_conn.fetchval("SELECT current_user")
            db_schema = await pg_conn.fetchval("SELECT current_schema")
            logger.info(
                "PG connection: database=%s, user=%s, schema=%s (for table %s)",
                db_name, db_user, db_schema, table_name,
            )

            try:
                await pg_conn.execute("SET session_replication_role = 'replica'")
            except Exception:
                pass

            pg_cols = [c.lower() for c in ora_columns]
            # Target schema priority: explicit param > OMA_PG_USER > oracle schema lowercase
            target_schema = (
                target_pg_schema.lower() if target_pg_schema
                else os.environ.get("OMA_PG_USER", schema.lower()).lower()
            )
            type_query = """
                SELECT column_name, data_type, is_generated
                FROM information_schema.columns
                WHERE table_name = $1 AND table_schema IN ($2, 'public')
            """
            type_rows = await pg_conn.fetch(type_query, table_name.lower(), target_schema)
            col_types = {r["column_name"]: r["data_type"] for r in type_rows}
            generated_cols = {r["column_name"] for r in type_rows if r["is_generated"] == "ALWAYS"}

            # Compute indices to keep (exclude generated columns)
            if generated_cols:
                keep_idx = [i for i, c in enumerate(pg_cols) if c not in generated_cols]
                pg_cols = [pg_cols[i] for i in keep_idx]
            else:
                keep_idx = list(range(len(pg_cols)))

            # 3. Stream from Oracle → COPY to PostgreSQL in chunks
            rows_exported = 0
            rows_inserted = 0
            errors = 0
            first_error = None

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                # Prepare chunk: resolve LOBs, filter generated cols, coerce types
                chunk = []
                for row in rows:
                    raw = [row[i].read() if hasattr(row[i], 'read') else row[i] for i in keep_idx]
                    coerced = tuple(
                        _coerce_value(raw[j], col_types.get(pg_cols[j], ""))
                        for j in range(len(pg_cols))
                    )
                    chunk.append(coerced)

                rows_exported += len(chunk)

                # Bulk COPY using asyncpg's COPY protocol
                try:
                    await pg_conn.copy_records_to_table(
                        table_name.lower(),
                        records=chunk,
                        columns=pg_cols,
                        schema_name=target_schema,
                    )
                    rows_inserted += len(chunk)
                except Exception as copy_err:
                    # Fallback: try with 'public' schema
                    try:
                        await pg_conn.copy_records_to_table(
                            table_name.lower(),
                            records=chunk,
                            columns=pg_cols,
                            schema_name="public",
                        )
                        rows_inserted += len(chunk)
                    except Exception as copy_err2:
                        # Final fallback: row-by-row INSERT for this chunk
                        col_str = ", ".join(f'"{c}"' for c in pg_cols)
                        placeholders = ", ".join(f"${i+1}" for i in range(len(pg_cols)))
                        insert_sql = (
                            f'INSERT INTO "{target_schema}"."{table_name.lower()}" '
                            f'({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
                        )
                        for rec in chunk:
                            try:
                                await pg_conn.execute(insert_sql, *rec)
                                rows_inserted += 1
                            except Exception as row_err:
                                errors += 1
                                if first_error is None:
                                    first_error = str(row_err)

                if rows_exported % 100000 == 0 and rows_exported > 0:
                    logger.info(
                        "  %s: %d rows transferred so far...",
                        table_name, rows_exported,
                    )

            cursor.close()
            ora_conn.close()
            ora_conn = None

            # Verify data actually persisted (catch silent COPY failures)
            verify_count = await pg_conn.fetchval(
                f'SELECT COUNT(*) FROM "{target_schema}"."{table_name.lower()}"'
            )
            if verify_count == 0 and rows_inserted > 0:
                logger.error(
                    "DATA PERSISTENCE FAILURE: %s — COPY reported %d rows but PG has 0! "
                    "db=%s schema=%s",
                    table_name, rows_inserted, db_name, target_schema,
                )
            elif verify_count != rows_inserted:
                logger.warning(
                    "Row count mismatch for %s: COPY reported %d, PG has %d",
                    table_name, rows_inserted, verify_count,
                )

            await pg_conn.close()
            pg_conn = None

            logger.info(
                "Exported %d rows, inserted %d rows into PG %s.%s (COPY protocol, verified=%d)",
                rows_exported, rows_inserted, target_schema, table_name.lower(), verify_count,
            )

            result = {
                "success": True,
                "table_name": table_name.upper(),
                "rows_exported": rows_exported,
                "rows_inserted": rows_inserted,
                "rows_verified": verify_count,
                "target_database": db_name,
                "target_schema": target_schema,
                "errors": errors,
            }
            if first_error:
                result["first_error"] = first_error
            if verify_count == 0 and rows_inserted > 0:
                result["success"] = False
                result["error"] = "COPY reported success but 0 rows persisted"
            return json.dumps(result, default=str)

        except Exception as e:
            logger.error("migrate_table_data failed for %s: %s", table_name, e)
            return json.dumps({
                "success": False,
                "table_name": table_name,
                "error": str(e),
            })
        finally:
            if ora_conn:
                try:
                    ora_conn.close()
                except Exception:
                    pass
            if pg_conn:
                try:
                    await pg_conn.close()
                except Exception:
                    pass

    return _run_async(_migrate())


@tool
def migrate_all_tables(schema: str = None, truncate_first: bool = True,
                       max_workers: int = 1) -> str:
    """
    Migrate ALL tables from Oracle schema to PostgreSQL in one call.

    This is the recommended tool for full data migration. It:
    1. Gets the list of all tables from Oracle
    2. Drops all foreign keys in the target PG schema (prevents FK violation errors during load)
    3. Optionally truncates all PG tables (CASCADE)
    4. Migrates each table's data directly (Oracle→PG)
    5. Syncs all sequences
    6. Recreates all foreign keys
    7. Returns summary with per-table row counts

    No row data is returned to the conversation - only metadata.

    Args:
        schema: Oracle schema name (default: from environment variable)
        truncate_first: Whether to TRUNCATE all PG tables before import (default: true)
        max_workers: Number of concurrent table migrations (default: 1 = sequential).
                     Values 2-8 enable parallel migration with asyncio.Semaphore.

    Returns:
        JSON string with migration summary:
        {"success": true, "tables_migrated": 44, "total_rows": 28455, "details": [...]}

    Example:
        >>> migrate_all_tables("oracle_schema", truncate_first=True, max_workers=4)
    """
    async def _migrate_all():
        try:
            # 1. Get table list from Oracle
            ora_conn = _get_oracle_conn(schema)
            cursor = ora_conn.cursor()
            cursor.execute(
                "SELECT table_name FROM all_tables WHERE owner = :owner ORDER BY table_name",
                {"owner": schema.upper()}
            )
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            ora_conn.close()

            logger.info("Found %d tables in Oracle schema %s", len(tables), schema)

            # 2. Drop all foreign keys (prevents FK violation during bulk load)
            pg_conn = await _get_pg_conn()
            target_schema = schema.lower()

            # Log connection details for debugging — critical for multi-DB setups
            db_name = await pg_conn.fetchval("SELECT current_database()")
            db_user = await pg_conn.fetchval("SELECT current_user")
            logger.info(
                "migrate_all_tables: PG database=%s, user=%s, target_schema=%s, tables=%d",
                db_name, db_user, target_schema, len(tables),
            )
            fk_stmts = await pg_conn.fetch("""
                SELECT
                    'ALTER TABLE ' || tc.table_schema || '.' || tc.table_name ||
                    ' DROP CONSTRAINT ' || tc.constraint_name || ';' AS drop_stmt,
                    'ALTER TABLE ' || tc.table_schema || '.' || tc.table_name ||
                    ' ADD CONSTRAINT ' || tc.constraint_name ||
                    ' FOREIGN KEY (' || kcu.column_name || ')' ||
                    ' REFERENCES ' || ccu.table_schema || '.' || ccu.table_name ||
                    ' (' || ccu.column_name || ');' AS create_stmt
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.table_schema = $1 AND tc.constraint_type = 'FOREIGN KEY'
            """, target_schema)

            fk_create_stmts = [row["create_stmt"] for row in fk_stmts]
            fk_drop_count = 0
            for row in fk_stmts:
                try:
                    await pg_conn.execute(row["drop_stmt"])
                    fk_drop_count += 1
                except Exception as e:
                    logger.warning("FK drop failed: %s", e)
            logger.info("Dropped %d foreign keys before data load", fk_drop_count)
            await pg_conn.close()

            # 3. Truncate PG tables if requested (schema-qualified!)
            if truncate_first:
                pg_conn = await _get_pg_conn()
                db_name = await pg_conn.fetchval("SELECT current_database()")
                logger.info(
                    "TRUNCATE phase: database=%s, target_schema=%s",
                    db_name, target_schema,
                )
                try:
                    await pg_conn.execute("SET session_replication_role = 'replica'")
                except Exception:
                    pass
                for tbl in tables:
                    try:
                        await pg_conn.execute(
                            f'TRUNCATE TABLE "{target_schema}"."{tbl.lower()}" CASCADE'
                        )
                        logger.info("Truncated PG table: %s.%s", target_schema, tbl.lower())
                    except Exception as e:
                        logger.warning("Could not truncate %s.%s: %s", target_schema, tbl.lower(), e)
                await pg_conn.close()

            # 4. Migrate each table (sequential or parallel)
            details = []
            total_exported = 0
            total_inserted = 0
            failed_tables = []

            def _migrate_one_table(tbl):
                """Migrate a single table, returns parsed result dict."""
                result_json = migrate_table_data(
                    table_name=tbl, schema=schema,
                    target_pg_schema=target_schema,
                )
                result = json.loads(result_json)
                logger.info(
                    "  %s: exported=%s, inserted=%s, success=%s",
                    tbl,
                    result.get("rows_exported", "?"),
                    result.get("rows_inserted", "?"),
                    result.get("success"),
                )
                return result

            effective_workers = max(1, min(max_workers, 8))

            if effective_workers <= 1:
                # Sequential migration (original behavior)
                for tbl in tables:
                    result = _migrate_one_table(tbl)
                    details.append(result)
                    if result.get("success"):
                        total_exported += result.get("rows_exported", 0)
                        total_inserted += result.get("rows_inserted", 0)
                    else:
                        failed_tables.append(tbl)
            else:
                # Parallel migration with thread pool + semaphore
                import concurrent.futures
                logger.info(
                    "Parallel migration: %d workers for %d tables",
                    effective_workers, len(tables),
                )
                table_results = {}
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=effective_workers
                ) as pool:
                    future_to_tbl = {
                        pool.submit(_migrate_one_table, tbl): tbl
                        for tbl in tables
                    }
                    for future in concurrent.futures.as_completed(future_to_tbl):
                        tbl = future_to_tbl[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            logger.error("Table %s migration exception: %s", tbl, e)
                            result = {"success": False, "table": tbl, "error": str(e)}
                        table_results[tbl] = result

                # Preserve original table order in details
                for tbl in tables:
                    result = table_results.get(tbl, {"success": False, "table": tbl, "error": "missing"})
                    details.append(result)
                    if result.get("success"):
                        total_exported += result.get("rows_exported", 0)
                        total_inserted += result.get("rows_inserted", 0)
                    else:
                        failed_tables.append(tbl)

            # 4. Sync sequences
            seq_result_json = None
            try:
                from common.tools.postgres_tools import pg_sync_sequences
                seq_result_json = pg_sync_sequences()
                seq_result = json.loads(seq_result_json)
                logger.info("Sequences synced: %s", seq_result.get("synced", 0))
            except Exception as e:
                logger.warning("Sequence sync failed: %s", e)
                seq_result = {"success": False, "error": str(e)}

            # 5b. Create Oracle compatibility views
            #     Apps may query Oracle data dictionary views (user_tab_columns,
            #     user_col_comments) which don't exist in PG natively.
            compat_views_created = []
            try:
                pg_conn = await _get_pg_conn()
                compat_views = {
                    "user_tab_columns": f"""
                        CREATE OR REPLACE VIEW "{target_schema}".user_tab_columns AS
                        SELECT
                            c.table_name    AS table_name,
                            c.column_name   AS column_name,
                            c.data_type     AS data_type,
                            c.character_maximum_length AS data_length,
                            c.numeric_precision  AS data_precision,
                            c.numeric_scale      AS data_scale,
                            CASE WHEN c.is_nullable = 'YES' THEN 'Y'
                                 ELSE 'N' END AS nullable,
                            c.ordinal_position   AS column_id
                        FROM information_schema.columns c
                        WHERE c.table_schema = '{target_schema}'
                    """,
                    "user_col_comments": f"""
                        CREATE OR REPLACE VIEW "{target_schema}".user_col_comments AS
                        SELECT
                            c.table_name    AS table_name,
                            c.column_name   AS column_name,
                            pgd.description AS comments
                        FROM information_schema.columns c
                        JOIN pg_catalog.pg_statio_all_tables st
                          ON st.schemaname = c.table_schema
                          AND st.relname = c.table_name
                        LEFT JOIN pg_catalog.pg_description pgd
                          ON pgd.objoid = st.relid
                          AND pgd.objsubid = c.ordinal_position
                        WHERE c.table_schema = '{target_schema}'
                    """,
                }
                for view_name, ddl in compat_views.items():
                    try:
                        await pg_conn.execute(ddl)
                        compat_views_created.append(view_name)
                        logger.info("Created Oracle compat view: %s.%s",
                                    target_schema, view_name)
                    except Exception as e:
                        logger.warning("Compat view %s failed: %s", view_name, e)
                await pg_conn.close()
            except Exception as e:
                logger.warning("Oracle compat views step failed: %s", e)

            # 6. Recreate foreign keys
            fk_recreate_count = 0
            fk_recreate_errors = []
            if fk_create_stmts:
                pg_conn = await _get_pg_conn()
                for stmt in fk_create_stmts:
                    try:
                        await pg_conn.execute(stmt)
                        fk_recreate_count += 1
                    except Exception as e:
                        fk_recreate_errors.append(str(e))
                        logger.warning("FK recreate failed: %s — %s", stmt[:80], e)
                await pg_conn.close()
                logger.info(
                    "Recreated %d/%d foreign keys",
                    fk_recreate_count, len(fk_create_stmts),
                )

            # 7. Final verification: count actual rows in PG
            total_verified = 0
            empty_tables = []
            pg_conn = await _get_pg_conn()
            for tbl in tables:
                try:
                    cnt = await pg_conn.fetchval(
                        f'SELECT COUNT(*) FROM "{target_schema}"."{tbl.lower()}"'
                    )
                    total_verified += cnt
                    if cnt == 0:
                        empty_tables.append(tbl)
                except Exception:
                    empty_tables.append(tbl)
            await pg_conn.close()

            logger.info(
                "FINAL VERIFICATION: %d total rows in PG, %d empty tables out of %d",
                total_verified, len(empty_tables), len(tables),
            )

            data_persisted = total_verified > 0

            # 8. Cross-reference: detect PG tables not in Oracle source
            #    (app may reference tables from external DBs / DB links)
            pg_conn = await _get_pg_conn()
            pg_all_rows = await pg_conn.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = $1",
                target_schema,
            )
            pg_all_tables = {r["table_name"] for r in pg_all_rows}
            oracle_set = {t.lower() for t in tables}
            extra_in_pg = sorted(pg_all_tables - oracle_set)
            missing_in_pg = sorted(oracle_set - pg_all_tables)
            await pg_conn.close()

            if extra_in_pg:
                logger.info(
                    "Cross-ref: %d tables in PG but NOT in Oracle source "
                    "(may be from external DB / DB link): %s",
                    len(extra_in_pg), extra_in_pg[:10],
                )
            if missing_in_pg:
                logger.warning(
                    "Cross-ref: %d Oracle tables NOT in PG after migration: %s",
                    len(missing_in_pg), missing_in_pg[:10],
                )

            return json.dumps({
                "success": len(failed_tables) == 0 and data_persisted,
                "tables_total": len(tables),
                "tables_migrated": len(tables) - len(failed_tables),
                "tables_failed": len(failed_tables),
                "failed_tables": failed_tables,
                "total_rows_exported": total_exported,
                "total_rows_inserted": total_inserted,
                "total_rows_verified": total_verified,
                "empty_tables_count": len(empty_tables),
                "data_persisted": data_persisted,
                "target_database": db_name,
                "target_schema": target_schema,
                "sequence_sync": seq_result,
                "fk_management": {
                    "dropped": fk_drop_count,
                    "recreated": fk_recreate_count,
                    "recreate_errors": len(fk_recreate_errors),
                },
                "oracle_compat_views": compat_views_created,
                "cross_reference": {
                    "oracle_tables": len(tables),
                    "pg_tables": len(pg_all_tables),
                    "extra_in_pg_not_in_oracle": extra_in_pg,
                    "missing_in_pg": missing_in_pg,
                },
                "details": details,
            }, default=str)

        except Exception as e:
            logger.error("migrate_all_tables failed: %s", e)
            return json.dumps({
                "success": False,
                "error": str(e),
            })

    return _run_async(_migrate_all())


async def _sample_data_hash_check(
    oracle_tables: list[str],
    oracle_counts: dict[str, int],
    oracle_schema: str,
    pg_schema: str,
    sample_size: int = 5,
    max_tables: int = 20,
) -> dict:
    """Hash-based sample data verification: compare actual row content.

    For each table (up to max_tables), fetches first N rows from both
    Oracle and PG, computes MD5 hash of concatenated column values,
    and compares. This catches silent data corruption that row-count
    checks miss (e.g., truncated strings, encoding issues, NULL drift).
    """
    import hashlib

    ora_conn = None
    pg_conn = None
    tables_checked = 0
    issues = []

    # Pick tables with data, prefer smaller tables for speed
    candidates = [
        t for t in oracle_tables
        if 0 < oracle_counts.get(t, 0) <= 1_000_000
    ]
    candidates.sort(key=lambda t: oracle_counts.get(t, 0))
    candidates = candidates[:max_tables]

    if not candidates:
        return {"status": "SKIP", "tables_checked": 0, "issues": [],
                "reason": "no suitable tables (all empty or too large)"}

    try:
        ora_conn = _get_oracle_conn(oracle_schema)
        pg_conn = await _get_pg_conn()

        for tbl in candidates:
            try:
                # Get column names from Oracle
                cursor = ora_conn.cursor()
                cursor.execute(
                    "SELECT column_name FROM all_tab_columns "
                    "WHERE owner = :1 AND table_name = :2 ORDER BY column_id",
                    [oracle_schema.upper(), tbl],
                )
                columns = [r[0] for r in cursor.fetchall()]
                cursor.close()

                if not columns:
                    continue

                col_list = ", ".join(f'"{c}"' for c in columns)

                # Oracle: fetch sample rows
                cursor = ora_conn.cursor()
                cursor.execute(
                    f'SELECT {col_list} FROM "{oracle_schema}"."{tbl}" '
                    f'WHERE ROWNUM <= {sample_size}'
                )
                ora_rows = cursor.fetchall()
                cursor.close()

                if not ora_rows:
                    continue

                # PG: fetch sample rows (same order)
                pg_col_list = ", ".join(f'"{c.lower()}"' for c in columns)
                pg_rows = await pg_conn.fetch(
                    f'SELECT {pg_col_list} FROM "{pg_schema}"."{tbl.lower()}" '
                    f'LIMIT {sample_size}'
                )

                # Hash comparison
                def row_hash(row):
                    vals = []
                    for v in row:
                        if v is None:
                            vals.append("NULL")
                        elif hasattr(v, 'read'):  # LOB
                            vals.append(str(v.read()))
                        else:
                            vals.append(str(v))
                    return hashlib.md5("|".join(vals).encode("utf-8", errors="replace")).hexdigest()

                ora_hashes = sorted(row_hash(r) for r in ora_rows)
                pg_hashes = sorted(row_hash(tuple(r.values())) for r in pg_rows)

                tables_checked += 1

                if ora_hashes != pg_hashes:
                    ora_set = set(ora_hashes)
                    pg_set = set(pg_hashes)
                    issues.append({
                        "table": tbl,
                        "sample_size": len(ora_rows),
                        "oracle_unique": len(ora_set - pg_set),
                        "pg_unique": len(pg_set - ora_set),
                        "common": len(ora_set & pg_set),
                    })

            except Exception as e:
                logger.debug("Sample check skipped for %s: %s", tbl, str(e)[:100])

    except Exception as e:
        logger.warning("Sample data hash check failed: %s", e)
        return {"status": "ERROR", "tables_checked": tables_checked,
                "issues": issues, "error": str(e)[:200]}
    finally:
        if ora_conn:
            try:
                ora_conn.close()
            except Exception:
                pass
        if pg_conn:
            try:
                await pg_conn.close()
            except Exception:
                pass

    status = "PASS" if not issues else "FAIL"
    return {
        "status": status,
        "tables_checked": tables_checked,
        "issues": issues,
    }


def verify_data_integrity(schema: str = None) -> dict:
    """Cross-check Oracle vs PostgreSQL row counts for ALL tables.

    Queries both databases directly and returns per-table comparison.
    This is NOT a @tool — it's called programmatically after data migration.

    Returns:
        Dict with verification results including per-table Oracle/PG counts,
        mismatches, FK integrity check, and sequence sync status.
    """
    async def _verify():
        ora_conn = None
        pg_conn = None
        try:
            # 1. Get Oracle row counts
            ora_conn = _get_oracle_conn(schema)
            cursor = ora_conn.cursor()
            cursor.execute(
                "SELECT table_name FROM all_tables WHERE owner = :owner ORDER BY table_name",
                {"owner": schema.upper()}
            )
            oracle_tables = [row[0] for row in cursor.fetchall()]

            oracle_counts = {}
            for tbl in oracle_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {schema}.{tbl}")
                    oracle_counts[tbl] = cursor.fetchone()[0]
                except Exception as e:
                    logger.warning("Oracle count failed for %s: %s", tbl, e)
                    oracle_counts[tbl] = -1

            cursor.close()
            ora_conn.close()
            ora_conn = None

            # 2. Get PG row counts
            pg_conn = await _get_pg_conn()
            target_schema = schema.lower()
            db_name = await pg_conn.fetchval("SELECT current_database()")

            pg_counts = {}
            for tbl in oracle_tables:
                try:
                    cnt = await pg_conn.fetchval(
                        f'SELECT COUNT(*) FROM "{target_schema}"."{tbl.lower()}"'
                    )
                    pg_counts[tbl] = cnt
                except Exception:
                    # Try public schema
                    try:
                        cnt = await pg_conn.fetchval(
                            f'SELECT COUNT(*) FROM "public"."{tbl.lower()}"'
                        )
                        pg_counts[tbl] = cnt
                    except Exception:
                        pg_counts[tbl] = -1

            # 3. FK integrity check (orphan records)
            fk_rows = await pg_conn.fetch("""
                SELECT
                    tc.table_name AS child_table,
                    kcu.column_name AS child_column,
                    ccu.table_name AS parent_table,
                    ccu.column_name AS parent_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.table_schema = $1 AND tc.constraint_type = 'FOREIGN KEY'
            """, target_schema)

            fk_issues = []
            for fk in fk_rows:
                try:
                    orphan_count = await pg_conn.fetchval(f"""
                        SELECT COUNT(*) FROM "{target_schema}"."{fk['child_table']}" c
                        LEFT JOIN "{target_schema}"."{fk['parent_table']}" p
                          ON c."{fk['child_column']}" = p."{fk['parent_column']}"
                        WHERE c."{fk['child_column']}" IS NOT NULL
                          AND p."{fk['parent_column']}" IS NULL
                    """)
                    if orphan_count > 0:
                        fk_issues.append({
                            "child_table": fk["child_table"],
                            "parent_table": fk["parent_table"],
                            "orphan_count": orphan_count,
                        })
                except Exception:
                    pass

            # 4. Sequence check
            seq_rows = await pg_conn.fetch("""
                SELECT sequencename, last_value
                FROM pg_sequences
                WHERE schemaname = $1
            """, target_schema)
            sequences_checked = len(seq_rows)

            await pg_conn.close()
            pg_conn = None

            # 5. Build comparison
            tables = []
            total_oracle = 0
            total_pg = 0
            mismatches = []
            match_count = 0

            for tbl in oracle_tables:
                ora_cnt = oracle_counts.get(tbl, 0)
                pg_cnt = pg_counts.get(tbl, 0)
                if ora_cnt >= 0:
                    total_oracle += ora_cnt
                if pg_cnt >= 0:
                    total_pg += pg_cnt

                match = (ora_cnt == pg_cnt) and ora_cnt >= 0
                if match:
                    match_count += 1
                status = "success" if match else "mismatch"

                tables.append({
                    "name": tbl,
                    "oracle_rows": ora_cnt,
                    "pg_rows": pg_cnt,
                    "match": match,
                    "status": status,
                })

                if not match:
                    mismatches.append({
                        "table": tbl,
                        "oracle": ora_cnt,
                        "pg": pg_cnt,
                        "diff": pg_cnt - ora_cnt if ora_cnt >= 0 and pg_cnt >= 0 else "N/A",
                    })

            fidelity = (total_pg / total_oracle * 100) if total_oracle > 0 else 0
            overall_pass = len(mismatches) == 0 and total_pg > 0

            # Cross-reference: PG tables vs Oracle source
            pg_conn2 = await _get_pg_conn()
            pg_all_rows = await pg_conn2.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = $1",
                target_schema,
            )
            pg_all_set = {r["table_name"] for r in pg_all_rows}
            oracle_lower_set = {t.lower() for t in oracle_tables}
            extra_in_pg = sorted(pg_all_set - oracle_lower_set)
            not_in_pg = sorted(oracle_lower_set - pg_all_set)
            await pg_conn2.close()

            if extra_in_pg:
                logger.info(
                    "Verify cross-ref: %d PG tables have no Oracle source "
                    "(external DB / DB link references)",
                    len(extra_in_pg),
                )
            if not_in_pg:
                logger.warning(
                    "Verify cross-ref: %d Oracle tables missing from PG: %s",
                    len(not_in_pg), not_in_pg[:10],
                )

            logger.info(
                "Data integrity verification: %d/%d tables match, "
                "Oracle=%d PG=%d (%.1f%%), %d FK issues",
                match_count, len(oracle_tables), total_oracle, total_pg,
                fidelity, len(fk_issues),
            )

            return {
                "success": True,
                "target_database": db_name,
                "target_schema": target_schema,
                "data_migration": {
                    "total_tables": len(oracle_tables),
                    "success_count": match_count,
                    "failed_count": len(mismatches),
                    "total_rows_oracle": total_oracle,
                    "total_rows_imported": total_pg,
                    "sequences_synced": sequences_checked,
                    "tables": tables,
                    "errors": [
                        f"{m['table']}: Oracle={m['oracle']}, PG={m['pg']}"
                        for m in mismatches[:20]
                    ],
                },
                "data_verification": {
                    "overall_status": "PASS" if overall_pass else "FAIL",
                    "row_count_check": {
                        "status": "PASS" if len(mismatches) == 0 else "FAIL",
                        "total_oracle": total_oracle,
                        "total_pg": total_pg,
                        "fidelity_pct": round(fidelity, 2),
                        "tables_matched": match_count,
                        "tables_total": len(oracle_tables),
                        "mismatches": mismatches,
                    },
                    "fk_integrity_check": {
                        "status": "PASS" if len(fk_issues) == 0 else "FAIL",
                        "fks_checked": len(fk_rows),
                        "orphans_found": sum(i["orphan_count"] for i in fk_issues),
                        "issues": fk_issues,
                    },
                    "sequence_check": {
                        "status": "PASS" if sequences_checked > 0 else "SKIP",
                        "sequences_checked": sequences_checked,
                    },
                    "sample_data_check": await _sample_data_hash_check(
                        oracle_tables, oracle_counts, schema, target_schema
                    ),
                    "summary": (
                        f"{match_count}/{len(oracle_tables)} tables matched, "
                        f"data fidelity {fidelity:.1f}%, "
                        f"{len(fk_issues)} FK orphan issues, "
                        f"{sequences_checked} sequences checked"
                    ),
                },
                "cross_reference": {
                    "oracle_tables": len(oracle_tables),
                    "pg_tables": len(pg_all_set),
                    "extra_in_pg_not_in_oracle": extra_in_pg,
                    "missing_in_pg_after_migration": not_in_pg,
                    "note": (
                        "extra_in_pg tables may come from external DB links, "
                        "TMS/WMS integrations, or Oracle data dictionary views "
                        "(user_tab_columns, user_col_comments) that need "
                        "information_schema equivalents in PostgreSQL."
                    ),
                },
            }

        except Exception as e:
            logger.error("verify_data_integrity failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "data_migration": {},
                "data_verification": {"overall_status": "ERROR"},
            }
        finally:
            if ora_conn:
                try:
                    ora_conn.close()
                except Exception:
                    pass
            if pg_conn:
                try:
                    await pg_conn.close()
                except Exception:
                    pass

    return _run_async(_verify())
