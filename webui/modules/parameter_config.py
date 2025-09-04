import streamlit as st
import pandas as pd
import os
import subprocess
import time

def render_parameter_config_page():
    """Parameter 구성 페이지"""
    st.markdown('<div class="main-header"><h1>⚙️ Parameter 구성</h1></div>', unsafe_allow_html=True)
    
    # TEST_FOLDER 환경 변수 확인
    test_folder = os.environ.get('TEST_FOLDER')
    if not test_folder:
        st.error("❌ TEST_FOLDER 환경 변수가 설정되지 않았습니다.")
        return
    
    if not os.path.exists(test_folder):
        st.error(f"❌ 디렉토리가 존재하지 않습니다: {test_folder}")
        return
    
    # bulk_prepare.sh 파일 경로
    oma_base_dir = os.environ.get('OMA_BASE_DIR')
    if not oma_base_dir:
        st.error("❌ OMA_BASE_DIR 환경 변수가 설정되지 않았습니다.")
        return
    
    bulk_prepare_script = os.path.join(oma_base_dir, "bin", "test", "bulk_prepare.sh")
    parameters_file = os.path.join(test_folder, "parameters.properties")
    
    st.info(f"📁 작업 디렉토리: {test_folder}")
    
    # 파라미터 구성 실행 버튼
    if st.button("🚀 파라미터 구성 실행", type="primary", use_container_width=True):
        if not os.path.exists(bulk_prepare_script):
            st.error(f"❌ bulk_prepare.sh 파일이 존재하지 않습니다: {bulk_prepare_script}")
            return
        
        # SOURCE_SQL_MAPPER_FOLDER 환경 변수 확인
        source_sql_mapper_folder = os.environ.get('SOURCE_SQL_MAPPER_FOLDER')
        if not source_sql_mapper_folder:
            st.error("❌ SOURCE_SQL_MAPPER_FOLDER 환경 변수가 설정되지 않았습니다.")
            return
        
        # APP_TOOLS_FOLDER 환경 변수 확인
        app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
        if not app_tools_folder:
            st.error("❌ APP_TOOLS_FOLDER 환경 변수가 설정되지 않았습니다.")
            return
        
        # 실행 로그 컨테이너
        log_container = st.empty()
        
        try:
            with st.spinner("파라미터 구성 중..."):
                # APP_TOOLS_FOLDER/../test에서 bulk_prepare.sh 실행
                test_dir = os.path.join(app_tools_folder, "..", "test")
                command = f"{bulk_prepare_script} {source_sql_mapper_folder}"
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=test_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # 실시간 로그 출력
                logs = []
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        logs.append(line.rstrip())
                        # 최근 20줄만 표시
                        recent_logs = logs[-20:] if len(logs) > 20 else logs
                        log_container.code('\n'.join(recent_logs))
                
                # 프로세스 완료 대기
                return_code = process.wait()
                
                # TEST_FOLDER에 parameters.properties 파일이 생성되었는지 확인
                if os.path.exists(parameters_file):
                    st.success("✅ 파라미터 구성이 완료되었습니다!")
                    # parameters.properties 파일이 생성되었으므로 페이지 새로고침
                    time.sleep(1)  # 파일 생성 완료 대기
                    st.rerun()
                else:
                    if return_code == 0:
                        st.warning("⚠️ 스크립트는 성공했지만 parameters.properties 파일을 찾을 수 없습니다.")
                    else:
                        st.error(f"❌ 파라미터 구성 실행 실패 (종료 코드: {return_code})")
                    
        except Exception as e:
            st.error(f"❌ 실행 중 오류 발생: {e}")
    
    st.markdown("---")
    
    # parameters.properties 파일 표시 및 편집
    render_parameters_editor(parameters_file)

def render_parameters_editor(parameters_file):
    """parameters.properties 파일 편집기"""
    st.subheader("📄 parameters.properties")
    
    if not os.path.exists(parameters_file):
        st.warning(f"⚠️ parameters.properties 파일이 존재하지 않습니다.")
        st.info("파라미터 구성을 먼저 실행하세요.")
        return
    
    try:
        # properties 파일을 DataFrame으로 변환
        properties_data = []
        
        with open(parameters_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        properties_data.append({
                            'Key': key.strip(),
                            'Value': value.strip(),
                            'Line': line_num
                        })
                    else:
                        # = 없는 라인도 표시
                        properties_data.append({
                            'Key': line,
                            'Value': '',
                            'Line': line_num
                        })
        
        if not properties_data:
            st.info("📝 설정 항목이 없습니다.")
            return
        
        df = pd.DataFrame(properties_data)
        
        # 파일 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 설정 항목 수", len(df))
        with col2:
            file_size = os.path.getsize(parameters_file)
            st.metric("📁 파일 크기", f"{file_size:,} bytes")
        with col3:
            mtime = os.path.getmtime(parameters_file)
            st.metric("🕒 수정 시간", time.strftime("%H:%M:%S", time.localtime(mtime)))
        
        # 검색 기능
        search_term = st.text_input("🔍 검색", placeholder="키 또는 값으로 검색")
        
        # 검색 필터링
        filtered_df = df.copy()
        if search_term:
            mask = (df['Key'].str.contains(search_term, case=False, na=False) | 
                   df['Value'].str.contains(search_term, case=False, na=False))
            filtered_df = df[mask]
            st.info(f"🔍 검색 결과: {len(filtered_df)}개 항목")
        
        # 편집 가능한 테이블 (Line 컬럼 제외)
        edit_df = filtered_df[['Key', 'Value']].copy()
        
        edited_df = st.data_editor(
            edit_df,
            use_container_width=True,
            num_rows="dynamic",
            key="parameters_editor"
        )
        
        # 저장 버튼
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 저장", type="primary"):
                try:
                    # 백업 생성
                    backup_path = f"{parameters_file}.backup"
                    import shutil
                    shutil.copy2(parameters_file, backup_path)
                    
                    # 새 properties 파일 작성
                    with open(parameters_file, 'w', encoding='utf-8') as f:
                        f.write("# Parameters Configuration\n")
                        f.write(f"# Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        
                        for _, row in edited_df.iterrows():
                            if row['Key'] and not pd.isna(row['Key']):
                                if row['Value'] and not pd.isna(row['Value']):
                                    f.write(f"{row['Key']}={row['Value']}\n")
                                else:
                                    f.write(f"{row['Key']}=\n")
                    
                    st.success("✅ parameters.properties 저장 완료!")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 저장 실패: {e}")
        
        with col2:
            if st.button("🔄 새로고침"):
                st.rerun()
        
        with col3:
            st.caption(f"📁 {parameters_file}")
        
        # 원본 파일 내용 미리보기
        with st.expander("📄 원본 파일 내용", expanded=False):
            with open(parameters_file, 'r', encoding='utf-8') as f:
                content = f.read()
            st.code(content, language='properties')
            
    except Exception as e:
        st.error(f"❌ 파일 읽기 오류: {e}")
        
        # 백업에서 복구
        backup_path = f"{parameters_file}.backup"
        if os.path.exists(backup_path):
            if st.button("🔧 백업에서 복구"):
                try:
                    import shutil
                    shutil.copy2(backup_path, parameters_file)
                    st.success("✅ 백업에서 복구되었습니다.")
                    st.rerun()
                except Exception as restore_e:
                    st.error(f"❌ 복구 실패: {restore_e}")
