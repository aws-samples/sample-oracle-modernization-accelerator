"""
Analysis Report Item Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime
import json


def render_app_reporting_page():
    """Analysis Report Item Page"""
    # at the top Item add button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="app_reporting_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📄 Analysis Report Item")
    
    # Item Info
    command = './processAppReporting.sh'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/appReporting.log"
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
                if st.button("🛑 Task Stop", key="stop_app_reporting", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ Task has been stopped.")
                        st.rerun()
                    if True:  # English only
                        st.info("Execute Item Task Item.")
            
            # Simple status display
            st.markdown("### 📊 Task Status")
            
            # Check log file creation
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                st.success(f"✅ Item FileText CreateText ({file_size:,} bytes)")
                
                # Check background process completion