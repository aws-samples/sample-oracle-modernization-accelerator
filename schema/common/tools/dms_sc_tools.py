"""
DMS Schema Conversion Integration Tools

Tools for running AWS DMS Schema Conversion, collecting converted DDL from S3,
and applying them to the target PostgreSQL database. This enables the
"DMS SC First" architecture where rule-based conversion handles ~95% of objects
and AI agents only process the remaining failures.

DMS SC Flow:
  0. start-extension-pack-association → installs conversion backend (one-time)
  1. start-metadata-model-import (empty rules) → loads Oracle metadata
  2. start-metadata-model-conversion (empty rules) → converts Oracle → PostgreSQL
  3. start-metadata-model-export-as-script → exports converted DDL to S3
  4. start-metadata-model-export-to-target → applies DDL directly to PostgreSQL
  5. start-metadata-model-assessment → generates assessment report
  6. Collect assessment from S3 → parse triage (Simple/Medium/Complex)
  7. Return failed objects list for agent-based conversion

IMPORTANT: DMS SC metadata model APIs use "full-path" selection rules with
"explicit" action to enable schema-specific conversion via API without
requiring DMS console "Launch Schema Conversion". See _build_selection_rules().
"""

import json
import logging
import os
import time
import tempfile
from pathlib import Path
from typing import Any

import boto3
from strands import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (from environment or defaults)
# ---------------------------------------------------------------------------

def _get_dms_config() -> dict:
    """Get DMS SC configuration from environment variables."""
    return {
        "migration_project_arn": os.environ.get(
            "DMS_MIGRATION_PROJECT_ARN",
            "arn:aws:dms:ap-northeast-2:YOUR_AWS_ACCOUNT_ID:migration-project:LGSWJVMLDBENBKN3J275ANX7SM",
        ),
        "s3_bucket": os.environ.get("DMS_SC_S3_BUCKET", "oma-dms-sc-YOUR_AWS_ACCOUNT_ID"),
        "region": os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2"),
    }


def _get_dms_client():
    """Create a DMS client."""
    config = _get_dms_config()
    return boto3.client("dms", region_name=config["region"])


def _apply_bigint_conversion_setting(dms_client, project_arn: str):
    """Apply ConvertNumberToBigint=true to all Oracle→PG conversion sections.

    DMS SC defaults to mapping Oracle NUMBER to PostgreSQL NUMERIC, which is
    suboptimal for PK/FK columns. This modifies the conversion configuration
    via API so NUMBER columns become BIGINT instead.
    """
    resp = dms_client.describe_conversion_configuration(
        MigrationProjectIdentifier=project_arn,
    )
    config = json.loads(resp["ConversionConfiguration"])

    modified = False
    for key in config:
        if isinstance(config[key], dict) and "ConvertNumberToBigint" in config[key]:
            if not config[key]["ConvertNumberToBigint"]:
                config[key]["ConvertNumberToBigint"] = True
                modified = True

    if modified:
        dms_client.modify_conversion_configuration(
            MigrationProjectIdentifier=project_arn,
            ConversionConfiguration=json.dumps(config),
        )
        logger.info("Applied ConvertNumberToBigint=true to conversion configuration")
    else:
        logger.info("ConvertNumberToBigint already enabled in conversion configuration")


def _estimate_oracle_object_count(schema: str) -> int:
    """Estimate total Oracle object count for adaptive timeout calculation.

    Queries Oracle ALL_OBJECTS to count tables, indexes, sequences, functions,
    procedures, packages, views, triggers, etc. for the given schema.
    Falls back to a conservative estimate of 500 on connection failure.

    Returns:
        Estimated total object count.
    """
    try:
        from common.tools.oracle_tools import get_oracle_connection
        conn = get_oracle_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM ALL_OBJECTS WHERE OWNER = :schema "
                "AND OBJECT_TYPE IN ("
                "'TABLE','INDEX','SEQUENCE','FUNCTION','PROCEDURE',"
                "'PACKAGE','PACKAGE BODY','VIEW','TRIGGER','TYPE','TYPE BODY',"
                "'SYNONYM','MATERIALIZED VIEW','JOB')",
                {"schema": schema.upper()},
            )
            count = cur.fetchone()[0]
        conn.close()
        logger.info("Oracle object count for %s: %d", schema.upper(), count)
        return count
    except Exception as e:
        logger.warning("Could not query Oracle object count: %s. Using default 500.", e)
        return 500


def _calculate_adaptive_timeout(obj_count: int) -> int:
    """Calculate adaptive timeout based on object count.

    Formula: max(600, 300 + obj_count * 2)
    - Minimum 600s (10 min) for small schemas
    - ~2s per object for larger schemas
    - AMZN (44 tables, ~50 objects) → 600s
    - large schema (688+ tables, ~1034 objects) → 2368s (~40 min)

    Returns:
        Timeout in seconds.
    """
    timeout = max(600, 300 + obj_count * 2)
    logger.info("Adaptive timeout: %ds (based on %d objects)", timeout, obj_count)
    return timeout


