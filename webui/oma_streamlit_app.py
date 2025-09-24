#!/usr/bin/env python3
"""
OMA (Oracle Migration Assistant) Streamlit Web Application
Web interface for Oracle to PostgreSQL migration
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

# Import separated page modules
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

# Page configuration
st.set_page_config(
    page_title="OMA - Oracle Migration Assistant",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS styling
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
    
    /* Accordion style menu - Light theme */
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
    
    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Card style */
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
    """File-based task status management class"""
    
    def __init__(self):
        self.tasks_dir = os.path.join(os.getcwd(), "oma_tasks")  # Task files only in current directory
        self.logs_dir = self.tasks_dir  # Add logs_dir attribute
        
        # Create directory
        os.makedirs(self.tasks_dir, exist_ok=True)
        
        # Clean up terminated tasks at startup
        self.cleanup_finished_tasks()
    
    def create_task(self, task_id, title, command, pid, log_file=None):
        """Create new task"""
        task_info = {
            "task_id": task_id,
            "title": title,
            "command": command,
            "pid": pid,
            "start_time": datetime.datetime.now().isoformat(),
            "status": "running",
            "log_file": log_file or "no_log_file"  # Actual log file path or default
        }
        
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_info, f, indent=2, ensure_ascii=False)
        
        return task_info
    
    def get_running_tasks(self):
        """Return list of running tasks"""
        running_tasks = []
        
        if not os.path.exists(self.tasks_dir):
            return running_tasks
        
        for task_file in os.listdir(self.tasks_dir):
            if task_file.endswith('.json'):
                try:
                    with open(os.path.join(self.tasks_dir, task_file), 'r', encoding='utf-8') as f:
                        task_info = json.load(f)
                    
                    # Check if process is actually running
                    if self.is_process_running(task_info['pid']):
                        running_tasks.append(task_info)
                    else:
                        # Clean up terminated processes
                        self.finish_task(task_info['task_id'])
                        
                except Exception as e:
                    print(f"Task file read error: {e}")
        
        return running_tasks
    
    def get_task_info(self, task_id):
        """Return specific task information"""
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        if os.path.exists(task_file):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Task info read error: {e}")
        return None
    
    def get_task_logs(self, task_id, tail_lines=100):
        """Read task logs (recent N lines)"""
        task_info = self.get_task_info(task_id)
        if task_info and os.path.exists(task_info['log_file']):
            try:
                with open(task_info['log_file'], 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    return [line.rstrip() for line in lines[-tail_lines:]]
            except Exception as e:
                print(f"Log read error: {e}")
        return []
    
    def finish_task(self, task_id):
        """Complete task processing"""
        task_file = os.path.join(self.tasks_dir, f"{task_id}.json")
        if os.path.exists(task_file):
            try:
                # Delete task info file
                os.remove(task_file)
            except Exception as e:
                print(f"Task cleanup error: {e}")
    
    def kill_task(self, task_id):
        """Force terminate task"""
        task_info = self.get_task_info(task_id)
        if task_info:
            try:
                pid = task_info['pid']
                if self.is_process_running(pid):
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    # Add interruption message to log file
                    if os.path.exists(task_info['log_file']):
                        with open(task_info['log_file'], 'a', encoding='utf-8') as f:
                            f.write(f"\n=== Task interrupted by user ===\n")
                
                self.finish_task(task_id)
                return True
            except Exception as e:
                print(f"Task interruption error: {e}")
        return False
    
    def is_process_running(self, pid):
        """Check if process is running"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def get_all_tasks(self):
        """Return all task list (including completed tasks)"""
        all_tasks = []
        
        # Running tasks
        running_tasks = self.get_running_tasks()
        all_tasks.extend(running_tasks)
        
        # Find completed tasks in log directory
        if os.path.exists(self.logs_dir):
            for log_file in os.listdir(self.logs_dir):
                if log_file.endswith('.log'):
                    task_id = log_file[:-4]  # Remove .log
                    
                    # Only if not already running
                    if not any(task['task_id'] == task_id for task in running_tasks):
                        log_path = os.path.join(self.logs_dir, log_file)
                        try:
                            # Generate task info based on log file modification time
                            mtime = os.path.getmtime(log_path)
                            completed_task = {
                                "task_id": task_id,
                                "title": "Completed Task",
                                "command": "unknown",
                                "pid": 0,
                                "start_time": datetime.datetime.fromtimestamp(mtime).isoformat(),
                                "status": "completed",
                                "log_file": log_path
                            }
                            all_tasks.append(completed_task)
                        except Exception as e:
                            print(f"Completed task info generation error: {e}")
        
        # Sort by start time
        all_tasks.sort(key=lambda x: x['start_time'])
        return all_tasks
    
    def cleanup_finished_tasks(self):
        """Clean up terminated tasks"""
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
                    print(f"Cleanup error: {e}")

