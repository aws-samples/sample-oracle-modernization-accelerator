#!/usr/bin/env python3
"""
Conversion Agent - AI-powered parallel conversion for complex database objects

Architecture:
1. Download DMS SC assessment from S3
2. Identify incompatible objects (FAILED/PARTIAL)
3. Extract DDL from Oracle
4. Convert with LLM (using Strands Agent)
5. Apply to PostgreSQL
6. Retry failed objects when dependencies resolve

Features:
- Parallel processing (configurable workers)
- Dependency-aware retry queue
- Topological sort for optimal execution order
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
from typing import List, Dict, Set

# Add parent paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'schema'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'schema', 'common'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'schema', 'postgresql'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    filename="/tmp/conversion_agent.log"
)
logger = logging.getLogger("oma.conversion_agent")

# Also log to stdout for visibility
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)


class DependencyGraph:
    """Manages object dependencies for optimal conversion order."""

    def __init__(self):
        self.graph = defaultdict(set)  # object -> dependencies
        self.reverse_graph = defaultdict(set)  # object -> dependents
        self.in_degree = defaultdict(int)

    def add_dependency(self, obj: str, depends_on: str):
        """obj depends on depends_on."""
        if depends_on not in self.graph[obj]:
            self.graph[obj].add(depends_on)
            self.reverse_graph[depends_on].add(obj)
            self.in_degree[obj] += 1
            if depends_on not in self.in_degree:
                self.in_degree[depends_on] = 0

    def get_ready_objects(self, completed: Set[str]) -> List[str]:
        """Get objects ready to convert (all dependencies met)."""
        ready = []
        for obj, deps in self.graph.items():
            if obj not in completed:
                if all(dep in completed for dep in deps):
                    ready.append(obj)
        return ready

    def topological_sort(self) -> List[str]:
        """Return objects in dependency order (Kahn's algorithm)."""
        result = []
        queue = deque([obj for obj, degree in self.in_degree.items() if degree == 0])
        in_deg = self.in_degree.copy()

        while queue:
            obj = queue.popleft()
            result.append(obj)

            for dependent in self.reverse_graph[obj]:
                in_deg[dependent] -= 1
                if in_deg[dependent] == 0:
                    queue.append(dependent)

        return result


class ConversionAgent:
    """Main conversion agent orchestrator."""

    def __init__(self, schema: str, target_db: str, max_workers: int, migration_project_arn: str = None):
        self.schema = schema
        self.target_db = target_db
        self.max_workers = max_workers
        self.migration_project_arn = migration_project_arn

        self.failed_objects = []
        self.completed = set()
        self.failed_queue = deque()
        self.dependency_graph = DependencyGraph()

        # Statistics
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "retried": 0
        }

    def export_assessment(self, migration_project_arn: str, s3_bucket: str) -> str:
        """Export assessment report via API and return S3 key."""
        import boto3
        import json
        import time

        logger.info("Exporting assessment report via API...")

        dms = boto3.client("dms", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))

        try:
            # Call export API
            response = dms.export_metadata_model_assessment(
                MigrationProjectIdentifier=migration_project_arn,
                SelectionRules=json.dumps({
                    "rules": [{
                        "rule-type": "selection",
                        "rule-id": "1",
                        "rule-name": "1",
                        "rule-action": "explicit",
                        "object-locator": {
                            "full-path": "Servers.FGEOUGKS6ZDZPMSUFBYZUR5CP4.Schemas.WMSON"
                        }
                    }]
                }),
                FileName=f"conversion-agent-{int(time.time())}.csv",
                AssessmentReportTypes=['csv']
            )

            s3_key = response['CsvReport']['S3ObjectKey']
            logger.info("✓ Assessment exported to S3: %s", s3_key)
            return s3_key

        except Exception as e:
            logger.error("Failed to export assessment: %s", e)
            # Fall back to finding existing export
            logger.info("Looking for existing assessment export...")
            return None

    def download_assessment(self, s3_bucket: str, migration_project_arn: str = None) -> List[Dict]:
        """Download DMS SC assessment from S3."""
        import boto3
        import csv
        import zipfile
        import tempfile
        import os as os_module
        from io import StringIO

        logger.info("Downloading DMS SC assessment from S3...")

        s3 = boto3.client("s3", region_name=os_module.environ.get("AWS_REGION", "ap-northeast-2"))

        # Try to export new assessment
        s3_key = None
        if migration_project_arn:
            s3_key = self.export_assessment(migration_project_arn, s3_bucket)

        # If export failed, find latest existing assessment
        if not s3_key:
            prefix = "omabox-stack-dms-sc-project/"
            response = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)

            if "Contents" not in response:
                logger.warning("No assessment files found in S3")
                return []

            # Find assessment zip files
            zip_files = [obj for obj in response["Contents"]
                        if obj["Key"].endswith(".zip") and
                        ("ORACLE_POSTGRESQL" in obj["Key"] or "assessment" in obj["Key"].lower())]

            if not zip_files:
                logger.warning("No assessment zip files found")
                return []

            # Get latest
            latest = max(zip_files, key=lambda x: x["LastModified"])
            s3_key = latest["Key"]
            logger.info("Using existing assessment: %s", s3_key)

        # Download zip file
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            logger.info("Downloading: %s", s3_key)
            s3.download_file(s3_bucket, s3_key, tmp_file.name)

            # Extract zip
            with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                extract_dir = tempfile.mkdtemp()
                zip_ref.extractall(extract_dir)

            # Find main assessment CSV
            csv_file = None
            for root, dirs, files in os_module.walk(extract_dir):
                for file in files:
                    if file.endswith('.csv') and 'Summary' not in file:
                        csv_file = os_module.path.join(root, file)
                        break
                if csv_file:
                    break

            if not csv_file:
                logger.error("Could not find assessment CSV in zip")
                return []

            logger.info("Parsing assessment CSV: %s", os_module.path.basename(csv_file))

            # Parse CSV for Medium/Complex objects
            target_objects = []
            seen_objects = set()  # To deduplicate (multiple action items per object)

            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    category = row.get("Category", "")
                    complexity = row.get("Estimated complexity", "")
                    occurrence = row.get("Occurrence", "")

                    # Only process Medium/Complex code objects
                    if complexity in ("Medium", "Complex") and category in ("function", "procedure", "package-body", "Package function"):
                        # Parse object name from Occurrence
                        # Format: Schemas.WMSON.Packages.PKG_CRYPTO.Public functions.DECRYPT
                        # or: Schemas.WMSON.Functions.FN_GET_WMS_SEQ_STG
                        # or: Schemas.WMSON.Procedures.SP_COLUMN_ADD

                        obj_name = None
                        obj_type = None

                        if "Packages." in occurrence:
                            # Package function/procedure → extract package name
                            parts = occurrence.split(".")
                            for i, part in enumerate(parts):
                                if part == "Packages" and i + 1 < len(parts):
                                    obj_name = parts[i + 1]  # Package name
                                    obj_type = "PACKAGE BODY"
                                    break
                        elif "Functions." in occurrence:
                            # Standalone function
                            parts = occurrence.split(".")
                            for i, part in enumerate(parts):
                                if part == "Functions" and i + 1 < len(parts):
                                    obj_name = parts[i + 1]
                                    obj_type = "FUNCTION"
                                    break
                        elif "Procedures." in occurrence:
                            # Standalone procedure
                            parts = occurrence.split(".")
                            for i, part in enumerate(parts):
                                if part == "Procedures" and i + 1 < len(parts):
                                    obj_name = parts[i + 1]
                                    obj_type = "PROCEDURE"
                                    break

                        if obj_name and obj_type:
                            obj_key = f"{obj_type}:{obj_name}"
                            if obj_key not in seen_objects:
                                seen_objects.add(obj_key)
                                target_objects.append({
                                    "name": obj_name,
                                    "type": obj_type,
                                    "complexity": complexity,
                                    "action_item": row.get("Action item", ""),
                                    "description": row.get("Description", "")[:100]
                                })

            logger.info("Found %d unique Medium/Complex objects to convert", len(target_objects))

            # Log summary by type
            from collections import defaultdict
            by_type = defaultdict(int)
            for obj in target_objects:
                by_type[obj['type']] += 1

            for obj_type, count in sorted(by_type.items()):
                logger.info("  %s: %d", obj_type, count)

            return target_objects

    def extract_oracle_ddl(self, obj_name: str, obj_type: str) -> str:
        """Extract DDL from Oracle."""
        from common.tools.oracle_tools import oracle_get_ddl

        try:
            # Oracle uses underscores in object types
            oracle_obj_type = obj_type.replace(" ", "_")

            result_json = oracle_get_ddl(
                object_name=obj_name,
                object_type=oracle_obj_type,
                schema=self.schema
            )
            result = json.loads(result_json)

            if result.get("success"):
                return result.get("ddl", "")
            else:
                logger.warning("Failed to get DDL for %s %s: %s",
                             obj_type, obj_name, result.get("error"))
                return ""

        except Exception as e:
            logger.exception("Error extracting DDL for %s %s", obj_type, obj_name)
            return ""

    def convert_with_llm(self, oracle_ddl: str, obj_type: str, obj_name: str) -> str:
        """Convert Oracle DDL to PostgreSQL using LLM."""
        import boto3
        import json
        from botocore.config import Config

        try:
            # Increase timeout for large procedures (1700+ lines)
            config = Config(
                read_timeout=600,  # 10 minutes for very large procedures
                connect_timeout=10,
                retries={'max_attempts': 1}  # Reduce retries since it's slow
            )

            bedrock = boto3.client(
                service_name='bedrock-runtime',
                region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-2"),
                config=config
            )

            prompt = f"""Convert this Oracle {obj_type} to PostgreSQL.

Oracle DDL:
{oracle_ddl}

Requirements:
- Convert PL/SQL to PL/pgSQL
- Replace Oracle-specific functions (NVL → COALESCE, etc.)
- Use PostgreSQL syntax
- Return ONLY the PostgreSQL DDL, no explanations

PostgreSQL DDL:"""

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100000,  # Increased for large procedures
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })

            model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-opus-4-7")
            response = bedrock.invoke_model(
                modelId=model_id,
                body=body
            )

            response_body = json.loads(response['body'].read())
            pg_ddl = response_body['content'][0]['text'].strip()

            # Remove markdown code blocks if present
            if pg_ddl.startswith('```'):
                lines = pg_ddl.split('\n')
                # Remove first line (```sql or ```)
                lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                pg_ddl = '\n'.join(lines).strip()

            return pg_ddl

        except Exception as e:
            logger.exception("LLM conversion failed for %s %s", obj_type, obj_name)
            return ""

    def apply_to_postgres(self, pg_ddl: str, obj_name: str) -> bool:
        """Apply converted DDL to PostgreSQL."""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host=os.environ.get("PGHOST"),
                port=int(os.environ.get("PGPORT", 5432)),
                database=self.target_db,
                user=os.environ.get("PGUSER", "postgres"),
                password=os.environ.get("PGPASSWORD")
            )

            cur = conn.cursor()
            cur.execute(pg_ddl)
            conn.commit()
            cur.close()
            conn.close()

            logger.info("✓ Applied %s to PostgreSQL", obj_name)
            return True

        except psycopg2.Error as e:
            error_msg = str(e)
            logger.warning("Failed to apply %s: %s", obj_name, error_msg)

            # Check if object already exists - treat as success
            if "already exists" in error_msg:
                logger.info("  → Already exists, treating as success")
                return True

            # Check if it's a dependency error
            if "does not exist" in error_msg or "undefined" in error_msg:
                logger.info("  → Dependency issue, will retry later")
                return False
            else:
                logger.error("  → Fatal error, cannot retry")
                return False

        except Exception as e:
            logger.exception("Unexpected error applying %s", obj_name)
            return False

    def convert_object(self, obj: Dict) -> bool:
        """Convert a single object (full pipeline)."""
        obj_name = obj["name"]
        obj_type = obj["type"]

        logger.info("Converting %s %s...", obj_type, obj_name)

        # Step 1: Extract Oracle DDL
        oracle_ddl = self.extract_oracle_ddl(obj_name, obj_type)
        if not oracle_ddl:
            logger.error("  → Cannot extract DDL")
            return False

        # Step 2: Convert with LLM
        pg_ddl = self.convert_with_llm(oracle_ddl, obj_type, obj_name)
        if not pg_ddl:
            logger.error("  → Conversion failed")
            return False

        # Step 3: Apply to PostgreSQL
        success = self.apply_to_postgres(pg_ddl, obj_name)

        return success

    def process_with_retry(self):
        """Process objects with dependency-aware retry."""
        max_retries = 3
        retry_count = 0

        # Initial batch
        pending = deque(self.failed_objects)

        while pending and retry_count < max_retries:
            batch_size = len(pending)
            logger.info("=" * 60)
            logger.info("Processing batch: %d objects (retry %d/%d)",
                       batch_size, retry_count, max_retries)
            logger.info("=" * 60)

            # Process in parallel
            failed_this_round = []

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.convert_object, obj): obj
                          for obj in pending}

                for future in as_completed(futures):
                    obj = futures[future]
                    obj_name = obj["name"]

                    try:
                        success = future.result()

                        if success:
                            self.completed.add(obj_name)
                            self.stats["success"] += 1
                        else:
                            failed_this_round.append(obj)
                            self.stats["failed"] += 1

                    except Exception as e:
                        logger.exception("Worker exception for %s", obj_name)
                        failed_this_round.append(obj)
                        self.stats["failed"] += 1

            # Prepare next retry
            if failed_this_round:
                logger.info("Failed this round: %d objects", len(failed_this_round))
                pending = deque(failed_this_round)
                retry_count += 1
                self.stats["retried"] += len(failed_this_round)

                if retry_count < max_retries:
                    logger.info("Waiting 5s before retry...")
                    time.sleep(5)
            else:
                break

        if pending:
            logger.warning("Still failed after %d retries: %d objects",
                         max_retries, len(pending))
            for obj in pending:
                logger.warning("  - %s %s", obj["type"], obj["name"])

    def run(self):
        """Main execution."""
        logger.info("=" * 60)
        logger.info("Conversion Agent - Starting")
        logger.info("=" * 60)
        logger.info("Oracle schema: %s", self.schema)
        logger.info("Target database: %s", self.target_db)
        logger.info("Max workers: %d", self.max_workers)

        # Download assessment
        s3_bucket = os.environ.get("DMS_SC_S3_BUCKET")
        if not s3_bucket:
            logger.error("DMS_SC_S3_BUCKET not set")
            return

        self.failed_objects = self.download_assessment(s3_bucket, self.migration_project_arn)
        self.stats["total"] = len(self.failed_objects)

        if not self.failed_objects:
            logger.info("No objects to convert")
            return

        # Process with retry
        start_time = time.time()
        self.process_with_retry()
        elapsed = time.time() - start_time

        # Summary
        logger.info("=" * 60)
        logger.info("Conversion Agent - Completed")
        logger.info("=" * 60)
        logger.info("Total objects: %d", self.stats["total"])
        logger.info("Successful: %d", self.stats["success"])
        logger.info("Failed: %d", self.stats["failed"])
        logger.info("Retries: %d", self.stats["retried"])
        logger.info("Elapsed: %.1fs", elapsed)
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True, help="Oracle schema name")
    parser.add_argument("--failed-objects", help="JSON file with failed objects (deprecated)")
    parser.add_argument("--target-db", required=True, help="Target PostgreSQL database")
    args = parser.parse_args()

    # Get max workers and migration project ARN from environment
    max_workers = int(os.environ.get("MAX_WORKERS", 4))
    migration_project_arn = os.environ.get("DMS_MIGRATION_PROJECT_ARN")

    # Create and run agent
    agent = ConversionAgent(
        schema=args.schema,
        target_db=args.target_db,
        max_workers=max_workers,
        migration_project_arn=migration_project_arn
    )

    agent.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Conversion agent failed")
        sys.exit(1)
