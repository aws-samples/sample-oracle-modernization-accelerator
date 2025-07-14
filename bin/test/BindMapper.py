#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#############################################################################
# Script: DB07.BindMapper.py
# Description: This script replaces bind variables in SQL files with actual
#              sample values to create executable SQL statements.
#
# Functionality:
# - Processes SQL files from both source and target extract directories
# - For each SQL file, looks for a corresponding JSON file in the 'sampler' directory
#   created by DB06.BindSampler.py
# - Replaces bind variables in the SQL with their sample values:
#   * :variable format (Oracle style)
#   * #{variable} format (MyBatis style)
# - Formats values appropriately based on their data type:
#   * Strings are quoted
#   * Dates are converted to TO_DATE() functions for Oracle, TO_TIMESTAMP() for PostgreSQL
#   * Numbers are inserted as-is
# - Saves the modified SQL files to the respective 'done' directories
# - If no bind variables are found or no sample values exist, copies the file unchanged
# - Target files use source sampler files (same bind variables, different SQL syntax)
#
# Usage:
#   python3 DB07.BindMapper.py
#
# Output:
#   Modified SQL files in 'src_sql_done' and 'tgt_sql_done' directories
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
        'src_sql_dir': os.path.join(test_folder, 'src_sql_extract'),
        'tgt_sql_dir': os.path.join(test_folder, 'tgt_sql_extract'),
        'src_sql_done_dir': os.path.join(test_folder, 'src_sql_done'),
        'tgt_sql_done_dir': os.path.join(test_folder, 'tgt_sql_done'),
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
BIND_PATTERN_COLON = r':([a-zA-Z][a-zA-Z0-9_]*)'  # Must start with letter
BIND_PATTERN_HASH = r'#{([a-zA-Z0-9_]+)(?:\s*[,:][^}]*)*}'

