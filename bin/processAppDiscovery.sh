#!/bin/bash

# Step 2: 애플리케이션 Discovery 및 SQL변환 대상 추출 스크립트

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
# Step 2: JNDI and XML Mapper information verification and listing for MyBatis-based Java applications
# ====================================================
process_mybatis_info() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 2: JNDI and XML Mapper Information Verification and Listing for MyBatis-based Java Applications${NC}"
    print_separator
    echo -e "${CYAN}This step performs the following tasks sequentially:${NC}"
    echo -e "${CYAN}1. Generate application analysis data (appAnalysis.md)${NC}"
    echo -e "${CYAN}2. Generate HTML report (appReporting.md)${NC}"
    echo -e "${CYAN}3. Extract JNDI information and generate mapping information${NC}"
    echo -e "${CYAN}4. Discover and analyze SQL patterns${NC}"
    echo -e "${CYAN}5. Generate integrated analysis report (DiscoveryReport.html)${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}Execution order:${NC}"
    echo -e "${BLUE}${BOLD}1. kiro-cli chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appAnalysis.md${NC}"
    echo -e "${BLUE}${BOLD}2. kiro-cli chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appReporting.md${NC}"

    # 1. Execute appAnalysis.md (Generate analysis data)
    if [ -f "$APP_TOOLS_FOLDER/appAnalysis.md" ]; then
        echo -e "${CYAN}1. Generating application analysis data...${NC}"
        echo -e "${BLUE}${BOLD}kiro-cli chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appAnalysis.md${NC}"
        kiro-cli chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appAnalysis.md"
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: An error occurred during appAnalysis.md execution.${NC}"
            return 1
        fi
    else
        echo -e "${RED}Error: appAnalysis.md file not found: $APP_TOOLS_FOLDER/appAnalysis.md${NC}"
        return 1
    fi

    # 2. Execute appReporting.md (Generate HTML report)
    if [ -f "$APP_TOOLS_FOLDER/appReporting.md" ]; then
        echo -e "${CYAN}2. Generating HTML report...${NC}"
        echo -e "${BLUE}${BOLD}kiro-cli chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appReporting.md${NC}"
        kiro-cli chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appReporting.md"
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: An error occurred during appReporting.md execution.${NC}"
            return 1
        fi
    else
        echo -e "${RED}Error: appReporting.md file not found: $APP_TOOLS_FOLDER/appReporting.md${NC}"
        return 1
    fi

    # Previous q call method (commented out)
    # if [ -f "$APP_TOOLS_FOLDER/appDiscovery.txt" ]; then
    #     echo -e "${CYAN}Analyzing application and extracting MyBatis information...${NC}"
    #     echo -e "${BLUE}${BOLD}kiro-cli chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appDiscovery.txt${NC}"
    #     kiro-cli chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appDiscovery.txt"
    # else
    #     echo -e "${RED}Error: appDiscovery.txt file not found: $APP_TOOLS_FOLDER/appDiscovery.txt${NC}"
    #     return 1
    # fi

    # Generate JNDI and Mapper file combinations (follow-up processing)
    echo -e "${BLUE}${BOLD}Generating JNDI and Mapper file combinations.${NC}"
    if [ -f "$APP_TOOLS_FOLDER/genSqlTransformTarget.py" ]; then
        python3 "$APP_TOOLS_FOLDER/genSqlTransformTarget.py"
    else
        echo -e "${YELLOW}Warning: genSqlTransformTarget.py file not found.${NC}"
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
echo -e "${BLUE}${BOLD}Step 2: 애플리케이션 Discovery 및 SQL변환 대상 추출 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}Currently configured project: $APPLICATION_NAME${NC}"
print_separator

# 애플리케이션 분석 실행
process_mybatis_info

echo -e "${GREEN}Step 2: Application Discovery and SQL transformation target extraction task completed.${NC}"
print_separator
