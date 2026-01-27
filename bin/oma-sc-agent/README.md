# Oracle to PostgreSQL Conversion Agent

Automated schema conversion using AWS DMS Schema Conversion, Bedrock Claude 3.5, and MCP servers.

## Quick Start

```bash
# 1. Ensure MCP servers are running
cd /workshop/oma-mcp
./start-servers.sh

# 2. Run conversion
cd /workshop/oma-sc-agent
python3.11 ora_to_pg_sc_agent.py s3://BUCKET/dms-sc-migration-project/PROJECT.zip

# 3. Check results
ls -lh /workshop/pg-ddl/
cat /workshop/pg-ddl/CONVERSION_REPORT.md
```

## Architecture

```
Oracle to PostgreSQL Agent (Python 3.11)
    ↓ Single SSE Session
MCP Servers (localhost:9080-9082)
    ├─ oma-sc-mcp (9080) - DMS SC + Bedrock
    ├─ pg-client-mcp (9081) - PostgreSQL client
    └─ oracle-client-mcp (9082) - Oracle client
    ↓
AWS Services
    ├─ S3 (DMS SC projects)
    ├─ Secrets Manager (DB credentials)
    └─ Bedrock (Claude 3.5 Sonnet)
```

## Files

- `ora_to_pg_sc_agent.py` - Main conversion agent
- `requirements.txt` - Python dependencies (boto3, httpx, mcp)
- `setup.sh` - Quick prerequisite checker
- `AGENT_DESIGN.md` - Detailed design document
- `ARCHITECTURE.md` - System architecture

## Features

- ✅ Automated DMS SC project analysis
- ✅ Oracle DDL extraction (offline, no live DB)
- ✅ AI-powered PostgreSQL conversion (Bedrock Claude 3.5)
- ✅ Batch processing (15+ objects in 1-2 minutes)
- ✅ Automatic report generation
- ✅ Single SSE session (stable, no reconnections)

## Workflow

1. **Analyze**: Parse DMS SC project CSV files for Complex/Medium objects
2. **Extract**: Get Oracle DDL from offline cache
3. **Convert**: Use Bedrock Claude 3.5 to convert to PostgreSQL
4. **Save**: Write DDL files to `/workshop/pg-ddl/`
5. **Report**: Generate conversion summary report

See [AGENT_DESIGN.md](AGENT_DESIGN.md) for complete details.

## Output

### DDL Files
Location: `/workshop/pg-ddl/*.sql`

Each file contains:
- Object metadata (name, type, complexity)
- PostgreSQL-compatible DDL
- Ready for deployment

### Conversion Report
Location: `/workshop/pg-ddl/CONVERSION_REPORT.md`

Contains:
- Executive summary with statistics
- Success/failure rates
- Object-by-object details
- Next steps guide

## Requirements

- Python 3.11+
- MCP Python SDK (from GitHub)
- boto3, httpx
- Running MCP servers (ports 9080-9082)
- AWS credentials with S3, Secrets Manager, Bedrock access

## Setup

See `/workshop/oma-mcp/README.md` for complete setup instructions.

Quick setup:
```bash
cd /workshop/oma-mcp
./validate-setup.sh  # Auto-installs dependencies
./build-all.sh       # Build MCP servers
./start-servers.sh   # Start all 3 servers
```

## Example

```bash
$ python3.11 ora_to_pg_sc_agent.py s3://mma-dms-sc-147671602580/dms-sc-migration-project/ORACLE_AURORA_POSTGRESQL_2026-01-27T08-20-40.298Z.zip

============================================================
Oracle to PostgreSQL Schema Conversion Agent
============================================================

🔗 Opening MCP session...
✅ Session ready

🔍 Step 1: Analyzing project...
   Found 3 CSV files
   Found 17 complex/medium objects

📋 Processing 17 objects...

============================================================
Object 1/17: Schemas.DEMO.Packages.BOOK_PKG.Public procedures.GET_BOOK_DETAILS
============================================================
📝 Getting DDL...
   ✓ Got DDL (424 chars)
🔄 Converting to PostgreSQL...
   ✓ Converted (412 chars)
   💾 Saved to /workshop/pg-ddl/Schemas_DEMO_Packages_BOOK_PKG_Public_procedures_GET_BOOK_DETAILS.sql

...

============================================================
CONVERSION SUMMARY
============================================================
✅ Success: 15
❌ Failed: 0
⊘ Skipped: 2

📁 All DDL files saved to: /workshop/pg-ddl

📄 Report saved to: /workshop/pg-ddl/CONVERSION_REPORT.md
```

## Troubleshooting

### MCP Servers Not Running
```bash
cd /workshop/oma-mcp
./start-servers.sh
ps aux | grep "\.jar" | grep java
```

### Python Dependencies Missing
```bash
python3.11 -m pip install git+https://github.com/modelcontextprotocol/python-sdk.git --user
python3.11 -m pip install -r requirements.txt --user
```

### Bedrock Access Denied
Add IAM permission:
```bash
aws iam put-role-policy --role-name YOUR-ROLE --policy-name BedrockInvokeModel --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel"],
    "Resource": "arn:aws:bedrock:*:*:inference-profile/*"
  }]
}'
```

## Documentation

- [AGENT_DESIGN.md](AGENT_DESIGN.md) - Detailed design and workflow
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and components
- [/workshop/oma-mcp/README.md](../oma-mcp/README.md) - MCP servers documentation

## License

Proprietary - Oracle Migration Assistant
