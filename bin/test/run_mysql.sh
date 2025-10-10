#!/bin/bash

# MySQL MyBatis test execution script

echo "=== MySQL MyBatis Test Execution ==="

# Check environment variables
if [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_PASSWORD" ]; then
    echo "❌ MySQL environment variables are not set."
    echo "Required environment variables:"
    echo "  MYSQL_USER (required)"
    echo "  MYSQL_PASSWORD (required)"
    echo "  MYSQL_HOST (optional, default: localhost)"
    echo "  MYSQL_TCP_PORT (optional, default: 3306)"
    echo "  MYSQL_DATABASE (optional, default: test)"
    echo ""
    echo "Example:"
    echo "  export MYSQL_USER=root"
    echo "  export MYSQL_PASSWORD=your_password"
    echo "  export MYSQL_HOST=localhost"
    echo "  export MYSQL_TCP_PORT=3306"
    echo "  export MYSQL_DATABASE=testdb"
    exit 1
fi

echo "✅ MySQL environment variables verified"
echo "   User: $MYSQL_USER"
echo "   Host: ${MYSQL_HOST:-localhost}"
echo "   Port: ${MYSQL_TCP_PORT:-3306}"
echo "   Database: ${MYSQL_DATABASE:-test}"

# Set TARGET_DBMS_TYPE (for SqlListRepository)
export TARGET_DBMS_TYPE=mysql
echo "   Target DB type: $TARGET_DBMS_TYPE"

# Check MySQL JDBC driver
if [ ! -f "lib/mysql-connector-j-8.2.0.jar" ]; then
    echo "❌ MySQL JDBC driver not found."
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
echo "=== MySQL Test Execution ==="

# Set TEST_FOLDER environment variable (first argument is mapper directory)
if [ -z "$TEST_FOLDER" ] && [ -n "$1" ]; then
    export TEST_FOLDER="$1"
fi

java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$@" --db mysql

echo ""
echo "=== Execution Completed ==="
