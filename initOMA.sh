#!/bin/bash

# 공통 메시지 함수들
msg_error() {
    echo -e "${RED}${ERROR_PREFIX}$1${NC}"
}

msg_success() {
    echo -e "${GREEN}${SUCCESS_PREFIX}$1${NC}"
}

msg_warning() {
    echo -e "${YELLOW}${WARNING_PREFIX}$1${NC}"
}

msg_info() {
    echo -e "${CYAN}$1${NC}"
}

msg_wait_3sec() {
    echo -e "${BLUE}${BOLD}$1${STARTING_TASK}${WAITING_3_SECONDS}${NC}"
    sleep 3
}

msg_script_exec() {
    echo -e "${BLUE}${BOLD}$1 ${SCRIPT_EXECUTION}${NC}"
}

msg_running_script() {
    echo -e "${CYAN}$1${RUNNING_SCRIPT}${NC}"
}

msg_file_not_found() {
    msg_error "${FILE_NOT_FOUND}$1"
}

msg_task_completed() {
    echo -e "${GREEN}$1 ${TASK_COMPLETED}${NC}"
}

msg_task_failed() {
    echo -e "${RED}$1 ${TASK_FAILED}${NC}"
}

# 언어 설정 (기본값: 한국어)
LANGUAGE="ko"

# oma.properties에서 언어 설정 읽기
load_language_from_properties() {
    local props_file="$OMA_BASE_DIR/config/oma.properties"
    if [ -f "$props_file" ]; then
        local lang=$(grep "^LANGUAGE=" "$props_file" | cut -d'=' -f2)
        if [ -n "$lang" ]; then
            LANGUAGE="$lang"
        fi
    fi
}

# oma.properties에 언어 설정 저장
save_language_to_properties() {
    local props_file="$OMA_BASE_DIR/config/oma.properties"
    if [ -f "$props_file" ]; then
        sed -i.bak "s/^LANGUAGE=.*/LANGUAGE=$LANGUAGE/" "$props_file"
    fi
}

# 메시지 로딩 함수
load_messages() {
    local msg_file="$OMA_BASE_DIR/config/messages_${LANGUAGE}.msg"
    if [ -f "$msg_file" ]; then
        source "$msg_file"
    else
        echo "Warning: Message file not found: $msg_file"
    fi
}

# 언어 변경 함수
change_language() {
    if [ "$LANGUAGE" = "ko" ]; then
        LANGUAGE="en"
    else
        LANGUAGE="ko"
    fi
    load_messages
    save_language_to_properties
    echo -e "${GREEN}${LANGUAGE_CHANGED}${NC}"
    sleep 1
    clear
}

