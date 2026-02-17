#!/usr/bin/env python3.11
"""
DMS Data Migration Agent
1. Drop FK constraints in PostgreSQL
2. Create and run DMS replication task
3. Recreate FK constraints after migration
"""
import os
import sys
import boto3
import time
import json
import asyncio
from pathlib import Path
from mcp.client.sse import sse_client
from strands import Agent
from strands.tools.mcp import MCPClient

# Configuration
REGION = os.getenv("AWS_REGION", "us-east-1")
SCHEMA_NAME = os.getenv("DMS_SC_SCHEMA_NAME", "DEMO")
REPLICATION_INSTANCE_ARN = None
SOURCE_ENDPOINT_ARN = None
TARGET_ENDPOINT_ARN = None

def get_dms_resources():
    """Get DMS replication instance and endpoints"""
    global REPLICATION_INSTANCE_ARN, SOURCE_ENDPOINT_ARN, TARGET_ENDPOINT_ARN
    
    print("\n📋 Getting DMS resources...")
    dms = boto3.client('dms', region_name=REGION)
    
    # Check for running tasks
    tasks = dms.describe_replication_tasks()['ReplicationTasks']
    running_tasks = [t for t in tasks if t['Status'] in ['starting', 'running', 'modifying']]
    if running_tasks:
        print(f"\n⚠️  Found {len(running_tasks)} migration task(s) in progress:")
        for task in running_tasks:
            print(f"   - {task['ReplicationTaskIdentifier']}: {task['Status']}")
            if 'ReplicationTaskStats' in task:
                stats = task['ReplicationTaskStats']
                print(f"     Progress: {stats.get('FullLoadProgressPercent', 0)}% | "
                      f"Tables Loaded: {stats.get('TablesLoaded', 0)}/{stats.get('TablesLoaded', 0) + stats.get('TablesLoading', 0)}")
        
        response = input("\n   Continue and create new task? (y/n): ")
        if response.lower() != 'y':
            print("   Aborted by user")
            sys.exit(0)
    
    # Get replication instance
    instances = dms.describe_replication_instances()['ReplicationInstances']
    if not instances:
        raise Exception("No replication instance found")
    REPLICATION_INSTANCE_ARN = instances[0]['ReplicationInstanceArn']
    print(f"   Replication Instance: {instances[0]['ReplicationInstanceIdentifier']}")
    
    # Get endpoints
    endpoints = dms.describe_endpoints()['Endpoints']
    for ep in endpoints:
        if ep['EndpointType'] == 'SOURCE':
            SOURCE_ENDPOINT_ARN = ep['EndpointArn']
            print(f"   Source Endpoint: {ep['EndpointIdentifier']}")
        elif ep['EndpointType'] == 'TARGET':
            TARGET_ENDPOINT_ARN = ep['EndpointArn']
            print(f"   Target Endpoint: {ep['EndpointIdentifier']}")
    
    if not SOURCE_ENDPOINT_ARN or not TARGET_ENDPOINT_ARN:
        raise Exception("Source or Target endpoint not found")

def setup_pg_client():
    """Setup PostgreSQL MCP client"""
    print("\n🔗 Setting up PostgreSQL MCP client...")
    pg_client = MCPClient(
        lambda: sse_client("http://localhost:9081/sse"),
        prefix="pg"
    )
    pg_client.start()
    print("   ✅ PostgreSQL MCP client ready")
    return pg_client

def drop_foreign_keys(pg_client):
    """Drop all FK constraints in schema"""
    print(f"\n🔓 Step 1: Dropping foreign key constraints in {SCHEMA_NAME}...")
    
    agent = Agent(
        tools=pg_client.list_tools_sync(),
        system_prompt=f"""You are a PostgreSQL DBA.
Query and drop all foreign key constraints in schema: {SCHEMA_NAME}

Steps:
1. Query information_schema.table_constraints to find all FOREIGN KEY constraints
2. Generate and execute ALTER TABLE DROP CONSTRAINT statements for each FK
3. Save the FK definitions for later recreation
4. Return the list of dropped FKs with their DDL for recreation"""
    )
    
    result = asyncio.run(agent.invoke_async(f"Drop all foreign key constraints in schema {SCHEMA_NAME} and return their DDL for recreation"))
    print("   ✅ Foreign keys dropped")
    return str(result)

