#!/bin/bash

# PostgreSQL MyBatis test execution script

echo "=== PostgreSQL MyBatis Test Execution ==="

# Check environment variables
if [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ]; then
    echo "❌ PostgreSQL environment variables are not set."
    echo "Required environment variables:"
    echo "  PGUSER (required)"
    echo "  PGPASSWORD (required)"
    echo "  PGHOST (optional, default: localhost)"
    echo "  PGPORT (optional, default: 5432)"
    echo "  PGDATABASE (optional, default: postgres)"
    echo ""
    echo "Example:"
    echo "  export PGUSER=postgres"
    echo "  export PGPASSWORD=your_password"
    echo "  export PGHOST=localhost"
    echo "  export PGPORT=5432"
    echo "  export PGDATABASE=testdb"
    exit 1
fi

echo "✅ PostgreSQL environment variables verified"
echo "   User: $PGUSER"
echo "   Host: ${PGHOST:-localhost}"
echo "   Port: ${PGPORT:-5432}"
echo "   Database: ${PGDATABASE:-postgres}"

# Set TARGET_DBMS_TYPE (for SqlListRepository)
export TARGET_DBMS_TYPE=postgresql
echo "   Target DB type: $TARGET_DBMS_TYPE"

# Check PostgreSQL JDBC driver
if [ ! -f "lib/postgresql-42.7.1.jar" ]; then
    echo "❌ PostgreSQL JDBC driver not found."
    exit 1
fi

# Check Oracle integration environment variables (optional)
if [ -n "$ORACLE_SVC_USER" ] && [ -n "$ORACLE_SVC_PASSWORD" ]; then
    echo "✅ Oracle integration environment variables verified"
    echo "   Oracle user: $ORACLE_SVC_USER"
    echo "   Oracle connection string: ${ORACLE_SVC_CONNECT_STRING:-using default}"
else
    echo "ℹ️  Oracle integration environment variables not set. (optional)"
    echo "   To enable Oracle integration, set the following environment variables:"
    echo "   ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_SVC_CONNECT_STRING"
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
echo "=== PostgreSQL Test Execution ==="

# Set TEST_FOLDER environment variable (first argument is mapper directory)
if [ -z "$TEST_FOLDER" ] && [ -n "$1" ]; then
    export TEST_FOLDER="$1"
fi

java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$@" --db postgres --compare

echo ""
echo "=== Execution Completed ==="
