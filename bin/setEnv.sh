#!/bin/bash

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

# ====================================================
# config/oma.properties 파일을 읽고 파싱하는 함수
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
    while read -r line || [ -n "$line" ]; do
        # 빈 줄이나 주석 건너뛰기
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # = 기준으로 key와 value 분리 (첫 번째 =만 사용)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
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
            expanded_value="${value//\$\{APPLICATION_NAME\}/$APPLICATION_NAME}"
            
            # 환경 변수 설정 (세션 환경 변수로 export)
            export "$env_var"="$expanded_value"
            
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: COMMON 환경변수 설정 - $env_var='$expanded_value'"
            fi
        fi
    done < "../config/oma.properties"
    
    # 2단계: 프로젝트 섹션 읽기 (오버라이드)
    local in_project_section=false
    while read -r line || [ -n "$line" ]; do
        # 빈 줄이나 주석 건너뛰기
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # = 기준으로 key와 value 분리 (첫 번째 =만 사용)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
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
            expanded_value="${value//\$\{APPLICATION_NAME\}/$APPLICATION_NAME}"
            expanded_value="${expanded_value//\$\{JAVA_SOURCE_FOLDER\}/$JAVA_SOURCE_FOLDER}"
            expanded_value="${expanded_value//\$\{APPLICATION_FOLDER\}/$APPLICATION_FOLDER}"
            expanded_value="${expanded_value//\$\{OMA_BASE_DIR\}/$OMA_BASE_DIR}"
            
            # TRANSFORM_RELATED_CLASS인 경우 쉼표 구분 형식을 유지
            if [ "$env_var" = "TRANSFORM_RELATED_CLASS" ]; then
                # 쉼표 구분 형식을 그대로 유지하면서 환경 변수 설정 (세션 환경 변수로 export)
                export "$env_var"="$expanded_value"
            else
                # 일반적인 환경 변수 설정 (세션 환경 변수로 export)
                export "$env_var"="$expanded_value"
            fi
            
            if [ "$DEBUG_MODE" = true ]; then
                echo "디버깅: PROJECT 환경변수 설정 - $env_var='$expanded_value'"
            fi
        fi
    done < "../config/oma.properties"
    
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
    echo -e "${GREEN}APPLICATION_FOLDER: $APPLICATION_FOLDER${NC}"
    echo -e "${GREEN}APP_TRANSFORM_FOLDER: $APP_TRANSFORM_FOLDER${NC}"
    echo -e "${GREEN}TEST_FOLDER: $TEST_FOLDER${NC}"
    echo -e "${GREEN}TRANSFORM_JNDI: $TRANSFORM_JNDI${NC}"
    echo -e "${GREEN}TRANSFORM_RELATED_CLASS: $TRANSFORM_RELATED_CLASS${NC}"
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
    if [ -d "$APPLICATION_FOLDER" ] && [ "$(ls -A $APPLICATION_FOLDER 2>/dev/null)" ]; then
        existing_analysis=true
        echo -e "${YELLOW}⚠️  기존 분석 내용이 존재합니다: $APPLICATION_FOLDER${NC}"
        echo -e "${CYAN}기존 분석 결과를 유지하고 스크립트 복제를 건너뜁니다.${NC}"
    fi

    # ====================================================
    # 01.Database 디렉토리 구조 생성
    # ====================================================
    echo -e "${BLUE}${BOLD}01.Database 디렉토리 구조 생성${NC}"
    
    mkdir -p "$DBMS_FOLDER"
    mkdir -p "$DBMS_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ DBMS_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ DBMS_LOGS_FOLDER 디렉토리 생성 완료${NC}"

    # ====================================================
    # 02.Application 디렉토리 구조 생성
    # ====================================================
    echo -e "${BLUE}${BOLD}02.Application 디렉토리 구조 생성${NC}"
    
    mkdir -p "$APPLICATION_FOLDER"
    mkdir -p "$APP_TRANSFORM_FOLDER"
    mkdir -p "$APP_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ APPLICATION_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ APP_TRANSFORM_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ APP_LOGS_FOLDER 디렉토리 생성 완료${NC}"

    # ====================================================
    # 03.Test 디렉토리 구조 생성
    # ====================================================
    echo -e "${BLUE}${BOLD}03.Test 디렉토리 구조 생성${NC}"
    
    mkdir -p "$TEST_FOLDER"
    mkdir -p "$TEST_LOGS_FOLDER"
    
    echo -e "${GREEN}✓ TEST_FOLDER 디렉토리 생성 완료${NC}"
    echo -e "${GREEN}✓ TEST_LOGS_FOLDER 디렉토리 생성 완료${NC}"

    # ====================================================
    # 프로젝트 구조 생성 (기존 분석 내용이 없는 경우에만)
    # ====================================================
    if [ "$existing_analysis" = false ]; then

        
        # 프로젝트 루트에 README 파일 생성
        local readme_file="$OMA_BASE_DIR/${APPLICATION_NAME}/README.md"
        cat > "$readme_file" << 'EOF'
