"""
Java Source Transform Page
"""
import streamlit as st
from .utils import execute_command_with_logs

def render_java_transform_page():
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="java_transform_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## ☕ Java Source 변환")
    
    
    execute_command_with_logs("./processJavaConvert.sh", "Java Source 변환")
