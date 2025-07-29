#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 DB 연결을 통한 MyBatis XML 테스터

사용법:
    python3 mybatis_db_test.py [--dbms src|tgt|all] [--output 결과파일명]

예시:
    # Oracle XML 파일만 테스트 (extract/*.xml)
    python3 mybatis_db_test.py --dbms src
    
    # PostgreSQL/MySQL XML 파일만 테스트 (transform/*.xml)
    python3 mybatis_db_test.py --dbms tgt
    
    # 모든 XML 파일 테스트
    python3 mybatis_db_test.py --dbms all
    
    # 결과 파일 지정
    python3 mybatis_db_test.py --dbms src --output oracle_test_result.json

경로 설정:
    기본 경로: $APP_LOGS_FOLDER/mapper
    - src: $APP_LOGS_FOLDER/mapper/*/extract/*.xml
    - tgt: $APP_LOGS_FOLDER/mapper/*/transform/*.xml
    - all: $APP_LOGS_FOLDER/mapper/**/*.xml

SQL 실행 정책:
    - SELECT: 실제 실행하여 결과 확인
    - INSERT/UPDATE/DELETE: 트랜잭션 내에서 실행 후 롤백 (안전한 검증)

환경 변수 설정 (필수):
    Oracle (src):
        export ORACLE_HOST="your-oracle-host"
        export ORACLE_PORT="1521"
        export ORACLE_SVC_USER="your-user"
        export ORACLE_SVC_PASSWORD="your-password"
        export ORACLE_SVC_CONNECT_STRING="your-service-name"
    
    MySQL (tgt):
        export MYSQL_HOST="your-mysql-host"
        export MYSQL_TCP_PORT="3306"
        export MYSQL_SVC_USER="your-user"
        export MYSQL_SVC_PASSWORD="your-password"
        export MYSQL_DATABASE="your-database"
    
    PostgreSQL (tgt):
        export PGHOST="your-postgresql-host"
        export PGPORT="5432"
        export PG_SVC_USER="your-user"
        export PG_SVC_PASSWORD="your-password"
        export PGDATABASE="your-database"

필요한 Python 라이브러리:
    pip install cx_Oracle pymysql psycopg2-binary
