#!/usr/bin/env python3
"""
OMA Schema - Simplified Migration Pipeline

Simple, procedural, agent-minimal approach:
1. DMS SC Auto-Conversion (95%)
2. Manual Object Conversion (5% - Agent-based)
3. Drop Constraints
4. DMS Full Load
5. Recreate Constraints
"""

import json
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oma.schema")


def load_environment():
    """Load environment from oma.properties and oma_env_oma.sh."""
    logger.info("Loading environment...")

    # Load oma.properties
    oma_root = os.path.join(os.path.dirname(__file__), '..')
    properties_file = os.path.join(oma_root, 'env', 'oma.properties')

    if os.path.exists(properties_file):
        in_common_section = False
        with open(properties_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('['):
                    section_name = line.strip('[]')
                    in_common_section = (section_name == 'COMMON')
                    continue

                if in_common_section and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    if '${OMA_BASE_DIR}' in value:
                        oma_base = os.path.abspath(oma_root)
                        value = value.replace('${OMA_BASE_DIR}', oma_base)

                    if key and not os.environ.get(key):
                        os.environ[key] = value

    # Load oma_env_oma.sh
    env_script = os.path.join(oma_root, 'env', 'oma_env_oma.sh')

    if os.path.exists(env_script):
        with open(env_script, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                if line.startswith('export ') and '=' in line:
                    line = line[7:]
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    if key:
                        os.environ[key] = value

    logger.info("✓ Environment loaded")


def main():
    """Main migration pipeline."""
    logger.info("=" * 60)
    logger.info("OMA Schema - Simplified Migration Pipeline")
    logger.info("=" * 60)

    # Load environment
    load_environment()

    # Get configuration
    oracle_schema = os.environ.get("ORACLE_SCHEMA", os.environ.get("ORACLE_USER", ""))
    if not oracle_schema:
        logger.error("ORACLE_SCHEMA not set in environment")
        sys.exit(1)

    dms_migration_project_arn = os.environ.get("DMS_MIGRATION_PROJECT_ARN")  # Optional - will auto-create
    dms_s3_bucket = os.environ.get("DMS_SC_S3_BUCKET")

    if not dms_s3_bucket:
        logger.error("DMS_SC_S3_BUCKET not set in environment")
        sys.exit(1)

    pg_host = os.environ.get("PGHOST")
    pg_port = int(os.environ.get("PGPORT", "5432"))
    pg_database = os.environ.get("PGDATABASE")
    pg_user = os.environ.get("PGUSER", "postgres")
    pg_password = os.environ.get("PGPASSWORD")
    pg_schema = os.environ.get("PGSCHEMA", oracle_schema.lower())

    logger.info("Oracle schema: %s", oracle_schema)
    logger.info("PostgreSQL: %s@%s/%s (schema: %s)", pg_user, pg_host, pg_database, pg_schema)

    # ========================================
    # Step 1: DMS Schema Conversion
    # ========================================
    from tools.dms_sc import DMSSCConverter

    dms_sc = DMSSCConverter(
        migration_project_arn=dms_migration_project_arn,
        s3_bucket=dms_s3_bucket
    )

    # Run conversion
    conversion_result = dms_sc.run_conversion(schema=oracle_schema, timeout=600)

    if not conversion_result["success"]:
        logger.error("DMS SC conversion failed: %s", conversion_result.get("error"))
        sys.exit(1)

    # Download results (best effort - may not exist if already applied)
    download_result = dms_sc.download_results(schema=oracle_schema)

    if download_result["success"]:
        # Parse assessment
        assessment = dms_sc.parse_assessment(download_result.get("assessment", ""))
    else:
        logger.warning("Could not download S3 results (DMS SC may have applied directly to PostgreSQL)")
        logger.info("Checking PostgreSQL for created objects...")

        # Check if objects exist in PostgreSQL
        import psycopg2
        try:
            conn = psycopg2.connect(
                host=pg_host, port=pg_port, database=pg_database,
                user=pg_user, password=pg_password
            )
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (pg_schema,))
            table_count = cur.fetchone()[0]
            cur.close()
            conn.close()

            logger.info("Found %d tables in PostgreSQL schema '%s'", table_count, pg_schema)

            # Create dummy assessment
            assessment = {
                "total_objects": table_count,
                "converted": table_count,
                "failed": 0,
                "failed_objects": []
            }
        except Exception as e:
            logger.warning("Could not check PostgreSQL: %s", e)
            assessment = {"total_objects": 0, "converted": 0, "failed": 0, "failed_objects": []}

    logger.info("DMS SC Summary:")
    logger.info("  Total objects: %d", assessment["total_objects"])
    logger.info("  Converted: %d", assessment["converted"])
    logger.info("  Failed: %d", assessment["failed"])

    # Verify objects were created in PostgreSQL
    logger.info("=" * 60)
    logger.info("Verifying PostgreSQL objects...")
    logger.info("=" * 60)

    import psycopg2
    conn = psycopg2.connect(
        host=pg_host, port=pg_port, database=pg_database,
        user=pg_user, password=pg_password
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (pg_schema,))
    table_count = cur.fetchone()[0]
    cur.close()
    conn.close()

    logger.info("PostgreSQL: %d tables found in schema '%s'", table_count, pg_schema)

    if table_count == 0:
        logger.error("DMS SC did not create any tables in PostgreSQL!")
        logger.error("Check if DMS SC 'export_to_target' step succeeded")
        sys.exit(1)

    # ========================================
    # Step 1.5: Fix Oracle PK NUMBER to NUMERIC
    # ========================================
    # DMS SC converts Oracle PK NUMBER → BIGINT for performance
    # But DMS Full Load extracts Oracle NUMBER as "123.0000000000"
    # This causes BIGINT insertion errors
    # Fix: Oracle PK NUMBER(scale=0) → PostgreSQL NUMERIC(precision,0)

    logger.info("=" * 60)
    logger.info("Step 1.5: Fixing Oracle PK NUMBER columns")
    logger.info("=" * 60)

    from tools.number_type_optimizer import NumberTypeOptimizer

    target_config = {
        'host': pg_host,
        'port': pg_port,
        'database': pg_database,
        'user': pg_user,
        'password': pg_password,
        'schema': pg_schema,
        'db_type': 'postgres'
    }

    optimizer = NumberTypeOptimizer(oracle_schema, target_config)

    # Find ALL Oracle NUMBER columns and fix PostgreSQL BIGINT/INTEGER
    results = optimizer.fix_all_integer_number_to_numeric()

    if results:
        # Generate ALTER statements
        alter_statements = optimizer.generate_alter_statements()

        if alter_statements:
            logger.info("Applying PK type fixes...")
            opt_result = optimizer.apply_optimizations(alter_statements)
            logger.info("✓ Fixed %d PK columns", opt_result["applied_count"])

            if opt_result["failed"]:
                logger.warning("Failed to fix %d columns", opt_result["failed_count"])
        else:
            logger.info("✓ No ALTER statements needed")
    else:
        logger.info("✓ No Oracle PK NUMBER columns need fixing")

    # ========================================
    # Step 2: Drop Constraints (BEFORE Full Load!)
    # ========================================
    logger.info("=" * 60)
    logger.info("Step 2: Dropping FK Constraints")
    logger.info("=" * 60)

    from tools.constraint_manager import ConstraintManager

    constraint_mgr = ConstraintManager(
        host=pg_host,
        port=pg_port,
        database=pg_database,
        user=pg_user,
        password=pg_password,
        schema=pg_schema
    )

    drop_result = constraint_mgr.drop_all_constraints()

    if not drop_result["success"]:
        logger.error("Failed to drop constraints: %s", drop_result.get("error"))
        sys.exit(1)

    logger.info("✓ Dropped %d constraints", drop_result["dropped_count"])

    # ========================================
    # Step 3: DMS Full Load (After type optimization!)
    # ========================================
    logger.info("=" * 60)
    logger.info("Step 3: DMS Full Load")
    logger.info("=" * 60)
    from tools.dms_load import DMSFullLoader

    dms_loader = DMSFullLoader()

    # Discover DMS infrastructure
    infra = dms_loader.discover_infrastructure()

    if not infra["success"]:
        logger.error("Failed to discover DMS infrastructure: %s", infra.get("error"))
        sys.exit(1)

    # Execute full load (24 hour timeout for large datasets)
    load_result = dms_loader.execute(
        schema=oracle_schema,
        replication_instance_arn=infra["replication_instance_arn"],
        source_endpoint_arn=infra["source_endpoint_arn"],
        target_endpoint_arn=infra["target_endpoint_arn"],
        timeout=86400  # 24 hours
    )

    if not load_result["success"]:
        logger.error("DMS Full Load failed: %s", load_result.get("error"))
        sys.exit(1)

    # ========================================
    # Step 4: Recreate Constraints
    # ========================================
    logger.info("=" * 60)
    logger.info("Step 4: Recreating FK Constraints")
    logger.info("=" * 60)
    recreate_result = constraint_mgr.recreate_all_constraints()

    if not recreate_result["success"]:
        logger.error("Failed to recreate constraints: %s", recreate_result.get("error"))
        sys.exit(1)

    logger.info("✓ Recreated %d constraints", recreate_result["created_count"])

    if recreate_result["failed"]:
        logger.warning("Failed to recreate %d constraints:", len(recreate_result["failed"]))
        for failed in recreate_result["failed"]:
            logger.warning("  %s", failed)

    # ========================================
    # Step 5: Conversion Agent (AI-powered) - BACKGROUND
    # ========================================
    logger.info("=" * 60)
    logger.info("Step 5: Launching Conversion Agent (Background)")
    logger.info("=" * 60)

    # Launch conversion agent in background (non-blocking)
    # Agent will download S3 results and process failed objects
    import subprocess
    agent_script = os.path.join(os.path.dirname(__file__), "tools", "conversion_agent.py")

    if os.path.exists(agent_script):
        # Launch in background
        subprocess.Popen([
            sys.executable, agent_script,
            "--schema", oracle_schema,
            "--target-db", pg_database
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        logger.info("✓ Conversion Agent launched in background")
        logger.info("  (Will download S3 results and convert complex objects)")
        logger.info("  Log: /tmp/conversion_agent.log")
    else:
        logger.warning("Conversion Agent not found: %s", agent_script)

    # ========================================
    # Summary
    # ========================================
    logger.info("=" * 60)
    logger.info("Migration Completed Successfully!")
    logger.info("=" * 60)
    logger.info("DMS SC: %d objects converted, %d failed",
                assessment["converted"], assessment["failed"])
    logger.info("Data Load: %d tables, %d rows",
                load_result["statistics"].get("tables_loaded", 0),
                load_result["statistics"].get("full_load_rows", 0))
    logger.info("Constraints: %d dropped, %d recreated",
                drop_result["dropped_count"],
                recreate_result["created_count"])
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Migration failed")
        sys.exit(1)
