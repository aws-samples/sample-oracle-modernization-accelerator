"""
OMA Streamlit 메뉴 템플릿
======================

새로운 메뉴를 추가할 때 이 템플릿을 복사해서 사용하세요.

사용법:
1. 이 파일을 복사해서 필요한 부분만 수정
2. oma_streamlit_app.py의 render_action_page()에 새 메뉴 추가
3. 사이드바 메뉴 설정에 새 메뉴 추가
"""

import streamlit as st
import os
import subprocess
import time

def render_MENU_NAME_page():
    """
    새 메뉴 페이지 렌더링
    
    수정 필요한 부분:
    - MENU_NAME: 실제 메뉴 이름으로 변경
    - 🔍 아이콘: 적절한 아이콘으로 변경
    - 메뉴 제목: 실제 메뉴 제목으로 변경
    - command: 실제 실행할 명령어로 변경
    - log_file_path: 실제 로그 파일 경로로 변경
    - key 값들: 고유한 key로 변경
    """
    
    # 1. 상단 홈 버튼
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="MENU_NAME_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 🔍 메뉴 제목")  # 여기 수정
    
    # 2. 명령어 정보
    command = '실제 실행할 명령어'  # 여기 수정
    log_file_path = "$APP_LOGS_FOLDER/qlogs/MENU_NAME.log"  # 여기 수정
    expanded_log_path = os.path.expandvars(log_file_path)
    
    # 3. 실행 중인 작업 확인 및 백그라운드 실행
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 작업이 이미 실행 중입니다.")
        else:
            st.error("❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.")
            return
    else:
        # 즉시 백그라운드 실행
        execute_MENU_NAME_background(command, expanded_log_path)  # 여기 수정
    
    # 4. 상단에 명령어 표시
    st.info(f"**실행 명령어:** `{command}`")
    st.caption(f"📄 로그 파일: {expanded_log_path}")
    
    # 5. 작업 중단 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🛑 작업 중단", key="stop_MENU_NAME", type="secondary"):  # 여기 수정
            if st.session_state.oma_controller.stop_current_process():
                st.success("✅ 작업이 중단되었습니다.")
            else:
                st.info("실행 중인 작업이 없습니다.")
    
    # 6. 간단한 상태 표시
    st.markdown("### 📊 작업 상태")
    
    # 로그 파일 생성 확인
    if os.path.exists(expanded_log_path):
        file_size = os.path.getsize(expanded_log_path)
        st.success(f"✅ 로그 파일이 생성되었습니다 ({file_size:,} bytes)")
        
        # 로그 보기 버튼 추가
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📋 로그 보기", key="view_logs_from_MENU_NAME", use_container_width=True):  # 여기 수정
                st.session_state.selected_action = "view_running_logs"
                st.rerun()
        with col2:
            # 수동 새로고침 버튼
            if st.button("🔄 상태 새로고침", key="refresh_MENU_NAME"):  # 여기 수정
                st.rerun()
    else:
        st.info("⏳ 로그 파일 생성 대기 중...")
        
        # 자동으로 한 번만 새로고침 (파일 생성 확인용)
        if st.button("🔄 상태 확인", key="check_MENU_NAME"):  # 여기 수정
            st.rerun()


def execute_MENU_NAME_background(command, log_file_path):
    """
    백그라운드에서 작업 실행
    
    수정 필요한 부분:
    - MENU_NAME: 실제 메뉴 이름으로 변경
    - task_id: 고유한 task_id 패턴으로 변경
    - title: 실제 작업 제목으로 변경
    
    작업 완료 시 task 파일은 자동으로 삭제됩니다.
    """
    try:
        # Task 정보 생성
        import time
        task_id = f"MENU_NAME_{int(time.time() * 1000)}"  # 여기 수정
        
        # Task 파일 생성
        task_data = {
            "task_id": task_id,
            "title": "작업 제목",  # 여기 수정
            "command": command,
            "pid": None,  # 실제 PID는 나중에 업데이트
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "running",
            "log_file": log_file_path
        }
        
        # Task 디렉토리 생성
        os.makedirs("./oma_tasks", exist_ok=True)
        
        # Task 파일 저장
        import json
        with open(f"./oma_tasks/{task_id}.json", 'w') as f:
            json.dump(task_data, f, indent=2)
        
        # 백그라운드에서 명령 실행
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.expandvars("$OMA_BASE_DIR")
        )
        
        # 프로세스를 컨트롤러에 등록
        st.session_state.oma_controller.current_process = process
        
        # Task 파일에 실제 PID 업데이트
        task_data["pid"] = process.pid
        with open(f"./oma_tasks/{task_id}.json", 'w') as f:
            json.dump(task_data, f, indent=2)
        
        st.success("✅ 백그라운드 실행 시작")
        
        # 참고: 작업 완료 시 task 파일은 check_and_cleanup_completed_tasks()에서 자동 삭제됩니다.
        
    except Exception as e:
        st.error(f"❌ 실행 오류: {e}")


# =============================================================================
# 사이드바 메뉴 추가 방법
# =============================================================================
"""
1. oma_streamlit_app.py의 사이드바 메뉴 설정 부분에 추가:

MENU_STRUCTURE = {
    "🔍 애플리케이션 분석": {
        "애플리케이션 분석": "app_analysis",
        "새 메뉴": "MENU_NAME",  # 여기 추가
        "분석 보고서 작성": "app_reporting",
        # ...
    },
    # ...
}

2. render_action_page() 함수에 추가:

elif action_key == "MENU_NAME":
    render_MENU_NAME_page()

"""

# =============================================================================
# 체크리스트
# =============================================================================
"""
새 메뉴 추가 시 확인사항:

□ MENU_NAME을 실제 메뉴 이름으로 변경
□ 아이콘과 제목 수정
□ 실행할 명령어 수정
□ 로그 파일 경로 수정
□ 모든 key 값들을 고유하게 수정
□ task_id 패턴 수정
□ 작업 제목 수정
□ 사이드바 메뉴에 추가
□ render_action_page()에 추가
□ 테스트: 실행 → 로그 보기 → 홈 버튼

"""
