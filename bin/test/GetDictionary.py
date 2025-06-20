#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#############################################################################
# Script: DB04.GetDictionary.py
# Description: This script extracts database metadata and sample data to create
#              a comprehensive dictionary of tables and columns.
#
# Functionality:
# - Connects to an Oracle database using SQLPlus
# - Extracts all tables owned by the connected user
# - For each table, retrieves column information (name, data type, length, nullable)
# - Collects sample values for each column
# - Classifies columns based on naming patterns and data types
# - Creates a structured dictionary with all this information
# - Saves the dictionary as a JSON file (all_dictionary.json)
#
# The dictionary is used by other tools in the migration process, particularly
# for bind variable sampling and mapping.
#
# Usage:
#   python3 DB04.GetDictionary.py
#
# Output:
#   - all_dictionary.json: Complete database dictionary with sample values
#   - dictionary_extraction.log: Log file with extraction details
#############################################################################

"""
get_dictionary.py

데이터베이스의 모든 테이블과 컬럼 정보를 추출하고, 각 컬럼의 데이터 타입과 
실제 샘플 데이터를 수집하여 all_dictionary.json 파일로 저장합니다.
"""

import os
import json
import subprocess
import tempfile
import logging
from datetime import datetime

# 한글 지원을 위한 환경 변수 설정
os.environ['NLS_LANG'] = 'KOREAN_KOREA.AL32UTF8'

# 환경 변수에서 디렉토리 경로 가져오기
TEST_FOLDER = os.environ.get('TEST_FOLDER', os.getcwd())
TEST_LOGS_FOLDER = os.environ.get('TEST_LOGS_FOLDER', TEST_FOLDER)

# 딕셔너리 저장을 위한 디렉토리 설정
DICTIONARY_DIR = os.path.join(TEST_FOLDER, 'dictionary')

# 디렉토리가 존재하지 않으면 생성
os.makedirs(DICTIONARY_DIR, exist_ok=True)
os.makedirs(TEST_LOGS_FOLDER, exist_ok=True)

# 로그 파일 경로 설정
log_file_path = os.path.join(TEST_LOGS_FOLDER, "dictionary_extraction.log")

