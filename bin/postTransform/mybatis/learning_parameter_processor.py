#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
학습형 파라미터 처리기 - 자동 추출, 매핑, 학습
"""

import re
import json
import os
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class LearningParameterProcessor:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), 'parameter_config.json')
        self.parameter_db = {}
        self.load_parameter_db()
        
    def load_parameter_db(self):
        """파라미터 DB 로드"""
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.parameter_db = config.get('parameters', {})
                    logger.info(f"파라미터 DB 로드: {len(self.parameter_db)}개")
            else:
                logger.info("파라미터 DB 파일이 없음, 새로 생성")
                self.parameter_db = {}
        except Exception as e:
            logger.error(f"파라미터 DB 로드 실패: {e}")
            self.parameter_db = {}
    
    def save_parameter_db(self):
        """파라미터 DB 저장"""
        
        try:
            config = {
                'comment': 'MyBatis 파라미터 학습 DB - 자동 생성/업데이트',
                'parameters': self.parameter_db,
                'last_updated': str(time.time())
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
            logger.info(f"파라미터 DB 저장: {len(self.parameter_db)}개")
            
        except Exception as e:
            logger.error(f"파라미터 DB 저장 실패: {e}")
    
    def extract_parameters_with_types(self, content: str) -> Dict[str, Dict]:
        """파라미터와 타입 정보 추출"""
        
        parameters = {}
        
        # 1. #{param,jdbcType=VARCHAR} 형태 추출
        jdbc_pattern = r'#\{([^}]+)\}'
        matches = re.findall(jdbc_pattern, content, re.IGNORECASE)
        
        for match in matches:
            param_info = self._parse_parameter_expression(match)
            if param_info:
                param_name = param_info['name']
                parameters[param_name] = param_info
        
        # 2. ${param} 형태 추출 (리터럴 치환용)
        literal_pattern = r'\$\{([^}]+)\}'
        matches = re.findall(literal_pattern, content, re.IGNORECASE)
        
        for match in matches:
            param_name = match.strip()
            if param_name not in parameters:
                parameters[param_name] = {
                    'name': param_name,
                    'jdbc_type': None,
                    'is_literal': True,
                    'usage_context': 'literal'
                }
        
        # 3. test 조건에서 파라미터 추출
        test_params = self._extract_test_parameters(content)
        for param_name in test_params:
            if param_name not in parameters:
                parameters[param_name] = {
                    'name': param_name,
                    'jdbc_type': None,
                    'is_literal': False,
                    'usage_context': 'condition'
                }
        
        # 4. foreach collection 파라미터
        foreach_matches = re.findall(r'<foreach[^>]*collection="([^"]+)"', content, re.IGNORECASE)
        for collection in foreach_matches:
            if collection not in parameters:
                parameters[collection] = {
                    'name': collection,
                    'jdbc_type': None,
                    'is_literal': False,
                    'usage_context': 'collection'
                }
        
        return parameters
    
    def _parse_parameter_expression(self, param_expr: str) -> Optional[Dict]:
        """파라미터 표현식 파싱"""
        
        param_expr = param_expr.strip()
        parts = [p.strip() for p in param_expr.split(',')]
        
        if not parts:
            return None
            
        param_name = parts[0]
        jdbc_type = None
        type_handler = None
        
        # jdbcType 추출
        for part in parts[1:]:
            if part.lower().startswith('jdbctype='):
                jdbc_type = part.split('=')[1].strip()
            elif part.lower().startswith('typehandler='):
                type_handler = part.split('=')[1].strip()
        
        return {
            'name': param_name,
            'jdbc_type': jdbc_type,
            'type_handler': type_handler,
            'is_literal': False,
            'usage_context': 'parameter'
        }
    
    def _extract_test_parameters(self, content: str) -> List[str]:
        """test 조건에서 파라미터 추출"""
        
        parameters = []
        
        test_patterns = [
            r'test="([^"]*)"',
            r"test='([^']*)'"
        ]
        
        for pattern in test_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # 조건식에서 변수명 추출
                var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
                vars_in_condition = re.findall(var_pattern, match)
                
                reserved_words = {
                    'null', 'and', 'or', 'not', 'true', 'false', 'eq', 'ne', 
                    'lt', 'le', 'gt', 'ge', 'contains', 'size', 'empty', 'length'
                }
                
                for var in vars_in_condition:
                    if var.lower() not in reserved_words:
                        parameters.append(var)
        
        return parameters
    
    def learn_and_get_default_value(self, param_name: str, param_info: Dict) -> Any:
        """파라미터 학습 및 기본값 결정"""
        
        # 1. 기존 DB에 있는지 확인
        if param_name in self.parameter_db:
            existing = self.parameter_db[param_name]
            # jdbcType 정보가 새로 들어왔으면 업데이트
            if param_info.get('jdbc_type') and not existing.get('jdbc_type'):
                existing['jdbc_type'] = param_info['jdbc_type']
                existing['learned_count'] = existing.get('learned_count', 0) + 1
            return existing['default_value']
        
        # 2. 새로운 파라미터 - 타입 추정 및 학습
        default_value = self._infer_default_value(param_name, param_info)
        
        # 3. DB에 추가
        self.parameter_db[param_name] = {
            'name': param_name,
            'default_value': default_value,
            'jdbc_type': param_info.get('jdbc_type'),
            'usage_context': param_info.get('usage_context', 'parameter'),
            'is_literal': param_info.get('is_literal', False),
            'inferred_type': self._infer_type_category(param_name, param_info),
            'learned_count': 1,
            'first_seen': str(time.time())
        }
        
        logger.info(f"새 파라미터 학습: {param_name} = {default_value} (타입: {param_info.get('jdbc_type', 'INFERRED')})")
        
        return default_value
    
    def _infer_default_value(self, param_name: str, param_info: Dict) -> Any:
        """파라미터 기본값 추정"""
        
        if param_info is None:
            param_info = {}
            
        param_lower = param_name.lower()
        jdbc_type = param_info.get('jdbc_type', '').upper() if param_info.get('jdbc_type') else ''
        usage_context = param_info.get('usage_context', '')
        is_literal = param_info.get('is_literal', False)
        
        # 1. jdbcType 기반 추정
        if jdbc_type:
            if jdbc_type in ['INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'NUMERIC', 'DECIMAL']:
                if 'seqno' in param_lower or 'id' in param_lower:
                    return 1
                else:
                    return 0
            elif jdbc_type in ['VARCHAR', 'CHAR', 'TEXT', 'LONGVARCHAR']:
                if 'cd' in param_lower or 'code' in param_lower:
                    return 'TEST'
                elif param_lower.endswith('yn') or param_lower.endswith('flag'):
                    return 'Y'
                else:
                    return 'DEFAULT'
            elif jdbc_type in ['TIMESTAMP', 'DATETIME', 'DATE']:
                if 'dtm' in param_lower:
                    return '20240101000000'
                else:
                    return '20240101'
        
        # 2. 사용 컨텍스트 기반 추정
        if is_literal and ('order' in param_lower or 'sort' in param_lower):
            return '1'  # ORDER BY용
        
        if usage_context == 'collection':
            return ['TEST1', 'TEST2']
        
        # 3. 파라미터명 패턴 기반 추정
        if 'seqno' in param_lower or param_lower.endswith('id') or param_lower.endswith('no'):
            return 1
        elif param_lower.endswith('cnt') or param_lower.endswith('amt'):
            return 0
        elif param_lower.endswith('cd') or param_lower.endswith('code'):
            return 'TEST'
        elif param_lower.endswith('yn') or param_lower.endswith('flag'):
            return 'Y'
        elif 'dtm' in param_lower:
            return '20240101000000'
        elif 'date' in param_lower:
            return '20240101'
        elif param_lower.startswith('list'):
            return ['TEST1', 'TEST2']
        elif 'order' in param_lower or 'sort' in param_lower:
            return '1'
        
        # 4. 기본값
        return 'DEFAULT'
    
    def _infer_type_category(self, param_name: str, param_info: Dict) -> str:
        """타입 카테고리 추정"""
        
        if param_info is None:
            param_info = {}
            
        jdbc_type = param_info.get('jdbc_type', '').upper() if param_info.get('jdbc_type') else ''
        
        if jdbc_type:
            if jdbc_type in ['INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'NUMERIC', 'DECIMAL']:
                return 'NUMBER'
            elif jdbc_type in ['VARCHAR', 'CHAR', 'TEXT', 'LONGVARCHAR']:
                return 'STRING'
            elif jdbc_type in ['TIMESTAMP', 'DATETIME', 'DATE']:
                return 'DATE'
            else:
                return 'OTHER'
        
        # jdbcType이 없으면 파라미터명으로 추정
        param_lower = param_name.lower()
        
        if any(keyword in param_lower for keyword in ['seqno', 'id', 'no', 'cnt', 'amt']):
            return 'NUMBER'
        elif any(keyword in param_lower for keyword in ['dtm', 'date', 'dt']):
            return 'DATE'
        elif param_lower.startswith('list'):
            return 'LIST'
        else:
            return 'STRING'
    
    def process_content_with_learning(self, content: str) -> str:
        """학습하면서 파라미터 처리"""
        
        # 1. 파라미터 추출 및 학습
        extracted_params = self.extract_parameters_with_types(content)
        
        param_values = {}
        new_params_count = 0
        
        for param_name, param_info in extracted_params.items():
            if param_name not in self.parameter_db:
                new_params_count += 1
                
            default_value = self.learn_and_get_default_value(param_name, param_info)
            param_values[param_name] = default_value
        
        if new_params_count > 0:
            logger.info(f"새로 학습된 파라미터: {new_params_count}개")
            self.save_parameter_db()  # 새로운 파라미터가 있으면 저장
        
        # 2. 파라미터 치환
        result = self._substitute_parameters(content, param_values)
        
        return result
    
    def _substitute_parameters(self, content: str, param_values: Dict) -> str:
        """파라미터 치환 - SQL 구조 보존 개선"""
        
        result = content
        
        # foreach 처리 먼저
        result = self._process_foreach(result, param_values)
        
        # 파라미터별 치환 - 더 안전한 방식
        for param, value in param_values.items():
            # #{param,jdbcType=VARCHAR} 패턴
            pattern1 = rf'#\{{{re.escape(param)}(?:,[^}}]*)?\}}'
            
            def replace_hash_param(match):
                if isinstance(value, str):
                    if value.isdigit():
                        return value
                    else:
                        return f"'{value}'"
                elif isinstance(value, (int, float)):
                    return str(value)
                else:
                    return f"'{str(value)}'"
            
            result = re.sub(pattern1, replace_hash_param, result)
            
            # ${param} 패턴 - 리터럴 치환
            pattern2 = rf'\${{{re.escape(param)}(?:,[^}}]*)?\}}'
            
            def replace_dollar_param(match):
                # 컨텍스트 확인
                start_pos = max(0, match.start() - 20)
                end_pos = min(len(result), match.end() + 20)
                context = result[start_pos:end_pos]
                
                if isinstance(value, str):
                    if param.lower() == 'orderby':
                        if value == 'DEFAULT':
                            return '1'  # ORDER BY 절에서는 컬럼 번호
                        else:
                            return value
                    else:
                        return str(value)
                else:
                    return str(value)
            
            result = re.sub(pattern2, replace_dollar_param, result)
        
        return result
    
    def _process_foreach(self, content: str, param_values: Dict) -> str:
        """foreach 처리"""
        
        def replace_foreach(match):
            full_tag = match.group(0)
            
            # 속성 추출
            collection_match = re.search(r'collection="([^"]+)"', full_tag)
            item_match = re.search(r'item="([^"]+)"', full_tag)
            separator_match = re.search(r'separator="([^"]+)"', full_tag)
            open_match = re.search(r'open="([^"]+)"', full_tag)
            close_match = re.search(r'close="([^"]+)"', full_tag)
            
            if not collection_match or not item_match:
                return "('DEFAULT')"
                
            collection = collection_match.group(1)
            item = item_match.group(1)
            separator = separator_match.group(1) if separator_match else ","
            open_char = open_match.group(1) if open_match else "("
            close_char = close_match.group(1) if close_match else ")"
            
            # 내용 추출
            content_match = re.search(r'<foreach[^>]*>(.*?)</foreach>', full_tag, re.DOTALL)
            if not content_match:
                return f"{open_char}'DEFAULT'{close_char}"
                
            inner_content = content_match.group(1).strip()
            
            # 컬렉션 값 확인
            if collection in param_values:
                collection_value = param_values[collection]
                if isinstance(collection_value, list) and len(collection_value) > 0:
                    items = []
                    for value in collection_value[:3]:  # 최대 3개
                        item_content = inner_content
                        # item 파라미터 치환
                        item_content = re.sub(rf'#\{{{re.escape(item)}[^}}]*\}}', f"'{value}'", item_content)
                        item_content = re.sub(rf'\${{{re.escape(item)}[^}}]*\}}', str(value), item_content)
                        items.append(item_content.strip())
                    return f"{open_char}{separator.join(items)}{close_char}"
            
            # 기본값 처리
            default_items = []
            for i in range(3):
                item_content = inner_content
                item_content = re.sub(rf'#\{{{re.escape(item)}[^}}]*\}}', "'DEFAULT'", item_content)
                item_content = re.sub(rf'\${{{re.escape(item)}[^}}]*\}}', "DEFAULT", item_content)
                default_items.append(item_content.strip())
                
            return f"{open_char}{separator.join(default_items)}{close_char}"
        
        foreach_pattern = r'<foreach[^>]*>.*?</foreach>'
        return re.sub(foreach_pattern, replace_foreach, content, flags=re.DOTALL | re.IGNORECASE)

# time 모듈 import 추가
import time
