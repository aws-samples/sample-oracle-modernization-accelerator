#!/usr/bin/env python3.11
"""
Oracle to PostgreSQL Conversion with Validation Swarm
Orchestrator pattern with parallel processing and validation
"""
import os
import asyncio
from pathlib import Path
from mcp.client.sse import sse_client
from strands.agent import Agent
from strands.tools.mcp import MCPClient

# Configuration
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent.parent.parent  # Go up to workshop level
OUTPUT_DIR = str(BASE_DIR / "target-database" / "pg-ddl")
DMS_SC_SCHEMA_NAME = os.getenv("DMS_SC_SCHEMA_NAME", "DEMO")


class ValidationSwarm:
    """Swarm of validators working together"""
    
    def __init__(self, pg_client, oracle_client):
        self.pg_client = pg_client
        self.oracle_client = oracle_client
        
        # Syntax Validator
        self.syntax_validator = Agent(
            tools=pg_client.list_tools_sync(),
            system_prompt="""You are a PostgreSQL syntax validator.
Check if the SQL is syntactically correct for PostgreSQL.
Test by executing in a transaction and rolling back.
Report any syntax errors."""
        )
        
        # Semantic Validator
        self.semantic_validator = Agent(
            tools=pg_client.list_tools_sync() + oracle_client.list_tools_sync(),
            system_prompt="""You are a semantic validator.
Compare Oracle and PostgreSQL behavior.
Check if the conversion preserves the original logic.
Report any semantic differences."""
        )
        
        # Performance Validator
        self.performance_validator = Agent(
            tools=pg_client.list_tools_sync(),
            system_prompt="""You are a performance validator.
Check for performance issues in PostgreSQL DDL.
Look for missing indexes, inefficient queries, etc.
Report any performance concerns."""
        )
        
        # Corrector
        self.corrector = Agent(
            tools=pg_client.list_tools_sync(),
            system_prompt="""You are a SQL corrector.
Fix issues found by validators.
Provide corrected SQL that passes all validations."""
        )
    
    async def validate_and_fix(self, object_name, sql):
        """Validate SQL with swarm and fix if needed"""
        print(f"  🔍 Validating {object_name}...")
        
        # Run validators in parallel
        validations = await asyncio.gather(
            self.syntax_validator.invoke_async(f"Validate syntax: {sql[:500]}..."),
            self.semantic_validator.invoke_async(f"Check semantics: {sql[:500]}..."),
            self.performance_validator.invoke_async(f"Check performance: {sql[:500]}..."),
            return_exceptions=True
        )
        
        # Check for issues
        has_issues = False
        issues = []
        for i, v in enumerate(validations):
            if isinstance(v, Exception):
                issues.append(f"Validator {i} error: {v}")
                has_issues = True
            elif "error" in str(v).lower() or "issue" in str(v).lower():
                issues.append(str(v))
                has_issues = True
        
        if has_issues:
            print(f"    ⚠️  Issues found, correcting...")
            try:
                corrected = await self.corrector.invoke_async(
                    f"Fix these issues in SQL:\nIssues: {issues}\nSQL: {sql}"
                )
                return {"status": "corrected", "sql": str(corrected), "issues": issues}
            except Exception as e:
                return {"status": "failed", "sql": sql, "issues": issues + [str(e)]}
        
        print(f"    ✅ Validation passed")
        return {"status": "valid", "sql": sql, "issues": []}


