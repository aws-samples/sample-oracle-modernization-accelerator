"""
애플리케이션 분석 페이지
"""
import streamlit as st
import subprocess
import os
import time
import datetime
from .utils import get_page_text, execute_command_with_logs


def render_app_analysis_page():
    """애플리케이션 분석 페이지 렌더링"""
    current_lang = st.session_state.get('language', 'ko')
    
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        home_text = "🏠 홈으로" if current_lang == 'ko' else "🏠 Home"
        if st.button(home_text, key="app_analysis_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown(f"## {get_page_text('app_analysis_title')}")
    
    # 설명
    st.markdown(f"**{get_page_text('app_analysis_desc')}**")
    
    # 명령어 정보
    command = 'q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appAnalysis.md"'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/appAnalysis.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    command_text = "실행 명령어:" if current_lang == 'ko' else "Command:"
    st.info(f"**{command_text}** `{command}`")
    st.caption(f"{get_page_text('log_file')} {expanded_log_path}")
    
    # 실행 중인 작업 확인
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            running_text = "🔄 애플리케이션 분석이 이미 실행 중입니다." if current_lang == 'ko' else "🔄 Application analysis is already running."
            st.warning(running_text)
            
            # 작업 중단 버튼
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(get_page_text("stop_task"), key="stop_app_analysis", type="secondary"):
                    if st.session_state.oma_controller.stop_current_process():
                        success_text = "✅ 작업이 중단되었습니다." if current_lang == 'ko' else "✅ Task has been stopped."
                        st.success(success_text)
                        st.rerun()
                    else:
                        st.info(get_page_text("no_running_task"))
            
            # 간단한 상태 표시
            status_text = "### 📊 작업 상태" if current_lang == 'ko' else "### 📊 Task Status"
            st.markdown(status_text)
            
            # 로그 파일 생성 확인
            if os.path.exists(expanded_log_path):
                file_size = os.path.getsize(expanded_log_path)
                log_created_text = "✅ 로그 파일이 생성되었습니다" if current_lang == 'ko' else "✅ Log file created"
                st.success(f"{log_created_text} ({file_size:,} bytes)")
                
                # 백그라운드 프로세스 완료 확인 및 메뉴 새로고침
                current_process = st.session_state.oma_controller.current_process
                running_tasks = st.session_state.task_manager.get_running_tasks()
                
                # 프로세스가 완료되었으면 홈으로 돌아가서 사이드바 새로고침
                if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
                    completed_text = "🎉 애플리케이션 분석이 완료되었습니다!" if current_lang == 'ko' else "🎉 Application analysis completed!"
                    update_text = "🏠 메뉴 상태를 업데이트합니다..." if current_lang == 'ko' else "🏠 Updating menu status..."
                    st.success(completed_text)
                    st.info(update_text)
                    time.sleep(1)
                    st.session_state.selected_action = None  # 홈으로
                    st.rerun()
                
                # 로그 보기 버튼 추가
                col1, col2 = st.columns([1, 1])
                with col1:
                    view_logs_text = "📋 로그 보기" if current_lang == 'ko' else "📋 View Logs"
                    if st.button(view_logs_text, key="view_logs_from_analysis", use_container_width=True):
                        st.session_state.selected_action = "view_running_logs"
                        st.rerun()
                with col2:
                    # 수동 새로고침 버튼
                    refresh_text = "🔄 상태 새로고침" if current_lang == 'ko' else "🔄 Refresh Status"
                    if st.button(refresh_text, key="refresh_status"):
                        st.rerun()
                
                # 실시간 상태 확인을 위한 자동 새로고침 (3초마다)
                time.sleep(3)
                st.rerun()
            else:
                waiting_text = "⏳ 로그 파일 생성 대기 중..." if current_lang == 'ko' else "⏳ Waiting for log file creation..."
                st.info(waiting_text)
                
                # 자동으로 한 번만 새로고침 (파일 생성 확인용)
                check_status_text = "🔄 상태 확인" if current_lang == 'ko' else "🔄 Check Status"
                if st.button(check_status_text, key="check_status"):
                    st.rerun()
        else:
            error_text = "❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요." if current_lang == 'ko' else "❌ Another task is running. Please complete or stop the existing task and try again."
            st.error(error_text)
    else:
        # 실행 버튼 표시
        execution_text = "### 🚀 작업 실행" if current_lang == 'ko' else "### 🚀 Task Execution"
        st.markdown(execution_text)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button(get_page_text("start_analysis"), key="start_app_analysis", type="primary", use_container_width=True):
                # 백그라운드 실행 시작
                execute_app_analysis_background(command, expanded_log_path)
                st.rerun()
        
        with col2:
            desc_text = "Java 소스 코드와 MyBatis Mapper 파일을 분석합니다" if current_lang == 'ko' else "Analyze Java source code and MyBatis Mapper files"
            st.caption(desc_text)
        
        # 작업 설명
        task_content_text = "### 📋 작업 내용" if current_lang == 'ko' else "### 📋 Task Details"
        st.markdown(task_content_text)
        
        if current_lang == 'ko':
            st.markdown("""
            **애플리케이션 분석 작업:**
            - Java 소스 코드 분석
            - MyBatis Mapper 파일 분석  
            - SQL 변환 대상 추출
            - 분석 결과 보고서 생성
            
            **예상 소요 시간:** 프로젝트 크기에 따라 5-30분
            """)
        else:
            st.markdown("""
            **Application Analysis Tasks:**
            - Java source code analysis
            - MyBatis Mapper file analysis  
            - SQL transformation target extraction
            - Analysis result report generation
            
            **Estimated Duration:** 5-30 minutes depending on project size
            """)
        
        # 주의사항
        if current_lang == 'ko':
            st.warning("⚠️ **주의사항:** 분석 작업은 시간이 오래 걸릴 수 있습니다. 작업 중에는 다른 OMA 작업을 실행할 수 없습니다.")
        else:
            st.warning("⚠️ **Note:** Analysis tasks may take a long time. No other OMA tasks can be executed during the analysis.")


def execute_app_analysis_background(command, log_file_path):
    """애플리케이션 분석을 백그라운드에서 실행"""
    current_lang = st.session_state.get('language', 'ko')
    
    try:
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(log_file_path)
        os.makedirs(log_dir, exist_ok=True)
        
        # 로그 파일 초기화
        with open(log_file_path, 'w', encoding='utf-8') as f:
            start_text = "애플리케이션 분석 시작" if current_lang == 'ko' else "Application Analysis Started"
            f.write(f"=== {start_text} ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
        
        # 백그라운드 실행
        cwd = os.path.join(st.session_state.oma_controller.oma_base_dir, 'bin')
        full_command = f"cd '{cwd}' && nohup {command} >> '{log_file_path}' 2>&1 &"
        
        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # 잠시 대기
        time.sleep(2)
        
        # 실제 프로세스 PID 찾기
        try:
            find_cmd = "pgrep -f 'q chat.*appAnalysis'"
            result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                actual_pid = int(result.stdout.strip().split('\n')[0])
                success_text = "✅ 백그라운드 실행 시작" if current_lang == 'ko' else "✅ Background execution started"
                st.success(f"{success_text} (PID: {actual_pid})")
            else:
                actual_pid = process.pid
                warning_text = "⚠️ PID 감지 실패, 기본 PID 사용:" if current_lang == 'ko' else "⚠️ PID detection failed, using default PID:"
                st.warning(f"{warning_text} {actual_pid}")
        except Exception as e:
            actual_pid = process.pid
            error_text = "⚠️ PID 감지 오류:" if current_lang == 'ko' else "⚠️ PID detection error:"
            st.warning(f"{error_text} {e}")
        
        # 백그라운드 프로세스 객체 생성
        class BackgroundProcess:
            def __init__(self, pid):
                self.pid = pid
            def poll(self):
                try:
                    os.kill(self.pid, 0)
                    return None  # 실행 중
                except OSError:
                    return 0  # 종료됨
        
        bg_process = BackgroundProcess(actual_pid)
        
        # 프로세스 정보 저장
        st.session_state.oma_controller.current_process = bg_process
        st.session_state.app_analysis_start_time = time.time()
        
        # TaskManager에 등록 (로그 파일 경로 포함)
        task_id = f"app_analysis_{int(time.time() * 1000)}"
        task_title = "애플리케이션 분석" if current_lang == 'ko' else "Application Analysis"
        task_info = st.session_state.task_manager.create_task(
            task_id, task_title, command, actual_pid, log_file_path
        )
        
        st.session_state.oma_controller.current_task_id = task_id
        
    except Exception as e:
        error_text = "❌ 실행 오류:" if current_lang == 'ko' else "❌ Execution error:"
        st.error(f"{error_text} {e}")
