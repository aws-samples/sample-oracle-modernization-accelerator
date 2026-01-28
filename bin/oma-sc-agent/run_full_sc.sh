#!/bin/bash
# Full Workflow with Strands Agent

set -e

echo "=========================================="
echo "Full Oracle to PostgreSQL Workflow"
echo "Using Strands Agents SDK"
echo "=========================================="

# Load environment
source /workshop/oma-mcp/env.sh

cd /workshop/oma-sc-agent

# Step 1: Run DMS SC automation
echo ""
echo "Step 1: Running DMS SC automation..."
OUTPUT=$(python3.11 dms_sc_automation.py 2>&1)
echo "$OUTPUT"

# Extract S3 path from output
S3_PATH=$(echo "$OUTPUT" | grep "s3://mma-dms-sc" | grep "\.zip" | tail -1 | awk '{print $NF}')

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
python3.11 -u ora_to_pg_sc_agent.py "$S3_PATH"

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
