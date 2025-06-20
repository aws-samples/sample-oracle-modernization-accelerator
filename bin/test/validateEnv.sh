#!/bin/bash

#############################################################################
# Script: validateEnv.sh
# Description: Comprehensive environment validation for Oracle Migration Assistant
#
# Functionality:
# - Validates environment variables for all OMA programs
# - Tests database connections (Oracle and PostgreSQL)
# - Checks program dependencies and requirements
# - Generates detailed validation report
# - Uses /tmp for temporary work
# - Logs to $TEST_LOGS_FOLDER or /tmp if not set
#
# Usage:
#   ./validateEnv.sh [options]
#
# Options:
#   -v, --verbose       Verbose output
#   -q, --quiet         Quiet mode (errors only)
#   -r, --report FILE   Generate report to specific file
#   --skip-db          Skip database connection tests
#   --help             Show this help message
#############################################################################

# 스크립트 설정
set -euo pipefail
SCRIPT_NAME="validateEnv.sh"
SCRIPT_VERSION="1.0"
START_TIME=$(date +%s)

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 로그 레벨
LOG_ERROR=1
LOG_WARN=2
LOG_INFO=3
LOG_DEBUG=4
CURRENT_LOG_LEVEL=3

# 전역 변수
VERBOSE=false
QUIET=false
SKIP_DB=false
REPORT_FILE=""
TEMP_DIR="/tmp/oma_validation_$$"
LOG_DIR=""
LOG_FILE=""
VALIDATION_RESULTS=()
ERROR_COUNT=0
WARNING_COUNT=0

# 프로그램 목록과 필요한 환경변수 정의
declare -A PROGRAM_ENV_VARS
PROGRAM_ENV_VARS[GetDDL.sh]="ORACLE_ADM_USER,ORACLE_ADM_PASSWORD,ORACLE_SVC_USER,PGUSER,PGHOST,PGPORT,PGDATABASE,PGPASSWORD"
PROGRAM_ENV_VARS[XMLToSQL.py]="TEST_FOLDER,TEST_LOGS_FOLDER"
PROGRAM_ENV_VARS[GetDictionary.py]="ORACLE_SVC_USER,ORACLE_SVC_PASSWORD,ORACLE_SVC_CONNECT_STRING,TEST_FOLDER,TEST_LOGS_FOLDER"
PROGRAM_ENV_VARS[BindSampler.py]="TEST_FOLDER,TEST_LOGS_FOLDER"
PROGRAM_ENV_VARS[BindMapper.py]="TEST_FOLDER,TEST_LOGS_FOLDER"
PROGRAM_ENV_VARS[SaveSQLToDB.py]="PGHOST,PGPORT,PGDATABASE,PGUSER,PGPASSWORD,TEST_FOLDER,TEST_LOGS_FOLDER"
PROGRAM_ENV_VARS[ExecuteAndCompareSQL.py]="ORACLE_SVC_USER,ORACLE_SVC_PASSWORD,ORACLE_SID,PGHOST,PGPORT,PGDATABASE,PGUSER,PGPASSWORD,TEST_FOLDER,TEST_LOGS_FOLDER"
PROGRAM_ENV_VARS[AnalyzeResult.py]="PGHOST,PGPORT,PGDATABASE,PGUSER,PGPASSWORD,TEST_FOLDER,TEST_LOGS_FOLDER"

# 환경변수 분류
ORACLE_VARS="ORACLE_ADM_USER,ORACLE_ADM_PASSWORD,ORACLE_SVC_USER,ORACLE_SVC_PASSWORD,ORACLE_SVC_CONNECT_STRING,ORACLE_SID"
POSTGRES_VARS="PGHOST,PGPORT,PGDATABASE,PGUSER,PGPASSWORD"
FOLDER_VARS="TEST_FOLDER,TEST_LOGS_FOLDER"
OPTIONAL_VARS="SQL_BATCH_SIZE,SQL_PARALLEL_EXECUTION,SQL_MAX_WORKERS,SQL_TEMP_CLEANUP,SQL_ARCHIVE_DAYS"

# 함수 정의
usage() {
    cat << EOF
사용법: $0 [옵션]

Oracle Migration Assistant 환경 검증 도구

옵션:
    -v, --verbose       상세 출력
    -q, --quiet         조용한 모드 (오류만 출력)
    -r, --report FILE   지정된 파일에 보고서 생성
    --skip-db          데이터베이스 연결 테스트 건너뛰기
    --help             이 도움말 표시

예시:
    $0                  # 기본 검증
    $0 -v               # 상세 출력으로 검증
    $0 -r report.txt    # 보고서 파일 생성
    $0 --skip-db        # DB 연결 테스트 제외

EOF
}

