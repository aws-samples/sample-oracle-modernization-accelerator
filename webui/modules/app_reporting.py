"""
분석 보고서 작성 페이지
"""
import streamlit as st
import subprocess
import os
import time
import datetime
import json


def render_app_reporting_page():
    """분석 보고서 작성 페이지"""
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="app_reporting_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📄 분석 보고서 작성")
    
    # 명령어 정보
    command = './processAppReporting.sh'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/appReporting.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    st.info(f"**실행 명령어:** `{command}`")
    st.caption(f"📄 로그 파일: {expanded_log_path}")
    
    # 실행 중인 작업 확인
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 분석 보고서 작성이 이미 실행 중입니다.")
            
            # 작업 중단 버튼
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🛑 작업 중단", key="stop_app_reporting", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        st.success("✅ 작업이 중단되었습니다.")
                        st.rerun()
                    else:
                        st.info("실행 중인 작업이 없습니다.")
            
            # 간단한 상태 표시
            st.markdown("### 📊 작업 상태")
            
            # 로그 파일 생성 확인
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                st.success(f"✅ 로그 파일이 생성되었습니다 ({file_size:,} bytes)")
                
                # 백그라운드 프로세스 완료 확인 및 메뉴 새로고침
                current_process = st.session_state.oma_controller.current_process
                running_tasks = st.session_state.task_manager.get_running_tasks()
                
                # 프로세스가 완료되었으면 홈으로 돌아가서 사이드바 새로고침
                if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
                    st.success("🎉 분석 보고서 작성이 완료되었습니다!")
                    st.info("🏠 메뉴 상태를 업데이트합니다...")
                    time.sleep(1)
                    st.session_state.selected_action = None  # 홈으로
                    st.rerun()
                
                # 로그 보기 버튼 추가
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📋 로그 보기", key="view_logs_from_app_reporting", use_container_width=True):
                        st.session_state.selected_action = "view_running_logs"
                        st.rerun()
                with col2:
                    # 수동 새로고침 버튼
                    if st.button("🔄 상태 새로고침", key="refresh_app_reporting"):
                        st.rerun()
                
                # 실시간 상태 확인을 위한 자동 새로고침 (3초마다)
                time.sleep(3)
                st.rerun()
            else:
                st.info("⏳ 로그 파일 생성 대기 중...")
                
                # 자동으로 한 번만 새로고침 (파일 생성 확인용)
                if st.button("🔄 상태 확인", key="check_app_reporting"):
                    st.rerun()
        else:
            st.error("❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.")
    else:
        # 실행 버튼 표시
        st.markdown("### 🚀 작업 실행")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📄 보고서 생성", key="start_app_reporting", type="primary", use_container_width=True):
                # 백그라운드 실행 시작
                execute_app_reporting_background(command, expanded_log_path)
                st.rerun()
        
        with col2:
            st.caption("애플리케이션 분석 결과를 바탕으로 보고서를 생성합니다")
        
        # 작업 설명
        st.markdown("### 📋 작업 내용")
        st.markdown("""
        **분석 보고서 작성 작업:**
        - 애플리케이션 분석 결과 취합
        - SQL 변환 대상 목록 생성
        - 변환 복잡도 분석
        - HTML/PDF 보고서 생성
        
        **예상 소요 시간:** 5-15분
        """)
        
        # 전제 조건
        st.info("💡 **전제 조건:** 먼저 '애플리케이션 분석' 작업이 완료되어야 합니다.")
        
        # 주의사항
        st.warning("⚠️ **주의사항:** 보고서 생성 중에는 다른 OMA 작업을 실행할 수 없습니다.")


def execute_app_reporting_background(command, log_file_path):
    """분석 보고서 작성을 백그라운드에서 실행 (스크립트가 자체적으로 로그 생성)"""
    try:
        # Task 정보 생성
        task_id = f"app_reporting_{int(time.time() * 1000)}"
        
        # Task 파일 생성
        task_data = {
            "task_id": task_id,
            "title": "분석 보고서 작성",
            "command": command,
            "pid": None,  # 실제 PID는 나중에 업데이트
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "running",
            "log_file": log_file_path  # 스크립트가 생성할 로그 파일 경로 (참조용)
        }
        
        # Task 디렉토리 생성
        os.makedirs("./oma_tasks", exist_ok=True)
        
        # Task 파일 저장
        with open(f"./oma_tasks/{task_id}.json", 'w') as f:
            json.dump(task_data, f, indent=2)
        
        # 백그라운드에서 명령 실행 ($OMA_BASE_DIR/bin에서 실행)
        bin_dir = os.path.join(os.path.expandvars("$OMA_BASE_DIR"), "bin")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=bin_dir,  # $OMA_BASE_DIR/bin에서 실행
            preexec_fn=os.setsid  # 프로세스 그룹 생성 (안전한 종료를 위해)
        )
        
        # 프로세스를 컨트롤러에 등록
        st.session_state.oma_controller.current_process = process
        
        # Task 파일에 실제 PID 업데이트
        task_data["pid"] = process.pid
        with open(f"./oma_tasks/{task_id}.json", 'w') as f:
            json.dump(task_data, f, indent=2)
        
        st.success("✅ 백그라운드 실행 시작")
        
    except Exception as e:
        st.error(f"❌ 실행 오류: {e}")
