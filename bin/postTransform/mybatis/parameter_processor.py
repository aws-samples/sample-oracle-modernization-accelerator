#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyBatis 파라미터 처리기 - jdbcType 등 복잡한 표현식 지원
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class ParameterProcessor:
    def __init__(self):
        self.parameter_defaults = {}
        self.setup_comprehensive_defaults()
        
    def setup_comprehensive_defaults(self):
        """포괄적인 파라미터 기본값 설정"""
        
        # 기본 타입별 기본값
        basic_defaults = {
            # 숫자 타입
            'seqno': 1, 'id': 1, 'no': 1, 'cnt': 0, 'amt': 0, 'price': 0,
            'rowstart': 1, 'rowfinish': 10, 'targetpage': 1, 'rowsperpage': 10,
            'pnrSeqno': 1, 'pnr_seqno': 1, 'grpmastrseqno': 1, 'grpdetailseqno': 1,
            
            # 문자열 타입
            'cd': 'TEST', 'code': 'TEST', 'flag': 'Y', 'yn': 'Y', 'status': 'Y',
            'agtCd': 'SELK138', 'agt_cd': 'SELK138', 'usrId': 'testuser', 'usr_id': 'testuser',
            'summary': 'on', 'serverpaging': 'on',
            
            # 날짜/시간 타입
            'dtm': '20240101000000', 'date': '20240101', 'dt': '20240101',
            'rsvDtm': '20240101', 'depDtm': '20240101', 'arrDtm': '20240101',
            'payTl': '20240101235959', 'airTtl': '20240101235959',
            
            # 특수 케이스
            'saletype': 'B2C', 'saleFormCd': 'B2C', 'diFlag': 'D',
            'orderby': 'A.RSV_DTM DESC', 'branchFlag': 'H',
            
            # 리스트 타입
            'listAreaRouteCd': ['TEST1', 'TEST2'], 
            'listStockAirCd': ['OZ', 'KE'],
            'listChrgUsrId': ['testuser'],
            'listIds': [1, 2, 3]
        }
        
        self.parameter_defaults.update(basic_defaults)
        
        # 패턴 기반 추가 기본값
        self.pattern_defaults = [
            (r'.*seqno.*', 1),
            (r'.*_id$', 1),
            (r'.*_no$', 1),
            (r'.*_cd$', 'TEST'),
            (r'.*_flag$', 'Y'),
            (r'.*_yn$', 'Y'),
            (r'.*dtm.*', '20240101000000'),
            (r'.*date.*', '20240101'),
            (r'.*amt$', 0),
            (r'.*cnt$', 0),
            (r'list.*', ['TEST1', 'TEST2']),
        ]
        
    def extract_parameters(self, content: str) -> List[str]:
        """포괄적인 파라미터 추출"""
        
        parameters = set()
        
        # 1. 기본 MyBatis 파라미터 패턴들
        patterns = [
            r'#\{([^}]+)\}',  # #{param} 또는 #{param,jdbcType=VARCHAR}
            r'\$\{([^}]+)\}',  # ${param}
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # 복잡한 파라미터 표현식 파싱
                param_name = self._parse_parameter_expression(match)
                if param_name:
                    parameters.add(param_name)
        
        # 2. test 조건 내 파라미터
        test_patterns = [
            r'test="([^"]*)"',
            r"test='([^']*)'"
        ]
        
        for pattern in test_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # 조건식에서 파라미터 추출
                condition_params = self._extract_parameters_from_condition(match)
                parameters.update(condition_params)
        
        # 3. foreach 컬렉션 파라미터
        foreach_matches = re.findall(r'<foreach[^>]*collection="([^"]+)"', content, re.IGNORECASE)
        for match in foreach_matches:
            parameters.add(match)
            
        return list(parameters)
    
    def _parse_parameter_expression(self, param_expr: str) -> Optional[str]:
        """복잡한 파라미터 표현식 파싱"""
        
        # #{paramName,jdbcType=VARCHAR,typeHandler=...} 형태 처리
        param_expr = param_expr.strip()
        
        # 쉼표로 분리된 첫 번째 부분이 파라미터명
        parts = param_expr.split(',')
        if parts:
            param_name = parts[0].strip()
            # 점 표기법 처리 (예: user.name -> user)
            if '.' in param_name:
                param_name = param_name.split('.')[0]
            return param_name
        
        return None
    
    def _extract_parameters_from_condition(self, condition: str) -> List[str]:
        """조건식에서 파라미터 추출"""
        
        parameters = []
        
        # 일반적인 변수명 패턴 (예약어 제외)
        var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(var_pattern, condition)
        
        reserved_words = {
            'null', 'and', 'or', 'not', 'true', 'false', 'eq', 'ne', 'lt', 'le', 'gt', 'ge',
            'contains', 'size', 'empty', 'length'
        }
        
        for match in matches:
            if match.lower() not in reserved_words:
                parameters.append(match)
                
        return parameters
    
    def get_default_value(self, param_name: str) -> Any:
        """스마트 기본값 결정"""
        
        param_lower = param_name.lower()
        
        # 직접 매칭
        if param_lower in self.parameter_defaults:
            return self.parameter_defaults[param_lower]
            
        # 패턴 매칭
        for pattern, default_value in self.pattern_defaults:
            if re.match(pattern, param_lower):
                return default_value
                
        # 타입 추론 기반 기본값
        if any(keyword in param_lower for keyword in ['seqno', 'id', 'no']):
            return 1
        elif any(keyword in param_lower for keyword in ['cnt', 'amt', 'price']):
            return 0
        elif any(keyword in param_lower for keyword in ['cd', 'code']):
            return 'TEST'
        elif any(keyword in param_lower for keyword in ['flag', 'yn']):
            return 'Y'
        elif any(keyword in param_lower for keyword in ['dtm', 'date', 'dt']):
            return '20240101000000' if 'dtm' in param_lower else '20240101'
        elif param_lower.startswith('list'):
            return ['TEST1', 'TEST2']
        else:
            return 'DEFAULT'
    
    def substitute_parameters(self, content: str) -> str:
        """포괄적인 파라미터 치환"""
        
        # 1단계: 파라미터 추출
        parameters = self.extract_parameters(content)
        
        # 2단계: 기본값 설정
        param_values = {}
        for param in parameters:
            param_values[param] = self.get_default_value(param)
            
        logger.info(f"설정된 파라미터 기본값: {len(param_values)}개")
        
        # 3단계: 안전한 치환
        result = content
        
        # foreach 처리 먼저
        result = self._process_foreach(result, param_values)
        
        # 일반 파라미터 치환
        result = self._substitute_regular_parameters(result, param_values)
        
        # 4단계: 후처리
        result = self._post_process_sql(result)
        
        return result
    
    def _process_foreach(self, content: str, param_values: Dict) -> str:
        """foreach 처리"""
        
        def replace_foreach(match):
            full_tag = match.group(0)
            
            # foreach 속성 추출
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
        
        # foreach 태그 처리
        foreach_pattern = r'<foreach[^>]*>.*?</foreach>'
        result = re.sub(foreach_pattern, replace_foreach, content, flags=re.DOTALL | re.IGNORECASE)
        
        return result
    
    def _substitute_regular_parameters(self, content: str, param_values: Dict) -> str:
        """일반 파라미터 치환"""
        
        result = content
        
        # 따옴표 위치 추적
        quote_positions = self._find_quote_positions(result)
        
        # 파라미터별 치환
        for param, value in param_values.items():
            # #{param,jdbcType=VARCHAR,typeHandler=...} 패턴
            pattern1 = rf'#\{{{re.escape(param)}(?:,[^}}]*)?\}}'
            result = self._safe_parameter_replace(result, pattern1, value, quote_positions)
            
            # ${param} 패턴  
            pattern2 = rf'\${{{re.escape(param)}(?:,[^}}]*)?\}}'
            result = self._safe_parameter_replace(result, pattern2, value, quote_positions, is_literal=True)
            
        return result
    
    def _find_quote_positions(self, content: str) -> List[Tuple[int, int]]:
        """따옴표 위치 찾기"""
        
        quote_ranges = []
        i = 0
        while i < len(content):
            if content[i] in ["'", '"']:
                quote_char = content[i]
                start = i
                i += 1
                while i < len(content):
                    if content[i] == quote_char:
                        if i + 1 < len(content) and content[i + 1] == quote_char:
                            # 이스케이프된 따옴표
                            i += 2
                        else:
                            quote_ranges.append((start, i + 1))
                            break
                    i += 1
            i += 1
            
        return quote_ranges
    
    def _is_inside_quotes(self, position: int, quote_positions: List[Tuple[int, int]]) -> bool:
        """위치가 따옴표 내부인지 확인"""
        
        for start, end in quote_positions:
            if start <= position < end:
                return True
        return False
    
    def _safe_parameter_replace(self, content: str, pattern: str, value: Any, 
                               quote_positions: List[Tuple[int, int]], is_literal: bool = False) -> str:
        """안전한 파라미터 치환 - SQL 구조 보존"""
        
        def replace_func(match):
            # 매치 위치가 따옴표 내부인지 확인
            if self._is_inside_quotes(match.start(), quote_positions):
                return match.group(0)  # 치환하지 않음
            
            # 매치 전후 컨텍스트 확인
            start_pos = max(0, match.start() - 10)
            end_pos = min(len(content), match.end() + 10)
            context = content[start_pos:end_pos]
            
            # 값 타입에 따른 치환
            if isinstance(value, str):
                if is_literal:
                    # ${} 는 리터럴 치환 - 특수 케이스 처리
                    if value == 'DEFAULT':
                        # 컨텍스트에 따라 적절한 기본값 설정
                        if 'ORDER BY' in context.upper():
                            return '1'
                        elif any(op in context for op in ['=', '<>', '!=', '>', '<', 'IN', 'LIKE']):
                            return "'DEFAULT'"
                        else:
                            return value
                    return value
                else:
                    # #{} 는 값 치환 - 컨텍스트 고려
                    if isinstance(value, str) and value.isdigit():
                        return value  # 숫자 문자열은 따옴표 없이
                    elif any(op in context for op in ['=', '<>', '!=', '>', '<']):
                        # 비교 연산자 다음에는 적절한 타입으로
                        if value == 'DEFAULT':
                            return "'DEFAULT'"
                        return f"'{value}'"
                    else:
                        return f"'{value}'"
            elif isinstance(value, (int, float)):
                return str(value)
            elif isinstance(value, list):
                if len(value) == 0:
                    return "('DEFAULT')"
                else:
                    # 리스트 값들의 타입에 따라 처리
                    formatted_values = []
                    for v in value:
                        if isinstance(v, (int, float)):
                            formatted_values.append(str(v))
                        else:
                            formatted_values.append(f"'{v}'")
                    return f"({','.join(formatted_values)})"
            else:
                return f"'{str(value)}'"
                
        return re.sub(pattern, replace_func, content)
    
    def _post_process_sql(self, content: str) -> str:
        """SQL 후처리"""
        
        # XML 주석 완전 제거
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = re.sub(r'<!\[CDATA\[', '', content)
        content = re.sub(r'\]\]>', '', content)
        content = re.sub(r'<!\s*', '', content)  # 남은 <! 제거
        
        # 공백 정리
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        return content