log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ $level -le $CURRENT_LOG_LEVEL ]; then
        case $level in
            $LOG_ERROR)
                echo -e "${RED}[ERROR]${NC} $message" >&2
                [ -n "$LOG_FILE" ] && echo "[$timestamp] [ERROR] $message" >> "$LOG_FILE"
                ;;
            $LOG_WARN)
                echo -e "${YELLOW}[WARN]${NC} $message" >&2
                [ -n "$LOG_FILE" ] && echo "[$timestamp] [WARN] $message" >> "$LOG_FILE"
                ;;
            $LOG_INFO)
                if [ "$QUIET" = false ]; then
                    echo -e "${GREEN}[INFO]${NC} $message"
                fi
                [ -n "$LOG_FILE" ] && echo "[$timestamp] [INFO] $message" >> "$LOG_FILE"
                ;;
            $LOG_DEBUG)
                if [ "$VERBOSE" = true ]; then
                    echo -e "${CYAN}[DEBUG]${NC} $message"
                fi
                [ -n "$LOG_FILE" ] && echo "[$timestamp] [DEBUG] $message" >> "$LOG_FILE"
                ;;
        esac
    fi
}

setup_logging() {
    # 로그 디렉토리 설정
    if [ -n "${TEST_LOGS_FOLDER:-}" ]; then
        LOG_DIR="$TEST_LOGS_FOLDER"
    else
        LOG_DIR="/tmp"
        log $LOG_WARN "TEST_LOGS_FOLDER가 설정되지 않아 /tmp를 사용합니다."
    fi
    
    # 로그 디렉토리 생성
    mkdir -p "$LOG_DIR"
    
    # 로그 파일 설정
    LOG_FILE="$LOG_DIR/validate_env_$(date +%Y%m%d_%H%M%S).log"
    
    log $LOG_INFO "로그 파일: $LOG_FILE"
}

setup_temp_dir() {
    # 임시 디렉토리 생성
    mkdir -p "$TEMP_DIR"
    log $LOG_DEBUG "임시 디렉토리 생성: $TEMP_DIR"
    
    # 스크립트 종료 시 정리
    trap cleanup EXIT
}

cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log $LOG_DEBUG "임시 디렉토리 정리: $TEMP_DIR"
    fi
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                CURRENT_LOG_LEVEL=4
                shift
                ;;
            -q|--quiet)
                QUIET=true
                CURRENT_LOG_LEVEL=1
                shift
                ;;
            -r|--report)
                REPORT_FILE="$2"
                shift 2
                ;;
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                log $LOG_ERROR "알 수 없는 옵션: $1"
                usage
                exit 1
                ;;
        esac
    done
}

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${WHITE}Oracle Migration Assistant 환경 검증 도구${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "버전: $SCRIPT_VERSION"
    echo -e "실행 시간: $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "호스트: $(hostname)"
    echo -e "사용자: $(whoami)"
    echo -e "${BLUE}============================================================${NC}"
    echo
}
check_env_var() {
    local var_name=$1
    local var_value="${!var_name:-}"
    local is_required=${2:-true}
    
    if [ -n "$var_value" ]; then
        if [[ "$var_name" == *"PASSWORD"* ]]; then
            log $LOG_INFO "✓ $var_name: $(printf '%*s' ${#var_value} | tr ' ' '*')"
        else
            log $LOG_INFO "✓ $var_name: $var_value"
        fi
        return 0
    else
        if [ "$is_required" = true ]; then
            log $LOG_ERROR "✗ $var_name: 설정되지 않음 (필수)"
            ((ERROR_COUNT++))
            return 1
        else
            log $LOG_WARN "- $var_name: 설정되지 않음 (선택사항)"
            ((WARNING_COUNT++))
            return 2
        fi
    fi
}

validate_oracle_env_vars() {
    log $LOG_INFO "${PURPLE}Oracle 환경변수 검증${NC}"
    echo "----------------------------------------"
    
    local oracle_vars_array
    IFS=',' read -ra oracle_vars_array <<< "$ORACLE_VARS"
    
    local oracle_missing=0
    for var in "${oracle_vars_array[@]}"; do
        if ! check_env_var "$var" true; then
            ((oracle_missing++))
        fi
    done
    
    if [ $oracle_missing -eq 0 ]; then
        log $LOG_INFO "Oracle 환경변수: 모두 설정됨"
        VALIDATION_RESULTS+=("Oracle 환경변수: ✓ 통과")
    else
        log $LOG_ERROR "Oracle 환경변수: $oracle_missing개 누락"
        VALIDATION_RESULTS+=("Oracle 환경변수: ✗ $oracle_missing개 누락")
    fi
    echo
}

