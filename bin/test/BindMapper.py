#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#############################################################################
# Script: DB07.BindMapper.py
# Description: This script replaces bind variables in SQL files with actual
#              sample values to create executable SQL statements.
#
# Functionality:
# - Processes SQL files from both Oracle and PostgreSQL extract directories
# - For each SQL file, looks for a corresponding JSON file in the 'sampler' directory
#   created by DB06.BindSampler.py
# - Replaces bind variables in the SQL with their sample values:
#   * :variable format (Oracle style)
#   * #{variable} format (MyBatis style)
# - Formats values appropriately based on their data type:
#   * Strings are quoted
#   * Dates are converted to TO_DATE() functions
#   * Numbers are inserted as-is
# - Saves the modified SQL files to the respective 'done' directories
# - If no bind variables are found or no sample values exist, copies the file unchanged
#
# Usage:
#   python3 DB07.BindMapper.py
#
# Output:
#   Modified SQL files in 'orcl_sql_done' and 'pg_sql_done' directories
#############################################################################

import os
import re
import json
import shutil
import logging
from datetime import datetime

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
        'TEST_LOGS_FOLDER'
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
    
    print("\n환경 변수 확인 완료.")
    print("=" * 60)

# 환경변수 기반 경로 설정
def get_paths():
    """환경변수를 기반으로 경로들을 반환합니다."""
    test_folder = os.environ.get('TEST_FOLDER', os.getcwd())
    test_logs_folder = os.environ.get('TEST_LOGS_FOLDER', test_folder)
    
    return {
        'orcl_sql_dir': os.path.join(test_folder, 'orcl_sql_extract'),
        'pg_sql_dir': os.path.join(test_folder, 'pg_sql_extract'),
        'orcl_sql_done_dir': os.path.join(test_folder, 'orcl_sql_done'),
        'pg_sql_done_dir': os.path.join(test_folder, 'pg_sql_done'),
        'sampler_dir': os.path.join(test_folder, 'sampler'),
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
    log_file = os.path.join(logs_dir, 'bind_mapper.log')
    
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
    logger.info("BindMapper 실행 시작")
    logger.info("=" * 60)
    
    return logger
# Regular expressions for bind variables
BIND_PATTERN_COLON = r':([a-zA-Z0-9_]+)'
BIND_PATTERN_HASH = r'#{([a-zA-Z0-9_]+)}'

def ensure_directories():
    """출력 디렉토리들이 존재하는지 확인하고 생성합니다."""
    paths = get_paths()
    
    directories = [
        paths['orcl_sql_done_dir'],
        paths['pg_sql_done_dir']
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"출력 디렉토리 확인/생성: {directory}")

def get_sql_files(directory):
    """디렉토리에서 SQL 파일 목록을 가져옵니다."""
    if not os.path.exists(directory):
        logger.warning(f"디렉토리가 존재하지 않습니다: {directory}")
        return []
    
    sql_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.sql')]
    logger.info(f"{directory}에서 {len(sql_files)}개의 SQL 파일을 발견했습니다.")
    
    return sql_files

def get_bind_variables(sql_file):
    """SQL 파일에서 바인드 변수를 추출합니다."""
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Extract bind variables
        colon_vars = re.findall(BIND_PATTERN_COLON, sql_content)
        hash_vars = re.findall(BIND_PATTERN_HASH, sql_content)
        
        if colon_vars or hash_vars:
            logger.debug(f"{sql_file}: 바인드 변수 발견 - colon: {colon_vars}, hash: {hash_vars}")
        
        return colon_vars, hash_vars, sql_content
    except Exception as e:
        logger.error(f"SQL 파일 읽기 오류 {sql_file}: {str(e)}")
        return [], [], ""

def load_bind_values(sql_file):
    """sampler 디렉토리에서 바인드 변수 값을 로드합니다."""
    paths = get_paths()
    sampler_dir = paths['sampler_dir']
    
    base_name = os.path.basename(sql_file)
    bind_file = os.path.join(sampler_dir, base_name.replace('.sql', '.json'))
    
    if not os.path.exists(bind_file):
        logger.warning(f"바인드 변수 파일을 찾을 수 없습니다: {bind_file}")
        return {}
    
    try:
        with open(bind_file, 'r', encoding='utf-8') as f:
            bind_data = json.load(f)
        
        # Convert to dictionary for easier lookup
        bind_values = {}
        for item in bind_data:
            bind_values[item['variable']] = {
                'value': item['sample_value'],
                'type': item['type']
            }
        
        logger.debug(f"바인드 값 로드 완료: {bind_file} ({len(bind_values)}개 변수)")
        return bind_values
    except Exception as e:
        logger.error(f"바인드 변수 파일 읽기 오류 {bind_file}: {str(e)}")
        return {}

def replace_bind_variables(sql_content, colon_vars, hash_vars, bind_values):
    """SQL 내용에서 바인드 변수를 실제 값으로 대체합니다."""
    modified_sql = sql_content
    replaced_vars = []
    missing_vars = []
    
    # Replace colon-style bind variables (:variable)
    for var in colon_vars:
        if var in bind_values:
            value = bind_values[var]['value']
            var_type = bind_values[var]['type']
            
            # Format value based on type
            if var_type == "DATE":
                formatted_value = f"TO_DATE('{value}', 'YYYYMMDDHH24MISS')"
            elif var_type == "VARCHAR2" or (isinstance(value, str) and not str(value).isdigit()):
                formatted_value = f"'{value}'"
            else:
                formatted_value = str(value)
            
            modified_sql = modified_sql.replace(f":{var}", formatted_value)
            replaced_vars.append(f":{var} -> {formatted_value}")
        else:
            missing_vars.append(f":{var}")
    
    # Replace hash-style bind variables (#{variable})
    for var in hash_vars:
        if var in bind_values:
            value = bind_values[var]['value']
            var_type = bind_values[var]['type']
            
            # Format value based on type
            if var_type == "DATE":
                formatted_value = f"TO_DATE('{value}', 'YYYYMMDDHH24MISS')"
            elif var_type == "VARCHAR2" or (isinstance(value, str) and not str(value).isdigit()):
                formatted_value = f"'{value}'"
            else:
                formatted_value = str(value)
            
            modified_sql = modified_sql.replace(f"#{{{var}}}", formatted_value)
            replaced_vars.append(f"#{{{var}}} -> {formatted_value}")
        else:
            missing_vars.append(f"#{{{var}}}")
    
    # 로깅
    if replaced_vars:
        logger.debug(f"대체된 바인드 변수: {', '.join(replaced_vars)}")
    if missing_vars:
        logger.warning(f"샘플 값이 없는 바인드 변수: {', '.join(missing_vars)}")
    
    return modified_sql

def process_sql_files(source_dir, target_dir, db_type):
    """소스 디렉토리의 SQL 파일들을 처리하여 타겟 디렉토리에 저장합니다."""
    logger.info(f"{db_type} SQL 파일 처리 시작: {source_dir} -> {target_dir}")
    
    sql_files = get_sql_files(source_dir)
    if not sql_files:
        logger.warning(f"{source_dir}에 처리할 SQL 파일이 없습니다.")
        return 0, 0
    
    processed_count = 0
    skipped_count = 0
    
    for sql_file in sql_files:
        file_name = os.path.basename(sql_file)
        logger.debug(f"처리 중: {file_name}")
        
        colon_vars, hash_vars, sql_content = get_bind_variables(sql_file)
        
        # Skip if no bind variables found
        if not colon_vars and not hash_vars:
            shutil.copy(sql_file, os.path.join(target_dir, file_name))
            logger.debug(f"{file_name}: 바인드 변수 없음, 원본 복사")
            skipped_count += 1
            continue
        
        # Load bind values
        bind_values = load_bind_values(sql_file)
        
        if not bind_values:
            # If no bind values found, just copy the file
            shutil.copy(sql_file, os.path.join(target_dir, file_name))
            logger.warning(f"{file_name}: 바인드 값 없음, 원본 복사")
            skipped_count += 1
            continue
        
        # Replace bind variables
        modified_sql = replace_bind_variables(sql_content, colon_vars, hash_vars, bind_values)
        
        # Save modified SQL
        output_file = os.path.join(target_dir, file_name)
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(modified_sql)
            logger.info(f"{file_name}: 바인드 변수 대체 완료")
            processed_count += 1
        except Exception as e:
            logger.error(f"{file_name}: 파일 저장 오류 - {str(e)}")
            # 오류 발생 시 원본 복사
            shutil.copy(sql_file, output_file)
            skipped_count += 1
    
    logger.info(f"{db_type} 처리 완료: {processed_count}개 처리, {skipped_count}개 복사")
    return processed_count, skipped_count

def main():
    """메인 실행 함수"""
    paths = get_paths()
    
    # 경로 정보 출력
    logger.info("경로 설정:")
    logger.info(f"  Oracle SQL 입력: {paths['orcl_sql_dir']}")
    logger.info(f"  PostgreSQL SQL 입력: {paths['pg_sql_dir']}")
    logger.info(f"  샘플러 입력: {paths['sampler_dir']}")
    logger.info(f"  Oracle SQL 출력: {paths['orcl_sql_done_dir']}")
    logger.info(f"  PostgreSQL SQL 출력: {paths['pg_sql_done_dir']}")
    logger.info(f"  로그 디렉토리: {paths['logs_dir']}")
    
    # 출력 디렉토리 생성
    ensure_directories()
    
    # Oracle SQL 파일 처리
    orcl_processed, orcl_skipped = process_sql_files(
        paths['orcl_sql_dir'], 
        paths['orcl_sql_done_dir'], 
        "Oracle"
    )
    
    # PostgreSQL SQL 파일 처리
    pg_processed, pg_skipped = process_sql_files(
        paths['pg_sql_dir'], 
        paths['pg_sql_done_dir'], 
        "PostgreSQL"
    )
    
    # 최종 결과 출력
    total_processed = orcl_processed + pg_processed
    total_skipped = orcl_skipped + pg_skipped
    
    logger.info("=" * 60)
    logger.info("BindMapper 실행 완료")
    logger.info("=" * 60)
    logger.info(f"Oracle SQL: {orcl_processed}개 처리, {orcl_skipped}개 복사")
    logger.info(f"PostgreSQL SQL: {pg_processed}개 처리, {pg_skipped}개 복사")
    logger.info(f"전체: {total_processed}개 처리, {total_skipped}개 복사")
    logger.info("=" * 60)

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