"""

import os
import re
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import argparse
import time

# DB 연결을 위한 라이브러리
try:
    import cx_Oracle
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False
    logging.warning("cx_Oracle이 설치되지 않았습니다. Oracle 테스트를 건너뜁니다.")

try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logging.warning("pymysql이 설치되지 않았습니다. MySQL 테스트를 건너뜁니다.")

try:
    import psycopg2
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    logging.warning("psycopg2가 설치되지 않았습니다. PostgreSQL 테스트를 건너뜁니다.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DbConfig:
    """DB 연결 설정"""
    dbms_type: str
    host: str
    port: int
    database: str
    user: str
    password: str
    service_name: str = None
    sid: str = None

@dataclass
class SqlElement:
    """SQL 요소 정보"""
    id: str
    type: str
    content: str
    namespace: str
    parameters: List[str]
    dynamic_conditions: List[str]
    includes: List[str]
    dbms_type: str

class EnvironmentConfig:
    """환경 변수에서 DB 설정을 읽어오는 클래스"""
    
    @staticmethod
    def get_oracle_config() -> Optional[DbConfig]:
        """Oracle 연결 설정 가져오기"""
        try:
            return DbConfig(
                dbms_type='oracle',
                host=os.environ.get('ORACLE_HOST'),
                port=int(os.environ.get('ORACLE_PORT', 1521)),
                database=os.environ.get('ORACLE_SVC_CONNECT_STRING'),
                user=os.environ.get('ORACLE_SVC_USER'),
                password=os.environ.get('ORACLE_SVC_PASSWORD'),
                service_name=os.environ.get('ORACLE_SVC_CONNECT_STRING'),
                sid=os.environ.get('ORACLE_SID')
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Oracle 환경 변수 설정 오류: {e}")
            return None
    
    @staticmethod
    def get_mysql_config() -> Optional[DbConfig]:
        """MySQL 연결 설정 가져오기"""
        try:
            return DbConfig(
                dbms_type='mysql',
                host=os.environ.get('MYSQL_HOST'),
                port=int(os.environ.get('MYSQL_TCP_PORT', 3306)),
                database=os.environ.get('MYSQL_DATABASE'),
                user=os.environ.get('MYSQL_SVC_USER'),
                password=os.environ.get('MYSQL_SVC_PASSWORD')
            )
        except (KeyError, ValueError) as e:
            logger.error(f"MySQL 환경 변수 설정 오류: {e}")
            return None
    
    @staticmethod
    def get_postgresql_config() -> Optional[DbConfig]:
        """PostgreSQL 연결 설정 가져오기"""
        try:
            return DbConfig(
                dbms_type='postgresql',
                host=os.environ.get('PGHOST'),
                port=int(os.environ.get('PGPORT', 5432)),
                database=os.environ.get('PGDATABASE'),
                user=os.environ.get('PG_SVC_USER'),
                password=os.environ.get('PG_SVC_PASSWORD')
            )
        except (KeyError, ValueError) as e:
            logger.error(f"PostgreSQL 환경 변수 설정 오류: {e}")
            return None

class DatabaseConnector:
    """DB 연결 관리 클래스"""
    
    def __init__(self, config: DbConfig):
        self.config = config
        self.connection = None
    
    def connect(self) -> bool:
        """DB 연결"""
        try:
            if self.config.dbms_type == 'oracle':
                if not ORACLE_AVAILABLE:
                    logger.error("Oracle 라이브러리가 설치되지 않았습니다.")
                    return False
                
                # Oracle 연결
                dsn = cx_Oracle.makedsn(
                    self.config.host, 
                    self.config.port, 
                    service_name=self.config.service_name
                )
                self.connection = cx_Oracle.connect(
                    self.config.user, 
                    self.config.password, 
                    dsn
                )
                
            elif self.config.dbms_type == 'mysql':
                if not MYSQL_AVAILABLE:
                    logger.error("MySQL 라이브러리가 설치되지 않았습니다.")
                    return False
                
                # MySQL 연결
                self.connection = pymysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    database=self.config.database,
                    charset='utf8mb4'
                )
                
            elif self.config.dbms_type == 'postgresql':
                if not POSTGRESQL_AVAILABLE:
                    logger.error("PostgreSQL 라이브러리가 설치되지 않았습니다.")
                    return False
                
                # PostgreSQL 연결
                self.connection = psycopg2.connect(
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password
                )
            
            logger.info(f"{self.config.dbms_type.upper()} DB 연결 성공")
            return True
            
        except Exception as e:
            logger.error(f"{self.config.dbms_type.upper()} DB 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """DB 연결 해제"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_sql(self, sql: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """SQL 실행"""
        if not self.connection:
            return {'success': False, 'error': 'DB 연결이 없습니다.'}
        
        try:
            cursor = self.connection.cursor()
            
            # SQL 타입 확인
            sql_type = sql.strip().upper().split()[0]
            
            # SELECT인 경우
            if sql_type == 'SELECT':
                # SQL 실행
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                
                # 결과 가져오기
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = {
                    'success': True,
                    'sql_type': 'SELECT',
                    'columns': columns,
                    'rows': rows,
                    'row_count': len(rows)
                }
            else:
                # INSERT, UPDATE, DELETE는 트랜잭션 내에서 실행 후 롤백
                try:
                    # DBMS별 트랜잭션 처리
                    if self.config.dbms_type == 'postgresql':
                        # PostgreSQL은 autocommit을 False로 설정
                        self.connection.autocommit = False
                    elif self.config.dbms_type in ['mysql', 'oracle']:
                        # MySQL, Oracle은 begin() 메서드 사용
                        self.connection.begin()
                    
                    # SQL 실행
                    if params:
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)
                    
                    # 영향받은 행 수 확인
                    affected_rows = cursor.rowcount
                    
                    # 트랜잭션 롤백 (변경사항 취소)
                    self.connection.rollback()
                    
                    # PostgreSQL autocommit 복원
                    if self.config.dbms_type == 'postgresql':
                        self.connection.autocommit = True
                    
                    result = {
                        'success': True,
                        'sql_type': sql_type,
                        'message': f'{sql_type} SQL 실행 성공 (트랜잭션 롤백됨)',
                        'affected_rows': affected_rows
                    }
                    
                except Exception as tx_error:
                    # 오류 발생 시에도 롤백 시도
                    try:
                        self.connection.rollback()
                        if self.config.dbms_type == 'postgresql':
                            self.connection.autocommit = True
                    except:
                        pass
                    
                    result = {
                        'success': False,
                        'sql_type': sql_type,
                        'error': f'{sql_type} SQL 실행 실패: {str(tx_error)}'
                    }
            
            cursor.close()
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'sql': sql,
                'params': params
            }

class MyBatisParser:
    """MyBatis XML 파서"""
    
    def __init__(self):
        self.sql_fragments: Dict[str, str] = {}
        self.namespace = ""
        self.xml_files: Dict[str, List[SqlElement]] = {}
    
    def parse_directory(self, directory: str, dbms_type: str = None) -> Dict[str, List[SqlElement]]:
        """디렉토리의 XML 파일들을 DBMS 타입별로 파싱"""
        xml_files = []
        
        # DBMS 타입에 따른 서브디렉토리 결정
        subdir = None
        if dbms_type == 'src':
            subdir = 'extract'
        elif dbms_type == 'tgt':
            subdir = 'transform'
        
        # XML 파일 검색
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.xml'):
                    # 특정 서브디렉토리 필터링
                    if subdir and subdir in root:
                        xml_files.append(os.path.join(root, file))
                    elif not subdir:  # all인 경우 모든 XML 파일
                        xml_files.append(os.path.join(root, file))
        
        # 먼저 sql 조각들을 파싱
        for xml_file in xml_files:
            elements = self.parse_xml_file(xml_file, dbms_type)
            if elements:
                self.xml_files[xml_file] = elements
                # sql 조각들을 수집
                for element in elements:
                    if element.type == 'sql':
                        self.sql_fragments[element.id] = element.content
        
        return self.xml_files
    
    def parse_xml_file(self, xml_file: str, dbms_type: str = None) -> List[SqlElement]:
        """XML 파일 파싱"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            self.namespace = root.get('namespace', '')
            elements = []
            
            for child in root:
                if child.tag in ['select', 'insert', 'update', 'delete', 'sql']:
                    element = self._parse_element(child, dbms_type)
                    if element:
                        elements.append(element)
            
            return elements
            
        except Exception as e:
            logger.error(f"XML 파싱 오류 {xml_file}: {e}")
            return []
    
    def _parse_element(self, element, dbms_type: str = None) -> Optional[SqlElement]:
        """요소 파싱"""
        element_id = element.get('id', '')
        element_type = element.tag
        
        # SQL 내용 추출
        content = self._extract_content(element)
        
        # 파라미터 추출
        parameters = self._extract_parameters(content)
        
        # 동적 조건 추출
        dynamic_conditions = self._extract_dynamic_conditions(content)
        
        # include 참조 추출
        includes = self._extract_includes(content)
        
        return SqlElement(
            id=element_id,
            type=element_type,
            content=content,
            namespace=self.namespace,
            parameters=parameters,
            dynamic_conditions=dynamic_conditions,
            includes=includes,
            dbms_type=dbms_type or 'unknown'
        )
    
    def _extract_content(self, element) -> str:
        """요소에서 내용 추출"""
        content = ""
        
        # 텍스트 노드들 수집
        for node in element.iter():
            if node.text and node.text.strip():
                content += node.text.strip() + " "
            if node.tail and node.tail.strip():
                content += node.tail.strip() + " "
        
        return content.strip()
    
    def _extract_parameters(self, content: str) -> List[str]:
        """바인드 파라미터 추출"""
        pattern = r'#\{([^}]+)\}'
        matches = re.findall(pattern, content)
        return list(set(matches))
    
    def _extract_dynamic_conditions(self, content: str) -> List[str]:
        """동적 조건 추출"""
        conditions = []
        
        # <if test="condition">
        if_pattern = r'<if\s+test="([^"]+)">'
        if_matches = re.findall(if_pattern, content)
        conditions.extend(if_matches)
        
        # <when test="condition">
        when_pattern = r'<when\s+test="([^"]+)">'
        when_matches = re.findall(when_pattern, content)
        conditions.extend(when_matches)
        
        # <foreach collection="name">
        foreach_pattern = r'<foreach\s+[^>]*collection="([^"]+)"[^>]*>'
        foreach_matches = re.findall(foreach_pattern, content)
        conditions.extend(foreach_matches)
        
        return list(set(conditions))
    
    def _extract_includes(self, content: str) -> List[str]:
        """include 참조 추출"""
        pattern = r'<include\s+refid="([^"]+)"\s*/>'
        matches = re.findall(pattern, content)
        return list(set(matches))

