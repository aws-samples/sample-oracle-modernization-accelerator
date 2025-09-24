#!/usr/bin/env python3
"""
OMA (Oracle Migration Assistant) Streamlit Web Application
기존 initOMA.sh shell 스크립트를 웹 인터페이스로 변환
"""

import streamlit as st
import subprocess
import os
import sys
import time
import threading
from pathlib import Path
import queue
import signal
import json
import re
import datetime
import tempfile
import re
import json

# 분리된 페이지 모듈들 import
from pages import (
    render_welcome_page,
    render_project_env_page,
    render_app_analysis_page,
    render_app_reporting_page,
    render_postgresql_meta_page,
    render_running_logs_page,
    render_sample_transform_page,
    render_full_transform_page,
    render_test_fix_page,
    render_merge_transform_page,
    render_xml_list_page,
    render_sql_unittest_page,
    render_transform_report_page,
    render_java_transform_page
)

# 페이지 설정
st.set_page_config(
    page_title="OMA - Oracle Migration Assistant",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .step-container {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #f8f9fa;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .log-container {
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        max-height: 900px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 14px;
        line-height: 1.4;
        border: 1px solid #444;
    }
    
    .log-container span {
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
    }
    .sidebar-menu {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .menu-item {
        padding: 0.5rem;
        margin: 0.2rem 0;
        border-radius: 5px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .menu-item:hover {
        background-color: #e0e0e0;
    }
    .menu-item.active {
        background-color: #4ECDC4;
        color: white;
    }
    .tree-menu-main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        margin: 4px 0;
        padding: 8px 12px;
        border: none;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .tree-menu-main:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .tree-menu-sub {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        border-radius: 6px;
        margin: 2px 0 2px 20px;
        padding: 6px 10px;
        border: none;
        font-size: 0.9em;
        font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .tree-menu-sub:hover {
        transform: translateX(2px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
    .menu-expanded {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .sidebar .stButton > button {
        transition: all 0.3s ease;
    }
    
    /* 메인 메뉴 버튼 스타일 */
    .sidebar .stButton > button[kind="primary"] {
        background: transparent;
        color: #333;
        border: none;
        border-radius: 0;
        margin: 2px 0;
        padding: 8px 4px;
        font-weight: 600;
        box-shadow: none;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        text-align: left;
        width: 100%;
    }
    
    .sidebar .stButton > button[kind="primary"]:hover {
        background: rgba(70, 130, 180, 0.1);
        transform: none;
        box-shadow: none;
    }
    
    /* 서브 메뉴 버튼 스타일 */
    .sidebar .stButton > button[kind="secondary"] {
        background: transparent;
        color: #555;
        border: none;
        border-radius: 0;
        margin: 1px 0;
        padding: 2px 4px;
        font-size: 0.85em;
        font-weight: 400;
        box-shadow: none;
        font-family: 'Courier New', monospace;
        text-align: left;
        width: 100%;
    }
    
    .sidebar .stButton > button[kind="secondary"]:hover {
        background: rgba(255, 140, 0, 0.1);
        transform: none;
        box-shadow: none;
        color: #ff8c00;
    }
    
    .sidebar .stButton > button[kind="secondary"]:focus {
        background: transparent;
        box-shadow: none;
        outline: none;
    }
    
    /* 트리 구조 컨테이너 */
    .tree-container {
        background: transparent;
        border: none;
        border-radius: 0;
        padding: 8px 0;
        margin: 4px 0;
        font-family: 'Courier New', monospace;
        font-size: 0.85em;
        line-height: 1.3;
    }
    /* 아코디언 스타일 메뉴 */
    .sidebar .streamlit-expanderHeader {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 4px 0;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .sidebar .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .sidebar .streamlit-expanderContent {
        background: #f8f9fa;
        border-radius: 0 0 8px 8px;
        padding: 8px;
        margin-bottom: 8px;
        border-left: 3px solid #667eea;
    }
    
    .sidebar .streamlit-expanderContent .stButton > button {
        background: white;
        color: #333;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        margin: 2px 0;
        padding: 8px 12px;
        font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .sidebar .streamlit-expanderContent .stButton > button:hover {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        border-color: #ff9a9e;
        transform: translateX(2px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

class TaskManager:
    """작업 상태를 파일 기반으로 관리하는 클래스"""
    
    def __init__(self):
        self.tasks_dir = os.path.join(os.getcwd(), "oma_tasks")  # 현재 디렉토리에 task 파일만
        
        # 디렉토리 생성
        os.makedirs(self.tasks_dir, exist_ok=True)
        
        # 시작 시 종료된 작업들 정리
        self.cleanup_finished_tasks()
    
    def create_task(self, task_id, title, command, pid, log_file=None):
        """새 작업 생성"""
        task_info = {
            "task_id": task_id,
            "title": title,
            "command": command,
            "pid": pid,
            "start_time": datetime.datetime.now().isoformat(),
            "status": "running",
            "log_file": log_file or "no_log_file"  # 실제 로그 파일 경로 또는 기본값
        }
        
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_info, f, indent=2, ensure_ascii=False)
        
        return task_info
    
    def get_running_tasks(self):
        """실행 중인 작업 목록 반환"""
        running_tasks = []
        
        if not os.path.exists(self.tasks_dir):
            return running_tasks
        
        for task_file in os.listdir(self.tasks_dir):
            if task_file.endswith('.json'):
                try:
                    with open(os.path.join(self.tasks_dir, task_file), 'r', encoding='utf-8') as f:
                        task_info = json.load(f)
                    
                    # 프로세스가 실제로 실행 중인지 확인
                    if self.is_process_running(task_info['pid']):
                        running_tasks.append(task_info)
                    else:
                        # 종료된 프로세스는 정리
                        self.finish_task(task_info['task_id'])
                        
                except Exception as e:
                    print(f"작업 파일 읽기 오류: {e}")
        
        return running_tasks
    
    def get_task_info(self, task_id):
        """특정 작업 정보 반환"""
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        if os.path.exists(task_file):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"작업 정보 읽기 오류: {e}")
        return None
    
    def get_task_logs(self, task_id, tail_lines=100):
        """작업 로그 읽기 (최근 N줄)"""
        task_info = self.get_task_info(task_id)
        if task_info and os.path.exists(task_info['log_file']):
            try:
                with open(task_info['log_file'], 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    return [line.rstrip() for line in lines[-tail_lines:]]
            except Exception as e:
                print(f"로그 읽기 오류: {e}")
        return []
    
    def finish_task(self, task_id):
        """작업 완료 처리"""
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        if os.path.exists(task_file):
            try:
                # 작업 정보 파일 삭제
                os.remove(task_file)
            except Exception as e:
                print(f"작업 정리 오류: {e}")
    
    def kill_task(self, task_id):
        """작업 강제 종료"""
        task_info = self.get_task_info(task_id)
        if task_info:
            try:
                pid = task_info['pid']
                if self.is_process_running(pid):
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    # 로그 파일에 중단 메시지 추가
                    if os.path.exists(task_info['log_file']):
                        with open(task_info['log_file'], 'a', encoding='utf-8') as f:
                            f.write(f"\n=== 작업이 사용자에 의해 중단되었습니다 ===\n")
                
                self.finish_task(task_id)
                return True
            except Exception as e:
                print(f"작업 중단 오류: {e}")
        return False
    
    def is_process_running(self, pid):
        """프로세스가 실행 중인지 확인"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def get_all_tasks(self):
        """모든 작업 목록 반환 (완료된 작업 포함)"""
        all_tasks = []
        
        # 실행 중인 작업들
        running_tasks = self.get_running_tasks()
        all_tasks.extend(running_tasks)
        
        # 로그 디렉토리에서 완료된 작업들 찾기
        if os.path.exists(self.logs_dir):
            for log_file in os.listdir(self.logs_dir):
                if log_file.endswith('.log'):
                    task_id = log_file[:-4]  # .log 제거
                    
                    # 이미 실행 중인 작업이 아닌 경우만
                    if not any(task['task_id'] == task_id for task in running_tasks):
                        log_path = os.path.join(self.logs_dir, log_file)
                        try:
                            # 로그 파일의 수정 시간을 기준으로 작업 정보 생성
                            mtime = os.path.getmtime(log_path)
                            completed_task = {
                                "task_id": task_id,
                                "title": "완료된 작업",
                                "command": "unknown",
                                "pid": 0,
                                "start_time": datetime.datetime.fromtimestamp(mtime).isoformat(),
                                "status": "completed",
                                "log_file": log_path
                            }
                            all_tasks.append(completed_task)
                        except Exception as e:
                            print(f"완료된 작업 정보 생성 오류: {e}")
        
        # 시작 시간 기준으로 정렬
        all_tasks.sort(key=lambda x: x['start_time'])
        return all_tasks
    
    def cleanup_finished_tasks(self):
        """종료된 작업들 정리"""
        if not os.path.exists(self.tasks_dir):
            return
        
        for task_file in os.listdir(self.tasks_dir):
            if task_file.endswith('.json'):
                try:
                    with open(os.path.join(self.tasks_dir, task_file), 'r', encoding='utf-8') as f:
                        task_info = json.load(f)
                    
                    if not self.is_process_running(task_info['pid']):
                        self.finish_task(task_info['task_id'])
                        
                except Exception as e:
                    print(f"정리 중 오류: {e}")

# 전역 작업 관리자
if 'task_manager' not in st.session_state:
    st.session_state.task_manager = TaskManager()

class OMAController:
    def __init__(self):
        self.oma_base_dir = self.get_oma_base_dir()
        self.current_process = None
        self.current_task_id = None  # 현재 작업 ID
        self.log_queue = queue.Queue()
        self.config_file = os.path.join(os.getcwd(), ".oma_config.json")
        # 생성자에서는 로드하지 않음 (main에서 처리)
        
    def get_oma_base_dir(self):
        """OMA_BASE_DIR 환경 변수 확인 및 설정"""
        oma_dir = os.environ.get('OMA_BASE_DIR')
        if not oma_dir:
            # 기본값으로 ~/workspace/oma 사용
            oma_dir = os.path.expanduser("~/workspace/oma")
        return oma_dir
    
    def is_running(self):
        """현재 실행 중인 작업이 있는지 확인"""
        running_tasks = st.session_state.task_manager.get_running_tasks()
        return len(running_tasks) > 0
    
    def get_current_task(self):
        """현재 실행 중인 작업 정보 반환"""
        running_tasks = st.session_state.task_manager.get_running_tasks()
        return running_tasks[0] if running_tasks else None
    
    def load_saved_config(self):
        """저장된 환경 설정 로드 및 시스템 환경변수에 적용"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # 저장된 환경변수들을 시스템 환경변수로 복원
                    env_vars = config.get('env_vars', {})
                    if env_vars:
                        for key, value in env_vars.items():
                            os.environ[key] = value
                    
                    return config, len(env_vars)  # 변수 개수도 반환
        except Exception as e:
            return {}, 0
        return {}, 0
    
    def save_config(self, env_vars=None):
        """환경 설정 저장"""
        try:
            config = {
                'oma_base_dir': self.oma_base_dir,
                'env_vars': env_vars or {},
                'last_updated': time.time(),
                'config_file_location': self.config_file
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            st.error(f"설정 파일 저장 중 오류: {e}")
            return False
    
    def update_environment_vars(self):
        """현재 환경 변수를 파일에 저장"""
        # checkEnv.sh에서 확인하는 모든 환경변수들
        important_vars = [
            # 핵심 환경 변수
            'APPLICATION_NAME', 'OMA_BASE_DIR', 'JAVA_SOURCE_FOLDER',
            'SOURCE_SQL_MAPPER_FOLDER', 'TARGET_SQL_MAPPER_FOLDER',
            'TRANSFORM_JNDI', 'TRANSFORM_RELATED_CLASS',
            'SOURCE_DBMS_TYPE', 'TARGET_DBMS_TYPE',
            
            # 폴더 관련
            'DBMS_FOLDER', 'DBMS_LOGS_FOLDER', 'APPLICATION_FOLDER',
            'APP_TOOLS_FOLDER', 'APP_TRANSFORM_FOLDER', 'APP_LOGS_FOLDER',
            'TEST_FOLDER', 'TEST_LOGS_FOLDER',
            
            # Oracle 연결 정보
            'ORACLE_ADM_USER', 'ORACLE_ADM_PASSWORD', 'ORACLE_HOST',
            'ORACLE_PORT', 'ORACLE_SID', 'ORACLE_SVC_USER',
            'ORACLE_SVC_PASSWORD', 'ORACLE_SVC_CONNECT_STRING',
            'ORACLE_SVC_USER_LIST', 'SERVICE_NAME', 'NLS_LANG',
            
            # PostgreSQL 연결 정보
            'PG_SVC_PASSWORD', 'PGPORT', 'PGPASSWORD', 'PG_ADM_PASSWORD',
            'PG_ADM_USER', 'PG_SVC_USER', 'PGUSER', 'PGDATABASE', 'PGHOST',
            
            # 시스템 환경 변수
            'JAVA_HOME', 'PATH', 'HOME', 'USER'
        ]
        
        env_vars = {}
        
        for var in important_vars:
            if var in os.environ:
                env_vars[var] = os.environ[var]
        
        return self.save_config(env_vars)
    
    def get_available_projects(self):
        """oma.properties에서 사용 가능한 프로젝트 목록 추출"""
        properties_file = os.path.join(self.oma_base_dir, "config", "oma.properties")
        projects = []
        
        try:
            if os.path.exists(properties_file):
                with open(properties_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # [프로젝트명] 형태의 섹션 찾기 (COMMON 제외)
                        if line.startswith('[') and line.endswith(']') and line != '[COMMON]':
                            project_name = line[1:-1]  # 대괄호 제거
                            projects.append(project_name)
        except Exception as e:
            st.error(f"oma.properties 파일 읽기 오류: {e}")
        
        return projects
    
    def get_project_config(self, project_name):
        """특정 프로젝트의 설정 정보 추출 (COMMON + 프로젝트 설정 병합)"""
        properties_file = os.path.join(self.oma_base_dir, "config", "oma.properties")
        config = {}
        
        try:
            if os.path.exists(properties_file):
                with open(properties_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                current_section = None
                raw_config = {}
                
                # 1단계: 원본 값들 수집
                for line in lines:
                    line = line.strip()
                    
                    # 섹션 헤더 확인
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]  # 대괄호 제거
                        continue
                    
                    # 설정 값 파싱 (COMMON 또는 선택된 프로젝트 섹션에서만)
                    if (current_section == 'COMMON' or current_section == project_name) and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        raw_config[key] = value
                
                # APPLICATION_NAME은 반드시 포함
                raw_config['APPLICATION_NAME'] = project_name
                
                # 2단계: 환경 변수 치환 (여러 번 반복하여 의존성 해결)
                config = raw_config.copy()
                
                # 최대 5번 반복하여 모든 변수 치환
                for iteration in range(5):
                    changed = False
                    for key, value in config.items():
                        if '${' in value:
                            original_value = value
                            
                            # 기본 변수들 치환
                            value = value.replace('${APPLICATION_NAME}', project_name)
                            value = value.replace('${OMA_BASE_DIR}', self.oma_base_dir)
                            
                            # config 내의 다른 값들로 치환
                            for config_key, config_value in config.items():
                                if config_key != key and '${' not in config_value:
                                    value = value.replace('${' + config_key + '}', config_value)
                            
                            # 시스템 환경 변수로 치환
                            for env_key, env_value in os.environ.items():
                                value = value.replace('${' + env_key + '}', env_value)
                            
                            if value != original_value:
                                config[key] = value
                                changed = True
                    
                    # 더 이상 변화가 없으면 종료
                    if not changed:
                        break
                
        except Exception as e:
            st.error(f"프로젝트 설정 읽기 오류: {e}")
        
        return config
    
    def set_project_environment(self, project_name):
        """선택된 프로젝트의 환경 변수 설정 (COMMON + 프로젝트 모든 변수 저장)"""
        if not project_name:
            return False
        
        # 프로젝트 설정 가져오기 (COMMON + 프로젝트 병합)
        project_config = self.get_project_config(project_name)
        
        if not project_config:
            st.error(f"프로젝트 '{project_name}' 설정을 찾을 수 없습니다.")
            return False
        
        # 모든 설정을 환경 변수로 설정
        for key, value in project_config.items():
            env_key = key.upper()
            os.environ[env_key] = value
            
        # 디버그: 설정된 변수 개수 표시
        st.info(f"📊 총 {len(project_config)}개 환경 변수가 설정되었습니다.")
        
        # 설정 파일에 저장 (모든 중요한 환경변수 포함)
        save_result = self.update_environment_vars()
        
        if save_result:
            st.success(f"💾 프로젝트 '{project_name}' 설정이 JSON 파일에 저장되었습니다.")
        else:
            st.error("❌ JSON 파일 저장에 실패했습니다.")
            
        return save_result
    
    def check_environment(self):
        """환경 변수 확인"""
        app_name = os.environ.get('APPLICATION_NAME')
        return {
            'oma_base_dir': self.oma_base_dir,
            'application_name': app_name,
            'is_configured': bool(app_name),
            'config_file': self.config_file
        }
    
    def run_command_with_logs(self, command, title="작업", cwd=None):
        """명령어를 실행하고 실시간 로그를 반환 (파일 기반 하이브리드 방식)"""
        # 이미 실행 중인 작업이 있는지 확인
        if self.is_running():
            yield "❌ 다른 작업이 실행 중입니다. 잠시 후 다시 시도하세요."
            return
        
        if cwd is None:
            cwd = os.path.join(self.oma_base_dir, 'bin')
        
        # 고유한 작업 ID 생성
        task_id = f"task_{int(time.time() * 1000)}"
        log_file = os.path.join(st.session_state.task_manager.logs_dir, f"{task_id}.log")
        
        try:
            # 프로세스 시작 (리다이렉션 없이 직접 파이프 사용)
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=cwd,
                preexec_fn=os.setsid  # 프로세스 그룹 생성
            )
            
            self.current_process = process
            self.current_task_id = task_id
            
            # TaskManager에 작업 등록
            task_info = st.session_state.task_manager.create_task(
                task_id, title, command, process.pid
            )
            
            # 실시간 로그 수집 및 파일 저장
            yield from self.collect_logs_and_save(process, log_file, task_id)
            
            # 프로세스 완료 대기
            process.wait()
            
            # 완료 로그 추가
            completion_msg = f"=== {title} 완료 (종료 코드: {process.returncode}) ==="
            st.session_state.task_manager.append_log(task_id, completion_msg)
            yield completion_msg
            
        except Exception as e:
            error_msg = f"❌ 오류 발생: {str(e)}"
            if task_id:
                st.session_state.task_manager.append_log(task_id, error_msg)
            yield error_msg
        finally:
            # 작업 완료 처리
            if task_id:
                st.session_state.task_manager.finish_task(task_id)
            self.current_process = None
            self.current_task_id = None
    
    def collect_logs_and_save(self, process, log_file, task_id):
        """프로세스 출력을 실시간으로 수집하고 파일에 저장"""
        try:
            # 로그 파일 열기
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== 작업 시작: {task_id} ===\n")
                f.flush()
                
                # 실시간 로그 수집
                while True:
                    line = process.stdout.readline()
                    if not line:
                        # 프로세스가 종료되었는지 확인
                        if process.poll() is not None:
                            break
                        continue
                    
                    # 줄바꿈 문자 제거
                    clean_line = line.rstrip('\n\r')
                    if clean_line:  # 빈 줄이 아닌 경우만
                        # 파일에 저장
                        f.write(clean_line + '\n')
                        f.flush()  # 즉시 파일에 쓰기
                        
                        # 화면에 표시
                        yield clean_line
                
                # 완료 메시지 추가
                f.write(f"=== 작업 완료: {task_id} ===\n")
                f.flush()
                
        except Exception as e:
            error_msg = f"로그 수집 오류: {e}"
            yield error_msg
            # 오류도 파일에 저장
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(error_msg + '\n')
            except:
                pass
    
    def cleanup_dead_processes(self):
        """죽은 프로세스들을 정리하고 실제 실행 상태를 반환"""
        cleaned = False
        
        # 1. current_process 확인 및 정리
        if self.current_process:
            if self.current_process.poll() is not None:
                # 프로세스가 종료됨
                if self.current_task_id:
                    st.session_state.task_manager.finish_task(self.current_task_id)
                self.current_process = None
                self.current_task_id = None
                cleaned = True
        
        # 2. TaskManager의 죽은 작업들 정리
        running_tasks = st.session_state.task_manager.get_running_tasks()
        for task in running_tasks:
            if not st.session_state.task_manager.is_process_running(task['pid']):
                st.session_state.task_manager.finish_task(task['task_id'])
                cleaned = True
        
        return cleaned
    
    def is_any_task_running(self):
        """현재 실행 중인 작업이 있는지 확인 (죽은 프로세스 자동 정리)"""
        # 먼저 죽은 프로세스들 정리
        self.cleanup_dead_processes()
        
        # 실제 실행 중인 작업 확인
        has_current_process = self.current_process and self.current_process.poll() is None
        has_running_tasks = len(st.session_state.task_manager.get_running_tasks()) > 0
        
        return has_current_process or has_running_tasks
    
    def stop_current_process(self):
        """현재 실행 중인 프로세스 중단 (current_process 우선)"""
        # 1. current_process 우선 확인 (애플리케이션 분석)
        if self.current_process and self.current_process.poll() is None:
            try:
                # 프로세스 그룹 전체 종료
                os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                
                # 로그 파일에 중단 메시지 추가
                if self.current_task_id:
                    app_analysis_log = os.path.expandvars("$APP_LOGS_FOLDER/qlogs/appAnalysis.log")
                    if os.path.exists(app_analysis_log):
                        with open(app_analysis_log, 'a', encoding='utf-8') as f:
                            f.write(f"\n=== 작업이 사용자에 의해 중단되었습니다 (PID: {self.current_process.pid}) ===\n")
                    
                    # TaskManager에서도 정리
                    st.session_state.task_manager.finish_task(self.current_task_id)
                
                self.current_process = None
                self.current_task_id = None
                return True
            except Exception as e:
                print(f"애플리케이션 분석 프로세스 중단 오류: {e}")
        
        # 2. TaskManager 기반 작업 중단
        running_tasks = st.session_state.task_manager.get_running_tasks()
        if running_tasks:
            current_task = running_tasks[0]
            try:
                success = st.session_state.task_manager.kill_task(current_task['task_id'])
                if success:
                    self.current_process = None
                    self.current_task_id = None
                return success
            except Exception as e:
                print(f"TaskManager 작업 중단 오류: {e}")
        
        return False

# 전역 OMA 컨트롤러 인스턴스
if 'oma_controller' not in st.session_state:
    st.session_state.oma_controller = OMAController()

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

def main():
    # 앱 시작 시 저장된 설정 자동 로드 (한 번만 실행)
    if 'config_loaded' not in st.session_state:
        config, var_count = st.session_state.oma_controller.load_saved_config()
        if var_count > 0:
            project_name = os.environ.get('APPLICATION_NAME', 'Unknown')
            st.success(f"💾 저장된 환경 설정을 복원했습니다 ({var_count}개 변수) - 프로젝트: {project_name}")
        st.session_state.config_loaded = True
    
    # 환경 상태 확인
    env_status = st.session_state.oma_controller.check_environment()
    
    # 사이드바 - 메뉴 및 환경 정보
    with st.sidebar:
        st.header("🔧 환경 정보")
        
        # 프로젝트 선택 드롭다운
        available_projects = st.session_state.oma_controller.get_available_projects()
        current_project = env_status['application_name']
        
        if available_projects:
            # 현재 프로젝트가 목록에 있는지 확인
            default_index = 0
            if current_project and current_project in available_projects:
                default_index = available_projects.index(current_project)
            
            selected_project = st.selectbox(
                "📋 프로젝트 선택:",
                options=available_projects,
                index=default_index,
                help="oma.properties에서 사용 가능한 프로젝트 목록"
            )
            
            # 프로젝트가 변경되었을 때
            if selected_project != current_project:
                if st.button("🔄 프로젝트 적용", type="primary", use_container_width=True):
                    if st.session_state.oma_controller.set_project_environment(selected_project):
                        st.success(f"프로젝트 '{selected_project}'로 변경되었습니다!")
                        st.rerun()
                    else:
                        st.error("프로젝트 설정 변경에 실패했습니다.")
        else:
            st.warning("⚠️ oma.properties에서 프로젝트를 찾을 수 없습니다.")
        
        # 현재 환경 상태 표시
        if env_status['is_configured']:
            st.success(f"✅ 현재 프로젝트: **{env_status['application_name']}**")
        else:
            st.error("❌ 프로젝트가 선택되지 않았습니다")
        
        st.info(f"📁 OMA Base Dir: {env_status['oma_base_dir']}")
        st.info(f"⚙️ 설정 파일: {os.path.basename(env_status['config_file'])}")
        
        # 실행 상태 표시 (간단하게)
        st.markdown("### 🔄 실행 상태")
        
        # 죽은 프로세스 정리 및 현재 상태 확인
        st.session_state.oma_controller.cleanup_dead_processes()
        
        current_process = st.session_state.oma_controller.current_process
        running_tasks = st.session_state.task_manager.get_running_tasks()
        
        # 1. current_process 우선 확인 (동적으로 작업 정보 표시)
        if current_process and current_process.poll() is None:
            # Task 파일에서 실제 작업 정보 읽기
            task_info = get_current_task_info()
            if task_info:
                task_title = task_info.get('title', '작업')
                st.error(f"🔴 **{task_title} 실행 중**")
            else:
                st.error("🔴 **작업 실행 중**")
            
            # 진행 시간 계산
            if hasattr(st.session_state, 'app_analysis_start_time'):
                elapsed = time.time() - st.session_state.app_analysis_start_time
                st.caption(f"⏱️ 진행 시간: {int(elapsed//60)}분 {int(elapsed%60)}초")
            
            # 상세 정보 (Task 파일에서 읽기)
            with st.expander("📊 작업 상세 정보", expanded=False):
                st.text(f"PID: {current_process.pid}")
                if task_info:
                    st.text(f"작업 ID: {task_info.get('task_id', 'Unknown')}")
                    st.text(f"로그: {task_info.get('log_file', 'Unknown')}")
                else:
                    if st.session_state.oma_controller.current_task_id:
                        st.text(f"작업 ID: {st.session_state.oma_controller.current_task_id}")
                    st.text("로그: 정보 없음")
            
            # 실행 중일 때도 로그 보기 버튼 제공 (메인 화면 로그로 이동)
            if st.button("📋 로그 보기", key="view_logs_btn", use_container_width=True):
                st.session_state.selected_action = "view_running_logs"
                st.rerun()
                
        # 2. TaskManager 기반 작업 확인
        elif running_tasks:
            task = running_tasks[0]
            st.warning(f"🟡 **{task['title']} 실행 중**")
            
            # 상세 정보
            with st.expander("📊 작업 상세 정보", expanded=False):
                st.text(f"PID: {task['pid']}")
                st.text(f"작업 ID: {task['task_id']}")
                st.text(f"시작: {task['start_time'][:19]}")
            
            # 실행 중일 때도 로그 보기 버튼 제공 (메인 화면 로그로 이동)
            if st.button("📋 로그 보기", key="view_logs_tm_btn", use_container_width=True):
                st.session_state.selected_action = "view_running_logs"
                st.rerun()
        else:
            # 대기 중
            st.success("🟢 **대기 중**")
            st.caption("현재 실행 중인 작업이 없습니다")
            
            # 대기 중에도 로그 보기 가능 (최근 로그)
            if st.button("📋 로그 보기", key="view_recent_logs_btn", use_container_width=True):
                st.session_state.selected_action = "view_running_logs"
                st.rerun()
        
        st.markdown("---")
        
        # 프로세스 중단 버튼 (실행 중일 때만 표시)
        if (current_process and current_process.poll() is None) or running_tasks:
            if st.button("🛑 현재 작업 중단", type="secondary", use_container_width=True):
                if st.session_state.oma_controller.stop_current_process():
                    st.success("작업이 중단되었습니다.")
                    st.rerun()
                else:
                    st.info("실행 중인 작업이 없습니다.")
            
            # 자동 새로고침 제거
            # time.sleep(5)
            # st.rerun()
        
        st.markdown("---")
        
        # 세션 상태 초기화 (한 번만 실행)
        if 'session_initialized' not in st.session_state:
            if 'selected_action' not in st.session_state:
                st.session_state.selected_action = None
            if 'current_screen' not in st.session_state:
                st.session_state.current_screen = 'welcome'
            st.session_state.session_initialized = True
        
        # 예쁜 아코디언 스타일 메뉴
        st.header("📋 작업 메뉴")
        
        # 메뉴 트리 구조 정의
        menu_tree = {
            "📊 프로젝트 환경 정보": {},  # 서브 메뉴 없음 - 바로 실행
            "📊 애플리케이션 분석": {
                "🔍 애플리케이션 분석": "app_analysis",
                "📄 분석 보고서 작성": "app_reporting",
                "🗄️ PostgreSQL 메타데이터": "postgresql_meta"
            },
            "🔄 애플리케이션 변환": {
                "🧪 샘플 변환 실행": "sample_transform",
                "🚀 전체 변환 실행": "full_transform",
                "🔧 테스트 및 결과 수정": "test_fix",
                "🔗 XML Merge 실행": "merge_transform"
            },
            "🧪 SQL 테스트": {
                "📝 XML List 생성": "xml_list",
                "🧪 Unit Test 실행": "sql_unittest"
            },
            "📋 변환 보고서": {
                "📊 변환 보고서 생성": "transform_report",
                "☕ Java Source 변환": "java_transform"
            }
        }
        
        # 아코디언 스타일 메뉴 렌더링 (죽은 프로세스 자동 정리)
        is_running = st.session_state.oma_controller.is_any_task_running()
        
        for main_menu, sub_menus in menu_tree.items():
            # 프로젝트 환경 정보는 바로 실행
            if main_menu == "📊 프로젝트 환경 정보":
                if st.button(main_menu, key=f"direct_{main_menu}", use_container_width=True, type="primary", disabled=is_running):
                    st.session_state.selected_action = "project_env_info"
                    st.session_state.current_screen = "project_env_info"
                    st.rerun()
            else:
                # 다른 메뉴들은 기존 아코디언 방식
                with st.expander(main_menu, expanded=False):
                    for sub_menu, action_key in sub_menus.items():
                        if st.button(
                            sub_menu,
                            key=f"menu_{action_key}",
                            use_container_width=True,
                            type="secondary",
                            disabled=is_running,
                            help=f"{sub_menu} 작업을 실행합니다" if not is_running else "다른 작업이 실행 중입니다"
                        ):
                            st.session_state.selected_action = action_key
                            st.session_state.current_screen = action_key
                            st.rerun()
    
    # 메인 컨텐츠 영역 - 페이지 기반 렌더링
    # st.write(f"🔍 DEBUG: selected_action = {st.session_state.selected_action}")
    
    if st.session_state.selected_action:
        # st.write(f"🔍 DEBUG: 액션 실행 중 - {st.session_state.selected_action}")
        
        # 선택된 액션에 따라 해당 페이지만 렌더링
        render_action_page(st.session_state.selected_action)
        
        # st.write(f"🔍 DEBUG: 액션 완료 후 - {st.session_state.selected_action}")
        
        # 상태 초기화 로직 완전 제거 - 각 페이지에서 명시적으로 홈 버튼 사용
        # st.write("🔍 DEBUG: 상태 초기화 로직 제거됨 - 상태 유지")
        
    else:
        # st.write("🔍 DEBUG: 환영 페이지 렌더링")
        # 환영 페이지 렌더링
        render_welcome_page()

def render_action_page(action_key):
    """액션별 페이지 렌더링"""
    # 각 액션별로 완전히 독립된 페이지 구성
    if action_key == "project_env_info":
        render_project_env_page()
    elif action_key == "view_running_logs":
        render_running_logs_page()
    elif action_key == "app_analysis":
        render_app_analysis_page()
    elif action_key == "app_reporting":
        render_app_reporting_page()
    elif action_key == "postgresql_meta":
        render_postgresql_meta_page()
    elif action_key == "sample_transform":
        render_sample_transform_page()
    elif action_key == "full_transform":
        render_full_transform_page()
    elif action_key == "test_fix":
        render_test_fix_page()
    elif action_key == "merge_transform":
        render_merge_transform_page()
    elif action_key == "xml_list":
        render_xml_list_page()
    elif action_key == "sql_unittest":
        render_sql_unittest_page()
    elif action_key == "transform_report":
        render_transform_report_page()
    elif action_key == "java_transform":
        render_java_transform_page()
    else:
        st.error(f"알 수 없는 액션: {action_key}")

def render_postgresql_meta_page():
    """PostgreSQL 메타데이터 생성 페이지"""
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="postgresql_meta_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 🗄️ PostgreSQL 메타데이터 생성")
    
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
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 실행", key="run_postgresql_meta", type="primary"):
            execute_postgresql_meta_script(expanded_script_path)
    with col2:
        st.caption("스크립트를 실행하여 PostgreSQL 메타데이터를 생성합니다")

def execute_postgresql_meta_script(script_path):
    """PostgreSQL 메타데이터 스크립트 실행 및 결과 표시"""
    st.markdown("### 📊 실행 결과")
    
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
        
        # 성공/실패 여부 확인
        if result.returncode == 0:
            st.success("✅ PostgreSQL 메타데이터 생성이 완료되었습니다!")
            
            # 표준 출력 표시
            if result.stdout.strip():
                st.markdown("#### 📄 실행 결과:")
                st.code(result.stdout, language=None, height=400)
            
            # 표준 에러가 있지만 성공한 경우 (경고 메시지 등)
            if result.stderr.strip():
                st.markdown("#### ⚠️ 경고/정보 메시지:")
                st.code(result.stderr, language=None, height=200)
                
        else:
            st.error(f"❌ 스크립트 실행 실패 (종료 코드: {result.returncode})")
            
            # 에러 출력 표시
            if result.stderr.strip():
                st.markdown("#### 🚨 에러 메시지:")
                st.code(result.stderr, language=None, height=300)
            
            # 표준 출력도 있으면 표시
            if result.stdout.strip():
                st.markdown("#### 📄 출력 내용:")
                st.code(result.stdout, language=None, height=200)
        
        # 진행률 바 제거
        progress_bar.empty()
        status_text.empty()
        
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

def render_project_env_page():
    """프로젝트 환경 정보 페이지"""
    st.markdown("## 📊 프로젝트 환경 정보")
    show_project_environment_info()

def render_running_logs_page():
    """실행 로그 보기 페이지"""
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="back_to_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📋 실행 중인 작업 로그")
    
    show_running_task_logs()

def get_current_task_info():
    """현재 실행 중인 작업의 Task 파일 정보 읽기"""
    try:
        if not os.path.exists("./oma_tasks"):
            return None
        
        task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
        if not task_files:
            return None
        
        # 가장 최근 task 파일 읽기
        latest_task_file = f"./oma_tasks/{sorted(task_files)[-1]}"
        
        import json
        with open(latest_task_file, 'r') as f:
            task_data = json.load(f)
        
        return task_data
        
    except Exception as e:
        return None


def check_and_cleanup_completed_tasks():
    """완료된 작업의 task 파일을 자동 삭제"""
    try:
        if not os.path.exists("./oma_tasks"):
            return
        
        task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
        
        for task_file in task_files:
            task_path = f"./oma_tasks/{task_file}"
            try:
                import json
                with open(task_path, 'r') as f:
                    task_data = json.load(f)
                
                pid = task_data.get('pid')
                if pid:
                    # 프로세스가 완료되었는지 확인
                    try:
                        # PID가 존재하는지 확인 (Unix 시스템)
                        os.kill(pid, 0)
                        # 프로세스가 아직 실행 중
                    except OSError:
                        # 프로세스가 완료됨 → task 파일 삭제
                        os.remove(task_path)
                        print(f"✅ 완료된 작업의 task 파일 삭제: {task_file}")
                        
            except Exception as e:
                # 손상된 task 파일 삭제
                os.remove(task_path)
                print(f"🗑️ 손상된 task 파일 삭제: {task_file}")
                
    except Exception as e:
        print(f"Task 파일 정리 중 오류: {e}")


def show_running_task_logs():
    """task 파일에서 로그 파일 찾아서 진짜 tail -f 스타일로 표시"""
    
    # task 파일 확인
    if not os.path.exists("./oma_tasks"):
        st.info("현재 실행 중인 작업이 없습니다.")
        return
    
    task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
    if not task_files:
        st.info("현재 실행 중인 작업이 없습니다.")
        
        # 최근 완료된 작업의 로그 표시 옵션
        st.markdown("### 📜 최근 로그 파일")
        
        # 로그 디렉토리에서 최근 로그 파일들 찾기
        log_dirs = [
            os.path.expandvars("$APP_LOGS_FOLDER/qlogs"),
            "./logs"
        ]
        
        recent_logs = []
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                for log_file in os.listdir(log_dir):
                    if log_file.endswith('.log'):
                        log_path = os.path.join(log_dir, log_file)
                        if os.path.exists(log_path):
                            mtime = os.path.getmtime(log_path)
                            recent_logs.append((log_file, log_path, mtime))
        
        # 최근 수정된 순으로 정렬
        recent_logs.sort(key=lambda x: x[2], reverse=True)
        
        if recent_logs:
            # 최근 3개 로그 파일 표시
            for log_name, log_path, mtime in recent_logs[:3]:
                mod_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                if st.button(f"📄 {log_name} ({mod_time})", key=f"recent_log_{log_name}"):
                    # 선택된 로그 파일 표시
                    st.markdown(f"### 📋 {log_name}")
                    show_static_log_file(log_path)
        else:
            st.info("최근 로그 파일이 없습니다.")
        
        return
    
    # 가장 최근 task 파일에서 로그 파일 경로 가져오기
    latest_task_file = f"./oma_tasks/{sorted(task_files)[-1]}"
    try:
        import json
        with open(latest_task_file, 'r') as f:
            task_data = json.load(f)
        
        log_file_path = task_data.get('log_file')
        st.success(f"📋 {task_data['title']} - {task_data['task_id']}")
        
        if not log_file_path or not os.path.exists(log_file_path):
            st.warning("로그 파일을 찾을 수 없습니다.")
            return
        
        st.caption(f"📄 {log_file_path}")
        
        # 컨트롤 버튼
        col1, col2 = st.columns([1, 3])
        with col1:
            auto_refresh = st.checkbox("🔴 실시간 모드", value=True, key="tail_f_mode")
        with col2:
            if not auto_refresh:
                if st.button("🔄 수동 새로고침", key="manual_refresh"):
                    st.rerun()
        
        # 세션 상태에 마지막 읽은 위치 저장
        if 'last_log_size' not in st.session_state:
            st.session_state.last_log_size = 0
        if 'log_content' not in st.session_state:
            st.session_state.log_content = ""
        
        # 현재 파일 크기 확인
        current_size = os.path.getsize(log_file_path)
        
        if current_size > st.session_state.last_log_size:
            # 새로운 내용이 있으면 추가된 부분만 읽기
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(st.session_state.last_log_size)
                new_content = f.read()
                
                # ANSI 색상 코드 및 이스케이프 시퀀스 제거
                import re
                # ANSI 색상 코드 제거
                new_content = re.sub(r'\x1b\[[0-9;]*m', '', new_content)
                # 커서 제어 시퀀스 제거 ([?25l, [?25h 등)
                new_content = re.sub(r'\x1b\[\?[0-9]+[lh]', '', new_content)
                # 기타 ANSI 이스케이프 시퀀스 제거
                new_content = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', new_content)
                
                # 기존 로그에 새 내용 추가
                st.session_state.log_content += new_content
                
                # 너무 길어지면 앞부분 잘라내기 (최근 5000줄 정도만 유지)
                lines = st.session_state.log_content.split('\n')
                if len(lines) > 5000:
                    st.session_state.log_content = '\n'.join(lines[-5000:])
                
                st.session_state.last_log_size = current_size
        
        # 실시간 모드 상태 표시
        if auto_refresh:
            st.caption("🔴 실시간 업데이트 중... (2초마다 자동 새로고침)")
        
        # 전체 로그 내용 표시 (높이 제한 + 자동 스크롤)
        if st.session_state.log_content:
            # 로그 내용을 역순으로 표시하여 최신 로그가 아래에 오도록 함
            lines = st.session_state.log_content.split('\n')
            
            # 실시간 모드일 때는 최신 로그를 강조하기 위해 마지막 몇 줄을 별도 표시
            if auto_refresh and len(lines) > 80:
                # 이전 로그 (접을 수 있는 형태)
                with st.expander("📜 이전 로그 보기", expanded=False):
                    old_logs = '\n'.join(lines[:-80])
                    st.code(old_logs, language=None, height=600)
                
                # 최신 로그 (항상 표시)
                st.markdown("### 📄 최신 로그")
                recent_logs = '\n'.join(lines[-80:])
                st.code(recent_logs, language=None, height=600)
            else:
                # 전체 로그 표시
                st.code(st.session_state.log_content, language=None, height=1000)
        else:
            st.info("로그 내용이 없습니다.")
        
        # 실시간 모드일 때 자동 스크롤을 위한 JavaScript 추가
        if auto_refresh:
            st.markdown("""
            <script>
            // 페이지 로드 후 맨 아래로 스크롤
            setTimeout(function() {
                window.scrollTo(0, document.body.scrollHeight);
            }, 100);
            </script>
            """, unsafe_allow_html=True)
        
        # 실시간 모드일 때만 자동 새로고침
        if auto_refresh:
            # 작업 완료 확인 및 task 파일 정리
            check_and_cleanup_completed_tasks()
            
            # 백그라운드 프로세스 완료 확인
            current_process = st.session_state.oma_controller.current_process
            running_tasks = st.session_state.task_manager.get_running_tasks()
            
            # 프로세스가 완료되었으면 홈으로 돌아가서 사이드바 새로고침
            if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
                st.success("✅ 작업이 완료되었습니다!")
                st.info("🏠 홈 화면으로 돌아갑니다...")
                time.sleep(1)
                st.session_state.selected_action = None  # 홈으로
                st.rerun()
            
            time.sleep(2)
            st.session_state.selected_action = "view_running_logs"  # 상태 유지
            st.rerun()
            
    except Exception as e:
        st.error(f"Task 파일 읽기 오류: {e}")
        st.info("현재 실행 중인 작업이 없습니다.")

def render_command_page(command, title, log_file_path=None):
    """명령어 실행 페이지"""
    st.markdown(f"## 🔄 {title}")
    execute_command_with_logs(command, title, log_file_path)

def render_app_reporting_page():
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
    
    # 실행 중인 작업 확인
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 분석 보고서 작성이 이미 실행 중입니다.")
        else:
            st.error("❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.")
            return
    else:
        # 즉시 백그라운드 실행 (로그 파일 경로는 참조용으로만 전달)
        execute_app_reporting_background(command, expanded_log_path)
    
    # 상단에 명령어 표시
    st.info(f"**실행 명령어:** `{command}`")
    st.caption(f"📄 로그 파일: {expanded_log_path}")
    
    # 작업 중단 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🛑 작업 중단", key="stop_app_reporting", type="secondary"):
            if st.session_state.oma_controller.stop_current_process():
                st.success("✅ 작업이 중단되었습니다.")
            else:
                st.info("실행 중인 작업이 없습니다.")
    
    # 간단한 상태 표시
    st.markdown("### 📊 작업 상태")
    
    # 로그 파일 생성 확인
    if os.path.exists(expanded_log_path):
        file_size = os.path.getsize(expanded_log_path)
        st.success(f"✅ 로그 파일이 생성되었습니다 ({file_size:,} bytes)")
        
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
    else:
        st.info("⏳ 로그 파일 생성 대기 중...")
        
        # 자동으로 한 번만 새로고침 (파일 생성 확인용)
        if st.button("🔄 상태 확인", key="check_app_reporting"):
            st.rerun()


def execute_app_reporting_background(command, log_file_path):
    """분석 보고서 작성을 백그라운드에서 실행 (스크립트가 자체적으로 로그 생성)"""
    try:
        # Task 정보 생성
        import time
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
        import json
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
            cwd=bin_dir  # $OMA_BASE_DIR/bin에서 실행
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


def render_app_analysis_page():
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="app_analysis_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 🔍 애플리케이션 분석")
    
    # 명령어 정보
    command = 'q chat --trust-all-tools --no-interactive < "$APP_TOOLS_FOLDER/appAnalysis.md"'
    log_file_path = "$APP_LOGS_FOLDER/qlogs/appAnalysis.log"
    expanded_log_path = os.path.expandvars(log_file_path)
    
    # 실행 중인 작업 확인
    if st.session_state.oma_controller.is_any_task_running():
        current_process = st.session_state.oma_controller.current_process
        if current_process and current_process.poll() is None:
            st.warning("🔄 애플리케이션 분석이 이미 실행 중입니다.")
        else:
            st.error("❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.")
            return
    else:
        # 즉시 백그라운드 실행
        execute_app_analysis_background(command, expanded_log_path)
    
    # 상단에 명령어 표시
    st.info(f"**실행 명령어:** `{command}`")
    st.caption(f"📄 로그 파일: {expanded_log_path}")
    
    # 작업 중단 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🛑 작업 중단", key="stop_app_analysis", type="secondary"):
            if st.session_state.oma_controller.stop_current_process():
                st.success("✅ 작업이 중단되었습니다.")
            else:
                st.info("실행 중인 작업이 없습니다.")
    
    # 간단한 상태 표시
    st.markdown("### 📊 작업 상태")
    
    # 로그 파일 생성 확인
    if os.path.exists(expanded_log_path):
        file_size = os.path.getsize(expanded_log_path)
        st.success(f"✅ 로그 파일이 생성되었습니다 ({file_size:,} bytes)")
        
        # 로그 보기 버튼 추가
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📋 로그 보기", key="view_logs_from_analysis", use_container_width=True):
                # st.write("🔍 DEBUG: 애플리케이션 분석에서 로그 보기 클릭!")
                # st.write(f"🔍 DEBUG: 클릭 전 selected_action = {st.session_state.selected_action}")
                st.session_state.selected_action = "view_running_logs"
                # st.write(f"🔍 DEBUG: 클릭 후 selected_action = {st.session_state.selected_action}")
                # st.write("🔍 DEBUG: st.rerun() 호출 직전")
                st.rerun()
        with col2:
            # 수동 새로고침 버튼
            if st.button("🔄 상태 새로고침", key="refresh_status"):
                st.rerun()
    else:
        st.info("⏳ 로그 파일 생성 대기 중...")
        
        # 자동으로 한 번만 새로고침 (파일 생성 확인용)
        if st.button("🔄 상태 확인", key="check_status"):
            st.rerun()

def execute_app_analysis_background(command, log_file_path):
    """애플리케이션 분석을 백그라운드에서 실행"""
    try:
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(log_file_path)
        os.makedirs(log_dir, exist_ok=True)
        
        # 로그 파일 초기화
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"=== 애플리케이션 분석 시작 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
        
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
                st.success(f"✅ 백그라운드 실행 시작 (PID: {actual_pid})")
            else:
                actual_pid = process.pid
                st.warning(f"⚠️ PID 감지 실패, 기본 PID 사용: {actual_pid}")
        except Exception as e:
            actual_pid = process.pid
            st.warning(f"⚠️ PID 감지 오류: {e}")
        
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
        task_info = st.session_state.task_manager.create_task(
            task_id, "애플리케이션 분석", command, actual_pid, log_file_path
        )
        
        st.session_state.oma_controller.current_task_id = task_id
        
    except Exception as e:
        st.error(f"❌ 실행 오류: {e}")

def monitor_app_analysis_process(log_container, log_file_path):
    """애플리케이션 분석 프로세스 모니터링 (3초마다 체크)"""
    
    # 프로세스 상태 확인
    current_process = st.session_state.oma_controller.current_process
    
    if current_process:
        process_status = current_process.poll()
        
        if process_status is None:
            # 실행 중
            status_text = "🔴 **실행 중**"
            if hasattr(st.session_state, 'app_analysis_start_time'):
                elapsed = time.time() - st.session_state.app_analysis_start_time
                status_text += f" (진행 시간: {int(elapsed//60)}분 {int(elapsed%60)}초)"
        else:
            # 완료됨
            status_text = "🟢 **완료됨**"
            # 프로세스 정리
            st.session_state.oma_controller.cleanup_dead_processes()
    else:
        status_text = "⚪ **대기 중**"
    
    # 상태 표시
    st.caption(status_text)
    
    # 로그 표시
    show_realtime_tail_log(log_container, log_file_path)
    
    # 자동 새로고침 - 작업 상태 실시간 업데이트 (로그 보기가 아닐 때만)
    if (current_process and current_process.poll() is None and 
        st.session_state.get('selected_action') != "view_running_logs"):
        # Task 파일 정리도 함께 수행
        check_and_cleanup_completed_tasks()
        time.sleep(3)
        st.rerun()

def show_realtime_tail_log(log_container, log_file_path, lines=50):
    """실시간 tail -f 로그 표시"""
    try:
        if os.path.exists(log_file_path):
            # 진짜 tail -f 실행
            process = subprocess.Popen(
                f"tail -f -n {lines} '{log_file_path}'",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 실시간 로그 수집 (3초간)
            log_lines = []
            start_time = time.time()
            
            while time.time() - start_time < 3:  # 3초간 수집
                line = process.stdout.readline()
                if line:
                    log_lines.append(line.rstrip())
                    
                    # 최근 100줄만 유지
                    if len(log_lines) > 100:
                        log_lines = log_lines[-100:]
                else:
                    # 새로운 로그가 없으면 잠시 대기
                    time.sleep(0.1)
            
            # 프로세스 종료
            process.terminate()
            
            # 수집된 로그 표시
            if log_lines:
                log_text = "\n".join(log_lines)
                colored_log_html = convert_ansi_to_html(log_text)
                
                with log_container.container():
                    st.markdown(f"""
                    <div class="log-container">
{colored_log_html}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # 로그가 없으면 정적 tail로 폴백
                cmd = f"tail -n {lines} '{log_file_path}'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
                
                if result.stdout:
                    log_text = result.stdout
                    colored_log_html = convert_ansi_to_html(log_text)
                    
                    with log_container.container():
                        st.markdown(f"""
                        <div class="log-container">
{colored_log_html}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    with log_container.container():
                        st.info("로그 내용이 없습니다.")
        else:
            with log_container.container():
                st.warning("로그 파일이 아직 생성되지 않았습니다.")
                
    except Exception as e:
        with log_container.container():
            st.error(f"❌ 로그 표시 오류: {e}")
        
        # 오류 시 정적 모드로 폴백
        try:
            if os.path.exists(log_file_path):
                cmd = f"tail -n {lines} '{log_file_path}'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
                if result.stdout:
                    log_text = result.stdout
                    colored_log_html = convert_ansi_to_html(log_text)
                    with log_container.container():
                        st.markdown(f"""
                        <div class="log-container">
{colored_log_html}
                        </div>
                        """, unsafe_allow_html=True)
        except:
            pass
    """프로젝트 환경 정보 페이지"""
    st.markdown("## 📊 프로젝트 환경 정보")
    show_project_environment_info()

def execute_command_with_logs(command, title, log_file_path=None):
    """명령어를 실행하고 실시간 로그를 표시 (특정 로그 파일 모니터링 지원)"""
    
    # 🔍 작업 시작 전 필수 체크: 실행 중인 작업 확인 및 정리
    if st.session_state.oma_controller.is_any_task_running():
        st.error("❌ 다른 작업이 실행 중입니다. 기존 작업을 완료하거나 중단한 후 다시 시도하세요.")
        
        # 현재 실행 중인 작업 정보 표시
        current_process = st.session_state.oma_controller.current_process
        running_tasks = st.session_state.task_manager.get_running_tasks()
        
        if current_process and current_process.poll() is None:
            st.warning(f"🔄 애플리케이션 분석이 실행 중입니다 (PID: {current_process.pid})")
        elif running_tasks:
            task = running_tasks[0]
            st.warning(f"🔄 {task['title']}이 실행 중입니다 (PID: {task['pid']})")
        
        st.info("💡 사이드바의 '🛑 현재 작업 중단' 버튼을 사용하여 기존 작업을 중단할 수 있습니다.")
        return
    
    # 상단에 실행 정보와 중단 버튼 배치
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"**{title}:** `{command}`")
        if log_file_path:
            # 환경 변수 치환
            expanded_log_path = os.path.expandvars(log_file_path)
            st.caption(f"📄 로그 파일: {expanded_log_path}")
    
    with col2:
        if st.button("🛑 작업 중단", key=f"stop_{hash(command)}", type="secondary"):
            if st.session_state.oma_controller.stop_current_process():
                st.warning("⚠️ 작업이 중단되었습니다.")
                st.stop()
            else:
                st.info("실행 중인 작업이 없습니다.")
    
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
        st.success(f"✅ {title} 작업이 완료되었습니다!")
        
        # 환경 변수 자동 저장 (환경 설정 관련 작업 후)
        if 'setEnv' in command or 'checkEnv' in command:
            st.session_state.oma_controller.update_environment_vars()
        
    except Exception as e:
        st.error(f"❌ 작업 실행 중 오류가 발생했습니다: {str(e)}")

def execute_with_specific_log_file(command, title, log_file_path, log_container):
    """특정 로그 파일을 사용하는 명령어를 백그라운드에서 실행 (로그 모니터링 분리)"""
    # 환경 변수 치환
    expanded_log_path = os.path.expandvars(log_file_path)
    
    # 로그 디렉토리 생성
    log_dir = os.path.dirname(expanded_log_path)
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 파일 초기화 (기존 내용 삭제)
    with open(expanded_log_path, 'w', encoding='utf-8') as f:
        f.write(f"=== {title} 시작 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
    
    try:
        # 백그라운드에서 완전히 독립적으로 명령어 실행
        cwd = os.path.join(st.session_state.oma_controller.oma_base_dir, 'bin')
        
        # nohup을 사용하여 완전히 독립적인 프로세스로 실행
        full_command = f"cd '{cwd}' && nohup {command} >> '{expanded_log_path}' 2>&1 &"
        
        st.info(f"🚀 백그라운드에서 실행 중: `{command}`")
        st.caption(f"📄 로그 파일: {expanded_log_path}")
        
        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # 프로세스 그룹 생성
        )
        
        # 잠시 대기하여 프로세스가 시작되도록 함
        time.sleep(2)
        
        # 실제 백그라운드 프로세스 PID 찾기
        try:
            # pgrep으로 실제 q chat 프로세스 찾기
            find_cmd = "pgrep -f 'q chat.*appAnalysis'"
            result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                actual_pid = int(result.stdout.strip().split('\n')[0])
                st.success(f"✅ 백그라운드 프로세스 시작됨 (PID: {actual_pid})")
            else:
                actual_pid = process.pid
                st.warning(f"⚠️ 프로세스 PID 감지 실패, 기본 PID 사용: {actual_pid}")
        except Exception as e:
            actual_pid = process.pid
            st.warning(f"⚠️ PID 감지 오류: {e}, 기본 PID 사용: {actual_pid}")
        
        # 가짜 프로세스 객체 생성 (실제 백그라운드 프로세스 추적용)
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
        
        # 시작 시간 기록 (진행 시간 계산용)
        st.session_state.app_analysis_start_time = time.time()
        
        # TaskManager에도 등록
        task_id = f"app_analysis_{int(time.time() * 1000)}"
        task_info = st.session_state.task_manager.create_task(
            task_id, title, command, actual_pid
        )
        task_info['log_file'] = expanded_log_path
        task_info['task_type'] = 'app_analysis'
        
        st.session_state.oma_controller.current_task_id = task_id
        
        # 간단한 안내 메시지
        st.markdown("---")
        st.info("🔄 **작업이 백그라운드에서 실행 중입니다**")
        st.markdown("""
        **로그 확인 방법:**
        1. 사이드바의 **"📋 실행 로그 보기"** 버튼 클릭
        2. 실시간으로 진행상황을 확인할 수 있습니다
        
        **작업 중단:**
        - 사이드바의 **"🛑 현재 작업 중단"** 버튼 사용
        """)
        
        # 로그 파일 생성 확인 (최대 5초 대기)
        for i in range(5):
            if os.path.exists(expanded_log_path) and os.path.getsize(expanded_log_path) > 50:
                st.success("📝 로그 파일이 생성되었습니다!")
                break
            time.sleep(1)
        else:
            st.warning("⚠️ 로그 파일 생성을 확인하지 못했습니다. 잠시 후 다시 확인해주세요.")
        
    except Exception as e:
        st.error(f"❌ 프로세스 시작 오류: {e}")
        # 오류 시 정리
        st.session_state.oma_controller.current_process = None
        st.session_state.oma_controller.current_task_id = None

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

def show_welcome_screen():
    """환영 화면 표시"""
    st.markdown("""
    <div class="main-header">
        <h1>🔄 OMA - Oracle Migration Assistant</h1>
        <p>Oracle to PostgreSQL Migration Tool - Web Interface</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### 📋 작업 순서 가이드
    
    1. **📊 프로젝트 환경 정보**
       - 현재 프로젝트의 환경 변수 및 설정 상태 확인
    
    2. **📊 애플리케이션 분석**
       - 애플리케이션 분석 → 분석 보고서 작성 → PostgreSQL 메타데이터 순서로 진행
       - Java 소스 코드와 SQL 매퍼 파일을 분석
    
    3. **🔄 애플리케이션 변환**
       - 샘플 변환 → 테스트 및 결과 수정 → 전체 변환 → XML Merge 순서로 진행
       - 샘플 변환으로 먼저 테스트 후 전체 변환 수행
    
    4. **🧪 SQL 테스트**
       - XML List 생성 → Unit Test 실행 순서로 진행
       - 변환된 SQL의 정확성 검증
    
    5. **📋 변환 보고서**
       - 변환 보고서 생성 → Java Source 변환 순서로 진행
       - 최종 결과 보고서 작성
    
    ### 💡 사용 팁
    - 왼쪽 사이드바에서 메뉴를 클릭하여 세부 작업을 선택하세요
    - 각 작업의 로그는 실시간으로 화면에 표시됩니다
    - 환경 변수는 자동으로 저장되어 앱 재시작 시에도 유지됩니다
    """)
    
    # 현재 환경 상태 요약
    env_status = st.session_state.oma_controller.check_environment()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if env_status['is_configured']:
            st.success(f"✅ **프로젝트 설정 완료**\n\n프로젝트: {env_status['application_name']}")
        else:
            st.error("❌ **환경 설정 필요**\n\n환경 설정을 먼저 실행하세요")
    
    with col2:
        st.info(f"📁 **OMA 디렉토리**\n\n{env_status['oma_base_dir']}")
    
    with col3:
        config_exists = os.path.exists(env_status['config_file'])
        if config_exists:
            st.success("💾 **설정 파일 존재**\n\n환경 변수 저장됨")
        else:
            st.warning("⚠️ **설정 파일 없음**\n\n환경 변수를 저장하세요")

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

def show_tail_log_with_auto_refresh(log_file_path, follow=False, lines=50):
    """tail 로그를 표시하는 간단한 함수"""
    
    try:
        if not os.path.exists(log_file_path):
            st.warning(f"로그 파일이 존재하지 않습니다: {log_file_path}")
            return
        
        # tail 명령어로 로그 읽기
        cmd = f"tail -n {lines} '{log_file_path}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout:
            # ANSI 색상 코드를 HTML로 변환
            log_text = result.stdout
            colored_log_html = convert_ansi_to_html(log_text)
            
            # 로그 표시
            st.markdown(f"""
            <div style="background-color: #1e1e1e; color: #ffffff; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: auto;">
{colored_log_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("로그 내용이 없습니다.")
        
        # 컨트롤 버튼들
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔄 새로고침", key=f"refresh_{hash(log_file_path)}"):
                st.rerun()
        
        with col2:
            if follow:
                auto_refresh = st.checkbox("자동 새로고침", key=f"auto_{hash(log_file_path)}", value=True)
        
        with col3:
            st.caption(f"📄 {log_file_path}")
        
        # 자동 새로고침 (3초마다)
        if follow and auto_refresh:
            time.sleep(3)
            st.rerun()
            
    except Exception as e:
        st.error(f"로그 표시 오류: {e}")
        st.caption(f"파일: {log_file_path}")
        st.caption(f"존재 여부: {os.path.exists(log_file_path)}")

def show_real_tail_f(log_container, log_file_path, lines=100):
    """진짜 tail -f 실시간 스트리밍"""
    try:
        # tail -f 프로세스 시작
        process = subprocess.Popen(
            f"tail -f -n {lines} '{log_file_path}'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 실시간 로그 수집 (5초간)
        log_lines = []
        start_time = time.time()
        
        while time.time() - start_time < 5:  # 5초간 수집
            # 논블로킹 읽기
            line = process.stdout.readline()
            if line:
                log_lines.append(line.rstrip())
                
                # 최근 100줄만 유지
                if len(log_lines) > 100:
                    log_lines = log_lines[-100:]
                
                # 실시간 로그 표시
                log_text = "\n".join(log_lines)
                colored_log_html = convert_ansi_to_html(log_text)
                
                with log_container.container():
                    st.markdown(f"""
                    <div class="log-container">
{colored_log_html}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # 새로운 로그가 없으면 잠시 대기
                time.sleep(0.1)
        
        # 프로세스 종료
        process.terminate()
        
        # 5초 후 자동 새로고침 (실시간 스트리밍 계속)
        time.sleep(1)
        st.rerun()
        
    except Exception as e:
        with log_container.container():
            st.error(f"실시간 로그 스트리밍 오류: {e}")
        
        # 오류 시 정적 모드로 폴백
        try:
            cmd = f"tail -n {lines} '{log_file_path}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            if result.stdout:
                log_text = result.stdout
                colored_log_html = convert_ansi_to_html(log_text)
                with log_container.container():
                    st.markdown(f"""
                    <div class="log-container">
{colored_log_html}
                    </div>
                    """, unsafe_allow_html=True)
        except:
            pass

if __name__ == "__main__":
    main()
