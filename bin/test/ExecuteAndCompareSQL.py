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
    
    # 필수 환경 변수 목록
    required_env_vars = [
        'ORACLE_SVC_USER',
        'ORACLE_SVC_PASSWORD',
        'ORACLE_SID',
        'PGHOST',
        'PGPORT', 
        'PGDATABASE',
        'PGUSER',
        'PGPASSWORD'
    ]
    
    # 권장 환경 변수 목록
    recommended_env_vars = [
        'TEST_FOLDER',
        'TEST_LOGS_FOLDER'
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
        'oracle_temp_dir': os.path.join(test_folder, 'sql_results', 'temp', 'oracle'),
        'pg_temp_dir': os.path.join(test_folder, 'sql_results', 'temp', 'postgresql'),
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
        paths['oracle_temp_dir'],
        paths['pg_temp_dir'],
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
    oracle_sid = os.environ.get('ORACLE_SID')
    
    if not all([oracle_user, oracle_password, oracle_sid]):
        error_msg = "Oracle 연결 정보가 환경 변수에 설정되어 있지 않습니다."
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    
    # SQL 문 끝에 있는 '/' 문자 제거
    sql = sql.strip()
    if sql.endswith('/'):
        sql = sql[:-1].strip()
    
    paths = get_paths()
    oracle_temp_dir = paths['oracle_temp_dir']
    
    # 임시 파일 경로 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_sql_path = os.path.join(oracle_temp_dir, f"temp_sql_{sql_id}_{timestamp}.sql")
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
            temp_sql.write("ALTER SESSION SET NLS_LANGUAGE = 'KOREAN';\n")
            temp_sql.write("ALTER SESSION SET NLS_TERRITORY = 'KOREA';\n")
            temp_sql.write("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS';\n")
            temp_sql.write("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF';\n")
            temp_sql.write(f"SPOOL {temp_result_path}\n")
            
            # 실행할 SQL 추가
            temp_sql.write(f"{sql};\n")
            temp_sql.write("SPOOL OFF\n")
            temp_sql.write("EXIT;\n")
        
        debug_logger.debug(f"Oracle 임시 SQL 파일 생성: {temp_sql_path}")
        
        # Oracle SQL 실행 - 한글 인코딩 설정
        env = os.environ.copy()
        env['NLS_LANG'] = 'KOREAN_KOREA.AL32UTF8'
        cmd = f"sqlplus -S {oracle_user}/{oracle_password}@{oracle_sid} @{temp_sql_path}"
        
        process = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, 
                               stdout=subprocess.PIPE, env=env, timeout=300)
        
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
        error_msg = "Oracle SQL 실행 타임아웃 (5분 초과)"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    except Exception as e:
        error_msg = f"Oracle SQL 실행 중 예외 발생: {str(e)}"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    finally:
        # 임시 파일 정리
        cleanup_temp_files(temp_files)