# Global task manager
if 'task_manager' not in st.session_state:
    st.session_state.task_manager = TaskManager()

class OMAController:
    def __init__(self):
        self.oma_base_dir = self.get_oma_base_dir()
        self.current_process = None
        self.current_task_id = None  # Current task ID
        self.log_queue = queue.Queue()
        self.config_file = os.path.join(os.getcwd(), ".oma_config.json")
        # Do not load in constructor (handled in main)
        
    def get_oma_base_dir(self):
        """Check and set OMA_BASE_DIR environment variable"""
        oma_dir = os.environ.get('OMA_BASE_DIR')
        if not oma_dir:
            # Use ~/workspace/oma as default
            oma_dir = os.path.expanduser("~/workspace/oma")
        return oma_dir
    
    def is_running(self):
        """Check if any task is currently running"""
        running_tasks = st.session_state.task_manager.get_running_tasks()
        return len(running_tasks) > 0
    
    def get_current_task(self):
        """Return current running task info"""
        running_tasks = st.session_state.task_manager.get_running_tasks()
        return running_tasks[0] if running_tasks else None
    
    def load_saved_config(self):
        """Load saved environment config and apply to system env vars"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # Restore saved environment variables to system
                    env_vars = config.get('env_vars', {})
                    if env_vars:
                        restored_count = 0
                        for key, value in env_vars.items():
                            # Use EC2 env var if available, otherwise use saved value
                            if key in os.environ:
                                # Update config with EC2 env var value
                                env_vars[key] = os.environ[key]
                            else:
                                # Set saved value as environment variable
                                os.environ[key] = value
                                restored_count += 1
                    
                    return config, restored_count  # Return actual number of restored variables
        except Exception as e:
            return {}, 0
        return {}, 0
    
    def save_config(self, env_vars=None):
        """Save environment config"""
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
            st.error(f"Error saving config file: {e}")
            return False
    
    def update_environment_vars(self):
        """Save current environment variables to file"""
        # All environment variables checked by checkEnv.sh
        important_vars = [
            # Core environment variables
            'APPLICATION_NAME', 'OMA_BASE_DIR', 'JAVA_SOURCE_FOLDER',
            'SOURCE_SQL_MAPPER_FOLDER', 'TARGET_SQL_MAPPER_FOLDER',
            'TRANSFORM_JNDI', 'TRANSFORM_RELATED_CLASS',
            'SOURCE_DBMS_TYPE', 'TARGET_DBMS_TYPE',
            
            # Folder related
            'DBMS_FOLDER', 'DBMS_LOGS_FOLDER', 'APPLICATION_FOLDER',
            'APP_TOOLS_FOLDER', 'APP_TRANSFORM_FOLDER', 'APP_LOGS_FOLDER',
            'TEST_FOLDER', 'TEST_LOGS_FOLDER',
            
            # Oracle connection info
            'ORACLE_ADM_USER', 'ORACLE_ADM_PASSWORD', 'ORACLE_HOST',
            'ORACLE_PORT', 'ORACLE_SID', 'ORACLE_SVC_USER',
            'ORACLE_SVC_PASSWORD', 'ORACLE_SVC_CONNECT_STRING',
            'ORACLE_SVC_USER_LIST', 'SERVICE_NAME', 'NLS_LANG',
            
            # PostgreSQL connection info
            'PG_SVC_PASSWORD', 'PGPORT', 'PGPASSWORD', 'PG_ADM_PASSWORD',
            'PG_ADM_USER', 'PG_SVC_USER', 'PGUSER', 'PGDATABASE', 'PGHOST',
            
            # System environment variables
            'JAVA_HOME', 'PATH', 'HOME', 'USER'
        ]
        
        env_vars = {}
        
        # Get current actual environment variable values
        for var in important_vars:
            if var in os.environ:
                env_vars[var] = os.environ[var]
        
        # Debug: Check Oracle related variables
        oracle_vars = ['ORACLE_HOST', 'ORACLE_SID', 'ORACLE_PORT']
        print(f"DEBUG: Current Oracle environment variables:")
        for var in oracle_vars:
            print(f"  {var} = {os.environ.get(var, 'NOT_SET')}")
        
        return self.save_config(env_vars)
    
    def get_available_projects(self):
        """Extract available project list from oma.properties"""
        properties_file = os.path.join(self.oma_base_dir, "config", "oma.properties")
        projects = []
        
        try:
            if os.path.exists(properties_file):
                with open(properties_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Find [project_name] format sections (excluding COMMON)
                        if line.startswith('[') and line.endswith(']') and line != '[COMMON]':
                            project_name = line[1:-1]  # Remove brackets
                            projects.append(project_name)
        except Exception as e:
            st.error(f"oma.properties file read error: {e}")
        
        return projects
    
    def get_project_config(self, project_name):
        """Extract specific project config info (COMMON + project config merge)"""
        properties_file = os.path.join(self.oma_base_dir, "config", "oma.properties")
        config = {}
        
        try:
            if os.path.exists(properties_file):
                with open(properties_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                current_section = None
                raw_config = {}
                
                # Step 1: Collect original values
                for line in lines:
                    line = line.strip()
                    
                    # Check section header
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]  # Remove brackets
                        continue
                    
                    # Parse config values (only from COMMON or selected project section)
                    if (current_section == 'COMMON' or current_section == project_name) and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        raw_config[key] = value
                
                # APPLICATION_NAME must be included
                raw_config['APPLICATION_NAME'] = project_name
                
                # Step 2: Environment variable substitution
                config = raw_config.copy()
                
                # Repeat up to 5 times to substitute all variables
                for iteration in range(5):
                    changed = False
                    for key, value in config.items():
                        if '${' in value:
                            original_value = value
                            
                            # Substitute basic variables
                            value = value.replace('${APPLICATION_NAME}', project_name)
                            value = value.replace('${OMA_BASE_DIR}', self.oma_base_dir)
                            
                            # Substitute with other values in config
                            for config_key, config_value in config.items():
                                if config_key != key and '${' not in config_value:
                                    value = value.replace('${' + config_key + '}', config_value)
                            
                            # Substitute with system environment variables
                            for env_key, env_value in os.environ.items():
                                value = value.replace('${' + env_key + '}', env_value)
                            
                            if value != original_value:
                                config[key] = value
                                changed = True
                    
                    # Exit if no more changes
                    if not changed:
                        break
                
        except Exception as e:
            st.error(f"Project config read error: {e}")
        
        return config
    
    def set_project_environment(self, project_name):
        """Set environment variables for selected project (COMMON + all project variables)"""
        if not project_name:
            return False
        
        # Get project config (COMMON + project merge)
        project_config = self.get_project_config(project_name)
        
        if not project_config:
            st.error(f"Cannot find project config.")
            return False
        
        # Set all configs as environment variables
        for key, value in project_config.items():
            env_key = key.upper()
            os.environ[env_key] = value
            
        # Debug: Display number of configured variables
        st.info(f"📊 Total environment variables configured.")
        
        # Save to config file (including all important env vars)
        save_result = self.update_environment_vars()
        
        if save_result:
            st.success(f"💾 Project config saved to JSON file.")
        else:
            st.error("❌ Failed to save JSON file.")
            
        return save_result
    
    def check_environment(self):
        """Check environment variables"""
        app_name = os.environ.get('APPLICATION_NAME')
        return {
            'oma_base_dir': self.oma_base_dir,
            'application_name': app_name,
            'is_configured': bool(app_name),
            'config_file': self.config_file
        }
    
    def run_command_with_logs(self, command, title="Task", cwd=None):
        """Execute command and return real-time logs (file-based hybrid method)"""
        # Check if task is already running
        if self.is_running():
            yield "❌ Another task is running. Please try again later."
            return
        
        if cwd is None:
            cwd = os.path.join(self.oma_base_dir, 'bin')
        
        # Generate unique task ID
        task_id = f"task_{int(time.time() * 1000)}"
        log_file = os.path.join(st.session_state.task_manager.logs_dir, f"{task_id}.log")
        
        try:
            # Start process (direct pipe without redirection)
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=cwd,
                preexec_fn=os.setsid  # Create process group
            )
            
            self.current_process = process
            self.current_task_id = task_id
            
            # Register task with TaskManager
            task_info = st.session_state.task_manager.create_task(
                task_id, title, command, process.pid
            )
            
            # Real-time log collection and file saving
            yield from self.collect_logs_and_save(process, log_file, task_id)
            
            # Wait for process completion
            process.wait()
            
            # Add completion log
            completion_msg = f"=== Task completed (exit code: {process.returncode}) ==="
            st.session_state.task_manager.append_log(task_id, completion_msg)
            yield completion_msg
            
        except Exception as e:
            error_msg = f"❌ Error occurred: {str(e)}"
            if task_id:
                st.session_state.task_manager.append_log(task_id, error_msg)
            yield error_msg
        finally:
            # Handle task completion
            if task_id:
                st.session_state.task_manager.finish_task(task_id)
            self.current_process = None
            self.current_task_id = None
    
    def collect_logs_and_save(self, process, log_file, task_id):
        """Collect process output in real-time and save to file"""
        try:
            # Open log file
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Task started: {task_id} ===\n")
                f.flush()
                
                # Real-time log collection
                while True:
                    line = process.stdout.readline()
                    if not line:
                        # Check if process terminated
                        if process.poll() is not None:
                            break
                        continue
                    
                    # Remove newline characters
                    clean_line = line.rstrip('\n\r')
                    if clean_line:  # Only if not empty line
                        # Save to file
                        f.write(clean_line + '\n')
                        f.flush()  # Write to file immediately
                        
                        # Display on screen
                        yield clean_line
                
                # Add completion message
                f.write(f"=== Task completed: {task_id} ===\n")
                f.flush()
                
        except Exception as e:
            error_msg = f"Log collection error: {e}"
            yield error_msg
            # Save error to file too
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(error_msg + '\n')
            except:
                pass
    
    def cleanup_dead_processes(self):
        """Clean up dead processes and return actual execution status"""
        cleaned = False
        
        # 1. Check and cleanup current_process
        if self.current_process:
            if self.current_process.poll() is not None:
                # Process terminated
                if self.current_task_id:
                    st.session_state.task_manager.finish_task(self.current_task_id)
                self.current_process = None
                self.current_task_id = None
                cleaned = True
        
        # 2. Cleanup dead tasks in TaskManager
        running_tasks = st.session_state.task_manager.get_running_tasks()
        for task in running_tasks:
            if not st.session_state.task_manager.is_process_running(task['pid']):
                st.session_state.task_manager.finish_task(task['task_id'])
                cleaned = True
        
        return cleaned
    
    def is_any_task_running(self):
        """Check if any task is running (auto cleanup dead processes)"""
        # First cleanup dead processes
        self.cleanup_dead_processes()
        
        # Check actually running tasks
        has_current_process = self.current_process and self.current_process.poll() is None
        has_running_tasks = len(st.session_state.task_manager.get_running_tasks()) > 0
        
        return has_current_process or has_running_tasks
    
    def stop_current_process(self):
        """Stop currently running process (current_process priority)"""
        # 1. Check current_process first (application analysis)
        if self.current_process and self.current_process.poll() is None:
            try:
                # Safer process termination method
                try:
                    # First try normal termination with SIGTERM
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                    
                    # Wait 2 seconds then check if process terminated
                    time.sleep(2)
                    if self.current_process.poll() is None:
                        # If still running, force terminate with SIGKILL
                        os.killpg(os.getpgid(self.current_process.pid), signal.SIGKILL)
                        
                except ProcessLookupError:
                    # If process already terminated
                    pass
                except OSError as e:
                    # If no process group, try individual process termination
                    try:
                        self.current_process.terminate()
                        time.sleep(1)
                        if self.current_process.poll() is None:
                            self.current_process.kill()
                    except:
                        pass
                
                # Add interruption message to log file
                if self.current_task_id:
                    # Select appropriate log file based on current task
                    log_files = [
                        os.path.expandvars("$APP_LOGS_FOLDER/qlogs/appAnalysis.log"),
                        os.path.expandvars("$APP_LOGS_FOLDER/qlogs/appReporting.log")
                    ]
                    
                    for log_file in log_files:
                        if os.path.exists(log_file):
                            try:
                                with open(log_file, 'a', encoding='utf-8') as f:
                                    f.write(f"\n=== Task interrupted by user (PID: {self.current_process.pid}) ===\n")
                            except:
                                pass
                    
                    # Cleanup in TaskManager too
                    st.session_state.task_manager.finish_task(self.current_task_id)
                
                self.current_process = None
                self.current_task_id = None
                return True
            except Exception as e:
                print(f"Application analysis process interruption error: {e}")
        
        # 2. TaskManager based task interruption
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
                print(f"TaskManager task interruption error: {e}")
        
        return False


# Global task manager
if 'task_manager' not in st.session_state:
    st.session_state.task_manager = TaskManager()

# Global OMA controller instance
if 'oma_controller' not in st.session_state:
    st.session_state.oma_controller = OMAController()

def main():
    # Auto load saved config at app start (once only)
    if 'config_loaded' not in st.session_state:
        config, var_count = st.session_state.oma_controller.load_saved_config()
        if var_count > 0:
            project_name = os.environ.get('APPLICATION_NAME', 'Unknown')
            st.success(f"💾 Restored saved environment config ({var_count} variables) - Project: {project_name}")
        
        # Immediately update config file with current env vars (env vars priority)
        update_result = st.session_state.oma_controller.update_environment_vars()
        if update_result:
            st.info("🔄 Updated config file with current environment variables.")
        
        st.session_state.config_loaded = True
    
    # Check environment status
    env_status = st.session_state.oma_controller.check_environment()
    
    # Sidebar - Menu and environment info
    with st.sidebar:
        st.header("🔧 Environment Info")
        
        # Project selection dropdown
        available_projects = st.session_state.oma_controller.get_available_projects()
        current_project = env_status['application_name']
        
        if available_projects:
            # Check if current project is in list
            default_index = 0
            if current_project and current_project in available_projects:
                default_index = available_projects.index(current_project)
            
            selected_project = st.selectbox(
                "📋 Select Project:",
                options=available_projects,
                index=default_index,
                help="Available projects from oma.properties"
            )
            
            # When project is changed
            if selected_project != current_project:
                if st.button("🔄 Apply Project", type="primary", use_container_width=True):
                    if st.session_state.oma_controller.set_project_environment(selected_project):
                        st.success(f"Changed to project '{selected_project}'!")
                        st.rerun()
                    else:
                        st.error("Failed to change project settings.")
        else:
            st.warning("⚠️ No projects found in oma.properties.")
        
        # Display current environment status
        if env_status['is_configured']:
            st.success(f"✅ Current Project: **{env_status['application_name']}**")
        else:
            st.error("❌ No project selected")
        
        st.info(f"📁 OMA Base Dir: {env_status['oma_base_dir']}")
        st.info(f"⚙️ Config File: {os.path.basename(env_status['config_file'])}")
        
        # Display execution status (simple)
        st.markdown("### 🔄 Running Status")
        
        # Cleanup dead processes and check current status
        st.session_state.oma_controller.cleanup_dead_processes()
        
        current_process = st.session_state.oma_controller.current_process
        running_tasks = st.session_state.task_manager.get_running_tasks()
        
        # 1. Check current_process first (dynamic task info display)
        if current_process and current_process.poll() is None:
            # Read actual task info from Task file
            task_info = get_current_task_info()
            if task_info:
                task_title = task_info.get('title', 'Task')
                st.error(f"🔴 **{task_title} Running**")
            else:
                st.error("🔴 **Task Running**")
            
            # Calculate elapsed time
            if hasattr(st.session_state, 'app_analysis_start_time'):
                elapsed = time.time() - st.session_state.app_analysis_start_time
                st.caption(f"⏱️ Elapsed: {int(elapsed//60)}m {int(elapsed%60)}s")
            
            # Detailed info (read from Task file)
            with st.expander("📊 Task Details", expanded=False):
                st.text(f"PID: {current_process.pid}")
                if task_info:
                    st.text(f"Task ID: {task_info.get('task_id', 'Unknown')}")
                    st.text(f"Log: {task_info.get('log_file', 'Unknown')}")
                    
                    # Add qlog view button for sample/full transform
                    task_title = task_info.get('title', '')
                    if 'Sample Transform' in task_title or 'Full Transform' in task_title:
                        if st.button("📊 View qlog", key="view_qlog_btn", use_container_width=True):
                            st.session_state.selected_action = "view_qlog"
                            st.rerun()
                else:
                    if st.session_state.oma_controller.current_task_id:
                        st.text(f"Task ID: {st.session_state.oma_controller.current_task_id}")
                    st.text("Log: No info")
            
            # Provide log view button even when running
            if st.button("📋 View Logs", key="view_logs_btn", use_container_width=True):
                st.session_state.selected_action = "view_running_logs"
                st.rerun()
                
        # 2. TaskManager based task check
        elif running_tasks:
            task = running_tasks[0]
            st.warning(f"🟡 **{task['title']} Running**")
            
            # Detailed info
            with st.expander("📊 Task Details", expanded=False):
                st.text(f"PID: {task['pid']}")
                st.text(f"Task ID: {task['task_id']}")
                st.text(f"Started: {task['start_time'][:19]}")
                
                # Add qlog view button for sample/full transform
                task_title = task.get('title', '')
                if 'Sample Transform' in task_title or 'Full Transform' in task_title:
                    if st.button("📊 View qlog", key="view_qlog_tm_btn", use_container_width=True):
                        st.session_state.selected_action = "view_qlog"
                        st.rerun()
            
            # Provide log view button even when running
            if st.button("📋 View Logs", key="view_logs_tm_btn", use_container_width=True):
                st.session_state.selected_action = "view_running_logs"
                st.rerun()
        else:
            # Waiting
            st.success("🟢 **Waiting**")
            st.caption("No running tasks")
            
            # Log viewing available even when waiting (recent logs)
            if st.button("📋 View Logs", key="view_recent_logs_btn", use_container_width=True):
                st.session_state.selected_action = "view_running_logs"
                st.rerun()
        
        st.markdown("---")
        
        # Process stop button (only when running)
        if (current_process and current_process.poll() is None) or running_tasks:
            if st.button("🛑 Stop Current Task", type="secondary", use_container_width=True):
                if st.session_state.oma_controller.stop_current_process():
                    st.success("Task stopped.")
                    st.rerun()
                else:
                    st.info("No running tasks.")
        
        st.markdown("---")
        
        # Session state initialization (once only)
        if 'session_initialized' not in st.session_state:
            if 'selected_action' not in st.session_state:
                st.session_state.selected_action = None
            if 'current_screen' not in st.session_state:
                st.session_state.current_screen = 'welcome'
            st.session_state.session_initialized = True
        
        # Pretty accordion style menu
        st.header("📋 Task Menu")
        
        # Define menu tree structure
        menu_tree = {
            "📊 Project Environment Info": {},  # No sub menu - direct execution
            "📊 Application Analysis": {
                "🔍 Application Analysis": "app_analysis",
                "📄 Analysis Report": "app_reporting",
                "📋 Review Analysis Report": "discovery_report_review",
                "🗄️ PostgreSQL Metadata": "postgresql_meta"
            },
            "🔄 Application Transform": {
                "✅ Mapper Validation": "mapper_validation",
                "🧪 Sample Transform": "sample_transform",
                "🚀 Full Transform": "full_transform",
                "🔗 XML Merge": "merge_transform"
            },
            "🧪 SQL Test": {
                "⚙️ Parameter Config": "parameter_config",
                "⚖️ Compare SQL Test": "source_sqls"
            },
            "📋 Transform Report": {
                "📊 Generate Transform Report": "transform_report",
                "📄 View Transform Report": "view_transform_report"
            }
        }
        
        # Render accordion style menu (auto cleanup dead processes)
        is_running = st.session_state.oma_controller.is_any_task_running()
        
        for main_menu, sub_menus in menu_tree.items():
            # Project environment info direct execution
            if "Project Environment Info" in main_menu:
                if st.button(main_menu, key=f"direct_{main_menu}", use_container_width=True, type="primary", disabled=is_running):
                    st.session_state.selected_action = "project_env_info"
                    st.session_state.current_screen = "project_env_info"
                    st.rerun()
            else:
                # Other menus use existing accordion method
                with st.expander(main_menu, expanded=False):
                    for sub_menu, action_key in sub_menus.items():
                        help_text = f"Execute {sub_menu} task"
                        disabled_help = "Another task is running"
                        
                        if st.button(
                            sub_menu,
                            key=f"menu_{action_key}",
                            use_container_width=True,
                            type="secondary",
                            disabled=is_running,
                            help=help_text if not is_running else disabled_help
                        ):
                            st.session_state.selected_action = action_key
                            st.session_state.current_screen = action_key
                            st.rerun()
    
    # Main content area - page based rendering
    # Render page only when action is selected
    selected_action = st.session_state.get('selected_action')
    
    # Log viewer handled completely independently
    if selected_action == "view_running_logs":
        # Render only log viewer and exit immediately
        render_running_logs_page()
        return  # Complete function exit
    
    # qlog viewer also handled independently
    if selected_action == "view_qlog":
        # Render only qlog viewer and exit immediately
        render_qlog_page()
        return  # Complete function exit
    
    # Handle other actions
    if selected_action:
        render_action_page(selected_action)
        return  # Complete function exit
    
    # Default welcome page
    render_welcome_page()


def render_action_page(action_key):
    """Render pages by action"""
    # Completely independent page composition for each action
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
        st.error(f"Unknown action: {action_key}")


def get_current_task_info():
    """Read Task file info of currently running task"""
    try:
        if not os.path.exists("./oma_tasks"):
            return None
        
        task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
        if not task_files:
            return None
        
        # Read most recent task file
        latest_task_file = f"./oma_tasks/{sorted(task_files)[-1]}"
        
        with open(latest_task_file, 'r') as f:
            task_data = json.load(f)
        
        return task_data
        
    except Exception as e:
        return None


if __name__ == "__main__":
    main()
