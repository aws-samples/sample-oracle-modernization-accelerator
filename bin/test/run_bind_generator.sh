#!/bin/bash

# =============================================================================
# Bind Variable Generator Execution Script
# Oracle Dictionary + Mapper Bind Variable Extraction + Matching
# =============================================================================

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Move to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}===============================================================================${NC}"
echo -e "${CYAN}🗄️  Oracle Dictionary-based Bind Variable Generator${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""

# Check mapper directory
MAPPER_DIR="$1"
if [[ -z "$MAPPER_DIR" ]]; then
    MAPPER_DIR="/home/ec2-user/workspace/src-orcl/src/main/resources/sqlmap/mapper"
fi

if [[ ! -d "$MAPPER_DIR" ]]; then
    echo -e "${RED}❌ Mapper directory not found: $MAPPER_DIR${NC}"
    echo -e "${YELLOW}Usage: $0 [mapper_directory]${NC}"
    echo -e "${YELLOW}Example: $0 ~/workspace/src-orcl/src/main/resources/sqlmap/mapper${NC}"
    exit 1
fi

# Set TEST_FOLDER (use mapper directory if environment variable is not set)
TEST_FOLDER="${TEST_FOLDER:-$MAPPER_DIR}"

echo -e "${BLUE}📁 Mapper directory: $MAPPER_DIR${NC}"

# Check environment variables
if [[ -z "$ORACLE_HOST" || -z "$ORACLE_SVC_USER" || -z "$ORACLE_SVC_PASSWORD" ]]; then
    echo -e "${RED}❌ Oracle environment variables are not set.${NC}"
    echo -e "${YELLOW}Required environment variables: ORACLE_HOST, ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_SID${NC}"
    exit 1
fi

# Check libraries
if [[ ! -f "lib/ojdbc8-21.9.0.0.jar" ]]; then
    echo -e "${RED}❌ Oracle JDBC driver not found: lib/ojdbc8-21.9.0.0.jar${NC}"
    exit 1
fi

# Check compilation
if [[ ! -f "com/test/mybatis/SimpleBindVariableGenerator.class" ]]; then
    echo -e "${YELLOW}⚠️  Class file not found. Starting compilation...${NC}"
    javac -cp ".:lib/*" com/test/mybatis/SimpleBindVariableGenerator.java
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ Compilation failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Compilation completed${NC}"
fi

# Backup existing result file
if [[ -f "$TEST_FOLDER/parameters.properties" ]]; then
    mv "$TEST_FOLDER/parameters.properties" "$TEST_FOLDER/parameters.properties.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓ Existing parameters.properties backed up${NC}"
fi

# Create output directory
mkdir -p out

echo ""
echo -e "${CYAN}🚀 Starting Bind Variable Generator Execution${NC}"
echo ""

# Measure execution time
START_TIME=$(date +%s)

# Execute SimpleBindVariableGenerator
java -cp ".:lib/*" com.test.mybatis.SimpleBindVariableGenerator "$MAPPER_DIR" "$TEST_FOLDER"

EXIT_CODE=$?

# Calculate execution time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${CYAN}===============================================================================${NC}"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}🎉 Bind Variable Generator Execution Completed!${NC}"
    echo ""
    
    # Check result file
    if [[ -f "$TEST_FOLDER/parameters.properties" ]]; then
        TOTAL_VARS=$(grep -c "^[^#].*=" "$TEST_FOLDER/parameters.properties" 2>/dev/null || echo "0")
        MATCHED_VARS=$(grep -B1 "^[^#].*=" "$TEST_FOLDER/parameters.properties" | grep -c "# OMA\." 2>/dev/null || echo "0")
        UNMATCHED_VARS=$((TOTAL_VARS - MATCHED_VARS))
        
        echo -e "${GREEN}✓ parameters.properties generated${NC}"
        echo -e "${BLUE}  - Total variables: ${TOTAL_VARS}${NC}"
        echo -e "${BLUE}  - Matched: ${MATCHED_VARS}${NC}"
        echo -e "${BLUE}  - Unmatched: ${UNMATCHED_VARS}${NC}"
        
        if [[ $UNMATCHED_VARS -gt 0 ]]; then
            echo ""
            echo -e "${YELLOW}📝 Unmatched variables (check bottom of file):${NC}"
            grep -A1 "# 매칭되지 않은 변수들" "$TEST_FOLDER/parameters.properties" | grep "^[^#]" | head -5
            if [[ $UNMATCHED_VARS -gt 5 ]]; then
                echo -e "${YELLOW}... and $((UNMATCHED_VARS - 5)) more${NC}"
            fi
        fi
        
        echo ""
        echo -e "${CYAN}📋 parameters.properties preview:${NC}"
        echo -e "${YELLOW}$(head -15 "$TEST_FOLDER/parameters.properties")${NC}"
        if [[ $(wc -l < "$TEST_FOLDER/parameters.properties") -gt 15 ]]; then
            echo -e "${YELLOW}... (total $(wc -l < "$TEST_FOLDER/parameters.properties") lines)${NC}"
        fi
    else
        echo -e "${RED}❌ parameters.properties file was not generated.${NC}"
    fi
    
    # Check dictionary file
    DICT_FILE=$(ls -t out/oracle_dictionary_*.json 2>/dev/null | head -1)
    if [[ -n "$DICT_FILE" ]]; then
        echo -e "${GREEN}✓ Oracle dictionary: $(basename "$DICT_FILE")${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}⏱️  Execution time: ${DURATION} seconds${NC}"
    
    echo ""
    echo -e "${CYAN}📖 Next steps:${NC}"
    echo -e "${YELLOW}1. Modify values for unmatched variables in parameters.properties file${NC}"
    echo -e "${YELLOW}2. Execute MyBatis test:${NC}"
    echo -e "${YELLOW}   ./run_oracle.sh $MAPPER_DIR --json${NC}"
    
else
    echo -e "${RED}❌ Bind Variable Generator execution failed (exit code: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}Check logs to resolve the issue.${NC}"
fi

echo -e "${CYAN}===============================================================================${NC}"

exit $EXIT_CODE
