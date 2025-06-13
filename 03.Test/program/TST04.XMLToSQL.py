#!/usr/bin/env python3
#############################################################################
# Script: DB03.XMLToSQL.py
# Description: This script extracts SQL statements from XML files (typically
#              MyBatis/iBatis mapper files) and saves them as individual SQL files.
#              It combines functionality for batch processing and filename analysis.
#
# Functionality:
# - Processes XML files from a list file or a single XML file
# - Extracts SQL statements from various XML tags (select, insert, update, delete, sql)
# - Handles CDATA sections and include references
# - Cleans and formats SQL statements
# - Saves each SQL statement as a separate file
# - Supports parallel processing for faster execution
# - Processes XML files in batches for better memory management
# - Analyzes and cleans up SQL file names
#
# Usage:
#   python3 DB03.XMLToSQL.py [XML file or list file] [--batch-size N] [--rename] [--analyze-only]
#
# Example:
#   python3 DB03.XMLToSQL.py orcl_xml.lst --batch-size 100
#   python3 DB03.XMLToSQL.py /path/to/mapper.xml
#   python3 DB03.XMLToSQL.py --analyze-only --rename
#############################################################################

"""
XML 파일에서 SQL 구문을 추출하고 파일명을 정리하는 통합 프로그램

사용법:
    python3 DB03.XMLToSQL.py [XML 파일 또는 목록 파일] [--batch-size N] [--rename] [--analyze-only]

예시:
    python3 DB03.XMLToSQL.py orcl_xml.lst --batch-size 100
    python3 DB03.XMLToSQL.py /path/to/mapper.xml
    python3 DB03.XMLToSQL.py --analyze-only --rename
"""

import os
import sys
import re
import time
import xml.etree.ElementTree as ET
import glob
import shutil
import filecmp
import difflib
import argparse
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

#############################################################################
# Part 1: SQL Extraction from XML (from DB03.ExtractSQLFromXMLs.py)
#############################################################################

def is_valid_sql(sql_text, sql_type):
    """
    SQL 구문이 유효한지 확인합니다.
    """
    if not sql_text or len(sql_text.strip()) < 5:
        return False
    
    # SQL 타입에 따라 검증
    if sql_type == 'select':
        return bool(re.search(r'SELECT|select', sql_text))
    elif sql_type == 'insert':
        return bool(re.search(r'INSERT|insert', sql_text))
    elif sql_type == 'update':
        return bool(re.search(r'UPDATE|update', sql_text))
    elif sql_type == 'delete':
        return bool(re.search(r'DELETE|delete', sql_text))
    elif sql_type == 'sql':
        return bool(re.search(r'SELECT|select|INSERT|insert|UPDATE|update|DELETE|delete|DECLARE|declare', sql_text))
    
    return True

def is_valid_sql_content(sql_content):
    """
    SQL 내용이 유효한지 확인합니다.
    """
    if not sql_content or len(sql_content.strip()) < 5:
        return False
    
    # 주석만 있는 경우 제외
    non_comment_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
    non_comment_content = re.sub(r'--.*?$', '', non_comment_content, flags=re.MULTILINE)
    
    if not non_comment_content.strip():
        return False
    
    return True

def process_sql_content(sql_content):
    """
    SQL 내용을 처리하여 CDATA 섹션과 if 구문을 처리합니다.
    """
    # CDATA 섹션 처리
    sql_content = re.sub(r'<!\[CDATA\[([\s\S]*?)\]\]>', r'\1', sql_content)
    
    # if 태그 내용 처리 (if 태그 내의 SQL 부분만 유지)
    if_pattern = r'<if test=[\'"][^\'"]+[\'"]>([\s\S]*?)<\/if>'
    while re.search(if_pattern, sql_content):
        sql_content = re.sub(if_pattern, r'\1', sql_content)

    # 불필요한 공백 정리
    lines = sql_content.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)
    
    # <include> 태그만 있는 경우 주석 추가
    if re.search(r'^\s*<include\s+refid=', result) and not re.search(r'[^\s<>](?!<include|refid=|\/include>)', result):
        result += "\n/* SQL 구문이 직접 포함되어 있지 않고 include 참조만 있습니다. */"
    
    return result

