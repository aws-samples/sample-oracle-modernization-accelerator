#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#############################################################################
# Script: DB06.BindSampler.py
# Description: This script analyzes SQL files to identify bind variables and
#              assigns appropriate sample values based on variable names and
#              a dictionary of database column values.
#
# Functionality:
# - Scans SQL files in the 'src_sql_extract' directory
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
from collections import defaultdict

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
        'DB_ASSESSMENTS_FOLDER',
        'BIND_SAMPLING_MODE'
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
            if var == 'BIND_SAMPLING_MODE':
                print(f"✓ {var}: {value}")
                if value.lower() in ['relational', 'relation', 'smart']:
                    print("    -> 관계형 샘플링 모드 활성화")
                else:
                    print("    -> 기본 샘플링 모드")
            else:
                print(f"✓ {var}: {value}")
        else:
            if var == 'BIND_SAMPLING_MODE':
                print(f"- {var}: 설정되지 않음 (기본값: basic)")
                print("    사용 가능한 값: basic (기본), relational (관계형)")
            else:
                print(f"- {var}: 설정되지 않음 (선택사항)")
    
    print("\n환경 변수 확인 완료.")
    print("=" * 60)

# Configuration - 환경변수 기반으로 경로 설정
def get_paths():
    """환경변수를 기반으로 경로들을 반환합니다."""
    test_folder = os.environ.get('TEST_FOLDER', os.getcwd())
    
    return {
        'sql_dir': os.path.join(test_folder, 'src_sql_extract'),
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
        print("먼저 XMLToSQL.py를 실행하여 소스 SQL 파일들을 생성하세요.")
        return []
    
    sql_files = [os.path.join(sql_dir, f) for f in os.listdir(sql_dir) if f.endswith('.sql')]
    print(f"소스 SQL 파일 디렉토리: {sql_dir}")
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

class SQLRelationshipAnalyzer:
    """SQL 문을 분석하여 테이블 관계와 바인드 변수 연관성을 분석하는 클래스"""
    
    def __init__(self):
        self.table_patterns = [
            r'FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s*([A-Za-z_][A-Za-z0-9_]*)?',
            r'JOIN\s+([A-Za-z_][A-Za-z0-9_]*)\s*([A-Za-z_][A-Za-z0-9_]*)?'
        ]
        
    def analyze_sql_structure(self, sql_content):
        """
        SQL 구조를 분석하여 테이블, JOIN, WHERE 조건 정보를 추출합니다.
        
        Args:
            sql_content (str): 분석할 SQL 문
            
        Returns:
            dict: 분석 결과 (tables, joins, conditions)
        """
        sql_upper = sql_content.upper()
        
        # 테이블과 alias 추출
        tables = self._extract_tables(sql_upper)
        
        # JOIN 조건 추출
        joins = self._extract_join_conditions(sql_upper)
        
        # WHERE 절 조건 추출
        conditions = self._extract_where_conditions(sql_upper)
        
        return {
            'tables': tables,
            'joins': joins,
            'conditions': conditions,
            'primary_table': self._identify_primary_table(tables, joins)
        }
    
    def _extract_tables(self, sql_upper):
        """테이블명과 alias를 추출합니다."""
        tables = {}
        
        for pattern in self.table_patterns:
            matches = re.findall(pattern, sql_upper, re.IGNORECASE)
            for match in matches:
                table_name = match[0].strip()
                alias = match[1].strip() if len(match) > 1 and match[1].strip() else table_name
                tables[alias] = table_name
                
        return tables
    
    def _extract_join_conditions(self, sql_upper):
        """JOIN 조건을 추출합니다."""
        joins = []
        
        # ON 절에서 조건 추출
        join_pattern = r'JOIN\s+([A-Za-z_][A-Za-z0-9_]*)\s*([A-Za-z_][A-Za-z0-9_]*)?\s+ON\s+([^)]+?)(?=\s+(?:JOIN|WHERE|GROUP|ORDER|HAVING|$))'
        matches = re.findall(join_pattern, sql_upper, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            table_name = match[0].strip()
            alias = match[1].strip() if match[1].strip() else table_name
            condition = match[2].strip()
            
            # 조건에서 컬럼 관계 추출
            column_relations = self._parse_join_condition(condition)
            
            joins.append({
                'table': table_name,
                'alias': alias,
                'condition': condition,
                'column_relations': column_relations
            })
            
        return joins
    
    def _parse_join_condition(self, condition):
        """JOIN 조건을 파싱하여 컬럼 관계를 추출합니다."""
        relations = []
        
        # 등호(=) 조건 추출: table1.col1 = table2.col2
        equality_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)'
        matches = re.findall(equality_pattern, condition)
        
        for match in matches:
            relations.append({
                'left_table': match[0],
                'left_column': match[1],
                'right_table': match[2],
                'right_column': match[3],
                'operator': '='
            })
            
        return relations
    
    def _extract_where_conditions(self, sql_upper):
        """WHERE 절의 조건을 추출합니다."""
        conditions = []
        
        # WHERE 절 전체 추출
        where_match = re.search(r'WHERE\s+(.+?)(?=\s+(?:GROUP|ORDER|HAVING|$))', sql_upper, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return conditions
            
        where_clause = where_match.group(1).strip()
        
        # 바인드 변수를 포함하는 조건 추출
        bind_conditions = re.findall(r'([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)\s*(=|!=|<>|<|>|<=|>=|LIKE|IN)\s*(:[A-Za-z_][A-Za-z0-9_]*|#{[A-Za-z_][A-Za-z0-9_]*})', where_clause, re.IGNORECASE)
        
        for condition in bind_conditions:
            column = condition[0].strip()
            operator = condition[1].strip()
            bind_var = condition[2].strip()
            
            # 바인드 변수 정규화 (: 또는 #{} 제거)
            clean_bind_var = re.sub(r'[:#{}]', '', bind_var)
            
            conditions.append({
                'column': column,
                'operator': operator,
                'bind_variable': clean_bind_var,
                'raw_condition': f"{column} {operator} {bind_var}"
            })
            
        return conditions
    
    def _identify_primary_table(self, tables, joins):
        """주요 테이블을 식별합니다 (FROM 절의 첫 번째 테이블)."""
        # FROM 절에서 첫 번째로 나오는 테이블을 주요 테이블로 간주
        for alias, table_name in tables.items():
            return {'alias': alias, 'table': table_name}
        return None
    
    def build_variable_dependency_graph(self, bind_vars, sql_analysis, dictionary):
        """
        바인드 변수 간 의존성 그래프를 구성합니다.
        
        Args:
            bind_vars (list): 바인드 변수 목록
            sql_analysis (dict): SQL 분석 결과
            dictionary (dict): 데이터베이스 딕셔너리
            
        Returns:
            dict: 변수 그룹과 의존성 정보
        """
        # 바인드 변수를 테이블별로 그룹화
        variable_groups = defaultdict(list)
        
        # WHERE 조건에서 바인드 변수와 컬럼 매핑
        for condition in sql_analysis['conditions']:
            bind_var = condition['bind_variable']
            column = condition['column']
            
            if bind_var in bind_vars:
                # 컬럼이 어느 테이블에 속하는지 확인
                table_info = self._resolve_column_table(column, sql_analysis['tables'], dictionary)
                if table_info:
                    variable_groups[table_info['table']].append({
                        'variable': bind_var,
                        'column': table_info['column'],
                        'table': table_info['table'],
                        'condition': condition
                    })
        
        # JOIN 조건을 통한 테이블 간 관계 정의
        table_relationships = self._build_table_relationships(sql_analysis['joins'])
        
        return {
            'variable_groups': dict(variable_groups),
            'table_relationships': table_relationships,
            'primary_table': sql_analysis['primary_table']
        }
    
    def _resolve_column_table(self, column, tables, dictionary):
        """컬럼이 어느 테이블에 속하는지 확인합니다."""
        # 컬럼이 이미 table.column 형태인지 확인
        if '.' in column:
            parts = column.split('.')
            if len(parts) == 2:
                alias_or_table = parts[0]
                column_name = parts[1]
                
                # alias인지 실제 테이블명인지 확인
                if alias_or_table in tables:
                    return {
                        'table': tables[alias_or_table],
                        'column': column_name,
                        'alias': alias_or_table
                    }
        else:
            # alias 없이 컬럼명만 있는 경우, 딕셔너리에서 해당 컬럼을 가진 테이블 찾기
            for schema_name, schema_data in dictionary.items():
                for table_name, table_data in schema_data.items():
                    if 'columns' in table_data and column in table_data['columns']:
                        # SQL에서 사용된 테이블인지 확인
                        for alias, sql_table in tables.items():
                            if sql_table == table_name:
                                return {
                                    'table': table_name,
                                    'column': column,
                                    'alias': alias
                                }
        
        return None
    
    def _build_table_relationships(self, joins):
        """JOIN 조건을 통해 테이블 간 관계를 구성합니다."""
        relationships = []
        
        for join in joins:
            for relation in join['column_relations']:
                relationships.append({
                    'left_table': relation['left_table'],
                    'left_column': relation['left_column'],
                    'right_table': relation['right_table'],
                    'right_column': relation['right_column'],
                    'relationship_type': 'join'
                })
                
        return relationships


class RelationalBindSampler:
    """
    관계형 데이터베이스의 제약조건을 고려하여 일관성 있는 바인드 변수 샘플 값을 생성하는 클래스
    """
    
    def __init__(self, dictionary):
        """
        Args:
            dictionary (dict): 데이터베이스 딕셔너리 (제약조건 정보 포함)
        """
        self.dictionary = dictionary
        self.analyzer = SQLRelationshipAnalyzer()
        self.sampled_values = {}  # 이미 샘플링된 값들을 캐시
        
    def generate_consistent_samples(self, bind_vars, sql_content):
        """
        SQL 구조와 제약조건을 분석하여 일관성 있는 바인드 변수 샘플을 생성합니다.
        
        Args:
            bind_vars (list): 바인드 변수 목록
            sql_content (str): SQL 문 내용
            
        Returns:
            list: 일관성 있는 샘플 값 목록
        """
        print(f"관계형 샘플링 시작: {len(bind_vars)}개 변수")
        
        # SQL 구조 분석
        sql_analysis = self.analyzer.analyze_sql_structure(sql_content)
        print(f"SQL 분석 완료: {len(sql_analysis['tables'])}개 테이블, {len(sql_analysis['conditions'])}개 조건")
        
        # 바인드 변수 의존성 그래프 생성
        dependency_graph = self.analyzer.build_variable_dependency_graph(
            bind_vars, sql_analysis, self.dictionary
        )
        
        # 관계형 샘플링 수행
        samples = self._perform_relational_sampling(bind_vars, dependency_graph, sql_content)
        
        print(f"관계형 샘플링 완료: {len(samples)}개 샘플 생성")
        return samples
        
    def _perform_relational_sampling(self, bind_vars, dependency_graph, sql_content):
        """실제 관계형 샘플링을 수행합니다."""
        samples = []
        variable_groups = dependency_graph['variable_groups']
        table_relationships = dependency_graph['table_relationships']
        
        # 처리된 변수 추적
        processed_vars = set()
        
        # 1. 주 테이블부터 시작하여 샘플링
        primary_table = dependency_graph.get('primary_table')
        if primary_table:
            primary_table_name = primary_table['table']
            if primary_table_name in variable_groups:
                print(f"주 테이블 {primary_table_name} 샘플링 시작")
                table_samples = self._sample_table_variables(
                    variable_groups[primary_table_name], 
                    primary_table_name,
                    sql_content
                )
                samples.extend(table_samples)
                processed_vars.update(var['variable'] for var in table_samples)
        
        # 2. 관계가 있는 다른 테이블들 순차 처리
        for relationship in table_relationships:
            left_table = relationship['left_table']
            right_table = relationship['right_table']
            
            # 아직 처리되지 않은 테이블의 변수들을 처리
            for table_name in [left_table, right_table]:
                if table_name in variable_groups:
                    table_vars = variable_groups[table_name]
                    unprocessed_vars = [
                        var_info for var_info in table_vars 
                        if var_info['variable'] not in processed_vars
                    ]
                    
                    if unprocessed_vars:
                        print(f"관련 테이블 {table_name} 샘플링 시작")
                        table_samples = self._sample_related_table_variables(
                            unprocessed_vars, 
                            table_name,
                            relationship,
                            sql_content
                        )
                        samples.extend(table_samples)
                        processed_vars.update(var['variable'] for var in table_samples)
        
        # 3. 독립적인 변수들 처리 (어떤 테이블에도 매핑되지 않은 변수들)
        for var in bind_vars:
            if var not in processed_vars:
                print(f"독립 변수 {var} 샘플링")
                var_type = guess_variable_type(var, self.dictionary)
                sample_value = get_sample_value(var_type, var, self.dictionary, sql_content)
                
                samples.append({
                    "variable": var,
                    "type": var_type,
                    "sample_value": sample_value
                })
                processed_vars.add(var)
        
        return samples
        
    def _sample_table_variables(self, table_vars, table_name, sql_content):
        """특정 테이블의 변수들을 일관성 있게 샘플링합니다."""
        samples = []
        
        # 해당 테이블에서 하나의 일관성 있는 레코드를 선택
        consistent_record = self._get_consistent_record(table_name)
        
        for var_info in table_vars:
            var = var_info['variable']
            column = var_info['column']
            
            # 제약조건 정보 확인
            constraints = self._get_column_constraints(table_name, column)
            
            # 일관성 있는 값 생성
            sample_value = self._generate_consistent_value(
                var, column, table_name, constraints, consistent_record, sql_content
            )
            
            var_type = guess_variable_type(var, self.dictionary)
            samples.append({
                "variable": var,
                "type": var_type,
                "sample_value": sample_value
            })
            
            # 생성된 값을 캐시에 저장
            self.sampled_values[f"{table_name}.{column}"] = sample_value
            
        return samples
        
    def _sample_related_table_variables(self, table_vars, table_name, relationship, sql_content):
        """관련 테이블의 변수들을 참조 무결성을 고려하여 샘플링합니다."""
        samples = []
        
        for var_info in table_vars:
            var = var_info['variable']
            column = var_info['column']
            
            # 관계에 따른 일관성 있는 값 생성
            sample_value = self._generate_related_value(
                var, column, table_name, relationship, sql_content
            )
            
            var_type = guess_variable_type(var, self.dictionary)
            samples.append({
                "variable": var,
                "type": var_type,
                "sample_value": sample_value
            })
            
            # 생성된 값을 캐시에 저장
            self.sampled_values[f"{table_name}.{column}"] = sample_value
            
        return samples
        
    def _get_consistent_record(self, table_name):
        """테이블에서 일관성 있는 하나의 레코드를 선택합니다."""
        # 딕셔너리에서 해당 테이블의 데이터 찾기
        for schema_name, schema_data in self.dictionary.items():
            if table_name in schema_data:
                table_data = schema_data[table_name]
                if 'columns' in table_data:
                    # 모든 컬럼에서 첫 번째 샘플 값을 사용 (일관성 보장)
                    consistent_record = {}
                    for col_name, col_data in table_data['columns'].items():
                        if 'sample_values' in col_data and col_data['sample_values']:
                            consistent_record[col_name] = col_data['sample_values'][0]
                    return consistent_record
        return {}
        
    def _get_column_constraints(self, table_name, column_name):
        """컬럼의 제약조건 정보를 반환합니다."""
        for schema_name, schema_data in self.dictionary.items():
            if table_name in schema_data:
                table_data = schema_data[table_name]
                if 'constraints' in table_data:
                    # 해당 컬럼과 관련된 제약조건 찾기
                    column_constraints = []
                    for constraint in table_data['constraints']:
                        if column_name in constraint.get('columns', []):
                            column_constraints.append(constraint)
                    return column_constraints
        return []
        
    def _generate_consistent_value(self, var, column, table_name, constraints, consistent_record, sql_content):
        """제약조건을 고려하여 일관성 있는 값을 생성합니다."""
        # 이미 샘플링된 값이 있는지 확인
        cache_key = f"{table_name}.{column}"
        if cache_key in self.sampled_values:
            return self.sampled_values[cache_key]
            
        # 일관성 있는 레코드에서 값 가져오기
        if column in consistent_record:
            value = consistent_record[column]
            
            # 제약조건에 따른 값 조정
            for constraint in constraints:
                if constraint['constraint_type'] == 'P':  # Primary Key
                    # PK는 고유해야 하므로 약간의 변형 추가
                    if isinstance(value, (int, float)):
                        value = int(value) + 1  # 숫자는 1 증가
                    elif isinstance(value, str) and value.isdigit():
                        value = str(int(value) + 1)
                        
            return value
            
        # 일관성 있는 레코드에서 값을 찾을 수 없는 경우 기본 방법 사용
        var_type = guess_variable_type(var, self.dictionary)
        return get_sample_value(var_type, var, self.dictionary, sql_content)
        
    def _generate_related_value(self, var, column, table_name, relationship, sql_content):
        """관계에 따른 일관성 있는 값을 생성합니다."""
        # 관계의 참조 컬럼에서 이미 생성된 값 찾기
        left_key = f"{relationship['left_table']}.{relationship['left_column']}"
        right_key = f"{relationship['right_table']}.{relationship['right_column']}"
        
        current_key = f"{table_name}.{column}"
        
        # FK 관계인 경우 참조되는 PK 값 사용
        if current_key == right_key and left_key in self.sampled_values:
            return self.sampled_values[left_key]
        elif current_key == left_key and right_key in self.sampled_values:
            return self.sampled_values[right_key]
            
        # 관련 값을 찾을 수 없는 경우 기본 방법 사용
        var_type = guess_variable_type(var, self.dictionary)
        return get_sample_value(var_type, var, self.dictionary, sql_content)


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

def get_sampling_mode():
    """환경변수를 통해 샘플링 모드를 결정합니다."""
    mode = os.environ.get('BIND_SAMPLING_MODE', 'basic').lower()
    if mode in ['relational', 'relation', 'smart']:
        return 'relational'
    else:
        return 'basic'

def main():
    # 경로 설정
    paths = get_paths()
    
    print(f"소스 SQL 파일 디렉토리: {paths['sql_dir']}")
    print(f"딕셔너리 파일: {paths['dictionary_file']}")
    print(f"출력 디렉토리: {paths['output_dir']}")
    
    # 샘플링 모드 확인
    sampling_mode = get_sampling_mode()
    print(f"샘플링 모드: {sampling_mode.upper()}")
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
    
    # 관계형 샘플러 초기화 (필요한 경우)
    relational_sampler = None
    if sampling_mode == 'relational':
        try:
            relational_sampler = RelationalBindSampler(dictionary)
            print("관계형 바인드 샘플러 초기화 완료")
        except Exception as e:
            print(f"관계형 샘플러 초기화 실패: {str(e)}")
            print("기본 샘플링 모드로 전환합니다.")
            sampling_mode = 'basic'
    
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
                print(f"처리 중: {file_name} ({len(unique_bind_vars)}개 바인드 변수)")
                
                # 샘플링 모드에 따른 처리
                if sampling_mode == 'relational' and relational_sampler:
                    try:
                        # 관계형 샘플링 수행
                        file_samples = relational_sampler.generate_consistent_samples(
                            unique_bind_vars, sql_content
                        )
                        results[file_name] = file_samples
                        
                        # 결과 출력
                        for sample in file_samples:
                            print(f"  - {sample['variable']}: {sample['type']} = {sample['sample_value']} (관계형)")
                            
                    except Exception as e:
                        print(f"관계형 샘플링 실패: {str(e)}")
                        print("기본 샘플링으로 폴백합니다.")
                        
                        # 폴백: 기본 샘플링
                        file_samples = []
                        for var in unique_bind_vars:
                            var_type = guess_variable_type(var, dictionary)
                            sample_value = get_sample_value(var_type, var, dictionary, sql_content)
                            
                            file_samples.append({
                                "variable": var,
                                "type": var_type,
                                "sample_value": sample_value
                            })
                            
                            print(f"  - {var}: {var_type} = {sample_value} (기본)")
                        
                        results[file_name] = file_samples
                else:
                    # 기본 샘플링
                    file_samples = []
                    for var in unique_bind_vars:
                        var_type = guess_variable_type(var, dictionary)
                        sample_value = get_sample_value(var_type, var, dictionary, sql_content)
                        
                        file_samples.append({
                            "variable": var,
                            "type": var_type,
                            "sample_value": sample_value
                        })
                        
                        print(f"  - {var}: {var_type} = {sample_value}")
                    
                    results[file_name] = file_samples
    
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
    print(f"- 샘플링 모드: {sampling_mode.upper()}")
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
