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

# 환경 변수 확인 함수
check_environment() {
    if [ -z "$APPLICATION_NAME" ]; then
        echo -e "${RED}${BOLD}오류: 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
}

# ====================================================
# Step 2-2: 분석 보고서 작성 및 SQL변환 대상 추출
# ====================================================
process_app_reporting() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 2-2: 분석 보고서 작성 및 SQL변환 대상 추출${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 다음 작업을 수행합니다:${NC}"
    echo -e "${CYAN}1. HTML 분석 리포트 생성 (appReporting.md)${NC}"
    echo -e "${CYAN}2. JNDI와 Mapper 파일 조합 생성${NC}"
    echo -e "${CYAN}3. SQL 변환 대상 목록 추출${NC}"
    echo -e "${CYAN}4. 통합 분석 리포트 (DiscoveryReport.html) 생성${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}실행 순서:${NC}"
    echo -e "${BLUE}${BOLD}1. q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appReporting.md${NC}"
    echo -e "${BLUE}${BOLD}2. python3 $APP_TOOLS_FOLDER/genSqlTransformTarget.py${NC}"

    # 1. appReporting.md 실행 (HTML 리포트 생성)
    if [ -f "$APP_TOOLS_FOLDER/appReporting.md" ]; then
        echo -e "${CYAN}1. HTML 분석 리포트 생성 중...${NC}"
        q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appReporting.md"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ HTML 분석 리포트 생성이 완료되었습니다.${NC}"
        else
            echo -e "${RED}오류: appReporting.md 실행 중 오류가 발생했습니다.${NC}"
            return 1
        fi
    else
        echo -e "${RED}오류: appReporting.md 파일을 찾을 수 없습니다: $APP_TOOLS_FOLDER/appReporting.md${NC}"
        return 1
    fi

    # 2. JNDI와 Mapper 파일 조합 생성 (후속 처리)
    echo -e "${CYAN}2. JNDI와 Mapper 파일 조합 생성 중...${NC}"
    if [ -f "$APP_TOOLS_FOLDER/genSqlTransformTarget.py" ]; then
        python3 "$APP_TOOLS_FOLDER/genSqlTransformTarget.py"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ SQL 변환 대상 목록 추출이 완료되었습니다.${NC}"
        else
            echo -e "${RED}오류: genSqlTransformTarget.py 실행 중 오류가 발생했습니다.${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}경고: genSqlTransformTarget.py 파일을 찾을 수 없습니다: $APP_TOOLS_FOLDER/genSqlTransformTarget.py${NC}"
        echo -e "${YELLOW}SQL 변환 대상 추출 단계를 건너뜁니다.${NC}"
    fi
    
    # SQL Mapper Report 생성 (주석 처리된 부분 - 필요시 활성화)
    #echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/GenSQLMapperReport.txt${NC}"
    #q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/GenSQLMapperReport.txt"

    # SQL Transform Target Report 생성 (주석 처리된 부분 - 필요시 활성화)
    #echo -e "${BLUE}${BOLD}SQL Transform Target Report 생성중입니다.${NC}"
    #python3 "$APP_TOOLS_FOLDER/ReportSQLTransformTarget.py"
}

# 메인 실행
clear
print_separator
echo -e "${BLUE}${BOLD}Step 2-2: 분석 보고서 작성 및 SQL변환 대상 추출 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}현재 설정된 프로젝트: $APPLICATION_NAME${NC}"
print_separator

# 분석 보고서 작성 실행
process_app_reporting

echo -e "${GREEN}Step 2-2: 분석 보고서 작성 및 SQL변환 대상 추출 작업이 완료되었습니다.${NC}"
echo -e "${YELLOW}다음 단계: 'PostgreSQL 데이터베이스 메타데이터 작성' 또는 'SQL 변환 작업'을 실행하세요.${NC}"
print_separator