def ensure_directories():
    """출력 디렉토리들이 존재하는지 확인하고 생성합니다."""
    paths = get_paths()
    
    directories = [
        paths['src_sql_done_dir'],
        paths['tgt_sql_done_dir']
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
        
        # Remove comment lines and process line by line to avoid false positives
        lines = sql_content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip comment lines that start with --
            if line.strip().startswith('--'):
                processed_lines.append('')  # Keep line structure but remove content
            else:
                processed_lines.append(line)
        
        processed_content = '\n'.join(processed_lines)
        
        # First extract hash variables to avoid conflicts with colon variables inside them
        hash_matches = re.finditer(BIND_PATTERN_HASH, processed_content)
        hash_vars = []
        for match in hash_matches:
            var_name = match.group(1).strip()  # Remove whitespace from variable name
            hash_vars.append(var_name)
        
        # Remove hash variable patterns from content before extracting colon variables
        temp_content = processed_content
        for match in re.finditer(BIND_PATTERN_HASH.replace('([a-zA-Z0-9_]+)', '[a-zA-Z0-9_]+'), processed_content):
            temp_content = temp_content.replace(match.group(0), '')
        
        # Now extract colon variables from the cleaned content
        colon_vars = re.findall(BIND_PATTERN_COLON, temp_content)
        
        # Remove duplicates while preserving order
        colon_vars = list(dict.fromkeys(colon_vars))
        hash_vars = list(dict.fromkeys(hash_vars))
        
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
    
    # PostgreSQL 파일인 경우 Oracle 샘플 파일을 찾도록 변환
    if '_pg-' in base_name:
        # PostgreSQL 파일명을 Oracle 파일명으로 변환
        oracle_base_name = base_name.replace('_pg-', '_orcl-')
        bind_file = os.path.join(sampler_dir, oracle_base_name.replace('.sql', '.json'))
        logger.debug(f"PostgreSQL 파일 {base_name}에 대해 Oracle 샘플 파일 사용: {oracle_base_name}")
    else:
        # Oracle 파일인 경우 그대로 사용
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

def clean_sql_content(sql_content):
    """SQL 내용에서 템플릿 변수와 불필요한 요소들을 제거합니다."""
    lines = sql_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # ${queryId} 같은 템플릿 변수가 단독으로 있는 라인 제거
        if line.strip() == '${queryId}' or line.strip().startswith('${') and line.strip().endswith('}'):
            continue
        
        # 라인 내의 템플릿 변수 패턴 제거 (${variable} 형태)
        line = re.sub(r'\$\{[^}]+\}', '', line)
        
        # 빈 줄이 아니거나 의미있는 내용이 있는 경우만 추가
        if line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
            cleaned_lines.append(line)
    
    # 마지막 빈 줄들 제거
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    
    return '\n'.join(cleaned_lines)

def replace_bind_variables(sql_content, colon_vars, hash_vars, bind_values, db_type="oracle"):
    """SQL 내용에서 바인드 변수를 실제 값으로 대체합니다."""
    modified_sql = sql_content
    replaced_vars = []
    missing_vars = []
    
    # Replace colon-style bind variables (:variable)
    for var in colon_vars:
        if var in bind_values:
            value = bind_values[var]['value']
            var_type = bind_values[var]['type']
            
            # Format value based on type and database
            if var_type == "DATE":
                if db_type.lower() == "postgresql":
                    # Determine the appropriate format based on value length
                    if len(str(value)) == 6:  # YYYYMM
                        formatted_value = f"TO_TIMESTAMP('{value}', 'YYYYMM')"
                    elif len(str(value)) == 8:  # YYYYMMDD
                        formatted_value = f"TO_TIMESTAMP('{value}', 'YYYYMMDD')"
                    else:  # YYYYMMDDHH24MISS or other formats
                        formatted_value = f"TO_TIMESTAMP('{value}', 'YYYYMMDDHH24MISS')"
                else:
                    # Determine the appropriate format based on value length
                    if len(str(value)) == 6:  # YYYYMM
                        formatted_value = f"TO_DATE('{value}', 'YYYYMM')"
                    elif len(str(value)) == 8:  # YYYYMMDD
                        formatted_value = f"TO_DATE('{value}', 'YYYYMMDD')"
                    else:  # YYYYMMDDHH24MISS or other formats
                        formatted_value = f"TO_DATE('{value}', 'YYYYMMDDHH24MISS')"
            elif var_type == "NUMBER" or isinstance(value, (int, float)):
                # For NUMBER type or numeric values, don't quote
                formatted_value = str(value)
            elif var_type == "VARCHAR2" or var_type == "CHAR" or isinstance(value, str):
                # For string types, add quotes
                formatted_value = f"'{value}'"
            else:
                formatted_value = str(value)
            
            modified_sql = modified_sql.replace(f":{var}", formatted_value)
            replaced_vars.append(f":{var} -> {formatted_value}")
        else:
            missing_vars.append(f":{var}")
    
    # Replace hash-style bind variables (#{variable}, #{variable:type}, #{variable,jdbcType=TYPE})
    for var in hash_vars:
        if var in bind_values:
            value = bind_values[var]['value']
            var_type = bind_values[var]['type']
            
            # Find all patterns that match this variable (with various type specifications)
            import re
            patterns_to_replace = []
            
            # Pattern 1: #{variable}
            pattern1 = f"#{{{var}}}"
            if pattern1 in modified_sql:
                patterns_to_replace.append(pattern1)
            
            # Pattern 2: #{variable:type} - find all type specifications for this variable
            pattern2_regex = f"#{{{re.escape(var)}:([a-zA-Z0-9_]+)}}"
            for match in re.finditer(pattern2_regex, modified_sql):
                patterns_to_replace.append(match.group(0))
            
            # Pattern 3: #{variable,jdbcType=TYPE} - find all jdbcType specifications
            pattern3_regex = f"#{{{re.escape(var)},jdbcType=([a-zA-Z0-9_]+)}}"
            for match in re.finditer(pattern3_regex, modified_sql):
                patterns_to_replace.append(match.group(0))
            
            # Pattern 4: #{variable           ,mode=OUT,jdbcType=TYPE} - find patterns with extra whitespace
            pattern4_regex = f"#{{{re.escape(var)}\s*[,:][^}}]*}}"
            for match in re.finditer(pattern4_regex, modified_sql):
                patterns_to_replace.append(match.group(0))
            
            # Check if this bind variable is inside a TO_DATE function
            is_inside_to_date = False
            for pattern in patterns_to_replace:
                for match in re.finditer(re.escape(pattern), modified_sql):
                    start_pos = match.start()
                    # Look backwards to see if we're inside a TO_DATE function
                    preceding_text = modified_sql[max(0, start_pos-50):start_pos]
                    if re.search(r'TO_DATE\s*\([^)]*$', preceding_text, re.IGNORECASE):
                        is_inside_to_date = True
                        break
                if is_inside_to_date:
                    break
            
            # Format value based on context and type
            if is_inside_to_date:
                # Inside TO_DATE function, use simple string
                formatted_value = f"'{value}'"
            elif var_type == "DATE":
                if db_type.lower() == "postgresql":
                    # Determine the appropriate format based on value length
                    if len(str(value)) == 6:  # YYYYMM
                        formatted_value = f"TO_TIMESTAMP('{value}', 'YYYYMM')"
                    elif len(str(value)) == 8:  # YYYYMMDD
                        formatted_value = f"TO_TIMESTAMP('{value}', 'YYYYMMDD')"
                    else:  # YYYYMMDDHH24MISS or other formats
                        formatted_value = f"TO_TIMESTAMP('{value}', 'YYYYMMDDHH24MISS')"
                else:
                    # Determine the appropriate format based on value length
                    if len(str(value)) == 6:  # YYYYMM
                        formatted_value = f"TO_DATE('{value}', 'YYYYMM')"
                    elif len(str(value)) == 8:  # YYYYMMDD
                        formatted_value = f"TO_DATE('{value}', 'YYYYMMDD')"
                    else:  # YYYYMMDDHH24MISS or other formats
                        formatted_value = f"TO_DATE('{value}', 'YYYYMMDDHH24MISS')"
            elif var_type == "NUMBER" or isinstance(value, (int, float)):
                # For NUMBER type or numeric values, don't quote
                formatted_value = str(value)
            elif var_type == "VARCHAR2" or var_type == "CHAR" or var_type == "CLOB" or isinstance(value, str):
                # For string types, add quotes
                formatted_value = f"'{value}'"
            else:
                formatted_value = str(value)
            
            # Replace all patterns for this variable
            for pattern in patterns_to_replace:
                if pattern in modified_sql:
                    modified_sql = modified_sql.replace(pattern, formatted_value)
                    replaced_vars.append(f"{pattern} -> {formatted_value}")
        else:
            missing_vars.append(f"#{{{var}}}")
    
    # 로깅
    if replaced_vars:
        logger.debug(f"대체된 바인드 변수: {', '.join(replaced_vars)}")
    if missing_vars:
        logger.warning(f"샘플 값이 없는 바인드 변수: {', '.join(missing_vars)}")
    
    return modified_sql

def add_oracle_terminator(sql_content):
    """Oracle SQL에 구문 종료 문자 '/'를 추가합니다."""
    # SQL 내용을 정리하고 마지막에 '/'가 없으면 추가
    sql_content = sql_content.strip()
    
    # 이미 ';' 또는 '/'로 끝나는지 확인
    if sql_content.endswith(';'):
        # ';'를 '/'로 교체
        sql_content = sql_content[:-1].strip() + '\n/'
    elif not sql_content.endswith('/'):
        # '/'가 없으면 추가
        sql_content = sql_content + '\n/'
    
    return sql_content

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
        
        # Clean SQL content first (remove template variables like ${queryId})
        cleaned_sql_content = clean_sql_content(sql_content)
        
        # Skip if no bind variables found
        if not colon_vars and not hash_vars:
            # Even if no bind variables, still clean the SQL content
            output_file = os.path.join(target_dir, file_name)
            try:
                # 소스 SQL인 경우 구문 종료 문자 추가 (Oracle SQL)
                if db_type.lower() == "source" and not '_pg-' in file_name:
                    cleaned_sql_content = add_oracle_terminator(cleaned_sql_content)
                    logger.debug(f"{file_name}: Oracle SQL에 구문 종료 문자 '/' 추가")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_sql_content)
                logger.debug(f"{file_name}: 바인드 변수 없음, 템플릿 정리 후 저장")
                skipped_count += 1
            except Exception as e:
                logger.error(f"{file_name}: 파일 저장 오류 - {str(e)}")
                shutil.copy(sql_file, output_file)
                skipped_count += 1
            continue
        
        # Load bind values
        bind_values = load_bind_values(sql_file)
        
        if not bind_values:
            # If no bind values found, save cleaned SQL
            output_file = os.path.join(target_dir, file_name)
            try:
                # 소스 SQL인 경우 구문 종료 문자 추가 (Oracle SQL)
                if db_type.lower() == "source" and not '_pg-' in file_name:
                    cleaned_sql_content = add_oracle_terminator(cleaned_sql_content)
                    logger.debug(f"{file_name}: Oracle SQL에 구문 종료 문자 '/' 추가")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_sql_content)
                logger.warning(f"{file_name}: 바인드 값 없음, 템플릿 정리 후 저장")
                skipped_count += 1
            except Exception as e:
                logger.error(f"{file_name}: 파일 저장 오류 - {str(e)}")
                shutil.copy(sql_file, output_file)
                skipped_count += 1
            continue
        
        # Replace bind variables with appropriate database type
        if '_pg-' in file_name:
            modified_sql = replace_bind_variables(cleaned_sql_content, colon_vars, hash_vars, bind_values, "postgresql")
        else:
            modified_sql = replace_bind_variables(cleaned_sql_content, colon_vars, hash_vars, bind_values, "oracle")
        
        # Oracle SQL인 경우 구문 종료 문자 추가 (소스 SQL 디렉토리에서 온 파일)
        if db_type.lower() == "source" and not '_pg-' in file_name:
            modified_sql = add_oracle_terminator(modified_sql)
            logger.debug(f"{file_name}: Oracle SQL에 구문 종료 문자 '/' 추가")
        
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
    logger.info(f"  소스 SQL 입력: {paths['src_sql_dir']}")
    logger.info(f"  타겟 SQL 입력: {paths['tgt_sql_dir']}")
    logger.info(f"  샘플러 입력: {paths['sampler_dir']}")
    logger.info(f"  소스 SQL 출력: {paths['src_sql_done_dir']}")
    logger.info(f"  타겟 SQL 출력: {paths['tgt_sql_done_dir']}")
    logger.info(f"  로그 디렉토리: {paths['logs_dir']}")
    
    # 출력 디렉토리 생성
    ensure_directories()
    
    # 소스 SQL 파일 처리
    src_processed, src_skipped = process_sql_files(
        paths['src_sql_dir'], 
        paths['src_sql_done_dir'], 
        "Source"
    )
    
    # 타겟 SQL 파일 처리
    tgt_processed, tgt_skipped = process_sql_files(
        paths['tgt_sql_dir'], 
        paths['tgt_sql_done_dir'], 
        "Target"
    )
    
    # 최종 결과 출력
    total_processed = src_processed + tgt_processed
    total_skipped = src_skipped + tgt_skipped
    
    logger.info("=" * 60)
    logger.info("BindMapper 실행 완료")
    logger.info("=" * 60)
    logger.info(f"소스 SQL: {src_processed}개 처리, {src_skipped}개 복사")
    logger.info(f"타겟 SQL: {tgt_processed}개 처리, {tgt_skipped}개 복사")
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
