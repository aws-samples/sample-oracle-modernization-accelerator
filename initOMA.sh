#!/bin/bash

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
    printf "${BLUE}${BOLD}%80s${NC}\n" | tr " " " "
}


print_separator
echo -e "${BLUE}${BOLD}OMA 프로젝트 디렉토리 구조${NC}"
print_separator
echo -e "${CYAN}OMA                                              OMA 폴더${NC}"
echo -e "${CYAN}├── setup                                        AWS Environment설정(사전 필수 구성요소)${NC}"
echo -e "${CYAN}├── initOMA.sh                                   OMA 애플리케이션 변환 프로그램 메인 수행 스크립트${NC}"
echo -e "${CYAN}├── OMA.properties                               프로젝트 설정 파일-환경 변수로 사용${NC}"
echo -e "${CYAN}├── [프로젝트명]                                   분석 및 변환 단위 : 애플리케이션명으로 구분${NC}"
echo -e "${CYAN}│   ├── 01.Database                              - 데이터데이스 스키마 변환 결과${NC}"
echo -e "${CYAN}│   │      ├── Tools                              - 데이터베이스 변환 프로그램${NC}"
echo -e "${CYAN}│   │      ├── work                                - 데이터베이슨 변환 중간 단계 결과 저장${NC}"
echo -e "${CYAN}│   │      └── Logs                                 - 데이터베이스 변환 로그 디렉토리${NC}"
echo -e "${CYAN}│   ├── 02.Application                           - 애플리케이션 분석 결과 디렉토리${NC}"
echo -e "${CYAN}│   │      ├── Assessments                         - 기초 분석 JNDI 정보와 분석 대상 리스트 정의${NC}"
echo -e "${CYAN}│   │      ├── Tools                               - Q Prompt와 프로그램 : initOMA.sh 수행 시 Tools 폴더에 복사됨${NC}"
echo -e "${CYAN}│   │      └── Transform                           - 애플리케이션 SQL 전환 결과 및 로그 정보${NC}"
echo -e "${CYAN}│   └── 03.Test                                  Unit 테스트 수행 결과 및 도구${NC}"
echo -e "${CYAN}│          ├── Tools                              - Unit Test Program${NC}"
echo -e "${CYAN}│          └── work                                - 임시 저장 화일들${NC}"
echo -e "${CYAN}└── 99.Templates                                 OMA 프로젝트 수행을 위한 분석 도구 템플릿. Tools 폴더에 복사됨${NC}"


# ====================================================
# OMA.properties 파일을 읽고 파싱하는 함수
# ====================================================
read_properties() {
    local APPLICATION_NAME=$1
    local DEBUG_MODE=${2:-false}
    
    if [ "$DEBUG_MODE" = true ]; then
        echo "디버깅: Properties 파일 읽기 시작"
    fi
    
    # APPLICATION_NAME을 즉시 export (COMMON 섹션 치환용)
    export APPLICATION_NAME="$APPLICATION_NAME"
    
    # 1단계: COMMON 섹션 먼저 읽기
    local in_common_section=false
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # 선행/후행 공백 제거
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # 디버깅 출력
        if [ "$DEBUG_MODE" = true ]; then
            echo "디버깅: COMMON 단계 - 키='$key', 값='$value', 섹션상태=$in_common_section"
        fi
        
        # COMMON 섹션인지 확인
        if [[ $key == "[COMMON]" ]]; then
            in_common_section=true
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: COMMON 섹션 시작"
            fi
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_common_section=false
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: 다른 섹션 시작 - $key"
            fi
            continue
        fi
        
        # COMMON 섹션에 있고 키-값 쌍이 있는 경우
        if [ "$in_common_section" = true ] && [[ -n $key && -n $value ]]; then
            # 키를 대문자로 변환하고 공백을 언더스코어로 변경
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            
            # 환경 변수 확장 (APPLICATION_NAME 치환)
            expanded_value=$(eval echo "$value")
            
            # 환경 변수 설정
            eval "export $env_var=\"$expanded_value\""
            
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: COMMON 환경변수 설정 - $env_var='$expanded_value'"
            fi
        fi
    done < "OMA.properties"
    
    # 2단계: 프로젝트 섹션 읽기 (오버라이드)
    local in_project_section=false
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # 선행/후행 공백 제거
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # 디버깅 출력
        if [ "$DEBUG_MODE" = true ]; then
            echo "디버깅: PROJECT 단계 - 키='$key', 값='$value', 섹션상태=$in_project_section"
        fi
        
        # 올바른 프로젝트 섹션인지 확인
        if [[ $key == "[$APPLICATION_NAME]" ]]; then
            in_project_section=true
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: 프로젝트 섹션 [$APPLICATION_NAME] 시작"
            fi
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_project_section=false
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: 다른 섹션 시작 - $key"
            fi
            continue
        fi
        
        # 올바른 프로젝트 섹션에 있고 키-값 쌍이 있는 경우
        if [ "$in_project_section" = true ] && [[ -n $key && -n $value ]]; then
            # 키를 대문자로 변환하고 공백을 언더스코어로 변경
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            
            # 환경 변수 확장
            expanded_value=$(eval echo "$value")
            
            # TRANSFORM_RELATED_CLASS인 경우 쉼표 구분 형식을 유지
            if [ "$env_var" = "TRANSFORM_RELATED_CLASS" ]; then
                # 쉼표 구분 형식을 그대로 유지하면서 환경 변수 설정
                eval "export $env_var=\"$expanded_value\""
            else
                # 일반적인 환경 변수 설정
                eval "export $env_var=\"$expanded_value\""
            fi
            
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: PROJECT 환경변수 설정 - $env_var='$expanded_value'"
            fi
        fi
    done < "OMA.properties"
    
    if [ "$DEBUG_MODE" = true ]; then
        echo "디버깅: Properties 파일 읽기 완료"
    fi
}

