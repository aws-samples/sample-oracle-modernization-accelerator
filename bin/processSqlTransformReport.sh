#!/bin/bash

# SQL Transform 결과 보고서 생성 스크립트

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
# SQL Transform Result Report Generation
# ====================================================
generate_sql_transform_report() {
    print_separator
    echo -e "${BLUE}${BOLD}Generating SQL Transform work result report.${NC}"
    print_separator
    
    # Check if sqlTransformReport.md file exists
    if [ ! -f "$APP_TOOLS_FOLDER/sqlTransformReport.md" ]; then
        echo -e "${RED}${BOLD}Error: sqlTransformReport.md file not found.${NC}"
        echo -e "${YELLOW}File path: $APP_TOOLS_FOLDER/sqlTransformReport.md${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}Executing report generation command...${NC}"
    sleep 1
    echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/sqlTransformReport.md${NC}"
    
    # Execute report generation through Amazon Q
    q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/sqlTransformReport.md"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}SQL transformation work report has been successfully created.${NC}"
        echo -e "${YELLOW}${BOLD}Report can be checked at $APP_TOOLS_FOLDER.${NC}"
    else
        echo -e "${RED}An error occurred during report generation.${NC}"
        return 1
    fi
    
    sleep 1
    print_separator
}

# 메인 실행
clear
print_separator
echo -e "${BLUE}${BOLD}SQL Transform 결과 보고서 생성 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}Currently configured project: $APPLICATION_NAME${NC}"
print_separator

# 보고서 생성 실행
generate_sql_transform_report

echo -e "${GREEN}SQL Transform result report generation completed.${NC}"
print_separator
