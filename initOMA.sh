#!/bin/bash

# OMA_BASE_DIR 환경 변수 확인 및 설정
if [ -z "$OMA_BASE_DIR" ]; then
    # 현재 스크립트의 디렉토리를 기준으로 OMA_BASE_DIR 설정
    # initOMA.sh가 OMA_BASE_DIR에 있다고 가정
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    export OMA_BASE_DIR="$SCRIPT_DIR"
    echo "OMA_BASE_DIR이 설정되지 않아 자동으로 설정합니다: $OMA_BASE_DIR"
fi

# 언어 설정 로드
load_language_config() {
    if [ -f "$OMA_BASE_DIR/.initOMA.env" ]; then
        source "$OMA_BASE_DIR/.initOMA.env"
    else
        LANG="Korean"
        echo "LANG=Korean" > "$OMA_BASE_DIR/.initOMA.env"
    fi
}

# 언어 설정 저장
save_language_config() {
    echo "LANG=$1" > "$OMA_BASE_DIR/.initOMA.env"
}

# 언어별 메시지 정의
get_message() {
    local key="$1"
    
    if [ "$LANG" = "English" ]; then
        case "$key" in
            "main_title") echo "OMA Main Menu" ;;
            "env_menu") echo "Environment Menu" ;;
            "analysis_menu") echo "Application Analysis Menu" ;;
            "transform_menu") echo "Application Transform Menu" ;;
            "test_menu") echo "SQL Data Test Menu" ;;
            "report_menu") echo "Transform Report" ;;
            "change_lang") echo "Change Language (E/K)" ;;
            "select_menu") echo "Select menu" ;;
            "invalid_choice") echo "Invalid choice. Please try again." ;;
            "exit_program") echo "Exiting program." ;;
            "current_project") echo "Current project" ;;
            "env_setup") echo "Environment Setup & Check" ;;
            "dbms_transform") echo "DBMS Additional Transform" ;;
            "app_analysis") echo "Application Analysis" ;;
            "app_transform") echo "Application Transform" ;;
            "sql_test") echo "SQL Data Test" ;;
            "transform_report") echo "Transform Report" ;;
            "quit") echo "Quit" ;;
            "back_main") echo "Back to Main Menu" ;;
            "lang_changed_en") echo "Language changed to English" ;;
            "lang_changed_ko") echo "Language changed to Korean" ;;
            "env_error") echo "Error: Environment variables not set." ;;
            "env_required") echo "Environment setup is required to perform OMA transformation tasks." ;;
            "env_methods") echo "Environment Setup Methods:" ;;
            "env_initial_setup") echo "1. Initial project setup and environment variable file creation:" ;;
            "env_existing_file") echo "2. If environment variable file already exists (e.g., oma_env_MyProject.sh):" ;;
            "env_check_files") echo "3. Check environment variable files in current directory:" ;;
            "env_files_found") echo "Found environment variable files:" ;;
            "env_select_file") echo "Would you like to select one of the above files to source?" ;;
            "env_select_which") echo "Select the environment variable file to use:" ;;
            "env_cancel") echo "Cancel" ;;
            "env_setup_cancelled") echo "Environment setup cancelled." ;;
            "env_selected_file") echo "Selected file" ;;
            "env_loading") echo "Loading environment variables..." ;;
            "env_load_success") echo "✓ Environment variables loaded successfully." ;;
            "env_load_failed") echo "Failed to load environment variables." ;;
            "env_file_not_found") echo "File not found" ;;
            "env_no_files") echo "No environment variable files found." ;;
            "env_run_setenv") echo "Please run setEnv.sh first to set up the project." ;;
            "env_run_setenv_now") echo "Would you like to run setEnv.sh now? (y/N)" ;;
            "env_running_setenv") echo "Running setEnv.sh..." ;;
            "env_setenv_complete") echo "setEnv.sh execution completed." ;;
            "env_restart_required") echo "Please restart initOMA.sh to load environment variables." ;;
            "env_or_source") echo "Or source the generated environment variable file:" ;;
            "env_setenv_failed") echo "setEnv.sh execution failed." ;;
            "env_skip") echo "Skipping environment setup." ;;
            "env_manual_setup") echo "Please set up the environment manually and run again." ;;
            "env_check_complete") echo "✅ Environment variable check complete!" ;;
            "env_redo") echo "Re-perform environment setup" ;;
            "env_check_current") echo "Check current environment variables" ;;
            "env_redo_desc") echo "Re-perform environment setup (setEnv.sh)" ;;
            "env_check_desc") echo "Check current environment variables (checkEnv.sh)" ;;
            "env_redo_start") echo "Re-performing environment setup." ;;
            "env_running_setenv_script") echo "Running setEnv.sh..." ;;
            "env_setup_complete") echo "Environment setup completed." ;;
            "env_continue") echo "Environment variables are set, you can continue." ;;
            "env_setup_failed") echo "Environment setup failed." ;;
            "env_check_start") echo "Checking current environment variables." ;;
            "app_analysis_desc") echo ": Java source code and MyBatis Mapper file analysis" ;;
            "app_report_desc") echo ": HTML report generation and SQL transformation target list extraction" ;;
            "postgresql_meta_desc") echo ": PostgreSQL database metadata generation (using Amazon Q Chat)" ;;
            "postgresql_only") echo "(PostgreSQL Only) Database metadata creation" ;;
            "sample_transform") echo "Sample Transform" ;;
            "full_transform") echo "Application SQL Full Transform" ;;
            "compare_xmls") echo "Compare XMLs" ;;
            "compare_xmls_desc") echo ": Compare original and transformed XML files" ;;
            "test_fix") echo "Transform Test & Result Fix" ;;
            "test_fix_desc") echo ": Syntax validation" ;;
            "xml_merge") echo "XML Merge - SQLID to XML" ;;
            "important_notice") echo "⚠️  Important Notice" ;;
            "sample_first") echo "After performing Sample transformation, you must first perform testing and result fixing." ;;
            "adjust_prompt") echo "This allows you to adjust the transformation prompt to match project characteristics." ;;
            "bind_generation") echo "Bind Variable Generation" ;;
            "bind_generation_desc") echo ": Generate bind variables for SQL Unit Test" ;;
            "sql_unittest") echo "Application SQL Unit Test" ;;
            "sql_unittest_desc") echo ": Test transformed SQL and analyze results (DB connection required)" ;;
            "sql_result_fix") echo "SQL Result Mismatch Fix" ;;
            "sql_result_fix_desc") echo ": Fix SQL statements with different results between source and target" ;;
            "db_connection_required") echo "OMA transformation tasks related to databases require pre-configured AWS environment connected to Source system." ;;
            "db_tasks") echo "(DB Schema transformation, SQL Unit Test, etc.)" ;;
            "aws_setup_required") echo "If pre-environment configuration is needed, please perform AWS environment setup first." ;;
            *) echo "$key" ;;
        esac
    else
        case "$key" in
            "main_title") echo "OMA 메인 메뉴" ;;
            "env_menu") echo "환경 메뉴" ;;
            "analysis_menu") echo "애플리케이션 분석 메뉴" ;;
            "transform_menu") echo "애플리케이션 변환 메뉴" ;;
            "test_menu") echo "SQL 데이터 테스트 수행 메뉴" ;;
            "report_menu") echo "변환 작업 보고서" ;;
            "change_lang") echo "언어 변경 (E/K)" ;;
            "select_menu") echo "메뉴를 선택하세요" ;;
            "invalid_choice") echo "잘못된 선택입니다. 다시 선택하세요." ;;
            "exit_program") echo "프로그램을 종료합니다." ;;
            "current_project") echo "현재 설정된 프로젝트" ;;
            "env_setup") echo "환경 설정 및 확인" ;;
            "dbms_transform") echo "DBMS 추가변환" ;;
            "app_analysis") echo "애플리케이션 분석" ;;
            "app_transform") echo "애플리케이션 변환" ;;
            "sql_test") echo "SQL 데이터 테스트 수행" ;;
            "transform_report") echo "변환 작업 보고서" ;;
            "quit") echo "종료" ;;
            "back_main") echo "메인 메뉴로 돌아가기" ;;
            "lang_changed_en") echo "언어가 영어로 변경되었습니다" ;;
            "lang_changed_ko") echo "언어가 한국어로 변경되었습니다" ;;
            "env_error") echo "오류: 환경 변수가 설정되지 않았습니다." ;;
            "env_required") echo "OMA 변환 작업을 수행하려면 먼저 환경 설정이 필요합니다." ;;
            "env_methods") echo "환경 설정 방법:" ;;
            "env_initial_setup") echo "1. 프로젝트 초기 설정 및 환경 변수 파일 생성:" ;;
            "env_existing_file") echo "2. 환경 변수 파일이 이미 있는 경우 (예: oma_env_MyProject.sh):" ;;
            "env_check_files") echo "3. 현재 디렉토리의 환경 변수 파일 확인:" ;;
            "env_files_found") echo "발견된 환경 변수 파일들:" ;;
            "env_select_file") echo "위 파일 중 하나를 선택하여 source 하시겠습니까?" ;;
            "env_select_which") echo "사용할 환경 변수 파일을 선택하세요:" ;;
            "env_cancel") echo "취소" ;;
            "env_setup_cancelled") echo "환경 설정을 취소합니다." ;;
            "env_selected_file") echo "선택된 파일" ;;
            "env_loading") echo "환경 변수를 로딩합니다..." ;;
            "env_load_success") echo "✓ 환경 변수가 성공적으로 로딩되었습니다." ;;
            "env_load_failed") echo "환경 변수 로딩에 실패했습니다." ;;
            "env_file_not_found") echo "파일을 찾을 수 없습니다" ;;
            "env_no_files") echo "환경 변수 파일이 발견되지 않았습니다." ;;
            "env_run_setenv") echo "setEnv.sh를 먼저 실행하여 프로젝트를 설정하세요." ;;
            "env_run_setenv_now") echo "지금 setEnv.sh를 실행하시겠습니까? (y/N)" ;;
            "env_running_setenv") echo "setEnv.sh를 실행합니다..." ;;
            "env_setenv_complete") echo "setEnv.sh 실행이 완료되었습니다." ;;
            "env_restart_required") echo "환경 변수를 로딩하기 위해 initOMA.sh를 다시 실행하세요." ;;
            "env_or_source") echo "또는 생성된 환경 변수 파일을 source 하세요:" ;;
            "env_setenv_failed") echo "setEnv.sh 실행에 실패했습니다." ;;
            "env_skip") echo "환경 설정을 건너뜁니다." ;;
            "env_manual_setup") echo "수동으로 환경을 설정한 후 다시 실행하세요." ;;
            "env_check_complete") echo "✅ 환경 변수 확인 완료!" ;;
            "env_redo") echo "환경 설정 다시 수행" ;;
            "env_check_current") echo "현재 환경 변수 확인" ;;
            "env_redo_desc") echo "환경 설정 다시 수행 (setEnv.sh)" ;;
            "env_check_desc") echo "현재 환경 변수 확인 (checkEnv.sh)" ;;
            "env_redo_start") echo "환경 설정을 다시 수행합니다." ;;
            "env_running_setenv_script") echo "setEnv.sh를 실행합니다..." ;;
            "env_setup_complete") echo "환경 설정이 완료되었습니다." ;;
            "env_continue") echo "환경 변수가 설정되었으므로 계속 진행할 수 있습니다." ;;
            "env_setup_failed") echo "환경 설정에 실패했습니다." ;;
            "env_check_start") echo "현재 환경 변수를 확인합니다." ;;
            "app_analysis_desc") echo " : Java 소스 코드 및 MyBatis Mapper 파일 분석" ;;
            "app_report_desc") echo " : HTML 리포트 생성 및 SQL 변환 대상 목록 추출" ;;
            "postgresql_meta_desc") echo " : PostgreSQL 데이터베이스 메타데이터 생성 (Amazon Q Chat 사용)" ;;
            "postgresql_only") echo "(PostgreSQL Only) 데이터베이스 메타데이터 작성" ;;
            "sample_transform") echo "샘플 변환" ;;
            "full_transform") echo "애플리케이션 SQL 전체 변환 작업" ;;
            "compare_xmls") echo "Compare XMLs" ;;
            "compare_xmls_desc") echo " : 원본과 변환된 XML 파일 비교" ;;
            "test_fix") echo "변환 테스트 및 결과 수정" ;;
            "test_fix_desc") echo " : 문법 검증" ;;
            "xml_merge") echo "XML Merge 작업 - SQLID to XML" ;;
            "important_notice") echo "⚠️  중요 안내" ;;
            "sample_first") echo "Sample 변환을 수행한 이후에, 테스트 및 결과 수정을 먼저 수행해야 합니다." ;;
            "adjust_prompt") echo "이를 통해서 변환 프롬프트를 프로젝트 특성에 맞게 조정해야 합니다." ;;
            "bind_generation") echo "바인드 변수 생성" ;;
            "bind_generation_desc") echo " : SQL Unit Test 용 바인드 변수 생성" ;;
            "sql_unittest") echo "애플리케이션 SQL Unit Test" ;;
            "sql_unittest_desc") echo " : 변환된 SQL 테스트 및 결과 분석 (DB 연결 필요)" ;;
            "sql_result_fix") echo "SQL 결과 불일치 수정" ;;
            "sql_result_fix_desc") echo " : 소스와 타겟의 결과가 다른 SQL 구문 수정" ;;
            "db_connection_required") echo "OMA 변환 작업 수행 중 데이터베이스 연관된 작업은 Source 시스템과 연결이 되는 AWS 환경 구성을 사전에 요구합니다." ;;
            "db_tasks") echo "(DB Schema 변환, SQL Unit Test 등)" ;;
            "aws_setup_required") echo "사전 환경 구성이 필요한 경우 AWS 환경 설정을 먼저 수행하세요." ;;
            *) echo "$key" ;;
        esac
    fi
}

