#!/usr/bin/env python3.11
"""
Oracle to PostgreSQL Conversion Agent (Single Session Version)
Uses single MCP SSE session for all operations
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from mcp import ClientSession
from mcp.client.sse import sse_client
import csv

# Configuration
MCP_OMA_SC = "http://localhost:9080/sse"
MCP_POSTGRES = "http://localhost:9081/sse"
OUTPUT_DIR = "/workshop/pg-ddl"
DMS_SC_SCHEMA_NAME = os.getenv("DMS_SC_SCHEMA_NAME", "DEMO")

stats = {"success": 0, "failed": 0, "skipped": 0, "failed_objects": [], "objects": []}

async def call_tool(session, tool_name, params):
    """Call MCP tool and return text content"""
    result = await session.call_tool(tool_name, params)
    return result.content[0].text if result.content else None

async def process_conversion(session, s3_path):
    """Main conversion workflow using single session"""
    
    # Step 1: Analyze
    print(f"\n🔍 Step 1: Analyzing project...")
    result = await call_tool(session, "analyze_dms_sc_project", {"arg0": s3_path})
    data = json.loads(result)
    if not data.get("success"):
        raise Exception(f"Analysis failed: {data.get('error')}")
    
    local_base = data.get("local_base")
    csv_files = list(Path(local_base).rglob("*.csv"))
    print(f"   Found {len(csv_files)} CSV files")
    
    # Parse objects
    objects = []
    for csv_file in csv_files:
        if "_Summary" in str(csv_file):
            continue
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
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
    
    print(f"   Found {len(objects)} complex/medium objects\n")
    print(f"📋 Processing {len(objects)} objects...")
    
    # Process each object
    for idx, obj in enumerate(objects, 1):
        print(f"\n{'='*60}")
        print(f"Object {idx}/{len(objects)}: {obj['objectIdentifier']}")
        print(f"{'='*60}")
        
        try:
            # Step 2: Get DDL
            print(f"📝 Getting DDL...")
            ddl_result = await call_tool(session, "get_offline_ddl", {
                "arg0": s3_path,
                "arg1": "source",  # ddlType
                "arg2": obj['schemaName'],
                "arg3": "",  # objectType
                "arg4": obj['objectName']
            })
            ddl_data = json.loads(ddl_result)
            
            if not ddl_data.get('success') or not ddl_data.get('ddls'):
                print(f"   ⊘ DDL not found, skipping")
                stats["skipped"] += 1
                continue
            
            oracle_ddl = ddl_data['ddls'][0]['ddl']
            print(f"   ✓ Got DDL ({len(oracle_ddl)} chars)")
            
            # Step 3: Convert
            print(f"🔄 Converting to PostgreSQL...")
            conv_result = await call_tool(session, "convert_ddl_to_pg", {
                "arg0": oracle_ddl,
                "arg1": obj['objectType'],
                "arg2": obj['complexity']
            })
            conv_data = json.loads(conv_result)
            
            if not conv_data.get('success'):
                raise Exception(f"Conversion failed: {conv_data.get('error')}")
            
            pg_ddl = conv_data['postgresql_ddl']
            print(f"   ✓ Converted ({len(pg_ddl)} chars)")
            
            # Save
            safe_name = obj['objectIdentifier'].replace('.', '_').replace(' ', '_')
            ddl_file = f"{OUTPUT_DIR}/{safe_name}.sql"
            Path(ddl_file).write_text(
                f"-- {obj['objectIdentifier']}\n"
                f"-- Type: {obj['objectType']} | Complexity: {obj['complexity']}\n\n"
                f"{pg_ddl}"
            )
            print(f"   💾 Saved to {ddl_file}")
            
            stats["success"] += 1
            stats["objects"].append({
                "name": obj['objectIdentifier'],
                "type": obj['objectType'],
                "complexity": obj['complexity'],
                "status": "success",
                "file": f"{safe_name}.sql"
            })
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            stats["failed"] += 1
            stats["failed_objects"].append(f"{obj['objectIdentifier']} ({obj['objectType']})")
            stats["objects"].append({
                "name": obj['objectIdentifier'],
                "type": obj['objectType'],
                "complexity": obj['complexity'],
                "status": "failed",
                "error": str(e)
            })

async def generate_report(s3_path):
    """Generate conversion report"""
    from datetime import datetime
    
    report = f"""# Oracle to PostgreSQL Schema Conversion Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Source:** {s3_path}  
