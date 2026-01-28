#!/usr/bin/env python3.11
"""
Oracle to PostgreSQL Conversion Agent - Strands Framework Version
Uses AWS Strands Agents SDK with MCP 1.11.0 + SSE
"""
import os
from pathlib import Path
from mcp.client.sse import sse_client
from strands import Agent
from strands.tools.mcp import MCPClient

# Configuration
OUTPUT_DIR = "/workshop/pg-ddl"
DMS_SC_SCHEMA_NAME = os.getenv("DMS_SC_SCHEMA_NAME", "DEMO")

def create_mcp_clients():
    """Create MCP clients for all three servers using SSE"""
    
    # OMA SC MCP (SSE transport)
    oma_sc_client = MCPClient(
        lambda: sse_client("http://localhost:9080/sse"),
        prefix="oma_sc"
    )
    
    # PostgreSQL client (SSE transport)
    pg_client = MCPClient(
        lambda: sse_client("http://localhost:9081/sse"),
        prefix="pg"
    )
    
    # Oracle client (SSE transport)
    oracle_client = MCPClient(
        lambda: sse_client("http://localhost:9082/sse"),
        prefix="oracle"
    )
    
    return oma_sc_client, pg_client, oracle_client

def parse_csv_for_medium_complex(s3_path):
    """Parse DMS SC CSV to extract Medium/Complex objects"""
    import csv
    import zipfile
    import tempfile
    import boto3
    from pathlib import Path
    
    # Download and extract CSV
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
    
    return objects

def main(s3_path):
    """Main conversion using Strands Agent"""
    
    print("="*60)
    print("Oracle to PostgreSQL Conversion (Strands Framework)")
    print("="*60)
    
    # Ensure output directory exists
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Step 1: Analyze and parse CSV to get Medium/Complex objects
    print("\n📊 Step 1: Parsing CSV to filter Medium/Complex objects...")
    
    try:
        objects = parse_csv_for_medium_complex(s3_path)
        medium_complex = [obj for obj in objects if obj['complexity'] in ['Medium', 'Complex']]
        
        print(f"✅ Found {len(medium_complex)} Medium/Complex objects (filtered from {len(objects)} total)")
        print(f"   Medium: {len([o for o in medium_complex if o['complexity'] == 'Medium'])}")
        print(f"   Complex: {len([o for o in medium_complex if o['complexity'] == 'Complex'])}")
    except Exception as e:
        print(f"⚠️  CSV parsing failed: {e}")
        print("   Falling back to agent-driven discovery...")
        medium_complex = []
    
    # Step 2: Create MCP clients and Strands agent
    print("\n🔗 Step 2: Connecting to MCP servers...")
    oma_sc_client, pg_client, oracle_client = create_mcp_clients()
    
    # Create Strands agent with all MCP tools
    with oma_sc_client, pg_client, oracle_client:
        print("✅ MCP clients connected")
        
        # Get all tools from MCP servers
        tools = (
            oma_sc_client.list_tools_sync() +
            pg_client.list_tools_sync() +
            oracle_client.list_tools_sync()
        )
        
        print(f"📦 Loaded {len(tools)} tools from MCP servers")
        
        # Create object list for agent
        if medium_complex:
            object_list = "\n".join([
                f"- {obj['objectName']} ({obj['objectType']}, {obj['complexity']})"
                for obj in medium_complex[:20]  # Show first 20
            ])
            more_text = f"\n... and {len(medium_complex) - 20} more" if len(medium_complex) > 20 else ""
            
            prompt = f"""You are an expert Oracle to PostgreSQL migration assistant.

Your task is to convert the following pre-filtered Medium/Complex objects from Oracle to PostgreSQL.

## Objects to Convert (already filtered by Python):
{object_list}{more_text}

## Available Tools:
- oma_sc_get_offline_ddl: Extract Oracle DDL from DMS SC project
- oma_sc_convert_ddl_to_pg: Convert Oracle DDL to PostgreSQL using Bedrock

## Workflow:
1. For each object in the list above:
   - Extract Oracle DDL using oma_sc_get_offline_ddl
   - Convert to PostgreSQL using oma_sc_convert_ddl_to_pg
2. Skip DR$ tables (Oracle Text internals)
3. Generate a summary report

Schema: {DMS_SC_SCHEMA_NAME}
S3 Path: {s3_path}
Output: {OUTPUT_DIR}

Begin converting the {len(medium_complex)} pre-filtered objects."""
        else:
            prompt = f"""You are an expert Oracle to PostgreSQL migration assistant.

Analyze the DMS SC project and convert Medium/Complex objects only.

S3 Path: {s3_path}
Schema: {DMS_SC_SCHEMA_NAME}
Output: {OUTPUT_DIR}

Begin the conversion process."""
        
        # Create agent with specific object list
        agent = Agent(tools=tools, system_prompt=prompt)
        
        # Run the agent
        count_text = f"{len(medium_complex)} pre-filtered" if medium_complex else "Medium/Complex"
        print(f"\n🤖 Step 3: Converting {count_text} objects with Strands agent...\n")
        import asyncio
        result = asyncio.run(agent.invoke_async(
            f"Convert the {count_text} objects to PostgreSQL"
        ))
        
        print("\n" + "="*60)
        print("CONVERSION COMPLETE")
        print("="*60)
        print(f"\n📁 Results saved to: {OUTPUT_DIR}")
        print(f"\n{result}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3.11 ora_to_pg_strands_agent.py <s3-path>")
        print("\nExample:")
        print("  python3.11 ora_to_pg_strands_agent.py s3://bucket/project.zip")
        sys.exit(1)
    
    s3_path = sys.argv[1]
    main(s3_path)
