#!/bin/bash

# 전체 사용자 대상 Background 프로세스 확인 스크립트

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
echo -e "${BLUE}${BOLD}전체 사용자 Background 프로세스 상태 확인${NC}"
print_separator

current_time=$(date +%s)
echo -e "${CYAN}현재 시간: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
print_separator

# 1. nohup 프로세스 확인
echo -e "${BLUE}${BOLD}1. nohup 프로세스${NC}"
print_separator

nohup_pids=$(pgrep -af nohup | awk '{print $1}')
nohup_count=0

if [ -n "$nohup_pids" ]; then
    for pid in $nohup_pids; do
        if kill -0 "$pid" 2>/dev/null; then
            process_info=$(ps -p $pid -o user,ppid,cmd,pcpu,pmem,etime --no-headers 2>/dev/null)
            if [ -n "$process_info" ]; then
                user=$(echo "$process_info" | awk '{print $1}')
                ppid=$(echo "$process_info" | awk '{print $2}')
                cmd=$(echo "$process_info" | awk '{for(i=3;i<=NF-3;i++) printf "%s ", $i; print ""}' | sed 's/ $//')
                cpu=$(echo "$process_info" | awk '{print $(NF-2)}')
                mem=$(echo "$process_info" | awk '{print $(NF-1)}')
                etime=$(echo "$process_info" | awk '{print $NF}')
                
                echo -e "${GREEN}✓ PID: $pid${NC}"
                echo -e "  ${CYAN}사용자: $user | 부모PID: $ppid${NC}"
                echo -e "  ${CYAN}실행시간: $etime | CPU: ${cpu}% | 메모리: ${mem}%${NC}"
                echo -e "  ${MAGENTA}명령어: $cmd${NC}"
                
                # 작업 디렉토리 확인
                if [ -L "/proc/$pid/cwd" ]; then
                    workdir=$(readlink /proc/$pid/cwd 2>/dev/null)
                    echo -e "  ${CYAN}작업디렉토리: $workdir${NC}"
                    
                    # nohup.out 파일 확인
                    if [ -f "$workdir/nohup.out" ]; then
                        nohup_size=$(ls -lh "$workdir/nohup.out" 2>/dev/null | awk '{print $5}')
                        echo -e "  ${YELLOW}nohup.out: $workdir/nohup.out (크기: $nohup_size)${NC}"
                    fi
                fi
                echo ""
                ((nohup_count++))
            fi
        fi
    done
else
    echo -e "${YELLOW}실행 중인 nohup 프로세스가 없습니다.${NC}"
fi

# 2. screen 세션 확인
print_separator
echo -e "${BLUE}${BOLD}2. screen 세션${NC}"
print_separator

screen_sessions=$(screen -ls 2>/dev/null | grep -E "^\s*[0-9]+\." | wc -l)
if [ $screen_sessions -gt 0 ]; then
    screen -ls 2>/dev/null | grep -E "^\s*[0-9]+\." | while read line; do
        session_id=$(echo "$line" | awk '{print $1}')
        session_name=$(echo "$line" | awk '{print $2}' | sed 's/.*\.//')
        status=$(echo "$line" | awk '{print $3}' | tr -d '()')
        
        echo -e "${GREEN}✓ Screen 세션: $session_id${NC}"
        echo -e "  ${CYAN}이름: $session_name${NC}"
        echo -e "  ${CYAN}상태: $status${NC}"
        echo ""
    done
else
    echo -e "${YELLOW}실행 중인 screen 세션이 없습니다.${NC}"
fi

# 3. tmux 세션 확인
print_separator
echo -e "${BLUE}${BOLD}3. tmux 세션${NC}"
print_separator

