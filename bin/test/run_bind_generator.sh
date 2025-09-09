#!/bin/bash

# =============================================================================
# 바인드 변수 생성기 실행 스크립트
# Oracle 딕셔너리 + 매퍼 바인드 변수 추출 + 매칭
# =============================================================================

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 스크립트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}===============================================================================${NC}"
echo -e "${CYAN}🗄️  Oracle 딕셔너리 기반 바인드 변수 생성기${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""

# 매퍼 디렉토리 확인
MAPPER_DIR="$1"
if [[ -z "$MAPPER_DIR" ]]; then
    MAPPER_DIR="/home/ec2-user/workspace/src-orcl/src/main/resources/sqlmap/mapper"
fi

if [[ ! -d "$MAPPER_DIR" ]]; then
    echo -e "${RED}❌ 매퍼 디렉토리를 찾을 수 없습니다: $MAPPER_DIR${NC}"
    echo -e "${YELLOW}사용법: $0 [매퍼디렉토리]${NC}"
    echo -e "${YELLOW}예시: $0 ~/workspace/src-orcl/src/main/resources/sqlmap/mapper${NC}"
    exit 1
fi

# TEST_FOLDER 설정 (환경변수가 없으면 매퍼 디렉토리 사용)
TEST_FOLDER="${TEST_FOLDER:-$MAPPER_DIR}"

echo -e "${BLUE}📁 매퍼 디렉토리: $MAPPER_DIR${NC}"

# 환경변수 확인
if [[ -z "$ORACLE_HOST" || -z "$ORACLE_SVC_USER" || -z "$ORACLE_SVC_PASSWORD" ]]; then
    echo -e "${RED}❌ Oracle 환경변수가 설정되지 않았습니다.${NC}"
    echo -e "${YELLOW}필요한 환경변수: ORACLE_HOST, ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_SID${NC}"
    exit 1
fi

# 라이브러리 확인
if [[ ! -f "lib/ojdbc8-21.9.0.0.jar" ]]; then
    echo -e "${RED}❌ Oracle JDBC 드라이버가 없습니다: lib/ojdbc8-21.9.0.0.jar${NC}"
    exit 1
fi

# 컴파일 확인
if [[ ! -f "com/test/mybatis/SimpleBindVariableGenerator.class" ]]; then
    echo -e "${YELLOW}⚠️  클래스 파일이 없습니다. 컴파일을 시작합니다...${NC}"
    javac -cp ".:lib/*" com/test/mybatis/SimpleBindVariableGenerator.java
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ 컴파일 실패${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ 컴파일 완료${NC}"
fi

# 기존 결과 파일 백업
if [[ -f "$TEST_FOLDER/parameters.properties" ]]; then
    mv "$TEST_FOLDER/parameters.properties" "$TEST_FOLDER/parameters.properties.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓ 기존 parameters.properties 백업됨${NC}"
fi

# 출력 디렉토리 생성
mkdir -p out

echo ""
echo -e "${CYAN}🚀 바인드 변수 생성기 실행 시작${NC}"
echo ""

# 실행 시간 측정
START_TIME=$(date +%s)

# SimpleBindVariableGenerator 실행
java -cp ".:lib/*" com.test.mybatis.SimpleBindVariableGenerator "$MAPPER_DIR" "$TEST_FOLDER"

EXIT_CODE=$?

# 실행 시간 계산
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${CYAN}===============================================================================${NC}"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}🎉 바인드 변수 생성기 실행 완료!${NC}"
    echo ""
    
    # 결과 파일 확인
    if [[ -f "$TEST_FOLDER/parameters.properties" ]]; then
        TOTAL_VARS=$(grep -c "^[^#].*=" "$TEST_FOLDER/parameters.properties" 2>/dev/null || echo "0")
        MATCHED_VARS=$(grep -B1 "^[^#].*=" "$TEST_FOLDER/parameters.properties" | grep -c "# OMA\." 2>/dev/null || echo "0")
        UNMATCHED_VARS=$((TOTAL_VARS - MATCHED_VARS))
        
        echo -e "${GREEN}✓ parameters.properties 생성됨${NC}"
        echo -e "${BLUE}  - 총 변수: ${TOTAL_VARS}개${NC}"
        echo -e "${BLUE}  - 매칭됨: ${MATCHED_VARS}개${NC}"
        echo -e "${BLUE}  - 매칭 안됨: ${UNMATCHED_VARS}개${NC}"
        
        if [[ $UNMATCHED_VARS -gt 0 ]]; then
            echo ""
            echo -e "${YELLOW}📝 매칭되지 않은 변수들 (파일 하단 확인):${NC}"
            grep -A1 "# 매칭 없음" "$TEST_FOLDER/parameters.properties" | grep "^[^#]" | head -5
            if [[ $UNMATCHED_VARS -gt 5 ]]; then
                echo -e "${YELLOW}... 외 $((UNMATCHED_VARS - 5))개${NC}"
            fi
        fi
        
        echo ""
        echo -e "${CYAN}📋 parameters.properties 미리보기:${NC}"
        echo -e "${YELLOW}$(head -15 "$TEST_FOLDER/parameters.properties")${NC}"
        if [[ $(wc -l < "$TEST_FOLDER/parameters.properties") -gt 15 ]]; then
            echo -e "${YELLOW}... (총 $(wc -l < "$TEST_FOLDER/parameters.properties")줄)${NC}"
        fi
    else
        echo -e "${RED}❌ parameters.properties 파일이 생성되지 않았습니다.${NC}"
    fi
    
    # 딕셔너리 파일 확인
    DICT_FILE=$(ls -t out/oracle_dictionary_*.json 2>/dev/null | head -1)
    if [[ -n "$DICT_FILE" ]]; then
        echo -e "${GREEN}✓ Oracle 딕셔너리: $(basename "$DICT_FILE")${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}⏱️  실행 시간: ${DURATION}초${NC}"
    
    echo ""
    echo -e "${CYAN}📖 다음 단계:${NC}"
    echo -e "${YELLOW}1. parameters.properties 파일에서 '매칭 없음' 변수들의 값을 수정하세요${NC}"
    echo -e "${YELLOW}2. MyBatis 테스트를 실행하세요:${NC}"
    echo -e "${YELLOW}   ./run_oracle.sh $MAPPER_DIR --json${NC}"
    
else
    echo -e "${RED}❌ 바인드 변수 생성기 실행 실패 (종료 코드: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}로그를 확인하여 문제를 해결하세요.${NC}"
fi

echo -e "${CYAN}===============================================================================${NC}"

exit $EXIT_CODE
