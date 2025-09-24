"""
페이지 공통 유틸리티 함수들
"""
import streamlit as st
import subprocess
import os
import time
import re

# 언어 설정 딕셔너리
PAGE_TEXTS = {
    "ko": {
        # 공통 메시지
        "task_running_error": "❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.",
        "stop_task_info": "💡 사이드바의 '🛑 현재 작업 중단' 버튼을 사용하여 기존 작업을 중단할 수 있습니다.",
        "stop_task": "🛑 작업 중단",
        "task_stopped": "⚠️ 작업이 중단되었습니다.",
        "no_running_task": "실행 중인 작업이 없습니다.",
        "task_completed": "✅ {} 작업이 완료되었습니다!",
        "task_error": "❌ 작업 실행 중 오류가 발생했습니다: {}",
        "log_file": "📄 로그 파일:",
        "running_with_pid": "🔄 {}이 실행 중입니다 (PID: {})",
        
        # 환영 페이지
        "welcome_title": "🏠 Oracle Migration Assistant (OMA) 웹 애플리케이션",
        "welcome_subtitle": "Oracle에서 PostgreSQL로의 데이터베이스 마이그레이션을 위한 통합 도구",
        
        # 프로젝트 환경 정보
        "project_env_title": "📊 프로젝트 환경 정보",
        "current_env_status": "현재 환경 상태",
        "project_configured": "✅ 프로젝트가 설정되었습니다",
        "project_not_configured": "❌ 프로젝트가 설정되지 않았습니다",
        
        # 애플리케이션 분석
        "app_analysis_title": "🔍 애플리케이션 분석",
        "app_analysis_desc": "Java 소스 코드와 MyBatis Mapper 파일을 분석합니다.",
        "start_analysis": "🚀 분석 시작",
        
        # 분석 보고서
        "app_reporting_title": "📄 분석 보고서 작성",
        "app_reporting_desc": "분석 결과를 바탕으로 보고서를 생성합니다.",
        "start_reporting": "📊 보고서 생성",
        
        # 샘플 변환
        "sample_transform_title": "🧪 샘플 변환 실행",
        "sample_transform_desc": "선택된 SQL 샘플을 PostgreSQL로 변환합니다.",
        "start_sample_transform": "🧪 샘플 변환 시작",
        
        # 전체 변환
        "full_transform_title": "🚀 전체 변환 실행",
        "full_transform_desc": "모든 SQL을 PostgreSQL로 변환합니다.",
        "start_full_transform": "🚀 전체 변환 시작"
    },
    "en": {
        # 공통 메시지
        "task_running_error": "❌ Another task is running. Please complete or stop the existing task and try again.",
        "stop_task_info": "💡 You can stop the existing task using the '🛑 Stop Current Task' button in the sidebar.",
        "stop_task": "🛑 Stop Task",
        "task_stopped": "⚠️ Task has been stopped.",
        "no_running_task": "No running tasks.",
        "task_completed": "✅ {} task completed!",
        "task_error": "❌ Error occurred during task execution: {}",
        "log_file": "📄 Log file:",
        "running_with_pid": "🔄 {} is running (PID: {})",
        
        # 환영 페이지
        "welcome_title": "🏠 Oracle Migration Assistant (OMA) Web Application",
        "welcome_subtitle": "Integrated tool for database migration from Oracle to PostgreSQL",
        
        # 프로젝트 환경 정보
        "project_env_title": "📊 Project Environment Information",
        "current_env_status": "Current Environment Status",
        "project_configured": "✅ Project is configured",
        "project_not_configured": "❌ Project is not configured",
        
        # 애플리케이션 분석
        "app_analysis_title": "🔍 Application Analysis",
        "app_analysis_desc": "Analyze Java source code and MyBatis Mapper files.",
        "start_analysis": "🚀 Start Analysis",
        
        # 분석 보고서
        "app_reporting_title": "📄 Analysis Report Generation",
        "app_reporting_desc": "Generate reports based on analysis results.",
        "start_reporting": "📊 Generate Report",
        
        # 샘플 변환
        "sample_transform_title": "🧪 Sample Transform Execution",
        "sample_transform_desc": "Transform selected SQL samples to PostgreSQL.",
        "start_sample_transform": "🧪 Start Sample Transform",
        
        # 전체 변환
        "full_transform_title": "🚀 Full Transform Execution",
        "full_transform_desc": "Transform all SQL to PostgreSQL.",
        "start_full_transform": "🚀 Start Full Transform"
    }
}

