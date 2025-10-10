"""
Log Viewer Page
"""
import streamlit as st
import os
import time
import datetime
import json


def render_running_logs_page():
    """실행 로그 보기 페이지 - 화면 초기화 후 표시"""
    
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
                if (!children[i].classList.contains('log-viewer-content')) {
                    children[i].remove();
                }
            }
        }
    }, 10);
    </script>
    """, unsafe_allow_html=True)
    
    # 로그 뷰어 전용 컨테이너 시작
    st.markdown('<div class="log-viewer-content">', unsafe_allow_html=True)
    
    # 상단에 홈 버튼 추가
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="back_to_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 📋 실행 중인 작업 로그")
    
    show_running_task_logs()
    
    # 로그 뷰어 컨테이너 종료
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 추가 내용 완전 차단
    st.stop()


def show_running_task_logs():
    """실행 중인 작업의 로그 표시 - 개선된 버전"""
    
    # task 파일 확인
    if not os.path.exists("./oma_tasks"):
        st.info("현재 실행 중인 작업이 없습니다.")
        return
    
    task_files = [f for f in os.listdir("./oma_tasks") if f.endswith('.json')]
    if not task_files:
        st.info("현재 실행 중인 작업이 없습니다.")
        return
    
    # 가장 최근 task 파일에서 로그 파일 경로 가져오기
    latest_task_file = f"./oma_tasks/{sorted(task_files)[-1]}"
    try:
        with open(latest_task_file, 'r') as f:
            task_data = json.load(f)
        
        log_file_path = task_data.get('log_file')
        
        # 작업 정보 표시
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.success(f"🔄 **{task_data['title']}**")
        with col2:
            st.caption(f"**Task ID:** {task_data['task_id']}")
        with col3:
            start_time = datetime.datetime.fromisoformat(task_data['start_time'])
            elapsed = datetime.datetime.now() - start_time
            st.caption(f"**실행시간:** {str(elapsed).split('.')[0]}")
        
        if not log_file_path or not os.path.exists(log_file_path):
            st.warning("로그 파일을 찾을 수 없습니다.")
            return
        
        st.caption(f"📄 **로그 파일:** `{log_file_path}`")
        
        # 컨트롤 패널
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            auto_refresh = st.checkbox("🔴 실시간 모드", value=True, key="tail_f_mode")
        with col2:
            if not auto_refresh:
                if st.button("🔄 새로고침", key="manual_refresh", use_container_width=True):
                    st.rerun()
        with col3:
            if st.button("📥 로그 다운로드", key="download_log", use_container_width=True):
                download_log_file(log_file_path, task_data['title'])
        with col4:
            show_full_log = st.checkbox("📜 전체 로그", value=False, key="show_full_log")
        
        # 로그 내용 처리 및 표시
        process_and_display_logs(log_file_path, auto_refresh, show_full_log)
        
        # 실시간 모드일 때만 자동 새로고침
        if auto_refresh:
            handle_auto_refresh()
            
    except Exception as e:
        st.error(f"Task 파일 읽기 오류: {e}")
        st.info("현재 실행 중인 작업이 없습니다.")


def process_and_display_logs(log_file_path, auto_refresh, show_full_log):
    """로그 내용 처리 및 표시"""
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
            new_content = clean_ansi_codes(new_content)
            
            # 기존 로그에 새 내용 추가
            st.session_state.log_content += new_content
            
            # 너무 길어지면 앞부분 잘라내기 (최근 5000줄 정도만 유지)
            lines = st.session_state.log_content.split('\n')
            if len(lines) > 5000:
                st.session_state.log_content = '\n'.join(lines[-5000:])
            
            st.session_state.last_log_size = current_size
    
    # 파일 정보 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("파일 크기", f"{current_size:,} bytes")
    with col2:
        lines_count = len(st.session_state.log_content.split('\n')) if st.session_state.log_content else 0
        st.metric("로그 라인 수", f"{lines_count:,}")
    with col3:
        if auto_refresh:
            st.success("🔴 실시간 업데이트 중")
        else:
            st.info("⏸️ 수동 모드")
    
    # 로그 내용 표시
    display_log_content(auto_refresh, show_full_log)


def display_log_content(auto_refresh, show_full_log):
    """로그 내용 표시"""
    if st.session_state.log_content:
        lines = st.session_state.log_content.split('\n')
        
        if show_full_log or not auto_refresh:
            # 전체 로그 표시
            st.markdown("### 📄 전체 로그")
            st.code(st.session_state.log_content, language=None, height=600)
        else:
            # 실시간 모드일 때는 최신 로그를 강조하기 위해 마지막 몇 줄을 별도 표시
            if len(lines) > 100:
                # 이전 로그 (접을 수 있는 형태)
                with st.expander(f"📜 이전 로그 보기 ({len(lines)-100:,}줄)", expanded=False):
                    old_logs = '\n'.join(lines[:-100])
                    st.code(old_logs, language=None, height=400)
                
                # 최신 로그 (타이틀 없이 바로 표시)
                recent_logs = '\n'.join(lines[-100:])
                st.code(recent_logs, language=None, height=700)
            else:
                # 전체 로그 표시
                st.markdown("### 📄 로그 내용")
                st.code(st.session_state.log_content, language=None, height=700)
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


def clean_ansi_codes(text):
    """ANSI 색상 코드 및 이스케이프 시퀀스 제거"""
    import re
    # ANSI 색상 코드 제거
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    # 커서 제어 시퀀스 제거 ([?25l, [?25h 등)
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    # 기타 ANSI 이스케이프 시퀀스 제거
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    return text


def download_log_file(log_file_path, task_title):
    """로그 파일 다운로드"""
    try:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 파일명 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{task_title}_{timestamp}.log"
            
            st.download_button(
                label="💾 다운로드",
                data=content,
                file_name=filename,
                mime="text/plain",
                key="download_button"
            )
        else:
            st.error("로그 파일을 찾을 수 없습니다.")
    except Exception as e:
        st.error(f"다운로드 오류: {e}")


def handle_auto_refresh():
    """자동 새로고침 처리"""
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
    
    # 실시간 모드에서는 자동 새로고침 (상태 유지하면서)
    time.sleep(2)
    st.rerun()  # selected_action 재설정 제거


def check_and_cleanup_completed_tasks():
    """완료된 작업의 task 파일을 자동 삭제"""
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
