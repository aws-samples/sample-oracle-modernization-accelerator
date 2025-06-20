#!/usr/bin/env python3
#############################################################################
# Script: DB03.XMLToSQL.py
# Description: This script extracts SQL statements from XML mapper files
#              and saves them as individual SQL files.
#
# Functionality:
# - Reads XML file lists from xmllist directory
# - Manages XML list files systematically
# - Extracts SQL statements from MyBatis XML mapper files
# - Handles various SQL statement types (select, insert, update, delete)
# - Saves extracted SQL statements as individual files
# - Provides comprehensive logging and error handling
#
# Usage:
#   python3 DB03.XMLToSQL.py [xml_list_file]
#
# Arguments:
#   xml_list_file   Optional. XML list file to process (orcl_xml.lst or pg_xml.lst)
#                   If not provided, processes both Oracle and PostgreSQL lists
#
# Output:
#   Individual SQL files in orcl_sql_extract/ and pg_sql_extract/ directories
#############################################################################

import os
import sys
import re
import shutil
import logging
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

def check_environment_variables():
    """
    환경 변수가 설정되어 있는지 확인합니다.
    """
    print("=" * 60)
    print("환경 변수 확인 중...")
    print("=" * 60)
    
    # 권장 환경 변수 목록
    recommended_env_vars = [
        'TEST_FOLDER',
        'TEST_LOGS_FOLDER',
        'APP_TRANSFORM_FOLDER'
    ]
    
    print("권장 환경 변수 확인 (설정되지 않으면 기본값 사용):")
    for var in recommended_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            if var == 'TEST_FOLDER':
                print(f"- {var}: 설정되지 않음 (기본값: 현재 작업 디렉토리)")
            elif var == 'TEST_LOGS_FOLDER':
                print(f"- {var}: 설정되지 않음 (기본값: TEST_FOLDER)")
            elif var == 'APP_TRANSFORM_FOLDER':
                print(f"- {var}: 설정되지 않음 (기본값: 현재 작업 디렉토리)")
    
    print("\n환경 변수 확인 완료.")
    print("=" * 60)

