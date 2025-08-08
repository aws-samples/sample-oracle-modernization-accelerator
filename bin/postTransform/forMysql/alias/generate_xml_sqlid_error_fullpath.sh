#!/bin/bash

# xml_sqlid_error.csv를 읽어서 xml_sqlid_error_fullpath.csv를 생성하는 스크립트
# 생성 시간: $(date)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_FILE="$SCRIPT_DIR/xml_sqlid_error.csv"
OUTPUT_CSV="$SCRIPT_DIR/xml_sqlid_error_fullpath.csv"
OUTPUT_TXT="$SCRIPT_DIR/xml_sqlid_error_fullpath.txt"

echo "=== XML SQLID 에러 파일 전체 경로 생성 시작 ==="
echo "입력 파일: $INPUT_FILE"
echo "출력 CSV: $OUTPUT_CSV"
echo "출력 TXT: $OUTPUT_TXT"
echo "검색 경로: $APP_LOGS_FOLDER/mapper/*/transform"

# CSV 헤더 작성
echo "상태,XML파일명,SQLID,SQL에러,실제파일경로" > "$OUTPUT_CSV"

# TXT 헤더 작성
echo "Sub query alias 오류 파일 검색 결과 (에러 정보 포함)" > "$OUTPUT_TXT"
echo "생성 시간: $(date)" >> "$OUTPUT_TXT"
echo "=======================================" >> "$OUTPUT_TXT"
echo "" >> "$OUTPUT_TXT"

found_count=0
total_count=0

while IFS=',' read -r xml_file sqlid sql_error; do
    # 헤더 스킵
    if [[ "$xml_file" == "XML파일명" ]]; then
        continue
    fi
    
    total_count=$((total_count + 1))
    
    # XML 확장자 제거
    xml_file_no_ext="${xml_file%.xml}"
    
    # 전체 mapper에서 리커시브 검색 - SQLID로만 검색
    search_pattern="${xml_file_no_ext}_tgt-*-*-${sqlid}.xml"
    found_file=$(find "$APP_LOGS_FOLDER/mapper" -path "*/transform/*" -name "$search_pattern" 2>/dev/null)
    
    if [[ -n "$found_file" ]]; then
        echo "FOUND,$xml_file,$sqlid,\"$sql_error\",$found_file" >> "$OUTPUT_CSV"
        echo "✓ FOUND: $xml_file -> $sqlid" >> "$OUTPUT_TXT"
        echo "   에러: $sql_error" >> "$OUTPUT_TXT"
        echo "   파일: $found_file" >> "$OUTPUT_TXT"
        echo "" >> "$OUTPUT_TXT"
        found_count=$((found_count + 1))
    else
        echo "NOT_FOUND,$xml_file,$sqlid,\"$sql_error\",N/A" >> "$OUTPUT_CSV"
        echo "✗ NOT FOUND: $xml_file -> $sqlid" >> "$OUTPUT_TXT"
        echo "   에러: $sql_error" >> "$OUTPUT_TXT"
        echo "   검색 패턴: $search_pattern in $APP_LOGS_FOLDER/mapper/*/transform" >> "$OUTPUT_TXT"
        echo "" >> "$OUTPUT_TXT"
    fi
    
done < "$INPUT_FILE"

# 요약 정보 추가
echo "" >> "$OUTPUT_TXT"
echo "=== 검색 결과 요약 ===" >> "$OUTPUT_TXT"
echo "총 검색 대상: $total_count 개" >> "$OUTPUT_TXT"
echo "발견된 파일: $found_count 개" >> "$OUTPUT_TXT"
echo "누락된 파일: $((total_count - found_count)) 개" >> "$OUTPUT_TXT"

echo ""
echo "=== 결과 파일 생성 완료 ==="
echo "CSV 파일: $OUTPUT_CSV"
echo "TXT 파일: $OUTPUT_TXT"
echo ""
echo "=== 검색 결과 요약 ==="
echo "총 검색 대상: $total_count 개"
echo "발견된 파일: $found_count 개"
echo "누락된 파일: $((total_count - found_count)) 개"
