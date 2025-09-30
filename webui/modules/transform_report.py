"""
변환 보고서 생성 페이지
"""
import streamlit as st
import subprocess
import os
import time
import datetime


def render_transform_report_page():
    """변환 보고서 생성 페이지 렌더링"""
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="transform_report_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📊 변환 보고서 생성")
    
    # 명령어 정보
    command = 'q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/sqlTransformReport.md"'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/sqlTransformReport.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**실행 명령어:** `{command}`")
    st.caption(f"📄 로그 파일: {expanded_log_path}")
    
    # 실행 중인 작업 확인
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 변환 보고서 생성이 이미 실행 중입니다.")
            
            # 작업 중단 버튼
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🛑 작업 중단", key="stop_transform_report", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ 작업이 중단되었습니다.")
                        st.rerun()
                    else:
                        st.info("실행 중인 작업이 없습니다.")
            
            # 간단한 상태 표시
            st.markdown("### 📊 작업 상태")
            
            # 로그 파일 생성 확인
            if os.path.exists(expanded_log_path):
                st.success("✅ 로그 파일이 생성되었습니다.")
                
                # 로그 파일 크기 및 수정 시간
                try:
                    file_size = os.path.getsize(expanded_log_path)
                    mod_time = os.path.getmtime(expanded_log_path)
                    mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("로그 파일 크기", f"{file_size:,} bytes")
                    with col2:
                        st.metric("마지막 수정", mod_time_str)
                except Exception as e:
                    st.warning(f"로그 파일 정보를 가져올 수 없습니다: {e}")
                
                # 실시간 로그 표시 (마지막 20줄)
                try:
                    with open(expanded_log_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        recent_lines = lines[-20:] if len(lines) > 20 else lines
                        log_content = ''.join(recent_lines)
                        
                        st.markdown("### 📋 최근 로그 (마지막 20줄)")
                        st.text_area("", log_content, height=300, key="transform_report_log_display")
                        
                        # 자동 새로고침 (5초마다)
                        time.sleep(0.1)  # 짧은 지연
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"로그 파일을 읽을 수 없습니다: {e}")
            else:
                st.info("⏳ 로그 파일 생성 대기 중...")
                # 로그 파일이 없으면 3초 후 새로고침
                time.sleep(3)
                st.rerun()
        else:
            # 다른 작업이 실행 중
            running_tasks = st.session_state.task_manager.get_running_tasks()
            if running_tasks:
                task = running_tasks[0]
                st.warning(f"🔄 {task['title']}이 실행 중입니다. 완료 후 다시 시도하세요.")
            else:
                st.info("실행 중인 작업이 없습니다.")
    else:
        # 실행 가능한 상태
        st.markdown("### 🚀 변환 보고서 생성 시작")
        
        # 환경 변수 확인
        app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER')
        
        if not app_tools_folder or not app_logs_folder:
            st.error("❌ 필요한 환경 변수가 설정되지 않았습니다. 프로젝트 환경을 먼저 설정하세요.")
            return
        
        # 필요한 파일 확인
        md_file = os.path.join(app_tools_folder, "sqlTransformReport.md")
        log_dir = os.path.join(app_logs_folder, "qlogs")
        
        # 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(md_file):
                st.success("✅ sqlTransformReport.md 파일 존재")
            else:
                st.error("❌ sqlTransformReport.md 파일이 없습니다")
            st.caption(f"경로: {md_file}")
        
        with col2:
            if os.path.exists(log_dir):
                st.success("✅ 로그 디렉토리 존재")
            else:
                st.warning("⚠️ 로그 디렉토리가 생성됩니다")
            st.caption(f"경로: {log_dir}")
        
        # 실행 버튼
        if st.button("🚀 변환 보고서 생성 시작", type="primary", use_container_width=True):
            if os.path.exists(md_file):
                # 백그라운드 실행 (애플리케이션 분석과 동일한 방식)
                try:
                    # 로그 디렉토리 생성
                    log_dir = os.path.dirname(expanded_log_path)
                    os.makedirs(log_dir, exist_ok=True)
                    
                    # 로그 파일 초기화
                    with open(expanded_log_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== 변환 보고서 생성 시작 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                    
                    # 백그라운드 실행
                    cwd = os.path.join(st.session_state.oma_controller.oma_base_dir, 'bin')
                    full_command = f"cd '{cwd}' && nohup {command} >> '{expanded_log_path}' 2>&1 &"
                    
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
                        find_cmd = "pgrep -f 'q chat.*sqlTransformReport'"
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
                    st.session_state.transform_report_start_time = time.time()
                    
                    # TaskManager에 등록 (로그 파일 경로 포함)
                    task_id = f"transform_report_{int(time.time() * 1000)}"
                    task_info = st.session_state.task_manager.create_task(
                        task_id, "변환 보고서 생성", command, actual_pid, expanded_log_path
                    )
                    
                    st.info("📋 진행 상황은 로그를 통해 확인할 수 있습니다.")
                    
                    # 즉시 새로고침하여 실행 중 상태 표시
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 변환 보고서 생성 시작 중 오류가 발생했습니다: {str(e)}")
            else:
                st.error("❌ sqlTransformReport.md 파일이 존재하지 않습니다.")
