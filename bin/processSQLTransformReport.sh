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

# 환경 변수 확인 함수
check_environment() {
    if [ -z "$APPLICATION_NAME" ]; then
        echo -e "${RED}${BOLD}오류: 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
}

# ====================================================
# SQL Transform 결과 보고서 생성
# ====================================================
generate_sql_transform_report() {
    print_separator
    echo -e "${BLUE}${BOLD}SQL Transform 작업 결과 보고서를 작성합니다.${NC}"
    print_separator
    
    # SQLTransformReport.md 파일 존재 확인
    if [ ! -f "$APP_TOOLS_FOLDER/SQLTransformReport.md" ]; then
        echo -e "${RED}${BOLD}오류: SQLTransformReport.md 파일을 찾을 수 없습니다.${NC}"
        echo -e "${YELLOW}파일 경로: $APP_TOOLS_FOLDER/SQLTransformReport.md${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}보고서 생성 명령을 실행합니다...${NC}"
    sleep 1
    echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/SQLTransformReport.md${NC}"
    
    # Amazon Q를 통한 보고서 생성 실행
    q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/SQLTransformReport.md"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}SQL 변환 작업 보고서가 성공적으로 작성되었습니다.${NC}"
        echo -e "${YELLOW}${BOLD}보고서는 $APP_TOOLS_FOLDER 에서 확인 가능합니다.${NC}"
    else
        echo -e "${RED}보고서 생성 중 오류가 발생했습니다.${NC}"
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

echo -e "${GREEN}현재 설정된 프로젝트: $APPLICATION_NAME${NC}"
print_separator

# 보고서 생성 실행
generate_sql_transform_report

echo -e "${GREEN}SQL Transform 결과 보고서 생성이 완료되었습니다.${NC}"
print_separator