validate_postgres_env_vars() {
    log $LOG_INFO "${PURPLE}PostgreSQL 환경변수 검증${NC}"
    echo "----------------------------------------"
    
    local postgres_vars_array
    IFS=',' read -ra postgres_vars_array <<< "$POSTGRES_VARS"
    
    local postgres_missing=0
    for var in "${postgres_vars_array[@]}"; do
        if ! check_env_var "$var" true; then
            ((postgres_missing++))
        fi
    done
    
    if [ $postgres_missing -eq 0 ]; then
        log $LOG_INFO "PostgreSQL 환경변수: 모두 설정됨"
        VALIDATION_RESULTS+=("PostgreSQL 환경변수: ✓ 통과")
    else
        log $LOG_ERROR "PostgreSQL 환경변수: $postgres_missing개 누락"
        VALIDATION_RESULTS+=("PostgreSQL 환경변수: ✗ $postgres_missing개 누락")
    fi
    echo
}

validate_folder_env_vars() {
    log $LOG_INFO "${PURPLE}폴더 환경변수 검증${NC}"
    echo "----------------------------------------"
    
    local folder_vars_array
    IFS=',' read -ra folder_vars_array <<< "$FOLDER_VARS"
    
    local folder_missing=0
    for var in "${folder_vars_array[@]}"; do
        if ! check_env_var "$var" false; then
            if [ $? -eq 1 ]; then  # 오류인 경우만 카운트
                ((folder_missing++))
            fi
        else
            # 폴더가 설정된 경우 존재 여부 확인
            local folder_path="${!var}"
            if [ ! -d "$folder_path" ]; then
                log $LOG_WARN "폴더가 존재하지 않습니다: $folder_path"
                log $LOG_INFO "폴더를 생성합니다: $folder_path"
                if mkdir -p "$folder_path" 2>/dev/null; then
                    log $LOG_INFO "폴더 생성 성공: $folder_path"
                else
                    log $LOG_ERROR "폴더 생성 실패: $folder_path"
                    ((ERROR_COUNT++))
                fi
            else
                log $LOG_DEBUG "폴더 존재 확인: $folder_path"
            fi
        fi
    done
    
    if [ $folder_missing -eq 0 ]; then
        log $LOG_INFO "폴더 환경변수: 설정 완료"
        VALIDATION_RESULTS+=("폴더 환경변수: ✓ 통과")
    else
        log $LOG_WARN "폴더 환경변수: $folder_missing개 미설정 (기본값 사용)"
        VALIDATION_RESULTS+=("폴더 환경변수: ⚠ $folder_missing개 미설정")
    fi
    echo
}

validate_optional_env_vars() {
    log $LOG_INFO "${PURPLE}선택적 환경변수 검증${NC}"
    echo "----------------------------------------"
    
    local optional_vars_array
    IFS=',' read -ra optional_vars_array <<< "$OPTIONAL_VARS"
    
    local defaults=(
        "SQL_BATCH_SIZE=10"
        "SQL_PARALLEL_EXECUTION=false"
        "SQL_MAX_WORKERS=4"
        "SQL_TEMP_CLEANUP=true"
        "SQL_ARCHIVE_DAYS=7"
    )
    
    for var in "${optional_vars_array[@]}"; do
        local default_value=""
        for default in "${defaults[@]}"; do
            if [[ "$default" == "$var="* ]]; then
                default_value="${default#*=}"
                break
            fi
        done
        
        if check_env_var "$var" false; then
            continue
        else
            log $LOG_INFO "  기본값: $default_value"
        fi
    done
    
    VALIDATION_RESULTS+=("선택적 환경변수: ✓ 확인됨")
    echo
}

