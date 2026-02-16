#!/bin/bash

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
    printf "${BLUE}${BOLD}%80s${NC}\n" | tr " " " "
}

# ====================================================
# Function to read and parse config/oma.properties file
# ====================================================
read_properties() {
    local APPLICATION_NAME=$1
    local DEBUG_MODE=${2:-false}
    
    if [ "$DEBUG_MODE" = true ]; then
        echo "Debug: Starting to read properties file"
    fi
    
    # Export APPLICATION_NAME immediately (for COMMON section substitution)
    export APPLICATION_NAME="$APPLICATION_NAME"
    
    # 1st step: Read COMMON section first
    local in_common_section=false
    while read -r line || [ -n "$line" ]; do
        # Skip empty lines or comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Split key and value based on = (use only first =)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
        # Remove leading/trailing spaces
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Debug output
        if [ "$DEBUG_MODE" = true ]; then
            echo "Debug: COMMON step - key='$key', value='$value', section_status=$in_common_section"
        fi
        
        # Check if it's COMMON section
        if [[ $key == "[COMMON]" ]]; then
            in_common_section=true
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: COMMON section started"
            fi
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_common_section=false
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: Other section started - $key"
            fi
            continue
        fi
        
        # If in COMMON section and has key-value pair
        if [ "$in_common_section" = true ] && [[ -n $key && -n $value ]]; then
            # Convert key to uppercase and replace spaces with underscores
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            
            # Environment variable expansion (APPLICATION_NAME substitution)
            expanded_value="${value//\$\{APPLICATION_NAME\}/$APPLICATION_NAME}"
            
            # Set environment variable (export as session environment variable)
            export "$env_var"="$expanded_value"
            
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: COMMON environment variable set - $env_var='$expanded_value'"
            fi
        fi
    done < "../config/oma.properties"
    
    # 2nd step: Read project section (override)
    local in_project_section=false
    while read -r line || [ -n "$line" ]; do
        # Skip empty lines or comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Split key and value based on = (use only first =)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
        # Remove leading/trailing spaces
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Debug output
        if [ "$DEBUG_MODE" = true ]; then
            echo "Debug: PROJECT step - key='$key', value='$value', section_status=$in_project_section"
        fi
        
        # Check if it's the correct project section
        if [[ $key == "[$APPLICATION_NAME]" ]]; then
            in_project_section=true
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: Project section [$APPLICATION_NAME] started"
            fi
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_project_section=false
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: Other section started - $key"
            fi
            continue
        fi
        
        # If in correct project section and has key-value pair
        if [ "$in_project_section" = true ] && [[ -n $key && -n $value ]]; then
            # Convert key to uppercase and replace spaces with underscores
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            
            # Environment variable expansion
            expanded_value="${value//\$\{APPLICATION_NAME\}/$APPLICATION_NAME}"
            expanded_value="${expanded_value//\$\{JAVA_SOURCE_FOLDER\}/$JAVA_SOURCE_FOLDER}"
            expanded_value="${expanded_value//\$\{APPLICATION_FOLDER\}/$APPLICATION_FOLDER}"
            expanded_value="${expanded_value//\$\{OMA_BASE_DIR\}/$OMA_BASE_DIR}"
            
            # For TRANSFORM_RELATED_CLASS, maintain comma-separated format
            if [ "$env_var" = "TRANSFORM_RELATED_CLASS" ]; then
                # Maintain comma-separated format while setting environment variable (export as session environment variable)
                export "$env_var"="$expanded_value"
            else
                # General environment variable setting (export as session environment variable)
                export "$env_var"="$expanded_value"
            fi
            
            if [ "$DEBUG_MODE" = true ]; then
                echo "Debug: PROJECT environment variable set - $env_var='$expanded_value'"
            fi
        fi
    done < "../config/oma.properties"
    
    if [ "$DEBUG_MODE" = true ]; then
        echo "Debug: Properties file reading completed"
    fi
}

