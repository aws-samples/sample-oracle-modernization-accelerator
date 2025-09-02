#!/bin/bash

# PostgreSQL 메타데이터 추출 스크립트
# AI 대신 직접 SQL 쿼리로 메타데이터 추출

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}PostgreSQL 메타데이터 추출을 시작합니다...${NC}"

# 환경 변수 확인
if [ -z "$APP_TRANSFORM_FOLDER" ]; then
    echo -e "${RED}오류: APP_TRANSFORM_FOLDER 환경 변수가 설정되지 않았습니다.${NC}"
    exit 1
fi

# 출력 파일 경로
OUTPUT_FILE="$APP_TRANSFORM_FOLDER/oma_metadata.txt"

echo -e "${YELLOW}출력 파일: $OUTPUT_FILE${NC}"

# PostgreSQL 연결 확인
echo -e "${BLUE}PostgreSQL 연결을 확인합니다...${NC}"
if ! psql -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${RED}오류: PostgreSQL 데이터베이스에 연결할 수 없습니다.${NC}"
    echo -e "${YELLOW}다음 환경 변수들이 올바르게 설정되어 있는지 확인하세요:${NC}"
    echo -e "${YELLOW}  - PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD${NC}"
    exit 1
fi

echo -e "${GREEN}PostgreSQL 연결 성공!${NC}"

# 메타데이터 추출 SQL 실행
echo -e "${BLUE}메타데이터를 추출합니다...${NC}"

psql -c "
SELECT 
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema NOT IN (
    'information_schema', 
    'pg_catalog', 
    'pg_toast',
    'aws_commons',
    'aws_oracle_context',
    'aws_oracle_data', 
    'aws_oracle_ext',
    'public'
)
ORDER BY table_schema, table_name, ordinal_position;
" > "$OUTPUT_FILE"

# 실행 결과 확인
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 메타데이터 추출이 완료되었습니다!${NC}"
    
    # 결과 검증
    echo -e "${BLUE}결과 검증:${NC}"
    
    # 파일 존재 확인
    if [ -f "$OUTPUT_FILE" ]; then
        echo -e "${GREEN}  ✓ 파일 생성 확인: $OUTPUT_FILE${NC}"
        
        # 파일 크기 확인
        file_size=$(wc -l < "$OUTPUT_FILE")
        echo -e "${GREEN}  ✓ 총 라인 수: $file_size${NC}"
        
        # 첫 10줄 미리보기
        echo -e "${BLUE}  📋 첫 10줄 미리보기:${NC}"
        head -10 "$OUTPUT_FILE"
        
        echo ""
        
        # 스키마별 통계
        echo -e "${BLUE}  📊 스키마별 테이블/뷰 개수:${NC}"
        grep -v "^-" "$OUTPUT_FILE" | grep -v "table_schema" | awk '{print $1}' | sort | uniq -c | while read count schema; do
            echo -e "${GREEN}    $schema: $count개${NC}"
        done
        
    else
        echo -e "${RED}  ✗ 파일이 생성되지 않았습니다.${NC}"
        exit 1
    fi
    
else
    echo -e "${RED}❌ 메타데이터 추출에 실패했습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 PostgreSQL 메타데이터 추출이 성공적으로 완료되었습니다!${NC}"
