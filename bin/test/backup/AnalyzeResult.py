#!/usr/bin/env python3
#############################################################################
# Script: DB10.AnalyzeResult.py
# Description: This script analyzes differences between Oracle and PostgreSQL
#              query results from multiple sources including database and files.
#
# Functionality:
# - Analyzes SQL statements where Oracle and PostgreSQL results differ
# - Utilizes results from ExecuteAndCompareSQL.py and SaveSQLToDB.py
# - Categorizes differences by type and provides detailed analysis
# - Generates comprehensive reports in multiple formats (HTML, JSON, CSV)
# - Provides recommendations for resolving compatibility issues
# - Tracks analysis trends over time
#
# Usage:
#   python3 DB10.AnalyzeResult.py [options]
#
# Options:
#   -t, --type TYPE     Filter by SQL statement type (S: Select, I: Insert, etc.)
#   -a, --app APP       Filter by application name
#   -l, --limit N       Limit the number of results to analyze (default: 100)
#   -f, --format FORMAT Output format: html,json,csv,all (default: html)
#   --use-latest        Use latest ExecuteAndCompareSQL results automatically
#############################################################################

import os
import sys
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
import difflib
import re
import json
import csv
import glob
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import html

def check_environment_variables():
    """
    환경 변수가 설정되어 있는지 확인합니다.
    """
    print("=" * 60)
    print("환경 변수 확인 중...")
    print("=" * 60)
    
    # 필수 환경 변수 목록
    required_env_vars = [
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
        # 입력 경로들
        'sql_results_dir': os.path.join(test_folder, 'sql_results'),
        'sql_results_csv_dir': os.path.join(test_folder, 'sql_results', 'csv'),
        'sql_results_summary_dir': os.path.join(test_folder, 'sql_results', 'summary'),
        'sqllist_dir': os.path.join(test_folder, 'sqllist'),
        
        # 출력 경로들
        'analysis_results_dir': os.path.join(test_folder, 'analysis_results'),
        'html_dir': os.path.join(test_folder, 'analysis_results', 'html'),
        'json_dir': os.path.join(test_folder, 'analysis_results', 'json'),
        'csv_dir': os.path.join(test_folder, 'analysis_results', 'csv'),
        'assets_dir': os.path.join(test_folder, 'analysis_results', 'assets'),
        'logs_dir': test_logs_folder
    }

# 로깅 설정
def setup_logging():
    """로깅을 설정합니다."""
    paths = get_paths()
    logs_dir = paths['logs_dir']
    
    # 로그 디렉토리 생성
    os.makedirs(logs_dir, exist_ok=True)
    
    # 로그 파일 경로
    log_file = os.path.join(logs_dir, 'analyze_result.log')
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("AnalyzeResult 실행 시작")
    logger.info("=" * 60)
    
    return logger

def setup_directories():
    """필요한 디렉토리들을 생성합니다."""
    paths = get_paths()
    
    directories = [
        paths['analysis_results_dir'],
        paths['html_dir'],
        paths['json_dir'],
        paths['csv_dir'],
        paths['assets_dir']
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

# 차이 유형 정의
DIFFERENCE_TYPES = {
    'data_type': '데이터 타입 차이',
    'date_format': '날짜 형식 차이',
    'null_handling': 'NULL 처리 차이',
    'case_sensitivity': '대소문자 구분 차이',
    'whitespace': '공백 차이',
    'order': '결과 순서 차이',
    'function': '함수 동작 차이',
    'syntax': '구문 차이',
    'error': '오류 발생',
    'performance': '성능 차이',
    'timeout': '타임아웃',
    'other': '기타 차이'
}

def get_input_sources():
    """분석에 사용할 입력 소스들을 확인하고 반환합니다."""
    paths = get_paths()
    sources = {}
    
    # 1. PostgreSQL 데이터베이스 확인
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sqllist WHERE same = 'N'")
            diff_count = cur.fetchone()[0]
        conn.close()
        sources['database'] = {
            'available': True,
            'different_results_count': diff_count
        }
        logger.info(f"데이터베이스: {diff_count}개의 차이 결과 발견")
    except Exception as e:
        sources['database'] = {'available': False, 'error': str(e)}
        logger.warning(f"데이터베이스 연결 실패: {e}")
    
    # 2. ExecuteAndCompareSQL CSV 결과 확인
    csv_files = glob.glob(os.path.join(paths['sql_results_csv_dir'], 'sql_comparison_results_*.csv'))
    sources['csv_results'] = {
        'available': len(csv_files) > 0,
        'files': csv_files,
        'count': len(csv_files)
    }
    logger.info(f"CSV 결과 파일: {len(csv_files)}개 발견")
    
    # 3. ExecuteAndCompareSQL 요약 결과 확인
    summary_files = glob.glob(os.path.join(paths['sql_results_summary_dir'], 'detailed_analysis_*.json'))
    sources['summary_results'] = {
        'available': len(summary_files) > 0,
        'files': summary_files,
        'count': len(summary_files)
    }
    logger.info(f"요약 결과 파일: {len(summary_files)}개 발견")
    
    # 4. SaveSQLToDB 결과 확인
    sqllist_files = glob.glob(os.path.join(paths['sqllist_dir'], 'sqllist_*.csv'))
    sources['sqllist_exports'] = {
        'available': len(sqllist_files) > 0,
        'files': sqllist_files,
        'count': len(sqllist_files)
    }
    logger.info(f"SQLList 내보내기 파일: {len(sqllist_files)}개 발견")
    
    return sources
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
            sys.exit(1)
        
        # 데이터베이스 연결
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=pg_database,
            user=pg_user,
            password=pg_password
        )
        
        return conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 오류: {e}")
        raise

