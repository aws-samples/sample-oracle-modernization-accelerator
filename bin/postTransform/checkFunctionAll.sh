#!/bin/bash

# Dynamic processing of transform xml files
cd $APP_TOOLS_FOLDER/../postTransform/function

# Get paths from environment variables
APP_LOGS_FOLDER=${APP_LOGS_FOLDER:-"/tmp"}
APP_TRANSFORM_FOLDER=${APP_TRANSFORM_FOLDER:-"/tmp"}

# Create log directory
POST_TRANSFORM_LOG_DIR="$APP_LOGS_FOLDER/postTransform"
mkdir -p "$POST_TRANSFORM_LOG_DIR"
mkdir -p "$APP_TRANSFORM_FOLDER"

# Integrated test log file
LOG_FILE="$POST_TRANSFORM_LOG_DIR/sqlTestResult.log"

# Initialize log file (on first run)
echo "🔄 Initializing log file: $LOG_FILE"
echo "=== SQL Function Test Log - $(date) ===" > "$LOG_FILE"

# Set and initialize result file paths
RESULT_FILE="$APP_TRANSFORM_FOLDER/sqlTestResult.json"
FAILED_RESULT_FILE="$APP_TRANSFORM_FOLDER/sqlTestResultFailed.json"
echo "🔄 Initializing result file: $RESULT_FILE"
echo "🔄 Initializing failed result file: $FAILED_RESULT_FILE"
rm -f "$RESULT_FILE"
rm -f "$FAILED_RESULT_FILE"

# Dynamically generate transform xml list
echo "🔍 Searching for transform xml files..."
transform_xml_list="$POST_TRANSFORM_LOG_DIR/sqlTestResult_xml_list.txt"
find $APP_LOGS_FOLDER/mapper/ -path "*/transform/*.xml" -type f > "$transform_xml_list" 2>/dev/null

# Check file count
file_count=$(wc -l < "$transform_xml_list")
echo "📁 Found transform xml files: ${file_count} files"

if [ $file_count -eq 0 ]; then
    echo "❌ No transform xml files found."
    echo "   Path: $APP_LOGS_FOLDER/mapper/*/transform/*.xml"
    exit 1
fi

echo "=== Starting transform xml file processing ==="
echo "$(date)"
echo "📁 Target files: ${file_count} files"
echo

# Set Python script path
script_path="$APP_TOOLS_FOLDER/../postTransform/function/genSelectFromXML.py"
if [ ! -f "$script_path" ]; then
    echo "❌ genSelectFromXML.py script not found."
    echo "   Path: $script_path"
    exit 1
fi

echo "🚀 Script to use: $script_path"
echo

# Read file list
mapfile -t files < "$transform_xml_list"

success_count=0
fail_count=0
no_func_count=0
timeout_count=0

for i in "${!files[@]}"; do
    file="${files[$i]}"
    filename=$(basename "$file")
    echo "[$((i+1))/${file_count}] $filename"
    
    # Set timeout (30 seconds)
    timeout 30s python3 "$script_path" "$file" > /tmp/test_result_$((i+1)).log 2>&1
    exit_code=$?
    
    if [ $exit_code -eq 124 ]; then
        echo "  ⏰ Timeout"
        timeout_count=$((timeout_count + 1))
    else
        result=$(cat /tmp/test_result_$((i+1)).log)
        
        if echo "$result" | grep -q "✅ Success"; then
            functions=$(echo "$result" | grep "Extracted function count" | sed 's/.*: //')
            unique=$(echo "$result" | grep "After deduplication" | sed 's/.*: //')
            echo "  ✅ Success - $functions → $unique"
            success_count=$((success_count + 1))
        elif echo "$result" | grep -q "No functions found"; then
            echo "  ⚪ No functions"
            no_func_count=$((no_func_count + 1))
        else
            echo "  ❌ Failed"
            fail_count=$((fail_count + 1))
        fi
    fi
    
    # Show progress (every 100 files or every 10 files if total is less than 100)
    progress_interval=$( [ $file_count -gt 100 ] && echo 100 || echo 10 )
    if [ $((($i + 1) % $progress_interval)) -eq 0 ]; then
        echo "  📊 Progress: $((i+1))/${file_count} - Success: $success_count, No functions: $no_func_count, Failed: $fail_count"
    fi
done

echo ""
echo "=== Final transform xml processing results ==="
echo "✅ Success: $success_count files"
echo "⚪ No functions: $no_func_count files"  
echo "❌ Failed: $fail_count files"
echo "⏰ Timeout: $timeout_count files"
echo "📊 Success rate: $(( (success_count + no_func_count) * 100 / file_count ))%"
echo ""
echo "🚀 Processing complete - Total ${file_count} files"
echo "$(date)"
echo "=== Transform xml processing complete ==="
