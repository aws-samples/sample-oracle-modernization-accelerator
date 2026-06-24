#!/usr/bin/env bash
# name: verify-env
# description: Verify Oracle and Aurora database connectivity and environment setup
# usage: verify-env

set -euo pipefail

# Load environment variables
if [ -f tools/load_oma_env.sh ]; then
    set -a
    source tools/load_oma_env.sh
    set +a
else
    exit 1
fi

echo "=== Oracle to Aurora Migration - Environment Verification ==="
echo ""

# Function to print section headers
print_section() {
    echo "-------------------------------------------"
    echo "$1"
    echo "-------------------------------------------"
}

# Function to print results
print_result() {
    if [ "$1" -eq 0 ]; then
        echo "✓ $2"
    else
        echo "✗ $2"
    fi
}

# Auto-detect Python 3.11
print_section "1. Python Environment Detection"

PYTHON_BIN=""
for cmd in python3.11 python3 python; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)

        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_BIN=$cmd
            print_result 0 "Found Python $VERSION at: $(command -v $cmd)"
            export PYTHON_BIN
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    print_result 1 "Python 3.11+ not found"
    MISSING_VARS=1
else
    echo "  Using: $PYTHON_BIN"
fi

echo ""

# Check required environment variables
print_section "2. Checking Environment Variables"
MISSING_VARS=0

check_var() {
    if [ -z "${!1:-}" ]; then
        echo "✗ $1 is not set"
        MISSING_VARS=1
    else
        echo "✓ $1=${!1}"
    fi
}

check_var "ORACLE_HOME"
check_var "ORACLE_HOST"
check_var "ORACLE_PORT"
check_var "ORACLE_USER"
check_var "ORACLE_PASSWORD"
check_var "ORACLE_SCHEMA"
check_var "SOURCE_WORKSPACE"
check_var "TARGET_WORKSPACE"
check_var "MAPPER_WORK_DIR"
check_var "TARGET_DB_TYPE"

if [ "$TARGET_DB_TYPE" = "postgres" ]; then
    check_var "PGHOST"
    check_var "PGPORT"
    check_var "PGDATABASE"
    check_var "PGUSER"
    check_var "PGPASSWORD"
elif [ "$TARGET_DB_TYPE" = "mysql" ]; then
    check_var "MYSQL_HOST"
    check_var "MYSQL_PORT"
    check_var "MYSQL_DATABASE"
    check_var "MYSQL_USER"
    check_var "MYSQL_PASSWORD"
fi

echo ""

# Check Oracle environment
print_section "3. Oracle Environment Check"

# Check ORACLE_HOME
if [ -d "$ORACLE_HOME" ]; then
    print_result 0 "ORACLE_HOME directory exists: $ORACLE_HOME"
else
    print_result 1 "ORACLE_HOME directory not found: $ORACLE_HOME"
    MISSING_VARS=1
fi

# Check sqlplus
if [ -x "$ORACLE_HOME/bin/sqlplus" ]; then
    SQLPLUS_PATH="$ORACLE_HOME/bin/sqlplus"
elif [ -x "$ORACLE_HOME/sqlplus" ]; then
    SQLPLUS_PATH="$ORACLE_HOME/sqlplus"
else
    SQLPLUS_PATH=""
fi

if [ -n "$SQLPLUS_PATH" ]; then
    print_result 0 "sqlplus found at: $SQLPLUS_PATH"
    SQLPLUS_VERSION=$($SQLPLUS_PATH -version 2>&1 | head -n 1)
    echo "  Version: $SQLPLUS_VERSION"
else
    print_result 1 "sqlplus not found in ORACLE_HOME"
    MISSING_VARS=1
fi

# Check tnsnames.ora
TNSNAMES_PATH="$ORACLE_HOME/network/admin/tnsnames.ora"
if [ -f "$TNSNAMES_PATH" ]; then
    print_result 0 "tnsnames.ora found at: $TNSNAMES_PATH"
else
    echo "⚠ tnsnames.ora not found at: $TNSNAMES_PATH (will use direct connection)"
fi

echo ""

# Check target database client
print_section "4. Target Database Client Check"