def load_database_results(stmt_type=None, app_name=None, limit=100):
    """데이터베이스에서 차이 결과를 로드합니다."""
    conn = get_db_connection()
    
    try:
        query = """
            SELECT sql_id, app_name, stmt_type, orcl_file_path, pg_file_path,
                   orcl, pg, orcl_result, pg_result, same
            FROM sqllist
            WHERE same = 'N'
        """
        params = []
        
        if stmt_type:
            query += " AND stmt_type = %s"
            params.append(stmt_type)
        
        if app_name:
            query += " AND app_name = %s"
            params.append(app_name)
        
        query += " ORDER BY sql_id, app_name LIMIT %s"
        params.append(limit)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
        
        logger.info(f"데이터베이스에서 {len(results)}개 결과 로드")
        return [dict(row) for row in results]
        
    finally:
        conn.close()

def load_csv_results(use_latest=False, stmt_type=None):
    """ExecuteAndCompareSQL CSV 결과를 로드합니다."""
    paths = get_paths()
    csv_dir = paths['sql_results_csv_dir']
    
    if not os.path.exists(csv_dir):
        logger.warning(f"CSV 디렉토리가 존재하지 않습니다: {csv_dir}")
        return []
    
    # CSV 파일 목록 가져오기
    pattern = 'sql_comparison_results_*.csv'
    if stmt_type:
        pattern = f'sql_comparison_results_{stmt_type}_*.csv'
    
    csv_files = glob.glob(os.path.join(csv_dir, pattern))
    
    if not csv_files:
        logger.warning("CSV 결과 파일을 찾을 수 없습니다.")
        return []
    
    # 최신 파일 사용 또는 모든 파일 사용
    if use_latest:
        csv_files = [max(csv_files, key=os.path.getctime)]
        logger.info(f"최신 CSV 파일 사용: {os.path.basename(csv_files[0])}")
    else:
        logger.info(f"{len(csv_files)}개 CSV 파일 로드")
    
    all_results = []
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                file_results = []
                for row in reader:
                    if row.get('same') == 'N':  # 차이가 있는 결과만
                        row['source_file'] = os.path.basename(csv_file)
                        file_results.append(row)
                all_results.extend(file_results)
                logger.debug(f"{csv_file}: {len(file_results)}개 차이 결과")
        except Exception as e:
            logger.error(f"CSV 파일 읽기 오류 {csv_file}: {e}")
    
    logger.info(f"총 {len(all_results)}개 CSV 결과 로드")
    return all_results

def load_summary_data():
    """ExecuteAndCompareSQL 요약 데이터를 로드합니다."""
    paths = get_paths()
    summary_dir = paths['sql_results_summary_dir']
    
    summary_files = glob.glob(os.path.join(summary_dir, 'detailed_analysis_*.json'))
    
    if not summary_files:
        logger.warning("요약 데이터 파일을 찾을 수 없습니다.")
        return {}
    
    # 최신 요약 파일 사용
    latest_file = max(summary_files, key=os.path.getctime)
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        logger.info(f"요약 데이터 로드: {os.path.basename(latest_file)}")
        return summary_data
    except Exception as e:
        logger.error(f"요약 데이터 로드 오류: {e}")
        return {}