def create_table_mappings():
    """Create table mappings for DMS task"""
    return {
        "rules": [
            {
                "rule-type": "selection",
                "rule-id": "1",
                "rule-name": "include-schema",
                "object-locator": {
                    "schema-name": SCHEMA_NAME,
                    "table-name": "%"
                },
                "rule-action": "include"
            },
            {
                "rule-type": "transformation",
                "rule-id": "2",
                "rule-name": "schema-lowercase",
                "rule-target": "schema",
                "object-locator": {
                    "schema-name": SCHEMA_NAME
                },
                "rule-action": "convert-lowercase"
            },
            {
                "rule-type": "transformation",
                "rule-id": "3",
                "rule-name": "table-lowercase",
                "rule-target": "table",
                "object-locator": {
                    "schema-name": SCHEMA_NAME,
                    "table-name": "%"
                },
                "rule-action": "convert-lowercase"
            },
            {
                "rule-type": "transformation",
                "rule-id": "4",
                "rule-name": "column-lowercase",
                "rule-target": "column",
                "object-locator": {
                    "schema-name": SCHEMA_NAME,
                    "table-name": "%",
                    "column-name": "%"
                },
                "rule-action": "convert-lowercase"
            }
        ]
    }

def create_task_settings():
    """Create DMS task settings"""
    return {
        "TargetMetadata": {
            "SupportLobs": True,
            "FullLobMode": False,
            "LobChunkSize": 64,
            "LimitedSizeLobMode": True,
            "LobMaxSize": 32
        },
        "FullLoadSettings": {
            "TargetTablePrepMode": "TRUNCATE_BEFORE_LOAD",
            "CreatePkAfterFullLoad": False,
            "StopTaskCachedChangesApplied": False,
            "StopTaskCachedChangesNotApplied": False,
            "MaxFullLoadSubTasks": 8,
            "TransactionConsistencyTimeout": 600,
            "CommitRate": 10000
        },
        "ValidationSettings": {
            "EnableValidation": True,
            "ValidationMode": "ROW_LEVEL",
            "ThreadCount": 5,
            "FailureMaxCount": 10000,
            "RecordFailureDelayLimitInMinutes": 0,
            "RecordSuspendDelayInMinutes": 30,
            "MaxKeyColumnSize": 8096,
            "TableFailureMaxCount": 1000,
            "ValidationOnly": False,
            "HandleCollationDiff": False,
            "RecordFailureDelayInMinutes": 5,
            "SkipLobColumns": True,
            "ValidationPartialLobSize": 0,
            "ValidationQueryCdcDelaySeconds": 0
        },
        "Logging": {
            "EnableLogging": True,
            "LogComponents": [
                {
                    "Id": "TRANSFORMATION",
                    "Severity": "LOGGER_SEVERITY_DEFAULT"
                },
                {
                    "Id": "SOURCE_UNLOAD",
                    "Severity": "LOGGER_SEVERITY_DEFAULT"
                },
                {
                    "Id": "TARGET_LOAD",
                    "Severity": "LOGGER_SEVERITY_DEFAULT"
                },
                {
                    "Id": "DATA_STRUCTURE",
                    "Severity": "LOGGER_SEVERITY_DEFAULT"
                }
            ]
        }
    }