# 환경변수 기반 경로 설정
def get_paths():
    """환경변수를 기반으로 경로들을 반환합니다."""
    test_folder = os.environ.get('TEST_FOLDER', os.getcwd())
    test_logs_folder = os.environ.get('TEST_LOGS_FOLDER', test_folder)
    
    return {
        'xmllist_dir': os.path.join(test_folder, 'xmllist'),
        'orcl_sql_extract_dir': os.path.join(test_folder, 'orcl_sql_extract'),
        'pg_sql_extract_dir': os.path.join(test_folder, 'pg_sql_extract'),
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
    log_file = os.path.join(logs_dir, 'xml_to_sql.log')
    
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
    logger.info("XMLToSQL 실행 시작")
    logger.info("=" * 60)
    
    return logger

def setup_directories():
    """필요한 디렉토리들을 생성합니다."""
    paths = get_paths()
    
    directories = [
        paths['xmllist_dir'],
        paths['orcl_sql_extract_dir'],
        paths['pg_sql_extract_dir']
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"디렉토리 확인/생성: {directory}")
    
    logger.info("디렉토리 구조 설정 완료")

def manage_xml_list_files():
    """XML 리스트 파일들을 xmllist 디렉토리로 복사하고 관리합니다."""
    paths = get_paths()
    xmllist_dir = paths['xmllist_dir']
    
    logger.info("XML 리스트 파일 관리 시작")
    
    # APP_TRANSFORM_FOLDER 환경변수에서 XML 리스트 파일 찾기 (파라미터가 없는 경우)
    app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER', os.getcwd())
    source_files = ['orcl_xml.lst', 'pg_xml.lst']
    copied_files = {}
    
    logger.info(f"XML 리스트 파일 검색 위치: {app_transform_folder}")
    
    for source_name in source_files:
        # 먼저 현재 디렉토리에서 찾기 (기존 동작 유지)
        source_path = os.path.join(os.getcwd(), source_name)
        
        # 현재 디렉토리에 없으면 APP_TRANSFORM_FOLDER에서 찾기
        if not os.path.exists(source_path):
            source_path = os.path.join(app_transform_folder, source_name)
            logger.info(f"현재 디렉토리에서 찾을 수 없어 APP_TRANSFORM_FOLDER에서 검색: {source_path}")
        
        target_path = os.path.join(xmllist_dir, source_name)
        
        if os.path.exists(source_path):
            try:
                # 파일 복사 (메타데이터 포함)
                shutil.copy2(source_path, target_path)
                copied_files[source_name] = target_path
                logger.info(f"XML 리스트 파일 복사: {source_name} -> {target_path}")
                
                # 파일 크기 및 수정 시간 로그
                file_size = os.path.getsize(target_path)
                mod_time = datetime.fromtimestamp(os.path.getmtime(target_path))
                logger.debug(f"  파일 크기: {file_size} bytes, 수정 시간: {mod_time}")
                
            except Exception as e:
                logger.error(f"XML 리스트 파일 복사 실패: {source_name} - {e}")
        else:
            logger.warning(f"XML 리스트 파일을 찾을 수 없습니다: {source_path}")
            logger.info(f"  다음 위치들을 확인했습니다:")
            logger.info(f"    - 현재 디렉토리: {os.path.join(os.getcwd(), source_name)}")
            logger.info(f"    - APP_TRANSFORM_FOLDER: {os.path.join(app_transform_folder, source_name)}")
            logger.info(f"  먼저 FindXMLFiles.py를 실행하여 {source_name}을 생성하세요.")
    
    if not copied_files:
        logger.error("처리할 XML 리스트 파일이 없습니다.")
        logger.info("다음 명령으로 XML 리스트 파일을 먼저 생성하세요:")
        logger.info("  python3 FindXMLFiles.py /path/to/xml/files --orcl")
        logger.info("  python3 FindXMLFiles.py /path/to/xml/files --pg")
        logger.info(f"생성된 파일을 다음 위치 중 하나에 배치하세요:")
        logger.info(f"  - 현재 디렉토리: {os.getcwd()}")
        logger.info(f"  - APP_TRANSFORM_FOLDER: {app_transform_folder}")
        return {}
    
    logger.info(f"XML 리스트 파일 관리 완료: {len(copied_files)}개 파일 처리")
    return copied_files

def backup_xml_list_files():
    """XML 리스트 파일들을 백업합니다."""
    paths = get_paths()
    xmllist_dir = paths['xmllist_dir']
    backup_dir = os.path.join(xmllist_dir, 'backup')
    
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_count = 0
    
    for filename in ['orcl_xml.lst', 'pg_xml.lst']:
        source_path = os.path.join(xmllist_dir, filename)
        if os.path.exists(source_path):
            backup_filename = f"{filename}.{timestamp}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            try:
                shutil.copy2(source_path, backup_path)
                backup_count += 1
                logger.info(f"XML 리스트 백업: {backup_filename}")
            except Exception as e:
                logger.error(f"백업 실패: {filename} - {e}")
    
    if backup_count > 0:
        logger.info(f"XML 리스트 백업 완료: {backup_count}개 파일")
    
    return backup_count

def read_xml_list_file(list_type='orcl'):
    """xmllist 디렉토리에서 XML 리스트 파일을 읽습니다."""
    paths = get_paths()
    xmllist_dir = paths['xmllist_dir']
    
    filename = f"{list_type}_xml.lst"
    filepath = os.path.join(xmllist_dir, filename)
    
    if not os.path.exists(filepath):
        logger.error(f"XML 리스트 파일을 찾을 수 없습니다: {filepath}")
        logger.info("먼저 manage_xml_list_files()를 실행하여 XML 리스트를 복사하세요.")
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            xml_files = [line.strip() for line in f if line.strip()]
        
        logger.info(f"{filename}에서 {len(xml_files)}개 XML 파일 경로 로드")
        return xml_files
    except Exception as e:
        logger.error(f"XML 리스트 파일 읽기 오류: {e}")
        return []

def validate_xml_list_files():
    """XML 리스트 파일의 유효성을 검증합니다."""
    paths = get_paths()
    xmllist_dir = paths['xmllist_dir']
    
    validation_results = {}
    
    logger.info("XML 리스트 파일 유효성 검증 시작")
    
    for list_type in ['orcl', 'pg']:
        filename = f"{list_type}_xml.lst"
        filepath = os.path.join(xmllist_dir, filename)
        
        if os.path.exists(filepath):
            xml_files = read_xml_list_file(list_type)
            valid_files = []
            invalid_files = []
            
            for xml_file in xml_files:
                if os.path.exists(xml_file):
                    valid_files.append(xml_file)
                else:
                    invalid_files.append(xml_file)
            
            validation_results[list_type] = {
                'total': len(xml_files),
                'valid': len(valid_files),
                'invalid': len(invalid_files),
                'invalid_files': invalid_files
            }
            
            logger.info(f"{filename}: {len(valid_files)}/{len(xml_files)} 파일 유효")
            
            if invalid_files:
                logger.warning(f"{filename}에 존재하지 않는 파일들:")
                for invalid_file in invalid_files[:5]:  # 처음 5개만 표시
                    logger.warning(f"  - {invalid_file}")
                if len(invalid_files) > 5:
                    logger.warning(f"  ... 외 {len(invalid_files) - 5}개 파일")
        else:
            validation_results[list_type] = {'error': 'File not found'}
            logger.error(f"{filename} 파일을 찾을 수 없습니다.")
    
    logger.info("XML 리스트 파일 유효성 검증 완료")
    return validation_results
def clean_sql_content(sql_content):
    """SQL 내용을 정리합니다."""
    if not sql_content:
        return ""
    
    # XML 엔티티 디코딩
    sql_content = sql_content.replace('&lt;', '<')
    sql_content = sql_content.replace('&gt;', '>')
    sql_content = sql_content.replace('&amp;', '&')
    sql_content = sql_content.replace('&quot;', '"')
    sql_content = sql_content.replace('&apos;', "'")
    
    # 불필요한 공백 제거
    lines = sql_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('<!--') and not line.endswith('-->'):
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def extract_sql_from_element(element, namespace=''):
    """XML 엘리먼트에서 SQL을 추출합니다."""
    sql_statements = []
    
    # SQL 태그들 정의
    sql_tags = ['select', 'insert', 'update', 'delete', 'sql']
    
    # 네임스페이스 처리
    if namespace:
        sql_tags = [f"{{{namespace}}}{tag}" for tag in sql_tags] + sql_tags
    
    for tag in sql_tags:
        elements = element.findall(f".//{tag}")
        
        for elem in elements:
            sql_id = elem.get('id', '')
            if not sql_id:
                continue
            
            # SQL 내용 추출
            sql_content = elem.text or ''
            
            # 하위 엘리먼트들의 텍스트도 포함
            for child in elem:
                if child.text:
                    sql_content += ' ' + child.text
                if child.tail:
                    sql_content += ' ' + child.tail
            
            # SQL 내용 정리
            cleaned_sql = clean_sql_content(sql_content)
            
            if cleaned_sql:
                sql_statements.append({
                    'id': sql_id,
                    'type': tag.split('}')[-1] if '}' in tag else tag,  # 네임스페이스 제거
                    'content': cleaned_sql
                })
                logger.debug(f"SQL 추출: {sql_id} ({tag})")
    
    return sql_statements

def parse_xml_file(xml_file_path):
    """XML 파일을 파싱하여 SQL 문들을 추출합니다."""
    logger.debug(f"XML 파일 파싱 시작: {xml_file_path}")
    
    if not os.path.exists(xml_file_path):
        logger.error(f"XML 파일이 존재하지 않습니다: {xml_file_path}")
        return []
    
    try:
        # XML 파일 파싱
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # 네임스페이스 확인
        namespace = ''
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0][1:]
        
        # SQL 문 추출
        sql_statements = extract_sql_from_element(root, namespace)
        
        if sql_statements:
            logger.info(f"XML 파싱 완료: {xml_file_path} ({len(sql_statements)}개 SQL 추출)")
        else:
            logger.warning(f"SQL을 찾을 수 없습니다: {xml_file_path}")
        
        return sql_statements
        
    except ExpatError as e:
        logger.error(f"XML 파싱 오류: {xml_file_path} - {e}")
        
        # 인코딩 문제 해결 시도
        try:
            logger.info("인코딩 변환 시도 중...")
            with open(xml_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 임시 파일로 저장 후 재시도
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                tree = ET.parse(temp_path)
                root = tree.getroot()
                sql_statements = extract_sql_from_element(root)
                logger.info(f"인코딩 변환 후 파싱 성공: {xml_file_path}")
                return sql_statements
            finally:
                os.unlink(temp_path)
                
        except Exception as e2:
            logger.error(f"인코딩 변환 후에도 파싱 실패: {xml_file_path} - {e2}")
            return []
    
    except Exception as e:
        logger.error(f"XML 파일 처리 중 예외 발생: {xml_file_path} - {e}")
        return []

def generate_sql_filename(xml_file_path, sql_id, sql_type):
    """SQL 파일명을 생성합니다."""
    # XML 파일명에서 확장자 제거
    xml_basename = os.path.basename(xml_file_path)
    xml_name = os.path.splitext(xml_basename)[0]
    
    # 파일명 정리 (특수문자 제거)
    xml_name = re.sub(r'[^\w\-_.]', '_', xml_name)
    sql_id = re.sub(r'[^\w\-_.]', '_', sql_id)
    
    # SQL 파일명 생성: {xml_name}.{sql_id}.sql
    sql_filename = f"{xml_name}.{sql_id}.sql"
    
    return sql_filename

def save_sql_file(sql_content, output_path):
    """SQL 내용을 파일로 저장합니다."""
    try:
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        logger.debug(f"SQL 파일 저장: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"SQL 파일 저장 실패: {output_path} - {e}")
        return False

def process_xml_files(xml_files, output_dir, db_type):
    """XML 파일들을 처리하여 SQL 파일들을 생성합니다."""
    logger.info(f"{db_type} XML 파일 처리 시작: {len(xml_files)}개 파일")
    
    total_sql_count = 0
    processed_files = 0
    error_files = 0
    
    for i, xml_file in enumerate(xml_files, 1):
        logger.info(f"[{i}/{len(xml_files)}] 처리 중: {os.path.basename(xml_file)}")
        
        try:
            # XML 파일에서 SQL 추출
            sql_statements = parse_xml_file(xml_file)
            
            if not sql_statements:
                logger.warning(f"SQL을 찾을 수 없습니다: {xml_file}")
                continue
            
            # 각 SQL 문을 개별 파일로 저장
            file_sql_count = 0
            for sql_stmt in sql_statements:
                sql_filename = generate_sql_filename(xml_file, sql_stmt['id'], sql_stmt['type'])
                sql_output_path = os.path.join(output_dir, sql_filename)
                
                # SQL 내용에 주석 추가
                sql_content = f"""-- Source XML: {xml_file}
-- SQL ID: {sql_stmt['id']}
-- SQL Type: {sql_stmt['type']}
-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{sql_stmt['content']}
"""
                
                if save_sql_file(sql_content, sql_output_path):
                    file_sql_count += 1
                    total_sql_count += 1
            
            if file_sql_count > 0:
                processed_files += 1
                logger.info(f"  완료: {file_sql_count}개 SQL 추출")
            else:
                logger.warning(f"  SQL 저장 실패: {xml_file}")
                error_files += 1
                
        except Exception as e:
            logger.error(f"XML 파일 처리 중 오류: {xml_file} - {e}")
            error_files += 1
    
    logger.info(f"{db_type} 처리 완료:")
    logger.info(f"  처리된 XML 파일: {processed_files}/{len(xml_files)}")
    logger.info(f"  추출된 SQL 파일: {total_sql_count}개")
    logger.info(f"  오류 파일: {error_files}개")
    
    return {
        'total_xml_files': len(xml_files),
        'processed_files': processed_files,
        'error_files': error_files,
        'total_sql_files': total_sql_count
    }

def generate_processing_summary(results):
    """처리 결과 요약을 생성합니다."""
    paths = get_paths()
    xmllist_dir = paths['xmllist_dir']
    
    summary_file = os.path.join(xmllist_dir, f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("XML to SQL 변환 처리 요약\n")
            f.write("=" * 60 + "\n")
            f.write(f"처리 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            total_xml = 0
            total_processed = 0
            total_errors = 0
            total_sql = 0
            
            for db_type, result in results.items():
                f.write(f"{db_type.upper()} 처리 결과:\n")
                f.write(f"  총 XML 파일: {result['total_xml_files']}개\n")
                f.write(f"  처리 성공: {result['processed_files']}개\n")
                f.write(f"  처리 실패: {result['error_files']}개\n")
                f.write(f"  추출된 SQL: {result['total_sql_files']}개\n")
                f.write(f"  성공률: {result['processed_files']/result['total_xml_files']*100:.1f}%\n\n")
                
                total_xml += result['total_xml_files']
                total_processed += result['processed_files']
                total_errors += result['error_files']
                total_sql += result['total_sql_files']
            
            f.write("전체 요약:\n")
            f.write(f"  총 XML 파일: {total_xml}개\n")
            f.write(f"  처리 성공: {total_processed}개\n")
            f.write(f"  처리 실패: {total_errors}개\n")
            f.write(f"  추출된 SQL: {total_sql}개\n")
            f.write(f"  전체 성공률: {total_processed/total_xml*100:.1f}%\n")
        
        logger.info(f"처리 요약 저장: {summary_file}")
        return summary_file
        
    except Exception as e:
        logger.error(f"처리 요약 저장 실패: {e}")
        return None
def main():
    """메인 실행 함수"""
    # 명령줄 인수 확인
    target_list = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['orcl_xml.lst', 'orcl']:
            target_list = 'orcl'
        elif arg in ['pg_xml.lst', 'pg']:
            target_list = 'pg'
        else:
            logger.warning(f"알 수 없는 인수: {sys.argv[1]}")
            logger.info("사용법: python3 XMLToSQL.py [orcl|pg]")
    
    # 디렉토리 설정
    setup_directories()
    
    # 경로 정보 출력
    paths = get_paths()
    logger.info("경로 설정:")
    logger.info(f"  XML 리스트 디렉토리: {paths['xmllist_dir']}")
    logger.info(f"  Oracle SQL 출력: {paths['orcl_sql_extract_dir']}")
    logger.info(f"  PostgreSQL SQL 출력: {paths['pg_sql_extract_dir']}")
    logger.info(f"  로그 디렉토리: {paths['logs_dir']}")
    
    # XML 리스트 파일 관리
    logger.info("XML 리스트 파일 관리 시작")
    copied_files = manage_xml_list_files()
    
    if not copied_files:
        logger.error("처리할 XML 리스트 파일이 없습니다.")
        return
    
    # XML 리스트 파일 백업
    backup_xml_list_files()
    
    # XML 리스트 파일 유효성 검증
    validation_results = validate_xml_list_files()
    
    # 처리할 리스트 결정
    lists_to_process = []
    if target_list:
        if target_list in validation_results and 'error' not in validation_results[target_list]:
            lists_to_process.append(target_list)
            logger.info(f"지정된 리스트만 처리: {target_list}")
        else:
            logger.error(f"지정된 리스트를 처리할 수 없습니다: {target_list}")
            return
    else:
        # 모든 유효한 리스트 처리
        for list_type in ['orcl', 'pg']:
            if list_type in validation_results and 'error' not in validation_results[list_type]:
                if validation_results[list_type]['valid'] > 0:
                    lists_to_process.append(list_type)
                else:
                    logger.warning(f"{list_type} 리스트에 유효한 파일이 없습니다.")
    
    if not lists_to_process:
        logger.error("처리할 유효한 XML 리스트가 없습니다.")
        return
    
    # XML 파일 처리
    processing_results = {}
    
    for list_type in lists_to_process:
        logger.info(f"{list_type.upper()} XML 파일 처리 시작")
        
        # XML 파일 목록 로드
        xml_files = read_xml_list_file(list_type)
        
        if not xml_files:
            logger.warning(f"{list_type} XML 파일 목록이 비어있습니다.")
            continue
        
        # 출력 디렉토리 결정
        if list_type == 'orcl':
            output_dir = paths['orcl_sql_extract_dir']
        else:
            output_dir = paths['pg_sql_extract_dir']
        
        # XML 파일들 처리
        result = process_xml_files(xml_files, output_dir, list_type.upper())
        processing_results[list_type] = result
    
    # 처리 결과 요약
    if processing_results:
        logger.info("=" * 60)
        logger.info("XML to SQL 변환 완료")
        logger.info("=" * 60)
        
        total_xml = 0
        total_processed = 0
        total_sql = 0
        
        for list_type, result in processing_results.items():
            logger.info(f"{list_type.upper()} 결과:")
            logger.info(f"  XML 파일: {result['processed_files']}/{result['total_xml_files']} 처리")
            logger.info(f"  SQL 파일: {result['total_sql_files']}개 생성")
            logger.info(f"  성공률: {result['processed_files']/result['total_xml_files']*100:.1f}%")
            
            total_xml += result['total_xml_files']
            total_processed += result['processed_files']
            total_sql += result['total_sql_files']
        
        logger.info("=" * 60)
        logger.info("전체 요약:")
        logger.info(f"  처리된 XML 파일: {total_processed}/{total_xml}")
        logger.info(f"  생성된 SQL 파일: {total_sql}개")
        logger.info(f"  전체 성공률: {total_processed/total_xml*100:.1f}%")
        logger.info("=" * 60)
        
        # 처리 요약 파일 생성
        summary_file = generate_processing_summary(processing_results)
        if summary_file:
            logger.info(f"상세 요약 보고서: {summary_file}")
        
        # 다음 단계 안내
        logger.info("다음 단계:")
        if 'orcl' in processing_results:
            logger.info(f"  Oracle SQL 파일들: {paths['orcl_sql_extract_dir']}")
        if 'pg' in processing_results:
            logger.info(f"  PostgreSQL SQL 파일들: {paths['pg_sql_extract_dir']}")
        logger.info("  다음 실행: python3 GetDictionary.py (데이터베이스 딕셔너리 생성)")
        
    else:
        logger.error("처리된 결과가 없습니다.")

if __name__ == "__main__":
    # 환경 변수 확인
    check_environment_variables()
    
    # 로깅 설정
    logger = setup_logging()
    
    try:
        # 메인 실행
        main()
        logger.info("XMLToSQL 실행 완료")
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {str(e)}")
        raise