def analyze_difference(orcl_result, pg_result, additional_info=None):
    """Oracle과 PostgreSQL 결과의 차이를 분석합니다."""
    if not orcl_result or not pg_result:
        return {
            'type': 'error',
            'description': '결과 없음',
            'oracle_empty': not orcl_result,
            'postgres_empty': not pg_result
        }
    
    # 오류 확인
    if orcl_result.startswith("ERROR:") or pg_result.startswith("ERROR:"):
        error_info = {
            'type': 'error',
            'description': '실행 오류',
            'oracle_error': orcl_result.startswith("ERROR:"),
            'postgres_error': pg_result.startswith("ERROR:")
        }
        
        if additional_info:
            error_info['oracle_error_detail'] = additional_info.get('orcl_error', '')
            error_info['postgres_error_detail'] = additional_info.get('pg_error', '')
            error_info['execution_time'] = additional_info.get('execution_time', 0)
        
        return error_info
    
    # 타임아웃 확인
    if 'timeout' in orcl_result.lower() or 'timeout' in pg_result.lower():
        return {
            'type': 'timeout',
            'description': '실행 타임아웃',
            'oracle_timeout': 'timeout' in orcl_result.lower(),
            'postgres_timeout': 'timeout' in pg_result.lower()
        }
    
    # 결과를 줄 단위로 분리
    orcl_lines = orcl_result.strip().split('\n')
    pg_lines = pg_result.strip().split('\n')
    
    # 줄 수 차이 확인
    if len(orcl_lines) != len(pg_lines):
        return {
            'type': 'other',
            'description': '결과 행 수 차이',
            'oracle_count': len(orcl_lines),
            'postgres_count': len(pg_lines),
            'diff_html': get_diff_html(orcl_result, pg_result)
        }
    
    # 날짜 형식 차이 확인
    date_pattern = r'\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?'
    orcl_dates = re.findall(date_pattern, orcl_result)
    pg_dates = re.findall(date_pattern, pg_result)
    
    if orcl_dates or pg_dates:
        if len(orcl_dates) != len(pg_dates) or orcl_dates != pg_dates:
            return {
                'type': 'date_format',
                'description': '날짜 형식 차이',
                'oracle_dates': orcl_dates[:3],  # 처음 3개만
                'postgres_dates': pg_dates[:3],
                'diff_html': get_diff_html(orcl_result, pg_result)
            }
    
    # NULL 처리 차이 확인
    orcl_nulls = orcl_result.count('NULL')
    pg_nulls = pg_result.count('NULL')
    
    if orcl_nulls != pg_nulls:
        return {
            'type': 'null_handling',
            'description': 'NULL 처리 차이',
            'oracle_null_count': orcl_nulls,
            'postgres_null_count': pg_nulls,
            'diff_html': get_diff_html(orcl_result, pg_result)
        }
    
    # 대소문자 구분 차이 확인
    if orcl_result.lower() == pg_result.lower() and orcl_result != pg_result:
        return {
            'type': 'case_sensitivity',
            'description': '대소문자 구분 차이',
            'diff_html': get_diff_html(orcl_result, pg_result)
        }
    
    # 공백 차이 확인
    orcl_no_space = re.sub(r'\s+', '', orcl_result)
    pg_no_space = re.sub(r'\s+', '', pg_result)
    if orcl_no_space == pg_no_space and orcl_result != pg_result:
        return {
            'type': 'whitespace',
            'description': '공백 차이',
            'diff_html': get_diff_html(orcl_result, pg_result)
        }
    
    # 숫자 정밀도 차이 확인
    number_pattern = r'\d+\.\d+'
    orcl_numbers = re.findall(number_pattern, orcl_result)
    pg_numbers = re.findall(number_pattern, pg_result)
    
    if orcl_numbers and pg_numbers and len(orcl_numbers) == len(pg_numbers):
        precision_diff = False
        for o_num, p_num in zip(orcl_numbers, pg_numbers):
            if abs(float(o_num) - float(p_num)) > 0.0001:  # 소수점 4자리 이하 차이
                precision_diff = True
                break
        
        if precision_diff:
            return {
                'type': 'data_type',
                'description': '숫자 정밀도 차이',
                'oracle_numbers': orcl_numbers[:3],
                'postgres_numbers': pg_numbers[:3],
                'diff_html': get_diff_html(orcl_result, pg_result)
            }
    
    # 성능 차이 (추가 정보가 있는 경우)
    if additional_info and 'execution_time' in additional_info:
        exec_time = float(additional_info['execution_time'])
        if exec_time > 10:  # 10초 이상
            return {
                'type': 'performance',
                'description': '성능 차이 (실행 시간 10초 이상)',
                'execution_time': exec_time,
                'diff_html': get_diff_html(orcl_result, pg_result)
            }
    
    # 기타 차이
    return {
        'type': 'other',
        'description': '기타 차이',
        'diff_html': get_diff_html(orcl_result, pg_result),
        'oracle_length': len(orcl_result),
        'postgres_length': len(pg_result)
    }

def get_diff_html(text1, text2):
    """두 텍스트의 차이를 HTML로 생성합니다."""
    diff = difflib.unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile='Oracle',
        tofile='PostgreSQL',
        lineterm=''
    )
    
    html_diff = []
    for line in diff:
        line = html.escape(line)
        if line.startswith('+++') or line.startswith('---'):
            html_diff.append(f'<div class="diff-header">{line}</div>')
        elif line.startswith('@@'):
            html_diff.append(f'<div class="diff-range">{line}</div>')
        elif line.startswith('+'):
            html_diff.append(f'<div class="diff-add">{line}</div>')
        elif line.startswith('-'):
            html_diff.append(f'<div class="diff-remove">{line}</div>')
        else:
            html_diff.append(f'<div class="diff-context">{line}</div>')
    
    return '\n'.join(html_diff)
