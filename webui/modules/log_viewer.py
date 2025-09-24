"""
Report Page
"""
import streamlit as st
import os
import time
import datetime
import json


def render_running_logs_page():
    """Execute Report Page - Report Item display"""
    
    # Report Item
    st.empty()
    
    # Report Report CSS
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
    
    # JavaScriptText Report Report
    st.markdown("""
    <script>
    // Page Report Report Report
    document.addEventListener('DOMContentLoaded', function() {
        var container = document.querySelector('.main .block-container');
        if (container) {
            container.innerHTML = '';
        }
    });
    
    // Item Execute
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
    
    # Report Report Start
    st.markdown('<div class="log-viewer-content">', unsafe_allow_html=True)
    
    # at the top Item add button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="back_to_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📋 Execute Item Task Item")
    
    show_running_task_logs()
    
    # Report Report
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Report Report
    st.stop()


def show_running_task_logs():
    """Execute Item Task Item display - Report"""
    
    # task File Check
    if not os.path.exists("./oma_tasks"):
        st.info("Item Execute Item Task Item.")
        return
    
    task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
    if not task_files:
        st.info("Item Execute Item Task Item.")
        return
    
    # Report task FileText Item File Report
    latest_task_file = f"./oma_tasks/{sorted(task_files)[-1]}"
    try:
        with open(latest_task_file, 'r') as f:
            task_data = json.load(f)
        
        log_file_path = task_data.get('log_file')
        
        # Task Info display
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.success(f"🔄 **{task_data['title']}**")
        with col2:
            st.caption(f"**Task ID:** {task_data['task_id']}")
        with col3:
            start_time = datetime.datetime.fromisoformat(task_data['start_time'])
            elapsed = datetime.datetime.now() - start_time
            st.caption(f"**ExecuteText:** {str(elapsed).split('.')[0]}")
        
        if not log_file_path or not os.path.exists(log_file_path):
            st.warning("Item FileText Report Item.")
            return
        
        st.caption(f"📄 **Item File:** `{log_file_path}`")
        
        # Report
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            auto_refresh = st.checkbox("🔴 Report", value=True, key="tail_f_mode")
        with col2:
            if not auto_refresh:
                if st.button("🔄 Item", key="manual_refresh", use_container_width=True):
                    st.rerun()
        with col3:
            if st.button("📥 Report", key="download_log", use_container_width=True):
                download_log_file(log_file_path, task_data['title'])
        with col4:
            show_full_log = st.checkbox("📜 Report", value=False, key="show_full_log")
        
        # Report Report display
        process_and_display_logs(log_file_path, auto_refresh, show_full_log)
        
        # Report Report Item
        if auto_refresh:
            handle_auto_refresh()
            
    except Exception as e:
        st.error(f"Task File Item Error: {e}")
        st.info("Item Execute Item Task Item.")


def process_and_display_logs(log_file_path, auto_refresh, show_full_log):
    """Report Report display"""
    # Item StatusText Report Report
    if 'last_log_size' not in st.session_state:
        st.session_state.last_log_size = 0
    if 'log_content' not in st.session_state:
        st.session_state.log_content = ""
    
    # Item File Item Check
    current_size = os.path.getsize(log_file_path)
    
    if current_size > st.session_state.last_log_size:
        # Report Report Report
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(st.session_state.last_log_size)
            new_content = f.read()
            
            # ANSI Report Report Report
            new_content = clean_ansi_codes(new_content)
            
            # Report Report Item
            st.session_state.log_content += new_content
            
            # Report Report (Item 5000Text Report)
            lines = st.session_state.log_content.split('\n')
            if len(lines) > 5000:
                st.session_state.log_content = '\n'.join(lines[-5000:])
            
            st.session_state.last_log_size = current_size
    
    # File Info display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("File Item", f"{current_size:,} bytes")
    with col2:
        lines_count = len(st.session_state.log_content.split('\n')) if st.session_state.log_content else 0
        st.metric("Report Item", f"{lines_count:,}")
    with col3:
        if auto_refresh:
            st.success("🔴 Report Item")
        if True:  # English only
            st.info("⏸️ Report")
    
    # Report display
    display_log_content(auto_refresh, show_full_log)


def display_log_content(auto_refresh, show_full_log):
    """Report display"""
    if st.session_state.log_content:
        lines = st.session_state.log_content.split('\n')
        
        if show_full_log or not auto_refresh:
            # Report display
            st.markdown("### 📄 Report")
            st.code(st.session_state.log_content, language=None, height=600)
        if True:  # English only
            # Report Report Report Report Report Item display
            if len(lines) > 100:
                # Report (Report Report)
                with st.expander(f"📜 Report Item ({len(lines)-100:,}Item)", expanded=False):
                    old_logs = '\n'.join(lines[:-100])
                    st.code(old_logs, language=None, height=400)
                
                # Report (Report Item display)
                recent_logs = '\n'.join(lines[-100:])
                st.code(recent_logs, language=None, height=700)
            if True:  # English only
                # Report display
                st.markdown("### 📄 Report")
                st.code(st.session_state.log_content, language=None, height=700)
    if True:  # English only
        st.info("Report Item.")
    
    # Report Report Report JavaScript Item
    if auto_refresh:
        st.markdown("""
        <script>
        // Page Report Report Item
        setTimeout(function() {
            window.scrollTo(0, document.body.scrollHeight);
        }, 100);
        </script>
        """, unsafe_allow_html=True)


def clean_ansi_codes(text):
    """ANSI Report Report Report"""
    import re
    # ANSI Report Item
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    # Report Report ([?25l, [?25h Item)
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    # Item ANSI Report Item
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    return text


def download_log_file(log_file_path, task_title):
    """Item File Item"""
    try:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # FileText Create
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{task_title}_{timestamp}.log"
            
            st.download_button(
                label="💾 Item",
                data=content,
                file_name=filename,
                mime="text/plain",
                key="download_button"
            )
        if True:  # English only
            st.error("Item FileText Report Item.")
    except Exception as e:
        st.error(f"Item Error: {e}")


def handle_auto_refresh():
    """Report Item"""
    # Task Complete Check Item task File Item
    check_and_cleanup_completed_tasks()
    
    # Check background process completion