# ====================================================
# 환경 변수 출력 함수
# ====================================================
print_environment_variables() {
    print_separator
    echo -e "${BLUE}${BOLD}[환경 변수 설정 결과]${NC}"
    print_separator
    echo -e "${GREEN}APPLICATION_NAME: $APPLICATION_NAME${NC}"
    echo -e "${GREEN}JAVA_SOURCE_FOLDER: $JAVA_SOURCE_FOLDER${NC}"
    echo -e "${GREEN}OMA_BASE_DIR: $OMA_BASE_DIR${NC}"
    echo -e "${GREEN}APP_ASSESSMENT_FOLDER: $APP_ASSESSMENT_FOLDER${NC}"
    echo -e "${GREEN}APP_TOOLS_FOLDER: $APP_TOOLS_FOLDER${NC}"
    echo -e "${GREEN}APP_TRANSFORM_FOLDER: $APP_TRANSFORM_FOLDER${NC}"
    echo -e "${GREEN}TEST_FOLDER: $TEST_FOLDER${NC}"
    echo -e "${GREEN}TRANSFORM_JNDI: $TRANSFORM_JNDI${NC}"
    echo -e "${GREEN}TEMPLATES_FOLDER: $TEMPLATES_FOLDER${NC}"
    echo -e "${GREEN}TRANSFORM_RELATED_CLASS: $TRANSFORM_RELATED_CLASS${NC}"
    echo -e "${GREEN}ASCT_HOME: $ASCT_HOME${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}[DB 연결 환경 변수]${NC}"
    print_separator
    echo -e "${GREEN}Oracle Connection:${NC}"
    echo -e "${GREEN}  ORACLE_ADM_USER: ${ORACLE_ADM_USER:-'(not set)'}${NC}"
    echo -e "${GREEN}  ORACLE_HOST: ${ORACLE_HOST:-'(not set)'}${NC}"
    echo -e "${GREEN}  ORACLE_PORT: ${ORACLE_PORT:-'(not set)'}${NC}"
    echo -e "${GREEN}  ORACLE_SID: ${ORACLE_SID:-'(not set)'}${NC}"
    echo -e "${GREEN}PostgreSQL Connection:${NC}"
    echo -e "${GREEN}  PGHOST: ${PGHOST:-'(not set)'}${NC}"
    echo -e "${GREEN}  PGUSER: ${PGUSER:-'(not set)'}${NC}"
    echo -e "${GREEN}  PGPORT: ${PGPORT:-'(not set)'}${NC}"
    echo -e "${GREEN}  PGDATABASE: ${PGDATABASE:-'(not set)'}${NC}"
}

