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

# 환경 변수 확인 함수
check_environment() {
    if [ -z "$APPLICATION_NAME" ]; then
        echo -e "${RED}${BOLD}오류: 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
}

# ====================================================
# Step 3: SQL 변환 작업
# ====================================================

# Merge 모드 처리 함수
process_sql_transform_merge() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 3: SQL 변환 Merge 작업${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 변환된 SQL들을 Merge 처리합니다.${NC}"
    print_separator
    
    echo -e "${BLUE}${BOLD}실행 명령:${NC}"
    echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py --mode merge${NC}"
    print_separator

    echo -e "${BLUE}${BOLD}작업을 수행하기 이전에 3초 대기 합니다.${NC}"
    sleep 3

    python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --mode merge
    print_separator
    echo -e "${GREEN}SQL 변환 Merge 작업이 완료되었습니다.${NC}"
    print_separator
}

process_sql_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 3: SQL 변환 작업${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 SQL 변환 작업을 수행합니다.${NC}"
    print_separator
    
    # 실행 모드 선택
    echo -e "${YELLOW}실행 모드를 선택하세요:${NC}"
    echo -e "${CYAN}1. 선별적 변환 - SQLTransformTargetSelective.csv의 항목만 재변환 (사용자 임의 선택 변환)${NC}"
    echo -e "${CYAN}2. 전체 - SQLTransformTarget.csv의 모든 항목을 변환 (Completed되지 않은 XML 변환 수행)${NC}"
    echo -e "${CYAN}3. 샘플 - SampleTransformTarget.csv의 샘플 항목만 변환 (테스트 목적)${NC}"
    echo ""
    echo -e "${MAGENTA}${BOLD}프로세스 실행시 qlog 를 실행하면 실시간 로그를 확인 할 수 있습니다.${NC}"
    read retry_mode
    retry_mode=${retry_mode:-1}  # 기본값 1
    
    local retry_arg=""
    if [ "$retry_mode" = "1" ]; then
        echo -e "${GREEN}선별적 변환 모드로 실행합니다. SQLTransformTargetSelective.csv의 항목만 처리합니다.${NC}"
        retry_arg="--file $APP_TRANSFORM_FOLDER/SQLTransformTargetSelective.csv"
    elif [ "$retry_mode" = "3" ]; then
        echo -e "${GREEN}샘플 모드로 실행합니다. SampleTransformTarget.csv의 항목만 처리합니다.${NC}"
        retry_arg="--file $APP_TRANSFORM_FOLDER/SampleTransformTarget.csv"
    else
        echo -e "${GREEN}전체 모드로 실행합니다. SQLTransformTarget.csv의 모든 항목을 처리합니다.${NC}"
    fi
    
    echo -e "${BLUE}${BOLD}실행 명령:${NC}"
    echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py $retry_arg${NC}"
    print_separator

    echo -e "${BLUE}${BOLD}작업을 수행하기 이전에 3초 대기 합니다.${NC}"
    sleep 3

    python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" $retry_arg
    print_separator
    echo -e "${GREEN}SQL 변환 작업이 완료되었습니다.${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}SQL Transform 작업 결과는 리포트 작성으로 검증하세요.${NC}"
    echo -e "${YELLOW}${BOLD}$APP_TOOLS_FOLDER 에서 확인 가능합니다.${NC}"
}

# 메인 실행
clear
print_separator
echo -e "${BLUE}${BOLD}Step 3: 애플리케이션 SQL 변환 작업 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}현재 설정된 프로젝트: $APPLICATION_NAME${NC}"
print_separator

# 파라미터 확인 및 처리
if [ "$1" = "merge" ]; then
    # Merge 모드 실행
    process_sql_transform_merge
    echo -e "${GREEN}Step 3: SQL 변환 Merge 작업이 완료되었습니다.${NC}"
else
    # 일반 SQL 변환 작업 실행
    process_sql_transform
    echo -e "${GREEN}Step 3: 애플리케이션 SQL 변환 작업이 완료되었습니다.${NC}"
fi

print_separator