# 로깅 설정 (DEBUG 레벨로 상세 정보 출력)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseDictionaryExtractor:
    def __init__(self, username, password, connect_string):
        """
        데이터베이스 딕셔너리 추출기 초기화
        
        Args:
            username (str): 데이터베이스 사용자 이름
            password (str): 데이터베이스 비밀번호
            connect_string (str): 데이터베이스 연결 문자열
        """
        self.username = username
        self.password = password
        self.connect_string = connect_string
        self.dictionary = {}
        
    def execute_sql(self, sql_command):
        """
        SQL 명령을 실행하고 결과를 반환합니다.
        
        Args:
            sql_command (str): 실행할 SQL 명령
            
        Returns:
            str: SQL 실행 결과
        """
        # 한글 설정을 위한 세션 설정 추가 (출력 무시)
        session_settings = """
        SET PAGESIZE 0
        SET FEEDBACK OFF
        SET HEADING OFF
        SET ECHO OFF
        SET VERIFY OFF
        SET LINESIZE 1000
        
        ALTER SESSION SET NLS_LANGUAGE = 'KOREAN';
        ALTER SESSION SET NLS_TERRITORY = 'KOREA';
        ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS';
        ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF';
        """
        
        # 세션 설정과 SQL 명령 결합
        full_sql_command = session_settings + sql_command
        
        try:
            # 임시 SQL 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.sql', delete=False) as temp_file:
                temp_file.write(full_sql_command)
                temp_file_path = temp_file.name
            
            logger.info(f"SQL 실행 중... (임시 파일: {temp_file_path})")
            
            # SQLPlus 명령 실행 (타임아웃 추가)
            cmd = f"sqlplus -S {self.username}/{self.password}@{self.connect_string} @{temp_file_path}"
            
            # 명령어 로깅 (비밀번호 마스킹)
            masked_cmd = cmd.replace(self.password, '*' * len(self.password))
            logger.debug(f"실행 명령: {masked_cmd}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, 
                                  encoding='utf-8', timeout=300)  # 5분 타임아웃
            
            # 임시 파일 삭제
            os.remove(temp_file_path)
            
            if result.returncode != 0:
                logger.error(f"SQL 실행 오류 (return code: {result.returncode})")
                logger.error(f"STDERR: {result.stderr}")
                logger.error(f"STDOUT: {result.stdout}")
                return ""
            
            logger.info("SQL 실행 완료")
            
            # "세션이 변경되었습니다" 메시지 제거
            output_lines = []
            for line in result.stdout.splitlines():
                if not line.strip().startswith("세션이 변경되었습니다"):
                    output_lines.append(line)
            
            return "\n".join(output_lines)
            
        except subprocess.TimeoutExpired:
            logger.error("SQL 실행 타임아웃 (5분 초과)")
            # 임시 파일 정리
            if 'temp_file_path' in locals():
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            return ""
        except Exception as e:
            logger.error(f"SQL 명령 실행 중 오류 발생: {e}")
            # 임시 파일 정리
            if 'temp_file_path' in locals():
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            return ""
    
    def test_connection(self):
        """
        데이터베이스 연결을 테스트합니다.
        
        Returns:
            bool: 연결 성공 여부
        """
        logger.info("데이터베이스 연결 테스트 중...")
        
        test_sql = """
        SET PAGESIZE 0
        SET FEEDBACK OFF
        SET HEADING OFF
        SET ECHO OFF
        SET VERIFY OFF
        SET LINESIZE 1000
        
        SELECT 'CONNECTION_OK' as status, 
               USER as current_user,
               TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') as current_time
        FROM dual;
        
        EXIT;
        """
        
        result = self.execute_sql(test_sql)
        
        if result and 'CONNECTION_OK' in result:
            logger.info("데이터베이스 연결 성공")
            # 연결 정보 파싱
            lines = [line.strip() for line in result.splitlines() if line.strip()]
            for line in lines:
                if 'CONNECTION_OK' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        logger.info(f"연결된 사용자: {parts[1]}")
                        logger.info(f"서버 시간: {' '.join(parts[2:])}")
            return True
        else:
            logger.error("데이터베이스 연결 실패")
            logger.error(f"테스트 결과: {result}")
            return False

    def get_all_tables(self):
        """
        데이터베이스의 모든 테이블 목록을 가져옵니다.
        
        Returns:
            list: 테이블 이름 목록
        """
        logger.info("데이터베이스에서 테이블 목록 가져오는 중...")
        
        # 먼저 연결 테스트
        test_sql = """
        SET PAGESIZE 0
        SET FEEDBACK OFF
        SET HEADING OFF
        SET ECHO OFF
        SET VERIFY OFF
        SET LINESIZE 1000
        
        SELECT 'CONNECTION_TEST' FROM dual;
        
        EXIT;
        """
        
        test_result = self.execute_sql(test_sql)
        if not test_result or 'CONNECTION_TEST' not in test_result:
            logger.error("데이터베이스 연결 테스트 실패")
            logger.error(f"테스트 결과: {test_result}")
            return []
        
        logger.info("데이터베이스 연결 확인됨")
        
        # 테이블 목록 조회
        sql = """
        SET PAGESIZE 0
        SET FEEDBACK OFF
        SET HEADING OFF
        SET ECHO OFF
        SET VERIFY OFF
        SET LINESIZE 1000
        
        SELECT table_name 
        FROM user_tables 
        ORDER BY table_name;
        
        EXIT;
        """
        
        logger.info("USER_TABLES에서 테이블 목록 조회 중...")
        result = self.execute_sql(sql)
        
        if not result:
            logger.warning("USER_TABLES에서 결과를 가져올 수 없습니다. ALL_TABLES로 시도합니다.")
            
            # ALL_TABLES로 재시도
            sql_all = """
            SET PAGESIZE 0
            SET FEEDBACK OFF
            SET HEADING OFF
            SET ECHO OFF
            SET VERIFY OFF
            SET LINESIZE 1000
            
            SELECT table_name 
            FROM all_tables 
            WHERE owner = USER
            ORDER BY table_name;
            
            EXIT;
            """
            
            result = self.execute_sql(sql_all)
        
        if not result:
            logger.error("테이블 목록을 가져올 수 없습니다.")
            return []
        
        tables = [line.strip() for line in result.splitlines() if line.strip()]
        
        # SQLPlus 메시지 및 빈 줄 제거
        tables = [table for table in tables if table and not table.startswith("SQL") and not table.startswith("세션이")]
        
        logger.info(f"{len(tables)}개의 테이블을 발견했습니다.")
        
        # 테이블 목록 로깅 (처음 10개만)
        if tables:
            logger.info("발견된 테이블 목록 (처음 10개):")
            for i, table in enumerate(tables[:10]):
                logger.info(f"  {i+1}. {table}")
            if len(tables) > 10:
                logger.info(f"  ... 외 {len(tables) - 10}개 테이블")
        
        return tables
    
    def get_table_columns(self, table_name):
        """
        특정 테이블의 모든 컬럼 정보를 가져옵니다.
        
        Args:
            table_name (str): 테이블 이름
            
        Returns:
            list: 컬럼 정보 목록 (이름, 데이터 타입)
        """
        # 테이블 이름에 따옴표 추가
        quoted_table = f'"{table_name}"'
        
        sql = f"""
        SET PAGESIZE 0
        SET FEEDBACK OFF
        SET HEADING OFF
        SET ECHO OFF
        SET VERIFY OFF
        SET LINESIZE 1000
        
        SELECT column_name, data_type, data_length, nullable
        FROM user_tab_columns
        WHERE table_name = '{table_name}'
        ORDER BY column_id;
        
        EXIT;
        """
        
        result = self.execute_sql(sql)
        columns_data = [line.strip() for line in result.splitlines() if line.strip()]
        
        # SQLPlus 메시지 및 빈 줄 제거
        columns_data = [col for col in columns_data if col and not col.startswith("SQL")]
        
        columns = []
        for column_info in columns_data:
            parts = column_info.split()
            if len(parts) >= 2:
                column_name = parts[0]
                data_type = parts[1]
                
                # 데이터 길이 정보 추출 (있는 경우)
                data_length = None
                if len(parts) >= 3 and parts[2].isdigit():
                    data_length = int(parts[2])
                
                # NULL 허용 여부 추출 (있는 경우)
                nullable = None
                if len(parts) >= 4:
                    nullable = parts[3]
                
                columns.append({
                    'name': column_name,
                    'type': data_type,
                    'length': data_length,
                    'nullable': nullable
                })
        
        return columns
    
    def get_column_sample_values(self, table_name, column_name, data_type, sample_count=1):
        """
        특정 컬럼의 샘플 값을 가져옵니다.
        
        Args:
            table_name (str): 테이블 이름
            column_name (str): 컬럼 이름
            data_type (str): 데이터 타입
            sample_count (int): 가져올 샘플 개수 (기본값: 1)
            
        Returns:
            list: 샘플 값 목록
        """
        # CLOB, BLOB 등 대용량 데이터 타입은 건너뛰기
        if data_type in ['CLOB', 'BLOB', 'LONG', 'LONG RAW']:
            return []
        
        try:
            # 테이블과 컬럼 이름에 따옴표 추가
            quoted_table = f'"{table_name}"'
            quoted_column = f'"{column_name}"'
            
            sql = f"""
            SET PAGESIZE 0
            SET FEEDBACK OFF
            SET HEADING OFF
            SET ECHO OFF
            SET VERIFY OFF
            SET LINESIZE 1000
            SET LONG 1000
            
            SELECT {quoted_column}
            FROM {quoted_table}
            WHERE {quoted_column} IS NOT NULL
            AND ROWNUM = 1;
            
            EXIT;
            """
            
            result = self.execute_sql(sql)
            values = [line.strip() for line in result.splitlines() if line.strip()]
            
            # SQLPlus 메시지 및 빈 줄 제거
            values = [val for val in values if val and not val.startswith("SQL") and not "세션이 변경되었습니다" in val]
            
            return values
        except Exception as e:
            logger.error(f"컬럼 {table_name}.{column_name} 샘플 값 추출 중 오류: {e}")
            return []
    
    def classify_column_type(self, column_name, data_type):
        """
        컬럼 이름과 데이터 타입을 기반으로 컬럼 유형을 분류합니다.
        
        Args:
            column_name (str): 컬럼 이름
            data_type (str): 데이터 타입
            
        Returns:
            str: 컬럼 유형 분류
        """
        column_name = column_name.lower()
        
        # 데이터 타입 기반 분류
        if 'DATE' in data_type or 'TIMESTAMP' in data_type:
            return 'date'
        elif 'NUMBER' in data_type or 'INT' in data_type or 'FLOAT' in data_type:
            # 금액 관련 컬럼
            if any(keyword in column_name for keyword in ['amt', 'amount', 'price', 'cost', 'fee']):
                return 'amount'
            # 수량 관련 컬럼
            elif any(keyword in column_name for keyword in ['cnt', 'count', 'qty', 'quantity']):
                return 'count'
            # 코드/ID 관련 컬럼
            elif any(keyword in column_name for keyword in ['id', 'no', 'seq', 'code', 'cd']):
                return 'id'
            else:
                return 'number'
        elif 'CHAR' in data_type or 'VARCHAR' in data_type:
            # 이름 관련 컬럼
            if any(keyword in column_name for keyword in ['name', 'nm']):
                return 'name'
            # 설명 관련 컬럼
            elif any(keyword in column_name for keyword in ['desc', 'description', 'remark', 'comment']):
                return 'description'
            # 코드 관련 컬럼
            elif any(keyword in column_name for keyword in ['code', 'cd']):
                return 'code'
            # 상태 관련 컬럼
            elif any(keyword in column_name for keyword in ['status', 'state', 'flag', 'yn']):
                return 'status'
            # 연락처 관련 컬럼
            elif any(keyword in column_name for keyword in ['phone', 'tel', 'email', 'contact']):
                return 'contact'
            # 주소 관련 컬럼
            elif any(keyword in column_name for keyword in ['addr', 'address', 'location']):
                return 'address'
            else:
                return 'text'
        else:
            return 'other'
    
    def extract_dictionary(self):
        """
        데이터베이스의 모든 테이블과 컬럼 정보를 추출하여 딕셔너리를 생성합니다.
        """
        logger.info("데이터베이스 딕셔너리 추출 시작...")
        start_time = datetime.now()
        
        # 모든 테이블 목록 가져오기
        tables = self.get_all_tables()
        
        # 각 테이블의 컬럼 정보 및 샘플 데이터 추출
        for i, table_name in enumerate(tables, 1):
            logger.info(f"테이블 처리 중: {table_name} ({i}/{len(tables)})")
            
            # 테이블의 컬럼 정보 가져오기
            columns = self.get_table_columns(table_name)
            
            # 테이블 정보 저장
            self.dictionary[table_name] = {
                'columns': {}
            }
            
            # 각 컬럼의 샘플 데이터 추출
            for column in columns:
                column_name = column['name']
                data_type = column['type']
                
                # 컬럼 유형 분류
                category = self.classify_column_type(column_name, data_type)
                
                # 샘플 값 추출
                sample_values = self.get_column_sample_values(table_name, column_name, data_type)
                
                # 컬럼 정보 저장
                self.dictionary[table_name]['columns'][column_name] = {
                    'type': data_type,
                    'category': category,
                    'length': column['length'],
                    'nullable': column['nullable'],
                    'sample_values': sample_values
                }
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"데이터베이스 딕셔너리 추출 완료 (소요 시간: {duration:.2f}초)")
    
    def save_dictionary(self, output_file="all_dictionary.json"):
        """
        추출한 딕셔너리를 JSON 파일로 저장합니다.
        
        Args:
            output_file (str): 출력 파일 이름 (경로 제외)
        """
        # TEST_FOLDER/dictionary/ 디렉토리에 저장
        output_path = os.path.join(DICTIONARY_DIR, output_file)
        
        logger.info(f"딕셔너리를 {output_path}로 저장 중...")
        
        # 한글 인코딩 문제 해결을 위한 설정
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.dictionary, f, indent=2, ensure_ascii=False)
        
        # 파일 크기 및 통계 정보 출력
        file_size = os.path.getsize(output_path)
        table_count = len(self.dictionary)
        total_columns = sum(len(table_data.get('columns', {})) for table_data in self.dictionary.values())
        
        logger.info(f"딕셔너리가 {output_path}에 저장되었습니다.")
        logger.info(f"파일 크기: {file_size:,} bytes")
        logger.info(f"테이블 수: {table_count}")
        logger.info(f"총 컬럼 수: {total_columns}")
    
    def run(self):
        """
        전체 추출 프로세스를 실행합니다.
        """
        self.extract_dictionary()
        self.save_dictionary()
        logger.info("데이터베이스 딕셔너리 추출 프로세스가 완료되었습니다.")


