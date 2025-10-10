#!/bin/bash

# MyBatis bulk parameter extraction script (with DB sample value collection)
# Usage: ./bulk_prepare.sh <directory_path>

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
show_help() {
    echo -e "${BLUE}MyBatis Bulk Parameter Extraction Script (with DB Sample Value Collection)${NC}"
    echo ""
    echo "Usage:"
    echo "  $0 <directory_path>"
    echo ""
    echo "Example:"
    echo "  $0 /home/ec2-user/workspace/src-orcl/src/main/resources/sqlmap/mapper"
    echo ""
    echo "Description:"
    echo "  - Recursively search all XML files in the specified directory"
    echo "  - Automatically extract all parameters and generate unified parameters.properties"
    echo "  - Automatically collect actual sample values from Oracle DB (YYYY-MM-DD date format)"
    echo "  - Automatically remove duplicate parameters and sort alphabetically"
    echo ""
    echo "Environment variable requirements:"
    echo "  - ORACLE_SVC_USER: Oracle username"
    echo "  - ORACLE_SVC_PASSWORD: Oracle password"
    echo "  - ORACLE_SVC_CONNECT_STRING: Oracle connection string"
    echo ""
    echo "Features:"
    echo "  🎯 Generate sample values based on actual data"
    echo "  🤖 Automatic parameter-column name matching"
    echo "  📊 High accuracy test data"
    echo "  ⚡ Save 50-70% of manual work"
    echo ""
}

# Parameter validation
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

MAPPER_DIR="$1"

# Check directory existence
if [ ! -d "$MAPPER_DIR" ]; then
    echo -e "${RED}Error: Directory does not exist: $MAPPER_DIR${NC}"
    exit 1
fi

# Check current directory
CURRENT_DIR=$(pwd)
if [ ! -f "$CURRENT_DIR/lib/mybatis-3.5.13.jar" ]; then
    echo -e "${RED}Error: lib/mybatis-3.5.13.jar file not found.${NC}"
    echo -e "${YELLOW}Current directory: $CURRENT_DIR${NC}"
    exit 1
fi

# Check Oracle JDBC driver
if [ ! -f "$CURRENT_DIR/lib/ojdbc8-21.9.0.0.jar" ]; then
    echo -e "${RED}Error: lib/ojdbc8-21.9.0.0.jar file not found.${NC}"
    exit 1
fi