def merge_data_sources(db_results, csv_results):
    """데이터베이스와 CSV 결과를 병합합니다."""
    merged_results = []
    
    # CSV 결과를 키로 인덱싱
    csv_index = {}
    for csv_row in csv_results:
        key = f"{csv_row.get('sql_id', '')}_{csv_row.get('app_name', '')}_{csv_row.get('stmt_type', '')}"
        csv_index[key] = csv_row
    
    # 데이터베이스 결과를 기준으로 병합
    for db_row in db_results:
        key = f"{db_row['sql_id']}_{db_row['app_name']}_{db_row['stmt_type']}"
        
        merged_row = dict(db_row)  # 데이터베이스 데이터를 기본으로
        
        # CSV 데이터가 있으면 추가 정보 병합
        if key in csv_index:
            csv_row = csv_index[key]
            merged_row.update({
                'execution_time': csv_row.get('execution_time', '0'),
                'orcl_error': csv_row.get('orcl_error', ''),
                'pg_error': csv_row.get('pg_error', ''),
                'source_file': csv_row.get('source_file', ''),
                'orcl_result_status': csv_row.get('orcl_result_status', ''),
                'pg_result_status': csv_row.get('pg_result_status', '')
            })
        
        merged_results.append(merged_row)
    
    logger.info(f"데이터 병합 완료: {len(merged_results)}개 결과")
    return merged_results

def generate_comprehensive_analysis(results, summary_data=None):
    """종합적인 분석을 수행합니다."""
    analysis = {
        'total_count': len(results),
        'analysis_timestamp': datetime.now().isoformat(),
        'difference_types': Counter(),
        'app_statistics': defaultdict(lambda: {'total': 0, 'types': Counter()}),
        'stmt_type_statistics': defaultdict(lambda: {'total': 0, 'types': Counter()}),
        'error_analysis': {
            'oracle_errors': 0,
            'postgres_errors': 0,
            'both_errors': 0,
            'timeouts': 0
        },
        'performance_analysis': {
            'slow_queries': [],  # 실행 시간 > 5초
            'avg_execution_time': 0,
            'max_execution_time': 0
        },
        'recommendations': []
    }
    
    total_execution_time = 0
    execution_times = []
    
    # 각 결과 분석
    for result in results:
        # 차이 분석 수행
        additional_info = {
            'execution_time': result.get('execution_time', '0'),
            'orcl_error': result.get('orcl_error', ''),
            'pg_error': result.get('pg_error', '')
        }
        
        diff_analysis = analyze_difference(
            result.get('orcl_result', ''),
            result.get('pg_result', ''),
            additional_info
        )
        
        result['analysis'] = diff_analysis
        
        # 통계 업데이트
        diff_type = diff_analysis['type']
        analysis['difference_types'][diff_type] += 1
        
        app_name = result.get('app_name', 'unknown')
        stmt_type = result.get('stmt_type', 'unknown')
        
        analysis['app_statistics'][app_name]['total'] += 1
        analysis['app_statistics'][app_name]['types'][diff_type] += 1
        
        analysis['stmt_type_statistics'][stmt_type]['total'] += 1
        analysis['stmt_type_statistics'][stmt_type]['types'][diff_type] += 1
        
        # 오류 분석
        if diff_type == 'error':
            if diff_analysis.get('oracle_error') and diff_analysis.get('postgres_error'):
                analysis['error_analysis']['both_errors'] += 1
            elif diff_analysis.get('oracle_error'):
                analysis['error_analysis']['oracle_errors'] += 1
            elif diff_analysis.get('postgres_error'):
                analysis['error_analysis']['postgres_errors'] += 1
        elif diff_type == 'timeout':
            analysis['error_analysis']['timeouts'] += 1
        
        # 성능 분석
        try:
            exec_time = float(result.get('execution_time', '0'))
            execution_times.append(exec_time)
            total_execution_time += exec_time
            
            if exec_time > 5:  # 5초 이상
                analysis['performance_analysis']['slow_queries'].append({
                    'sql_id': result.get('sql_id'),
                    'app_name': app_name,
                    'execution_time': exec_time
                })
        except (ValueError, TypeError):
            pass
    
    # 성능 통계 계산
    if execution_times:
        analysis['performance_analysis']['avg_execution_time'] = total_execution_time / len(execution_times)
        analysis['performance_analysis']['max_execution_time'] = max(execution_times)
    
    # 권장사항 생성
    analysis['recommendations'] = generate_recommendations(analysis)
    
    # 요약 데이터와 비교 (트렌드 분석)
    if summary_data:
        analysis['trend_analysis'] = compare_with_previous_analysis(analysis, summary_data)
    
    logger.info("종합 분석 완료")
    return analysis