# OMA_BASE_DIR 환경 변수 확인 및 설정
if [ -z "$OMA_BASE_DIR" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    export OMA_BASE_DIR="$SCRIPT_DIR"
    echo "${OMA_BASE_DIR_AUTO_SET}$OMA_BASE_DIR"
fi

# 언어 설정 로딩
load_language_from_properties
# 메시지 로딩
load_messages

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
        msg_error "${ENV_VAR_NOT_SET}"
        print_separator
        echo -e "${YELLOW}${ENV_SETUP_REQUIRED}${NC}"
        echo ""
        echo -e "${CYAN}${BOLD}${ENV_SETUP_METHODS}${NC}"
        echo -e "${CYAN}${ENV_SETUP_STEP1}${NC}"
        echo -e "${GREEN}   ./setEnv.sh${NC}"
        echo ""
        echo -e "${CYAN}${ENV_SETUP_STEP2}${NC}"
        echo -e "${GREEN}${SOURCE_ENV_EXAMPLE}${NC}"
        echo ""
        echo -e "${CYAN}${ENV_SETUP_STEP3}${NC}"
        echo -e "${GREEN}   ls -la oma_env_*.sh${NC}"
        print_separator

        # OMA_BASE_DIR에 환경 변수 파일이 있는지 확인
        cd "$OMA_BASE_DIR"
        env_files=(oma_env_*.sh)
        if [ -f "${env_files[0]}" ]; then
            echo -e "${BLUE}${BOLD}${FOUND_ENV_FILES}${NC}"
            for file in oma_env_*.sh; do
                if [ -f "$file" ]; then
                    echo -e "${GREEN}  - $file${NC}"
                fi
            done
            echo ""
            echo -e "${YELLOW}${SELECT_ENV_FILE}${NC}"
            echo -ne "${BLUE}${BOLD}${SELECT_FILE_PROMPT}${NC}"
            read select_env_file

            if [[ "$select_env_file" =~ ^[Yy]$ ]]; then
                echo -e "${CYAN}${SELECT_ENV_FILE_PROMPT}${NC}"
                select env_file in oma_env_*.sh "${CANCEL}"; do
                    case $env_file in
                        "${CANCEL}")
                            echo -e "${YELLOW}${ENV_SETUP_CANCELLED}${NC}"
                            exit 1
                            ;;
                        *.sh)
                            if [ -f "$env_file" ]; then
                                echo -e "${GREEN}${SELECTED_FILE}$env_file${NC}"
                                echo -e "${BLUE}${LOADING_ENV_VARS}${NC}"
                                source "$OMA_BASE_DIR/$env_file"
                                if [ -n "$APPLICATION_NAME" ]; then
                                    msg_success "${ENV_LOADED_SUCCESS}"
                                    echo -e "${GREEN}${CURRENT_PROJECT}$APPLICATION_NAME${NC}"
                                    cd "$OMA_BASE_DIR/bin"
                                    return 0
                                else
                                    msg_error "${ENV_LOADING_FAILED}"
                                    exit 1
                                fi
                            else
                                msg_error "${FILE_NOT_FOUND}$env_file"
                            fi
                            break
                            ;;
                        *)
                            echo -e "${RED}${INVALID_SELECTION}${NC}"
                            ;;
                    esac
                done
            else
                echo -e "${YELLOW}${SKIP_ENV_SETUP}${NC}"
                echo -e "${CYAN}${MANUAL_ENV_SETUP}${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}${NO_ENV_FILES_FOUND}${NC}"
            echo -e "${CYAN}${RUN_SETENV_FIRST}${NC}"
            echo ""
            echo -ne "${BLUE}${BOLD}${RUN_SETENV_NOW}${NC}"
            read run_setenv

            if [[ "$run_setenv" =~ ^[Yy]$ ]]; then
                echo -e "${GREEN}${RUNNING_SETENV}${NC}"
                print_separator
                cd "$OMA_BASE_DIR/bin"
                ./setEnv.sh
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}${SETENV_COMPLETED}${NC}"
                    echo -e "${YELLOW}${RESTART_INITOMA}${NC}"
                    echo -e "${CYAN}${OR_SOURCE_ENV_FILE}${NC}"
                    cd "$OMA_BASE_DIR"
                    for file in oma_env_*.sh; do
                        if [ -f "$file" ]; then
                            echo -e "${GREEN}  source $OMA_BASE_DIR/$file${NC}"
                            break
                        fi
                    done
                else
                    msg_error "${SETENV_FAILED}"
                fi
                exit 0
            else
                echo -e "${YELLOW}${SKIP_ENV_SETUP}${NC}"
                exit 1
            fi
        fi
    else
        print_separator
        echo -e "${GREEN}${BOLD}${SUCCESS_PREFIX}${ENV_CHECK_COMPLETE}${NC}"
        echo -e "${GREEN}${BOLD}${CURRENT_PROJECT}$APPLICATION_NAME${NC}"
    fi
}

# ====================================================
# Step별 스크립트 실행 함수들
# ====================================================

