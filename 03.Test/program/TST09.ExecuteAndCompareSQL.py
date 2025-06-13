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
# - Generates a CSV report of the execution results
#
# Usage:
#   python3 DB09.ExecuteAndCompareSQL.py [options]
#
# Options:
#   -t, --type TYPE     SQL statement type to execute (S: Select, I: Insert, U: Update, D: Delete, P: PL/SQL Block, O: Other)
#                       Multiple types can be specified with commas (e.g., S,U,I)
#############################################################################

"""
Oracle과 PostgreSQL에서 SQL을 실행하고 결과를 비교하는 프로그램

이 프로그램은 sqllist 테이블에서 orcl과 pg 컬럼이 모두 NULL이 아닌 로우를 찾아
Oracle과 PostgreSQL에서 각각 실행하고 결과를 저장합니다.

사용법:
    python DB09.ExecuteAndCompareSQL.py [옵션]

옵션:
    -t, --type TYPE     실행할 SQL 문의 타입 (S: Select, I: Insert, U: Update, D: Delete, P: PL/SQL Block, O: Other)
                        여러 타입을 지정하려면 쉼표로 구분 (예: S,U,I)
"""

import os
import sys
import subprocess
import tempfile
import csv
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import argparse
from datetime import datetime

# 결과 저장 디렉토리
RESULT_DIR = "sql_results"
os.makedirs(RESULT_DIR, exist_ok=True)

# SQL 문 타입 매핑
STMT_TYPES = {
    'S': 'Select',
    'I': 'Insert',
    'U': 'Update',
    'D': 'Delete',
    'P': 'PL/SQL Block',
    'O': 'Other'
}

