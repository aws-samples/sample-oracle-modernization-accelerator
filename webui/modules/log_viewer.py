"""
Log Viewer Page
"""
import streamlit as st
import os
import time
import datetime
import json


def render_running_logs_page():
    """Running logs view page - display after screen initialization"""
    
    # Complete screen initialization
    st.empty()
    
    # CSS to remove all existing content
    st.markdown("""
    <style>
    .main .block-container {
        background: white;
        min-height: 100vh;
    }
    .main .block-container > div:not(:last-child) {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # JavaScript to completely remove existing content
    st.markdown("""
    <script>
    // Remove all existing content on page load
    document.addEventListener('DOMContentLoaded', function() {
        var container = document.querySelector('.main .block-container');
        if (container) {
            container.innerHTML = '';
        }
    });
    
    // Execute immediately
    setTimeout(function() {
        var container = document.querySelector('.main .block-container');
        if (container) {
            var children = container.children;
            for (var i = children.length - 1; i >= 0; i--) {
                if (!children[i].classList.contains('log-viewer-content')) {
                    children[i].remove();
                }
            }
        }
    }, 10);
    </script>
    """, unsafe_allow_html=True)
    
    # Start log viewer dedicated container
    st.markdown('<div class="log-viewer-content">', unsafe_allow_html=True)
    
    # Add home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="back_to_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📋 Running Task Logs")
    
    show_running_task_logs()
    
    # End log viewer container
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Completely block additional content
    st.stop()


def show_running_task_logs():
    """Display logs of running tasks - improved version"""
    
    # Check task files
    if not os.path.exists("./oma_tasks"):
        st.info("No currently running tasks.")
        return
    
    task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
    if not task_files:
        st.info("No currently running tasks.")
        return
    
    # Get log file path from the most recent task file
    latest_task_file = f"./oma_tasks/{sorted(task_files)[-1]}"
    try:
        with open(latest_task_file, 'r') as f:
            task_data = json.load(f)
        
        log_file_path = task_data.get('log_file')
        
        # Display task information
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.success(f"🔄 **{task_data['title']}**")
        with col2:
            st.caption(f"**Task ID:** {task_data['task_id']}")
        with col3:
            start_time = datetime.datetime.fromisoformat(task_data['start_time'])
            elapsed = datetime.datetime.now() - start_time
            st.caption(f"**Runtime:** {str(elapsed).split('.')[0]}")
        
        if not log_file_path or not os.path.exists(log_file_path):
            st.warning("Log file not found.")
            return
        
        st.caption(f"📄 **Log file:** `{log_file_path}`")
        
        # Control panel
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            auto_refresh = st.checkbox("🔴 Real-time Mode", value=True, key="tail_f_mode")
        with col2:
            if not auto_refresh:
                if st.button("🔄 Refresh", key="manual_refresh", use_container_width=True):
                    st.rerun()
        with col3:
            if st.button("📥 Download Log", key="download_log", use_container_width=True):
                download_log_file(log_file_path, task_data['title'])
        with col4:
            show_full_log = st.checkbox("📜 Full Log", value=False, key="show_full_log")
        
        # Process and display log content
        process_and_display_logs(log_file_path, auto_refresh, show_full_log)
        
        # Auto refresh only in real-time mode
        if auto_refresh:
            handle_auto_refresh()
            
    except Exception as e:
        st.error(f"Task file read error: {e}")
        st.info("No currently running tasks.")


def process_and_display_logs(log_file_path, auto_refresh, show_full_log):
    """Process and display log content"""
    # Store last read position in session state
    if 'last_log_size' not in st.session_state:
        st.session_state.last_log_size = 0
    if 'log_content' not in st.session_state:
        st.session_state.log_content = ""
    
    # Check current file size
    current_size = os.path.getsize(log_file_path)
    
    if current_size > st.session_state.last_log_size:
        # If there's new content, read only the added part
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(st.session_state.last_log_size)
            new_content = f.read()
            
            # Remove ANSI color codes and escape sequences
            new_content = clean_ansi_codes(new_content)
            
            # Add new content to existing log
            st.session_state.log_content += new_content
            
            # Trim front if too long (keep only recent 5000 lines)
            lines = st.session_state.log_content.split('\n')
            if len(lines) > 5000:
                st.session_state.log_content = '\n'.join(lines[-5000:])
            
            st.session_state.last_log_size = current_size
    
    # Display file information
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("File Size", f"{current_size:,} bytes")
    with col2:
        lines_count = len(st.session_state.log_content.split('\n')) if st.session_state.log_content else 0
        st.metric("Log Lines", f"{lines_count:,}")
    with col3:
        if auto_refresh:
            st.success("🔴 Real-time updating")
        else:
            st.info("⏸️ Manual Mode")
    
    # Display log content
    display_log_content(auto_refresh, show_full_log)


def display_log_content(auto_refresh, show_full_log):
    """Display log content"""
    if st.session_state.log_content:
        lines = st.session_state.log_content.split('\n')
        
        if show_full_log or not auto_refresh:
            # Display full log
            st.markdown("### 📄 Full Log")
            st.code(st.session_state.log_content, language=None, height=600)
        else:
            # In real-time mode, display last few lines separately to emphasize latest logs
            if len(lines) > 100:
                # Previous logs (collapsible)
                with st.expander(f"📜 View Previous Logs ({len(lines)-100:,} lines)", expanded=False):
                    old_logs = '\n'.join(lines[:-100])
                    st.code(old_logs, language=None, height=400)
                
                # Latest logs (display directly without title)
                recent_logs = '\n'.join(lines[-100:])
                st.code(recent_logs, language=None, height=700)
            else:
                # Display full log
                st.markdown("### 📄 Log Content")
                st.code(st.session_state.log_content, language=None, height=700)
    else:
        st.info("No log content available.")
    
    # Add JavaScript for auto scroll in real-time mode
    if auto_refresh:
        st.markdown("""
        <script>
        // Scroll to bottom after page load
        setTimeout(function() {
            window.scrollTo(0, document.body.scrollHeight);
        }, 100);
        </script>
        """, unsafe_allow_html=True)


def clean_ansi_codes(text):
    """Remove ANSI color codes and escape sequences"""
    import re
    # Remove ANSI color codes
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    # Remove cursor control sequences ([?25l, [?25h etc)
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    # Remove other ANSI escape sequences
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    return text


def download_log_file(log_file_path, task_title):
    """Log file Download"""
    try:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{task_title}_{timestamp}.log"
            
            st.download_button(
                label="💾 Download",
                data=content,
                file_name=filename,
                mime="text/plain",
                key="download_button"
            )
        else:
            st.error("Log file not found.")
    except Exception as e:
        st.error(f"Download error: {e}")


def handle_auto_refresh():
    """Handle auto refresh"""
    # Check task completion and cleanup task files
    check_and_cleanup_completed_tasks()
    
    # Check background process completion
    current_process = st.session_state.oma_controller.current_process
    running_tasks = st.session_state.task_manager.get_running_tasks()
    
    # If process is completed, return to home and refresh sidebar
    if (not current_process or (current_process and current_process.poll() is not None)) and not running_tasks:
        st.success("✅ Task completed!")
        st.info("🏠 Returning to home screen...")
        time.sleep(1)
        st.session_state.selected_action = None  # Go to home
        st.rerun()
    
    # Auto refresh in real-time mode (while maintaining state)
    time.sleep(2)
    st.rerun()  # Remove selected_action reset


def check_and_cleanup_completed_tasks():
    """Automatically delete task files of completed tasks"""
    try:
        if not os.path.exists("./oma_tasks"):
            return
        
        task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
        
        for task_file in task_files:
            task_path = f"./oma_tasks/{task_file}"
            try:
                with open(task_path, 'r') as f:
                    task_data = json.load(f)
                
                pid = task_data.get('pid')
                if pid:
                    # Check if process is completed
                    try:
                        # Check if PID exists (Unix system)
                        os.kill(pid, 0)
                        # Process is still running
                    except OSError:
                        # Process completed → delete task file
                        os.remove(task_path)
                        print(f"✅ Deleted task file of completed task: {task_file}")
                        
            except Exception as e:
                # Delete corrupted task file
                os.remove(task_path)
                print(f"🗑️ Deleted corrupted task file: {task_file}")
                
    except Exception as e:
        print(f"Error during task file cleanup: {e}")