class ConvertStage:
    """Parallel conversion stage"""
    
    def __init__(self, oma_sc_client, s3_path):
        self.oma_sc_client = oma_sc_client
        self.s3_path = s3_path
        self.agent = Agent(
            tools=oma_sc_client.list_tools_sync(),
            system_prompt=f"""Extract and convert Oracle DDL to PostgreSQL.
Use oma_sc_get_offline_ddl to extract Oracle DDL.
Use oma_sc_convert_ddl_to_pg to convert to PostgreSQL.

IMPORTANT: The DMS SC project is at: {s3_path}
When calling tools, use s3Path parameter: "{s3_path}" """
        )
    
    async def convert_single(self, obj):
        """Convert single object"""
        try:
            # Provide full context to agent
            prompt = f"""Extract and convert Oracle object to PostgreSQL:

Object: {obj['objectName']}
Type: {obj['objectType']}
Schema: {obj['schemaName']}
Complexity: {obj['complexity']}

Steps:
1. Use oma_sc_get_offline_ddl with:
   - objectType: {obj['objectType']}
   - schemaName: {obj['schemaName']}
   - objectName: {obj['objectName']}
2. Use oma_sc_convert_ddl_to_pg to convert the DDL
3. Return the converted PostgreSQL DDL"""

            result = await self.agent.invoke_async(prompt)
            return {"object": obj, "status": "success", "result": result}
        except Exception as e:
            return {"object": obj, "status": "failed", "error": str(e)}
    
    async def run_parallel(self, objects, batch_size=3):
        """Convert objects in parallel batches"""
        print(f"\n🔄 Converting {len(objects)} objects in batches of {batch_size}...")
        results = []
        
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i+batch_size]
            print(f"\n  Batch {i//batch_size + 1}: {len(batch)} objects")
            
            # Parallel conversion within batch
            batch_results = await asyncio.gather(*[
                self.convert_single(obj) for obj in batch
            ], return_exceptions=True)
            
            results.extend(batch_results)
        
        return results


class SchemaConversionOrchestrator:
    """Main orchestrator for schema conversion"""
    
    def __init__(self):
        self.oma_sc_client = None
        self.pg_client = None
        self.oracle_client = None
        self.convert_stage = None
        self.validate_stage = None
    
    def setup_clients(self):
        """Setup MCP clients"""
        print("🔗 Setting up MCP clients...")
        
        self.oma_sc_client = MCPClient(
            lambda: sse_client("http://localhost:9080/sse"),
            prefix="oma_sc"
        )
        self.pg_client = MCPClient(
            lambda: sse_client("http://localhost:9081/sse"),
            prefix="pg"
        )
        self.oracle_client = MCPClient(
            lambda: sse_client("http://localhost:9082/sse"),
            prefix="oracle"
        )
        
        self.oma_sc_client.start()
        self.pg_client.start()
        self.oracle_client.start()
        
        print("✅ MCP clients ready")
    
    def setup_stages(self, s3_path):
        """Setup processing stages"""
        self.convert_stage = ConvertStage(self.oma_sc_client, s3_path)
        self.validate_stage = ValidationSwarm(self.pg_client, self.oracle_client)
    
    def parse_csv(self, s3_path):
        """Parse CSV to get Medium/Complex objects"""
        import csv
        import zipfile
        import tempfile
        import boto3
        
        print(f"\n📊 Parsing CSV from {s3_path}...")
        
        s3 = boto3.client('s3')
        bucket = s3_path.split('/')[2]
        key = '/'.join(s3_path.split('/')[3:])
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            s3.download_file(bucket, key, tmp.name)
            
            objects = []
            with zipfile.ZipFile(tmp.name, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith('.csv') and not ('Summary' in file or 'Action_Items' in file):
                        with zip_ref.open(file) as csv_file:
                            content = csv_file.read().decode('utf-8')
                            reader = csv.DictReader(content.splitlines())
                            
                            for row in reader:
                                complexity = row.get('Estimated complexity', '').strip()
                                if complexity in ['Complex', 'Medium']:
                                    obj_id = row.get('Occurrence', '').strip()
                                    object_name = obj_id.split('.')[-1] if '.' in obj_id else obj_id
                                    objects.append({
                                        "objectIdentifier": obj_id,
                                        "objectType": row.get('Category', '').strip(),
                                        "objectName": object_name,
                                        "schemaName": row.get('Schema name', DMS_SC_SCHEMA_NAME).strip(),
                                        "complexity": complexity
                                    })
            
            Path(tmp.name).unlink()
        
        print(f"✅ Found {len(objects)} Medium/Complex objects")
        return objects
    
    async def run(self, s3_path):
        """Run complete orchestration"""
        print("="*60)
        print("Schema Conversion Orchestrator")
        print("With Validation Swarm & Parallel Processing")
        print("="*60)
        
        # Ensure output directory
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        # Setup
        self.setup_clients()
        self.setup_stages(s3_path)
        
        # Stage 1: Parse CSV
        objects = self.parse_csv(s3_path)
        
        # Stage 2: Parallel Conversion
        converted = await self.convert_stage.run_parallel(objects, batch_size=3)
        
        # Stage 3: Validation Swarm
        print(f"\n🔍 Validating {len(converted)} converted objects...")
        validated = []
        for item in converted:
            if item.get("status") == "success":
                result = await self.validate_stage.validate_and_fix(
                    item["object"]["objectName"],
                    str(item["result"])
                )
                validated.append({
                    "object": item["object"],
                    "validation": result
                })
        
        # Stage 4: Save Results
        print(f"\n💾 Saving results to {OUTPUT_DIR}...")
        for item in validated:
            obj_name = item["object"]["objectName"]
            sql = item["validation"]["sql"]
            
            output_file = Path(OUTPUT_DIR) / f"{obj_name}.sql"
            with open(output_file, 'w') as f:
                f.write(f"-- Object: {obj_name}\n")
                f.write(f"-- Type: {item['object']['objectType']}\n")
                f.write(f"-- Complexity: {item['object']['complexity']}\n")
                f.write(f"-- Validation: {item['validation']['status']}\n\n")
                f.write(sql)
        
        # Summary
        print("\n" + "="*60)
        print("CONVERSION COMPLETE")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"  Total objects: {len(objects)}")
        print(f"  Converted: {len(converted)}")
        print(f"  Validated: {len(validated)}")
        print(f"  Valid: {len([v for v in validated if v['validation']['status'] == 'valid'])}")
        print(f"  Corrected: {len([v for v in validated if v['validation']['status'] == 'corrected'])}")
        print(f"  Failed: {len([v for v in validated if v['validation']['status'] == 'failed'])}")
        print(f"\n📁 Results: {OUTPUT_DIR}/")


