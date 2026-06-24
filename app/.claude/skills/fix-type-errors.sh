#!/bin/bash
set -euo pipefail

# Fix type casting errors using LLM

if [ $# -lt 4 ]; then
    echo "Usage: $0 <type-cast-errors.json> <convert-dir> <original-source-dir> <oracle-mapper-file>"
    echo "Example: $0 output/type-cast-errors.json mappers/daiso-oms/convert \\"
    echo "  /path/to/oracle/mappers \\"
    echo "  /path/to/oracle/mappers/oms-common-sql-oracle.xml"
    exit 1
fi

ERROR_FILE="$1"
CONVERT_DIR="$2"
ORIGINAL_SOURCE_DIR="$3"
ORACLE_MAPPER_FILE="$4"

if [ ! -f "$ERROR_FILE" ]; then
    echo "Error: $ERROR_FILE not found"
    exit 1
fi

if [ ! -d "$CONVERT_DIR" ]; then
    echo "Error: $CONVERT_DIR not found"
    exit 1
fi

echo "=== Type Casting Error Fixer ==="
echo ""
echo "Error File:   $ERROR_FILE"
echo "Convert Dir:  $CONVERT_DIR"
echo ""
echo "Step 1: Fix convert files..."
python3.11 tools/fix_type_errors.py "$ERROR_FILE" "$CONVERT_DIR"

echo ""
echo "Step 2: Re-merge..."
python3.11 tools/merge_mapper.py \
  --source-dir "$CONVERT_DIR" \
  --target-dir "${CONVERT_DIR%/convert}/target" \
  --original-source-dir "$ORIGINAL_SOURCE_DIR"

echo ""
echo "Step 3: Re-validate..."
TARGET_DIR="${CONVERT_DIR%/convert}/target"
rm -rf /tmp/target-test /tmp/oracle-test
mkdir -p /tmp/target-test /tmp/oracle-test
cp "$TARGET_DIR"/oms-common-sql-oracle.xml /tmp/target-test/
cp "$ORACLE_MAPPER_FILE" /tmp/oracle-test/

bash .claude/skills/run-validator.sh \
  /tmp/oracle-test \
  /tmp/target-test \
  "$CONVERT_DIR" \
  postgres > output/validation.log 2>&1

echo ""
echo "✓ Complete! Check output/validation-report.json"
