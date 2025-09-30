"""
테스트 및 결과 수정 페이지 - Shell 스타일 웹 터미널
"""
import streamlit as st
import subprocess
import os
import time
import shlex


def render_test_fix_page():
    """테스트 및 결과 수정 페이지 - Shell 스타일 웹 터미널"""
    
    # 화면 완전 초기화
    st.empty()
    
    # CSS 스타일
    st.markdown("""
    <style>
    .main .block-container {
        background: white;
        min-height: 100vh;
    }
    .terminal-container {
        background-color: #000000;
        color: #00ff00;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        padding: 20px;
        border-radius: 8px;
        height: 600px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 14px;
        border: 2px solid #333;
        margin: 10px 0;
    }
    .terminal-input {
        background-color: #1a1a1a;
        color: #00ff00;
        border: 1px solid #333;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 상단 헤더
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 홈으로", key="test_fix_home"):
            cleanup_terminal_session()
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## 🔧 테스트 및 결과 수정 - Shell 터미널")
    
    # 터미널 세션 초기화
    if 'terminal_history' not in st.session_state:
        initialize_terminal()
    
    # 터미널 화면 표시
    display_terminal()
    
    # 명령어 입력
    handle_command_input()
    
    # 자동 스크롤
    st.markdown("""
    <script>
    setTimeout(function() {
        const terminal = document.getElementById('terminal');
        if (terminal) {
            terminal.scrollTop = terminal.scrollHeight;
        }
    }, 100);
    </script>
    """, unsafe_allow_html=True)


def initialize_terminal():
    """터미널 초기화"""
    st.session_state.terminal_history = []
    st.session_state.current_dir = get_working_directory()
    
    # 환경 확인
    tools_folder = os.getenv('APP_TOOLS_FOLDER')
    if tools_folder:
        edit_errors_path = os.path.join(tools_folder, '..', 'postTransform', 'editErrors.md')
        if os.path.exists(edit_errors_path):
            add_to_history("system", f"OMA Shell Terminal - Ready")
            add_to_history("system", f"Working directory: {st.session_state.current_dir}")
            add_to_history("system", f"editErrors.md found: {edit_errors_path}")
            add_to_history("system", "Type 'help' for available commands")
            add_to_history("system", "=" * 60)
        else:
            add_to_history("error", f"editErrors.md not found: {edit_errors_path}")
    else:
        add_to_history("error", "APP_TOOLS_FOLDER environment variable not set")


def display_terminal():
    """터미널 화면 표시"""
    terminal_content = ""
    
    for entry in st.session_state.terminal_history:
        entry_type = entry.get('type', 'output')
        content = entry.get('content', '')
        timestamp = entry.get('timestamp', '')
        
        if entry_type == 'command':
            terminal_content += f'<span style="color: #00ff00;">{get_prompt()} {content}</span>\n'
        elif entry_type == 'output':
            terminal_content += f'<span style="color: #ffffff;">{content}</span>\n'
        elif entry_type == 'error':
            terminal_content += f'<span style="color: #ff4444;">{content}</span>\n'
        elif entry_type == 'system':
            terminal_content += f'<span style="color: #ffaa00;">[{timestamp}] {content}</span>\n'
    
    st.markdown(f"""
    <div class="terminal-container" id="terminal">
{terminal_content}
    </div>
    """, unsafe_allow_html=True)


def handle_command_input():
    """명령어 입력 처리"""
    # 현재 프롬프트 표시
    prompt = get_prompt()
    
    # 입력 폼
    with st.form(key="shell_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            command = st.text_input(
                "Command:", 
                placeholder="Enter shell command...",
                label_visibility="collapsed",
                key="shell_input"
            )
        with col2:
            submit = st.form_submit_button("Execute", type="primary")
    
    # 명령어 실행
    if submit and command.strip():
        execute_shell_command(command.strip())
        st.rerun()


def execute_shell_command(command):
    """Shell 명령어 실행"""
    # 명령어를 히스토리에 추가
    add_to_history("command", command)
    
    try:
        # 내장 명령어 처리
        if handle_builtin_commands(command):
            return
        
        # 일반 shell 명령어 실행
        execute_system_command(command)
        
    except Exception as e:
        add_to_history("error", f"Command execution error: {str(e)}")


def handle_builtin_commands(command):
    """내장 명령어 처리"""
    cmd_parts = shlex.split(command) if command else []
    if not cmd_parts:
        return True
    
    cmd = cmd_parts[0].lower()
    
    # 도움말
    if cmd == 'help':
        show_help()
        return True
    
    # 디렉토리 변경
    elif cmd == 'cd':
        change_directory(cmd_parts[1] if len(cmd_parts) > 1 else os.path.expanduser('~'))
        return True
    
    # 현재 디렉토리
    elif cmd == 'pwd':
        add_to_history("output", st.session_state.current_dir)
        return True
    
    # 화면 지우기
    elif cmd in ['clear', 'cls']:
        st.session_state.terminal_history = []
        add_to_history("system", "Terminal cleared")
        return True
    
    # 종료
    elif cmd in ['exit', 'quit']:
        add_to_history("system", "Exiting terminal...")
        st.session_state.selected_action = None
        return True
    
    # Q Chat 실행
    elif cmd == 'qchat' or command.startswith('q chat'):
        execute_qchat_command(command)
        return True
    
    # 환경변수 표시
    elif cmd == 'env':
        show_environment()
        return True
    
    return False


def execute_system_command(command):
    """시스템 명령어 실행"""
    try:
        # 환경변수 설정
        env = dict(os.environ)
        if os.getenv('APP_TOOLS_FOLDER'):
            env['APP_TOOLS_FOLDER'] = os.getenv('APP_TOOLS_FOLDER')
        
        # 명령어 실행
        result = subprocess.run(
            command,
            shell=True,
            cwd=st.session_state.current_dir,
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        
        # 출력 표시
        if result.stdout:
            add_to_history("output", result.stdout.strip())
        
        if result.stderr:
            add_to_history("error", result.stderr.strip())
        
        if result.returncode != 0:
            add_to_history("error", f"Command failed with exit code: {result.returncode}")
    
    except subprocess.TimeoutExpired:
        add_to_history("error", "Command timed out (60 seconds)")
    except Exception as e:
        add_to_history("error", f"Execution error: {str(e)}")


def execute_qchat_command(command):
    """Q Chat 명령어 실행"""
    try:
        tools_folder = os.getenv('APP_TOOLS_FOLDER')
        if not tools_folder:
            add_to_history("error", "APP_TOOLS_FOLDER environment variable not set")
            return
        
        edit_errors_path = os.path.join(tools_folder, '..', 'postTransform', 'editErrors.md')
        
        if not os.path.exists(edit_errors_path):
            add_to_history("error", f"editErrors.md not found: {edit_errors_path}")
            return
        
        # Q Chat 명령어 구성
        if command == 'qchat':
            qchat_cmd = f'q chat --trust-all-tools "{edit_errors_path}"'
        else:
            qchat_cmd = command.replace('q chat', f'q chat --trust-all-tools "{edit_errors_path}"', 1)
        
        add_to_history("system", f"Executing: {qchat_cmd}")
        add_to_history("system", "Starting Q Chat session...")
        
        # 환경변수 설정
        env = dict(os.environ)
        env['APP_TOOLS_FOLDER'] = tools_folder
        
        # Q Chat 실행
        result = subprocess.run(
            qchat_cmd,
            shell=True,
            cwd=st.session_state.current_dir,
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        
        # 결과 출력
        if result.stdout:
            add_to_history("output", result.stdout.strip())
        
        if result.stderr:
            add_to_history("error", result.stderr.strip())
        
        if result.returncode == 0:
            add_to_history("system", "Q Chat session completed")
        else:
            add_to_history("error", f"Q Chat failed with exit code: {result.returncode}")
    
    except subprocess.TimeoutExpired:
        add_to_history("error", "Q Chat timed out (120 seconds)")
    except Exception as e:
        add_to_history("error", f"Q Chat execution error: {str(e)}")


def change_directory(path):
    """디렉토리 변경"""
    try:
        if path == '..':
            new_dir = os.path.dirname(st.session_state.current_dir)
        elif path.startswith('/'):
            new_dir = path
        elif path.startswith('~'):
            new_dir = os.path.expanduser(path)
        else:
            new_dir = os.path.join(st.session_state.current_dir, path)
        
        if os.path.exists(new_dir) and os.path.isdir(new_dir):
            st.session_state.current_dir = os.path.abspath(new_dir)
            add_to_history("output", f"Changed directory to: {st.session_state.current_dir}")
        else:
            add_to_history("error", f"Directory not found: {path}")
    
    except Exception as e:
        add_to_history("error", f"Directory change error: {str(e)}")


def show_help():
    """도움말 표시"""
    help_text = """
Available commands:
  help          - Show this help message
  cd <dir>      - Change directory
  pwd           - Show current directory
  ls [options]  - List directory contents
  clear/cls     - Clear terminal
  env           - Show environment variables
  qchat         - Start Q Chat with editErrors.md
  q chat <args> - Run Q Chat with custom arguments
  exit/quit     - Exit terminal
  
Any other command will be executed as a shell command.
"""
    add_to_history("output", help_text)


def show_environment():
    """환경변수 표시"""
    env_info = f"""
OMA Environment Variables:
  OMA_BASE_DIR: {os.getenv('OMA_BASE_DIR', 'Not set')}
  APP_TOOLS_FOLDER: {os.getenv('APP_TOOLS_FOLDER', 'Not set')}
  APPLICATION_NAME: {os.getenv('APPLICATION_NAME', 'Not set')}
  
Current Directory: {st.session_state.current_dir}
"""
    add_to_history("output", env_info)


def get_working_directory():
    """작업 디렉토리 가져오기"""
    oma_base = os.getenv('OMA_BASE_DIR')
    if oma_base:
        return os.path.join(oma_base, 'bin')
    return os.path.expanduser('~/workspace/oma/bin')


def get_prompt():
    """프롬프트 문자열 생성"""
    user = os.getenv('USER', 'user')
    hostname = os.getenv('HOSTNAME', 'localhost')
    current_dir = os.path.basename(st.session_state.current_dir)
    return f"{user}@{hostname}:{current_dir}$"


def add_to_history(entry_type, content):
    """터미널 히스토리에 추가"""
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.terminal_history.append({
        'type': entry_type,
        'content': content,
        'timestamp': timestamp
    })


def cleanup_terminal_session():
    """터미널 세션 정리"""
    if 'terminal_history' in st.session_state:
        del st.session_state.terminal_history
    if 'current_dir' in st.session_state:
        del st.session_state.current_dir
