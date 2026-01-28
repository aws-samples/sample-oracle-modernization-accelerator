#!/bin/bash
# Setup and run Oracle to PostgreSQL Conversion Agent

set -e

echo "============================================"
echo "Oracle to PostgreSQL Conversion Agent Setup"
echo "============================================"

# Load environment variables
if [ -f "/workshop/oma-mcp/env.sh" ]; then
    echo ""
    echo "Loading environment variables from env.sh..."
    source /workshop/oma-mcp/env.sh
    echo "✅ Environment loaded"
    echo "   S3 Bucket: $DMS_SC_S3_BUCKET"
    echo "   Schema: $DMS_SC_SCHEMA_NAME"
else
    echo "⚠️  env.sh not found. Using default values."
fi

# 1. Check prerequisites
echo ""
echo "1. Checking prerequisites..."

if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Please install Python 3.11+"
    echo "   sudo yum install -y python3.11 python3.11-pip"
    exit 1
fi

if ! command -v java &> /dev/null; then
    echo "❌ Java not found. Please install Java 21+"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI"
    exit 1
fi

echo "✅ Prerequisites OK"

# 2. Install Python dependencies
echo ""
echo "2. Installing Python dependencies..."
# Install MCP SDK from GitHub for Python 3.10+ requirement
python3.11 -m pip install -q git+https://github.com/modelcontextprotocol/python-sdk.git --user
# Install Strands Agents SDK
python3.11 -m pip install -q strands-agents --user
# Install other dependencies
python3.11 -m pip install -q -r requirements.txt --user
echo "✅ Dependencies installed (including Strands Agents SDK)"

# 3. Check MCP servers
echo ""
echo "3. Checking MCP servers..."

if ! curl -s http://localhost:9080/health &> /dev/null; then
    echo "⚠️  oma-sc-mcp not running on port 9080"
    echo "   Start with: cd /workshop/oma-mcp/oma-sc-mcp && java -jar target/oma-sc-mcp-server-1.0.0.jar &"
fi

if ! curl -s http://localhost:9081/health &> /dev/null; then
    echo "⚠️  pg-client-mcp not running on port 9081"
    echo "   Start with: cd /workshop/oma-mcp/pg-client-mcp && java -jar target/postgresql-mcp-server-1.0.0.jar &"
fi

# 4. Test OAuth
echo ""
echo "4. Testing OAuth connection..."
TOKEN=$(curl -s -X POST https://agentcore-8e9e317c.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=5p5b2k57kq43tmodn9otpm451s&client_secret=uo5ge7vlk2350kehra92196lrh20p1aiutki9flsfrltccji4lb&scope=oma-mcp/mcp.access" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo "❌ Failed to get OAuth token"
    exit 1
fi
echo "✅ OAuth token obtained"

# 5. Test Bedrock access
echo ""
echo "5. Testing Bedrock access..."
if ! aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId' --output text &> /dev/null; then
    echo "❌ Cannot access Bedrock. Check AWS credentials and permissions"
    exit 1
fi
echo "✅ Bedrock access OK"

echo ""
echo "============================================"
echo "✅ Setup complete!"
echo "============================================"
echo ""
echo "Environment:"
echo "  S3 Bucket: ${DMS_SC_S3_BUCKET:-mma-dms-sc-940597661534}"
echo "  Schema: ${DMS_SC_SCHEMA_NAME:-DEMO}"
echo ""
echo "Usage:"
echo "  python3.11 ora_to_pg_sc_agent.py <s3_path>"
echo ""
echo "Example:"
echo "  python3.11 ora_to_pg_sc_agent.py s3://${DMS_SC_S3_BUCKET:-mma-dms-sc-940597661534}/dms-sc-migration-project/PROJECT.zip"
echo ""
