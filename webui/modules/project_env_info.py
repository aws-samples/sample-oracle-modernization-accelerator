"""
프로젝트 환경 정보 페이지
"""
import streamlit as st


def render_project_env_page():
    """프로젝트 환경 정보 페이지"""
    st.markdown("## 📊 프로젝트 환경 정보")
    show_project_environment_info()


def show_project_environment_info():
    """프로젝트 환경 정보를 테이블 형태로 표시"""
    # 현재 설정 파일 로드
    config, _ = st.session_state.oma_controller.load_saved_config()
    env_vars = config.get('env_vars', {})
    
    if not env_vars:
        st.warning("⚠️ 저장된 환경 정보가 없습니다. 먼저 프로젝트를 선택해주세요.")
        return
    
    # 프로젝트 기본 정보
    project_name = env_vars.get('APPLICATION_NAME', 'Unknown')
    st.subheader(f"🎯 현재 프로젝트: **{project_name}**")
    
    # 환경 변수 테이블 데이터 준비
    table_data = []
    for key, value in sorted(env_vars.items()):
        # 비밀번호는 마스킹
        if 'PASSWORD' in key.upper():
            display_value = "••••••••"
        else:
            display_value = value
        
        table_data.append({
            "환경 변수": key,
            "값": display_value
        })
    
    # 테이블 표시
    if table_data:
        # 로그 컨테이너와 동일한 높이로 통일 (900px)
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            height=900,  # 로그 컨테이너와 동일한 높이
            column_config={
                "환경 변수": st.column_config.TextColumn(
                    "환경 변수",
                    width="medium",
                ),
                "값": st.column_config.TextColumn(
                    "값",
                    width="large",
                )
            }
        )
        
        # 요약 정보
        st.info(f"📊 총 **{len(env_vars)}개**의 환경 변수가 설정되어 있습니다.")
    else:
        st.error("환경 변수 정보를 불러올 수 없습니다.")