# 언어 변경 함수
change_language() {
    echo -ne "${CYAN}$(get_message "change_lang"): ${NC}"
    read lang_choice
    
    case $lang_choice in
        e|E)
            save_language_config "English"
            LANG="English"
            echo -e "${GREEN}$(get_message "lang_changed_en")${NC}"
            ;;
        k|K)
            save_language_config "Korean"
            LANG="Korean"
            echo -e "${GREEN}$(get_message "lang_changed_ko")${NC}"
            ;;
        *)
            echo -e "${RED}$(get_message "invalid_choice")${NC}"
            return 1
            ;;
    esac
    sleep 2
    clear
}

# 언어 설정 로드
load_language_config

# bin 디렉토리로 이동
cd "$OMA_BASE_DIR/bin"

# 화면 지우기
clear

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



# ====================================================
# 환경 변수 확인 함수
# ====================================================
check_environment() {
    if [ -z "$APPLICATION_NAME" ]; then
        print_separator
        echo -e "${RED}${BOLD}$(get_message "env_error")${NC}"
        print_separator
        echo -e "${YELLOW}$(get_message "env_required")${NC}"
        echo ""
        echo -e "${CYAN}${BOLD}$(get_message "env_methods")${NC}"
        echo -e "${CYAN}$(get_message "env_initial_setup")${NC}"
        echo -e "${GREEN}   ./setEnv.sh${NC}"
        echo ""
        echo -e "${CYAN}$(get_message "env_existing_file")${NC}"
        echo -e "${GREEN}   source ./oma_env_프로젝트명.sh${NC}"
        echo ""
        echo -e "${CYAN}$(get_message "env_check_files")${NC}"
        echo -e "${GREEN}   ls -la oma_env_*.sh${NC}"
        print_separator

        # OMA_BASE_DIR에 환경 변수 파일이 있는지 확인
        cd "$OMA_BASE_DIR"
        env_files=(oma_env_*.sh)
        if [ -f "${env_files[0]}" ]; then
            echo -e "${BLUE}${BOLD}$(get_message "env_files_found")${NC}"
            for file in oma_env_*.sh; do
                if [ -f "$file" ]; then
                    echo -e "${GREEN}  - $file${NC}"
                fi
            done
            echo ""
            echo -e "${YELLOW}$(get_message "env_select_file")${NC}"
            echo -ne "${BLUE}${BOLD}$(get_message "env_select_file") (y/N): ${NC}"
            read select_env_file

            if [[ "$select_env_file" =~ ^[Yy]$ ]]; then
                echo -e "${CYAN}$(get_message "env_select_which")${NC}"
                select env_file in oma_env_*.sh "$(get_message "env_cancel")"; do
                    case $env_file in
                        "$(get_message "env_cancel")")
                            echo -e "${YELLOW}$(get_message "env_setup_cancelled")${NC}"
                            exit 1
                            ;;
                        *.sh)
                            if [ -f "$env_file" ]; then
                                echo -e "${GREEN}$(get_message "env_selected_file"): $env_file${NC}"
                                echo -e "${BLUE}$(get_message "env_loading")${NC}"
                                source "$OMA_BASE_DIR/$env_file"
                                if [ -n "$APPLICATION_NAME" ]; then
                                    echo -e "${GREEN}$(get_message "env_load_success")${NC}"
                                    echo -e "${GREEN}$(get_message "current_project"): $APPLICATION_NAME${NC}"
                                    cd "$OMA_BASE_DIR/bin"
                                    return 0
                                else
                                    echo -e "${RED}$(get_message "env_load_failed")${NC}"
                                    exit 1
                                fi
                            else
                                echo -e "${RED}$(get_message "env_file_not_found"): $env_file${NC}"
                            fi
                            break
                            ;;
                        *)
                            echo -e "${RED}$(get_message "invalid_choice")${NC}"
                            ;;
                    esac
                done
            else
                echo -e "${YELLOW}$(get_message "env_skip")${NC}"
                echo -e "${CYAN}$(get_message "env_manual_setup")${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}$(get_message "env_no_files")${NC}"
            echo -e "${CYAN}$(get_message "env_run_setenv")${NC}"
            echo ""
            echo -ne "${BLUE}${BOLD}$(get_message "env_run_setenv_now"): ${NC}"
            read run_setenv

            if [[ "$run_setenv" =~ ^[Yy]$ ]]; then
                echo -e "${GREEN}$(get_message "env_running_setenv")${NC}"
                print_separator
                cd "$OMA_BASE_DIR/bin"
                ./setEnv.sh
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}$(get_message "env_setenv_complete")${NC}"
                    echo -e "${YELLOW}$(get_message "env_restart_required")${NC}"
                    echo -e "${CYAN}$(get_message "env_or_source")${NC}"
                    cd "$OMA_BASE_DIR"
                    for file in oma_env_*.sh; do
                        if [ -f "$file" ]; then
                            echo -e "${GREEN}  source $OMA_BASE_DIR/$file${NC}"
                            break
                        fi
                    done
                else
                    echo -e "${RED}$(get_message "env_setenv_failed")${NC}"
                fi
                exit 0
            else
                echo -e "${YELLOW}$(get_message "env_skip")${NC}"
                exit 1
            fi
        fi
    else
        print_separator
        echo -e "${GREEN}${BOLD}$(get_message "env_check_complete")${NC}"
        echo -e "${GREEN}${BOLD}$(get_message "current_project"): $APPLICATION_NAME${NC}"
    fi
}

