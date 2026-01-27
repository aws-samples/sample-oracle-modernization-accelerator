#!/bin/bash

# Build all OMA MCP servers

set -e

echo "Building OMA MCP Servers..."
echo

cd "$(dirname "$0")"

echo "=== Building oma-sc-mcp ==="
cd oma-sc-mcp
mvn clean package -DskipTests
echo "✓ oma-sc-mcp built successfully"
echo

cd ..

echo "=== Building pg-client-mcp ==="
cd pg-client-mcp
mvn clean package -DskipTests
echo "✓ pg-client-mcp built successfully"
echo

cd ..

echo "=== Building oracle-client-mcp ==="
cd oracle-client-mcp
mvn clean package -DskipTests
echo "✓ oracle-client-mcp built successfully"
echo

cd ..

echo "=== Build Summary ==="
echo "All OMA MCP servers built successfully!"
echo
echo "JAR files:"
echo "  - oma-sc-mcp/target/oma-sc-mcp-server-1.0.0.jar"
echo "  - pg-client-mcp/target/postgresql-mcp-server-1.0.0.jar"
echo "  - oracle-client-mcp/target/oracle-mcp-server-1.0.0.jar"

