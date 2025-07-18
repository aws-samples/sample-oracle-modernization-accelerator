#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
다중 DB 에러 유형 분석 스크립트
타겟 DB(PostgreSQL/MySQL) 실행 결과에서 에러 유형을 분석하고 분류합니다.

사용법:
  python3 analyze_db_errors.py                    # 전체 에러 분석
  python3 analyze_db_errors.py --missing=t        # 누락된 테이블 분석
  python3 analyze_db_errors.py --missing=s        # 누락된 스키마 분석
  python3 analyze_db_errors.py --missing=f        # 누락된 함수 분석
  python3 analyze_db_errors.py --missing=o        # 누락된 오퍼레이터 분석
"""

import re
import json
import sys
import os
import argparse
from collections import defaultdict, Counter
from datetime import datetime
import subprocess

def check_environment_variables():
    """환경 변수가 설정되어 있는지 확인합니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    if target_dbms in ['postgres', 'postgresql']:
        required_vars = ['PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD']
    elif target_dbms == 'mysql':
        required_vars = ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD']
    else:
        print(f"지원하지 않는 TARGET_DBMS_TYPE: {target_dbms}")
        print("지원되는 타입: postgres, postgresql, mysql")
        return False
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"다음 환경 변수들이 설정되지 않았습니다: {', '.join(missing_vars)}")
        return False
    
    return True

def execute_db_query(query):
    """TARGET_DBMS_TYPE에 따라 데이터베이스 쿼리를 실행합니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    try:
        if target_dbms in ['postgres', 'postgresql']:
            # PostgreSQL 쿼리 실행
            pg_host = os.environ.get('PGHOST')
            pg_port = os.environ.get('PGPORT')
            pg_database = os.environ.get('PGDATABASE')
            pg_user = os.environ.get('PGUSER')
            
            cmd = ['psql', '-h', pg_host, '-p', pg_port, '-d', pg_database, '-U', pg_user, '-c', query]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
            
        elif target_dbms == 'mysql':
            # MySQL 쿼리 실행
            mysql_host = os.environ.get('MYSQL_HOST')
            mysql_port = os.environ.get('MYSQL_PORT')
            mysql_database = os.environ.get('MYSQL_DATABASE')
            mysql_user = os.environ.get('MYSQL_USER')
            mysql_password = os.environ.get('MYSQL_PASSWORD')
            
            cmd = ['mysql', '-h', mysql_host, '-P', mysql_port, '-u', mysql_user, f'-p{mysql_password}', '-D', mysql_database, '-e', query]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
            
    except subprocess.CalledProcessError as e:
        print(f"{target_dbms.upper()} 쿼리 실행 오류: {e}")
        return ""

def get_db_errors():
    """타겟 DB 에러 결과를 가져옵니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    if target_dbms in ['postgres', 'postgresql']:
        # PostgreSQL 에러 쿼리
        query = """
        select tgt_file_path, tgt_result 
        from sqllist 
        where sql_id != 'retrieveCsrBatchJobMst.csrBatchJobRegDao.retrieveCsrBatchJobMst' 
        and same='N' 
        and tgt_result like '%ERROR%' 
        and tgt_result not like '%ERROR:  schema%' 
        and tgt_result not like '%ERROR:  relation%' 
        and tgt_result not like '%ERROR:  operator%' 
        and tgt_result not like '%ERROR:  function%';
        """
    elif target_dbms == 'mysql':
        # MySQL 에러 쿼리
        query = """
        select tgt_file_path, tgt_result 
        from sqllist 
        where sql_id != 'retrieveCsrBatchJobMst.csrBatchJobRegDao.retrieveCsrBatchJobMst' 
        and same='N' 
        and tgt_result like '%ERROR%' 
        and tgt_result not like '%ERROR:  schema%' 
        and tgt_result not like '%ERROR:  relation%' 
        and tgt_result not like '%ERROR:  operator%' 
        and tgt_result not like '%ERROR:  function%';
        """
    
    return execute_db_query(query)

