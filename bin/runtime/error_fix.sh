#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 도움말 표시 함수
show_help() {
    echo -e "${BLUE}=== SQL 에러 수정 도구 사용법 ===${NC}"
    echo ""
    echo "사용법:"
    echo "  ./error_fix.sh <result파일>           # 일반 모드 (수동 확인 후 삭제)"
    echo "  ./error_fix.sh <result파일> -auto     # 자동 삭제 모드 (수정 후 자동 삭제)"
    echo "  ./error_fix.sh --help                # 도움말 표시"
    echo ""
    echo "예시:"
    echo "  ./error_fix.sh result.txt"
    echo "  ./error_fix.sh result.catalina.out_20250813_093338.txt"
    echo "  ./error_fix.sh result.txt -auto"
    echo ""
    echo "기능:"
    echo "  - 지정된 result 파일의 에러 목록 표시"
    echo "  - 에러 번호 선택"
    echo "  - 자동 프롬프트 생성 및 Q CLI 실행"
    echo "  - 수정 완료 후 해당 에러를 result 파일에서 삭제"
    echo ""
}

# 인자 확인
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

if [ $# -eq 0 ]; then
    echo -e "${RED}Error: result 파일을 지정해주세요.${NC}"
    echo ""
    show_help
    exit 1
fi

# result 파일 경로 설정
RESULT_FILE="$1"

# 자동 삭제 모드 확인
AUTO_DELETE=false
if [[ "$2" == "-auto" || "$2" == "--auto" ]]; then
    AUTO_DELETE=true
    echo -e "${BLUE}자동 삭제 모드가 활성화되었습니다.${NC}"
fi

# result 파일 존재 확인
if [ ! -f "$RESULT_FILE" ]; then
    echo -e "${RED}Error: $RESULT_FILE 파일을 찾을 수 없습니다.${NC}"
    echo "파일 경로를 확인해주세요."
    exit 1
fi

# result 파일이 비어있는지 확인
if [ ! -s "$RESULT_FILE" ]; then
    echo -e "${RED}Error: $RESULT_FILE 파일이 비어있습니다.${NC}"
    exit 1
fi

echo -e "${BLUE}=== SQL 에러 수정 도구 ===${NC}"
echo -e "${YELLOW}대상 파일: $RESULT_FILE${NC}"
echo ""

# 처음 실행할 때 에러 목록 표시
echo -e "${BLUE}=== 데이터베이스 에러 목록 ===${NC}"
echo ""

# result.txt 내용 표시 (SQL은 2줄만)
while IFS= read -r line; do
    if [[ "$line" =~ ^SQL:\ (.+)$ ]]; then
        sql_content="${BASH_REMATCH[1]}"
        # SQL을 2줄로 제한 (첫 번째 줄은 처음 80자, 두 번째 줄은 다음 80자)
        first_line="${sql_content:0:80}"
        second_line="${sql_content:80:80}"

        echo "SQL: $first_line"
        if [ ${#sql_content} -gt 80 ]; then
            echo "     $second_line"
            if [ ${#sql_content} -gt 160 ]; then
                echo "     ..."
            fi
        fi
    else
        echo "$line"
    fi
done < "$RESULT_FILE"

echo -e "${YELLOW}================================${NC}"
echo ""

# 사용자로부터 번호 입력 받기
while true; do
    echo -n "수정할 에러 번호를 입력하세요 (목록 다시 보기: 'list', 종료: 'q'): "
    read -r selected_number

    # 종료 조건
    if [[ "$selected_number" == "q" || "$selected_number" == "Q" ]]; then
        echo "프로그램을 종료합니다."
        exit 0
    fi

    # 전체 목록 다시 보기
    if [[ "$selected_number" == "list" || "$selected_number" == "LIST" ]]; then
        echo -e "${BLUE}=== 데이터베이스 에러 목록 ===${NC}"
        echo ""

        # result.txt 내용 표시 (SQL은 2줄만)
        while IFS= read -r line; do
            if [[ "$line" =~ ^SQL:\ (.+)$ ]]; then
                sql_content="${BASH_REMATCH[1]}"
                # SQL을 2줄로 제한 (첫 번째 줄은 처음 80자, 두 번째 줄은 다음 80자)
                first_line="${sql_content:0:80}"
                second_line="${sql_content:80:80}"

                echo "SQL: $first_line"
                if [ ${#sql_content} -gt 80 ]; then
                    echo "     $second_line"
                    if [ ${#sql_content} -gt 160 ]; then
                        echo "     ..."
                    fi
                fi
            else
                echo "$line"
            fi
        done < "$RESULT_FILE"

        echo -e "${YELLOW}================================${NC}"
        echo ""
        continue
    fi

    # 숫자인지 확인
    if ! [[ "$selected_number" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}올바른 번호를 입력해주세요.${NC}"
        continue
    fi

    # 선택한 번호가 존재하는지 확인
    if ! grep -q "번호 \[$selected_number\]" "$RESULT_FILE"; then
        echo -e "${RED}번호 [$selected_number]를 찾을 수 없습니다.${NC}"
        continue
    fi

    break
done

echo -e "${GREEN}번호 [$selected_number]를 선택했습니다.${NC}"
echo ""

# 선택한 번호의 정보만 추출
temp_selected="/tmp/selected_error_$selected_number.tmp"

# 선택한 번호부터 다음 번호 전까지 또는 파일 끝까지 추출
awk -v num="$selected_number" '
    /^번호 \[/ {
        current_num = $0
        gsub(/번호 \[|\]/, "", current_num)
        if (current_num == num) {
            found = 1
        } else if (found) {
            exit
        }
    }
    found { print }
' "$RESULT_FILE" > "$temp_selected"

# 정보 파싱
file_path=""
sql_id=""
error_msg=""
sql_query=""

while IFS= read -r line; do
    if [[ "$line" =~ ^파일:\ (.+)$ ]]; then
        file_path="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^sqlid:\ (.+)$ ]]; then
        sql_id="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^에러:\ (.+)$ ]]; then
        error_msg="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^SQL:\ (.+)$ ]]; then
        sql_query="${BASH_REMATCH[1]}"
    fi
done < "$temp_selected"

# 템플릿 파일 경로
TEMPLATE_FILE="error_fix.md"

# 템플릿 파일 존재 확인
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: $TEMPLATE_FILE 템플릿 파일을 찾을 수 없습니다.${NC}"
    rm -f "$temp_selected"
    exit 1
fi

# 템플릿 읽기 및 변수 치환
template_content=$(cat "$TEMPLATE_FILE")
final_prompt=$(echo "$template_content" | \
    sed "s|{{FILE_PATH}}|$file_path|g" | \
    sed "s|{{SQL_ID}}|$sql_id|g" | \
    sed "s|{{ERROR_MESSAGE}}|$error_msg|g" | \
    sed "s|{{SQL_QUERY}}|${sql_query:0:200}...|g")

# 완성된 프롬프트 표시
echo -e "${BLUE}=== 완성된 프롬프트 (복사해서 사용하세요) ===${NC}"
echo -e "${YELLOW}==================== 프롬프트 시작 ====================${NC}"
echo "$final_prompt"
echo -e "${YELLOW}==================== 프롬프트 끝 ====================${NC}"
echo ""

# Q 바로 실행
echo -e "${GREEN}Q를 실행합니다...${NC}"
echo ""

# Q 실행
q chat

# Q 실행 후 수정 완료 여부 확인
echo ""
if [ "$AUTO_DELETE" = true ]; then
    echo -e "${GREEN}자동 삭제 모드: 번호 [$selected_number] 항목을 $RESULT_FILE에서 삭제합니다...${NC}"
    fix_success="y"
else
    echo -n "수정이 성공적으로 완료되었나요? (y/n): "
    read -r fix_success
fi

if [[ "$fix_success" == "y" || "$fix_success" == "Y" ]]; then
    if [ "$AUTO_DELETE" != true ]; then
        echo -e "${GREEN}번호 [$selected_number] 항목을 $RESULT_FILE에서 삭제합니다...${NC}"
    fi

    # fix_list.csv에 정보 추가
    FIX_LIST_FILE="fix_list.csv"

    # CSV 헤더가 없으면 생성
    if [ ! -f "$FIX_LIST_FILE" ]; then
        echo "번호,XML파일이름,sqlid (중복건수),에러메시지,결과처리" > "$FIX_LIST_FILE"
    fi

    # XML 파일명 추출 (파일 경로에서 파일명만)
    xml_filename=$(basename "$file_path")

    # 중복건수 확인 (같은 sqlid가 result 파일에 몇 개 있는지)
    duplicate_count=$(grep -c "sqlid: $sql_id" "$RESULT_FILE" 2>/dev/null || echo "1")

    # CSV에 추가할 데이터 준비 (쉼표와 따옴표 처리)
    csv_number="$selected_number"
    csv_xml_filename="\"$xml_filename\""
    csv_sqlid="\"$sql_id ($duplicate_count)\""
    csv_error_msg="\"${error_msg//\"/\"\"}\""  # 따옴표 이스케이프
    csv_result="\"수정완료\""

    # CSV 파일에 추가
    echo "$csv_number,$csv_xml_filename,$csv_sqlid,$csv_error_msg,$csv_result" >> "$FIX_LIST_FILE"

    echo -e "${BLUE}📝 fix_list.csv에 수정 내역이 기록되었습니다.${NC}"

    # result 파일에서 해당 번호 항목 삭제
    temp_result="/tmp/result_temp_$$.txt"

    # 선택한 번호부터 다음 번호 전까지 또는 파일 끝까지 제외하고 복사
    awk -v num="$selected_number" '
        /^번호 \[/ {
            current_num = $0
            gsub(/번호 \[|\]/, "", current_num)
            if (current_num == num) {
                skip = 1
                next
            } else if (skip) {
                skip = 0
            }
        }
        !skip { print }
    ' "$RESULT_FILE" > "$temp_result"

    # 원본 파일을 임시 파일로 교체
    mv "$temp_result" "$RESULT_FILE"

    echo -e "${GREEN}✅ 번호 [$selected_number] 항목이 $RESULT_FILE에서 삭제되었습니다.${NC}"

    # 남은 에러 개수 확인
    remaining_errors=$(grep -c "^번호 \[" "$RESULT_FILE" 2>/dev/null || echo "0")
    # 개행문자 제거 및 숫자만 추출
    remaining_errors=$(echo "$remaining_errors" | tr -d '\n' | grep -o '[0-9]*' | head -1)
    # 빈 값이면 0으로 설정
    remaining_errors=${remaining_errors:-0}

    echo -e "${BLUE}📊 남은 에러 개수: ${remaining_errors}개${NC}"

    if [ "$remaining_errors" -eq 0 ]; then
        echo -e "${GREEN}🎉 축하합니다! 모든 에러가 수정 완료되었습니다!${NC}"
        echo -e "${YELLOW}💡 이제 애플리케이션을 다시 테스트해보세요.${NC}"
    else
        echo -e "${YELLOW}💡 다음 에러를 수정하려면 다시 ./error_fix.sh $RESULT_FILE를 실행하세요.${NC}"
    fi
else
    echo -e "${YELLOW}번호 [$selected_number] 항목이 $RESULT_FILE에 그대로 유지됩니다.${NC}"
    echo -e "${BLUE}💡 나중에 다시 수정을 시도할 수 있습니다.${NC}"
fi

# 임시 파일 정리
rm -f "$temp_selected"

echo ""
echo -e "${GREEN}작업이 완료되었습니다.${NC}"