# ====================================================
# Environment variable output function
# ====================================================
print_environment_variables() {
    print_separator
    echo -e "${BLUE}${BOLD}[Environment Variable Settings Result]${NC}"
    print_separator
    echo -e "${GREEN}APPLICATION_NAME: $APPLICATION_NAME${NC}"
    echo -e "${GREEN}JAVA_SOURCE_FOLDER: $JAVA_SOURCE_FOLDER${NC}"
    echo -e "${GREEN}OMA_BASE_DIR: $OMA_BASE_DIR${NC}"
    echo -e "${GREEN}APPLICATION_FOLDER: $APPLICATION_FOLDER${NC}"
    echo -e "${GREEN}APP_TRANSFORM_FOLDER: $APP_TRANSFORM_FOLDER${NC}"
    echo -e "${GREEN}TEST_FOLDER: $TEST_FOLDER${NC}"
    echo -e "${GREEN}TRANSFORM_JNDI: $TRANSFORM_JNDI${NC}"
    echo -e "${GREEN}TRANSFORM_RELATED_CLASS: $TRANSFORM_RELATED_CLASS${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}[DB Connection Environment Variables]${NC}"
    print_separator
    echo -e "${GREEN}Oracle Connection:${NC}"
    echo -e "${GREEN}  ORACLE_ADM_USER: ${ORACLE_ADM_USER:-'(not set)'}${NC}"
    echo -e "${GREEN}  ORACLE_HOST: ${ORACLE_HOST:-'(not set)'}${NC}"
    echo -e "${GREEN}  ORACLE_PORT: ${ORACLE_PORT:-'(not set)'}${NC}"
    echo -e "${GREEN}  ORACLE_SID: ${ORACLE_SID:-'(not set)'}${NC}"
    echo -e "${GREEN}PostgreSQL Connection:${NC}"
    echo -e "${GREEN}  PGHOST: ${PGHOST:-'(not set)'}${NC}"
    echo -e "${GREEN}  PGUSER: ${PGUSER:-'(not set)'}${NC}"
    echo -e "${GREEN}  PGPORT: ${PGPORT:-'(not set)'}${NC}"
    echo -e "${GREEN}  PGDATABASE: ${PGDATABASE:-'(not set)'}${NC}"
}

# ====================================================
# Application analysis environment setup function
# ====================================================
setup_application_environment() {
    print_separator
    echo -e "${BLUE}${BOLD}Application Analysis Environment Setup${NC}"
    print_separator

    # Check JAVA_SOURCE_FOLDER src directory
    if [ ! -d "$JAVA_SOURCE_FOLDER" ]; then
        echo -e "${RED}Error: $JAVA_SOURCE_FOLDER directory does not exist.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ JAVA_SOURCE_FOLDER src directory check completed${NC}"

    # Check existing analysis content
    local existing_analysis=false
    if [ -d "$APPLICATION_FOLDER" ] && [ "$(ls -A $APPLICATION_FOLDER 2>/dev/null)" ]; then
        existing_analysis=true
        echo -e "${YELLOW}⚠️  Existing analysis content found: $APPLICATION_FOLDER${NC}"
        echo -e "${CYAN}Keeping existing analysis results and skipping script duplication.${NC}"
    fi

    # ====================================================
    # 01.Database directory structure creation
    # ====================================================
    echo -e "${BLUE}${BOLD}01.Database Directory Structure Creation${NC}"
    
    mkdir -p "$DBMS_FOLDER"
    mkdir -p "$DBMS_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ DBMS_FOLDER directory creation completed${NC}"
    echo -e "${GREEN}✓ DBMS_LOGS_FOLDER directory creation completed${NC}"

    # ====================================================
    # 02.Application directory structure creation
    # ====================================================
    echo -e "${BLUE}${BOLD}02.Application Directory Structure Creation${NC}"
    
    mkdir -p "$APPLICATION_FOLDER"
    mkdir -p "$APP_TRANSFORM_FOLDER"
    mkdir -p "$APP_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ APPLICATION_FOLDER directory creation completed${NC}"
    echo -e "${GREEN}✓ APP_TRANSFORM_FOLDER directory creation completed${NC}"
    echo -e "${GREEN}✓ APP_LOGS_FOLDER directory creation completed${NC}"

    # ====================================================
    # 03.Test directory structure creation
    # ====================================================
    echo -e "${BLUE}${BOLD}03.Test Directory Structure Creation${NC}"
    
    mkdir -p "$TEST_FOLDER"
    mkdir -p "$TEST_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ TEST_FOLDER directory creation completed${NC}"
    echo -e "${GREEN}✓ TEST_LOGS_FOLDER directory creation completed${NC}"

    # ====================================================
    # Project structure creation (only when no existing analysis content)
    # ====================================================
    if [ "$existing_analysis" = false ]; then

        
        # Create README file in project root
        local readme_file="$OMA_BASE_DIR/${APPLICATION_NAME}/README.md"
        cat > "$readme_file" << 'EOF'
## Environment Setup
```bash
# Load environment variables
source ./bin/oma_env_${APPLICATION_NAME}.sh

# Check environment variables
./checkEnv.sh
```

## Perform Transformation Tasks
```bash
# Perform necessary tasks in each directory
# Perform necessary tasks in each directory

# Execute by each tool
```

## Directory Structure
- `transform` - DB schema transformation results
- `transform` - Application analysis and transformation results
- `transform` - Test related files

## Notes
- DB related tasks require Oracle/PostgreSQL connection
- Environment variable file must be sourced first
EOF
        
        echo -e "${GREEN}✓ README.md file creation completed${NC}"
        
    else
        print_separator
        echo -e "${CYAN}${BOLD}Existing Analysis Project - Script Update${NC}"
        print_separator
        echo -e "${CYAN}Using existing project structure as is.${NC}"
        
        # Create README file if it doesn't exist
        local readme_file="$OMA_BASE_DIR/${APPLICATION_NAME}/README.md"
        if [ ! -f "$readme_file" ]; then
            cat > "$readme_file" << 'EOF'
# OMA Project Execution Guide

## Environment Setup
```bash
# Load environment variables
source ./bin/oma_env_${APPLICATION_NAME}.sh

# Check environment variables
./checkEnv.sh
```

## Perform Transformation Tasks
```bash
# Perform necessary tasks in each directory
# Perform necessary tasks in each directory

# Execute by each tool
```

## Directory Structure
- `transform` - DB schema transformation results
- `transform` - Application analysis and transformation results
- `transform` - Test related files

## Notes
- DB related tasks require Oracle/PostgreSQL connection
- Environment variable file must be sourced first
EOF
            echo -e "${GREEN}✓ README.md file creation completed${NC}"
        fi
    fi
}

