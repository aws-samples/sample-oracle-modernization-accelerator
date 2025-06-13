#!/usr/bin/env python3
#############################################################################
# Script: DB08.SaveSQLToDB.py
# Description: This script reads SQL files from pg_sql_done and orcl_sql_done
#              directories and saves them to the sqllist table in PostgreSQL.
#
# Functionality:
# - Creates the sqllist table in PostgreSQL if it doesn't exist
# - Reads SQL files from pg_sql_done and orcl_sql_done directories
# - Extracts SQL ID, application name, and statement type from file names and content
# - Inserts the data into the sqllist table
#
# Usage:
#   python3 DB08.SaveSQLToDB.py
#
#############################################################################

import os
import sys
import re
import psycopg2
from psycopg2 import sql
import glob
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# SQL statement type mapping
SQL_TYPE_MAP = {
    'SELECT': 'S',  # Select
    'INSERT': 'I',  # Insert
    'UPDATE': 'U',  # Update
    'DELETE': 'D',  # Delete
    'DECLARE': 'P', # PL/SQL Block
    'BEGIN': 'P',   # PL/SQL Block
    'CREATE': 'O',  # Other (DDL)
    'ALTER': 'O',   # Other (DDL)
    'DROP': 'O',    # Other (DDL)
    'TRUNCATE': 'O' # Other (DDL)
}