# 환경 설정 다시 수행
execute_setenv() {
    print_separator
    echo -e "${YELLOW}${ENV_SETUP_RETRY_MSG}${NC}"
    msg_running_script "setEnv.sh"
    cd "$OMA_BASE_DIR/bin"
    ./setEnv.sh
    if [ $? -eq 0 ]; then
        msg_success "환경 설정이 완료되었습니다."
        echo -e "${YELLOW}${ENV_VAR_SET_CONTINUE}${NC}"
    else
        msg_error "환경 설정에 실패했습니다."
        return 1
    fi
    print_separator
}

# 현재 환경 변수 확인
execute_checkenv() {
    print_separator
    msg_info "현재 환경 변수를 확인합니다."
    cd "$OMA_BASE_DIR/bin"
    ./checkEnv.sh
    print_separator
}

# DB Schema 변환
execute_db_schema() {
    print_separator
    msg_wait_3sec "DB Schema 변환"
    msg_script_exec "DB Schema 변환"

    if [ -f "$OMA_BASE_DIR/bin/processDbSchema.sh" ]; then
        msg_running_script "processDbSchema.sh"
        cd "$OMA_BASE_DIR/bin"
        ./processDbSchema.sh
        if [ $? -eq 0 ]; then
            msg_task_completed "DB Schema 변환이"
        else
            msg_task_failed "DB Schema 변환"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/processDbSchema.sh"
        return 1
    fi
    print_separator
}

# 애플리케이션 분석
execute_app_analysis() {
    print_separator
    msg_wait_3sec "애플리케이션 분석"
    msg_script_exec "애플리케이션 분석"

    if [ -f "$OMA_BASE_DIR/bin/processAppAnalysis.sh" ]; then
        msg_running_script "processAppAnalysis.sh"
        cd "$OMA_BASE_DIR/bin"
        ./processAppAnalysis.sh
        if [ $? -eq 0 ]; then
            msg_task_completed "애플리케이션 분석이"
        else
            msg_task_failed "애플리케이션 분석"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/processAppAnalysis.sh"
        return 1
    fi
    print_separator
}

# 분석 보고서 작성
execute_app_reporting() {
    print_separator
    msg_wait_3sec "분석 보고서 작성"
    msg_script_exec "분석 보고서 작성"

    if [ -f "$OMA_BASE_DIR/bin/processAppReporting.sh" ]; then
        msg_running_script "processAppReporting.sh"
        cd "$OMA_BASE_DIR/bin"
        ./processAppReporting.sh
        if [ $? -eq 0 ]; then
            msg_task_completed "분석 보고서 작성이"
        else
            msg_task_failed "분석 보고서 작성"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/processAppReporting.sh"
        return 1
    fi
    print_separator
}

# SQL 샘플 변환
execute_sql_sample_transform() {
    print_separator
    msg_wait_3sec "SQL 샘플 변환 작업"
    echo ""
    echo -e "${BLUE}${BOLD}${SAMPLE_TRANSFORM_DESC}${NC}"
    sleep 3
    msg_script_exec "SQL 샘플 변환"

    if [ -f "$APP_TOOLS_FOLDER/sqlTransformTarget.py" ]; then
        msg_info "sqlTransformTarget.py를 샘플 모드로 실행합니다..."
        echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py --file $APP_TRANSFORM_FOLDER/SampleTransformTarget.csv${NC}"
        cd "$OMA_BASE_DIR/bin"
        python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --file "$APP_TRANSFORM_FOLDER/SampleTransformTarget.csv"
        if [ $? -eq 0 ]; then
            msg_task_completed "SQL 샘플 변환 작업이"
        else
            msg_task_failed "SQL 샘플 변환 작업"
        fi
    else
        msg_file_not_found "$APP_TOOLS_FOLDER/sqlTransformTarget.py"
        return 1
    fi
    print_separator
}

