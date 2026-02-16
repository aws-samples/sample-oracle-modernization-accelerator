#!/usr/bin/env python3.11
"""
Database Assessment Agent
Runs DMS SC assessment, exports PDF/Excel, and generates HTML report using Bedrock
"""
import os
import sys
import boto3
import time
import json
import base64
from pathlib import Path
from datetime import datetime

# Configuration
REGION = os.getenv("AWS_REGION", "us-east-1")
OUTPUT_DIR = "/workshop/dms-sc-output"
DMS_SC_S3_BUCKET = os.getenv("DMS_SC_S3_BUCKET")
DMS_MIGRATION_PROJECT_ARN = os.getenv("DMS_MIGRATION_PROJECT_ARN")
DMS_SC_SCHEMA_NAME = os.getenv("ORACLE_SVC_USER_LIST", "DEMO").strip('"')

def get_migration_project_info(client, project_arn):
    """Get migration project information"""
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
    server_name = source_dp['Settings']['OracleSettings']['ServerName']
    
    return {
        'server_name': server_name,
        'schema_name': DMS_SC_SCHEMA_NAME
    }

def create_selection_rules(schema_name, server_name):
    """Create selection rules for assessment"""
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

def wait_for_completion(client, describe_func, project_arn, operation_name):
    """Wait for DMS SC operation to complete"""
    print(f"⏳ Waiting for {operation_name} to complete...")
    
    while True:
        response = describe_func(MigrationProjectIdentifier=project_arn)
        if not response.get('Requests'):
            time.sleep(5)
            continue
        
        latest_request = response['Requests'][0]
        status = latest_request['Status']
        print(f"   Status: {status}")
        
        if status == 'SUCCESS':
            print(f"   ✅ {operation_name} completed")
            return True
        elif status == 'FAILED':
            print(f"   ❌ {operation_name} failed")
            return False
        
        time.sleep(10)

def run_assessment_and_export(client, project_info, selection_rules):
    """Run assessment and export PDF/Excel"""
    filename = f"Assessment_Report_{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"
    
    # Step 1: Run Assessment
    print(f"\n🔍 Step 1: Starting assessment...")
    try:
        response = client.start_metadata_model_assessment(
            MigrationProjectIdentifier=DMS_MIGRATION_PROJECT_ARN,
            SelectionRules=json.dumps(selection_rules)
        )
        print(f"   Request ID: {response['RequestIdentifier']}")
        
        if not wait_for_completion(
            client,
            client.describe_metadata_model_assessments,
            DMS_MIGRATION_PROJECT_ARN,
            "Assessment"
        ):
            return None
    except Exception as e:
        print(f"   ❌ Assessment failed: {e}")
        return None
    
    # Step 2: Export PDF
    print(f"\n📄 Step 2: Exporting PDF report...")
    try:
        client.export_metadata_model_assessment(
            MigrationProjectIdentifier=DMS_MIGRATION_PROJECT_ARN,
            SelectionRules=json.dumps(selection_rules),
            FileName=filename,
            AssessmentReportTypes=['pdf']
        )
        print(f"   ✅ PDF export initiated")
    except Exception as e:
        print(f"   ⚠️  PDF export failed: {e}")
    
    # Step 3: Export CSV
    print(f"\n📊 Step 3: Exporting CSV report...")
    try:
        client.export_metadata_model_assessment(
            MigrationProjectIdentifier=DMS_MIGRATION_PROJECT_ARN,
            SelectionRules=json.dumps(selection_rules),
            FileName=filename,
            AssessmentReportTypes=['csv']
        )
        print(f"   ✅ CSV export initiated")
    except Exception as e:
        print(f"   ⚠️  CSV export failed: {e}")
    
    # Wait for exports
    print(f"\n⏳ Waiting for exports to complete (30 seconds)...")
    time.sleep(30)
    
    return filename

def download_reports(s3_client, filename):
    """Download PDF and CSV ZIP from S3"""
    print(f"\n📥 Step 4: Downloading reports from S3...")
    
    pdf_key = f"dms-sc-migration-project/{filename}.pdf"
    csv_key = f"dms-sc-migration-project/{filename}.zip"
    
    pdf_path = Path(OUTPUT_DIR) / f"{filename}.pdf"
    csv_zip_path = Path(OUTPUT_DIR) / f"{filename}.zip"
    
    try:
        s3_client.download_file(DMS_SC_S3_BUCKET, pdf_key, str(pdf_path))
        print(f"   ✅ Downloaded PDF")
    except Exception as e:
        print(f"   ⚠️  PDF download failed: {e}")
        pdf_path = None
    
    csv_files = []
    try:
        s3_client.download_file(DMS_SC_S3_BUCKET, csv_key, str(csv_zip_path))
        print(f"   ✅ Downloaded CSV ZIP")
        
        # Extract CSV files
        import zipfile
        csv_dir = Path(OUTPUT_DIR) / f"{filename}_csv"
        csv_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(csv_zip_path, 'r') as zip_ref:
            zip_ref.extractall(csv_dir)
            csv_files = list(csv_dir.glob("*.csv"))
            print(f"   ✅ Extracted {len(csv_files)} CSV files")
    except Exception as e:
        print(f"   ⚠️  CSV download/extract failed: {e}")
    
    return pdf_path, csv_files

