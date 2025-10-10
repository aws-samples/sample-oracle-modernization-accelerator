"""
Analysis Report Generation Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime
import json


def render_app_reporting_page():
    """Analysis Report creation page"""
    # Add Home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="app_reporting_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📄 Analysis Report Creation")
    
    # Command Info
    command = './processAppReporting.sh'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/appReporting.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**Execute Command:** `{command}`")
    st.caption(f"📄 Log file: {expanded_log_path}")
    
    # Check running task execution
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 Analysis Report creation is already in progress.")
            
            # Task Stop button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🛑 Task Stop", key="stop_app_reporting", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ Task has been stopped.")
                        st.rerun()
                    else:
                        st.info("No task is currently running.")
            
            # Simple status display
            st.markdown("### 📊 Task Status")
            
            # Check log file creation
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                st.success(f"✅ Log file has been created ({file_size:,} bytes)")
                
                # Check background process completion and refresh menu
                current_process = st.session_state.oma_controller.current_process
                running_tasks = st.session_state.task_manager.get_running_tasks()
                
                # If process is complete, return to Home and refresh sidebar
                if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
                    st.success("🎉 Analysis Report creation has been completed!")
                    st.info("🏠 Updating menu status...")
                    time.sleep(1)
                    st.session_state.selected_action = None  # Home
                    st.rerun()
                
                # Add log view button
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📋 View Logs", key="view_logs_from_app_reporting", use_container_width=True):
                        st.session_state.selected_action = "view_running_logs"
                        st.rerun()
                with col2:
                    # Manual refresh button
                    if st.button("🔄 Status Refresh", key="refresh_app_reporting"):
                        st.rerun()
                
                # Auto refresh for real-time status check (every 3 seconds)
                time.sleep(3)
                st.rerun()
            else:
                st.info("⏳ Waiting for log file creation...")
                
                # Auto refresh only once (for file creation check)
                if st.button("🔄 Check Status", key="check_app_reporting"):
                    st.rerun()
        else:
            st.error("❌ Another task is currently running. Please complete or stop the existing task and try again.")
    else:
        # Display execute button
        st.markdown("### 🚀 Task Execute")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📄 Report Create", key="start_app_reporting", type="primary", use_container_width=True):
                # Start background execution
                execute_app_reporting_background(command, expanded_log_path)
                st.rerun()
        
        with col2:
            st.caption("Creates a report based on application analysis results")
        
        # Task description
        st.markdown("### 📋 Task Details")
        st.markdown("""
        **Analysis Report Creation Task:**
        - Compile application analysis results
        - Create SQL transformation target list
        - Transform complexity analysis
        - HTML/PDF report creation
        
        **Estimated Duration:** 5-15 minutes
        """)
        
        # Prerequisites
        st.info("💡 **Prerequisites:** The 'Application Analysis' task must be completed first.")
        
        # Precautions
        st.warning("⚠️ **Warning:** Other OMA tasks cannot be executed during report creation.")


def execute_app_reporting_background(command, log_file_path):
    """Execute Analysis Report creation in background (script creates logs automatically)"""
    try:
        # Task Info Create
        task_id = f"app_reporting_{int(time.time() * 1000)}"
        
        # Task File Create
        task_data = {
            "task_id": task_id,
            "title": "Analysis Report Creation",
            "command": command,
            "pid": None,  # Actual PID will be updated later
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "running",
            "log_file": log_file_path  # Log file path that script will create (for reference)
        }
        
        # Task Directory Create
        os.makedirs("./oma_tasks", exist_ok=True)
        
        # Save task file
        with open(f"./oma_tasks/{task_id}.json", 'w') as f:
            json.dump(task_data, f, indent=2)
        
        # Execute command in background (execute in $OMA_BASE_DIR/bin)
        bin_dir = os.path.join(os.path.expandvars("$OMA_BASE_DIR"), "bin")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=bin_dir,  # Execute in $OMA_BASE_DIR/bin
            preexec_fn=os.setsid  # Create process group (for safe termination)
        )
        
        # Register process with controller
        st.session_state.oma_controller.current_process = process
        
        # Update actual PID in task file
        task_data["pid"] = process.pid
        with open(f"./oma_tasks/{task_id}.json", 'w') as f:
            json.dump(task_data, f, indent=2)
        
        st.success("✅ Background execution started")
        
    except Exception as e:
        st.error(f"❌ Execution Error: {e}")