# SQL 전체 변환
execute_sql_full_transform() {
    print_separator
    msg_wait_3sec "SQL 전체 변환 작업"
    echo ""
    echo -e "${BLUE}${BOLD}${FULL_TRANSFORM_DESC}${NC}"
    sleep 3
    msg_script_exec "SQL 전체 변환"

    if [ -f "$APP_TOOLS_FOLDER/sqlTransformTarget.py" ]; then
        msg_info "sqlTransformTarget.py를 전체 모드로 실행합니다..."
        echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/sqlTransformTarget.py${NC}"
        cd "$OMA_BASE_DIR/bin"
        python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py"
        if [ $? -eq 0 ]; then
            msg_task_completed "SQL 전체 변환 작업이"
        else
            msg_task_failed "SQL 전체 변환 작업"
        fi
    else
        msg_file_not_found "$APP_TOOLS_FOLDER/sqlTransformTarget.py"
        return 1
    fi
    print_separator
}

# XML List 생성
execute_xml_list_generation() {
    print_separator
    msg_wait_3sec "바인드 변수 생성"
    msg_script_exec "바인드 변수 생성"

    if [ -f "$OMA_BASE_DIR/bin/test/run_bind_generator.sh" ]; then
        msg_running_script "run_bind_generator.sh"
        echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_bind_generator.sh${NC}"
        "$OMA_BASE_DIR/bin/test/run_bind_generator.sh"
        if [ $? -eq 0 ]; then
            msg_task_completed "바인드 변수 생성이"
        else
            msg_task_failed "바인드 변수 생성"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/test/run_bind_generator.sh"
        return 1
    fi
    print_separator
}

# SQL Unit Test
execute_sql_unittest() {
    print_separator
    msg_wait_3sec "애플리케이션 SQL Unit Test"
    msg_script_exec "SQL Unit Test"

    # Oracle 테스트 실행
    if [ -f "$OMA_BASE_DIR/bin/test/run_oracle.sh" ]; then
        msg_info "${ORACLE_TEST_RUNNING}"
        echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_oracle.sh $SOURCE_SQL_MAPPER_FOLDER/mapper${NC}"
        cd "$OMA_BASE_DIR/bin/test"
        ./run_oracle.sh "$SOURCE_SQL_MAPPER_FOLDER/mapper"
        if [ $? -eq 0 ]; then
            msg_success "${ORACLE_TEST_COMPLETED}"
        else
            msg_error "${ORACLE_TEST_FAILED}"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/test/run_oracle.sh"
        return 1
    fi

    # Target DBMS 테스트 실행
    if [ "$TARGET_DBMS_TYPE" = "postgres" ]; then
        if [ -f "$OMA_BASE_DIR/bin/test/run_postgresql.sh" ]; then
            msg_info "${POSTGRESQL_TEST_RUNNING}"
            echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_postgresql.sh $TARGET_SQL_MAPPER_FOLDER/mapper${NC}"
            cd "$OMA_BASE_DIR/bin/test"
            ./run_postgresql.sh "$TARGET_SQL_MAPPER_FOLDER/mapper"
            if [ $? -eq 0 ]; then
                msg_success "${POSTGRESQL_TEST_COMPLETED}"
            else
                msg_error "${POSTGRESQL_TEST_FAILED}"
            fi
        else
            msg_file_not_found "$OMA_BASE_DIR/bin/test/run_postgresql.sh"
            return 1
        fi
    elif [ "$TARGET_DBMS_TYPE" = "mysql" ]; then
        if [ -f "$OMA_BASE_DIR/bin/test/run_mysql.sh" ]; then
            msg_info "${MYSQL_TEST_RUNNING}"
            echo -e "${BLUE}${BOLD}$OMA_BASE_DIR/bin/test/run_mysql.sh $TARGET_SQL_MAPPER_FOLDER/mapper${NC}"
            cd "$OMA_BASE_DIR/bin/test"
            ./run_mysql.sh "$TARGET_SQL_MAPPER_FOLDER/mapper"
            if [ $? -eq 0 ]; then
                msg_success "${MYSQL_TEST_COMPLETED}"
            else
                msg_error "${MYSQL_TEST_FAILED}"
            fi
        else
            msg_file_not_found "$OMA_BASE_DIR/bin/test/run_mysql.sh"
            return 1
        fi
    else
        msg_error "${UNSUPPORTED_TARGET_DBMS}$TARGET_DBMS_TYPE"
        return 1
    fi

    print_separator
}

