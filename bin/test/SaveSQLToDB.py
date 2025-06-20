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
# - Exports sqllist table data to CSV files in TEST_FOLDER/sqllist directory
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
import logging
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

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
        'orcl_sql_done_dir': os.path.join(test_folder, 'orcl_sql_done'),
        'pg_sql_done_dir': os.path.join(test_folder, 'pg_sql_done'),
        'sqllist_output_dir': os.path.join(test_folder, 'sqllist'),
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
    log_file = os.path.join(logs_dir, 'save_sql_to_db.log')
    
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
    logger.info("SaveSQLToDB 실행 시작")
    logger.info("=" * 60)
    
    return logger

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
            logger.error("PostgreSQL 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
            logger.error(f"PGHOST: {host}, PGPORT: {port}, PGDATABASE: {database}, PGUSER: {user}")
            sys.exit(1)
        
        # 데이터베이스 연결
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        logger.info(f"PostgreSQL 연결 성공: {host}:{port}/{database}")
        return conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 오류: {e}")
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
                logger.info("sqllist 테이블을 생성합니다...")
                
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
                logger.info("sqllist 테이블이 성공적으로 생성되었습니다.")
            else:
                logger.info("sqllist 테이블이 이미 존재합니다.")
                
    except Exception as e:
        logger.error(f"테이블 생성 오류: {e}")
        conn.rollback()
        sys.exit(1)
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
        
        logger.debug(f"파일 처리 완료: {os.path.basename(file_path)} - {app_name}.{sql_id} ({stmt_type})")
        
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
        logger.error(f"파일 처리 오류 ({file_path}): {e}")
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
                logger.debug(f"레코드 업데이트: {sql_data['app_name']}.{sql_data['sql_id']}")
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
                logger.debug(f"레코드 삽입: {sql_data['app_name']}.{sql_data['sql_id']}")
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"데이터 삽입/업데이트 오류: {e}")
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
        logger.warning(f"{directory} 디렉토리에 SQL 파일이 없습니다.")
        return 0
    
    db_type = "Oracle" if is_oracle else "PostgreSQL"
    logger.info(f"{db_type} SQL 파일 처리 시작: {directory} ({total_files}개 파일)")
    
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
                    progress = (i/total_files)*100
                    logger.info(f"{db_type} 진행 중: {i}/{total_files} 파일 처리됨 ({progress:.1f}%)")
                
            except Exception as e:
                logger.error(f"파일 처리 오류 ({file_path}): {e}")
                error_count += 1
    
    logger.info(f"{db_type} 처리 완료: {success_count}개 성공, {error_count}개 실패")
    return success_count