def get_all_db_errors():
    """모든 타겟 DB 에러 결과를 파일 경로와 함께 가져옵니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    if target_dbms in ['postgres', 'postgresql']:
        query = """
        select tgt_file_path, tgt_result 
        from sqllist 
        where sql_id != 'retrieveCsrBatchJobMst.csrBatchJobRegDao.retrieveCsrBatchJobMst' 
        and same='N' 
        and tgt_result like '%ERROR%';
        """
    elif target_dbms == 'mysql':
        query = """
        select tgt_file_path, tgt_result 
        from sqllist 
        where sql_id != 'retrieveCsrBatchJobMst.csrBatchJobRegDao.retrieveCsrBatchJobMst' 
        and same='N' 
        and tgt_result like '%ERROR%';
        """
    
    return execute_db_query(query)

def parse_error_data(db_output):
    """데이터베이스 출력에서 파일 경로와 에러를 파싱합니다."""
    lines = db_output.strip().split('\n')
    error_data = []
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    for line in lines:
        # PostgreSQL과 MySQL 모두 탭으로 구분되거나 |로 구분될 수 있음
        if '\t' in line and 'ERROR' in line:
            parts = line.split('\t', 1)
        elif '|' in line and 'ERROR' in line:
            parts = line.split('|', 1)
        else:
            continue
            
        if len(parts) == 2:
            file_path = parts[0].strip()
            error_result = parts[1].strip()
            
            # ERROR: 로 시작하는 에러 메시지 추출
            if target_dbms in ['postgres', 'postgresql']:
                error_matches = re.findall(r'ERROR:\s*([^\n]+)', error_result)
            elif target_dbms == 'mysql':
                # MySQL은 ERROR 1234 (HY000): 형태
                error_matches = re.findall(r'ERROR \d+.*?:\s*([^\n]+)', error_result)
                if not error_matches:
                    # 일반적인 ERROR: 형태도 처리
                    error_matches = re.findall(r'ERROR:\s*([^\n]+)', error_result)
            
            for error_msg in error_matches:
                # 파일 경로와 라인 번호 제거
                if target_dbms in ['postgres', 'postgresql']:
                    clean_error = re.sub(r'^psql:[^:]+:\d+:\s*', '', error_msg)
                    clean_error = re.sub(r'^ERROR:\s*', '', clean_error)
                elif target_dbms == 'mysql':
                    clean_error = re.sub(r'^mysql:[^:]+:\d+:\s*', '', error_msg)
                    clean_error = re.sub(r'^ERROR \d+.*?:\s*', '', clean_error)
                
                error_data.append({
                    'file_path': file_path,
                    'error': clean_error.strip()
                })
    
    return error_data

def categorize_errors_with_files(error_data):
    """에러들을 유형별로 분류하고 파일 경로도 함께 저장합니다."""
    error_categories = defaultdict(lambda: {'errors': [], 'files': set()})
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    for item in error_data:
        error = item['error']
        file_path = item['file_path']
        
        # 에러 유형 분류 (DB별 분기)
        if target_dbms in ['postgres', 'postgresql']:
            category = categorize_postgresql_error(error)
        elif target_dbms == 'mysql':
            category = categorize_mysql_error(error)
        else:
            category = '99. Other Errors'
        
        error_categories[category]['errors'].append(error)
        error_categories[category]['files'].add(file_path)
    
    return error_categories

def categorize_postgresql_error(error):
    """PostgreSQL 에러를 분류합니다."""
    if 'relation' in error and 'does not exist' in error:
        return '01. Relation Not Found'
    elif 'schema' in error and 'does not exist' in error:
        return '02. Schema Not Found'
    elif 'function' in error and 'does not exist' in error:
        return '03. Function Not Found'
    elif 'operator does not exist' in error:
        return '04. Operator Not Found'
    elif 'subquery in FROM must have an alias' in error:
        return '05. Subquery Alias Missing'
    elif 'syntax error at or near' in error:
        return '06. Syntax Error'
    elif 'cross-database references are not implemented' in error:
        return '07. Cross-Database Reference'
    elif 'COALESCE types' in error and 'cannot be matched' in error:
        return '08. Type Mismatch (COALESCE)'
    elif 'invalid input syntax for type' in error:
        return '09. Invalid Input Syntax'
    elif 'invalid reference to FROM-clause entry' in error:
        return '10. Invalid FROM Reference'
    elif 'recursive query' in error and 'column' in error and 'has type' in error:
        return '11. Recursive Query Type Mismatch'
    elif 'column' in error and 'does not exist' in error:
        return '12. Column Not Found'
    elif 'missing FROM-clause entry for table' in error:
        return '13. Missing FROM Clause'
    elif 'procedure' in error and 'does not exist' in error:
        return '14. Procedure Not Found'
    elif 'must appear in the GROUP BY clause' in error:
        return '15. GROUP BY Clause Error'
    elif 'date/time field value out of range' in error:
        return '16. Date Format Error'
    else:
        return '99. Other Errors'

def categorize_mysql_error(error):
    """MySQL 에러를 분류합니다."""
    error_lower = error.lower()
    
    if "table" in error_lower and "doesn't exist" in error_lower:
        return '01. Table Not Found'
    elif "database" in error_lower and "doesn't exist" in error_lower:
        return '02. Database Not Found'
    elif "function" in error_lower and "does not exist" in error_lower:
        return '03. Function Not Found'
    elif "unknown column" in error_lower:
        return '12. Column Not Found'
    elif "syntax error" in error_lower or "you have an error in your sql syntax" in error_lower:
        return '06. Syntax Error'
    elif "subquery" in error_lower and "alias" in error_lower:
        return '05. Subquery Alias Missing'
    elif "data type" in error_lower and "mismatch" in error_lower:
        return '08. Type Mismatch'
    elif "invalid" in error_lower and "datetime" in error_lower:
        return '16. Date Format Error'
    elif "group by" in error_lower:
        return '15. GROUP BY Clause Error'
    elif "procedure" in error_lower and "does not exist" in error_lower:
        return '14. Procedure Not Found'
    elif "operator" in error_lower and "does not exist" in error_lower:
        return '04. Operator Not Found'
    else:
        return '99. Other Errors'

def get_missing_objects_data(object_type):
    """특정 타입의 누락된 오브젝트 데이터를 가져옵니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    if target_dbms in ['postgres', 'postgresql']:
        type_conditions = {
            't': "tgt_result like '%ERROR:  relation%does not exist%'",
            's': "tgt_result like '%ERROR:  schema%does not exist%'", 
            'f': "tgt_result like '%ERROR:  function%does not exist%'",
            'o': "tgt_result like '%ERROR:  operator does not exist%'"
        }
    elif target_dbms == 'mysql':
        type_conditions = {
            't': "tgt_result like '%Table%doesn''t exist%'",
            's': "tgt_result like '%Database%doesn''t exist%'", 
            'f': "tgt_result like '%function%does not exist%'",
            'o': "tgt_result like '%operator%does not exist%'"
        }
    
    if object_type not in type_conditions:
        return ""
    
    query = f"""
    select tgt_file_path, tgt_result 
    from sqllist 
    where sql_id != 'retrieveCsrBatchJobMst.csrBatchJobRegDao.retrieveCsrBatchJobMst' 
    and same='N' 
    and {type_conditions[object_type]};
    """
    
    return execute_db_query(query)