# 샘플 테스트 및 결과 수정
execute_sample_test_fix() {
    print_separator
    msg_wait_3sec "샘플 테스트 및 결과 수정"
    echo -e "${BLUE}${BOLD}${SAMPLE_TEST_FIX_PERFORMING}${NC}"

    if [ -f "$APP_TOOLS_FOLDER/../postTransform/editErrors.md" ]; then
        msg_info "editErrors.md를 사용하여 Amazon Q chat을 실행합니다..."
        echo -e "${BLUE}${BOLD}q chat --trust-all-tools \"$APP_TOOLS_FOLDER/../postTransform/editErrors.md\"${NC}"
        q chat --trust-all-tools "$APP_TOOLS_FOLDER/../postTransform/editErrors.md"
        if [ $? -eq 0 ]; then
            msg_task_completed "샘플 테스트 및 결과 수정이"
        else
            msg_task_failed "샘플 테스트 및 결과 수정"
        fi
    else
        msg_file_not_found "$APP_TOOLS_FOLDER/../postTransform/editErrors.md"
        return 1
    fi

    print_separator
}

# SQL 변환 Merge
execute_sql_transform_merge() {
    print_separator
    msg_wait_3sec "SQL 변환 Merge 작업"
    echo ""
    echo -e "${BLUE}${BOLD}${MERGE_PROCESSING}${NC}"
    sleep 3

    # Merge 작업 전에 delete_target_xml_files.sh 실행
    if [ -f "$APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh" ]; then
        msg_info "${DELETE_TARGET_XML_RUNNING}"
        echo -e "${BLUE}${BOLD}$APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh${NC}"
        "$APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh"
        if [ $? -eq 0 ]; then
            msg_success "${DELETE_TARGET_XML_COMPLETED}"
        else
            msg_error "${DELETE_TARGET_XML_FAILED}"
            echo -e "${YELLOW}${CONTINUE_PROCESSING}${NC}"
        fi
    else
        msg_warning "$APP_TOOLS_FOLDER/../postTransform/delete_target_xml_files.sh 파일을 찾을 수 없습니다."
        echo -e "${YELLOW}${MERGE_CONTINUE}${NC}"
    fi
    msg_script_exec "SQL 변환 Merge"

    if [ -f "$OMA_BASE_DIR/bin/processSqlTransform.sh" ]; then
        msg_info "processSqlTransform.sh merge 옵션으로 실행합니다..."
        cd "$OMA_BASE_DIR/bin"
        ./processSqlTransform.sh merge
        if [ $? -eq 0 ]; then
            msg_task_completed "SQL 변환 Merge 작업이"
        else
            msg_task_failed "SQL 변환 Merge 작업"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/processSqlTransform.sh"
        return 1
    fi
    print_separator
}

# 변환 작업 보고서
execute_transform_report() {
    print_separator
    msg_wait_3sec "변환 작업 보고서"
    msg_script_exec "변환 작업 보고서"

    if [ -f "$OMA_BASE_DIR/bin/processSqlTransformReport.sh" ]; then
        msg_running_script "processSqlTransformReport.sh"
        cd "$OMA_BASE_DIR/bin"
        ./processSqlTransformReport.sh
        if [ $? -eq 0 ]; then
            msg_task_completed "변환 작업 보고서가"
        else
            msg_task_failed "변환 작업 보고서"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/processSqlTransformReport.sh"
        return 1
    fi
    print_separator
}

