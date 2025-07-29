#!/bin/bash

#  transform xml 파일 동적 처리
cd $APP_TOOLS_FOLDER/../postTransform/function

# 환경변수에서 경로 가져오기
APP_LOGS_FOLDER=${APP_LOGS_FOLDER:-"/tmp"}
APP_TRANSFORM_FOLDER=${APP_TRANSFORM_FOLDER:-"/tmp"}

# 로그 디렉토리 생성
POST_TRANSFORM_LOG_DIR="$APP_LOGS_FOLDER/postTransform"
mkdir -p "$POST_TRANSFORM_LOG_DIR"
mkdir -p "$APP_TRANSFORM_FOLDER"

# 통합 테스트 로그 파일
LOG_FILE="$POST_TRANSFORM_LOG_DIR/sqlTestResult.log"

# 로그 파일 초기화 (처음 실행시)
echo "🔄 로그 파일 초기화: $LOG_FILE"
echo "=== SQL Function Test Log - $(date) ===" > "$LOG_FILE"

# 결과 파일 경로 설정 및 초기화
RESULT_FILE="$APP_TRANSFORM_FOLDER/sqlTestResult.json"
FAILED_RESULT_FILE="$APP_TRANSFORM_FOLDER/sqlTestResultFailed.json"
echo "🔄 결과 파일 초기화: $RESULT_FILE"
echo "🔄 실패 결과 파일 초기화: $FAILED_RESULT_FILE"
rm -f "$RESULT_FILE"
rm -f "$FAILED_RESULT_FILE"

# transform xml 리스트 동적 생성
echo "🔍 transform xml 파일 검색 중..."
transform_xml_list="$POST_TRANSFORM_LOG_DIR/sqlTestResult_xml_list.txt"
find $APP_LOGS_FOLDER/mapper/ -path "*/transform/*.xml" -type f > "$transform_xml_list" 2>/dev/null

# 파일 개수 확인
file_count=$(wc -l < "$transform_xml_list")
echo "📁 발견된 transform xml 파일: ${file_count}개"

if [ $file_count -eq 0 ]; then
    echo "❌ transform xml 파일을 찾을 수 없습니다."
    echo "   경로: $APP_LOGS_FOLDER/mapper/*/transform/*.xml"
    exit 1
fi

echo "=== transform xml 파일 처리 시작 ==="
echo "$(date)"
echo "📁 대상 파일: ${file_count}개"
echo

# Python 스크립트 경로 설정
script_path="$APP_TOOLS_FOLDER/../postTransform/function/genSelectFromXML.py"
if [ ! -f "$script_path" ]; then
    echo "❌ genSelectFromXML.py 스크립트를 찾을 수 없습니다."
    echo "   경로: $script_path"
    exit 1
fi

echo "🚀 사용할 스크립트: $script_path"
echo

# 파일 리스트 읽기
mapfile -t files < "$transform_xml_list"

success_count=0
fail_count=0
no_func_count=0
timeout_count=0

for i in "${!files[@]}"; do
    file="${files[$i]}"
    filename=$(basename "$file")
    echo "[$((i+1))/${file_count}] $filename"
    
    # 타임아웃 설정 (30초)
    timeout 30s python3 "$script_path" "$file" > /tmp/test_result_$((i+1)).log 2>&1
    exit_code=$?
    
    if [ $exit_code -eq 124 ]; then
        echo "  ⏰ 타임아웃"
        timeout_count=$((timeout_count + 1))
    else
        result=$(cat /tmp/test_result_$((i+1)).log)
        
        if echo "$result" | grep -q "✅ 성공"; then
            functions=$(echo "$result" | grep "추출된 함수 개수" | sed 's/.*: //')
            unique=$(echo "$result" | grep "중복 제거 후" | sed 's/.*: //')
            echo "  ✅ 성공 - $functions → $unique"
            success_count=$((success_count + 1))
        elif echo "$result" | grep -q "함수를 찾을 수 없습니다"; then
            echo "  ⚪ 함수 없음"
            no_func_count=$((no_func_count + 1))
        else
            echo "  ❌ 실패"
            fail_count=$((fail_count + 1))
        fi
    fi
    
    # 진행률 표시 (100개마다 또는 전체 파일이 100개 미만인 경우 10개마다)
    progress_interval=$( [ $file_count -gt 100 ] && echo 100 || echo 10 )
    if [ $((($i + 1) % $progress_interval)) -eq 0 ]; then
        echo "  📊 진행률: $((i+1))/${file_count} - 성공: $success_count, 함수없음: $no_func_count, 실패: $fail_count"
    fi
done

echo ""
echo "=== transform xml 처리 최종 결과 ==="
echo "✅ 성공: $success_count개"
echo "⚪ 함수 없음: $no_func_count개"  
echo "❌ 실패: $fail_count개"
echo "⏰ 타임아웃: $timeout_count개"
echo "📊 성공률: $(( (success_count + no_func_count) * 100 / file_count ))%"
echo ""
echo "🚀 처리 완료 - 총 ${file_count}개 파일"
echo "$(date)"
echo "=== transform xml 처리 완료 ==="