if command -v tmux >/dev/null 2>&1; then
    tmux_sessions=$(tmux list-sessions 2>/dev/null | wc -l)
    if [ $tmux_sessions -gt 0 ]; then
        tmux list-sessions 2>/dev/null | while read line; do
            session_name=$(echo "$line" | cut -d':' -f1)
            windows=$(echo "$line" | grep -o '[0-9]* windows' | cut -d' ' -f1)
            created=$(echo "$line" | grep -o 'created [^)]*' | cut -d' ' -f2-)
            
            echo -e "${GREEN}✓ tmux 세션: $session_name${NC}"
            echo -e "  ${CYAN}윈도우 수: $windows${NC}"
            echo -e "  ${CYAN}생성시간: $created${NC}"
            echo ""
        done
    else
        echo -e "${YELLOW}실행 중인 tmux 세션이 없습니다.${NC}"
    fi
else
    echo -e "${YELLOW}tmux가 설치되어 있지 않습니다.${NC}"
fi

# 4. 데몬 프로세스 확인 (주요 서비스들)
print_separator
echo -e "${BLUE}${BOLD}4. 주요 데몬/서비스 프로세스${NC}"
print_separator

daemon_patterns=("httpd" "nginx" "mysql" "postgres" "redis" "mongodb" "java" "python.*server" "node" "docker" "jenkins")
daemon_count=0

for pattern in "${daemon_patterns[@]}"; do
    pids=$(pgrep -af "$pattern" 2>/dev/null | grep -v grep | awk '{print $1}')
    if [ -n "$pids" ]; then
        echo -e "${MAGENTA}${BOLD}[$pattern 관련 프로세스]${NC}"
        for pid in $pids; do
            if kill -0 "$pid" 2>/dev/null; then
                process_info=$(ps -p $pid -o user,cmd,pcpu,pmem,etime --no-headers 2>/dev/null)
                if [ -n "$process_info" ]; then
                    user=$(echo "$process_info" | awk '{print $1}')
                    cmd=$(echo "$process_info" | awk '{for(i=2;i<=NF-3;i++) printf "%s ", $i; print ""}' | sed 's/ $//' | cut -c1-60)
                    cpu=$(echo "$process_info" | awk '{print $(NF-2)}')
                    mem=$(echo "$process_info" | awk '{print $(NF-1)}')
                    etime=$(echo "$process_info" | awk '{print $NF}')
                    
                    echo -e "${GREEN}  ✓ PID: $pid${NC}"
                    echo -e "    ${CYAN}사용자: $user | 실행시간: $etime${NC}"
                    echo -e "    ${CYAN}CPU: ${cpu}% | 메모리: ${mem}%${NC}"
                    echo -e "    ${MAGENTA}명령어: $cmd...${NC}"
                    ((daemon_count++))
                fi
            fi
        done
        echo ""
    fi
done

if [ $daemon_count -eq 0 ]; then
    echo -e "${YELLOW}주요 데몬 프로세스가 실행되고 있지 않습니다.${NC}"
fi

# 5. 모든 사용자의 프로세스 확인
print_separator
echo -e "${BLUE}${BOLD}5. 전체 사용자 프로세스 (python, q, java 등)${NC}"
print_separator

# 전체 시스템에서 주요 프로세스들 확인
user_process_patterns=("python" "q " "java" "node" "ruby" "perl" "php")
user_process_count=0

for pattern in "${user_process_patterns[@]}"; do
    # 전체 시스템에서 해당 패턴의 프로세스 검색
    processes=$(ps -eo pid,user,cmd,pcpu,pmem,etime --no-headers | grep -i "$pattern" | grep -v grep | grep -v "check_all_background")
    
    if [ -n "$processes" ]; then
        echo -e "${MAGENTA}${BOLD}[$pattern 관련 프로세스]${NC}"
        echo "$processes" | while read line; do
            pid=$(echo "$line" | awk '{print $1}')
            user=$(echo "$line" | awk '{print $2}')
            cmd=$(echo "$line" | awk '{for(i=3;i<=NF-3;i++) printf "%s ", $i; print ""}' | sed 's/ $//' | cut -c1-80)
            cpu=$(echo "$line" | awk '{print $(NF-2)}')
            mem=$(echo "$line" | awk '{print $(NF-1)}')
            etime=$(echo "$line" | awk '{print $NF}')
            
            echo -e "${GREEN}  ✓ PID: $pid${NC}"
            echo -e "    ${CYAN}사용자: $user | 실행시간: $etime${NC}"
            echo -e "    ${CYAN}CPU: ${cpu}% | 메모리: ${mem}%${NC}"
            echo -e "    ${MAGENTA}명령어: $cmd${NC}"
            echo ""
        done
        user_process_count=$((user_process_count + $(echo "$processes" | wc -l)))
    fi