# ====================================================
# Application 분석 환경 설정 함수
# ====================================================
setup_application_environment() {
    print_separator
    echo -e "${BLUE}${BOLD}Application 분석 환경 설정${NC}"
    print_separator

    # JAVA_SOURCE_FOLDER의 src 확인
    if [ ! -d "$JAVA_SOURCE_FOLDER" ]; then
        echo -e "${RED}오류: $JAVA_SOURCE_FOLDER 디렉토리가 존재하지 않습니다.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ JAVA_SOURCE_FOLDER의 src 디렉토리 확인 완료${NC}"

    # 기존 분석 내용 확인
    local existing_analysis=false
    if [ -d "$APP_ASSESSMENT_FOLDER" ] && [ "$(ls -A $APP_ASSESSMENT_FOLDER 2>/dev/null)" ]; then
        existing_analysis=true
        echo -e "${YELLOW}⚠️  기존 분석 내용이 존재합니다: $APP_ASSESSMENT_FOLDER${NC}"
        echo -e "${CYAN}기존 분석 결과를 유지하고 스크립트 복제를 건너뜁니다.${NC}"
    fi

    # ====================================================
    # 01.Database 디렉토리 구조 생성
    # ====================================================
    echo -e "${BLUE}${BOLD}01.Database 디렉토리 구조 생성${NC}"
    
    mkdir -p "$DB_ASSESSMENTS_FOLDER"
    mkdir -p "$DB_LOGS_FOLDER"
    mkdir -p "$DB_TOOLS_FOLDER"
    mkdir -p "$DB_TRANSFORM_FOLDER"
    
    echo -e "${GREEN}✓ DB_ASSESSMENTS_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ DB_LOGS_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ DB_TOOLS_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ DB_TRANSFORM_FOLDER 디렉토리 생성 완료${NC}"

    # ====================================================
    # 02.Application 디렉토리 구조 생성
    # ====================================================
    echo -e "${BLUE}${BOLD}02.Application 디렉토리 구조 생성${NC}"
    
    mkdir -p "$APP_ASSESSMENT_FOLDER"
    mkdir -p "$APP_TOOLS_FOLDER"
    mkdir -p "$APP_TRANSFORM_FOLDER"
    mkdir -p "$APP_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ APP_ASSESSMENT_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ APP_TOOLS_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ APP_TRANSFORM_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ APP_LOGS_FOLDER 디렉토리 생성 완료${NC}"

    # ====================================================
    # 03.Test 디렉토리 구조 생성
    # ====================================================
    echo -e "${BLUE}${BOLD}03.Test 디렉토리 구조 생성${NC}"
    
    mkdir -p "$TEST_TOOLS_FOLDER"
    mkdir -p "$TEST_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ TEST_TOOLS_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ TEST_LOGS_FOLDER 디렉토리 생성 완료${NC}"

    # ====================================================
    # Template Script 복사 (기존 분석 내용이 없는 경우에만)
    # ====================================================
    if [ "$existing_analysis" = false ]; then
        print_separator
        echo -e "${BLUE}${BOLD}Template Script 복사 (신규 프로젝트)${NC}"
        print_separator

        if [ ! -d "$TEMPLATES_FOLDER" ]; then
            echo -e "${RED}오류: 99.Templates 디렉토리가 존재하지 않습니다.${NC}"
            exit 1
        fi

        # ====================================================
        # DB01* 파일들을 DB_TOOLS_FOLDER에 복사
        # ====================================================
        echo -e "${CYAN}DB01* 파일들을 Database Tools 폴더에 복사 중...${NC}"
        local db_copied_count=0
        for template_file in "$TEMPLATES_FOLDER"/DB01*; do
            if [ -f "$template_file" ]; then
                filename=$(basename "$template_file")
                target_file="$DB_TOOLS_FOLDER/$filename"
                
                # 환경 변수 치환하여 복사
                sed -e "s|\$APPLICATION_NAME|$APPLICATION_NAME|g" \
                    -e "s|\$ASCT_HOME|$ASCT_HOME|g" \
                    -e "s|\$DB_ASSESSMENTS_FOLDER|$DB_ASSESSMENTS_FOLDER|g" \
                    -e "s|\$DB_LOGS_FOLDER|$DB_LOGS_FOLDER|g" \
                    -e "s|\$DB_TOOLS_FOLDER|$DB_TOOLS_FOLDER|g" \
                    -e "s|\$DB_TRANSFORM_FOLDER|$DB_TRANSFORM_FOLDER|g" \
                    -e "s|\$OMA_BASE_DIR|$OMA_BASE_DIR|g" \
                    -e "s|\$TEMPLATES_FOLDER|$TEMPLATES_FOLDER|g" \
                    "$template_file" > "$target_file"
                
                echo -e "${GREEN}✓ $filename → Database/Tools 복사 완료${NC}"
                ((db_copied_count++))
            fi
        done

        # ====================================================
        # AP* 파일들을 APP_TOOLS_FOLDER에 복사
        # ====================================================
        echo -e "${CYAN}AP* 파일들을 Application Tools 폴더에 복사 중...${NC}"
        local app_copied_count=0
        for template_file in "$TEMPLATES_FOLDER"/AP*; do
            if [ -f "$template_file" ]; then
                filename=$(basename "$template_file")
                target_file="$APP_TOOLS_FOLDER/$filename"
                
                # 환경 변수 치환하여 복사
                sed -e "s|\$APPLICATION_NAME|$APPLICATION_NAME|g" \
                    -e "s|\$APP_ASSESSMENT_FOLDER|$APP_ASSESSMENT_FOLDER|g" \
                    -e "s|\$JAVA_SOURCE_FOLDER|$JAVA_SOURCE_FOLDER|g" \
                    -e "s|\$APP_TRANSFORM_FOLDER|$APP_TRANSFORM_FOLDER|g" \
                    -e "s|\$APP_LOGS_FOLDER|$APP_LOGS_FOLDER|g" \
                    -e "s|\$TRANSFORM_JNDI|$TRANSFORM_JNDI|g" \
                    -e "s|\$OMA_BASE_DIR|$OMA_BASE_DIR|g" \
                    -e "s|\$APP_TOOLS_FOLDER|$APP_TOOLS_FOLDER|g" \
                    -e "s|\$TEMPLATES_FOLDER|$TEMPLATES_FOLDER|g" \
                    -e "s|\$TRANSFORM_RELATED_CLASS|$TRANSFORM_RELATED_CLASS|g" \
                    "$template_file" > "$target_file"
                
                echo -e "${GREEN}✓ $filename → Application/Tools 복사 완료${NC}"
                ((app_copied_count++))
            fi
        done

        # ====================================================
        # TST* 파일들을 TEST_TOOLS_FOLDER에 복사
        # ====================================================
        echo -e "${CYAN}TST* 파일들을 Test Tools 폴더에 복사 중...${NC}"
        local test_copied_count=0
        for template_file in "$TEMPLATES_FOLDER"/TST*; do
            if [ -f "$template_file" ]; then
                filename=$(basename "$template_file")
                target_file="$TEST_TOOLS_FOLDER/$filename"
                
                # 환경 변수 치환하여 복사
                sed -e "s|\$APPLICATION_NAME|$APPLICATION_NAME|g" \
                    -e "s|\$TEST_FOLDER|$TEST_FOLDER|g" \
                    -e "s|\$TEST_TOOLS_FOLDER|$TEST_TOOLS_FOLDER|g" \
                    -e "s|\$TEST_LOGS_FOLDER|$TEST_LOGS_FOLDER|g" \
                    -e "s|\$OMA_BASE_DIR|$OMA_BASE_DIR|g" \
                    -e "s|\$TEMPLATES_FOLDER|$TEMPLATES_FOLDER|g" \
                    "$template_file" > "$target_file"
                
                echo -e "${GREEN}✓ $filename → Test/Tools 복사 완료${NC}"
                ((test_copied_count++))
            fi
        done
        
        # 복사 결과 요약
        echo -e "${GREEN}✓ Database: $db_copied_count 개 파일 복사 완료${NC}"
        echo -e "${GREEN}✓ Application: $app_copied_count 개 파일 복사 완료${NC}"
        echo -e "${GREEN}✓ Test: $test_copied_count 개 파일 복사 완료${NC}"
        
    else
        print_separator
        echo -e "${CYAN}${BOLD}기존 분석 프로젝트 - 스크립트 복제 건너뜀${NC}"
        print_separator
        echo -e "${CYAN}기존 Tools 폴더의 스크립트들을 그대로 사용합니다.${NC}"
        echo -e "${YELLOW}필요시 수동으로 99.Templates에서 개별 파일을 복사하세요.${NC}"
    fi
}