def export_sqllist_to_csv(conn):
    """
    sqllist 테이블 데이터를 CSV 파일로 내보냅니다.
    """
    paths = get_paths()
    output_dir = paths['sqllist_output_dir']
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        with conn.cursor() as cursor:
            # 전체 데이터 조회
            cursor.execute("""
                SELECT sql_id, app_name, stmt_type, orcl_file_path, pg_file_path, 
                       orcl, pg, orcl_result, pg_result, same
                FROM sqllist 
                ORDER BY app_name, sql_id, stmt_type
            """)
            
            rows = cursor.fetchall()
            
            if not rows:
                logger.warning("sqllist 테이블에 데이터가 없습니다.")
                return
            
            # CSV 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = os.path.join(output_dir, f"sqllist_{timestamp}.csv")
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 헤더 작성
                writer.writerow([
                    'sql_id', 'app_name', 'stmt_type', 'orcl_file_path', 'pg_file_path',
                    'orcl', 'pg', 'orcl_result', 'pg_result', 'same'
                ])
                
                # 데이터 작성
                writer.writerows(rows)
            
            logger.info(f"sqllist 데이터를 CSV로 내보냈습니다: {csv_file}")
            logger.info(f"총 {len(rows)}개 레코드 내보냄")
            
            # 요약 정보도 별도 파일로 저장
            summary_file = os.path.join(output_dir, f"sqllist_summary_{timestamp}.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("SQLList 요약 정보\n")
                f.write("=" * 60 + "\n")
                f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"총 레코드 수: {len(rows)}\n\n")
                
                # 애플리케이션별 통계
                cursor.execute("""
                    SELECT app_name, COUNT(*) as count
                    FROM sqllist 
                    GROUP BY app_name 
                    ORDER BY app_name
                """)
                app_stats = cursor.fetchall()
                
                f.write("애플리케이션별 SQL 수:\n")
                f.write("-" * 30 + "\n")
                for app_name, count in app_stats:
                    f.write(f"{app_name}: {count}개\n")
                
                # SQL 유형별 통계
                cursor.execute("""
                    SELECT stmt_type, COUNT(*) as count
                    FROM sqllist 
                    GROUP BY stmt_type 
                    ORDER BY stmt_type
                """)
                type_stats = cursor.fetchall()
                
                f.write("\nSQL 유형별 통계:\n")
                f.write("-" * 30 + "\n")
                type_names = {'S': 'SELECT', 'I': 'INSERT', 'U': 'UPDATE', 'D': 'DELETE', 'P': 'PL/SQL', 'O': 'OTHER'}
                for stmt_type, count in type_stats:
                    type_name = type_names.get(stmt_type, stmt_type)
                    f.write(f"{type_name} ({stmt_type}): {count}개\n")
            
            logger.info(f"요약 정보 저장: {summary_file}")
            
    except Exception as e:
        logger.error(f"CSV 내보내기 오류: {e}")

def main():
    """메인 실행 함수"""
    start_time = time.time()
    paths = get_paths()
    
    # 경로 정보 출력
    logger.info("경로 설정:")
    logger.info(f"  Oracle SQL 입력: {paths['orcl_sql_done_dir']}")
    logger.info(f"  PostgreSQL SQL 입력: {paths['pg_sql_done_dir']}")
    logger.info(f"  SQLList 출력: {paths['sqllist_output_dir']}")
    logger.info(f"  로그 디렉토리: {paths['logs_dir']}")
    
    # 데이터베이스 연결
    conn = get_db_connection()
    
    try:
        # sqllist 테이블 생성
        create_sqllist_table(conn)
        
        # 디렉토리 경로 설정
        orcl_dir = paths['orcl_sql_done_dir']
        pg_dir = paths['pg_sql_done_dir']
        
        total_orcl_count = 0
        total_pg_count = 0
        
        # Oracle SQL 파일 처리
        if os.path.isdir(orcl_dir):
            total_orcl_count = process_directory(orcl_dir, True, conn)
        else:
            logger.warning(f"Oracle SQL 디렉토리가 존재하지 않습니다: {orcl_dir}")
        
        # PostgreSQL SQL 파일 처리
        if os.path.isdir(pg_dir):
            total_pg_count = process_directory(pg_dir, False, conn)
        else:
            logger.warning(f"PostgreSQL SQL 디렉토리가 존재하지 않습니다: {pg_dir}")
        
        # 처리 결과 요약
        elapsed_time = time.time() - start_time
        logger.info(f"파일 처리 완료: 총 소요 시간 {elapsed_time:.2f}초")
        
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
            
            logger.info("=" * 60)
            logger.info("통계 정보:")
            logger.info(f"  총 SQL 문 수: {total_records}")
            logger.info(f"  Oracle과 PostgreSQL 모두 있는 SQL 문 수: {matched_records}")
            logger.info(f"  Oracle만 있는 SQL 문 수: {orcl_only}")
            logger.info(f"  PostgreSQL만 있는 SQL 문 수: {pg_only}")
            logger.info("=" * 60)
        
        # CSV로 내보내기
        export_sqllist_to_csv(conn)
        
        logger.info("SaveSQLToDB 실행 완료")
        
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        raise
    finally:
        # 데이터베이스 연결 종료
        if conn:
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
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {str(e)}")
        raise