# ====================================================
# Step별 스크립트 실행 함수들
# ====================================================

# 환경 설정 다시 수행
execute_setenv() {
    print_separator
    echo -e "${YELLOW}$(get_message "env_redo_start")${NC}"
    echo -e "${CYAN}$(get_message "env_running_setenv_script")${NC}"
    cd "$OMA_BASE_DIR/bin"
    ./setEnv.sh
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}$(get_message "env_setup_complete")${NC}"
        echo -e "${YELLOW}$(get_message "env_continue")${NC}"
    else
        echo -e "${RED}$(get_message "env_setup_failed")${NC}"
        return 1
    fi
    print_separator
}

# 현재 환경 변수 확인
execute_checkenv() {
    print_separator
    echo -e "${CYAN}$(get_message "env_check_start")${NC}"
    cd "$OMA_BASE_DIR/bin"
    ./checkEnv.sh
    print_separator
}

# DB Schema 변환
execute_db_schema() {
    print_separator
    echo -e "${BLUE}${BOLD}DB Schema 변환을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}DB Schema 변환 스크립트 실행${NC}"

    if [ -f "$OMA_BASE_DIR/bin/processDbSchema.sh" ]; then
        echo -e "${CYAN}processDbSchema.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processDbSchema.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}DB Schema 변환이 완료되었습니다.${NC}"
        else
            echo -e "${RED}DB Schema 변환 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processDbSchema.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# 애플리케이션 분석
execute_app_analysis() {
    print_separator
    echo -e "${BLUE}${BOLD}애플리케이션 분석을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}애플리케이션 분석 스크립트 실행${NC}"

    if [ -f "$OMA_BASE_DIR/bin/processAppAnalysis.sh" ]; then
        echo -e "${CYAN}processAppAnalysis.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processAppAnalysis.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}애플리케이션 분석이 완료되었습니다.${NC}"
        else
            echo -e "${RED}애플리케이션 분석 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processAppAnalysis.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# 분석 보고서 작성
execute_app_reporting() {
    print_separator
    echo -e "${BLUE}${BOLD}분석 보고서 작성을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}분석 보고서 작성 스크립트 실행${NC}"

    if [ -f "$OMA_BASE_DIR/bin/processAppReporting.sh" ]; then
        echo -e "${CYAN}processAppReporting.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processAppReporting.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}분석 보고서 작성이 완료되었습니다.${NC}"
        else
            echo -e "${RED}분석 보고서 작성 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processAppReporting.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# SQL 샘플 변환
execute_sql_sample_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}SQL 샘플 변환 작업을 시작하기 전 3초 대기합니다...${NC}"
    echo ""
    echo -e "${BLUE}${BOLD}샘플 변환: SampleTransformTarget.csv의 샘플 항목만 변환합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}SQL 샘플 변환 스크립트 실행${NC}"

    if [ -f "$APP_TOOLS_FOLDER/sqlTransformTarget.py" ]; then
        echo -e "${CYAN}sqlTransformTarget.py를 샘플 모드로 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py --file $APP_TRANSFORM_FOLDER/SampleTransformTarget.csv${NC}"
        cd "$OMA_BASE_DIR/bin"
        python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --file "$APP_TRANSFORM_FOLDER/SampleTransformTarget.csv"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}SQL 샘플 변환 작업이 완료되었습니다.${NC}"
        else
            echo -e "${RED}SQL 샘플 변환 작업 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $APP_TOOLS_FOLDER/sqlTransformTarget.py 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# SQL 전체 변환
execute_sql_full_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}SQL 전체 변환 작업을 시작하기 전 3초 대기합니다...${NC}"
    echo ""
    echo -e "${BLUE}${BOLD}전체 변환: SQLTransformTarget.csv의 모든 항목을 변환합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}SQL 전체 변환 스크립트 실행${NC}"

    if [ -f "$APP_TOOLS_FOLDER/sqlTransformTarget.py" ]; then
        echo -e "${CYAN}sqlTransformTarget.py를 전체 모드로 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py${NC}"
        cd "$OMA_BASE_DIR/bin"
        python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}SQL 전체 변환 작업이 완료되었습니다.${NC}"
        else
            echo -e "${RED}SQL 전체 변환 작업 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $APP_TOOLS_FOLDER/sqlTransformTarget.py 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# XML List 생성