# ====================================================
# Main execution section
# ====================================================

# Check if config/oma.properties file exists
if [ ! -f "../config/oma.properties" ]; then
    echo -e "${RED}Error: config/oma.properties file not found.${NC}"
    exit 1
fi

# Get project list from config/oma.properties (excluding COMMON)
projects=($(grep -o '\[.*\]' ../config/oma.properties | tr -d '[]' | grep -v '^COMMON$'))

if [ ${#projects[@]} -eq 0 ]; then
    echo -e "${RED}Error: No projects defined in config/oma.properties.${NC}"
    exit 1
fi

# Display project selection menu
print_separator
echo -e "${BLUE}${BOLD}Select a project for environment variable setup:${NC}"
print_separator
echo -e "${BLUE}${BOLD}Available project list:${NC}"
for i in "${!projects[@]}"; do
    echo -e "${CYAN}$((i+1)). ${projects[$i]}${NC}"
done

# Get user selection
echo -ne "${BLUE}${BOLD}Select project number (1-${#projects[@]}): ${NC}"
read selection

# Validate selection
if [[ $selection -lt 1 || $selection -gt ${#projects[@]} ]]; then
    echo -e "${RED}Invalid selection. Please enter a number between 1-${#projects[@]}.${NC}"
    exit 1
fi

# Get selected project name
selected_project="${projects[$((selection-1))]}"

# Set project name as environment variable
export APPLICATION_NAME="$selected_project"

# Check debug mode
DEBUG_MODE=false
if [[ "$*" == *"--debug"* ]]; then
    DEBUG_MODE=true
fi

# Read and set properties for selected project
read_properties "$selected_project" "$DEBUG_MODE"

# Automatically perform Application analysis environment setup
echo -e "${BLUE}${BOLD}Selected project: $selected_project${NC}"
echo -e "${CYAN}Automatically performing environment setup...${NC}"
setup_application_environment

# Check and notify existing analysis content (after environment setup)
if [ -d "$APPLICATION_FOLDER" ] && [ "$(ls -A $APPLICATION_FOLDER 2>/dev/null)" ]; then
    print_separator
    echo -e "${YELLOW}${BOLD}⚠️  Existing analysis content found${NC}"
    echo -e "${CYAN}APPLICATION_FOLDER: $APPLICATION_FOLDER${NC}"
    echo -e "${CYAN}Existing analysis results have been protected.${NC}"
    print_separator
    sleep 2
fi

# Output environment variables (only in debug mode)
if [ "$DEBUG_MODE" = true ]; then
    print_environment_variables
fi

echo -e "${GREEN}Environment setup completed.${NC}"
echo -e "${CYAN}Project structure creation completed.${NC}"

# Create environment variable file in current directory and project root
ENV_FILE="./oma_env_${APPLICATION_NAME}.sh"
PROJECT_ENV_FILE="$OMA_BASE_DIR/oma_env_${APPLICATION_NAME}.sh"

echo -e "${BLUE}${BOLD}Saving environment variables to file...${NC}"

# Create environment variable file - handle completely dynamically
cat > "$ENV_FILE" << EOF
#!/bin/bash
# OMA environment variable settings (auto-generated)
# Project: $APPLICATION_NAME
# Creation time: $(date)

EOF

# Dynamically extract all currently set environment variables and save to file
# Check all variables defined in oma.properties
if [ -f "../config/oma.properties" ]; then
    # Collect all defined variables
    all_defined_vars=()
    
    # Process COMMON section
    in_common_section=false
    while read -r line || [ -n "$line" ]; do
        # Skip empty lines or comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Split key and value based on = (use only first =)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
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
            all_defined_vars+=("$env_var")
        fi
    done < "../config/oma.properties"
    
    # Process project section
    in_project_section=false
    while read -r line || [ -n "$line" ]; do
        # Skip empty lines or comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Split key and value based on = (use only first =)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [[ $key == "[$selected_project]" ]]; then
            in_project_section=true
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_project_section=false
            continue
        fi
        
        if [ "$in_project_section" = true ] && [[ -n $key && $key != \#* ]]; then
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            all_defined_vars+=("$env_var")
        fi
    done < "../config/oma.properties"
    
    # Remove duplicates and sort
    unique_vars=($(printf "%s\n" "${all_defined_vars[@]}" | sort -u))
    
    # Save only set environment variables to file
    for var in "${unique_vars[@]}"; do
        if [ -n "${!var}" ]; then
            echo "export $var=\"${!var}\"" >> "$ENV_FILE"
        fi
    done
    
    # Add PATH setting
    echo "" >> "$ENV_FILE"
    echo "# PATH setting" >> "$ENV_FILE"
    echo "export PATH=\"\$APP_TOOLS_FOLDER:\$OMA_BASE_DIR/bin:\$PATH\"" >> "$ENV_FILE"
    
    # Add Alias settings
    echo "" >> "$ENV_FILE"
    echo "# Alias settings" >> "$ENV_FILE"
    echo "alias qlog='cd \$APP_LOGS_FOLDER/qlogs && \$APP_TOOLS_FOLDER/tailLatestLog.sh'" >> "$ENV_FILE"

    # Add NLS environment variables
    echo "" >> "$ENV_FILE"
    echo "# NLS Environment Variables" >> "$ENV_FILE"
    echo "export NLS_DATE_FORMAT=${NLS_DATE_FORMAT}" >> "$ENV_FILE"
    echo "export NLS_LANG=${NLS_LANG}" >> "$ENV_FILE"

    # Add database connection aliases
    echo "" >> "$ENV_FILE"
    echo "# Database Connection Aliases" >> "$ENV_FILE"
    echo "alias sqlplus-oma='sqlplus \$ORACLE_ADM_USER/\$ORACLE_ADM_PASSWORD@\$ORACLE_HOST:1521/\$ORACLE_SID'" >> "$ENV_FILE"
fi

# Grant execute permission to environment variable file
chmod +x "$ENV_FILE"

# Copy environment variable file to project root
cp "$ENV_FILE" "$PROJECT_ENV_FILE"
chmod +x "$PROJECT_ENV_FILE"

echo -e "${GREEN}✓ Environment variable file created: $ENV_FILE${NC}"
echo -e "${GREEN}✓ Environment variable file copied: $PROJECT_ENV_FILE${NC}"

# Set environment variables in current shell
echo -e "${BLUE}${BOLD}Setting environment variables in current shell session...${NC}"
source "$ENV_FILE"

# Update PATH environment variable
echo -e "${BLUE}${BOLD}Updating PATH environment variable...${NC}"
export PATH="$APP_TOOLS_FOLDER:$OMA_BASE_DIR/bin:$PATH"
echo -e "${GREEN}✓ APP_TOOLS_FOLDER and OMA_BASE_DIR/bin added to PATH.${NC}"

echo -e "${GREEN}✓ Environment variables set in current shell session.${NC}"
echo -e "${BLUE}${BOLD}Current project: ${GREEN}$APPLICATION_NAME${NC}"

print_separator
echo -e "${YELLOW}${BOLD}Automatic Environment Variable Loading Setup${NC}"
print_separator
echo -e "${CYAN}Would you like to automatically load OMA environment variables on login?${NC}"
echo -e "${YELLOW}(This will add source command to shell profile)${NC}"
echo -ne "${BLUE}${BOLD}Setup automatic loading (y/N): ${NC}"
read auto_load

if [[ "$auto_load" =~ ^[Yy]$ ]]; then
    # Check current shell
    CURRENT_SHELL=$(basename "$SHELL")
    
    case "$CURRENT_SHELL" in
        "bash")
            PROFILE_FILE="$HOME/.bashrc"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                PROFILE_FILE="$HOME/.bash_profile"
            fi
            ;;
        "zsh")
            PROFILE_FILE="$HOME/.zshrc"
            ;;
        *)
            PROFILE_FILE="$HOME/.profile"
            ;;
    esac
    
    # Absolute path of current directory
    CURRENT_DIR="$(pwd)"
    SOURCE_LINE="source \"$CURRENT_DIR/$ENV_FILE\""
    
    # Check if already added
    if grep -q "$SOURCE_LINE" "$PROFILE_FILE" 2>/dev/null; then
        echo -e "${YELLOW}Already configured in profile: $PROFILE_FILE${NC}"
    else
        # Add to profile file
        echo "" >> "$PROFILE_FILE"
        echo "# OMA environment variable auto-loading ($(date))" >> "$PROFILE_FILE"
        echo "$SOURCE_LINE" >> "$PROFILE_FILE"
        
        echo -e "${GREEN}✓ Auto-loading configuration added to profile: $PROFILE_FILE${NC}"
        echo -e "${CYAN}OMA environment variables will be loaded automatically from next login.${NC}"
        
        # Check if apply to current session immediately
        echo -ne "${BLUE}Apply to current session immediately? (Y/n): ${NC}"
        read apply_now
        if [[ ! "$apply_now" =~ ^[Nn]$ ]]; then
            source "$PROFILE_FILE"
            echo -e "${GREEN}✓ Applied to current session.${NC}"
        fi
    fi
else
    echo -e "${CYAN}Skipping auto-loading setup.${NC}"
fi

print_separator
echo -e "${YELLOW}${BOLD}Usage:${NC}"
echo -e "${CYAN}${BOLD}From bin directory:${NC}"
echo -e "${CYAN}1. Check environment variables: ${BOLD}./checkEnv.sh${NC}"
echo -e "${CYAN}2. Move to project directory: ${BOLD}# Perform necessary tasks in each directory${NC}"
echo -e "${CYAN}3. Manually load environment variables: ${BOLD}source $ENV_FILE${NC}"
echo -e "${CYAN}${BOLD}From project directory($APPLICATION_NAME):${NC}"
echo -e "${CYAN}1. Load environment variables: ${BOLD}source ./oma_env_${APPLICATION_NAME}.sh${NC}"
echo -e "${CYAN}2. Check environment variables: ${BOLD}./checkEnv.sh${NC}"
echo -e "${CYAN}3. Move to project directory: ${BOLD}# Perform necessary tasks in each directory${NC}"
if [[ "$auto_load" =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}4. Remove auto-loading: Delete corresponding line from profile file($PROFILE_FILE)${NC}"
fi
print_separator

echo -e "${YELLOW}Environment variable file locations:${NC}"
echo -e "${GREEN}  - bin directory: $ENV_FILE${NC}"
echo -e "${GREEN}  - project root: $PROJECT_ENV_FILE${NC}"
echo -e "${CYAN}You can move to project directory and work independently.${NC}"