def execute_postgres_sql(sql_id, sql):
    """
    PostgreSQL에서 SQL을 실행하고 결과를 반환합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    debug_logger = logging.getLogger('debug')
    error_logger = logging.getLogger('error')
    perf_logger = logging.getLogger('performance')
    
    start_time = time.time()
    logger.info(f"PostgreSQL SQL 실행 시작: {sql_id}")
    debug_logger.debug(f"PostgreSQL SQL 내용: {sql[:200]}...")
    
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
    
    # SQL 문 끝에 있는 '/' 문자 제거
    sql = sql.strip()
    if sql.endswith('/'):
        sql = sql[:-1].strip()
    
    paths = get_paths()
    pg_temp_dir = paths['pg_temp_dir']
    
    # 임시 파일 경로 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_sql_path = os.path.join(pg_temp_dir, f"temp_sql_{sql_id}_{timestamp}.sql")
    
    temp_files = [temp_sql_path]
    
    try:
        # 임시 SQL 파일 생성
        with open(temp_sql_path, 'w', encoding='utf-8') as temp_sql:
            # 결과를 CSV 형식으로 출력하는 설정 추가
            temp_sql.write("\\set QUIET on\n")
            temp_sql.write("\\pset tuples_only on\n")
            temp_sql.write("\\pset format unaligned\n")
            temp_sql.write("\\pset fieldsep ','\n")
            temp_sql.write("\\pset footer off\n")
            temp_sql.write("\\pset pager off\n")
            
            # 실행할 SQL 추가
            temp_sql.write(f"{sql};\n")
            temp_sql.write("\\q\n")
        
        debug_logger.debug(f"PostgreSQL 임시 SQL 파일 생성: {temp_sql_path}")
        
        # PostgreSQL SQL 실행
        env = os.environ.copy()
        cmd = f"psql -h {pg_host} -p {pg_port} -d {pg_database} -U {pg_user} -f {temp_sql_path}"
        
        process = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, 
                               stdout=subprocess.PIPE, env=env, timeout=300)
        
        execution_time = time.time() - start_time
        perf_logger.info(f"PostgreSQL SQL 실행 시간: {sql_id} - {execution_time:.2f}초")
        
        if process.returncode != 0:
            error_msg = process.stderr.decode('utf-8', errors='replace')
            error_logger.error(f"PostgreSQL SQL 실행 오류: {sql_id} - {error_msg}")
            return f"ERROR: {error_msg}"
        
        result = process.stdout.decode('utf-8', errors='replace').strip()
        
        # PostgreSQL 오류 확인
        if 'ERROR:' in result:
            error_lines = [line for line in result.split('\n') if 'ERROR:' in line]
            if error_lines:
                error_msg = error_lines[0]
                error_logger.error(f"PostgreSQL SQL 오류: {sql_id} - {error_msg}")
                return error_msg
        
        logger.info(f"PostgreSQL SQL 실행 성공: {sql_id}")
        debug_logger.debug(f"PostgreSQL 결과 길이: {len(result)} 문자")
        return result
        
    except subprocess.TimeoutExpired:
        error_msg = "PostgreSQL SQL 실행 타임아웃 (5분 초과)"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    except Exception as e:
        error_msg = f"PostgreSQL SQL 실행 중 예외 발생: {str(e)}"
        error_logger.error(f"{sql_id}: {error_msg}")
        return f"ERROR: {error_msg}"
    finally:
        # 임시 파일 정리
        cleanup_temp_files(temp_files)
def update_results(conn, sql_id, app_name, stmt_type, orcl_result, pg_result):
    """
    sqllist 테이블에 실행 결과를 업데이트합니다.
    """
    try:
        # 결과 비교
        same = 'Y' if orcl_result == pg_result else 'N'
        
        # 오류가 있는 경우 무조건 다름으로 처리
        if orcl_result.startswith("ERROR:") or pg_result.startswith("ERROR:"):
            same = 'N'
        
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE sqllist 
                SET orcl_result = %s, pg_result = %s, same = %s
                WHERE sql_id = %s AND app_name = %s AND stmt_type = %s
                """,
                (orcl_result, pg_result, same, sql_id, app_name, stmt_type)
            )
        
        logger.debug(f"결과 업데이트 완료: {sql_id} - 동일: {same}")
        return True, same
    except Exception as e:
        logger.error(f"결과 업데이트 중 오류 발생: {sql_id} - {str(e)}")
        conn.rollback()
        return False, 'N'

