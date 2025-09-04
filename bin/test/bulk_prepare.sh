#!/bin/bash

# MyBatis 벌크 파라미터 추출 스크립트 (DB 샘플 값 수집 포함)
# 사용법: ./bulk_prepare.sh <디렉토리경로>

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 도움말 함수
show_help() {
    echo -e "${BLUE}MyBatis 벌크 파라미터 추출 스크립트 (DB 샘플 값 수집)${NC}"
    echo ""
    echo "사용법:"
    echo "  $0 <디렉토리경로>"
    echo ""
    echo "예시:"
    echo "  $0 /home/ec2-user/workspace/src-orcl/src/main/resources/sqlmap/mapper"
    echo ""
    echo "설명:"
    echo "  - 지정된 디렉토리의 모든 XML 파일을 재귀적으로 검색"
    echo "  - 모든 파라미터를 자동 추출하여 통합 parameters.properties 생성"
    echo "  - Oracle DB에서 실제 샘플 값을 자동 수집 (YYYY-MM-DD 날짜 포맷)"
    echo "  - 중복 파라미터 자동 제거 및 알파벳순 정렬"
    echo ""
    echo "환경변수 요구사항:"
    echo "  - ORACLE_SVC_USER: Oracle 사용자명"
    echo "  - ORACLE_SVC_PASSWORD: Oracle 비밀번호"
    echo "  - ORACLE_SVC_CONNECT_STRING: Oracle 연결 문자열"
    echo ""
    echo "기능:"
    echo "  🎯 실제 데이터 기반 샘플 값 생성"
    echo "  🤖 파라미터-컬럼명 자동 매칭"
    echo "  📊 높은 정확도의 테스트 데이터"
    echo "  ⚡ 수동 작업 50-70% 절약"
    echo ""
}

# 파라미터 검증
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

MAPPER_DIR="$1"

# 디렉토리 존재 확인
if [ ! -d "$MAPPER_DIR" ]; then
    echo -e "${RED}오류: 디렉토리가 존재하지 않습니다: $MAPPER_DIR${NC}"
    exit 1
fi

# 현재 디렉토리 확인
CURRENT_DIR=$(pwd)
if [ ! -f "$CURRENT_DIR/lib/mybatis-3.5.13.jar" ]; then
    echo -e "${RED}오류: lib/mybatis-3.5.13.jar 파일이 없습니다.${NC}"
    echo -e "${YELLOW}현재 디렉토리: $CURRENT_DIR${NC}"
    exit 1
fi

# Oracle JDBC 드라이버 확인
if [ ! -f "$CURRENT_DIR/lib/ojdbc8-21.9.0.0.jar" ]; then
    echo -e "${RED}오류: lib/ojdbc8-21.9.0.0.jar 파일이 없습니다.${NC}"
    exit 1
fi

