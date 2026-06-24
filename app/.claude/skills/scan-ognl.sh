#!/usr/bin/env bash
# name: scan-ognl
# description: Scan MyBatis mappers for OGNL expressions and generate handler library or implementation guide
# usage: scan-ognl [source-dir] [--generate|--guide-only]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load environment
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Detect Python
if command -v python3.11 &> /dev/null; then
    PYTHON_BIN=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" = "3.11" ]; then
        PYTHON_BIN=python3
    else
        echo "✗ Python 3.11+ required (found $PYTHON_VERSION)"
        exit 1
    fi
else
    echo "✗ Python not found"
    exit 1
fi

echo "=== OGNL Scanner & Handler Generator ==="
echo ""

# Parse arguments
SOURCE_DIR="${1:-}"
GENERATE="${2:-}"

if [ -z "$SOURCE_DIR" ]; then
    # Auto-detect: scan all projects
    if [ -z "$MAPPER_WORK_DIR" ]; then
        MAPPER_WORK_DIR="./mappers"
    fi

    echo "📁 Auto-detecting mapper directories..."
    PROJECTS=$(find "$MAPPER_WORK_DIR" -maxdepth 1 -type d ! -path "$MAPPER_WORK_DIR" -exec basename {} \;)

    if [ -z "$PROJECTS" ]; then
        echo "✗ No projects found in $MAPPER_WORK_DIR"
        echo ""
        echo "Usage: $0 <source-dir> [--generate]"
        echo ""
        echo "Examples:"
        echo "  $0 mappers/daiso-oms/source              # Scan only"
        echo "  $0 mappers/daiso-oms/source --generate  # Scan and generate handlers (auto)"
        echo "  $0 mappers/daiso-oms/source --guide-only # Generate implementation guide for manual coding"
        echo "  $0 --all --generate                     # Scan all projects and generate"
        exit 1
    fi

    echo "Found projects:"
    for proj in $PROJECTS; do
        echo "  - $proj"
    done
    echo ""

    # Scan all projects
    TEMP_DIRS=""
    for proj in $PROJECTS; do
        SOURCE_PATH="$MAPPER_WORK_DIR/$proj/source"
        if [ -d "$SOURCE_PATH" ]; then
            TEMP_DIRS="$TEMP_DIRS $SOURCE_PATH"
        fi
    done

    SOURCE_DIR="$TEMP_DIRS"
fi

# Handle --all flag
if [ "$SOURCE_DIR" = "--all" ]; then
    SOURCE_DIR="$MAPPER_WORK_DIR/*/source"
    GENERATE="$2"
fi

# Output directory
OUTPUT_DIR="${OMA_OGNL_JAR%/*}"
if [ -z "$OUTPUT_DIR" ] || [ "$OUTPUT_DIR" = "." ]; then
    OUTPUT_DIR="./lib/ognl_handlers"
fi

echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

# Build command
CMD="$PYTHON_BIN tools/scan_ognl.py"

# Handle multiple directories
if [[ "$SOURCE_DIR" == *" "* ]]; then
    # Multiple directories - scan each
    for dir in $SOURCE_DIR; do
        if [ -d "$dir" ]; then
            CMD_FULL="$CMD --source-dir $dir --output-dir $OUTPUT_DIR"
            if [ "$GENERATE" = "--generate" ]; then
                CMD_FULL="$CMD_FULL --generate"
            elif [ "$GENERATE" = "--guide-only" ]; then
                CMD_FULL="$CMD_FULL --guide-only"
            fi

            echo "Scanning $dir..."
            cd "$PROJECT_ROOT"
            $CMD_FULL
            echo ""
        fi
    done
else
    # Single directory
    CMD="$CMD --source-dir $SOURCE_DIR --output-dir $OUTPUT_DIR"

    if [ "$GENERATE" = "--generate" ]; then
        CMD="$CMD --generate"
    elif [ "$GENERATE" = "--guide-only" ]; then
        CMD="$CMD --guide-only"
    fi

    cd "$PROJECT_ROOT"
    $CMD
fi

echo ""
echo "=== Summary ==="
echo ""

if [ -f "$OUTPUT_DIR/ognl_scan_report.json" ]; then
    echo "✓ Scan report: $OUTPUT_DIR/ognl_scan_report.json"
fi

if [ "$GENERATE" = "--generate" ]; then
    if [ -f "$OUTPUT_DIR/oma-ognl-handlers.jar" ]; then
        echo "✓ JAR file: $OUTPUT_DIR/oma-ognl-handlers.jar"
        echo ""
        echo "Next steps:"
        echo "  1. Deploy JAR to application server:"
        echo "     cp $OUTPUT_DIR/oma-ognl-handlers.jar \$CATALINA_HOME/lib/"
        echo ""
        echo "  2. Or add to application classpath:"
        echo "     java -cp $OUTPUT_DIR/oma-ognl-handlers.jar:app.jar com.your.Main"
    else
        echo ""
        echo "⚠ JAR file not found. Build manually:"
        echo "  cd $OUTPUT_DIR"
        echo "  javac com/*/framework/util/*.java org/springframework/util/*.java"
        echo "  jar cvf oma-ognl-handlers.jar com/ org/"
    fi
fi

echo ""
echo "✓ OGNL scan complete"
