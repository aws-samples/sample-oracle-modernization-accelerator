#!/bin/bash

# OMA_BASE_DIR 환경 변수 확인 및 설정
if [ -z "$OMA_BASE_DIR" ]; then
    # 현재 스크립트의 디렉토리를 기준으로 OMA_BASE_DIR 설정
    # initOMA.sh가 OMA_BASE_DIR에 있다고 가정
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    export OMA_BASE_DIR="$SCRIPT_DIR"
    echo "OMA_BASE_DIR이 설정되지 않아 자동으로 설정합니다: $OMA_BASE_DIR"
fi

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
        echo -e "${RED}${BOLD}오류: 환경 변수가 설정되지 않았습니다.${NC}"
        print_separator
        echo -e "${YELLOW}OMA 변환 작업을 수행하려면 먼저 환경 설정이 필요합니다.${NC}"
        echo ""
        echo -e "${CYAN}${BOLD}환경 설정 방법:${NC}"
        echo -e "${CYAN}1. 프로젝트 초기 설정 및 환경 변수 파일 생성:${NC}"
        echo -e "${GREEN}   ./setEnv.sh${NC}"
        echo ""
        echo -e "${CYAN}2. 환경 변수 파일이 이미 있는 경우 (예: oma_env_MyProject.sh):${NC}"
        echo -e "${GREEN}   source ./oma_env_프로젝트명.sh${NC}"
        echo ""
        echo -e "${CYAN}3. 현재 디렉토리의 환경 변수 파일 확인:${NC}"
        echo -e "${GREEN}   ls -la oma_env_*.sh${NC}"
        print_separator
        
        # OMA_BASE_DIR에 환경 변수 파일이 있는지 확인
        cd "$OMA_BASE_DIR"
        env_files=(oma_env_*.sh)
        if [ -f "${env_files[0]}" ]; then
            echo -e "${BLUE}${BOLD}발견된 환경 변수 파일들:${NC}"
            for file in oma_env_*.sh; do
                if [ -f "$file" ]; then
                    echo -e "${GREEN}  - $file${NC}"
                fi
            done
            echo ""
            echo -e "${YELLOW}위 파일 중 하나를 선택하여 source 하시겠습니까?${NC}"
            echo -ne "${BLUE}${BOLD}파일을 선택하시겠습니까? (y/N): ${NC}"
            read select_env_file
            
            if [[ "$select_env_file" =~ ^[Yy]$ ]]; then
                echo -e "${CYAN}사용할 환경 변수 파일을 선택하세요:${NC}"
                select env_file in oma_env_*.sh "취소"; do
                    case $env_file in
                        "취소")
                            echo -e "${YELLOW}환경 설정을 취소합니다.${NC}"
                            exit 1
                            ;;
                        *.sh)
                            if [ -f "$env_file" ]; then
                                echo -e "${GREEN}선택된 파일: $env_file${NC}"
                                echo -e "${BLUE}환경 변수를 로딩합니다...${NC}"
                                source "$OMA_BASE_DIR/$env_file"
                                if [ -n "$APPLICATION_NAME" ]; then
                                    echo -e "${GREEN}✓ 환경 변수가 성공적으로 로딩되었습니다.${NC}"
                                    echo -e "${GREEN}현재 프로젝트: $APPLICATION_NAME${NC}"
                                    cd "$OMA_BASE_DIR/bin"
                                    return 0
                                else
                                    echo -e "${RED}환경 변수 로딩에 실패했습니다.${NC}"
                                    exit 1
                                fi
                            else
                                echo -e "${RED}파일을 찾을 수 없습니다: $env_file${NC}"
                            fi
                            break
                            ;;
                        *)
                            echo -e "${RED}잘못된 선택입니다. 다시 선택하세요.${NC}"
                            ;;
                    esac
                done
            else
                echo -e "${YELLOW}환경 설정을 건너뜁니다.${NC}"
                echo -e "${CYAN}수동으로 환경을 설정한 후 다시 실행하세요.${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}환경 변수 파일이 발견되지 않았습니다.${NC}"
            echo -e "${CYAN}setEnv.sh를 먼저 실행하여 프로젝트를 설정하세요.${NC}"
            echo ""
            echo -ne "${BLUE}${BOLD}지금 setEnv.sh를 실행하시겠습니까? (y/N): ${NC}"
            read run_setenv
            
            if [[ "$run_setenv" =~ ^[Yy]$ ]]; then
                echo -e "${GREEN}setEnv.sh를 실행합니다...${NC}"
                print_separator
                cd "$OMA_BASE_DIR/bin"
                ./setEnv.sh
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}setEnv.sh 실행이 완료되었습니다.${NC}"
                    echo -e "${YELLOW}환경 변수를 로딩하기 위해 initOMA.sh를 다시 실행하세요.${NC}"
                    echo -e "${CYAN}또는 생성된 환경 변수 파일을 source 하세요:${NC}"
                    cd "$OMA_BASE_DIR"
                    for file in oma_env_*.sh; do
                        if [ -f "$file" ]; then
                            echo -e "${GREEN}  source $OMA_BASE_DIR/$file${NC}"
                            break
                        fi
                    done
                else
                    echo -e "${RED}setEnv.sh 실행에 실패했습니다.${NC}"
                fi
                exit 0
            else
                echo -e "${YELLOW}환경 설정을 건너뜁니다.${NC}"
                exit 1
            fi
        fi
    else
        print_separator
        echo -e "${GREEN}${BOLD}✅ 환경 변수 확인 완료!${NC}"
        echo -e "${GREEN}${BOLD}현재 프로젝트: $APPLICATION_NAME${NC}"
    fi
}