def _get_s3_client():
    """Create an S3 client."""
    config = _get_dms_config()
    return boto3.client("s3", region_name=config["region"])


def _ensure_dms_sc_project(dms_client, schema: str, region: str) -> str:
    """Ensure a DMS SC migration project exists for the given schema.

    If DMS_MIGRATION_PROJECT_ARN env var is set, uses that.
    Otherwise, looks for an existing project named '{schema}-dms-sc-project'.
    If not found, creates one using the Oracle source data provider and
    a schema-specific PostgreSQL/MySQL target data provider + secrets.

    Returns the migration project ARN.
    """
    # Detect target DB type
    target_db = os.environ.get("TARGET_DB", "postgresql").lower()

    # If explicitly set, use it
    env_arn = os.environ.get("DMS_MIGRATION_PROJECT_ARN")
    if env_arn:
        return env_arn

    project_name = f"{schema.lower()}-dms-sc-project"

    # Check if project already exists
    resp = dms_client.describe_migration_projects()
    for proj in resp.get("MigrationProjects", []):
        if proj["MigrationProjectName"] == project_name:
            logger.info("Found existing DMS SC project: %s", project_name)
            return proj["MigrationProjectArn"]

    # Need to create — find required resources
    logger.info("Creating DMS SC project: %s (target: %s)", project_name, target_db)

    # Find Oracle source data provider (shared across all projects)
    providers = dms_client.describe_data_providers()["DataProviders"]
    source_arn = None
    for p in providers:
        if p.get("Engine") == "oracle":
            source_arn = p["DataProviderArn"]
            break

    # Find schema-specific target data provider (PG or MySQL)
    target_arn = None
    target_engine = "postgres" if target_db == "postgresql" else "mysql"
    for p in providers:
        if (p["DataProviderName"] == f"{schema.lower()}-dms-sc-target" and
            p.get("Engine") == target_engine):
            target_arn = p["DataProviderArn"]
            break

    if not source_arn or not target_arn:
        raise RuntimeError(
            f"Missing data providers. source={source_arn}, target={target_arn}. "
            f"Create '{schema.lower()}-dms-sc-target' data provider (engine: {target_engine}) first."
        )

    # Find instance profile
    profiles = dms_client.describe_instance_profiles()["InstanceProfiles"]
    profile_arn = profiles[0]["InstanceProfileArn"] if profiles else None
    if not profile_arn:
        raise RuntimeError("No DMS SC instance profile found")

    # Find secrets and role from existing project as template
    existing = resp.get("MigrationProjects", [])
    if not existing:
        raise RuntimeError("No existing DMS SC project to use as template for role ARNs")

    template = existing[0]
    secrets_role = template["SourceDataProviderDescriptors"][0]["SecretsManagerAccessRoleArn"]
    s3_attrs = template.get("SchemaConversionApplicationAttributes", {})

    # Find schema-specific secrets
    sm = boto3.client("secretsmanager", region_name=region)
    oracle_secret = None
    target_secret = None
    target_secret_name = f"oma-secret-{target_db}-{schema.lower()}"

    for secret in sm.list_secrets()["SecretList"]:
        name = secret["Name"]
        if name == "oma-secret-oracle-admin":
            oracle_secret = secret["ARN"]
        elif name == target_secret_name:
            target_secret = secret["ARN"]

    if not oracle_secret:
        oracle_secret = template["SourceDataProviderDescriptors"][0]["SecretsManagerSecretId"]
    if not target_secret:
        raise RuntimeError(
            f"Secret '{target_secret_name}' not found in Secrets Manager. "
            f"Create a secret with target database credentials for {target_db}."
        )

    # Create project
    create_resp = dms_client.create_migration_project(
        MigrationProjectName=project_name,
        SourceDataProviderDescriptors=[{
            "DataProviderIdentifier": source_arn,
            "SecretsManagerSecretId": oracle_secret,
            "SecretsManagerAccessRoleArn": secrets_role,
        }],
        TargetDataProviderDescriptors=[{
            "DataProviderIdentifier": target_arn,
            "SecretsManagerSecretId": target_secret,
            "SecretsManagerAccessRoleArn": secrets_role,
        }],
        InstanceProfileIdentifier=profile_arn,
        SchemaConversionApplicationAttributes=s3_attrs,
    )

    new_arn = create_resp["MigrationProject"]["MigrationProjectArn"]
    logger.info("Created DMS SC project: %s → %s (target: %s)", project_name, new_arn, target_db)
    return new_arn


# ---------------------------------------------------------------------------
# Tool: Run DMS SC Schema Conversion
# ---------------------------------------------------------------------------

