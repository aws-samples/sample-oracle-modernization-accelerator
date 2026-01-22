#!/bin/bash
set -e

SERVER_HOST=${1:-"localhost"}
SERVER_USER=${2:-"ec2-user"}

for mcp in oma-mcp pg-client-mcp oracle-client-mcp; do
  echo "Deploying $mcp to $SERVER_HOST..."
  scp -r $mcp $SERVER_USER@$SERVER_HOST:/opt/mcp/
  ssh $SERVER_USER@$SERVER_HOST "cd /opt/mcp/$mcp && ./mvnw clean package -DskipTests"
done
echo "Deployment complete"
