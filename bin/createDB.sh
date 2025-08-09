#!/bin/bash

# 통합 Database 생성 스크립트 (PostgreSQL/MySQL)
# TARGET_DBMS_TYPE 환경 변수에 따라 적절한 데이터베이스 생성

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

# TARGET_DBMS_TYPE 확인 함수
check_target_dbms_type() {
    if [ -z "$TARGET_DBMS_TYPE" ]; then
        echo -e "${RED}${BOLD}오류: TARGET_DBMS_TYPE 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}TARGET_DBMS_TYPE을 'postgres' (PostgreSQL) 또는 'mysql' (MySQL)로 설정하세요.${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
    
    case "$TARGET_DBMS_TYPE" in
        "postgres"|"postgresql")
            TARGET_DBMS_TYPE="postgres"
            echo -e "${GREEN}✓ 타겟 DBMS: PostgreSQL${NC}"
            ;;
        "mysql")
            echo -e "${GREEN}✓ 타겟 DBMS: MySQL${NC}"
            ;;
        *)
            echo -e "${RED}${BOLD}오류: 지원하지 않는 TARGET_DBMS_TYPE입니다: $TARGET_DBMS_TYPE${NC}"
            echo -e "${YELLOW}지원되는 값: 'postgres', 'postgresql', 'mysql'${NC}"
            exit 1
            ;;
    esac
}

# PostgreSQL 환경 변수 확인 함수
check_postgresql_environment() {
    if [ -z "$PGHOST" ] || [ -z "$PGPORT" ] || [ -z "$PG_ADM_USER" ] || [ -z "$PG_ADM_PASSWORD" ] || [ -z "$PGDATABASE" ]; then
        echo -e "${RED}${BOLD}오류: PostgreSQL 연결 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}필요한 환경 변수: PGHOST, PGPORT, PG_ADM_USER, PG_ADM_PASSWORD, PGDATABASE${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
    
    if [ -z "$PG_SVC_USER" ] || [ -z "$PG_SVC_PASSWORD" ]; then
        echo -e "${RED}${BOLD}오류: PostgreSQL 서비스 사용자 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}필요한 환경 변수: PG_SVC_USER, PG_SVC_PASSWORD${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ PostgreSQL 연결 환경 변수 확인 완료${NC}"
    echo -e "${CYAN}  PGHOST: $PGHOST${NC}"
    echo -e "${CYAN}  PGPORT: $PGPORT${NC}"
    echo -e "${CYAN}  PG_ADM_USER: $PG_ADM_USER${NC}"
    echo -e "${CYAN}  PG_ADM_PASSWORD: [설정됨]${NC}"
    echo -e "${CYAN}  PGDATABASE: $PGDATABASE${NC}"
    echo -e "${CYAN}  PG_SVC_USER: $PG_SVC_USER${NC}"
    echo -e "${CYAN}  PG_SVC_PASSWORD: [설정됨]${NC}"
}

# MySQL 환경 변수 확인 함수
check_mysql_environment() {
    if [ -z "$MYSQL_HOST" ] || [ -z "$MYSQL_TCP_PORT" ] || [ -z "$MYSQL_ADM_USER" ] || [ -z "$MYSQL_PASSWORD" ] || [ -z "$MYSQL_DATABASE" ]; then
        echo -e "${RED}${BOLD}오류: MySQL 연결 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}필요한 환경 변수: MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_ADM_USER, MYSQL_PASSWORD, MYSQL_DATABASE${NC}"
        echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ MySQL 연결 환경 변수 확인 완료${NC}"
    echo -e "${CYAN}  MYSQL_HOST: $MYSQL_HOST${NC}"
    echo -e "${CYAN}  MYSQL_TCP_PORT: $MYSQL_TCP_PORT${NC}"
    echo -e "${CYAN}  MYSQL_ADM_USER: $MYSQL_ADM_USER${NC}"
    echo -e "${CYAN}  MYSQL_PASSWORD: [설정됨]${NC}"
    echo -e "${CYAN}  MYSQL_DATABASE: $MYSQL_DATABASE${NC}"
}

