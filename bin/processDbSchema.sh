#!/bin/bash

# processDbSchema.sh - Database Schema Processing Tool
# Handles DMS Schema Conversion report analysis and object transformation

set -e

# Enable alias expansion for using sqlplus-oma
shopt -s expand_aliases
source ~/.bashrc

# Load Oracle environment variables if not set
if [ -z "$ORACLE_HOST" ]; then
    export ORACLE_HOST=10.255.255.155
    export ORACLE_PORT=1521
    export ORACLE_SID=XEPDB1
    export ORACLE_ADM_USER=system
    export ORACLE_ADM_PASSWORD=welcome1
    export ORACLE_SVC_USER=oma
    export ORACLE_SVC_PASSWORD=welcome1
fi

# Set NLS_LANG if not already set
if [ -z "$NLS_LANG" ]; then
    export NLS_LANG=KOREAN_KOREA.AL32UTF8
fi

# Set default port if not specified
if [ -z "$ORACLE_PORT" ]; then
    export ORACLE_PORT=1521
fi

# Setup logging
LOG_DIR="/home/ec2-user/workspace/oma/logs/database"
LOG_FILE="$LOG_DIR/db_schema_conversion_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

# Logging functions
log_info() {
    local message="$1"
    echo -e "${GREEN}INFO - $message${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    local message="$1"
    echo -e "${RED}ERROR - $message${NC}" | tee -a "$LOG_FILE"
}

log_debug() {
    local message="$1"
    echo -e "${CYAN}DEBUG - $message${NC}" >> "$LOG_FILE"
}

# Function to display initial banner
show_initial_banner() {
    clear
    print_separator
    echo -e "${BLUE}${BOLD}Step 1: Additional DB Schema Conversion${NC}"
    print_separator
    echo -e "${CYAN}This step performs additional conversion work on database objects.${NC}"
    echo -e "${CYAN}Performs Oracle schema to PostgreSQL conversion work.${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}Environment Variable Settings:${NC}"
    echo -e "${GREEN}  SOURCE_DDL_DIR: $SOURCE_DDL_DIR${NC}"
    echo -e "${GREEN}  CONVERTED_DIR: $CONVERTED_DIR${NC}"
    echo -e "${GREEN}  ORACLE_HOST: $ORACLE_HOST${NC}"
    echo -e "${GREEN}  PGHOST: $PGHOST${NC}"
    print_separator
    echo -e "${YELLOW}You must be pre-logged into Amazon Q before starting DB Schema conversion.${NC}"
    echo -e "${CYAN}Running DB Schema conversion script${NC}"
    echo ""
    echo -e "${BLUE}${BOLD}=== Basic Menu ===${NC}"
    echo -e "${CYAN}b) Back to previous menu${NC}"
    echo -e "${CYAN}q) Quit${NC}"
    echo ""
}

# Function to handle initial mode selection
handle_initial_mode() {
    show_initial_banner
    main  # Start main conversion process directly
}

# Function to deploy existing converted schemas
deploy_existing_schemas() {
    print_color $BLUE "Checking converted schema files..."
    
    if [ ! -d "$CONVERTED_DIR" ] || [ -z "$(ls -A "$CONVERTED_DIR" 2>/dev/null)" ]; then
        print_color $RED "No converted schema files found."
        print_color $YELLOW "Please run 'Full Conversion' mode first."
        echo
        handle_initial_mode
        return
    fi
    
    deploy_all_objects
}

WORKSPACE_DIR="/home/ec2-user/workspace"
TARGET_DIR="$WORKSPACE_DIR/tgt-pg-db"
CONVERTED_DIR="$TARGET_DIR/target-ddl"
SOURCE_DDL_DIR="$TARGET_DIR/source-ddl"
TEMP_DIR="/tmp/processDbSchema_$$"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'
UNDERLINE='\033[4m'

# Separator output function
print_separator() {
    printf "${BLUE}${BOLD}%80s${NC}\n" | tr " " "="
}

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to show menu options
show_menu() {
    echo
    echo -e "${CYAN}b) Back to previous menu${NC}"
    echo -e "${CYAN}q) Quit${NC}"
    echo
}

# Function to handle user input for back/quit
handle_navigation() {
    case "$1" in
        "b"|"B") 
            print_color $YELLOW "Returning to previous menu..."
            return 1  # Return to previous menu
            ;;
        "q"|"Q") 
            cleanup_temp_files
            print_color $YELLOW "Exiting..."
            exit 0
            ;;
        *)
            # For any other input (valid selections), add spacing for visibility
            echo
            echo
            echo
            return 0
            ;;
    esac
}

# Function to cleanup temporary files
cleanup_temp_files() {
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    rm -f /tmp/complex_objects.txt 2>/dev/null || true
    rm -f /tmp/selected_zip.txt 2>/dev/null || true
}