def get_db_connection():
    """
    PostgreSQL 데이터베이스 연결을 생성합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    try:
        # 환경 변수에서 연결 정보 가져오기
        host = os.environ.get('PGHOST')
        port = os.environ.get('PGPORT')
        database = os.environ.get('PGDATABASE')
        user = os.environ.get('PGUSER')
        password = os.environ.get('PGPASSWORD')
        
        # 연결 정보 확인
        if not all([host, port, database, user, password]):
            print("오류: PostgreSQL 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
            print(f"PGHOST: {host}, PGPORT: {port}, PGDATABASE: {database}, PGUSER: {user}")
            sys.exit(1)
        
        # 데이터베이스 연결
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        return conn
    except Exception as e:
        print(f"데이터베이스 연결 오류: {e}")
        sys.exit(1)

def create_sqllist_table(conn):
    """
    sqllist 테이블을 생성합니다.
    """
    try:
        with conn.cursor() as cursor:
            # 테이블이 존재하는지 확인
            cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sqllist')")
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print("sqllist 테이블을 생성합니다...")
                
                # 테이블 생성 SQL
                create_table_sql = """
                CREATE TABLE sqllist (
                  sql_id          varchar(100) not null,
                  app_name        varchar(20) not null,
                  stmt_type       char(1) not null,
                  orcl_file_path  varchar(150),
                  pg_file_path    varchar(150),
                  orcl            text,
                  pg              text, 
                  orcl_result     text,
                  pg_result       text,
                  same            char(1),
                  PRIMARY KEY (sql_id, app_name, stmt_type)
                );

                COMMENT ON COLUMN sqllist.sql_id IS 'Unique SQL statement ID. File_Name.ID';
                COMMENT ON COLUMN sqllist.app_name IS 'Application name';
                COMMENT ON COLUMN sqllist.stmt_type IS 'SQL statement type. S: Select, I: Insert, U: Update, D: Delete, P: PL/SQL Block';
                COMMENT ON COLUMN sqllist.orcl_file_path IS 'Oracle XML file path of this SQL statement';
                COMMENT ON COLUMN sqllist.pg_file_path IS 'PostgreSQL XML file path of this SQL statement';
                COMMENT ON COLUMN sqllist.orcl IS 'Origin Oracle statement';
                COMMENT ON COLUMN sqllist.pg IS 'Transformed to Postgres statement';
                COMMENT ON COLUMN sqllist.same IS 'Is it same orcl_result and pg_result? Y: same, N: different';
                """
                
                cursor.execute(create_table_sql)
                conn.commit()
                print("sqllist 테이블이 성공적으로 생성되었습니다.")
            else:
                print("sqllist 테이블이 이미 존재합니다.")
                
    except Exception as e:
        print(f"테이블 생성 오류: {e}")
        conn.rollback()
        sys.exit(1)

def determine_sql_type(sql_content):
    """
    SQL 내용을 분석하여 SQL 문 유형을 결정합니다.
    """
    # SQL 내용에서 주석 제거
    sql_without_comments = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
    sql_without_comments = re.sub(r'--.*?$', '', sql_without_comments, flags=re.MULTILINE)
    
    # 첫 번째 단어 추출 (대문자로 변환)
    first_word_match = re.search(r'^\s*(\w+)', sql_without_comments, re.IGNORECASE)
    
    if first_word_match:
        first_word = first_word_match.group(1).upper()
        
        # SQL 유형 매핑
        if first_word in SQL_TYPE_MAP:
            return SQL_TYPE_MAP[first_word]
        
        # PL/SQL 블록 확인
        if "DECLARE" in sql_without_comments.upper() or "BEGIN" in sql_without_comments.upper():
            return 'P'
    
    # 기본값: 기타
    return 'O'

def extract_app_name(filename):
    """
    파일 이름에서 어플리케이션 이름을 추출합니다.
    파일 이름의 첫 번째 부분이 어플리케이션 이름입니다.
    """
    # 파일 이름에서 확장자 제거
    base_name = os.path.basename(filename)
    name_parts = base_name.split('.')
    
    # 첫 번째 부분이 어플리케이션 이름
    if len(name_parts) > 1:
        return name_parts[0]
    
    return "unknown"

def extract_sql_id(filename):
    """
    파일 이름에서 SQL ID를 추출합니다.
    파일 이름에서 .sql 확장자를 제외한 부분입니다.
    """
    # 파일 이름에서 확장자 제거
    base_name = os.path.basename(filename)
    sql_id_with_ext = os.path.splitext(base_name)[0]
    
    # 어플리케이션 이름 제외 (첫 번째 부분 제외)
    parts = sql_id_with_ext.split('.')
    if len(parts) > 1:
        return '.'.join(parts[1:])  # 첫 번째 부분(앱 이름) 제외
    
    return sql_id_with_ext

def process_sql_file(file_path, is_oracle):
    """
    SQL 파일을 처리하여 필요한 정보를 추출합니다.
    """
    try:
        # 파일 내용 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # SQL ID 추출 (파일 이름에서 .sql 확장자 제외)
        sql_id = extract_sql_id(file_path)
        
        # 어플리케이션 이름 추출
        app_name = extract_app_name(file_path)
        
        # SQL 유형 결정
        stmt_type = determine_sql_type(sql_content)
        
        # 파일 경로 설정
        orcl_file_path = os.path.abspath(file_path) if is_oracle else None
        pg_file_path = os.path.abspath(file_path) if not is_oracle else None
        
        # SQL 내용 설정
        orcl_content = sql_content if is_oracle else None
        pg_content = sql_content if not is_oracle else None
        
        return {
            'sql_id': sql_id,
            'app_name': app_name,
            'stmt_type': stmt_type,
            'orcl_file_path': orcl_file_path,
            'pg_file_path': pg_file_path,
            'orcl': orcl_content,
            'pg': pg_content
        }
    except Exception as e:
        print(f"파일 처리 오류 ({file_path}): {e}")
        return None

def insert_or_update_sql_data(conn, sql_data):
    """
    SQL 데이터를 sqllist 테이블에 삽입하거나 업데이트합니다.
    """
    try:
        with conn.cursor() as cursor:
            # 기존 레코드 확인
            cursor.execute(
                "SELECT * FROM sqllist WHERE sql_id = %s AND app_name = %s AND stmt_type = %s",
                (sql_data['sql_id'], sql_data['app_name'], sql_data['stmt_type'])
            )
            existing_record = cursor.fetchone()
            
            if existing_record:
                # 기존 레코드 업데이트
                update_query = """
                UPDATE sqllist
                SET orcl_file_path = COALESCE(%s, orcl_file_path),
                    pg_file_path = COALESCE(%s, pg_file_path),
                    orcl = COALESCE(%s, orcl),
                    pg = COALESCE(%s, pg)
                WHERE sql_id = %s AND app_name = %s AND stmt_type = %s
                """
                
                cursor.execute(
                    update_query,
                    (
                        sql_data['orcl_file_path'],
                        sql_data['pg_file_path'],
                        sql_data['orcl'],
                        sql_data['pg'],
                        sql_data['sql_id'],
                        sql_data['app_name'],
                        sql_data['stmt_type']
                    )
                )
            else:
                # 새 레코드 삽입
                insert_query = """
                INSERT INTO sqllist (
                    sql_id, app_name, stmt_type, orcl_file_path, pg_file_path, orcl, pg
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(
                    insert_query,
                    (
                        sql_data['sql_id'],
                        sql_data['app_name'],
                        sql_data['stmt_type'],
                        sql_data['orcl_file_path'],
                        sql_data['pg_file_path'],
                        sql_data['orcl'],
                        sql_data['pg']
                    )
                )
            
            conn.commit()
            return True
    except Exception as e:
        print(f"데이터 삽입/업데이트 오류: {e}")
        conn.rollback()
        return False

def process_directory(directory, is_oracle, conn):
    """
    지정된 디렉토리의 모든 SQL 파일을 처리합니다.
    """
    # SQL 파일 목록 가져오기
    sql_files = glob.glob(os.path.join(directory, "*.sql"))
    total_files = len(sql_files)
    
    if total_files == 0:
        print(f"경고: {directory} 디렉토리에 SQL 파일이 없습니다.")
        return 0
    
    print(f"{directory} 디렉토리에서 {total_files}개의 SQL 파일을 처리합니다...")
    
    success_count = 0
    error_count = 0
    
    # 병렬 처리
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # 작업 제출
        future_to_file = {executor.submit(process_sql_file, file_path, is_oracle): file_path for file_path in sql_files}
        
        # 결과 처리
        for i, future in enumerate(as_completed(future_to_file), 1):
            file_path = future_to_file[future]
            try:
                sql_data = future.result()
                
                if sql_data:
                    # 데이터베이스에 삽입 또는 업데이트
                    if insert_or_update_sql_data(conn, sql_data):
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1
                
                # 진행 상황 표시
                if i % 100 == 0 or i == total_files:
                    print(f"진행 중: {i}/{total_files} 파일 처리됨 ({(i/total_files)*100:.1f}%)")
                
            except Exception as e:
                print(f"파일 처리 오류 ({file_path}): {e}")
                error_count += 1
    
    print(f"{directory} 처리 완료: {success_count}개 성공, {error_count}개 실패")
    return success_count

def main():
    start_time = time.time()
    
    # 데이터베이스 연결
    conn = get_db_connection()
    
    try:
        # sqllist 테이블 생성
        create_sqllist_table(conn)
        
        # 디렉토리 경로 설정
        orcl_dir = os.path.join(os.getcwd(), "orcl_sql_done")
        pg_dir = os.path.join(os.getcwd(), "pg_sql_done")
        
        # 디렉토리 존재 확인
        if not os.path.isdir(orcl_dir):
            print(f"경고: {orcl_dir} 디렉토리가 존재하지 않습니다.")
        else:
            # Oracle SQL 파일 처리
            orcl_count = process_directory(orcl_dir, True, conn)
            print(f"Oracle SQL 파일 {orcl_count}개가 처리되었습니다.")
        
        if not os.path.isdir(pg_dir):
            print(f"경고: {pg_dir} 디렉토리가 존재하지 않습니다.")
        else:
            # PostgreSQL SQL 파일 처리
            pg_count = process_directory(pg_dir, False, conn)
            print(f"PostgreSQL SQL 파일 {pg_count}개가 처리되었습니다.")
        
        # 처리 결과 요약
        elapsed_time = time.time() - start_time
        print(f"\n처리 완료: 총 소요 시간 {elapsed_time:.2f}초")
        
        # 통계 정보 출력
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM sqllist")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sqllist WHERE orcl IS NOT NULL AND pg IS NOT NULL")
            matched_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sqllist WHERE orcl IS NOT NULL AND pg IS NULL")
            orcl_only = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sqllist WHERE orcl IS NULL AND pg IS NOT NULL")
            pg_only = cursor.fetchone()[0]
            
            print(f"\n통계 정보:")
            print(f"총 SQL 문 수: {total_records}")
            print(f"Oracle과 PostgreSQL 모두 있는 SQL 문 수: {matched_records}")
            print(f"Oracle만 있는 SQL 문 수: {orcl_only}")
            print(f"PostgreSQL만 있는 SQL 문 수: {pg_only}")
        
    finally:
        # 데이터베이스 연결 종료
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