def generate_recommendations(analysis):
    """분석 결과를 바탕으로 권장사항을 생성합니다."""
    recommendations = []
    
    # 차이 유형별 권장사항
    diff_types = analysis['difference_types']
    
    if diff_types.get('date_format', 0) > 0:
        recommendations.append({
            'type': 'date_format',
            'priority': 'high',
            'title': '날짜 형식 통일 필요',
            'description': f"{diff_types['date_format']}개의 SQL에서 날짜 형식 차이가 발견되었습니다.",
            'solution': "TO_CHAR() 함수를 사용하여 날짜 형식을 통일하거나, 애플리케이션 레벨에서 날짜 형식을 처리하세요."
        })
    
    if diff_types.get('null_handling', 0) > 0:
        recommendations.append({
            'type': 'null_handling',
            'priority': 'medium',
            'title': 'NULL 처리 로직 검토',
            'description': f"{diff_types['null_handling']}개의 SQL에서 NULL 처리 차이가 발견되었습니다.",
            'solution': "COALESCE() 함수나 CASE 문을 사용하여 NULL 처리를 명시적으로 정의하세요."
        })
    
    if diff_types.get('case_sensitivity', 0) > 0:
        recommendations.append({
            'type': 'case_sensitivity',
            'priority': 'low',
            'title': '대소문자 처리 통일',
            'description': f"{diff_types['case_sensitivity']}개의 SQL에서 대소문자 차이가 발견되었습니다.",
            'solution': "UPPER() 또는 LOWER() 함수를 사용하여 대소문자를 통일하세요."
        })
    
    if diff_types.get('error', 0) > 0:
        recommendations.append({
            'type': 'error',
            'priority': 'critical',
            'title': 'SQL 오류 수정 필요',
            'description': f"{diff_types['error']}개의 SQL에서 실행 오류가 발생했습니다.",
            'solution': "오류 메시지를 확인하고 SQL 구문을 PostgreSQL 호환 형태로 수정하세요."
        })
    
    # 성능 관련 권장사항
    slow_queries_count = len(analysis['performance_analysis']['slow_queries'])
    if slow_queries_count > 0:
        recommendations.append({
            'type': 'performance',
            'priority': 'medium',
            'title': '성능 최적화 필요',
            'description': f"{slow_queries_count}개의 SQL이 5초 이상 실행되었습니다.",
            'solution': "인덱스 추가, 쿼리 최적화, 또는 데이터 파티셔닝을 고려하세요."
        })
    
    return recommendations

def compare_with_previous_analysis(current_analysis, previous_summary):
    """이전 분석 결과와 비교하여 트렌드를 분석합니다."""
    trend_analysis = {
        'comparison_available': True,
        'improvements': [],
        'regressions': [],
        'new_issues': []
    }
    
    try:
        prev_stats = previous_summary.get('statistics', {})
        current_total = current_analysis['total_count']
        prev_total = prev_stats.get('total_sql_count', 0)
        
        if prev_total > 0:
            # 전체 차이 비율 변화
            current_diff_rate = current_total
            prev_diff_rate = prev_total
            
            if current_diff_rate < prev_diff_rate:
                trend_analysis['improvements'].append(
                    f"차이 발생 SQL 수가 {prev_diff_rate - current_diff_rate}개 감소했습니다."
                )
            elif current_diff_rate > prev_diff_rate:
                trend_analysis['regressions'].append(
                    f"차이 발생 SQL 수가 {current_diff_rate - prev_diff_rate}개 증가했습니다."
                )
        
        # 차이 유형별 변화 분석
        prev_type_stats = previous_summary.get('type_statistics', {})
        for diff_type, count in current_analysis['difference_types'].items():
            prev_count = prev_type_stats.get(diff_type, {}).get('count', 0)
            if prev_count == 0 and count > 0:
                trend_analysis['new_issues'].append(f"새로운 {DIFFERENCE_TYPES.get(diff_type, diff_type)} 문제가 {count}개 발견되었습니다.")
            elif prev_count > count:
                trend_analysis['improvements'].append(f"{DIFFERENCE_TYPES.get(diff_type, diff_type)} 문제가 {prev_count - count}개 해결되었습니다.")
            elif prev_count < count:
                trend_analysis['regressions'].append(f"{DIFFERENCE_TYPES.get(diff_type, diff_type)} 문제가 {count - prev_count}개 증가했습니다.")
    
    except Exception as e:
        logger.warning(f"트렌드 분석 중 오류: {e}")
        trend_analysis['comparison_available'] = False
    
    return trend_analysis

def save_json_report(analysis, results, output_path):
    """JSON 형식으로 분석 결과를 저장합니다."""
    report_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_analyzed': len(results),
            'analysis_version': '2.0'
        },
        'summary': analysis,
        'detailed_results': []
    }
    
    # 상세 결과 추가 (처음 100개만)
    for result in results[:100]:
        detailed_result = {
            'sql_id': result.get('sql_id'),
            'app_name': result.get('app_name'),
            'stmt_type': result.get('stmt_type'),
            'analysis': result.get('analysis', {}),
            'execution_time': result.get('execution_time', '0'),
            'has_oracle_error': result.get('orcl_error', '') != '',
            'has_postgres_error': result.get('pg_error', '') != ''
        }
        report_data['detailed_results'].append(detailed_result)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"JSON 보고서 저장: {output_path}")

