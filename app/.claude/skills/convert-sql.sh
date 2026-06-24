#!/usr/bin/env bash
# name: convert-sql
# description: Convert Oracle SQL to target database using Bedrock LLM with explicit type casting
# usage: convert-sql [project-name]

set -euo pipefail

# Load environment variables
if [ -f tools/load_oma_env.sh ]; then
    set -a
    source tools/load_oma_env.sh
    set +a
else
    exit 1
fi

# Auto-detect Python if not set
if [ -z "${PYTHON_BIN:-}" ]; then
    for cmd in python3.11 python3 python; do
        if command -v $cmd &> /dev/null; then
            VERSION=$($cmd --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
            MAJOR=$(echo $VERSION | cut -d. -f1)
            MINOR=$(echo $VERSION | cut -d. -f2)
            if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
                PYTHON_BIN=$cmd
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.11+ not found"
    exit 1
fi

# Check boto3
if ! ${PYTHON_BIN} -c "import boto3" 2>/dev/null; then
    echo "Error: boto3 module not found"
    echo "Install with: pip install boto3"
    exit 1
fi

PROJECT_NAME=${1:-""}

echo "=== SQL Converter (Oracle → ${TARGET_DB_TYPE}) ==="
echo ""
echo "Using Bedrock Model: ${BEDROCK_MODEL_ID}"
echo "Region: ${BEDROCK_REGION}"
echo ""

# Get list of projects
if [ -z "$PROJECT_NAME" ]; then
    PROJECTS=($(ls -1 "$SOURCE_WORKSPACE" 2>/dev/null | grep -v "^\." || true))
    echo "Processing all projects: ${#PROJECTS[@]}"
    echo ""
else
    PROJECTS=("$PROJECT_NAME")
    echo "Processing single project: $PROJECT_NAME"
    echo ""
fi

TOTAL_CONVERTED=0

for project in "${PROJECTS[@]}"; do
    echo "-------------------------------------------"
    echo "Project: $project"
    echo "-------------------------------------------"

    SOURCE_DIR="${MAPPER_WORK_DIR}/${project}/source"
    TARGET_DIR="${MAPPER_WORK_DIR}/${project}/target"

    if [ ! -d "$SOURCE_DIR" ]; then
        echo "  ✗ Source directory not found: $SOURCE_DIR"
        continue
    fi

    # Count source files
    SOURCE_COUNT=$(find "$SOURCE_DIR" -name "*.xml" -type f 2>/dev/null | wc -l)

    if [ "$SOURCE_COUNT" -eq 0 ]; then
        echo "  ⚠ No source files to convert"
        continue
    fi

    echo "  Found ${SOURCE_COUNT} mapper files"

    # Create target directory
    mkdir -p "$TARGET_DIR"

    # Run converter
    ${PYTHON_BIN} tools/convert_sql.py \
        --source-dir "$SOURCE_DIR" \
        --target-dir "$TARGET_DIR" \
        --dict-path "${ORACLE_DICT_PATH}"

    if [ $? -eq 0 ]; then
        CONVERTED_COUNT=$(find "$TARGET_DIR" -name "*.xml" -type f 2>/dev/null | wc -l)
        TC_COUNT=$(find "$TARGET_DIR" -name "*.tc.json" -type f 2>/dev/null | wc -l)
        echo "  ✓ Converted ${CONVERTED_COUNT} mapper files"
        echo "  ✓ Generated ${TC_COUNT} test case files"
        TOTAL_CONVERTED=$((TOTAL_CONVERTED + CONVERTED_COUNT))
    else
        echo "  ✗ Conversion failed for $project"
    fi

    echo ""
done

echo "=== Summary ==="
echo "Total converted files: ${TOTAL_CONVERTED}"
echo "Location: ${MAPPER_WORK_DIR}/{project}/target/"
