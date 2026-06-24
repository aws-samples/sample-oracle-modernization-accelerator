#!/usr/bin/env python3
"""End-to-end OMA migration pipeline runner.

Connects to Oracle (Oracle schema) and migrates to PostgreSQL using
Strands Agents SDK Graph pipeline with Opus 4.6 on Bedrock.

Usage:
    python3 scripts/run_migration.py                    # Fresh run
    python3 scripts/run_migration.py --resume <migration_id>  # Resume from checkpoint
"""

import argparse
import json
import logging
import os
import sys
import time

# Ensure schema-migration root and modules are on sys.path
schema_migration_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, schema_migration_root)  # schema-migration/
sys.path.insert(0, os.path.join(schema_migration_root, 'common'))
sys.path.insert(0, os.path.join(schema_migration_root, 'postgresql'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oma.runner")


def load_oma_properties():
    """Load environment variables from oma.properties [COMMON] section.

    Priority: oma.properties > existing env vars (doesn't overwrite).
    """
    # Find oma.properties: schema -> oma/env/oma.properties
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_root = os.path.join(script_dir, '..', '..')
    oma_root = os.path.join(schema_root, '..')
    properties_file = os.path.join(oma_root, 'env', 'oma.properties')

    if not os.path.exists(properties_file):
        logger.warning("oma.properties not found at: %s", properties_file)
        return

    logger.info("Loading environment from: %s", properties_file)

    in_common_section = False

    with open(properties_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Check for section headers
            if line.startswith('['):
                section_name = line.strip('[]')
                in_common_section = (section_name == 'COMMON')
                continue

            # Parse key=value in [COMMON] section
            if in_common_section and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Variable expansion for ${OMA_BASE_DIR}
                if '${OMA_BASE_DIR}' in value:
                    oma_base = os.path.join(schema_root, '..')
                    oma_base = os.path.abspath(oma_base)
                    value = value.replace('${OMA_BASE_DIR}', oma_base)

                # Set environment variable (don't overwrite existing)
                if key and not os.environ.get(key):
                    os.environ[key] = value
                    logger.debug("Set %s from oma.properties", key)

    logger.info("Environment variables loaded from oma.properties")


def setup_env_from_secrets():
    """Set ORACLE_* and PG* env vars from Secrets Manager."""
    import boto3
    region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")
    client = boto3.client("secretsmanager", region_name=region)

    # Oracle service credentials
    try:
        resp = client.get_secret_value(SecretId="oma-secret-oracle-service")
        oracle = json.loads(resp["SecretString"])
        os.environ.setdefault("ORACLE_HOST", oracle.get("host", ""))
        os.environ.setdefault("ORACLE_PORT", str(oracle.get("port", "1521")))
        os.environ.setdefault("ORACLE_USER", oracle.get("username", ""))
        os.environ.setdefault("ORACLE_PASSWORD", oracle.get("password", ""))
        os.environ.setdefault("ORACLE_SERVICE_NAME", oracle.get("sid", ""))
        os.environ.setdefault("ORACLE_SID", oracle.get("sid", ""))
        logger.info("Oracle credentials loaded from Secrets Manager")
    except Exception as e:
        logger.warning("Could not load Oracle secrets: %s", e)

    # PostgreSQL service credentials
    try:
        resp = client.get_secret_value(SecretId="oma-secret-postgres-service")
        pg = json.loads(resp["SecretString"])
        os.environ.setdefault("PGHOST", pg.get("host", ""))
        os.environ.setdefault("PGPORT", str(pg.get("port", "5432")))
        os.environ.setdefault("PGDATABASE", pg.get("database", pg.get("dbname", "")))
        os.environ.setdefault("PGUSER", pg.get("username", ""))
        os.environ.setdefault("PGPASSWORD", pg.get("password", ""))
        logger.info("PostgreSQL credentials loaded from Secrets Manager")
    except Exception as e:
        logger.warning("Could not load PostgreSQL secrets: %s", e)


def collect_tools() -> dict:
    """Collect all tool functions keyed by name."""
    from common.tools.oracle_tools import (
        oracle_query, oracle_get_ddl, oracle_get_dependencies,
        oracle_get_object_list, oracle_get_source, oracle_get_table_columns,
        oracle_get_constraints, oracle_get_indexes, oracle_get_sequences,
        oracle_get_partitions,
    )
    from postgresql.tools.postgres_tools import (
        pg_execute_ddl, pg_query, pg_explain, pg_syntax_check,
        pg_get_column_type, pg_get_table_list,
        pg_sync_sequences,
    )
    from common.tools.mybatis_tools import (
        mybatis_extract_sqls, mybatis_merge_sqls, mybatis_scan_directory,
        mybatis_validate_xml,
    )
    from common.tools.dms_tools import dms_parse_assessment_csv, dms_get_failed_objects
    from common.tools.dms_sc_tools import (
        dms_sc_run_conversion, dms_sc_collect_results,
        dms_sc_apply_ddl, dms_sc_list_s3, dms_sc_verify_target,
    )
    from common.tools.analysis_tools import (
        apply_static_rules, compute_coverage_score, compute_equivalence_score,
        deploy_compat_library, execute_sql_comparison, functional_test_sql,
        generate_bind_variables, generate_html_report,
    )
    from common.tools.reference_tools import oracle_to_pg_reference
    from postgresql.tools.data_transfer_tools import migrate_table_data, migrate_all_tables
    from common.tools.rag_tools import search_conversion_knowledge, store_learned_pattern

    return {
        # Oracle
        "oracle_query": oracle_query,
        "oracle_get_ddl": oracle_get_ddl,
        "oracle_get_dependencies": oracle_get_dependencies,
        "oracle_get_object_list": oracle_get_object_list,
        "oracle_get_source": oracle_get_source,
        "oracle_get_table_columns": oracle_get_table_columns,
        "oracle_get_constraints": oracle_get_constraints,
        "oracle_get_indexes": oracle_get_indexes,
        "oracle_get_sequences": oracle_get_sequences,
        "oracle_get_partitions": oracle_get_partitions,
        # PostgreSQL
        "pg_execute_ddl": pg_execute_ddl,
        "pg_query": pg_query,
        "pg_explain": pg_explain,
        "pg_syntax_check": pg_syntax_check,
        "pg_get_column_type": pg_get_column_type,
        "pg_get_table_list": pg_get_table_list,
        "pg_sync_sequences": pg_sync_sequences,
        # MyBatis
        "mybatis_extract_sqls": mybatis_extract_sqls,
        "mybatis_merge_sqls": mybatis_merge_sqls,
        "mybatis_scan_directory": mybatis_scan_directory,
        "mybatis_validate_xml": mybatis_validate_xml,
        # DMS
        "dms_parse_assessment_csv": dms_parse_assessment_csv,
        "dms_get_failed_objects": dms_get_failed_objects,
        # DMS Schema Conversion (DMS SC First architecture)
        "dms_sc_run_conversion": dms_sc_run_conversion,
        "dms_sc_collect_results": dms_sc_collect_results,
        "dms_sc_apply_ddl": dms_sc_apply_ddl,
        "dms_sc_list_s3": dms_sc_list_s3,
        "dms_sc_verify_target": dms_sc_verify_target,
        # Analysis
        "apply_static_rules": apply_static_rules,
        "compute_coverage_score": compute_coverage_score,
        "compute_equivalence_score": compute_equivalence_score,
        "deploy_compat_library": deploy_compat_library,
        "execute_sql_comparison": execute_sql_comparison,
        "functional_test_sql": functional_test_sql,
        "generate_bind_variables": generate_bind_variables,
        "generate_html_report": generate_html_report,
        # Reference
        "oracle_to_pg_reference": oracle_to_pg_reference,
        # Data Transfer (direct Oracle→PG, no token overflow)
        "migrate_table_data": migrate_table_data,
        "migrate_all_tables": migrate_all_tables,
        # RAG (Agentic RAG for dynamic knowledge retrieval)
        "search_conversion_knowledge": search_conversion_knowledge,
        "store_learned_pattern": store_learned_pattern,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="OMA Migration Pipeline Runner")
    parser.add_argument(
        "--resume",
        metavar="MIGRATION_ID",
        help="Resume a previously failed migration from its last checkpoint",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    if args.resume:
        logger.info("OMA Migration Pipeline - RESUMING: %s", args.resume)
    else:
        logger.info("OMA Migration Pipeline - End-to-End Run")
    logger.info("=" * 60)

    # Step 0: Load environment from oma.properties (priority)
    load_oma_properties()

    # Step 0.5: Load credentials from Secrets Manager (fallback)
    setup_env_from_secrets()

    # Step 1: Verify connectivity
    logger.info("Step 1: Verifying database connectivity...")
    tools = collect_tools()

    # Test Oracle
    oracle_schema = os.environ.get("ORACLE_USER", "oracle_schema").upper()
    oracle_result = json.loads(tools["oracle_query"](
        sql="SELECT COUNT(*) AS cnt FROM user_tables",
        schema=oracle_schema,
    ))
    if not oracle_result.get("success"):
        logger.error("Oracle connection failed: %s", oracle_result.get("error"))
        sys.exit(1)
    table_count = oracle_result["rows"][0]["CNT"]
    logger.info("Oracle OK: %d tables in %s schema", table_count, oracle_schema)

    # Test PostgreSQL
    pg_result = json.loads(tools["pg_get_table_list"]())
    if not pg_result.get("success"):
        logger.error("PostgreSQL connection failed: %s", pg_result.get("error"))
        sys.exit(1)
    logger.info("PostgreSQL OK: %d existing tables", pg_result["count"])

    # Step 2: Create agents
    logger.info("Step 2: Creating agents with Opus 4.6...")
    from postgresql.agents.factory import create_agents, OMAConfig, BedrockConfig

    config = OMAConfig(
        bedrock=BedrockConfig(
            region="ap-northeast-2",
            opus_model_id="global.anthropic.claude-opus-4-6-v1",
            sonnet_model_id="global.anthropic.claude-opus-4-6-v1",
            haiku_model_id="global.anthropic.claude-opus-4-6-v1",
        ),
        oracle_schema=oracle_schema,
    )

    agents = create_agents(config, tools)
    logger.info("Created %d agents: %s", len(agents), list(agents.keys()))

    # Step 3: Build pipelines
    logger.info("Step 3: Building migration pipelines...")
    from common.orchestrator.pipeline import (
        build_migration_pipeline, build_data_pipeline, run_migration,
    )

    schema_graph = build_migration_pipeline(
        agents,
        oracle_schema=oracle_schema,
        max_node_executions=20,
        execution_timeout=10800,  # 3 hours
        node_timeout=3600,  # 60 minutes per node
    )
    logger.info("Schema pipeline built successfully")

    migration_config = {
        "migration_id": f"oma-{int(time.time())}",
        "oracle_config": {
            "host": os.environ.get("ORACLE_HOST", "10.0.X.X"),
            "port": 1521,
            "service": "YOUR_SERVICE_NAME",
            "schema": oracle_schema,
        },
        "pg_config": {
            "host": os.environ.get("PGHOST", "your-aurora-cluster.cluster-xxxxx.ap-northeast-2.rds.amazonaws.com"),
            "port": 5432,
            "database": os.environ.get("PGDATABASE", "target_db"),
            "target_schema": oracle_schema.lower(),
        },
        "dms_sc_config": {
            "migration_project_arn": os.environ.get(
                "DMS_MIGRATION_PROJECT_ARN",
                "arn:aws:dms:ap-northeast-2:YOUR_AWS_ACCOUNT_ID:migration-project:YOUR_DMS_PROJECT_ID",
            ),
            "s3_bucket": os.environ.get("DMS_SC_S3_BUCKET", "oma-dms-sc-YOUR_AWS_ACCOUNT_ID"),
        },
        "scope": {
            "object_types": "ALL",
            "include": "*",
            "exclude": "NONE",
        },
    }

    # ── Phase 1: Schema Migration ──
    logger.info("=" * 60)
    logger.info("PHASE 1: Schema Migration Pipeline")
    logger.info("=" * 60)
    start = time.time()

    # Check if resuming from a checkpoint
    resume_id = args.resume if args.resume else None
    if resume_id:
        # Use the original migration_id for resumption
        migration_config["migration_id"] = resume_id

    schema_result = run_migration(
        schema_graph, migration_config,
        resume_from=resume_id,
    )
    schema_elapsed = time.time() - start

    logger.info("Schema status: %s (%.1fs)", schema_result.get("status"), schema_elapsed)
    logger.info("Nodes executed: %s", schema_result.get("execution_order", []))

    if schema_result.get("nodes"):
        for node_id, node_data in schema_result["nodes"].items():
            logger.info("  Node '%s': status=%s", node_id, node_data.get("status"))

    # ── Phase 2: Data Migration (DMS Full Load Task) ──
    logger.info("=" * 60)
    logger.info("PHASE 2: Data Migration via DMS Full Load Task")
    logger.info("=" * 60)

    data_start = time.time()
    try:
        from common.tools.dms_full_load_tools import (
            create_dms_full_load_task,
            start_dms_task,
            wait_for_dms_task_completion,
        )

        # Get DMS infrastructure from environment
        dms_instance = os.environ.get("DMS_REPLICATION_INSTANCE_ARN")
        source_endpoint = os.environ.get("DMS_SOURCE_ENDPOINT_ARN")
        target_endpoint = os.environ.get("DMS_TARGET_ENDPOINT_ARN")

        # If not in env, discover from AWS
        if not all([dms_instance, source_endpoint, target_endpoint]):
            logger.info("Discovering DMS infrastructure...")
            import boto3
            dms = boto3.client("dms", region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2"))

            # Get replication instance
            instances = dms.describe_replication_instances()['ReplicationInstances']
            if instances:
                dms_instance = instances[0]['ReplicationInstanceArn']
                logger.info("Found DMS instance: %s", instances[0]['ReplicationInstanceIdentifier'])

            # Get endpoints
            endpoints = dms.describe_endpoints()['Endpoints']
            for ep in endpoints:
                if ep['EndpointType'] == 'SOURCE' and ep['EngineName'] == 'oracle':
                    source_endpoint = ep['EndpointArn']
                    logger.info("Found source endpoint: %s", ep['EndpointIdentifier'])
                elif ep['EndpointType'] == 'TARGET' and 'postgres' in ep['EngineName']:
                    target_endpoint = ep['EndpointArn']
                    logger.info("Found target endpoint: %s", ep['EndpointIdentifier'])

        if not all([dms_instance, source_endpoint, target_endpoint]):
            raise ValueError("DMS infrastructure not found. Please check DMS setup.")

        # Create DMS Full Load Task
        logger.info("Creating DMS Full Load task for schema: %s", oracle_schema)
        create_result = json.loads(create_dms_full_load_task(
            replication_instance_arn=dms_instance,
            source_endpoint_arn=source_endpoint,
            target_endpoint_arn=target_endpoint,
            schema_name=oracle_schema,
        ))

        if not create_result.get("success"):
            raise Exception(f"Failed to create DMS task: {create_result.get('error')}")

        task_arn = create_result['task_arn']
        logger.info("DMS task created: %s", create_result['task_identifier'])

        # Wait for task to be ready
        logger.info("Waiting for task to be ready...")
        time.sleep(10)

        # Start DMS Task
        logger.info("Starting DMS Full Load task...")
        start_result = json.loads(start_dms_task(task_arn))

        if not start_result.get("success"):
            raise Exception(f"Failed to start DMS task: {start_result.get('error')}")

        logger.info("DMS task started. Waiting for completion...")

        # Wait for completion (with progress updates)
        wait_result = json.loads(wait_for_dms_task_completion(
            task_arn=task_arn,
            check_interval=30,
            max_wait_seconds=28800  # 8 hours
        ))

        data_elapsed = time.time() - data_start

        if not wait_result.get("success"):
            raise Exception(f"DMS task failed: {wait_result.get('error')}")

        logger.info("Data migration completed in %.1fs", data_elapsed)
        logger.info("Statistics: %s", json.dumps(wait_result.get('statistics', {}), indent=2))

        # Prepare result in expected format
        data_result = {
            "status": "COMPLETED",
            "dms_task_arn": task_arn,
            "statistics": wait_result.get('statistics', {}),
            "elapsed_seconds": wait_result.get('elapsed_seconds', int(data_elapsed))
        }
        data_serialized = data_result

        from common.orchestrator.state import serialize_migration_state, save_checkpoint
        data_serialized = serialize_migration_state(data_result)

        # Save Phase 2 completion checkpoint
        save_checkpoint(
            migration_config["migration_id"], "data_verify",
            {"migration_id": migration_config["migration_id"]},
            phase="data", status="completed",
        )
    except Exception as e:
        data_elapsed = time.time() - data_start
        logger.error("Data pipeline failed: %s", e)
        data_serialized = {"status": "FAILED", "error": str(e)}

        # Save Phase 2 failure checkpoint
        from common.orchestrator.state import save_checkpoint
        save_checkpoint(
            migration_config["migration_id"], "data_migrate",
            {"migration_id": migration_config["migration_id"]},
            phase="data", status="failed",
        )

    # ── Phase 3: Data Integrity Verification (actual DB queries) ──
    logger.info("=" * 60)
    logger.info("PHASE 3: Data Integrity Verification (Oracle vs PG)")
    logger.info("=" * 60)

    verification = None
    try:
        from postgresql.tools.data_transfer_tools import verify_data_integrity
        verification = verify_data_integrity(schema=oracle_schema)

        if verification.get("success"):
            dv = verification.get("data_verification", {})
            dm = verification.get("data_migration", {})
            logger.info(
                "Verification: %s — Oracle=%s rows, PG=%s rows, Fidelity=%.1f%%, Matched=%s/%s tables",
                dv.get("overall_status", "N/A"),
                dm.get("total_rows_oracle", "?"),
                dm.get("total_rows_imported", "?"),
                dv.get("row_count_check", {}).get("fidelity_pct", 0),
                dm.get("success_count", "?"),
                dm.get("total_tables", "?"),
            )

            # Log mismatches
            mismatches = dv.get("row_count_check", {}).get("mismatches", [])
            if mismatches:
                logger.warning("%d table(s) with row count mismatches:", len(mismatches))
                for mm in mismatches[:20]:
                    logger.warning(
                        "  %s: Oracle=%s, PG=%s (diff=%s)",
                        mm.get("table"), mm.get("oracle"), mm.get("pg"), mm.get("diff"),
                    )
        else:
            logger.error("Verification failed: %s", verification.get("error"))
    except Exception as e:
        logger.error("Data verification error: %s", e)

    # ── Phase 4: Generate Combined Phase 1+2 Report ──
    logger.info("=" * 60)
    logger.info("PHASE 4: Generating Combined Migration Report")
    logger.info("=" * 60)

    total_duration = schema_elapsed + data_elapsed
    try:
        from common.orchestrator.pipeline import ensure_combined_report
        report_path = ensure_combined_report(
            schema_result=schema_result,
            data_result=data_serialized if isinstance(data_serialized, dict) else {},
            config=migration_config,
            migration_id=migration_config["migration_id"],
            total_duration=total_duration,
            verification=verification,
        )
        if report_path:
            logger.info("Combined report: %s", report_path)
        else:
            logger.warning("Combined report generation returned None")
    except Exception as e:
        logger.error("Combined report generation failed: %s", e)

    # ── Combine results ──
    result = {
        "migration_id": migration_config["migration_id"],
        "schema_migration": schema_result,
        "data_migration": data_serialized,
        "data_verification": verification,
        "total_duration_seconds": round(total_duration, 1),
    }

    # Save result to file
    output_path = os.path.join(os.path.dirname(__file__), '..', 'migration_result.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Full result saved to: %s", output_path)

    # ── Phase 1→2 handoff: migration-config.json 갱신 ──
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'migration-config.json')
        if os.path.exists(config_path):
            with open(config_path) as f:
                mc = json.load(f)
        else:
            mc = {"project": {"name": migration_config.get("migration_id", "unknown")}, "db": {}}

        mc["phase1"] = {
            "status": "completed" if schema_result.get("status") != "FAILED" else "failed",
            "completed_at": datetime.now().isoformat() if 'datetime' in dir() else "",
            "migration_id": migration_config.get("migration_id", ""),
            "total_duration_seconds": round(total_duration, 1),
        }
        # 스키마 결과 요약만 (전체는 migration_result.json에)
        if isinstance(schema_result, dict):
            mc["phase1"]["tables_total"] = schema_result.get("tables_total", 0)
            mc["phase1"]["tables_success"] = schema_result.get("tables_success", 0)
            mc["phase1"]["functions_total"] = schema_result.get("functions_total", 0)
        if isinstance(data_serialized, dict):
            mc["phase1"]["data_tables_migrated"] = data_serialized.get("tables_migrated", 0)
            mc["phase1"]["data_total_rows"] = data_serialized.get("total_rows", 0)

        with open(config_path, 'w') as f:
            json.dump(mc, f, indent=2, default=str)
        logger.info("migration-config.json updated for Phase 2 handoff: %s", config_path)
    except Exception as e:
        logger.warning("Could not update migration-config.json: %s", e)

    return 0 if schema_result.get("status") != "FAILED" else 1


if __name__ == "__main__":
    sys.exit(main())
