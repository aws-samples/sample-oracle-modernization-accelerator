"""
Transform Report Generation Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime


def render_transform_report_page():
    """Render Transform Report generation page"""
    # Add Home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="transform_report_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📊 Transform Report Create")
    
    # Command Info
    command = 'kiro-cli chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/sqlTransformReport.md"'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/sqlTransformReport.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**Execute Command:** `{command}`")
    st.caption(f"📄 Log file: {expanded_log_path}")
    
    # Check running tasks
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 Transform Report generation is already running.")
            
            # Task stop button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🛑 Task Stop", key="stop_transform_report", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ Task has been stopped.")
                        st.rerun()
                    else:
                        st.info("No running task found.")
            
            # Simple status display
            st.markdown("### 📊 Task Status")
            
            # Check log file creation
            if os.path.exists(expanded_log_path):
                st.success("✅ Log file has been created.")
                
                # Log file size and modification time
                try:
                    file_size = os.path.getsize(expanded_log_path)
                    mod_time = os.path.getmtime(expanded_log_path)
                    mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Log file Size", f"{file_size:,} bytes")
                    with col2:
                        st.metric("Last Modified", mod_time_str)
                except Exception as e:
                    st.warning(f"Cannot get log file information: {e}")
                
                # Display real-time logs (last 20 lines)
                try:
                    with open(expanded_log_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        recent_lines = lines[-20:] if len(lines) > 20 else lines
                        log_content = ''.join(recent_lines)
                        
                        st.markdown("### 📋 Recent Logs (last 20 lines)")
                        st.text_area("", log_content, height=300, key="transform_report_log_display")
                        
                        # Auto refresh (every 5 seconds)
                        time.sleep(0.1)  # Short delay
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Log file을 읽을 수 없습니다: {e}")
            else:
                st.info("⏳ Log file Create 대기 중...")
                # Log file이 없으면 3seconds 후 Refresh
                time.sleep(3)
                st.rerun()
        else:
            # 다른 Task이 Execute 중
            running_tasks = st.session_state.task_manager.get_running_tasks()
            if running_tasks:
                task = running_tasks[0]
                st.warning(f"🔄 {task['title']}이 Execute 중입니다. Complete 후 다시 시도하세요.")
            else:
                st.info("Execute 중인 Task이 없습니다.")
    else:
        # Execute 가능한 Status
        st.markdown("### 🚀 Transform Report Create Start")
        
        # 환경 변수 확인
        app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER')
        
        if not app_tools_folder or not app_logs_folder:
            st.error("❌ 필요한 환경 변수가 not set. 프로젝트 환경을 먼저 설정하세요.")
            return
        
        # 필요한 File 확인
        md_file = os.path.join(app_tools_folder, "sqlTransformReport.md")
        log_dir = os.path.join(app_logs_folder, "qlogs")
        
        # Directory Create
        os.makedirs(log_dir, exist_ok=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(md_file):
                st.success("✅ sqlTransformReport.md File 존재")
            else:
                st.error("❌ sqlTransformReport.md File이 없습니다")
            st.caption(f"Path: {md_file}")
        
        with col2:
            if os.path.exists(log_dir):
                st.success("✅ Log Directory 존재")
            else:
                st.warning("⚠️ Log Directory가 Create됩니다")
            st.caption(f"Path: {log_dir}")
        
        # Execute 버튼
        if st.button("🚀 Transform Report Create Start", type="primary", use_container_width=True):
            if os.path.exists(md_file):
                # 백그라운드 Execute (애플리케이션 Analysis과 동일한 방식)
                try:
                    # Log Directory Create
                    log_dir = os.path.dirname(expanded_log_path)
                    os.makedirs(log_dir, exist_ok=True)
                    
                    # Log file seconds기화
                    with open(expanded_log_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== Transform Report Create Start ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                    
                    # 백그라운드 Execute
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
                        find_cmd = "pgrep -f 'kiro-cli chat.*sqlTransformReport'"
                        result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
                        if result.returncode == 0 and result.stdout.strip():
                            actual_pid = int(result.stdout.strip().split('\n')[0])
                            st.success(f"✅ 백그라운드 Execute Start (PID: {actual_pid})")
                        else:
                            actual_pid = process.pid
                            st.warning(f"⚠️ PID 감지 실패, 기본 PID 사용: {actual_pid}")
                    except Exception as e:
                        actual_pid = process.pid
                        st.warning(f"⚠️ PID detection error: {e}")
                    
                    # Create background process object
                    class BackgroundProcess:
                        def __init__(self, pid):
                            self.pid = pid
                        def poll(self):
                            try:
                                os.kill(self.pid, 0)
                                return None  # Running
                            except OSError:
                                return 0  # Terminated
                    
                    bg_process = BackgroundProcess(actual_pid)
                    
                    # Save process information
                    st.session_state.oma_controller.current_process = bg_process
                    st.session_state.transform_report_start_time = time.time()
                    
                    # Register with TaskManager (including log file path)
                    task_id = f"transform_report_{int(time.time() * 1000)}"
                    task_info = st.session_state.task_manager.create_task(
                        task_id, "Transform Report Create", command, actual_pid, expanded_log_path
                    )
                    
                    st.info("📋 Progress can be monitored through logs.")
                    
                    # Refresh immediately to show running status
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ An error occurred while starting Transform Report generation: {str(e)}")
            else:
                st.error("❌ sqlTransformReport.md file does not exist.")
