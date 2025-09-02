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

# 환경 변수 확인 함수
check_environment() {
    if [ -z "$APPLICATION_NAME" ]; then
        echo -e "${RED}${BOLD}오류: 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
}

# ====================================================
# Step 2-1: 애플리케이션 분석 데이터 생성
# ====================================================
process_app_analysis() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 2-1: 애플리케이션 분석 데이터 생성${NC}"
    print_separator
    
    # 로그 디렉토리 생성
    mkdir -p "$APP_LOGS_FOLDER/qlogs"
    LOG_FILE="$APP_LOGS_FOLDER/qlogs/appAnalysis.log"
    
    echo -e "${CYAN}이 단계에서는 다음 작업을 수행합니다:${NC}"
    echo -e "${CYAN}1. Java 소스 코드 분석${NC}"
    echo -e "${CYAN}2. MyBatis Mapper 파일 분석${NC}"
    echo -e "${CYAN}3. JNDI 설정 정보 추출${NC}"
    echo -e "${CYAN}4. SQL 패턴 발견 및 기초 분석${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}실행 명령:${NC}"
    echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/appAnalysis.md${NC}"
    echo -e "${YELLOW}로그 파일: $LOG_FILE${NC}"

    # appAnalysis.md 실행 (분석 데이터 생성) - 로그 저장
    if [ -f "$APP_TOOLS_FOLDER/appAnalysis.md" ]; then
        echo -e "${CYAN}애플리케이션 분석 데이터 생성 중...${NC}"
        
        # 로그 파일 헤더 작성
        echo "=== 애플리케이션 분석 시작: $(date) ===" > "$LOG_FILE"
        echo "프로젝트: $APPLICATION_NAME" >> "$LOG_FILE"
        echo "Java 소스 폴더: $JAVA_SOURCE_FOLDER" >> "$LOG_FILE"
        echo "Mapper 폴더: $SOURCE_SQL_MAPPER_FOLDER" >> "$LOG_FILE"
        echo "Target DBMS: $TARGET_DBMS_TYPE" >> "$LOG_FILE"
        echo "========================================" >> "$LOG_FILE"
        
        # Q Chat 실행 및 로그 저장
        q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appAnalysis.md" >> "$LOG_FILE" 2>&1
        
        # 실행 결과 확인
        if [ $? -eq 0 ]; then
            echo "=== 애플리케이션 분석 완료: $(date) ===" >> "$LOG_FILE"
            echo -e "${GREEN}✓ 애플리케이션 분석 데이터 생성이 완료되었습니다.${NC}"
            echo -e "${GREEN}✓ 로그 파일 저장 완료: $LOG_FILE${NC}"
        else
            echo "=== 애플리케이션 분석 오류 발생: $(date) ===" >> "$LOG_FILE"
            echo -e "${RED}오류: appAnalysis.md 실행 중 오류가 발생했습니다.${NC}"
            echo -e "${RED}로그 파일을 확인하세요: $LOG_FILE${NC}"
            return 1
        fi
    else
        echo -e "${RED}오류: appAnalysis.md 파일을 찾을 수 없습니다: $APP_TOOLS_FOLDER/appAnalysis.md${NC}"
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

echo -e "${GREEN}현재 설정된 프로젝트: $APPLICATION_NAME${NC}"
print_separator

# 애플리케이션 분석 실행
process_app_analysis

echo -e "${GREEN}Step 2-1: 애플리케이션 분석 작업이 완료되었습니다.${NC}"
echo -e "${YELLOW}다음 단계: '분석 보고서 작성 및 SQL변환 대상 추출'을 실행하세요.${NC}"
print_separator
