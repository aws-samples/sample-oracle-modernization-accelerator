"""
Sample Transform Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime


def render_sample_transform_page():
    """Sample transform page"""
    # Add home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="sample_transform_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 🧪 SQL Sample Transform")
    
    # 명령어 정보
    command = 'python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --file "$APP_TRANSFORM_FOLDER/SampleTransformTarget.csv"'
    log_file_path = "$APP_LOGS_FOLDER/pylogs/SampleTransformTarget.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**실행 명령어:** `{command}`")
    st.caption(f"📄 로그 파일: {expanded_log_path}")
    
    # 실행 중인 작업 확인
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 샘플 변환이 이미 실행 중입니다.")
            
            # 작업 중단 버튼
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🛑 작업 중단", key="stop_sample_transform", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ 작업이 중단되었습니다.")
                        st.rerun()
                    else:
                        st.info("실행 중인 작업이 없습니다.")
            
            # 간단한 상태 표시
            st.markdown("### 📊 작업 상태")
            
            # 로그 파일 생성 확인
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                st.success(f"✅ 로그 파일이 생성되었습니다 ({file_size:,} bytes)")
                
                # 백그라운드 프로세스 완료 확인 및 메뉴 새로고침
                current_process = st.session_state.oma_controller.current_process
                running_tasks = st.session_state.task_manager.get_running_tasks()
                
                # 프로세스가 완료되었으면 홈으로 돌아가서 사이드바 새로고침
                if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
                    st.success("🎉 샘플 변환이 완료되었습니다!")
                    st.info("🏠 메뉴 상태를 업데이트합니다...")
                    time.sleep(1)
                    st.session_state.selected_action = None  # 홈으로
                    st.rerun()
                
                # 로그 보기 버튼 추가
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📋 로그 보기", key="view_logs_from_sample", use_container_width=True):
                        st.session_state.selected_action = "view_running_logs"
                        st.rerun()
                with col2:
                    # 수동 새로고침 버튼
                    if st.button("🔄 상태 새로고침", key="refresh_status"):
                        st.rerun()
                
                # 실시간 상태 확인을 위한 자동 새로고침 (3초마다)
                time.sleep(3)
                st.rerun()
            else:
                st.info("⏳ 로그 파일 생성 대기 중...")
                
                # 자동으로 한 번만 새로고침 (파일 생성 확인용)
                if st.button("🔄 상태 확인", key="check_status"):
                    st.rerun()
        else:
            st.error("❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.")
    else:
        # 실행 버튼 표시
        st.markdown("### 🚀 작업 실행")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🧪 샘플 변환 시작", key="start_sample_transform", type="primary", use_container_width=True):
                # 백그라운드 실행 시작
                execute_sample_transform_background(command, expanded_log_path)
                st.rerun()
        
        with col2:
            st.caption("샘플 SQL을 PostgreSQL로 변환합니다")
        
        # 작업 설명
        st.markdown("### 📋 작업 내용")
        st.markdown("""
        **샘플 변환 작업:**
        - SampleTransformTarget.csv 파일의 SQL 변환
        - Oracle SQL을 PostgreSQL SQL로 변환
        - 변환 결과 및 로그 생성
        
        **예상 소요 시간:** 샘플 크기에 따라 1-10분
        """)
        
        # 주의사항
        st.warning("⚠️ **주의사항:** 변환 작업 중에는 다른 OMA 작업을 실행할 수 없습니다.")


def execute_sample_transform_background(command, log_file_path):
    """샘플 변환을 백그라운드에서 실행"""
    try:
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(log_file_path)
        os.makedirs(log_dir, exist_ok=True)
        
        # 로그 파일 초기화
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"=== 샘플 변환 시작 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
        
        # 백그라운드 실행
        cwd = os.path.join(st.session_state.oma_controller.oma_base_dir, 'bin')
        full_command = f"cd '{cwd}' && nohup {command} >> '{log_file_path}' 2>&1 &"
        
        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # 잠시 대기
        time.sleep(2)
        
        # 실제 프로세스 PID 찾기
        try:
            find_cmd = "pgrep -f 'python3.*sqlTransformTarget.py'"
            result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                actual_pid = int(result.stdout.strip().split('\n')[0])
                st.success(f"✅ 백그라운드 실행 시작 (PID: {actual_pid})")
            else:
                actual_pid = process.pid
                st.warning(f"⚠️ PID 감지 실패, 기본 PID 사용: {actual_pid}")
        except Exception as e:
            actual_pid = process.pid
            st.warning(f"⚠️ PID 감지 오류: {e}")
        
        # 백그라운드 프로세스 객체 생성
        class BackgroundProcess:
            def __init__(self, pid):
                self.pid = pid
            def poll(self):
                try:
                    os.kill(self.pid, 0)
                    return None  # 실행 중
                except OSError:
                    return 0  # 종료됨
        
        bg_process = BackgroundProcess(actual_pid)
        
        # 프로세스 정보 저장
        st.session_state.oma_controller.current_process = bg_process
        st.session_state.sample_transform_start_time = time.time()
        
        # TaskManager에 등록 (로그 파일 경로 포함)
        task_id = f"sample_transform_{int(time.time() * 1000)}"
        task_info = st.session_state.task_manager.create_task(
            task_id, "샘플 변환", command, actual_pid, log_file_path
        )
        
        st.session_state.oma_controller.current_task_id = task_id
        
    except Exception as e:
        st.error(f"❌ 실행 오류: {e}")