validate_program_env_vars() {
    log $LOG_INFO "${PURPLE}프로그램별 환경변수 검증${NC}"
    echo "----------------------------------------"
    
    for program in "${!PROGRAM_ENV_VARS[@]}"; do
        log $LOG_INFO "프로그램: $program"
        
        local required_vars="${PROGRAM_ENV_VARS[$program]}"
        IFS=',' read -ra vars_array <<< "$required_vars"
        
        local program_missing=0
        local program_warnings=0
        
        for var in "${vars_array[@]}"; do
            local is_required=true
            
            # 폴더 변수들은 선택사항으로 처리
            if [[ "$FOLDER_VARS" == *"$var"* ]]; then
                is_required=false
            fi
            
            local result
            check_env_var "$var" $is_required
            result=$?
            
            if [ $result -eq 1 ]; then
                ((program_missing++))
            elif [ $result -eq 2 ]; then
                ((program_warnings++))
            fi
        done
        
        if [ $program_missing -eq 0 ]; then
            if [ $program_warnings -eq 0 ]; then
                log $LOG_INFO "  결과: ✓ 모든 환경변수 설정됨"
                VALIDATION_RESULTS+=("$program: ✓ 통과")
            else
                log $LOG_WARN "  결과: ⚠ $program_warnings개 선택사항 미설정"
                VALIDATION_RESULTS+=("$program: ⚠ $program_warnings개 선택사항 미설정")
            fi
        else
            log $LOG_ERROR "  결과: ✗ $program_missing개 필수 환경변수 누락"
            VALIDATION_RESULTS+=("$program: ✗ $program_missing개 누락")
        fi
        echo
    done
}
test_oracle_connection() {
    log $LOG_INFO "${PURPLE}Oracle 데이터베이스 연결 테스트${NC}"
    echo "----------------------------------------"
    
    # 필수 환경변수 확인
    local required_vars=("ORACLE_SVC_USER" "ORACLE_SVC_PASSWORD")
    local connect_string=""
    
    # 연결 문자열 결정
    if [ -n "${ORACLE_SVC_CONNECT_STRING:-}" ]; then
        connect_string="$ORACLE_SVC_CONNECT_STRING"
    elif [ -n "${ORACLE_SID:-}" ]; then
        connect_string="$ORACLE_SID"
    else
        log $LOG_ERROR "Oracle 연결 정보 없음 (ORACLE_SVC_CONNECT_STRING 또는 ORACLE_SID 필요)"
        VALIDATION_RESULTS+=("Oracle 연결: ✗ 연결 정보 없음")
        return 1
    fi
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log $LOG_ERROR "Oracle 연결 테스트 실패: $var 환경변수 없음"
            VALIDATION_RESULTS+=("Oracle 연결: ✗ 환경변수 누락")
            return 1
        fi
    done
    
    # SQLPlus 설치 확인
    if ! command -v sqlplus &> /dev/null; then
        log $LOG_ERROR "SQLPlus가 설치되지 않았습니다."
        VALIDATION_RESULTS+=("Oracle 연결: ✗ SQLPlus 없음")
        return 1
    fi
    
    log $LOG_INFO "Oracle 연결 테스트 중..."
    log $LOG_DEBUG "연결 문자열: $connect_string"
    
    # 임시 SQL 파일 생성
    local temp_sql="$TEMP_DIR/oracle_test.sql"
    cat > "$temp_sql" << EOF
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET ECHO OFF
SELECT 'CONNECTION_OK' FROM DUAL;
SELECT USER FROM DUAL;
SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') FROM DUAL;
EXIT;
EOF
    
    # Oracle 연결 테스트
    local result_file="$TEMP_DIR/oracle_result.txt"
    local error_file="$TEMP_DIR/oracle_error.txt"
    
    # 환경변수 설정
    export NLS_LANG=KOREAN_KOREA.AL32UTF8
    
    # SQLPlus 실행
    timeout 30 sqlplus -S "${ORACLE_SVC_USER}/${ORACLE_SVC_PASSWORD}@${connect_string}" @"$temp_sql" > "$result_file" 2> "$error_file"
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && grep -q "CONNECTION_OK" "$result_file"; then
        local oracle_user=$(grep -v "CONNECTION_OK" "$result_file" | head -1 | tr -d ' ')
        local oracle_time=$(grep -v "CONNECTION_OK" "$result_file" | tail -1 | tr -d ' ')
        
        log $LOG_INFO "✓ Oracle 연결 성공"
        log $LOG_INFO "  연결 사용자: $oracle_user"
        log $LOG_INFO "  서버 시간: $oracle_time"
        VALIDATION_RESULTS+=("Oracle 연결: ✓ 성공")
        
        # 추가 권한 테스트
        test_oracle_permissions
        
        return 0
    else
        log $LOG_ERROR "✗ Oracle 연결 실패"
        if [ -s "$error_file" ]; then
            log $LOG_ERROR "오류 내용:"
            while IFS= read -r line; do
                log $LOG_ERROR "  $line"
            done < "$error_file"
        fi
        VALIDATION_RESULTS+=("Oracle 연결: ✗ 실패")
        return 1
    fi
}

test_oracle_permissions() {
    log $LOG_DEBUG "Oracle 권한 테스트 중..."
    
    local temp_sql="$TEMP_DIR/oracle_perm_test.sql"
    cat > "$temp_sql" << EOF
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET ECHO OFF
-- 테이블 조회 권한 테스트
SELECT COUNT(*) FROM USER_TABLES WHERE ROWNUM <= 1;
-- 메타데이터 조회 권한 테스트  
SELECT COUNT(*) FROM USER_TAB_COLUMNS WHERE ROWNUM <= 1;
EXIT;
EOF
    
    local result_file="$TEMP_DIR/oracle_perm_result.txt"
    sqlplus -S "${ORACLE_SVC_USER}/${ORACLE_SVC_PASSWORD}@${connect_string}" @"$temp_sql" > "$result_file" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log $LOG_INFO "  권한 테스트: ✓ 통과"
    else
        log $LOG_WARN "  권한 테스트: ⚠ 일부 제한"
    fi
}

