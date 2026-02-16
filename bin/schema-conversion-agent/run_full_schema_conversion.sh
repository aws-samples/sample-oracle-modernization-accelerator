#!/bin/bash
# Full Workflow with Strands Agent

set -e

echo "=========================================="
echo "Full Oracle to PostgreSQL Workflow"
echo "Using Strands Agents SDK"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if environment is loaded
if [ -z "$DMS_SC_S3_BUCKET" ]; then
    echo "❌ Environment not loaded. Please run: source bin/oma_env_demo.sh"
    exit 1
fi

# Set schema name
export DMS_SC_SCHEMA_NAME="${ORACLE_SVC_USER_LIST//\"/}"

cd "$SCRIPT_DIR"

# Step 1: Run DMS SC automation
echo ""
echo "Step 1: Running DMS SC automation..."
OUTPUT=$(python3.11 dms_sc_automation.py 2>&1)
echo "$OUTPUT"

# Extract S3 path from output
S3_PATH=$(echo "$OUTPUT" | grep "s3://${DMS_SC_S3_BUCKET}" | grep "\.zip" | tail -1 | awk '{print $NF}')

if [ -z "$S3_PATH" ]; then
    echo "❌ Failed to get S3 path from DMS SC output"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ DMS SC Project Created: $S3_PATH"
echo "=========================================="

# Step 2: Run Strands conversion agent
echo ""
echo "Step 2: Running Strands conversion agent..."
python3.11 -u schema_convert_agent.py "$S3_PATH"

echo ""
echo "=========================================="
echo "Step 3: Extracting PostgreSQL DDL..."
echo "=========================================="
python3.11 extract_pg_ddl.py "$S3_PATH"

echo ""
echo "=========================================="
echo "✅ WORKFLOW COMPLETE"
echo "=========================================="
echo ""
echo "📁 Results:"
echo "  - Agent output: /workshop/pg-ddl/"
echo "  - Extracted DDL: /tmp/oma-conversion/"
echo ""
