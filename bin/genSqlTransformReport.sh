#!/bin/bash

# genSqlTransformReport.sh
# SQL Transform Report 생성 스크립트

set -e  # 에러 발생 시 스크립트 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Environment variable check function
check_environment() {
    log_info "Starting environment variable check..."
    
    local missing_vars=()
    
    # Check required environment variables
    if [[ -z "$APP_TOOLS_FOLDER" ]]; then
        missing_vars+=("APP_TOOLS_FOLDER")
    fi
    
    # Check additional environment variables that may be needed (modify as needed)
    # if [[ -z "$AWS_REGION" ]]; then
    #     missing_vars+=("AWS_REGION")
    # fi
    
    # if [[ -z "$AWS_PROFILE" ]]; then
    #     missing_vars+=("AWS_PROFILE")
    # fi
    
    # Check if there are missing environment variables
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "The following environment variables are not set:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_error "Please set the required environment variables and run again."
        exit 1
    fi
    
    # Check if APP_TOOLS_FOLDER path exists
    if [[ ! -d "$APP_TOOLS_FOLDER" ]]; then
        log_error "APP_TOOLS_FOLDER path does not exist: $APP_TOOLS_FOLDER"
        exit 1
    fi
    
    # Check if sqlTransformReport.md file exists
    if [[ ! -f "$APP_TOOLS_FOLDER/sqlTransformReport.md" ]]; then
        log_error "sqlTransformReport.md file does not exist: $APP_TOOLS_FOLDER/sqlTransformReport.md"
        exit 1
    fi
    
    log_info "Environment variable check completed"
    log_info "APP_TOOLS_FOLDER: $APP_TOOLS_FOLDER"
}

# Check q command existence
check_q_command() {
    log_info "Checking q command existence..."
    
    if ! command -v q &> /dev/null; then
        log_error "q command not found."
        log_error "Please check if Amazon Q CLI is installed."
        exit 1
    fi
    
    log_info "q command check completed"
}

# Main execution function
run_sql_transform_report() {
    log_info "Starting SQL Transform Report generation..."
    log_info "Input file: $APP_TOOLS_FOLDER/sqlTransformReport.md"
    
    # Execute kiro-cli chat command
    if kiro-cli chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/sqlTransformReport.md"; then
        log_info "SQL Transform Report generation completed."
    else
        log_error "An error occurred during SQL Transform Report generation."
        exit 1
    fi
}

# Main execution section
main() {
    log_info "=== SQL Transform Report Generation Script Started ==="
    
    # Environment variable check
    check_environment
    
    # q command check
    check_q_command
    
    # Execute SQL Transform Report
    run_sql_transform_report
    
    log_info "=== Script execution completed ==="
}

# 스크립트 실행
main "$@"