@tool
def dms_sc_run_conversion(schema: str, wait: bool = True, timeout: int = 0) -> str:
    """
    Run DMS Schema Conversion to convert Oracle schema to PostgreSQL DDL.

    This triggers the DMS SC engine to perform rule-based conversion of all
    database objects (tables, indexes, sequences, views, procedures, etc.)
    and export the converted DDL scripts to S3.

    Args:
        schema: Oracle schema name to convert (e.g., "AMZN")
        wait: Whether to wait for conversion to complete (default: True)
        timeout: Maximum wait time in seconds. 0 = adaptive (auto-calculated
                 from Oracle object count: max(600, 300 + obj_count * 2))

    Returns:
        JSON string with conversion status and S3 output location.
    """
    try:
        config = _get_dms_config()
        dms = _get_dms_client()

        # Auto-create or find the DMS SC project for this schema
        project_arn = _ensure_dms_sc_project(dms, schema, config["region"])

        # Adaptive timeout: query Oracle object count and calculate
        if timeout <= 0:
            obj_count = _estimate_oracle_object_count(schema)
            timeout = _calculate_adaptive_timeout(obj_count)

        logger.info("Starting DMS SC conversion for schema: %s (timeout: %ds)", schema, timeout)
        logger.info("Migration Project ARN: %s", project_arn)

        # Build full-path selection rules for source and target.
        # Using "full-path" locator with "explicit" action enables schema-specific
        # conversion via API without requiring DMS console initialization.
        # Reference: dms_sc_automation.py
        proj_desc = dms.describe_migration_projects(
            Filters=[{"Name": "migration-project-identifier", "Values": [project_arn]}]
        )
        proj = proj_desc["MigrationProjects"][0]
        src_dp_arn = proj["SourceDataProviderDescriptors"][0]["DataProviderArn"]
        tgt_dp_arn = proj["TargetDataProviderDescriptors"][0]["DataProviderArn"]

        src_dp = dms.describe_data_providers(
            Filters=[{"Name": "data-provider-arn", "Values": [src_dp_arn]}]
        )["DataProviders"][0]
        source_server = src_dp["Settings"]["OracleSettings"]["ServerName"]

        tgt_dp = dms.describe_data_providers(
            Filters=[{"Name": "data-provider-arn", "Values": [tgt_dp_arn]}]
        )["DataProviders"][0]
        target_server = tgt_dp["Settings"]["PostgreSqlSettings"]["ServerName"]

        source_rules = json.dumps({
            "rules": [{
                "rule-id": "1", "rule-name": "1",
                "rule-action": "explicit", "rule-type": "selection",
                "object-locator": {
                    "full-path": f'Servers."{source_server}".Schemas.{schema.upper()}'
                }
            }]
        })
        target_rules = json.dumps({
            "rules": [{
                "rule-id": "1", "rule-name": "1",
                "rule-action": "explicit", "rule-type": "selection",
                "object-locator": {
                    "full-path": f'Servers."{target_server}".Schemas.{schema.lower()}'
                }
            }]
        })
        logger.info("DMS SC source rules: %s", source_rules)
        logger.info("DMS SC target rules: %s", target_rules)

        start_time = time.time()

        # Step -1: Apply ConvertNumberToBigint=true in conversion configuration
        # This ensures Oracle NUMBER PK/FK columns become BIGINT, not NUMERIC.
        try:
            _apply_bigint_conversion_setting(dms, project_arn)
        except Exception as e:
            logger.warning("Could not apply BIGINT conversion setting: %s", e)

        def _wait_for(describe_fn, req_id, label, poll_interval=15):
            """Poll a DMS describe API until completion or timeout."""
            status = "RUNNING"
            while status in ("RUNNING", "IN_PROGRESS", "CREATING") and (time.time() - start_time) < timeout:
                time.sleep(poll_interval)
                desc = describe_fn(
                    MigrationProjectIdentifier=project_arn,
                    Filters=[{"Name": "request-id", "Values": [req_id]}],
                )
                reqs = desc.get("Requests", [])
                if reqs:
                    status = reqs[0].get("Status", "UNKNOWN")
                    logger.info("%s status: %s (%.0fs elapsed)", label, status, time.time() - start_time)
            return status

        # Step 0: Ensure extension pack is installed
        ext_desc = dms.describe_extension_pack_associations(
            MigrationProjectIdentifier=project_arn,
        )
        if not ext_desc.get("Requests"):
            logger.info("Step 0/5: Installing extension pack...")
            ext_resp = dms.start_extension_pack_association(
                MigrationProjectIdentifier=project_arn,
            )
            ext_status = _wait_for(
                dms.describe_extension_pack_associations,
                ext_resp.get("RequestIdentifier", ""),
                "ExtensionPack",
            )
            if ext_status not in ("SUCCESSFUL", "SUCCESS", "COMPLETED"):
                return json.dumps({
                    "success": False, "phase": "extension_pack",
                    "status": ext_status,
                    "error": f"Extension pack install failed: {ext_status}",
                })
            logger.info("Extension pack installed successfully")
        else:
            logger.info("Extension pack already installed, skipping")

        # Step 1: Import metadata model from Oracle source
        logger.info("Step 1/5: Importing metadata model from Oracle source...")
        import_response = dms.start_metadata_model_import(
            MigrationProjectIdentifier=project_arn,
            SelectionRules=source_rules,
            Origin="SOURCE",
            Refresh=True,
        )
        import_status = _wait_for(
            dms.describe_metadata_model_imports,
            import_response.get("RequestIdentifier", ""),
            "Import",
        )
        if import_status not in ("SUCCESSFUL", "SUCCESS", "COMPLETED"):
            return json.dumps({
                "success": False, "phase": "import",
                "import_status": import_status,
                "error": f"Metadata model import failed: {import_status}",
                "elapsed_seconds": round(time.time() - start_time, 1),
            })
        logger.info("Metadata model import completed successfully")

        # Step 2: Convert metadata model (Oracle → PostgreSQL)
        logger.info("Step 2/5: Converting metadata model (Oracle → PostgreSQL)...")
        convert_response = dms.start_metadata_model_conversion(
            MigrationProjectIdentifier=project_arn,
            SelectionRules=source_rules,
        )
        convert_status = _wait_for(
            dms.describe_metadata_model_conversions,
            convert_response.get("RequestIdentifier", ""),
            "Conversion",
        )
        if convert_status not in ("SUCCESSFUL", "SUCCESS", "COMPLETED"):
            return json.dumps({
                "success": False, "phase": "conversion",
                "convert_status": convert_status,
                "error": f"Metadata model conversion failed: {convert_status}",
                "elapsed_seconds": round(time.time() - start_time, 1),
            })
        logger.info("Metadata model conversion completed successfully")

        # Step 3: Export converted DDL to S3 (source Oracle DDL)
        logger.info("Step 3/5: Exporting converted DDL to S3...")
        export_response = dms.start_metadata_model_export_as_script(
            MigrationProjectIdentifier=project_arn,
            SelectionRules=target_rules,
            Origin="TARGET",
            FileName=f"dms-sc-{schema.lower()}",
        )
        request_id = export_response.get("RequestIdentifier", "")
        export_status = _wait_for(
            dms.describe_metadata_model_exports_as_script,
            request_id,
            "Export",
        )

        if not wait:
            return json.dumps({
                "success": True, "status": "STARTED",
                "request_id": request_id,
                "message": "DMS SC export started. Use dms_sc_collect_results when ready.",
            })

        # Step 4: Apply converted DDL directly to target PostgreSQL
        logger.info("Step 4/5: Applying converted DDL to target PostgreSQL...")
        apply_response = dms.start_metadata_model_export_to_target(
            MigrationProjectIdentifier=project_arn,
            SelectionRules=target_rules,
            OverwriteExtensionPack=True,
        )
        apply_status = _wait_for(
            dms.describe_metadata_model_exports_to_target,
            apply_response.get("RequestIdentifier", ""),
            "ApplyToTarget",
        )

        # Step 5: Run assessment
        logger.info("Step 5/5: Running assessment...")
        assess_response = dms.start_metadata_model_assessment(
            MigrationProjectIdentifier=project_arn,
            SelectionRules=source_rules,
        )
        assess_status = _wait_for(
            dms.describe_metadata_model_assessments,
            assess_response.get("RequestIdentifier", ""),
            "Assessment",
            poll_interval=10,
        )

        elapsed = time.time() - start_time

        return json.dumps({
            "success": export_status in ("SUCCESSFUL", "SUCCESS", "COMPLETED"),
            "import_status": import_status,
            "convert_status": convert_status,
            "export_status": export_status,
            "apply_to_target_status": apply_status,
            "assessment_status": assess_status,
            "request_id": request_id,
            "s3_bucket": config["s3_bucket"],
            "s3_prefix": os.environ.get("DMS_SC_PROJECT_NAME", "dms-sc-project"),
            "elapsed_seconds": round(elapsed, 1),
            "timeout_used": timeout,
            "message": f"DMS SC full pipeline completed in {elapsed:.0f}s (ext→import→convert→export→apply→assess)",
        })

    except Exception as e:
        logger.error("DMS SC conversion failed: %s", e)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })


# ---------------------------------------------------------------------------
# Tool: Collect DMS SC Results from S3
# ---------------------------------------------------------------------------

@tool
def dms_sc_collect_results(schema: str) -> str:
    """
    Collect DMS Schema Conversion results from S3 bucket.

    Downloads the converted DDL scripts and assessment report generated
    by DMS SC. Returns the DDL content and a triage of objects into
    "dms_converted" (apply directly) and "agent_required" (need AI conversion).

    Args:
        schema: Oracle schema name (e.g., "AMZN")

    Returns:
        JSON string with:
        - ddl_scripts: list of converted DDL files with content
        - assessment: conversion assessment summary
        - triage: {dms_converted: [...], agent_required: [...]}
    """
    try:
        config = _get_dms_config()
        s3 = _get_s3_client()
        bucket = config["s3_bucket"]

        # List all objects in the DMS SC output
        prefix_patterns = [
            os.environ.get("DMS_SC_PROJECT_NAME", "dms-sc-project") + "/",
            f"default/{schema.upper()}/",
            f"default/{schema.lower()}/",
            f"dms-sc-{schema.lower()}/",
            f"{schema.upper()}/",
            f"{schema.lower()}/",
        ]

        all_objects = []
        for prefix in prefix_patterns:
            try:
                paginator = s3.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        all_objects.append(obj)
            except Exception:
                continue

        if not all_objects:
            # Try listing all objects in bucket to find the right prefix
            try:
                resp = s3.list_objects_v2(Bucket=bucket, MaxKeys=100)
                sample_keys = [o["Key"] for o in resp.get("Contents", [])]
                return json.dumps({
                    "success": False,
                    "error": f"No DMS SC output found for schema '{schema}'",
                    "bucket": bucket,
                    "sample_keys": sample_keys[:20],
                    "hint": "Check if DMS SC conversion has been run. Use dms_sc_run_conversion first.",
                })
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Cannot access S3 bucket: {e}",
                })

        # Download and categorize files
        ddl_scripts = []
        assessment_files = []
        other_files = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for obj in all_objects:
                key = obj["Key"]
                size = obj["Size"]

                # Skip very large files (>5MB) and empty files
                if size == 0 or size > 5 * 1024 * 1024:
                    other_files.append({"key": key, "size": size, "skipped": True})
                    continue

                local_path = os.path.join(tmpdir, key.replace("/", "_"))
                try:
                    s3.download_file(bucket, key, local_path)
                    with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception as e:
                    other_files.append({"key": key, "error": str(e)})
                    continue

                if key.endswith(".sql"):
                    ddl_scripts.append({
                        "key": key,
                        "size": size,
                        "content": content,
                        "type": _classify_ddl_file(key),
                    })
                elif key.endswith(".csv") or "assessment" in key.lower():
                    assessment_files.append({
                        "key": key,
                        "size": size,
                        "content": content,
                    })
                else:
                    other_files.append({"key": key, "size": size})

        # Parse assessment for triage
        triage = _build_triage(assessment_files, ddl_scripts)

        return json.dumps({
            "success": True,
            "bucket": bucket,
            "total_files": len(all_objects),
            "ddl_script_count": len(ddl_scripts),
            "assessment_file_count": len(assessment_files),
            "ddl_scripts": ddl_scripts,
            "assessment_files": [
                {"key": a["key"], "size": a["size"]}
                for a in assessment_files
            ],
            "triage": triage,
        })

    except Exception as e:
        logger.error("Failed to collect DMS SC results: %s", e)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })


def _classify_ddl_file(key: str) -> str:
    """Classify a DDL file by its S3 key."""
    key_lower = key.lower()
    if "table" in key_lower:
        return "TABLE"
    elif "index" in key_lower:
        return "INDEX"
    elif "sequence" in key_lower:
        return "SEQUENCE"
    elif "view" in key_lower:
        return "VIEW"
    elif "procedure" in key_lower or "function" in key_lower:
        return "STORED_CODE"
    elif "trigger" in key_lower:
        return "TRIGGER"
    elif "constraint" in key_lower:
        return "CONSTRAINT"
    elif "package" in key_lower:
        return "PACKAGE"
    return "OTHER"


def _build_triage(assessment_files: list, ddl_scripts: list) -> dict:
    """
    Build triage from assessment: separate DMS-converted vs agent-required.

    Objects with "Simple" complexity → DMS handled → apply DDL directly
    Objects with "Medium"/"Complex" complexity → need agent conversion
    """
    import csv
    import io

    dms_converted = []
    agent_required = []
    assessment_summary = {"Simple": 0, "Medium": 0, "Complex": 0}

    for af in assessment_files:
        content = af.get("content", "")
        if not content:
            continue

        try:
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                complexity = row.get("Estimated complexity", "").strip()
                category = row.get("Category", "").strip()
                occurrence = row.get("Occurrence", "").strip()
                schema_name = row.get("Schema name", "").strip()
                action = row.get("Action", "").strip()

                # Extract object name
                parts = occurrence.split(".") if occurrence else []
                object_name = parts[-1] if parts else category

                if complexity in assessment_summary:
                    assessment_summary[complexity] += 1

                obj_info = {
                    "object_name": object_name,
                    "category": category,
                    "complexity": complexity,
                    "schema": schema_name,
                    "action": action,
                    "occurrence": occurrence,
                }

                if complexity == "Simple":
                    dms_converted.append(obj_info)
                elif complexity in ("Medium", "Complex"):
                    agent_required.append(obj_info)
        except Exception as e:
            logger.warning("Failed to parse assessment CSV: %s", e)

    # If no assessment found, treat all DDL scripts as DMS-converted
    if not dms_converted and not agent_required and ddl_scripts:
        for script in ddl_scripts:
            dms_converted.append({
                "object_name": script["key"],
                "category": script["type"],
                "complexity": "Simple",
                "schema": "",
                "action": "Convert",
                "occurrence": script["key"],
            })

    return {
        "dms_converted_count": len(dms_converted),
        "agent_required_count": len(agent_required),
        "assessment_summary": assessment_summary,
        "dms_converted": dms_converted,
        "agent_required": agent_required,
    }


# ---------------------------------------------------------------------------
# Tool: Apply DMS-converted DDL to PostgreSQL
# ---------------------------------------------------------------------------

