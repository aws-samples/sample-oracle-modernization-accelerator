"""
DMS Full Load Task Management Tools

Creates and manages DMS replication tasks for full data load.
"""

import json
import time
import logging
from typing import Optional, Dict, Any
from strands import tool
import boto3

logger = logging.getLogger(__name__)


def _get_dms_client():
    """Get DMS client."""
    import os
    region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")
    return boto3.client("dms", region_name=region)


@tool
def create_dms_full_load_task(
    replication_instance_arn: str,
    source_endpoint_arn: str,
    target_endpoint_arn: str,
    schema_name: str,
    task_identifier: Optional[str] = None,
) -> str:
    """
    Create a DMS Full Load replication task.

    Args:
        replication_instance_arn: ARN of DMS replication instance
        source_endpoint_arn: ARN of source (Oracle) endpoint
        target_endpoint_arn: ARN of target (PostgreSQL) endpoint
        schema_name: Source schema name (e.g., 'WMSON')
        task_identifier: Optional task name (auto-generated if not provided)

    Returns:
        JSON with task ARN and status
    """
    try:
        dms = _get_dms_client()

        # Generate task identifier
        if not task_identifier:
            import time
            task_identifier = f"oma-full-load-{schema_name.lower()}-{int(time.time())}"

        # Table mappings
        table_mappings = {
            "rules": [
                {
                    "rule-type": "selection",
                    "rule-id": "1",
                    "rule-name": f"include-{schema_name.lower()}-schema",
                    "object-locator": {
                        "schema-name": schema_name.upper(),
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
                        "schema-name": schema_name.upper()
                    },
                    "rule-action": "convert-lowercase"
                },
                {
                    "rule-type": "transformation",
                    "rule-id": "3",
                    "rule-name": "convert-tables-to-lowercase",
                    "rule-target": "table",
                    "object-locator": {
                        "schema-name": schema_name.upper(),
                        "table-name": "%"
                    },
                    "rule-action": "convert-lowercase"
                }
            ]
        }

        # Task settings
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
            "Logging": {
                "EnableLogging": True,
                "LogComponents": [
                    {"Id": "SOURCE_CAPTURE", "Severity": "LOGGER_SEVERITY_INFO"},
                    {"Id": "TARGET_APPLY", "Severity": "LOGGER_SEVERITY_INFO"},
                    {"Id": "TASK_MANAGER", "Severity": "LOGGER_SEVERITY_INFO"}
                ]
            },
            "ControlTablesSettings": {
                "ControlSchema": "",
                "HistoryTimeslotInMinutes": 5,
                "HistoryTableEnabled": True,
                "SuspendedTablesTableEnabled": True,
                "StatusTableEnabled": True
            }
        }

        logger.info("Creating DMS Full Load task: %s", task_identifier)

        response = dms.create_replication_task(
            ReplicationTaskIdentifier=task_identifier,
            SourceEndpointArn=source_endpoint_arn,
            TargetEndpointArn=target_endpoint_arn,
            ReplicationInstanceArn=replication_instance_arn,
            MigrationType='full-load',
            TableMappings=json.dumps(table_mappings),
            ReplicationTaskSettings=json.dumps(task_settings),
            Tags=[
                {'Key': 'Project', 'Value': 'OMA'},
                {'Key': 'Schema', 'Value': schema_name},
                {'Key': 'Type', 'Value': 'FullLoad'}
            ]
        )

        task = response['ReplicationTask']

        return json.dumps({
            "success": True,
            "task_arn": task['ReplicationTaskArn'],
            "task_identifier": task['ReplicationTaskIdentifier'],
            "status": task['Status'],
            "message": f"DMS Full Load task created: {task_identifier}"
        })

    except Exception as e:
        logger.exception("Failed to create DMS task")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def start_dms_task(task_arn: str) -> str:
    """
    Start a DMS replication task.

    Args:
        task_arn: ARN of the replication task

    Returns:
        JSON with task status
    """
    try:
        dms = _get_dms_client()

        logger.info("Starting DMS task: %s", task_arn)

        response = dms.start_replication_task(
            ReplicationTaskArn=task_arn,
            StartReplicationTaskType='start-replication'
        )

        task = response['ReplicationTask']

        return json.dumps({
            "success": True,
            "task_arn": task['ReplicationTaskArn'],
            "status": task['Status'],
            "message": "DMS task started"
        })

    except Exception as e:
        logger.exception("Failed to start DMS task")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def get_dms_task_status(task_arn: str) -> str:
    """
    Get DMS replication task status and statistics.

    Args:
        task_arn: ARN of the replication task

    Returns:
        JSON with task status, progress, and statistics
    """
    try:
        dms = _get_dms_client()

        response = dms.describe_replication_tasks(
            Filters=[
                {'Name': 'replication-task-arn', 'Values': [task_arn]}
            ]
        )

        if not response['ReplicationTasks']:
            return json.dumps({
                "success": False,
                "error": "Task not found"
            })

        task = response['ReplicationTasks'][0]

        # Get table statistics
        stats_response = dms.describe_table_statistics(
            ReplicationTaskArn=task_arn,
            MaxRecords=100
        )

        table_stats = stats_response.get('TableStatistics', [])

        result = {
            "success": True,
            "task_arn": task['ReplicationTaskArn'],
            "task_identifier": task['ReplicationTaskIdentifier'],
            "status": task['Status'],
            "percent_complete": task.get('ReplicationTaskStats', {}).get('FullLoadProgressPercent', 0),
            "stop_reason": task.get('StopReason', ''),
            "statistics": {
                "total_tables": len(table_stats),
                "full_load_completed": sum(1 for t in table_stats if t.get('FullLoadCondtnlChkFailedRows', 0) == 0 and t.get('LastUpdateTime')),
                "full_load_rows": sum(t.get('FullLoadRows', 0) for t in table_stats),
                "inserts": sum(t.get('Inserts', 0) for t in table_stats),
                "validation_pending": sum(t.get('ValidationPendingRecords', 0) for t in table_stats),
                "validation_failed": sum(t.get('ValidationFailedRecords', 0) for t in table_stats),
            },
            "table_stats_sample": table_stats[:10]  # First 10 tables
        }

        return json.dumps(result, default=str)

    except Exception as e:
        logger.exception("Failed to get DMS task status")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def wait_for_dms_task_completion(
    task_arn: str,
    check_interval: int = 30,
    max_wait_seconds: int = 28800
) -> str:
    """
    Wait for DMS task to complete (with progress updates).

    Args:
        task_arn: ARN of the replication task
        check_interval: Seconds between status checks (default 30)
        max_wait_seconds: Maximum wait time (default 8 hours)

    Returns:
        JSON with final task status and statistics
    """
    try:
        dms = _get_dms_client()
        start_time = time.time()
        last_percent = -1

        logger.info("Waiting for DMS task completion: %s", task_arn)

        while True:
            elapsed = time.time() - start_time

            if elapsed > max_wait_seconds:
                return json.dumps({
                    "success": False,
                    "error": f"Timeout after {max_wait_seconds} seconds",
                    "elapsed_seconds": int(elapsed)
                })

            # Get current status
            status_json = get_dms_task_status(task_arn)
            status = json.loads(status_json)

            if not status.get("success"):
                return status_json

            task_status = status['status']
            percent = status.get('percent_complete', 0)

            # Log progress if changed
            if int(percent) != last_percent:
                logger.info(
                    "DMS task progress: %d%% (status=%s, tables=%d, rows=%d)",
                    int(percent),
                    task_status,
                    status['statistics']['total_tables'],
                    status['statistics']['full_load_rows']
                )
                last_percent = int(percent)

            # Check if completed
            if task_status == 'stopped':
                stop_reason = status.get('stop_reason', '')
                if 'Stop Reason FULL_LOAD_ONLY_FINISHED' in stop_reason:
                    logger.info("DMS task completed successfully")
                    return json.dumps({
                        "success": True,
                        "status": "completed",
                        "elapsed_seconds": int(elapsed),
                        "statistics": status['statistics']
                    })
                else:
                    logger.error("DMS task stopped with error: %s", stop_reason)
                    return json.dumps({
                        "success": False,
                        "error": f"Task stopped: {stop_reason}",
                        "elapsed_seconds": int(elapsed)
                    })

            elif task_status == 'failed':
                return json.dumps({
                    "success": False,
                    "error": "Task failed",
                    "stop_reason": status.get('stop_reason', ''),
                    "elapsed_seconds": int(elapsed)
                })

            # Wait before next check
            time.sleep(check_interval)

    except Exception as e:
        logger.exception("Error waiting for DMS task")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def delete_dms_task(task_arn: str) -> str:
    """
    Delete a DMS replication task.

    Args:
        task_arn: ARN of the replication task

    Returns:
        JSON with success status
    """
    try:
        dms = _get_dms_client()

        logger.info("Deleting DMS task: %s", task_arn)

        dms.delete_replication_task(
            ReplicationTaskArn=task_arn
        )

        return json.dumps({
            "success": True,
            "message": "DMS task deleted"
        })

    except Exception as e:
        logger.exception("Failed to delete DMS task")
        return json.dumps({
            "success": False,
            "error": str(e)
        })
