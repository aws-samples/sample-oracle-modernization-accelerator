#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check LOG_DIR environment variable
if [ -z "$LOG_DIR" ]; then
    echo -e "${RED}Error: LOG_DIR environment variable is not set.${NC}"
    echo "Usage: export LOG_DIR=/path/to/logs && ./error_extractor.sh <filename>"
    echo "Example: ./error_extractor.sh catalina.out"
    echo "         ./error_extractor.sh catalina.out.20250813_104748"
    exit 1
fi

# Check filename argument
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Please specify log filename.${NC}"
    echo "Usage: ./error_extractor.sh <filename>"
    echo "Example: ./error_extractor.sh catalina.out"
    echo "         ./error_extractor.sh catalina.out.20250813_104748"
    exit 1
fi

# Set log file path
LOG_FILE="$LOG_DIR/$1"

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}Error: Cannot find file $LOG_FILE.${NC}"
    exit 1
fi

# Generate backup filename with current datetime
BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${LOG_FILE}_${BACKUP_TIMESTAMP}"

echo -e "${BLUE}=== Log File Error Extractor (Mapper Name Extraction) ===${NC}"
echo -e "${YELLOW}Source file: $LOG_FILE${NC}"
echo -e "${YELLOW}Backup file: $BACKUP_FILE${NC}"
echo ""

# Backup log file
echo -e "${GREEN}1. Backing up log file...${NC}"
if cp "$LOG_FILE" "$BACKUP_FILE"; then
    echo -e "${GREEN}   ✓ Backup completed: $BACKUP_FILE${NC}"
else
    echo -e "${RED}   ✗ Backup failed${NC}"
    exit 1
fi

# Initialize result files
RESULT_FILE="result.$1.txt"
TEMP_RESULT_FILE="temp_result.txt"
TEMP_UNIQUE_FILE="temp_unique.txt"
> "$TEMP_RESULT_FILE"

echo -e "${GREEN}2. Extracting database errors...${NC}"

