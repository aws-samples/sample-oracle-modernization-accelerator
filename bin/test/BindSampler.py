#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#############################################################################
# Script: DB06.BindSampler.py
# Description: This script analyzes SQL files to identify bind variables and
#              assigns appropriate sample values based on variable names and
#              a dictionary of database column values.
#
# Functionality:
# - Scans SQL files in the 'orcl_sql_extract' directory
# - Extracts bind variables (both :variable and #{variable} formats)
# - Determines the likely data type of each variable based on:
#   * Matching against column names in the dictionary
#   * Analyzing variable naming patterns (e.g., date_*, *_id, is_*)
# - Assigns appropriate sample values from the dictionary:
#   * First tries to find a direct match for the variable name
#   * Then looks for similar column names
#   * Falls back to any column of the same data type
#   * Uses default values if no match is found
# - Saves the results as JSON files in the 'sampler' directory
#
# The output JSON files are used by DB07.BindMapper.py to replace bind
# variables with actual values in SQL statements.
#
# Usage:
#   python3 DB06.BindSampler.py
#
# Output:
#   JSON files in the 'sampler' directory, one per SQL file
#############################################################################

import os
import re
import json
import random
from datetime import datetime, timedelta

def check_environment_variables():
    """
    필수 환경 변수가 설정되어 있는지 확인합니다.
    """
    print("=" * 60)
    print("환경 변수 확인 중...")
    print("=" * 60)
    
    # 권장 환경 변수 목록
    recommended_env_vars = [
        'TEST_FOLDER'
    ]
    
    # 선택적 환경 변수 목록
    optional_env_vars = [
        'DB_ASSESSMENTS_FOLDER'
    ]
    
    print("권장 환경 변수 확인 (설정되지 않으면 기본값 사용):")
    for var in recommended_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            if var == 'TEST_FOLDER':
                print(f"- {var}: 설정되지 않음 (기본값: 현재 작업 디렉토리)")
    
    print("\n선택적 환경 변수 확인:")
    for var in optional_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"- {var}: 설정되지 않음 (선택사항)")
    
    print("\n환경 변수 확인 완료.")
    print("=" * 60)

# Configuration - 환경변수 기반으로 경로 설정
def get_paths():
    """환경변수를 기반으로 경로들을 반환합니다."""
    test_folder = os.environ.get('TEST_FOLDER', os.getcwd())
    
    return {
        'sql_dir': os.path.join(test_folder, 'orcl_sql_extract'),
        'dictionary_file': os.path.join(test_folder, 'dictionary', 'all_dictionary.json'),
        'output_dir': os.path.join(test_folder, 'sampler')
    }

# Regular expressions for bind variables
# More precise pattern to avoid matching Oracle date format elements like :MI: and :SS:
BIND_PATTERN = r'(?:^|[^A-Z])[:#{]([a-zA-Z][a-zA-Z0-9_]*)[}]?(?![A-Z:])'  # Match both :var and #{var} but not :MI: or :SS:
# Common type patterns
DATE_PATTERN = r'(?i)(date|dt|day|time)'
NUMBER_PATTERN = r'(?i)(num|cnt|count|id|no|seq|amt|amount|rate|pct|percent|age|year|month|day|hour|min|sec)'
BOOLEAN_PATTERN = r'(?i)(yn|flag|is_|has_|use_|active|enabled|status)'

def load_dictionary():
    """Load the dictionary from JSON file"""
    paths = get_paths()
    dictionary_file = paths['dictionary_file']
    
    if not os.path.exists(dictionary_file):
        print(f"오류: 딕셔너리 파일을 찾을 수 없습니다: {dictionary_file}")
        print("먼저 GetDictionary.py를 실행하여 딕셔너리 파일을 생성하세요.")
        return {}
    
    try:
        with open(dictionary_file, 'r', encoding='utf-8') as f:
            dictionary = json.load(f)
        print(f"딕셔너리 파일 로드 완료: {dictionary_file}")
        
        # 스키마별 테이블 수 계산
        total_tables = 0
        for schema_name, schema_data in dictionary.items():
            schema_table_count = len(schema_data)
            total_tables += schema_table_count
            print(f"스키마 {schema_name}: {schema_table_count}개 테이블")
        
        print(f"전체 테이블 수: {total_tables}")
        return dictionary
    except Exception as e:
        print(f"딕셔너리 파일 로드 중 오류 발생: {e}")
        return {}

