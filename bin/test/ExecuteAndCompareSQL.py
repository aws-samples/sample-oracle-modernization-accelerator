#!/usr/bin/env python3
#############################################################################
# Script: DB09.ExecuteAndCompareSQL.py
# Description: This script executes SQL statements from the sqllist table
#              in both Oracle and PostgreSQL databases and compares the results.
#
# Functionality:
# - Reads SQL statements from the sqllist table
# - Executes each SQL in both Oracle and PostgreSQL
# - Compares the results and updates the sqllist table
# - Generates comprehensive reports and logs
# - Manages temporary files systematically
#
# Usage:
#   python3 DB09.ExecuteAndCompareSQL.py [options]
#
# Options:
#   -t, --type TYPE     SQL statement type to execute (S: Select, I: Insert, U: Update, D: Delete, P: PL/SQL Block, O: Other)
#                       Multiple types can be specified with commas (e.g., S,U,I)
#############################################################################

import os
import sys
import subprocess
import tempfile
import csv
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import argparse
import logging
import shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_environment_variables():
    """
    환경 변수가 설정되어 있는지 확인합니다.
    """
    print("=" * 60)
    print("환경 변수 확인 중...")
    print("=" * 60)
    
    # TARGET_DBMS_TYPE 확인
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    print(f"타겟 DBMS 타입: {target_dbms}")
    
    # 필수 환경 변수 목록 (소스는 항상 Oracle, 타겟은 TARGET_DBMS_TYPE에 따라)
    required_env_vars = [
        'ORACLE_SVC_USER',
        'ORACLE_SVC_PASSWORD',
        'ORACLE_SVC_CONNECT_STRING'
    ]
    
    # 타겟 DBMS에 따른 환경 변수 추가
    if target_dbms in ['postgres', 'postgresql']:
        required_env_vars.extend([
            'PGHOST',
            'PGPORT', 
            'PGDATABASE',
            'PGUSER',
            'PGPASSWORD'
        ])
    elif target_dbms == 'mysql':
        required_env_vars.extend([
            'MYSQL_HOST',
            'MYSQL_PORT',
            'MYSQL_DATABASE',
            'MYSQL_USER',
            'MYSQL_PASSWORD'
        ])
    else:
        print(f"지원하지 않는 타겟 DBMS 타입: {target_dbms}")
        print("지원되는 타입: postgres, postgresql, mysql")
        sys.exit(1)
    
    # 권장 환경 변수 목록
    recommended_env_vars = [
        'TEST_FOLDER',
        'TEST_LOGS_FOLDER',
        'TARGET_DBMS_TYPE'
    ]
    
    # 선택적 환경 변수 목록
    optional_env_vars = [
        'SQL_BATCH_SIZE',
        'SQL_PARALLEL_EXECUTION',
        'SQL_MAX_WORKERS',
        'SQL_TEMP_CLEANUP',
        'SQL_ARCHIVE_DAYS'
    ]
    
    missing_vars = []
    
    print("필수 환경 변수 확인:")
    for var in required_env_vars:
        value = os.environ.get(var)
        if value:
            # 비밀번호는 마스킹하여 표시
            if 'PASSWORD' in var:
                print(f"✓ {var}: {'*' * len(value)}")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: 설정되지 않음")
            missing_vars.append(var)
    
    print("\n권장 환경 변수 확인:")
    for var in recommended_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            if var == 'TEST_FOLDER':
                print(f"- {var}: 설정되지 않음 (기본값: 현재 작업 디렉토리)")
            elif var == 'TEST_LOGS_FOLDER':
                print(f"- {var}: 설정되지 않음 (기본값: TEST_FOLDER)")
            elif var == 'TARGET_DBMS_TYPE':
                print(f"- {var}: 설정되지 않음 (기본값: postgres)")
    
    print("\n선택적 환경 변수 확인:")
    for var in optional_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            defaults = {
                'SQL_BATCH_SIZE': '10',
                'SQL_PARALLEL_EXECUTION': 'false',
                'SQL_MAX_WORKERS': '4',
                'SQL_TEMP_CLEANUP': 'true',
                'SQL_ARCHIVE_DAYS': '7'
            }
            print(f"- {var}: 설정되지 않음 (기본값: {defaults.get(var, 'N/A')})")
    
    if missing_vars:
        print(f"\n오류: 다음 필수 환경 변수들이 설정되지 않았습니다:")
        for var in missing_vars:
            print(f"  export {var}=<값>")
        print("\n환경 변수를 설정한 후 다시 실행하세요.")
        sys.exit(1)
    
    print("\n환경 변수 확인 완료.")
    print("=" * 60)

# 환경변수 기반 경로 설정
def get_paths():
    """환경변수를 기반으로 경로들을 반환합니다."""
    test_folder = os.environ.get('TEST_FOLDER', os.getcwd())
    test_logs_folder = os.environ.get('TEST_LOGS_FOLDER', test_folder)
    
    return {
        'sql_results_dir': os.path.join(test_folder, 'sql_results'),
        'csv_dir': os.path.join(test_folder, 'sql_results', 'csv'),
        'summary_dir': os.path.join(test_folder, 'sql_results', 'summary'),
        'temp_dir': os.path.join(test_folder, 'sql_results', 'temp'),
        'src_temp_dir': os.path.join(test_folder, 'sql_results', 'temp', 'src'),
        'tgt_temp_dir': os.path.join(test_folder, 'sql_results', 'temp', 'tgt'),
        'cleanup_dir': os.path.join(test_folder, 'sql_results', 'temp', 'cleanup'),
        'archive_dir': os.path.join(test_folder, 'sql_results', 'archive'),
        'logs_dir': test_logs_folder
    }

# 로깅 설정
def setup_logging():
    """로깅을 설정합니다."""
    paths = get_paths()
    logs_dir = paths['logs_dir']
    
    # 로그 디렉토리 생성
    os.makedirs(logs_dir, exist_ok=True)
    
    # 로그 파일 경로들
    main_log = os.path.join(logs_dir, 'execute_and_compare_sql.log')
    debug_log = os.path.join(logs_dir, 'execute_and_compare_sql_debug.log')
    error_log = os.path.join(logs_dir, 'sql_execution_errors.log')
    perf_log = os.path.join(logs_dir, 'performance_metrics.log')
    
    # 메인 로거 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(main_log, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # 디버그 로거 설정
    debug_logger = logging.getLogger('debug')
    debug_handler = logging.FileHandler(debug_log, encoding='utf-8')
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(logging.Formatter('%(asctime)s - DEBUG - %(message)s'))
    debug_logger.addHandler(debug_handler)
    debug_logger.setLevel(logging.DEBUG)
    
    # 오류 로거 설정
    error_logger = logging.getLogger('error')
    error_handler = logging.FileHandler(error_log, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter('%(asctime)s - ERROR - %(message)s'))
    error_logger.addHandler(error_handler)
    error_logger.setLevel(logging.ERROR)
    
    # 성능 로거 설정
    perf_logger = logging.getLogger('performance')
    perf_handler = logging.FileHandler(perf_log, encoding='utf-8')
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(logging.Formatter('%(asctime)s - PERF - %(message)s'))
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    
    logger.info("=" * 60)
    logger.info("ExecuteAndCompareSQL 실행 시작")
    logger.info("=" * 60)
    
    return logger

