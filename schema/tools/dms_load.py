"""DMS Full Load - Step 4"""

import json
import logging
import time
import boto3

logger = logging.getLogger(__name__)


class DMSFullLoader:
    """Execute DMS Full Load for data migration."""

    def __init__(self, region: str = "ap-northeast-2"):
        self.region = region
        self.dms = boto3.client("dms", region_name=region)

    def execute(
        self,
        schema: str,
        replication_instance_arn: str,
        source_endpoint_arn: str,
        target_endpoint_arn: str,
        timeout: int = 7200
    ) -> dict:
        """
        Execute DMS Full Load.

        Returns:
            dict: {
                "success": bool,
                "task_arn": str,
                "statistics": dict
            }
        """
        logger.info("=" * 60)
        logger.info("Step 4: DMS Full Load")
        logger.info("=" * 60)

        try:
            # Create task
            task_id = f"oma-full-load-{schema.lower()}-{int(time.time())}"

            table_mappings = {
                "rules": [
                    {
                        "rule-type": "selection",
                        "rule-id": "1",
                        "rule-name": f"include-{schema.lower()}-schema",
                        "object-locator": {
                            "schema-name": schema.upper(),
                            "table-name": "%"
                        },
                        "rule-action": "include"
                    },
                    {
                        "rule-type": "transformation",
                        "rule-id": "2",
                        "rule-name": "convert-schema-to-lowercase",
                        "rule-target": "schema",
                        "object-locator": {
                            "schema-name": schema.upper()
                        },
                        "rule-action": "convert-lowercase"
                    },
                    {
                        "rule-type": "transformation",
                        "rule-id": "3",
                        "rule-name": "convert-tables-to-lowercase",
                        "rule-target": "table",
                        "object-locator": {
                            "schema-name": schema.upper(),
                            "table-name": "%"
                        },
                        "rule-action": "convert-lowercase"
                    }
                ]
            }

            task_settings = {
                "TargetMetadata": {
                    "SupportLobs": True,
                    "FullLobMode": False,
                    "LobChunkSize": 64,
                    "LimitedSizeLobMode": True,
                    "LobMaxSize": 32
                },
                "FullLoadSettings": {
                    "TargetTablePrepMode": "TRUNCATE_BEFORE_LOAD",
                    "MaxFullLoadSubTasks": 8,
                    "TransactionConsistencyTimeout": 600,
                    "CommitRate": 10000
                },
                "ChangeProcessingTuning": {
                    "BatchApplyPreserveTransaction": True,
                    "MinTransactionSize": 1000
                },
                "Logging": {
                    "EnableLogging": True
                }
            }

            logger.info("Creating DMS task: %s", task_id)

            response = self.dms.create_replication_task(
                ReplicationTaskIdentifier=task_id,
                SourceEndpointArn=source_endpoint_arn,
                TargetEndpointArn=target_endpoint_arn,
                ReplicationInstanceArn=replication_instance_arn,
                MigrationType="full-load",
                TableMappings=json.dumps(table_mappings),
                ReplicationTaskSettings=json.dumps(task_settings)
            )

            task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
            logger.info("✓ Task created: %s", task_arn)

            # Wait for ready
            logger.info("Waiting for task to be ready...")
            self._wait_for_status(task_arn, "ready", timeout=300)

            # Start task
            logger.info("Starting task...")
            self.dms.start_replication_task(
                ReplicationTaskArn=task_arn,
                StartReplicationTaskType="start-replication"
            )

            # Wait for completion
            logger.info("Waiting for completion...")
            stats = self._wait_for_completion(task_arn, timeout)

            logger.info("✓ Data migration completed")
            logger.info("Tables loaded: %d", stats.get("tables_loaded", 0))
            logger.info("Rows loaded: %d", stats.get("full_load_rows", 0))
            logger.info("Errors: %d", stats.get("full_load_error_rows", 0))

            return {
                "success": True,
                "task_arn": task_arn,
                "statistics": stats
            }

        except Exception as e:
            logger.exception("DMS Full Load failed")
            return {
                "success": False,
                "error": str(e)
            }

    def _wait_for_status(self, task_arn: str, target_status: str, timeout: int):
        """Wait for task to reach target status."""
        elapsed = 0
        check_interval = 10

        while elapsed < timeout:
            response = self.dms.describe_replication_tasks(
                Filters=[
                    {"Name": "replication-task-arn", "Values": [task_arn]}
                ]
            )

            if response["ReplicationTasks"]:
                task = response["ReplicationTasks"][0]
                status = task["Status"]

                logger.info("Task status: %s (waited %ds)", status, elapsed)

                if status == target_status:
                    return

                if status in ("failed", "deleting", "deleted"):
                    raise Exception(f"Task entered terminal state: {status}")

            time.sleep(check_interval)
            elapsed += check_interval

        raise TimeoutError(f"Task did not reach {target_status} within {timeout}s")

    def _wait_for_completion(self, task_arn: str, timeout: int) -> dict:
        """Wait for task to complete and return statistics."""
        elapsed = 0
        check_interval = 30

        while elapsed < timeout:
            response = self.dms.describe_replication_tasks(
                Filters=[
                    {"Name": "replication-task-arn", "Values": [task_arn]}
                ]
            )

            if response["ReplicationTasks"]:
                task = response["ReplicationTasks"][0]
                status = task["Status"]
                stop_reason = task.get("StopReason", "")

                # Get table statistics
                stats_response = self.dms.describe_table_statistics(
                    ReplicationTaskArn=task_arn,
                    MaxRecords=500
                )

                table_stats = stats_response.get("TableStatistics", [])

                total_rows = sum(t.get("FullLoadRows", 0) for t in table_stats)
                error_rows = sum(t.get("FullLoadErrorRows", 0) for t in table_stats)
                tables_loaded = sum(1 for t in table_stats if t.get("TableState") == "Table completed")
                tables_loading = sum(1 for t in table_stats if t.get("TableState") == "Table is being loaded")
                tables_errored = sum(1 for t in table_stats if t.get("TableState") == "Table error")

                logger.info(
                    "[%ds] %s | Tables: %d loaded, %d loading, %d errors | Rows: %d",
                    elapsed, status, tables_loaded, tables_loading, tables_errored, total_rows
                )

                if status == "stopped":
                    if "FULL_LOAD_ONLY_FINISHED" in stop_reason or "NORMAL" in stop_reason:
                        return {
                            "tables_loaded": tables_loaded,
                            "full_load_rows": total_rows,
                            "full_load_error_rows": error_rows,
                            "tables_errored": tables_errored
                        }
                    else:
                        raise Exception(f"Task stopped unexpectedly: {stop_reason}")

                if status == "failed":
                    raise Exception(f"Task failed: {stop_reason}")

            time.sleep(check_interval)
            elapsed += check_interval

        raise TimeoutError(f"Task did not complete within {timeout}s")

    def discover_infrastructure(self) -> dict:
        """
        Discover DMS infrastructure (instance, endpoints).

        Returns:
            dict: {
                "success": bool,
                "replication_instance_arn": str,
                "source_endpoint_arn": str,
                "target_endpoint_arn": str
            }
        """
        try:
            # Get replication instance
            instances = self.dms.describe_replication_instances()
            if not instances["ReplicationInstances"]:
                raise ValueError("No DMS replication instance found")

            instance = instances["ReplicationInstances"][0]
            replication_instance_arn = instance["ReplicationInstanceArn"]
            logger.info("Found DMS instance: %s", instance["ReplicationInstanceIdentifier"])

            # Get source endpoint (Oracle)
            source_endpoints = self.dms.describe_endpoints(
                Filters=[{"Name": "engine-name", "Values": ["oracle"]}]
            )
            if not source_endpoints["Endpoints"]:
                raise ValueError("No Oracle source endpoint found")

            source_endpoint_arn = source_endpoints["Endpoints"][0]["EndpointArn"]
            logger.info("Found source endpoint: %s", source_endpoints["Endpoints"][0]["EndpointIdentifier"])

            # Get target endpoint (PostgreSQL)
            target_endpoints = self.dms.describe_endpoints(
                Filters=[{"Name": "engine-name", "Values": ["aurora-postgresql", "postgres"]}]
            )
            if not target_endpoints["Endpoints"]:
                raise ValueError("No PostgreSQL target endpoint found")

            target_endpoint_arn = target_endpoints["Endpoints"][0]["EndpointArn"]
            logger.info("Found target endpoint: %s", target_endpoints["Endpoints"][0]["EndpointIdentifier"])

            return {
                "success": True,
                "replication_instance_arn": replication_instance_arn,
                "source_endpoint_arn": source_endpoint_arn,
                "target_endpoint_arn": target_endpoint_arn
            }

        except Exception as e:
            logger.exception("Failed to discover DMS infrastructure")
            return {
                "success": False,
                "error": str(e)
            }
