#!/usr/bin/env bash
# name: split-mappers
# description: Split MyBatis mapper XML files into individual SQL statement files by project
# usage: split-mappers [project-name]

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

PROJECT_NAME=${1:-""}

echo "=== MyBatis Mapper Splitter ==="
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

TOTAL_SPLIT=0

for project in "${PROJECTS[@]}"; do
    echo "-------------------------------------------"
    echo "Project: $project"
    echo "-------------------------------------------"

    SOURCE_DIR="${SOURCE_WORKSPACE}/${project}"
    OUTPUT_DIR="${MAPPER_WORK_DIR}/${project}/source"

    if [ ! -d "$SOURCE_DIR" ]; then
        echo "  ✗ Project directory not found: $SOURCE_DIR"
        continue
    fi

    # Count mapper files
    MAPPER_COUNT=$(find "$SOURCE_DIR" -name "*.xml" -type f 2>/dev/null | wc -l)
    echo "  Found ${MAPPER_COUNT} mapper XML files"

    if [ "$MAPPER_COUNT" -eq 0 ]; then
        echo "  ⚠ No mapper files to split"
        continue
    fi

    # Run splitter
    ${PYTHON_BIN} tools/split_mapper.py --source-dir "$SOURCE_DIR" --output-dir "$OUTPUT_DIR"

    if [ $? -eq 0 ]; then
        SPLIT_COUNT=$(find "$OUTPUT_DIR" -name "*_*.xml" -type f 2>/dev/null | wc -l)
        echo "  ✓ Generated ${SPLIT_COUNT} individual SQL files"
        TOTAL_SPLIT=$((TOTAL_SPLIT + SPLIT_COUNT))
    else
        echo "  ✗ Split failed for $project"
    fi

    echo ""
done

echo "=== Summary ==="
echo "Total SQL files generated: ${TOTAL_SPLIT}"