def setup_directories():
    """필요한 디렉토리들을 생성합니다."""
    paths = get_paths()
    
    directories = [
        paths['sql_results_dir'],
        paths['csv_dir'],
        paths['summary_dir'],
        paths['temp_dir'],
        paths['src_temp_dir'],
        paths['tgt_temp_dir'],
        paths['cleanup_dir'],
        paths['archive_dir']
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"디렉토리 확인/생성: {directory}")
    
    logger.info("디렉토리 구조 설정 완료")

# SQL 문 타입 매핑
STMT_TYPES = {
    'S': 'Select',
    'I': 'Insert',
    'U': 'Update',
    'D': 'Delete',
    'P': 'PL/SQL Block',
    'O': 'Other'
}

def save_timeout_list(timeout_sqls, db_type='src'):
    """타임아웃 발생한 SQL 목록을 파일에 저장합니다."""
    if not timeout_sqls:
        return
    
    paths = get_paths()
    if db_type == 'src':
        timeout_file = os.path.join(paths['sql_results_dir'], 'timeout_src.lst')
        db_name = '소스'
    else:
        timeout_file = os.path.join(paths['sql_results_dir'], 'timeout_tgt.lst')
        db_name = '타겟'
    
    try:
        with open(timeout_file, 'w', encoding='utf-8') as f:
            f.write(f"# {db_name} SQL 타임아웃 목록\n")
            f.write(f"# 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 총 {len(timeout_sqls)}개 SQL이 타임아웃되었습니다.\n")
            f.write("# 형식: SQL_ID|APP_NAME|STMT_TYPE|FILE_PATH\n")
            f.write("#" + "="*60 + "\n")
            
            for sql_info in timeout_sqls:
                f.write(f"{sql_info['sql_id']}|{sql_info['app_name']}|{sql_info['stmt_type']}|{sql_info['file_path']}\n")
        
        logger.info(f"{db_name} 타임아웃 목록 저장: {timeout_file} ({len(timeout_sqls)}개)")
        
    except Exception as e:
        logger.error(f"{db_name} 타임아웃 목록 저장 실패: {str(e)}")