# ====================================================
# Step별 스크립트 실행 함수들
# ====================================================

# 환경 설정 다시 수행
execute_setenv() {
    print_separator
    echo -e "${YELLOW}환경 설정을 다시 수행합니다.${NC}"
    echo -e "${CYAN}setEnv.sh를 실행합니다...${NC}"
    cd "$OMA_BASE_DIR/bin"
    ./setEnv.sh
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}환경 설정이 완료되었습니다.${NC}"
        echo -e "${YELLOW}환경 변수가 설정되었으므로 계속 진행할 수 있습니다.${NC}"
    else
        echo -e "${RED}환경 설정에 실패했습니다.${NC}"
        return 1
    fi
    print_separator
}

# 현재 환경 변수 확인
execute_checkenv() {
    print_separator
    echo -e "${CYAN}현재 환경 변수를 확인합니다.${NC}"
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
    echo -e "${BLUE}${BOLD}XML List 생성을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}XML List 생성 스크립트 실행${NC}"
    
    if [ -f "$APP_TOOLS_FOLDER/../postTransform/genUnitTestList.sh" ]; then
        echo -e "${CYAN}genUnitTestList.sh를 실행합니다...${NC}"
        echo -e "${BLUE}${BOLD}$APP_TOOLS_FOLDER/../postTransform/genUnitTestList.sh${NC}"
        "$APP_TOOLS_FOLDER/../postTransform/genUnitTestList.sh"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}XML List 생성이 완료되었습니다.${NC}"
        else
            echo -e "${RED}XML List 생성 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $APP_TOOLS_FOLDER/../postTransform/genUnitTestList.sh 파일을 찾을 수 없습니다.${NC}"
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
    
    if [ -f "$OMA_BASE_DIR/bin/processSqlTest.sh" ]; then
        echo -e "${CYAN}processSqlTest.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processSqlTest.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}애플리케이션 SQL Unit Test가 완료되었습니다.${NC}"
        else
            echo -e "${RED}애플리케이션 SQL Unit Test 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processSqlTest.sh 파일을 찾을 수 없습니다.${NC}"
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
        echo -e "${BLUE}${BOLD}0. 환경 메뉴${NC}"
        print_separator
        echo -e "${CYAN}1. 환경 설정 다시 수행 (setEnv.sh)${NC}"
        echo -e "${CYAN}2. 현재 환경 변수 확인 (checkEnv.sh)${NC}"
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        echo -e "${YELLOW}q. 종료${NC}"
        print_separator
        echo -ne "${CYAN}선택하세요 (1,2,b,q): ${NC}"
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
        echo -e "${BLUE}${BOLD}1. 애플리케이션 분석 메뉴${NC}"
        print_separator
        echo -e "${CYAN}1. 애플리케이션 분석${NC}${YELLOW} : Java 소스 코드 및 MyBatis Mapper 파일 분석${NC}"
        echo ""
        echo -e "${CYAN}2. 분석 보고서 작성 및 SQL변환 대상 추출${NC}${YELLOW} : HTML 리포트 생성 및 SQL 변환 대상 목록 추출${NC}"
        echo ""
        echo -e "${CYAN}3. (PostgreSQL Only) 데이터베이스 메타데이터 작성${NC}${YELLOW} : PostgreSQL 데이터베이스 메타데이터 생성 (Amazon Q Chat 사용)${NC}"
        echo ""
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        echo -e "${YELLOW}q. 종료${NC}"
        print_separator
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
        echo -e "${BLUE}${BOLD}1. 애플리케이션 분석 메뉴${NC}"
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

