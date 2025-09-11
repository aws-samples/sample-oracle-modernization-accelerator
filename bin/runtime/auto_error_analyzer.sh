#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== 자동 에러 분석기 ===${NC}"

# ERROR_LOG_FILE 환경변수 확인
if [ -z "$ERROR_LOG_FILE" ]; then
    echo -e "${RED}Error: ERROR_LOG_FILE 환경변수가 설정되지 않았습니다.${NC}"
    echo "사용법: export ERROR_LOG_FILE=/path/to/error.log && ./auto_error_analyzer.sh"
    exit 1
fi

# 로그 파일 존재 확인
if [ ! -f "$ERROR_LOG_FILE" ]; then
    echo -e "${RED}Error: $ERROR_LOG_FILE 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}1. 에러 로그 파일에서 패턴 추출 중: $ERROR_LOG_FILE${NC}"

# 임시 파일
ALL_PATTERNS="/tmp/all_patterns_$$.txt"

# 모든 에러 패턴 추출 (Error, Exception, Failed 등) - 드라이버/연결 에러 제외
grep -n -E "(Error|Exception|Failed|FATAL)" "$ERROR_LOG_FILE" | \
grep -v -i -E "(driver|connection|jdbc|network|timeout|refused|host|port|database.*url)" | \
head -50 > "$ALL_PATTERNS"

pattern_count=$(wc -l < "$ALL_PATTERNS")
echo -e "${YELLOW}   추출된 패턴: ${pattern_count}건${NC}"

if [ "$pattern_count" -eq 0 ]; then
    echo -e "${BLUE}추출할 에러 패턴이 없습니다.${NC}"
    rm -f "$ALL_PATTERNS"
    exit 0
fi

# Q Chat 요청 메시지 생성
echo -e "${GREEN}2. Q Chat 요청 메시지 생성 중...${NC}"

CHAT_REQUEST="/tmp/chat_request_$$.txt"

cat > "$CHAT_REQUEST" << 'EOF'
**반드시 한글로만 대답해! 영어 사용 절대 금지!**
다음은 로그 파일에서 추출한 에러 패턴들이야:
**!!!!! 절대 금지 !!!!!**
다음 키워드가 포함된 에러는 절대로 분석하지 말고 무시:
- JDBC, Driver, Connection, PostgreSQL, MySQL
- Host, Port, Database, URL, Network
- Timeout, Refused, Connect, Socket
- 환경변수, ${PGHOST}, ${PGPORT}, ${PGDATABASE}

**허용되는 에러만 분석:**
- SQL 문법 에러 (Syntax Error)  
- 제약조건 위반 (Constraint Violation)
- 화면/UI 에러
- 비즈니스 로직 에러

**작업:**
다음에 나오는 에러 메시지를 분석해서 error_extractor.sh 해당 에러를 추출하여 파일에 로깅할 수 있도록 에러 추출 로직을 추가!

EOF

cat "$ALL_PATTERNS" >> "$CHAT_REQUEST"

cat >> "$CHAT_REQUEST" << 'EOF'

EOF

echo -e "${GREEN}3. Q Chat 실행 중...${NC}"
echo -e "${BLUE}요청 내용 미리보기:${NC}"
echo "----------------------------------------"
head -10 "$CHAT_REQUEST"
echo "... (총 $(($(wc -l < "$CHAT_REQUEST")))줄)"
echo "----------------------------------------"

# Q Chat 실행
q chat < "$CHAT_REQUEST"

# 임시 파일 정리
rm -f "$ALL_PATTERNS" "$CHAT_REQUEST"

echo -e "${GREEN}=== 완료 ===${NC}"