def save_csv_report(analysis, results, output_path):
    """CSV 형식으로 분석 결과를 저장합니다."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'sql_id', 'app_name', 'stmt_type', 'difference_type', 'difference_description',
            'execution_time', 'oracle_error', 'postgres_error', 'recommendation'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            analysis_result = result.get('analysis', {})
            writer.writerow({
                'sql_id': result.get('sql_id', ''),
                'app_name': result.get('app_name', ''),
                'stmt_type': result.get('stmt_type', ''),
                'difference_type': analysis_result.get('type', ''),
                'difference_description': analysis_result.get('description', ''),
                'execution_time': result.get('execution_time', '0'),
                'oracle_error': result.get('orcl_error', ''),
                'postgres_error': result.get('pg_error', ''),
                'recommendation': get_recommendation_for_type(analysis_result.get('type', ''))
            })
    
    logger.info(f"CSV 보고서 저장: {output_path}")

def get_recommendation_for_type(diff_type):
    """차이 유형에 따른 권장사항을 반환합니다."""
    recommendations = {
        'date_format': 'TO_CHAR() 함수로 날짜 형식 통일',
        'null_handling': 'COALESCE() 함수로 NULL 처리',
        'case_sensitivity': 'UPPER()/LOWER() 함수로 대소문자 통일',
        'whitespace': '문자열 함수로 공백 처리',
        'error': 'SQL 구문을 PostgreSQL 호환으로 수정',
        'performance': '인덱스 추가 또는 쿼리 최적화',
        'timeout': '쿼리 복잡도 감소 또는 타임아웃 설정 조정'
    }
    return recommendations.get(diff_type, '상세 분석 필요')
def generate_html_report(analysis, results, output_path):
    """HTML 형식으로 종합 보고서를 생성합니다."""
    
    # CSS 스타일 생성
    css_styles = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        h3 { color: #7f8c8d; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .summary-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card h3 { color: white; margin: 0 0 10px 0; }
        .summary-card .number { font-size: 2em; font-weight: bold; }
        .chart-container { margin: 30px 0; text-align: center; }
        .recommendations { background-color: #ecf0f1; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .recommendation { margin: 10px 0; padding: 15px; border-left: 4px solid #3498db; background-color: white; }
        .recommendation.critical { border-left-color: #e74c3c; }
        .recommendation.high { border-left-color: #f39c12; }
        .recommendation.medium { border-left-color: #f1c40f; }
        .recommendation.low { border-left-color: #2ecc71; }
        .sql-item { margin: 20px 0; padding: 20px; border: 1px solid #bdc3c7; border-radius: 8px; background-color: #fafafa; }
        .sql-header { background-color: #34495e; color: white; padding: 10px; margin: -20px -20px 15px -20px; border-radius: 8px 8px 0 0; }
        .sql-content { background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px; overflow-x: auto; margin: 10px 0; }
        .result-diff { background-color: white; border: 1px solid #bdc3c7; padding: 15px; border-radius: 4px; margin: 10px 0; }
        .diff-header { font-weight: bold; color: #2c3e50; }
        .diff-add { background-color: #d5f4e6; color: #27ae60; }
        .diff-remove { background-color: #fadbd8; color: #e74c3c; }
        .diff-context { color: #7f8c8d; }
        .diff-range { background-color: #ebf3fd; color: #3498db; font-weight: bold; }
        .stats-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .stats-table th, .stats-table td { border: 1px solid #bdc3c7; padding: 12px; text-align: left; }
        .stats-table th { background-color: #34495e; color: white; }
        .stats-table tr:nth-child(even) { background-color: #f8f9fa; }
        .trend-analysis { background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .trend-improvement { color: #27ae60; font-weight: bold; }
        .trend-regression { color: #e74c3c; font-weight: bold; }
        .trend-new { color: #f39c12; font-weight: bold; }
        .performance-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 10px 0; }
    </style>
    """
    
    # HTML 시작
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Oracle vs PostgreSQL 결과 차이 분석 보고서</title>
        {css_styles}
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="container">
            <h1>Oracle vs PostgreSQL 결과 차이 분석 보고서</h1>
            <p><strong>생성 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>분석 대상:</strong> {analysis['total_count']}개 SQL 문</p>
    """
    
    # 요약 카드들
    html_content += """
            <div class="summary-grid">
    """
    
    # 차이 유형별 카드
    for diff_type, count in analysis['difference_types'].most_common(4):
        type_name = DIFFERENCE_TYPES.get(diff_type, diff_type)
        html_content += f"""
                <div class="summary-card">
                    <h3>{type_name}</h3>
                    <div class="number">{count}</div>
                </div>
        """
    
    html_content += """
            </div>
    """
    
    # 차트
    html_content += """
            <div class="chart-container">
                <h2>차이 유형별 분포</h2>
                <canvas id="diffTypeChart" width="400" height="200"></canvas>
            </div>
    """
    
    # 권장사항
    if analysis['recommendations']:
        html_content += """
            <div class="recommendations">
                <h2>권장사항</h2>
        """
        
        for rec in analysis['recommendations']:
            priority_class = rec.get('priority', 'medium')
            html_content += f"""
                <div class="recommendation {priority_class}">
                    <h3>{rec['title']}</h3>
                    <p>{rec['description']}</p>
                    <p><strong>해결방안:</strong> {rec['solution']}</p>
                </div>
            """
        
        html_content += """
            </div>
        """
    
    # 트렌드 분석
    if 'trend_analysis' in analysis and analysis['trend_analysis']['comparison_available']:
        trend = analysis['trend_analysis']
        html_content += """
            <div class="trend-analysis">
                <h2>트렌드 분석</h2>
        """
        
        if trend['improvements']:
            html_content += "<h3>개선사항</h3><ul>"
            for improvement in trend['improvements']:
                html_content += f'<li class="trend-improvement">{improvement}</li>'
            html_content += "</ul>"
        
        if trend['regressions']:
            html_content += "<h3>악화사항</h3><ul>"
            for regression in trend['regressions']:
                html_content += f'<li class="trend-regression">{regression}</li>'
            html_content += "</ul>"
        
        if trend['new_issues']:
            html_content += "<h3>신규 문제</h3><ul>"
            for issue in trend['new_issues']:
                html_content += f'<li class="trend-new">{issue}</li>'
            html_content += "</ul>"
        
        html_content += """
            </div>
        """
    
    # 애플리케이션별 통계
    html_content += """
            <h2>애플리케이션별 통계</h2>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>애플리케이션</th>
                        <th>총 차이 수</th>
                        <th>주요 차이 유형</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for app_name, stats in analysis['app_statistics'].items():
        top_type = stats['types'].most_common(1)
        top_type_name = DIFFERENCE_TYPES.get(top_type[0][0], top_type[0][0]) if top_type else 'N/A'
        html_content += f"""
                    <tr>
                        <td>{app_name}</td>
                        <td>{stats['total']}</td>
                        <td>{top_type_name}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
    """
    
    # 성능 분석
    perf_analysis = analysis['performance_analysis']
    if perf_analysis['slow_queries']:
        html_content += f"""
            <h2>성능 분석</h2>
            <div class="performance-warning">
                <h3>느린 쿼리 감지</h3>
                <p>{len(perf_analysis['slow_queries'])}개의 쿼리가 5초 이상 실행되었습니다.</p>
                <p><strong>평균 실행 시간:</strong> {perf_analysis['avg_execution_time']:.2f}초</p>
                <p><strong>최대 실행 시간:</strong> {perf_analysis['max_execution_time']:.2f}초</p>
            </div>
        """
    
    # 상세 결과 (처음 20개만)
    html_content += """
            <h2>상세 분석 결과 (상위 20개)</h2>
    """
    
    for i, result in enumerate(results[:20], 1):
        analysis_result = result.get('analysis', {})
        diff_type = analysis_result.get('type', 'unknown')
        diff_desc = analysis_result.get('description', 'N/A')
        
        html_content += f"""
            <div class="sql-item">
                <div class="sql-header">
                    <h3>#{i} SQL ID: {result.get('sql_id', 'N/A')}, App: {result.get('app_name', 'N/A')} ({STMT_TYPES.get(result.get('stmt_type', ''), 'Unknown')})</h3>
                    <p><strong>차이 유형:</strong> {DIFFERENCE_TYPES.get(diff_type, diff_type)} - {diff_desc}</p>
                    <p><strong>실행 시간:</strong> {result.get('execution_time', '0')}초</p>
                </div>
        """
        
        # Oracle SQL
        if result.get('orcl'):
            html_content += f"""
                <h4>Oracle SQL</h4>
                <div class="sql-content">{html.escape(result['orcl'][:500])}{'...' if len(result['orcl']) > 500 else ''}</div>
            """
        
        # PostgreSQL SQL
        if result.get('pg'):
            html_content += f"""
                <h4>PostgreSQL SQL</h4>
                <div class="sql-content">{html.escape(result['pg'][:500])}{'...' if len(result['pg']) > 500 else ''}</div>
            """
        
        # 차이 분석 결과
        if analysis_result.get('diff_html'):
            html_content += f"""
                <h4>결과 차이</h4>
                <div class="result-diff">{analysis_result['diff_html']}</div>
            """
        
        html_content += """
            </div>
        """
    
    # 차트 스크립트
    chart_labels = [DIFFERENCE_TYPES.get(dt, dt) for dt in analysis['difference_types'].keys()]
    chart_data = list(analysis['difference_types'].values())
    
    html_content += f"""
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const ctx = document.getElementById('diffTypeChart').getContext('2d');
                    const diffTypeChart = new Chart(ctx, {{
                        type: 'doughnut',
                        data: {{
                            labels: {json.dumps(chart_labels)},
                            datasets: [{{
                                label: '차이 유형별 개수',
                                data: {json.dumps(chart_data)},
                                backgroundColor: [
                                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                                    '#4BC0C0', '#FF6384'
                                ]
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{
                                    position: 'bottom'
                                }},
                                title: {{
                                    display: true,
                                    text: '차이 유형별 분포'
                                }}
                            }}
                        }}
                    }});
                }});
            </script>
        </div>
    </body>
    </html>
    """
    
    # HTML 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"HTML 보고서 저장: {output_path}")