def get_page_text(key, lang=None):
    """페이지별 다국어 텍스트 반환"""
    if lang is None:
        lang = st.session_state.get('language', 'ko')
    return PAGE_TEXTS.get(lang, PAGE_TEXTS['ko']).get(key, key)


def execute_command_with_logs(command, title, log_file_path=None):
    """명령어를 실행하고 실시간 로그를 표시 (특정 로그 파일 모니터링 지원)"""
    
    # 🔍 작업 시작 전 필수 체크: 실행 중인 작업 확인 및 정리
    if st.session_state.oma_controller.is_any_task_running():
        st.error(get_page_text("task_running_error"))
        
        # 현재 실행 중인 작업 정보 표시
        current_process = st.session_state.oma_controller.current_process
        running_tasks = st.session_state.task_manager.get_running_tasks()
        
        if current_process and current_process.poll() is None:
            analysis_text = "애플리케이션 분석" if st.session_state.get('language', 'ko') == 'ko' else "Application Analysis"
            st.warning(get_page_text("running_with_pid").format(analysis_text, current_process.pid))
        elif running_tasks:
            task = running_tasks[0]
            st.warning(get_page_text("running_with_pid").format(task['title'], task['pid']))
        
        st.info(get_page_text("stop_task_info"))
        return
    
    # 상단에 실행 정보와 중단 버튼 배치
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"**{title}:** `{command}`")
        if log_file_path:
            # 환경 변수 치환
            expanded_log_path = os.path.expandvars(log_file_path)
            st.caption(f"{get_page_text('log_file')} {expanded_log_path}")
    
    with col2:
        if st.button(get_page_text("stop_task"), key=f"stop_{hash(command)}", type="secondary"):
            if st.session_state.oma_controller.stop_current_process():
                st.warning(get_page_text("task_stopped"))
                st.stop()
            else:
                st.info(get_page_text("no_running_task"))
    
    # 로그 영역 (전체 화면 활용)
    log_container = st.empty()
    
    try:
        if log_file_path:
            # 특정 로그 파일을 모니터링하는 방식
            execute_with_specific_log_file(command, title, log_file_path, log_container)
        else:
            # 기존 방식 (TaskManager 사용)
            execute_with_task_manager(command, title, log_container)
        
        # 작업 완료 메시지
        st.success(get_page_text("task_completed").format(title))
        
        # 환경 변수 자동 저장 (환경 설정 관련 작업 후)
        if 'setEnv' in command or 'checkEnv' in command:
            st.session_state.oma_controller.update_environment_vars()
        
    except Exception as e:
        st.error(get_page_text("task_error").format(str(e)))


def execute_with_task_manager(command, title, log_container):
    """기존 TaskManager 방식으로 명령어 실행"""
    # 실시간 로그 수집 및 표시
    log_generator = st.session_state.oma_controller.run_command_with_logs(command, title)
    
    for log_line in log_generator:
        # 현재 작업의 모든 로그를 TaskManager에서 가져와서 표시
        current_task = st.session_state.oma_controller.get_current_task()
        if current_task:
            all_logs = st.session_state.task_manager.get_task_logs(current_task['task_id'])
            log_text = "\n".join(all_logs)
            
            # ANSI 색상 코드를 HTML로 변환
            colored_log_html = convert_ansi_to_html(log_text)
            
            with log_container.container():
                st.markdown(f"""
                <div class="log-container">
{colored_log_html}
                </div>
                """, unsafe_allow_html=True)


def convert_ansi_to_html(text):
    """ANSI 색상 코드를 HTML로 변환하고 제어 문자 제거"""
    # 모든 ANSI 이스케이프 시퀀스를 제거하고 깔끔한 텍스트만 남김
    # 커서 제어: [?25l (커서 숨김), [?25h (커서 표시)
    text = re.sub(r'\x1b\[\?25[lh]', '', text)
    
    # 기타 커서 이동, 화면 제어 시퀀스 제거
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    
    # 백스페이스, 캐리지 리턴 등 제어 문자 제거
    text = re.sub(r'[\x08\x0c\x0e\x0f]', '', text)
    
    # 연속된 공백을 하나로 정리
    text = re.sub(r' +', ' ', text)
    
    # 빈 줄 정리
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()
