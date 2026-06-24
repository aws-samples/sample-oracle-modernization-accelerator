#!/usr/bin/env python3
"""
Run Phase 2 (Data Migration) only.
Assumes Phase 1 (Schema) is already completed.
"""

import os
import sys
import json
import logging

# Add paths
schema_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, schema_root)
sys.path.insert(0, os.path.join(schema_root, 'common'))
sys.path.insert(0, os.path.join(schema_root, 'postgresql'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oma.data_only")


def load_oma_properties():
    """Load environment variables from oma.properties [COMMON] section."""
    properties_file = os.path.join(schema_root, '..', 'env', 'oma.properties')

    if not os.path.exists(properties_file):
        logger.warning("oma.properties not found at: %s", properties_file)
        return

    logger.info("Loading environment from: %s", properties_file)
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
                    oma_base = os.path.abspath(os.path.join(schema_root, '..'))
                    value = value.replace('${OMA_BASE_DIR}', oma_base)

                if key and not os.environ.get(key):
                    os.environ[key] = value

    logger.info("Environment variables loaded from oma.properties")


def main():
    logger.info("=" * 60)
    logger.info("OMA - Phase 2 (Data Migration) ONLY")
    logger.info("=" * 60)

    # Load environment
    load_oma_properties()

    # Get schema name
    oracle_schema = os.environ.get("ORACLE_USER", "WMSON").upper()
    logger.info("Oracle Schema: %s", oracle_schema)

    # Import data transfer tool
    from postgresql.tools.data_transfer_tools import migrate_all_tables

    logger.info("Starting data migration for schema: %s", oracle_schema)
    logger.info("This will:")
    logger.info("  1. Truncate all PostgreSQL tables")
    logger.info("  2. Export data from Oracle")
    logger.info("  3. Import to PostgreSQL using COPY protocol")
    logger.info("  4. Sync sequences")

    try:
        result_json = migrate_all_tables(
            schema=oracle_schema,
            truncate_first=True
        )

        result = json.loads(result_json)

        logger.info("=" * 60)
        logger.info("Data Migration Completed!")
        logger.info("=" * 60)

        if result.get("success"):
            logger.info("✓ Status: SUCCESS")
            logger.info("  Total tables: %s", result.get("total_tables", "?"))
            logger.info("  Success: %s", result.get("success_count", "?"))
            logger.info("  Failed: %s", result.get("failed_count", "?"))
            logger.info("  Skipped: %s", result.get("skipped_count", "?"))
            logger.info("  Oracle rows: %s", result.get("total_rows_oracle", "?"))
            logger.info("  Imported rows: %s", result.get("total_rows_imported", "?"))
            logger.info("  Sequences synced: %s", result.get("sequences_synced", "?"))

            # Show failed tables if any
            failed = result.get("failed_tables", [])
            if failed:
                logger.warning("Failed tables:")
                for table in failed[:10]:
                    logger.warning("  - %s: %s", table.get("name"), table.get("error"))

            return 0
        else:
            logger.error("✗ Status: FAILED")
            logger.error("  Error: %s", result.get("error", "Unknown error"))
            return 1

    except Exception as e:
        logger.exception("Data migration failed with exception: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
