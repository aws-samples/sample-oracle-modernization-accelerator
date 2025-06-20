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
BIND_PATTERN = r'[:#{]([a-zA-Z0-9_]+)[}]?'  # Match both :var and #{var}
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
        print(f"테이블 수: {len(dictionary)}")
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
    return re.findall(BIND_PATTERN, sql_content)

def find_column_in_dictionary(var_name, dictionary):
    """Find a column in the dictionary that matches the variable name"""
    # Convert variable name to lowercase for case-insensitive comparison
    var_name_lower = var_name.lower()
    
    # First, try to find an exact match
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            if col_name.lower() == var_name_lower:
                return col_data.get("type", "").upper()
    
    # If no exact match, try to find a partial match
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            # Check if column name contains the variable name or vice versa
            if col_name.lower() in var_name_lower or var_name_lower in col_name.lower():
                return col_data.get("type", "").upper()
    
    # Special case for variables that might map to database columns
    # Map camelCase or snake_case variable names to database column names
    # For example, pnrNo might map to PYPB_PNR_NO
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            col_parts = col_name.lower().split('_')
            var_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', var_name)
            var_parts = [p.lower() for p in var_parts]
            
            # Check if the variable parts are contained in the column parts
            matches = 0
            for var_part in var_parts:
                if any(var_part in col_part for col_part in col_parts):
                    matches += 1
            
            # If more than half of the parts match, consider it a match
            if matches >= len(var_parts) / 2:
                return col_data.get("type", "").upper()
    
    return None

def guess_variable_type(var_name, dictionary):
    """Guess the type of variable based on dictionary first, then name patterns"""
    # First try to find the type in the dictionary
    dict_type = find_column_in_dictionary(var_name, dictionary)
    if dict_type:
        return dict_type
    
    # If not found in dictionary, use naming patterns
    if re.search(DATE_PATTERN, var_name):
        return "DATE"
    elif re.search(NUMBER_PATTERN, var_name):
        return "NUMBER"
    elif re.search(BOOLEAN_PATTERN, var_name):
        return "BOOLEAN"
    else:
        return "VARCHAR2"

def get_sample_value(var_type, var_name, dictionary):
    """Get a sample value for the variable type from dictionary"""
    # Default values if no match found
    default_values = {
        "DATE": datetime.now().strftime("%Y%m%d%H%M%S"),
        "NUMBER": "1",
        "BOOLEAN": "Y",
        "VARCHAR2": "SAMPLE_VALUE"
    }
    
    # First try to find a direct match for the variable name in the dictionary
    matched_column = None
    matched_column_data = None
    
    # Try to find a matching column in the dictionary based on variable name
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            # Check for exact match or if column name contains the variable name or vice versa
            if col_name.lower() == var_name.lower() or col_name.lower() in var_name.lower() or var_name.lower() in col_name.lower():
                # Check if the column has sample values
                if "sample_values" in col_data and col_data["sample_values"]:
                    matched_column = col_name
                    matched_column_data = col_data
                    break
        
        if matched_column:
            break
    
    # If no direct match found, try to find a match using camelCase/snake_case conversion
    if not matched_column:
        for table_name, table_data in dictionary.items():
            if "columns" not in table_data:
                continue
                
            for col_name, col_data in table_data["columns"].items():
                col_parts = col_name.lower().split('_')
                var_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', var_name)
                var_parts = [p.lower() for p in var_parts]
                
                # Check if the variable parts are contained in the column parts
                matches = 0
                for var_part in var_parts:
                    if any(var_part in col_part for col_part in col_parts):
                        matches += 1
                
                # If more than half of the parts match, consider it a match
                if matches >= len(var_parts) / 2:
                    if "sample_values" in col_data and col_data["sample_values"]:
                        matched_column = col_name
                        matched_column_data = col_data
                        break
            
            if matched_column:
                break
    
    # If we found a matching column, use its sample value
    if matched_column and matched_column_data:
        # Get a random sample value
        sample_value = random.choice(matched_column_data["sample_values"])
        
        # Check if the column has a length constraint
        if "length" in matched_column_data:
            max_length = int(matched_column_data["length"])
            # If the sample value exceeds the length, truncate it or get another value
            if len(str(sample_value)) > max_length:
                # Try to find another sample value that fits the length constraint
                valid_samples = [s for s in matched_column_data["sample_values"] if len(str(s)) <= max_length]
                if valid_samples:
                    sample_value = random.choice(valid_samples)
                else:
                    # If no valid sample found, truncate the value
                    sample_value = str(sample_value)[:max_length]
        
        return sample_value
    
    # If no match found for the specific variable, try to find any column of the same type
    # that has a length constraint if applicable
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            if col_data.get("type", "").upper() == var_type:
                if "sample_values" in col_data and col_data["sample_values"]:
                    sample_value = random.choice(col_data["sample_values"])
                    
                    # Check if the column has a length constraint
                    if "length" in col_data:
                        max_length = int(col_data["length"])
                        # If the sample value exceeds the length, truncate it or get another value
                        if len(str(sample_value)) > max_length:
                            # Try to find another sample value that fits the length constraint
                            valid_samples = [s for s in col_data["sample_values"] if len(str(s)) <= max_length]
                            if valid_samples:
                                sample_value = random.choice(valid_samples)
                            else:
                                # If no valid sample found, truncate the value
                                sample_value = str(sample_value)[:max_length]
                    
                    return sample_value
    
    # If still no match, return default value
    return default_values[var_type]

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
                    sample_value = get_sample_value(var_type, var, dictionary)
                    
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
