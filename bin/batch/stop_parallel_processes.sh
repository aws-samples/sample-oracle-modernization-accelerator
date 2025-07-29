#!/bin/bash

# 병렬 프로세스 종료 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# 구분선 출력 함수
print_separator() {
    printf "${BLUE}${BOLD}%80s${NC}\n" | tr " " "="
}

print_separator
echo -e "${BLUE}${BOLD}병렬 프로세스 종료${NC}"
print_separator

# 환경 변수 확인
if [ -z "$APPLICATION_NAME" ]; then
    echo -e "${RED}${BOLD}오류: 환경 변수가 설정되지 않았습니다.${NC}"
    exit 1
fi

BG_LOG_DIR="$APP_LOGS_FOLDER/background"
PID_DIR="$BG_LOG_DIR/pids"

if [ ! -d "$PID_DIR" ]; then
    echo -e "${YELLOW}PID 디렉토리가 없습니다: $PID_DIR${NC}"
    echo -e "${YELLOW}병렬 프로세스가 실행되지 않았거나 이미 종료되었습니다.${NC}"
    exit 1
fi

echo -e "${CYAN}프로젝트: $APPLICATION_NAME${NC}"

# 종료 확인
echo -e "${YELLOW}${BOLD}정말로 모든 병렬 프로세스를 종료하시겠습니까?${NC}"
echo -e "${RED}진행 중인 작업이 손실될 수 있습니다.${NC}"
read -p "계속하려면 'yes'를 입력하세요: " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${CYAN}취소되었습니다.${NC}"
    exit 0
fi

print_separator
echo -e "${BLUE}${BOLD}프로세스 종료 중...${NC}"
print_separator

terminated_count=0
already_stopped_count=0

# 각 프로세스 종료
for i in {0..9}; do
    pid_file="$PID_DIR/process_$i.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        
        # 프로세스가 실행 중인지 확인
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}프로세스 $i 종료 중... (PID: $pid)${NC}"
            
            # SIGTERM으로 정상 종료 시도
            kill "$pid" 2>/dev/null
            
            # 5초 대기
            sleep 5
            
            # 여전히 실행 중이면 강제 종료
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${RED}  강제 종료 중... (SIGKILL)${NC}"
                kill -9 "$pid" 2>/dev/null
                sleep 2
            fi
            
            # 종료 확인
            if ! kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}  ✓ 프로세스 $i 종료됨${NC}"
                ((terminated_count++))
            else
                echo -e "${RED}  ✗ 프로세스 $i 종료 실패${NC}"
            fi
            
            # PID 파일 삭제
            rm -f "$pid_file"
        else
            echo -e "${CYAN}프로세스 $i: 이미 중지됨 (PID: $pid)${NC}"
            ((already_stopped_count++))
            # PID 파일 삭제
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}프로세스 $i: PID 파일 없음${NC}"
        ((already_stopped_count++))
    fi
done

# 추가로 프로세스명으로 검색해서 종료
echo -e "${YELLOW}추가 프로세스 검색 중...${NC}"
additional_pids=$(pgrep -f "sqlTransformTarget_parallel")
if [ -n "$additional_pids" ]; then
    echo -e "${YELLOW}추가 프로세스 발견: $additional_pids${NC}"
    for pid in $additional_pids; do
        kill "$pid" 2>/dev/null
        sleep 2
        kill -9 "$pid" 2>/dev/null
    done
fi

print_separator
echo -e "${BLUE}${BOLD}종료 완료${NC}"
print_separator
echo -e "${GREEN}종료된 프로세스: $terminated_count 개${NC}"
echo -e "${CYAN}이미 중지됨: $already_stopped_count 개${NC}"

# PID 디렉토리가 비어있으면 삭제
if [ -d "$PID_DIR" ] && [ -z "$(ls -A "$PID_DIR")" ]; then
    rmdir "$PID_DIR"
    echo -e "${CYAN}PID 디렉토리 정리됨${NC}"
fi

print_separator
echo -e "${GREEN}${BOLD}모든 병렬 프로세스가 종료되었습니다.${NC}"
print_separator
