#!/bin/bash

# Oracle MyBatis test execution script

echo "=== Oracle MyBatis Test Execution ==="

# Help function
print_usage() {
    echo "Usage: $0 <directory_path> [options]"
    echo ""
    echo "Options:"
    echo "  --select-only   Execute SELECT statements only (default)"
    echo "  --all          Execute all SQL statements (including INSERT/UPDATE/DELETE)"
    echo "  --summary      Output summary information only"
    echo "  --verbose      Output detailed information"
    echo "  --json         Generate JSON result file"
    echo "  --json-file <filename>  Generate JSON result file (specify filename)"
    echo "  --include <pattern>     Search only folders containing specified pattern"
    echo "  --compare      Enable SQL result comparison (Oracle ↔ PostgreSQL/MySQL)"
    echo ""
    echo "Environment variables:"
    echo "  ORACLE_SVC_USER        Oracle username (required)"
    echo "  ORACLE_SVC_PASSWORD    Oracle password (required)"
    echo "  ORACLE_SVC_CONNECT_STRING  Oracle connection string (optional)"
    echo "  TARGET_DBMS_TYPE       Target DB type for comparison (mysql or postgresql, required when using --compare)"
    echo ""
    echo "PostgreSQL integration environment variables (when using --compare):"
    echo "  PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE"
    echo ""
    echo "MySQL integration environment variables (when using --compare):"
    echo "  MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_DATABASE"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/mappers --select-only --summary"
    echo "  $0 /path/to/mappers --all --verbose --json"
    echo "  $0 /path/to/mappers --compare --verbose"
}

# Check parameters
if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    print_usage
    exit 0
fi

# Check environment variables
if [ -z "$ORACLE_SVC_USER" ] || [ -z "$ORACLE_SVC_PASSWORD" ]; then
    echo "❌ Oracle environment variables are not set."
    echo "Required environment variables:"
    echo "  ORACLE_SVC_USER"
    echo "  ORACLE_SVC_PASSWORD"
    echo "  ORACLE_SVC_CONNECT_STRING (optional)"
    echo ""
    echo "Example:"
    echo "  export ORACLE_SVC_USER=your_username"
    echo "  export ORACLE_SVC_PASSWORD=your_password"
    echo "  export ORACLE_SVC_CONNECT_STRING=your_tns_name"
    exit 1
fi

echo "✅ Oracle environment variables verified"
echo "   User: $ORACLE_SVC_USER"
echo "   Connection string: ${ORACLE_SVC_CONNECT_STRING:-using default}"

# Set environment variables for PostgreSQL integration (optional)
if [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then
    echo "✅ PostgreSQL integration environment variables verified"
    echo "   PostgreSQL user: $PGUSER"
    echo "   PostgreSQL host: ${PGHOST:-localhost}"
    echo "   PostgreSQL port: ${PGPORT:-5432}"
    echo "   PostgreSQL database: ${PGDATABASE:-postgres}"
    
    # Automatically set TARGET_DBMS_TYPE
    export TARGET_DBMS_TYPE=postgresql
    echo "   Target DB type: $TARGET_DBMS_TYPE"
else
    echo "ℹ️  PostgreSQL integration environment variables not set. (optional)"
    echo "   To enable PostgreSQL integration, set the following environment variables:"
    echo "   PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE"
fi

# Compile
echo ""
echo "=== Java Compilation ==="
javac -cp ".:lib/*" com/test/mybatis/*.java

if [ $? -ne 0 ]; then
    echo "❌ Compilation failed"
    exit 1
fi

echo "✅ Compilation completed"

# Execute
echo ""
echo "=== Oracle Test Execution ==="

# Set TEST_FOLDER environment variable (first argument is mapper directory)
if [ -z "$TEST_FOLDER" ] && [ -n "$1" ]; then
    export TEST_FOLDER="$1"
fi

java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$@" --db oracle --compare

echo ""
echo "=== Execution Completed ==="