# Check Java class file
if [ ! -f "$CURRENT_DIR/com/test/mybatis/MyBatisBulkPreparator.class" ]; then
    echo -e "${YELLOW}Java class file not found. Attempting to compile...${NC}"
    
    if [ ! -f "$CURRENT_DIR/com/test/mybatis/MyBatisBulkPreparator.java" ]; then
        echo -e "${RED}Error: MyBatisBulkPreparator.java file not found.${NC}"
        exit 1
    fi
    
    javac -cp ".:lib/*" com/test/mybatis/*.java
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Compilation failed.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Compilation completed${NC}"
fi

# Check Oracle environment variables
echo -e "${BLUE}=== Oracle Environment Variable Check ===${NC}"
if [ -z "$ORACLE_SVC_USER" ]; then
    echo -e "${RED}Warning: ORACLE_SVC_USER environment variable is not set.${NC}"
    echo -e "${YELLOW}Only basic parameter extraction will be performed without DB sample value collection.${NC}"
    DB_MODE=""
else
    echo -e "${GREEN}Oracle user: $ORACLE_SVC_USER${NC}"
    if [ -n "$ORACLE_SVC_CONNECT_STRING" ]; then
        echo -e "${GREEN}Oracle connection: $ORACLE_SVC_CONNECT_STRING${NC}"
    fi
    DB_MODE="--db oracle --date-format YYYY-MM-DD"
fi

echo -e "${BLUE}=== MyBatis Bulk Parameter Extraction + DB Sample Value Collection Started ===${NC}"
echo -e "Search directory: ${YELLOW}$MAPPER_DIR${NC}"
if [ -n "$DB_MODE" ]; then
    echo -e "DB mode: ${GREEN}Oracle (YYYY-MM-DD date format)${NC}"
else
    echo -e "DB mode: ${YELLOW}Disabled (parameter extraction only)${NC}"
fi
echo ""

# Backup existing parameter file
if [ -f "$TEST_FOLDER/parameters.properties" ]; then
    BACKUP_FILE="$TEST_FOLDER/parameters.properties.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$TEST_FOLDER/parameters.properties" "$BACKUP_FILE"
    echo -e "${YELLOW}Existing parameter file backed up: $BACKUP_FILE${NC}"
fi

# Execute bulk preparation program
echo -e "${GREEN}Extracting parameters and collecting DB sample values...${NC}"
if [ -n "$DB_MODE" ]; then
    java -cp ".:lib/*" com.test.mybatis.MyBatisBulkPreparator "$MAPPER_DIR" $DB_MODE
else
    java -cp ".:lib/*" com.test.mybatis.MyBatisBulkPreparator "$MAPPER_DIR"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== Parameter Extraction Completed ===${NC}"
    
    if [ -f "$TEST_FOLDER/parameters.properties" ]; then
        PARAM_COUNT=$(grep -c "^[^#].*=" "$TEST_FOLDER/parameters.properties" 2>/dev/null | tr -d '\n' || echo "0")
        SAMPLE_COUNT=$(grep -c "매치$" "$TEST_FOLDER/parameters.properties" 2>/dev/null | tr -d '\n' || echo "0")
        
        # Ensure variables are numeric
        if ! [[ "$PARAM_COUNT" =~ ^[0-9]+$ ]]; then
            PARAM_COUNT=0
        fi
        if ! [[ "$SAMPLE_COUNT" =~ ^[0-9]+$ ]]; then
            SAMPLE_COUNT=0
        fi
        
        MANUAL_COUNT=$((PARAM_COUNT - SAMPLE_COUNT))
        
        echo -e "Generated file: ${YELLOW}$TEST_FOLDER/parameters.properties${NC}"
        echo -e "Total parameters: ${YELLOW}$PARAM_COUNT${NC}"
        
        if [ -n "$DB_MODE" ] && [ $SAMPLE_COUNT -gt 0 ]; then
            if [ $PARAM_COUNT -gt 0 ]; then
                SAMPLE_RATE=$(awk "BEGIN {printf \"%.1f\", $SAMPLE_COUNT * 100 / $PARAM_COUNT}")
            else
                SAMPLE_RATE="0.0"
            fi
            echo -e "DB sample values: ${GREEN}$SAMPLE_COUNT (${SAMPLE_RATE}%)${NC}"
            echo -e "Manual setup required: ${YELLOW}$MANUAL_COUNT${NC}"
            echo ""
            echo -e "${GREEN}🎯 Sample values based on actual production data have been automatically set!${NC}"
        fi
        
        echo ""
        echo -e "${BLUE}Next steps:${NC}"
        echo -e "1. Check and modify ${YELLOW}$TEST_FOLDER/parameters.properties${NC} file if needed"
        echo -e "2. Execute with ${YELLOW}./bulk_execute.sh${NC} or ${YELLOW}./bulk_json.sh${NC}"
        echo ""
        echo -e "${GREEN}Parameter file preview (first 15 lines):${NC}"
        head -15 "$TEST_FOLDER/parameters.properties"
        
        if [ $PARAM_COUNT -gt 15 ]; then
            echo -e "${BLUE}... (total $PARAM_COUNT parameters)${NC}"
        fi
    else
        echo -e "${RED}Error: $TEST_FOLDER/parameters.properties file was not created.${NC}"
        exit 1
    fi
else
    echo -e "${RED}Error: Parameter extraction failed.${NC}"
    exit 1
fi
