"""
Transform Report Item Page
"""
import streamlit as st
import os
import glob
from datetime import datetime


def render_view_transform_report_page():
    """Transform Report Item Page"""
    # Report
    if st.button("🏠 Home", key="view_transform_report_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    st.markdown("# 📄 Transform Report Item")
    
    # APPLICATION_FOLDER Environment Item Check
    application_folder = os.environ.get('APPLICATION_FOLDER')
    
    if not application_folder:
        st.error("❌ Environment variable is not set.")
        return
    
    if not os.path.exists(application_folder):
        st.error(f"❌ APPLICATION_FOLDER Report Item: {application_folder}")
        return
    
    # Transform-Report.html File Item (Report)
    html_pattern = os.path.join(application_folder, "Transform-Report*.html")
    html_files = glob.glob(html_pattern)
    
    if not html_files:
        st.warning("⚠️ Transform-Report.html FileText Report Item.")
        st.info(f"📁 Report: {html_pattern}")
        st.info("💡 Transform ReportText Item CreateText.")
        return
    
    # Report File Item (Report Item)
    latest_file = max(html_files, key=os.path.getmtime)
    file_mtime = os.path.getmtime(latest_file)
    file_size = os.path.getsize(latest_file)
    
    # File Info display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("FileText", os.path.basename(latest_file))
    with col2:
        st.metric("File Item", f"{file_size:,} bytes")
    with col3:
        st.metric("Report", datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S"))
    
    st.info(f"📁 **File Item:** {latest_file}")
    
    # HTML File Report Item display
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # HTML Item iframeText display
        st.markdown("### 📊 Transform Report Item")
        
        # HTMLText Report
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # Report
        st.download_button(
            label="💾 Report Item",
            data=html_content,
            file_name=os.path.basename(latest_file),
            mime="text/html",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ HTML FileText Report Item: {str(e)}")
        
        # File Report TextCheck
        if os.path.exists(latest_file):
            st.info("FileText Report Report Report Item.")
        if True:  # English only
            st.error("FileText Report.")