execute_xml_list_generation() {
    print_separator
    echo -e "${BLUE}${BOLD}바인드 변수 생성을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}바인드 변수 생성 스크립트 실행${NC}"

    if [ -f "$OMA_BASE_DIR/bin/test/run_bind_generator.sh" ]; then
        echo -e "${CYAN}run_bind_generator.sh를 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_bind_generator.sh${NC}"
        "$OMA_BASE_DIR/bin/test/run_bind_generator.sh"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}바인드 변수 생성이 완료되었습니다.${NC}"
        else
            echo -e "${RED}바인드 변수 생성 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/test/run_bind_generator.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# SQL Unit Test
execute_sql_unittest() {
    print_separator
    echo -e "${BLUE}${BOLD}애플리케이션 SQL Unit Test를 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}SQL Unit Test 스크립트 실행${NC}"

    # Oracle 테스트 실행
    if [ -f "$OMA_BASE_DIR/bin/test/run_oracle.sh" ]; then
        echo -e "${CYAN}Oracle 테스트를 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_oracle.sh $SOURCE_SQL_MAPPER_FOLDER/mapper${NC}"
        cd "$OMA_BASE_DIR/bin/test"
        ./run_oracle.sh "$SOURCE_SQL_MAPPER_FOLDER/mapper"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Oracle 테스트가 완료되었습니다.${NC}"
        else
            echo -e "${RED}Oracle 테스트 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/test/run_oracle.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi

    # Target DBMS 테스트 실행
    if [ "$TARGET_DBMS_TYPE" = "postgres" ]; then
        if [ -f "$OMA_BASE_DIR/bin/test/run_postgresql.sh" ]; then
            echo -e "${CYAN}PostgreSQL 테스트를 실행합니다...${NC}"
            echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_postgresql.sh $TARGET_SQL_MAPPER_FOLDER/mapper${NC}"
            cd "$OMA_BASE_DIR/bin/test"
            ./run_postgresql.sh "$TARGET_SQL_MAPPER_FOLDER/mapper"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}PostgreSQL 테스트가 완료되었습니다.${NC}"
            else
                echo -e "${RED}PostgreSQL 테스트 중 오류가 발생했습니다.${NC}"
            fi
        else
            echo -e "${RED}오류: $OMA_BASE_DIR/bin/test/run_postgresql.sh 파일을 찾을 수 없습니다.${NC}"
            return 1
        fi
    elif [ "$TARGET_DBMS_TYPE" = "mysql" ]; then
        if [ -f "$OMA_BASE_DIR/bin/test/run_mysql.sh" ]; then
            echo -e "${CYAN}MySQL 테스트를 실행합니다...${NC}"
            echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_mysql.sh $TARGET_SQL_MAPPER_FOLDER/mapper${NC}"
            cd "$OMA_BASE_DIR/bin/test"
            ./run_mysql.sh "$TARGET_SQL_MAPPER_FOLDER/mapper"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}MySQL 테스트가 완료되었습니다.${NC}"
            else
                echo -e "${RED}MySQL 테스트 중 오류가 발생했습니다.${NC}"
            fi
        else
            echo -e "${RED}오류: $OMA_BASE_DIR/bin/test/run_mysql.sh 파일을 찾을 수 없습니다.${NC}"
            return 1
        fi
    else
        echo -e "${RED}오류: 지원되지 않는 TARGET_DBMS_TYPE입니다: $TARGET_DBMS_TYPE${NC}"
        return 1
    fi

    print_separator
}

