#!/usr/bin/env bash
# name: scan-extension
# description: Scan mapper files for Extension variables and configure extension.json
# usage: scan-extension <mapper-directory>

set -euo pipefail

# Load environment variables
if [ -f tools/load_oma_env.sh ]; then
    set -a
    source tools/load_oma_env.sh
    set +a
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

if [ -z "${PYTHON_BIN:-}" ]; then
    echo "✗ Error: Python 3.11+ not found"
    exit 1
fi

# Get mapper directory from argument or SOURCE_WORKSPACE
if [ $# -ge 1 ]; then
    MAPPER_DIR="$1"
elif [ -n "${SOURCE_WORKSPACE:-}" ]; then
    # Use SOURCE_WORKSPACE as default
    MAPPER_DIR="${SOURCE_WORKSPACE}"
    echo "Using SOURCE_WORKSPACE: ${SOURCE_WORKSPACE}"
else
    echo "Usage: scan-extension [mapper-directory]"
    echo ""
    echo "If no directory is provided, SOURCE_WORKSPACE from .env will be used."
    echo ""
    echo "Example:"
    echo "  scan-extension                              # Uses SOURCE_WORKSPACE"
    echo "  scan-extension mappers/daiso-oms/source     # Uses specific directory"
    exit 1
fi

# Check if directory exists
if [ ! -d "$MAPPER_DIR" ]; then
    echo "✗ Error: Directory not found: $MAPPER_DIR"
    exit 1
fi

# Run scanner
$PYTHON_BIN tools/scan_extension_variables.py "$MAPPER_DIR" extensions/extension.json
