"""DMS Schema Conversion - Step 1

Simplified wrapper around DMS SC, based on proven dms_sc_tools.py logic.
"""

import json
import logging
import os
import sys
import time

# Import from existing proven implementation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'schema', 'common', 'tools'))

from dms_sc_tools import dms_sc_run_conversion, dms_sc_collect_results

logger = logging.getLogger(__name__)


class DMSSCConverter:
    """Execute DMS Schema Conversion using proven implementation."""

    def __init__(self, migration_project_arn: str = None, s3_bucket: str = None, region: str = "ap-northeast-2"):
        self.migration_project_arn = migration_project_arn  # Optional - will auto-create
        self.s3_bucket = s3_bucket
        self.region = region

        # Set environment for dms_sc_tools (only if provided)
        if migration_project_arn:
            os.environ["DMS_MIGRATION_PROJECT_ARN"] = migration_project_arn
        elif "DMS_MIGRATION_PROJECT_ARN" in os.environ:
            # Remove stale ARN from environment
            del os.environ["DMS_MIGRATION_PROJECT_ARN"]

        os.environ["DMS_SC_S3_BUCKET"] = s3_bucket
        os.environ["AWS_DEFAULT_REGION"] = region
        os.environ["DMS_SC_PROJECT_NAME"] = "omabox-stack-dms-sc-project"

    def run_conversion(self, schema: str, timeout: int = 600) -> dict:
        """
        Execute DMS SC conversion using proven dms_sc_tools.

        Returns:
            dict: {
                "success": bool,
                "schema": str,
                "s3_bucket": str,
                "s3_prefix": str
            }
        """
        logger.info("=" * 60)
        logger.info("Step 1: DMS Schema Conversion")
        logger.info("=" * 60)
        logger.info("Migration Project ARN: %s", self.migration_project_arn)
        logger.info("Schema: %s", schema)

        try:
            # Call proven implementation
            result_json = dms_sc_run_conversion(
                oracle_schema=schema,
                wait=True,
                timeout=timeout
            )

            result = json.loads(result_json)

            if not result.get("success"):
                logger.error("DMS SC conversion failed: %s", result.get("error"))
                return {
                    "success": False,
                    "error": result.get("error")
                }

            logger.info("✓ DMS SC conversion completed successfully")

            return {
                "success": True,
                "schema": schema,
                "s3_bucket": self.s3_bucket,
                "s3_prefix": f"dms-sc/{schema.upper()}"
            }

        except Exception as e:
            logger.exception("DMS SC conversion failed")
            return {
                "success": False,
                "error": str(e)
            }

    def download_results(self, schema: str) -> dict:
        """
        Download conversion results from S3 using proven implementation.

        Returns:
            dict: {
                "success": bool,
                "ddl_scripts": [{"key": str, "content": str}],
                "assessment": str
            }
        """
        logger.info("Downloading DMS SC results from S3...")

        try:
            # Call proven implementation
            result_json = dms_sc_collect_results(oracle_schema=schema)
            result = json.loads(result_json)

            if not result.get("success"):
                logger.warning("Failed to collect results: %s", result.get("error"))
                return {
                    "success": False,
                    "error": result.get("error")
                }

            # Extract DDL scripts and assessment
            ddl_scripts = result.get("ddl_scripts", [])
            assessment_files = result.get("assessment_files", [])

            # Get assessment content from first assessment file
            assessment_csv = None
            if assessment_files:
                assessment_csv = assessment_files[0].get("content", "")

            logger.info("Downloaded %d DDL scripts", len(ddl_scripts))
            logger.info("Downloaded %d assessment files", len(assessment_files))

            return {
                "success": True,
                "ddl_scripts": ddl_scripts,
                "assessment_files": assessment_files,
                "assessment": assessment_csv,
                "triage": result.get("triage", {})
            }

        except Exception as e:
            logger.exception("Failed to download results")
            return {
                "success": False,
                "error": str(e)
            }

    def parse_assessment(self, assessment_csv: str) -> dict:
        """
        Parse DMS assessment CSV to find failed objects.

        Returns:
            dict: {
                "total_objects": int,
                "converted": int,
                "failed": int,
                "failed_objects": [{"name": str, "type": str, "reason": str}]
            }
        """
        if not assessment_csv:
            logger.warning("No assessment CSV provided")
            return {
                "total_objects": 0,
                "converted": 0,
                "failed": 0,
                "failed_objects": []
            }

        import csv
        from io import StringIO

        failed_objects = []
        total = 0
        converted = 0
        failed = 0

        try:
            reader = csv.DictReader(StringIO(assessment_csv))

            for row in reader:
                total += 1

                # Check conversion status
                status = row.get("ConversionStatus", "").upper()
                obj_name = row.get("ObjectName", "")
                obj_type = row.get("ObjectType", "")
                action_item = row.get("ActionItem", "")

                if status in ("FAILED", "PARTIAL", "ACTION_REQUIRED"):
                    failed += 1
                    failed_objects.append({
                        "name": obj_name,
                        "type": obj_type,
                        "reason": action_item,
                        "status": status
                    })
                else:
                    converted += 1

        except Exception as e:
            logger.warning("Error parsing assessment CSV: %s", e)

        logger.info("Assessment: %d total, %d converted, %d failed", total, converted, failed)

        return {
            "total_objects": total,
            "converted": converted,
            "failed": failed,
            "failed_objects": failed_objects
        }