# Function to create target directory
create_target_directory() {
    if [ ! -d "$TARGET_DIR" ]; then
        mkdir -p "$TARGET_DIR"
        print_color $GREEN "Directory created: $TARGET_DIR"
    fi
    
    if [ ! -d "$CONVERTED_DIR" ]; then
        mkdir -p "$CONVERTED_DIR"
        echo
        print_color $GREEN "Converted object storage location: $CONVERTED_DIR"
    fi
    
    if [ ! -d "$SOURCE_DDL_DIR" ]; then
        mkdir -p "$SOURCE_DDL_DIR"
        print_color $GREEN "Created directory: $SOURCE_DDL_DIR"
    fi
    
    mkdir -p "$TEMP_DIR"
}

# Function to list existing zip files or go to S3 download
select_zip_file() {
    local zip_files=($(find "$TARGET_DIR" -name "*.zip" 2>/dev/null))
    
    if [ ${#zip_files[@]} -gt 0 ]; then
        echo
        print_color $BLUE "The following files exist in the conversion target folder ${BOLD}$TARGET_DIR/${NC}${BLUE}. You can select an existing file or download a new target list from S3.${NC}"
        for i in "${!zip_files[@]}"; do
            echo -e "${CYAN}$((i+1)). $(basename "${zip_files[$i]}")${NC}"
        done
        echo -e "${CYAN}$((${#zip_files[@]}+1)). Download from S3${NC}"
        echo
        echo -n "Select option (num or b/q): "
        read selection
        handle_navigation "$selection"
        
        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -le "${#zip_files[@]}" ] && [ "$selection" -gt 0 ]; then
            echo "${zip_files[$((selection-1))]}" > /tmp/selected_zip.txt
            return 0
        elif [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -eq "$((${#zip_files[@]}+1))" ]; then
            if download_from_s3; then
                return 0
            else
                select_zip_file  # Return to file selection if download_from_s3 returned 1
                return $?
            fi
        else
            print_color $RED "Invalid option. Please select again."
            select_zip_file  # Retry file selection
            return $?
            select_zip_file
        fi
    else
        if ! download_from_s3; then
            select_zip_file  # Return to file selection if user chose 'b'
        fi
    fi
}

# Function to download from S3
download_from_s3() {
    print_color $YELLOW "S3 download is required."
    echo
    echo -n "Please enter the S3 URI of the zip file to download. (e.g., s3://oma-dms-sc-[accountid]/dms-sc-migration-project/ORACLE_AURORA_POSTGRESQL_[time].zip): "
    read s3_path
    handle_navigation "$s3_path"
    
    if [ -z "$s3_path" ]; then
        echo "File URI was not entered. Would you like to return to the previous menu? (b, q)"
        read choice
        case "$choice" in
            q) exit 0 ;;
            b) return 1 ;;
            *) download_from_s3 ;;
        esac
        return
    fi
    
    local filename=$(basename "$s3_path")
    local local_path="$TARGET_DIR/$filename"
    
    print_color $YELLOW "Downloading from S3..."
    if aws s3 cp "$s3_path" "$local_path"; then
        print_color $GREEN "Download successful: $filename"
        echo "$local_path" > /tmp/selected_zip.txt
    else
        print_color $RED "S3 download failed"
        download_from_s3
    fi
}