def create_and_run_task(dms):
    """Create and run DMS replication task"""
    print("\n🚀 Step 2: Creating DMS replication task...")
    
    task_id = f"data-migration-{SCHEMA_NAME.lower()}-{int(time.time())}"
    
    try:
        response = dms.create_replication_task(
            ReplicationTaskIdentifier=task_id,
            SourceEndpointArn=SOURCE_ENDPOINT_ARN,
            TargetEndpointArn=TARGET_ENDPOINT_ARN,
            ReplicationInstanceArn=REPLICATION_INSTANCE_ARN,
            MigrationType='full-load',
            TableMappings=json.dumps(create_table_mappings()),
            ReplicationTaskSettings=json.dumps(create_task_settings())
        )
        
        task_arn = response['ReplicationTask']['ReplicationTaskArn']
        print(f"   ✅ Task created: {task_id}")
        
        # Wait for task to be ready
        print("   ⏳ Waiting for task to be ready...")
        waiter = dms.get_waiter('replication_task_ready')
        waiter.wait(
            Filters=[{'Name': 'replication-task-arn', 'Values': [task_arn]}],
            WaiterConfig={'Delay': 15, 'MaxAttempts': 40}
        )
        print("   ✅ Task ready")
        
        # Start task
        print("\n📊 Step 3: Starting data migration...")
        dms.start_replication_task(
            ReplicationTaskArn=task_arn,
            StartReplicationTaskType='start-replication'
        )
        print("   ✅ Migration started")
        
        # Monitor task
        print("   ⏳ Monitoring migration progress...")
        while True:
            response = dms.describe_replication_tasks(
                Filters=[{'Name': 'replication-task-arn', 'Values': [task_arn]}]
            )
            
            task = response['ReplicationTasks'][0]
            status = task['Status']
            
            if 'ReplicationTaskStats' in task:
                stats = task['ReplicationTaskStats']
                validation_info = ""
                if stats.get('ValidationPendingRecords', 0) > 0 or stats.get('ValidationFailedRecords', 0) > 0:
                    validation_info = f" | Validation: Pending={stats.get('ValidationPendingRecords', 0)}, Failed={stats.get('ValidationFailedRecords', 0)}"
                
                print(f"      Status: {status} | "
                      f"Full Load: {stats.get('FullLoadProgressPercent', 0)}% | "
                      f"Tables Loaded: {stats.get('TablesLoaded', 0)} | "
                      f"Tables Loading: {stats.get('TablesLoading', 0)}"
                      f"{validation_info}")
            else:
                print(f"      Status: {status}")
            
            if status == 'stopped':
                stop_reason = task.get('StopReason', 'Unknown')
                if 'FULL_LOAD_ONLY_FINISHED' in stop_reason or 'Full load complete' in stop_reason:
                    print("   ✅ Migration completed successfully")
                    return task_arn
                else:
                    print(f"   ❌ Migration stopped: {stop_reason}")
                    return None
            elif status == 'failed':
                print(f"   ❌ Migration failed")
                return None
            
            time.sleep(15)
            
    except Exception as e:
        print(f"   ❌ Task creation/execution failed: {e}")
        return None

def recreate_foreign_keys(pg_client, fk_ddl):
    """Recreate FK constraints"""
    print(f"\n🔒 Step 4: Recreating foreign key constraints...")
    
    agent = Agent(
        tools=pg_client.list_tools_sync(),
        system_prompt=f"""You are a PostgreSQL DBA.
Recreate foreign key constraints using the provided DDL statements.
Execute each ALTER TABLE ADD CONSTRAINT statement."""
    )
    
    result = asyncio.run(agent.invoke_async(f"Recreate foreign key constraints using this DDL:\n{fk_ddl}"))
    print("   ✅ Foreign keys recreated")
    return str(result)

def main():
    """Main workflow"""
    print("="*60)
    print("DMS Data Migration Agent")
    print("="*60)
    
    # Get DMS resources
    get_dms_resources()
    
    # Setup PostgreSQL client
    pg_client = setup_pg_client()
    
    # Drop FKs
    fk_ddl = drop_foreign_keys(pg_client)
    
    # Create and run DMS task
    dms = boto3.client('dms', region_name=REGION)
    task_arn = create_and_run_task(dms)
    
    if not task_arn:
        print("\n❌ Migration failed")
        return False
    
    # Recreate FKs
    recreate_foreign_keys(pg_client, fk_ddl)
    
    print("\n" + "="*60)
    print("✅ DATA MIGRATION COMPLETE")
    print("="*60)
    print(f"\n📊 DMS Task: {task_arn}")
    
    return True

if __name__ == "__main__":
    if not os.getenv("AWS_REGION"):
        print("❌ Environment not loaded. Please run: source bin/oma_env_demo.sh")
        sys.exit(1)
    
    success = main()
    sys.exit(0 if success else 1)
