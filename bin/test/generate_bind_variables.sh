#!/bin/bash

# =============================================================================
# SqlPlusBindVariableGenerator 실행 스크립트
# Oracle DB 메타데이터 기반 지능형 바인드 변수 생성기
# =============================================================================

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 스크립트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}===============================================================================${NC}"
echo -e "${CYAN}🤖 Oracle DB 기반 지능형 바인드 변수 생성기${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""

# 환경 확인
echo -e "${BLUE}📋 환경 확인...${NC}"

# Java 확인
if ! command -v java &> /dev/null; then
    echo -e "${RED}❌ Java가 설치되지 않았습니다.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Java: $(java -version 2>&1 | head -n 1)${NC}"

# Oracle 환경변수 확인
if [[ -z "$ORACLE_HOST" || -z "$ORACLE_SVC_USER" || -z "$ORACLE_SVC_PASSWORD" ]]; then
    echo -e "${RED}❌ Oracle 환경변수가 설정되지 않았습니다.${NC}"
    echo -e "${YELLOW}필요한 환경변수:${NC}"
    echo "  - ORACLE_HOST"
    echo "  - ORACLE_PORT (기본값: 1521)"
    echo "  - ORACLE_SVC_USER"
    echo "  - ORACLE_SVC_PASSWORD"
    echo "  - ORACLE_SID"
    exit 1
fi
echo -e "${GREEN}✓ Oracle 환경변수 설정됨${NC}"

# 라이브러리 확인
if [[ ! -f "lib/ojdbc8-21.9.0.0.jar" ]]; then
    echo -e "${RED}❌ Oracle JDBC 드라이버가 없습니다: lib/ojdbc8-21.9.0.0.jar${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Oracle JDBC 드라이버 확인${NC}"

# 클래스 파일 확인
if [[ ! -f "com/test/mybatis/SqlPlusBindVariableGenerator.class" ]]; then
    echo -e "${YELLOW}⚠️  클래스 파일이 없습니다. 컴파일을 시작합니다...${NC}"
    javac -cp ".:lib/*" com/test/mybatis/*.java
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ 컴파일 실패${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ 컴파일 완료${NC}"
else
    echo -e "${GREEN}✓ 클래스 파일 확인${NC}"
fi

echo ""

# Q Chat 설정
echo -e "${BLUE}🤖 Q Chat 설정${NC}"
Q_CHAT_TIMEOUT=${Q_CHAT_TIMEOUT:-10}
echo -e "${GREEN}✓ Q Chat 타임아웃: ${Q_CHAT_TIMEOUT}초${NC}"

# q 명령어 확인
if command -v q &> /dev/null; then
    echo -e "${GREEN}✓ Q Chat 사용 가능${NC}"
else
    echo -e "${YELLOW}⚠️  Q Chat 명령어를 찾을 수 없습니다. Fallback 모드로 실행됩니다.${NC}"
fi

echo ""

# 기존 결과 파일 정리
echo -e "${BLUE}🧹 기존 결과 파일 정리...${NC}"
if [[ -f "parameters.properties" ]]; then
    mv parameters.properties "parameters.properties.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓ 기존 parameters.properties 백업됨${NC}"
fi

# 출력 디렉토리 생성
mkdir -p out
echo -e "${GREEN}✓ 출력 디렉토리 준비 완료${NC}"

echo ""
echo -e "${PURPLE}===============================================================================${NC}"
echo -e "${PURPLE}🚀 바인드 변수 생성기 실행 시작${NC}"
echo -e "${PURPLE}===============================================================================${NC}"
echo ""

# 실행 시간 측정 시작
START_TIME=$(date +%s)

# SqlPlusBindVariableGenerator 실행
export Q_CHAT_TIMEOUT
java -cp ".:lib/*" com.test.mybatis.SqlPlusBindVariableGenerator

EXIT_CODE=$?

# 실행 시간 계산
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${PURPLE}===============================================================================${NC}"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}🎉 바인드 변수 생성기 실행 완료!${NC}"
    echo ""
    
    # 결과 파일 확인
    echo -e "${BLUE}📄 생성된 파일:${NC}"
    
    if [[ -f "parameters.properties" ]]; then
        PARAM_COUNT=$(grep -c "^[^#].*=" parameters.properties 2>/dev/null || echo "0")
        echo -e "${GREEN}✓ parameters.properties (${PARAM_COUNT}개 변수)${NC}"
        
        # 파일 미리보기
        echo ""
        echo -e "${CYAN}📋 parameters.properties 미리보기:${NC}"
        echo -e "${YELLOW}$(head -20 parameters.properties)${NC}"
        if [[ $(wc -l < parameters.properties) -gt 20 ]]; then
            echo -e "${YELLOW}... (총 $(wc -l < parameters.properties)줄)${NC}"
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
    echo -e "${YELLOW}1. parameters.properties 파일을 확인하고 필요시 값을 수정하세요${NC}"
    echo -e "${YELLOW}2. MyBatis 테스트를 실행하세요:${NC}"
    echo -e "${YELLOW}   ./run_oracle.sh ~/workspace/src-orcl/src/main/resources/sqlmap/mapper/ --json${NC}"
    
else
    echo -e "${RED}❌ 바인드 변수 생성기 실행 실패 (종료 코드: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}로그를 확인하여 문제를 해결하세요.${NC}"
fi

echo -e "${PURPLE}===============================================================================${NC}"

exit $EXIT_CODE
