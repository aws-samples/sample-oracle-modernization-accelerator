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

# 분리된 페이지 모듈들 import
from modules import (
    render_welcome_page,
    render_project_env_page,
    render_app_analysis_page,
    render_app_reporting_page,
    render_discovery_report_review_page,
    render_postgresql_meta_page,
    render_running_logs_page,
    render_mapper_validation_page,
    render_sample_transform_page,
    render_full_transform_page,
    render_merge_transform_page,
    render_transform_report_page,
    render_view_transform_report_page,
    render_java_transform_page,
    render_parameter_config_page,
    render_source_sqls_page
)
from modules.qlog_viewer import render_qlog_page

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
        background-color: #f8f9fa;
        color: #212529;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        max-height: 900px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 14px;
        line-height: 1.4;
        border: 1px solid #dee2e6;
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
    
    /* 아코디언 스타일 메뉴 - 라이트 테마 */
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
        background: #ffffff;
        border-radius: 0 0 8px 8px;
        padding: 8px;
        margin-bottom: 8px;
        border-left: 3px solid #667eea;
        border: 1px solid #e0e0e0;
    }
    
    .sidebar .streamlit-expanderContent .stButton > button {
        background: white;
        color: #333;
        border: 1px solid #d0d0d0;
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
    
    /* 메인 컨텐츠 영역 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* 카드 스타일 */
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)
class TaskManager:
    """작업 상태를 파일 기반으로 관리하는 클래스"""
    
    def __init__(self):
        self.tasks_dir = os.path.join(os.getcwd(), "oma_tasks")  # 현재 디렉토리에 task 파일만
        self.logs_dir = self.tasks_dir  # logs_dir 속성 추가
        
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
                # 더 안전한 프로세스 종료 방식
                try:
                    # 먼저 SIGTERM으로 정상 종료 시도
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                    
                    # 2초 대기 후 프로세스가 종료되었는지 확인
                    time.sleep(2)
                    if self.current_process.poll() is None:
                        # 아직 실행 중이면 SIGKILL로 강제 종료
                        os.killpg(os.getpgid(self.current_process.pid), signal.SIGKILL)
                        
                except ProcessLookupError:
                    # 프로세스가 이미 종료된 경우
                    pass
                except OSError as e:
                    # 프로세스 그룹이 없는 경우 개별 프로세스 종료 시도
                    try:
                        self.current_process.terminate()
                        time.sleep(1)
                        if self.current_process.poll() is None:
                            self.current_process.kill()
                    except:
                        pass
                
                # 로그 파일에 중단 메시지 추가
                if self.current_task_id:
                    # 현재 작업에 따라 적절한 로그 파일 선택
                    log_files = [
                        os.path.expandvars("$APP_LOGS_FOLDER/qlogs/appAnalysis.log"),
                        os.path.expandvars("$APP_LOGS_FOLDER/qlogs/appReporting.log")
                    ]
                    
                    for log_file in log_files:
                        if os.path.exists(log_file):
                            try:
                                with open(log_file, 'a', encoding='utf-8') as f:
                                    f.write(f"\n=== 작업이 사용자에 의해 중단되었습니다 (PID: {self.current_process.pid}) ===\n")
                            except:
                                pass
                    
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


# 전역 작업 관리자
if 'task_manager' not in st.session_state:
    st.session_state.task_manager = TaskManager()

# 전역 OMA 컨트롤러 인스턴스
if 'oma_controller' not in st.session_state:
    st.session_state.oma_controller = OMAController()

