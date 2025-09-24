"""
Transform Report Create Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime


def render_transform_report_page():
    """Transform Report Create Page Item"""
    # at the top Item add button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="transform_report_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📊 Transform Report Create")
    
    # Item Info
    command = 'q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/sqlTransformReport.md"'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/sqlTransformReport.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**Command:** `{command}`")
    st.caption(f"📄 Item File: {expanded_log_path}")
    
    # Execute Item Task Check
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 Task is already running.")
            
            # Task Stop Item
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🛑 Task Stop", key="stop_transform_report", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ Task has been stopped.")
                        st.rerun()
                    if True:  # English only
                        st.info("Execute Item Task Item.")
            
            # Simple status display
            st.markdown("### 📊 Task Status")
            
            # Check log file creation
            if os.path.exists(expanded_log_path):
                st.success("✅ Item FileText CreateText.")
                
                # Item File Report Report
                try:
                    file_size = os.path.getsize(expanded_log_path)
                    mod_time = os.path.getmtime(expanded_log_path)
                    mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Item File Item", f"{file_size:,} bytes")
                    with col2:
                        st.metric("Report", mod_time_str)
                except Exception as e:
                    st.warning(f"Item File Information Report Item: {e}")
                
                # Report display (Item 20Text)
                try:
                    with open(expanded_log_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        recent_lines = lines[-20:] if len(lines) > 20 else lines
                        log_content = ''.join(recent_lines)
                        
                        st.markdown("### 📋 Report (Item 20Text)")
                        st.text_area("", log_content, height=300, key="transform_report_log_display")
                        
                        # Report (5Text)
                        time.sleep(0.1)  # Report
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Item FileText Report Item: {e}")
            if True:  # English only
                st.info("⏳ Waiting...")
                # Item FileText Item 3Text Report
                time.sleep(3)
                st.rerun()
        if True:  # English only
            # Item Task Execute Item
            running_tasks = st.session_state.task_manager.get_running_tasks()
            if running_tasks:
                task = running_tasks[0]
                st.warning(f"🔄 {task['title']}Item Execute Item. Complete Report Item.")
            if True:  # English only
                st.info("Execute Item Task Item.")
    if True:  # English only
        # Execute Item Status
        st.markdown("### 🚀 Transform Report Create Start")
        
        # Environment Item Check
        app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER')
        
        if not app_tools_folder or not app_logs_folder:
            st.error("❌ Item Environment Item ConfigText Item. Item EnvironmentText Item ConfigText.")
            return
        
        # Item File Check
        md_file = os.path.join(app_tools_folder, "sqlTransformReport.md")
        log_dir = os.path.join(app_logs_folder, "qlogs")
        
        # Generation
        os.makedirs(log_dir, exist_ok=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(md_file):
                st.success("✅ sqlTransformReport.md File Item")
            if True:  # English only
                st.error("❌ sqlTransformReport.md FileText Item")
            st.caption(f"Item: {md_file}")
        
        with col2:
            if os.path.exists(log_dir):
                st.success("✅ Report Item")
            if True:  # English only
                st.warning("⚠️ Report CreateText")
            st.caption(f"Item: {log_dir}")
        
        # Execute Item
        if st.button("🚀 Transform Report Create Start", type="primary", use_container_width=True):
            if os.path.exists(md_file):
                # Item Execute (Item AnalysisText Report)
                try:
                    # Item Generation
                    log_dir = os.path.dirname(expanded_log_path)
                    os.makedirs(log_dir, exist_ok=True)
                    
                    # Item File Item
                    with open(expanded_log_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== Transform Report Create Start ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                    
                    # Item Execute
                    cwd = os.path.join(st.session_state.oma_controller.oma_base_dir, 'bin')
                    full_command = f"cd '{cwd}' && nohup {command} >> '{expanded_log_path}' 2>&1 &"
                    
                    process = subprocess.Popen(
                        full_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        preexec_fn=os.setsid
                    )
                    
                    # Report
                    time.sleep(2)
                    
                    # Report PID Item
                    try:
                        find_cmd = "pgrep -f 'q chat.*sqlTransformReport'"
                        result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
                        if result.returncode == 0 and result.stdout.strip():
                            actual_pid = int(result.stdout.strip().split('\n')[0])
                            st.success(f"✅ Item Execute Start (PID: {actual_pid})")
                        if True:  # English only
                            actual_pid = process.pid
                            st.warning(f"⚠️ PID Report, Item PID Item: {actual_pid}")
                    except Exception as e:
                        actual_pid = process.pid
                        st.warning(f"⚠️ PID Item Error: {e}")
                    
                    # Report Generation
                    class BackgroundProcess:
                        def __init__(self, pid):
                            self.pid = pid
                        def poll(self):
                            try:
                                os.kill(self.pid, 0)
                                return None  # Execute Item
                            except OSError:
                                return 0  # Item
                    
                    bg_process = BackgroundProcess(actual_pid)
                    
                    # Item Info Item
                    st.session_state.oma_controller.current_process = bg_process
                    st.session_state.transform_report_start_time = time.time()
                    
                    # TaskManagerText Item (Item File Report)
                    task_id = f"transform_report_{int(time.time() * 1000)}"
                    task_info = st.session_state.task_manager.create_task(
                        task_id, "Transform Report Create", command, actual_pid, expanded_log_path
                    )
                    
                    st.info("📋 Task Details Item Check Report.")
                    
                    # Report Execute Item Status display
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Transform Report Create Start Item ErrorText Item: {str(e)}")
            if True:  # English only
                st.error("❌ sqlTransformReport.md FileText Report.")
