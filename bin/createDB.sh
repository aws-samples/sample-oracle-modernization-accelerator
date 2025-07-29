#!/bin/bash

# MySQL Database 생성 스크립트

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

# 환경 변수 확인 함수
check_environment() {
    if [ -z "$MYSQL_HOST" ] || [ -z "$MYSQL_TCP_PORT" ] || [ -z "$MYSQL_ADM_USER" ] || [ -z "$MYSQL_PASSWORD" ]; then
        echo -e "${RED}${BOLD}오류: MySQL 연결 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}필요한 환경 변수: MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_ADM_USER, MYSQL_PASSWORD${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ MySQL 연결 환경 변수 확인 완료${NC}"
    echo -e "${CYAN}  MYSQL_HOST: $MYSQL_HOST${NC}"
    echo -e "${CYAN}  MYSQL_TCP_PORT: $MYSQL_TCP_PORT${NC}"
    echo -e "${CYAN}  MYSQL_ADM_USER: $MYSQL_ADM_USER${NC}"
    echo -e "${CYAN}  MYSQL_PASSWORD: [설정됨]${NC}"
}

# MySQL 연결 테스트 함수
test_mysql_connection() {
    echo -e "${BLUE}${BOLD}MySQL 연결 테스트 중...${NC}"
    
    # MySQL 연결 테스트
    mysql -h$MYSQL_HOST -P$MYSQL_TCP_PORT -u$MYSQL_ADM_USER -p$MYSQL_PASSWORD -e "SELECT 1;" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ MySQL 연결 성공${NC}"
        return 0
    else
        echo -e "${RED}✗ MySQL 연결 실패${NC}"
        echo -e "${YELLOW}연결 정보를 확인하세요:${NC}"
        echo -e "${YELLOW}  Host: $MYSQL_HOST${NC}"
        echo -e "${YELLOW}  Port: $MYSQL_TCP_PORT${NC}"
        echo -e "${YELLOW}  User: $MYSQL_ADM_USER${NC}"
        return 1
    fi
}

