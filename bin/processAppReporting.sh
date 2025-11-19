#!/bin/bash

# Step 2-2: 분석 보고서 작성 및 SQL변환 대상 추출 스크립트

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
# Step 2-2: Analysis report creation and SQL transformation target extraction
# ====================================================
process_app_reporting() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 2-2: Analysis Report Creation and SQL Transformation Target Extraction${NC}"
    print_separator
    echo -e "${CYAN}This step performs the following tasks:${NC}"
    echo -e "${CYAN}1. Generate HTML analysis report (appReporting.md)${NC}"
    echo -e "${CYAN}2. Generate JNDI and Mapper file combinations${NC}"
    echo -e "${CYAN}3. Extract SQL transformation target list${NC}"
    echo -e "${CYAN}4. Generate integrated analysis report (DiscoveryReport.html)${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}Execution order:${NC}"
    echo -e "${BLUE}${BOLD}1. kiro-cli chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appReporting.md${NC}"
    echo -e "${BLUE}${BOLD}2. python3 $APP_TOOLS_FOLDER/genSqlTransformTarget.py${NC}"

    # 1. Execute appReporting.md (Generate HTML report)
    if [ -f "$APP_TOOLS_FOLDER/appReporting.md" ]; then
        echo -e "${CYAN}1. Generating HTML analysis report...${NC}"
        
        # Create kiro-cli chat log directory
        mkdir -p "$APP_LOGS_FOLDER/qlogs"
        
        # Record start time in log file
        echo "=== kiro-cli chat appReporting.md execution started: $(date) ===" >> "$APP_LOGS_FOLDER/qlogs/appReporting.log"
        
        # Execute kiro-cli chat and save log
        kiro-cli chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appReporting.md" >> "$APP_LOGS_FOLDER/qlogs/appReporting.log" 2>&1
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ HTML analysis report generation completed.${NC}"
            echo "=== kiro-cli chat appReporting.md execution completed: $(date) ===" >> "$APP_LOGS_FOLDER/qlogs/appReporting.log"
        else
            echo -e "${RED}Error: An error occurred during appReporting.md execution.${NC}"
            echo "=== kiro-cli chat appReporting.md execution failed: $(date) ===" >> "$APP_LOGS_FOLDER/qlogs/appReporting.log"
            return 1
        fi
    else
        echo -e "${RED}Error: appReporting.md file not found: $APP_TOOLS_FOLDER/appReporting.md${NC}"
        return 1
    fi

    # 2. Generate JNDI and Mapper file combinations (follow-up processing)
    echo -e "${CYAN}2. Generating JNDI and Mapper file combinations...${NC}"
    if [ -f "$APP_TOOLS_FOLDER/genSqlTransformTarget.py" ]; then
        # Create log directory
        mkdir -p "$APP_LOGS_FOLDER/pylogs"
        
        # Record start time in log file
        echo "=== genSqlTransformTarget.py execution started: $(date) ===" >> "$APP_LOGS_FOLDER/pylogs/genSqlTransformTarget.log"
        
        # Execute Python script and save log
        python3 "$APP_TOOLS_FOLDER/genSqlTransformTarget.py" >> "$APP_LOGS_FOLDER/pylogs/genSqlTransformTarget.log" 2>&1
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ SQL transformation target list extraction completed.${NC}"
            echo "=== genSqlTransformTarget.py execution completed: $(date) ===" >> "$APP_LOGS_FOLDER/pylogs/genSqlTransformTarget.log"
        else
            echo -e "${RED}Error: An error occurred during genSqlTransformTarget.py execution.${NC}"
            echo "=== genSqlTransformTarget.py execution failed: $(date) ===" >> "$APP_LOGS_FOLDER/pylogs/genSqlTransformTarget.log"
            return 1
        fi
    else
        echo -e "${YELLOW}Warning: genSqlTransformTarget.py file not found: $APP_TOOLS_FOLDER/genSqlTransformTarget.py${NC}"
        echo -e "${YELLOW}Skipping SQL transformation target extraction step.${NC}"
    fi
    
    # SQL Mapper Report generation (commented section - activate if needed)
    #echo -e "${BLUE}${BOLD}kiro-cli chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/GenSQLMapperReport.txt${NC}"
    #kiro-cli chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/GenSQLMapperReport.txt"

    # SQL Transform Target Report generation (commented section - activate if needed)
    #echo -e "${BLUE}${BOLD}Generating SQL Transform Target Report.${NC}"
    #python3 "$APP_TOOLS_FOLDER/ReportSQLTransformTarget.py"
}

# 메인 실행
clear
print_separator
echo -e "${BLUE}${BOLD}Step 2-2: Application Report & Extract Transform SQL Target${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}Currently configured project: $APPLICATION_NAME${NC}"
print_separator

# 분석 보고서 작성 실행
process_app_reporting

echo -e "${GREEN}Step 2-2: Analysis report creation and SQL transformation target extraction task completed.${NC}"
echo -e "${YELLOW}Next step: Execute 'PostgreSQL database metadata creation' or 'SQL transformation task'.${NC}"
print_separator
