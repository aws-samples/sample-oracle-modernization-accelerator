#!/bin/bash

# qchat 프로세스 상태 확인 스크립트

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

# 시간 변환 함수 (초를 시:분:초로 변환)
convert_seconds() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    local secs=$((seconds % 60))
    printf "%02d:%02d:%02d" $hours $minutes $secs
}

print_separator
echo -e "${BLUE}${BOLD}qchat 프로세스 상태 확인${NC}"
print_separator

# qchat 프로세스 확인 (전체 시스템 대상)
qchat_pids=$(pgrep -af qchat | awk '{print $1}')

if [ -z "$qchat_pids" ]; then
    echo -e "${YELLOW}실행 중인 qchat 프로세스가 없습니다.${NC}"
    exit 0
fi

running_count=0
current_time=$(date +%s)

echo -e "${CYAN}현재 시간: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
print_separator

for pid in $qchat_pids; do
    if kill -0 "$pid" 2>/dev/null; then
        # 프로세스 시작 시간 가져오기 (epoch seconds)
        start_time=$(stat -c %Y /proc/$pid 2>/dev/null)
        
        if [ -n "$start_time" ]; then
            # 실제 실행 시간 계산
            runtime=$((current_time - start_time))
            runtime_formatted=$(convert_seconds $runtime)
        else
            runtime_formatted="알 수 없음"
        fi
        
        # 프로세스 정보 가져오기
        process_info=$(ps -p $pid -o user,cmd,pcpu,pmem --no-headers 2>/dev/null)
        
        if [ -n "$process_info" ]; then
            user=$(echo "$process_info" | awk '{print $1}')
            cmd=$(echo "$process_info" | awk '{for(i=2;i<=NF-2;i++) printf "%s ", $i; print ""}' | sed 's/ $//')
            cpu=$(echo "$process_info" | awk '{print $(NF-1)}')
            mem=$(echo "$process_info" | awk '{print $NF}')
            
            echo -e "${GREEN}✓ PID: $pid${NC}"
            echo -e "  ${CYAN}사용자: $user${NC}"
            echo -e "  ${CYAN}실행시간: $runtime_formatted${NC}"
            echo -e "  ${CYAN}CPU: ${cpu}% | 메모리: ${mem}%${NC}"
            echo -e "  ${MAGENTA}명령어: $cmd${NC}"
            
            # 프로세스 상태 확인
            status=$(ps -p $pid -o stat --no-headers 2>/dev/null | tr -d ' ')
            case $status in
                S*) echo -e "  ${GREEN}상태: 대기 중 (정상)${NC}" ;;
                R*) echo -e "  ${GREEN}상태: 실행 중${NC}" ;;
                D*) echo -e "  ${YELLOW}상태: 디스크 대기${NC}" ;;
                Z*) echo -e "  ${RED}상태: 좀비 프로세스${NC}" ;;
                T*) echo -e "  ${YELLOW}상태: 중지됨${NC}" ;;
                *) echo -e "  ${CYAN}상태: $status${NC}" ;;
            esac
            
            ((running_count++))
        fi
        echo ""
    fi
done

print_separator
echo -e "${BLUE}${BOLD}상태 요약${NC}"
print_separator
echo -e "${GREEN}실행 중인 qchat 프로세스: $running_count 개${NC}"

if [ $running_count -gt 0 ]; then
    echo -e "${GREEN}${BOLD}qchat 프로세스들이 정상 실행 중입니다!${NC}"
else
    echo -e "${RED}${BOLD}실행 중인 qchat 프로세스가 없습니다.${NC}"
fi

print_separator
echo -e "${YELLOW}${BOLD}유용한 명령어:${NC}"
echo -e "${CYAN}# qchat 프로세스 종료${NC}"
echo -e "pkill -f qchat"
echo ""
echo -e "${CYAN}# 특정 PID 종료${NC}"
echo -e "kill <PID>"
echo ""
echo -e "${CYAN}# 시스템 리소스 확인${NC}"
echo -e "top -p \$(pgrep -f qchat | tr '\\n' ',' | sed 's/,$//')"
print_separator