def get_sql_files():
    """Get list of SQL files in the directory"""
    paths = get_paths()
    sql_dir = paths['sql_dir']
    
    if not os.path.exists(sql_dir):
        print(f"오류: SQL 디렉토리가 존재하지 않습니다: {sql_dir}")
        print("먼저 XMLToSQL.py를 실행하여 SQL 파일들을 생성하세요.")
        return []
    
    sql_files = [os.path.join(sql_dir, f) for f in os.listdir(sql_dir) if f.endswith('.sql')]
    print(f"SQL 파일 디렉토리: {sql_dir}")
    print(f"발견된 SQL 파일 수: {len(sql_files)}")
    
    return sql_files

def extract_bind_variables(sql_content):
    """Extract bind variables from SQL content"""
    # Find all potential bind variables
    all_matches = re.findall(r'[:#{]([a-zA-Z0-9_]+)[}]?', sql_content)
    
    # Filter out Oracle date format elements
    oracle_date_formats = {'YYYY', 'MM', 'DD', 'HH', 'HH24', 'MI', 'SS', 'RRRR', 'YY', 'MON', 'MONTH', 'DY', 'DAY'}
    
    # Only keep variables that are not Oracle date format elements
    bind_vars = [var for var in all_matches if var not in oracle_date_formats]
    
    return bind_vars

def camel_to_snake(name):
    """Convert camelCase to SNAKE_CASE"""
    # Insert underscore before uppercase letters (except the first one)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Insert underscore before uppercase letters that follow lowercase letters
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()

def analyze_date_format_from_sql(var_name, sql_content):
    """SQL 내용을 분석해서 날짜 변수의 적절한 형식을 결정합니다."""
    import re
    
    # 변수가 사용되는 패턴들을 찾아서 적절한 형식 결정
    patterns = [
        # TO_DATE 함수에서 YYYYMMDD 형식을 명시적으로 요구하는 경우
        (r'TO_DATE\s*\(\s*[#:{}]*' + re.escape(var_name) + r'[}]*\s*,\s*[\'"]YYYYMMDD[\'"]', 'YYYYMMDD'),
        # TO_DATE 함수에서 YYYYMM 형식을 명시적으로 요구하는 경우  
        (r'TO_DATE\s*\(\s*[#:{}]*' + re.escape(var_name) + r'[}]*\s*,\s*[\'"]YYYYMM[\'"]', 'YYYYMM'),
        # TO_DATE 함수에서 YYYY-MM-DD 형식을 명시적으로 요구하는 경우
        (r'TO_DATE\s*\(\s*[#:{}]*' + re.escape(var_name) + r'[}]*\s*,\s*[\'"]YYYY-MM-DD[\'"]', 'YYYY-MM-DD'),
        # ||'01' 패턴과 함께 YYYYMMDD를 사용하는 경우 (월말일 추가)
        (r'TO_DATE\s*\(\s*[#:{}]*' + re.escape(var_name) + r'[}]*\s*\|\|\s*[\'"]01[\'"].*?YYYYMMDD', 'YYYYMM'),
    ]
    
    for pattern, format_type in patterns:
        if re.search(pattern, sql_content, re.IGNORECASE):
            print(f"SQL 분석: {var_name} -> {format_type} 형식 감지")
            return format_type
    
    return None
    # Insert underscore before uppercase letters that follow lowercase letters
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()