if [ "$TARGET_DB_TYPE" = "postgres" ]; then
    if command -v psql &> /dev/null; then
        print_result 0 "psql client found"
        PSQL_VERSION=$(psql --version)
        echo "  Version: $PSQL_VERSION"
    else
        print_result 1 "psql client not found"
        MISSING_VARS=1
    fi
elif [ "$TARGET_DB_TYPE" = "mysql" ]; then
    if command -v mysql &> /dev/null; then
        print_result 0 "mysql client found"
        MYSQL_VERSION=$(mysql --version)
        echo "  Version: $MYSQL_VERSION"
    else
        print_result 1 "mysql client not found"
        MISSING_VARS=1
    fi
fi

echo ""

# Test Oracle connectivity
print_section "5. Oracle Database Connectivity Test"

if [ "$ORACLE_CONN_TYPE" = "service" ]; then
    ORACLE_CONN_STRING="${ORACLE_USER}/${ORACLE_PASSWORD}@//${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}"
else
    ORACLE_CONN_STRING="${ORACLE_USER}/${ORACLE_PASSWORD}@${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}"
fi

ORACLE_TEST=$(cat <<'EOF'
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT 'CONNECTED' FROM DUAL;
EXIT;
EOF
)

if echo "$ORACLE_TEST" | $SQLPLUS_PATH -S "$ORACLE_CONN_STRING" 2>&1 | grep -q "CONNECTED"; then
    print_result 0 "Oracle connection successful"

    # Get Oracle version
    ORACLE_VERSION=$(cat <<'EOF'
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1;
EXIT;
EOF
)
    VERSION_INFO=$(echo "$ORACLE_VERSION" | $SQLPLUS_PATH -S "$ORACLE_CONN_STRING" 2>&1 | grep -v "^$")
    echo "  Version: $VERSION_INFO"

    # Check schema
    SCHEMA_CHECK=$(cat <<EOF
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT 'SCHEMA_EXISTS' FROM DBA_USERS WHERE USERNAME = '${ORACLE_SCHEMA}';
EXIT;
EOF
)
    if echo "$SCHEMA_CHECK" | $SQLPLUS_PATH -S "$ORACLE_CONN_STRING" 2>&1 | grep -q "SCHEMA_EXISTS"; then
        print_result 0 "Oracle schema '${ORACLE_SCHEMA}' exists"
    else
        print_result 1 "Oracle schema '${ORACLE_SCHEMA}' not found"
    fi
else
    print_result 1 "Oracle connection failed"
    echo "  Connection string: ${ORACLE_USER}@//${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}"
    MISSING_VARS=1
fi

echo ""

# Test target database connectivity
print_section "6. Target Database Connectivity Test"

if [ "$TARGET_DB_TYPE" = "postgres" ]; then
    # PGPASSWORD is already set, psql will use standard PG* variables automatically
    if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "SELECT 'CONNECTED';" &> /dev/null; then
        print_result 0 "PostgreSQL connection successful"

        # Get PostgreSQL version
        PG_VERSION=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -c "SELECT version();" 2>&1 | head -n 1 | xargs)
        echo "  Version: $PG_VERSION"

        # Check schema
        SCHEMA_EXISTS=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -c "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = '${PGSCHEMA}';" 2>&1 | xargs)
        if [ "$SCHEMA_EXISTS" = "1" ]; then
            print_result 0 "PostgreSQL schema '${PGSCHEMA}' exists"
        else
            print_result 1 "PostgreSQL schema '${PGSCHEMA}' not found"
        fi
    else
        print_result 1 "PostgreSQL connection failed"
        echo "  Connection: ${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}"
        MISSING_VARS=1
    fi

elif [ "$TARGET_DB_TYPE" = "mysql" ]; then
    if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 'CONNECTED';" &> /dev/null; then
        print_result 0 "MySQL connection successful"

        # Get MySQL version
        MYSQL_VERSION=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT VERSION();" 2>&1 | tail -n 1)
        echo "  Version: $MYSQL_VERSION"

        # Check database
        DB_EXISTS=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '${MYSQL_DATABASE}';" 2>&1 | tail -n 1)
        if [ "$DB_EXISTS" = "1" ]; then
            print_result 0 "MySQL database '${MYSQL_DATABASE}' exists"
        else
            print_result 1 "MySQL database '${MYSQL_DATABASE}' not found"
        fi
    else
        print_result 1 "MySQL connection failed"
        echo "  Connection: ${MYSQL_USER}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}"
        MISSING_VARS=1
    fi