# ====================================================
# Step 3: MyBatis 기반 Java 애플리케이션의 JNDI와 XML Mapper정보 확인 및 리스트화
# ====================================================
process_mybatis_info() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 3: MyBatis 기반 Java 애플리케이션의 JNDI와 XML Mapper정보 확인 및 리스트화${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 다음 작업을 수행합니다:${NC}"
    echo -e "${CYAN}1. 애플리케이션 기본 정보 수집 및 기술 스택 분석${NC}"
    echo -e "${CYAN}2. MyBatis 설정 파일 분석 및 Mapper 파일 목록 생성${NC}"
    echo -e "${CYAN}3. JNDI 정보 추출 및 매핑 정보 생성${NC}"
    echo -e "${CYAN}4. SQL 패턴 발견 및 분석${NC}"
    echo -e "${CYAN}5. 통합 분석 리포트 (ApplicationReport.html) 생성${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}실행 예시:${NC}"
    echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/AP01.Discovery.txt${NC}"

    # AP01.Discovery.txt 실행 (통합된 분석 작업)
    if [ -f "$APP_TOOLS_FOLDER/AP01.Discovery.txt" ]; then
        echo -e "${CYAN}애플리케이션 분석 및 MyBatis 정보 추출 중...${NC}"
        echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/AP01.Discovery.txt${NC}"
        q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/AP01.Discovery.txt"
    else
        echo -e "${RED}오류: AP01.Discovery.txt 파일을 찾을 수 없습니다: $APP_TOOLS_FOLDER/AP01.Discovery.txt${NC}"
        return 1
    fi

    # JNDI와 Mapper 파일 조합 생성 (후속 처리)
    echo -e "${BLUE}${BOLD}JNDI와 Mapper 파일 조합을 생성중입니다.${NC}"
    if [ -f "$APP_TOOLS_FOLDER/AP02.GenSQLTransformTarget.py" ]; then
        python3 "$APP_TOOLS_FOLDER/AP02.GenSQLTransformTarget.py"
    else
        echo -e "${YELLOW}경고: AP02.GenSQLTransformTarget.py 파일을 찾을 수 없습니다.${NC}"
    fi
    
    # SQL Mapper Report 생성 (주석 처리된 부분 - 필요시 활성화)
    #echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/AP02.GenSQLMapperReport.txt${NC}"
    #q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/AP02.GenSQLMapperReport.txt"

    # SQL Transform Target Report 생성 (주석 처리된 부분 - 필요시 활성화)
    #echo -e "${BLUE}${BOLD}SQL Transform Target Report 생성중입니다.${NC}"
    #python3 "$APP_TOOLS_FOLDER/AP02.ReportSQLTransformTarget.py"
}

