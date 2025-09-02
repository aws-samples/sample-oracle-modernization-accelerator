"""
변환 보고서 보기 페이지
"""
import streamlit as st
import os
import glob
from datetime import datetime


def render_view_transform_report_page():
    """변환 보고서 보기 페이지"""
    # 홈 버튼
    if st.button("🏠 홈으로", key="view_transform_report_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    st.markdown("# 📄 변환 보고서 보기")
    
    # APPLICATION_FOLDER 환경 변수 확인
    application_folder = os.environ.get('APPLICATION_FOLDER')
    
    if not application_folder:
        st.error("❌ APPLICATION_FOLDER 환경 변수가 설정되지 않았습니다.")
        return
    
    if not os.path.exists(application_folder):
        st.error(f"❌ APPLICATION_FOLDER 경로가 존재하지 않습니다: {application_folder}")
        return
    
    # Transform-Report.html 파일 찾기 (가장 최신본)
    html_pattern = os.path.join(application_folder, "Transform-Report*.html")
    html_files = glob.glob(html_pattern)
    
    if not html_files:
        st.warning("⚠️ Transform-Report.html 파일을 찾을 수 없습니다.")
        st.info(f"📁 검색 경로: {html_pattern}")
        st.info("💡 변환 보고서를 먼저 생성하세요.")
        return
    
    # 가장 최신 파일 선택 (수정 시간 기준)
    latest_file = max(html_files, key=os.path.getmtime)
    file_mtime = os.path.getmtime(latest_file)
    file_size = os.path.getsize(latest_file)
    
    # 파일 정보 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("파일명", os.path.basename(latest_file))
    with col2:
        st.metric("파일 크기", f"{file_size:,} bytes")
    with col3:
        st.metric("수정 시간", datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S"))
    
    st.info(f"📁 **파일 경로:** {latest_file}")
    
    # HTML 파일 내용 읽기 및 표시
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # HTML 내용을 iframe으로 표시
        st.markdown("### 📊 변환 보고서 내용")
        
        # HTML을 직접 렌더링
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # 다운로드 버튼
        st.download_button(
            label="💾 보고서 다운로드",
            data=html_content,
            file_name=os.path.basename(latest_file),
            mime="text/html",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ HTML 파일을 읽을 수 없습니다: {str(e)}")
        
        # 파일 존재 여부 재확인
        if os.path.exists(latest_file):
            st.info("파일은 존재하지만 읽기 권한이나 인코딩 문제일 수 있습니다.")
        else:
            st.error("파일이 존재하지 않습니다.")
