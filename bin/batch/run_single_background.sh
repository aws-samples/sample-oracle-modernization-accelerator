#!/bin/bash

# 단일 프로세스 백그라운드 실행 스크립트
# 사용법: ./run_single_background.sh <process_id> [mode] [batch_size]

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# 파라미터 확인
if [ $# -lt 1 ]; then
    echo -e "${RED}사용법: $0 <process_id> [mode] [batch_size]${NC}"
    echo -e "${YELLOW}예시:${NC}"
    echo -e "  $0 0                    # 프로세스 0, all 모드, 배치크기 10"
    echo -e "  $0 3 transform          # 프로세스 3, transform 모드, 배치크기 10"
    echo -e "  $0 7 extract 5          # 프로세스 7, extract 모드, 배치크기 5"
    echo -e "${CYAN}process_id: 0~9 (CSV No 끝자리와 매칭)${NC}"
    echo -e "${CYAN}mode: all|extract|transform|merge (기본값: all)${NC}"
    echo -e "${CYAN}batch_size: 숫자 (기본값: 10)${NC}"
    exit 1
fi

PROCESS_ID=$1
MODE=${2:-all}
BATCH_SIZE=${3:-10}

# process_id 유효성 검사
if ! [[ "$PROCESS_ID" =~ ^[0-9]$ ]]; then
    echo -e "${RED}오류: process_id는 0~9 사이의 숫자여야 합니다.${NC}"
    exit 1
fi

# mode 유효성 검사
if [[ ! "$MODE" =~ ^(all|extract|transform|merge)$ ]]; then
    echo -e "${RED}오류: mode는 all, extract, transform, merge 중 하나여야 합니다.${NC}"
    exit 1
fi

echo -e "${BLUE}${BOLD}단일 프로세스 백그라운드 실행${NC}"
echo -e "${CYAN}프로세스 ID: $PROCESS_ID (No 끝자리 $PROCESS_ID 처리)${NC}"
echo -e "${CYAN}실행 모드: $MODE${NC}"
echo -e "${CYAN}배치 크기: $BATCH_SIZE${NC}"

# 환경 변수 확인
if [ -z "$APPLICATION_NAME" ]; then
    echo -e "${RED}${BOLD}오류: 환경 변수가 설정되지 않았습니다.${NC}"
    echo -e "${YELLOW}환경 변수 파일을 source 하세요. 예: source ./oma_env_프로젝트명.sh${NC}"
    exit 1
fi

echo -e "${GREEN}프로젝트: $APPLICATION_NAME${NC}"

# 백그라운드 로그 디렉토리 생성
BG_LOG_DIR="$APP_LOGS_FOLDER/background"
mkdir -p "$BG_LOG_DIR"

# 로그 파일명
PROCESS_LOG="$BG_LOG_DIR/process_${PROCESS_ID}_$(date +%Y%m%d_%H%M%S).log"

# PID 디렉토리 생성
PID_DIR="$BG_LOG_DIR/pids"
mkdir -p "$PID_DIR"

echo -e "${YELLOW}백그라운드 실행 시작...${NC}"

# nohup으로 백그라운드 실행
nohup python3 ./sqlTransformTarget_parallel.py \
    --process-id $PROCESS_ID \
    --mode $MODE \
    --batch-size $BATCH_SIZE \
    --verbose > "$PROCESS_LOG" 2>&1 &

# PID 저장
PID=$!
echo $PID > "$PID_DIR/process_$PROCESS_ID.pid"

echo -e "${GREEN}${BOLD}백그라운드 실행 시작됨!${NC}"
echo -e "${CYAN}PID: $PID${NC}"
echo -e "${CYAN}로그 파일: $PROCESS_LOG${NC}"
echo -e "${CYAN}PID 파일: $PID_DIR/process_$PROCESS_ID.pid${NC}"

echo ""
echo -e "${YELLOW}${BOLD}모니터링 명령어:${NC}"
echo -e "${CYAN}# 실시간 로그 확인${NC}"
echo -e "tail -f $PROCESS_LOG"
echo ""
echo -e "${CYAN}# 프로세스 상태 확인${NC}"
echo -e "ps aux | grep $PID"
echo ""
echo -e "${CYAN}# 프로세스 종료${NC}"
echo -e "kill $PID"

echo ""
echo -e "${GREEN}${BOLD}프로세스 $PROCESS_ID 백그라운드 실행 완료!${NC}"
