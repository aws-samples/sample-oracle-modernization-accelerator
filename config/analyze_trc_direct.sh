#!/bin/bash

# TRC 파일에서 주요 정보 추출

TRC_FILE="$1"

if [ -z "$TRC_FILE" ]; then
    echo "사용법: $0 <trc_file_path>"
    exit 1
fi

echo "=== TRC 파일 분석: $TRC_FILE ==="
echo

# 1. SQL 문장 추출
echo "1. 실행된 SQL 문장들:"
echo "========================"
grep -A 5 "^PARSING IN CURSOR" "$TRC_FILE" | grep -E "^(len=|dep=|uid=|oct=|lid=|tim=|hv=|ad=|sqlid=)"
echo

# 2. 실행 통계 추출
echo "2. 실행 통계:"
echo "============="
grep -E "^STAT|^EXEC|^FETCH|^PARSE" "$TRC_FILE"
echo

# 3. Wait 이벤트 추출
echo "3. Wait 이벤트:"
echo "==============="
grep "^WAIT" "$TRC_FILE" | head -20
echo

# 4. 바인드 변수 추출
echo "4. 바인드 변수:"
echo "==============="
grep -A 3 "^BINDS" "$TRC_FILE"
echo

# 5. 에러 메시지 추출
echo "5. 에러 메시지:"
echo "==============="
grep -i "error\|exception\|ora-" "$TRC_FILE"
