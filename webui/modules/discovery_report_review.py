"""
Discovery Report Review Page
"""
import streamlit as st
import os
import glob
from datetime import datetime


def render_discovery_report_review_page():
    """분석 보고서 리뷰 페이지"""
    # 홈 버튼
    if st.button("🏠 홈으로", key="discovery_report_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    st.markdown("# 📋 분석 보고서 리뷰")
    
    # 보고서 파일 경로
    application_folder = os.path.expandvars("$APPLICATION_FOLDER")
    report_pattern = os.path.join(application_folder, "DiscoveryReport*.html")
    
    st.info(f"**보고서 경로:** `{report_pattern}`")
    st.caption(f"📄 실제 경로: {application_folder}")
    
    # 디렉토리 존재 확인
    if not os.path.exists(application_folder):
        st.error(f"❌ APPLICATION_FOLDER를 찾을 수 없습니다: {application_folder}")
        st.info("💡 환경 변수 설정을 확인해주세요.")
        return
    
    # DiscoveryReport*.html 파일 검색
    report_files = glob.glob(report_pattern)
    
    if not report_files:
        st.warning("📄 DiscoveryReport*.html 파일을 찾을 수 없습니다.")
        st.info("💡 먼저 '애플리케이션 분석' → '분석 보고서 작성'을 실행해주세요.")
        
        # 디렉토리 내 파일 목록 표시 (디버깅용)
        try:
            all_files = os.listdir(application_folder)
            html_files = [f for f in all_files if f.endswith('.html')]
            if html_files:
                st.markdown("### 📁 디렉토리 내 HTML 파일들:")
                for file in html_files:
                    st.text(f"  • {file}")
            else:
                st.info("디렉토리에 HTML 파일이 없습니다.")
        except Exception as e:
            st.error(f"디렉토리 읽기 오류: {e}")
        return
    
    # 가장 최신 파일 찾기
    latest_report = max(report_files, key=os.path.getmtime)
    file_info = os.stat(latest_report)
    file_size = file_info.st_size
    modified_time = datetime.fromtimestamp(file_info.st_mtime)
    
    # 파일 정보 표시
    st.success(f"✅ 최신 보고서를 찾았습니다!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 파일명", os.path.basename(latest_report))
    with col2:
        st.metric("📊 파일 크기", f"{file_size:,} bytes")
    with col3:
        st.metric("🕒 수정 시간", modified_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # 여러 파일이 있는 경우 선택 옵션 제공
    if len(report_files) > 1:
        st.markdown("### 📋 보고서 선택")
        
        # 파일 목록을 수정 시간 순으로 정렬 (최신 순)
        sorted_files = sorted(report_files, key=os.path.getmtime, reverse=True)
        
        file_options = []
        for file_path in sorted_files:
            file_name = os.path.basename(file_path)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_options.append(f"{file_name} ({file_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        selected_index = st.selectbox(
            "보고서 선택:",
            range(len(file_options)),
            format_func=lambda x: file_options[x],
            key="report_selector"
        )
        
        selected_report = sorted_files[selected_index]
    else:
        selected_report = latest_report
    
    # HTML 파일 내용 읽기 및 표시
    try:
        with open(selected_report, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        st.markdown("---")
        st.markdown("### 📊 분석 보고서")
        
        # HTML 내용을 iframe으로 표시
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        # 다운로드 버튼
        st.markdown("### 📥 다운로드")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📄 HTML 다운로드",
                data=html_content,
                file_name=os.path.basename(selected_report),
                mime="text/html",
                key="download_report"
            )
        with col2:
            st.caption("보고서를 로컬에 저장하여 오프라인에서도 확인할 수 있습니다.")
        
    except Exception as e:
        st.error(f"❌ 보고서 파일 읽기 오류: {str(e)}")
        st.info("💡 파일이 손상되었거나 읽기 권한이 없을 수 있습니다.")
