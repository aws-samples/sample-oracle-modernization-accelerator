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

print_separator
echo -e "${BLUE}${BOLD}OMA 프로젝트 디렉토리 구조${NC}"
print_separator
echo -e "${CYAN}sample-oracle-modernization-accelerator          OMA 루트 폴더${NC}"
echo -e "${CYAN}├── initOMA.sh                                   메인 실행 스크립트 (통합 진입점)${NC}"
echo -e "${CYAN}├── oma_env_[프로젝트명].sh                        프로젝트별 환경 변수 파일${NC}"
echo -e "${CYAN}├── config/                                      프로젝트 설정 파일 디렉토리${NC}"
echo -e "${CYAN}│   └── oma.properties                           - 환경 변수로 사용되는 설정 파일${NC}"
echo -e "${CYAN}├── [프로젝트명]/                                  분석 및 변환 단위 : 애플리케이션명으로 구분${NC}"
echo -e "${CYAN}│   ├── database/                                 - 데이터베이스 스키마 변환 결과${NC}"
echo -e "${CYAN}│   ├── logs/                                    - 전체 프로세스 로그 디렉토리${NC}"
echo -e "${CYAN}│   ├── application/                             - 애플리케이션 분석 및 변환 결과${NC}"
echo -e "${CYAN}│   │   ├── *.csv                                - JNDI, Mapper 분석 결과 파일들${NC}"
echo -e "${CYAN}│   │   ├── Discovery-Report.html                - 애플리케이션 분석 리포트${NC}"
echo -e "${CYAN}│   │   └── transform/                           - SQL 변환 결과 및 로그${NC}"
echo -e "${CYAN}│   └── test/                                    - Unit 테스트 수행 결과 및 도구${NC}"
echo -e "${CYAN}└── bin/                                         OMA 실행 스크립트 및 템플릿${NC}"
echo -e "${CYAN}    ├── *.sh                                     - 각종 실행 스크립트들${NC}"
echo -e "${CYAN}    ├── database/                                - 데이터베이스 변환 템플릿${NC}"
echo -e "${CYAN}    ├── application/                             - 애플리케이션 변환 템플릿${NC}"
echo -e "${CYAN}    └── test/                                    - 테스트 템플릿${NC}"

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
    
    if [ -f "$OMA_BASE_DIR/bin/processDBSchema.sh" ]; then
        echo -e "${CYAN}processDBSchema.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processDBSchema.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}DB Schema 변환이 완료되었습니다.${NC}"
        else
            echo -e "${RED}DB Schema 변환 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processDBSchema.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# 애플리케이션 Discovery
execute_app_discovery() {
    print_separator
    echo -e "${BLUE}${BOLD}애플리케이션 Discovery를 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}애플리케이션 Discovery 스크립트 실행${NC}"
    
    if [ -f "$OMA_BASE_DIR/bin/processappDiscovery.sh" ]; then
        echo -e "${CYAN}processappDiscovery.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processappDiscovery.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}애플리케이션 Discovery가 완료되었습니다.${NC}"
        else
            echo -e "${RED}애플리케이션 Discovery 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processappDiscovery.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# SQL 변환
execute_sql_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}SQL 변환 작업을 시작하기 전 3초 대기합니다...${NC}"
    echo ""
    echo -e "${BLUE}${BOLD}변환 실패 항목 리스트 (Assessment/SQLTransformFailure.csv)를 새로 생성한 이후에 실행 됩니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}SQL 변환 스크립트 실행${NC}"
    
    if [ -f "$OMA_BASE_DIR/bin/processSQLTransform.sh" ]; then
        echo -e "${CYAN}processSQLTransform.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processSQLTransform.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}SQL 변환 작업이 완료되었습니다.${NC}"
        else
            echo -e "${RED}SQL 변환 작업 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processSQLTransform.sh 파일을 찾을 수 없습니다.${NC}"
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
    
    if [ -f "$OMA_BASE_DIR/bin/processSQLTest.sh" ]; then
        echo -e "${CYAN}processSQLTest.sh를 실행합니다...${NC}"
        cd "$OMA_BASE_DIR/bin"
        ./processSQLTest.sh
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}애플리케이션 SQL Unit Test가 완료되었습니다.${NC}"
        else
            echo -e "${RED}애플리케이션 SQL Unit Test 중 오류가 발생했습니다.${NC}"
        fi
    else
        echo -e "${RED}오류: $OMA_BASE_DIR/bin/processSQLTest.sh 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    print_separator
}

