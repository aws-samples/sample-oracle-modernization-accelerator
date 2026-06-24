#!/usr/bin/env bash
# name: build-oracle-dict
# description: Build Oracle database dictionary with metadata and sample data
# usage: build-oracle-dict [sample-size]

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

SAMPLE_SIZE=${1:-1}
OUTPUT_PATH="${ORACLE_DICT_PATH}"

echo "=== Oracle Dictionary Builder ==="
echo ""
echo "Schema: ${ORACLE_SCHEMA}"
echo "Output: ${OUTPUT_PATH}"
echo "Sample size: ${SAMPLE_SIZE}"
echo ""

# Check if oracledb is installed
if ! ${PYTHON_BIN} -c "import oracledb" 2>/dev/null; then
    echo "Error: oracledb module not found"
    echo "Install with: pip install oracledb"
    exit 1
fi

# Run dictionary builder
${PYTHON_BIN} tools/oracle_dictionary.py --build --sample-size "${SAMPLE_SIZE}" --output "${OUTPUT_PATH}"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Dictionary build complete"
    echo ""

    # Show summary
    if [ -f "${OUTPUT_PATH}" ]; then
        TABLE_COUNT=$(${PYTHON_BIN} -c "import json; print(json.load(open('${OUTPUT_PATH}'))['table_count'])")
        FILE_SIZE=$(du -h "${OUTPUT_PATH}" | cut -f1)
        echo "Summary:"
        echo "  Tables: ${TABLE_COUNT}"
        echo "  File size: ${FILE_SIZE}"
        echo "  Location: ${OUTPUT_PATH}"
    fi
else
    echo "✗ Dictionary build failed"
    exit 1
fi
