#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyBatis 동적 태그 처리기 - 균형잡힌 태그 매칭
"""

import re
import logging
from typing import Dict, List, Optional, Any
from .learning_parameter_processor import LearningParameterProcessor

logger = logging.getLogger(__name__)

class DynamicProcessor:
    def __init__(self):
        self.param_processor = LearningParameterProcessor()
        self.parameter_values = {}
        
    def process_dynamic_conditions(self, content: str) -> str:
        """동적 조건 처리"""
        
        # 1단계: 파라미터 추출 및 학습 (간소화)
        result_with_params = self.param_processor.process_content_with_learning(content)
        
        # 학습된 파라미터 값들을 가져와서 조건 평가에 사용
        extracted_params = self.param_processor.extract_parameters_with_types(content)
        for param_name, param_info in extracted_params.items():
            self.parameter_values[param_name] = self.param_processor.learn_and_get_default_value(param_name, param_info)
            
        logger.info(f"설정된 파라미터 기본값: {len(self.parameter_values)}개")
        
        # 2단계: 동적 태그 처리는 원본 content로 (파라미터 치환은 나중에)
        result = content
        
        # include 태그 먼저 처리
        result = self._process_include_tags(result)
        
        # 중첩 처리를 위한 반복
        max_iterations = 5
        for i in range(max_iterations):
            old_result = result
            
            # foreach 처리 (가장 안쪽부터)
            result = self._process_foreach_tags(result)
            
            # if 태그 처리 (균형잡힌 매칭)
            result = self._process_if_tags(result)
            
            # choose/when/otherwise 처리
            result = self._process_choose_tags(result)
            
            # where 태그 처리
            result = self._process_where_tags(result)
            
            # set 태그 처리
            result = self._process_set_tags(result)
            
            if result == old_result:
                break  # 더 이상 변화가 없으면 종료
                
        # 3단계: 파라미터 치환 (학습형 처리기 사용)
        result = self.param_processor._substitute_parameters(result, self.parameter_values)
        
        # 4단계: 최종 정리
        result = self._final_cleanup(result)
        
        return result
    
    def _process_include_tags(self, content: str) -> str:
        """include 태그 처리"""
        return re.sub(r'<include[^>]*/?>', '', content, flags=re.IGNORECASE)
    
    def _process_if_tags(self, content: str) -> str:
        """균형잡힌 if 태그 처리"""
        
        def find_balanced_if_tags(text):
            """균형잡힌 if 태그 찾기"""
            results = []
            pos = 0
            
            while pos < len(text):
                # if 시작 태그 찾기
                start_match = re.search(r'<if\s+[^>]*>', text[pos:], re.IGNORECASE)
                if not start_match:
                    break
                    
                start_pos = pos + start_match.start()
                tag_start = pos + start_match.end()
                
                # test 조건 추출
                test_match = re.search(r'test\s*=\s*["\']([^"\']*)["\']', start_match.group(0))
                if not test_match:
                    pos = tag_start
                    continue
                    
                test_condition = test_match.group(1)
                
                # 균형잡힌 종료 태그 찾기
                depth = 1
                current_pos = tag_start
                
                while current_pos < len(text) and depth > 0:
                    # 다음 if 시작 또는 종료 태그 찾기
                    next_tag = re.search(r'<(/?)if(?:\s+[^>]*)?>', text[current_pos:], re.IGNORECASE)
                    if not next_tag:
                        break
                        
                    if next_tag.group(1):  # 종료 태그
                        depth -= 1
                    else:  # 시작 태그
                        depth += 1
                        
                    current_pos += next_tag.end()
                
                if depth == 0:
                    # 균형잡힌 태그 쌍을 찾음
                    end_pos = current_pos
                    # 내용 추출 (종료 태그 제외)
                    end_tag_match = re.search(r'</if>', text[:current_pos][::-1])
                    if end_tag_match:
                        inner_end = current_pos - end_tag_match.end()
                        inner_content = text[tag_start:inner_end]
                    else:
                        inner_content = text[tag_start:current_pos-5]  # </if> 길이만큼 빼기
                    
                    results.append({
                        'start': start_pos,
                        'end': end_pos,
                        'test_condition': test_condition,
                        'inner_content': inner_content
                    })
                
                pos = tag_start
            
            return results
        
        # if 태그들을 뒤에서부터 처리 (중첩 처리를 위해)
        if_tags = find_balanced_if_tags(content)
        if_tags.sort(key=lambda x: x['start'], reverse=True)
        
        result = content
        for tag_info in if_tags:
            if self._evaluate_condition(tag_info['test_condition']):
                # 조건이 참이면 내용만 남김
                replacement = tag_info['inner_content']
            else:
                # 조건이 거짓이면 전체 제거
                replacement = ""
                
            result = result[:tag_info['start']] + replacement + result[tag_info['end']:]
        
        return result
    
    def _process_foreach_tags(self, content: str) -> str:
        """foreach 태그 처리"""
        
        def replace_foreach(match):
            full_tag = match.group(0)
            
            # 속성 추출
            collection_match = re.search(r'collection\s*=\s*["\']([^"\']*)["\']', full_tag)
            item_match = re.search(r'item\s*=\s*["\']([^"\']*)["\']', full_tag)
            separator_match = re.search(r'separator\s*=\s*["\']([^"\']*)["\']', full_tag)
            open_match = re.search(r'open\s*=\s*["\']([^"\']*)["\']', full_tag)
            close_match = re.search(r'close\s*=\s*["\']([^"\']*)["\']', full_tag)
            
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
            if collection in self.parameter_values:
                collection_value = self.parameter_values[collection]
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
        
        # foreach는 중첩되지 않는다고 가정하고 간단한 정규식 사용
        pattern = r'<foreach[^>]*>.*?</foreach>'
        return re.sub(pattern, replace_foreach, content, flags=re.DOTALL | re.IGNORECASE)
    
    def _process_choose_tags(self, content: str) -> str:
        """choose 태그 처리"""
        
        def replace_choose(match):
            full_tag = match.group(0)
            
            # when 태그들 찾기
            when_pattern = r'<when\s+test\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</when>'
            when_matches = re.findall(when_pattern, full_tag, re.DOTALL | re.IGNORECASE)
            
            # when 조건 평가
            for test_condition, when_content in when_matches:
                if self._evaluate_condition(test_condition):
                    return when_content
                    
            # otherwise 찾기
            otherwise_match = re.search(r'<otherwise[^>]*>(.*?)</otherwise>', full_tag, re.DOTALL | re.IGNORECASE)
            if otherwise_match:
                return otherwise_match.group(1)
                
            return ""
        
        pattern = r'<choose[^>]*>.*?</choose>'
        return re.sub(pattern, replace_choose, content, flags=re.DOTALL | re.IGNORECASE)
    
    def _process_where_tags(self, content: str) -> str:
        """where 태그 처리"""
        
        def replace_where(match):
            full_tag = match.group(0)
            
            # 내용 추출
            content_match = re.search(r'<where[^>]*>(.*?)</where>', full_tag, re.DOTALL)
            if not content_match:
                return "WHERE 1=1"
                
            inner_content = content_match.group(1).strip()
            
            if not inner_content:
                return "WHERE 1=1"
                
            # 앞의 AND/OR 제거
            inner_content = re.sub(r'^\s*(AND|OR)\s+', '', inner_content, flags=re.IGNORECASE)
            
            return f"WHERE {inner_content}"
        
        pattern = r'<where[^>]*>.*?</where>'
        return re.sub(pattern, replace_where, content, flags=re.DOTALL | re.IGNORECASE)
    
    def _process_set_tags(self, content: str) -> str:
        """set 태그 처리"""
        
        def replace_set(match):
            full_tag = match.group(0)
            
            # 내용 추출
            content_match = re.search(r'<set[^>]*>(.*?)</set>', full_tag, re.DOTALL)
            if not content_match:
                return "SET "
                
            inner_content = content_match.group(1).strip()
            
            if not inner_content:
                return "SET "
                
            # 마지막 쉼표 제거
            inner_content = re.sub(r',\s*$', '', inner_content)
            
            return f"SET {inner_content}"
        
        pattern = r'<set[^>]*>.*?</set>'
        return re.sub(pattern, replace_set, content, flags=re.DOTALL | re.IGNORECASE)
    
    def _evaluate_condition(self, condition: str) -> bool:
        """조건 평가"""
        
        if not condition:
            return True
            
        condition = condition.strip()
        
        # 복합 조건 처리
        if ' and ' in condition.lower():
            parts = re.split(r'\s+and\s+', condition, flags=re.IGNORECASE)
            return all(self._evaluate_single_condition(part.strip()) for part in parts)
        elif ' or ' in condition.lower():
            parts = re.split(r'\s+or\s+', condition, flags=re.IGNORECASE)
            return any(self._evaluate_single_condition(part.strip()) for part in parts)
        else:
            return self._evaluate_single_condition(condition)
    
    def _evaluate_single_condition(self, condition: str) -> bool:
        """단일 조건 평가"""
        
        condition = condition.strip()
        
        # null 체크
        if re.match(r'(\w+)\s*!=\s*null', condition, re.IGNORECASE):
            param = re.match(r'(\w+)\s*!=\s*null', condition, re.IGNORECASE).group(1)
            return param in self.parameter_values and self.parameter_values[param] is not None
        elif re.match(r'(\w+)\s*==\s*null', condition, re.IGNORECASE):
            param = re.match(r'(\w+)\s*==\s*null', condition, re.IGNORECASE).group(1)
            return param not in self.parameter_values or self.parameter_values[param] is None
        
        # 빈 문자열 체크
        if re.match(r"(\w+)\s*!=\s*''", condition):
            param = re.match(r"(\w+)\s*!=\s*''", condition).group(1)
            value = self.parameter_values.get(param, '')
            return value != '' and value is not None
        elif re.match(r"(\w+)\s*==\s*''", condition):
            param = re.match(r"(\w+)\s*==\s*''", condition).group(1)
            value = self.parameter_values.get(param, '')
            return value == '' or value is None
        
        # 값 비교
        comparison_match = re.match(r"(\w+)\s*(==|!=|>=|<=|>|<)\s*'([^']*)'", condition)
        if comparison_match:
            param, op, expected = comparison_match.groups()
            actual = str(self.parameter_values.get(param, ''))
            
            if op == '==':
                return actual == expected
            elif op == '!=':
                return actual != expected
            elif op == '>=':
                return actual >= expected
            elif op == '<=':
                return actual <= expected
            elif op == '>':
                return actual > expected
            elif op == '<':
                return actual < expected
        
        # contains 체크
        if '.contains(' in condition:
            return True
            
        # 리스트 크기 체크
        if re.match(r'(\w+)\.size\(\)\s*>\s*0', condition):
            param = re.match(r'(\w+)\.size\(\)\s*>\s*0', condition).group(1)
            value = self.parameter_values.get(param, [])
            return isinstance(value, list) and len(value) > 0
        
        # 기본값: 파라미터가 존재하고 비어있지 않으면 true
        param_match = re.match(r'^(\w+)$', condition)
        if param_match:
            param = param_match.group(1)
            value = self.parameter_values.get(param)
            return value is not None and value != '' and value != []
        
        return True
    
    def _final_cleanup(self, content: str) -> str:
        """최종 정리"""
        
        # XML 주석 제거
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # 남은 XML 태그 제거
        content = re.sub(r'<[^>]+>', '', content)
        
        # CDATA 잔여물 제거
        content = re.sub(r'<!\[CDATA\[', '', content)
        content = re.sub(r'\]\]>', '', content)
        content = re.sub(r'<!\s*', '', content)
        
        # 공백 정리
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