@tool
def dms_sc_apply_ddl(schema: str, ddl_content: str = "") -> str:
    """
    Apply DMS Schema Conversion generated DDL to PostgreSQL target.

    If ddl_content is empty, collects DDL from S3 and applies all
    DMS-converted scripts in dependency order.

    Args:
        schema: Target schema name in PostgreSQL (e.g., "amzn")
        ddl_content: Optional DDL content to apply directly.
                     If empty, fetches from S3.

    Returns:
        JSON string with applied DDL results.
    """
    try:
        # Import target DB tools for execution (PostgreSQL or MySQL)
        import sys
        is_mysql = any('mysql' in p for p in sys.path)

        if is_mysql:
            from mysql.tools.mysql_tools import mysql_execute_ddl as execute_ddl
        else:
            from postgresql.tools.postgres_tools import pg_execute_ddl as execute_ddl

        if not ddl_content:
            # Collect from S3
            results_json = dms_sc_collect_results(schema=schema.upper())
            results = json.loads(results_json)

            if not results.get("success"):
                return json.dumps({
                    "success": False,
                    "error": f"Failed to collect DMS results: {results.get('error')}",
                })

            ddl_scripts = results.get("ddl_scripts", [])
            if not ddl_scripts:
                return json.dumps({
                    "success": False,
                    "error": "No DDL scripts found in DMS SC output",
                })

            # Concatenate all DDL scripts in order:
            # sequences → tables → indexes → constraints → views → stored code → triggers
            order = ["SEQUENCE", "TABLE", "INDEX", "CONSTRAINT", "VIEW", "STORED_CODE", "TRIGGER", "PACKAGE", "OTHER"]
            sorted_scripts = sorted(ddl_scripts, key=lambda s: (
                order.index(s["type"]) if s["type"] in order else 99
            ))

            ddl_content = "\n\n".join(s["content"] for s in sorted_scripts)

        if not ddl_content.strip():
            return json.dumps({
                "success": False,
                "error": "No DDL content to apply",
            })

        # Split into individual statements and execute
        statements = _split_ddl_statements(ddl_content)
        applied = []
        failed = []

        skipped = []
        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue

            result = json.loads(execute_ddl(ddl=stmt))
            if result.get("success"):
                applied.append({
                    "index": i,
                    "statement": stmt[:200],
                    "status": "OK",
                })
            else:
                error_msg = result.get("error", "unknown").lower()
                # Idempotent: skip "already exists" errors — DMS SC
                # export_to_target may have already created these objects
                if "already exists" in error_msg or "duplicate" in error_msg:
                    skipped.append({
                        "index": i,
                        "statement": stmt[:200],
                        "status": "SKIPPED_ALREADY_EXISTS",
                    })
                else:
                    failed.append({
                        "index": i,
                        "statement": stmt[:200],
                        "error": result.get("error", "unknown"),
                    })

        return json.dumps({
            "success": len(failed) == 0,
            "total_statements": len(statements),
            "applied_count": len(applied),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
            "applied": applied[:20],  # Truncate for token safety
            "skipped": skipped[:20],
            "failed": failed,
            "message": (
                f"Applied {len(applied)}/{len(statements)} DDL statements, "
                f"{len(skipped)} skipped (already exist), {len(failed)} failures"
            ),
        })

    except Exception as e:
        logger.error("Failed to apply DMS DDL: %s", e)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })


def _split_ddl_statements(ddl: str) -> list[str]:
    """Split DDL text into individual statements."""
    # Handle both ; and $$ delimiters (for PL/pgSQL)
    statements = []
    current = []
    in_dollar_quote = False

    for line in ddl.split("\n"):
        stripped = line.strip()

        # Track $$ blocks
        if "$$" in stripped:
            in_dollar_quote = not in_dollar_quote

        current.append(line)

        if not in_dollar_quote and stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current = []

    # Handle remaining content
    if current:
        stmt = "\n".join(current).strip()
        if stmt and stmt != ";":
            statements.append(stmt)

    return statements


# ---------------------------------------------------------------------------
# Tool: List S3 contents for DMS SC bucket
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tool: Verify what DMS SC actually created in PostgreSQL (GROUND TRUTH)
# ---------------------------------------------------------------------------

