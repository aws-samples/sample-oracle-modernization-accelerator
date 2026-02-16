#!/usr/bin/env python3.11
"""
DMS Schema Conversion Automation
Converts Oracle to PostgreSQL using DMS SC CLI, then exports results for agent processing
"""
import asyncio
import json
import sys
import os
import time
import boto3
from pathlib import Path
from datetime import datetime

# Configuration
REGION = os.getenv("AWS_REGION", "us-east-1")
OUTPUT_DIR = "/workshop/dms-sc-output"

def get_migration_project_arn():
    """Get migration project ARN from environment or parameter"""
    return os.getenv("DMS_MIGRATION_PROJECT_ARN")

def get_migration_project_info(client, project_arn):
    """Get migration project and data provider information"""
    response = client.describe_migration_projects(
        Filters=[{
            'Name': 'migration-project-arn',
            'Values': [project_arn]
        }]
    )
    
    project = response['MigrationProjects'][0]
    
    # Get source data provider
    source_dp_arn = project['SourceDataProviderDescriptors'][0]['DataProviderArn']
    response = client.describe_data_providers(
        Filters=[{
            'Name': 'data-provider-arn',
            'Values': [source_dp_arn]
        }]
    )
    
    source_dp = response['DataProviders'][0]
    oracle_settings = source_dp['Settings']['OracleSettings']
    
    # Get target data provider
    target_dp_arn = project['TargetDataProviderDescriptors'][0]['DataProviderArn']
    response = client.describe_data_providers(
        Filters=[{
            'Name': 'data-provider-arn',
            'Values': [target_dp_arn]
        }]
    )
    
    target_dp = response['DataProviders'][0]
    pg_settings = target_dp['Settings']['PostgreSqlSettings']
    
    return {
        'server_name': oracle_settings['ServerName'],
        'database_name': oracle_settings['DatabaseName'],
        'target_server_name': pg_settings['ServerName'],
        's3_bucket': project['SchemaConversionApplicationAttributes']['S3BucketPath'],
        'project_name': project['MigrationProjectName']
    }

def create_selection_rules(schema_name, server_name, database_name):
    """Create source selection rules"""
    return {
        "rules": [{
            "rule-id": "1",
            "rule-name": "1",
            "rule-action": "explicit",
            "rule-type": "selection",
            "object-locator": {
                "full-path": f'Servers."{server_name}".Schemas.{schema_name}'
            }
        }]
    }

def wait_for_completion(client, describe_func, project_arn, operation_name, request_id=None):
    """Wait for DMS SC operation to complete"""
    print(f"⏳ Waiting for {operation_name} to complete...")
    
    while True:
        response = describe_func(MigrationProjectIdentifier=project_arn)
        if not response.get('Requests'):
            print(f"   ❌ No requests found")
            return False
        
        # Find the specific request if request_id provided
        if request_id:
            request = None
            for req in response['Requests']:
                if req['RequestIdentifier'] == request_id:
                    request = req
                    break
            if not request:
                print(f"   ❌ Request {request_id} not found")
                return False
            status = request['Status']
        else:
            status = response['Requests'][0]['Status']
        
        print(f"   Status: {status}")
        
        if status == 'SUCCESS':
            print(f"   ✅ {operation_name} completed")
            return True
        elif status in ['FAILED', 'CANCELLED']:
            print(f"   ❌ {operation_name} failed: {status}")
            return False
        
        time.sleep(10)