# Java 클래스 파일 확인
if [ ! -f "$CURRENT_DIR/com/test/mybatis/MyBatisBulkPreparator.class" ]; then
    echo -e "${YELLOW}Java 클래스 파일이 없습니다. 컴파일을 시도합니다...${NC}"
    
    if [ ! -f "$CURRENT_DIR/com/test/mybatis/MyBatisBulkPreparator.java" ]; then
        echo -e "${RED}오류: MyBatisBulkPreparator.java 파일이 없습니다.${NC}"
        exit 1
    fi
    
    javac -cp ".:lib/*" com/test/mybatis/*.java
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}오류: 컴파일에 실패했습니다.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}컴파일 완료${NC}"
fi

# Oracle 환경변수 확인
echo -e "${BLUE}=== Oracle 환경변수 확인 ===${NC}"
if [ -z "$ORACLE_SVC_USER" ]; then
    echo -e "${RED}경고: ORACLE_SVC_USER 환경변수가 설정되지 않았습니다.${NC}"
    echo -e "${YELLOW}DB 샘플 값 수집 없이 기본 파라미터 추출만 수행됩니다.${NC}"
    DB_MODE=""
else
    echo -e "${GREEN}Oracle 사용자: $ORACLE_SVC_USER${NC}"
    if [ -n "$ORACLE_SVC_CONNECT_STRING" ]; then
        echo -e "${GREEN}Oracle 연결: $ORACLE_SVC_CONNECT_STRING${NC}"
    fi
    DB_MODE="--db oracle --date-format YYYY-MM-DD"
fi

echo -e "${BLUE}=== MyBatis 벌크 파라미터 추출 + DB 샘플 값 수집 시작 ===${NC}"
echo -e "검색 디렉토리: ${YELLOW}$MAPPER_DIR${NC}"
if [ -n "$DB_MODE" ]; then
    echo -e "DB 모드: ${GREEN}Oracle (YYYY-MM-DD 날짜 포맷)${NC}"
else
    echo -e "DB 모드: ${YELLOW}비활성화 (파라미터만 추출)${NC}"
fi
echo ""

# 기존 파라미터 파일 백업
if [ -f "$TEST_FOLDER/parameters.properties" ]; then
    BACKUP_FILE="$TEST_FOLDER/parameters.properties.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$TEST_FOLDER/parameters.properties" "$BACKUP_FILE"
    echo -e "${YELLOW}기존 파라미터 파일을 백업했습니다: $BACKUP_FILE${NC}"
fi

# 벌크 준비 프로그램 실행
echo -e "${GREEN}파라미터 추출 및 DB 샘플 값 수집 중...${NC}"
if [ -n "$DB_MODE" ]; then
    java -cp ".:lib/*" com.test.mybatis.MyBatisBulkPreparator "$MAPPER_DIR" $DB_MODE
else
    java -cp ".:lib/*" com.test.mybatis.MyBatisBulkPreparator "$MAPPER_DIR"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== 파라미터 추출 완료 ===${NC}"
    
    if [ -f "$TEST_FOLDER/parameters.properties" ]; then
        PARAM_COUNT=$(grep -c "^[^#].*=" "$TEST_FOLDER/parameters.properties" 2>/dev/null | tr -d '\n' || echo "0")
        SAMPLE_COUNT=$(grep -c "# 소스:" "$TEST_FOLDER/parameters.properties" 2>/dev/null | tr -d '\n' || echo "0")
        
        # Ensure variables are numeric
        if ! [[ "$PARAM_COUNT" =~ ^[0-9]+$ ]]; then
            PARAM_COUNT=0
        fi
        if ! [[ "$SAMPLE_COUNT" =~ ^[0-9]+$ ]]; then
            SAMPLE_COUNT=0
        fi
        
        MANUAL_COUNT=$((PARAM_COUNT - SAMPLE_COUNT))
        
        echo -e "생성된 파일: ${YELLOW}$TEST_FOLDER/parameters.properties${NC}"
        echo -e "총 파라미터: ${YELLOW}$PARAM_COUNT개${NC}"
        
        if [ -n "$DB_MODE" ] && [ $SAMPLE_COUNT -gt 0 ]; then
            if [ $PARAM_COUNT -gt 0 ]; then
                SAMPLE_RATE=$(awk "BEGIN {printf \"%.1f\", $SAMPLE_COUNT * 100 / $PARAM_COUNT}")
            else
                SAMPLE_RATE="0.0"
            fi
            echo -e "DB 샘플 값: ${GREEN}$SAMPLE_COUNT개 (${SAMPLE_RATE}%)${NC}"
            echo -e "수동 설정 필요: ${YELLOW}$MANUAL_COUNT개${NC}"
            echo ""
            echo -e "${GREEN}🎯 실제 운영 데이터 기반 샘플 값이 자동 설정되었습니다!${NC}"
        fi
        
        echo ""
        echo -e "${BLUE}다음 단계:${NC}"
        echo -e "1. ${YELLOW}$TEST_FOLDER/parameters.properties${NC} 파일을 확인하고 필요시 수정하세요"
        echo -e "2. ${YELLOW}./bulk_execute.sh${NC} 또는 ${YELLOW}./bulk_json.sh${NC}로 실행하세요"
        echo ""
        echo -e "${GREEN}파라미터 파일 미리보기 (처음 15줄):${NC}"
        head -15 "$TEST_FOLDER/parameters.properties"
        
        if [ $PARAM_COUNT -gt 15 ]; then
            echo -e "${BLUE}... (총 $PARAM_COUNT개 파라미터)${NC}"
        fi
    else
        echo -e "${RED}오류: $TEST_FOLDER/parameters.properties 파일이 생성되지 않았습니다.${NC}"
        exit 1
    fi
else
    echo -e "${RED}오류: 파라미터 추출에 실패했습니다.${NC}"
    exit 1
fi