def extract_missing_objects(db_output, object_type):
    """누락된 오브젝트들을 추출하고 분류합니다."""
    lines = db_output.strip().split('\n')
    missing_objects = defaultdict(lambda: {'files': set(), 'errors': []})
    
    for line in lines:
        # PostgreSQL과 MySQL 모두 탭으로 구분되거나 |로 구분될 수 있음
        if '\t' in line and 'ERROR' in line:
            parts = line.split('\t', 1)
        elif '|' in line and 'ERROR' in line:
            parts = line.split('|', 1)
        else:
            continue
            
        if len(parts) == 2:
            file_path = parts[0].strip()
            error_result = parts[1].strip()
            
            # 오브젝트 이름 추출
            object_names = extract_object_names(error_result, object_type)
            
            for obj_name in object_names:
                missing_objects[obj_name]['files'].add(file_path)
                missing_objects[obj_name]['errors'].append(error_result)
    
    return missing_objects

def extract_object_names(error_text, object_type):
    """에러 텍스트에서 오브젝트 이름을 추출합니다."""
    object_names = []
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    if target_dbms in ['postgres', 'postgresql']:
        if object_type == 't':  # 테이블/뷰
            matches = re.findall(r'relation "([^"]+)" does not exist', error_text)
            object_names.extend(matches)
        elif object_type == 's':  # 스키마
            matches = re.findall(r'schema "([^"]+)" does not exist', error_text)
            object_names.extend(matches)
        elif object_type == 'f':  # 함수
            matches = re.findall(r'function ([^(]+)\([^)]*\) does not exist', error_text)
            object_names.extend(matches)
        elif object_type == 'o':  # 오퍼레이터
            matches = re.findall(r'operator does not exist: ([^:]+)', error_text)
            object_names.extend(matches)
    
    elif target_dbms == 'mysql':
        if object_type == 't':  # 테이블
            matches = re.findall(r"Table '([^']+)' doesn't exist", error_text)
            object_names.extend(matches)
        elif object_type == 's':  # 데이터베이스
            matches = re.findall(r"Database '([^']+)' doesn't exist", error_text)
            object_names.extend(matches)
        elif object_type == 'f':  # 함수
            matches = re.findall(r'function ([^(]+)\([^)]*\) does not exist', error_text)
            object_names.extend(matches)
        elif object_type == 'o':  # 오퍼레이터
            matches = re.findall(r'operator does not exist: ([^:]+)', error_text)
            object_names.extend(matches)
    
    return object_names

