"""
PostgreSQL Metadata Generation Page
"""
import streamlit as st
import subprocess
import os
import re
import html
import pandas as pd


def render_postgresql_meta_page():
    """PostgreSQL 메타데이터 생성 페이지"""
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
    if st.button("🏠 홈으로", key="postgresql_meta_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    # 제목을 전체 폭으로 표시
    st.markdown("# 🗄️ PostgreSQL 메타데이터")
    
    # 탭 구성
    tab1, tab2 = st.tabs(["📊 메타데이터 생성", "🔍 메타데이터 검증"])
    
    with tab1:
        render_metadata_generation_tab()
    
    with tab2:
        render_metadata_verification_tab()


def render_metadata_generation_tab():
    """메타데이터 생성 탭"""
    st.markdown("## 📊 PostgreSQL 메타데이터 생성")
    
    # 명령어 정보
    script_path = "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh"
    expanded_script_path = os.path.expandvars(script_path)
    
    st.info(f"**실행 스크립트:** `{script_path}`")
    st.caption(f"📄 실제 경로: {expanded_script_path}")
    
    # 스크립트 존재 확인
    if not os.path.exists(expanded_script_path):
        st.error(f"❌ 스크립트 파일을 찾을 수 없습니다: {expanded_script_path}")
        st.info("💡 환경 변수 설정을 확인하거나 파일 경로를 확인해주세요.")
        return
    
    # 실행 중인 작업 확인
    if st.session_state.oma_controller.is_any_task_running():
        st.error("❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.")
        return
    
    # 실행 버튼
    if st.button("🚀 실행", key="run_postgresql_meta", type="primary"):
        execute_postgresql_meta_script(expanded_script_path)
    
    st.caption("스크립트를 실행하여 PostgreSQL 메타데이터를 생성합니다")


def render_metadata_verification_tab():
    """메타데이터 검증 탭"""
    st.markdown("## 🔍 메타데이터 검증")
    
    # 메타데이터 파일 경로
    metadata_file = "$APP_TRANSFORM_FOLDER/oma_metadata.txt"
    expanded_metadata_file = os.path.expandvars(metadata_file)
    
    st.info(f"**메타데이터 파일:** `{metadata_file}`")
    st.caption(f"📄 실제 경로: {expanded_metadata_file}")
    
    # 파일 존재 확인
    if not os.path.exists(expanded_metadata_file):
        st.error(f"❌ 메타데이터 파일을 찾을 수 없습니다: {expanded_metadata_file}")
        st.info("💡 먼저 '메타데이터 생성' 탭에서 메타데이터를 생성해주세요.")
        return
    
    # 메타데이터 로드 및 표시
    try:
        metadata_df = load_metadata_file(expanded_metadata_file)
        
        if metadata_df is not None and not metadata_df.empty:
            # 검색 필터 UI
            st.markdown("### 🔍 검색 필터")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # 스키마 필터
                schemas = ['전체'] + sorted(metadata_df['table_schema'].unique().tolist())
                selected_schema = st.selectbox("스키마", schemas, key="schema_filter")
            
            with col2:
                # 테이블명 필터
                table_filter = st.text_input("테이블명 (부분 검색)", key="table_filter", 
                                           help="테이블명의 일부를 입력하세요")
            
            with col3:
                # 컬럼명 필터
                column_filter = st.text_input("컬럼명 (부분 검색)", key="column_filter",
                                            help="컬럼명의 일부를 입력하세요")
            
            # 필터 적용
            filtered_df = apply_metadata_filters(metadata_df, selected_schema, table_filter, column_filter)
            
            # 결과 표시
            st.markdown("### 📋 검색 결과")
            st.info(f"총 {len(filtered_df):,}개의 레코드가 검색되었습니다.")
            
            if not filtered_df.empty:
                # 데이터프레임 표시 (높이 조정)
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    height=600,
                    column_config={
                        "table_schema": st.column_config.TextColumn("스키마", width="medium"),
                        "table_name": st.column_config.TextColumn("테이블명", width="medium"),
                        "column_name": st.column_config.TextColumn("컬럼명", width="medium"),
                        "data_type": st.column_config.TextColumn("데이터 타입", width="medium"),
                    }
                )
                
                # 다운로드 버튼
                csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=csv_data,
                    file_name=f"metadata_filtered_{len(filtered_df)}_records.csv",
                    mime="text/csv",
                    key="download_filtered_metadata"
                )
            else:
                st.warning("검색 조건에 맞는 데이터가 없습니다.")
        else:
            st.error("메타데이터 파일이 비어있거나 올바르지 않은 형식입니다.")
            
    except Exception as e:
        st.error(f"❌ 메타데이터 파일 로드 중 오류 발생: {str(e)}")
        st.info("💡 메타데이터 파일 형식을 확인해주세요.")