def clean_filename(filename):
    """
    파일 이름에서 _orcl, _pg, _sql 등의 접미사를 제거합니다.
    """
    # _orcl 또는 _pg 제거
    filename = re.sub(r'_(orcl|pg)', '', filename)
    # _sql 접미사 제거 (파일명 끝에 있는 경우)
    filename = re.sub(r'_sql$', '', filename)
    # 중간에 있는 _sql도 제거
    filename = re.sub(r'_sql_', '_', filename)
    # 연속된 언더스코어 제거
    filename = re.sub(r'__+', '_', filename)
    # 끝에 있는 언더스코어 제거
    filename = re.sub(r'_$', '', filename)
    return filename

def remove_xml_comments(xml_content):
    """
    XML 내용에서 <!-- 로 시작하는 XML 주석을 모두 제거합니다.
    """
    # XML 주석 패턴: <!-- 로 시작하고 --> 로 끝나는 모든 내용 제거
    return re.sub(r'<!--[\s\S]*?-->', '', xml_content)

def get_app_name_from_path(xml_file):
    """
    XML 파일 경로에서 어플리케이션 이름을 추출합니다.
    $OMA_TRANSFORM 디렉토리 아래의 디렉토리 이름을 어플리케이션 이름으로 사용합니다.
    """
    try:
        # 환경 변수에서 OMA_TRANSFORM 경로 가져오기
        oma_transform = os.environ.get('OMA_TRANSFORM', '')
        
        if not oma_transform:
            print(f"경고: OMA_TRANSFORM 환경 변수가 설정되지 않았습니다.")
            return None
            
        # 절대 경로로 변환
        xml_abs_path = os.path.abspath(xml_file)
        
        # OMA_TRANSFORM 디렉토리 아래의 경로인지 확인
        if oma_transform in xml_abs_path:
            # OMA_TRANSFORM 이후의 첫 번째 디렉토리가 어플리케이션 이름
            rel_path = os.path.relpath(xml_abs_path, oma_transform)
            app_name = rel_path.split(os.sep)[0]
            
            # 유효한 어플리케이션 이름인지 확인 (디렉토리인지)
            app_dir = os.path.join(oma_transform, app_name)
            if os.path.isdir(app_dir):
                return app_name
        
        return None
    except Exception as e:
        print(f"어플리케이션 이름 추출 중 오류 발생: {e}")
        return None

def determine_output_dir(xml_file_or_list):
    """
    XML 파일 또는 목록 파일 이름에 따라 출력 디렉토리를 결정합니다.
    orcl이 포함된 경우 orcl_sql_extract, pg가 포함된 경우 pg_sql_extract를 사용합니다.
    """
    if 'orcl' in xml_file_or_list.lower():
        return "orcl_sql_extract"
    elif 'pg' in xml_file_or_list.lower():
        return "pg_sql_extract"
    else:
        return "sql_extract"  # 기본값

def extract_sql_with_cdata(xml_file, xml_content):
    """
    CDATA 섹션을 포함한 SQL 구문을 추출합니다.
    """
    result = []
    
    # CDATA 섹션 패턴
    cdata_pattern = r'<\s*(select|update|delete|insert|sql)\s+id\s*=\s*"([^"]+)"[^>]*>.*?<!\[CDATA\[([\s\S]*?)\]\]>.*?<\/\s*\1\s*>'
    cdata_matches = re.findall(cdata_pattern, xml_content, re.IGNORECASE)
    
    for sql_type, sql_id, sql_content in cdata_matches:
        sql_text = process_sql_content(sql_content)
        
        if is_valid_sql(sql_text, sql_type):
            sql_type_display = 'plsql' if sql_text.strip().lower().startswith('declare') else sql_type.lower()
            file_name = os.path.basename(xml_file)
            result.append((sql_type_display, sql_id, sql_text, file_name))
    
    return result