# 샘플 테스트 및 결과 수정
execute_sample_test_fix() {
    print_separator
    echo -e "${BLUE}${BOLD}샘플 테스트 및 결과 수정을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}샘플 테스트 및 결과 수정을 수행합니다...${NC}"

    if [ -f "$APP_TOOLS_FOLDER/../postTransform/editErrors.md" ]; then
        echo -e "${CYAN}editErrors.md를 사용하여 Amazon Q chat을 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}q chat --trust-all-tools \"$APP_TOOLS_FOLDER/../postTransform/editErrors.md\"${NC}"
        q chat --trust-all-tools "$APP_TOOLS_FOLDER/../postTransform/editErrors.md"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}샘플 테스트 및 결과 수정이 완료되었습니다.${NC}"
        else
            echo -e "${RED}샘플 테스트 및 결과 수정 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $APP_TOOLS_FOLDER/../postTransform/editErrors.md 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi

    print_separator
}

# SQL 변환 Merge
execute_sql_transform_merge() {
    print_separator
    echo -e "${BLUE}${BOLD}SQL 변환 Merge 작업을 시작하기 전 3초 대기합니다...${NC}"
    echo ""
    echo -e "${BLUE}${BOLD}변환된 SQL들을 Merge 처리합니다...${NC}"
    sleep 3

    # Merge 작업 전에 delete_target_xml_files.sh 실행
    if [ -f "$APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh" ]; then
        echo -e "${CYAN}Merge 작업 전 delete_target_xml_files.sh를 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}$APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh${NC}"
        "$APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}delete_target_xml_files.sh 실행이 완료되었습니다.${NC}"
        else
            echo -e "${RED}delete_target_xml_files.sh 실행 중 오류가 발생했습니다.${NC}"
            echo -e "${YELLOW}계속 진행합니다...${NC}"
        fi
    else
        echo -e "${YELLOW}경고: $APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh 파일을 찾을 수 없습니다.${NC}"
        echo -e "${YELLOW}Merge 작업을 계속 진행합니다...${NC}"
    fi
    echo -e "${BLUE}${BOLD}SQL 변환 Merge 스크립트 실행${NC}"

    if [ -f "$OMA_BASE_DIR/bin/processSqlTransform.sh" ]; then
        echo -e "${CYAN}processSqlTransform.sh merge 옵션으로 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processSqlTransform.sh merge
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}SQL 변환 Merge 작업이 완료되었습니다.${NC}"
        else
            echo -e "${RED}SQL 변환 Merge 작업 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processSqlTransform.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# 변환 작업 보고서