def main():
    # 앱 시작 시 저장된 설정 자동 로드 (한 번만 실행)
    if 'config_loaded' not in st.session_state:
        config, var_count = st.session_state.oma_controller.load_saved_config()
        if var_count > 0:
            project_name = os.environ.get('APPLICATION_NAME', 'Unknown')
            st.success(f"💾 저장된 환경 설정을 복원했습니다 ({var_count}개 변수) - 프로젝트: {project_name}")
        
        # 현재 환경변수로 config 파일 자동 업데이트
        st.session_state.oma_controller.save_config(dict(os.environ))
        
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
                    
                    # 샘플변환, 전체변환인 경우 qlog 보기 버튼 추가
                    task_title = task_info.get('title', '')
                    if '샘플 변환' in task_title or '전체 변환' in task_title:
                        if st.button("📊 qlog 보기", key="view_qlog_btn", use_container_width=True):
                            st.session_state.selected_action = "view_qlog"
                            st.rerun()
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
                
                # 샘플변환, 전체변환인 경우 qlog 보기 버튼 추가
                task_title = task.get('title', '')
                if '샘플 변환' in task_title or '전체 변환' in task_title:
                    if st.button("📊 qlog 보기", key="view_qlog_tm_btn", use_container_width=True):
                        st.session_state.selected_action = "view_qlog"
                        st.rerun()
            
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
                "📋 분석 보고서 리뷰": "discovery_report_review",
                "🗄️ PostgreSQL 메타데이터": "postgresql_meta"
            },
            "🔄 애플리케이션 변환": {
                "✅ 매퍼 파일 검증": "mapper_validation",
                "🧪 샘플 변환 실행": "sample_transform",
                "🚀 전체 변환 실행": "full_transform",
                "🔗 XML Merge 실행": "merge_transform"
            },
            "🧪 SQL 테스트": {
                "⚙️ Parameter 구성": "parameter_config",
                "⚖️ Compare SQL Test": "source_sqls"
            },
            "📋 변환 보고서": {
                "📊 변환 보고서 생성": "transform_report",
                "📄 변환 보고서 보기": "view_transform_report"
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
    # 선택된 액션이 있는 경우에만 해당 페이지 렌더링
    selected_action = st.session_state.get('selected_action')
    
    # 로그 뷰어는 완전히 독립적으로 처리
    if selected_action == "view_running_logs":
        # 로그 뷰어만 렌더링하고 즉시 종료
        render_running_logs_page()
        return  # 함수 완전 종료
    
    # qlog 뷰어도 독립적으로 처리
    if selected_action == "view_qlog":
        # qlog 뷰어만 렌더링하고 즉시 종료
        render_qlog_page()
        return  # 함수 완전 종료
    
    # 다른 액션들 처리
    if selected_action:
        render_action_page(selected_action)
        return  # 함수 완전 종료
    
    # 기본 환영 페이지
    render_welcome_page()


def render_action_page(action_key):
    """액션별 페이지 렌더링"""
    # 각 액션별로 완전히 독립된 페이지 구성
    if action_key == "project_env_info":
        render_project_env_page()
    elif action_key == "app_analysis":
        render_app_analysis_page()
    elif action_key == "app_reporting":
        render_app_reporting_page()
    elif action_key == "discovery_report_review":
        render_discovery_report_review_page()
    elif action_key == "postgresql_meta":
        render_postgresql_meta_page()
    elif action_key == "mapper_validation":
        render_mapper_validation_page()
    elif action_key == "sample_transform":
        render_sample_transform_page()
    elif action_key == "full_transform":
        render_full_transform_page()
    elif action_key == "merge_transform":
        render_merge_transform_page()
    elif action_key == "parameter_config":
        render_parameter_config_page()
    elif action_key == "source_sqls":
        render_source_sqls_page()
    elif action_key == "transform_report":
        render_transform_report_page()
    elif action_key == "view_transform_report":
        render_view_transform_report_page()
    elif action_key == "java_transform":
        render_java_transform_page()
    else:
        st.error(f"알 수 없는 액션: {action_key}")


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
        
        with open(latest_task_file, 'r') as f:
            task_data = json.load(f)
        
        return task_data
        
    except Exception as e:
        return None


if __name__ == "__main__":
    main()