def generate_summary_report(results, execution_time, type_filter=None):
    """실행 요약 보고서를 생성합니다."""
    paths = get_paths()
    summary_dir = paths['summary_dir']
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    type_suffix = f"_{type_filter.replace(',', '')}" if type_filter else ""
    
    # 텍스트 요약 보고서
    summary_file = os.path.join(summary_dir, f"execution_summary{type_suffix}_{timestamp}.txt")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("SQL 실행 및 비교 요약 보고서\n")
        f.write("=" * 60 + "\n")
        f.write(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"총 소요 시간: {execution_time:.2f}초\n")
        f.write(f"총 실행 SQL 수: {len(results)}\n")
        if type_filter:
            f.write(f"필터링된 타입: {type_filter}\n")
        f.write("\n")
        
        # 성공/실패 통계
        oracle_success = sum(1 for r in results if r['orcl_status'] == 'SUCCESS')
        pg_success = sum(1 for r in results if r['pg_status'] == 'SUCCESS')
        same_results = sum(1 for r in results if r['same'] == 'Y')
        both_success = sum(1 for r in results if r['orcl_status'] == 'SUCCESS' and r['pg_status'] == 'SUCCESS')
        
        f.write("실행 결과 통계:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Oracle 성공: {oracle_success}/{len(results)} ({oracle_success/len(results)*100:.1f}%)\n")
        f.write(f"PostgreSQL 성공: {pg_success}/{len(results)} ({pg_success/len(results)*100:.1f}%)\n")
        f.write(f"양쪽 모두 성공: {both_success}/{len(results)} ({both_success/len(results)*100:.1f}%)\n")
        f.write(f"결과 일치: {same_results}/{len(results)} ({same_results/len(results)*100:.1f}%)\n")
        
        # SQL 타입별 통계
        type_stats = {}
        for result in results:
            stmt_type = result['stmt_type']
            if stmt_type not in type_stats:
                type_stats[stmt_type] = {'total': 0, 'oracle_success': 0, 'pg_success': 0, 'same': 0}
            
            type_stats[stmt_type]['total'] += 1
            if result['orcl_status'] == 'SUCCESS':
                type_stats[stmt_type]['oracle_success'] += 1
            if result['pg_status'] == 'SUCCESS':
                type_stats[stmt_type]['pg_success'] += 1
            if result['same'] == 'Y':
                type_stats[stmt_type]['same'] += 1
        
        f.write("\nSQL 타입별 통계:\n")
        f.write("-" * 30 + "\n")
        for stmt_type, stats in type_stats.items():
            type_name = STMT_TYPES.get(stmt_type, stmt_type)
            f.write(f"{type_name} ({stmt_type}):\n")
            f.write(f"  총 개수: {stats['total']}\n")
            f.write(f"  Oracle 성공: {stats['oracle_success']} ({stats['oracle_success']/stats['total']*100:.1f}%)\n")
            f.write(f"  PostgreSQL 성공: {stats['pg_success']} ({stats['pg_success']/stats['total']*100:.1f}%)\n")
            f.write(f"  결과 일치: {stats['same']} ({stats['same']/stats['total']*100:.1f}%)\n")
            f.write("\n")
        
        # 오류 발생 SQL 목록
        error_sqls = [r for r in results if r['orcl_status'] == 'ERROR' or r['pg_status'] == 'ERROR']
        if error_sqls:
            f.write("오류 발생 SQL 목록:\n")
            f.write("-" * 30 + "\n")
            for sql in error_sqls[:10]:  # 처음 10개만
                f.write(f"- {sql['app_name']}.{sql['sql_id']} ({sql['stmt_type']})\n")
                if sql['orcl_status'] == 'ERROR':
                    f.write(f"  Oracle 오류: {sql.get('orcl_error', 'N/A')[:100]}...\n")
                if sql['pg_status'] == 'ERROR':
                    f.write(f"  PostgreSQL 오류: {sql.get('pg_error', 'N/A')[:100]}...\n")
            if len(error_sqls) > 10:
                f.write(f"  ... 외 {len(error_sqls) - 10}개 오류\n")
    
    logger.info(f"요약 보고서 생성: {summary_file}")
    
    # JSON 상세 분석 데이터
    json_file = os.path.join(summary_dir, f"detailed_analysis{type_suffix}_{timestamp}.json")
    
    analysis_data = {
        'execution_info': {
            'timestamp': datetime.now().isoformat(),
            'total_execution_time': execution_time,
            'total_sql_count': len(results),
            'type_filter': type_filter
        },
        'statistics': {
            'oracle_success_count': oracle_success,
            'postgresql_success_count': pg_success,
            'both_success_count': both_success,
            'same_result_count': same_results,
            'oracle_success_rate': oracle_success/len(results)*100,
            'postgresql_success_rate': pg_success/len(results)*100,
            'same_result_rate': same_results/len(results)*100
        },
        'type_statistics': type_stats,
        'error_details': [
            {
                'sql_id': r['sql_id'],
                'app_name': r['app_name'],
                'stmt_type': r['stmt_type'],
                'oracle_status': r['orcl_status'],
                'postgresql_status': r['pg_status'],
                'oracle_error': r.get('orcl_error', ''),
                'postgresql_error': r.get('pg_error', ''),
                'execution_time': r['execution_time']
            }
            for r in error_sqls
        ]
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"상세 분석 데이터 생성: {json_file}")
    
    return summary_file, json_file

def parse_arguments():
    """
    명령줄 인수를 파싱합니다.
    """
    parser = argparse.ArgumentParser(description='Oracle과 PostgreSQL에서 SQL을 실행하고 결과를 비교합니다.')
    parser.add_argument('-t', '--type', 
                        help='실행할 SQL 문의 타입 (S: Select, I: Insert, U: Update, D: Delete, P: PL/SQL Block, O: Other). '
                             '여러 타입을 지정하려면 쉼표로 구분 (예: S,U,I)')
    return parser.parse_args()