class DynamicSqlProcessor:
    """동적 SQL 처리기"""
    
    def __init__(self, sql_fragments: Dict[str, str]):
        self.sql_fragments = sql_fragments
    
    def process_sql(self, sql_content: str, parameters: Dict[str, Any]) -> Tuple[str, List[str]]:
        """SQL 처리"""
        processed_sql = sql_content
        used_params = []
        
        # include 처리
        processed_sql = self._process_includes(processed_sql)
        
        # 동적 조건 처리
        processed_sql = self._process_dynamic_conditions(processed_sql, parameters, used_params)
        
        # 바인드 파라미터 처리
        processed_sql = self._process_bind_parameters(processed_sql, parameters, used_params)
        
        # ${} 스타일 변수 처리
        processed_sql = self._process_dollar_variables(processed_sql, parameters, used_params)
        
        # XML 태그 정리
        processed_sql = self._clean_xml_tags(processed_sql)
        
        return processed_sql.strip(), used_params
    
    def _process_includes(self, sql: str) -> str:
        """include 참조 처리"""
        pattern = r'<include\s+refid="([^"]+)"\s*/>'
        
        def replace_include(match):
            ref_id = match.group(1)
            if ref_id in self.sql_fragments:
                return self.sql_fragments[ref_id]
            else:
                return f"<!-- INCLUDE_NOT_FOUND: {ref_id} -->"
        
        return re.sub(pattern, replace_include, sql)
    
    def _process_dynamic_conditions(self, sql: str, params: Dict[str, Any], used_params: List[str]) -> str:
        """동적 조건 처리"""
        # <if> 처리
        sql = self._process_if_conditions(sql, params, used_params)
        
        # <choose> 처리
        sql = self._process_choose_conditions(sql, params, used_params)
        
        # <foreach> 처리
        sql = self._process_foreach_conditions(sql, params, used_params)
        
        return sql
    
    def _process_if_conditions(self, sql: str, params: Dict[str, Any], used_params: List[str]) -> str:
        """<if> 조건 처리"""
        pattern = r'<if\s+test="([^"]+)">(.*?)</if>'
        
        def replace_if(match):
            condition = match.group(1)
            content = match.group(2)
            
            if self._evaluate_condition(condition, params):
                return content
            else:
                return ""
        
        return re.sub(pattern, replace_if, sql, flags=re.DOTALL)
    
    def _process_choose_conditions(self, sql: str, params: Dict[str, Any], used_params: List[str]) -> str:
        """<choose> 조건 처리"""
        choose_pattern = r'<choose>(.*?)</choose>'
        
        def replace_choose(match):
            choose_content = match.group(1)
            
            # <when> 조건들 처리
            when_pattern = r'<when\s+test="([^"]+)">(.*?)</when>'
            when_matches = re.findall(when_pattern, choose_content, re.DOTALL)
            
            for condition, content in when_matches:
                if self._evaluate_condition(condition, params):
                    return content
            
            # <otherwise> 처리
            otherwise_pattern = r'<otherwise>(.*?)</otherwise>'
            otherwise_match = re.search(otherwise_pattern, choose_content, re.DOTALL)
            if otherwise_match:
                return otherwise_match.group(1)
            
            return ""
        
        return re.sub(choose_pattern, replace_choose, sql, flags=re.DOTALL)
    
    def _process_foreach_conditions(self, sql: str, params: Dict[str, Any], used_params: List[str]) -> str:
        """<foreach> 처리"""
        pattern = r'<foreach\s+collection="([^"]+)"\s+item="([^"]+)"[^>]*>(.*?)</foreach>'
        
        def replace_foreach(match):
            collection_name = match.group(1)
            item_name = match.group(2)
            content = match.group(3)
            
            if collection_name in params and isinstance(params[collection_name], (list, tuple)):
                items = params[collection_name]
                result = []
                for item in items:
                    item_content = content.replace(f"#{item_name}", str(item))
                    result.append(item_content)
                
                return ",".join(result)
            else:
                return ""
        
        return re.sub(pattern, replace_foreach, sql, flags=re.DOTALL)
    
    def _process_bind_parameters(self, sql: str, params: Dict[str, Any], used_params: List[str]) -> str:
        """바인드 파라미터 처리"""
        pattern = r'#\{([^}]+)\}'
        
        def replace_param(match):
            param_name = match.group(1)
            if param_name in params:
                used_params.append(param_name)
                value = params[param_name]
                if isinstance(value, str):
                    return f"'{value}'"
                else:
                    return str(value)
            else:
                return f"<!-- PARAM_NOT_FOUND: {param_name} -->"
        
        return re.sub(pattern, replace_param, sql)
    
    def _process_dollar_variables(self, sql: str, params: Dict[str, Any], used_params: List[str]) -> str:
        """${} 스타일 변수 처리"""
        pattern = r'\$\{([^}]+)\}'
        
        def replace_variable(match):
            var_name = match.group(1)
            if var_name in params:
                used_params.append(var_name)
                value = params[var_name]
                return str(value)
            else:
                # queryId와 같은 기본 변수들은 빈 문자열로 처리
                if var_name.lower() in ['queryid', 'query_id']:
                    return ""
                return f"/* VARIABLE_NOT_FOUND: {var_name} */"
        
        return re.sub(pattern, replace_variable, sql)
    
    def _clean_xml_tags(self, sql: str) -> str:
        """XML 태그 정리"""
        # 남은 XML 태그들 제거
        sql = re.sub(r'<[^>]+>', '', sql)
        # 연속된 공백 정리
        sql = re.sub(r'\s+', ' ', sql)
        return sql.strip()
    
    def _evaluate_condition(self, condition: str, params: Dict[str, Any]) -> bool:
        """조건 평가"""
        # 파라미터 존재 여부 확인
        if condition in params:
            value = params[condition]
            if isinstance(value, bool):
                return value
            elif isinstance(value, (list, tuple)):
                return len(value) > 0
            elif isinstance(value, str):
                return value.strip() != ""
            else:
                return value is not None
        
        # null 체크
        if condition.endswith(' != null'):
            param_name = condition[:-9].strip()
            return param_name in params and params[param_name] is not None
        
        if condition.endswith(' == null'):
            param_name = condition[:-8].strip()
            return param_name not in params or params[param_name] is None
        
        # 복합 조건 (간단한 버전)
        if ' and ' in condition:
            parts = condition.split(' and ')
            return all(self._evaluate_condition(part.strip(), params) for part in parts)
        
        if ' or ' in condition:
            parts = condition.split(' or ')
            return any(self._evaluate_condition(part.strip(), params) for part in parts)
        
        return False