# Function to confirm zip file selection
confirm_zip_selection() {
    local zip_file=$(cat /tmp/selected_zip.txt)
    local filename=$(basename "$zip_file")
    # Extract timestamp from filename pattern: ORACLE_AURORA_POSTGRESQL_2025-09-07T05-00-40.891Z.zip
    local timestamp=$(echo "$filename" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}T[0-9]\{2\}-[0-9]\{2\}-[0-9]\{2\}\.[0-9]\{3\}Z' || echo "Unknown")
    
    print_color $BLUE "Selected file: ${BOLD}$filename${NC}"
    print_color $BLUE "Timestamp: ${BOLD}$timestamp${NC}"
    echo
    print_color $YELLOW "Do you want to proceed with conversion based on this file?"
    print_color $CYAN "(Selecting N will return to the file selection step)"
    echo -n "Is this correct? (Y/n): "
    read confirmation
    handle_navigation "$confirmation"
    
    case "$confirmation" in
        ""|"Y"|"y"|"yes"|"Yes")
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to extract and analyze zip file
analyze_zip_file() {
    local zip_file=$(cat /tmp/selected_zip.txt)
    local extract_dir="$TEMP_DIR/extracted"
    
    echo
    print_color $YELLOW "Extracting ZIP file..."
    mkdir -p "$extract_dir"
    unzip -q "$zip_file" -d "$extract_dir"
    
    # Extract timestamp from ZIP filename and create target directory
    local zip_filename=$(basename "$zip_file")
    local timestamp=$(echo "$zip_filename" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}T[0-9]\{2\}-[0-9]\{2\}-[0-9]\{2\}\.[0-9]\{3\}Z' || echo "unknown")
    local timestamp_dir="$TARGET_DIR/$timestamp"
    
    # Copy extracted files to timestamp directory
    mkdir -p "$timestamp_dir"
    cp -r "$extract_dir"/* "$timestamp_dir/" 2>/dev/null || true
    print_color $GREEN "File extraction completed: $timestamp_dir"
    echo
    
    # Find the CSV file (without Summary in name)
    local csv_file=$(find "$extract_dir" -name "*.csv" | grep -v Summary | head -1)
    
    if [ -z "$csv_file" ]; then
        print_color $RED "Required CSV file not found"
        return 1
    fi
    
    print_color $YELLOW "Analyzing objects with complexity..."
    
    # Call external Python script
    local script_path="/home/ec2-user/workspace/oma/bin/database/db_conversion.py"
    
    if [ -f "$script_path" ]; then
        if ! python3 "$script_path" analyze "$csv_file"; then
            echo
            echo "1. Return to previous menu"
            echo "2. Download new file from S3"
            echo -n "Select option (num or b/q): "
            read choice
            
            if ! handle_navigation "$choice"; then
                return 1  # Return to file selection
            fi
            
            case "$choice" in
                "1")
                    return 1  # Return to file selection menu
                    ;;
                "2")
                    download_from_s3
                    return $?
                    ;;
                *)
                    print_color $RED "Invalid selection"
                    return 1
                    ;;
            esac
        fi
    else
        print_color $RED "Python script not found at: $script_path"
        return 1
    fi
    
    if [ ! -f "/tmp/complex_objects.txt" ]; then
        print_color $GREEN "No complex objects found to convert."
        return 1
    fi
    
    return 0
}

# Function to handle object conversion choice
handle_conversion_choice() {
    echo
    echo -e "${CYAN}1. Would you like to convert all these objects using Amazon Q?${NC}"
    echo -e "${CYAN}2. Would you like to convert objects individually using Amazon Q?${NC}"
    echo -n "Select (1/2, or b/q): "
    read choice
    
    if ! handle_navigation "$choice"; then
        return 1  # Return to file selection
    fi
    
    case "$choice" in
        "1")
            if ! convert_all_objects; then
                # Return to file selection if convert_all_objects returns non-zero
                return 1
            fi
            ;;
        "2")
            convert_individual_objects
            ;;
        *)
            print_color $RED "Invalid selection"
            handle_conversion_choice
            ;;
    esac
}

# Function to convert all objects
convert_all_objects() {
    log_info "Starting conversion of all objects"
    print_color $YELLOW "Converting all objects..."
    
    # Check if there are already converted files
    local existing_files=0
    for sql_file in "$CONVERTED_DIR"/*.sql; do
        [ -f "$sql_file" ] && existing_files=$((existing_files + 1))
    done
    
    if [ $existing_files -gt 0 ]; then
        log_info "Found $existing_files existing conversion files"
        echo
        print_color $YELLOW "There are already $existing_files converted files."
        echo "1. Keep existing files and convert only new ones"
        echo "2. Convert all files again (overwrite)"
        echo -n "Select (1/2): "
        read overwrite_choice
        
        echo
        echo
        echo
        
        if [ "$overwrite_choice" = "2" ]; then
            log_info "Deleting existing conversion files"
            print_color $BLUE "Deleting existing conversion files..."
            rm -f "$CONVERTED_DIR"/*.sql
        fi
    fi
    
    local total_objects=$(wc -l < /tmp/complex_objects.txt)
    local current=0
    local failed_count=0
    
    log_info "Converting a total of $total_objects objects"
    
    while IFS= read -r object; do
        current=$((current + 1))
        echo
        log_info "Converting object ($current/$total_objects): $object"
        print_color $BLUE "Processing object $current/$total_objects: $object"
        
        # Convert object without user interaction
        convert_single_object_batch "$object"
        
        if [ $? -eq 0 ]; then
            print_color $GREEN "✓ $object conversion completed"
        else
            print_color $RED "✗ $object conversion failed"
            failed_count=$((failed_count + 1))
        fi
        
    done < /tmp/complex_objects.txt
    
    if [ $failed_count -eq 0 ]; then
        log_info "All object conversions completed"
        print_color $GREEN "All object conversions completed!"
    else
        log_error "$failed_count object conversions failed"
        print_color $RED "$failed_count object conversions failed!"
    fi
    handle_deployment_choice
}

# Function to convert individual objects
convert_individual_objects() {
    local objects=($(cat /tmp/complex_objects.txt))
    
    while true; do
        echo
        print_color $BLUE "Select the object to convert:"
        for i in "${!objects[@]}"; do
            local object_name="${objects[$i]}"
            local simple_name=$(echo "$object_name" | awk -F'.' '{print $NF}')
            local converted_name=$(echo "$object_name" | sed 's/Schemas\.//g' | tr '[:upper:]' '[:lower:]')
            local converted_file="$CONVERTED_DIR/${converted_name}.sql"
            
            if [ -f "$converted_file" ]; then
                echo "$((i+1)). $object_name [Converted]"
            else
                echo "$((i+1)). $object_name"
            fi
        done
        echo -n "Select number (or b/q): "
        read selection
        
        if ! handle_navigation "$selection"; then
            return 1  # Return to previous menu
        fi
        
        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -le "${#objects[@]}" ] && [ "$selection" -gt 0 ]; then
            convert_single_object "${objects[$((selection-1))]}"
        else
            print_color $RED "Invalid selection"
        fi
    done
    
    handle_deployment_choice
}

# Function to convert single object in batch mode (no user interaction)
convert_single_object_batch() {
    local object_name="$1"
    local simple_object_name=$(echo "$object_name" | sed 's/Schemas\.//g' | tr '[:upper:]' '[:lower:]')
    local original_name=$(echo "$object_name" | awk -F'.' '{print $NF}')  # Extract just the procedure name for Oracle
    
    # Check if already converted
    local final_output="$CONVERTED_DIR/${simple_object_name}.sql"
    if [ -f "$final_output" ]; then
        print_color $YELLOW "Already converted: $simple_object_name (skip)"
        return 0
    fi
    
    local source_file="$SOURCE_DDL_DIR/${original_name}.sql"
    local prompt_file="$TEMP_DIR/${simple_object_name}_prompt.txt"
    local output_file="$TEMP_DIR/${simple_object_name}_output.txt"
    
    if [ ! -f "$source_file" ]; then
        # Call Python script to extract DDL from Oracle
        if ! python3 "/home/ec2-user/workspace/oma/bin/database/db_conversion.py" extract "$original_name" "$source_file"; then
            print_color $RED "Failed to extract DDL from Oracle for $original_name"
            return 1
        fi
        
        # Check if file exists and has content
        if [ ! -s "$source_file" ]; then
            print_color $RED "DDL file is empty or missing: $source_file"
            return 1
        fi
    fi
    
    # Create prompt
    local template_file="/home/ec2-user/workspace/oma/bin/database/ora_to_pg_prompt.md"
    if [ ! -f "$template_file" ]; then
        print_color $RED "Template file not found: $template_file"
        return 1
    fi
    
    local oracle_ddl=$(cat "$source_file")
    sed "s/{OBJECT_NAME}/$simple_object_name/g; s/{SOURCE_DBMS_TYPE}/Oracle/g; s/{TARGET_DBMS_TYPE}/PostgreSQL/g" "$template_file" > "$prompt_file"
    echo "" >> "$prompt_file"
    echo "\`\`\`sql" >> "$prompt_file"
    echo "$oracle_ddl" >> "$prompt_file"
    echo "\`\`\`" >> "$prompt_file"
    
    # Execute Q Chat with visible progress
    print_color $BLUE "Converting using Amazon Q: $simple_object_name"
    echo "Conversion progress:"
    
    if q chat --trust-all-tools --no-interactive < "$prompt_file" | tee "$output_file"; then
        echo
        print_color $BLUE "변환 결과 처리 중..."
        
        # Extract SQL content with comprehensive cleaning
        print_color $BLUE "Processing conversion result..."
        
        # Use sed and awk to extract clean SQL
        # Step 1: Remove ANSI color codes and control characters
        sed 's/\x1b\[[0-9;]*[mK]//g' "$output_file" | \
        sed 's/\[[0-9;]*m//g' | \
        sed 's/\[[0-9]*[ABCD]//g' > "$TEMP_DIR/clean1.txt"
        
        # Step 2: Extract lines between CREATE and $$; (inclusive)
        awk '
        /CREATE OR REPLACE PROCEDURE|CREATE PROCEDURE/ { found=1; print; next }
        found && /\$\$;/ { print; found=0; exit }
        found { print }
        ' "$TEMP_DIR/clean1.txt" > "$TEMP_DIR/clean2.txt"
        
        # Step 3: Clean up line numbers and artifacts
        sed -E 's/^[[:space:]]*[0-9]+,[[:space:]]*[0-9]+:[[:space:]]*//' "$TEMP_DIR/clean2.txt" | \
        sed -E 's/^[[:space:]]*[\+\-][[:space:]]*[0-9]*:[[:space:]]*//' | \
        sed -E 's/^[[:space:]]*[0-9]+:[[:space:]]*//' | \
        sed -E 's/^[[:space:]]*[\+\-][[:space:]]*$//' | \
        sed -E 's/^[[:space:]]*:[[:space:]]*//' | \
        sed '/^[[:space:]]*$/d' > "$final_output"
        
        # Verify the output
        if [ -s "$final_output" ] && grep -q "CREATE OR REPLACE PROCEDURE\|CREATE PROCEDURE" "$final_output"; then
            print_color $GREEN "SQL extracted successfully"
        else
            print_color $RED "Failed to extract valid SQL, saving raw output"
            cp "$output_file" "$final_output"
        fi
        
        if [ ! -s "$final_output" ]; then
            cp "$output_file" "$final_output"
        fi
        
        print_color $BLUE "Converted file: $final_output"
        return 0
    else
        print_color $RED "✗ Amazon Q 변환에 실패했습니다."
        return 1
    fi
}