def find_column_in_dictionary(var_name, dictionary):
    """Find a column in the dictionary that matches the variable name"""
    # Convert variable name to different formats for matching
    var_name_lower = var_name.lower()
    var_name_upper = var_name.upper()
    var_name_snake = camel_to_snake(var_name)
    
    # Special mappings for common variable patterns with preferred table
    special_mappings = {
        'fileid': ('ATCH_FILE_ID', 'TB_COM003'),
        'fileseq': ('ATCH_FILE_SEQ', 'TB_COM003'),
        'attachfileid': ('ATCH_FILE_ID', 'TB_COM003'),
        'attachfileseq': ('ATCH_FILE_SEQ', 'TB_COM003'),
        'atchfileid': ('ATCH_FILE_ID', 'TB_COM003'),
        'atchfileseq': ('ATCH_FILE_SEQ', 'TB_COM003')
    }
    
    # Check special mappings first
    if var_name_lower in special_mappings:
        target_column, preferred_table = special_mappings[var_name_lower]
        print(f"특별 매핑 적용: {var_name} -> {target_column} (선호 테이블: {preferred_table})")
        
        # First try to find in preferred table
        for schema_name, schema_data in dictionary.items():
            if preferred_table in schema_data:
                table_data = schema_data[preferred_table]
                if "columns" in table_data and target_column in table_data["columns"]:
                    col_data = table_data["columns"][target_column]
                    print(f"특별 매핑 발견 (선호 테이블): {var_name} -> {target_column} in {preferred_table} ({col_data.get('type')})")
                    return col_data.get("type", "").upper()
        
        # If not found in preferred table, search in any table
        for schema_name, schema_data in dictionary.items():
            for table_name, table_data in schema_data.items():
                if "columns" not in table_data:
                    continue
                if target_column in table_data["columns"]:
                    col_data = table_data["columns"][target_column]
                    print(f"특별 매핑 발견 (일반): {var_name} -> {target_column} in {table_name} ({col_data.get('type')})")
                    return col_data.get("type", "").upper()
    
    # List of possible column name variations to try
    possible_names = [
        var_name_upper,           # workDt -> WORKDT
        var_name_snake,           # workDt -> WORK_DT
        var_name_lower,           # workDt -> workdt
        var_name                  # workDt -> workDt
    ]
    
    print(f"변수 '{var_name}'에 대한 매칭 시도: {possible_names}")
    
    # First, try exact matches with all possible variations
    for schema_name, schema_data in dictionary.items():
        for table_name, table_data in schema_data.items():
            if "columns" not in table_data:
                continue
                
            for col_name, col_data in table_data["columns"].items():
                if col_name in possible_names:
                    print(f"정확한 매칭 발견: {var_name} -> {col_name} ({col_data.get('type')})")
                    return col_data.get("type", "").upper()
    
    # If no exact match, try partial matches
    for schema_name, schema_data in dictionary.items():
        for table_name, table_data in schema_data.items():
            if "columns" not in table_data:
                continue
                
            for col_name, col_data in table_data["columns"].items():
                # Check if column name contains any of the possible variable names or vice versa
                for possible_name in possible_names:
                    if (col_name.lower() in possible_name.lower() or 
                        possible_name.lower() in col_name.lower()):
                        print(f"부분 매칭 발견: {var_name} -> {col_name} ({col_data.get('type')})")
                        return col_data.get("type", "").upper()
    
    print(f"매칭 실패: {var_name}")
    return None

def guess_variable_type(var_name, dictionary):
    """Guess the type of variable based on dictionary first, then name patterns"""
    # First try to find the type in the dictionary
    dict_type = find_column_in_dictionary(var_name, dictionary)
    if dict_type:
        return dict_type
    
    # If not found in dictionary, default to VARCHAR2 instead of pattern matching
    # This prevents incorrect DATE type assignment
    print(f"딕셔너리에서 매칭되지 않음: {var_name} -> VARCHAR2로 기본 설정")
    return "VARCHAR2"

