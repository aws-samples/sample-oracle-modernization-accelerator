#!/usr/bin/env python3

"""
postTransCheckSource.py - Oracle Function Transformation Script
현재 위치: /home/ec2-user/workspace/oracle-mod-ax/bin/post-transform
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import signal
import time

def signal_handler(signum, frame):
    """CTRL+C 처리 - 완전히 종료"""
    print("\n\n스크립트가 사용자에 의해 중단되었습니다.")
    sys.exit(130)

# CTRL+C 핸들러 등록
signal.signal(signal.SIGINT, signal_handler)

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    
    # 스크립트 위치 확인
    script_dir = Path(__file__).parent.absolute()
    print(f"스크립트 실행 위치: {script_dir}")
    
    # 필요한 파일 경로 설정
    oracle_functions_file = script_dir / "expression" / "oracle_functions.txt"
    prompt_file = script_dir / "expression" / "postTransCheckSource.md"
    
    # 로그 디렉토리 생성
    app_logs_folder = os.environ.get('APP_LOGS_FOLDER', '/tmp')
    log_dir = Path(app_logs_folder) / "qlogs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # qprompt 폴더 (명령어 히스토리용)
    qprompt_folder = log_dir / "qprompt"
    qprompt_folder.mkdir(parents=True, exist_ok=True)
    
    # 파일 존재 확인
    if not oracle_functions_file.exists():
        print(f"오류: {oracle_functions_file} 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    if not prompt_file.exists():
        print(f"오류: {prompt_file} 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    print(f"Oracle Functions 파일: {oracle_functions_file}")
    print(f"프롬프트 파일: {prompt_file}")
    print(f"로그 디렉토리: {log_dir}")
    
    # oracle_functions.txt 파일 읽기 및 전체 라인 수 계산
    valid_lines = []
    with open(oracle_functions_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # 빈 줄이나 주석 건너뛰기
            if line and not line.startswith('#'):
                valid_lines.append((line_num, line))
    
    total_lines = len(valid_lines)
    print(f"총 처리할 Oracle Function 개수: {total_lines}")
    print("=" * 40)
    
    processed_count = 0
    
    for line_num, line in valid_lines:
        # 각 처리 전 1초 대기
        print("처리 시작 전 1초 대기...")
        time.sleep(1)
        
        processed_count += 1
        
        # 파이프로 분리 (oracle_function|search_pattern)
        parts = line.split('|')
        if len(parts) >= 2:
            oracle_function = parts[0].strip()
            search_pattern = parts[1].strip()
        else:
            oracle_function = parts[0].strip()
            search_pattern = ""
        
        print(f"\n[{processed_count}/{total_lines}] 시작: {oracle_function} (패턴: {search_pattern})")
        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 환경변수 설정
        env = os.environ.copy()
        env['ORACLE_FUNCTION'] = oracle_function
        env['SEARCH_PATTERN'] = search_pattern
        
        # 로그 파일 이름 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_log_file = log_dir / f"{oracle_function}_{timestamp}.log"
        
        # q chat 실행
        print(f"Q Chat 실행 중... -> {batch_log_file}")
        start_time = datetime.now()
        
        cmd = f"q chat --trust-all-tools --no-interactive < {prompt_file} > {batch_log_file}"
        
        # 명령어 히스토리 저장
        cmd_history_file = qprompt_folder / "qchat_command_history.log"
        with open(cmd_history_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {oracle_function} - {cmd}\n")
        
        logger.info(f"Executing batch {oracle_function}: {cmd}")
        
        # 명령어 실행
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            exit_code = result.returncode
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 실행 결과 확인
            if exit_code == 0:
                print(f"✓ 완료: {oracle_function} 처리 성공 (소요시간: {duration:.0f}초)")
                logger.info(f"Q chat execution completed for {oracle_function}")
            else:
                print(f"✗ 오류: {oracle_function} 처리 실패 (종료코드: {exit_code}, 소요시간: {duration:.0f}초)")
                logger.error(f"Q chat execution failed for {oracle_function}: {result.stderr}")
                
                # 오류 로그도 파일에 저장
                if result.stderr:
                    error_log_file = log_dir / f"{oracle_function}_{timestamp}_error.log"
                    with open(error_log_file, 'w', encoding='utf-8') as f:
                        f.write(result.stderr)
            
        except Exception as e:
            print(f"✗ 예외 발생: {oracle_function} 처리 중 오류 - {str(e)}")
            logger.error(f"Exception during Q chat execution for {oracle_function}: {str(e)}")
        
        print(f"로그 파일: {batch_log_file}")
        print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 40)
    
    print(f"\n🎉 모든 Oracle Function 처리 완료!")
    print(f"총 처리된 함수: {processed_count}/{total_lines}")
    print(f"최종 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