done

# 6. 각 사용자별 프로세스 요약
print_separator
echo -e "${BLUE}${BOLD}6. 사용자별 프로세스 요약${NC}"
print_separator

# /home 디렉토리의 모든 사용자 확인
for user_home in /home/*; do
    if [ -d "$user_home" ]; then
        username=$(basename "$user_home")
        # 해당 사용자의 모든 프로세스 개수 확인
        user_process_count=$(ps -u "$username" --no-headers 2>/dev/null | wc -l)
        if [ $user_process_count -gt 0 ]; then
            echo -e "${GREEN}✓ 사용자: $username${NC}"
            echo -e "  ${CYAN}실행 중인 프로세스: $user_process_count 개${NC}"
            
            # 주요 프로세스들만 표시
            main_processes=$(ps -u "$username" -o pid,cmd,pcpu,pmem,etime --no-headers 2>/dev/null | head -5)
            if [ -n "$main_processes" ]; then
                echo "$main_processes" | while read line; do
                    pid=$(echo "$line" | awk '{print $1}')
                    cmd=$(echo "$line" | awk '{for(i=2;i<=NF-3;i++) printf "%s ", $i; print ""}' | sed 's/ $//' | cut -c1-60)
                    cpu=$(echo "$line" | awk '{print $(NF-2)}')
                    mem=$(echo "$line" | awk '{print $(NF-1)}')
                    etime=$(echo "$line" | awk '{print $NF}')
                    
                    echo -e "    ${YELLOW}PID: $pid | CPU: ${cpu}% | 메모리: ${mem}% | 시간: $etime${NC}"
                    echo -e "    ${MAGENTA}$cmd${NC}"
                done
            fi
            echo ""
        fi
    fi
done

if [ $user_process_count -eq 0 ]; then
    echo -e "${YELLOW}사용자 프로세스가 실행되고 있지 않습니다.${NC}"
fi

# 7. 요약 정보
print_separator
echo -e "${BLUE}${BOLD}상태 요약${NC}"
print_separator
echo -e "${GREEN}nohup 프로세스: $nohup_count 개${NC}"
echo -e "${GREEN}screen 세션: $screen_sessions 개${NC}"
echo -e "${GREEN}tmux 세션: ${tmux_sessions:-0} 개${NC}"
echo -e "${GREEN}데몬 프로세스: $daemon_count 개${NC}"
echo -e "${GREEN}사용자 프로세스: $user_process_count 개${NC}"

total_bg=$((nohup_count + screen_sessions + ${tmux_sessions:-0} + daemon_count + user_process_count))
echo -e "${GREEN}${BOLD}총 백그라운드 프로세스: $total_bg 개${NC}"

print_separator
echo -e "${YELLOW}${BOLD}유용한 명령어:${NC}"
echo -e "${CYAN}# 모든 nohup 프로세스 종료${NC}"
echo -e "pkill -f nohup"
echo ""
echo -e "${CYAN}# screen 세션 재연결${NC}"
echo -e "screen -r <session_id>"
echo ""
echo -e "${CYAN}# tmux 세션 재연결${NC}"
echo -e "tmux attach -t <session_name>"
echo ""
echo -e "${CYAN}# 특정 사용자 프로세스 확인${NC}"
echo -e "ps -u <username> -f"
echo ""
echo -e "${CYAN}# 시스템 전체 프로세스 트리${NC}"
echo -e "pstree -p"
print_separator
