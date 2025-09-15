#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# LOG_DIR 환경변수 확인
if [ -z "$LOG_DIR" ]; then
    echo -e "${RED}Error: LOG_DIR 환경변수가 설정되지 않았습니다.${NC}"
    echo "사용법: export LOG_DIR=/path/to/logs && ./error_extractor.sh <파일명>"
    echo "예시: ./error_extractor.sh catalina.out"
    echo "      ./error_extractor.sh catalina.out.20250813_104748"
    exit 1
fi

# 파일명 인자 확인
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: 로그 파일명을 지정해주세요.${NC}"
    echo "사용법: ./error_extractor.sh <파일명>"
    echo "예시: ./error_extractor.sh catalina.out"
    echo "      ./error_extractor.sh catalina.out.20250813_104748"
    exit 1
fi

# 로그 파일 경로 설정
LOG_FILE="$LOG_DIR/$1"

# 로그 파일 존재 확인
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}Error: $LOG_FILE 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# 현재 날짜시간으로 백업 파일명 생성
BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${LOG_FILE}_${BACKUP_TIMESTAMP}"

echo -e "${BLUE}=== 로그 파일 에러 추출기 (매퍼명 추출) ===${NC}"
echo -e "${YELLOW}원본 파일: $LOG_FILE${NC}"
echo -e "${YELLOW}백업 파일: $BACKUP_FILE${NC}"
echo ""

# 로그 파일 백업
echo -e "${GREEN}1. 로그 파일을 백업 중...${NC}"
if cp "$LOG_FILE" "$BACKUP_FILE"; then
    echo -e "${GREEN}   ✓ 백업 완료: $BACKUP_FILE${NC}"
else
    echo -e "${RED}   ✗ 백업 실패${NC}"
    exit 1
fi

# 결과 파일 초기화
RESULT_FILE="result.$1.txt"
TEMP_RESULT_FILE="temp_result.txt"
TEMP_UNIQUE_FILE="temp_unique.txt"
> "$TEMP_RESULT_FILE"

echo -e "${GREEN}2. 데이터베이스 에러를 추출 중...${NC}"

