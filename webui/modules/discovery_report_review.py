"""
Discovery Report Review Page
"""
import streamlit as st
import os
import glob
from datetime import datetime


def render_discovery_report_review_page():
    """Analysis Report review page"""
    # Home button
    if st.button("🏠 Home", key="discovery_report_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    st.markdown("# 📋 Analysis Report Review")
    
    # Report File Path
    application_folder = os.path.expandvars("$APPLICATION_FOLDER")
    report_pattern = os.path.join(application_folder, "DiscoveryReport*.html")
    
    st.info(f"**Report Path:** `{report_pattern}`")
    st.caption(f"📄 Actual path: {application_folder}")
    
    # Check directory existence
    if not os.path.exists(application_folder):
        st.error(f"❌ APPLICATION_FOLDER not found: {application_folder}")
        st.info("💡 Please check environment variable settings.")
        return
    
    # Search for DiscoveryReport*.html files
    report_files = glob.glob(report_pattern)
    
    if not report_files:
        st.warning("📄 DiscoveryReport*.html files not found.")
        st.info("💡 Please first execute 'Application Analysis' → 'Generate Analysis Report'.")
        
        # Display file list in directory (for debugging)
        try:
            all_files = os.listdir(application_folder)
            html_files = [f for f in all_files if f.endswith('.html')]
            if html_files:
                st.markdown("### 📁 HTML Files in Directory:")
                for file in html_files:
                    st.text(f"  • {file}")
            else:
                st.info("No HTML files in directory.")
        except Exception as e:
            st.error(f"Directory read error: {e}")
        return
    
    # Find the latest file
    latest_report = max(report_files, key=os.path.getmtime)
    file_info = os.stat(latest_report)
    file_size = file_info.st_size
    modified_time = datetime.fromtimestamp(file_info.st_mtime)
    
    # Display file information
    st.success(f"✅ Latest report found!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Filename", os.path.basename(latest_report))
    with col2:
        st.metric("📊 File Size", f"{file_size:,} bytes")
    with col3:
        st.metric("🕒 Modify Time", modified_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Provide selection option when multiple files exist
    if len(report_files) > 1:
        st.markdown("### 📋 Report Selection")
        
        # Sort file list by modification time (newest first)
        sorted_files = sorted(report_files, key=os.path.getmtime, reverse=True)
        
        file_options = []
        for file_path in sorted_files:
            file_name = os.path.basename(file_path)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_options.append(f"{file_name} ({file_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        selected_index = st.selectbox(
            "Select Report:",
            range(len(file_options)),
            format_func=lambda x: file_options[x],
            key="report_selector"
        )
        
        selected_report = sorted_files[selected_index]
    else:
        selected_report = latest_report
    
    # Read and display HTML file content
    try:
        with open(selected_report, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        st.markdown("---")
        st.markdown("### 📊 Analysis Report")
        
        # Display HTML content as iframe
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # Download button
        st.markdown("### 📥 Download")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📄 HTML Download",
                data=html_content,
                file_name=os.path.basename(selected_report),
                mime="text/html",
                key="download_report"
            )
        with col2:
            st.caption("Save the report locally to view it offline.")
        
    except Exception as e:
        st.error(f"❌ Report file read error: {str(e)}")
        st.info("💡 The file may be corrupted or you may not have read permissions.")