def get_db_connection():
    """
    PostgreSQL 데이터베이스 연결을 생성합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    try:
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
    
    # 현재 시간을 기반으로 한 결과 파일 이름
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 타입 필터링이 있는 경우 파일 이름에 추가
    type_suffix = ""
    if args.type:
        type_suffix = f"_{args.type.replace(',', '')}"
    
    csv_file = os.path.join(paths['csv_dir'], f"sql_comparison_results{type_suffix}_{timestamp}.csv")
    
    # Oracle 한글 인코딩 환경 변수 설정
    os.environ['NLS_LANG'] = 'KOREAN_KOREA.AL32UTF8'
    
    # PostgreSQL 연결
    conn = get_db_connection()
    
    # 환경변수에서 배치 크기 가져오기
    batch_size = int(os.environ.get('SQL_BATCH_SIZE', '10'))
    
    start_time = time.time()
    results = []
    
    try:
        # CSV 결과 파일 생성
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['sql_id', 'app_name', 'stmt_type', 'orcl_file_path', 'pg_file_path', 
                         'orcl_result_status', 'pg_result_status', 'same', 'execution_time',
                         'orcl_error', 'pg_error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # SQL 쿼리 구성
            query = """
                SELECT sql_id, app_name, stmt_type, orcl_file_path, pg_file_path, orcl, pg
                FROM sqllist
                WHERE orcl IS NOT NULL AND pg IS NOT NULL
            """
            
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
                    
                    # Oracle SQL 실행
                    orcl_result = execute_oracle_sql(sql_id, orcl_sql)
                    orcl_status = "SUCCESS" if not orcl_result.startswith("ERROR:") else "ERROR"
                    orcl_error = orcl_result if orcl_status == "ERROR" else ""
                    
                    # PostgreSQL SQL 실행
                    pg_result = execute_postgres_sql(sql_id, pg_sql)
                    pg_status = "SUCCESS" if not pg_result.startswith("ERROR:") else "ERROR"
                    pg_error = pg_result if pg_status == "ERROR" else ""
                    
                    # 실행 시간 계산
                    sql_execution_time = time.time() - sql_start_time
                    
                    # 결과 업데이트
                    update_success, same = update_results(conn, sql_id, app_name, stmt_type, orcl_result, pg_result)
                    
                    # 결과 저장
                    result_data = {
                        'sql_id': sql_id,
                        'app_name': app_name,
                        'stmt_type': stmt_type,
                        'orcl_file_path': row['orcl_file_path'],
                        'pg_file_path': row['pg_file_path'],
                        'orcl_status': orcl_status,
                        'pg_status': pg_status,
                        'same': same,
                        'execution_time': f"{sql_execution_time:.2f}",
                        'orcl_error': orcl_error,
                        'pg_error': pg_error
                    }
                    
                    results.append(result_data)
                    
                    # CSV에 결과 기록
                    writer.writerow({
                        'sql_id': sql_id,
                        'app_name': app_name,
                        'stmt_type': stmt_type,
                        'orcl_file_path': row['orcl_file_path'],
                        'pg_file_path': row['pg_file_path'],
                        'orcl_result_status': orcl_status,
                        'pg_result_status': pg_status,
                        'same': same,
                        'execution_time': f"{sql_execution_time:.2f}",
                        'orcl_error': orcl_error,
                        'pg_error': pg_error
                    })
                    
                    # 진행 상황 출력
                    logger.info(f"[{i}/{total_rows}] 처리 완료 - Oracle: {orcl_status}, PostgreSQL: {pg_status}, 같음: {same}, 시간: {sql_execution_time:.2f}초")
                    
                    # 배치 커밋
                    if i % batch_size == 0:
                        conn.commit()
                        logger.info(f"배치 커밋 완료: {i}/{total_rows}")
                
                # 최종 커밋
                conn.commit()
        
        # 총 실행 시간 계산
        total_execution_time = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info("SQL 실행 및 비교 완료")
        logger.info("=" * 60)
        logger.info(f"총 소요 시간: {total_execution_time:.2f}초")
        logger.info(f"CSV 결과 파일: {csv_file}")
        
        # 요약 보고서 생성
        summary_file, json_file = generate_summary_report(results, total_execution_time, args.type)
        logger.info(f"요약 보고서: {summary_file}")
        logger.info(f"상세 분석: {json_file}")
        
        # 최종 통계 출력
        oracle_success = sum(1 for r in results if r['orcl_status'] == 'SUCCESS')
        pg_success = sum(1 for r in results if r['pg_status'] == 'SUCCESS')
        same_results = sum(1 for r in results if r['same'] == 'Y')
        
        logger.info("=" * 60)
        logger.info("최종 통계:")
        logger.info(f"  총 SQL 수: {len(results)}")
        logger.info(f"  Oracle 성공: {oracle_success} ({oracle_success/len(results)*100:.1f}%)")
        logger.info(f"  PostgreSQL 성공: {pg_success} ({pg_success/len(results)*100:.1f}%)")
        logger.info(f"  결과 일치: {same_results} ({same_results/len(results)*100:.1f}%)")
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