test_postgresql_connection() {
    log $LOG_INFO "${PURPLE}PostgreSQL 데이터베이스 연결 테스트${NC}"
    echo "----------------------------------------"
    
    # 필수 환경변수 확인
    local required_vars=("PGHOST" "PGPORT" "PGDATABASE" "PGUSER" "PGPASSWORD")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log $LOG_ERROR "PostgreSQL 연결 테스트 실패: $var 환경변수 없음"
            VALIDATION_RESULTS+=("PostgreSQL 연결: ✗ 환경변수 누락")
            return 1
        fi
    done
    
    # psql 설치 확인
    if ! command -v psql &> /dev/null; then
        log $LOG_ERROR "psql이 설치되지 않았습니다."
        VALIDATION_RESULTS+=("PostgreSQL 연결: ✗ psql 없음")
        return 1
    fi
    
    log $LOG_INFO "PostgreSQL 연결 테스트 중..."
    log $LOG_DEBUG "호스트: $PGHOST:$PGPORT"
    log $LOG_DEBUG "데이터베이스: $PGDATABASE"
    log $LOG_DEBUG "사용자: $PGUSER"
    
    # PostgreSQL 연결 테스트
    local result_file="$TEMP_DIR/postgres_result.txt"
    local error_file="$TEMP_DIR/postgres_error.txt"
    
    # 연결 테스트 SQL
    local test_sql="SELECT 'CONNECTION_OK' as status, current_user, now();"
    
    # psql 실행
    timeout 30 psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -U "$PGUSER" -t -A -c "$test_sql" > "$result_file" 2> "$error_file"
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && grep -q "CONNECTION_OK" "$result_file"; then
        local pg_info=$(grep "CONNECTION_OK" "$result_file")
        IFS='|' read -ra info_array <<< "$pg_info"
        
        log $LOG_INFO "✓ PostgreSQL 연결 성공"
        log $LOG_INFO "  연결 사용자: ${info_array[1]}"
        log $LOG_INFO "  서버 시간: ${info_array[2]}"
        VALIDATION_RESULTS+=("PostgreSQL 연결: ✓ 성공")
        
        # 추가 권한 테스트
        test_postgresql_permissions
        
        return 0
    else
        log $LOG_ERROR "✗ PostgreSQL 연결 실패"
        if [ -s "$error_file" ]; then
            log $LOG_ERROR "오류 내용:"
            while IFS= read -r line; do
                log $LOG_ERROR "  $line"
            done < "$error_file"
        fi
        VALIDATION_RESULTS+=("PostgreSQL 연결: ✗ 실패")
        return 1
    fi
}

test_postgresql_permissions() {
    log $LOG_DEBUG "PostgreSQL 권한 테스트 중..."
    
    local result_file="$TEMP_DIR/postgres_perm_result.txt"
    
    # 권한 테스트 SQL들
    local tests=(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' LIMIT 1;"
        "SELECT has_database_privilege(current_user, current_database(), 'CREATE');"
        "SELECT has_schema_privilege(current_user, 'public', 'CREATE');"
    )
    
    local all_passed=true
    for test_sql in "${tests[@]}"; do
        psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -U "$PGUSER" -t -A -c "$test_sql" > "$result_file" 2>/dev/null
        if [ $? -ne 0 ]; then
            all_passed=false
            break
        fi
    done
    
    if [ "$all_passed" = true ]; then
        log $LOG_INFO "  권한 테스트: ✓ 통과"
    else
        log $LOG_WARN "  권한 테스트: ⚠ 일부 제한"
    fi
}