# Extract mapper name from mapper path function
extract_mapper_name() {
    local mapper_full="$1"

    # amzn.com.dao.mapper.
    if [[ "$mapper_full" =~ amzn\.[^.]+\.dao\.mapper\.([^.]+)Mapper ]]; then
        echo "${BASH_REMATCH[1]}Mapper"
    elif [[ "$mapper_full" =~ ([^.]+Mapper) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}

# Error number counter
error_count=0

# Temporary files
temp_error_blocks="/tmp/error_blocks_$$.tmp"

# Find various error patterns
grep -n "^### \(Error \(querying\|updating\) database\|Cause:.*SQL.*Exception\)" "$LOG_FILE" > "$temp_error_blocks"

# Additionally find independent SQLException patterns
grep -n "SQLException:" "$LOG_FILE" | grep -v "^###" | while IFS=':' read -r line_num rest; do
    echo "$line_num:SQLException: $rest" >> "$temp_error_blocks"
done

# Sort and remove duplicates
sort -n -t: -k1 "$temp_error_blocks" | uniq > "${temp_error_blocks}.sorted"
mv "${temp_error_blocks}.sorted" "$temp_error_blocks"

# Debug: Check number of error lines found
error_lines_found=$(wc -l < "$temp_error_blocks")
echo -e "   ${YELLOW}Error blocks found: $error_lines_found${NC}"

if [ "$error_lines_found" -eq 0 ]; then
    echo -e "   ${RED}No SQL error patterns found${NC}"
    echo -e "   ${YELLOW}File content sample:${NC}"
    head -5 "$LOG_FILE" | sed 's/^/     /'
fi

while IFS=':' read -r line_num rest; do
    error_count=$((error_count + 1))

    echo -e "   ${BLUE}Processing error #$error_count... (line: $line_num)${NC}"

    # Initialize variables
    file_path=""
    sql_id=""
    error_msg=""
    sql_query=""
    mapper_full=""

    # Find next error block start line
    next_error_line=""
    if [ -s "$temp_error_blocks" ]; then
        next_error_line=$(awk -F: -v current="$line_num" '$1 > current {print $1; exit}' "$temp_error_blocks")
    fi

    # Calculate lines to read
    if [ -n "$next_error_line" ]; then
        lines_to_read=$((next_error_line - line_num))
        if [ $lines_to_read -gt 100 ]; then
            lines_to_read=100
        fi
    else
        lines_to_read=100
    fi

    # Extract entire current error block
    start_line=$((line_num - 5))
    if [ $start_line -lt 1 ]; then
        start_line=1
    fi
    total_lines=$((lines_to_read + 10))

    error_block=$(tail -n +$start_line "$LOG_FILE" | head -n $total_lines)

    echo -e "   ${YELLOW}Analyzing error block... (lines $start_line ~ $((start_line + total_lines - 1)))${NC}"

    # Extract information from error block
    while IFS= read -r line; do
        # Extract error message from ### patterns
        if [[ "$line" =~ ^###\ Error\ querying\ database\..*Cause:\ (.+)$ ]]; then
            error_msg="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}Error message found (querying): ${error_msg:0:80}...${NC}"
        elif [[ "$line" =~ ^###\ Error\ updating\ database\..*Cause:\ (.+)$ ]]; then
            error_msg="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}Error message found (updating): ${error_msg:0:80}...${NC}"
        elif [[ "$line" =~ ^###\ Cause:\ (.+)$ ]]; then
            error_msg="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}Error message found (Cause): ${error_msg:0:80}...${NC}"
        elif [[ "$line" =~ SQLException:\ (.+)$ ]]; then
            # Independent SQLException pattern
            error_msg="SQLException: ${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}Error message found (SQLException): ${error_msg:0:80}...${NC}"
        fi

        # Extract file path
        if [[ "$line" =~ ^###\ The\ error\ may\ exist\ in\ file\ \[([^\]]+)\] ]]; then
            file_path="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}File path found: $file_path${NC}"
        fi

        # Extract SQL ID and save mapper name
        if [[ "$line" =~ ^###\ The\ error\ may\ involve\ (.+)$ ]]; then
            sql_id_full="${BASH_REMATCH[1]}"
            mapper_full="$sql_id_full"

            # Remove -Inline
            sql_id_full="${sql_id_full%-Inline}"
            # Extract only after last dot
            sql_id="${sql_id_full##*.}"
            echo -e "   ${GREEN}SQL ID found: $sql_id${NC}"
            echo -e "   ${BLUE}Full mapper name: $mapper_full${NC}"
        fi

        # Extract SQL query
        if [[ "$line" =~ ^###\ SQL:(.*)$ ]]; then
            sql_content="${BASH_REMATCH[1]}"
            # Use if content exists after SQL:
            if [[ -n "$sql_content" && "$sql_content" != " " ]]; then
                sql_query="$sql_content"
                echo -e "   ${GREEN}SQL query found: ${sql_query:0:80}...${NC}"
            else
                # Find SQL in next line after ### SQL:
                sql_found_flag=true
            fi
        elif [[ "$sql_found_flag" == true && -n "$line" && ! "$line" =~ ^### ]]; then
            # Extract actual SQL from next line after ### SQL:
            sql_query="$line"
            sql_found_flag=false
            echo -e "   ${GREEN}SQL query found: ${sql_query:0:80}...${NC}"
        fi

        # Attempt to extract SQL ID from INSERT/UPDATE/DELETE statements
        if [[ -z "$sql_id" && "$line" =~ (INSERT|UPDATE|DELETE).*INTO.*TB_[A-Z_0-9]+ ]]; then
            # Infer SQL ID from table name
            if [[ "$line" =~ TB_([A-Z_0-9]+) ]]; then
                table_name="${BASH_REMATCH[1]}"
                sql_id="insert"  # Default value
                echo -e "   ${YELLOW}SQL ID inferred from table name: $sql_id (table: TB_$table_name)${NC}"
            fi
        fi

        # Stop if Java stack trace starts
        if [[ "$line" =~ (\tat\ |Caused\ by:.*Exception) ]]; then
            echo -e "   ${YELLOW}Java stack trace detected, stopping additional parsing${NC}"
            break
        fi

    done <<< "$error_block"

    # If file path is empty and mapper name exists, use mapper name as filename
    if [[ -z "$file_path" && -n "$mapper_full" ]]; then
        mapper_name=$(extract_mapper_name "$mapper_full")
        if [[ -n "$mapper_name" ]]; then
            file_path="$mapper_name"
            echo -e "   ${CYAN}Filename extracted from mapper name: $file_path${NC}"
        fi
    fi

    # Output to temporary result file only if essential information exists
    if [[ -n "$error_msg" ]]; then
        {
            echo "Number [$error_count]"
            echo "File: $file_path"
            echo "sqlid: $sql_id"
            echo "Error: $error_msg"
            echo "SQL: $sql_query"
            echo ""
        } >> "$TEMP_RESULT_FILE"
        echo -e "   ${GREEN}✓ Error #$error_count extraction completed${NC}"
        echo -e "     File: ${file_path:0:50}..."
        echo -e "     SQL ID: $sql_id"
        echo -e "     SQL: ${sql_query:0:50}..."
    else
        echo -e "   ${RED}✗ Error #$error_count: Error message not found, skipping${NC}"
        error_count=$((error_count - 1))  # Rollback counter
    fi

    echo ""

done < "$temp_error_blocks"

echo -e "${GREEN}3. Removing duplicate errors (improved logic)...${NC}"

# Error normalization function
normalize_error() {
    local error="$1"
    # Extract SQLException type and main keywords only
    if [[ "$error" =~ (SQLIntegrityConstraintViolationException|SQLSyntaxErrorException|SQLException) ]]; then
        error_type="${BASH_REMATCH[1]}"

        # Extract main error patterns
        if [[ "$error" =~ Duplicate\ entry.*for\ key ]]; then
            echo "${error_type}:Duplicate_entry"
        elif [[ "$error" =~ You\ have\ an\ error\ in\ your\ SQL\ syntax.*near ]]; then
            echo "${error_type}:SQL_syntax_error"
        elif [[ "$error" =~ Unknown\ column.*in ]]; then
            echo "${error_type}:Unknown_column"
        else
            # Use first 50 characters only
            echo "${error_type}:${error:0:50}"
        fi
    else
        # Use first 50 characters only
        echo "${error:0:50}"
    fi
}

# Temporary file for duplicate removal
> "$TEMP_UNIQUE_FILE"

# Hash storage for duplicate checking
declare -A seen_errors
declare -A error_counts
unique_count=0

# Read temporary result file 6 lines at a time (number, file, sqlid, error, SQL, blank line)
while IFS= read -r line1 && IFS= read -r line2 && IFS= read -r line3 && IFS= read -r line4 && IFS= read -r line5 && IFS= read -r line6; do
    # Extract values from each line
    current_file=$(echo "$line2" | sed 's/^File: //')
    current_sqlid=$(echo "$line3" | sed 's/^sqlid: //')
    current_error=$(echo "$line4" | sed 's/^Error: //')
    current_sql=$(echo "$line5" | sed 's/^SQL: //')

    # Normalize error
    normalized_error=$(normalize_error "$current_error")

    # Generate key for duplicate checking (composed of file, sqlid, normalized error)
    check_key="${current_file}|||${current_sqlid}|||${normalized_error}"

    # Count duplicates
    count_key="${normalized_error}|||${current_sqlid}"
    error_counts[$count_key]=$((${error_counts[$count_key]} + 1))

    echo -e "   ${BLUE}Processing: ${current_error:0:60}...${NC}"
    echo -e "   ${YELLOW}Normalized: $normalized_error${NC}"

    # Check for duplicates
    if [[ -z "${seen_errors[$check_key]}" ]]; then
        # New error - add
        unique_count=$((unique_count + 1))
        seen_errors[$check_key]=1

        {
            echo "Number [$unique_count]"
            echo "File: $current_file"
            echo "sqlid: $current_sqlid"
            echo "Error: $current_error"
            echo "SQL: $current_sql"
            echo ""
        } >> "$TEMP_UNIQUE_FILE"

        echo -e "   ${GREEN}✓ Unique error #$unique_count added${NC}"
    else
        echo -e "   ${YELLOW}✗ Duplicate error skipped${NC}"
    fi

done < "$TEMP_RESULT_FILE"

# Add duplicate count information
echo -e "${GREEN}4. Adding duplicate count information...${NC}"
TEMP_FINAL_FILE="temp_final.txt"
> "$TEMP_FINAL_FILE"

while IFS= read -r line1 && IFS= read -r line2 && IFS= read -r line3 && IFS= read -r line4 && IFS= read -r line5 && IFS= read -r line6; do
    current_file=$(echo "$line2" | sed 's/^File: //')
    current_sqlid=$(echo "$line3" | sed 's/^sqlid: //')
    current_error=$(echo "$line4" | sed 's/^Error: //')
    current_sql=$(echo "$line5" | sed 's/^SQL: //')

    # Find duplicate count with normalized error
    normalized_error=$(normalize_error "$current_error")
    count_key="${normalized_error}|||${current_sqlid}"
    duplicate_count=${error_counts[$count_key]}

    {
        echo "$line1"
        echo "$line2"
        echo "sqlid: $current_sqlid (${duplicate_count} cases)"
        echo "$line4"
        echo "$line5"
        echo ""
    } >> "$TEMP_FINAL_FILE"

done < "$TEMP_UNIQUE_FILE"

# Save to final result file
cp "$TEMP_FINAL_FILE" "$RESULT_FILE"

echo -e "${GREEN}   ✓ Total ${error_count} errors, ${unique_count} unique errors, $((error_count - unique_count)) duplicates removed${NC}"

# Initialize log file
echo -e "${GREEN}5. Initializing log file...${NC}"
if > "$LOG_FILE"; then
    echo -e "${GREEN}   ✓ Log file has been initialized${NC}"
else
    echo -e "${RED}   ✗ Log file initialization failed${NC}"
fi

# Clean up temporary files
rm -f "$temp_error_blocks" "$TEMP_RESULT_FILE" "$TEMP_UNIQUE_FILE" "$TEMP_FINAL_FILE"

echo ""
echo -e "${BLUE}=== Task Completed ===${NC}"
echo -e "${GREEN}✓ Backup file: $BACKUP_FILE${NC}"
echo -e "${GREEN}✓ Result file: $RESULT_FILE (${unique_count} unique errors)${NC}"
echo -e "${GREEN}✓ Original file: $LOG_FILE (initialized)${NC}"
echo -e "${BLUE}✓ Duplicate removal: $((error_count - unique_count)) duplicate errors removed${NC}"
echo ""

if [ "$unique_count" -gt 0 ]; then
    echo -e "${YELLOW}Next step: Run ./error_fix.sh to fix errors.${NC}"
else
    echo -e "${BLUE}No database errors found.${NC}"
fi