def cleanup_temp_files(temp_files):
    """임시 파일들을 정리합니다."""
    paths = get_paths()
    cleanup_dir = paths['cleanup_dir']
    
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                logger.debug(f"임시 파일 삭제: {temp_file}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {temp_file} - {e}")
            # 삭제 실패한 파일을 cleanup 디렉토리로 이동
            try:
                filename = os.path.basename(temp_file)
                cleanup_path = os.path.join(cleanup_dir, f"failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
                shutil.move(temp_file, cleanup_path)
                logger.info(f"삭제 실패 파일을 cleanup 디렉토리로 이동: {cleanup_path}")
            except Exception as move_error:
                logger.error(f"cleanup 디렉토리 이동도 실패: {temp_file} - {move_error}")
def execute_oracle_sql(sql_id, sql):
    """
    Oracle에서 SQL을 실행하고 결과를 반환합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    debug_logger = logging.getLogger('debug')
    error_logger = logging.getLogger('error')
    perf_logger = logging.getLogger('performance')
    
    start_time = time.time()
    logger.info(f"Oracle SQL 실행 시작: {sql_id}")
    debug_logger.debug(f"Oracle SQL 내용: {sql[:200]}...")
    
    # 환경 변수에서 Oracle 연결 정보 가져오기
    oracle_user = os.environ.get('ORACLE_SVC_USER')
    oracle_password = os.environ.get('ORACLE_SVC_PASSWORD')
    oracle_connect_string = os.environ.get('ORACLE_SVC_CONNECT_STRING')
    
    if not all([oracle_user, oracle_password, oracle_connect_string]):
        error_msg = "Oracle 연결 정보가 환경 변수에 설정되어 있지 않습니다."
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    
    # SQL 문 정리
    sql = sql.strip()
    
    # Oracle PL/SQL 블록 종료 문자 '/' 제거 (줄의 시작에 있는 경우만)
    # 주석의 일부인 '*/' 는 제거하지 않음
    lines = sql.split('\n')
    if lines and lines[-1].strip() == '/':
        lines = lines[:-1]
        sql = '\n'.join(lines).strip()
    
    paths = get_paths()
    src_temp_dir = paths['src_temp_dir']
    
    # 임시 파일 경로 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_sql_path = os.path.join(src_temp_dir, f"temp_sql_{sql_id}_{timestamp}.sql")
    temp_result_path = f"{temp_sql_path}_result.csv"
    
    temp_files = [temp_sql_path, temp_result_path]
    
    try:
        # 임시 SQL 파일 생성
        with open(temp_sql_path, 'w', encoding='utf-8') as temp_sql:
            # 결과를 CSV 형식으로 출력하는 설정 추가
            temp_sql.write("SET PAGESIZE 0\n")
            temp_sql.write("SET HEADING OFF\n")
            temp_sql.write("SET FEEDBACK OFF\n")
            temp_sql.write("SET ECHO OFF\n")
            temp_sql.write("SET TERMOUT OFF\n")
            temp_sql.write("SET TRIMSPOOL ON\n")
            temp_sql.write("SET LINESIZE 32767\n")
            temp_sql.write("SET LONG 1000000\n")
            temp_sql.write("SET LONGCHUNKSIZE 1000000\n")
            temp_sql.write("SET WRAP OFF\n")
            temp_sql.write("SET MARKUP CSV ON QUOTE OFF\n")
            temp_sql.write("SET TIMING OFF\n")
            temp_sql.write("SET SQLPROMPT ''\n")
            temp_sql.write("ALTER SESSION SET NLS_LANGUAGE = 'KOREAN';\n")
            temp_sql.write("ALTER SESSION SET NLS_TERRITORY = 'KOREA';\n")
            temp_sql.write("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS';\n")
            temp_sql.write("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF';\n")
            temp_sql.write(f"SPOOL {temp_result_path}\n")
            
            # 실행할 SQL 추가 - 구문 종료 처리 개선
            sql_trimmed = sql.strip()
            
            # 이미 세미콜론이나 슬래시로 끝나는지 확인
            if not sql_trimmed.endswith(';') and not sql_trimmed.endswith('/'):
                # PL/SQL 블록인지 확인 (BEGIN, DECLARE, CREATE OR REPLACE 등으로 시작)
                sql_upper = sql_trimmed.upper()
                if (sql_upper.startswith('BEGIN') or 
                    sql_upper.startswith('DECLARE') or 
                    'CREATE OR REPLACE' in sql_upper or
                    sql_upper.startswith('CREATE FUNCTION') or
                    sql_upper.startswith('CREATE PROCEDURE')):
                    temp_sql.write(f"{sql_trimmed}\n/\n")
                else:
                    temp_sql.write(f"{sql_trimmed};\n")
            else:
                # 이미 종료 문자가 있으면 그대로 사용
                temp_sql.write(f"{sql_trimmed}\n")
            
            temp_sql.write("SPOOL OFF\n")
            temp_sql.write("EXIT;\n")
        
        debug_logger.debug(f"Oracle 임시 SQL 파일 생성: {temp_sql_path}")
        
        # Oracle SQL 실행 - 한글 인코딩 설정
        env = os.environ.copy()
        env['NLS_LANG'] = 'KOREAN_KOREA.AL32UTF8'
        
        # sqlplus 명령어 - 표준 방식으로 복원하되 출력 처리 개선
        cmd = f"sqlplus -S {oracle_user}/{oracle_password}@{oracle_connect_string} @{temp_sql_path}"
        
        debug_logger.debug(f"Oracle 실행 명령어: {cmd}")
        
        # subprocess 실행 - stdout을 파일로 리다이렉트하지 않고 무시
        with open(os.devnull, 'w') as devnull:
            process = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, 
                                   stdout=devnull, env=env, timeout=10)
        
        execution_time = time.time() - start_time
        perf_logger.info(f"Oracle SQL 실행 시간: {sql_id} - {execution_time:.2f}초")
        
        if process.returncode != 0:
            error_msg = process.stderr.decode('utf-8', errors='replace')
            error_logger.error(f"Oracle SQL 실행 오류: {sql_id} - {error_msg}")
            return f"ERROR: {error_msg}"
        
        # 결과 파일 읽기
        if os.path.exists(temp_result_path):
            with open(temp_result_path, 'r', encoding='utf-8', errors='replace') as f:
                result = f.read().strip()
                
            # ORA- 오류가 있는지 확인
            lines = result.split('\n')
            for line in lines:
                if line.strip().startswith('ORA-'):
                    error_logger.error(f"Oracle SQL 오류: {sql_id} - {line.strip()}")
                    return line.strip()
            
            logger.info(f"Oracle SQL 실행 성공: {sql_id}")
            debug_logger.debug(f"Oracle 결과 길이: {len(result)} 문자")
            return result
        else:
            error_msg = f"Oracle SQL 결과 파일이 생성되지 않았습니다: {temp_result_path}"
            error_logger.error(f"{sql_id}: {error_msg}")
            return f"ERROR: {error_msg}"
            
    except subprocess.TimeoutExpired:
        error_msg = "Oracle SQL 실행 타임아웃 (10초 초과)"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"TIMEOUT: {error_msg}"
    except Exception as e:
        error_msg = f"Oracle SQL 실행 중 예외 발생: {str(e)}"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    finally:
        # 임시 파일 정리
        cleanup_temp_files(temp_files)

def execute_target_sql(sql_id, sql):
    """
    TARGET_DBMS_TYPE에 따라 타겟 데이터베이스에서 SQL을 실행하고 결과를 반환합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    debug_logger = logging.getLogger('debug')
    error_logger = logging.getLogger('error')
    perf_logger = logging.getLogger('performance')
    
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    start_time = time.time()
    logger.info(f"타겟 {target_dbms.upper()} SQL 실행 시작: {sql_id}")
    debug_logger.debug(f"타겟 {target_dbms.upper()} SQL 내용: {sql[:200]}...")
    
    # SQL 문 정리
    sql = sql.strip()
    
    # Oracle PL/SQL 블록 종료 문자 '/' 제거 (줄의 시작에 있는 경우만)
    lines = sql.split('\n')
    if lines and lines[-1].strip() == '/':
        lines = lines[:-1]
        sql = '\n'.join(lines).strip()
    
    paths = get_paths()
    tgt_temp_dir = paths['tgt_temp_dir']
    
    # 임시 파일 경로 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_sql_path = os.path.join(tgt_temp_dir, f"temp_sql_{sql_id}_{timestamp}.sql")
    
    temp_files = [temp_sql_path]
    
    try:
        if target_dbms in ['postgres', 'postgresql']:
            return execute_postgresql_sql(sql_id, sql, temp_sql_path, temp_files)
        elif target_dbms == 'mysql':
            return execute_mysql_sql(sql_id, sql, temp_sql_path, temp_files)
        else:
            error_msg = f"지원하지 않는 타겟 DBMS 타입: {target_dbms}"
            error_logger.error(f"{sql_id}: {error_msg}")
            return f"ERROR: {error_msg}"
            
    except Exception as e:
        error_msg = f"타겟 {target_dbms.upper()} SQL 실행 중 예외 발생: {str(e)}"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    finally:
        # 임시 파일 정리
        cleanup_temp_files(temp_files)

def execute_postgresql_sql(sql_id, sql, temp_sql_path, temp_files):
    """PostgreSQL에서 SQL을 실행합니다."""
    debug_logger = logging.getLogger('debug')
    error_logger = logging.getLogger('error')
    perf_logger = logging.getLogger('performance')
    
    start_time = time.time()
    
    # 환경 변수에서 PostgreSQL 연결 정보 가져오기
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('PGPASSWORD')
    pg_host = os.environ.get('PGHOST')
    pg_port = os.environ.get('PGPORT')
    pg_database = os.environ.get('PGDATABASE')
    
    if not all([pg_user, pg_password, pg_host, pg_port, pg_database]):
        error_msg = "PostgreSQL 연결 정보가 환경 변수에 설정되어 있지 않습니다."
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    
    # SQL 문 끝에 세미콜론이 없으면 추가
    if not sql.endswith(';'):
        sql = sql + ';'
    
    try:
        # 임시 SQL 파일 생성
        with open(temp_sql_path, 'w', encoding='utf-8', newline='\n') as temp_sql:
            # 결과를 CSV 형식으로 출력하는 설정 추가
            temp_sql.write("\\set QUIET on\n")
            temp_sql.write("\\pset tuples_only on\n")
            temp_sql.write("\\pset format unaligned\n")
            temp_sql.write("\\pset fieldsep ','\n")
            temp_sql.write("\\pset footer off\n")
            temp_sql.write("\\pset pager off\n")
            
            # 실행할 SQL 추가 (세미콜론은 이미 추가됨)
            temp_sql.write(f"{sql}\n")
            temp_sql.write("\\q\n")
        
        debug_logger.debug(f"PostgreSQL 임시 SQL 파일 생성: {temp_sql_path}")
        
        # PostgreSQL SQL 실행
        env = os.environ.copy()
        cmd = f"psql -h {pg_host} -p {pg_port} -d {pg_database} -U {pg_user} -f {temp_sql_path}"
        
        process = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, 
                               stdout=subprocess.PIPE, env=env, timeout=10)
        
        execution_time = time.time() - start_time
        perf_logger.info(f"PostgreSQL SQL 실행 시간: {sql_id} - {execution_time:.2f}초")
        
        # stdout과 stderr 모두 확인
        stdout_result = process.stdout.decode('utf-8', errors='replace').strip()
        stderr_result = process.stderr.decode('utf-8', errors='replace').strip()
        
        # stderr에 오류가 있는 경우
        if stderr_result and ('ERROR:' in stderr_result or 'FATAL:' in stderr_result):
            error_logger.error(f"PostgreSQL SQL 실행 오류 (stderr): {sql_id} - {stderr_result}")
            return f"ERROR: {stderr_result}"
        
        # stdout에 오류가 있는 경우 (psql은 SQL 오류를 stdout에 출력)
        if 'ERROR:' in stdout_result or 'FATAL:' in stdout_result:
            error_lines = [line for line in stdout_result.split('\n') if 'ERROR:' in line or 'FATAL:' in line]
            if error_lines:
                error_msg = error_lines[0]
                error_logger.error(f"PostgreSQL SQL 오류 (stdout): {sql_id} - {error_msg}")
                return f"ERROR: {error_msg}"
        
        # return code가 0이 아닌 경우
        if process.returncode != 0:
            error_msg = stderr_result if stderr_result else f"Process returned {process.returncode}"
            error_logger.error(f"PostgreSQL SQL 실행 오류 (returncode): {sql_id} - {error_msg}")
            return f"ERROR: {error_msg}"
        
        result = stdout_result
        
        logger.info(f"PostgreSQL SQL 실행 성공: {sql_id}")
        debug_logger.debug(f"PostgreSQL 결과 길이: {len(result)} 문자")
        return result
        
    except subprocess.TimeoutExpired:
        error_msg = "PostgreSQL SQL 실행 타임아웃 (10초 초과)"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"TIMEOUT: {error_msg}"

