"""
Common utility functions for pages
"""
import streamlit as st
import subprocess
import os
import time
import re


def execute_command_with_logs(command, title, log_file_path=None):
    """Execute command and display real-time logs (supports specific log file monitoring)"""
    
    # 🔍 Essential check before task start: Check and clean up running tasks
    if st.session_state.oma_controller.is_any_task_running():
        st.error("❌ Another task is currently running. Please complete or stop the existing task before trying again.")
        
        # Display currently running task information
        current_process = st.session_state.oma_controller.current_process
        running_tasks = st.session_state.task_manager.get_running_tasks()
        
        if current_process and current_process.poll() is None:
            st.warning(f"🔄 Application analysis is running (PID: {current_process.pid})")
        elif running_tasks:
            task = running_tasks[0]
            st.warning(f"🔄 {task['title']} is running (PID: {task['pid']})")
        
        st.info("💡 You can use the '🛑 Stop Current Task' button in the sidebar to stop existing tasks.")
        return
    
    # Place execution info and stop button at the top
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"**{title}:** `{command}`")
        if log_file_path:
            # Substitute environment variables
            expanded_log_path = os.path.expandvars(log_file_path)
            st.caption(f"📄 Log file: {expanded_log_path}")
    
    with col2:
        if st.button("🛑 Task Stop", key=f"stop_{hash(command)}", type="secondary"):
            if st.session_state.oma_controller.stop_current_process():
                st.warning("⚠️ Task has been stopped.")
                st.stop()
            else:
                st.info("No running task found.")
    
    # Log area (utilize full screen)
    log_container = st.empty()
    
    try:
        if log_file_path:
            # Method to monitor specific log file
            execute_with_specific_log_file(command, title, log_file_path, log_container)
        else:
            # Existing method (using TaskManager)
            execute_with_task_manager(command, title, log_container)
        
        # Task completion message
        st.success(f"✅ {title} task completed successfully!")
        
        # Auto-save environment variables (after Environment Setup related tasks)
        if 'setEnv' in command or 'checkEnv' in command:
            st.session_state.oma_controller.update_environment_vars()
        
    except Exception as e:
        st.error(f"❌ An error occurred during task execution: {str(e)}")


def execute_with_task_manager(command, title, log_container):
    """Execute command using existing TaskManager method"""
    # Collect and display real-time logs
    log_generator = st.session_state.oma_controller.run_command_with_logs(command, title)
    
    for log_line in log_generator:
        # Get all logs from TaskManager for current task and display
        current_task = st.session_state.oma_controller.get_current_task()
        if current_task:
            all_logs = st.session_state.task_manager.get_task_logs(current_task['task_id'])
            log_text = "\n".join(all_logs)
            
            # Convert ANSI color codes to HTML
            colored_log_html = convert_ansi_to_html(log_text)
            
            with log_container.container():
                st.markdown(f"""
                <div class="log-container">
{colored_log_html}
                </div>
                """, unsafe_allow_html=True)


def convert_ansi_to_html(text):
    """Convert ANSI color codes to HTML and remove control characters"""
    # Remove all ANSI escape sequences and keep only clean text
    # Cursor control: [?25l (hide cursor), [?25h (show cursor)
    text = re.sub(r'\x1b\[\?25[lh]', '', text)
    
    # Remove other cursor movement and screen control sequences
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    
    # Remove control characters like backspace, carriage return, etc
    text = re.sub(r'[\x08\x0c\x0e\x0f]', '', text)
    
    # Consolidate consecutive spaces into one
    text = re.sub(r' +', ' ', text)
    
    # Clean up empty lines
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()
