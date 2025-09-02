"""
XML Merge 페이지
"""
import streamlit as st
import subprocess
import os
import re
import html
import pandas as pd


def render_merge_transform_page():
    """XML Merge 실행 페이지"""
    # 전체 페이지 폭을 강제로 확장하는 CSS
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
    
    # 홈 버튼을 상단 좌측에 간단하게 배치
    if st.button("🏠 홈으로", key="merge_transform_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    # 제목을 전체 폭으로 표시
    st.markdown("# 🔗 XML Merge 실행")
    
    # 탭 구성
    tab1, tab2 = st.tabs(["🔗 XML Merge 실행", "📋 실행 결과"])
    
    with tab1:
        render_xml_merge_execution_tab()
    
    with tab2:
        render_xml_merge_results_tab()


def render_xml_merge_execution_tab():
    """XML Merge 실행 탭"""
    st.markdown("## 🔗 XML Merge 작업")
    
    # 작업 설명
    st.info("""
    **XML Merge 작업 순서:**
    1. 기존 타겟 XML 파일들 삭제 (`delete_target_xml_files.sh`)
    2. SQL 변환 Merge 작업 실행 (`processSqlTransform.sh merge`)
    
    이 작업은 변환된 SQL 파일들을 병합하여 최종 XML 파일을 생성합니다.
    """)
    
    # 환경 변수 확인
    app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
    oma_base_dir = os.environ.get('OMA_BASE_DIR')
    
    if not app_tools_folder or not oma_base_dir:
        st.error("❌ 필요한 환경 변수가 설정되지 않았습니다. 프로젝트 환경을 먼저 설정하세요.")
        return
    
    # 스크립트 파일 존재 확인
    delete_script = os.path.join(app_tools_folder, "..", "postTransform", "delete_target_xml_files.sh")
    transform_script = os.path.join(oma_base_dir, "bin", "processSqlTransform.sh")
    
    st.markdown("### 📁 스크립트 파일 확인")
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists(delete_script):
            st.success(f"✅ delete_target_xml_files.sh")
        else:
            st.error(f"❌ delete_target_xml_files.sh 파일이 없습니다")
        st.caption(f"경로: {delete_script}")
    
    with col2:
        if os.path.exists(transform_script):
            st.success(f"✅ processSqlTransform.sh")
        else:
            st.error(f"❌ processSqlTransform.sh 파일이 없습니다")
        st.caption(f"경로: {transform_script}")
    
    # 실행 버튼
    st.markdown("### 🚀 XML Merge 실행")
    
    # 실행 중인지 확인
    if st.session_state.oma_controller.is_any_task_running():
        st.warning("⚠️ 다른 작업이 실행 중입니다. 잠시 후 다시 시도하세요.")
        return
    
    if st.button("🔗 XML Merge 시작", type="primary", use_container_width=True):
        if os.path.exists(delete_script) and os.path.exists(transform_script):
            # 복합 명령어 구성
            command = f"{delete_script} && cd {oma_base_dir}/bin && ./processSqlTransform.sh merge"
            
            # TaskManager 없이 직접 실행
            execute_xml_merge_directly(command)
        else:
            st.error("❌ 필요한 스크립트 파일이 존재하지 않습니다.")


def execute_xml_merge_directly(command):
    """XML Merge를 TaskManager 없이 직접 실행"""
    st.info(f"🔗 **XML Merge 실행:** `{command}`")
    
    # 로그 컨테이너
    log_container = st.empty()
    
    try:
        # 프로세스 실행
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 실시간 로그 수집
        log_lines = []
        
        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue
            
            clean_line = line.rstrip('\n\r')
            if clean_line:
                log_lines.append(clean_line)
                
                # 로그 표시 (최근 100줄만)
                display_lines = log_lines[-100:] if len(log_lines) > 100 else log_lines
                log_text = '\n'.join(display_lines)
                
                with log_container.container():
                    st.markdown(f"""
                    <div class="log-container">
{log_text}
                    </div>
                    """, unsafe_allow_html=True)
        
        # 프로세스 완료 대기
        return_code = process.wait()
        
        if return_code == 0:
            st.success("✅ XML Merge 작업이 성공적으로 완료되었습니다!")
        else:
            st.error(f"❌ XML Merge 작업이 실패했습니다. (종료 코드: {return_code})")
            
    except Exception as e:
        st.error(f"❌ XML Merge 실행 중 오류가 발생했습니다: {str(e)}")


def render_xml_merge_results_tab():
    """XML Merge 결과 탭"""
    st.markdown("## 📋 XML Merge 실행 결과")
    
    # TARGET_SQL_MAPPER_FOLDER 확인
    target_sql_mapper_folder = os.environ.get('TARGET_SQL_MAPPER_FOLDER')
    
    if not target_sql_mapper_folder:
        st.warning("⚠️ TARGET_SQL_MAPPER_FOLDER 환경 변수가 설정되지 않았습니다.")
        return
    
    if not os.path.exists(target_sql_mapper_folder):
        st.error(f"❌ TARGET_SQL_MAPPER_FOLDER 경로가 존재하지 않습니다: {target_sql_mapper_folder}")
        return
    
    st.info(f"📁 **TARGET_SQL_MAPPER_FOLDER:** {target_sql_mapper_folder}")
    
    # 1/3, 2/3 컬럼 분할
    col_list, col_content = st.columns([1, 2])
    
    with col_list:
        st.markdown("### 🔍 XML 파일 목록")
        
        # 파일명 필터
        file_filter = st.text_input(
            "파일명 필터",
            value="",
            placeholder="예: mapper, user",
            help="파일명이나 경로에 포함된 텍스트로 필터링"
        )
        
        show_all = st.checkbox("모든 파일 표시", value=True)
        
        # XML 파일 검색
        xml_files = []
        if os.path.exists(target_sql_mapper_folder):
            for root, dirs, files in os.walk(target_sql_mapper_folder):
                for file in files:
                    if file.endswith('.xml'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, target_sql_mapper_folder)
                        
                        # 필터 적용
                        if show_all or not file_filter or file_filter.lower() in full_path.lower():
                            xml_files.append({
                                'name': file,
                                'rel_path': rel_path,
                                'full_path': full_path,
                                'size': os.path.getsize(full_path),
                                'dir': os.path.dirname(rel_path) if os.path.dirname(rel_path) else '.'
                            })
        
        # 결과 표시
        if xml_files:
            st.success(f"✅ {len(xml_files)}개 파일")
            
            # 표 형태로 표시
            # 데이터프레임 생성
            df_data = []
            for xml_file in sorted(xml_files, key=lambda x: x['rel_path']):
                df_data.append({
                    '디렉토리': xml_file['dir'],
                    '파일명': xml_file['name'],
                    '크기': f"{xml_file['size']:,}",
                    '경로': xml_file['full_path']
                })
            
            df = pd.DataFrame(df_data)
            
            # 선택 가능한 표로 표시
            selected_indices = st.dataframe(
                df[['디렉토리', '파일명', '크기']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # 선택된 행이 있으면 파일 내용 표시
            if selected_indices.selection.rows:
                selected_idx = selected_indices.selection.rows[0]
                selected_file_path = df.iloc[selected_idx]['경로']
                st.session_state.selected_xml_file = selected_file_path
        
        else:
            if file_filter:
                st.info(f"'{file_filter}' 조건에 맞는 파일이 없습니다.")
            else:
                st.info("XML 파일이 없습니다.")
    
    with col_content:
        st.markdown("### 📄 XML 파일 내용")
        
        # 선택된 파일 내용 표시
        if 'selected_xml_file' in st.session_state and st.session_state.selected_xml_file:
            display_xml_content_inline(st.session_state.selected_xml_file)
        else:
            st.info("👈 왼쪽에서 XML 파일을 선택하세요.")


def display_xml_content_inline(file_path):
    """선택된 XML 파일 내용을 인라인으로 표시"""
    # 파일 정보
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    rel_path = os.path.relpath(file_path, os.environ.get('TARGET_SQL_MAPPER_FOLDER', ''))
    
    # 헤더 (파일 정보 + 닫기 버튼)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"**{file_name}**")
        st.caption(f"📁 {rel_path} | 💾 {file_size:,} bytes")
    with col2:
        if st.button("❌", key="close_xml_viewer", help="닫기"):
            del st.session_state.selected_xml_file
            st.rerun()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 통계 정보 (간단하게)
        line_count = len(content.split('\n'))
        char_count = len(content)
        sql_count = content.count('<select') + content.count('<insert') + content.count('<update') + content.count('<delete')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("라인", f"{line_count:,}")
        with col2:
            st.metric("문자", f"{char_count:,}")
        with col3:
            st.metric("SQL", f"{sql_count:,}")
        
        # XML 내용을 코드 블록으로 표시 (높이 조정)
        st.code(content, language='xml', line_numbers=True)
        
        # 다운로드 버튼
        st.download_button(
            "💾 파일 다운로드",
            data=content,
            file_name=file_name,
            mime="application/xml",
            key=f"download_{file_path}",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ 파일을 읽을 수 없습니다: {str(e)}")
        if st.button("🔄 다시 시도", key="retry_xml_read"):
            st.rerun()