def load_metadata_file(file_path):
    """메타데이터 파일을 로드하여 DataFrame으로 반환"""
    try:
        # 파일 읽기 (파이프 구분자, 1행은 헤더, 2행은 구분자라서 건너뛰기)
        df = pd.read_csv(file_path, sep='|', encoding='utf-8', header=0, skiprows=[1])
        
        # 컬럼명 정리 (공백 제거)
        df.columns = df.columns.str.strip()
        
        # 필수 컬럼 확인
        required_columns = ['table_schema', 'table_name', 'column_name', 'data_type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"필수 컬럼이 없습니다: {missing_columns}")
            st.info(f"현재 컬럼: {list(df.columns)}")
            
            # 파일의 처음 5줄을 보여주어 구조 확인
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            st.info("파일의 처음 5줄:")
            for i, line in enumerate(first_lines, 1):
                st.text(f"{i}: {line}")
            return None
        
        # 데이터 정리
        df = df.fillna('')  # NaN 값을 빈 문자열로 변경
        df = df.astype(str)  # 모든 컬럼을 문자열로 변환
        
        # 데이터 값의 공백도 제거
        for col in df.columns:
            df[col] = df[col].str.strip()
        
        # 빈 행 제거
        df = df[df['table_schema'] != '']
        
        # 마지막 줄이 카운트 정보인지 확인하고 제거
        if not df.empty:
            last_row = df.iloc[-1]
            # 마지막 행이 숫자로만 구성되어 있거나 "Total:", "Count:" 등이 포함된 경우 제거
            last_row_text = ' '.join(last_row.values).lower()
            if (last_row_text.isdigit() or 
                'total' in last_row_text or 
                'count' in last_row_text or 
                'records' in last_row_text or
                '개' in last_row_text or
                'rows' in last_row_text):
                df = df.iloc[:-1]  # 마지막 행 제거
                st.info(f"마지막 줄 카운트 정보 제거: {last_row_text}")
        
        return df
        
    except pd.errors.EmptyDataError:
        st.error("메타데이터 파일이 비어있습니다.")
        return None
    except pd.errors.ParserError as e:
        st.error(f"파일 파싱 오류: {e}")
        st.info("파일이 파이프(|) 구분자로 되어있는지 확인해주세요.")
        return None
    except Exception as e:
        st.error(f"파일 로드 오류: {e}")
        return None


def apply_metadata_filters(df, schema_filter, table_filter, column_filter):
    """메타데이터에 필터를 적용"""
    filtered_df = df.copy()
    
    # 스키마 필터
    if schema_filter and schema_filter != '전체':
        filtered_df = filtered_df[filtered_df['table_schema'].str.contains(schema_filter, case=False, na=False)]
    
    # 테이블명 필터
    if table_filter:
        filtered_df = filtered_df[filtered_df['table_name'].str.contains(table_filter, case=False, na=False)]
    
    # 컬럼명 필터
    if column_filter:
        filtered_df = filtered_df[filtered_df['column_name'].str.contains(column_filter, case=False, na=False)]
    
    return filtered_df


def clean_ansi_codes(text):
    """ANSI 색상 코드 및 제어 문자, HTML 태그 제거"""
    # ANSI 색상 코드 제거 (예: [0;34m, [1;32m 등)
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    
    # 기타 ANSI 이스케이프 시퀀스 제거
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    
    # 커서 제어 시퀀스 제거 ([?25l, [?25h 등)
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    
    # 백스페이스, 캐리지 리턴 등 제어 문자 제거
    text = re.sub(r'[\x08\x0c\x0e\x0f\r]', '', text)
    
    # HTML 태그 제거 (</textarea>, </div> 등)
    text = re.sub(r'</?(textarea|div)[^>]*>', '', text, flags=re.IGNORECASE)
    
    # 기타 HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML 엔티티 디코딩 (&lt;, &gt; 등을 <, >로 변환)
    import html as html_module
    text = html_module.unescape(text)
    
    # 연속된 공백을 하나로 정리
    text = re.sub(r' +', ' ', text)
    
    # 빈 줄 정리 (3개 이상의 연속 줄바꿈을 2개로)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def execute_postgresql_meta_script(script_path):
    """PostgreSQL 메타데이터 스크립트 실행 및 결과 표시"""
    st.markdown("## 📊 실행 결과")
    
    # 진행률 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 스크립트 실행 중...")
        progress_bar.progress(25)
        
        # 스크립트 실행
        result = subprocess.run(
            f"bash '{script_path}'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,  # 60초 타임아웃
            cwd=os.path.dirname(script_path)
        )
        
        progress_bar.progress(75)
        status_text.text("📝 결과 처리 중...")
        
        # 결과 표시
        progress_bar.progress(100)
        status_text.text("✅ 완료!")
        
        # 진행률 바 제거
        progress_bar.empty()
        status_text.empty()
        
        # 성공/실패 여부 확인
        if result.returncode == 0:
            st.success("✅ PostgreSQL 메타데이터 생성 완료!")
            
            # 실행 결과를 적당한 폭으로 표시
            if result.stdout.strip():
                st.markdown("---")
                st.markdown("### 📄 실행 결과")
                
                # ANSI 코드 제거 및 HTML 이스케이프 처리
                clean_stdout = clean_ansi_codes(result.stdout)
                escaped_stdout = html.escape(clean_stdout)
                
                # HTML 구조를 한 줄로 작성하여 줄바꿈 문제 방지 (라이트 테마)
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 600px; background-color: #f8f9fa; color: #212529; border: 1px solid #dee2e6; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stdout}</textarea></div>', unsafe_allow_html=True)
            
            # 경고 메시지가 있는 경우
            if result.stderr.strip():
                st.markdown("### ⚠️ 경고/정보 메시지")
                
                # ANSI 코드 제거 및 HTML 이스케이프 처리
                clean_stderr = clean_ansi_codes(result.stderr)
                escaped_stderr = html.escape(clean_stderr)
                
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 200px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stderr}</textarea></div>', unsafe_allow_html=True)
                
        else:
            st.error(f"❌ 스크립트 실행 실패 (종료 코드: {result.returncode})")
            
            # 에러 메시지
            if result.stderr.strip():
                st.markdown("### 🚨 에러 메시지")
                
                # ANSI 코드 제거 및 HTML 이스케이프 처리
                clean_stderr = clean_ansi_codes(result.stderr)
                escaped_stderr = html.escape(clean_stderr)
                
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 400px; background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stderr}</textarea></div>', unsafe_allow_html=True)
            
            # 표준 출력도 표시
            if result.stdout.strip():
                st.markdown("### 📄 출력 내용")
                
                # ANSI 코드 제거 및 HTML 이스케이프 처리
                clean_stdout = clean_ansi_codes(result.stdout)
                escaped_stdout = html.escape(clean_stdout)
                
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 300px; background-color: #f8f9fa; color: #212529; border: 1px solid #dee2e6; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stdout}</textarea></div>', unsafe_allow_html=True)
        
    except subprocess.TimeoutExpired:
        progress_bar.empty()
        status_text.empty()
        st.error("❌ 스크립트 실행 시간이 초과되었습니다 (60초)")
        st.info("💡 스크립트가 너무 오래 실행되고 있습니다. 수동으로 확인해주세요.")
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ 스크립트 실행 중 오류 발생: {str(e)}")
        st.info("💡 스크립트 파일 권한이나 환경 설정을 확인해주세요.")