def process_sql_includes(xml_file, xml_content, current_results):
    """
    SQL 태그 내부의 include 태그를 처리합니다.
    """
    # 이미 처리된 SQL ID 목록
    processed_ids = set(item[1] for item in current_results)
    
    # XML 파싱
    try:
        root = ET.fromstring(xml_content)
        
        # 네임스페이스 처리
        ns = {'ns': root.tag.split('}')[0].strip('{') if '}' in root.tag else ''}
        
        # SQL 태그 내부의 include 태그 찾기
        for sql_type in ['select', 'update', 'delete', 'insert', 'sql']:
            for sql_elem in root.findall(f".//{sql_type}", ns):
                sql_id = sql_elem.get('id', '')
                
                # 이미 처리된 SQL ID는 건너뛰기
                if not sql_id or sql_id in processed_ids:
                    continue
                
                # include 태그 찾기
                include_refs = []
                for include_elem in sql_elem.findall(".//include", ns):
                    ref_id = include_elem.get('refid', '')
                    if ref_id:
                        include_refs.append(ref_id)
                
                # include 태그가 있는 경우
                if include_refs:
                    # SQL 태그 내용 가져오기
                    sql_content = ET.tostring(sql_elem, encoding='unicode')
                    
                    # include 태그 참조 ID 추출
                    for ref_id in include_refs:
                        # 참조된 SQL 태그 찾기
                        for ref_type in ['sql']:
                            for ref_elem in root.findall(f".//{ref_type}[@id='{ref_id}']", ns):
                                # 참조된 SQL 내용 가져오기
                                ref_content = ''.join(ref_elem.itertext())
                                ref_content = process_sql_content(ref_content)
                                
                                # 원본 SQL에 참조된 SQL 내용 추가
                                file_name = os.path.basename(xml_file)
                                current_results.append((sql_type.lower(), sql_id, ref_content, file_name))
                                processed_ids.add(sql_id)
    except Exception as e:
        print(f"SQL include 처리 중 오류 발생: {e}")
    
    return current_results

def extract_sql_using_xml_parser(xml_file, xml_content):
    """
    XML 파서를 사용하여 SQL 구문을 추출합니다.
    """
    # XML 파싱
    root = ET.fromstring(xml_content)
    
    # 네임스페이스 처리
    ns = {'ns': root.tag.split('}')[0].strip('{') if '}' in root.tag else ''}
    
    result = []
    
    # SQL 태그 찾기 (select, update, delete, insert, sql)
    for sql_type in ['select', 'update', 'delete', 'insert', 'sql']:
        # 해당 타입의 모든 태그 찾기
        for sql_elem in root.findall(f".//{sql_type}", ns):
            sql_id = sql_elem.get('id', '')
            if not sql_id:
                continue
            
            # 태그 내용 가져오기
            sql_content = ''.join(sql_elem.itertext())
            
            # SQL 내용 정리
            sql_text = process_sql_content(sql_content)
            
            # SQL 구문이 유효한지 확인
            if not is_valid_sql(sql_text, sql_type):
                continue
            
            # PL/SQL 블록 확인
            if sql_text.strip().lower().startswith('declare'):
                sql_type_display = 'plsql'
            else:
                sql_type_display = sql_type.lower()
            
            # 파일 이름 추출
            file_name = os.path.basename(xml_file)
            
            result.append((sql_type_display, sql_id, sql_text, file_name))
    
    # SQL 태그 찾기 (sql 태그)
    for sql_elem in root.findall(".//sql", ns):
        sql_id = sql_elem.get('id', '')
        if not sql_id:
            continue
        
        # 태그 내용 가져오기
        sql_content = ''.join(sql_elem.itertext())
        
        # SQL 내용 정리
        sql_text = process_sql_content(sql_content)
        
        # SQL 구문이 유효한지 확인
        if not is_valid_sql(sql_text, 'sql'):
            continue
        
        # 파일 이름 추출
        file_name = os.path.basename(xml_file)
        
        result.append(('sql', sql_id, sql_text, file_name))
    
    return result

