"""
PostgreSQL Generation Page
"""
import streamlit as st
import subprocess
import os
import re
import html
import pandas as pd


def render_postgresql_meta_page():
    """PostgreSQL Generation Page"""
    # Item Page Report Item CSS
    st.markdown("""
    <style>
    .main .block-container {
        max-width: none !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .stTextArea > div > div > textarea {
        width: 100% !important;
        max-width: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Report Report Report
    if st.button("🏠 Home", key="postgresql_meta_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    # Report Item display
    st.markdown("# 🗄️ PostgreSQL Item")
    
    # Report
    tab1, tab2 = st.tabs(["📊 Generation", "🔍 Report"])
    
    with tab1:
        render_metadata_generation_tab()
    
    with tab2:
        render_metadata_verification_tab()


def render_metadata_generation_tab():
    """Generation Item"""
    st.markdown("## 📊 PostgreSQL Generation")
    
    # Item Info
    script_path = "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh"
    expanded_script_path = os.path.expandvars(script_path)
    
    st.info(f"**Execute Item:** `{script_path}`")
    st.caption(f"📄 Report: {expanded_script_path}")
    
    # Report Check
    if not os.path.exists(expanded_script_path):
        st.error(f"❌ Item FileText Report Item: {expanded_script_path}")
        st.info("💡 Environment Item ConfigText Check File Item Check.")
        return
    
    # Execute Item Task Check
    if st.session_state.oma_controller.is_any_task_running():
        st.error("❌ Another task is running. Please complete or stop the existing task and try again.")
