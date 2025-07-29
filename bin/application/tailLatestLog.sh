#!/bin/bash

# 새로 생성되는 로그 파일을 자동으로 tail -f하는 스크립트

# 로그 디렉토리 설정
LOG_DIR="$APP_LOGS_FOLDER/qlogs"

echo "로그 파일 모니터링을 시작합니다..."
echo "모니터링 경로: $LOG_DIR"
echo "Ctrl+C로 종료할 수 있습니다."
echo ""

cleanup() {
    if [ ! -z "$tail_pid" ]; then
        kill $tail_pid 2>/dev/null
    fi
    echo ""
    echo "모니터링을 종료합니다."
    exit 0
}

# Ctrl+C 시그널 처리
trap cleanup INT

while true; do
    # 가장 최근 로그 파일 찾기
    latest_file=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
    
    if [ -n "$latest_file" ]; then
        echo "=== Following: $(basename "$latest_file") ==="
        tail -f "$latest_file" &
        tail_pid=$!
        
        # 새 파일이 생성될 때까지 대기
        current_latest="$latest_file"
        while [ "$current_latest" = "$latest_file" ]; do
            sleep 2
            current_latest=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
        done
        
        # 이전 tail 프로세스 종료
        kill $tail_pid 2>/dev/null
        echo ""
        echo "새로운 로그 파일이 생성되었습니다. 전환합니다..."
        echo ""
    else
        echo "로그 파일을 찾을 수 없습니다. 2초 후 다시 확인합니다..."
        sleep 2
    fi
done
