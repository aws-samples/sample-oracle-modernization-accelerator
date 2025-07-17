#!/bin/bash

# Step 1: DB Schema 변환 스크립트

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
    
    if [ -z "$DBMS_FOLDER" ]; then
        echo -e "${RED}${BOLD}오류: DBMS_FOLDER 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
    
    if [ -z "$DBMS_LOGS_FOLDER" ]; then
        echo -e "${RED}${BOLD}오류: DBMS_LOGS_FOLDER 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
}

# ====================================================
# Step 1: DB Schema 변환
# ====================================================
process_db_schema_conversion() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 1: DB Schema 변환${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 데이터베이스 스키마 변환 작업을 수행합니다.${NC}"
    echo -e "${CYAN}Oracle 스키마를 PostgreSQL로 변환하는 작업을 수행합니다.${NC}"
    print_separator
    
    # DB Schema 변환을 위한 환경 변수 설정
    # 템플릿 파일 경로 (bin/database에 있는 파일을 직접 사용)
    local TEMPLATE_ASCT_PROGRAM="$OMA_BASE_DIR/bin/database/asct.py"
    
    # 필수 디렉토리 확인 및 생성
    if [ ! -d "$DBMS_FOLDER" ]; then
        echo -e "${YELLOW}DBMS 디렉토리가 존재하지 않습니다. 생성합니다: $DBMS_FOLDER${NC}"
        mkdir -p "$DBMS_FOLDER"
    fi
    
    if [ ! -d "$DBMS_LOGS_FOLDER" ]; then
        echo -e "${YELLOW}Logs 디렉토리가 존재하지 않습니다. 생성합니다: $DBMS_LOGS_FOLDER${NC}"
        mkdir -p "$DBMS_LOGS_FOLDER"
    fi
    
    # 템플릿 파일 경로 확인 (bin/database에 있는 파일을 직접 사용)
    local TEMPLATE_ASCT_PROGRAM="$OMA_BASE_DIR/bin/database/asct.py"
    
    # 템플릿 파일 존재 확인
    if [ ! -f "$TEMPLATE_ASCT_PROGRAM" ]; then
        echo -e "${RED}오류: 템플릿 파일을 찾을 수 없습니다: $TEMPLATE_ASCT_PROGRAM${NC}"
        return 1
    fi
    
    # Oracle 연결 환경 변수 확인
    if [ -z "$ORACLE_ADM_USER" ] || [ -z "$ORACLE_ADM_PASSWORD" ] || [ -z "$ORACLE_HOST" ]; then
        echo -e "${YELLOW}경고: Oracle 연결 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}필요한 환경 변수: ORACLE_ADM_USER, ORACLE_ADM_PASSWORD, ORACLE_HOST, ORACLE_PORT, ORACLE_SID${NC}"
        echo -e "${CYAN}계속 진행하시겠습니까? (y/N): ${NC}"
        read continue_without_oracle
        if [[ ! "$continue_without_oracle" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}DB Schema 변환을 취소합니다.${NC}"
            return 1
        fi
    fi
    
    # PostgreSQL 연결 환경 변수 확인
    if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGDATABASE" ]; then
        echo -e "${YELLOW}경고: PostgreSQL 연결 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}필요한 환경 변수: PGHOST, PGUSER, PGDATABASE, PGPASSWORD${NC}"
        echo -e "${CYAN}계속 진행하시겠습니까? (y/N): ${NC}"
        read continue_without_postgres
        if [[ ! "$continue_without_postgres" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}DB Schema 변환을 취소합니다.${NC}"
            return 1
        fi
    fi
    
    # ASCT_HOME 환경 변수 설정 (DBMS 폴더를 기준으로)
    export ASCT_HOME="$DBMS_FOLDER"
    
    echo -e "${GREEN}환경 변수 설정:${NC}"
    echo -e "${GREEN}  ASCT_HOME: $ASCT_HOME${NC}"
    echo -e "${GREEN}  DBMS_FOLDER: $DBMS_FOLDER${NC}"
    echo -e "${GREEN}  TEMPLATE_ASCT_PROGRAM: $TEMPLATE_ASCT_PROGRAM${NC}"
    echo -e "${GREEN}  DBMS_LOGS_FOLDER: $DBMS_LOGS_FOLDER${NC}"
    print_separator
    
    # 실행 모드 선택
    echo -e "${BLUE}${BOLD}DB Schema 변환 실행 모드를 선택하세요:${NC}"
    echo -e "${CYAN}1. 전체 변환 - 모든 스키마 객체를 변환합니다${NC}"
    echo -e "${CYAN}2. PostgreSQL 배포만 - 이미 변환된 스키마를 PostgreSQL에 배포합니다${NC}"
    echo -e "${CYAN}3. 취소${NC}"
    echo -ne "${BLUE}${BOLD}모드를 선택하세요 (1-3): ${NC}"
    read db_mode
    
    case $db_mode in
        1)
            echo -e "${GREEN}전체 변환 모드로 실행합니다.${NC}"
            echo -e "${BLUE}${BOLD}실행 명령:${NC}"
            echo -e "${BLUE}${BOLD}cd $DBMS_FOLDER && python3 $TEMPLATE_ASCT_PROGRAM${NC}"
            print_separator
            
            echo -e "${BLUE}${BOLD}DB Schema 변환을 시작합니다...${NC}"
            cd "$DBMS_FOLDER"
            python3 "$TEMPLATE_ASCT_PROGRAM"
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}DB Schema 변환이 성공적으로 완료되었습니다.${NC}"
                echo -e "${CYAN}변환 결과는 다음 위치에서 확인할 수 있습니다:${NC}"
                echo -e "${CYAN}  - 변환된 스키마: $DBMS_FOLDER/Transform/${NC}"
                echo -e "${CYAN}  - 변환 로그: $DBMS_LOGS_FOLDER/${NC}"
            else
                echo -e "${RED}DB Schema 변환 중 오류가 발생했습니다.${NC}"
                echo -e "${YELLOW}로그를 확인하세요: $DBMS_LOGS_FOLDER/asct.log${NC}"
            fi
            ;;
        2)
            echo -e "${GREEN}PostgreSQL 배포 모드로 실행합니다.${NC}"
            echo -e "${BLUE}${BOLD}실행 명령:${NC}"
            echo -e "${BLUE}${BOLD}cd $DBMS_FOLDER && python3 $TEMPLATE_ASCT_PROGRAM --deploy-only${NC}"
            print_separator
            
            echo -e "${BLUE}${BOLD}PostgreSQL 배포를 시작합니다...${NC}"
            cd "$DBMS_FOLDER"
            python3 "$TEMPLATE_ASCT_PROGRAM" --deploy-only
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}PostgreSQL 배포가 성공적으로 완료되었습니다.${NC}"
            else
                echo -e "${RED}PostgreSQL 배포 중 오류가 발생했습니다.${NC}"
                echo -e "${YELLOW}로그를 확인하세요: $DBMS_LOGS_FOLDER/asct.log${NC}"
            fi
            ;;
        3)
            echo -e "${YELLOW}DB Schema 변환을 취소합니다.${NC}"
            return 0
            ;;
        *)
            echo -e "${RED}잘못된 선택입니다.${NC}"
            return 1
            ;;
    esac
    
    print_separator
}

# 메인 실행
clear
print_separator
echo -e "${BLUE}${BOLD}Step 1: DB Schema 변환 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

echo -e "${GREEN}현재 설정된 프로젝트: $APPLICATION_NAME${NC}"
print_separator

# DB Schema 변환 실행
process_db_schema_conversion

echo -e "${GREEN}Step 1: DB Schema 변환 작업이 완료되었습니다.${NC}"
print_separator
