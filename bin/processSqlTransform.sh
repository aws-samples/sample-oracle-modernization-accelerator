#!/bin/bash

# Step 3: 애플리케이션 SQL 변환 작업 스크립트

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
# Step 3: SQL 변환 작업
# ====================================================

# Merge mode processing function
process_sql_transform_merge() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 3: SQL Transform Merge Task${NC}"
    print_separator
    echo -e "${CYAN}This step performs merge processing of transformed SQLs.${NC}"
    print_separator
    
    echo -e "${BLUE}${BOLD}Execution command:${NC}"
    echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py --mode merge${NC}"
    print_separator

    echo -e "${BLUE}${BOLD}Waiting 3 seconds before performing the task.${NC}"
    sleep 3

    python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --mode merge
    print_separator
    echo -e "${GREEN}SQL Transform Merge task completed.${NC}"
    print_separator
}

process_sql_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 3: SQL Transform Task${NC}"
    print_separator
    echo -e "${CYAN}This step performs SQL transformation tasks.${NC}"
    print_separator
    
    # Select execution mode
    echo -e "${YELLOW}Select execution mode:${NC}"
    echo -e "${CYAN}1. Selective transformation - Re-transform only items in SQLTransformTargetSelective.csv (User arbitrary selection transformation)${NC}"
    echo -e "${CYAN}2. Full - Transform all items in SQLTransformTarget.csv (Perform XML transformation for non-Completed items)${NC}"
    echo -e "${CYAN}3. Sample - Transform only sample items in SampleTransformTarget.csv (For testing purposes)${NC}"
    echo ""
    echo -e "${MAGENTA}${BOLD}You can check real-time logs by running qlog during process execution.${NC}"
    read retry_mode
    retry_mode=${retry_mode:-1}  # Default value 1
    
    local retry_arg=""
    if [ "$retry_mode" = "1" ]; then
        echo -e "${GREEN}Running in selective transformation mode. Processing only items in SQLTransformTargetSelective.csv.${NC}"
        retry_arg="--file $APP_TRANSFORM_FOLDER/SQLTransformTargetSelective.csv"
    elif [ "$retry_mode" = "3" ]; then
        echo -e "${GREEN}Running in sample mode. Processing only items in SampleTransformTarget.csv.${NC}"
        retry_arg="--file $APP_TRANSFORM_FOLDER/SampleTransformTarget.csv"
    else
        echo -e "${GREEN}Running in full mode. Processing all items in SQLTransformTarget.csv.${NC}"
    fi
    
    echo -e "${BLUE}${BOLD}Execution command:${NC}"
    echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py $retry_arg${NC}"
    print_separator

    echo -e "${BLUE}${BOLD}Waiting 3 seconds before performing the task.${NC}"
    sleep 3

    python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" $retry_arg
    print_separator
    echo -e "${GREEN}SQL transformation task completed.${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}Verify SQL Transform task results by creating a report.${NC}"
    echo -e "${YELLOW}${BOLD}Available at $APP_TOOLS_FOLDER.${NC}"
}

# 메인 실행
clear
print_separator
echo -e "${BLUE}${BOLD}Step 3: 애플리케이션 SQL 변환 작업 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}Currently configured project: $APPLICATION_NAME${NC}"
print_separator

# 파라미터 확인 및 처리
if [ "$1" = "merge" ]; then
    # Execute Merge mode
    process_sql_transform_merge
    echo -e "${GREEN}Step 3: SQL Transform Merge task completed.${NC}"
else
    # Execute general SQL transformation task
    process_sql_transform
    echo -e "${GREEN}Step 3: Application SQL transformation task completed.${NC}"
fi

print_separator
