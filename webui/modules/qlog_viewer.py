"""
qlog Viewer Page
"""
import streamlit as st
import subprocess
import os
import time
import glob
import re


def clean_ansi_codes(text):
    """Remove ANSI color codes and escape sequences"""
    if not text:
        return text
    
    # Remove ANSI color codes (more comprehensive pattern)
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    # Remove cursor control sequences
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    # Remove other ANSI escape sequences
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    # Remove additional ANSI sequences
    text = re.sub(r'\x1b\[[0-9;]*[~]', '', text)
    # Remove 38;5;number format 256-color codes
    text = re.sub(r'\x1b\[38;5;[0-9]+m', '', text)
    text = re.sub(r'\x1b\[48;5;[0-9]+m', '', text)
    # Remove all ESC sequences (stronger pattern)
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z~]', '', text)
    
    return text


def render_qlog_page():
    """qlog viewer page - display after screen initialization"""
    
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
                if (!children[i].classList.contains('qlog-viewer-content')) {
                    children[i].remove();
                }
            }
        }
    }, 10);
    </script>
    """, unsafe_allow_html=True)
    
    # Start qlog viewer dedicated container
    st.markdown('<div class="qlog-viewer-content">', unsafe_allow_html=True)
    
    # Add home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="qlog_back_to_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📊 qlog Real-time View")
    
    # Control panel
    col1, col2 = st.columns([1, 3])
    with col1:
        auto_refresh = st.checkbox("🔴 Real-time Mode", value=True, key="qlog_auto_refresh")
    with col2:
        if not auto_refresh:
            if st.button("🔄 Refresh", key="qlog_manual_refresh", use_container_width=True):
                st.rerun()
    
    # Display qlog content
    show_qlog_content(auto_refresh)
    
    # End qlog viewer container
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Completely block additional content
    st.stop()


def show_qlog_content(auto_refresh):
    """Display qlog content - last 50 lines from latest file in qlogs directory"""
    try:
        # Check APP_LOGS_FOLDER environment variable
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER', '')
        if not app_logs_folder:
            st.error("❌ APP_LOGS_FOLDER environment variable is not set.")
            return
        
        qlogs_dir = os.path.join(app_logs_folder, 'qlogs')
        if not os.path.exists(qlogs_dir):
            st.error(f"❌ qlogs directory not found: {qlogs_dir}")
            return
        
        # Find all log files in qlogs directory
        log_files = glob.glob(os.path.join(qlogs_dir, '*'))
        log_files = [f for f in log_files if os.path.isfile(f)]
        
        if not log_files:
            st.warning("⚠️ No log files in qlogs directory.")
            return
        
        # Find latest file (based on modification time)
        latest_file = max(log_files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        file_size = os.path.getsize(latest_file)
        
        # Display file information (more info, smaller font)
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate file modification time
        import datetime
        mod_time = os.path.getmtime(latest_file)
        mod_datetime = datetime.datetime.fromtimestamp(mod_time)
        time_ago = datetime.datetime.now() - mod_datetime
        
        # Convert time difference to human-readable format
        if time_ago.total_seconds() < 60:
            time_str = f"{int(time_ago.total_seconds())} seconds ago"
        elif time_ago.total_seconds() < 3600:
            time_str = f"{int(time_ago.total_seconds()//60)} minutes ago"
        else:
            time_str = f"{int(time_ago.total_seconds()//3600)} hours ago"
        
        with col1:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>📄 Filename</strong><br>
                {file_name}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>📏 Size</strong><br>
                {file_size:,} bytes
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>🕒 ModifyTime</strong><br>
                {time_str}
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            status_color = "#28a745" if auto_refresh else "#6c757d"
            status_text = "🔴 Real-time" if auto_refresh else "⏸️ Manual Mode"
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>⚡ Status</strong><br>
                <span style="color: {status_color};">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Get last 50 lines from latest file
        result = subprocess.run(
            ['tail', '-n', '50', latest_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            qlog_content = result.stdout
            
            # Remove ANSI color codes
            qlog_content = clean_ansi_codes(qlog_content)
            
            # Display qlog content
            if qlog_content.strip():
                lines_count = len(qlog_content.split('\n'))
                st.markdown(f"""
                <div style="font-size: 1.0em;">
                    <h3>📊 Latest qlog content (last {lines_count} lines)</h3>
                </div>
                """, unsafe_allow_html=True)
                st.code(qlog_content, language=None, height=700)
            else:
                st.info("No qlog content available.")
                
        else:
            st.error(f"❌ tail command execution error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        st.error("❌ tail command execution timeout (10 seconds)")
    except Exception as e:
        st.error(f"❌ qlog read error: {str(e)}")
    
    # Auto refresh in real-time mode (every 2 seconds)
    if auto_refresh:
        time.sleep(2)  # Refresh every 2 seconds
        st.rerun()
