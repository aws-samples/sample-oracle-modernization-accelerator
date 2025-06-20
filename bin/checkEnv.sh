#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'
UNDERLINE='\033[4m'

# 구분선 출력 함수
print_separator() {
    printf "${BLUE}${BOLD}%80s${NC}\n" | tr " " "="
}

# 화면 지우기
clear

print_separator
echo -e "${BLUE}${BOLD}OMA 환경 변수 확인${NC}"
print_separator

# 환경 변수 파일 자동 로드 시도
ENV_FILE_PATTERN="oma_env_*.sh"
ENV_FILES=($(ls $ENV_FILE_PATTERN 2>/dev/null))

if [ ${#ENV_FILES[@]} -gt 0 ]; then
    # 가장 최근 파일 선택 (여러 개가 있을 경우)
    LATEST_ENV_FILE=$(ls -t $ENV_FILE_PATTERN 2>/dev/null | head -n1)
    echo -e "${CYAN}환경 변수 파일 발견: ${BOLD}$LATEST_ENV_FILE${NC}"
    echo -e "${CYAN}환경 변수를 로드합니다...${NC}"
    source "$LATEST_ENV_FILE"
    echo -e "${GREEN}✓ 환경 변수 로드 완료${NC}"
    print_separator
fi

# 필수 환경 변수 목록 (oma.properties에 실제로 정의된 변수들만)
required_vars=(
    "APPLICATION_NAME"
    "JAVA_SOURCE_FOLDER"
    "OMA_BASE_DIR"
    "APPLICATION_FOLDER"
    "APP_TOOLS_FOLDER"
    "APP_TRANSFORM_FOLDER"
    "APP_LOGS_FOLDER"
    "DBMS_FOLDER"
    "DBMS_LOGS_FOLDER"
    "TEST_FOLDER"
    "TEST_LOGS_FOLDER"
    "TRANSFORM_JNDI"
    "TRANSFORM_RELATED_CLASS"
)

# 선택적 환경 변수 목록 (DB 연결 관련)
optional_vars=(
    "ORACLE_ADM_USER"
    "ORACLE_ADM_PASSWORD"
    "ORACLE_HOST"
    "ORACLE_PORT"
    "ORACLE_SID"
    "PGHOST"
    "PGUSER"
    "PGPASSWORD"
    "PGPORT"
    "PGDATABASE"
)

# 환경 변수 상태 확인
missing_vars=()
set_vars=()

echo -e "${BLUE}${BOLD}[필수 환경 변수]${NC}"
print_separator

for var in "${required_vars[@]}"; do
    if [ -n "${!var}" ]; then
        echo -e "${GREEN}✓ $var: ${!var}${NC}"
        set_vars+=("$var")
    else
        echo -e "${RED}✗ $var: (not set)${NC}"
        missing_vars+=("$var")
    fi
done

print_separator
echo -e "${BLUE}${BOLD}[DB 연결 환경 변수 - 선택사항]${NC}"
print_separator

echo -e "${CYAN}Oracle Connection:${NC}"
for var in "ORACLE_ADM_USER" "ORACLE_ADM_PASSWORD" "ORACLE_HOST" "ORACLE_PORT" "ORACLE_SID"; do
    if [ -n "${!var}" ]; then
        if [ "$var" = "ORACLE_ADM_PASSWORD" ]; then
            echo -e "${GREEN}✓ $var: ********${NC}"
        else
            echo -e "${GREEN}✓ $var: ${!var}${NC}"
        fi
    else
        echo -e "${YELLOW}○ $var: (not set)${NC}"
    fi
done

echo -e "${CYAN}PostgreSQL Connection:${NC}"
for var in "PGHOST" "PGUSER" "PGPASSWORD" "PGPORT" "PGDATABASE"; do
    if [ -n "${!var}" ]; then
        if [ "$var" = "PGPASSWORD" ]; then
            echo -e "${GREEN}✓ $var: ********${NC}"
        else
            echo -e "${GREEN}✓ $var: ${!var}${NC}"
        fi
    else
        echo -e "${YELLOW}○ $var: (not set)${NC}"
    fi
done

print_separator
echo -e "${BLUE}${BOLD}[환경 상태 요약]${NC}"
print_separator

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ 모든 필수 환경 변수가 설정되었습니다!${NC}"
    echo -e "${GREEN}initOMA.sh를 실행할 수 있습니다.${NC}"
    
    # 프로젝트 디렉토리 존재 확인
    if [ -n "$APPLICATION_NAME" ] && [ -n "$OMA_BASE_DIR" ]; then
        project_dir="$OMA_BASE_DIR"
        if [ -d "$project_dir" ]; then
            echo -e "${GREEN}✓ 프로젝트 디렉토리 존재: $project_dir${NC}"
        else
            echo -e "${YELLOW}⚠️  프로젝트 디렉토리가 존재하지 않습니다: $project_dir${NC}"
            echo -e "${CYAN}setEnv.sh를 실행하여 프로젝트 구조를 생성하세요.${NC}"
        fi
    fi
else
    echo -e "${RED}${BOLD}✗ 누락된 필수 환경 변수: ${#missing_vars[@]}개${NC}"
    echo -e "${RED}누락된 변수들:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    echo ""
    echo -e "${YELLOW}${BOLD}해결 방법:${NC}"
    echo -e "${CYAN}1. config/oma.properties 파일에 프로젝트 설정이 있는지 확인${NC}"
    echo -e "${CYAN}2. setEnv.sh를 실행하여 환경 설정 및 프로젝트 구조 생성${NC}"
    echo -e "${CYAN}   ${BOLD}./setEnv.sh${NC}"
fi

print_separator
echo -e "${BLUE}${BOLD}[추가 정보]${NC}"
print_separator
echo -e "${CYAN}설정된 환경 변수 개수: ${GREEN}${#set_vars[@]}${NC}"
echo -e "${CYAN}현재 작업 디렉토리: ${GREEN}$(pwd)${NC}"
echo -e "${CYAN}스크립트 실행 시간: ${GREEN}$(date)${NC}"

if [ -n "$APPLICATION_NAME" ]; then
    echo -e "${CYAN}현재 프로젝트: ${GREEN}${BOLD}$APPLICATION_NAME${NC}"
fi

# 환경 변수 파일 정보 표시
if [ -n "$LATEST_ENV_FILE" ]; then
    echo -e "${CYAN}로드된 환경 변수 파일: ${GREEN}$LATEST_ENV_FILE${NC}"
    echo -e "${CYAN}파일 수정 시간: ${GREEN}$(stat -f "%Sm" "$LATEST_ENV_FILE" 2>/dev/null || stat -c "%y" "$LATEST_ENV_FILE" 2>/dev/null)${NC}"
fi

print_separator
