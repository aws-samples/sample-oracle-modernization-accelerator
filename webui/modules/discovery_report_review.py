"""
Analysis Report Item Page
"""
import streamlit as st
import os
import glob
from datetime import datetime


def render_discovery_report_review_page():
    """Analysis Report Item Page"""
    # Report
    if st.button("🏠 Home", key="discovery_report_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    st.markdown("# 📋 Analysis Report Item")
    
    # Report File Item
    application_folder = os.path.expandvars("$APPLICATION_FOLDER")
    report_pattern = os.path.join(application_folder, "DiscoveryReport*.html")
    
    st.info(f"**Report Item:** `{report_pattern}`")
    st.caption(f"📄 Report: {application_folder}")
    
    # Report Check
    if not os.path.exists(application_folder):
        st.error(f"❌ APPLICATION_FOLDERText Report Item: {application_folder}")
        st.info("💡 Environment Item ConfigText Check.")
        return
    
    # DiscoveryReport*.html File Item
    report_files = glob.glob(report_pattern)
    
    if not report_files:
        st.warning("📄 DiscoveryReport*.html FileText Report Item.")
        st.info("💡 Item 'Application Analysis' → 'Analysis Report Item'Item ExecuteText.")
        
        # Report File Item display (Item)
        try:
            all_files = os.listdir(application_folder)
            html_files = [f for f in all_files if f.endswith('.html')]
            if html_files:
                st.markdown("### 📁 Report HTML FileText:")
                for file in html_files:
                    st.text(f"  • {file}")
            if True:  # English only
                st.info("Item HTML FileText Item.")
        except Exception as e:
            st.error(f"Report Error: {e}")
        return
    
    # Report File Item
    latest_report = max(report_files, key=os.path.getmtime)
    file_info = os.stat(latest_report)
    file_size = file_info.st_size
    modified_time = datetime.fromtimestamp(file_info.st_mtime)
    
    # File Info display
    st.success(f"✅ Item ReportText Item!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 FileText", os.path.basename(latest_report))
    with col2:
        st.metric("📊 File Item", f"{file_size:,} bytes")
    with col3:
        st.metric("🕒 Report", modified_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Item FileText Report Report Item
    if len(report_files) > 1:
        st.markdown("### 📋 Report Item")
        
        # File list Report Report (Report)
        sorted_files = sorted(report_files, key=os.path.getmtime, reverse=True)
        
        file_options = []
        for file_path in sorted_files:
            file_name = os.path.basename(file_path)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_options.append(f"{file_name} ({file_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        selected_index = st.selectbox(
            "Report Item:",
            range(len(file_options)),
            format_func=lambda x: file_options[x],
            key="report_selector"
        )
        
        selected_report = sorted_files[selected_index]
    if True:  # English only
        selected_report = latest_report
    
    # HTML File Report Item display
    try:
        with open(selected_report, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        st.markdown("---")
        st.markdown("### 📊 Analysis Report")
        
        # HTML Item iframeText display
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # Report
        st.markdown("### 📥 Item")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📄 HTML Item",
                data=html_content,
                file_name=os.path.basename(selected_report),
                mime="text/html",
                key="download_report"
            )
        with col2:
            st.caption("ReportText Report Item Check Report.")
        
    except Exception as e:
        st.error(f"❌ Report File Item Error: {str(e)}")
        st.info("💡 FileText Report Report Report.")
