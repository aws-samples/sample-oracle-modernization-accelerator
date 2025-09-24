"""
Application Analysis Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime
from .utils import get_page_text, execute_command_with_logs


def render_app_analysis_page():
    """Render application analysis page"""
    
    # Add home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="app_analysis_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown(f"## {get_page_text('app_analysis_title')}")
    
    # Description
    st.markdown(f"**{get_page_text('app_analysis_desc')}**")
    
    # Command information
    command = 'q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appAnalysis.md"'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/appAnalysis.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**Command:** `{command}`")
    st.caption(f"{get_page_text('log_file')} {expanded_log_path}")
    
    # Check for running tasks
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 Application analysis is already running.")
            
            # Task stop button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(get_page_text("stop_task"), key="stop_app_analysis", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ Task has been stopped.")
                        st.rerun()
                    else:
                        st.info(get_page_text("no_running_task"))
            
            # Simple status display
            st.markdown("### 📊 Task Status")
            
            # Check log file creation
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                st.success(f"✅ Log file created ({file_size:,} bytes)")
                
                # Check background process completion and refresh menu
                current_process = st.session_state.oma_controller.current_process
                running_tasks = st.session_state.task_manager.get_running_tasks()
                
                # If process completed, return to home and refresh sidebar
                if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
                    st.success("🎉 Application analysis completed!")
                    st.info("🏠 Updating menu status...")
                    time.sleep(1)
                    st.session_state.selected_action = None  # Return to home
                    st.rerun()
                
                # Add view logs button
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📋 View Logs", key="view_logs_from_analysis", use_container_width=True):
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
                
                # Auto refresh once only (for file creation check)
                if st.button("🔄 Check Status", key="check_status"):
                    st.rerun()
        else:
            st.error("❌ Another task is running. Please complete or stop the existing task and try again.")
