"""
Compare SQL Test Page - XML File List and SQL Testing
"""
import streamlit as st
import os
import glob
import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time
import re
import pandas as pd
import datetime
import difflib


def render_source_sqls_page():
    """Compare SQL Test 페이지"""
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="source_sqls_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## ⚖️ Compare SQL Test")
    
    # 환경변수 확인
    app_logs_folder = os.getenv('APP_LOGS_FOLDER')
    if not app_logs_folder:
        st.error("❌ APP_LOGS_FOLDER 환경변수가 설정되지 않았습니다.")
        return
    
    # XML 파일 경로
    xml_pattern = os.path.join(app_logs_folder, 'mapper', '**', 'extract', '*.xml')
    xml_files = glob.glob(xml_pattern, recursive=True)
    
    if not xml_files:
        st.warning(f"⚠️ XML 파일을 찾을 수 없습니다: {xml_pattern}")
        st.info("경로를 확인하거나 매퍼 분석을 먼저 실행해주세요.")
        return
    
    # 조회 필터와 파일 목록을 좌우로 나누어 표시
    with st.expander("🔍 조회 및 파일 목록", expanded=True):
        # 컴팩트한 폰트를 위한 CSS
        st.markdown("""
        <style>
        .compact-filter .stSelectbox label,
        .compact-filter .stTextInput label {
            font-size: 12px !important;
            margin-bottom: 2px !important;
        }
        .compact-filter .stSelectbox div[data-baseweb="select"] > div,
        .compact-filter .stTextInput input {
            font-size: 12px !important;
            padding: 4px 8px !important;
            height: 32px !important;
        }
        .compact-filter .stButton button {
            font-size: 12px !important;
            padding: 4px 12px !important;
            height: 32px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 좌우 분할: 왼쪽 필터, 오른쪽 파일 목록
        col_filter, col_files = st.columns([1, 2])
        
        with col_filter:
            st.markdown("#### 🔍 조회 필터")
            st.markdown('<div class="compact-filter">', unsafe_allow_html=True)
            
            search_text = st.text_input(
                "파일명 검색",
                placeholder="파일명 입력...",
                key="xml_search"
            )
            
            search_path = st.text_input(
                "경로 검색", 
                placeholder="경로 입력...",
                key="path_search"
            )
            
            sql_type = st.selectbox(
                "SQL Type",
                ["전체", "select", "insert", "update", "delete"],
                key="sql_type_filter"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                apply_filter = st.button("🔍 필터", use_container_width=True)
            with col_btn2:
                reset_filter = st.button("🔄 초기화", use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_files:
            st.markdown("#### 📁 파일 목록")
            
            # 필터 적용
            filtered_files = apply_simple_file_filters(
                xml_files, app_logs_folder, search_text, search_path, 
                sql_type, apply_filter, reset_filter
            )
            
            # 파일 개수 표시
            st.markdown(f'<p style="font-size: 11px; color: #666; margin: 5px 0;">총 {len(xml_files)}개 중 {len(filtered_files)}개 표시</p>', unsafe_allow_html=True)
            
            # 파일 목록 (테이블 형태로만 표시)
            if filtered_files:
                display_simple_file_table(filtered_files, app_logs_folder)
            else:
                st.info("조건에 맞는 파일이 없습니다.")
    
    # Tab으로 구성된 하단 영역
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        display_tabbed_content(st.session_state.selected_xml_file)
    else:
        st.info("👆 위에서 XML 파일을 선택하세요.")


def display_explorer_style_list(xml_files, base_path):
    """Windows 탐색기 스타일의 파일 리스트 표시"""
    
    # 파일 정보를 데이터프레임으로 구성
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        relative_path = os.path.relpath(xml_file, base_path)
        dir_path = os.path.dirname(relative_path)
        file_size = os.path.getsize(xml_file)
        file_mtime = os.path.getmtime(xml_file)
        
        # 수정 시간 포맷팅
        mod_time = datetime.datetime.fromtimestamp(file_mtime).strftime("%m/%d %H:%M")
        
        file_data.append({
            '📄': '📄',  # 파일 아이콘
            '파일명': file_name,
            '경로': dir_path if dir_path != '.' else '/',
            '크기': format_file_size(file_size),
            '수정일': mod_time,
            '_full_path': xml_file,
            '_sort_size': file_size,
            '_sort_time': file_mtime
        })
    
    if not file_data:
        return
    
    df = pd.DataFrame(file_data)
    
    # 빠른 선택을 테이블 위에 배치 (작은 폰트)
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">빠른 선택:</p>', unsafe_allow_html=True)
    file_options = [f"{row['파일명']} ({row['경로']})" for _, row in df.iterrows()]
    
    # 현재 선택된 파일의 인덱스 찾기
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, (_, row) in enumerate(df.iterrows()):
            if row['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    # selectbox 변경 감지를 위한 키 생성
    selectbox_key = f"quick_file_selector_{len(xml_files)}"
    
    selected_index = st.selectbox(
        "파일 선택:",
        range(len(file_options)),
        index=current_selection,
        format_func=lambda x: file_options[x] if x < len(file_options) else "",
        key=selectbox_key,
        label_visibility="collapsed"
    )
    
    # selectbox 선택 처리 (즉시 반영)
    if selected_index is not None and selected_index < len(df):
        selected_file = df.iloc[selected_index]['_full_path']
        if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
            st.session_state.selected_xml_file = selected_file
            # SQL 테스트 결과 초기화 (새 파일 선택 시)
            if hasattr(st.session_state, 'sql_test_result'):
                del st.session_state.sql_test_result
            st.rerun()
    
    # 스타일링을 위한 CSS (더 작은 폰트)
    st.markdown("""
    <style>
    .compact-table .dataframe {
        font-size: 11px !important;
    }
    .compact-table .dataframe th {
        font-size: 11px !important;
        padding: 2px 6px !important;
        background-color: #f8f9fa !important;
        font-weight: bold !important;
        border-bottom: 1px solid #dee2e6 !important;
    }
    .compact-table .dataframe td {
        font-size: 11px !important;
        padding: 2px 6px !important;
        border-bottom: 1px solid #f1f3f4 !important;
        line-height: 1.2 !important;
    }
    .compact-table .dataframe tbody tr:hover {
        background-color: #e3f2fd !important;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 컴팩트 테이블 컨테이너
    st.markdown('<div class="compact-table">', unsafe_allow_html=True)
    
    # 테이블 형태로 표시 (클릭 가능)
    display_df = df[['📄', '파일명', '경로', '크기', '수정일']].copy()
    
    # 현재 선택된 파일 하이라이트를 위한 스타일 함수
    def highlight_selected_row(row):
        if hasattr(st.session_state, 'selected_xml_file'):
            current_file = df[df['파일명'] == row['파일명']]['_full_path'].iloc[0]
            if st.session_state.selected_xml_file == current_file:
                return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # 선택 가능한 테이블 (이벤트 처리 개선)
    event = st.dataframe(
        display_df.style.apply(highlight_selected_row, axis=1),
        use_container_width=True,
        height=200,  # 250px에서 200px로 더 줄임
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"file_table_{len(xml_files)}"
    )
    
    # 컴팩트 테이블 컨테이너 닫기
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 테이블 선택 이벤트 처리
    if event and hasattr(event, 'selection') and event.selection and 'rows' in event.selection:
        if event.selection['rows']:
            selected_row_index = event.selection['rows'][0]
            if selected_row_index < len(df):
                selected_file = df.iloc[selected_row_index]['_full_path']
                if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
                    st.session_state.selected_xml_file = selected_file
                    # SQL 테스트 결과 초기화 (새 파일 선택 시)
                    if hasattr(st.session_state, 'sql_test_result'):
                        del st.session_state.sql_test_result
                    st.rerun()


def display_tabbed_content(xml_file_path):
    """3개 Tab으로 구성된 컨텐츠 표시"""
    try:
        file_name = os.path.basename(xml_file_path)
        target_xml_path = get_target_xml_path(xml_file_path)
        
        # 2개 Tab 구성
        tab1, tab2 = st.tabs(["📄 XML 비교", "🧪 SQL Test"])
        
        with tab1:
            # XML 파일 비교
            display_xml_comparison_section(xml_file_path, target_xml_path, file_name)
            
            # Text Diff (같은 Tab 내에)
            if target_xml_path and os.path.exists(target_xml_path):
                st.markdown("---")
                display_text_diff_section(xml_file_path, target_xml_path)
        
        with tab2:
            # 테스트 파라미터 (SQL Test용)
            display_parameter_section(xml_file_path, form_key="sql_test")
            
            # SQL 테스트 (같은 Tab 내에)
            st.markdown("---")
            display_sql_test_section(xml_file_path, target_xml_path, test_type="sql")
            
    except Exception as e:
        st.error(f"❌ 컨텐츠 표시 오류: {str(e)}")


def display_xml_comparison_section(xml_file_path, target_xml_path, file_name):
    """XML 비교 섹션"""
    # 2단 구성: 왼쪽 Source XML, 오른쪽 Target XML
    col1, col2 = st.columns(2)
    
    with col1:
        source_lines = count_xml_lines(xml_file_path)
        st.markdown(f"#### 📄 Source XML ({source_lines}줄)")
        st.caption(f"파일: {file_name}")
        display_single_xml(xml_file_path, height=400)
    
    with col2:
        if target_xml_path and os.path.exists(target_xml_path):
            target_lines = count_xml_lines(target_xml_path)
            st.markdown(f"#### 🎯 Target XML ({target_lines}줄)")
            target_file_name = os.path.basename(target_xml_path)
            st.caption(f"파일: {target_file_name}")
            display_single_xml(target_xml_path, height=400)
        else:
            st.markdown("#### 🎯 Target XML")
            st.caption("Target XML을 찾을 수 없습니다.")
            if target_xml_path:
                st.info(f"예상 경로: {target_xml_path}")
            else:
                st.info("Target 경로를 계산할 수 없습니다.")


def display_text_diff_section(xml_file_path, target_xml_path):
    """Text Diff 섹션"""
    # Text Diff 버튼
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("🔍 Text Diff", key="text_diff_btn", use_container_width=True):
            st.session_state.show_text_diff = True
            st.rerun()
    with col2:
        if st.button("📄 개별 보기", key="individual_view_btn", use_container_width=True):
            st.session_state.show_text_diff = False
            st.rerun()
    with col3:
        if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
            if st.button("🙈 Diff 감추기", key="hide_diff_btn", use_container_width=True):
                st.session_state.show_text_diff = False
                st.rerun()
        else:
            st.button("🙈 Diff 감추기", key="hide_diff_btn_disabled", disabled=True, use_container_width=True)
    with col4:
        st.caption("텍스트 파일 차이점 비교")
    
    # Text Diff 결과 표시
    if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
        display_text_diff(xml_file_path, target_xml_path)


def display_sql_test_section(xml_file_path, target_xml_path, test_type="sql"):
    """SQL 테스트 섹션"""
    # Target 데이터베이스 타입 결정
    target_dbms_type = os.getenv('TARGET_DBMS_TYPE', 'postgresql')
    target_db_display = get_target_db_display_info(target_dbms_type)
    
    # 통합 SQL 테스트 버튼
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🧪 전체 SQL Test", key="full_sql_test_btn", type="primary", use_container_width=True):
            # Oracle 테스트 실행
            execute_sql_test(xml_file_path, "oracle", "source")
            
            # Target 테스트 실행 (Target XML이 있는 경우)
            if target_xml_path and os.path.exists(target_xml_path):
                execute_sql_test(target_xml_path, target_dbms_type, "target")
            
            st.rerun()
    
    with col2:
        if st.button("🧹 결과 지우기", key="clear_all_results_btn", use_container_width=True):
            if hasattr(st.session_state, 'oracle_test_result'):
                del st.session_state.oracle_test_result
            if hasattr(st.session_state, 'target_test_result'):
                del st.session_state.target_test_result
            st.rerun()
    
    with col3:
        test_info = f"Oracle + {target_db_display['name']} 동시 테스트"
        if not target_xml_path or not os.path.exists(target_xml_path):
            test_info += " (Target XML 없음 - Oracle만 테스트)"
        st.caption(test_info)
    
    # 테스트 결과 표시
    display_dual_test_results(target_db_display['name'])


def display_simple_file_table(xml_files, base_path):
    """간단한 테이블 형태로 파일 리스트 표시"""
    
    # 파일 정보를 데이터프레임으로 구성
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        file_size = os.path.getsize(xml_file)
        
        file_data.append({
            '파일명': file_name,
            '크기': format_file_size(file_size),
            '_full_path': xml_file
        })
    
    if not file_data:
        return
    
    df = pd.DataFrame(file_data)
    
    # 현재 선택된 파일의 인덱스 찾기
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, (_, row) in enumerate(df.iterrows()):
            if row['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    # 선택된 행을 하이라이트하는 함수
    def highlight_selected_row(row):
        if hasattr(st.session_state, 'selected_xml_file'):
            current_file = df[df['파일명'] == row['파일명']]['_full_path'].iloc[0]
            if st.session_state.selected_xml_file == current_file:
                return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # 테이블 표시 (파일명과 크기만)
    display_df = df[['파일명', '크기']].copy()
    
    # 선택 가능한 테이블
    event = st.dataframe(
        display_df.style.apply(highlight_selected_row, axis=1),
        use_container_width=True,
        height=300,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"simple_file_table_{len(xml_files)}"
    )
    
    # 테이블 선택 이벤트 처리
    if event and hasattr(event, 'selection') and event.selection and 'rows' in event.selection:
        if event.selection['rows']:
            selected_row_index = event.selection['rows'][0]
            if selected_row_index < len(df):
                selected_file = df.iloc[selected_row_index]['_full_path']
                if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
                    st.session_state.selected_xml_file = selected_file
                    # SQL 테스트 결과 초기화
                    if hasattr(st.session_state, 'oracle_test_result'):
                        del st.session_state.oracle_test_result
                    if hasattr(st.session_state, 'target_test_result'):
                        del st.session_state.target_test_result
                    st.rerun()


def apply_simple_file_filters(xml_files, base_path, search_text, search_path, sql_type, apply_filter, reset_filter):
    """간소화된 파일 필터 적용"""
    
    # 필터 초기화
    if reset_filter:
        if 'xml_search' in st.session_state:
            st.session_state.xml_search = ""
        if 'path_search' in st.session_state:
            st.session_state.path_search = ""
        if 'sql_type_filter' in st.session_state:
            st.session_state.sql_type_filter = "전체"
        st.rerun()
    
    filtered_files = xml_files.copy()
    
    # 파일명 검색 필터
    if search_text:
        filtered_files = [
            f for f in filtered_files 
            if search_text.lower() in os.path.basename(f).lower()
        ]
    
    # 경로 검색 필터
    if search_path:
        filtered_files = [
            f for f in filtered_files 
            if search_path.lower() in os.path.relpath(f, base_path).lower()
        ]
    
    # SQL Type 필터 (파일명 기준)
    if sql_type and sql_type != "전체":
        filtered_files = [
            f for f in filtered_files 
            if sql_type.lower() in os.path.basename(f).lower()
        ]
    
    # 파일명 기준 정렬 (기본)
    filtered_files.sort(key=lambda x: os.path.basename(x).lower())
    
    return filtered_files


def display_compact_file_list(xml_files, base_path):
    """2단으로 나누어 컴팩트하게 파일 리스트 표시"""
    
    # 파일 정보를 리스트로 구성
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        file_size = os.path.getsize(xml_file)
        
        file_data.append({
            '파일명': file_name,
            '크기': format_file_size(file_size),
            '_full_path': xml_file
        })
    
    if not file_data:
        return
    
    # 빠른 선택을 위한 selectbox
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">빠른 선택:</p>', unsafe_allow_html=True)
    file_options = [f"{item['파일명']} ({item['크기']})" for item in file_data]
    
    # 현재 선택된 파일의 인덱스 찾기
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, item in enumerate(file_data):
            if item['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    selected_index = st.selectbox(
        "파일 선택:",
        range(len(file_options)),
        index=current_selection,
        format_func=lambda x: file_options[x] if x < len(file_options) else "",
        key=f"quick_file_selector_{len(xml_files)}",
        label_visibility="collapsed"
    )
    
    # selectbox 선택 처리
    if selected_index is not None and selected_index < len(file_data):
        selected_file = file_data[selected_index]['_full_path']
        if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
            st.session_state.selected_xml_file = selected_file
            # SQL 테스트 결과 초기화
            if hasattr(st.session_state, 'oracle_test_result'):
                del st.session_state.oracle_test_result
            if hasattr(st.session_state, 'target_test_result'):
                del st.session_state.target_test_result
            st.rerun()
    
    # 2단으로 나누어 파일 목록 표시
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">파일 목록:</p>', unsafe_allow_html=True)
    
    # 파일을 2개씩 나누어 표시
    for i in range(0, len(file_data), 2):
        col1, col2 = st.columns(2)
        
        # 첫 번째 파일
        with col1:
            item = file_data[i]
            is_selected = (hasattr(st.session_state, 'selected_xml_file') and 
                          st.session_state.selected_xml_file == item['_full_path'])
            
            button_style = "primary" if is_selected else "secondary"
            if st.button(
                f"📄 {item['파일명']}\n📏 {item['크기']}", 
                key=f"file_btn_{i}",
                use_container_width=True,
                type=button_style
            ):
                st.session_state.selected_xml_file = item['_full_path']
                # SQL 테스트 결과 초기화
                if hasattr(st.session_state, 'oracle_test_result'):
                    del st.session_state.oracle_test_result
                if hasattr(st.session_state, 'target_test_result'):
                    del st.session_state.target_test_result
                st.rerun()
        
        # 두 번째 파일 (있는 경우)
        with col2:
            if i + 1 < len(file_data):
                item = file_data[i + 1]
                is_selected = (hasattr(st.session_state, 'selected_xml_file') and 
                              st.session_state.selected_xml_file == item['_full_path'])
                
                button_style = "primary" if is_selected else "secondary"
                if st.button(
                    f"📄 {item['파일명']}\n📏 {item['크기']}", 
                    key=f"file_btn_{i+1}",
                    use_container_width=True,
                    type=button_style
                ):
                    st.session_state.selected_xml_file = item['_full_path']
                    # SQL 테스트 결과 초기화
                    if hasattr(st.session_state, 'oracle_test_result'):
                        del st.session_state.oracle_test_result
                    if hasattr(st.session_state, 'target_test_result'):
                        del st.session_state.target_test_result
                    st.rerun()


def apply_file_filters(xml_files, base_path, search_text, search_path, min_size, max_size, sort_by, sort_order, apply_filter, reset_filter):
    """파일 필터 적용"""
    
    # 필터 초기화
    if reset_filter:
        if 'xml_search' in st.session_state:
            st.session_state.xml_search = ""
        if 'path_search' in st.session_state:
            st.session_state.path_search = ""
        if 'min_size_filter' in st.session_state:
            st.session_state.min_size_filter = 0
        if 'max_size_filter' in st.session_state:
            st.session_state.max_size_filter = 0
        st.rerun()
    
    filtered_files = xml_files.copy()
    
    # 파일명 검색 필터
    if search_text:
        filtered_files = [
            f for f in filtered_files 
            if search_text.lower() in os.path.basename(f).lower()
        ]
    
    # 경로 검색 필터
    if search_path:
        filtered_files = [
            f for f in filtered_files 
            if search_path.lower() in os.path.relpath(f, base_path).lower()
        ]
    
    # 크기 필터
    if min_size > 0 or max_size > 0:
        size_filtered = []
        for f in filtered_files:
            file_size_kb = os.path.getsize(f) / 1024
            
            if min_size > 0 and file_size_kb < min_size:
                continue
            if max_size > 0 and file_size_kb > max_size:
                continue
            
            size_filtered.append(f)
        
        filtered_files = size_filtered
    
    # 정렬 적용
    if sort_by == "파일명":
        filtered_files.sort(key=lambda x: os.path.basename(x).lower())
    elif sort_by == "경로":
        filtered_files.sort(key=lambda x: os.path.relpath(x, base_path).lower())
    elif sort_by == "크기":
        filtered_files.sort(key=lambda x: os.path.getsize(x))
    elif sort_by == "수정시간":
        filtered_files.sort(key=lambda x: os.path.getmtime(x))
    
    # 정렬 순서
    if sort_order == "내림차순":
        filtered_files.reverse()
    
    return filtered_files


def build_tree_structure(xml_files, base_path):
    """XML 파일들로부터 Tree 구조 생성"""
    tree = {}
    
    for xml_file in xml_files:
        # 상대 경로 계산
        rel_path = os.path.relpath(xml_file, base_path)
        path_parts = rel_path.split(os.sep)
        
        # Tree 구조에 경로 추가
        current_level = tree
        for i, part in enumerate(path_parts):
            if part not in current_level:
                if i == len(path_parts) - 1:  # 파일인 경우
                    current_level[part] = {
                        '_type': 'file',
                        '_path': xml_file,
                        '_size': os.path.getsize(xml_file)
                    }
                else:  # 디렉토리인 경우
                    current_level[part] = {'_type': 'directory'}
            
            if current_level[part]['_type'] == 'directory':
                current_level = current_level[part]
    
    return tree


def display_tree_structure(tree, base_path, level=0, parent_key=""):
    """Tree 구조를 재귀적으로 표시"""
    for key, value in sorted(tree.items()):
        if key.startswith('_'):  # 메타데이터 스킵
            continue
        
        indent = "　" * level  # 전각 공백으로 들여쓰기
        current_key = f"{parent_key}_{key}" if parent_key else key
        
        if value['_type'] == 'directory':
            # 디렉토리 표시
            folder_key = f"folder_{current_key}_{level}"
            
            # 하위 파일 개수 계산
            file_count = count_files_in_tree(value)
            
            with st.expander(f"{indent}📁 {key} ({file_count}개)", expanded=level < 2):
                display_tree_structure(value, base_path, level + 1, current_key)
        
        elif value['_type'] == 'file':
            # 파일 표시
            file_size = value['_size']
            file_size_str = format_file_size(file_size)
            
            file_key = f"file_{current_key}_{level}"
            
            # 파일 선택 버튼
            if st.button(
                f"{indent}📄 {key} ({file_size_str})",
                key=file_key,
                use_container_width=True,
                help=f"경로: {os.path.relpath(value['_path'], base_path)}"
            ):
                st.session_state.selected_xml_file = value['_path']
                st.rerun()


def count_files_in_tree(tree_node):
    """Tree 노드 내의 파일 개수 계산"""
    count = 0
    for key, value in tree_node.items():
        if key.startswith('_'):
            continue
        
        if value['_type'] == 'file':
            count += 1
        elif value['_type'] == 'directory':
            count += count_files_in_tree(value)
    
    return count


def format_file_size(size_bytes):
    """파일 크기를 읽기 쉬운 형태로 포맷"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"


def display_xml_content(xml_file_path):
    """XML 파일 내용 표시 - Source와 Target 2단 구성"""
    try:
        file_name = os.path.basename(xml_file_path)
        
        # Target XML 경로 계산
        target_xml_path = get_target_xml_path(xml_file_path)
        
        # 2단 구성: 왼쪽 Source XML, 오른쪽 Target XML
        col1, col2 = st.columns(2)
        
        with col1:
            source_lines = count_xml_lines(xml_file_path)
            st.markdown(f"#### 📄 Source XML ({source_lines}줄)")
            st.caption(f"파일: {file_name}")
            display_single_xml(xml_file_path, height=400)
        
        with col2:
            if target_xml_path and os.path.exists(target_xml_path):
                target_lines = count_xml_lines(target_xml_path)
                st.markdown(f"#### 🎯 Target XML ({target_lines}줄)")
                target_file_name = os.path.basename(target_xml_path)
                st.caption(f"파일: {target_file_name}")
                display_single_xml(target_xml_path, height=400)
            else:
                st.markdown("#### 🎯 Target XML")
                st.caption("Target XML을 찾을 수 없습니다.")
                if target_xml_path:
                    st.info(f"예상 경로: {target_xml_path}")
                else:
                    st.info("Target 경로를 계산할 수 없습니다.")
        
        # SQL 테스트 파라미터 섹션
        st.markdown("---")
        display_parameter_section(xml_file_path)
        
        # Target 데이터베이스 타입 결정
        target_dbms_type = os.getenv('TARGET_DBMS_TYPE', 'postgresql')
        target_db_display = get_target_db_display_info(target_dbms_type)
        
        # SQL 테스트 버튼 (2개로 분리)
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🧪 Source SQL Test (Oracle)")
            if st.button("🗄️ Oracle Test", key="oracle_test_btn", type="primary", use_container_width=True):
                execute_sql_test(xml_file_path, "oracle", "source")
                st.rerun()
            st.caption("Source XML을 Oracle 데이터베이스에서 테스트")
        
        with col2:
            st.markdown(f"#### 🧪 Target SQL Test ({target_db_display['name']})")
            if target_xml_path and os.path.exists(target_xml_path):
                if st.button(f"{target_db_display['icon']} {target_db_display['name']} Test", key="target_test_btn", type="primary", use_container_width=True):
                    execute_sql_test(target_xml_path, target_dbms_type, "target")
                    st.rerun()
                st.caption(f"Target XML을 {target_db_display['name']} 데이터베이스에서 테스트")
            else:
                st.button(f"{target_db_display['icon']} {target_db_display['name']} Test", key="target_test_btn_disabled", disabled=True, use_container_width=True)
                st.caption("Target XML이 없어서 테스트할 수 없습니다")
        
        # 테스트 결과 표시 (2개로 분리)
        display_dual_test_results(target_db_display['name'])
        
        # Text Diff 비교 버튼
        if target_xml_path and os.path.exists(target_xml_path):
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                if st.button("🔍 Text Diff", key="text_diff_btn", use_container_width=True):
                    st.session_state.show_text_diff = True
                    st.rerun()
            with col2:
                if st.button("📄 개별 보기", key="individual_view_btn", use_container_width=True):
                    st.session_state.show_text_diff = False
                    st.rerun()
            with col3:
                if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
                    if st.button("🙈 Diff 감추기", key="hide_diff_btn", use_container_width=True):
                        st.session_state.show_text_diff = False
                        st.rerun()
                else:
                    st.button("🙈 Diff 감추기", key="hide_diff_btn_disabled", disabled=True, use_container_width=True)
            with col4:
                st.caption("텍스트 파일 차이점 비교")
        
        # Text Diff 결과 표시
        if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff and target_xml_path and os.path.exists(target_xml_path):
            display_text_diff(xml_file_path, target_xml_path)
    
    except Exception as e:
        st.error(f"❌ XML 파일 읽기 오류: {str(e)}")


def count_xml_lines(xml_file_path):
    """XML 파일의 라인 수 계산"""
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 빈 줄 제외하고 실제 내용이 있는 줄만 카운트
            non_empty_lines = [line for line in lines if line.strip()]
            return len(non_empty_lines)
    except Exception as e:
        return 0


def get_target_xml_path(source_xml_path):
    """Source XML 경로에서 Target XML 경로 계산"""
    try:
        # 경로에서 ../transform/ 경로로 변경
        path_parts = source_xml_path.split(os.sep)
        
        # extract를 transform으로 변경
        if 'extract' in path_parts:
            extract_index = path_parts.index('extract')
            path_parts[extract_index] = 'transform'
        else:
            return None
        
        # 파일명에서 src를 tgt로 변경
        file_name = path_parts[-1]
        if 'src' in file_name:
            target_file_name = file_name.replace('src', 'tgt')
            path_parts[-1] = target_file_name
        else:
            return None
        
        target_path = os.sep.join(path_parts)
        return target_path
        
    except Exception as e:
        st.warning(f"⚠️ Target XML 경로 계산 오류: {str(e)}")
        return None


def display_text_diff(source_file_path, target_file_path):
    """Source와 Target 텍스트 파일의 diff 표시"""
    try:
        st.markdown("#### 🔍 Text Diff 비교")
        
        # 파일 읽기
        with open(source_file_path, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        with open(target_file_path, 'r', encoding='utf-8') as f:
            target_content = f.read()
        
        # 라인별로 분할
        source_lines = source_content.splitlines()
        target_lines = target_content.splitlines()
        
        # 통계 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Source 라인", len(source_lines))
        with col2:
            st.metric("Target 라인", len(target_lines))
        with col3:
            line_diff = len(target_lines) - len(source_lines)
            st.metric("라인 차이", f"{line_diff:+d}")
        
        # unified diff 생성
        unified_diff = list(difflib.unified_diff(
            source_lines,
            target_lines,
            fromfile=f"Source: {os.path.basename(source_file_path)}",
            tofile=f"Target: {os.path.basename(target_file_path)}",
            lineterm='',
            n=3
        ))
        
        if unified_diff:
            diff_text = '\n'.join(unified_diff)
            st.code(diff_text, language="diff")
        else:
            st.success("✅ 두 파일이 동일합니다!")
        
    except Exception as e:
        st.error(f"❌ Text Diff 비교 오류: {str(e)}")


def display_single_xml(xml_file_path, height=400):
    """단일 XML 파일 내용 표시"""
    try:
        # XML 내용 읽기 및 표시
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # XML 포맷팅 (예쁘게 표시)
        try:
            # XML 파싱 및 포맷팅
            root = ET.fromstring(xml_content)
            pretty_xml = minidom.parseString(xml_content).toprettyxml(indent="  ")
            # XML 선언 제거 (첫 번째 줄)
            pretty_lines = pretty_xml.split('\n')[1:]
            formatted_xml = '\n'.join(line for line in pretty_lines if line.strip())
        except:
            # 파싱 실패 시 원본 사용
            formatted_xml = xml_content
        
        # XML 내용 표시
        st.code(formatted_xml, language="xml", height=height)
        
    except Exception as e:
        st.error(f"❌ XML 파일 읽기 오류: {str(e)}")


def format_file_size(size_bytes):
    """파일 크기를 읽기 쉬운 형태로 포맷"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"


def extract_parameters_from_xml(xml_file_path):
    """XML 파일에서 MyBatis 파라미터 추출"""
    parameters = set()
    
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # #{parameter} 형태의 파라미터 추출
        import re
        param_pattern = r'#\{([^}]+)\}'
        matches = re.findall(param_pattern, xml_content)
        
        for match in matches:
            # 파라미터명만 추출 (타입 정보 등 제거)
            param_name = match.split(',')[0].strip()
            if param_name:
                parameters.add(param_name)
        
        # ${parameter} 형태의 파라미터도 추출
        param_pattern2 = r'\$\{([^}]+)\}'
        matches2 = re.findall(param_pattern2, xml_content)
        
        for match in matches2:
            param_name = match.split(',')[0].strip()
            if param_name:
                parameters.add(param_name)
    
    except Exception as e:
        st.warning(f"⚠️ XML 파라미터 추출 오류: {str(e)}")
    
    return sorted(list(parameters))


def display_parameter_section(xml_file_path, form_key="default"):
    """SQL 테스트 파라미터 섹션 표시"""
    st.markdown("#### ⚙️ 테스트 파라미터")
    
    # XML에서 파라미터 추출
    xml_parameters = extract_parameters_from_xml(xml_file_path)
    
    if not xml_parameters:
        st.info("📝 이 XML 파일에는 파라미터가 없습니다.")
        return
    
    # 파라미터 파일 경로
    test_folder = os.getenv('TEST_FOLDER')
    if not test_folder:
        st.error("❌ TEST_FOLDER 환경변수가 설정되지 않았습니다.")
        return
    
    param_file_path = os.path.join(test_folder, 'parameters.properties')
    
    # 기존 파라미터 로드
    existing_params = load_parameters(param_file_path)
    
    st.markdown(f"**📝 발견된 파라미터 ({len(xml_parameters)}개):**")
    
    # 파라미터 입력 폼
    with st.form(key=f"parameter_form_{form_key}"):
        # 동적으로 파라미터 입력 필드 생성
        param_values = {}
        
        # 2열로 배치
        cols = st.columns(2)
        for i, param_name in enumerate(xml_parameters):
            col_idx = i % 2
            with cols[col_idx]:
                # 파라미터 타입 추정
                param_type = guess_parameter_type(param_name)
                placeholder = get_parameter_placeholder(param_name, param_type)
                
                param_values[param_name] = st.text_input(
                    f"🔧 {param_name}",
                    value=existing_params.get(param_name, ''),
                    placeholder=placeholder,
                    help=f"타입: {param_type}"
                )
        
        # 저장 버튼
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            save_params = st.form_submit_button("💾 저장", type="primary")
        with col2:
            clear_params = st.form_submit_button("🧹 초기화")
        with col3:
            st.caption(f"파일: {os.path.basename(param_file_path)}")
    
    # 파라미터 저장 처리
    if save_params:
        save_xml_parameters(param_file_path, param_values, xml_file_path)
        st.success(f"✅ 파라미터가 저장되었습니다! ({form_key})")
        st.rerun()
    
    # 파라미터 초기화 처리
    if clear_params:
        clear_parameters(param_file_path)
        st.success(f"✅ 파라미터가 초기화되었습니다! ({form_key})")
        st.rerun()


def guess_parameter_type(param_name):
    """파라미터 이름으로부터 타입 추정"""
    param_lower = param_name.lower()
    
    if 'id' in param_lower:
        return 'ID'
    elif 'date' in param_lower or 'time' in param_lower:
        return 'Date'
    elif 'count' in param_lower or 'size' in param_lower or 'limit' in param_lower:
        return 'Number'
    elif 'name' in param_lower or 'title' in param_lower:
        return 'String'
    elif 'status' in param_lower or 'type' in param_lower:
        return 'Code'
    elif 'email' in param_lower:
        return 'Email'
    elif 'phone' in param_lower:
        return 'Phone'
    else:
        return 'String'


def get_parameter_placeholder(param_name, param_type):
    """파라미터 타입에 따른 placeholder 생성"""
    placeholders = {
        'ID': f'예: {param_name.upper()}001',
        'Date': '예: 2024-01-01',
        'Number': '예: 10',
        'String': f'예: {param_name} 값',
        'Code': '예: ACTIVE',
        'Email': '예: test@example.com',
        'Phone': '예: 010-1234-5678'
    }
    return placeholders.get(param_type, f'예: {param_name} 값')


def save_xml_parameters(param_file_path, param_values, xml_file_path):
    """XML 파라미터를 파일에 저장"""
    try:
        # 디렉토리 생성
        os.makedirs(os.path.dirname(param_file_path), exist_ok=True)
        
        xml_file_name = os.path.basename(xml_file_path)
        
        with open(param_file_path, 'w', encoding='utf-8') as f:
            f.write("# SQL Test Parameters\n")
            f.write(f"# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# XML File: {xml_file_name}\n\n")
            
            # XML에서 추출된 파라미터 저장
            for param_name, param_value in param_values.items():
                if param_value.strip():  # 빈 값이 아닌 경우만 저장
                    f.write(f"{param_name}={param_value}\n")
    
    except Exception as e:
        st.error(f"❌ 파라미터 저장 오류: {str(e)}")


def load_parameters(param_file_path):
    """파라미터 파일에서 파라미터 로드"""
    params = {}
    
    try:
        if os.path.exists(param_file_path):
            with open(param_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        params[key.strip()] = value.strip()
    except Exception as e:
        st.warning(f"⚠️ 파라미터 파일 읽기 오류: {str(e)}")
    
    return params


def clear_parameters(param_file_path):
    """파라미터 파일 초기화"""
    try:
        if os.path.exists(param_file_path):
            os.remove(param_file_path)
    except Exception as e:
        st.error(f"❌ 파라미터 초기화 오류: {str(e)}")


def execute_sql_test(xml_file_path, db_type, test_type, compare=False):
    """SQL 테스트 실행"""
    try:
        # 환경변수 확인
        app_tools_folder = os.getenv('APP_TOOLS_FOLDER')
        app_logs_folder = os.getenv('APP_LOGS_FOLDER')
        
        if not app_tools_folder:
            save_test_result(test_type, {
                'success': False,
                'error': 'APP_TOOLS_FOLDER 환경변수가 설정되지 않았습니다.'
            })
            return
        
        if not app_logs_folder:
            save_test_result(test_type, {
                'success': False,
                'error': 'APP_LOGS_FOLDER 환경변수가 설정되지 않았습니다.'
            })
            return
        
        # 테스트 디렉토리
        test_dir = os.path.join(app_tools_folder, '..', 'test')
        if not os.path.exists(test_dir):
            save_test_result(test_type, {
                'success': False,
                'error': f'테스트 디렉토리를 찾을 수 없습니다: {test_dir}'
            })
            return
        
        # 파일의 상대 경로 계산 (APP_LOGS_FOLDER 기준)
        relative_path = os.path.relpath(xml_file_path, app_logs_folder)
        
        # Java 명령어 구성
        compare_param = " --compare" if compare else ""
        java_cmd = f'java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$APP_LOGS_FOLDER/{relative_path}" --db {db_type}{compare_param} --show-data --json'
        
        save_test_result(test_type, {
            'success': None,
            'command': java_cmd,
            'file_path': relative_path,
            'full_path': xml_file_path,
            'test_dir': test_dir,
            'db_type': db_type,
            'test_type': test_type,
            'compare_mode': compare,
            'running': True
        })
        
        # 환경변수 설정
        env = dict(os.environ)
        env['APP_TOOLS_FOLDER'] = app_tools_folder
        env['APP_LOGS_FOLDER'] = app_logs_folder
        
        # Java 명령어 실행
        result = subprocess.run(
            java_cmd,
            shell=True,
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=120,  # 2분 타임아웃
            env=env
        )
        
        # 결과 저장 (실제 테스트 결과 분석)
        actual_success = analyze_test_result(result.stdout, result.stderr, result.returncode)
        
        save_test_result(test_type, {
            'success': actual_success,
            'command': java_cmd,
            'file_path': relative_path,
            'full_path': xml_file_path,
            'test_dir': test_dir,
            'db_type': db_type,
            'test_type': test_type,
            'compare_mode': compare,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode,
            'running': False
        })
    
    except subprocess.TimeoutExpired:
        save_test_result(test_type, {
            'success': False,
            'error': 'SQL 테스트 시간 초과 (2분)',
            'command': java_cmd,
            'file_path': relative_path,
            'db_type': db_type,
            'test_type': test_type,
            'running': False
        })
    except Exception as e:
        save_test_result(test_type, {
            'success': False,
            'error': f'SQL 테스트 실행 오류: {str(e)}',
            'db_type': db_type,
            'test_type': test_type,
            'running': False
        })


def extract_test_summary(stdout):
    """테스트 결과에서 요약 정보 추출"""
    try:
        if not stdout:
            return None
        
        lines = stdout.split('\n')
        summary_info = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ['총 테스트 수:', '실제 실행:', '성공:', '실패:', '실제 성공률:']):
                summary_info.append(line)
        
        if summary_info:
            return ' | '.join(summary_info)
        
        return None
        
    except Exception:
        return None


def analyze_test_result(stdout, stderr, return_code):
    """실제 테스트 결과를 분석하여 성공/실패 판단"""
    try:
        # stdout이 없으면 실패로 간주
        if not stdout:
            return False
        
        stdout_lower = stdout.lower()
        
        # 실행 결과 요약에서 성공률 확인
        if "실행 결과 요약" in stdout or "실제 성공률" in stdout:
            # 성공률이 0%이면 실패
            if "실제 성공률: 0.0%" in stdout or "성공: 0개" in stdout:
                return False
            
            # 실패 개수 확인
            import re
            failure_match = re.search(r'실패:\s*(\d+)개', stdout)
            if failure_match:
                failure_count = int(failure_match.group(1))
                if failure_count > 0:
                    return False
            
            # 성공 개수 확인
            success_match = re.search(r'성공:\s*(\d+)개', stdout)
            if success_match:
                success_count = int(success_match.group(1))
                if success_count > 0:
                    return True
        
        # 일반적인 성공/실패 키워드 확인
        failure_keywords = [
            'failed', 'error', 'exception', 'failure',
            '실패', '오류', '에러', 'SQLException'
        ]
        
        success_keywords = [
            'success', 'completed', 'passed',
            '성공', '완료', '통과'
        ]
        
        # 실패 키워드가 있으면 실패
        for keyword in failure_keywords:
            if keyword in stdout_lower:
                return False
        
        # stderr에 심각한 오류가 있으면 실패
        if stderr:
            stderr_lower = stderr.lower()
            critical_errors = ['exception', 'error', 'failed', 'SQLException']
            for error in critical_errors:
                if error in stderr_lower:
                    return False
        
        # 성공 키워드가 있으면 성공
        for keyword in success_keywords:
            if keyword in stdout_lower:
                return True
        
        # 종료 코드로 최종 판단
        return return_code == 0
        
    except Exception as e:
        # 분석 중 오류 발생 시 종료 코드로 판단
        return return_code == 0


def get_target_db_display_info(target_dbms_type):
    """Target 데이터베이스 타입에 따른 표시 정보 반환"""
    db_info = {
        'postgresql': {'name': 'PostgreSQL', 'icon': '🐘'},
        'postgres': {'name': 'PostgreSQL', 'icon': '🐘'},
        'mysql': {'name': 'MySQL', 'icon': '🐬'},
        'mariadb': {'name': 'MariaDB', 'icon': '🦭'},
        'sqlite': {'name': 'SQLite', 'icon': '📦'}
    }
    
    return db_info.get(target_dbms_type.lower(), {'name': target_dbms_type.upper(), 'icon': '🗄️'})


def save_test_result(test_type, result):
    """테스트 결과를 세션에 저장"""
    if test_type == "source":
        st.session_state.oracle_test_result = result
    elif test_type == "target":
        st.session_state.target_test_result = result
    elif test_type == "validation_source":
        st.session_state.validation_oracle_test_result = result
    elif test_type == "validation_target":
        st.session_state.validation_target_test_result = result


def display_dual_test_results(target_db_name):
    """Oracle과 Target DB 테스트 결과를 나란히 표시"""
    col1, col2 = st.columns(2)
    
    with col1:
        if hasattr(st.session_state, 'oracle_test_result') and st.session_state.oracle_test_result:
            display_single_test_result_without_output(st.session_state.oracle_test_result, "Oracle", "oracle")
    
    with col2:
        if hasattr(st.session_state, 'target_test_result') and st.session_state.target_test_result:
            display_single_test_result_without_output(st.session_state.target_test_result, target_db_name, "target")
    
    # JSON 결과 비교 표시
    display_json_comparison_results()
    
    # 표준 출력 표시 (JSON 비교 다음에)
    display_test_outputs(target_db_name)


def display_json_comparison_results():
    """JSON 결과 비교 표시"""
    oracle_result = getattr(st.session_state, 'oracle_test_result', None)
    target_result = getattr(st.session_state, 'target_test_result', None)
    
    if not oracle_result and not target_result:
        return
    
    oracle_json = None
    target_json = None
    
    if oracle_result:
        oracle_json = parse_json_from_output(oracle_result.get('stdout', ''))
    
    if target_result:
        target_json = parse_json_from_output(target_result.get('stdout', ''))
    
    st.markdown("---")
    st.markdown("#### 📊 JSON 결과 비교")
    
    # Row Count 정보 표시
    display_row_count_summary(oracle_json, target_json)
    
    # 1행 비교 테이블
    display_first_row_comparison(oracle_json, target_json)
    
    # 전체 JSON 결과 (접힌 상태)
    with st.expander("🔍 전체 JSON 결과", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Oracle JSON 결과**")
            if oracle_json:
                st.json(oracle_json)
            else:
                st.info("JSON 결과 없음")
        
        with col2:
            st.markdown("**Target JSON 결과**")
            if target_json:
                st.json(target_json)
            else:
                st.info("JSON 결과 없음")
        
        # 비교 분석
        if oracle_json and target_json:
            display_json_comparison_analysis(oracle_json, target_json)


def parse_json_from_output(output):
    """출력에서 JSON 파일 경로를 찾아 JSON 파싱"""
    if not output:
        return None
    
    import json
    import re
    import os
    
    # JSON 파일 경로 찾기
    json_file_pattern = r'JSON 결과 파일 생성: (.+\.json)'
    match = re.search(json_file_pattern, output)
    
    if match:
        json_file_path = match.group(1)
        
        # 상대 경로인 경우 절대 경로로 변환
        if not os.path.isabs(json_file_path):
            # 테스트 디렉토리 기준으로 경로 구성
            app_tools_folder = os.getenv('APP_TOOLS_FOLDER', '')
            if app_tools_folder:
                test_dir = os.path.join(app_tools_folder, '..', 'test')
                json_file_path = os.path.join(test_dir, json_file_path)
        
        # JSON 파일 읽기
        try:
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"JSON 파일 읽기 오류: {e}")
    
    return None


def display_first_row_comparison(oracle_json, target_json):
    """첫 번째 행 데이터 비교 테이블"""
    oracle_first_row = extract_first_row_data(oracle_json)
    target_first_row = extract_first_row_data(target_json)
    
    if oracle_first_row or target_first_row:
        st.markdown("**📋 1행 비교**")
        
        # 컬럼명을 소문자로 변환하여 매핑
        oracle_columns = {}
        target_columns = {}
        
        if oracle_first_row:
            oracle_columns = {k.lower(): (k, v) for k, v in oracle_first_row.items()}
        if target_first_row:
            target_columns = {k.lower(): (k, v) for k, v in target_first_row.items()}
        
        # 모든 컬럼명 수집 (소문자 기준)
        all_columns = set()
        all_columns.update(oracle_columns.keys())
        all_columns.update(target_columns.keys())
        
        if all_columns:
            # 테이블 데이터 구성
            comparison_data = []
            for column_lower in sorted(all_columns):
                oracle_info = oracle_columns.get(column_lower, (column_lower, "N/A"))
                target_info = target_columns.get(column_lower, (column_lower, "N/A"))
                
                oracle_value = oracle_info[1]
                target_value = target_info[1]
                
                # 값이 다른 경우 표시
                match_status = "✅" if oracle_value == target_value else "❌"
                
                # 원본 컬럼명 사용 (Oracle 우선, 없으면 Target)
                display_column = oracle_info[0] if oracle_info[1] != "N/A" else target_info[0]
                
                comparison_data.append({
                    "컬럼명": display_column,
                    "Oracle": oracle_value,
                    "Target": target_value,
                    "일치": match_status
                })
            
            # 데이터프레임으로 표시
            import pandas as pd
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True, hide_index=True)


def extract_first_row_data(json_data):
    """JSON에서 첫 번째 행 데이터 추출"""
    if not json_data:
        return None
    
    # successfulTests[0].resultData.data[0] 경로로 찾기
    if isinstance(json_data, dict) and 'successfulTests' in json_data:
        successful_tests = json_data['successfulTests']
        if isinstance(successful_tests, list) and len(successful_tests) > 0:
            first_test = successful_tests[0]
            if isinstance(first_test, dict) and 'resultData' in first_test:
                result_data = first_test['resultData']
                if isinstance(result_data, dict) and 'data' in result_data:
                    data_array = result_data['data']
                    if isinstance(data_array, list) and len(data_array) > 0:
                        return data_array[0]
    
    return None


def display_row_count_summary(oracle_json, target_json):
    """Row Count 요약 정보 표시"""
    oracle_count = extract_row_count(oracle_json)
    target_count = extract_row_count(target_json)
    
    if oracle_count is not None or target_count is not None:
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if oracle_count is not None:
                st.metric("Oracle Row Count", oracle_count)
        
        with col2:
            if target_count is not None:
                st.metric("Target Row Count", target_count)
        
        with col3:
            if oracle_count is not None and target_count is not None:
                if oracle_count == target_count:
                    st.success(f"✅ Row Count 일치: {oracle_count}")
                else:
                    st.error(f"❌ Row Count 불일치: Oracle({oracle_count}) vs Target({target_count})")


def extract_row_count(json_data):
    """JSON에서 Row Count 추출"""
    if not json_data:
        return None
    
    # successfulTests 배열에서 rowCount 찾기
    if isinstance(json_data, dict) and 'successfulTests' in json_data:
        successful_tests = json_data['successfulTests']
        if isinstance(successful_tests, list) and len(successful_tests) > 0:
            first_test = successful_tests[0]
            if isinstance(first_test, dict):
                # rowCount 직접 찾기
                if 'rowCount' in first_test:
                    return first_test['rowCount']
                # resultData.count에서 찾기
                if 'resultData' in first_test and isinstance(first_test['resultData'], dict):
                    if 'count' in first_test['resultData']:
                        return first_test['resultData']['count']
    
    # 기존 로직도 유지
    if isinstance(json_data, dict):
        for key in ['rowCount', 'row_count', 'totalRows', 'count']:
            if key in json_data:
                return json_data[key]
        
        for value in json_data.values():
            if isinstance(value, dict):
                count = extract_row_count(value)
                if count is not None:
                    return count
    
    return None


def display_json_comparison_analysis(oracle_json, target_json):
    """JSON 비교 분석 표시"""
    st.markdown("**🔍 비교 분석**")
    
    differences = []
    
    # 기본 구조 비교
    if type(oracle_json) != type(target_json):
        differences.append(f"데이터 타입 차이: Oracle({type(oracle_json).__name__}) vs Target({type(target_json).__name__})")
    
    # 딕셔너리인 경우 키 비교
    if isinstance(oracle_json, dict) and isinstance(target_json, dict):
        oracle_keys = set(oracle_json.keys())
        target_keys = set(target_json.keys())
        
        if oracle_keys != target_keys:
            only_oracle = oracle_keys - target_keys
            only_target = target_keys - oracle_keys
            
            if only_oracle:
                differences.append(f"Oracle에만 있는 키: {list(only_oracle)}")
            if only_target:
                differences.append(f"Target에만 있는 키: {list(only_target)}")
    
    # 리스트인 경우 길이 비교
    if isinstance(oracle_json, list) and isinstance(target_json, list):
        if len(oracle_json) != len(target_json):
            differences.append(f"배열 길이 차이: Oracle({len(oracle_json)}) vs Target({len(target_json)})")
    
    if differences:
        for diff in differences:
            st.warning(f"⚠️ {diff}")
    else:
        st.success("✅ 구조적 차이 없음")


def display_test_outputs(target_db_name):
    """테스트 표준 출력을 별도로 표시"""
    oracle_result = getattr(st.session_state, 'oracle_test_result', None)
    target_result = getattr(st.session_state, 'target_test_result', None)
    
    if not oracle_result and not target_result:
        return
    
    # 전체 출력을 접힌 상태로 표시
    with st.expander("📤 테스트 출력 결과", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if oracle_result:
                st.markdown("**Oracle 출력**")
                if oracle_result.get('stdout'):
                    with st.expander("📤 표준 출력", expanded=False):
                        st.code(oracle_result['stdout'], language=None)
                if oracle_result.get('stderr'):
                    with st.expander("⚠️ 표준 에러", expanded=False):
                        st.code(oracle_result['stderr'], language=None)
        
        with col2:
            if target_result:
                st.markdown(f"**{target_db_name} 출력**")
                if target_result.get('stdout'):
                    with st.expander("📤 표준 출력", expanded=False):
                        st.code(target_result['stdout'], language=None)
                if target_result.get('stderr'):
                    with st.expander("⚠️ 표준 에러", expanded=False):
                        st.code(target_result['stderr'], language=None)


def display_single_test_result_without_output(result, db_name, result_key):
    """표준 출력 없이 테스트 결과만 표시"""
    st.markdown(f"#### 🧪 {db_name} 테스트 결과")
    
    # 실행 중 표시
    if result.get('running'):
        st.info(f"🔄 {db_name} 테스트 실행 중... (최대 2분)")
        return
    
    # 테스트 파일 및 DB 정보
    if 'file_path' in result:
        st.caption(f"**파일:** {result['file_path']}")
    if 'db_type' in result:
        st.caption(f"**DB:** {result['db_type'].upper()}")
    
    # 성공/실패 상태
    if result.get('success') is True:
        st.success("✅ 테스트 성공!")
        # 성공률 정보 추출 및 표시
        if result.get('stdout'):
            success_info = extract_test_summary(result['stdout'])
            if success_info:
                st.info(f"📊 {success_info}")
    elif result.get('success') is False:
        st.error("❌ 테스트 실패!")
        # 실패 정보 추출 및 표시
        if result.get('stdout'):
            failure_info = extract_test_summary(result['stdout'])
            if failure_info:
                st.warning(f"📊 {failure_info}")
    
    # 에러 메시지
    if result.get('error'):
        st.error(f"**오류:** {result['error']}")
    
    # 종료 코드
    if 'return_code' in result:
        if result['return_code'] == 0:
            st.success(f"**종료 코드:** {result['return_code']} (정상 종료)")
        else:
            st.error(f"**종료 코드:** {result['return_code']} (비정상 종료)")


def display_single_test_result(result, db_name, result_key):
    """단일 테스트 결과 표시"""
    st.markdown(f"#### 🧪 {db_name} 테스트 결과")
    
    # 실행 중 표시
    if result.get('running'):
        st.info(f"🔄 {db_name} 테스트 실행 중... (최대 2분)")
        return
    
    # 테스트 파일 및 DB 정보
    if 'file_path' in result:
        st.markdown(f"**📄 파일:** `{os.path.basename(result['file_path'])}`")
    
    if 'db_type' in result:
        st.markdown(f"**🗄️ DB:** `{result['db_type'].upper()}`")
    
    # 명령어 정보 (전체 표시)
    if 'command' in result:
        st.markdown("**💻 실행 명령어:**")
        st.code(f"$ cd {result.get('test_dir', '')}\n$ {result['command']}", language="bash")
    
    # 결과 상태 (상세 분석)
    if result.get('success') is True:
        st.success("✅ 테스트 성공!")
        # 성공률 정보 추출 및 표시
        if result.get('stdout'):
            success_info = extract_test_summary(result['stdout'])
            if success_info:
                st.info(f"📊 {success_info}")
    elif result.get('success') is False:
        st.error("❌ 테스트 실패!")
        # 실패 정보 추출 및 표시
        if result.get('stdout'):
            failure_info = extract_test_summary(result['stdout'])
            if failure_info:
                st.warning(f"📊 {failure_info}")
    
    # 종료 코드와 실제 결과 비교
    if 'return_code' in result:
        code_success = result['return_code'] == 0
        actual_success = result.get('success', False)
        
        if code_success != actual_success:
            st.warning(f"⚠️ 종료 코드({result['return_code']})와 실제 결과가 다릅니다!")
        
        if result['return_code'] == 0:
            st.success(f"**종료 코드:** {result['return_code']} (정상 종료)")
        else:
            st.error(f"**종료 코드:** {result['return_code']} (비정상 종료)")
    
    # 표준 출력 (접힌 상태로 표시)
    if result.get('stdout'):
        with st.expander("📤 표준 출력", expanded=False):
            st.code(result['stdout'], language=None)
    
    # 표준 에러 (전체 표시)
    if result.get('stderr'):
        st.markdown("**📥 표준 에러:**")
        st.code(result['stderr'], language=None)
    
    # 에러 메시지
    if result.get('error'):
        st.error(f"**오류:** {result['error']}")
    
    # 결과 지우기 버튼
    if st.button(f"🧹 {db_name} 결과 지우기", key=f"clear_{result_key}_result"):
        if result_key == "oracle" and hasattr(st.session_state, 'oracle_test_result'):
            del st.session_state.oracle_test_result
        elif result_key == "target" and hasattr(st.session_state, 'target_test_result'):
            del st.session_state.target_test_result
        elif result_key == "validation_oracle" and hasattr(st.session_state, 'validation_oracle_test_result'):
            del st.session_state.validation_oracle_test_result
        elif result_key == "validation_target" and hasattr(st.session_state, 'validation_target_test_result'):
            del st.session_state.validation_target_test_result
        elif result_key == "postgresql" and hasattr(st.session_state, 'postgresql_test_result'):
            del st.session_state.postgresql_test_result
        st.rerun()


def display_test_result():
    """테스트 결과 표시"""
    result = st.session_state.sql_test_result
    
    st.markdown("#### 🧪 SQL 테스트 결과")
    
    # 실행 중 표시
    if result.get('running'):
        st.info("🔄 SQL 테스트 실행 중... (최대 2분)")
        return
    
    # 테스트 파일 및 DB 정보
    col1, col2 = st.columns(2)
    with col1:
        if 'file_path' in result:
            st.markdown(f"**📄 테스트 파일:** `{result['file_path']}`")
    with col2:
        if 'db_type' in result:
            st.markdown(f"**🗄️ 데이터베이스:** `{result['db_type'].upper()}`")
    
    # 명령어 정보
    if 'command' in result:
        st.markdown("**💻 실행 명령어:**")
        st.code(f"$ cd {result.get('test_dir', '')}\n$ {result['command']}", language="bash")
    
    # 결과 상태
    if result.get('success') is True:
        st.success("✅ SQL 테스트 성공!")
    elif result.get('success') is False:
        st.error("❌ SQL 테스트 실패!")
    
    # 표준 출력 (접힌 상태로 표시)
    if result.get('stdout'):
        with st.expander("📤 표준 출력", expanded=False):
            st.code(result['stdout'], language=None)
    
    # 표준 에러
    if result.get('stderr'):
        st.markdown("**📥 표준 에러:**")
        st.code(result['stderr'], language=None)
    
    # 에러 메시지
    if result.get('error'):
        st.error(f"**오류:** {result['error']}")
    
    # 종료 코드
    if 'return_code' in result:
        if result['return_code'] == 0:
            st.success(f"**종료 코드:** {result['return_code']} (성공)")
        else:
            st.error(f"**종료 코드:** {result['return_code']} (실패)")
    
    # 결과 지우기 버튼
    if st.button("🧹 결과 지우기", key="clear_test_result"):
        if hasattr(st.session_state, 'sql_test_result'):
            del st.session_state.sql_test_result
        st.rerun()
