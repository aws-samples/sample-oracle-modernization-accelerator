#!/bin/bash
# Setup and run Oracle to PostgreSQL Conversion Agent

set -e

echo "============================================"
echo "Oracle to PostgreSQL Conversion Agent Setup"
echo "============================================"

# Check if environment variables are already loaded
if [ -z "$DMS_SC_S3_BUCKET" ]; then
    echo "❌ Environment variables not loaded"
    echo "Please run: source bin/oma_env_demo.sh"
    exit 1
fi

# Use DMS_SC_SCHEMA_NAME if set, otherwise derive from ORACLE_SVC_USER_LIST
if [ -z "$DMS_SC_SCHEMA_NAME" ]; then
    export DMS_SC_SCHEMA_NAME="${ORACLE_SVC_USER_LIST//\"/}"
fi

echo "✅ Environment loaded"
echo "   S3 Bucket: $DMS_SC_S3_BUCKET"
echo "   Schema: $DMS_SC_SCHEMA_NAME"

# 1. Check prerequisites
echo ""
echo "1. Checking prerequisites..."

# Check for Python 3.10+
PYTHON_CMD=""
for py_version in python3.11 python3.10; do
    if command -v $py_version &> /dev/null; then
        PYTHON_CMD=$py_version
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "⚠️  Python 3.10+ not found. Installing Python 3.11..."
    sudo yum install -y python3.11 python3.11-pip &> /dev/null
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
        echo "✅ Python 3.11 installed"
    else
        echo "❌ Failed to install Python 3.11"
        exit 1
    fi
else
    echo "✅ $PYTHON_CMD found"
fi

if ! command -v java &> /dev/null; then
    echo "❌ Java not found"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found"
    exit 1
fi

echo "✅ Prerequisites OK ($PYTHON_CMD, Java, AWS CLI)"

# 2. Install Python dependencies
echo ""
echo "2. Installing Python dependencies..."
$PYTHON_CMD -m pip install -q --upgrade pip --user 2>/dev/null
$PYTHON_CMD -m pip install -q git+https://github.com/modelcontextprotocol/python-sdk.git --user 2>/dev/null || echo "⚠️  MCP SDK already installed or failed"
$PYTHON_CMD -m pip install -q strands-agents --user 2>/dev/null || echo "⚠️  strands-agents installation failed"
$PYTHON_CMD -m pip install -q boto3 httpx --user 2>/dev/null || echo "⚠️  boto3/httpx already installed or failed"

# Verify strands-agents installation
if $PYTHON_CMD -c "import strands" &> /dev/null; then
    echo "✅ Dependencies installed (including strands-agents)"
else
    echo "❌ strands-agents installation failed. Python 3.10+ is required."
    exit 1
fi

# 3. Check MCP servers
echo ""
echo "3. Checking MCP servers..."

MCP_OK=true
if ! ps aux | grep -q "[j]ava.*oma-sc-mcp-server"; then
    echo "⚠️  oma-sc-mcp not running"
    MCP_OK=false
fi

if ! ps aux | grep -q "[j]ava.*postgresql-mcp-server"; then
    echo "⚠️  pg-client-mcp not running"
    MCP_OK=false
fi

if ! ps aux | grep -q "[j]ava.*oracle-mcp-server"; then
    echo "⚠️  oracle-client-mcp not running"
    MCP_OK=false
fi

if [ "$MCP_OK" = true ]; then
    echo "✅ All MCP servers running"
else
    echo ""
    echo "Start MCP servers with:"
    echo "  cd bin/mcp && ./start-servers.sh"
fi

# 4. Test Bedrock access
echo ""
echo "4. Testing Bedrock access..."
if aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId' --output text &> /dev/null; then
    echo "✅ Bedrock access OK"
else
    echo "⚠️  Cannot access Bedrock. Check AWS credentials and permissions"
fi

echo ""
echo "============================================"
echo "✅ Setup complete!"
echo "============================================"
echo ""
echo "Environment:"
echo "  S3 Bucket: $DMS_SC_S3_BUCKET"
echo "  Schema: $DMS_SC_SCHEMA_NAME"
echo ""
echo "Usage:"
echo "  $PYTHON_CMD schema_convert_agent.py <s3_path>"
echo ""
echo "Example:"
echo "  $PYTHON_CMD schema_convert_agent.py s3://$DMS_SC_S3_BUCKET/dms-sc-migration-project/PROJECT.zip"
echo ""
