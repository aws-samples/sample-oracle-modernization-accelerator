#!/bin/bash

# 색상 정의
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

# Clear screen
clear

print_separator
echo -e "${BLUE}${BOLD}OMA Environment Variable Check${NC}"
print_separator

# Attempt to automatically load environment variable file
ENV_FILE_PATTERN="oma_env_*.sh"
ENV_FILES=($(ls $ENV_FILE_PATTERN 2>/dev/null))

if [ ${#ENV_FILES[@]} -gt 0 ]; then
    # Select most recent file (if multiple exist)
    LATEST_ENV_FILE=$(ls -t $ENV_FILE_PATTERN 2>/dev/null | head -n1)
    echo -e "${CYAN}Environment variable file found: ${BOLD}$LATEST_ENV_FILE${NC}"
    echo -e "${CYAN}Loading environment variables...${NC}"
    source "$LATEST_ENV_FILE"
    echo -e "${GREEN}✓ Environment variable loading completed${NC}"
    print_separator
fi

# ====================================================
# Dynamically extract all environment variables from oma.properties
# ====================================================
get_all_properties_variables() {
    local APPLICATION_NAME=$1
    local all_vars=()
    
    if [ ! -f "../config/oma.properties" ]; then
        echo -e "${RED}Error: config/oma.properties file not found.${NC}"
        return 1
    fi
    
    # Extract variables from COMMON section
    local in_common_section=false
    while IFS='=' read -r key value || [ -n "$key" ]; do
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [[ $key == "[COMMON]" ]]; then
            in_common_section=true
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_common_section=false
            continue
        fi
        
        if [ "$in_common_section" = true ] && [[ -n $key && $key != \#* ]]; then
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            all_vars+=("$env_var")
        fi
    done < "../config/oma.properties"
    
    # Extract variables from project section
    if [ -n "$APPLICATION_NAME" ]; then
        local in_project_section=false
        while IFS='=' read -r key value || [ -n "$key" ]; do
            key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            if [[ $key == "[$APPLICATION_NAME]" ]]; then
                in_project_section=true
                continue
            elif [[ $key =~ ^\[.*\]$ ]]; then
                in_project_section=false
                continue
            fi
            
            if [ "$in_project_section" = true ] && [[ -n $key && $key != \#* ]]; then
                env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
                all_vars+=("$env_var")
            fi
        done < "../config/oma.properties"
    fi
    
    # Remove duplicates and sort
    all_properties_vars=($(printf "%s\n" "${all_vars[@]}" | sort -u))
}

# Dynamically extracted list of all environment variables
all_properties_vars=()

# Check current APPLICATION_NAME
current_app_name="$APPLICATION_NAME"

# Dynamically extract all environment variable list from oma.properties
get_all_properties_variables "$current_app_name"

# Check environment variable status
missing_vars=()
set_vars=()
core_vars=()
db_vars=()
other_vars=()

# Automatically categorize variables by category
for var in "${all_properties_vars[@]}"; do
    if [[ $var =~ ^(APPLICATION_NAME|JAVA_SOURCE_FOLDER|OMA_BASE_DIR|.*_FOLDER|TRANSFORM_.*|TARGET_DBMS_TYPE|SQL_MAPPER_FOLDER)$ ]]; then
        core_vars+=("$var")
    elif [[ $var =~ ^(ORACLE_|PG) ]]; then
        db_vars+=("$var")
    else
        other_vars+=("$var")
    fi
done

# Output core environment variables
echo -e "${BLUE}${BOLD}[Core Environment Variables]${NC}"
print_separator

for var in "${core_vars[@]}"; do
    if [ -n "${!var}" ]; then
        echo -e "${GREEN}✓ $var: ${!var}${NC}"
        set_vars+=("$var")
    else
        echo -e "${RED}✗ $var: (not set)${NC}"
        missing_vars+=("$var")
    fi
done

# Output DB-related environment variables
if [ ${#db_vars[@]} -gt 0 ]; then
    print_separator
    echo -e "${BLUE}${BOLD}[DB Connection Environment Variables]${NC}"
    print_separator
    
    # Automatically categorize Oracle and PostgreSQL variables
    oracle_vars=()
    pg_vars=()
    
    for var in "${db_vars[@]}"; do
        if [[ $var =~ ^ORACLE_ ]]; then
            oracle_vars+=("$var")
        elif [[ $var =~ ^PG ]]; then
            pg_vars+=("$var")
        fi
    done
    
    # Output Oracle variables
    if [ ${#oracle_vars[@]} -gt 0 ]; then
        echo -e "${CYAN}Oracle Connection:${NC}"
        for var in "${oracle_vars[@]}"; do
            if [ -n "${!var}" ]; then
                if [[ $var =~ PASSWORD ]]; then
                    echo -e "${GREEN}✓ $var: ********${NC}"
                else
                    echo -e "${GREEN}✓ $var: ${!var}${NC}"
                fi
            else
                echo -e "${YELLOW}○ $var: (not set)${NC}"
            fi
        done
    fi
    
    # Output PostgreSQL variables
    if [ ${#pg_vars[@]} -gt 0 ]; then
        echo -e "${CYAN}PostgreSQL Connection:${NC}"
        for var in "${pg_vars[@]}"; do
            if [ -n "${!var}" ]; then
                if [[ $var =~ PASSWORD ]]; then
                    echo -e "${GREEN}✓ $var: ********${NC}"
                else
                    echo -e "${GREEN}✓ $var: ${!var}${NC}"
                fi
            else
                echo -e "${YELLOW}○ $var: (not set)${NC}"
            fi
        done
    fi
fi

# Output other environment variables
if [ ${#other_vars[@]} -gt 0 ]; then
    print_separator
    echo -e "${BLUE}${BOLD}[Other Environment Variables]${NC}"
    print_separator
    
    for var in "${other_vars[@]}"; do
        if [ -n "${!var}" ]; then
            if [[ $var =~ PASSWORD ]]; then
                echo -e "${GREEN}✓ $var: ********${NC}"
            else
                echo -e "${GREEN}✓ $var: ${!var}${NC}"
            fi
        else
            echo -e "${YELLOW}○ $var: (not set)${NC}"
        fi
    done
fi

print_separator
echo -e "${BLUE}${BOLD}[Environment Status Summary]${NC}"
print_separator

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ All required environment variables are set!${NC}"
    echo -e "${GREEN}You can run initOMA.sh.${NC}"
    
    # Check project directory existence
    if [ -n "$APPLICATION_NAME" ] && [ -n "$OMA_BASE_DIR" ]; then
        project_dir="$OMA_BASE_DIR"
        if [ -d "$project_dir" ]; then
            echo -e "${GREEN}✓ Project directory exists: $project_dir${NC}"
        else
            echo -e "${YELLOW}⚠️  Project directory does not exist: $project_dir${NC}"
            echo -e "${CYAN}Run setEnv.sh to create project structure.${NC}"
        fi
    fi
else
    echo -e "${RED}${BOLD}✗ Missing required environment variables: ${#missing_vars[@]} variables${NC}"
    echo -e "${RED}Missing variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    echo ""
    echo -e "${YELLOW}${BOLD}Solution:${NC}"
    echo -e "${CYAN}1. Check if project settings exist in config/oma.properties file${NC}"
    echo -e "${CYAN}2. Run setEnv.sh to set up environment and create project structure${NC}"
    echo -e "${CYAN}   ${BOLD}./setEnv.sh${NC}"
fi

print_separator
echo -e "${BLUE}${BOLD}[Additional Information]${NC}"
print_separator
echo -e "${CYAN}Number of set environment variables: ${GREEN}${#set_vars[@]}${NC}"
echo -e "${CYAN}Current working directory: ${GREEN}$(pwd)${NC}"
echo -e "${CYAN}Script execution time: ${GREEN}$(date)${NC}"

if [ -n "$APPLICATION_NAME" ]; then
    echo -e "${CYAN}Current project: ${GREEN}${BOLD}$APPLICATION_NAME${NC}"
fi

# Display environment variable file information
if [ -n "$LATEST_ENV_FILE" ]; then
    echo -e "${CYAN}Loaded environment variable file: ${GREEN}$LATEST_ENV_FILE${NC}"
    echo -e "${CYAN}File modification time: ${GREEN}$(stat -f "%Sm" "$LATEST_ENV_FILE" 2>/dev/null || stat -c "%y" "$LATEST_ENV_FILE" 2>/dev/null)${NC}"
fi

print_separator