def analyze_missing_objects(object_type):
    """누락된 오브젝트를 분석합니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').upper()
    
    if target_dbms in ['POSTGRES', 'POSTGRESQL']:
        type_names = {
            't': '테이블/뷰',
            's': '스키마', 
            'f': '함수',
            'o': '오퍼레이터'
        }
    elif target_dbms == 'MYSQL':
        type_names = {
            't': '테이블',
            's': '데이터베이스', 
            'f': '함수',
            'o': '오퍼레이터'
        }
    
    type_name = type_names.get(object_type, '알 수 없음')
    
    print("=" * 80)
    print(f"누락된 {type_name} 상세 분석 ({target_dbms})")
    print("=" * 80)
    
    # 데이터 수집
    print(f"누락된 {type_name} 데이터 수집 중...")
    db_output = get_missing_objects_data(object_type)
    
    if not db_output:
        print(f"누락된 {type_name} 데이터를 가져올 수 없습니다.")
        return
    
    # 오브젝트 추출 및 분류
    missing_objects = extract_missing_objects(db_output, object_type)
    
    if not missing_objects:
        print(f"누락된 {type_name}이 없습니다.")
        return
    
    print(f"총 {len(missing_objects)}개의 누락된 {type_name} 발견")
    
    # 결과 출력
    print(f"\n📊 누락된 {type_name} 목록:")
    print("=" * 60)
    
    # 파일 개수 순으로 정렬
    sorted_objects = sorted(missing_objects.items(), 
                          key=lambda x: len(x[1]['files']), reverse=True)
    
    for i, (obj_name, obj_data) in enumerate(sorted_objects, 1):
        file_count = len(obj_data['files'])
        error_count = len(obj_data['errors'])
        
        print(f"\n🔸 {i:2d}. {obj_name}")
        print(f"     에러 발생: {error_count}회, 영향 파일: {file_count}개")
        
        # 대표 에러 메시지 (첫 번째)
        if obj_data['errors']:
            first_error = obj_data['errors'][0]
            # ERROR 부분만 추출
            error_match = re.search(r'ERROR[^:]*:\s*([^\n]+)', first_error)
            if error_match:
                clean_error = error_match.group(1)
                print(f"     에러: {clean_error}")
    
    # 상세 파일 목록
    print(f"\n" + "=" * 80)
    print(f"📎 누락된 {type_name}별 상세 파일 목록")
    print("=" * 80)
    
    for i, (obj_name, obj_data) in enumerate(sorted_objects, 1):
        file_count = len(obj_data['files'])
        
        print(f"\n🔸 {i:2d}. {obj_name} ({file_count}개 파일)")
        print("-" * 70)
        
        # 파일 경로를 알파벳 순으로 정렬해서 출력
        sorted_files = sorted(list(obj_data['files']))
        for j, file_path in enumerate(sorted_files, 1):
            print(f"     {j:2d}. {file_path}")
    
    # JSON 파일로 저장
    analysis_result = {
        'analysis_date': datetime.now().isoformat(),
        'target_dbms': target_dbms,
        'object_type': type_name,
        'total_missing_objects': len(missing_objects),
        'missing_objects': {
            obj_name: {
                'error_count': len(obj_data['errors']),
                'file_count': len(obj_data['files']),
                'files': sorted(list(obj_data['files'])),
                'sample_errors': obj_data['errors'][:3]  # 샘플 에러 3개
            }
            for obj_name, obj_data in missing_objects.items()
        }
    }
    
    test_folder = os.environ.get('TEST_FOLDER', '/tmp')
    output_file = os.path.join(test_folder, f"missing_{object_type}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 상세 분석 결과가 저장되었습니다: {output_file}")
    
    # 요약
    print(f"\n📋 요약:")
    print(f"   - 누락된 {type_name} 수: {len(missing_objects)}개")
    total_files = len(set().union(*[obj_data['files'] for obj_data in missing_objects.values()]))
    print(f"   - 영향받는 파일 수: {total_files}개")
    if missing_objects:
        most_used = max(missing_objects.items(), key=lambda x: len(x[1]['files']))
        print(f"   - 가장 많이 사용된 {type_name}: {most_used[0]} ({len(most_used[1]['files'])}개 파일)")

def get_error_type_mapping():
    """에러 유형 번호와 이름의 매핑을 반환합니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    if target_dbms in ['postgres', 'postgresql']:
        return {
            '01': 'Relation Not Found',
            '02': 'Schema Not Found', 
            '03': 'Function Not Found',
            '04': 'Operator Not Found',
            '05': 'Subquery Alias Missing',
            '06': 'Syntax Error',
            '07': 'Cross-Database Reference',
            '08': 'Type Mismatch (COALESCE)',
            '09': 'Invalid Input Syntax',
            '10': 'Invalid FROM Reference',
            '11': 'Recursive Query Type Mismatch',
            '12': 'Column Not Found',
            '13': 'Missing FROM Clause',
            '14': 'Procedure Not Found',
            '15': 'GROUP BY Clause Error',
            '16': 'Date Format Error',
            '99': 'Other Errors'
        }
    elif target_dbms == 'mysql':
        return {
            '01': 'Table Not Found',
            '02': 'Database Not Found',
            '03': 'Function Not Found',
            '04': 'Operator Not Found',
            '05': 'Subquery Alias Missing',
            '06': 'Syntax Error',
            '07': 'Cross-Database Reference',
            '08': 'Type Mismatch',
            '09': 'Invalid Input Syntax',
            '10': 'Invalid FROM Reference',
            '11': 'Recursive Query Type Mismatch',
            '12': 'Column Not Found',
            '13': 'Missing FROM Clause',
            '14': 'Procedure Not Found',
            '15': 'GROUP BY Clause Error',
            '16': 'Date Format Error',
            '99': 'Other Errors'
        }