# Java Source 변환
execute_java_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}애플리케이션 Java Source 변환 작업을 시작하기 전 3초 대기합니다...${NC}"
    sleep 3
    echo -e "${BLUE}${BOLD}애플리케이션 Java Source 변환 작업은 아직 통합 되지 않았습니다...${NC}"
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
        print_separator
        echo -ne "${CYAN}선택하세요 (1,2,b): ${NC}"
        read choice
        
        case $choice in
            1)
                execute_setenv
                ;;
            2)
                execute_checkenv
                ;;
            b|B)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 선택하세요.${NC}"
                ;;
        esac
    done
}

# 데이터베이스 변환 메뉴
show_database_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}1. 데이터베이스 변환 메뉴${NC}"
        print_separator
        echo -e "${MAGENTA}1. DB Schema 변환${NC}"
        echo -e "${YELLOW}   - Source → Target 스키마 변환 (DB 연결 필요)${NC}"
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        print_separator
        echo -ne "${CYAN}선택하세요 (1,b): ${NC}"
        read choice
        
        case $choice in
            1)
                execute_db_schema
                ;;
            b|B)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 선택하세요.${NC}"
                ;;
        esac
    done
}

# 애플리케이션 변환 메뉴
show_application_menu() {
    while true; do
        print_separator
        echo -e "${BLUE}${BOLD}2. 애플리케이션 변환 메뉴${NC}"
        print_separator
        echo -e "${CYAN}1. 애플리케이션 분석 및 SQL변환 대상 추출${NC}"
        echo -e "${YELLOW}   - JNDI, Mapper 파일 분석 → CSV 및 ApplicationReport.html 생성${NC}"
        echo -e "${CYAN}2. 애플리케이션 SQL 변환 작업${NC}"
        echo -e "${YELLOW}   - Source SQL → Target SQL 변환 (전체/재시도 모드)${NC}"
        echo -e "${CYAN}3. 애플리케이션 Java Source 변환 작업${NC}"
        echo -e "${YELLOW}   - Java 소스 코드 내 Source 관련 코드 변환 (미구현)${NC}"
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        print_separator
        echo -ne "${CYAN}선택하세요 (1,2,3,b): ${NC}"
        read choice
        
        case $choice in
            1)
                execute_app_discovery
                ;;
            2)
                execute_sql_transform
                ;;
            3)
                execute_java_transform
                ;;
            b|B)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 선택하세요.${NC}"
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
        echo -e "${CYAN}1. 애플리케이션 SQL Unit Test${NC}"
        echo -e "${YELLOW}   - 변환된 SQL 테스트 및 결과 분석 (DB 연결 필요)${NC}"
        echo -e "${YELLOW}b. 메인 메뉴로 돌아가기${NC}"
        print_separator
        echo -ne "${CYAN}선택하세요 (1,b): ${NC}"
        read choice
        
        case $choice in
            1)
                execute_sql_unittest
                ;;
            b|B)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 선택하세요.${NC}"
                ;;
        esac
    done
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
    echo -e "${MAGENTA}1. 데이터베이스 변환${NC}"
    echo -e "${CYAN}2. 애플리케이션 변환${NC}"
    echo -e "${CYAN}3. SQL 테스트 수행${NC}"
    echo -e "${YELLOW}q. 종료${NC}"
    print_separator
    echo -ne "${CYAN}메뉴를 선택하세요 (0,1,2,3,q): ${NC}"
    read choice

    case $choice in
        0)
            show_environment_menu
            ;;
        1)
            show_database_menu
            ;;
        2)
            show_application_menu
            ;;
        3)
            show_test_menu
            ;;
        q|Q)
            print_separator
            echo -e "${GREEN}프로그램을 종료합니다.${NC}"
            print_separator
            exit 0
            ;;
        *)
            echo -e "${RED}잘못된 선택입니다. 다시 선택하세요.${NC}"
            ;;
    esac
done

echo -e "${GREEN}모든 설정이 완료되었습니다.${NC}"