def generate_html_report(pdf_path, csv_files):
    """Generate HTML report using Bedrock"""
    print(f"\n🤖 Step 5: Analyzing with Bedrock Claude...")
    
    if not pdf_path or not pdf_path.exists():
        print("   ❌ No PDF available for analysis")
        return None
    
    bedrock = boto3.client('bedrock-runtime', region_name=REGION)
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_content = base64.b64encode(f.read()).decode('utf-8')
    
    # Read CSV files
    csv_data = []
    for csv_file in csv_files[:3]:  # Limit to 3 CSV files
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                csv_data.append({
                    'filename': csv_file.name,
                    'content': f.read()[:5000]  # First 5000 chars
                })
        except Exception as e:
            print(f"   ⚠️  Failed to read {csv_file.name}: {e}")
    
    # Prepare content
    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_content
            }
        }
    ]
    
    # Add CSV data to prompt
    csv_text = "\n\n".join([f"CSV File: {c['filename']}\n{c['content']}" for c in csv_data])
    
    content.append({
        "type": "text",
        "text": f"""Analyze this DMS Schema Conversion assessment report (PDF and CSV data) and generate a comprehensive HTML Database Discovery Report.

CSV Data:
{csv_text}

Complexity Definitions:
- Simple: Less than 2 hours per object
- Medium: 2-6 hours per object  
- Significant/Complex: More than 6 hours per object

Include:
1. Executive Summary
   - Total objects analyzed
   - Complexity breakdown (Simple/Medium/Complex counts)
   - Estimated conversion effort in Man-Months (MM)
     * Calculate: (Simple × 2h + Medium × 4h + Complex × 8h) / 160h per MM
   - Key findings and recommendations

2. Schema Analysis (tables, views, procedures, functions, packages with counts)

3. Conversion Complexity
   - Objects by complexity level with counts
   - Estimated hours and MM per complexity
   - Top complex objects requiring manual review

4. Action Items (high/medium priority items)

5. Detailed Object List (table with: Object Name, Type, Schema, Complexity, Estimated Hours)

Generate complete HTML with modern CSS styling, responsive tables, color-coded complexity indicators.
Show MM calculations prominently in the Executive Summary.
Return ONLY the HTML code."""
    })
    
    # Call Bedrock
    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10000,
            "messages": [{
                "role": "user",
                "content": content
            }],
            "temperature": 0.3
        })
    )
    
    result = json.loads(response['body'].read())
    html_content = result['content'][0]['text']
    
    # Extract HTML
    if '```html' in html_content:
        html_content = html_content.split('```html')[1].split('```')[0].strip()
    elif '```' in html_content:
        html_content = html_content.split('```')[1].split('```')[0].strip()
    
    print("   ✅ Analysis complete")
    return html_content

def main():
    """Main workflow"""
    print("="*60)
    print("Database Assessment Agent")
    print("="*60)
    
    # Ensure output directory
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Initialize clients
    dms_client = boto3.client('dms', region_name=REGION)
    s3_client = boto3.client('s3', region_name=REGION)
    
    # Get project info
    print("\n📋 Getting migration project information...")
    project_info = get_migration_project_info(dms_client, DMS_MIGRATION_PROJECT_ARN)
    print(f"   Server: {project_info['server_name']}")
    print(f"   Schema: {project_info['schema_name']}")
    
    # Create selection rules
    selection_rules = create_selection_rules(
        project_info['schema_name'],
        project_info['server_name']
    )
    
    # Run assessment and export
    filename = run_assessment_and_export(dms_client, project_info, selection_rules)
    if not filename:
        return False
    
    # Download reports
    pdf_path, csv_files = download_reports(s3_client, filename)
    
    # Generate HTML report
    html_content = generate_html_report(pdf_path, csv_files)
    if not html_content:
        return False
    
    # Save report
    print(f"\n💾 Step 6: Saving HTML report...")
    report_path = Path(OUTPUT_DIR) / "database_analysis_report.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"   ✅ Report saved")
    
    print("\n" + "="*60)
    print("✅ ASSESSMENT COMPLETE")
    print("="*60)
    print(f"\n📄 Report: {report_path}")
    print(f"   Open: file://{report_path}")
    
    return True

if __name__ == "__main__":
    if not DMS_MIGRATION_PROJECT_ARN:
        print("❌ Environment not loaded. Please run: source bin/oma_env_demo.sh")
        sys.exit(1)
    
    success = main()
    sys.exit(0 if success else 1)