execute_transform_report() {
    print_separator
    echo -e "${BLUE}${BOLD}변환 작업 보고서를 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}변환 작업 보고서 스크립트 실행${NC}"

    if [ -f "$OMA_BASE_DIR/bin/processSqlTransformReport.sh" ]; then
        echo -e "${CYAN}processSqlTransformReport.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processSqlTransformReport.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}변환 작업 보고서가 완료되었습니다.${NC}"
        else
            echo -e "${RED}변환 작업 보고서 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processSqlTransformReport.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# PostgreSQL 메타데이터 작성
execute_postgresql_meta() {
    print_separator
    echo -e "${BLUE}${BOLD}PostgreSQL 데이터베이스 메타데이터 작성을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}PostgreSQL 메타데이터 작성 스크립트 실행${NC}"

    if [ -f "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh" ]; then
        echo -e "${CYAN}genPostgreSqlMeta.sh를 직접 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh${NC}"
        "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}PostgreSQL 메타데이터 작성이 완료되었습니다.${NC}"
        else
            echo -e "${RED}PostgreSQL 메타데이터 작성 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $APP_TOOLS_FOLDER/genPostgreSqlMeta.sh 파일을 찾을 수 없습니다.${NC}"
        echo -e "${YELLOW}대안: 기존 AI 방식을 사용합니다...${NC}"
        if [ -f "$APP_TOOLS_FOLDER/genPostgreSqlMeta.md" ]; then
            echo -e "${CYAN}genPostgreSQLMeta.md를 사용하여 Amazon Q chat을 실행합니다...${NC}"
            echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/genPostgreSqlMeta.md${NC}"
            q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/genPostgreSqlMeta.md"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}PostgreSQL 메타데이터 작성이 완료되었습니다.${NC}"
            else
                echo -e "${RED}PostgreSQL 메타데이터 작성 중 오류가 발생했습니다.${NC}"
            fi
        else
            echo -e "${RED}오류: $APP_TOOLS_FOLDER/genPostgreSqlMeta.md 파일도 찾을 수 없습니다.${NC}"
            return 1
        fi
    fi
    print_separator
}

# Java Source 변환
execute_java_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}애플리케이션 Java Source 변환 작업을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}Java Source 변환 작업을 수행합니다...${NC}"
    echo ""
    echo -e "${RED}${BOLD}⚠️  중요 안내: Target Java Source Folder 지정 필요${NC}"
    echo -e "${YELLOW}${BOLD}Java Source 변환 작업 시 변환할 Java 소스 코드가 위치한 디렉토리를 지정해야 합니다.${NC}"
    echo -e "${CYAN}${BOLD}예시: /workspace/project/src/main/java 또는 /home/user/myproject/backend${NC}"
    echo ""

    if [ -f "$OMA_BASE_DIR/bin/postTransform/convertOracleJava.md" ]; then
        echo -e "${CYAN}convertOracleJava.md를 사용하여 Amazon Q chat을 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}q chat --trust-all-tools \"$OMA_BASE_DIR/bin/postTransform/convertOracleJava.md\"${NC}"
        q chat --trust-all-tools "$OMA_BASE_DIR/bin/postTransform/convertOracleJava.md"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Java Source 변환 작업이 완료되었습니다.${NC}"
        else
            echo -e "${RED}Java Source 변환 작업 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/postTransform/convertOracleJava.md 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi

    print_separator
}

# ====================================================
# 메뉴 함수들
# ====================================================

