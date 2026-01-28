# Quick Start Guide

## Prerequisites

- Java 21+
- Maven 3.6+
- Python 3.9+ (with pip)
- AWS CLI v2
- AWS credentials configured

## Quick Setup

### 1. Extract and Configure

```bash
# Extract archive
tar -xzf oma-no-auth-YYYYMMDD-HHMMSS.tar.gz
cd oma-mcp

# Configure environment
cp env.sh.template env.sh
nano env.sh  # Update with your values

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
# This will automatically:
# - Check prerequisites
# - Install pip if missing
# - Install Python dependencies (boto3, httpx)
# - Verify AWS access
./validate-setup.sh
```

### 3. Build and Start

```bash
# Build all MCP servers
./build-all.sh

# Start all servers
./start-servers.sh

# Verify servers are running
ps aux | grep "\.jar" | grep java
```

### 4. Run Agent

```bash
cd ../oma-sc-agent

# Test conversion
python3 ora_to_pg_sc_agent.py s3://YOUR-BUCKET/dms-sc-migration-project/YOUR-PROJECT.zip

# Check results
ls -lh /tmp/oma-conversion/
```

## What Gets Created

- ✅ 3 MCP servers running on localhost:
  - **oma-sc-mcp** (port 9080): DMS Schema Conversion + Bedrock
  - **pg-client-mcp** (port 9081): PostgreSQL client
  - **oracle-client-mcp** (port 9082): Oracle client
- ✅ No authentication required (localhost only)
- ✅ Direct database connections via Secrets Manager

## Configuration

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

## Troubleshooting

**Servers not starting:**
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

**Database connection fails:**
```bash
# Verify secrets
aws secretsmanager get-secret-value --secret-id YOUR-SECRET-ARN

# Test connectivity
telnet your-db-host 5432  # PostgreSQL
telnet your-db-host 1521  # Oracle
```

**Python dependencies missing:**
```bash
# Re-run validation (auto-installs)
./validate-setup.sh

# Or install manually
python3 -m pip install -r ../oma-sc-agent/requirements.txt --user
```

## Clean Up

```bash
# Stop servers
pkill -f "oma-sc-mcp-server"
pkill -f "postgresql-mcp-server"
pkill -f "oracle-mcp-server"

# Clean build artifacts
cd oma-mcp
mvn clean
```
