#!/bin/bash

# Check required environment variables
if [ -z "$APP_TRANSFORM_FOLDER" ] || [ -z "$SOURCE_SQL_MAPPER_FOLDER" ] || [ -z "$TARGET_SQL_MAPPER_FOLDER" ]; then
    echo "Error: Required environment variables are not set."
    echo "APP_TRANSFORM_FOLDER: $APP_TRANSFORM_FOLDER"
    echo "SOURCE_SQL_MAPPER_FOLDER: $SOURCE_SQL_MAPPER_FOLDER"
    echo "TARGET_SQL_MAPPER_FOLDER: $TARGET_SQL_MAPPER_FOLDER"
    exit 1
fi

CSV_FILE="$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv"

# Check if CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo "Error: CSV file not found: $CSV_FILE"
    exit 1
fi

echo "=== XML File Deletion Script Started ==="
echo "CSV File: $CSV_FILE"
echo "SOURCE Path: $SOURCE_SQL_MAPPER_FOLDER"
echo "TARGET Path: $TARGET_SQL_MAPPER_FOLDER"
echo ""

# Counters for deleted files
deleted_count=0
not_found_count=0

# Read CSV file and process (skip header)
tail -n +2 "$CSV_FILE" | while IFS=',' read -r no filename namespace dao_class parent_dao transform_target process; do
    # Skip empty lines
    if [ -z "$filename" ]; then
        continue
    fi
    
    # Transform path: SOURCE_SQL_MAPPER_FOLDER -> TARGET_SQL_MAPPER_FOLDER
    target_file=$(echo "$filename" | sed "s|$SOURCE_SQL_MAPPER_FOLDER|$TARGET_SQL_MAPPER_FOLDER|g")
    
    echo "Processing: $filename"
    echo "  -> Transformed path: $target_file"
    
    # Check if file exists and delete
    if [ -f "$target_file" ]; then
        rm -f "$target_file"
        if [ $? -eq 0 ]; then
            echo "  ✓ Successfully deleted"
            ((deleted_count++))
        else
            echo "  ✗ Failed to delete"
        fi
    else
        echo "  - File does not exist"
        ((not_found_count++))
    fi
    echo ""
done

echo "=== Task Completed ==="
echo "Files deleted: $deleted_count"
echo "Files not found: $not_found_count"
