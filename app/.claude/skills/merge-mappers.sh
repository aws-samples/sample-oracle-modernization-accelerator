#!/usr/bin/env bash
# name: merge-mappers
# description: Merge split mapper files back into original structure and copy to target workspace
# usage: merge-mappers [project-name]

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

echo "=== MyBatis Mapper Merger ==="
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

TOTAL_MERGED=0

for project in "${PROJECTS[@]}"; do
    echo "-------------------------------------------"
    echo "Project: $project"
    echo "-------------------------------------------"

    SOURCE_DIR="${MAPPER_WORK_DIR}/${project}/target"
    TARGET_DIR="${TARGET_WORKSPACE}/${project}"
    ORIGINAL_SOURCE_DIR="${SOURCE_WORKSPACE}/${project}"

    if [ ! -d "$SOURCE_DIR" ]; then
        echo "  ✗ Source directory not found: $SOURCE_DIR"
        continue
    fi

    # Count split files
    SPLIT_COUNT=$(find "$SOURCE_DIR" -name "*_*.xml" -type f 2>/dev/null | wc -l)

    if [ "$SPLIT_COUNT" -eq 0 ]; then
        echo "  ⚠ No split files to merge"
        continue
    fi

    echo "  Found ${SPLIT_COUNT} split files"

    # Create target directory
    mkdir -p "$TARGET_DIR"

    # Run merger
    ${PYTHON_BIN} tools/merge_mapper.py \
        --source-dir "$SOURCE_DIR" \
        --target-dir "$TARGET_DIR" \
        --original-source-dir "$ORIGINAL_SOURCE_DIR"

    if [ $? -eq 0 ]; then
        MERGED_COUNT=$(find "$TARGET_DIR" -name "*.xml" -type f 2>/dev/null | wc -l)
        echo "  ✓ Merged ${MERGED_COUNT} mapper files to: $TARGET_DIR"
        TOTAL_MERGED=$((TOTAL_MERGED + MERGED_COUNT))
    else
        echo "  ✗ Merge failed for $project"
    fi

    echo ""
done

echo "=== Summary ==="
echo "Total merged mapper files: ${TOTAL_MERGED}"
echo "Target workspace: ${TARGET_WORKSPACE}"