@tool
def dms_sc_verify_target(schema: str) -> str:
    """
    Verify what DMS Schema Conversion actually created in target database (PostgreSQL or MySQL)
    by comparing Oracle source objects against target database objects.

    This is the GROUND TRUTH tool. Instead of relying on DMS SC assessment
    CSV or agent conversation, it directly queries both databases and returns
    a definitive list of what still needs agent conversion.

    SCHEMA ARCHITECT MUST CALL THIS BEFORE ANY CONVERSION WORK.

    Args:
        schema: Oracle schema name (e.g., "AMZN")

    Returns:
        JSON with:
        - target_exists: objects already in target database (DO NOT convert these)
        - agent_required: objects missing from target database (MUST convert these)
        - summary: counts and statistics
        - target_db: name of target database ("PostgreSQL" or "MySQL")
    """
    try:
        import oracledb
        import sys
        from common.tools.oracle_tools import get_oracle_connection

        # Determine target database from sys.path
        is_mysql = any('mysql' in p for p in sys.path)
        is_postgresql = any('postgresql' in p for p in sys.path)

        if is_mysql:
            from mysql.tools.mysql_tools import get_mysql_connection, _run_async
        elif is_postgresql:
            from postgresql.tools.postgres_tools import get_pg_connection, _run_async
        else:
            # Default to PostgreSQL for backward compatibility
            from postgresql.tools.postgres_tools import get_pg_connection, _run_async

        # --- Step 1: Get Oracle source objects ---
        ora_conn = get_oracle_connection()
        ora_cursor = ora_conn.cursor()

        # Tables
        ora_cursor.execute(
            "SELECT table_name FROM all_tables WHERE owner = :1 "
            "AND table_name NOT LIKE 'BIN$%'",
            [schema.upper()],
        )
        oracle_tables = {row[0] for row in ora_cursor.fetchall()}

        # Views
        ora_cursor.execute(
            "SELECT view_name FROM all_views WHERE owner = :1",
            [schema.upper()],
        )
        oracle_views = {row[0] for row in ora_cursor.fetchall()}

        # Sequences
        ora_cursor.execute(
            "SELECT sequence_name FROM all_sequences WHERE sequence_owner = :1",
            [schema.upper()],
        )
        oracle_sequences = {row[0] for row in ora_cursor.fetchall()}

        # Stored procedures/functions
        ora_cursor.execute(
            "SELECT DISTINCT object_name, object_type FROM all_objects "
            "WHERE owner = :1 AND object_type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY')",
            [schema.upper()],
        )
        oracle_code = {(row[0], row[1]) for row in ora_cursor.fetchall()}

        # Indexes (non-system)
        ora_cursor.execute(
            "SELECT index_name FROM all_indexes WHERE owner = :1 "
            "AND index_type != 'LOB' AND index_name NOT LIKE 'SYS_%'",
            [schema.upper()],
        )
        oracle_indexes = {row[0] for row in ora_cursor.fetchall()}

        # Constraints
        ora_cursor.execute(
            "SELECT constraint_name, constraint_type FROM all_constraints "
            "WHERE owner = :1 AND constraint_name NOT LIKE 'SYS_%' "
            "AND constraint_name NOT LIKE 'BIN$%'",
            [schema.upper()],
        )
        oracle_constraints = {(row[0], row[1]) for row in ora_cursor.fetchall()}

        ora_cursor.close()
        ora_conn.close()

        # --- Step 2: Get target database objects ---
        if is_mysql:
            async def _check_target():
                conn = await get_mysql_connection()
                target_schema = schema.lower()

                async with conn.cursor() as cursor:
                    # Tables
                    await cursor.execute(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
                    )
                    rows = await cursor.fetchall()
                    target_tables = {row[0].upper() for row in rows}

                    # Views
                    await cursor.execute(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS "
                        "WHERE TABLE_SCHEMA = DATABASE()"
                    )
                    rows = await cursor.fetchall()
                    target_views = {row[0].upper() for row in rows}

                    # Sequences (MySQL doesn't have sequences, check AUTO_INCREMENT columns)
                    await cursor.execute(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() AND AUTO_INCREMENT IS NOT NULL"
                    )
                    rows = await cursor.fetchall()
                    target_sequences = {f"{row[0]}_SEQ".upper() for row in rows}

                    # Functions/Procedures
                    await cursor.execute(
                        "SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES "
                        "WHERE ROUTINE_SCHEMA = DATABASE()"
                    )
                    rows = await cursor.fetchall()
                    target_routines = {row[0].upper() for row in rows}

                    # Indexes
                    await cursor.execute(
                        "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
                        "WHERE TABLE_SCHEMA = DATABASE() GROUP BY INDEX_NAME"
                    )
                    rows = await cursor.fetchall()
                    target_indexes = {row[0].upper() for row in rows}

                    # Constraints
                    await cursor.execute(
                        "SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE "
                        "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS "
                        "WHERE CONSTRAINT_SCHEMA = DATABASE()"
                    )
                    rows = await cursor.fetchall()
                    target_constraints = {(row[0].upper(), row[1][0]) for row in rows}

                conn.close()
                return target_tables, target_views, target_sequences, target_routines, target_indexes, target_constraints
        else:
            # PostgreSQL
            async def _check_target():
                conn = await get_pg_connection()
                target_schema = schema.lower()

                # Tables
                rows = await conn.fetch(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = $1 AND table_type = 'BASE TABLE'",
                    target_schema,
                )
                target_tables = {row["table_name"].upper() for row in rows}

                # Views
                rows = await conn.fetch(
                    "SELECT table_name FROM information_schema.views "
                    "WHERE table_schema = $1",
                    target_schema,
                )
                target_views = {row["table_name"].upper() for row in rows}

                # Sequences
                rows = await conn.fetch(
                    "SELECT sequence_name FROM information_schema.sequences "
                    "WHERE sequence_schema = $1",
                    target_schema,
                )
                target_sequences = {row["sequence_name"].upper() for row in rows}

                # Functions/Procedures
                rows = await conn.fetch(
                    "SELECT routine_name, routine_type FROM information_schema.routines "
                    "WHERE routine_schema = $1",
                    target_schema,
                )
                target_routines = {row["routine_name"].upper() for row in rows}

                # Indexes
                rows = await conn.fetch(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = $1",
                    target_schema,
                )
                target_indexes = {row["indexname"].upper() for row in rows}

                # Constraints
                rows = await conn.fetch(
                    "SELECT constraint_name, constraint_type "
                    "FROM information_schema.table_constraints "
                    "WHERE constraint_schema = $1",
                    target_schema,
                )
                target_constraints = {(row["constraint_name"].upper(), row["constraint_type"][0]) for row in rows}

                await conn.close()
                return target_tables, target_views, target_sequences, target_routines, target_indexes, target_constraints

        target_tables, target_views, target_sequences, target_routines, target_indexes, target_constraints = _run_async(_check_target())

        # --- Step 3: Compute diff (GROUND TRUTH) ---
        target_exists = []
        agent_required = []

        # Tables
        for t in sorted(oracle_tables):
            if t in target_tables:
                target_exists.append({"name": t, "type": "TABLE", "status": "EXISTS_IN_TARGET"})
            else:
                agent_required.append({"name": t, "type": "TABLE", "reason": "MISSING_IN_TARGET"})

        # Views
        for v in sorted(oracle_views):
            if v in target_views:
                target_exists.append({"name": v, "type": "VIEW", "status": "EXISTS_IN_TARGET"})
            else:
                agent_required.append({"name": v, "type": "VIEW", "reason": "MISSING_IN_TARGET"})

        # Sequences
        for s in sorted(oracle_sequences):
            if s in target_sequences:
                target_exists.append({"name": s, "type": "SEQUENCE", "status": "EXISTS_IN_TARGET"})
            else:
                agent_required.append({"name": s, "type": "SEQUENCE", "reason": "MISSING_IN_TARGET"})

        # Stored code — ALWAYS agent_required (DMS SC rarely handles PL/SQL well)
        for name, otype in sorted(oracle_code):
            if name.upper() in target_routines:
                target_exists.append({"name": name, "type": otype, "status": "EXISTS_IN_TARGET"})
            else:
                agent_required.append({"name": name, "type": otype, "reason": "MISSING_IN_TARGET"})

        summary = {
            "oracle_tables": len(oracle_tables),
            "oracle_views": len(oracle_views),
            "oracle_sequences": len(oracle_sequences),
            "oracle_stored_code": len(oracle_code),
            "oracle_indexes": len(oracle_indexes),
            "oracle_constraints": len(oracle_constraints),
            "target_tables": len(target_tables),
            "target_views": len(target_views),
            "target_sequences": len(target_sequences),
            "target_routines": len(target_routines),
            "target_indexes": len(target_indexes),
            "target_constraints": len(target_constraints),
            "dms_sc_coverage_pct": round(len(target_exists) / max(len(target_exists) + len(agent_required), 1) * 100, 1),
            "already_in_target": len(target_exists),
            "needs_agent_conversion": len(agent_required),
        }

        target_db_name = "MySQL" if is_mysql else "PostgreSQL"
        logger.info(
            "DMS SC verify: %d objects in %s, %d need agent conversion (%.1f%% coverage)",
            len(target_exists), target_db_name, len(agent_required), summary["dms_sc_coverage_pct"],
        )

        return json.dumps({
            "success": True,
            "schema": schema.upper(),
            "target_db": target_db_name,
            "summary": summary,
            "target_exists": target_exists,
            "agent_required": agent_required,
            "instruction": (
                f"ONLY convert objects in 'agent_required' list. "
                f"Objects in 'target_exists' were already created by DMS SC — DO NOT touch them. "
                f"This is CODE-ENFORCED ground truth from actual database state."
            ),
        })

    except Exception as e:
        logger.error("DMS SC verify target failed: %s", e)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })


# ---------------------------------------------------------------------------
# Tool: List S3 contents for DMS SC bucket
# ---------------------------------------------------------------------------

@tool
def dms_sc_list_s3(prefix: str = "") -> str:
    """
    List contents of the DMS Schema Conversion S3 bucket.

    Useful for debugging and understanding what DMS SC has produced.

    Args:
        prefix: Optional S3 key prefix to filter (default: list all)

    Returns:
        JSON string with S3 object listing.
    """
    try:
        config = _get_dms_config()
        s3 = _get_s3_client()
        bucket = config["s3_bucket"]

        objects = []
        paginator = s3.get_paginator("list_objects_v2")
        kwargs = {"Bucket": bucket}
        if prefix:
            kwargs["Prefix"] = prefix

        for page in paginator.paginate(**kwargs):
            for obj in page.get("Contents", []):
                objects.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": str(obj["LastModified"]),
                })

        return json.dumps({
            "success": True,
            "bucket": bucket,
            "prefix": prefix,
            "object_count": len(objects),
            "objects": objects[:100],  # Limit for token safety
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })
