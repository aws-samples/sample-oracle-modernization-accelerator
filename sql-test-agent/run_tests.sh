#!/bin/bash

# Run tests for SQL Test Agent

set -e

echo "=== Running SQL Test Agent Tests ==="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run unit tests
echo ""
echo "Running unit tests..."
pytest tests/unit/ -v --tb=short

echo ""
echo "=== Tests Complete ==="
