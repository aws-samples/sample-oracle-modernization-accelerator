"""
Sample Transform Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime
from .utils import get_page_text


def render_sample_transform_page():
    """Sample transform page"""
    
    # Add home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="sample_transform_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown(f"## {get_page_text('sample_transform_title')}")
    
    # Description
    st.markdown(f"**{get_page_text('sample_transform_desc')}**")
    
    # Command information
    command = 'python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --file "$APP_TRANSFORM_FOLDER/SampleTransformTarget.csv"'
    log_file_path = "$APP_LOGS_FOLDER/pylogs/SampleTransformTarget.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**Command:** `{command}`")
    st.caption(f"{get_page_text('log_file')} {expanded_log_path}")
    
    # Check for running tasks
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 Sample transform is already running.")
            
            # Task stop button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(get_page_text("stop_task"), key="stop_sample_transform", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ Task has been stopped.")
                        st.success(success_text)
                        st.rerun()
                    else:
                        st.info(get_page_text("no_running_task"))
            
            # Simple status display
            status_text = "### 📊 Task Status" if False else "### 📊 Task Status"
            st.markdown(status_text)
            
            # Check log file creation
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                st.success(f"✅ Item FileText CreateText ({file_size:,} bytes)")
                
                # Check background process completion