# Function to convert a single object using Amazon Q
convert_single_object() {
    local object_name="$1"
    print_color $YELLOW "Converting object using Amazon Q: $object_name"
    
    # Extract just the object name from full path
    local simple_object_name=$(echo "$object_name" | sed 's/Schemas\.//g' | tr '[:upper:]' '[:lower:]')
    local original_name=$(echo "$object_name" | awk -F'.' '{print $NF}')  # Extract just the procedure name for Oracle
    local ddl_file="$SOURCE_DDL_DIR/${original_name}.sql"
    local final_output="$CONVERTED_DIR/${simple_object_name}.sql"
    
    # Always re-extract: remove existing files
    if [ -f "$ddl_file" ]; then
        print_color $BLUE "Deleting existing DDL file and re-extracting from Oracle..."
        rm -f "$ddl_file"
    fi
    
    if [ -f "$final_output" ]; then
        print_color $BLUE "Deleting existing conversion file..."
        rm -f "$final_output"
    fi
    
    # Call Python script directly
    if ! python3 "/home/ec2-user/workspace/oma/bin/database/db_conversion.py" extract "$original_name" "$ddl_file"; then
        print_color $RED "Failed to extract DDL from Oracle for $original_name"
        return 1
    fi
    
    # Check if file exists and has content
    if [ ! -s "$ddl_file" ]; then
        print_color $RED "DDL file is empty or missing: $ddl_file"
        return 1
    fi
    
    # Read DDL content
    local oracle_ddl=""
    if [ -f "$ddl_file" ]; then
        oracle_ddl=$(cat "$ddl_file")
    fi
    
    if [ -z "$oracle_ddl" ]; then
        print_color $RED "Failed to read DDL content"
        return 1
    fi
    
    # Create prompt file
    local prompt_file="$TEMP_DIR/prompt_${simple_object_name}.txt"
    local output_file="$TEMP_DIR/output_${simple_object_name}.log"
    local template_file="/home/ec2-user/workspace/oma/bin/database/ora_to_pg_prompt.md"
    
    if [ ! -f "$template_file" ]; then
        print_color $RED "Template file not found: $template_file"
        return 1
    fi
    
    # Create prompt from template using a safer method
    python3 -c "
import sys
template_file = '$template_file'
prompt_file = '$prompt_file'
object_name = '$simple_object_name'
ddl_content = open('$ddl_file', 'r').read()

with open(template_file, 'r') as f:
    template = f.read()

# Replace placeholders
result = template.replace('{OBJECT_NAME}', object_name)
result = result.replace('{SOURCE_DBMS_TYPE}', 'orcl')
result = result.replace('{TARGET_DBMS_TYPE}', 'postgres')
result = result.replace('{ORACLE_DDL}', ddl_content)

with open(prompt_file, 'w') as f:
    f.write(result)
"
    
    # Execute Q Chat
    print_color $BLUE "Executing Amazon Q conversion..."
    if q chat --trust-all-tools --no-interactive < "$prompt_file" | tee "$output_file"; then
        local final_output="$CONVERTED_DIR/${simple_object_name}.sql"
        
        # Extract only SQL content from Q Chat output
        # Remove all ANSI color codes, control characters, and formatting
        sed 's/\x1b\[[0-9;]*[mK]//g' "$output_file" | \
        # Remove lines with special characters and metadata
        grep -v "^🛠️\|^●\|^↳\|^>\|^\s*⋮\|Purpose:\|Creating:\|Completed in\|Major Conversions\|Key Technical" | \
        # Remove line numbers and + symbols from fs_write output
        sed 's/^[+]\s*[0-9]*:\s*//' | \
        # Extract SQL content between CREATE and $$;
        awk '
        BEGIN { in_sql = 0; sql_content = "" }
        /CREATE OR REPLACE FUNCTION|CREATE FUNCTION|CREATE OR REPLACE PROCEDURE|CREATE PROCEDURE/ { 
            in_sql = 1; 
            sql_content = $0 "\n"
            next 
        }
        in_sql == 1 {
            sql_content = sql_content $0 "\n"
            if ($0 ~ /\$\$;$/) {
                print sql_content
                exit
            }
        }
        ' > "$final_output"
        
        # If no SQL was extracted, save the original output
        if [ ! -s "$final_output" ]; then
            cp "$output_file" "$final_output"
        fi
        
        if [ -s "$final_output" ] && grep -q "CREATE OR REPLACE PROCEDURE\|CREATE PROCEDURE" "$final_output"; then
            print_color $GREEN "✓ Conversion completed for $simple_object_name."
            print_color $BLUE "Converted file: $final_output"
        else
            print_color $RED "✗ Conversion failed for $simple_object_name."
            return 1
        fi
        
        # Ask user what to do next
        echo
        echo "1. Would you like to apply to target DB?"
        echo "2. Would you like to convert other objects?"
        echo -n "Select (1/2, or b/q): "
        read choice
        handle_navigation "$choice"
        
        case "$choice" in
            "1")
                print_color $BLUE "Applying DDL to PostgreSQL..."
                if python3 "/home/ec2-user/workspace/oma/bin/database/db_conversion.py" deploy "$final_output"; then
                    print_color $GREEN "✓ DDL applied successfully."
                    echo
                    echo "1. Would you like to apply other converted objects to DB?"
                    echo "2. Would you like to convert other objects?"
                    echo -n "Select (1/2, or b/q): "
                    read next_choice
                    handle_navigation "$next_choice"
                    
                    case "$next_choice" in
                        "1")
                            # Go to individual deployment menu for converted objects
                            show_converted_objects_for_deployment
                            return $?
                            ;;
                        "2")
                            # Continue with object conversion
                            return 0
                            ;;
                        *)
                            print_color $RED "Invalid selection"
                            # Ask again
                            echo
                            echo "1. Would you like to apply other converted objects to DB?"
                            echo "2. Would you like to convert other objects?"
                            echo -n "Select (1/2, or b/q): "
                            read next_choice
                            handle_navigation "$next_choice"
                            
                            case "$next_choice" in
                                "1")
                                    show_converted_objects_for_deployment
                                    return $?
                                    ;;
                                "2")
                                    return 0
                                    ;;
                                *)
                                    print_color $RED "Invalid selection"
                                    return 0
                                    ;;
                            esac
                            ;;
                    esac
                else
                    print_color $RED "✗ DDL application failed. Re-conversion is required."
                    echo
                    echo "1. Convert again"
                    echo "2. Convert other objects"
                    echo -n "Select (1/2, or b/q): "
                    read retry_choice
                    handle_navigation "$retry_choice"
                    
                    case "$retry_choice" in
                        "1")
                            # Retry conversion for the same object
                            convert_single_object "$object_name"
                            return $?
                            ;;
                        "2")
                            # Continue with other objects
                            return 0
                            ;;
                    esac
                fi
                ;;
            "2")
                print_color $BLUE "Continuing with other object conversions..."
                return 0
                ;;
        esac
        
        return 0
    else
        print_color $RED "Failed to convert $simple_object_name"
        return 1
    fi
}