test_database_connections() {
    if [ "$SKIP_DB" = true ]; then
        log $LOG_INFO "데이터베이스 연결 테스트를 건너뜁니다."
        VALIDATION_RESULTS+=("데이터베이스 연결: - 건너뜀")
        return 0
    fi
    
    log $LOG_INFO "${BLUE}데이터베이스 연결 테스트${NC}"
    echo "============================================"
    
    local oracle_result=0
    local postgres_result=0
    
    # Oracle 연결 테스트
    if [[ "$ORACLE_VARS" == *"ORACLE_SVC_USER"* ]] && [ -n "${ORACLE_SVC_USER:-}" ]; then
        test_oracle_connection
        oracle_result=$?
    else
        log $LOG_WARN "Oracle 환경변수가 설정되지 않아 연결 테스트를 건너뜁니다."
        VALIDATION_RESULTS+=("Oracle 연결: - 환경변수 없음")
    fi
    
    echo
    
    # PostgreSQL 연결 테스트
    if [[ "$POSTGRES_VARS" == *"PGUSER"* ]] && [ -n "${PGUSER:-}" ]; then
        test_postgresql_connection
        postgres_result=$?
    else
        log $LOG_WARN "PostgreSQL 환경변수가 설정되지 않아 연결 테스트를 건너뜁니다."
        VALIDATION_RESULTS+=("PostgreSQL 연결: - 환경변수 없음")
    fi
    
    echo
    
    # 전체 데이터베이스 연결 결과
    if [ $oracle_result -eq 0 ] && [ $postgres_result -eq 0 ]; then
        log $LOG_INFO "모든 데이터베이스 연결 테스트 통과"
    elif [ $oracle_result -ne 0 ] || [ $postgres_result -ne 0 ]; then
        log $LOG_ERROR "일부 데이터베이스 연결 테스트 실패"
        ((ERROR_COUNT++))
    fi
}
check_program_dependencies() {
    log $LOG_INFO "${BLUE}프로그램 의존성 검사${NC}"
    echo "============================================"
    
    # 필수 명령어들
    local required_commands=(
        "python3:Python 3"
        "sqlplus:Oracle SQL*Plus"
        "psql:PostgreSQL Client"
        "java:Java Runtime"
    )
    
    # 선택적 명령어들
    local optional_commands=(
        "jq:JSON 처리기"
        "curl:HTTP 클라이언트"
        "unzip:압축 해제"
    )
    
    log $LOG_INFO "필수 명령어 확인:"
    local missing_required=0
    
    for cmd_info in "${required_commands[@]}"; do
        IFS=':' read -ra cmd_array <<< "$cmd_info"
        local cmd="${cmd_array[0]}"
        local desc="${cmd_array[1]}"
        
        if command -v "$cmd" &> /dev/null; then
            local version=""
            case "$cmd" in
                "python3")
                    version=$(python3 --version 2>&1 | cut -d' ' -f2)
                    ;;
                "java")
                    version=$(java -version 2>&1 | head -1 | cut -d'"' -f2)
                    ;;
                "sqlplus")
                    version=$(sqlplus -version 2>&1 | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
                    ;;
                "psql")
                    version=$(psql --version | cut -d' ' -f3)
                    ;;
            esac
            
            log $LOG_INFO "  ✓ $desc ($cmd): $version"
        else
            log $LOG_ERROR "  ✗ $desc ($cmd): 설치되지 않음"
            ((missing_required++))
            ((ERROR_COUNT++))
        fi
    done
    
    echo
    log $LOG_INFO "선택적 명령어 확인:"
    local missing_optional=0
    
    for cmd_info in "${optional_commands[@]}"; do
        IFS=':' read -ra cmd_array <<< "$cmd_info"
        local cmd="${cmd_array[0]}"
        local desc="${cmd_array[1]}"
        
        if command -v "$cmd" &> /dev/null; then
            log $LOG_INFO "  ✓ $desc ($cmd): 설치됨"
        else
            log $LOG_WARN "  - $desc ($cmd): 설치되지 않음"
            ((missing_optional++))
            ((WARNING_COUNT++))
        fi
    done
    
    # Python 패키지 확인
    echo
    log $LOG_INFO "Python 패키지 확인:"
    local python_packages=(
        "psycopg2:PostgreSQL 어댑터"
        "cx_Oracle:Oracle 어댑터"
        "lxml:XML 처리"
        "pandas:데이터 분석"
        "matplotlib:그래프 생성"
        "jinja2:템플릿 엔진"
    )
    
    local missing_packages=0
    for pkg_info in "${python_packages[@]}"; do
        IFS=':' read -ra pkg_array <<< "$pkg_info"
        local pkg="${pkg_array[0]}"
        local desc="${pkg_array[1]}"
        
        if python3 -c "import $pkg" &> /dev/null; then
            local version=$(python3 -c "import $pkg; print(getattr($pkg, '__version__', 'unknown'))" 2>/dev/null)
            log $LOG_INFO "  ✓ $desc ($pkg): $version"
        else
            log $LOG_WARN "  - $desc ($pkg): 설치되지 않음"
            ((missing_packages++))
            ((WARNING_COUNT++))
        fi
    done
    
    # 결과 요약
    echo
    if [ $missing_required -eq 0 ]; then
        log $LOG_INFO "필수 의존성: ✓ 모두 설치됨"
        VALIDATION_RESULTS+=("필수 의존성: ✓ 통과")
    else
        log $LOG_ERROR "필수 의존성: ✗ $missing_required개 누락"
        VALIDATION_RESULTS+=("필수 의존성: ✗ $missing_required개 누락")
    fi
    
    if [ $missing_optional -eq 0 ] && [ $missing_packages -eq 0 ]; then
        log $LOG_INFO "선택적 의존성: ✓ 모두 설치됨"
        VALIDATION_RESULTS+=("선택적 의존성: ✓ 모두 설치됨")
    else
        local total_missing=$((missing_optional + missing_packages))
        log $LOG_WARN "선택적 의존성: ⚠ $total_missing개 누락"
        VALIDATION_RESULTS+=("선택적 의존성: ⚠ $total_missing개 누락")
    fi
    
    echo
}