def check_environment_variables():
    """
    필수 환경변수들이 설정되어 있는지 확인합니다.
    """
    logger.info("환경변수 확인 중...")
    
    # 필수 환경변수 목록
    required_env_vars = [
        'ORACLE_SVC_USER',
        'ORACLE_SVC_PASSWORD', 
        'ORACLE_SVC_CONNECT_STRING'
    ]
    
    # 권장 환경변수 목록
    recommended_env_vars = [
        'TEST_FOLDER'
    ]
    
    # 선택적 환경변수 목록 (기본값 있음)
    optional_env_vars = [
        'TEST_LOGS_FOLDER'
    ]
    
    missing_vars = []
    
    # 필수 환경변수 확인
    logger.info("필수 환경변수 확인:")
    for var in required_env_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            logger.error(f"✗ {var}: 설정되지 않음")
        else:
            # 비밀번호는 마스킹하여 로그에 출력
            if 'PASSWORD' in var:
                logger.info(f"✓ {var}: {'*' * len(value)}")
            else:
                logger.info(f"✓ {var}: {value}")
    
    # 권장 환경변수 확인
    logger.info("권장 환경변수 확인:")
    for var in recommended_env_vars:
        value = os.environ.get(var)
        if value:
            logger.info(f"✓ {var}: {value}")
        else:
            logger.warning(f"- {var}: 설정되지 않음 (기본값: 현재 작업 디렉토리)")
    
    # 선택적 환경변수 확인 및 기본값 표시
    logger.info("선택적 환경변수 확인:")
    for var in optional_env_vars:
        value = os.environ.get(var)
        if value:
            logger.info(f"✓ {var}: {value}")
        else:
            default_value = TEST_FOLDER if var == 'TEST_LOGS_FOLDER' else '.'
            logger.info(f"- {var}: 설정되지 않음 (기본값: {default_value})")
    
    # 필수 환경변수가 누락된 경우 종료
    if missing_vars:
        logger.error("다음 환경변수들을 설정해주세요:")
        for var in missing_vars:
            logger.error(f"  export {var}=<값>")
        logger.error("스크립트를 종료합니다.")
        exit(1)
    
    logger.info("모든 필수 환경변수가 설정되었습니다.")
    
    # 디렉토리 경로 확인
    logger.info(f"딕셔너리 저장 경로: {os.path.abspath(DICTIONARY_DIR)}")
    logger.info(f"로그 파일 저장 경로: {os.path.abspath(TEST_LOGS_FOLDER)}")


