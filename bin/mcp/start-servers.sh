#!/bin/bash
# Start MCP servers as background services

# Check if environment variables are loaded
if [ -z "$APPLICATION_NAME" ] || [ -z "$ORACLE_HOST" ] || [ -z "$PGHOST" ]; then
  echo "❌ Environment variables not loaded."
  echo "Please run: source bin/oma_env_<project>.sh"
  exit 1
fi

echo "✅ Using environment from project: $APPLICATION_NAME"

# Derive MCP connection details from oma.properties variables
export PG_CONNECTION_TYPE="password"
export ORACLE_CONNECTION_TYPE="password"
export PG_CONNECTION_DETAIL="${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}"
export ORACLE_CONNECTION_DETAIL="${ORACLE_ADM_USER}:${ORACLE_ADM_PASSWORD}@${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}"

# Set default S3 path for oma-sc-mcp (use latest DMS SC project if available)
if [ -n "$DMS_SC_S3_BUCKET" ]; then
    export OMA_SC_DEFAULT_S3PATH="s3://${DMS_SC_S3_BUCKET}/dms-sc-migration-project/"
fi

# Kill existing
pkill -f "oma-sc-mcp-server" 2>/dev/null
pkill -f "postgresql-mcp-server" 2>/dev/null
pkill -f "oracle-mcp-server" 2>/dev/null
sleep 2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start oma-sc-mcp
cd "${SCRIPT_DIR}/schema-conversion-mcp"
nohup java -jar target/oma-sc-mcp-server-1.0.0.jar \
  > /tmp/oma-sc.log 2>&1 </dev/null &
echo "Started oma-sc-mcp (PID: $!)"

# Start pg-client-mcp
cd "${SCRIPT_DIR}/pg-client-mcp"
nohup java -jar target/postgresql-mcp-server-1.0.0.jar \
  > /tmp/pg-client.log 2>&1 </dev/null &
echo "Started pg-client-mcp (PID: $!)"

# Start oracle-client-mcp
cd "${SCRIPT_DIR}/oracle-client-mcp"
nohup java -jar target/oracle-mcp-server-1.0.0.jar \
  > /tmp/oracle-client.log 2>&1 </dev/null &
echo "Started oracle-client-mcp (PID: $!)"

sleep 8

# Verify
echo ""
echo "Running servers:"
ps aux | grep "\.jar" | grep -E "(oma-sc|postgresql|oracle)" | grep -v grep

echo ""
echo "Logs:"
echo "  oma-sc-mcp: tail -f /tmp/oma-sc.log"
echo "  pg-client-mcp: tail -f /tmp/pg-client.log"
echo "  oracle-client-mcp: tail -f /tmp/oracle-client.log"