# 데이터베이스 생성 함수
create_database() {
    local db_name="$1"
    local charset="$2"
    local collate="$3"
    
    print_separator
    echo -e "${BLUE}${BOLD}MySQL 데이터베이스 생성${NC}"
    print_separator
    
    echo -e "${CYAN}생성할 데이터베이스 정보:${NC}"
    echo -e "${CYAN}  데이터베이스명: $db_name${NC}"
    echo -e "${CYAN}  CHARACTER SET: $charset${NC}"
    echo -e "${CYAN}  COLLATE: $collate${NC}"
    print_separator
    
    # 데이터베이스 존재 여부 확인
    echo -e "${BLUE}${BOLD}기존 데이터베이스 확인 중...${NC}"
    
    DB_EXISTS=$(mysql -h$MYSQL_HOST -P$MYSQL_TCP_PORT -u$MYSQL_ADM_USER -p$MYSQL_PASSWORD -e "SHOW DATABASES LIKE '$db_name';" 2>/dev/null | grep -c "$db_name")
    
    if [ "$DB_EXISTS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  데이터베이스 '$db_name'이 이미 존재합니다.${NC}"
        echo -ne "${BLUE}${BOLD}기존 데이터베이스를 삭제하고 다시 생성하시겠습니까? (y/N): ${NC}"
        read recreate_db
        
        if [[ "$recreate_db" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}기존 데이터베이스를 삭제합니다...${NC}"
            mysql -h$MYSQL_HOST -P$MYSQL_TCP_PORT -u$MYSQL_ADM_USER -p$MYSQL_PASSWORD -e "DROP DATABASE \`$db_name\`;" 2>/dev/null
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ 기존 데이터베이스 삭제 완료${NC}"
            else
                echo -e "${RED}✗ 기존 데이터베이스 삭제 실패${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}데이터베이스 생성을 취소합니다.${NC}"
            return 0
        fi
    fi
    
    # 데이터베이스 생성 SQL 구성
    CREATE_SQL="CREATE DATABASE \`$db_name\` CHARACTER SET $charset COLLATE $collate;"
    
    echo -e "${BLUE}${BOLD}실행할 SQL:${NC}"
    echo -e "${CYAN}$CREATE_SQL${NC}"
    print_separator
    
    echo -ne "${BLUE}${BOLD}데이터베이스를 생성하시겠습니까? (Y/n): ${NC}"
    read confirm_create
    
    if [[ ! "$confirm_create" =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}${BOLD}데이터베이스 생성 중...${NC}"
        
        mysql -h$MYSQL_HOST -P$MYSQL_TCP_PORT -u$MYSQL_ADM_USER -p$MYSQL_PASSWORD -e "$CREATE_SQL"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 데이터베이스 '$db_name' 생성 성공${NC}"
            
            # 생성된 데이터베이스 정보 확인
            echo -e "${BLUE}${BOLD}생성된 데이터베이스 정보 확인:${NC}"
            mysql -h$MYSQL_HOST -P$MYSQL_TCP_PORT -u$MYSQL_ADM_USER -p$MYSQL_PASSWORD -e "SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '$db_name';"
            
            return 0
        else
            echo -e "${RED}✗ 데이터베이스 생성 실패${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}데이터베이스 생성을 취소합니다.${NC}"
        return 0
    fi
}

# 메인 실행 부분
clear
print_separator
echo -e "${BLUE}${BOLD}MySQL Database 생성 스크립트${NC}"
print_separator

# 환경 변수 확인
check_environment

# MySQL 연결 테스트
if ! test_mysql_connection; then
    echo -e "${RED}MySQL 연결에 실패했습니다. 환경 변수와 네트워크 연결을 확인하세요.${NC}"
    exit 1
fi

print_separator
echo -e "${BLUE}${BOLD}데이터베이스 생성 설정${NC}"
print_separator

# 데이터베이스 이름 입력 (기본값: MYSQL_DATABASE 환경 변수)
DEFAULT_DB_NAME="${MYSQL_DATABASE:-devdb}"
echo -ne "${BLUE}${BOLD}데이터베이스 이름 [$DEFAULT_DB_NAME]: ${NC}"
read db_name
db_name=${db_name:-$DEFAULT_DB_NAME}

# CHARACTER SET 입력 (기본값: utf8mb4)
DEFAULT_CHARSET="utf8mb4"
echo -ne "${BLUE}${BOLD}CHARACTER SET [$DEFAULT_CHARSET]: ${NC}"
read charset
charset=${charset:-$DEFAULT_CHARSET}

# COLLATE 입력 (기본값: utf8mb4_bin)
DEFAULT_COLLATE="utf8mb4_bin"
echo -ne "${BLUE}${BOLD}COLLATE [$DEFAULT_COLLATE]: ${NC}"
read collate
collate=${collate:-$DEFAULT_COLLATE}

# 입력값 검증
if [ -z "$db_name" ]; then
    echo -e "${RED}오류: 데이터베이스 이름이 비어있습니다.${NC}"
    exit 1
fi

if [ -z "$charset" ]; then
    echo -e "${RED}오류: CHARACTER SET이 비어있습니다.${NC}"
    exit 1
fi

if [ -z "$collate" ]; then
    echo -e "${RED}오류: COLLATE가 비어있습니다.${NC}"
    exit 1
fi

# 데이터베이스 생성 실행
create_database "$db_name" "$charset" "$collate"

if [ $? -eq 0 ]; then
    print_separator
    echo -e "${GREEN}${BOLD}데이터베이스 생성 작업이 완료되었습니다.${NC}"
    print_separator
    
    echo -e "${CYAN}${BOLD}생성된 데이터베이스 연결 정보:${NC}"
    echo -e "${CYAN}  Host: $MYSQL_HOST${NC}"
    echo -e "${CYAN}  Port: $MYSQL_TCP_PORT${NC}"
    echo -e "${CYAN}  Database: $db_name${NC}"
    echo -e "${CYAN}  CHARACTER SET: $charset${NC}"
    echo -e "${CYAN}  COLLATE: $collate${NC}"
    
    echo -e "${YELLOW}${BOLD}연결 테스트:${NC}"
    echo -e "${YELLOW}mysql -h$MYSQL_HOST -P$MYSQL_TCP_PORT -u$MYSQL_ADM_USER -p$MYSQL_PASSWORD $db_name${NC}"
    
    print_separator
else
    echo -e "${RED}데이터베이스 생성에 실패했습니다.${NC}"
    exit 1
fi

