#!/bin/bash

if command -v python3.11 &> /dev/null; then
    echo "Python 3.11 is already installed"
    python3.11 --version
    exit 0
fi

echo "Installing Python 3.11..."
sudo yum install -y python3.11 python3.11-pip

if command -v python3.11 &> /dev/null; then
    echo "Python 3.11 installed successfully"
    python3.11 --version
else
    echo "Failed to install Python 3.11"
    exit 1
fi

echo "Installing boto3..."
python3.11 -m pip install boto3

echo "Installing MCP and Strands Agents..."
python3.11 -m pip uninstall -y strands 2>/dev/null || true
python3.11 -m pip install --upgrade mcp strands-agents

echo "Installing psycopg2..."
python3.11 -m pip install psycopg2-binary

echo ""
echo "✅ All prerequisites installed successfully"
