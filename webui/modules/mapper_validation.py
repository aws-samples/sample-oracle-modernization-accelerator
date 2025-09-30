import streamlit as st
import pandas as pd
import os
from pathlib import Path

def render_mapper_validation_page():
    """매퍼 파일 검증 페이지"""
    st.markdown('<div class="main-header"><h1>✅ 매퍼 파일 검증</h1></div>', unsafe_allow_html=True)
    
    # Process 상태 의미 설명
    st.markdown("""
    ### 📋 Process 상태 의미
    - **Not Yet**: 변환 필요
    - **Sampled**: Sample 변환 (처리됨으로 간주)  
    - **Processed**: 처리됨
    """)
    
    st.markdown("---")
    
    # APP_TRANSFORM_FOLDER 환경 변수 확인
    app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER')
    if not app_transform_folder:
        st.error("❌ APP_TRANSFORM_FOLDER 환경 변수가 설정되지 않았습니다.")
        return
    
    if not os.path.exists(app_transform_folder):
        st.error(f"❌ 디렉토리가 존재하지 않습니다: {app_transform_folder}")
        return
    
    # CSV 파일 경로
    sample_csv = os.path.join(app_transform_folder, "SampleTransformTarget.csv")
    sql_csv = os.path.join(app_transform_folder, "SQLTransformTarget.csv")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["📋 SampleTransformTarget.csv", "📊 SQLTransformTarget.csv"])
    
    with tab1:
        render_csv_editor("SampleTransformTarget.csv", sample_csv)
    
    with tab2:
        render_csv_editor("SQLTransformTarget.csv", sql_csv)

def render_csv_editor(file_name, file_path):
    """CSV 파일 편집기"""
    st.subheader(f"📄 {file_name}")
    
    if not os.path.exists(file_path):
        st.warning(f"⚠️ 파일이 존재하지 않습니다: {file_path}")
        
        # 새 파일 생성 버튼
        if st.button(f"📝 {file_name} 새로 생성", key=f"create_{file_name}"):
            try:
                # 기본 컬럼으로 빈 CSV 생성
                if "Sample" in file_name:
                    df = pd.DataFrame(columns=['file_path', 'status', 'error_message'])
                else:
                    df = pd.DataFrame(columns=['sql_id', 'file_path', 'status', 'error_message'])
                
                df.to_csv(file_path, index=False, encoding='utf-8')
                st.success(f"✅ {file_name} 파일이 생성되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 파일 생성 실패: {e}")
        return
    
    try:
        # CSV 파일 읽기
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # 파일 정보 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 총 행 수", len(df))
        with col2:
            st.metric("📋 컬럼 수", len(df.columns))
        with col3:
            file_size = os.path.getsize(file_path)
            st.metric("📁 파일 크기", f"{file_size:,} bytes")
        
        # 검색 기능
        st.markdown("### 🔍 검색")
        search_col, filter_col = st.columns([2, 1])
        
        with search_col:
            search_term = st.text_input("검색어 입력", key=f"search_{file_name}", placeholder="파일명, SQL ID, 상태 등으로 검색")
        
        with filter_col:
            if len(df.columns) > 0:
                search_column = st.selectbox("검색 컬럼", ["전체"] + list(df.columns), key=f"search_col_{file_name}")
        
        # 검색 결과 필터링
        filtered_df = df.copy()
        original_indices = df.index.tolist()
        
        if search_term:
            if search_column == "전체":
                # 모든 컬럼에서 검색
                mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            else:
                # 특정 컬럼에서 검색
                mask = df[search_column].astype(str).str.contains(search_term, case=False, na=False)
            
            filtered_df = df[mask].copy()
            original_indices = df[mask].index.tolist()
            
            st.info(f"🔍 검색 결과: {len(filtered_df)}개 행 (전체 {len(df)}개 중)")
        
        # 데이터 편집기
        st.markdown("### 📝 데이터 편집")
        
        if len(filtered_df) > 0:
            # 편집 가능한 데이터 그리드 (검색 결과)
            edited_filtered_df = st.data_editor(
                filtered_df,
                use_container_width=True,
                num_rows="dynamic",
                key=f"editor_{file_name}_{len(original_indices)}"  # 검색 결과가 바뀔 때마다 키 변경
            )
            
            # 원본 데이터프레임 업데이트
            updated_df = df.copy()
            
            # 검색 결과에서 수정된 내용을 원본에 반영
            for i, original_idx in enumerate(original_indices):
                if i < len(edited_filtered_df):
                    updated_df.loc[original_idx] = edited_filtered_df.iloc[i]
            
            # 새로 추가된 행들 처리 (검색 결과에서 추가된 경우)
            if len(edited_filtered_df) > len(original_indices):
                new_rows = edited_filtered_df.iloc[len(original_indices):].copy()
                updated_df = pd.concat([updated_df, new_rows], ignore_index=True)
            
            # 삭제된 행들 처리 (검색 결과에서 삭제된 경우)
            if len(edited_filtered_df) < len(original_indices):
                deleted_indices = original_indices[len(edited_filtered_df):]
                updated_df = updated_df.drop(deleted_indices).reset_index(drop=True)
        else:
            st.info("📝 검색 결과가 없습니다.")
            updated_df = df.copy()
        
        # 저장 버튼
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 저장", key=f"save_{file_name}", type="primary"):
                try:
                    # 백업 생성
                    backup_path = f"{file_path}.backup"
                    if os.path.exists(file_path):
                        import shutil
                        shutil.copy2(file_path, backup_path)
                    
                    # 새 데이터 저장
                    updated_df.to_csv(file_path, index=False, encoding='utf-8')
                    st.success(f"✅ {file_name} 저장 완료!")
                    
                except Exception as e:
                    st.error(f"❌ 저장 실패: {e}")
        
        with col2:
            if st.button("🔄 새로고침", key=f"refresh_{file_name}"):
                st.rerun()
        
        with col3:
            # 파일 경로 표시
            st.caption(f"📁 {file_path}")
        
        # 전체 데이터 미리보기 (읽기 전용)
        if len(df) > 0:
            with st.expander("👀 전체 데이터 미리보기", expanded=False):
                st.dataframe(df, use_container_width=True)
        else:
            st.info("📝 데이터가 없습니다. 위의 편집기에서 새 행을 추가하세요.")
            
    except Exception as e:
        st.error(f"❌ CSV 파일 읽기 오류: {e}")
        
        # 파일 복구 옵션
        backup_path = f"{file_path}.backup"
        if os.path.exists(backup_path):
            if st.button(f"🔧 백업에서 복구", key=f"restore_{file_name}"):
                try:
                    import shutil
                    shutil.copy2(backup_path, file_path)
                    st.success("✅ 백업에서 복구되었습니다.")
                    st.rerun()
                except Exception as restore_e:
                    st.error(f"❌ 복구 실패: {restore_e}")