def execute_mysql_sql(sql_id, sql, temp_sql_path, temp_files):
    """MySQL에서 SQL을 실행합니다."""
    debug_logger = logging.getLogger('debug')
    error_logger = logging.getLogger('error')
    perf_logger = logging.getLogger('performance')
    
    start_time = time.time()
    
    # 환경 변수에서 MySQL 연결 정보 가져오기
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_port = os.environ.get('MYSQL_PORT')
    mysql_database = os.environ.get('MYSQL_DATABASE')
    
    if not all([mysql_user, mysql_password, mysql_host, mysql_port, mysql_database]):
        error_msg = "MySQL 연결 정보가 환경 변수에 설정되어 있지 않습니다."
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    
    # SQL 문 정리 (세미콜론 제거)
    sql = sql.strip()
    if sql.endswith(';'):
        sql = sql[:-1]
    
    # CSV 출력 파일 경로 생성
    paths = get_paths()
    tgt_temp_dir = paths['tgt_temp_dir']
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    csv_output_path = os.path.join(tgt_temp_dir, f"mysql_result_{sql_id}_{timestamp}.csv")
    temp_files.append(csv_output_path)
    
    try:
        # SELECT ... INTO OUTFILE을 사용한 CSV 출력 SQL 생성
        csv_sql = f"""
{sql}
INTO OUTFILE '{csv_output_path}'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
ESCAPED BY '\\\\'
LINES TERMINATED BY '\\n';
"""
        
        # 임시 SQL 파일 생성
        with open(temp_sql_path, 'w', encoding='utf-8', newline='\n') as temp_sql:
            temp_sql.write(csv_sql)
        
        debug_logger.debug(f"MySQL 임시 SQL 파일 생성: {temp_sql_path}")
        debug_logger.debug(f"MySQL CSV 출력 파일: {csv_output_path}")
        
        # MySQL SQL 실행
        env = os.environ.copy()
        cmd = f"mysql -h {mysql_host} -P {mysql_port} -u {mysql_user} -p{mysql_password} -D {mysql_database} < {temp_sql_path}"
        
        process = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, 
                               stdout=subprocess.PIPE, env=env, timeout=10)
        
        execution_time = time.time() - start_time
        perf_logger.info(f"MySQL SQL 실행 시간: {sql_id} - {execution_time:.2f}초")
        
        # stderr 확인
        stderr_result = process.stderr.decode('utf-8', errors='replace').strip()
        
        # stderr에 오류가 있는 경우
        if stderr_result and ('ERROR' in stderr_result or 'FATAL' in stderr_result):
            error_logger.error(f"MySQL SQL 실행 오류 (stderr): {sql_id} - {stderr_result}")
            return f"ERROR: {stderr_result}"
        
        # return code가 0이 아닌 경우
        if process.returncode != 0:
            error_msg = stderr_result if stderr_result else f"Process returned {process.returncode}"
            error_logger.error(f"MySQL SQL 실행 오류 (returncode): {sql_id} - {error_msg}")
            return f"ERROR: {error_msg}"
        
        # CSV 파일에서 결과 읽기
        if os.path.exists(csv_output_path):
            with open(csv_output_path, 'r', encoding='utf-8', errors='replace') as f:
                result = f.read().strip()
            
            logger.info(f"MySQL SQL 실행 성공: {sql_id}")
            debug_logger.debug(f"MySQL 결과 길이: {len(result)} 문자")
            return result
        else:
            error_msg = f"MySQL CSV 출력 파일이 생성되지 않았습니다: {csv_output_path}"
            error_logger.error(f"{sql_id}: {error_msg}")
            return f"ERROR: {error_msg}"
        
    except subprocess.TimeoutExpired:
        error_msg = "MySQL SQL 실행 타임아웃 (10초 초과)"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"TIMEOUT: {error_msg}"
    except Exception as e:
        error_msg = f"MySQL SQL 실행 중 예외 발생: {str(e)}"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
