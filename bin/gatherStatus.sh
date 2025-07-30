#!/bin/bash

# gatherStatus.sh - 통계 자료 생성 스크립트
# 작성 위치: /tmp/gatherStatus.sh

echo "=== 통계 자료 수집 시작 ==="
echo "수집 시간: $(date)"
echo

# 1. SQLTransformTarget.csv Process 컬럼별 통계
echo "=== SQLTransformTarget.csv Process 컬럼별 통계 ==="
if [ -f "$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv" ]; then
    echo "파일 위치: $APP_TRANSFORM_FOLDER/SQLTransformTarget.csv"
    total_records=$(tail -n +2 "$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv" | wc -l)
    echo "총 레코드 수: $total_records"
    echo
    echo "Process 상태별 통계 및 비율:"
    echo "+---------------+-------+--------+"
    echo "| 상태          | 개수  | 비율   |"
    echo "+---------------+-------+--------+"
    
    # 임시 파일에 통계 저장
    temp_stats="/tmp/process_stats.tmp"
    tail -n +2 "$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv" | cut -d',' -f7 | tr -d '\r' | sed 's/^$/EMPTY/' | sort | uniq -c | sort -nr > "$temp_stats"
    
    # 표 형태로 출력
    while read -r count status; do
        # 빈 값 처리
        if [ -z "$status" ] || [ "$status" = "EMPTY" ]; then
            status="(빈값)"
        fi
        percentage=$(echo "scale=2; $count * 100 / $total_records" | bc -l)
        printf "| %-13s | %5d | %5.2f%% |\n" "$status" "$count" "$percentage"
    done < "$temp_stats"
    
    echo "+---------------+-------+--------+"
    printf "| %-13s | %5d | %5.2f%% |\n" "전체" "$total_records" "100.00"
    echo "+---------------+-------+--------+"
    
    # 임시 파일 정리
    rm -f "$temp_stats"
else
    echo "파일을 찾을 수 없습니다: $APP_TRANSFORM_FOLDER/SQLTransformTarget.csv"
fi
echo

# 2. extract XML 파일 통계
echo "=== Extract XML 파일 통계 ==="
extract_count=$(find $APP_LOGS_FOLDER -path "*/extract/*.xml" 2>/dev/null | wc -l)
echo "Extract XML 파일 개수: $extract_count"
echo

# 3. transform XML 파일 통계
echo "=== Transform XML 파일 통계 ==="
transform_count=$(find $APP_LOGS_FOLDER -path "*/transform/*.xml" 2>/dev/null | wc -l)
echo "Transform XML 파일 개수: $transform_count"
echo

# 4. 전체 요약
echo "=== 전체 요약 ==="
echo "CSV 파일: $APP_TRANSFORM_FOLDER/SQLTransformTarget.csv"
echo "Extract XML 파일: $extract_count 개"
echo "Transform XML 파일: $transform_count 개"
echo "총 XML 파일: $((extract_count + transform_count)) 개"
echo
echo "=== 통계 자료 수집 완료 ==="