# Function to validate DDL output
validate_ddl_output() {
    local output_file="$1"
    local object_name="$2"
    
    if [ ! -f "$output_file" ] || [ ! -s "$output_file" ]; then
        print_color $RED "Output file is empty or missing"
        return 1
    fi
    
    # Basic PostgreSQL DDL validation
    local content=$(cat "$output_file")
    
    # Check for basic DDL keywords
    if ! echo "$content" | grep -qi -E "(CREATE|ALTER|DROP|TABLE|INDEX|SEQUENCE|FUNCTION|PROCEDURE)"; then
        print_color $RED "No valid DDL keywords found"
        return 1
    fi
    
    # Check for Oracle-specific syntax that should be converted
    if echo "$content" | grep -qi -E "(VARCHAR2|NUMBER\(|SYSDATE|NVL\(|\|\|)"; then
        print_color $YELLOW "Warning: Possible unconverted Oracle syntax detected"
    fi
    
    # Check for PostgreSQL-specific improvements
    if echo "$content" | grep -qi -E "(SERIAL|BIGSERIAL|TEXT|BOOLEAN|TIMESTAMP|COALESCE|CONCAT)"; then
        print_color $GREEN "PostgreSQL-specific syntax detected - good conversion"
    fi
    
    return 0
}

# Function to show converted objects for individual deployment
show_converted_objects_for_deployment() {
    local converted_files=($(find "$CONVERTED_DIR" -name "*.sql" -type f 2>/dev/null))
    
    if [ ${#converted_files[@]} -eq 0 ]; then
        print_color $YELLOW "No converted files found."
        return 1
    fi
    
    echo
    print_color $BLUE "List of converted objects:"
    for i in "${!converted_files[@]}"; do
        local file_path="${converted_files[$i]}"
        local file_name=$(basename "$file_path" .sql)
        echo "$((i+1)). $file_name"
    done
    
    echo -n "Select the object number to deploy (or b/q): "
    read selection
    
    if ! handle_navigation "$selection"; then
        return 1
    fi
    
    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -le "${#converted_files[@]}" ] && [ "$selection" -gt 0 ]; then
        local selected_file="${converted_files[$((selection-1))]}"
        print_color $BLUE "Applying DDL to PostgreSQL..."
        if python3 "/home/ec2-user/workspace/oma/bin/database/db_conversion.py" deploy "$selected_file"; then
            print_color $GREEN "✓ DDL applied successfully."
            echo
            echo "1. Would you like to apply other objects to DB?"
            echo "2. Would you like to proceed with object conversion?"
            echo -n "Select (1/2, or b/q): "
            read next_choice
            
            if ! handle_navigation "$next_choice"; then
                return 1
            fi
            
            case "$next_choice" in
                "1")
                    show_converted_objects_for_deployment  # Show deployment menu again
                    ;;
                "2")
                    return 0  # Return to conversion menu
                    ;;
                *)
                    print_color $RED "Invalid selection"
                    show_converted_objects_for_deployment
                    ;;
            esac
        else
            print_color $RED "✗ DDL application failed."
            show_converted_objects_for_deployment  # Show menu again
        fi
    else
        print_color $RED "Invalid selection"
        show_converted_objects_for_deployment  # Show menu again
    fi
}