if __name__ == "__main__":
    # 환경변수 확인
    check_environment_variables()
    
    # 데이터베이스 연결 정보
    DB_USERNAME = os.environ.get('ORACLE_SVC_USER')
    DB_PASSWORD = os.environ.get('ORACLE_SVC_PASSWORD')
    DB_CONNECT_STRING = os.environ.get('ORACLE_SVC_CONNECT_STRING')
    
    # 딕셔너리 추출기 생성
    extractor = DatabaseDictionaryExtractor(DB_USERNAME, DB_PASSWORD, DB_CONNECT_STRING)
    
    # 연결 테스트 먼저 수행
    logger.info("=" * 60)
    logger.info("데이터베이스 딕셔너리 추출 시작")
    logger.info("=" * 60)
    
    if not extractor.test_connection():
        logger.error("데이터베이스 연결에 실패했습니다. 다음 사항을 확인해주세요:")
        logger.error("1. Oracle 서버가 실행 중인지 확인")
        logger.error("2. 연결 정보가 올바른지 확인 (ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_SVC_CONNECT_STRING)")
        logger.error("3. SQLPlus가 설치되어 있고 PATH에 포함되어 있는지 확인")
        logger.error("4. 네트워크 연결 상태 확인")
        exit(1)
    
    # 딕셔너리 추출 실행
    try:
        extractor.run()
        logger.info("=" * 60)
        logger.info("데이터베이스 딕셔너리 추출 완료")
        logger.info("=" * 60)
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단되었습니다.")
        exit(1)
    except Exception as e:
        logger.error(f"딕셔너리 추출 중 오류 발생: {e}")
        exit(1)
