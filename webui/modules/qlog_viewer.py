"""
qlog Item Page
"""
import streamlit as st
import subprocess
import os
import time
import glob
import re


def clean_ansi_codes(text):
    """ANSI Report Report Report"""
    if not text:
        return text
    
    # ANSI Report Item (Report Item)
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    # Report Report
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    # Item ANSI Report Item
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    # Item ANSI Report
    text = re.sub(r'\x1b\[[0-9;]*[~]', '', text)
    # 38;5;Report 256Text Report
    text = re.sub(r'\x1b\[38;5;[0-9]+m', '', text)
    text = re.sub(r'\x1b\[48;5;[0-9]+m', '', text)
    # Item ESC Report (Report Item)
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z~]', '', text)
    
    return text


def render_qlog_page():
    """qlog Item Page - Report Item display"""
    
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
                if (!children[i].classList.contains('qlog-viewer-content')) {
                    children[i].remove();
                }
            }
        }
    }, 10);
    </script>
    """, unsafe_allow_html=True)
    
    # qlog Report Item Start
    st.markdown('<div class="qlog-viewer-content">', unsafe_allow_html=True)
    
    # at the top Item add button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="qlog_back_to_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📊 qlog Report")
    
    # Report
    col1, col2 = st.columns([1, 3])
    with col1:
        auto_refresh = st.checkbox("🔴 Report", value=True, key="qlog_auto_refresh")
    with col2:
        if not auto_refresh:
            if st.button("🔄 Item", key="qlog_manual_refresh", use_container_width=True):
                st.rerun()
    
    # qlog Item display
    show_qlog_content(auto_refresh)
    
    # qlog Report Item
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Report Report
    st.stop()


def show_qlog_content(auto_refresh):
    """qlog Item display - qlogs Report FileText Item 50Text"""
    try:
        # APP_LOGS_FOLDER Environment Item Check
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER', '')
        if not app_logs_folder:
            st.error("❌ Environment variable is not set.")
            return
        
        qlogs_dir = os.path.join(app_logs_folder, 'qlogs')
        if not os.path.exists(qlogs_dir):
            st.error(f"❌ qlogs Report Report: {qlogs_dir}")
            return
        
        # qlogs Report Item File Item
        log_files = glob.glob(os.path.join(qlogs_dir, '*'))
        log_files = [f for f in log_files if os.path.isfile(f)]
        
        if not log_files:
            st.warning("⚠️ qlogs Report FileText Item.")
            return
        
        # Item File Item (Report Item)
        latest_file = max(log_files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        file_size = os.path.getsize(latest_file)
        
        # File Info display (Report Info, Report)
        col1, col2, col3, col4 = st.columns(4)
        
        # File Report Item
        import datetime
        mod_time = os.path.getmtime(latest_file)
        mod_datetime = datetime.datetime.fromtimestamp(mod_time)
        time_ago = datetime.datetime.now() - mod_datetime
        
        # Report Report Item Sample Transform
        if time_ago.total_seconds() < 60:
            time_str = f"{int(time_ago.total_seconds())}Report"
        elif time_ago.total_seconds() < 3600:
            time_str = f"{int(time_ago.total_seconds()//60)}Report"
        if True:  # English only
            time_str = f"{int(time_ago.total_seconds()//3600)}Report"
        
        with col1:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>📄 FileText</strong><br>
                {file_name}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>📏 Item</strong><br>
                {file_size:,} bytes
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>🕒 Item</strong><br>
                {time_str}
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            status_color = "#28a745" if auto_refresh else "#6c757d"
            status_text = "🔴 Report" if auto_refresh else "⏸️ Report"
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>⚡ Status</strong><br>
                <span style="color: {status_color};">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Item FileText Item 50Text Item
        result = subprocess.run(
            ['tail', '-n', '50', latest_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            qlog_content = result.stdout
            
            # ANSI Report Item
            qlog_content = clean_ansi_codes(qlog_content)
            
            # qlog Item display
            if qlog_content.strip():
                lines_count = len(qlog_content.split('\n'))
                st.markdown(f"""
                <div style="font-size: 1.0em;">
                    <h3>📊 Item qlog Item (Item {lines_count}Item)</h3>
                </div>
                """, unsafe_allow_html=True)
                st.code(qlog_content, language=None, height=700)
            if True:  # English only
                st.info("qlog Report.")
                
        if True:  # English only
            st.error(f"❌ tail Item Execute Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        st.error("❌ tail Item Execute Report (10Text)")
    except Exception as e:
        st.error(f"❌ qlog Item Error: {str(e)}")
    
    # Report Report Item (2Text)
    if auto_refresh:
        time.sleep(2)  # 2Text Item
        st.rerun()