fi

echo ""

# Check source workspace and detect projects
print_section "7. Source Workspace & Project Detection"

if [ -d "$SOURCE_WORKSPACE" ]; then
    print_result 0 "Source workspace exists: $SOURCE_WORKSPACE"

    # Detect projects
    PROJECTS=($(ls -1 "$SOURCE_WORKSPACE" 2>/dev/null | grep -v "^\." || true))
    PROJECT_COUNT=${#PROJECTS[@]}

    if [ $PROJECT_COUNT -gt 0 ]; then
        echo "  Detected projects: $PROJECT_COUNT"
        for project in "${PROJECTS[@]}"; do
            echo "    - $project"
        done
    else
        echo "  ⚠ No projects found in workspace"
    fi
else
    print_result 1 "Source workspace not found: $SOURCE_WORKSPACE"
    MISSING_VARS=1
fi

echo ""

# Initialize mapper directory structure
print_section "8. Mapper Directory Structure"

if [ -n "${MAPPER_WORK_DIR:-}" ]; then
    if [ -d "$MAPPER_WORK_DIR" ]; then
        print_result 0 "Mapper work directory exists: $MAPPER_WORK_DIR"
    else
        echo "⚠ Mapper work directory not found, creating: $MAPPER_WORK_DIR"
        mkdir -p "$MAPPER_WORK_DIR"
    fi

    # Create project-based structure
    if [ $PROJECT_COUNT -gt 0 ]; then
        echo "  Initializing project structure..."
        for project in "${PROJECTS[@]}"; do
            mkdir -p "$MAPPER_WORK_DIR/$project"/{original,source,target}
            if [ -d "$MAPPER_WORK_DIR/$project/original" ]; then
                echo "    ✓ $project/ (original, source, target)"
            fi
        done
        print_result 0 "Project structure initialized for $PROJECT_COUNT projects"
    fi
fi

echo ""

# Test Bedrock connectivity
print_section "9. Bedrock LLM Connection Test"

check_var "BEDROCK_REGION"
check_var "BEDROCK_MODEL_ID"

# Test using Python boto3
if ! ${PYTHON_BIN:-python3} -c "import boto3" 2>/dev/null; then
    print_result 1 "boto3 not installed (pip install boto3)"
    MISSING_VARS=1
else
    BEDROCK_TEST=$(${PYTHON_BIN:-python3} << 'PYEOF'
import sys
import json
import boto3

try:
    client = boto3.client('bedrock-runtime', region_name='${BEDROCK_REGION}')

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "test"}]
    })

    response = client.invoke_model(
        modelId='${BEDROCK_MODEL_ID}',
        body=body
    )

    result = json.loads(response['body'].read())
    if 'content' in result:
        print("SUCCESS")
    else:
        print(f"ERROR: {result}")
        sys.exit(1)

except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
PYEOF
)

    if echo "$BEDROCK_TEST" | grep -q "SUCCESS"; then
        print_result 0 "Bedrock model access successful"
        echo "  Model: ${BEDROCK_MODEL_ID}"
        echo "  Region: ${BEDROCK_REGION}"
    else
        print_result 1 "Bedrock model access failed"
        echo "  $BEDROCK_TEST"
        MISSING_VARS=1
    fi
fi

echo ""

# Scan for Extension variables
print_section "10. Extension Variable Detection"

