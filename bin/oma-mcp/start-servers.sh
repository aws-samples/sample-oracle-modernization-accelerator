#!/bin/bash
# Start MCP servers as background services

source /workshop/oma-mcp/env.sh

# Kill existing
pkill -f "oma-sc-mcp-server" 2>/dev/null
pkill -f "postgresql-mcp-server" 2>/dev/null
pkill -f "oracle-mcp-server" 2>/dev/null
sleep 2

# Start oma-sc-mcp
cd /workshop/oma-mcp/oma-sc-mcp
nohup java -jar target/oma-sc-mcp-server-1.0.0.jar \
  > /tmp/oma-sc.log 2>&1 </dev/null &
echo "Started oma-sc-mcp (PID: $!)"

# Start pg-client-mcp
cd /workshop/oma-mcp/pg-client-mcp
nohup java -jar target/postgresql-mcp-server-1.0.0.jar \
  > /tmp/pg-client.log 2>&1 </dev/null &
echo "Started pg-client-mcp (PID: $!)"

# Start oracle-client-mcp
cd /workshop/oma-mcp/oracle-client-mcp
nohup java -jar target/oracle-mcp-server-1.0.0.jar \
  > /tmp/oracle-client.log 2>&1 </dev/null &
echo "Started oracle-client-mcp (PID: $!)"

sleep 8

# Verify
echo ""
echo "Running servers:"
ps aux | grep "\.jar" | grep -E "(oma-sc|postgresql|oracle)" | grep -v grep

echo ""
echo "Logs:"
echo "  oma-sc-mcp: tail -f /tmp/oma-sc.log"
echo "  pg-client-mcp: tail -f /tmp/pg-client.log"
echo "  oracle-client-mcp: tail -f /tmp/oracle-client.log"
