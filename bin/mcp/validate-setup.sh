#!/bin/bash
# Validate OMA MCP Setup

set -e

ERRORS=0
WARNINGS=0

echo "🔍 Validating OMA MCP Setup"
echo "============================================================"
echo ""

# Check if environment variables are loaded
if [ -z "$APPLICATION_NAME" ] || [ -z "$ORACLE_HOST" ] || [ -z "$PGHOST" ]; then
  echo "❌ Environment variables not loaded"
  echo "Please run: source bin/oma_env_<project>.sh"
  ERRORS=$((ERRORS + 1))
else
  echo "✅ Environment variables loaded (project: $APPLICATION_NAME)"
fi

echo ""
echo "1️⃣  Checking Prerequisites..."
echo "------------------------------------------------------------"

# Java
if command -v java &> /dev/null; then
  JAVA_VERSION=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | cut -d'.' -f1)
  if [ "$JAVA_VERSION" -ge 21 ]; then
    echo "✅ Java $JAVA_VERSION installed"
  else
    echo "⚠️  Java $JAVA_VERSION found (Java 21+ recommended)"
    WARNINGS=$((WARNINGS + 1))
  fi
else
  echo "❌ Java not found"
  ERRORS=$((ERRORS + 1))
fi

# Maven
if command -v mvn &> /dev/null; then
  MVN_VERSION=$(mvn -version | head -1 | awk '{print $3}')
  echo "✅ Maven $MVN_VERSION installed"
else
  echo "❌ Maven not found"
  ERRORS=$((ERRORS + 1))
fi

# Python 3.11 or 3.9
if command -v python3.11 &> /dev/null; then
  PYTHON_CMD=python3.11
  PY_VERSION=$(python3.11 --version | awk '{print $2}')
  echo "✅ Python $PY_VERSION installed"
elif command -v python3 &> /dev/null; then
  PYTHON_CMD=python3
  PY_VERSION=$(python3 --version | awk '{print $2}')
  echo "✅ Python $PY_VERSION installed"
else
  echo "❌ Python not found"
  ERRORS=$((ERRORS + 1))
fi

# Install pip if missing
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
  echo "⚙️  Installing pip..."
  sudo yum install -y python3-pip &> /dev/null
  if $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "✅ pip installed"
  else
    echo "❌ Failed to install pip"
    ERRORS=$((ERRORS + 1))
  fi
fi

# AWS CLI
if command -v aws &> /dev/null; then
  AWS_VERSION=$(aws --version | awk '{print $1}' | cut -d'/' -f2)
  echo "✅ AWS CLI $AWS_VERSION installed"
else
  echo "❌ AWS CLI not found"
  ERRORS=$((ERRORS + 1))
fi

echo ""
echo "2️⃣  Checking Environment Variables..."
echo "------------------------------------------------------------"

# S3
if [ -n "$DMS_SC_S3_BUCKET" ]; then
  echo "✅ DMS_SC_S3_BUCKET set: $DMS_SC_S3_BUCKET"
else
  echo "❌ DMS_SC_S3_BUCKET not set"
  ERRORS=$((ERRORS + 1))
fi

# Database connections
if [ -n "$PG_CONNECTION_DETAIL" ]; then
  echo "✅ PG_CONNECTION_DETAIL set"
else
  echo "❌ PG_CONNECTION_DETAIL not set"
  ERRORS=$((ERRORS + 1))
fi

if [ -n "$ORACLE_CONNECTION_DETAIL" ]; then
  echo "✅ ORACLE_CONNECTION_DETAIL set"
else
  echo "⚠️  ORACLE_CONNECTION_DETAIL not set (optional)"
  WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "3️⃣  Checking AWS Access..."
echo "------------------------------------------------------------"

# S3 bucket access
if aws s3 ls "s3://$DMS_SC_S3_BUCKET" &> /dev/null; then
  echo "✅ S3 bucket accessible: $DMS_SC_S3_BUCKET"
else
  echo "❌ Cannot access S3 bucket: $DMS_SC_S3_BUCKET"
  ERRORS=$((ERRORS + 1))
fi

# Secrets Manager access (only if using secretsmanager connection type)
if [ -n "$PG_CONNECTION_DETAIL" ] && [[ "$PG_CONNECTION_DETAIL" == arn:aws:secretsmanager:* ]]; then
  if aws secretsmanager describe-secret --secret-id "$PG_CONNECTION_DETAIL" &> /dev/null; then
    echo "✅ PostgreSQL secret accessible"
  else
    echo "❌ Cannot access PostgreSQL secret"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "✅ Using direct database connection (not Secrets Manager)"
fi

# Bedrock access
if aws bedrock list-foundation-models --region us-east-1 &> /dev/null; then
  echo "✅ Bedrock accessible"
else
  echo "❌ Cannot access Bedrock"
  ERRORS=$((ERRORS + 1))
fi

echo ""
echo "4️⃣  Checking MCP Server Builds..."
echo "------------------------------------------------------------"

if [ -f "schema-conversion-mcp/target/oma-sc-mcp-server-1.0.0.jar" ]; then
  echo "✅ oma-sc-mcp built"
else
  echo "⚠️  oma-sc-mcp not built (run ./build-all.sh)"
  WARNINGS=$((WARNINGS + 1))
fi

if [ -f "pg-client-mcp/target/postgresql-mcp-server-1.0.0.jar" ]; then
  echo "✅ pg-client-mcp built"
else
  echo "⚠️  pg-client-mcp not built (run ./build-all.sh)"
  WARNINGS=$((WARNINGS + 1))
fi

if [ -f "oracle-client-mcp/target/oracle-mcp-server-1.0.0.jar" ]; then
  echo "✅ oracle-client-mcp built"
else
  echo "⚠️  oracle-client-mcp not built (run ./build-all.sh)"
  WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "5️⃣  Checking Python Dependencies..."
echo "------------------------------------------------------------"

if $PYTHON_CMD -c "import boto3, httpx" &> /dev/null; then
  echo "✅ Python dependencies installed"
else
  echo "⚙️  Installing basic Python dependencies..."
  $PYTHON_CMD -m pip install boto3 httpx --user --quiet 2>/dev/null
  if $PYTHON_CMD -c "import boto3, httpx" &> /dev/null; then
    echo "✅ Python dependencies installed"
  else
    echo "⚠️  Some Python dependencies missing (optional for MCP servers)"
    WARNINGS=$((WARNINGS + 1))
  fi
fi

echo ""
echo "============================================================"
echo "Validation Summary"
echo "============================================================"
echo "❌ Errors: $ERRORS"
echo "⚠️  Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
  echo "✅ Setup is ready!"
  echo ""
  echo "Next steps:"
  echo "  1. Build MCP servers: ./build-all.sh"
  echo "  2. Start servers: ./start-servers.sh"
  echo "  3. Run agent: cd ../oma-sc-agent && $PYTHON_CMD ora_to_pg_sc_agent.py s3://..."
  exit 0
else
  echo "❌ Please fix errors before proceeding"
  exit 1
fi