def parse_arguments():
    """명령줄 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(description='Oracle과 PostgreSQL 쿼리 결과 차이를 종합 분석합니다.')
    parser.add_argument('-t', '--type', help='SQL 문 타입으로 필터링 (S: Select, I: Insert 등)')
    parser.add_argument('-a', '--app', help='애플리케이션 이름으로 필터링')
    parser.add_argument('-l', '--limit', type=int, default=100, help='분석할 결과 수 제한 (기본값: 100)')
    parser.add_argument('-f', '--format', choices=['html', 'json', 'csv', 'all'], default='html', 
                       help='출력 형식 (기본값: html)')
    parser.add_argument('--use-latest', action='store_true', 
                       help='최신 ExecuteAndCompareSQL 결과만 사용')
    return parser.parse_args()

def main():
    """메인 실행 함수"""
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 디렉토리 설정
    setup_directories()
    
    # 경로 정보 출력
    paths = get_paths()
    logger.info("경로 설정:")
    logger.info(f"  입력 - SQL 결과: {paths['sql_results_dir']}")
    logger.info(f"  입력 - SQLList: {paths['sqllist_dir']}")
    logger.info(f"  출력 - 분석 결과: {paths['analysis_results_dir']}")
    logger.info(f"  로그 디렉토리: {paths['logs_dir']}")
    
    # 입력 소스 확인
    logger.info("입력 소스 확인 중...")
    sources = get_input_sources()
    
    if not sources['database']['available']:
        logger.error("데이터베이스에 접근할 수 없습니다.")
        return
    
    if sources['database']['different_results_count'] == 0:
        logger.warning("분석할 차이 결과가 없습니다.")
        return
    
    try:
        # 데이터 로드
        logger.info("데이터 로드 중...")
        
        # 1. 데이터베이스에서 기본 데이터 로드
        db_results = load_database_results(args.type, args.app, args.limit)
        
        # 2. CSV 결과 로드 (추가 정보)
        csv_results = []
        if sources['csv_results']['available']:
            csv_results = load_csv_results(args.use_latest, args.type)
        
        # 3. 요약 데이터 로드 (트렌드 분석용)
        summary_data = {}
        if sources['summary_results']['available']:
            summary_data = load_summary_data()
        
        # 데이터 병합
        logger.info("데이터 병합 중...")
        merged_results = merge_data_sources(db_results, csv_results)
        
        if not merged_results:
            logger.warning("분석할 데이터가 없습니다.")
            return
        
        # 종합 분석 수행
        logger.info("종합 분석 수행 중...")
        analysis = generate_comprehensive_analysis(merged_results, summary_data)
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_suffix = f"_{args.type}" if args.type else ""
        app_suffix = f"_{args.app}" if args.app else ""
        
        # 출력 형식에 따라 보고서 생성
        if args.format in ['html', 'all']:
            html_path = os.path.join(paths['html_dir'], f"difference_analysis{type_suffix}{app_suffix}_{timestamp}.html")
            generate_html_report(analysis, merged_results, html_path)
        
        if args.format in ['json', 'all']:
            json_path = os.path.join(paths['json_dir'], f"analysis_data{type_suffix}{app_suffix}_{timestamp}.json")
            save_json_report(analysis, merged_results, json_path)
        
        if args.format in ['csv', 'all']:
            csv_path = os.path.join(paths['csv_dir'], f"difference_summary{type_suffix}{app_suffix}_{timestamp}.csv")
            save_csv_report(analysis, merged_results, csv_path)
        
        # 최종 요약 출력
        logger.info("=" * 60)
        logger.info("분석 완료")
        logger.info("=" * 60)
        logger.info(f"총 분석 SQL 수: {analysis['total_count']}")
        logger.info(f"주요 차이 유형: {', '.join([DIFFERENCE_TYPES.get(dt, dt) for dt in analysis['difference_types'].most_common(3)])}")
        logger.info(f"권장사항 수: {len(analysis['recommendations'])}")
        
        if analysis['performance_analysis']['slow_queries']:
            logger.warning(f"느린 쿼리 {len(analysis['performance_analysis']['slow_queries'])}개 발견")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"분석 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    # 환경 변수 확인
    check_environment_variables()
    
    # 로깅 설정
    logger = setup_logging()
    
    try:
        # 메인 실행
        main()
        logger.info("AnalyzeResult 실행 완료")
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {str(e)}")
        raise
