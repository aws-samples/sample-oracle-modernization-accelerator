#!/bin/bash
set -e

echo "Initializing MCP servers..."

for mcp in oma-mcp pg-client-mcp oracle-client-mcp; do
  cd $mcp
  if [ -f "application-secretsmanager.properties" ]; then
    echo "Configure $mcp/application-secretsmanager.properties with your AWS credentials"
  fi
  cd ..
done

echo "Initialization complete. Update configuration files before running."