# 매퍼명에서 파일명 추출 함수
extract_mapper_name() {
    local mapper_full="$1"

    # amzn.com.dao.mapper.
    if [[ "$mapper_full" =~ amzn\.[^.]+\.dao\.mapper\.([^.]+)Mapper ]]; then
        echo "${BASH_REMATCH[1]}Mapper"
    elif [[ "$mapper_full" =~ ([^.]+Mapper) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}

# 에러 번호 카운터
error_count=0

# 임시 파일들
temp_error_blocks="/tmp/error_blocks_$$.tmp"

# 다양한 에러 패턴 찾기
grep -n "^### \(Error \(querying\|updating\) database\|Cause:.*SQL.*Exception\)" "$LOG_FILE" > "$temp_error_blocks"

# 추가로 독립적인 SQLException 패턴도 찾기
grep -n "SQLException:" "$LOG_FILE" | grep -v "^###" | while IFS=':' read -r line_num rest; do
    echo "$line_num:SQLException: $rest" >> "$temp_error_blocks"
done

# 정렬해서 중복 제거
sort -n -t: -k1 "$temp_error_blocks" | uniq > "${temp_error_blocks}.sorted"
mv "${temp_error_blocks}.sorted" "$temp_error_blocks"

# 디버깅: 찾은 에러 라인 수 확인
error_lines_found=$(wc -l < "$temp_error_blocks")
echo -e "   ${YELLOW}발견된 에러 블록 수: $error_lines_found${NC}"

if [ "$error_lines_found" -eq 0 ]; then
    echo -e "   ${RED}SQL 에러 패턴을 찾을 수 없습니다${NC}"
    echo -e "   ${YELLOW}파일 내용 샘플:${NC}"
    head -5 "$LOG_FILE" | sed 's/^/     /'
fi

while IFS=':' read -r line_num rest; do
    error_count=$((error_count + 1))

    echo -e "   ${BLUE}에러 #$error_count 처리 중... (라인: $line_num)${NC}"

    # 변수 초기화
    file_path=""
    sql_id=""
    error_msg=""
    sql_query=""
    mapper_full=""

    # 다음 에러 블록의 시작 라인 찾기
    next_error_line=""
    if [ -s "$temp_error_blocks" ]; then
        next_error_line=$(awk -F: -v current="$line_num" '$1 > current {print $1; exit}' "$temp_error_blocks")
    fi

    # 읽을 라인 수 계산
    if [ -n "$next_error_line" ]; then
        lines_to_read=$((next_error_line - line_num))
        if [ $lines_to_read -gt 100 ]; then
            lines_to_read=100
        fi
    else
        lines_to_read=100
    fi

    # 현재 에러 블록 전체 추출
    start_line=$((line_num - 5))
    if [ $start_line -lt 1 ]; then
        start_line=1
    fi
    total_lines=$((lines_to_read + 10))

    error_block=$(tail -n +$start_line "$LOG_FILE" | head -n $total_lines)

    echo -e "   ${YELLOW}에러 블록 분석 중... (라인 $start_line ~ $((start_line + total_lines - 1)))${NC}"

    # 에러 블록에서 정보 추출
    while IFS= read -r line; do
        # ### 패턴에서 에러 메시지 추출
        if [[ "$line" =~ ^###\ Error\ querying\ database\..*Cause:\ (.+)$ ]]; then
            error_msg="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}에러 메시지 발견 (querying): ${error_msg:0:80}...${NC}"
        elif [[ "$line" =~ ^###\ Error\ updating\ database\..*Cause:\ (.+)$ ]]; then
            error_msg="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}에러 메시지 발견 (updating): ${error_msg:0:80}...${NC}"
        elif [[ "$line" =~ ^###\ Cause:\ (.+)$ ]]; then
            error_msg="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}에러 메시지 발견 (Cause): ${error_msg:0:80}...${NC}"
        elif [[ "$line" =~ SQLException:\ (.+)$ ]]; then
            # 독립적인 SQLException 패턴
            error_msg="SQLException: ${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}에러 메시지 발견 (SQLException): ${error_msg:0:80}...${NC}"
        fi

        # 파일 경로 추출
        if [[ "$line" =~ ^###\ The\ error\ may\ exist\ in\ file\ \[([^\]]+)\] ]]; then
            file_path="${BASH_REMATCH[1]}"
            echo -e "   ${GREEN}파일 경로 발견: $file_path${NC}"
        fi

        # SQL ID 추출 및 매퍼명 저장
        if [[ "$line" =~ ^###\ The\ error\ may\ involve\ (.+)$ ]]; then
            sql_id_full="${BASH_REMATCH[1]}"
            mapper_full="$sql_id_full"

            # -Inline 제거
            sql_id_full="${sql_id_full%-Inline}"
            # 마지막 점 이후만 추출
            sql_id="${sql_id_full##*.}"
            echo -e "   ${GREEN}SQL ID 발견: $sql_id${NC}"
            echo -e "   ${BLUE}매퍼 전체명: $mapper_full${NC}"
        fi

        # SQL 쿼리 추출
        if [[ "$line" =~ ^###\ SQL:(.*)$ ]]; then
            sql_content="${BASH_REMATCH[1]}"
            # SQL: 다음에 내용이 있으면 사용
            if [[ -n "$sql_content" && "$sql_content" != " " ]]; then
                sql_query="$sql_content"
                echo -e "   ${GREEN}SQL 쿼리 발견: ${sql_query:0:80}...${NC}"
            else
                # ### SQL: 다음 라인에서 SQL 찾기
                sql_found_flag=true
            fi
        elif [[ "$sql_found_flag" == true && -n "$line" && ! "$line" =~ ^### ]]; then
            # ### SQL: 다음 라인에서 실제 SQL 추출
            sql_query="$line"
            sql_found_flag=false
            echo -e "   ${GREEN}SQL 쿼리 발견: ${sql_query:0:80}...${NC}"
        fi

        # INSERT/UPDATE/DELETE 문에서 SQL ID 추출 시도
        if [[ -z "$sql_id" && "$line" =~ (INSERT|UPDATE|DELETE).*INTO.*TB_[A-Z_0-9]+ ]]; then
            # 테이블명에서 SQL ID 유추
            if [[ "$line" =~ TB_([A-Z_0-9]+) ]]; then
                table_name="${BASH_REMATCH[1]}"
                sql_id="insert"  # 기본값
                echo -e "   ${YELLOW}테이블명에서 SQL ID 유추: $sql_id (테이블: TB_$table_name)${NC}"
            fi
        fi

        # Java 스택 트레이스가 시작되면 중단
        if [[ "$line" =~ (\tat\ |Caused\ by:.*Exception) ]]; then
            echo -e "   ${YELLOW}Java 스택 트레이스 감지, 추가 파싱 중단${NC}"
            break
        fi

    done <<< "$error_block"

    # 파일 경로가 비어있고 매퍼명이 있으면 매퍼명을 파일명으로 사용
    if [[ -z "$file_path" && -n "$mapper_full" ]]; then
        mapper_name=$(extract_mapper_name "$mapper_full")
        if [[ -n "$mapper_name" ]]; then
            file_path="$mapper_name"
            echo -e "   ${CYAN}매퍼명에서 파일명 추출: $file_path${NC}"
        fi
    fi

    # 필수 정보가 있는 경우만 임시 결과 파일에 출력
    if [[ -n "$error_msg" ]]; then
        {
            echo "번호 [$error_count]"
            echo "파일: $file_path"
            echo "sqlid: $sql_id"
            echo "에러: $error_msg"
            echo "SQL: $sql_query"
            echo ""
        } >> "$TEMP_RESULT_FILE"
        echo -e "   ${GREEN}✓ 에러 #$error_count 추출 완료${NC}"
        echo -e "     파일: ${file_path:0:50}..."
        echo -e "     SQL ID: $sql_id"
        echo -e "     SQL: ${sql_query:0:50}..."
    else
        echo -e "   ${RED}✗ 에러 #$error_count: 에러 메시지를 찾을 수 없음, 건너뜀${NC}"
        error_count=$((error_count - 1))  # 카운터 되돌리기
    fi

    echo ""

done < "$temp_error_blocks"

echo -e "${GREEN}3. 중복 에러 제거 중 (개선된 로직)...${NC}"

# 에러 정규화 함수
normalize_error() {
    local error="$1"
    # SQLException 타입과 주요 키워드만 추출
    if [[ "$error" =~ (SQLIntegrityConstraintViolationException|SQLSyntaxErrorException|SQLException) ]]; then
        error_type="${BASH_REMATCH[1]}"

        # 주요 에러 패턴 추출
        if [[ "$error" =~ Duplicate\ entry.*for\ key ]]; then
            echo "${error_type}:Duplicate_entry"
        elif [[ "$error" =~ You\ have\ an\ error\ in\ your\ SQL\ syntax.*near ]]; then
            echo "${error_type}:SQL_syntax_error"
        elif [[ "$error" =~ Unknown\ column.*in ]]; then
            echo "${error_type}:Unknown_column"
        else
            # 처음 50자만 사용
            echo "${error_type}:${error:0:50}"
        fi
    else
        # 처음 50자만 사용
        echo "${error:0:50}"
    fi
}

# 중복 제거를 위한 임시 파일
> "$TEMP_UNIQUE_FILE"

# 중복 체크를 위한 해시 저장
declare -A seen_errors
declare -A error_counts
unique_count=0

# 임시 결과 파일을 6줄씩 읽어서 처리 (번호, 파일, sqlid, 에러, SQL, 빈줄)
while IFS= read -r line1 && IFS= read -r line2 && IFS= read -r line3 && IFS= read -r line4 && IFS= read -r line5 && IFS= read -r line6; do
    # 각 라인에서 값 추출
    current_file=$(echo "$line2" | sed 's/^파일: //')
    current_sqlid=$(echo "$line3" | sed 's/^sqlid: //')
    current_error=$(echo "$line4" | sed 's/^에러: //')
    current_sql=$(echo "$line5" | sed 's/^SQL: //')

    # 에러 정규화
    normalized_error=$(normalize_error "$current_error")

    # 중복 체크를 위한 키 생성 (파일, sqlid, 정규화된 에러로 구성)
    check_key="${current_file}|||${current_sqlid}|||${normalized_error}"

    # 중복 개수 카운트
    count_key="${normalized_error}|||${current_sqlid}"
    error_counts[$count_key]=$((${error_counts[$count_key]} + 1))

    echo -e "   ${BLUE}처리 중: ${current_error:0:60}...${NC}"
    echo -e "   ${YELLOW}정규화: $normalized_error${NC}"

    # 중복 체크
    if [[ -z "${seen_errors[$check_key]}" ]]; then
        # 새로운 에러 - 추가
        unique_count=$((unique_count + 1))
        seen_errors[$check_key]=1

        {
            echo "번호 [$unique_count]"
            echo "파일: $current_file"
            echo "sqlid: $current_sqlid"
            echo "에러: $current_error"
            echo "SQL: $current_sql"
            echo ""
        } >> "$TEMP_UNIQUE_FILE"

        echo -e "   ${GREEN}✓ 고유 에러 #$unique_count 추가${NC}"
    else
        echo -e "   ${YELLOW}✗ 중복 에러 건너뜀${NC}"
    fi

done < "$TEMP_RESULT_FILE"

# 중복 개수를 sqlid에 추가
echo -e "${GREEN}4. 중복 개수 정보 추가 중...${NC}"
TEMP_FINAL_FILE="temp_final.txt"
> "$TEMP_FINAL_FILE"

while IFS= read -r line1 && IFS= read -r line2 && IFS= read -r line3 && IFS= read -r line4 && IFS= read -r line5 && IFS= read -r line6; do
    current_file=$(echo "$line2" | sed 's/^파일: //')
    current_sqlid=$(echo "$line3" | sed 's/^sqlid: //')
    current_error=$(echo "$line4" | sed 's/^에러: //')
    current_sql=$(echo "$line5" | sed 's/^SQL: //')

    # 정규화된 에러로 중복 개수 찾기
    normalized_error=$(normalize_error "$current_error")
    count_key="${normalized_error}|||${current_sqlid}"
    duplicate_count=${error_counts[$count_key]}

    {
        echo "$line1"
        echo "$line2"
        echo "sqlid: $current_sqlid ($duplicate_count건)"
        echo "$line4"
        echo "$line5"
        echo ""
    } >> "$TEMP_FINAL_FILE"

done < "$TEMP_UNIQUE_FILE"

# 최종 결과 파일에 저장
cp "$TEMP_FINAL_FILE" "$RESULT_FILE"

echo -e "${GREEN}   ✓ 총 ${error_count}개 에러 중 ${unique_count}개 고유 에러, $((error_count - unique_count))개 중복 제거${NC}"

# 로그 파일 초기화
echo -e "${GREEN}5. 로그 파일 초기화 중...${NC}"
if > "$LOG_FILE"; then
    echo -e "${GREEN}   ✓ 로그 파일이 초기화되었습니다${NC}"
else
    echo -e "${RED}   ✗ 로그 파일 초기화 실패${NC}"
fi

# 임시 파일 정리
rm -f "$temp_error_blocks" "$TEMP_RESULT_FILE" "$TEMP_UNIQUE_FILE" "$TEMP_FINAL_FILE"

echo ""
echo -e "${BLUE}=== 작업 완료 ===${NC}"
echo -e "${GREEN}✓ 백업 파일: $BACKUP_FILE${NC}"
echo -e "${GREEN}✓ 결과 파일: $RESULT_FILE (${unique_count}개 고유 에러)${NC}"
echo -e "${GREEN}✓ 원본 파일: $LOG_FILE (초기화됨)${NC}"
echo -e "${BLUE}✓ 중복 제거: $((error_count - unique_count))개 중복 에러 제거됨${NC}"
echo ""

if [ "$unique_count" -gt 0 ]; then
    echo -e "${YELLOW}다음 단계: ./error_fix.sh 를 실행하여 에러를 수정하세요.${NC}"
else
    echo -e "${BLUE}발견된 데이터베이스 에러가 없습니다.${NC}"
fi