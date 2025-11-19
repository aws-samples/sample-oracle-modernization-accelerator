#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help display function
show_help() {
    echo -e "${BLUE}=== SQL Error Fix Tool Usage ===${NC}"
    echo ""
    echo "Usage:"
    echo "  ./error_fix.sh <result_file>           # Normal mode (manual confirmation before deletion)"
    echo "  ./error_fix.sh <result_file> -auto     # Auto delete mode (automatic deletion after fix)"
    echo "  ./error_fix.sh --help                  # Show help"
    echo ""
    echo "Examples:"
    echo "  ./error_fix.sh result.txt"
    echo "  ./error_fix.sh result.catalina.out_20250813_093338.txt"
    echo "  ./error_fix.sh result.txt -auto"
    echo ""
    echo "Features:"
    echo "  - Display error list from specified result file"
    echo "  - Select error number"
    echo "  - Auto prompt generation and Q CLI execution"
    echo "  - Delete fixed error from result file after completion"
    echo ""
}

# Argument validation
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Please specify a result file.${NC}"
    echo ""
    show_help
    exit 1
fi

# Set result file path
RESULT_FILE="$1"

# Check auto delete mode
AUTO_DELETE=false
if [[ "$2" == "-auto" || "$2" == "--auto" ]]; then
    AUTO_DELETE=true
    echo -e "${BLUE}Auto delete mode is enabled.${NC}"
fi

# Check if result file exists
if [ ! -f "$RESULT_FILE" ]; then
    echo -e "${RED}Error: Cannot find $RESULT_FILE file.${NC}"
    echo "Please check the file path."
    exit 1
fi

# Check if result file is empty
if [ ! -s "$RESULT_FILE" ]; then
    echo -e "${RED}Error: $RESULT_FILE file is empty.${NC}"
    exit 1
fi

echo -e "${BLUE}=== SQL Error Fix Tool ===${NC}"
echo -e "${YELLOW}Target file: $RESULT_FILE${NC}"
echo ""

# Display error list on first run
echo -e "${BLUE}=== Database Error List ===${NC}"
echo ""

