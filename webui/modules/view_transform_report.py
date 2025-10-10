"""
View Transform Report Page
"""
import streamlit as st
import os
import glob
from datetime import datetime


def render_view_transform_report_page():
    """Transform Report 보기 페이지"""
    # Home 버튼
    if st.button("🏠 Home", key="view_transform_report_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    st.markdown("# 📄 Transform Report 보기")
    
    # APPLICATION_FOLDER 환경 변수 확인
    application_folder = os.environ.get('APPLICATION_FOLDER')
    
    if not application_folder:
        st.error("❌ APPLICATION_FOLDER 환경 변수가 not set.")
        return
    
    if not os.path.exists(application_folder):
        st.error(f"❌ APPLICATION_FOLDER Path가 존재하지 않습니다: {application_folder}")
        return
    
    # Transform-Report.html File 찾기 (가장 최신본)
    html_pattern = os.path.join(application_folder, "Transform-Report*.html")
    html_files = glob.glob(html_pattern)
    
    if not html_files:
        st.warning("⚠️ Transform-Report.html File을 not found.")
        st.info(f"📁 검색 Path: {html_pattern}")
        st.info("💡 Transform Report를 먼저 Create하세요.")
        return
    
    # 가장 최신 File 선택 (Modify Time 기준)
    latest_file = max(html_files, key=os.path.getmtime)
    file_mtime = os.path.getmtime(latest_file)
    file_size = os.path.getsize(latest_file)
    
    # File Info 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("File명", os.path.basename(latest_file))
    with col2:
        st.metric("File Size", f"{file_size:,} bytes")
    with col3:
        st.metric("Modify Time", datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S"))
    
    st.info(f"📁 **File Path:** {latest_file}")
    
    # HTML File 내용 읽기 및 표시
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # HTML 내용을 iframe으로 표시
        st.markdown("### 📊 Transform Report 내용")
        
        # HTML을 직접 렌더링
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # Download 버튼
        st.download_button(
            label="💾 Report Download",
            data=html_content,
            file_name=os.path.basename(latest_file),
            mime="text/html",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ HTML File을 읽을 수 없습니다: {str(e)}")
        
        # File 존재 여부 재확인
        if os.path.exists(latest_file):
            st.info("File은 존재하지만 읽기 권한이나 인코딩 문제일 수 있습니다.")
        else:
            st.error("File이 존재하지 않습니다.")