# PostgreSQL 메타데이터 작성
execute_postgresql_meta() {
    print_separator
    msg_wait_3sec "PostgreSQL 데이터베이스 메타데이터 작성"
    msg_script_exec "PostgreSQL 메타데이터 작성"

    if [ -f "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh" ]; then
        msg_running_script "genPostgreSqlMeta.sh"
        echo -e "${BLUE}${BOLD}$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh${NC}"
        "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh"
        if [ $? -eq 0 ]; then
            msg_task_completed "PostgreSQL 메타데이터 작성이"
        else
            msg_task_failed "PostgreSQL 메타데이터 작성"
        fi
    else
        msg_error "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh 파일을 찾을 수 없습니다."
        echo -e "${YELLOW}${AI_ALTERNATIVE}${NC}"
        if [ -f "$APP_TOOLS_FOLDER/genPostgreSqlMeta.md" ]; then
            msg_info "genPostgreSQLMeta.md를 사용하여 Amazon Q chat을 실행합니다..."
            echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/genPostgreSqlMeta.md${NC}"
            q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/genPostgreSqlMeta.md"
            if [ $? -eq 0 ]; then
                msg_task_completed "PostgreSQL 메타데이터 작성이"
            else
                msg_task_failed "PostgreSQL 메타데이터 작성"
            fi
        else
            msg_file_not_found "$APP_TOOLS_FOLDER/genPostgreSqlMeta.md"
            return 1
        fi
    fi
    print_separator
}

# Java Source 변환
execute_java_transform() {
    print_separator
    msg_wait_3sec "애플리케이션 Java Source 변환 작업"
    echo -e "${BLUE}${BOLD}${JAVA_TRANSFORM_PERFORMING}${NC}"
    echo ""
    echo -e "${RED}${BOLD}${TARGET_JAVA_FOLDER_REQUIRED}${NC}"
    echo -e "${YELLOW}${BOLD}${JAVA_TRANSFORM_NOTICE}${NC}"
    echo -e "${CYAN}${BOLD}${JAVA_TRANSFORM_EXAMPLE}${NC}"
    echo ""

    if [ -f "$OMA_BASE_DIR/bin/postTransform/convertOracleJava.md" ]; then
        msg_info "convertOracleJava.md를 사용하여 Amazon Q chat을 실행합니다..."
        echo -e "${BLUE}${BOLD}q chat --trust-all-tools \"$OMA_BASE_DIR/bin/postTransform/convertOracleJava.md\"${NC}"
        q chat --trust-all-tools "$OMA_BASE_DIR/bin/postTransform/convertOracleJava.md"
        if [ $? -eq 0 ]; then
            msg_task_completed "Java Source 변환 작업이"
        else
            msg_task_failed "Java Source 변환 작업"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/postTransform/convertOracleJava.md"
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
        echo -e "${BLUE}${BOLD}0. ${ENV_MENU}${NC}"
        print_separator
        echo -e "${CYAN}1. ${ENV_SETUP_RETRY}${NC}"
        echo -e "${CYAN}2. ${ENV_VAR_CHECK}${NC}"
        echo -e "${YELLOW}b. ${BACK_TO_MAIN}${NC}"
        echo -e "${YELLOW}q. ${QUIT}${NC}"
        print_separator
        echo -ne "${CYAN}${SELECT_OPTION} (1,2,b,q): ${NC}"
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
                echo -e "${GREEN}${PROGRAM_EXIT}${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}${INVALID_SELECTION}${NC}"
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
        echo -e "${BLUE}${BOLD}2. ${APP_ANALYSIS_MENU}${NC}"
        print_separator
        echo -e "${CYAN}1. ${APP_ANALYSIS}${NC}${YELLOW} : ${APP_ANALYSIS_DESC}${NC}"
        echo ""
        echo -e "${CYAN}2. ${APP_REPORTING_SQL_EXTRACT}${NC}${YELLOW} : ${APP_REPORTING_DESC}${NC}"
        echo ""
        echo -e "${CYAN}3. ${POSTGRESQL_ONLY_META}${NC}${YELLOW} : ${POSTGRESQL_META_DESC}${NC}"
        echo ""
        echo -e "${YELLOW}b. ${BACK_TO_MAIN}${NC}"
        echo -e "${YELLOW}q. ${QUIT}${NC}"
        print_separator
        echo -ne "${CYAN}${SELECT_OPTION} (1,2,3,b,q): ${NC}"
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
                echo -e "${GREEN}${PROGRAM_EXIT}${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}${INVALID_SELECTION}${NC}"
                sleep 2
                clear
                ;;
        esac
    done
}

