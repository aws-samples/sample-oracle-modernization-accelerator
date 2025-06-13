#!/bin/bash

# 입력 파라미터 확인
if [ $# -lt 1 ]; then
    echo "사용법: $0 <JAVA_SOURCE_DIR> [OUTPUT_DIR]"
    exit 1
fi

JAVA_SOURCE_DIR=$1
OUTPUT_DIR=${2:-"./java_sql_analysis"}

# 출력 디렉토리 생성
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/backups"

echo "Step 1: Java 소스 코드 파일 목록 생성 중..."
find "$JAVA_SOURCE_DIR" -name "*.java" > "$OUTPUT_DIR/java_files_list.txt"
echo "Java 파일 목록이 생성되었습니다: $OUTPUT_DIR/java_files_list.txt"

echo "Step 2: SQL 쿼리 및 컬럼 참조 패턴 검색 중..."
python3 "AP03.SQLPattern_analyzer.py" "$OUTPUT_DIR/java_files_list.txt" "$OUTPUT_DIR/sql_patterns.csv"

echo "Step 3: 대문자를 소문자로 변환 중..."
python3 "AP03.Convert_case.py" "$OUTPUT_DIR/sql_patterns.csv" "$OUTPUT_DIR/backups"

echo "작업이 완료되었습니다."
echo "분석 결과: $OUTPUT_DIR/sql_patterns.csv"
echo "원본 파일 백업: $OUTPUT_DIR/backups/"