if [ -d "$SOURCE_WORKSPACE" ]; then
    # Find mapper XML files in source workspace
    MAPPER_FILES=$(find "$SOURCE_WORKSPACE" -name "*.xml" -path "*/mapper/*" 2>/dev/null | wc -l)

    if [ $MAPPER_FILES -gt 0 ]; then
        echo "Found $MAPPER_FILES mapper files in source workspace"
        echo "Scanning for Extension variables..."
        echo ""

        # Run Extension scanner
        if ${PYTHON_BIN:-python3} tools/scan_extension_variables.py "$SOURCE_WORKSPACE" extensions/extension.json 2>&1; then
            print_result 0 "Extension scan completed"
        else
            print_result 1 "Extension scan failed"
        fi
    else
        echo "⚠ No mapper XML files found in source workspace"
        echo "  Extension scan will be skipped"

        # Create disabled extension config
        if [ ! -f extensions/extension.json ]; then
            mkdir -p extensions
            cat > extensions/extension.json <<'EOF'
{
  "enabled": false,
  "variables": {}
}
EOF
            echo "  Created disabled extension.json"
        fi
    fi
else
    echo "⚠ Source workspace not found, skipping Extension scan"
fi

echo ""

# Scan for OGNL expressions
print_section "11. OGNL Expression Detection"

if [ -d "$SOURCE_WORKSPACE" ] && [ $MAPPER_FILES -gt 0 ]; then
    echo "Scanning for OGNL expressions (@Class@method patterns)..."
    echo ""

    # Run OGNL scanner with guide-only mode
    OGNL_OUTPUT=$(${PYTHON_BIN:-python3} tools/scan_ognl.py \
        --source-dir "$SOURCE_WORKSPACE" \
        --output-dir lib/ognl_handlers \
        --guide-only 2>&1)

    OGNL_EXIT=$?

    if [ $OGNL_EXIT -eq 0 ]; then
        # Check if any OGNL expressions were found
        if echo "$OGNL_OUTPUT" | grep -q "No OGNL expressions found"; then
            print_result 0 "No OGNL expressions found - OGNL handlers not needed"
        else
            print_result 0 "OGNL implementation guide generated"

            # Count OGNL classes if report exists
            if [ -f lib/ognl_handlers/ognl_scan_report.json ]; then
                OGNL_CLASSES=$(grep -o '"classes":' lib/ognl_handlers/ognl_scan_report.json | wc -l)
                if [ $OGNL_CLASSES -gt 0 ]; then
                    echo "  → Found OGNL expressions requiring implementation"
                    echo "  → Implementation guide: docs/OGNL_IMPLEMENTATION_GUIDE.md"
                fi
            fi
        fi
    else
        print_result 1 "OGNL scan failed"
        echo "  Error: $OGNL_OUTPUT"
    fi
else
    echo "⚠ Skipping OGNL scan (no mapper files found)"
fi

echo ""
print_section "Verification Summary"

if [ $MISSING_VARS -eq 0 ]; then
    echo "✓ All checks passed - Environment is ready for migration"

    # Print Extension status
    echo ""
    echo "📋 Configuration Status:"
    echo ""

    if [ -f extensions/extension.json ]; then
        EXT_ENABLED=$(grep -o '"enabled": *true' extensions/extension.json || echo "")
        if [ -n "$EXT_ENABLED" ]; then
            echo "  Extension Variables:"
            echo "    ✓ ENABLED - Review extensions/extension.json for configuration"
        else
            echo "  Extension Variables:"
            echo "    ✓ DISABLED (no framework variables found)"
        fi
    fi

    # OGNL Status
    echo ""
    echo "  OGNL Expressions:"
    if [ -f docs/OGNL_IMPLEMENTATION_GUIDE.md ]; then
        echo "    ⚠ FOUND - Implementation required"
        echo "    → Read guide: docs/OGNL_IMPLEMENTATION_GUIDE.md"
        echo "    → Implement handlers and place JAR in lib/ognl_handlers/"
        echo "    → Update .env with OMA_OGNL_JAR path"
    elif [ -f lib/ognl_handlers/ognl_scan_report.json ]; then
        # Check report content
        if grep -q '"total_classes": *0' lib/ognl_handlers/ognl_scan_report.json 2>/dev/null; then
            echo "    ✓ NONE FOUND (OGNL handlers not needed)"
        else
            echo "    ⚠ FOUND - Check lib/ognl_handlers/ognl_scan_report.json"
        fi
    else
        echo "    ✓ NOT SCANNED (will be checked during verify-env)"
    fi

    exit 0
else
    echo "✗ Some checks failed - Please review errors above"
    exit 1
fi
