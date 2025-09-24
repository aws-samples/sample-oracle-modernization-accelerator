"""
Common utility functions for pages
"""
import streamlit as st
import subprocess
import os
import time
import re

def get_page_text(key, lang=None):
    """Return English text for all keys"""
    # Common messages
    texts = {
        "task_running_error": "❌ Another task is running. Please complete or stop the existing task and try again.",
        "stop_task_info": "💡 You can stop the existing task using the '🛑 Stop Current Task' button in the sidebar.",
        "stop_task": "🛑 Stop Task",
        "task_stopped": "⚠️ Task has been stopped.",
        "no_running_task": "No running tasks.",
        "task_completed": "✅ {} task completed!",
        "task_error": "❌ Error occurred during task execution: {}",
        "log_file": "📄 Log file:",
        "running_with_pid": "🔄 {} is running (PID: {})",
        
        # Welcome page
        "welcome_title": "🏠 Oracle Migration Assistant (OMA) Web Application",
        "welcome_subtitle": "Integrated tool for database migration from Oracle to PostgreSQL",
        
        # Project environment info
        "project_env_title": "📊 Project Environment Information",
        "current_env_status": "Current Environment Status",
        "project_configured": "✅ Project is configured",
        "project_not_configured": "❌ Project is not configured",
        
        # Application analysis
        "app_analysis_title": "🔍 Application Analysis",
        "app_analysis_desc": "Analyze Java source code and MyBatis Mapper files.",
        "start_analysis": "🚀 Start Analysis",
        
        # Analysis report
        "app_reporting_title": "📄 Analysis Report Generation",
        "app_reporting_desc": "Generate reports based on analysis results.",
        "start_reporting": "📊 Generate Report",
        
        # Sample transform
        "sample_transform_title": "🧪 Sample Transform Execution",
        "sample_transform_desc": "Transform selected SQL samples to PostgreSQL.",
        "start_sample_transform": "🧪 Start Sample Transform",
        
        # Full transform
        "full_transform_title": "🚀 Full Transform Execution",
        "full_transform_desc": "Transform all SQL to PostgreSQL.",
        "start_full_transform": "🚀 Start Full Transform"
    }
    
    return texts.get(key, key)


def execute_command_with_logs(command, title, log_file_path=None):
    """Execute command and display real-time logs (with specific log file monitoring support)"""
    
    # 🔍 Essential check before starting task: check and clean up running tasks
    if st.session_state.oma_controller.is_any_task_running():
        st.error(get_page_text("task_running_error"))
        
        # Display current running task info
        current_process = st.session_state.oma_controller.current_process
        running_tasks = st.session_state.task_manager.get_running_tasks()
        
        if current_process and current_process.poll() is None:
            st.warning(get_page_text("running_with_pid").format("Application Analysis", current_process.pid))
        elif running_tasks:
            task = running_tasks[0]
            st.warning(get_page_text("running_with_pid").format(task['title'], task['pid']))
        
        st.info(get_page_text("stop_task_info"))
        return
    
    # Place execution info and stop button at the top
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"**{title}:** `{command}`")
        if log_file_path:
            # Environment variable substitution
            expanded_log_path = os.path.expandvars(log_file_path)
            st.caption(f"{get_page_text('log_file')} {expanded_log_path}")
    
    with col2:
        if st.button(get_page_text("stop_task"), key=f"stop_{hash(command)}", type="secondary"):
            if st.session_state.oma_controller.stop_current_process():
                st.warning(get_page_text("task_stopped"))
                st.stop()
            else:
                st.info(get_page_text("no_running_task"))
    
    # Report (Report Item)
    log_container = st.empty()
    
    try:
        if log_file_path:
            # Report FileText Report
            execute_with_specific_log_file(command, title, log_file_path, log_container)
        else:
            # Report (TaskManager Item)
            execute_with_task_manager(command, title, log_container)
        
        # Task Complete Item
        st.success(get_page_text("task_completed").format(title))
        
        # Environment Report Item (Environment Config Item Task Item)
        if 'setEnv' in command or 'checkEnv' in command:
            st.session_state.oma_controller.update_environment_vars()
        
    except Exception as e:
        st.error(get_page_text("task_error").format(str(e)))


def execute_with_task_manager(command, title, log_container):
    """Item TaskManager Report Execute"""
    # Report Report display
    log_generator = st.session_state.oma_controller.run_command_with_logs(command, title)
    
    for log_line in log_generator:
        # Item Task Report TaskManagerText Item display
        current_task = st.session_state.oma_controller.get_current_task()
        if current_task:
            all_logs = st.session_state.task_manager.get_task_logs(current_task['task_id'])
            log_text = "\n".join(all_logs)
            
            # ANSI Report HTMLText Transform
            colored_log_html = convert_ansi_to_html(log_text)
            
            with log_container.container():
                st.markdown(f"""
                <div class="log-container">
{colored_log_html}
                </div>
                """, unsafe_allow_html=True)


def convert_ansi_to_html(text):
    """ANSI Report HTMLText TransformText Report Item"""
    # Item ANSI Report Report Report
    # Report: [?25l (Report), [?25h (Item display)
    text = re.sub(r'\x1b\[\?25[lh]', '', text)
    
    # Report Item, Report Report
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    
    # Item, Report Report Report
    text = re.sub(r'[\x08\x0c\x0e\x0f]', '', text)
    
    # Report Report
    text = re.sub(r' +', ' ', text)
    
    # Report Item
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()
