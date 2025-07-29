#!/bin/bash

# 백그라운드 프로세스 PID 확인 스크립트
# 위치: /home/ec2-user/workspace/oracle-mod-ax/bin/batch/check_background_processes.sh

# sudo 권한으로 재실행
if [ "$EUID" -ne 0 ]; then
    echo "sudo 권한으로 재실행합니다..."
    exec sudo "$0" "$@"
fi

PID_DIR="/home/ec2-user/workspace/oracle-mod-ax/ibe-vof-trans/logs/application/background/pids"

# PID 디렉토리 존재 확인
if [ ! -d "$PID_DIR" ]; then
    echo "❌ ERROR: PID 디렉토리가 존재하지 않습니다: $PID_DIR"
    exit 1
fi

# PID 파일 개수 확인
pid_count=$(ls -1 "$PID_DIR"/*.pid 2>/dev/null | wc -l)

echo "🔍 백그라운드 프로세스 상태 확인"
echo "📁 PID 디렉토리: $PID_DIR"
echo "⏰ 확인 시간: $(date)"
echo "📊 총 PID 파일: $pid_count개"
echo

if [ $pid_count -eq 0 ]; then
    echo "PID 파일이 없습니다."
    exit 0
fi

# 각 PID 파일 확인
echo "📋 프로세스 상태 및 체인 정보"
echo "════════════════════════════════════════════════════════════════════════════════"

running_processes=()
stopped_processes=()

for pid_file in "$PID_DIR"/*.pid; do
    if [ -f "$pid_file" ]; then
        filename=$(basename "$pid_file" .pid)
        
        # PID 읽기
        if [ -r "$pid_file" ]; then
            pid=$(cat "$pid_file" 2>/dev/null | tr -d '\n\r ')
            
            if [ -n "$pid" ] && [[ "$pid" =~ ^[0-9]+$ ]]; then
                # 프로세스 존재 여부 확인
                if kill -0 "$pid" 2>/dev/null; then
                    running_processes+=("$filename:$pid")
                else
                    stopped_processes+=("$filename:$pid")
                fi
            else
                stopped_processes+=("$filename:INVALID")
            fi
        else
            stopped_processes+=("$filename:UNREADABLE")
        fi
    fi
done

# 실행중인 프로세스 상세 정보
if [ ${#running_processes[@]} -gt 0 ]; then
    echo "🟢 실행중인 프로세스 (${#running_processes[@]}개)"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    for proc in "${running_processes[@]}"; do
        IFS=':' read -r name pid <<< "$proc"
        
        # 프로세스 기본 정보
        ps_info=$(ps -p "$pid" -o pid,ppid,user,cmd --no-headers 2>/dev/null)
        if [ -n "$ps_info" ]; then
            echo "📌 $name (PID: $pid)"
            echo "   $ps_info"
            
            # 프로세스 체인 정보
            echo "   🔗 프로세스 체인:"
            pstree -p "$pid" 2>/dev/null | sed 's/^/      /' || {
                # pstree가 없는 경우 대안
                parent_pid=$(ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ')
                if [ -n "$parent_pid" ] && [ "$parent_pid" != "0" ]; then
                    parent_cmd=$(ps -p "$parent_pid" -o cmd= 2>/dev/null)
                    echo "      └─ 부모: $parent_pid ($parent_cmd)"
                fi
                
                # 자식 프로세스 확인
                children=$(pgrep -P "$pid" 2>/dev/null)
                if [ -n "$children" ]; then
                    echo "      └─ 자식들:"
                    for child in $children; do
                        child_cmd=$(ps -p "$child" -o cmd= 2>/dev/null)
                        echo "         └─ $child ($child_cmd)"
                    done
                fi
            }
            echo
        fi
    done
fi

# 중지된 프로세스 정보
if [ ${#stopped_processes[@]} -gt 0 ]; then
    echo "🔴 중지된/문제있는 프로세스 (${#stopped_processes[@]}개)"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    for proc in "${stopped_processes[@]}"; do
        IFS=':' read -r name pid <<< "$proc"
        case "$pid" in
            "INVALID") echo "❌ $name - 잘못된 PID 형식" ;;
            "UNREADABLE") echo "❌ $name - PID 파일 읽기 불가" ;;
            *) echo "⏹️  $name (PID: $pid) - 프로세스 중지됨" ;;
        esac
    done
    echo
fi

echo "════════════════════════════════════════════════════════════════════════════════"

# 요약 정보
echo "📈 요약 정보"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "🟢 실행중인 프로세스: ${#running_processes[@]}개"
echo "🔴 중지된 프로세스: ${#stopped_processes[@]}개"
echo "📊 총 PID 파일: $pid_count개"