# Compare XMLs 실행
execute_compare_xmls() {
    print_separator
    echo -e "${BLUE}${BOLD}${XML_COMPARE_TOOL_RUNNING}${NC}"

    if [ -f "$APP_TOOLS_FOLDER/compareXMLs.sh" ]; then
        msg_running_script "compareXMLs.sh"
        "$APP_TOOLS_FOLDER/compareXMLs.sh"
        if [ $? -eq 0 ]; then
            msg_task_completed "XML 파일 비교가"
        else
            msg_task_failed "XML 파일 비교"
        fi
    else
        msg_file_not_found "$APP_TOOLS_FOLDER/compareXMLs.sh"
        return 1
    fi
    print_separator
}

# Parameter 구성 실행
execute_parameter_config() {
    print_separator
    msg_wait_3sec "Parameter 구성"
    msg_script_exec "Parameter 구성"

    if [ -f "$APP_TOOLS_FOLDER/../test/bulk_prepare.sh" ]; then
        msg_running_script "bulk_prepare.sh"
        echo -e "${BLUE}${BOLD}$APP_TOOLS_FOLDER/../test/bulk_prepare.sh $SOURCE_SQL_MAPPER_FOLDER${NC}"
        (cd "$APP_TOOLS_FOLDER/../test" && ./bulk_prepare.sh "$SOURCE_SQL_MAPPER_FOLDER")
        if [ $? -eq 0 ]; then
            msg_task_completed "Parameter 구성이"
        else
            msg_task_failed "Parameter 구성"
        fi
    else
        msg_file_not_found "$APP_TOOLS_FOLDER/../test/bulk_prepare.sh"
        return 1
    fi
    print_separator
}

# 애플리케이션 변환 메뉴
show_application_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}3. ${APP_TRANSFORM_MENU}${NC}"
        print_separator
        echo -e "${RED}${BOLD}${IMPORTANT_NOTICE}${NC}"
        echo -e "${YELLOW}${SAMPLE_TRANSFORM_NOTICE}${NC}"
        echo -e "${YELLOW}${TRANSFORM_PROMPT_ADJUST}${NC}"
        print_separator
        echo -e "${CYAN}1. ${SAMPLE_TRANSFORM}${NC}"
        echo -e "${CYAN}2. ${FULL_SQL_TRANSFORM}${NC}"
        echo ""
        echo -e "${CYAN}3. ${COMPARE_XMLS}${NC}${YELLOW} : ${COMPARE_XMLS_DESC}${NC}"
        echo -e "${CYAN}4. ${TRANSFORM_TEST_FIX}${NC}${YELLOW} : ${TRANSFORM_TEST_FIX_DESC}${NC}"
        echo ""
        echo -e "${CYAN}5. ${XML_MERGE}${NC}"
        echo ""
        echo -e "${YELLOW}b. ${BACK_TO_MAIN}${NC}"
        echo -e "${YELLOW}q. ${QUIT}${NC}"
        print_separator
        echo -ne "${CYAN}${SELECT_OPTION} (1,2,3,4,5,b,q): ${NC}"
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
                echo -e "${GREEN}${PROGRAM_EXIT}${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}${INVALID_SELECTION}${NC}"
                sleep 2
                clear
                ;;
        esac
    done
}