# ====================================================
# Step 4: SQL 변환 작업
# ====================================================
process_sql_transform() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 4: SQL 변환 작업${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 SQL 변환 작업을 수행합니다.${NC}"
    print_separator
    
    # 재시도 옵션 확인
    echo -e "${YELLOW}재시도 모드를 선택하세요:${NC}"
    echo -e "${CYAN}1. 재시도 - SQLTransformTargetFailure.csv의 항목만 재변환 (기존 오류 항목만 재작업)${NC}"
    echo -e "${CYAN}2. 전체 - SQLTransformTarget.csv의 모든 항목을 변환 (전체 작업 다시 수행)${NC}"
    echo -e "${CYAN}재작업이 필요한 경우 1. 재시도 선택이 효율적입니다.${NC}"
    read retry_mode
    retry_mode=${retry_mode:-1}  # 기본값 1
    
    local retry_arg=""
    if [ "$retry_mode" = "1" ]; then
        echo -e "${GREEN}재시도 모드로 실행합니다. SQLTransformTargetFailure.csv의 항목만 처리합니다.${NC}"
        retry_arg="--file $APP_TRANSFORM_FOLDER/SQLTransformTargetFailure.csv"
    else
        echo -e "${GREEN}전체 모드로 실행합니다. SQLTransformTarget.csv의 모든 항목을 처리합니다.${NC}"
    fi
    
    echo -e "${BLUE}${BOLD}실행 명령:${NC}"
    echo -e "${BLUE}${BOLD}python3 $APP_TOOLS_FOLDER/AP03.SQLTransformTarget.py $retry_arg${NC}"
    print_separator

    echo -e "${BLUE}${BOLD}작업을 수행하기 이전에 3초 대기 합니다.${NC}"
    sleep 3

    python3 "$APP_TOOLS_FOLDER/AP03.SQLTransformTarget.py" $retry_arg
    print_separator
    print_separator
    echo -e "${GREEN}SQL 변환 작업이 완료되었습니다.${NC}"
    echo -e "${YELLOW}오류 정보는 Assessment/SQLTransformFailure.csv에 리스팅되었습니다.${NC}"
    print_separator
    echo -e "${BLUE}${BOLD}SQL Transform 작업 결과 보고서를 작성합니다.${NC}"
    sleep 1
    echo -e "${BLUE}${BOLD}q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/AP03.TransformReport.txt ${NC}"
    q chat --trust-all-tools --no-interactive < $APP_TOOLS_FOLDER/AP03.TransformReport.txt
    sleep 1
    print_separator
    echo -e "${GREEN}SQL 변환 작업 보고서가 작성되었습니다.${NC}"
    echo -e "${YELLOW}${BOLD}$APP_TOOLS_FOLDER 에서 확인 가능합니다.${NC}"
}

