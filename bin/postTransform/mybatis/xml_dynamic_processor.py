#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyBatis 동적 태그 처리기 - XML 파서 기반
"""

import re
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from .learning_parameter_processor import LearningParameterProcessor

logger = logging.getLogger(__name__)

class XmlDynamicProcessor:
    def __init__(self):
        self.param_processor = LearningParameterProcessor()
        self.parameter_values = {}
        
    def process_dynamic_conditions(self, content: str) -> str:
        """동적 조건 처리 - XML 파서 기반"""
        
        # 1단계: 파라미터 추출 및 학습
        extracted_params = self.param_processor.extract_parameters_with_types(content)
        for param_name, param_info in extracted_params.items():
            self.parameter_values[param_name] = self.param_processor.learn_and_get_default_value(param_name, param_info)
            
        logger.info(f"설정된 파라미터 기본값: {len(self.parameter_values)}개")
        
        # 2단계: XML 파서 기반 동적 태그 처리
        result = self._process_with_xml_parser(content)
        
        # 3단계: 최종 파라미터 치환
        final_result = self.param_processor.process_content_with_learning(result)
        
        return final_result
    
    def _process_with_xml_parser(self, content: str) -> str:
        """XML 파서를 사용한 동적 태그 처리"""
        
        try:
            # XML 래핑하여 파싱 가능하게 만들기
            wrapped_content = f"<root>{content}</root>"
            
            # CDATA 섹션 임시 치환
            cdata_map = {}
            cdata_counter = 0
            
            def replace_cdata(match):
                nonlocal cdata_counter
                placeholder = f"__CDATA_PLACEHOLDER_{cdata_counter}__"
                cdata_map[placeholder] = match.group(0)
                cdata_counter += 1
                return placeholder
            
            wrapped_content = re.sub(r'<!\[CDATA\[.*?\]\]>', replace_cdata, wrapped_content, flags=re.DOTALL)
            
            # XML 파싱
            root = ET.fromstring(wrapped_content)
            
            # 동적 태그 처리
            self._process_element(root)
            
            # XML을 다시 문자열로 변환
            result = ET.tostring(root, encoding='unicode', method='xml')
            
            # root 태그 제거
            result = re.sub(r'^<root>(.*)</root>$', r'\1', result, flags=re.DOTALL)
            
            # CDATA 복원
            for placeholder, original in cdata_map.items():
                result = result.replace(placeholder, original)
            
            return result
            
        except ET.ParseError as e:
            logger.warning(f"XML 파싱 실패, 기본 처리로 fallback: {e}")
            return self._fallback_processing(content)
    
    def _process_element(self, element: ET.Element):
        """XML 요소 재귀 처리"""
        
        # 자식 요소들을 리스트로 복사 (수정 중 변경되므로)
        children = list(element)
        
        for child in children:
            if child.tag == 'if':
                self._process_if_element(element, child)
            elif child.tag == 'choose':
                self._process_choose_element(element, child)
            elif child.tag == 'foreach':
                self._process_foreach_element(element, child)
            elif child.tag == 'where':
                self._process_where_element(element, child)
            elif child.tag == 'set':
                self._process_set_element(element, child)
            else:
                # 재귀적으로 자식 처리
                self._process_element(child)
    
    def _process_if_element(self, parent: ET.Element, if_elem: ET.Element):
        """if 태그 처리"""
        
        test_condition = if_elem.get('test', '')
        
        if self._evaluate_condition(test_condition):
            # 조건이 참이면 내용을 부모에 추가
            self._replace_element_with_content(parent, if_elem)
        else:
            # 조건이 거짓이면 요소 제거
            parent.remove(if_elem)
    
    def _process_choose_element(self, parent: ET.Element, choose_elem: ET.Element):
        """choose 태그 처리"""
        
        # when 태그들 확인
        for when_elem in choose_elem.findall('when'):
            test_condition = when_elem.get('test', '')
            
            if self._evaluate_condition(test_condition):
                # 첫 번째 참인 when의 내용으로 교체
                self._replace_element_with_content(parent, choose_elem, when_elem)
                return
        
        # 모든 when이 거짓이면 otherwise 확인
        otherwise_elem = choose_elem.find('otherwise')
        if otherwise_elem is not None:
            self._replace_element_with_content(parent, choose_elem, otherwise_elem)
        else:
            # otherwise도 없으면 제거
            parent.remove(choose_elem)
    
    def _replace_element_with_content(self, parent: ET.Element, old_elem: ET.Element, content_elem: ET.Element = None):
        """요소를 다른 요소의 내용으로 교체"""
        
        if content_elem is None:
            content_elem = old_elem
        
        # 기존 요소의 인덱스 찾기
        index = list(parent).index(old_elem)
        
        # 기존 요소 제거
        parent.remove(old_elem)
        
        # 새 내용의 텍스트와 자식들을 추가
        if content_elem.text:
            if index == 0:
                parent.text = (parent.text or '') + content_elem.text
            else:
                prev_elem = parent[index - 1] if index > 0 else None
                if prev_elem is not None:
                    prev_elem.tail = (prev_elem.tail or '') + content_elem.text
        
        # 자식 요소들 추가
        for i, child in enumerate(content_elem):
            parent.insert(index + i, child)
    
    def _evaluate_condition(self, condition: str) -> bool:
        """조건 평가"""
        
        if not condition:
            return False
            
        # 간단한 조건 평가
        condition = condition.strip()
        
        # null 체크
        if ' != null' in condition or ' != ""' in condition or " != ''" in condition:
            param_name = condition.split()[0]
            return param_name in self.parameter_values and self.parameter_values[param_name] not in [None, '', 'null']
        
        if ' == null' in condition or ' == ""' in condition or " == ''" in condition:
            param_name = condition.split()[0]
            return param_name not in self.parameter_values or self.parameter_values[param_name] in [None, '', 'null']
        
        # 기본적으로 true 반환 (테스트용)
        return True
    
    def _fallback_processing(self, content: str) -> str:
        """XML 파싱 실패시 fallback 처리"""
        
        logger.info("Fallback 처리 모드")
        
        # 기본적인 정규식 기반 처리
        result = content
        
        # if 태그 간단 처리
        result = re.sub(r'<if[^>]*test="[^"]*"[^>]*>(.*?)</if>', r'\1', result, flags=re.DOTALL | re.IGNORECASE)
        
        # choose/when/otherwise 간단 처리 - 첫 번째 when 선택
        def replace_choose_simple(match):
            full_tag = match.group(0)
            when_match = re.search(r'<when[^>]*>(.*?)</when>', full_tag, re.DOTALL | re.IGNORECASE)
            if when_match:
                return when_match.group(1)
            
            otherwise_match = re.search(r'<otherwise[^>]*>(.*?)</otherwise>', full_tag, re.DOTALL | re.IGNORECASE)
            if otherwise_match:
                return otherwise_match.group(1)
            
            return ""
        
        result = re.sub(r'<choose[^>]*>.*?</choose>', replace_choose_simple, result, flags=re.DOTALL | re.IGNORECASE)
        
        # where 태그 처리
        result = re.sub(r'<where[^>]*>(.*?)</where>', r'WHERE \1', result, flags=re.DOTALL | re.IGNORECASE)
        
        # 공백 정리
        result = re.sub(r'\s+', ' ', result)
        
        return result
