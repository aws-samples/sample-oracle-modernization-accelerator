#!/bin/bash

# genSQLTransformReport.sh
# SQL Transform Report 생성 스크립트

set -e  # 에러 발생 시 스크립트 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 환경변수 체크 함수
check_environment() {
    log_info "환경변수 체크를 시작합니다..."
    
    local missing_vars=()
    
    # 필수 환경변수 체크
    if [[ -z "$APP_TOOLS_FOLDER" ]]; then
        missing_vars+=("APP_TOOLS_FOLDER")
    fi
    
    # 추가로 필요할 수 있는 환경변수들 체크 (필요에 따라 수정)
    # if [[ -z "$AWS_REGION" ]]; then
    #     missing_vars+=("AWS_REGION")
    # fi
    
    # if [[ -z "$AWS_PROFILE" ]]; then
    #     missing_vars+=("AWS_PROFILE")
    # fi
    
    # 누락된 환경변수가 있는지 확인
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "다음 환경변수들이 설정되지 않았습니다:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_error "필요한 환경변수를 설정한 후 다시 실행해주세요."
        exit 1
    fi
    
    # APP_TOOLS_FOLDER 경로 존재 여부 확인
    if [[ ! -d "$APP_TOOLS_FOLDER" ]]; then
        log_error "APP_TOOLS_FOLDER 경로가 존재하지 않습니다: $APP_TOOLS_FOLDER"
        exit 1
    fi
    
    # SQLTransformReport.txt 파일 존재 여부 확인
    if [[ ! -f "$APP_TOOLS_FOLDER/SQLTransformReport.txt" ]]; then
        log_error "SQLTransformReport.txt 파일이 존재하지 않습니다: $APP_TOOLS_FOLDER/SQLTransformReport.txt"
        exit 1
    fi
    
    log_info "환경변수 체크 완료"
    log_info "APP_TOOLS_FOLDER: $APP_TOOLS_FOLDER"
}

# q 명령어 존재 여부 체크
check_q_command() {
    log_info "q 명령어 존재 여부를 확인합니다..."
    
    if ! command -v q &> /dev/null; then
        log_error "q 명령어를 찾을 수 없습니다."
        log_error "Amazon Q CLI가 설치되어 있는지 확인해주세요."
        exit 1
    fi
    
    log_info "q 명령어 확인 완료"
}

# 메인 실행 함수
run_sql_transform_report() {
    log_info "SQL Transform Report 생성을 시작합니다..."
    log_info "입력 파일: $APP_TOOLS_FOLDER/SQLTransformReport.txt"
    
    # q chat 명령어 실행
    if q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/SQLTransformReport.txt"; then
        log_info "SQL Transform Report 생성이 완료되었습니다."
    else
        log_error "SQL Transform Report 생성 중 오류가 발생했습니다."
        exit 1
    fi
}

# 메인 실행부
main() {
    log_info "=== SQL Transform Report 생성 스크립트 시작 ==="
    
    # 환경변수 체크
    check_environment
    
    # q 명령어 체크
    check_q_command
    
    # SQL Transform Report 실행
    run_sql_transform_report
    
    log_info "=== 스크립트 실행 완료 ==="
}

# 스크립트 실행
main "$@"