## 환경 설정
```bash
# 환경 변수 로드
source ./bin/oma_env_${APPLICATION_NAME}.sh

# 환경 변수 확인
./checkEnv.sh
```

## 변환 작업 수행
```bash
# 각 디렉토리에서 필요한 작업 수행
# 각 디렉토리에서 필요한 작업 수행

# 각 도구별로 실행
```

## 디렉토리 구조
- `transform` - DB 스키마 변환 결과
- `transform` - 애플리케이션 분석 및 변환 결과
- `transform` - 테스트 관련 파일들

## 주의사항
- DB 관련 작업은 Oracle/PostgreSQL 연결이 필요합니다
- 환경 변수 파일을 먼저 source 해야 합니다
EOF
        
        echo -e "${GREEN}✓ README.md 파일 생성 완료${NC}"
        
    else
        print_separator
        echo -e "${CYAN}${BOLD}기존 분석 프로젝트 - 스크립트 업데이트${NC}"
        print_separator
        echo -e "${CYAN}기존 프로젝트 구조를 그대로 사용합니다.${NC}"
        
        # README 파일이 없으면 생성
        local readme_file="$OMA_BASE_DIR/${APPLICATION_NAME}/README.md"
        if [ ! -f "$readme_file" ]; then
            cat > "$readme_file" << 'EOF'
# OMA 프로젝트 실행 가이드

## 환경 설정
```bash
# 환경 변수 로드
source ./bin/oma_env_${APPLICATION_NAME}.sh

# 환경 변수 확인
./checkEnv.sh
```

## 변환 작업 수행
```bash
# 각 디렉토리에서 필요한 작업 수행
# 각 디렉토리에서 필요한 작업 수행

# 각 도구별로 실행
```

## 디렉토리 구조
- `transform` - DB 스키마 변환 결과
- `transform` - 애플리케이션 분석 및 변환 결과
- `transform` - 테스트 관련 파일들

## 주의사항
- DB 관련 작업은 Oracle/PostgreSQL 연결이 필요합니다
- 환경 변수 파일을 먼저 source 해야 합니다
EOF
            echo -e "${GREEN}✓ README.md 파일 생성 완료${NC}"
        fi
    fi
}

# ====================================================
# 메인 실행 부분
# ====================================================

# config/oma.properties 파일 존재 확인
if [ ! -f "../config/oma.properties" ]; then
    echo -e "${RED}오류: config/oma.properties 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# config/oma.properties에서 프로젝트 목록 가져오기 (COMMON 제외)
projects=($(grep -o '\[.*\]' ../config/oma.properties | tr -d '[]' | grep -v '^COMMON$'))

