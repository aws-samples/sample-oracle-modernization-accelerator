"""
Sample Transform Page
"""
import streamlit as st
import subprocess
import os
import time
import datetime


def render_full_transform_page():
    """Sample Transform Page"""
    # at the top Item add button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="full_transform_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 🚀 SQL Sample Transform")
    
    # Item Info (Item TransformText CSV File Item)
    command = 'python3 "$APP_TOOLS_FOLDER/sqlTransformTarget.py" --file "$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv"'
    log_file_path = "$APP_LOGS_FOLDER/pylogs/SQLTransformTarget.log"
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
                if st.button("🛑 Task Stop", key="stop_full_transform", type="secondary"):
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