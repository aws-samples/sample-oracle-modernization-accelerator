#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
새로운 통합 바인드 변수 처리 시스템
기존 BindSampler.py + BindMapper.py 기능을 통합하여 개선된 매핑 시스템 적용
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import sqlparse
from difflib import SequenceMatcher

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BindVariable:
    name: str
    data_type: str
    sample_value: Any
    confidence: str
    mapping_method: str
    matched_column: Optional[str] = None

def get_paths():
    """환경변수를 기반으로 경로들을 반환합니다."""
    test_folder = os.environ.get('TEST_FOLDER', os.getcwd())
    
    return {
        'sql_dir': os.path.join(test_folder, 'orcl_sql_extract'),
        'pg_sql_dir': os.path.join(test_folder, 'pg_sql_extract'),
        'dictionary_file': os.path.join(test_folder, 'dictionary', 'all_dictionary.json'),
        'sampler_dir': os.path.join(test_folder, 'sampler'),
        'orcl_done_dir': os.path.join(test_folder, 'orcl_sql_done'),
        'pg_done_dir': os.path.join(test_folder, 'pg_sql_done'),
        'final_mappings': '/home/ec2-user/workspace/sample-oracle-modernization-accelerator/jihook/bind_variable_mappings.json'
    }

class NewBindProcessor:
    def __init__(self):
        self.paths = get_paths()
        self.dictionary = self.load_dictionary()
        self.final_mappings = self.load_final_mappings()
        self.abbreviations = self.load_abbreviations()
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """추가 설정 로드"""
        config_file = os.path.join(os.path.dirname(__file__), 'bind_config.json')
        default_config = {
            'similarity_threshold': {'value': 0.7},
            'custom_mappings': {}
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                    default_config.update(custom_config)
                    logger.info(f"추가 설정 로드: {config_file}")
            except Exception as e:
                logger.warning(f"설정 파일 로드 실패: {e}")
        
        return default_config
        
    def load_dictionary(self) -> Dict:
        """딕셔너리 파일 로드"""
        try:
            with open(self.paths['dictionary_file'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"딕셔너리 로드 실패: {e}")
            return {}
    
    def load_final_mappings(self) -> Dict:
        """최종 바인드 변수 매핑 파일 로드"""
        try:
            with open(self.paths['final_mappings'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"최종 매핑 파일 로드 실패: {e}")
            return {}
    
    def load_abbreviations(self) -> Dict[str, str]:
        """약어 사전 로드 (기본값 + 외부 설정 파일)"""
        # 기본 약어 사전
        default_abbreviations = {
            'Cd': 'CODE', 'Nm': 'NAME', 'No': 'NUMBER', 'Id': 'ID',
            'Dt': 'DATE', 'Tm': 'TIME', 'Yn': 'YN', 'Seq': 'SEQUENCE',
            'Cnt': 'COUNT', 'Amt': 'AMOUNT', 'Qty': 'QUANTITY',
            'Usr': 'USER', 'Emp': 'EMPLOYEE', 'Dept': 'DEPARTMENT',
            'Org': 'ORGANIZATION', 'Grp': 'GROUP', 'Mgmt': 'MANAGEMENT'
        }
        
        # 외부 설정 파일이 있으면 추가/오버라이드
        config_file = os.path.join(os.path.dirname(__file__), 'bind_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    custom_abbreviations = config.get('abbreviations', {})
                    default_abbreviations.update(custom_abbreviations)
                    logger.info(f"외부 설정 로드: {len(custom_abbreviations)}개 약어 추가")
            except Exception as e:
                logger.warning(f"외부 설정 로드 실패: {e}")
        
        return default_abbreviations
    
    def extract_bind_variables(self, sql_content: str) -> List[str]:
        """SQL에서 바인드 변수 추출"""
        # MyBatis 스타일 정리
        sql_content = re.sub(r'<[^>]+>', '', sql_content)
        
        # 바인드 변수 패턴 매칭
        patterns = [
            r'#\{([^}]+)\}',  # #{variable}
            r':([a-zA-Z][a-zA-Z0-9_]*)',  # :variable
        ]
        
        bind_vars = set()
        for pattern in patterns:
            matches = re.findall(pattern, sql_content, re.IGNORECASE)
            bind_vars.update(matches)
        
        return list(bind_vars)
    
    def get_sample_value_from_mapping(self, var_name: str) -> Optional[BindVariable]:
        """최종 매핑 또는 커스텀 매핑에서 샘플 값 가져오기"""
        # 1. 커스텀 매핑 확인
        custom_mappings = self.config.get('custom_mappings', {})
        if var_name in custom_mappings:
            custom = custom_mappings[var_name]
            return BindVariable(
                name=var_name,
                data_type=custom.get('data_type', 'VARCHAR2'),
                sample_value=custom.get('sample_value', 'CUSTOM_VALUE'),
                confidence='HIGH',
                mapping_method='CUSTOM_MAPPING',
                matched_column=f"{custom.get('table', '')}.{custom.get('column', '')}"
            )
        
        # 2. 기존 최종 매핑에서 찾기
        if var_name in self.final_mappings:
            mappings = self.final_mappings[var_name]
            if mappings:
                best_mapping = max(mappings, key=lambda x: {
                    'HIGH': 3, 'MEDIUM': 2, 'LOW': 1
                }.get(x.get('confidence', 'LOW'), 1))
                
                data_type = best_mapping.get('data_type', 'VARCHAR2')
                sample_value = self.generate_sample_value(var_name, data_type, best_mapping)
                
                return BindVariable(
                    name=var_name,
                    data_type=data_type,
                    sample_value=sample_value,
                    confidence=best_mapping.get('confidence', 'LOW'),
                    mapping_method=best_mapping.get('mapping_method', 'FINAL_MAPPING'),
                    matched_column=f"{best_mapping.get('table_name', '')}.{best_mapping.get('column_name', '')}"
                )
        
        # 3. 기본값 설정
        data_type, sample_value = self.generate_default_sample(var_name)
        return BindVariable(
            name=var_name,
            data_type=data_type,
            sample_value=sample_value,
            confidence='LOW',
            mapping_method='DEFAULT',
            matched_column=None
        )
    
    def generate_default_sample(self, var_name: str) -> tuple:
        """기본 샘플 값 생성"""
        var_lower = var_name.lower()
        
        if any(suffix in var_lower for suffix in ['dt', 'date', 'time']):
            return 'DATE', '2024-01-01'
        elif any(suffix in var_lower for suffix in ['no', 'id', 'seq', 'cnt', 'amt']):
            return 'NUMBER', 100
        elif any(suffix in var_lower for suffix in ['yn', 'flag']):
            return 'VARCHAR2', 'Y'
        elif any(suffix in var_lower for suffix in ['cd', 'code']):
            return 'VARCHAR2', 'TEST_CODE'
        elif any(suffix in var_lower for suffix in ['nm', 'name']):
            return 'VARCHAR2', 'TEST_NAME'
        else:
            return 'VARCHAR2', 'TEST_VALUE'
    
    def generate_sample_value(self, var_name: str, data_type: str, mapping: Dict) -> Any:
        """데이터 타입에 따른 샘플 값 생성"""
        table_name = mapping.get('table_name', '')
        column_name = mapping.get('column_name', '')
        
        # 딕셔너리에서 실제 값 찾기
        if table_name in self.dictionary and column_name in self.dictionary[table_name]:
            sample_values = self.dictionary[table_name][column_name]
            if sample_values and len(sample_values) > 0:
                return sample_values[0]  # 첫 번째 값 사용
        
        # 기본 샘플 값 생성
        if data_type == 'DATE':
            return '2024-01-01'
        elif data_type == 'NUMBER':
            if 'id' in var_name.lower() or 'seq' in var_name.lower():
                return 1
            elif 'cnt' in var_name.lower() or 'count' in var_name.lower():
                return 10
            else:
                return 100
        elif 'yn' in var_name.lower() or 'flag' in var_name.lower():
            return 'Y'
        else:  # VARCHAR2, CHAR, CLOB
            if 'cd' in var_name.lower() or 'code' in var_name.lower():
                return 'TEST_CODE'
            elif 'nm' in var_name.lower() or 'name' in var_name.lower():
                return 'TEST_NAME'
            else:
                return 'TEST_VALUE'
    
    def process_sql_files(self):
        """SQL 파일들을 처리하여 바인드 변수 샘플링"""
        logger.info("바인드 변수 샘플링 시작...")
        
        # 출력 디렉토리 생성
        os.makedirs(self.paths['sampler_dir'], exist_ok=True)
        
        sql_files = list(Path(self.paths['sql_dir']).glob('*.sql'))
        logger.info(f"처리할 SQL 파일 수: {len(sql_files)}")
        
        processed_count = 0
        for sql_file in sql_files:
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # 바인드 변수 추출
                bind_vars = self.extract_bind_variables(sql_content)
                
                if not bind_vars:
                    continue
                
                # 각 바인드 변수에 대한 샘플 값 생성
                sampler_data = {}
                for var_name in bind_vars:
                    bind_var = self.get_sample_value_from_mapping(var_name)
                    if bind_var:
                        sampler_data[var_name] = {
                            'value': bind_var.sample_value,
                            'type': bind_var.data_type,
                            'confidence': bind_var.confidence,
                            'method': bind_var.mapping_method,
                            'matched_column': bind_var.matched_column
                        }
                
                # JSON 파일로 저장
                output_file = Path(self.paths['sampler_dir']) / f"{sql_file.stem}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(sampler_data, f, indent=2, ensure_ascii=False)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"파일 처리 실패 {sql_file}: {e}")
        
        logger.info(f"바인드 변수 샘플링 완료: {processed_count}개 파일 처리")
    
    def replace_bind_variables(self, sql_content: str, sampler_data: Dict) -> str:
        """SQL에서 바인드 변수를 실제 값으로 치환"""
        modified_sql = sql_content
        
        # 1. ${queryId} 패턴 제거 (SQL 파일 상단의 식별자)
        # 단독으로 한 줄에 있는 ${queryId} 제거
        modified_sql = re.sub(r'^[ \t]*\$\{queryId\}[ \t]*\n?', '', modified_sql, flags=re.MULTILINE)
        
        # 2. MyBatis 스타일 태그 제거
        modified_sql = re.sub(r'<[^>]+>', '', modified_sql)
        
        # 3. 바인드 변수 치환
        for var_name, var_info in sampler_data.items():
            value = var_info['value']
            data_type = var_info['type']
            
            # 값 포맷팅
            if data_type == 'DATE':
                formatted_value = f"TO_DATE('{value}', 'YYYY-MM-DD')"
            elif data_type == 'NUMBER':
                formatted_value = str(value)
            else:
                formatted_value = f"'{value}'"
            
            # 바인드 변수 치환
            patterns = [
                (f'#{{{var_name}}}', formatted_value),
                (f':{var_name}', formatted_value)
            ]
            
            for pattern, replacement in patterns:
                modified_sql = modified_sql.replace(pattern, replacement)
        
        # 4. 불필요한 빈 줄 정리
        modified_sql = re.sub(r'\n\s*\n', '\n\n', modified_sql)
        modified_sql = modified_sql.strip()
        
        return modified_sql
    
    def process_bind_mapping(self):
        """바인드 변수 매핑 처리"""
        logger.info("바인드 변수 매핑 시작...")
        
        # 출력 디렉토리 생성
        os.makedirs(self.paths['orcl_done_dir'], exist_ok=True)
        os.makedirs(self.paths['pg_done_dir'], exist_ok=True)
        
        # Oracle SQL 파일 처리
        self.process_sql_directory(
            self.paths['sql_dir'], 
            self.paths['orcl_done_dir'], 
            'Oracle'
        )
        
        # PostgreSQL SQL 파일 처리
        self.process_sql_directory(
            self.paths['pg_sql_dir'], 
            self.paths['pg_done_dir'], 
            'PostgreSQL'
        )
        
        logger.info("바인드 변수 매핑 완료")
    
    def process_sql_directory(self, input_dir: str, output_dir: str, db_type: str):
        """특정 디렉토리의 SQL 파일들 처리"""
        if not os.path.exists(input_dir):
            logger.warning(f"디렉토리가 존재하지 않음: {input_dir}")
            return
        
        sql_files = list(Path(input_dir).glob('*.sql'))
        logger.info(f"{db_type} SQL 파일 처리: {len(sql_files)}개")
        
        for sql_file in sql_files:
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # 샘플러 데이터 로드 - PostgreSQL 파일명을 Oracle 파일명으로 변환하여 찾기
                sampler_filename = sql_file.stem
                if db_type == 'PostgreSQL':
                    # _pg-를 _orcl-로 변환하여 sampler 파일 찾기
                    sampler_filename = sampler_filename.replace('_pg-', '_orcl-')
                
                sampler_file = Path(self.paths['sampler_dir']) / f"{sampler_filename}.json"
                
                if sampler_file.exists():
                    with open(sampler_file, 'r', encoding='utf-8') as f:
                        sampler_data = json.load(f)
                    
                    # 바인드 변수 치환
                    modified_sql = self.replace_bind_variables(sql_content, sampler_data)
                    
                    # PostgreSQL용 추가 변환
                    if db_type == 'PostgreSQL':
                        modified_sql = self.convert_to_postgresql(modified_sql)
                    
                    logger.info(f"바인드 변수 치환 완료: {sql_file.name} (sampler: {sampler_filename}.json)")
                else:
                    logger.warning(f"샘플러 파일 없음: {sampler_filename}.json")
                    # 바인드 변수 치환 없이 ${queryId}만 제거
                    modified_sql = self.replace_bind_variables(sql_content, {})
                
                # 결과 파일 저장
                output_file = Path(output_dir) / sql_file.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(modified_sql)
                
            except Exception as e:
                logger.error(f"파일 처리 실패 {sql_file}: {e}")
    
    def convert_to_postgresql(self, sql_content: str) -> str:
        """Oracle SQL을 PostgreSQL용으로 변환"""
        # 기본적인 변환 규칙들
        conversions = [
            (r'TO_DATE\(([^,]+),\s*[^)]+\)', r'TO_TIMESTAMP(\1, \'YYYY-MM-DD\')'),
            (r'SYSDATE', 'CURRENT_TIMESTAMP'),
            (r'NVL\(', 'COALESCE('),
            (r'ROWNUM', 'ROW_NUMBER() OVER ()')
        ]
        
        modified_sql = sql_content
        for pattern, replacement in conversions:
            modified_sql = re.sub(pattern, replacement, modified_sql, flags=re.IGNORECASE)
        
        return modified_sql
    
    def run(self):
        """전체 프로세스 실행"""
        logger.info("새로운 바인드 변수 처리 시스템 시작")
        
        # 1. 바인드 변수 샘플링
        self.process_sql_files()
        
        # 2. 바인드 변수 매핑
        self.process_bind_mapping()
        
        logger.info("새로운 바인드 변수 처리 시스템 완료")

def main():
    processor = NewBindProcessor()
    processor.run()

if __name__ == "__main__":
    main()