if [ ${#projects[@]} -eq 0 ]; then
    echo -e "${RED}오류: config/oma.properties에 프로젝트가 정의되어 있지 않습니다.${NC}"
    exit 1
fi

# 프로젝트 선택 메뉴 표시
print_separator
echo -e "${BLUE}${BOLD}환경 변수 설정을 위한 프로젝트를 선택하세요:${NC}"
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
if [ -d "$APPLICATION_FOLDER" ] && [ "$(ls -A $APPLICATION_FOLDER 2>/dev/null)" ]; then
    print_separator
    echo -e "${YELLOW}${BOLD}⚠️  기존 분석 내용이 존재합니다${NC}"
    echo -e "${CYAN}APPLICATION_FOLDER: $APPLICATION_FOLDER${NC}"
    echo -e "${CYAN}기존 분석 결과가 보호되었습니다.${NC}"
    print_separator
    sleep 2
fi

# 환경 변수 출력 (디버그 모드일 때만)
if [ "$DEBUG_MODE" = true ]; then
    print_environment_variables
fi

echo -e "${GREEN}환경 설정이 완료되었습니다.${NC}"
echo -e "${CYAN}프로젝트 구조 생성이 완료되었습니다.${NC}"

# 현재 디렉토리와 프로젝트 루트에 환경 변수 파일 생성
ENV_FILE="./oma_env_${APPLICATION_NAME}.sh"
PROJECT_ENV_FILE="$OMA_BASE_DIR/oma_env_${APPLICATION_NAME}.sh"

echo -e "${BLUE}${BOLD}환경 변수를 파일에 저장 중...${NC}"

# 환경 변수 파일 생성 - 완전히 동적으로 처리
cat > "$ENV_FILE" << EOF
#!/bin/bash
# OMA 환경 변수 설정 (자동 생성됨)
# 프로젝트: $APPLICATION_NAME
# 생성 시간: $(date)

EOF

# 현재 설정된 모든 환경 변수를 동적으로 추출하여 파일에 저장
# oma.properties에서 정의된 모든 변수들을 확인
if [ -f "../config/oma.properties" ]; then
    # 모든 정의된 변수들을 수집
    all_defined_vars=()
    
    # COMMON 섹션 처리
    in_common_section=false
    while read -r line || [ -n "$line" ]; do
        # 빈 줄이나 주석 건너뛰기
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # = 기준으로 key와 value 분리 (첫 번째 =만 사용)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [[ $key == "[COMMON]" ]]; then
            in_common_section=true
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_common_section=false
            continue
        fi
        
        if [ "$in_common_section" = true ] && [[ -n $key && $key != \#* ]]; then
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            all_defined_vars+=("$env_var")
        fi
    done < "../config/oma.properties"
    
    # 프로젝트 섹션 처리
    in_project_section=false
    while read -r line || [ -n "$line" ]; do
        # 빈 줄이나 주석 건너뛰기
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # = 기준으로 key와 value 분리 (첫 번째 =만 사용)
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
        else
            key="$line"
            value=""
        fi
        
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [[ $key == "[$selected_project]" ]]; then
            in_project_section=true
            continue
        elif [[ $key =~ ^\[.*\]$ ]]; then
            in_project_section=false
            continue
        fi
        
        if [ "$in_project_section" = true ] && [[ -n $key && $key != \#* ]]; then
            env_var=$(echo "$key" | tr '[:lower:]' '[:upper:]' | tr ' ' '_')
            all_defined_vars+=("$env_var")
        fi
    done < "../config/oma.properties"
    
    # 중복 제거하고 정렬
    unique_vars=($(printf "%s\n" "${all_defined_vars[@]}" | sort -u))
    
    # 설정된 환경 변수들만 파일에 저장
    for var in "${unique_vars[@]}"; do
        if [ -n "${!var}" ]; then
            echo "export $var=\"${!var}\"" >> "$ENV_FILE"
        fi
    done
    
    # PATH 설정 추가
    echo "" >> "$ENV_FILE"
    echo "# PATH 설정" >> "$ENV_FILE"
    echo "export PATH=\"\$APP_TOOLS_FOLDER:\$OMA_BASE_DIR/bin:\$PATH\"" >> "$ENV_FILE"
    
    # Alias 설정 추가
    echo "" >> "$ENV_FILE"
    echo "# Alias 설정" >> "$ENV_FILE"
    echo "alias qlog='cd \$APP_LOGS_FOLDER/qlogs && \$APP_TOOLS_FOLDER/tailLatestLog.sh'" >> "$ENV_FILE"

    # NLS 환경 변수 추가
    echo "" >> "$ENV_FILE"
    echo "# NLS Environment Variables" >> "$ENV_FILE"
    echo "export NLS_DATE_FORMAT='${NLS_DATE_FORMAT}'" >> "$ENV_FILE"
    echo "export NLS_LANG=${NLS_LANG}" >> "$ENV_FILE"

    # 데이터베이스 연결 alias 추가
    echo "" >> "$ENV_FILE"
    echo "# Database Connection Aliases" >> "$ENV_FILE"
    echo "alias sqlplus-oma='sqlplus \$ORACLE_ADM_USER/\$ORACLE_ADM_PASSWORD@\$ORACLE_HOST:1521/\$ORACLE_SID'" >> "$ENV_FILE"
fi

# 환경 변수 파일에 실행 권한 부여
chmod +x "$ENV_FILE"

# 프로젝트 루트에도 환경 변수 파일 복사
cp "$ENV_FILE" "$PROJECT_ENV_FILE"
chmod +x "$PROJECT_ENV_FILE"

echo -e "${GREEN}✓ 환경 변수 파일 생성: $ENV_FILE${NC}"
echo -e "${GREEN}✓ 환경 변수 파일 복사: $PROJECT_ENV_FILE${NC}"

# 현재 셸에 환경 변수 설정
echo -e "${BLUE}${BOLD}현재 셸 세션에 환경 변수 설정 중...${NC}"
source "$ENV_FILE"

# PATH에 필요한 디렉토리 추가
echo -e "${BLUE}${BOLD}PATH 환경 변수 업데이트 중...${NC}"
export PATH="$APP_TOOLS_FOLDER:$OMA_BASE_DIR/bin:$PATH"
echo -e "${GREEN}✓ PATH에 APP_TOOLS_FOLDER와 OMA_BASE_DIR/bin이 추가되었습니다.${NC}"

echo -e "${GREEN}✓ 환경 변수가 현재 셸 세션에 설정되었습니다.${NC}"
echo -e "${BLUE}${BOLD}현재 프로젝트: ${GREEN}$APPLICATION_NAME${NC}"

print_separator
echo -e "${YELLOW}${BOLD}환경 변수 자동 로딩 설정${NC}"
print_separator
echo -e "${CYAN}로그인 시 자동으로 OMA 환경 변수를 로딩하시겠습니까?${NC}"
echo -e "${YELLOW}(쉘 프로필에 source 명령을 추가합니다)${NC}"
echo -ne "${BLUE}${BOLD}자동 로딩 설정 (y/N): ${NC}"
read auto_load

if [[ "$auto_load" =~ ^[Yy]$ ]]; then
    # 사용 중인 쉘 확인
    CURRENT_SHELL=$(basename "$SHELL")
    
    case "$CURRENT_SHELL" in
        "bash")
            PROFILE_FILE="$HOME/.bashrc"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                PROFILE_FILE="$HOME/.bash_profile"
            fi
            ;;
        "zsh")
            PROFILE_FILE="$HOME/.zshrc"
            ;;
        *)
            PROFILE_FILE="$HOME/.profile"
            ;;
    esac
    
    # 현재 디렉토리의 절대 경로
    CURRENT_DIR="$(pwd)"
    SOURCE_LINE="source \"$CURRENT_DIR/$ENV_FILE\""
    
    # 이미 추가되어 있는지 확인
    if grep -q "$SOURCE_LINE" "$PROFILE_FILE" 2>/dev/null; then
        echo -e "${YELLOW}이미 프로필에 설정되어 있습니다: $PROFILE_FILE${NC}"
    else
        # 프로필 파일에 추가
        echo "" >> "$PROFILE_FILE"
        echo "# OMA 환경 변수 자동 로딩 ($(date))" >> "$PROFILE_FILE"
        echo "$SOURCE_LINE" >> "$PROFILE_FILE"
        
        echo -e "${GREEN}✓ 프로필에 자동 로딩 설정 추가: $PROFILE_FILE${NC}"
        echo -e "${CYAN}다음 로그인부터 자동으로 OMA 환경 변수가 로딩됩니다.${NC}"
        
        # 현재 세션에서 바로 적용할지 확인
        echo -ne "${BLUE}현재 세션에서 바로 적용하시겠습니까? (Y/n): ${NC}"
        read apply_now
        if [[ ! "$apply_now" =~ ^[Nn]$ ]]; then
            source "$PROFILE_FILE"
            echo -e "${GREEN}✓ 현재 세션에 적용되었습니다.${NC}"
        fi
    fi
else
    echo -e "${CYAN}자동 로딩 설정을 건너뜁니다.${NC}"
fi

print_separator
echo -e "${YELLOW}${BOLD}사용 방법:${NC}"
echo -e "${CYAN}${BOLD}bin 디렉토리에서:${NC}"
echo -e "${CYAN}1. 환경 변수 확인: ${BOLD}./checkEnv.sh${NC}"
echo -e "${CYAN}2. 프로젝트 디렉토리 이동: ${BOLD}# 각 디렉토리에서 필요한 작업 수행${NC}"
echo -e "${CYAN}3. 수동으로 환경 변수 로드: ${BOLD}source $ENV_FILE${NC}"
echo -e "${CYAN}${BOLD}프로젝트 디렉토리($APPLICATION_NAME)에서:${NC}"
echo -e "${CYAN}1. 환경 변수 로드: ${BOLD}source ./oma_env_${APPLICATION_NAME}.sh${NC}"
echo -e "${CYAN}2. 환경 변수 확인: ${BOLD}./checkEnv.sh${NC}"
echo -e "${CYAN}3. 프로젝트 디렉토리 이동: ${BOLD}# 각 디렉토리에서 필요한 작업 수행${NC}"
if [[ "$auto_load" =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}4. 자동 로딩 제거: 프로필 파일($PROFILE_FILE)에서 해당 라인 삭제${NC}"
fi
print_separator

echo -e "${YELLOW}환경 변수 파일 위치:${NC}"
echo -e "${GREEN}  - bin 디렉토리: $ENV_FILE${NC}"
echo -e "${GREEN}  - 프로젝트 루트: $PROJECT_ENV_FILE${NC}"
echo -e "${CYAN}프로젝트 디렉토리로 이동하여 독립적으로 작업할 수 있습니다.${NC}"