def get_latest_conversion_zip():
    """Get latest DMS SC conversion zip from S3 (with CSV files)"""
    import boto3
    import zipfile
    import tempfile
    
    bucket = os.getenv("DMS_SC_S3_BUCKET")
    if not bucket:
        return None
    
    s3 = boto3.client('s3', region_name=os.getenv("AWS_REGION", "us-east-1"))
    
    try:
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix='dms-sc-migration-project/',
            MaxKeys=1000
        )
        
        if 'Contents' not in response:
            return None
        
        # Filter for .zip files and check if they contain CSV
        zip_files = [
            obj for obj in response['Contents']
            if obj['Key'].endswith('.zip')
        ]
        
        if not zip_files:
            return None
        
        # Find the latest zip that contains CSV files (not just SQL)
        for obj in sorted(zip_files, key=lambda x: x['LastModified'], reverse=True):
            try:
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                    s3.download_file(bucket, obj['Key'], tmp.name)
                    with zipfile.ZipFile(tmp.name, 'r') as zf:
                        csv_files = [f for f in zf.namelist() if f.endswith('.csv')]
                        if csv_files:
                            s3_path = f"s3://{bucket}/{obj['Key']}"
                            print(f"Found latest conversion with CSV: {s3_path}")
                            Path(tmp.name).unlink()
                            return s3_path
                    Path(tmp.name).unlink()
            except Exception as e:
                continue
        
        return None
        
    except Exception as e:
        print(f"Error finding conversion zip: {e}")
        return None


def main(s3_path):
    """Main entry point"""
    orchestrator = SchemaConversionOrchestrator()
    asyncio.run(orchestrator.run(s3_path))


if __name__ == "__main__":
    import sys
    import boto3
    
    # Load environment if not already loaded
    if not os.getenv("DMS_SC_S3_BUCKET"):
        import subprocess
        env_script = Path(__file__).parent.parent / "oma_env_demo.sh"
        if env_script.exists():
            print(f"Loading environment from {env_script}...")
            result = subprocess.run(
                f"source {env_script} && env",
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if '=' in line and not line.startswith('_'):
                        try:
                            key, value = line.split('=', 1)
                            os.environ[key] = value
                        except:
                            pass
    
    # Get S3 path from argument or auto-discover
    s3_path = None
    if len(sys.argv) >= 2:
        s3_path = sys.argv[1]
    else:
        s3_path = get_latest_conversion_zip()
    
    if not s3_path:
        print("Usage: python3.11 ora_to_pg_orchestrator.py <s3-path>")
        print("\nOr set DMS_SC_S3_BUCKET environment variable to auto-discover latest conversion")
        sys.exit(1)
    
    main(s3_path)