**Schema:** {DMS_SC_SCHEMA_NAME}  
**Tool:** Oracle to PostgreSQL Conversion Agent (MCP + Bedrock Claude 3.5)

---

## Executive Summary

Successfully converted **{stats['success']} out of {stats['success'] + stats['failed'] + stats['skipped']}** Oracle database objects to PostgreSQL-compatible DDL.

### Conversion Statistics

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Success | {stats['success']} | {stats['success']/(stats['success']+stats['failed']+stats['skipped'])*100:.1f}% |
| ❌ Failed | {stats['failed']} | {stats['failed']/(stats['success']+stats['failed']+stats['skipped'])*100:.1f}% |
| ⊘ Skipped | {stats['skipped']} | {stats['skipped']/(stats['success']+stats['failed']+stats['skipped'])*100:.1f}% |
| **Total** | **{stats['success']+stats['failed']+stats['skipped']}** | **100%** |

---

## Converted Objects

"""
    
    # Group by type
    by_type = {}
    for obj in stats['objects']:
        obj_type = obj['type']
        if obj_type not in by_type:
            by_type[obj_type] = []
        by_type[obj_type].append(obj)
    
    for obj_type, objs in by_type.items():
        report += f"\n### {obj_type} ({len(objs)} objects)\n\n"
        report += "| Object Name | Status | File |\n"
        report += "|-------------|--------|------|\n"
        for obj in objs:
            status = "✅" if obj['status'] == 'success' else "❌"
            file_name = obj.get('file', 'N/A')
            report += f"| {obj['name']} | {status} | {file_name} |\n"
    
    if stats['failed_objects']:
        report += "\n---\n\n## Failed Objects\n\n"
        for obj in stats['failed_objects']:
            report += f"- {obj}\n"
    
    report += f"""
---

## Technology Stack

- **Analysis Tool:** AWS DMS Schema Conversion
- **AI Model:** Amazon Bedrock Claude 3.5 Sonnet
- **MCP Servers:**
  - oma-sc-mcp (Port 9080) - DMS SC + Bedrock integration
  - pg-client-mcp (Port 9081) - PostgreSQL client
  - oracle-client-mcp (Port 9082) - Oracle client
- **Agent:** Python 3.11 with MCP SDK
- **Transport:** Server-Sent Events (SSE)

---

## Next Steps

1. **Review DDL Files** - Check all generated SQL files in this directory
2. **Test in PostgreSQL** - Execute DDL files in target database
3. **Validate Functionality** - Test each function/procedure with sample data
4. **Handle Dependencies** - Ensure objects are created in correct order

---

**Generated by:** Oracle to PostgreSQL Conversion Agent  
**Timestamp:** {datetime.now().isoformat()}
"""
    
    report_file = f"{OUTPUT_DIR}/CONVERSION_REPORT.md"
    Path(report_file).write_text(report)
    print(f"\n📄 Report saved to: {report_file}")

async def main(s3_path):
    print("="*60)
    print("Oracle to PostgreSQL Schema Conversion Agent")
    print("="*60)
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    print("\n🔗 Opening MCP session...")
    async with sse_client(MCP_OMA_SC) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Session ready")
            
            await process_conversion(session, s3_path)
    
    print("\n" + "="*60)
    print("CONVERSION SUMMARY")
    print("="*60)
    print(f"✅ Success: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"⊘ Skipped: {stats['skipped']}")
    
    if stats["failed_objects"]:
        print(f"\nFailed objects:")
        for obj in stats["failed_objects"]:
            print(f"  - {obj}")
    
    print(f"\n📁 All DDL files saved to: {OUTPUT_DIR}")
    
    # Generate report
    await generate_report(s3_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3.11 ora_to_pg_sc_agent.py <s3-path>")
        sys.exit(1)
    
    s3_path = sys.argv[1]
    asyncio.run(main(s3_path))