class MyBatisDbTester:
    """실제 DB 연결을 통한 MyBatis 테스터"""
    
    def __init__(self):
        self.parser = MyBatisParser()
        self.processor = None
        self.db_connectors = {}
    
    def setup_db_connections(self, dbms_type: str = None) -> bool:
        """DB 연결 설정"""
        # DBMS 타입에 따른 연결 설정
        if dbms_type == 'src':
            # Oracle만 연결
            oracle_config = EnvironmentConfig.get_oracle_config()
            if oracle_config and ORACLE_AVAILABLE:
                self.db_connectors['oracle'] = DatabaseConnector(oracle_config)
                if not self.db_connectors['oracle'].connect():
                    logger.warning("Oracle 연결 실패")
        elif dbms_type == 'tgt':
            # PostgreSQL과 MySQL만 연결
            mysql_config = EnvironmentConfig.get_mysql_config()
            if mysql_config and MYSQL_AVAILABLE:
                self.db_connectors['mysql'] = DatabaseConnector(mysql_config)
                if not self.db_connectors['mysql'].connect():
                    logger.warning("MySQL 연결 실패")
            
            pg_config = EnvironmentConfig.get_postgresql_config()
            if pg_config and POSTGRESQL_AVAILABLE:
                self.db_connectors['postgresql'] = DatabaseConnector(pg_config)
                if not self.db_connectors['postgresql'].connect():
                    logger.warning("PostgreSQL 연결 실패")
        else:
            # all인 경우 모든 DB 연결
            oracle_config = EnvironmentConfig.get_oracle_config()
            if oracle_config and ORACLE_AVAILABLE:
                self.db_connectors['oracle'] = DatabaseConnector(oracle_config)
                if not self.db_connectors['oracle'].connect():
                    logger.warning("Oracle 연결 실패")
            
            mysql_config = EnvironmentConfig.get_mysql_config()
            if mysql_config and MYSQL_AVAILABLE:
                self.db_connectors['mysql'] = DatabaseConnector(mysql_config)
                if not self.db_connectors['mysql'].connect():
                    logger.warning("MySQL 연결 실패")
            
            pg_config = EnvironmentConfig.get_postgresql_config()
            if pg_config and POSTGRESQL_AVAILABLE:
                self.db_connectors['postgresql'] = DatabaseConnector(pg_config)
                if not self.db_connectors['postgresql'].connect():
                    logger.warning("PostgreSQL 연결 실패")
        
        return len(self.db_connectors) > 0
    
    def test_directory(self, directory: str, dbms_type: str = None) -> Dict[str, Any]:
        """디렉토리 테스트"""
        logger.info(f"디렉토리 파싱 중: {directory} (DBMS: {dbms_type or 'all'})")
        
        # DB 연결 설정
        if not self.setup_db_connections(dbms_type):
            logger.error("사용 가능한 DB 연결이 없습니다.")
            return {'error': 'DB 연결 실패'}
        
        # XML 파일 파싱
        xml_files = self.parser.parse_directory(directory, dbms_type)
        
        # 프로세서 초기화
        self.processor = DynamicSqlProcessor(self.parser.sql_fragments)
        
        results = {
            'directory': directory,
            'dbms_type': dbms_type or 'all',
            'sql_fragments': list(self.parser.sql_fragments.keys()),
            'files': [],
            'db_connections': list(self.db_connectors.keys())
        }
        
        # 각 파일 테스트
        for xml_file, elements in xml_files.items():
            file_result = self._test_file(xml_file, elements)
            results['files'].append(file_result)
        
        # DB 연결 해제
        for connector in self.db_connectors.values():
            connector.disconnect()
        
        return results
    
    def _test_file(self, xml_file: str, elements: List[SqlElement]) -> Dict[str, Any]:
        """파일 테스트"""
        logger.info(f"파일 테스트 중: {xml_file}")
        
        file_result = {
            'file': xml_file,
            'namespace': elements[0].namespace if elements else '',
            'dbms_type': elements[0].dbms_type if elements else 'unknown',
            'elements': []
        }
        
        # 각 요소 테스트
        for element in elements:
            if element.type in ['select', 'insert', 'update', 'delete']:
                element_result = self._test_element(element)
                file_result['elements'].append(element_result)
        
        return file_result
    
    def _test_element(self, element: SqlElement) -> Dict[str, Any]:
        """요소 테스트"""
        logger.info(f"  요소 테스트 중: {element.id} ({element.type}) - {element.dbms_type}")
        
        # 테스트 파라미터 생성
        test_params = self._generate_test_parameters(element.parameters, element.dbms_type)
        
        try:
            # SQL 처리
            processed_sql, used_params = self.processor.process_sql(element.content, test_params)
            
            # DB 실행 테스트
            db_test_results = self._execute_db_test(processed_sql, test_params, element.dbms_type)
            
            return {
                'id': element.id,
                'type': element.type,
                'dbms_type': element.dbms_type,
                'original_sql': element.content,
                'processed_sql': processed_sql,
                'parameters': element.parameters,
                'test_parameters': test_params,
                'used_parameters': used_params,
                'dynamic_conditions': element.dynamic_conditions,
                'includes': element.includes,
                'db_test_results': db_test_results,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"    오류: {e}")
            return {
                'id': element.id,
                'type': element.type,
                'dbms_type': element.dbms_type,
                'error': str(e),
                'status': 'error'
            }
    
    def _execute_db_test(self, sql: str, params: Dict[str, Any], dbms_type: str) -> Dict[str, Any]:
        """DB 실행 테스트"""
        results = {}
        
        # 각 DB에서 테스트 실행
        for db_name, connector in self.db_connectors.items():
            try:
                # SQL 실행
                result = connector.execute_sql(sql, params)
                results[db_name] = result
                
                if result['success']:
                    logger.info(f"    {db_name.upper()} 실행 성공")
                else:
                    logger.warning(f"    {db_name.upper()} 실행 실패: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                results[db_name] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"    {db_name.upper()} 실행 오류: {e}")
        
        return results
    
    def _generate_test_parameters(self, param_names: List[str], dbms_type: str) -> Dict[str, Any]:
        """DBMS별 테스트 파라미터 생성"""
        params = {
            'queryId': '',  # queryId는 기본적으로 빈 문자열
            'QUERYID': '',  # 대문자 버전도 추가
        }
        
        for param in param_names:
            if 'id' in param.lower() or 'seq' in param.lower():
                params[param] = 1
            elif 'name' in param.lower():
                params[param] = "test_name"
            elif 'date' in param.lower():
                # DBMS별 날짜 형식 차이
                if dbms_type == 'src':  # Oracle
                    params[param] = "TO_DATE('2025-01-01', 'YYYY-MM-DD')"
                elif dbms_type == 'tgt':  # PostgreSQL/MySQL
                    params[param] = "'2025-01-01'"
                else:
                    params[param] = "20250101"
            elif 'flag' in param.lower() or 'yn' in param.lower():
                params[param] = "Y"
            elif 'list' in param.lower() or 'array' in param.lower():
                params[param] = [1, 2, 3]
            elif 'count' in param.lower():
                params[param] = 10
            elif 'distinct' in param.lower():
                params[param] = True
            elif 'orderByClause' in param.lower():
                params[param] = "id desc"
            else:
                params[param] = "test_value"
        
        return params

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='실제 DB 연결을 통한 MyBatis XML 테스터')
    parser.add_argument('--dbms', choices=['src', 'tgt', 'all'], default='all',
                       help='DBMS 타입 (src: Oracle, tgt: PostgreSQL/MySQL, all: 전체)')
    parser.add_argument('--output', help='결과 파일명')
    parser.add_argument('--directory', help='매퍼 디렉토리 경로')
    
    args = parser.parse_args()
    
    # 디렉토리 경로 결정
    if args.directory:
        base_mapper_path = args.directory
    else:
        # 환경 변수에서 기본 경로 읽기
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER', '../logs')
        base_mapper_path = os.path.join(app_logs_folder, 'mapper')
    
    if not os.path.isdir(base_mapper_path):
        print(f"매퍼 디렉토리를 찾을 수 없습니다: {base_mapper_path}")
        if not args.directory:
            print(f"APP_LOGS_FOLDER 환경 변수를 확인하세요. 현재값: {os.environ.get('APP_LOGS_FOLDER', '../logs')}")
        sys.exit(1)
    
    tester = MyBatisDbTester()
    results = tester.test_directory(base_mapper_path, args.dbms)
    
    if 'error' in results:
        print(f"❌ 오류: {results['error']}")
        sys.exit(1)
    
    # 결과 출력
    print(f"\n=== 실제 DB 연결 MyBatis 테스트 결과 ===")
    print(f"디렉토리: {results['directory']}")
    print(f"DBMS 타입: {results['dbms_type']}")
    print(f"DB 연결: {', '.join(results['db_connections'])}")
    print(f"SQL 조각 개수: {len(results['sql_fragments'])}")
    print(f"파일 개수: {len(results['files'])}")
    
    if results['sql_fragments']:
        print(f"SQL 조각들: {', '.join(results['sql_fragments'])}")
    
    total_elements = 0
    success_count = 0
    error_count = 0
    db_error_count = 0
    
    # DBMS별로 그룹화하여 출력
    dbms_groups = {}
    for file_result in results['files']:
        for element in file_result['elements']:
            dbms_type = element.get('dbms_type', 'unknown')
            if dbms_type not in dbms_groups:
                dbms_groups[dbms_type] = []
            dbms_groups[dbms_type].append(element)
    
    for dbms_type, elements in dbms_groups.items():
        print(f"\n--- {dbms_type.upper()} DBMS ---")
        
        for element in elements:
            total_elements += 1
            element_has_error = False
            
            if element['status'] == 'success':
                print(f"  ✓ {element['id']} ({element['type']})")
                if element['includes']:
                    print(f"    Includes: {element['includes']}")
                print(f"    처리된 SQL: {element['processed_sql'][:100]}...")
                
                # DB 테스트 결과 출력
                if 'db_test_results' in element:
                    for db_name, result in element['db_test_results'].items():
                        if result['success']:
                            if result.get('sql_type') == 'SELECT':
                                print(f"    {db_name.upper()}: {result['row_count']}행 조회")
                            else:
                                affected_rows = result.get('affected_rows', 0)
                                print(f"    {db_name.upper()}: {affected_rows}행 영향 (롤백됨)")
                        else:
                            print(f"    {db_name.upper()}: 실패 - {result.get('error', 'Unknown error')}")
                            element_has_error = True
                            db_error_count += 1
                
                if not element_has_error:
                    success_count += 1
                else:
                    error_count += 1
            else:
                error_count += 1
                print(f"  ✗ {element['id']} ({element['type']}): {element['error']}")
    
    print(f"\n=== 요약 ===")
    print(f"총 요소: {total_elements}")
    print(f"성공: {success_count}")
    print(f"실패: {error_count}")
    if db_error_count > 0:
        print(f"DB 쿼리 실패: {db_error_count}")
    
    # 결과 저장
    if args.output:
        output_file = args.output
    else:
        directory_name = Path(base_mapper_path).name
        output_file = f"{directory_name}_{results['dbms_type']}_db_test_result.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_file}")
    
    # Query Error가 발생한 경우 실패 상태로 종료
    if error_count > 0:
        print(f"\n❌ Query Error 발생으로 인해 테스트 실패 (실패 개수: {error_count})")
        sys.exit(1)
    else:
        print(f"\n✅ 모든 테스트 성공")
        sys.exit(0)

if __name__ == "__main__":
    main() 