# 환경 메뉴
show_environment_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}0. $(get_message "env_menu")${NC}"
        print_separator
        echo -e "${CYAN}1. $(get_message "env_redo")${NC}${YELLOW} (setEnv.sh)${NC}"
        echo -e "${CYAN}2. $(get_message "env_check_current")${NC}${YELLOW} (checkEnv.sh)${NC}"
        echo -e "${YELLOW}b. $(get_message "back_main")${NC}"
        echo -e "${YELLOW}q. $(get_message "quit")${NC}"
        print_separator
        echo -ne "${CYAN}$(get_message "select_menu") (1,2,b,q): ${NC}"
        read choice

        case $choice in
            1)
                clear
                execute_setenv
                ;;
            2)
                clear
                execute_checkenv
                ;;
            b|B)
                clear
                return
                ;;
            q|Q)
                clear
                print_separator
                echo -e "${GREEN}$(get_message "exit_program")${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}$(get_message "invalid_choice")${NC}"
                sleep 2
                clear
                ;;
        esac
    done
}

# 애플리케이션 분석 메뉴
show_analysis_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}2. 애플리케이션 분석 메뉴${NC}"
        print_separator
        echo -e "${CYAN}1. 애플리케이션 분석${NC}${YELLOW} : Java 소스 코드 및 MyBatis Mapper 파일 분석${NC}"
        echo ""
        echo -e "${CYAN}2. 분석 보고서 작성 및 SQL변환 대상 추출${NC}${YELLOW} : HTML 리포트 생성 및 SQL 변환 대상 목록 추출${NC}"
        echo ""
        echo -e "${CYAN}3. (PostgreSQL Only) 데이터베이스 메타데이터 작성${NC}${YELLOW} : PostgreSQL 데이터베이스 메타데이터 생성 (Amazon Q Chat 사용)${NC}"
        echo ""
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        echo -e "${YELLOW}q. 종료${NC}"
        echo -ne "${CYAN}선택하세요 (1,2,3,b,q): ${NC}"
        read choice

        case $choice in
            1)
                clear
                execute_app_analysis
                ;;
            2)
                clear
                execute_app_reporting
                ;;
            3)
                clear
                execute_postgresql_meta
                ;;
            b|B)
                clear
                return
                ;;
            q|Q)
                clear
                print_separator
                echo -e "${GREEN}프로그램을 종료합니다.${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 선택하세요.${NC}"
                sleep 2
                clear
                ;;
        esac
    done
}

# 애플리케이션 분석 메뉴
show_analysis_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}2. $(get_message "analysis_menu")${NC}"
        print_separator
        echo -e "${CYAN}1. $(get_message "app_analysis")${NC}${YELLOW}$(get_message "app_analysis_desc")${NC}"
        echo ""
        echo -e "${CYAN}2. $(get_message "app_report_desc" | cut -d':' -f1)${NC}${YELLOW}$(get_message "app_report_desc")${NC}"
        echo ""
        echo -e "${CYAN}3. $(get_message "postgresql_only")${NC}${YELLOW}$(get_message "postgresql_meta_desc")${NC}"
        echo ""
        echo -e "${YELLOW}b. $(get_message "back_main")${NC}"
        echo -e "${YELLOW}q. $(get_message "quit")${NC}"
        print_separator
        echo -ne "${CYAN}$(get_message "select_menu") (1,2,3,b,q): ${NC}"
        read choice

        case $choice in
            1)
                clear
                execute_app_analysis
                ;;
            2)
                clear
                execute_app_reporting
                ;;
            3)
                clear
                execute_postgresql_meta
                ;;
            b|B)
                clear
                return
                ;;
            q|Q)
                clear
                print_separator
                echo -e "${GREEN}$(get_message "exit_program")${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}$(get_message "invalid_choice")${NC}"
                sleep 2
                clear
                ;;
        esac
    done
}

# Compare XMLs 실행
execute_compare_xmls() {
    print_separator
    echo -e "${BLUE}${BOLD}XML 파일 비교 도구를 실행합니다...${NC}"

    if [ -f "$APP_TOOLS_FOLDER/compareXMLs.sh" ]; then
        echo -e "${CYAN}compareXMLs.sh를 실행합니다...${NC}"
        "$APP_TOOLS_FOLDER/compareXMLs.sh"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}XML 파일 비교가 완료되었습니다.${NC}"
        else
            echo -e "${RED}XML 파일 비교 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $APP_TOOLS_FOLDER/compareXMLs.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# Parameter 구성 실행
execute_parameter_config() {
    print_separator
    echo -e "${BLUE}${BOLD}Parameter 구성을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}Parameter 구성 스크립트 실행${NC}"

    if [ -f "$APP_TOOLS_FOLDER/../test/bulk_prepare.sh" ]; then
        echo -e "${CYAN}bulk_prepare.sh를 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}$APP_TOOLS_FOLDER/../test/bulk_prepare.sh $SOURCE_SQL_MAPPER_FOLDER${NC}"
        (cd "$APP_TOOLS_FOLDER/../test" && ./bulk_prepare.sh "$SOURCE_SQL_MAPPER_FOLDER")
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Parameter 구성이 완료되었습니다.${NC}"
        else
            echo -e "${RED}Parameter 구성 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $APP_TOOLS_FOLDER/../test/bulk_prepare.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# 애플리케이션 변환 메뉴
show_application_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}3. $(get_message "transform_menu")${NC}"
        print_separator
        echo -e "${RED}${BOLD}$(get_message "important_notice")${NC}"
        echo -e "${YELLOW}$(get_message "sample_first")${NC}"
        echo -e "${YELLOW}$(get_message "adjust_prompt")${NC}"
        print_separator
        echo -e "${CYAN}1. $(get_message "sample_transform")${NC}"
        echo -e "${CYAN}2. $(get_message "full_transform")${NC}"
        echo ""
        echo -e "${CYAN}3. $(get_message "compare_xmls")${NC}${YELLOW}$(get_message "compare_xmls_desc")${NC}"
        echo -e "${CYAN}4. $(get_message "test_fix")${NC}${YELLOW}$(get_message "test_fix_desc")${NC}"
        echo ""
        echo -e "${CYAN}5. $(get_message "xml_merge")${NC}"
        echo ""
        echo -e "${YELLOW}b. $(get_message "back_main")${NC}"
        echo -e "${YELLOW}q. $(get_message "quit")${NC}"
        print_separator
        echo -ne "${CYAN}$(get_message "select_menu") (1,2,3,4,5,b,q): ${NC}"
        read choice

        case $choice in
            1)
                clear
                execute_sql_sample_transform
                ;;
            2)
                clear
                execute_sql_full_transform
                ;;
            3)
                clear
                execute_compare_xmls
                ;;
            4)
                clear
                execute_sample_test_fix
                ;;
            5)
                clear
                execute_sql_transform_merge
                ;;
            b|B)
                clear
                return
                ;;
            q|Q)
                clear
                print_separator
                echo -e "${GREEN}$(get_message "exit_program")${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}$(get_message "invalid_choice")${NC}"
                sleep 2
                clear
                ;;
        esac
    done
}

