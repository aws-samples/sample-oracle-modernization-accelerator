#!/bin/bash
# Auto fix loop for type casting errors

set -e

if [ $# -lt 3 ]; then
    echo "Usage: $0 <oracle_mapper_dir> <target_dir> <convert_dir> [max_iterations]"
    echo "Example: $0 /path/to/oracle/mappers mappers/daiso-oms/target mappers/daiso-oms/convert 5"
    exit 1
fi

ORACLE_MAPPER_DIR="$1"
TARGET_DIR="$2"
CONVERT_DIR="$3"
MAX_ITERATIONS="${4:-5}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

iteration=0

echo "======================================================================"
echo "Starting Auto Fix Loop for Type Casting Errors"
echo "======================================================================"
echo "Oracle Mappers: $ORACLE_MAPPER_DIR"
echo "Target Dir:     $TARGET_DIR"
echo "Convert Dir:    $CONVERT_DIR"
echo "Max Iterations: $MAX_ITERATIONS"
echo "======================================================================"
echo ""

# Initial validation
echo "Running initial validation..."
bash .claude/skills/run-validator.sh \
  "$ORACLE_MAPPER_DIR" \
  "$TARGET_DIR" \
  "$CONVERT_DIR" \
  postgres > output/validation.log 2>&1

echo ""

while [ $iteration -lt $MAX_ITERATIONS ]; do
  iteration=$((iteration + 1))

  echo "======================================================================"
  echo "Iteration $iteration / $MAX_ITERATIONS"
  echo "======================================================================"
  echo ""

  # Analyze errors
  echo "Step 1: Analyzing type casting errors..."
  python3.11 tools/analyze_type_errors.py output/validation-report.json

  # Check if there are errors to fix
  error_count=$(jq '.type_cast_errors' output/type-cast-errors.json)

  if [ "$error_count" -eq 0 ]; then
    echo ""
    echo "✅ No more type casting errors! Loop complete."
    exit 0
  fi

  echo ""
  echo "Step 2: Fixing $error_count type casting errors..."
  python3.11 tools/fix_type_errors.py output/type-cast-errors.json "$TARGET_DIR"

  echo ""
  echo "Step 3: Re-validating..."
  bash .claude/skills/run-validator.sh \
    "$ORACLE_MAPPER_DIR" \
    "$TARGET_DIR" \
    "$CONVERT_DIR" \
    postgres > output/validation.log 2>&1

  echo ""
done

echo "======================================================================"
echo "Reached maximum iterations ($MAX_ITERATIONS)"
echo "======================================================================"
