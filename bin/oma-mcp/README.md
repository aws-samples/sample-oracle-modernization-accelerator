# OMA MCP Servers

Model Context Protocol (MCP) servers for Oracle to PostgreSQL migration using AWS DMS Schema Conversion and Bedrock.

## Overview

Three MCP servers that work together to automate Oracle to PostgreSQL schema conversion:

### 1. oma-sc-mcp (Port 9080)
**DMS Schema Conversion + Bedrock DDL Converter**

Tools:
- `analyze`: Analyze DMS SC project from S3
- `get_ddl`: Extract Oracle DDL for specific objects
- `convert`: Convert Oracle DDL to PostgreSQL using Bedrock Claude

### 2. pg-client-mcp (Port 9081)
**PostgreSQL Database Client**

Tools:
- `executeSql`: Execute SQL query on PostgreSQL
- `executeTestCase`: Execute test with rollback
- `executeTestCaseReadOnly`: Execute test in read-only mode

### 3. oracle-client-mcp (Port 9082)
**Oracle Database Client**

Tools:
- `executeSql`: Execute SQL query on Oracle
- `executeTestCase`: Execute test with rollback
- `executeTestCaseReadOnly`: Execute test in read-only mode

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Oracle to PostgreSQL Agent (Strands Framework)             │
│  • Python CSV parsing + LLM conversion                      │
│  • Async workflow: Parse → Filter → Convert → Save          │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ oma-sc-mcp   │   │ pg-client    │   │ oracle-client│
│ Port 9080    │   │ Port 9081    │   │ Port 9082    │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
            ┌──────────────┐  ┌──────────────┐
            │ AWS S3       │  │ Bedrock      │
            │ Secrets Mgr  │  │ Claude 3.5   │
            └──────────────┘  └──────────────┘
```

## Quick Start

### 1. Configure Environment

```bash
# Copy template and edit
cp env.sh.template env.sh
nano env.sh

# Required variables:
# - DMS_SC_S3_BUCKET: Your S3 bucket name
# - DMS_SC_SCHEMA_NAME: Schema to convert (e.g., DEMO)
# - PG_CONNECTION_DETAIL: PostgreSQL Secrets Manager ARN
# - ORACLE_CONNECTION_DETAIL: Oracle Secrets Manager ARN

# Load environment
source env.sh
```

### 2. Validate and Auto-Install

```bash
# Automatically checks and installs:
# - pip (if missing)
# - Python dependencies (boto3, httpx)
# - Verifies AWS access and database secrets
./validate-setup.sh
```

### 3. Build and Start Servers

```bash
# Build all 3 servers
./build-all.sh

# Start all servers
./start-servers.sh

# Verify
ps aux | grep "\.jar" | grep java
```

### 4. Run Agent

```bash
cd ../oma-sc-agent

# Convert schema
# Run Strands agent (recommended)
python3.11 ora_to_pg_strands_agent.py s3://YOUR-BUCKET/dms-sc-migration-project/YOUR-PROJECT.zip

# Or run original agent (fallback)
python3.11 ora_to_pg_sc_agent.py s3://YOUR-BUCKET/dms-sc-migration-project/YOUR-PROJECT.zip

# Check results
ls -lh /tmp/oma-conversion/
```

## Configuration

### Environment Variables (env.sh)

```bash
# DMS SC Configuration
export DMS_SC_S3_BUCKET="your-bucket-name"
export DMS_SC_SCHEMA_NAME="YOUR_SCHEMA"

# PostgreSQL (Secrets Manager)
export PG_CONNECTION_TYPE="secretsmanager"
export PG_CONNECTION_DETAIL="arn:aws:secretsmanager:region:account:secret:name"

# Oracle (Secrets Manager)
export ORACLE_CONNECTION_TYPE="secretsmanager"
export ORACLE_CONNECTION_DETAIL="arn:aws:secretsmanager:region:account:secret:name"
```

### Secrets Manager Format

**PostgreSQL:**
```json
{
  "username": "postgres",
  "password": "your-password",
  "host": "your-cluster.region.rds.amazonaws.com",
  "port": 5432,
  "dbname": "postgres"
}
```

**Oracle:**
```json
{
  "username": "admin",
  "password": "your-password",
  "host": "your-instance.region.rds.amazonaws.com",
  "port": 1521,
  "dbname": "ORCL"
}
```

## Technical Details

### Stack
- Java 21 (Amazon Corretto)
- Spring Boot 3.5.5
- Spring AI MCP 2.0.0-M2
- MCP Protocol (SSE transport)
- Spring WebFlux (reactive)
- AWS SDK (S3, Secrets Manager, Bedrock)
- Python 3.11 + Strands Agents SDK 1.23.0
- MCP SDK 1.11.0

### Security
- No authentication (localhost only)
- Database credentials via AWS Secrets Manager
- IAM role-based AWS access

### Performance
- Processing: ~18 objects in 2-3 minutes
- Hybrid approach: Python parsing + LLM conversion
- Parallel DDL extraction (5 workers)
- Async workflow with error handling

## Project Structure

```
oma-mcp/
├── oma-sc-mcp/              # DMS SC + Bedrock tools
│   ├── src/main/java/com/example/
│   │   ├── OmaScMcpServerApplication.java
│   │   ├── OmaScMcpTools.java
│   │   └── DatabaseConfig.java
│   └── pom.xml
├── pg-client-mcp/           # PostgreSQL client
├── oracle-client-mcp/       # Oracle client
├── build-all.sh             # Build all servers
├── start-servers.sh         # Start all servers
├── validate-setup.sh        # Validate and auto-install
└── env.sh.template          # Environment template
```

## Troubleshooting

### Servers Not Starting

```bash
# Check logs
tail -f /tmp/oma-sc.log
tail -f /tmp/pg-client.log
tail -f /tmp/oracle-client.log

# Check ports
lsof -i :9080
lsof -i :9081
lsof -i :9082
```

### Database Connection Issues

```bash
# Test secrets access
aws secretsmanager get-secret-value --secret-id YOUR-SECRET-ARN

# Test connectivity
telnet your-db-host 5432  # PostgreSQL
telnet your-db-host 1521  # Oracle
```

### Python Dependencies

```bash
# Re-run validation (auto-installs)
./validate-setup.sh

# Or install manually
python3 -m pip install -r ../oma-sc-agent/requirements.txt --user
```

## Documentation

- **README.md** - This file (overview)
- **QUICK_START.md** - Quick deployment guide
- **env.sh.template** - Environment configuration template
- **../oma-sc-agent/AGENT_DESIGN.md** - Agent design details

## License

Proprietary - Oracle Migration Assistant