# Display result.txt content (limit SQL to 2 lines)
while IFS= read -r line; do
    if [[ "$line" =~ ^SQL:\ (.+)$ ]]; then
        sql_content="${BASH_REMATCH[1]}"
        # Limit SQL to 2 lines (first line: first 80 chars, second line: next 80 chars)
        first_line="${sql_content:0:80}"
        second_line="${sql_content:80:80}"

        echo "SQL: $first_line"
        if [ ${#sql_content} -gt 80 ]; then
            echo "     $second_line"
            if [ ${#sql_content} -gt 160 ]; then
                echo "     ..."
            fi
        fi
    else
        echo "$line"
    fi
done < "$RESULT_FILE"

echo -e "${YELLOW}================================${NC}"
echo ""

# Get number input from user
while true; do
    echo -n "Enter error number to fix (show list again: 'list', exit: 'q'): "
    read -r selected_number

    # Exit condition
    if [[ "$selected_number" == "q" || "$selected_number" == "Q" ]]; then
        echo "Exiting program."
        exit 0
    fi

    # Show full list again
    if [[ "$selected_number" == "list" || "$selected_number" == "LIST" ]]; then
        echo -e "${BLUE}=== Database Error List ===${NC}"
        echo ""

        # Display result.txt content (limit SQL to 2 lines)
        while IFS= read -r line; do
            if [[ "$line" =~ ^SQL:\ (.+)$ ]]; then
                sql_content="${BASH_REMATCH[1]}"
                # Limit SQL to 2 lines (first line: first 80 chars, second line: next 80 chars)
                first_line="${sql_content:0:80}"
                second_line="${sql_content:80:80}"

                echo "SQL: $first_line"
                if [ ${#sql_content} -gt 80 ]; then
                    echo "     $second_line"
                    if [ ${#sql_content} -gt 160 ]; then
                        echo "     ..."
                    fi
                fi
            else
                echo "$line"
            fi
        done < "$RESULT_FILE"

        echo -e "${YELLOW}================================${NC}"
        echo ""
        continue
    fi

    # Check if it's a number
    if ! [[ "$selected_number" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Please enter a valid number.${NC}"
        continue
    fi

    # Check if selected number exists
    if ! grep -q "Number \[$selected_number\]" "$RESULT_FILE"; then
        echo -e "${RED}Number [$selected_number] not found.${NC}"
        continue
    fi

    break
done

echo -e "${GREEN}Selected number [$selected_number].${NC}"
echo ""

# Extract information for selected number only
temp_selected="/tmp/selected_error_$selected_number.tmp"

# Extract from selected number to next number or end of file
awk -v num="$selected_number" '
    /^Number \[/ {
        current_num = $0
        gsub(/Number \[|\]/, "", current_num)
        if (current_num == num) {
            found = 1
        } else if (found) {
            exit
        }
    }
    found { print }
' "$RESULT_FILE" > "$temp_selected"

# Parse information
file_path=""
sql_id=""
error_msg=""
sql_query=""

while IFS= read -r line; do
    if [[ "$line" =~ ^File:\ (.+)$ ]]; then
        file_path="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^sqlid:\ (.+)$ ]]; then
        sql_id="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^Error:\ (.+)$ ]]; then
        error_msg="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^SQL:\ (.+)$ ]]; then
        sql_query="${BASH_REMATCH[1]}"
    fi
done < "$temp_selected"

# Template file path
TEMPLATE_FILE="error_fix.md"

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Cannot find $TEMPLATE_FILE template file.${NC}"
    rm -f "$temp_selected"
    exit 1
fi

# Read template and substitute variables
template_content=$(cat "$TEMPLATE_FILE")
final_prompt=$(echo "$template_content" | \
    sed "s|{{FILE_PATH}}|$file_path|g" | \
    sed "s|{{SQL_ID}}|$sql_id|g" | \
    sed "s|{{ERROR_MESSAGE}}|$error_msg|g" | \
    sed "s|{{SQL_QUERY}}|${sql_query:0:200}...|g")

# Display completed prompt
echo -e "${BLUE}=== Completed Prompt (copy and use) ===${NC}"
echo -e "${YELLOW}==================== Prompt Start ====================${NC}"
echo "$final_prompt"
echo -e "${YELLOW}==================== Prompt End ====================${NC}"
echo ""

# Execute Q directly
echo -e "${GREEN}Executing Q...${NC}"
echo ""

# Execute Q
kiro-cli chat

# Check fix completion after Q execution
echo ""
if [ "$AUTO_DELETE" = true ]; then
    echo -e "${GREEN}Auto delete mode: Deleting number [$selected_number] item from $RESULT_FILE...${NC}"
    fix_success="y"
else
    echo -n "Was the fix completed successfully? (y/n): "
    read -r fix_success
fi

if [[ "$fix_success" == "y" || "$fix_success" == "Y" ]]; then
    if [ "$AUTO_DELETE" != true ]; then
        echo -e "${GREEN}Deleting number [$selected_number] item from $RESULT_FILE...${NC}"
    fi

    # Add information to fix_list.csv
    FIX_LIST_FILE="fix_list.csv"

    # Create CSV header if it doesn't exist
    if [ ! -f "$FIX_LIST_FILE" ]; then
        echo "Number,XML File Name,SQL ID (Duplicate Count),Error Message,Result Status" > "$FIX_LIST_FILE"
    fi

    # Extract XML filename (filename only from file path)
    xml_filename=$(basename "$file_path")

    # Check duplicate count (how many same sqlid exist in result file)
    duplicate_count=$(grep -c "sqlid: $sql_id" "$RESULT_FILE" 2>/dev/null || echo "1")

    # Prepare data to add to CSV (handle commas and quotes)
    csv_number="$selected_number"
    csv_xml_filename="\"$xml_filename\""
    csv_sqlid="\"$sql_id ($duplicate_count)\""
    csv_error_msg="\"${error_msg//\"/\"\"}\""  # Escape quotes
    csv_result="\"Fixed\""

    # Add to CSV file
    echo "$csv_number,$csv_xml_filename,$csv_sqlid,$csv_error_msg,$csv_result" >> "$FIX_LIST_FILE"

    echo -e "${BLUE}📝 Fix history has been recorded in fix_list.csv.${NC}"

    # Delete selected number item from result file
    temp_result="/tmp/result_temp_$$.txt"

    # Copy excluding from selected number to next number or end of file
    awk -v num="$selected_number" '
        /^Number \[/ {
            current_num = $0
            gsub(/Number \[|\]/, "", current_num)
            if (current_num == num) {
                skip = 1
                next
            } else if (skip) {
                skip = 0
            }
        }
        !skip { print }
    ' "$RESULT_FILE" > "$temp_result"

    # Replace original file with temporary file
    mv "$temp_result" "$RESULT_FILE"

    echo -e "${GREEN}✅ Number [$selected_number] item has been deleted from $RESULT_FILE.${NC}"

    # Check remaining error count
    remaining_errors=$(grep -c "^Number \[" "$RESULT_FILE" 2>/dev/null || echo "0")
    # Remove newline characters and extract numbers only
    remaining_errors=$(echo "$remaining_errors" | tr -d '\n' | grep -o '[0-9]*' | head -1)
    # Set to 0 if empty
    remaining_errors=${remaining_errors:-0}

    echo -e "${BLUE}📊 Remaining errors: ${remaining_errors}${NC}"

    if [ "$remaining_errors" -eq 0 ]; then
        echo -e "${GREEN}🎉 Congratulations! All errors have been fixed!${NC}"
        echo -e "${YELLOW}💡 Now test your application again.${NC}"
    else
        echo -e "${YELLOW}💡 To fix the next error, run ./error_fix.sh $RESULT_FILE again.${NC}"
    fi
else
    echo -e "${YELLOW}Number [$selected_number] item remains in $RESULT_FILE.${NC}"
    echo -e "${BLUE}💡 You can try fixing it again later.${NC}"
fi

# Clean up temporary files
rm -f "$temp_selected"

echo ""
echo -e "${GREEN}Task completed.${NC}"