def get_sample_value(var_type, var_name, dictionary, sql_content=None):
    """Get a sample value for the variable type from dictionary"""
    # Default values if no match found
    default_values = {
        "DATE": "20191118",  # 기본 날짜 형식을 YYYYMMDD로 변경
        "NUMBER": 1,         # 숫자는 정수로 반환
        "BOOLEAN": "Y",
        "VARCHAR2": "SAMPLE_VALUE"
    }
    
    # Convert variable name to different formats for matching
    var_name_lower = var_name.lower()
    var_name_upper = var_name.upper()
    var_name_snake = camel_to_snake(var_name)
    
    # Special mappings for common variable patterns with preferred table
    special_mappings = {
        'fileid': ('ATCH_FILE_ID', 'TB_COM003'),
        'fileseq': ('ATCH_FILE_SEQ', 'TB_COM003'),
        'attachfileid': ('ATCH_FILE_ID', 'TB_COM003'),
        'attachfileseq': ('ATCH_FILE_SEQ', 'TB_COM003'),
        'atchfileid': ('ATCH_FILE_ID', 'TB_COM003'),
        'atchfileseq': ('ATCH_FILE_SEQ', 'TB_COM003')
    }
    
    # Check special mappings first
    if var_name_lower in special_mappings:
        target_column, preferred_table = special_mappings[var_name_lower]
        print(f"샘플 값 특별 매핑 적용: {var_name} -> {target_column} (선호 테이블: {preferred_table})")
        
        # First try to find in preferred table
        for schema_name, schema_data in dictionary.items():
            if preferred_table in schema_data:
                table_data = schema_data[preferred_table]
                if "columns" in table_data and target_column in table_data["columns"]:
                    col_data = table_data["columns"][target_column]
                    if "sample_values" in col_data and col_data["sample_values"]:
                        sample_value = col_data["sample_values"][0]  # Use first sample value
                        column_type = col_data.get("type", "").upper()
                        
                        # Convert sample value based on column type
                        if column_type == "NUMBER":
                            try:
                                if '.' in str(sample_value):
                                    sample_value = float(sample_value)
                                else:
                                    sample_value = int(sample_value)
                            except (ValueError, TypeError):
                                sample_value = 1
                        
                        print(f"특별 매핑 샘플 값 (선호 테이블): {var_name} -> {target_column} in {preferred_table} = {sample_value}")
                        return sample_value
        
        # If not found in preferred table or no sample values, search in any table
        for schema_name, schema_data in dictionary.items():
            for table_name, table_data in schema_data.items():
                if "columns" not in table_data:
                    continue
                if target_column in table_data["columns"]:
                    col_data = table_data["columns"][target_column]
                    if "sample_values" in col_data and col_data["sample_values"]:
                        sample_value = col_data["sample_values"][0]  # Use first sample value
                        column_type = col_data.get("type", "").upper()
                        
                        # Convert sample value based on column type
                        if column_type == "NUMBER":
                            try:
                                if '.' in str(sample_value):
                                    sample_value = float(sample_value)
                                else:
                                    sample_value = int(sample_value)
                            except (ValueError, TypeError):
                                sample_value = 1
                        
                        print(f"특별 매핑 샘플 값 (일반): {var_name} -> {target_column} in {table_name} = {sample_value}")
                        return sample_value
    
    possible_names = [var_name_upper, var_name_snake, var_name_lower, var_name]
    
    # First try to find a direct match for the variable name in the dictionary
    matched_column = None
    matched_column_data = None
    
    # Try to find a matching column in the dictionary based on variable name
    for schema_name, schema_data in dictionary.items():
        for table_name, table_data in schema_data.items():
            if "columns" not in table_data:
                continue
                
            for col_name, col_data in table_data["columns"].items():
                # Check for exact match with any possible name variation
                if col_name in possible_names:
                    if "sample_values" in col_data and col_data["sample_values"]:
                        matched_column = col_name
                        matched_column_data = col_data
                        print(f"샘플 값 매칭: {var_name} -> {col_name} (샘플: {col_data['sample_values']})")
                        break
            
            if matched_column:
                break
        
        if matched_column:
            break
    
    # If no direct match found, try partial matching
    if not matched_column:
        for schema_name, schema_data in dictionary.items():
            for table_name, table_data in schema_data.items():
                if "columns" not in table_data:
                    continue
                    
                for col_name, col_data in table_data["columns"].items():
                    # Check for partial matches
                    for possible_name in possible_names:
                        if (col_name.lower() in possible_name.lower() or 
                            possible_name.lower() in col_name.lower()):
                            if "sample_values" in col_data and col_data["sample_values"]:
                                matched_column = col_name
                                matched_column_data = col_data
                                print(f"부분 샘플 값 매칭: {var_name} -> {col_name} (샘플: {col_data['sample_values']})")
                                break
                    
                    if matched_column:
                        break
                
                if matched_column:
                    break
            
            if matched_column:
                break
    
    # If we found a matching column, use its sample value
    if matched_column and matched_column_data:
        # Special handling for DATE type columns
        if matched_column_data.get("type", "").upper() == "DATE":
            # Analyze SQL content to determine appropriate date format
            if sql_content:
                date_format = analyze_date_format_from_sql(var_name, sql_content)
                if date_format == 'YYYYMM':
                    var_name_lower = var_name.lower()
                    if 'end' in var_name_lower or 'to' in var_name_lower or 'ed' in var_name_lower:
                        return "202103"  # End month
                    else:
                        return "202103"  # Month format
                elif date_format == 'YYYYMMDD':
                    var_name_lower = var_name.lower()
                    if 'end' in var_name_lower or 'to' in var_name_lower or 'ed' in var_name_lower:
                        return "20210331"  # End date
                    else:
                        return "20210301"  # Start date
                elif date_format == 'YYYY-MM-DD':
                    return "2021-03-01"
                # Default to YYYYMMDD for other cases
            
            # For DATE columns, use appropriate date format (default to YYYYMMDD)
            var_name_lower = var_name.lower()
            if 'end' in var_name_lower or 'to' in var_name_lower or 'ed' in var_name_lower:
                return "20210331"  # End date
            else:
                return "20210301"  # Start date
        
        # Get a random sample value for non-DATE types
        if matched_column_data["sample_values"]:
            sample_value = random.choice(matched_column_data["sample_values"])
        else:
            sample_value = "SAMPLE_VALUE"
        
        # Convert sample value based on column type
        column_type = matched_column_data.get("type", "").upper()
        if column_type == "NUMBER":
            # For NUMBER columns, ensure we return a numeric value
            try:
                # Try to convert to int first, then float if needed
                if '.' in str(sample_value):
                    sample_value = float(sample_value)
                else:
                    sample_value = int(sample_value)
            except (ValueError, TypeError):
                # If conversion fails, use default numeric value
                sample_value = 1
        elif column_type in ["VARCHAR2", "CHAR", "CLOB", "NVARCHAR2", "NCHAR"]:
            # For string types, ensure it's a string and check length constraints
            sample_value = str(sample_value)
            
            # Check if the column has a length constraint
            if "length" in matched_column_data and matched_column_data["length"]:
                max_length = int(matched_column_data["length"])
                # If the sample value exceeds the length, truncate it or get another value
                if len(sample_value) > max_length:
                    # Try to find another sample value that fits the length constraint
                    if matched_column_data["sample_values"]:
                        valid_samples = [s for s in matched_column_data["sample_values"] if len(str(s)) <= max_length]
                        if valid_samples:
                            sample_value = str(random.choice(valid_samples))
                        else:
                            # If no valid sample found, truncate the value
                            sample_value = sample_value[:max_length]
        
        return sample_value
    
    # If no match found for the specific variable, try to find any column of the same type
    # But only if the variable name doesn't suggest a specific type
    var_name_lower = var_name.lower()
    if not any(pattern in var_name_lower for pattern in ['dt', 'date', 'day', 'time', 'id', 'no', 'seq', 'cnt', 'count', 'num', 'yn', 'flag']):
        for schema_name, schema_data in dictionary.items():
            for table_name, table_data in schema_data.items():
                if "columns" not in table_data:
                    continue
                    
                for col_name, col_data in table_data["columns"].items():
                    if col_data.get("type", "").upper() == var_type:
                        if "sample_values" in col_data and col_data["sample_values"]:
                            sample_value = random.choice(col_data["sample_values"])
                            
                            # Convert sample value based on column type
                            column_type = col_data.get("type", "").upper()
                            if column_type == "NUMBER":
                                # For NUMBER columns, ensure we return a numeric value
                                try:
                                    # Try to convert to int first, then float if needed
                                    if '.' in str(sample_value):
                                        sample_value = float(sample_value)
                                    else:
                                        sample_value = int(sample_value)
                                except (ValueError, TypeError):
                                    # If conversion fails, use default numeric value
                                    sample_value = 1
                            elif column_type in ["VARCHAR2", "CHAR", "CLOB", "NVARCHAR2", "NCHAR"]:
                                # For string types, ensure it's a string and check length constraints
                                sample_value = str(sample_value)
                                
                                # Check if the column has a length constraint
                                if "length" in col_data and col_data["length"]:
                                    max_length = int(col_data["length"])
                                    # If the sample value exceeds the length, truncate it or get another value
                                    if len(sample_value) > max_length:
                                        # Try to find another sample value that fits the length constraint
                                        valid_samples = [s for s in col_data["sample_values"] if len(str(s)) <= max_length]
                                        if valid_samples:
                                            sample_value = str(random.choice(valid_samples))
                                        else:
                                            # If no valid sample found, truncate the value
                                            sample_value = sample_value[:max_length]
                            
                            return sample_value
    
    # If still no match, return default value based on variable name and type
    var_name_lower = var_name.lower()
    if any(pattern in var_name_lower for pattern in ['dt', 'date', 'day', 'time']):
        # Analyze SQL content for date format if available
        if sql_content:
            date_format = analyze_date_format_from_sql(var_name, sql_content)
            if date_format == 'YYYYMM':
                if 'end' in var_name_lower or 'to' in var_name_lower or 'ed' in var_name_lower:
                    return "202103"  # End month
                else:
                    return "202103"  # Month format
            elif date_format == 'YYYY-MM-DD':
                return "2021-03-01"
        # Default to YYYYMMDD format
        if 'end' in var_name_lower or 'to' in var_name_lower or 'ed' in var_name_lower:
            return "20210331"  # End date
        else:
            return "20210301"  # Start date
    elif any(pattern in var_name_lower for pattern in ['id', 'no', 'seq', 'cnt', 'count', 'num']):
        return 1  # 숫자 관련 변수 (정수로 반환)
    elif any(pattern in var_name_lower for pattern in ['yn', 'flag']):
        return "Y"  # 불린 관련 변수
    else:
        # Return appropriate default based on variable type
        if var_type == "NUMBER":
            return 1  # 숫자 타입은 정수로 반환
        elif var_type == "DATE":
            # Analyze SQL content for date format if available
            if sql_content:
                date_format = analyze_date_format_from_sql(var_name, sql_content)
                if date_format == 'YYYYMM':
                    return "202103"
                elif date_format == 'YYYY-MM-DD':
                    return "2021-03-01"
            return "20210301"  # Default YYYYMMDD format
        else:
            return default_values.get(var_type, "SAMPLE_VALUE")