# SQL 결과 불일치 수정
execute_sql_result_fix() {
    print_separator
    msg_wait_3sec "SQL 결과 불일치 수정"
    msg_script_exec "SQL 결과 불일치 수정"

    if [ -f "$OMA_BASE_DIR/bin/test/analyze_results.sh" ]; then
        msg_running_script "analyze_results.sh"
        echo -e "${BLUE}${BOLD}cd $OMA_BASE_DIR/bin/test && ./analyze_results.sh${NC}"
        cd "$OMA_BASE_DIR/bin/test"
        ./analyze_results.sh
        if [ $? -eq 0 ]; then
            msg_task_completed "SQL 결과 불일치 수정이"
        else
            msg_task_failed "SQL 결과 불일치 수정"
        fi
    else
        msg_file_not_found "$OMA_BASE_DIR/bin/test/analyze_results.sh"
        return 1
    fi
    print_separator
}

# SQL 데이터 테스트 수행 메뉴
show_test_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}4. ${SQL_TEST_MENU}${NC}"
        print_separator
        echo -e "${CYAN}1. ${BIND_VAR_GEN}${NC}${YELLOW} : ${BIND_VAR_GEN_DESC}${NC}"
        echo -e "${CYAN}2. ${SQL_UNIT_TEST}${NC}${YELLOW} : ${SQL_UNIT_TEST_DESC}${NC}"
        echo -e "${CYAN}3. ${SQL_RESULT_FIX}${NC}${YELLOW} : ${SQL_RESULT_FIX_DESC}${NC}"
        echo -e "${YELLOW}b. ${BACK_TO_MAIN}${NC}"
        echo -e "${YELLOW}q. ${QUIT}${NC}"
        print_separator
        echo -ne "${CYAN}${SELECT_OPTION} (1,2,3,b,q): ${NC}"
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
                echo -e "${GREEN}${PROGRAM_EXIT}${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}${INVALID_SELECTION}${NC}"
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
echo -e "${BLUE}${BOLD}${OMA_INTRO}${NC}"
echo -e "${GREEN}${CURRENT_PROJECT}${APPLICATION_NAME}${NC}"
echo -e "${RED}${BOLD}${IMPORTANT_NOTICE}${NC}"
echo -e "${YELLOW}${DB_CONNECTION_REQUIRED}${NC}"
echo -e "${YELLOW}${DB_TASKS_EXAMPLES}${NC}"
echo -e "${CYAN}${BOLD}${AWS_ENV_SETUP_REQUIRED}${NC}"

while true; do
    print_separator
    echo -e "${BLUE}${BOLD}${MAIN_MENU}${NC}"
    print_separator
    echo -e "${MAGENTA}l. ${LANGUAGE_CHANGE}${NC}"
    echo -e "${YELLOW}0. ${ENV_SETUP_CHECK}${NC}"
    echo -e "${CYAN}1. ${DBMS_ADDITIONAL_TRANSFORM}${NC}"
    echo -e "${CYAN}2. ${APP_ANALYSIS}${NC}"
    echo -e "${CYAN}3. ${APP_TRANSFORM}${NC}"
    echo -e "${CYAN}4. ${SQL_DATA_TEST}${NC}"
    echo -e "${CYAN}5. ${TRANSFORM_REPORT}${NC}"
    echo -e "${YELLOW}q. ${QUIT}${NC}"
    print_separator
    echo -ne "${CYAN}${SELECT_MENU}${NC}"
    read choice

    case $choice in
        l|L)
            clear
            change_language
            ;;
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
        q|Q)
            clear
            print_separator
            echo -e "${GREEN}${PROGRAM_EXIT}${NC}"
            print_separator
            exit 0
            ;;
        *)
            echo -e "${RED}${INVALID_SELECTION}${NC}"
            sleep 2
            clear
            ;;
    esac
done

echo -e "${GREEN}${ALL_SETUP_COMPLETED}${NC}"