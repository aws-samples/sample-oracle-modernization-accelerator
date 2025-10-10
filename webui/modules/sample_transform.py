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
    
    # Command information
    command = 'python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --file "$APP_TRANSFORM_FOLDER/SampleTransformTarget.csv"'
    log_file_path = "$APP_LOGS_FOLDER/pylogs/SampleTransformTarget.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**Command:** `{command}`")
    st.caption(f"📄 Log file: {expanded_log_path}")
    
    # Check running tasks
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 Sample transformation is already running.")
            
            # Stop task button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🛑 Stop Task", key="stop_sample_transform", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ Task has been stopped.")
                        st.rerun()
                    else:
                        st.info("No running task found.")
            
            # Simple status display
            st.markdown("### 📊 Task Status")
            
            # Check log file creation
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                st.success(f"✅ Log file created ({file_size:,} bytes)")
                
                # Check background process completion and refresh menu
                current_process = st.session_state.oma_controller.current_process
                running_tasks = st.session_state.task_manager.get_running_tasks()
                
                # If process is completed, return to home and refresh sidebar
                if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
                    st.success("🎉 Sample transformation completed!")
                    st.info("🏠 Updating menu status...")
                    time.sleep(1)
                    st.session_state.selected_action = None  # Go to home
                    st.rerun()
                
                # Add view logs button
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📋 View Logs", key="view_logs_from_sample", use_container_width=True):
                        st.session_state.selected_action = "view_running_logs"
                        st.rerun()
                with col2:
                    # Manual refresh button
                    if st.button("🔄 Refresh Status", key="refresh_status"):
                        st.rerun()
                
                # Auto refresh for real-time status check (every 3 seconds)
                time.sleep(3)
                st.rerun()
            else:
                st.info("⏳ Waiting for log file creation...")
                
                # Auto refresh only once (for file creation check)
                if st.button("🔄 Check Status", key="check_status"):
                    st.rerun()
        else:
            st.error("❌ Another task is currently running. Please complete or stop the existing task before trying again.")
    else:
        # Show execute button
        st.markdown("### 🚀 Execute Task")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🧪 Start Sample Transform", key="start_sample_transform", type="primary", use_container_width=True):
                # Start background execution
                execute_sample_transform_background(command, expanded_log_path)
                st.rerun()
        
        with col2:
            st.caption("Transform sample SQL to PostgreSQL")
        
        # Task description
        st.markdown("### 📋 Task Details")
        st.markdown("""
        **Sample Transform Task:**
        - Transform SQL from SampleTransformTarget.csv file
        - Convert Oracle SQL to PostgreSQL SQL
        - Generate transformation results and logs
        
        **Estimated Duration:** 1-10 minutes depending on sample size
        """)
        
        # Precautions
        st.warning("⚠️ **Note:** No other OMA tasks can be executed during transformation.")


def execute_sample_transform_background(command, log_file_path):
    """Execute sample transformation in background"""
    try:
        # Create log directory
        log_dir = os.path.dirname(log_file_path)
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize log file
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"=== Sample Transform Started ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
        
        # Background execution
        cwd = os.path.join(st.session_state.oma_controller.oma_base_dir, 'bin')
        full_command = f"cd '{cwd}' && nohup {command} >> '{log_file_path}' 2>&1 &"
        
        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait briefly
        time.sleep(2)
        
        # Find actual process PID
        try:
            find_cmd = "pgrep -f 'python3.*sqlTransformTarget.py'"
            result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                actual_pid = int(result.stdout.strip().split('\n')[0])
                st.success(f"✅ Background execution started (PID: {actual_pid})")
            else:
                actual_pid = process.pid
                st.warning(f"⚠️ PID detection failed, using default PID: {actual_pid}")
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
        st.session_state.sample_transform_start_time = time.time()
        
        # Register with TaskManager (including log file path)
        task_id = f"sample_transform_{int(time.time() * 1000)}"
        task_info = st.session_state.task_manager.create_task(
            task_id, "Sample Transform", command, actual_pid, log_file_path
        )
        
        st.session_state.oma_controller.current_task_id = task_id
        
    except Exception as e:
        st.error(f"❌ Execution error: {e}")
