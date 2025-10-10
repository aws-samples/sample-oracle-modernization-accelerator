#!/bin/bash

# Step 2-1: 애플리케이션 분석 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# 구분선 출력 함수
print_separator() {
    printf "${BLUE}${BOLD}%80s${NC}\n" | tr " " "="
}

# Environment variable check function
check_environment() {
    if [ -z "$APPLICATION_NAME" ]; then
        echo -e "${RED}${BOLD}Error: Environment variables are not set.${NC}"
        echo -e "${YELLOW}Please source the environment variable file. Example: source ./oma_env_projectname.sh${NC}"
        exit 1
    fi
}

# ====================================================
# Step 2-1: Application analysis data generation
# ====================================================
process_app_analysis() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 2-1: Application Analysis Data Generation${NC}"
    print_separator
    
    # Create log directory
    mkdir -p "$APP_LOGS_FOLDER/qlogs"
    LOG_FILE="$APP_LOGS_FOLDER/qlogs/appAnalysis.log"
    
    echo -e "${CYAN}This step performs the following tasks:${NC}"
    echo -e "${CYAN}1. Java source code analysis${NC}"
    echo -e "${CYAN}2. MyBatis Mapper file analysis${NC}"
    echo -e "${CYAN}3. JNDI configuration information extraction${NC}"
    echo -e "${CYAN}4. SQL pattern discovery and basic analysis${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}Execution command:${NC}"
    echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appAnalysis.md${NC}"
    echo -e "${YELLOW}Log file: $LOG_FILE${NC}"

    # Execute appAnalysis.md (Generate analysis data) - Save log
    if [ -f "$APP_TOOLS_FOLDER/appAnalysis.md" ]; then
        echo -e "${CYAN}Generating application analysis data...${NC}"
        
        # Write log file header
        echo "=== Application analysis started: $(date) ===" > "$LOG_FILE"
        echo "Project: $APPLICATION_NAME" >> "$LOG_FILE"
        echo "Java source folder: $JAVA_SOURCE_FOLDER" >> "$LOG_FILE"
        echo "Mapper folder: $SOURCE_SQL_MAPPER_FOLDER" >> "$LOG_FILE"
        echo "Target DBMS: $TARGET_DBMS_TYPE" >> "$LOG_FILE"
        echo "========================================" >> "$LOG_FILE"
        
        # Execute Q Chat and save log
        q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appAnalysis.md" >> "$LOG_FILE" 2>&1
        
        # Check execution result
        if [ $? -eq 0 ]; then
            echo "=== Application analysis completed: $(date) ===" >> "$LOG_FILE"
            echo -e "${GREEN}✓ Application analysis data generation completed.${NC}"
            echo -e "${GREEN}✓ Log file saved: $LOG_FILE${NC}"
        else
            echo "=== Application analysis error occurred: $(date) ===" >> "$LOG_FILE"
            echo -e "${RED}Error: An error occurred during appAnalysis.md execution.${NC}"
            echo -e "${RED}Please check the log file: $LOG_FILE${NC}"
            return 1
        fi
    else
        echo -e "${RED}Error: appAnalysis.md file not found: $APP_TOOLS_FOLDER/appAnalysis.md${NC}"
        return 1
    fi
}

# 메인 실행
clear
print_separator
echo -e "${BLUE}${BOLD}Step 2-1: 애플리케이션 분석 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}Currently configured project: $APPLICATION_NAME${NC}"
print_separator

# 애플리케이션 분석 실행
process_app_analysis

echo -e "${GREEN}Step 2-1: Application analysis task completed.${NC}"
echo -e "${YELLOW}Next step: Execute 'Analysis report creation and SQL transformation target extraction'.${NC}"
print_separator