def update_results(conn, sql_id, app_name, stmt_type, src_result, tgt_result):
    """
    sqllist 테이블에 실행 결과를 업데이트합니다.
    """
    try:
        # 결과 비교
        same = 'Y' if src_result == tgt_result else 'N'
        
        # 오류가 있는 경우 무조건 다름으로 처리
        if src_result.startswith("ERROR:") or tgt_result.startswith("ERROR:"):
            same = 'N'
        
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE sqllist 
                SET src_result = %s, tgt_result = %s, same = %s
                WHERE sql_id = %s AND app_name = %s AND stmt_type = %s
                """,
                (src_result, tgt_result, same, sql_id, app_name, stmt_type)
            )
        
        logger.debug(f"결과 업데이트 완료: {sql_id} - 동일: {same}")
        return True, same
    except Exception as e:
        logger.error(f"결과 업데이트 중 오류 발생: {sql_id} - {str(e)}")
        conn.rollback()
        return False, 'N'

def update_tgt_only_results(conn, sql_id, app_name, stmt_type, tgt_result):
    """
    타겟 전용 모드에서 sqllist 테이블에 타겟 결과만 업데이트합니다.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE sqllist 
                SET tgt_result = %s
                WHERE sql_id = %s AND app_name = %s AND stmt_type = %s
                """,
                (tgt_result, sql_id, app_name, stmt_type)
            )
        
        logger.debug(f"타겟 결과 업데이트 완료: {sql_id}")
        return True, 'N/A'
    except Exception as e:
        logger.error(f"타겟 결과 업데이트 중 오류 발생: {sql_id} - {str(e)}")
        conn.rollback()
        return False, 'N/A'

def update_src_only_results(conn, sql_id, app_name, stmt_type, src_result):
    """
    소스 전용 모드에서 sqllist 테이블에 소스 결과만 업데이트합니다.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE sqllist 
                SET src_result = %s
                WHERE sql_id = %s AND app_name = %s AND stmt_type = %s
                """,
                (src_result, sql_id, app_name, stmt_type)
            )
        
        logger.debug(f"소스 결과 업데이트 완료: {sql_id}")
        return True, 'N/A'
    except Exception as e:
        logger.error(f"소스 결과 업데이트 중 오류 발생: {sql_id} - {str(e)}")
        conn.rollback()
        return False, 'N/A'

def generate_summary_report(results, execution_time, type_filter=None, src_only=False, tgt_only=False):
    """실행 요약 보고서를 생성합니다."""
    paths = get_paths()
    summary_dir = paths['summary_dir']
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').upper()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    type_suffix = f"_{type_filter.replace(',', '')}" if type_filter else ""
    db_suffix = ""
    if src_only:
        db_suffix = "_src_only"
    elif tgt_only:
        db_suffix = "_tgt_only"
    
    # 텍스트 요약 보고서
    summary_file = os.path.join(summary_dir, f"execution_summary{type_suffix}{db_suffix}_{timestamp}.txt")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        if src_only:
            f.write("소스 SQL 실행 요약 보고서\n")
        elif tgt_only:
            f.write(f"타겟 {target_dbms} SQL 실행 요약 보고서\n")
        else:
            f.write(f"SQL 실행 및 비교 요약 보고서 (타겟: {target_dbms})\n")
        f.write("=" * 60 + "\n")
        f.write(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"총 소요 시간: {execution_time:.2f}초\n")
        f.write(f"총 실행 SQL 수: {len(results)}\n")
        if type_filter:
            f.write(f"필터링된 타입: {type_filter}\n")
        if src_only:
            f.write("실행 모드: 소스 전용\n")
        elif tgt_only:
            f.write(f"실행 모드: 타겟 {target_dbms} 전용\n")
        f.write("\n")
        
        # 성공/실패 통계
        f.write("실행 결과 통계:\n")
        f.write("-" * 30 + "\n")
        
        if not tgt_only:
            src_success = sum(1 for r in results if r.get('src_status') == 'SUCCESS')
            src_timeout = sum(1 for r in results if r.get('src_status') == 'TIMEOUT')
            src_error = sum(1 for r in results if r.get('src_status') == 'ERROR')
            
            f.write(f"소스 성공: {src_success}/{len(results)} ({src_success/len(results)*100:.1f}%)\n")
            f.write(f"소스 타임아웃: {src_timeout}/{len(results)} ({src_timeout/len(results)*100:.1f}%)\n")
            f.write(f"소스 오류: {src_error}/{len(results)} ({src_error/len(results)*100:.1f}%)\n")
        
        if not src_only:
            tgt_success = sum(1 for r in results if r.get('tgt_status') == 'SUCCESS')
            tgt_timeout = sum(1 for r in results if r.get('tgt_status') == 'TIMEOUT')
            tgt_error = sum(1 for r in results if r.get('tgt_status') == 'ERROR')
            
            f.write(f"타겟 {target_dbms} 성공: {tgt_success}/{len(results)} ({tgt_success/len(results)*100:.1f}%)\n")
            f.write(f"타겟 {target_dbms} 타임아웃: {tgt_timeout}/{len(results)} ({tgt_timeout/len(results)*100:.1f}%)\n")
            f.write(f"타겟 {target_dbms} 오류: {tgt_error}/{len(results)} ({tgt_error/len(results)*100:.1f}%)\n")
        
        if not src_only and not tgt_only:
            same_results = sum(1 for r in results if r.get('same') == 'Y')
            both_success = sum(1 for r in results if r.get('src_status') == 'SUCCESS' and r.get('tgt_status') == 'SUCCESS')
            f.write(f"양쪽 모두 성공: {both_success}/{len(results)} ({both_success/len(results)*100:.1f}%)\n")
            f.write(f"결과 일치: {same_results}/{len(results)} ({same_results/len(results)*100:.1f}%)\n")
        
        # SQL 타입별 통계
        type_stats = {}
        for result in results:
            stmt_type = result['stmt_type']
            if stmt_type not in type_stats:
                type_stats[stmt_type] = {'total': 0}
                if not pg_only:
                    type_stats[stmt_type].update({'oracle_success': 0, 'oracle_timeout': 0, 'oracle_error': 0})
                if not oracle_only:
                    type_stats[stmt_type].update({'pg_success': 0, 'pg_timeout': 0, 'pg_error': 0})
                if not oracle_only and not pg_only:
                    type_stats[stmt_type]['same'] = 0
            
            type_stats[stmt_type]['total'] += 1
            
            if not pg_only:
                if result.get('orcl_status') == 'SUCCESS':
                    type_stats[stmt_type]['oracle_success'] += 1
                elif result.get('orcl_status') == 'TIMEOUT':
                    type_stats[stmt_type]['oracle_timeout'] += 1
                elif result.get('orcl_status') == 'ERROR':
                    type_stats[stmt_type]['oracle_error'] += 1
            
            if not oracle_only:
                if result.get('pg_status') == 'SUCCESS':
                    type_stats[stmt_type]['pg_success'] += 1
                elif result.get('pg_status') == 'TIMEOUT':
                    type_stats[stmt_type]['pg_timeout'] += 1
                elif result.get('pg_status') == 'ERROR':
                    type_stats[stmt_type]['pg_error'] += 1
            
            if not oracle_only and not pg_only and result.get('same') == 'Y':
                type_stats[stmt_type]['same'] += 1
        
        f.write("\nSQL 타입별 통계:\n")
        f.write("-" * 30 + "\n")
        for stmt_type, stats in type_stats.items():
            type_name = STMT_TYPES.get(stmt_type, stmt_type)
            f.write(f"{type_name} ({stmt_type}):\n")
            f.write(f"  총 개수: {stats['total']}\n")
            
            if not pg_only:
                f.write(f"  Oracle 성공: {stats['oracle_success']} ({stats['oracle_success']/stats['total']*100:.1f}%)\n")
                f.write(f"  Oracle 타임아웃: {stats['oracle_timeout']} ({stats['oracle_timeout']/stats['total']*100:.1f}%)\n")
                f.write(f"  Oracle 오류: {stats['oracle_error']} ({stats['oracle_error']/stats['total']*100:.1f}%)\n")
            
            if not oracle_only:
                f.write(f"  PostgreSQL 성공: {stats['pg_success']} ({stats['pg_success']/stats['total']*100:.1f}%)\n")
                f.write(f"  PostgreSQL 타임아웃: {stats['pg_timeout']} ({stats['pg_timeout']/stats['total']*100:.1f}%)\n")
                f.write(f"  PostgreSQL 오류: {stats['pg_error']} ({stats['pg_error']/stats['total']*100:.1f}%)\n")
            
            if not oracle_only and not pg_only:
                f.write(f"  결과 일치: {stats['same']} ({stats['same']/stats['total']*100:.1f}%)\n")
            f.write("\n")
        
        # 타임아웃 발생 SQL 목록
        timeout_sqls = []
        if not pg_only:
            timeout_sqls.extend([r for r in results if r.get('orcl_status') == 'TIMEOUT'])
        if not oracle_only:
            timeout_sqls.extend([r for r in results if r.get('pg_status') == 'TIMEOUT'])
        
        if timeout_sqls:
            f.write("타임아웃 발생 SQL 목록:\n")
            f.write("-" * 30 + "\n")
            for sql in timeout_sqls[:10]:  # 처음 10개만
                db_info = ""
                if sql.get('orcl_status') == 'TIMEOUT':
                    db_info += "Oracle "
                if sql.get('pg_status') == 'TIMEOUT':
                    db_info += "PostgreSQL "
                f.write(f"- {sql['app_name']}.{sql['sql_id']} ({sql['stmt_type']}) - {db_info.strip()}\n")
            if len(timeout_sqls) > 10:
                f.write(f"  ... 외 {len(timeout_sqls) - 10}개 타임아웃\n")
            f.write("\n")
        
        # 오류 발생 SQL 목록
        error_sqls = []
        if not pg_only:
            error_sqls.extend([r for r in results if r.get('orcl_status') == 'ERROR'])
        if not oracle_only:
            error_sqls.extend([r for r in results if r.get('pg_status') == 'ERROR'])
        
        if error_sqls:
            f.write("오류 발생 SQL 목록:\n")
            f.write("-" * 30 + "\n")
            for sql in error_sqls[:10]:  # 처음 10개만
                f.write(f"- {sql['app_name']}.{sql['sql_id']} ({sql['stmt_type']})\n")
                if sql.get('orcl_status') == 'ERROR':
                    f.write(f"  Oracle 오류: {sql.get('orcl_error', 'N/A')[:100]}...\n")
                if sql.get('pg_status') == 'ERROR':
                    f.write(f"  PostgreSQL 오류: {sql.get('pg_error', 'N/A')[:100]}...\n")
            if len(error_sqls) > 10:
                f.write(f"  ... 외 {len(error_sqls) - 10}개 오류\n")
    
    logger.info(f"요약 보고서 생성: {summary_file}")
    
    # JSON 상세 분석 데이터
    json_file = os.path.join(summary_dir, f"detailed_analysis{type_suffix}{db_suffix}_{timestamp}.json")
    
    analysis_data = {
        'execution_info': {
            'timestamp': datetime.now().isoformat(),
            'total_execution_time': execution_time,
            'total_sql_count': len(results),
            'type_filter': type_filter,
            'oracle_only': oracle_only,
            'pg_only': pg_only
        },
        'statistics': {},
        'type_statistics': type_stats,
        'timeout_details': [
            {
                'sql_id': r['sql_id'],
                'app_name': r['app_name'],
                'stmt_type': r['stmt_type'],
                'oracle_status': r.get('orcl_status', 'N/A'),
                'postgresql_status': r.get('pg_status', 'N/A'),
                'execution_time': r['execution_time']
            }
            for r in timeout_sqls
        ],
        'error_details': [
            {
                'sql_id': r['sql_id'],
                'app_name': r['app_name'],
                'stmt_type': r['stmt_type'],
                'oracle_status': r.get('orcl_status', 'N/A'),
                'postgresql_status': r.get('pg_status', 'N/A'),
                'oracle_error': r.get('orcl_error', ''),
                'postgresql_error': r.get('pg_error', ''),
                'execution_time': r['execution_time']
            }
            for r in error_sqls
        ]
    }
    
    # 통계 데이터 추가
    if not pg_only:
        oracle_success = sum(1 for r in results if r.get('orcl_status') == 'SUCCESS')
        oracle_timeout = sum(1 for r in results if r.get('orcl_status') == 'TIMEOUT')
        oracle_error = sum(1 for r in results if r.get('orcl_status') == 'ERROR')
        
        analysis_data['statistics'].update({
            'oracle_success_count': oracle_success,
            'oracle_timeout_count': oracle_timeout,
            'oracle_error_count': oracle_error,
            'oracle_success_rate': oracle_success/len(results)*100,
            'oracle_timeout_rate': oracle_timeout/len(results)*100,
            'oracle_error_rate': oracle_error/len(results)*100
        })
    
    if not oracle_only:
        pg_success = sum(1 for r in results if r.get('pg_status') == 'SUCCESS')
        pg_timeout = sum(1 for r in results if r.get('pg_status') == 'TIMEOUT')
        pg_error = sum(1 for r in results if r.get('pg_status') == 'ERROR')
        
        analysis_data['statistics'].update({
            'postgresql_success_count': pg_success,
            'postgresql_timeout_count': pg_timeout,
            'postgresql_error_count': pg_error,
            'postgresql_success_rate': pg_success/len(results)*100,
            'postgresql_timeout_rate': pg_timeout/len(results)*100,
            'postgresql_error_rate': pg_error/len(results)*100
        })
    
    if not oracle_only and not pg_only:
        same_results = sum(1 for r in results if r.get('same') == 'Y')
        both_success = sum(1 for r in results if r.get('orcl_status') == 'SUCCESS' and r.get('pg_status') == 'SUCCESS')
        
        analysis_data['statistics'].update({
            'both_success_count': both_success,
            'same_result_count': same_results,
            'same_result_rate': same_results/len(results)*100
        })
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"상세 분석 데이터 생성: {json_file}")
    
    return summary_file, json_file

def parse_arguments():
    """
    명령줄 인수를 파싱합니다.
    """
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').upper()
    
    parser = argparse.ArgumentParser(description=f'소스(Oracle)와 타겟({target_dbms})에서 SQL을 실행하고 결과를 비교합니다.')
    parser.add_argument('-t', '--type', 
                        help='실행할 SQL 문의 타입 (S: Select, I: Insert, U: Update, D: Delete, P: PL/SQL Block, O: Other). '
                             '여러 타입을 지정하려면 쉼표로 구분 (예: S,U,I)')
    parser.add_argument('--src-only', action='store_true',
                        help='소스(Oracle)에서만 SQL을 실행합니다 (타겟 실행 생략)')
    parser.add_argument('--tgt-only', action='store_true',
                        help=f'타겟({target_dbms})에서만 SQL을 실행합니다 (소스 실행 생략)')
    
    args = parser.parse_args()
    
    # 상호 배타적 옵션 검증
    if args.src_only and args.tgt_only:
        parser.error("--src-only와 --tgt-only 옵션은 동시에 사용할 수 없습니다.")
    
    return args

def get_db_connection():
    """
    TARGET_DBMS_TYPE에 따라 데이터베이스 연결을 생성합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    try:
        target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
        
        if target_dbms in ['postgres', 'postgresql']:
            # PostgreSQL 연결
            import psycopg2
            
            # 환경 변수에서 연결 정보 가져오기
            pg_user = os.environ.get('PGUSER')
            pg_password = os.environ.get('PGPASSWORD')
            pg_host = os.environ.get('PGHOST')
            pg_port = os.environ.get('PGPORT')
            pg_database = os.environ.get('PGDATABASE')
            
            # 연결 정보 확인
            if not all([pg_host, pg_port, pg_database, pg_user, pg_password]):
                logger.error("PostgreSQL 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
                logger.error(f"PGHOST: {pg_host}, PGPORT: {pg_port}, PGDATABASE: {pg_database}, PGUSER: {pg_user}")
                sys.exit(1)
            
            # 데이터베이스 연결
            conn = psycopg2.connect(
                host=pg_host,
                port=pg_port,
                database=pg_database,
                user=pg_user,
                password=pg_password
            )
            
            logger.info(f"PostgreSQL 연결 성공: {pg_host}:{pg_port}/{pg_database}")
            return conn
            
        elif target_dbms == 'mysql':
            # MySQL 연결
            import mysql.connector
            
            # 환경 변수에서 연결 정보 가져오기
            mysql_host = os.environ.get('MYSQL_HOST')
            mysql_port = os.environ.get('MYSQL_PORT')
            mysql_database = os.environ.get('MYSQL_DATABASE')
            mysql_user = os.environ.get('MYSQL_USER')
            mysql_password = os.environ.get('MYSQL_PASSWORD')
            
            # 연결 정보 확인
            if not all([mysql_host, mysql_port, mysql_database, mysql_user, mysql_password]):
                logger.error("MySQL 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
                logger.error(f"MYSQL_HOST: {mysql_host}, MYSQL_PORT: {mysql_port}, MYSQL_DATABASE: {mysql_database}, MYSQL_USER: {mysql_user}")
                sys.exit(1)
            
            # 데이터베이스 연결
            conn = mysql.connector.connect(
                host=mysql_host,
                port=int(mysql_port),
                database=mysql_database,
                user=mysql_user,
                password=mysql_password,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            logger.info(f"MySQL 연결 성공: {mysql_host}:{mysql_port}/{mysql_database}")
            return conn
            
        else:
            logger.error(f"지원하지 않는 타겟 DBMS 타입: {target_dbms}")
            logger.error("지원되는 타입: postgres, postgresql, mysql")
            sys.exit(1)
            
    except ImportError as e:
        logger.error(f"데이터베이스 드라이버 import 오류: {e}")
        if target_dbms in ['postgres', 'postgresql']:
            logger.error("PostgreSQL 드라이버를 설치하세요: pip install psycopg2-binary")
        elif target_dbms == 'mysql':
            logger.error("MySQL 드라이버를 설치하세요: pip install mysql-connector-python")
        sys.exit(1)
    except Exception as e:
        logger.error(f"데이터베이스 연결 오류: {e}")
        sys.exit(1)
def main():
    """메인 실행 함수"""
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 디렉토리 설정
    setup_directories()
    
    # 경로 정보 출력
    paths = get_paths()
    logger.info("경로 설정:")
    logger.info(f"  SQL 결과 디렉토리: {paths['sql_results_dir']}")
    logger.info(f"  CSV 출력: {paths['csv_dir']}")
    logger.info(f"  요약 보고서: {paths['summary_dir']}")
    logger.info(f"  임시 파일: {paths['temp_dir']}")
    logger.info(f"  로그 디렉토리: {paths['logs_dir']}")
    
    # 실행 모드 로그 출력
    if args.oracle_only:
        logger.info("Oracle 전용 모드로 실행합니다 (PostgreSQL 실행 생략)")
    elif args.pg_only:
        logger.info("PostgreSQL 전용 모드로 실행합니다 (Oracle 실행 생략)")
    
    # 현재 시간을 기반으로 한 결과 파일 이름
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 타입 필터링이 있는 경우 파일 이름에 추가
    type_suffix = ""
    if args.type:
        type_suffix = f"_{args.type.replace(',', '')}"
    
    # 단일 DB 모드인 경우 파일 이름에 추가
    db_suffix = ""
    if args.oracle_only:
        db_suffix = "_oracle_only"
    elif args.pg_only:
        db_suffix = "_pg_only"
    
    csv_file = os.path.join(paths['csv_dir'], f"sql_comparison_results{type_suffix}{db_suffix}_{timestamp}.csv")
    
    # Oracle 한글 인코딩 환경 변수 설정
    os.environ['NLS_LANG'] = 'KOREAN_KOREA.AL32UTF8'
    
    # PostgreSQL 연결
    conn = get_db_connection()
    
    # 환경변수에서 배치 크기 가져오기
    batch_size = int(os.environ.get('SQL_BATCH_SIZE', '10'))
    
    start_time = time.time()
    results = []
    oracle_timeout_sqls = []  # Oracle 타임아웃 발생한 SQL 목록
    pg_timeout_sqls = []      # PostgreSQL 타임아웃 발생한 SQL 목록
    
    try:
        # CSV 결과 파일 생성
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            if args.oracle_only:
                fieldnames = ['sql_id', 'app_name', 'stmt_type', 'orcl_file_path', 
                             'orcl_result_status', 'execution_time', 'orcl_error']
            elif args.pg_only:
                fieldnames = ['sql_id', 'app_name', 'stmt_type', 'pg_file_path', 
                             'pg_result_status', 'execution_time', 'pg_error']
            else:
                fieldnames = ['sql_id', 'app_name', 'stmt_type', 'orcl_file_path', 'pg_file_path', 
                             'orcl_result_status', 'pg_result_status', 'same', 'execution_time',
                             'orcl_error', 'pg_error']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # SQL 쿼리 구성
            query = """
                SELECT sql_id, app_name, stmt_type, src_file_path, tgt_file_path, src, tgt
                FROM sqllist
                WHERE 1=1
            """
            
            # 실행 모드에 따른 조건 추가
            if args.src_only:
                query += " AND src IS NOT NULL"
            elif args.tgt_only:
                query += " AND tgt IS NOT NULL"
            else:
                query += " AND src IS NOT NULL AND tgt IS NOT NULL"
            
            # 타입 필터링이 있는 경우 WHERE 절에 추가
            if args.type:
                stmt_types = args.type.upper().split(',')
                valid_types = [t for t in stmt_types if t in STMT_TYPES]
                
                if valid_types:
                    type_list = "', '".join(valid_types)
                    query += f" AND stmt_type IN ('{type_list}')"
                    logger.info(f"SQL 문 타입 필터링: {', '.join([STMT_TYPES.get(t, t) for t in valid_types])}")
            
            query += " ORDER BY sql_id, app_name, stmt_type"
            
            # 쿼리 실행
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchall()
                total_rows = len(rows)
                
                if total_rows == 0:
                    logger.warning("조건에 맞는 SQL 문이 없습니다.")
                    return
                
                logger.info(f"총 {total_rows}개의 SQL 문을 실행합니다.")
                
                for i, row in enumerate(rows, 1):
                    sql_id = row['sql_id']
                    app_name = row['app_name']
                    stmt_type = row['stmt_type']
                    orcl_sql = row['orcl']
                    pg_sql = row['pg']
                    
                    logger.info(f"[{i}/{total_rows}] SQL ID: {sql_id}, App: {app_name} (타입: {stmt_type} - {STMT_TYPES.get(stmt_type, '알 수 없음')}) 처리 중...")
                    
                    sql_start_time = time.time()
                    
                    # Oracle SQL 실행 (PostgreSQL 전용 모드가 아닌 경우에만)
                    if args.pg_only:
                        orcl_result = None
                        orcl_status = "SKIPPED"
                        orcl_error = ""
                    else:
                        orcl_result = execute_oracle_sql(sql_id, orcl_sql)
                        orcl_status = "SUCCESS" if not orcl_result.startswith("ERROR:") and not orcl_result.startswith("TIMEOUT:") else "ERROR"
                        orcl_error = orcl_result if orcl_status == "ERROR" else ""
                        
                        # Oracle 타임아웃 발생한 경우 목록에 추가
                        if orcl_result.startswith("TIMEOUT:"):
                            oracle_timeout_sqls.append({
                                'sql_id': sql_id,
                                'app_name': app_name,
                                'stmt_type': stmt_type,
                                'file_path': row['orcl_file_path']
                            })
                            orcl_status = "TIMEOUT"
                    
                    # PostgreSQL SQL 실행 (Oracle 전용 모드가 아닌 경우에만)
                    if args.oracle_only:
                        pg_result = None
                        pg_status = "SKIPPED"
                        pg_error = ""
                        same = "N/A"
                    else:
                        pg_result = execute_postgres_sql(sql_id, pg_sql)
                        pg_status = "SUCCESS" if not pg_result.startswith("ERROR:") and not pg_result.startswith("TIMEOUT:") else "ERROR"
                        pg_error = pg_result if pg_status == "ERROR" else ""
                        
                        # PostgreSQL 타임아웃 발생한 경우 목록에 추가
                        if pg_result.startswith("TIMEOUT:"):
                            pg_timeout_sqls.append({
                                'sql_id': sql_id,
                                'app_name': app_name,
                                'stmt_type': stmt_type,
                                'file_path': row['pg_file_path']
                            })
                            pg_status = "TIMEOUT"
                        
                        # 결과 비교 (둘 다 성공한 경우에만, 비교 모드일 때만)
                        if not args.oracle_only and not args.pg_only:
                            if orcl_status == "SUCCESS" and pg_status == "SUCCESS":
                                same = 'Y' if orcl_result == pg_result else 'N'
                            else:
                                same = 'N'
                        else:
                            same = "N/A"
                    
                    # 실행 시간 계산
                    sql_execution_time = time.time() - sql_start_time
                    
                    # 결과 업데이트
                    if not args.oracle_only and not args.pg_only:
                        # 비교 모드: 양쪽 결과 모두 업데이트
                        update_success, same = update_results(conn, sql_id, app_name, stmt_type, orcl_result, pg_result)
                    elif args.pg_only:
                        # PostgreSQL 전용 모드: PostgreSQL 결과만 업데이트
                        update_success, same = update_pg_only_results(conn, sql_id, app_name, stmt_type, pg_result)
                    elif args.oracle_only:
                        # Oracle 전용 모드: Oracle 결과만 업데이트
                        update_success, same = update_oracle_only_results(conn, sql_id, app_name, stmt_type, orcl_result)
                    
                    # 결과 저장
                    result_data = {
                        'sql_id': sql_id,
                        'app_name': app_name,
                        'stmt_type': stmt_type,
                        'execution_time': f"{sql_execution_time:.2f}"
                    }
                    
                    if not args.pg_only:
                        result_data.update({
                            'orcl_file_path': row['orcl_file_path'],
                            'orcl_status': orcl_status,
                            'orcl_error': orcl_error
                        })
                    
                    if not args.oracle_only:
                        result_data.update({
                            'pg_file_path': row['pg_file_path'],
                            'pg_status': pg_status,
                            'pg_error': pg_error
                        })
                    
                    if not args.oracle_only and not args.pg_only:
                        result_data['same'] = same
                    
                    results.append(result_data)
                    
                    # CSV에 결과 기록
                    csv_row = {
                        'sql_id': sql_id,
                        'app_name': app_name,
                        'stmt_type': stmt_type,
                        'execution_time': f"{sql_execution_time:.2f}"
                    }
                    
                    if not args.pg_only:
                        csv_row.update({
                            'orcl_file_path': row['orcl_file_path'],
                            'orcl_result_status': orcl_status,
                            'orcl_error': orcl_error
                        })
                    
                    if not args.oracle_only:
                        csv_row.update({
                            'pg_file_path': row['pg_file_path'],
                            'pg_result_status': pg_status,
                            'pg_error': pg_error
                        })
                    
                    if not args.oracle_only and not args.pg_only:
                        csv_row['same'] = same
                    
                    writer.writerow(csv_row)
                    
                    # 진행 상황 출력
                    if args.oracle_only:
                        logger.info(f"[{i}/{total_rows}] 처리 완료 - Oracle: {orcl_status}, 시간: {sql_execution_time:.2f}초")
                    elif args.pg_only:
                        logger.info(f"[{i}/{total_rows}] 처리 완료 - PostgreSQL: {pg_status}, 시간: {sql_execution_time:.2f}초")
                    else:
                        logger.info(f"[{i}/{total_rows}] 처리 완료 - Oracle: {orcl_status}, PostgreSQL: {pg_status}, 같음: {same}, 시간: {sql_execution_time:.2f}초")
                    
                    # 배치 커밋
                    if i % batch_size == 0:
                        conn.commit()
                        logger.info(f"배치 커밋 완료: {i}/{total_rows}")
                
                # 최종 커밋
                conn.commit()
        
        # 타임아웃 목록 저장
        if oracle_timeout_sqls:
            save_timeout_list(oracle_timeout_sqls, 'oracle')
        if pg_timeout_sqls:
            save_timeout_list(pg_timeout_sqls, 'postgresql')
        
        # 총 실행 시간 계산
        total_execution_time = time.time() - start_time
        
        logger.info("=" * 60)
        if args.oracle_only:
            logger.info("Oracle SQL 실행 완료")
        elif args.pg_only:
            logger.info("PostgreSQL SQL 실행 완료")
        else:
            logger.info("SQL 실행 및 비교 완료")
        logger.info("=" * 60)
        logger.info(f"총 소요 시간: {total_execution_time:.2f}초")
        logger.info(f"CSV 결과 파일: {csv_file}")
        
        # 요약 보고서 생성
        summary_file, json_file = generate_summary_report(results, total_execution_time, args.type, args.oracle_only, args.pg_only)
        logger.info(f"요약 보고서: {summary_file}")
        logger.info(f"상세 분석: {json_file}")
        
        # 최종 통계 출력
        logger.info("=" * 60)
        logger.info("최종 통계:")
        logger.info(f"  총 SQL 수: {len(results)}")
        
        if not args.pg_only:
            oracle_success = sum(1 for r in results if r.get('orcl_status') == 'SUCCESS')
            oracle_timeout = sum(1 for r in results if r.get('orcl_status') == 'TIMEOUT')
            logger.info(f"  Oracle 성공: {oracle_success} ({oracle_success/len(results)*100:.1f}%)")
            logger.info(f"  Oracle 타임아웃: {oracle_timeout} ({oracle_timeout/len(results)*100:.1f}%)")
        
        if not args.oracle_only:
            pg_success = sum(1 for r in results if r.get('pg_status') == 'SUCCESS')
            pg_timeout = sum(1 for r in results if r.get('pg_status') == 'TIMEOUT')
            logger.info(f"  PostgreSQL 성공: {pg_success} ({pg_success/len(results)*100:.1f}%)")
            logger.info(f"  PostgreSQL 타임아웃: {pg_timeout} ({pg_timeout/len(results)*100:.1f}%)")
        
        if not args.oracle_only and not args.pg_only:
            same_results = sum(1 for r in results if r.get('same') == 'Y')
            logger.info(f"  결과 일치: {same_results} ({same_results/len(results)*100:.1f}%)")
        
        if oracle_timeout_sqls:
            logger.info(f"  Oracle 타임아웃 목록: timeout_orcl.lst ({len(oracle_timeout_sqls)}개)")
        if pg_timeout_sqls:
            logger.info(f"  PostgreSQL 타임아웃 목록: timeout_pg.lst ({len(pg_timeout_sqls)}개)")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()
        logger.info("데이터베이스 연결 종료")

if __name__ == "__main__":
    # 환경 변수 확인
    check_environment_variables()
    
    # 로깅 설정
    logger = setup_logging()
    
    try:
        # 메인 실행
        main()
        logger.info("ExecuteAndCompareSQL 실행 완료")
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {str(e)}")
        raise