def extract_sql_from_xml(xml_file):
    """
    XML 파일에서 SQL 구문을 추출합니다.
    여러 방법을 시도하여 최대한 많은 SQL을 추출합니다.
    """
    try:
        # XML 파일을 문자열로 읽기
        with open(xml_file, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # PostgreSQL XML 파일인 경우 주석 제거 사전 처리
        if xml_file.endswith('_pg.xml'):
            xml_content = remove_xml_comments(xml_content)
        
        # 결과를 저장할 리스트
        result = []
        
        # 방법 1: XML 파서를 사용한 추출
        try:
            result = extract_sql_using_xml_parser(xml_file, xml_content)
            if result:
                return result
        except Exception as e:
            print(f"XML 파서 방식 실패 ({xml_file}): {e}")
        
        # 방법 2: 정규식을 사용한 기본 추출
        sql_pattern = r'<\s*(select|update|delete|insert|sql)\s+id\s*=\s*"([^"]+)"[^>]*>([\s\S]*?)<\/\s*\1\s*>'
        sql_matches = re.findall(sql_pattern, xml_content, re.IGNORECASE)
        
        for sql_type, sql_id, sql_content in sql_matches:
            sql_text = process_sql_content(sql_content)
            
            if is_valid_sql(sql_text, sql_type):
                sql_type_display = 'plsql' if sql_text.strip().lower().startswith('declare') else sql_type.lower()
                file_name = os.path.basename(xml_file)
                result.append((sql_type_display, sql_id, sql_text, file_name))
        
        # 방법 3: CDATA 섹션을 포함한 추출
        if not result:
            result = extract_sql_with_cdata(xml_file, xml_content)
            
        # 방법 4: SQL 태그 내부의 include 태그 처리
        result = process_sql_includes(xml_file, xml_content, result)
        
        return result
        
    except FileNotFoundError:
        print(f"오류: '{xml_file}' 파일을 찾을 수 없습니다.")
        file_name = os.path.basename(xml_file)
        return [('error', 'file_not_found', f"/* 오류: '{xml_file}' 파일을 찾을 수 없습니다. */", file_name)]
    except Exception as e:
        print(f"오류 발생: {xml_file} - {e}")
        file_name = os.path.basename(xml_file)
        return [('error', 'unknown_error', f"/* 오류 발생: {e} */", file_name)]

def format_sql_output(sql_data):
    """
    SQL 데이터를 포맷팅하여 출력합니다.
    """
    output = []
    
    for sql_type, sql_id, sql_content, file_name in sql_data:
        # 헤더 추가
        output.append(f"/* 파일: {file_name}, 타입: {sql_type}, ID: {sql_id} */")
        
        # SQL 내용이 주석으로 시작하는지 확인
        if sql_content.strip().startswith('/*') or sql_content.strip().startswith('--'):
            output.append(sql_content)
        else:
            # SQL 내용 추가
            output.append(sql_content)
        
        # 구분선 추가
        output.append("\n" + "-" * 80 + "\n")
    
    return "\n".join(output)

def add_slash_to_sql(sql_content):
    """
    SQL 구문 끝에 / 문자를 추가합니다.
    """
    sql_content = sql_content.rstrip()
    
    # PL/SQL 블록이나 일반 SQL 구문에 / 추가
    if sql_content:
        return sql_content + "\n/"
    
    return sql_content

def process_xml_file(xml_file, output_dir):
    """
    XML 파일을 처리하여 SQL을 추출하고 개별 SQL 파일로 저장합니다.
    """
    try:
        start_time = time.time()
        
        # SQL 추출
        sql_data = extract_sql_from_xml(xml_file)
        
        if not sql_data:
            print(f"경고: '{xml_file}'에서 SQL 구문을 찾을 수 없습니다.")
            return False, xml_file, 0
        
        # 중간 파일 경로 설정 (디버깅 목적이지만 생성하지 않음)
        base_name = os.path.basename(xml_file)
        # intermediate_file = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}_sql.sql")
        
        # SQL 출력 포맷팅 (중간 파일은 저장하지 않음)
        formatted_sql = format_sql_output(sql_data)
        # with open(intermediate_file, 'w', encoding='utf-8') as f:
        #     f.write(formatted_sql)
        
        # 개별 SQL 파일로 분리하여 저장
        success_count = 0
        skipped_count = 0
        base_filename = os.path.splitext(base_name)[0]  # 확장자 제거
        
        # 파일명 정리 전 원본 저장
        original_base_filename = base_filename
        
        # 파일명 정리
        base_filename = clean_filename(base_filename)  # _orcl, _pg, _sql 등 제거
        
        # 디버깅 정보 출력
        if original_base_filename != base_filename:
            print(f"파일명 정리: '{original_base_filename}' -> '{base_filename}'")
        
        # 어플리케이션 이름 추출
        app_name = get_app_name_from_path(xml_file)
        
        for sql_type, sql_id, sql_content, _ in sql_data:
            # SQL 내용이 유효한지 확인
            if not is_valid_sql_content(sql_content):
                print(f"경고: '{base_filename}.{sql_id}.sql' - 유효하지 않은 SQL 구문, 건너뜁니다.")
                skipped_count += 1
                continue
                
            # SQL 구문 끝에 / 추가
            sql_content_with_slash = add_slash_to_sql(sql_content)
            
            # 파일 이름 생성: file_name.sql_id.sql
            # SQL ID에서 특수문자 제거 (파일명으로 사용할 수 없는 문자 제거)
            clean_sql_id = re.sub(r'[^\w\d]', '_', sql_id)
            # 연속된 언더스코어 제거
            clean_sql_id = re.sub(r'__+', '_', clean_sql_id)
            # 끝에 있는 언더스코어 제거
            clean_sql_id = re.sub(r'_$', '', clean_sql_id)
            
            # 어플리케이션 이름이 있으면 파일명에 추가: app_name.file_name.sql_id.sql
            if app_name:
                output_filename = f"{app_name}.{base_filename}.{clean_sql_id}.sql"
            else:
                output_filename = f"{base_filename}.{clean_sql_id}.sql"
                
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(sql_content_with_slash)
                success_count += 1
            except Exception as e:
                print(f"오류: {output_path} 저장 중 예외 발생: {e}")
        
        elapsed_time = time.time() - start_time
        if skipped_count > 0:
            print(f"완료: {xml_file} -> {success_count}개 SQL 파일 생성, {skipped_count}개 건너뜀 (소요 시간: {elapsed_time:.2f}초)")
        else:
            print(f"완료: {xml_file} -> {success_count}개 SQL 파일 생성 (소요 시간: {elapsed_time:.2f}초)")
        
        return True, xml_file, success_count
    except Exception as e:
        print(f"오류: {xml_file} 처리 중 예외 발생: {e}")
        return False, xml_file, 0
#############################################################################
# Part 2: Batch Processing (from DB04.XMLToSQL.py)
#############################################################################

def read_xml_list(list_file):
    """
    XML 목록 파일을 읽어서 XML 파일 경로 리스트를 반환합니다.
    """
    try:
        with open(list_file, 'r', encoding='utf-8') as f:
            xml_files = [line.strip() for line in f if line.strip()]
        return xml_files
    except FileNotFoundError:
        print(f"오류: '{list_file}' 파일을 찾을 수 없습니다.")
        print("먼저 DB02.FindXMLFiles.py를 실행하여 XML 목록 파일을 생성하세요.")
        print("예시: python3 DB02.FindXMLFiles.py /경로 --orcl")
        sys.exit(1)
    except Exception as e:
        print(f"XML 목록 파일을 읽는 중 오류가 발생했습니다: {e}")
        sys.exit(1)

def process_xml_batch(xml_files, output_dir):
    """
    XML 파일 배치를 처리합니다.
    """
    success_count = 0
    failed_files = []
    
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # 작업 제출
        future_to_xml = {executor.submit(process_xml_file, xml_file, output_dir): xml_file for xml_file in xml_files}
        
        # 결과 처리
        for future in as_completed(future_to_xml):
            xml_file = future_to_xml[future]
            try:
                success, file_path, count = future.result()
                if success:
                    success_count += count
                else:
                    failed_files.append(file_path)
            except Exception as e:
                print(f"오류: {xml_file} 처리 중 예외 발생: {e}")
                failed_files.append(xml_file)
    
    return success_count, failed_files

def process_in_batches(xml_files, output_dir, batch_size=50):
    """
    XML 파일 목록을 배치로 나누어 처리합니다.
    """
    total_files = len(xml_files)
    total_batches = (total_files + batch_size - 1) // batch_size  # 올림 나눗셈
    
    print(f"총 {total_files}개의 XML 파일을 {total_batches}개의 배치로 처리합니다.")
    
    total_success = 0
    total_failed = []
    start_time = time.time()
    
    for i in range(0, total_files, batch_size):
        batch = xml_files[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\n배치 {batch_num}/{total_batches} 처리 중 ({len(batch)}개 파일)...")
        
        batch_success, batch_failed = process_xml_batch(batch, output_dir)
        total_success += batch_success
        total_failed.extend(batch_failed)
        
        # 진행 상황 출력
        progress = min(100, (i + len(batch)) / total_files * 100)
        elapsed = time.time() - start_time
        est_total = elapsed / progress * 100 if progress > 0 else 0
        remaining = est_total - elapsed if est_total > 0 else 0
        
        print(f"진행 상황: {progress:.1f}% 완료, 예상 남은 시간: {remaining:.1f}초")
    
    elapsed_time = time.time() - start_time
    print(f"\n처리 완료: 총 {total_files}개 중 {total_success}개 SQL 파일 생성, {len(total_failed)}개 파일 처리 실패")
    print(f"총 소요 시간: {elapsed_time:.2f}초")
    
    if total_failed:
        print("\n실패한 파일 목록:")
        for file_path in total_failed[:10]:  # 처음 10개만 표시
            print(f"  - {file_path}")
        if len(total_failed) > 10:
            print(f"  ... 외 {len(total_failed) - 10}개 파일")
    
    return total_success, total_failed

#############################################################################
# Part 3: Filename Analysis (from DB05.AnalyzeXMLFilenames.py)
#############################################################################

def analyze_filenames(directory, rename=False):
    """
    지정된 디렉토리에서 _orcl_sql.sql 또는 _pg_sql.sql로 끝나는 파일을 찾아
    분석하고 필요한 경우 이름을 변경합니다.
    """
    # 디렉토리가 존재하는지 확인
    if not os.path.isdir(directory):
        print(f"오류: '{directory}'는 유효한 디렉토리가 아닙니다.")
        return 0, 0, 0
    
    # 백업 디렉토리 생성
    backup_dir = os.path.join(os.path.dirname(directory), "backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    # 패턴에 맞는 파일 찾기
    pattern = r'(.+)_(orcl|pg)_sql\.sql$'
    renamed_count = 0
    conflict_count = 0
    skipped_count = 0
    
    for file_path in glob.glob(os.path.join(directory, "*_*_sql.sql")):
        file_name = os.path.basename(file_path)
        match = re.match(pattern, file_name)
        
        if match:
            # 원래 파일 이름과 새 파일 이름 생성
            base_name = match.group(1)
            new_file_name = f"{base_name}.sql"
            new_file_path = os.path.join(directory, new_file_name)
            
            # 이미 정리된 이름의 파일이 있는지 확인
            if os.path.exists(new_file_path):
                # 파일 내용 비교
                if filecmp.cmp(file_path, new_file_path, shallow=False):
                    print(f"정보: '{file_name}'과 '{new_file_name}'의 내용이 동일합니다.")
                    
                    # 이름 변경 옵션이 활성화된 경우 중복 파일 백업 후 삭제
                    if rename:
                        backup_file_path = os.path.join(backup_dir, file_name)
                        shutil.copy2(file_path, backup_file_path)
                        os.remove(file_path)
                        print(f"  -> 중복 파일 '{file_name}'을 백업 후 삭제했습니다.")
                        renamed_count += 1
                    else:
                        skipped_count += 1
                else:
                    print(f"경고: '{file_name}'과 '{new_file_name}'의 내용이 다릅니다!")
                    
                    # 차이점 출력
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f1, \
                         open(new_file_path, 'r', encoding='utf-8', errors='ignore') as f2:
                        try:
                            diff = list(difflib.unified_diff(
                                f1.readlines(), 
                                f2.readlines(), 
                                fromfile=file_name, 
                                tofile=new_file_name,
                                n=1
                            ))
                            if diff:
                                print("  차이점 (최대 5줄):")
                                for i, line in enumerate(diff):
                                    if i < 5:  # 최대 5줄만 출력
                                        print(f"    {line.rstrip()}")
                                    else:
                                        print("    ...")
                                        break
                        except UnicodeDecodeError:
                            print("  -> 파일 인코딩 문제로 차이점을 표시할 수 없습니다.")
                    
                    conflict_count += 1
            else:
                # 백업 파일 경로
                backup_file_path = os.path.join(backup_dir, file_name)
                
                # 이름 변경 옵션이 활성화된 경우 파일 이름 변경
                if rename:
                    # 파일 이름 변경 전에 백업
                    shutil.copy2(file_path, backup_file_path)
                    
                    # 파일 이름 변경
                    os.rename(file_path, new_file_path)
                    print(f"'{file_name}' -> '{new_file_name}'으로 변경되었습니다.")
                    renamed_count += 1
                else:
                    print(f"정보: '{file_name}'은 '{new_file_name}'으로 안전하게 변경할 수 있습니다.")
                    skipped_count += 1
    
    return renamed_count, conflict_count, skipped_count

def analyze_all_filenames(rename=False):
    """
    orcl_sql_extract와 pg_sql_extract 디렉토리의 파일 이름을 분석합니다.
    """
    # orcl_sql_extract 디렉토리 처리
    print("\n=== orcl_sql_extract 디렉토리 분석 ===")
    orcl_dir = "orcl_sql_extract"
    orcl_renamed, orcl_conflict, orcl_skipped = analyze_filenames(orcl_dir, rename)
    
    # pg_sql_extract 디렉토리 처리
    print("\n=== pg_sql_extract 디렉토리 분석 ===")
    pg_dir = "pg_sql_extract"
    pg_renamed, pg_conflict, pg_skipped = analyze_filenames(pg_dir, rename)
    
    # 결과 요약
    print("\n=== 분석 결과 요약 ===")
    total_renamed = orcl_renamed + pg_renamed
    total_conflict = orcl_conflict + pg_conflict
    total_skipped = orcl_skipped + pg_skipped
    
    print(f"orcl_sql_extract: {orcl_renamed}개 이름 변경, {orcl_conflict}개 충돌, {orcl_skipped}개 건너뜀")
    print(f"pg_sql_extract: {pg_renamed}개 이름 변경, {pg_conflict}개 충돌, {pg_skipped}개 건너뜀")
    print(f"총계: {total_renamed}개 이름 변경, {total_conflict}개 충돌, {total_skipped}개 건너뜀")
    
    if rename:
        print("\n변경된 파일의 원본은 backup 디렉토리에 백업되었습니다.")
    else:
        print("\n이름을 변경하려면 --rename 옵션을 사용하세요.")
    
    return total_renamed, total_conflict, total_skipped
def main():
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='XML 파일에서 SQL 구문을 추출하고 파일명을 정리하는 통합 프로그램')
    parser.add_argument('xml_file_or_list', nargs='?', default=None, help='XML 파일 또는 목록 파일 (기본값: 자동 감지)')
    parser.add_argument('--batch-size', type=int, default=100, help='배치당 처리할 XML 파일 수 (기본값: 100)')
    parser.add_argument('--rename', action='store_true', help='파일명 분석 후 안전하게 이름을 변경할 수 있는 파일의 이름을 변경합니다.')
    parser.add_argument('--analyze-only', action='store_true', help='SQL 추출 없이 파일명 분석만 수행합니다.')
    parser.add_argument('--no-rename', action='store_true', help='파일명 분석만 수행하고 이름 변경은 하지 않습니다.')
    parser.add_argument('--no-analyze', action='store_true', help='파일명 분석을 수행하지 않습니다.')
    
    args = parser.parse_args()
    
    # 파일명 분석만 수행하는 경우
    if args.analyze_only:
        print("파일명 분석 모드로 실행합니다.")
        analyze_all_filenames(args.rename)
        return
    
    # 처리할 XML 파일 목록 또는 파일 결정
    xml_files_to_process = []
    
    # XML 파일 또는 목록 파일 자동 감지
    if args.xml_file_or_list is None:
        # orcl_xml.lst와 pg_xml.lst 모두 처리
        if os.path.exists("orcl_xml.lst"):
            xml_files_to_process.append("orcl_xml.lst")
        if os.path.exists("pg_xml.lst"):
            xml_files_to_process.append("pg_xml.lst")
        
        if not xml_files_to_process:
            print("오류: XML 파일 또는 목록 파일을 찾을 수 없습니다.")
            print("먼저 DB02.FindXMLFiles.py를 실행하여 XML 목록 파일을 생성하세요.")
            print("예시: python3 DB02.FindXMLFiles.py /경로 --orcl")
            sys.exit(1)
    else:
        # 명시적으로 지정된 파일만 처리
        xml_files_to_process.append(args.xml_file_or_list)
    
    # 각 XML 파일 또는 목록 파일 처리
    for xml_file_or_list in xml_files_to_process:
        # 출력 디렉토리 자동 결정
        output_dir = determine_output_dir(xml_file_or_list)
        print(f"\n=== {xml_file_or_list} 처리 시작 ===")
        print(f"출력 디렉토리: {output_dir}")
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # XML 파일 또는 목록 파일 처리
        start_time = time.time()
        
        if os.path.isfile(xml_file_or_list) and xml_file_or_list.endswith('.lst'):
            # XML 목록 파일 처리
            print(f"XML 목록 파일 '{xml_file_or_list}'을 처리합니다.")
            xml_files = read_xml_list(xml_file_or_list)
            
            if not xml_files:
                print(f"'{xml_file_or_list}'에 처리할 XML 파일이 없습니다.")
                continue
            
            print(f"총 {len(xml_files)}개의 XML 파일을 처리합니다.")
            
            # 배치 처리
            process_in_batches(xml_files, output_dir, args.batch_size)
        elif os.path.isfile(xml_file_or_list) and (xml_file_or_list.endswith('.xml')):
            # 단일 XML 파일 처리
            print(f"단일 XML 파일 '{xml_file_or_list}'을 처리합니다.")
            success, _, count = process_xml_file(xml_file_or_list, output_dir)
            
            if success:
                print(f"처리 완료: {count}개의 SQL 파일이 생성되었습니다.")
            else:
                print("처리 실패")
                continue
        else:
            print(f"오류: '{xml_file_or_list}'는 유효한 XML 파일 또는 목록 파일이 아닙니다.")
            continue
        
        # 처리 시간 출력
        elapsed_time = time.time() - start_time
        print(f"{xml_file_or_list} 처리 완료: 소요 시간 {elapsed_time:.2f}초")
    
    # 파일명 분석 수행 (--no-analyze 옵션이 없는 경우)
    if not args.no_analyze:
        print("\n=== 파일명 분석 및 정리 시작 ===")
        # --no-rename 옵션이 있으면 이름 변경 안함, 없으면 기본적으로 이름 변경 수행
        rename_files = not args.no_rename
        analyze_all_filenames(rename_files)

if __name__ == "__main__":
    main()