def main():
    # 경로 설정
    paths = get_paths()
    
    print(f"SQL 파일 디렉토리: {paths['sql_dir']}")
    print(f"딕셔너리 파일: {paths['dictionary_file']}")
    print(f"출력 디렉토리: {paths['output_dir']}")
    print()
    
    dictionary = load_dictionary()
    if not dictionary:
        print("딕셔너리를 로드할 수 없어 프로그램을 종료합니다.")
        return
    
    sql_files = get_sql_files()
    if not sql_files:
        print("처리할 SQL 파일이 없어 프로그램을 종료합니다.")
        return
    
    results = {}
    
    for sql_file in sql_files:
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Extract bind variables
            bind_vars = extract_bind_variables(sql_content)
            
            # Remove duplicates while preserving order
            unique_bind_vars = []
            for var in bind_vars:
                if var not in unique_bind_vars:
                    unique_bind_vars.append(var)
            
            if unique_bind_vars:
                file_name = os.path.basename(sql_file)
                results[file_name] = []
                
                print(f"처리 중: {file_name} ({len(unique_bind_vars)}개 바인드 변수)")
                
                for var in unique_bind_vars:
                    var_type = guess_variable_type(var, dictionary)
                    sample_value = get_sample_value(var_type, var, dictionary, sql_content)
                    
                    results[file_name].append({
                        "variable": var,
                        "type": var_type,
                        "sample_value": sample_value
                    })
                    
                    print(f"  - {var}: {var_type} = {sample_value}")
    
        except Exception as e:
            print(f"Error processing {sql_file}: {str(e)}")
    
    # Save results to sampler directory
    output_dir = paths['output_dir']
    os.makedirs(output_dir, exist_ok=True)
    
    for file_name, bind_vars in results.items():
        output_file = os.path.join(output_dir, file_name.replace('.sql', '.json'))
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bind_vars, f, indent=2, ensure_ascii=False)
    
    print(f"\n처리 완료:")
    print(f"- 처리된 SQL 파일: {len(sql_files)}개")
    print(f"- 바인드 변수가 있는 파일: {len(results)}개")
    print(f"- 생성된 JSON 파일 위치: {output_dir}")
    
    # 생성된 파일 목록 출력 (처음 10개만)
    if results:
        print(f"\n생성된 JSON 파일 목록 (처음 10개):")
        for i, file_name in enumerate(list(results.keys())[:10]):
            json_file = file_name.replace('.sql', '.json')
            print(f"  {i+1}. {json_file}")
        if len(results) > 10:
            print(f"  ... 외 {len(results) - 10}개 파일")

if __name__ == "__main__":
    # 환경 변수 확인
    check_environment_variables()
    main()