# 애플리케이션 변환 메뉴
show_application_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}2. 애플리케이션 변환 메뉴${NC}"
        print_separator
        echo -e "${RED}${BOLD}⚠️  중요 안내${NC}"
        echo -e "${YELLOW}Sample 변환을 수행한 이후에, 테스트 및 결과 수정을 먼저 수행해야 합니다.${NC}"
        echo -e "${YELLOW}이를 통해서 변환 프롬프트를 프로젝트 특성에 맞게 조정해야 합니다.${NC}"
        print_separator
        echo -e "${CYAN}1. 샘플 변환${NC}"
        echo -e "${CYAN}2. 애플리케이션 SQL 전체 변환 작업${NC}"
        echo ""
        echo -e "${CYAN}3. Compare XMLs${NC}${YELLOW} : 원본과 변환된 XML 파일 비교${NC}"
        echo -e "${CYAN}4. 변환 테스트 및 결과 수정${NC}"
        echo ""
        echo -e "${CYAN}5. XML Merge 작업 - SQLID to XML${NC}"
        echo ""
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        echo -e "${YELLOW}q. 종료${NC}"
        print_separator
        echo -ne "${CYAN}선택하세요 (1,2,3,4,5,b,q): ${NC}"
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

# SQL 테스트 수행 메뉴
show_test_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}3. SQL 테스트 수행 메뉴${NC}"
        print_separator
        echo -e "${CYAN}1. XML List 생성${NC}${YELLOW} : Unit Test용 XML 목록 생성${NC}"
        echo -e "${CYAN}2. 애플리케이션 SQL Unit Test${NC}${YELLOW} : 변환된 SQL 테스트 및 결과 분석 (DB 연결 필요)${NC}"
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        echo -e "${YELLOW}q. 종료${NC}"
        print_separator
        echo -ne "${CYAN}선택하세요 (1,2,b,q): ${NC}"
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
echo -e "${GREEN}현재 설정된 프로젝트: $APPLICATION_NAME${NC}"
echo -e "${RED}${BOLD}⚠️  중요 안내${NC}"
echo -e "${YELLOW}OMA 변환 작업 수행 중 데이터베이스 연관된 작업은 Source 시스템과 연결이 되는 AWS 환경 구성을 사전에 요구합니다.${NC}"
echo -e "${YELLOW}(DB Schema 변환, SQL Unit Test 등)${NC}"
echo -e "${CYAN}${BOLD}사전 환경 구성이 필요한 경우 AWS 환경 설정을 먼저 수행하세요.${NC}"

while true; do
    print_separator
    echo -e "${BLUE}${BOLD}OMA 메인 메뉴${NC}"
    print_separator
    echo -e "${YELLOW}0. 환경 설정 및 확인${NC}"
    echo -e "${CYAN}1. 애플리케이션 분석${NC}"
    echo -e "${CYAN}2. 애플리케이션 변환${NC}"
    echo -e "${CYAN}3. SQL 테스트 수행${NC}"
    echo -e "${CYAN}4. 변환 작업 보고서${NC}"
    echo -e "${YELLOW}q. 종료${NC}"
    print_separator
    echo -ne "${CYAN}메뉴를 선택하세요 (0,1,2,3,4,q): ${NC}"
    read choice

    case $choice in
        0)
            clear
            show_environment_menu
            ;;
        1)
            clear
            show_analysis_menu
            ;;
        2)
            clear
            show_application_menu
            ;;
        3)
            clear
            show_test_menu
            ;;
        4)
            clear
            show_completion_menu
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

echo -e "${GREEN}모든 설정이 완료되었습니다.${NC}"