def execute_oracle_sql(sql_id, sql):
    """
    Oracle에서 SQL을 실행하고 결과를 반환합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    print(f"Oracle에서 SQL 실행 중: {sql_id}")
    
    # 환경 변수에서 Oracle 연결 정보 가져오기
    oracle_user = os.environ.get('ORACLE_SVC_USER')
    oracle_password = os.environ.get('ORACLE_SVC_PASSWORD')
    oracle_sid = os.environ.get('ORACLE_SID')
    
    if not all([oracle_user, oracle_password, oracle_sid]):
        print("오류: Oracle 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
        return "ERROR: Oracle 연결 정보 누락"
    
    # SQL 문 끝에 있는 '/' 문자 제거
    sql = sql.strip()
    if sql.endswith('/'):
        sql = sql[:-1].strip()
    
    # 임시 SQL 파일 생성
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', encoding='utf-8', delete=False) as temp_sql:
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
        temp_sql.write("SPOOL " + temp_sql.name + "_result.csv\n")  # 결과를 파일로 저장
        
        # 실행할 SQL 추가
        temp_sql.write(f"{sql};\n")
        temp_sql.write("SPOOL OFF\n")  # 스풀 종료
        temp_sql.write("EXIT;\n")
        temp_sql_path = temp_sql.name
    
    # 임시 결과 파일 경로
    temp_result_path = f"{temp_sql_path}_result.csv"
    
    try:
        # Oracle SQL 실행 - 한글 인코딩 설정
        env = os.environ.copy()
        env['NLS_LANG'] = 'KOREAN_KOREA.AL32UTF8'
        cmd = f"sqlplus -S {oracle_user}/{oracle_password}@{oracle_sid} @{temp_sql_path}"
        process = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, env=env)
        
        if process.returncode != 0:
            error_msg = process.stderr.decode('utf-8', errors='replace')
            print(f"Oracle SQL 실행 오류: {error_msg}")
            return f"ERROR: {error_msg}"
        
        # 결과 파일 읽기
        if os.path.exists(temp_result_path):
            with open(temp_result_path, 'r', encoding='utf-8', errors='replace') as f:
                result = f.read().strip()
                
            # ORA- 오류가 있는지 확인
            lines = result.split('\n')
            for line in lines:
                if line.strip().startswith('ORA-'):
                    # ORA- 오류가 있으면 해당 라인만 반환
                    return line.strip()
                    
            return result
        else:
            print(f"Oracle SQL 결과 파일이 생성되지 않았습니다: {temp_result_path}")
            return "ERROR: 결과 파일이 생성되지 않았습니다"
    except Exception as e:
        print(f"Oracle SQL 실행 중 예외 발생: {str(e)}")
        return f"ERROR: {str(e)}"
    finally:
        # 임시 파일 삭제
        try:
            os.unlink(temp_sql_path)
            if os.path.exists(temp_result_path):
                os.unlink(temp_result_path)
        except:
            pass

def execute_postgres_sql(sql_id, sql):
    """
    PostgreSQL에서 SQL을 실행하고 결과를 반환합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    print(f"PostgreSQL에서 SQL 실행 중: {sql_id}")
    
    # 환경 변수에서 PostgreSQL 연결 정보 가져오기
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('PGPASSWORD')
    pg_host = os.environ.get('PGHOST')
    pg_port = os.environ.get('PGPORT')
    pg_database = os.environ.get('PGDATABASE')
    
    if not all([pg_user, pg_password, pg_host, pg_port, pg_database]):
        print("오류: PostgreSQL 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
        return "ERROR: PostgreSQL 연결 정보 누락"
    
    # SQL 문 끝에 있는 '/' 문자 제거
    sql = sql.strip()
    if sql.endswith('/'):
        sql = sql[:-1].strip()
    
    # 임시 SQL 파일 생성
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_sql:
        # 결과를 CSV 형식으로 출력하는 설정 추가 (메타 정보 출력 안함)
        temp_sql.write("\\set QUIET on\n")  # 모든 메타 정보 출력 안함
        temp_sql.write("\\pset tuples_only on\n")  # 튜플만 출력 (메타 정보 없이)
        temp_sql.write("\\pset format unaligned\n")  # 정렬되지 않은 출력
        temp_sql.write("\\pset fieldsep ','\n")  # 필드 구분자를 쉼표로 설정
        temp_sql.write("\\pset footer off\n")  # 푸터 정보 출력 안함
        temp_sql.write("\\pset pager off\n")  # 페이저 사용 안함
        
        # 실행할 SQL 추가
        temp_sql.write(f"{sql};\n")
        temp_sql.write("\\q\n")  # 종료
        temp_sql_path = temp_sql.name
    
    # 임시 결과 파일 경로
    temp_result_path = f"{temp_sql_path}_result.csv"
    
    try:
        # PostgreSQL SQL 실행 - 에러 메시지도 결과 파일에 포함되도록 stderr를 stdout으로 리다이렉트
        cmd = f"PGPASSWORD={pg_password} psql -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_database} -f {temp_sql_path} > {temp_result_path} 2>&1"
        process = subprocess.run(cmd, shell=True)
        
        # 결과 파일 읽기
        if os.path.exists(temp_result_path):
            with open(temp_result_path, 'r', encoding='utf-8', errors='replace') as f:
                result = f.read().strip()
                
            # 에러 메시지가 있는지 확인
            lines = result.split('\n')
            for line in lines:
                if line.strip().startswith('ERROR:'):
                    # ERROR: 로 시작하는 에러 메시지가 있으면 해당 라인만 반환
                    return line.strip()
                    
            return result
        else:
            print(f"PostgreSQL SQL 결과 파일이 생성되지 않았습니다: {temp_result_path}")
            return "ERROR: 결과 파일이 생성되지 않았습니다"
    except Exception as e:
        print(f"PostgreSQL SQL 실행 중 예외 발생: {str(e)}")
        return f"ERROR: {str(e)}"
    finally:
        # 임시 파일 삭제
        try:
            os.unlink(temp_sql_path)
            if os.path.exists(temp_result_path):
                os.unlink(temp_result_path)
        except:
            pass

def update_results(conn, sql_id, app_name, stmt_type, orcl_result, pg_result):
    """
    실행 결과를 데이터베이스에 업데이트합니다.
    결과가 같은지 여부도 확인하여 same 컬럼을 업데이트합니다.
    """
    try:
        # 결과가 같은지 확인
        same = 'Y' if orcl_result == pg_result else 'N'
        
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sqllist SET orcl_result = %s, pg_result = %s, same = %s WHERE sql_id = %s AND app_name = %s AND stmt_type = %s",
                (orcl_result, pg_result, same, sql_id, app_name, stmt_type)
            )
        conn.commit()
        return True, same
    except Exception as e:
        print(f"결과 업데이트 중 오류 발생: {str(e)}")
        conn.rollback()
        return False, 'N'

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
            print("오류: PostgreSQL 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
            print(f"PGHOST: {pg_host}, PGPORT: {pg_port}, PGDATABASE: {pg_database}, PGUSER: {pg_user}")
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
        print(f"데이터베이스 연결 오류: {e}")
        sys.exit(1)

def main():
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 현재 시간을 기반으로 한 결과 파일 이름
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 타입 필터링이 있는 경우 파일 이름에 추가
    type_suffix = ""
    if args.type:
        type_suffix = f"_{args.type.replace(',', '')}"
    
    RESULT_CSV = os.path.join(RESULT_DIR, f"sql_comparison_results{type_suffix}_{timestamp}.csv")
    
    # Oracle 한글 인코딩 환경 변수 설정
    os.environ['NLS_LANG'] = 'KOREAN_KOREA.AL32UTF8'
    
    # PostgreSQL 연결
    try:
        conn = get_db_connection()
        print("PostgreSQL 데이터베이스에 연결되었습니다.")
    except Exception as e:
        print(f"PostgreSQL 연결 오류: {str(e)}")
        sys.exit(1)
    
    try:
        # CSV 결과 파일 생성
        with open(RESULT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['sql_id', 'app_name', 'stmt_type', 'orcl_file_path', 'pg_file_path', 
                         'orcl_result_status', 'pg_result_status', 'same', 'execution_time']
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
                    print(f"SQL 문 타입 필터링: {', '.join([STMT_TYPES.get(t, t) for t in valid_types])}")
            
            query += " ORDER BY sql_id, app_name, stmt_type"
            
            # 쿼리 실행
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchall()
                total_rows = len(rows)
                
                if total_rows == 0:
                    print("조건에 맞는 SQL 문이 없습니다.")
                    return
                
                print(f"총 {total_rows}개의 SQL 문을 실행합니다.")
                
                for i, row in enumerate(rows, 1):
                    sql_id = row['sql_id']
                    app_name = row['app_name']
                    stmt_type = row['stmt_type']
                    orcl_sql = row['orcl']
                    pg_sql = row['pg']
                    
                    print(f"[{i}/{total_rows}] SQL ID: {sql_id}, App: {app_name} (타입: {stmt_type} - {STMT_TYPES.get(stmt_type, '알 수 없음')}) 처리 중...")
                    
                    start_time = time.time()
                    
                    # Oracle SQL 실행
                    orcl_result = execute_oracle_sql(sql_id, orcl_sql)
                    orcl_status = "SUCCESS" if not orcl_result.startswith("ERROR:") else "ERROR"
                    
                    # PostgreSQL SQL 실행
                    pg_result = execute_postgres_sql(sql_id, pg_sql)
                    pg_status = "SUCCESS" if not pg_result.startswith("ERROR:") else "ERROR"
                    
                    # 실행 시간 계산
                    execution_time = time.time() - start_time
                    
                    # 결과 업데이트
                    update_success, same = update_results(conn, sql_id, app_name, stmt_type, orcl_result, pg_result)
                    
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
                        'execution_time': f"{execution_time:.2f}"
                    })
                    
                    # 진행 상황 출력
                    print(f"[{i}/{total_rows}] SQL ID: {sql_id}, App: {app_name} 처리 완료 - Oracle: {orcl_status}, PostgreSQL: {pg_status}, 같음: {same}, 시간: {execution_time:.2f}초")
                    
                    # 일정 간격으로 커밋
                    if i % 10 == 0:
                        conn.commit()
                        print(f"중간 커밋 완료: {i}/{total_rows}")
                
                # 최종 커밋
                conn.commit()
                
        print(f"모든 SQL 실행이 완료되었습니다. 결과가 {RESULT_CSV}에 저장되었습니다.")
        
    except Exception as e:
        print(f"처리 중 오류 발생: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