def generate_dms_sc_report(zip_file, output_dir):
    """Generate DMS SC conversion report from CSV files"""
    import zipfile
    import csv
    import tempfile
    from collections import defaultdict
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract ZIP
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
        
        # Find main CSV file
        csv_files = list(Path(tmpdir).rglob("*.csv"))
        main_csv = None
        for csv_file in csv_files:
            if not ('Summary' in csv_file.name or 'Action_Items' in csv_file.name):
                main_csv = csv_file
                break
        
        if not main_csv:
            print(f"   ⚠️  No main CSV file found")
            return
        
        # Parse CSV
        objects = {}
        storage_objects = defaultdict(lambda: {'auto': 0, 'simple': 0, 'medium': 0, 'complex': 0})
        code_objects = defaultdict(lambda: {'auto': 0, 'simple': 0, 'medium': 0, 'complex': 0})
        
        with open(main_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                obj_type = row.get('Category', 'Unknown')
                obj_name = row.get('Occurrence', 'Unknown')
                complexity = row.get('Estimated complexity', 'Simple').strip()
                
                # Track unique objects
                if obj_name not in objects:
                    objects[obj_name] = {
                        'type': obj_type,
                        'complexity': 'Auto',
                        'issues': []
                    }
                
                objects[obj_name]['issues'].append(complexity)
                
                # Determine object complexity (highest complexity wins)
                if complexity == 'Complex':
                    objects[obj_name]['complexity'] = 'Complex'
                elif complexity == 'Medium' and objects[obj_name]['complexity'] not in ['Complex']:
                    objects[obj_name]['complexity'] = 'Medium'
                elif complexity == 'Simple' and objects[obj_name]['complexity'] == 'Auto':
                    objects[obj_name]['complexity'] = 'Simple'
        
        # Categorize objects
        storage_types = ['table', 'index', 'constraint', 'Schema']
        code_types = ['function', 'procedure', 'Package', 'Trigger']
        
        total_storage = 0
        total_code = 0
        agent_candidates = []
        
        for obj_name, obj_info in objects.items():
            obj_type = obj_info['type']
            complexity = obj_info['complexity']
            
            # Determine if storage or code
            is_storage = any(st in obj_type for st in storage_types)
            is_code = any(ct in obj_type for ct in code_types)
            
            if is_storage:
                total_storage += 1
                storage_objects[obj_type][complexity.lower()] += 1
            elif is_code:
                total_code += 1
                code_objects[obj_type][complexity.lower()] += 1
                
                if complexity in ['Medium', 'Complex']:
                    agent_candidates.append({
                        'name': obj_name,
                        'type': obj_type,
                        'complexity': complexity,
                        'issues': len(obj_info['issues'])
                    })
        
        # Calculate statistics
        storage_auto = sum(v['auto'] for v in storage_objects.values())
        storage_simple = sum(v['simple'] for v in storage_objects.values())
        storage_medium = sum(v['medium'] for v in storage_objects.values())
        storage_complex = sum(v['complex'] for v in storage_objects.values())
        storage_convertible = storage_auto + storage_simple
        
        code_auto = sum(v['auto'] for v in code_objects.values())
        code_simple = sum(v['simple'] for v in code_objects.values())
        code_medium = sum(v['medium'] for v in code_objects.values())
        code_complex = sum(v['complex'] for v in code_objects.values())
        code_convertible = code_auto + code_simple
        code_ai_candidates = code_medium + code_complex
        
        # Generate report
        report = f"""# DMS Schema Conversion Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

Of the total **{total_storage} database storage object(s)** and **{total_code} database code object(s)** in the source database, we identified:

- **{storage_convertible} ({(storage_convertible/total_storage*100) if total_storage > 0 else 0:.0f}%)** database storage object(s) can be converted automatically or with minimal changes
- **{code_convertible} ({(code_convertible/total_code*100) if total_code > 0 else 0:.0f}%)** database code object(s) can be converted automatically or with minimal changes

**{storage_medium + storage_complex} ({((storage_medium + storage_complex)/total_storage*100) if total_storage > 0 else 0:.0f}%)** database storage object(s) require {storage_medium} medium and {storage_complex} complex user action(s) to complete the conversion.

**{code_medium + code_complex} ({((code_medium + code_complex)/total_code*100) if total_code > 0 else 0:.0f}%)** database code object(s) require {code_medium} medium and {code_complex} complex user action(s) to complete the conversion.

**{code_ai_candidates} ({(code_ai_candidates/total_code*100) if total_code > 0 else 0:.0f}%)** database code object(s) may be candidates for conversion using generative AI.

---

## Conversion Statistics for Database Storage Objects

| Object Type | Total | Auto | Simple | Medium | Complex |
|-------------|-------|------|--------|--------|---------|
"""
        
        for obj_type, stats in sorted(storage_objects.items()):
            total = sum(stats.values())
            report += f"| {obj_type} | {total} | {stats['auto']} | {stats['simple']} | {stats['medium']} | {stats['complex']} |\n"
        
        report += f"""
**Total Storage Objects**: {total_storage}
- ✅ Automatically converted or simple: {storage_convertible} ({(storage_convertible/total_storage*100) if total_storage > 0 else 0:.0f}%)
- ⚠️  Medium complexity: {storage_medium} ({(storage_medium/total_storage*100) if total_storage > 0 else 0:.0f}%)
- ❌ Complex: {storage_complex} ({(storage_complex/total_storage*100) if total_storage > 0 else 0:.0f}%)

---

## Conversion Statistics for Database Code Objects

| Object Type | Total | Auto | Simple | Medium | Complex |
|-------------|-------|------|--------|--------|---------|
"""
        
        for obj_type, stats in sorted(code_objects.items()):
            total = sum(stats.values())
            report += f"| {obj_type} | {total} | {stats['auto']} | {stats['simple']} | {stats['medium']} | {stats['complex']} |\n"
        
        report += f"""
**Total Code Objects**: {total_code}
- ✅ Automatically converted or simple: {code_convertible} ({(code_convertible/total_code*100) if total_code > 0 else 0:.0f}%)
- ⚠️  Medium complexity: {code_medium} ({(code_medium/total_code*100) if total_code > 0 else 0:.0f}%)
- ❌ Complex: {code_complex} ({(code_complex/total_code*100) if total_code > 0 else 0:.0f}%)
- 🤖 AI Conversion Candidates: {code_ai_candidates} ({(code_ai_candidates/total_code*100) if total_code > 0 else 0:.0f}%)

---

## AI Conversion Candidates ({len(agent_candidates)} objects)

These objects have Medium or Complex complexity and will be converted by the agent using Bedrock Claude 3.5:

"""
        
        for obj in sorted(agent_candidates, key=lambda x: (x['complexity'], x['type'], x['name'])):
            report += f"- **{obj['name']}** ({obj['type']}) - {obj['complexity']} ({obj['issues']} action items)\n"
        
        report += f"""
---

## Next Steps

1. ✅ **DMS SC Applied**: {storage_convertible} storage objects and {code_convertible} code objects have been applied to the target database
2. 🔄 **Agent Conversion**: Run the agent to convert {len(agent_candidates)} medium/complex objects:
   ```bash
   python3.11 ora_to_pg_sc_agent.py <s3-path-to-csv-zip>
   ```
3. 📋 **Review**: Check the agent conversion report in `/workshop/pg-ddl/CONVERSION_REPORT.md`
"""
        
        # Save report
        report_file = f"{output_dir}/DMS_SC_REPORT.md"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        Path(report_file).write_text(report)
        print(f"   ✅ Report saved: {report_file}")


def main(migration_project_arn, schema_name):
    """Main workflow"""
    print("="*60)
    print("DMS Schema Conversion Automation")
    print("="*60)
    
    client = boto3.client('dms', region_name=REGION)
    s3_client = boto3.client('s3', region_name=REGION)
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Get project information
    print(f"\n📋 Getting migration project information...")
    project_info = get_migration_project_info(client, migration_project_arn)
    print(f"   Source: {project_info['server_name']}")
    print(f"   Target: {project_info['target_server_name']}")
    print(f"   Schema: {schema_name}")
    
    # Create selection rules
    selection_rules = create_selection_rules(
        schema_name,
        project_info['server_name'],
        project_info['database_name']
    )
    rules_file = f"{OUTPUT_DIR}/selection_rules.json"
    Path(rules_file).write_text(json.dumps(selection_rules, indent=2))
    print(f"   Selection rules: {rules_file}")
    
    # CSV filename for tracking
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    
    # Step 1: Assessment
    print(f"\n🔍 Step 1: Starting assessment...")
    try:
        response = client.start_metadata_model_assessment(
            MigrationProjectIdentifier=migration_project_arn,
            SelectionRules=json.dumps(selection_rules)
        )
        print(f"   Request ID: {response['RequestIdentifier']}")
        
        if not wait_for_completion(
            client,
            client.describe_metadata_model_assessments,
            migration_project_arn,
            "Assessment"
        ):
            return False
    except Exception as e:
        print(f"   ❌ Assessment failed: {e}")
        return False
    
    # Step 2: Export Assessment Report (CSV)
    print(f"\n📊 Step 2: Exporting assessment report (CSV)...")
    csv_filename = f"ORACLE_AURORA_POSTGRESQL_{datetime.now().strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3]}Z"
    try:
        # Use source server and schema for CSV export
        source_server = project_info['server_name']
        export_rules = {
            "rules": [{
                "rule-id": "1",
                "rule-name": "1",
                "rule-action": "explicit",
                "rule-type": "selection",
                "object-locator": {
                    "full-path": f'Servers."{source_server}".Schemas.{schema_name}'
                }
            }]
        }
        
        response = client.export_metadata_model_assessment(
            MigrationProjectIdentifier=migration_project_arn,
            SelectionRules=json.dumps(export_rules),
            FileName=csv_filename,
            AssessmentReportTypes=['csv']
        )
        print(f"   ✅ CSV export initiated: {csv_filename}")
    except Exception as e:
        print(f"   ❌ CSV export failed: {e}")
        return False
    
    # Step 3: Conversion
    print(f"\n🔄 Step 3: Starting conversion...")
    try:
        response = client.start_metadata_model_conversion(
            MigrationProjectIdentifier=migration_project_arn,
            SelectionRules=json.dumps(selection_rules)
        )
        print(f"   Request ID: {response['RequestIdentifier']}")
        
        if not wait_for_completion(
            client,
            client.describe_metadata_model_conversions,
            migration_project_arn,
            "Conversion"
        ):
            return False
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        return False
    
    # Step 4: Export Converted SQL (before Apply)
    print(f"\n💾 Step 4: Exporting converted SQL...")
    try:
        # Create target selection rules with full-path format
        target_server = project_info['target_server_name']
        target_rules = {
            "rules": [{
                "rule-id": "1",
                "rule-name": "1",
                "rule-action": "explicit",
                "rule-type": "selection",
                "object-locator": {
                    "full-path": f'Servers."{target_server}".Schemas.{schema_name.lower()}'
                }
            }]
        }
        
        response = client.start_metadata_model_export_as_script(
            MigrationProjectIdentifier=migration_project_arn,
            SelectionRules=json.dumps(target_rules),
            Origin='TARGET'
        )
        request_id = response['RequestIdentifier']
        print(f"   Request ID: {request_id}")
        
        if not wait_for_completion(
            client,
            client.describe_metadata_model_exports_as_script,
            migration_project_arn,
            "Export SQL",
            request_id
        ):
            print(f"   ⚠️  Export SQL failed, continuing...")
        else:
            # Download Export SQL ZIP to pg-ddl
            print(f"   📥 Downloading Export SQL to /workshop/pg-ddl...")
            response = client.describe_metadata_model_exports_as_script(
                MigrationProjectIdentifier=migration_project_arn,
                Filters=[{'Name': 'request-id', 'Values': [request_id]}]
            )
            if response['Requests'] and response['Requests'][0].get('ExportSqlDetails'):
                from urllib.parse import unquote
                s3_url = response['Requests'][0]['ExportSqlDetails']['S3ObjectKey']
                # Extract bucket and key from s3:// URL
                s3_url = s3_url.replace('s3://', '')
                parts = s3_url.split('/', 1)
                bucket = parts[0]
                key = unquote(parts[1]) if len(parts) > 1 else ''
                
                local_sql_zip = f"/workshop/pg-ddl/converted_sql_{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
                Path("/workshop/pg-ddl").mkdir(parents=True, exist_ok=True)
                s3_client.download_file(bucket, key, local_sql_zip)
                print(f"   ✅ Export SQL saved: {local_sql_zip}")
    except Exception as e:
        print(f"   ⚠️  Export SQL failed: {e}")
    
    # Step 5: Apply to Target
    print(f"\n🚀 Step 5: Applying to target database...")
    try:
        response = client.start_metadata_model_export_to_target(
            MigrationProjectIdentifier=migration_project_arn,
            SelectionRules=json.dumps(target_rules),
            OverwriteExtensionPack=True
        )
        print(f"   Request ID: {response['RequestIdentifier']}")
        
        if not wait_for_completion(
            client,
            client.describe_metadata_model_exports_to_target,
            migration_project_arn,
            "Apply to Target"
        ):
            return False
    except Exception as e:
        print(f"   ❌ Apply failed: {e}")
        return False
    
    # Step 6: Wait and download CSV ZIP from S3
    print(f"\n📦 Step 6: Retrieving CSV ZIP from S3...")
    try:
        bucket_name = project_info['s3_bucket']
        project_name = project_info['project_name']
        
        print(f"   S3 Bucket: {bucket_name}")
        print(f"   Project: {project_name}")
        print(f"   Looking for CSV export...")
        
        # Wait for CSV export to complete and upload to S3
        max_wait = 60  # 60 seconds
        wait_interval = 5
        zip_key = None
        
        for i in range(0, max_wait, wait_interval):
            if i > 0:
                print(f"   Waiting for CSV ZIP... ({i}s)")
                time.sleep(wait_interval)
            
            # List files in S3
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=f"{project_name}/"
            )
            
            if 'Contents' in response:
                # Look for the CSV ZIP file (ORACLE_AURORA_POSTGRESQL_*.zip format)
                for obj in response['Contents']:
                    if obj['Key'].endswith('.zip') and 'ORACLE_AURORA_POSTGRESQL' in obj['Key']:
                        # Check if it's recent (within last 2 minutes)
                        age = (datetime.now(obj['LastModified'].tzinfo) - obj['LastModified']).total_seconds()
                        if age < 120:
                            zip_key = obj['Key']
                            break
            
            if zip_key:
                break
        
        if not zip_key:
            print(f"   ❌ CSV ZIP file not found after {max_wait}s")
            return False
        
        # Download ZIP
        local_zip = f"{OUTPUT_DIR}/{Path(zip_key).name}"
        
        print(f"   📥 Downloading: {zip_key}")
        s3_client.download_file(bucket_name, zip_key, local_zip)
        print(f"   ✅ Downloaded to: {local_zip}")
        
        # Create S3 path for agent
        s3_url = f"s3://{bucket_name}/{zip_key}"
        
        # Step 7: Generate DMS SC Report
        print(f"\n📊 Step 7: Generating DMS SC report...")
        generate_dms_sc_report(local_zip, "/workshop/pg-ddl")
        
        print(f"\n{'='*60}")
        print(f"✅ DMS Schema Conversion Complete!")
        print(f"{'='*60}")
        print(f"\n📁 Results:")
        print(f"   Local: {local_zip}")
        print(f"   S3: {s3_url}")
        print(f"   Report: /workshop/pg-ddl/DMS_SC_REPORT.md")
        print(f"\n🤖 Use with agent:")
        print(f"   python3.11 ora_to_pg_sc_agent.py {s3_url}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to retrieve results: {e}")
        return False

if __name__ == "__main__":
    # Get from environment variables or command line
    migration_project_arn = os.getenv("DMS_MIGRATION_PROJECT_ARN")
    schema_name = os.getenv("DMS_SC_SCHEMA_NAME")
    
    # Override with command line if provided
    if len(sys.argv) >= 3:
        migration_project_arn = sys.argv[1]
        schema_name = sys.argv[2]
    
    if not migration_project_arn or not schema_name:
        print("Usage: python3.11 dms_sc_automation.py [migration-project-arn] [schema-name]")
        print("\nOr set environment variables:")
        print("  export DMS_MIGRATION_PROJECT_ARN=arn:aws:dms:...")
        print("  export DMS_SC_SCHEMA_NAME=DEMO")
        print("  python3.11 dms_sc_automation.py")
        sys.exit(1)
    
    success = main(migration_project_arn, schema_name)
    sys.exit(0 if success else 1)