check_file_permissions() {
    log $LOG_INFO "${BLUE}파일 권한 검사${NC}"
    echo "============================================"
    
    # 현재 디렉토리의 스크립트 파일들 확인
    local script_files=(
        "GetDDL.sh"
        "XMLToSQL.py"
        "GetDictionary.py"
        "BindSampler.py"
        "BindMapper.py"
        "SaveSQLToDB.py"
        "ExecuteAndCompareSQL.py"
        "AnalyzeResult.py"
        "validateEnv.sh"
    )
    
    local permission_issues=0
    
    for script in "${script_files[@]}"; do
        if [ -f "$script" ]; then
            if [ -r "$script" ]; then
                log $LOG_INFO "  ✓ $script: 읽기 가능"
                
                # 실행 권한 확인 (.sh 파일의 경우)
                if [[ "$script" == *.sh ]]; then
                    if [ -x "$script" ]; then
                        log $LOG_DEBUG "    실행 권한: ✓"
                    else
                        log $LOG_WARN "    실행 권한: ⚠ 없음"
                        log $LOG_INFO "    권한 설정: chmod +x $script"
                        ((WARNING_COUNT++))
                    fi
                fi
            else
                log $LOG_ERROR "  ✗ $script: 읽기 불가"
                ((permission_issues++))
                ((ERROR_COUNT++))
            fi
        else
            log $LOG_WARN "  - $script: 파일 없음"
            ((WARNING_COUNT++))
        fi
    done
    
    # 디렉토리 권한 확인
    local test_folders=("${TEST_FOLDER:-$(pwd)}" "${TEST_LOGS_FOLDER:-/tmp}")
    
    for folder in "${test_folders[@]}"; do
        if [ -d "$folder" ]; then
            if [ -w "$folder" ]; then
                log $LOG_INFO "  ✓ $folder: 쓰기 가능"
            else
                log $LOG_ERROR "  ✗ $folder: 쓰기 불가"
                ((permission_issues++))
                ((ERROR_COUNT++))
            fi
        else
            log $LOG_WARN "  - $folder: 디렉토리 없음"
            ((WARNING_COUNT++))
        fi
    done
    
    if [ $permission_issues -eq 0 ]; then
        VALIDATION_RESULTS+=("파일 권한: ✓ 통과")
    else
        VALIDATION_RESULTS+=("파일 권한: ✗ $permission_issues개 문제")
    fi
    
    echo
}