# Function to handle deployment choice
handle_deployment_choice() {
    echo
    echo -e "${CYAN}1. Apply directly to PostgreSQL${NC}"
    echo -e "${CYAN}2. Convert again${NC}"
    echo -e "${CYAN}3. Apply later${NC}"
    echo -n "Select (1/2/3, or b/q): "
    read choice
    
    if ! handle_navigation "$choice"; then
        return 1  # Return to previous menu
    fi
    
    case "$choice" in
        "1")
            deploy_all_objects
            ;;
        "2")
            # Return to conversion choice menu without re-extracting ZIP
            if [ -f "/tmp/complex_objects.txt" ]; then
                echo
                print_color $BLUE "Objects with Medium or Complex complexity:"
                print_color $BLUE "$(printf '%50s' | tr ' ' '-')"
                local count=1
                while IFS= read -r object; do
                    echo "${count}. ${object}"
                    count=$((count + 1))
                done < /tmp/complex_objects.txt
                echo
                handle_conversion_choice
            else
                print_color $YELLOW "No complex object list found. Re-analyzing ZIP file."
                if analyze_zip_file; then
                    handle_conversion_choice
                fi
            fi
            ;;
        "3")
            print_color $GREEN "Converted DDL files have been saved to ${BOLD}$CONVERTED_DIR${NC}${GREEN}.${NC}"
            print_color $BLUE "Please review and apply manually."
            ;;
        *)
            print_color $RED "Invalid selection"
            handle_deployment_choice
            ;;
    esac
}