def analyze_specific_patterns(db_output):
    """특정 에러 패턴을 더 자세히 분석합니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
    
    if target_dbms in ['postgres', 'postgresql']:
        patterns = {
            'TABLE function usage': r'FROM TABLE\(',
            'Database link (@)': r'@[A-Z_]+',
            'Oracle-style LIMIT': r'and limit \d+',
            'Stored procedure call': r'call [A-Z_]+\.',
            'JSON/CLOB syntax': r'\{[^}]*\}',
            'Missing column in bind': r'AND [A-Z]\. = ',
        }
    elif target_dbms == 'mysql':
        patterns = {
            'Oracle-style LIMIT': r'and limit \d+',
            'Stored procedure call': r'call [A-Z_]+\.',
            'JSON syntax': r'\{[^}]*\}',
            'Missing column in bind': r'AND [A-Z]\. = ',
            'Oracle dual table': r'FROM dual',
            'Oracle decode function': r'DECODE\(',
        }
    
    pattern_counts = {}
    for pattern_name, pattern in patterns.items():
        matches = re.findall(pattern, db_output, re.IGNORECASE)
        pattern_counts[pattern_name] = len(matches)
    
    return pattern_counts

def parse_arguments():
    """명령행 인수를 파싱합니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').upper()
    
    parser = argparse.ArgumentParser(
        description=f'{target_dbms} 에러 유형 분석 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
사용 예시:
  python3 analyze_db_errors.py                    # 전체 에러 분석
  python3 analyze_db_errors.py --missing=t        # 누락된 테이블 분석
  python3 analyze_db_errors.py --missing=s        # 누락된 스키마/DB 분석
  python3 analyze_db_errors.py --missing=f        # 누락된 함수 분석
  python3 analyze_db_errors.py --missing=o        # 누락된 오퍼레이터 분석
  python3 analyze_db_errors.py --types             # 에러 유형 번호 매핑 표시

현재 타겟 DBMS: {target_dbms}
        """
    )
    
    parser.add_argument(
        '--missing',
        choices=['t', 's', 'f', 'o'],
        help='누락된 오브젝트 분석 (t:테이블, s:스키마/DB, f:함수, o:오퍼레이터)'
    )
    
    parser.add_argument(
        '--types',
        action='store_true',
        help='에러 유형 번호 매핑 표시'
    )
    
    return parser.parse_args()

def show_error_types():
    """에러 유형 번호 매핑을 표시합니다."""
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').upper()
    
    print("=" * 80)
    print(f"{target_dbms} 에러 유형 번호 매핑")
    print("=" * 80)
    
    error_mapping = get_error_type_mapping()
    
    print("\n📋 에러 유형 번호:")
    print("-" * 50)
    
    for number, name in sorted(error_mapping.items()):
        print(f"  {number}: {name}")
    
    print(f"\n💡 사용법:")
    print(f"   - 다른 프로그램에서 이 번호를 사용하여 특정 에러 유형을 참조할 수 있습니다")
    print(f"   - JSON 결과 파일에서 'error_number' 필드로 번호를 확인할 수 있습니다")

def main():
    """메인 실행 함수"""
    # 환경 변수 확인
    if not check_environment_variables():
        sys.exit(1)
    
    target_dbms = os.environ.get('TARGET_DBMS_TYPE', 'postgres').upper()
    
    # 명령행 인수 파싱
    args = parse_arguments()
    
    # 에러 유형 번호 매핑 표시 모드
    if args.types:
        show_error_types()
        return
    
    # 누락된 오브젝트 분석 모드
    if args.missing:
        analyze_missing_objects(args.missing)
        return
    
    # 기본 전체 에러 분석 모드
    print("=" * 80)
    print(f"{target_dbms} 에러 유형 분석")
    print("=" * 80)
    
    # 모든 타겟 DB 에러 결과 가져오기
    print(f"{target_dbms} 에러 데이터 수집 중...")
    all_db_output = get_all_db_errors()
    
    if not all_db_output:
        print("에러 데이터를 가져올 수 없습니다.")
        return
    
    # 에러 데이터 파싱
    error_data = parse_error_data(all_db_output)
    print(f"총 {len(error_data)}개의 에러 발견")
    
    # 에러 분류 (파일 경로 포함)
    error_categories = categorize_errors_with_files(error_data)
    
    # 결과 출력
    print(f"\n📊 에러 유형별 분석 결과:")
    print("=" * 50)
    
    total_errors = sum(len(cat_data['errors']) for cat_data in error_categories.values())
    
    for category, cat_data in sorted(error_categories.items(), 
                                   key=lambda x: len(x[1]['errors']), reverse=True):
        count = len(cat_data['errors'])
        file_count = len(cat_data['files'])
        percentage = (count / total_errors) * 100 if total_errors > 0 else 0
        
        print(f"\n🔸 {category}: {count}개 ({percentage:.1f}%) - {file_count}개 파일")
        
        # 각 카테고리의 대표 에러 예시 (최대 3개)
        for i, error in enumerate(cat_data['errors'][:3]):
            print(f"   {i+1}. {error[:100]}{'...' if len(error) > 100 else ''}")
        
        if len(cat_data['errors']) > 3:
            print(f"   ... 외 {len(cat_data['errors']) - 3}개 더")
    
    # 특정 패턴 분석
    print(f"\n🔍 특정 패턴 분석:")
    print("=" * 30)
    
    pattern_counts = analyze_specific_patterns(all_db_output)
    for pattern_name, count in sorted(pattern_counts.items(), 
                                    key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"   {pattern_name}: {count}개")
    
    # 상세 결과를 JSON 파일로 저장
    analysis_result = {
        'analysis_date': datetime.now().isoformat(),
        'target_dbms': target_dbms,
        'total_errors': total_errors,
        'error_type_mapping': get_error_type_mapping(),
        'error_categories': {
            category: {
                'error_number': category.split('.')[0],
                'error_name': category.split('. ', 1)[1] if '. ' in category else category,
                'count': len(cat_data['errors']),
                'file_count': len(cat_data['files']),
                'percentage': (len(cat_data['errors']) / total_errors) * 100 if total_errors > 0 else 0,
                'examples': cat_data['errors'][:5],  # 상위 5개 예시
                'files': sorted(list(cat_data['files']))  # 파일 목록
            }
            for category, cat_data in error_categories.items()
        },
        'pattern_analysis': pattern_counts
    }
    
    test_folder = os.environ.get('TEST_FOLDER', '/tmp')
    output_file = os.path.join(test_folder, f"db_error_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 상세 분석 결과가 저장되었습니다: {output_file}")
    
    # 요약
    print(f"\n📋 요약:")
    print(f"   - 총 에러 수: {total_errors}개")
    print(f"   - 주요 에러 유형: {len(error_categories)}개 카테고리")
    if error_categories:
        max_category = max(error_categories.items(), key=lambda x: len(x[1]['errors']))
        print(f"   - 가장 많은 에러: {max_category[0]} ({len(max_category[1]['errors'])}개)")
    
    # 별첨: 유형별 에러 파일 경로
    print(f"\n" + "=" * 80)
    print("📎 별첨: 유형별 에러 파일 경로")
    print("=" * 80)
    
    # CSV 파일 저장을 위한 데이터 수집
    csv_data = []
    
    # 파일별 에러 메시지 매핑 생성 (더 정확한 매핑을 위해)
    file_to_errors = {}
    for item in error_data:
        file_path = item['file_path']
        error_msg = item['error']
        if file_path not in file_to_errors:
            file_to_errors[file_path] = []
        file_to_errors[file_path].append(error_msg)
    
    for category, cat_data in sorted(error_categories.items(), 
                                   key=lambda x: len(x[1]['errors']), reverse=True):
        count = len(cat_data['errors'])
        file_count = len(cat_data['files'])
        
        print(f"\n🔸 {category} ({count}개 에러, {file_count}개 파일)")
        print("-" * 60)
        
        # 파일 경로를 알파벳 순으로 정렬해서 출력
        sorted_files = sorted(list(cat_data['files']))
        
        for i, file_path in enumerate(sorted_files, 1):
            print(f"   {i:2d}. {file_path}")
            
            # 해당 파일의 첫 번째 에러 메시지 사용
            representative_error = "에러 메시지 없음"
            if file_path in file_to_errors and file_to_errors[file_path]:
                representative_error = file_to_errors[file_path][0]
            
            # CSV 데이터에 추가 (파일경로, 에러메시지)
            csv_data.append([file_path, representative_error])
        
        if len(sorted_files) == 0:
            print("   (파일 없음)")
    
    # CSV 파일로 저장
    csv_file_path = os.path.join(test_folder, "db_error.csv")
    try:
        import csv
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # 헤더 작성
            writer.writerow(['sql파일', '에러메시지'])
            # 데이터 작성
            writer.writerows(csv_data)
        
        print(f"\n💾 에러 파일 목록이 CSV로 저장되었습니다: {csv_file_path}")
        print(f"   - 총 {len(csv_data)}개 파일 정보 저장")
        print(f"   - 형식: sql파일, 에러메시지")
        
    except Exception as e:
        print(f"\n❌ CSV 파일 저장 실패: {e}")

if __name__ == "__main__":
    main()