generate_report() {
    local report_file="$1"
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    log $LOG_INFO "검증 보고서 생성 중..."
    
    {
        echo "============================================================"
        echo "Oracle Migration Assistant 환경 검증 보고서"
        echo "============================================================"
        echo "생성 시간: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "호스트: $(hostname)"
        echo "사용자: $(whoami)"
        echo "검증 소요 시간: ${duration}초"
        echo "스크립트 버전: $SCRIPT_VERSION"
        echo ""
        
        echo "검증 결과 요약:"
        echo "----------------------------------------"
        echo "총 오류: $ERROR_COUNT"
        echo "총 경고: $WARNING_COUNT"
        echo ""
        
        echo "상세 결과:"
        echo "----------------------------------------"
        for result in "${VALIDATION_RESULTS[@]}"; do
            echo "$result"
        done
        echo ""
        
        echo "환경변수 현황:"
        echo "----------------------------------------"
        echo "Oracle 환경변수:"
        IFS=',' read -ra oracle_vars_array <<< "$ORACLE_VARS"
        for var in "${oracle_vars_array[@]}"; do
            local value="${!var:-}"
            if [ -n "$value" ]; then
                if [[ "$var" == *"PASSWORD"* ]]; then
                    echo "  $var: $(printf '%*s' ${#value} | tr ' ' '*')"
                else
                    echo "  $var: $value"
                fi
            else
                echo "  $var: (설정되지 않음)"
            fi
        done
        echo ""
        
        echo "PostgreSQL 환경변수:"
        IFS=',' read -ra postgres_vars_array <<< "$POSTGRES_VARS"
        for var in "${postgres_vars_array[@]}"; do
            local value="${!var:-}"
            if [ -n "$value" ]; then
                if [[ "$var" == *"PASSWORD"* ]]; then
                    echo "  $var: $(printf '%*s' ${#value} | tr ' ' '*')"
                else
                    echo "  $var: $value"
                fi
            else
                echo "  $var: (설정되지 않음)"
            fi
        done
        echo ""
        
        echo "폴더 환경변수:"
        IFS=',' read -ra folder_vars_array <<< "$FOLDER_VARS"
        for var in "${folder_vars_array[@]}"; do
            local value="${!var:-}"
            if [ -n "$value" ]; then
                echo "  $var: $value"
            else
                echo "  $var: (설정되지 않음)"
            fi
        done
        echo ""
        
        echo "권장사항:"
        echo "----------------------------------------"
        if [ $ERROR_COUNT -gt 0 ]; then
            echo "1. 오류 해결이 필요합니다:"
            echo "   - 누락된 환경변수를 설정하세요"
            echo "   - 데이터베이스 연결 정보를 확인하세요"
            echo "   - 필수 프로그램을 설치하세요"
        fi
        
        if [ $WARNING_COUNT -gt 0 ]; then
            echo "2. 경고 사항 검토:"
            echo "   - 선택적 환경변수 설정을 고려하세요"
            echo "   - 권장 프로그램 설치를 고려하세요"
        fi
        
        if [ $ERROR_COUNT -eq 0 ] && [ $WARNING_COUNT -eq 0 ]; then
            echo "모든 검증이 통과되었습니다!"
            echo "Oracle Migration Assistant를 실행할 준비가 완료되었습니다."
        fi
        
        echo ""
        echo "============================================================"
        
    } > "$report_file"
    
    log $LOG_INFO "보고서 생성 완료: $report_file"
}

print_summary() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    echo
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${WHITE}검증 결과 요약${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "검증 소요 시간: ${duration}초"
    echo -e "총 오류: ${RED}$ERROR_COUNT${NC}"
    echo -e "총 경고: ${YELLOW}$WARNING_COUNT${NC}"
    echo
    
    echo -e "${PURPLE}상세 결과:${NC}"
    for result in "${VALIDATION_RESULTS[@]}"; do
        if [[ "$result" == *"✓"* ]]; then
            echo -e "${GREEN}$result${NC}"
        elif [[ "$result" == *"✗"* ]]; then
            echo -e "${RED}$result${NC}"
        elif [[ "$result" == *"⚠"* ]]; then
            echo -e "${YELLOW}$result${NC}"
        else
            echo -e "${CYAN}$result${NC}"
        fi
    done
    
    echo
    if [ $ERROR_COUNT -eq 0 ]; then
        echo -e "${GREEN}✓ 환경 검증이 성공적으로 완료되었습니다!${NC}"
        echo -e "${GREEN}  Oracle Migration Assistant를 실행할 준비가 되었습니다.${NC}"
    else
        echo -e "${RED}✗ 환경 검증에서 오류가 발견되었습니다.${NC}"
        echo -e "${RED}  오류를 해결한 후 다시 실행하세요.${NC}"
    fi
    
    if [ $WARNING_COUNT -gt 0 ]; then
        echo -e "${YELLOW}⚠ 경고 사항이 있습니다. 검토를 권장합니다.${NC}"
    fi
    
    echo -e "${BLUE}============================================================${NC}"
}
main() {
    # 인수 파싱
    parse_arguments "$@"
    
    # 초기 설정
    setup_temp_dir
    setup_logging
    
    # 헤더 출력
    print_header
    
    # 환경변수 검증
    log $LOG_INFO "${BLUE}환경변수 검증 시작${NC}"
    echo "============================================"
    
    validate_oracle_env_vars
    validate_postgres_env_vars
    validate_folder_env_vars
    validate_optional_env_vars
    validate_program_env_vars
    
    # 프로그램 의존성 검사
    check_program_dependencies
    
    # 파일 권한 검사
    check_file_permissions
    
    # 데이터베이스 연결 테스트
    test_database_connections
    
    # 보고서 생성
    if [ -n "$REPORT_FILE" ]; then
        generate_report "$REPORT_FILE"
    else
        # 기본 보고서 파일 생성
        local default_report="$LOG_DIR/validation_report_$(date +%Y%m%d_%H%M%S).txt"
        generate_report "$default_report"
        log $LOG_INFO "기본 보고서: $default_report"
    fi
    
    # 결과 요약 출력
    print_summary
    
    # 종료 코드 결정
    if [ $ERROR_COUNT -gt 0 ]; then
        exit 1
    elif [ $WARNING_COUNT -gt 0 ]; then
        exit 2
    else
        exit 0
    fi
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