# ====================================================
# 메인 스크립트 시작
# ====================================================

# OMA.properties 파일 존재 확인
if [ ! -f "OMA.properties" ]; then
    echo -e "${RED}오류: OMA.properties 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# OMA.properties에서 프로젝트 목록 가져오기 (COMMON 제외)
projects=($(grep -o '\[.*\]' OMA.properties | tr -d '[]' | grep -v '^COMMON$'))

if [ ${#projects[@]} -eq 0 ]; then
    echo -e "${RED}오류: OMA.properties에 프로젝트가 정의되어 있지 않습니다.${NC}"
    exit 1
fi

# 프로젝트 선택 메뉴 표시
print_separator
echo -e "${BLUE}${BOLD}OMA는 AWS에서 사전 환경이 구성된 상태에서 DB/Application 변환을 수행합니다.${NC}"
echo -e "${BLUE}${BOLD}변환 대상 프로젝트를 선택하세요:${NC}"
print_separator
echo -e "${RED}${BOLD}⚠️  중요 안내${NC}"
echo -e "${YELLOW}OMA 변환 작업 수행 중 데이터베이스 연관된 작업은 Source 시스템과 연결이 되는 AWS 환경 구성을 사전에 요구합니다.${NC}"
echo -e "${YELLOW}(DB Schema 변환, SQL Unit Test 등)${NC}"
echo -e "${CYAN}${BOLD}사전 환경 구성 스크립트: ${GREEN}./setup/deploy-omabox.sh${NC}"
print_separator
echo -e "${BLUE}${BOLD}사용 가능한 프로젝트 목록:${NC}"
for i in "${!projects[@]}"; do
    echo -e "${CYAN}$((i+1)). ${projects[$i]}${NC}"
done

# 사용자 선택 받기
echo -ne "${BLUE}${BOLD}프로젝트 번호를 선택하세요 (1-${#projects[@]}): ${NC}"
read selection

# 선택 유효성 검사
if [[ $selection -lt 1 || $selection -gt ${#projects[@]} ]]; then
    echo -e "${RED}잘못된 선택입니다. 1-${#projects[@]} 범위의 번호를 입력하세요.${NC}"
    exit 1
fi

# 선택된 프로젝트 이름 가져오기
selected_project="${projects[$((selection-1))]}"

# 프로젝트 이름을 환경 변수로 설정
export APPLICATION_NAME="$selected_project"

# 디버그 모드 확인
DEBUG_MODE=false
if [[ "$*" == *"--debug"* ]]; then
    DEBUG_MODE=true
fi

# 선택된 프로젝트의 속성 읽기 및 설정
read_properties "$selected_project" "$DEBUG_MODE"

# 자동으로 Application 분석 환경 설정 수행
echo -e "${BLUE}${BOLD}선택된 프로젝트: $selected_project${NC}"
echo -e "${CYAN}환경 설정을 자동으로 수행합니다...${NC}"
setup_application_environment

# 기존 분석 내용 확인 및 알림 (환경 설정 후)
if [ -d "$APP_ASSESSMENT_FOLDER" ] && [ "$(ls -A $APP_ASSESSMENT_FOLDER 2>/dev/null)" ]; then
    print_separator
    echo -e "${YELLOW}${BOLD}⚠️  기존 분석 내용이 존재합니다${NC}"
    echo -e "${CYAN}APP_ASSESSMENT_FOLDER: $APP_ASSESSMENT_FOLDER${NC}"
    echo -e "${CYAN}기존 분석 결과가 보호되었습니다.${NC}"
    print_separator
    sleep 2
fi

# 환경 변수 출력 (디버그 모드일 때만)
if [ "$DEBUG_MODE" = true ]; then
    print_environment_variables
fi

# ====================================================
# Step 2: DB Schema 변환
# ====================================================
process_db_schema_conversion() {
    print_separator
    echo -e "${BLUE}${BOLD}Step 2: DB Schema 변환${NC}"
    print_separator
    echo -e "${CYAN}이 단계에서는 데이터베이스 스키마 변환 작업을 수행합니다.${NC}"
    echo -e "${CYAN}Oracle 스키마를 PostgreSQL로 변환하는 작업을 수행합니다.${NC}"
    print_separator
    
    # DB Schema 변환을 위한 환경 변수 설정
    local DB_BASE_DIR="$OMA_BASE_DIR/01.Database"
    local DB_TOOLS_DIR="$DB_BASE_DIR/Tools"
    local DB_ASCT_PROGRAM="$DB_TOOLS_DIR/DB01.asct.py"
    
    # 필수 디렉토리 및 파일 확인
    if [ ! -d "$DB_BASE_DIR" ]; then
        echo -e "${RED}오류: 01.Database 디렉토리가 존재하지 않습니다: $DB_BASE_DIR${NC}"
        return 1
    fi
    
    if [ ! -f "$DB_ASCT_PROGRAM" ]; then
        echo -e "${RED}오류: DB01.asct.py 프로그램이 존재하지 않습니다: $DB_ASCT_PROGRAM${NC}"
        echo -e "${YELLOW}99.Templates에서 DB01.asct.py를 복사해야 할 수 있습니다.${NC}"
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
    
    # ASCT_HOME 환경 변수 설정
    export ASCT_HOME="$DB_BASE_DIR"
    
    echo -e "${GREEN}환경 변수 설정:${NC}"
    echo -e "${GREEN}  ASCT_HOME: $ASCT_HOME${NC}"
    echo -e "${GREEN}  DB_ASCT_PROGRAM: $DB_ASCT_PROGRAM${NC}"
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
            echo -e "${BLUE}${BOLD}cd $DB_BASE_DIR && python3 Tools/DB01.asct.py${NC}"
            print_separator
            
            echo -e "${BLUE}${BOLD}DB Schema 변환을 시작합니다...${NC}"
            cd "$DB_BASE_DIR"
            python3 "Tools/DB01.asct.py"
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}DB Schema 변환이 성공적으로 완료되었습니다.${NC}"
                echo -e "${CYAN}변환 결과는 다음 위치에서 확인할 수 있습니다:${NC}"
                echo -e "${CYAN}  - 변환된 스키마: $DB_BASE_DIR/Transform/${NC}"
                echo -e "${CYAN}  - 변환 로그: $DB_BASE_DIR/Logs/${NC}"
            else
                echo -e "${RED}DB Schema 변환 중 오류가 발생했습니다.${NC}"
                echo -e "${YELLOW}로그를 확인하세요: $DB_BASE_DIR/Logs/asct.log${NC}"
            fi
            ;;
        2)
            echo -e "${GREEN}PostgreSQL 배포 모드로 실행합니다.${NC}"
            echo -e "${BLUE}${BOLD}실행 명령:${NC}"
            echo -e "${BLUE}${BOLD}cd $DB_BASE_DIR && python3 Tools/DB01.asct.py --deploy-only${NC}"
            print_separator
            
            echo -e "${BLUE}${BOLD}PostgreSQL 배포를 시작합니다...${NC}"
            cd "$DB_BASE_DIR"
            python3 "Tools/DB01.asct.py" --deploy-only
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}PostgreSQL 배포가 성공적으로 완료되었습니다.${NC}"
            else
                echo -e "${RED}PostgreSQL 배포 중 오류가 발생했습니다.${NC}"
                echo -e "${YELLOW}로그를 확인하세요: $DB_BASE_DIR/Logs/asct.log${NC}"
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

# Step별 수행 루프
while true; do
    print_separator
    echo -e "${BLUE}${BOLD}Step별 수행을 선택하세요.${NC}"
    print_separator
    echo -e "${YELLOW}0. 상위 메뉴로 가기${NC}"
    echo -e "${MAGENTA}1. DB Schema 변환${NC}"
    echo -e "${YELLOW}   - Oracle → PostgreSQL 스키마 변환 (DB 연결 필요)${NC}"

    echo -e "${CYAN}2. 애플리케이션 분석 및 SQL변환 대상 추출${NC}"
    echo -e "${YELLOW}   - JNDI, Mapper 파일 분석 → CSV 및 ApplicationReport.html 생성${NC}"

    echo -e "${CYAN}3. 애플리케이션 SQL 변환 작업${NC}"
    echo -e "${YELLOW}   - Oracle SQL → PostgreSQL SQL 변환 (전체/재시도 모드)${NC}"

    echo -e "${CYAN}4. 애플리케이션 SQL Unit Test${NC}"
    echo -e "${YELLOW}   - 변환된 SQL 테스트 (미구현)${NC}"

    echo -e "${CYAN}5. 애플리케이션 Java Source 변환 작업${NC}"
    echo -e "${YELLOW}   - Java 소스 코드 내 Oracle 관련 코드 변환 (미구현)${NC}"
    echo -e "${YELLOW}6. 종료${NC}"
    print_separator
    echo -ne "${CYAN}수행할 Step을 선택하세요 (0,1,2,3,4,5,6 또는 여러개 선택 가능, 예: 1, 2): ${NC}"
    read selected_steps

    # 선택된 Step들을 배열로 변환
    IFS=',' read -ra steps <<< "$selected_steps"

    for step in "${steps[@]}"; do
        case $step in
            0)
                print_separator
                echo -e "${YELLOW}상위 메뉴(프로젝트 선택)로 돌아갑니다.${NC}"
                print_separator
                exec "$0" "$@"
                ;;
            1)
                print_separator
                echo -e "${BLUE}${BOLD}DB Schema 변환을 시작하기 전 3초 대기합니다...${NC}"
                print_separator
                sleep 3
                process_db_schema_conversion
                print_separator
                ;;
            2)
                print_separator
                echo -e "${BLUE}${BOLD}애플리케이션 분석 및 SQL변환 대상 추출을 시작하기 전 3초 대기합니다...${NC}"
                print_separator
                sleep 3
                process_mybatis_info
                print_separator
                ;;
            3)
                print_separator
                echo -e "${BLUE}${BOLD}SQL 변환 작업을 시작하기 전 3초 대기합니다...${NC}"
                print_separator
                echo ""
                echo -e "${BLUE}${BOLD}변환 실패 항목 리스트 (Assessment/SQLTransformFailure.csv)를 새로 생성한 이후에 실행 됩니다...${NC}"
                print_separator
                sleep 3
                process_sql_transform
                print_separator
                ;;
            4)
                print_separator
                echo -e "${BLUE}${BOLD}애플리케이션 SQL Unit Test를 시작하기 전 3초 대기합니다...${NC}"
                print_separator
                sleep 3
                echo -e "${BLUE}${BOLD}애플리케이션 SQL Unit Test는 아직 통합 되지 않았습니다...${NC}"
                ;;
            5)
                print_separator
                echo -e "${BLUE}${BOLD}애플리케이션 Java Source 변환 작업을 시작하기 전 3초 대기합니다...${NC}"
                print_separator
                sleep 3
                echo -e "${BLUE}${BOLD}애플리케이션 Java Source 변환 작업은 아직 통합 되지 않았습니다...${NC}"
                ;;
            6)
                print_separator
                echo -e "${GREEN}프로그램을 종료합니다.${NC}"
                print_separator
                exit 0
                ;;
            *)
                echo -e "${RED}잘못된 Step 번호입니다: $step${NC}"
                ;;
        esac
    done
done

echo -e "${GREEN}모든 설정이 완료되었습니다.${NC}" 