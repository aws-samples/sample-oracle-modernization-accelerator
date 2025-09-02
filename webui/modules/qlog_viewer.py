"""
qlog 뷰어 페이지
"""
import streamlit as st
import subprocess
import os
import time
import glob
import re


def clean_ansi_codes(text):
    """ANSI 색상 코드 및 이스케이프 시퀀스 제거"""
    if not text:
        return text
    
    # ANSI 색상 코드 제거 (더 포괄적인 패턴)
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    # 커서 제어 시퀀스 제거
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    # 기타 ANSI 이스케이프 시퀀스 제거
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    # 추가 ANSI 시퀀스 제거
    text = re.sub(r'\x1b\[[0-9;]*[~]', '', text)
    # 38;5;숫자 형태의 256색 코드 제거
    text = re.sub(r'\x1b\[38;5;[0-9]+m', '', text)
    text = re.sub(r'\x1b\[48;5;[0-9]+m', '', text)
    # 모든 ESC 시퀀스 제거 (더 강력한 패턴)
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z~]', '', text)
    
    return text


def render_qlog_page():
    """qlog 뷰어 페이지 - 화면 초기화 후 표시"""
    
    # 화면 완전 초기화
    st.empty()
    
    # 모든 기존 내용 제거하는 CSS
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
    
    # JavaScript로 기존 내용 완전 제거
    st.markdown("""
    <script>
    // 페이지 로드 시 기존 내용 모두 제거
    document.addEventListener('DOMContentLoaded', function() {
        var container = document.querySelector('.main .block-container');
        if (container) {
            container.innerHTML = '';
        }
    });
    
    // 즉시 실행
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
    
    # qlog 뷰어 전용 컨테이너 시작
    st.markdown('<div class="qlog-viewer-content">', unsafe_allow_html=True)
    
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="qlog_back_to_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📊 qlog 실시간 보기")
    
    # 컨트롤 패널
    col1, col2 = st.columns([1, 3])
    with col1:
        auto_refresh = st.checkbox("🔴 실시간 모드", value=True, key="qlog_auto_refresh")
    with col2:
        if not auto_refresh:
            if st.button("🔄 새로고침", key="qlog_manual_refresh", use_container_width=True):
                st.rerun()
    
    # qlog 내용 표시
    show_qlog_content(auto_refresh)
    
    # qlog 뷰어 컨테이너 종료
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 추가 내용 완전 차단
    st.stop()


def show_qlog_content(auto_refresh):
    """qlog 내용 표시 - qlogs 디렉토리에서 최신 파일의 마지막 50라인"""
    try:
        # APP_LOGS_FOLDER 환경 변수 확인
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER', '')
        if not app_logs_folder:
            st.error("❌ APP_LOGS_FOLDER 환경 변수가 설정되지 않았습니다.")
            return
        
        qlogs_dir = os.path.join(app_logs_folder, 'qlogs')
        if not os.path.exists(qlogs_dir):
            st.error(f"❌ qlogs 디렉토리를 찾을 수 없습니다: {qlogs_dir}")
            return
        
        # qlogs 디렉토리에서 모든 로그 파일 찾기
        log_files = glob.glob(os.path.join(qlogs_dir, '*'))
        log_files = [f for f in log_files if os.path.isfile(f)]
        
        if not log_files:
            st.warning("⚠️ qlogs 디렉토리에 로그 파일이 없습니다.")
            return
        
        # 최신 파일 찾기 (수정 시간 기준)
        latest_file = max(log_files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        file_size = os.path.getsize(latest_file)
        
        # 파일 정보 표시 (더 많은 정보, 작은 폰트)
        col1, col2, col3, col4 = st.columns(4)
        
        # 파일 수정 시간 계산
        import datetime
        mod_time = os.path.getmtime(latest_file)
        mod_datetime = datetime.datetime.fromtimestamp(mod_time)
        time_ago = datetime.datetime.now() - mod_datetime
        
        # 시간 차이를 사람이 읽기 쉬운 형태로 변환
        if time_ago.total_seconds() < 60:
            time_str = f"{int(time_ago.total_seconds())}초 전"
        elif time_ago.total_seconds() < 3600:
            time_str = f"{int(time_ago.total_seconds()//60)}분 전"
        else:
            time_str = f"{int(time_ago.total_seconds()//3600)}시간 전"
        
        with col1:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>📄 파일명</strong><br>
                {file_name}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>📏 크기</strong><br>
                {file_size:,} bytes
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>🕒 수정시간</strong><br>
                {time_str}
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            status_color = "#28a745" if auto_refresh else "#6c757d"
            status_text = "🔴 실시간 중" if auto_refresh else "⏸️ 수동 모드"
            st.markdown(f"""
            <div style="font-size: 1.0em;">
                <strong>⚡ 상태</strong><br>
                <span style="color: {status_color};">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # 최신 파일의 마지막 50라인 가져오기
        result = subprocess.run(
            ['tail', '-n', '50', latest_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            qlog_content = result.stdout
            
            # ANSI 색상 코드 제거
            qlog_content = clean_ansi_codes(qlog_content)
            
            # qlog 내용 표시
            if qlog_content.strip():
                lines_count = len(qlog_content.split('\n'))
                st.markdown(f"""
                <div style="font-size: 1.0em;">
                    <h3>📊 최신 qlog 내용 (마지막 {lines_count}줄)</h3>
                </div>
                """, unsafe_allow_html=True)
                st.code(qlog_content, language=None, height=700)
            else:
                st.info("qlog 내용이 없습니다.")
                
        else:
            st.error(f"❌ tail 명령 실행 오류: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        st.error("❌ tail 명령 실행 시간 초과 (10초)")
    except Exception as e:
        st.error(f"❌ qlog 읽기 오류: {str(e)}")
    
    # 실시간 모드일 때 자동 새로고침 (2초마다)
    if auto_refresh:
        time.sleep(2)  # 2초마다 새로고침
        st.rerun()