# SQL 결과 불일치 수정
execute_sql_result_fix() {
    print_separator
    echo -e "${BLUE}${BOLD}SQL 결과 불일치 수정을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}SQL 결과 불일치 수정 스크립트 실행${NC}"

    if [ -f "$OMA_BASE_DIR/bin/test/analyze_results.sh" ]; then
        echo -e "${CYAN}analyze_results.sh를 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}cd $OMA_BASE_DIR/bin/test && ./analyze_results.sh${NC}"
        cd "$OMA_BASE_DIR/bin/test"
        ./analyze_results.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}SQL 결과 불일치 수정이 완료되었습니다.${NC}"
        else
            echo -e "${RED}SQL 결과 불일치 수정 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/test/analyze_results.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# SQL 데이터 테스트 수행 메뉴
show_test_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}4. $(get_message "test_menu")${NC}"
        print_separator
        echo -e "${CYAN}1. $(get_message "bind_generation")${NC}${YELLOW}$(get_message "bind_generation_desc")${NC}"
        echo -e "${CYAN}2. $(get_message "sql_unittest")${NC}${YELLOW}$(get_message "sql_unittest_desc")${NC}"
        echo -e "${CYAN}3. $(get_message "sql_result_fix")${NC}${YELLOW}$(get_message "sql_result_fix_desc")${NC}"
        echo -e "${YELLOW}b. $(get_message "back_main")${NC}"
        echo -e "${YELLOW}q. $(get_message "quit")${NC}"
        print_separator
        echo -ne "${CYAN}$(get_message "select_menu") (1,2,3,b,q): ${NC}"
        read choice

        case $choice in
            1)
                clear
                execute_xml_list_generation
                ;;
            2)
                clear
                execute_sql_unittest
                ;;
            3)
                clear
                execute_sql_result_fix
                ;;
            b|B)
                clear
                return
                ;;
            q|Q)
                clear
                print_separator
                echo -e "${GREEN}$(get_message "exit_program")${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}$(get_message "invalid_choice")${NC}"
                sleep 2
                clear
                ;;
        esac
    done
}

# 변환 작업 보고서 메뉴
show_completion_menu() {
    clear
    execute_transform_report
}

# ====================================================
# 메인 스크립트 시작
# ====================================================

# 환경 변수 확인
check_environment

# 메인 메뉴 루프
print_separator
echo -e "${BLUE}${BOLD}OMA는 AWS에서 사전 환경이 구성된 상태에서 DB/Application 변환을 수행합니다.${NC}"
echo -e "${GREEN}$(get_message "current_project"): $APPLICATION_NAME${NC}"
echo -e "${RED}${BOLD}$(get_message "important_notice")${NC}"
echo -e "${YELLOW}$(get_message "db_connection_required")${NC}"
echo -e "${YELLOW}$(get_message "db_tasks")${NC}"
echo -e "${CYAN}${BOLD}$(get_message "aws_setup_required")${NC}"

while true; do
    print_separator
    echo -e "${BLUE}${BOLD}$(get_message "main_title")${NC}"
    print_separator
    echo -e "${YELLOW}0. $(get_message "env_setup")${NC}"
    echo -e "${CYAN}1. $(get_message "dbms_transform")${NC}"
    echo -e "${CYAN}2. $(get_message "app_analysis")${NC}"
    echo -e "${CYAN}3. $(get_message "app_transform")${NC}"
    echo -e "${CYAN}4. $(get_message "sql_test")${NC}"
    echo -e "${CYAN}5. $(get_message "transform_report")${NC}"
    echo -e "${MAGENTA}l. $(get_message "change_lang")${NC}"
    echo -e "${YELLOW}q. $(get_message "quit")${NC}"
    print_separator
    echo -ne "${CYAN}$(get_message "select_menu") (0,1,2,3,4,5,l,q): ${NC}"
    read choice

    case $choice in
        0)
            clear
            show_environment_menu
            ;;
        1)
            clear
            execute_db_schema
            ;;
        2)
            clear
            show_analysis_menu
            ;;
        3)
            clear
            show_application_menu
            ;;
        4)
            clear
            show_test_menu
            ;;
        5)
            clear
            show_completion_menu
            ;;
        l|L)
            change_language
            ;;
        q|Q)
            clear
            print_separator
            echo -e "${GREEN}$(get_message "exit_program")${NC}"
            print_separator
            exit 0
            ;;
        *)
            echo -e "${RED}$(get_message "invalid_choice")${NC}"
            sleep 2
            clear
            ;;
    esac
done

echo -e "${GREEN}모든 설정이 완료되었습니다.${NC}"