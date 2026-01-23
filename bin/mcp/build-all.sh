#!/bin/bash
set -e

for mcp in oma-mcp pg-client-mcp oracle-client-mcp; do
  echo "Building $mcp..."
  cd $mcp && ./mvnw clean package -DskipTests && cd ..
done
echo "All MCPs built successfully"
