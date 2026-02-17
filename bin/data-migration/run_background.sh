#!/bin/bash
# Run data migration in background

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$BASE_DIR/target-database"
mkdir -p "$OUTPUT_DIR"
LOG_FILE="$OUTPUT_DIR/data_migration_$(date +%Y%m%d_%H%M%S).log"

echo "Starting data migration in background..."
echo "Log file: $LOG_FILE"

# Source environment
source "$SCRIPT_DIR/../oma_env_demo.sh"

# Run in background
nohup python3.11 -u "$SCRIPT_DIR/data_migration.py" > "$LOG_FILE" 2>&1 &
PID=$!

echo "Process ID: $PID"
echo ""
echo "Monitor progress:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Check status:"
echo "  ps -p $PID"
echo ""
echo "Kill if needed:"
echo "  kill $PID"