# PostgreSQL 연결 테스트 함수
test_postgresql_connection() {
    echo -e "${BLUE}${BOLD}PostgreSQL 연결 테스트 중...${NC}"
    
    # PostgreSQL 연결 테스트 (postgres 데이터베이스에 연결)
    PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "SELECT 1;" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PostgreSQL 연결 성공${NC}"
        return 0
    else
        echo -e "${RED}✗ PostgreSQL 연결 실패${NC}"
        echo -e "${YELLOW}연결 정보를 확인하세요:${NC}"
        echo -e "${YELLOW}  Host: $PGHOST${NC}"
        echo -e "${YELLOW}  Port: $PGPORT${NC}"
        echo -e "${YELLOW}  User: $PG_ADM_USER${NC}"
        return 1
    fi
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

# PostgreSQL 서비스 사용자 생성 함수
create_postgresql_service_user() {
    local db_name="$1"
    
    print_separator
    echo -e "${BLUE}${BOLD}PostgreSQL 서비스 사용자 생성${NC}"
    print_separator
    
    echo -e "${CYAN}생성할 서비스 사용자 정보:${NC}"
    echo -e "${CYAN}  사용자명: $PG_SVC_USER${NC}"
    echo -e "${CYAN}  패스워드: [설정됨]${NC}"
    echo -e "${CYAN}  대상 데이터베이스: $db_name${NC}"
    print_separator
    
    # 사용자 존재 여부 확인
    echo -e "${BLUE}${BOLD}기존 사용자 확인 중...${NC}"
    
    USER_EXISTS=$(PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -t -c "SELECT 1 FROM pg_roles WHERE rolname = '$PG_SVC_USER';" 2>/dev/null | grep -c "1")
    
    if [ "$USER_EXISTS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  사용자 '$PG_SVC_USER'가 이미 존재합니다.${NC}"
        echo -ne "${BLUE}${BOLD}기존 사용자를 삭제하고 다시 생성하시겠습니까? (y/N): ${NC}"
        read recreate_user
        
        if [[ "$recreate_user" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}기존 사용자를 삭제합니다...${NC}"
            
            # 사용자 삭제
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "DROP USER IF EXISTS \"$PG_SVC_USER\";" 2>/dev/null
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ 기존 사용자 삭제 완료${NC}"
            else
                echo -e "${RED}✗ 기존 사용자 삭제 실패${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}사용자 생성을 취소합니다.${NC}"
            return 0
        fi
    fi
    
    # 사용자 생성 SQL 구성
    CREATE_USER_SQL="CREATE USER \"$PG_SVC_USER\" WITH PASSWORD '$PG_SVC_PASSWORD';"
    GRANT_CONNECT_SQL="GRANT CONNECT ON DATABASE \"$db_name\" TO \"$PG_SVC_USER\";"
    GRANT_USAGE_SQL="GRANT USAGE ON SCHEMA public TO \"$PG_SVC_USER\";"
    GRANT_ALL_SQL="GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"$PG_SVC_USER\";"
    GRANT_SEQUENCES_SQL="GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"$PG_SVC_USER\";"
    ALTER_DEFAULT_PRIVILEGES_TABLES_SQL="ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"$PG_SVC_USER\";"
    ALTER_DEFAULT_PRIVILEGES_SEQUENCES_SQL="ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO \"$PG_SVC_USER\";"
    
    echo -e "${BLUE}${BOLD}실행할 SQL:${NC}"
    echo -e "${CYAN}$CREATE_USER_SQL${NC}"
    echo -e "${CYAN}$GRANT_CONNECT_SQL${NC}"
    echo -e "${CYAN}$GRANT_USAGE_SQL${NC}"
    echo -e "${CYAN}$GRANT_ALL_SQL${NC}"
    echo -e "${CYAN}$GRANT_SEQUENCES_SQL${NC}"
    echo -e "${CYAN}$ALTER_DEFAULT_PRIVILEGES_TABLES_SQL${NC}"
    echo -e "${CYAN}$ALTER_DEFAULT_PRIVILEGES_SEQUENCES_SQL${NC}"
    print_separator
    
    echo -ne "${BLUE}${BOLD}서비스 사용자를 생성하시겠습니까? (Y/n): ${NC}"
    read confirm_create_user
    
    if [[ ! "$confirm_create_user" =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}${BOLD}서비스 사용자 생성 중...${NC}"
        
        # 사용자 생성
        PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "$CREATE_USER_SQL"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 사용자 '$PG_SVC_USER' 생성 성공${NC}"
            
            # 데이터베이스 연결 권한 부여
            echo -e "${BLUE}${BOLD}데이터베이스 연결 권한 부여 중...${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "$GRANT_CONNECT_SQL"
            
            # 스키마 사용 권한 부여
            echo -e "${BLUE}${BOLD}스키마 사용 권한 부여 중...${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d "$db_name" -c "$GRANT_USAGE_SQL"
            
            # 테이블 권한 부여
            echo -e "${BLUE}${BOLD}테이블 권한 부여 중...${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d "$db_name" -c "$GRANT_ALL_SQL"
            
            # 시퀀스 권한 부여
            echo -e "${BLUE}${BOLD}시퀀스 권한 부여 중...${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d "$db_name" -c "$GRANT_SEQUENCES_SQL"
            
            # 기본 권한 설정 (향후 생성될 테이블에 대한 권한)
            echo -e "${BLUE}${BOLD}기본 권한 설정 중...${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d "$db_name" -c "$ALTER_DEFAULT_PRIVILEGES_TABLES_SQL"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d "$db_name" -c "$ALTER_DEFAULT_PRIVILEGES_SEQUENCES_SQL"
            
            echo -e "${GREEN}✓ 서비스 사용자 '$PG_SVC_USER' 권한 설정 완료${NC}"
            
            # 생성된 사용자 정보 확인
            echo -e "${BLUE}${BOLD}생성된 사용자 정보 확인:${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "SELECT rolname, rolcanlogin, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = '$PG_SVC_USER';"
            
            return 0
        else
            echo -e "${RED}✗ 서비스 사용자 생성 실패${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}서비스 사용자 생성을 취소합니다.${NC}"
        return 0
    fi
}

# PostgreSQL 데이터베이스 생성 함수
create_postgresql_database() {
    local db_name="$1"
    local encoding="$2"
    local lc_collate="$3"
    local lc_ctype="$4"
    local template="$5"
    
    print_separator
    echo -e "${BLUE}${BOLD}PostgreSQL 데이터베이스 생성${NC}"
    print_separator
    
    echo -e "${CYAN}생성할 데이터베이스 정보:${NC}"
    echo -e "${CYAN}  데이터베이스명: $db_name${NC}"
    echo -e "${CYAN}  ENCODING: $encoding${NC}"
    echo -e "${CYAN}  LC_COLLATE: $lc_collate${NC}"
    echo -e "${CYAN}  LC_CTYPE: $lc_ctype${NC}"
    echo -e "${CYAN}  TEMPLATE: $template${NC}"
    print_separator
    
    # 데이터베이스 존재 여부 확인
    echo -e "${BLUE}${BOLD}기존 데이터베이스 확인 중...${NC}"
    
    DB_EXISTS=$(PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname = '$db_name';" 2>/dev/null | grep -c "1")
    
    if [ "$DB_EXISTS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  데이터베이스 '$db_name'이 이미 존재합니다.${NC}"
        echo -ne "${BLUE}${BOLD}기존 데이터베이스를 삭제하고 다시 생성하시겠습니까? (y/N): ${NC}"
        read recreate_db
        
        if [[ "$recreate_db" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}기존 데이터베이스를 삭제합니다...${NC}"
            
            # 활성 연결 종료
            echo -e "${YELLOW}활성 연결을 종료합니다...${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db_name';" >/dev/null 2>&1
            
            # 데이터베이스 삭제
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "DROP DATABASE IF EXISTS \"$db_name\";" 2>/dev/null
            
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
    CREATE_SQL="CREATE DATABASE \"$db_name\" ENCODING '$encoding' LC_COLLATE '$lc_collate' LC_CTYPE '$lc_ctype' TEMPLATE $template;"
    
    echo -e "${BLUE}${BOLD}실행할 SQL:${NC}"
    echo -e "${CYAN}$CREATE_SQL${NC}"
    print_separator
    
    echo -ne "${BLUE}${BOLD}데이터베이스를 생성하시겠습니까? (Y/n): ${NC}"
    read confirm_create
    
    if [[ ! "$confirm_create" =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}${BOLD}데이터베이스 생성 중...${NC}"
        
        PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "$CREATE_SQL"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 데이터베이스 '$db_name' 생성 성공${NC}"
            
            # 생성된 데이터베이스 정보 확인
            echo -e "${BLUE}${BOLD}생성된 데이터베이스 정보 확인:${NC}"
            PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d postgres -c "SELECT datname, encoding, datcollate, datctype FROM pg_database WHERE datname = '$db_name';"
            
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

# MySQL 데이터베이스 생성 함수
create_mysql_database() {
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

# PostgreSQL 데이터베이스 생성 설정 입력 함수
get_postgresql_settings() {
    print_separator
    echo -e "${BLUE}${BOLD}PostgreSQL 데이터베이스 생성 설정${NC}"
    print_separator
    
    # 데이터베이스 이름 (PGDATABASE 환경 변수 필수)
    if [ -z "$PGDATABASE" ]; then
        echo -e "${RED}${BOLD}오류: PGDATABASE 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}PGDATABASE 환경 변수를 설정하세요.${NC}"
        exit 1
    fi
    db_name="$PGDATABASE"
    echo -e "${CYAN}데이터베이스 이름: $db_name (PGDATABASE 환경 변수)${NC}"
    
    # ENCODING 입력 (기본값: UTF8)
    DEFAULT_ENCODING="UTF8"
    echo -ne "${BLUE}${BOLD}ENCODING [$DEFAULT_ENCODING]: ${NC}"
    read encoding
    encoding=${encoding:-$DEFAULT_ENCODING}
    
    # LC_COLLATE 입력 (기본값: C)
    DEFAULT_LC_COLLATE="C"
    echo -ne "${BLUE}${BOLD}LC_COLLATE [$DEFAULT_LC_COLLATE]: ${NC}"
    read lc_collate
    lc_collate=${lc_collate:-$DEFAULT_LC_COLLATE}
    
    # LC_CTYPE 입력 (기본값: C)
    DEFAULT_LC_CTYPE="C"
    echo -ne "${BLUE}${BOLD}LC_CTYPE [$DEFAULT_LC_CTYPE]: ${NC}"
    read lc_ctype
    lc_ctype=${lc_ctype:-$DEFAULT_LC_CTYPE}
    
    # TEMPLATE 입력 (기본값: template0)
    DEFAULT_TEMPLATE="template0"
    echo -ne "${BLUE}${BOLD}TEMPLATE [$DEFAULT_TEMPLATE]: ${NC}"
    read template
    template=${template:-$DEFAULT_TEMPLATE}
    
    # 입력값 검증
    if [ -z "$db_name" ] || [ -z "$encoding" ] || [ -z "$lc_collate" ] || [ -z "$lc_ctype" ] || [ -z "$template" ]; then
        echo -e "${RED}오류: 필수 입력값이 비어있습니다.${NC}"
        exit 1
    fi
    
    # PostgreSQL 데이터베이스 생성 실행
    create_postgresql_database "$db_name" "$encoding" "$lc_collate" "$lc_ctype" "$template"
    
    if [ $? -eq 0 ]; then
        # 서비스 사용자 생성
        create_postgresql_service_user "$db_name"
        
        if [ $? -eq 0 ]; then
            print_separator
            echo -e "${GREEN}${BOLD}PostgreSQL 데이터베이스 및 서비스 사용자 생성 작업이 완료되었습니다.${NC}"
            print_separator
            
            echo -e "${CYAN}${BOLD}생성된 데이터베이스 연결 정보:${NC}"
            echo -e "${CYAN}  Host: $PGHOST${NC}"
            echo -e "${CYAN}  Port: $PGPORT${NC}"
            echo -e "${CYAN}  Database: $db_name${NC}"
            echo -e "${CYAN}  ENCODING: $encoding${NC}"
            echo -e "${CYAN}  LC_COLLATE: $lc_collate${NC}"
            echo -e "${CYAN}  LC_CTYPE: $lc_ctype${NC}"
            echo -e "${CYAN}  TEMPLATE: $template${NC}"
            
            echo -e "${CYAN}${BOLD}생성된 서비스 사용자 정보:${NC}"
            echo -e "${CYAN}  Service User: $PG_SVC_USER${NC}"
            echo -e "${CYAN}  Service Password: [설정됨]${NC}"
            
            echo -e "${YELLOW}${BOLD}관리자 연결 테스트:${NC}"
            echo -e "${YELLOW}PGPASSWORD=$PG_ADM_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_ADM_USER -d $db_name${NC}"
            
            echo -e "${YELLOW}${BOLD}서비스 사용자 연결 테스트:${NC}"
            echo -e "${YELLOW}PGPASSWORD=$PG_SVC_PASSWORD psql -h $PGHOST -p $PGPORT -U $PG_SVC_USER -d $db_name${NC}"
            
            print_separator
            return 0
        else
            echo -e "${RED}서비스 사용자 생성에 실패했습니다.${NC}"
            return 1
        fi
    else
        echo -e "${RED}PostgreSQL 데이터베이스 생성에 실패했습니다.${NC}"
        return 1
    fi
}

# MySQL 데이터베이스 생성 설정 입력 함수
get_mysql_settings() {
    print_separator
    echo -e "${BLUE}${BOLD}MySQL 데이터베이스 생성 설정${NC}"
    print_separator
    
    # 데이터베이스 이름 (MYSQL_DATABASE 환경 변수 필수)
    if [ -z "$MYSQL_DATABASE" ]; then
        echo -e "${RED}${BOLD}오류: MYSQL_DATABASE 환경 변수가 설정되지 않았습니다.${NC}"
        echo -e "${YELLOW}MYSQL_DATABASE 환경 변수를 설정하세요.${NC}"
        exit 1
    fi
    db_name="$MYSQL_DATABASE"
    echo -e "${CYAN}데이터베이스 이름: $db_name (MYSQL_DATABASE 환경 변수)${NC}"
    
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
    if [ -z "$db_name" ] || [ -z "$charset" ] || [ -z "$collate" ]; then
        echo -e "${RED}오류: 필수 입력값이 비어있습니다.${NC}"
        exit 1
    fi
    
    # MySQL 데이터베이스 생성 실행
    create_mysql_database "$db_name" "$charset" "$collate"
    
    if [ $? -eq 0 ]; then
        print_separator
        echo -e "${GREEN}${BOLD}MySQL 데이터베이스 생성 작업이 완료되었습니다.${NC}"
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
        return 0
    else
        echo -e "${RED}MySQL 데이터베이스 생성에 실패했습니다.${NC}"
        return 1
    fi
}

# 메인 실행 부분
clear
print_separator
echo -e "${BLUE}${BOLD}통합 Database 생성 스크립트 (PostgreSQL/MySQL)${NC}"
print_separator

# TARGET_DBMS_TYPE 확인
check_target_dbms_type

# TARGET_DBMS_TYPE에 따른 분기 처리
case "$TARGET_DBMS_TYPE" in
    "postgres")
        # PostgreSQL 환경 변수 확인
        check_postgresql_environment
        
        # PostgreSQL 연결 테스트
        if ! test_postgresql_connection; then
            echo -e "${RED}PostgreSQL 연결에 실패했습니다. 환경 변수와 네트워크 연결을 확인하세요.${NC}"
            exit 1
        fi
        
        # PostgreSQL 데이터베이스 생성
        get_postgresql_settings
        ;;
    "mysql")
        # MySQL 환경 변수 확인
        check_mysql_environment
        
        # MySQL 연결 테스트
        if ! test_mysql_connection; then
            echo -e "${RED}MySQL 연결에 실패했습니다. 환경 변수와 네트워크 연결을 확인하세요.${NC}"
            exit 1
        fi
        
        # MySQL 데이터베이스 생성
        get_mysql_settings
        ;;
esac

exit $?