# Function to deploy all converted objects to PostgreSQL
deploy_all_objects() {
    print_color $BLUE "Applying all converted objects to PostgreSQL..."
    
    local success_list=()
    local failed_list=()
    local total_files=0
    
    # Count total files
    for sql_file in "$CONVERTED_DIR"/*.sql; do
        [ -f "$sql_file" ] && total_files=$((total_files + 1))
    done
    
    if [ $total_files -eq 0 ]; then
        print_color $YELLOW "No converted files to apply."
        return 0
    fi
    
    local current=0
    echo
    print_color $BLUE "Deploying a total of ${BOLD}$total_files${NC}${BLUE} objects...${NC}"
    
    # Deploy each file
    for sql_file in "$CONVERTED_DIR"/*.sql; do
        if [ -f "$sql_file" ]; then
            current=$((current + 1))
            local object_name=$(basename "$sql_file" .sql)
            
            print_color $CYAN "[$current/$total_files] Deploying: ${BOLD}$object_name${NC}"
            
            if python3 "/home/ec2-user/workspace/oma/bin/database/db_conversion.py" deploy "$sql_file"; then
                success_list+=("$object_name")
                print_color $GREEN "  ✓ Success"
            else
                failed_list+=("$object_name")
                print_color $RED "  ✗ Failed"
            fi
        fi
    done
    
    # Generate deployment report
    echo
    print_separator
    print_color $BLUE "${BOLD}Deployment Result Summary${NC}"
    print_separator
    print_color $GREEN "${BOLD}Success: ${#success_list[@]} objects${NC}"
    print_color $RED "${BOLD}Failed: ${#failed_list[@]} objects${NC}"
    
    # Show successful deployments
    if [ ${#success_list[@]} -gt 0 ]; then
        echo
        print_color $GREEN "${BOLD}✓ Successfully deployed objects:${NC}"
        for obj in "${success_list[@]}"; do
            echo -e "${GREEN}  - $obj${NC}"
        done
    fi
    
    # Handle failed deployments
    if [ ${#failed_list[@]} -gt 0 ]; then
        echo
        print_color $RED "${BOLD}✗ Objects that failed deployment:${NC}"
        for obj in "${failed_list[@]}"; do
            echo -e "${RED}  - $obj${NC}"
        done
        
        # Save failed objects list
        local failed_objects_file="$CONVERTED_DIR/failed_objects.txt"
        printf "%s\n" "${failed_list[@]}" > "$failed_objects_file"
        
        echo
        print_color $YELLOW "Failed objects list has been saved: ${BOLD}$failed_objects_file${NC}"
        print_color $YELLOW "Please re-convert those objects and try again."
        
        echo
        echo -e "${CYAN}1. Re-convert failed objects${NC}"
        echo -e "${CYAN}2. Handle manually later${NC}"
        echo -n "Select (1/2): "
        read retry_choice
        
        case "$retry_choice" in
            "1")
                echo
                echo
                echo
                retry_failed_objects "${failed_list[@]}"
                ;;
            "2")
                echo
                echo
                echo
                print_color $BLUE "Please handle failed objects manually later."
                ;;
        esac
    else
        print_color $GREEN "${BOLD}All objects have been successfully deployed!${NC}"
    fi
}

# Function to retry failed objects
retry_failed_objects() {
    local failed_objects=("$@")
    
    print_color $BLUE "Re-converting failed objects..."
    
    for obj in "${failed_objects[@]}"; do
        echo
        print_color $YELLOW "Re-converting: $obj"
        
        # Find full object name from original list
        local full_object_name=$(grep "$obj" /tmp/complex_objects.txt | head -1)
        if [ -n "$full_object_name" ]; then
            # Use individual conversion (with Oracle re-extraction)
            convert_single_object "$full_object_name"
            
            # Try to deploy again
            local sql_file="$CONVERTED_DIR/${obj}.sql"
            if [ -f "$sql_file" ]; then
                print_color $CYAN "Attempting re-deployment: $obj"
                if python3 "/home/ec2-user/workspace/oma/bin/database/db_conversion.py" deploy "$sql_file"; then
                    print_color $GREEN "✓ $obj re-deployment successful"
                else
                    print_color $RED "✗ $obj re-deployment failed"
                fi
            fi
        else
            print_color $RED "Cannot find original object name: $obj"
        fi
    done
}

# Function to deploy to PostgreSQL
deploy_to_postgresql() {
    if [ -z "$PGHOST" ] || [ -z "$PGDATABASE" ] || [ -z "$PGUSER" ]; then
        print_color $RED "PostgreSQL environment variables not set (PGHOST, PGDATABASE, PGUSER)"
        return 1
    fi
    
    # Test connection first
    print_color $YELLOW "Testing PostgreSQL connection..."
    if ! psql -c "SELECT 1;" >/dev/null 2>&1; then
        print_color $RED "Cannot connect to PostgreSQL database"
        return 1
    fi
    
    print_color $YELLOW "Deploying to PostgreSQL..."
    
    # Deploy in transaction
    local temp_script="$TEMP_DIR/deploy_all.sql"
    echo "BEGIN;" > "$temp_script"
    
    for sql_file in "$CONVERTED_DIR"/*.sql; do
        if [ -f "$sql_file" ]; then
            echo "-- From: $(basename "$sql_file")" >> "$temp_script"
            cat "$sql_file" >> "$temp_script"
            echo "" >> "$temp_script"
        fi
    done
    
    echo "COMMIT;" >> "$temp_script"
    
    print_color $BLUE "Executing deployment script..."
    if psql -f "$temp_script"; then
        print_color $GREEN "All DDL statements applied successfully"
    else
        print_color $RED "Deployment failed - changes rolled back"
        return 1
    fi
}

# Main execution
main() {
    # Check environment variables and set defaults if not provided
    if [ -z "$SOURCE_DBMS_TYPE" ]; then
        export SOURCE_DBMS_TYPE="orcl"
    fi
    
    if [ -z "$TARGET_DBMS_TYPE" ]; then
        export TARGET_DBMS_TYPE="postgres"
    fi
    
    # Check Oracle environment variables for DDL extraction
    if [ -z "$ORACLE_HOST" ] || [ -z "$ORACLE_ADM_USER" ] || [ -z "$ORACLE_ADM_PASSWORD" ]; then
        log_error "Oracle environment variables must be set for DDL extraction"
        print_color $RED "Oracle environment variables must be set for DDL extraction:"
        print_color $RED "ORACLE_HOST, ORACLE_ADM_USER, ORACLE_ADM_PASSWORD"
        print_color $YELLOW "Optional: ORACLE_PORT (default: 1521), ORACLE_SID"
        exit 1
    fi
    
    # Setup trap for cleanup
    trap cleanup_temp_files EXIT
    
    # Step 1: Create target directory
    create_target_directory
    
    # Step 2-3: Handle ZIP file selection/download
    log_info "Starting ZIP file selection"
    select_zip_file
    
    # Step 4: Confirm selection
    while ! confirm_zip_selection; do
        select_zip_file
    done
    
    # Step 5: Analyze ZIP file
    log_info "Starting ZIP file analysis"
    if analyze_zip_file; then
        while true; do
            if handle_conversion_choice; then
                log_info "Conversion process completed successfully"
                break  # Conversion completed successfully
            else
                # User chose to go back, return to file selection
                log_info "User chose to return to previous menu"
                return 1  # Return to restart the process
                return
            fi
        done
    else
        log_info "No complex objects requiring conversion found, completing work"
        print_color $YELLOW "No complex objects requiring conversion found, completing work."
    fi
    
    log_info "Please check the log: $LOG_FILE"
}

# Run main function only if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    handle_initial_mode
fi
