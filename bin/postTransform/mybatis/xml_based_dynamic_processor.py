#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XML 파서 기반 동적 태그 처리기
"""

import xml.etree.ElementTree as ET
import re
import logging
from typing import Dict, List, Optional, Any
from enhanced_parameter_processor import EnhancedParameterProcessor

logger = logging.getLogger(__name__)

class XmlBasedDynamicProcessor:
    def __init__(self):
        self.param_processor = EnhancedParameterProcessor()
        self.parameter_values = {}
        
    def process_dynamic_conditions(self, content: str) -> str:
        """XML 파서 기반 동적 조건 처리"""
        
        # 1단계: 파라미터 추출 및 기본값 설정
        parameters = self.param_processor.extract_parameters_comprehensive(content)
        for param in parameters:
            self.parameter_values[param] = self.param_processor.get_smart_default_value(param)
            
        logger.info(f"설정된 파라미터 기본값: {len(self.parameter_values)}개")
        
        # 2단계: XML을 파싱 가능한 형태로 래핑
        wrapped_content = f"<root>{content}</root>"
        
        try:
            # 3단계: XML 파싱
            root = ET.fromstring(wrapped_content)
            
            # 4단계: 동적 태그 처리
            self._process_element_recursively(root)
            
            # 5단계: 결과 추출
            result = self._extract_text_content(root)
            
            # 6단계: 파라미터 치환
            result = self.param_processor.substitute_parameters_comprehensive(result)
            
            # 7단계: 최종 정리
            result = self._final_cleanup(result)
            
            return result
            
        except ET.ParseError as e:
            logger.warning(f"XML 파싱 실패, 정규식 방식으로 fallback: {e}")
            # XML 파싱이 실패하면 기존 방식으로 fallback
            return self._fallback_regex_processing(content)
    
    def _process_element_recursively(self, element: ET.Element):
        """요소를 재귀적으로 처리"""
        
        # 현재 요소 처리
        if element.tag == 'if':
            self._process_if_element(element)
        elif element.tag == 'choose':
            self._process_choose_element(element)
        elif element.tag == 'foreach':
            self._process_foreach_element(element)
        elif element.tag == 'where':
            self._process_where_element(element)
        elif element.tag == 'set':
            self._process_set_element(element)
        elif element.tag == 'trim':
            self._process_trim_element(element)
        elif element.tag == 'include':
            self._process_include_element(element)
        
        # 자식 요소들 재귀 처리
        for child in list(element):
            self._process_element_recursively(child)
    
    def _process_if_element(self, element: ET.Element):
        """if 요소 처리"""
        
        test_condition = element.get('test', '')
        
        if self._evaluate_condition(test_condition):
            # 조건이 참이면 if 태그만 제거하고 내용은 유지
            self._replace_element_with_content(element)
        else:
            # 조건이 거짓이면 전체 제거
            self._remove_element(element)
    
    def _process_choose_element(self, element: ET.Element):
        """choose 요소 처리"""
        
        # when 요소들 찾기
        for child in element:
            if child.tag == 'when':
                test_condition = child.get('test', '')
                if self._evaluate_condition(test_condition):
                    # 첫 번째 참인 when의 내용으로 choose 전체를 교체
                    self._replace_element_with_child_content(element, child)
                    return
        
        # when이 모두 거짓이면 otherwise 찾기
        for child in element:
            if child.tag == 'otherwise':
                self._replace_element_with_child_content(element, child)
                return
        
        # otherwise도 없으면 전체 제거
        self._remove_element(element)
    
    def _process_foreach_element(self, element: ET.Element):
        """foreach 요소 처리"""
        
        collection = element.get('collection', '')
        item = element.get('item', 'item')
        separator = element.get('separator', ',')
        open_char = element.get('open', '(')
        close_char = element.get('close', ')')
        
        # 컬렉션 값 확인
        if collection in self.parameter_values:
            collection_value = self.parameter_values[collection]
            if isinstance(collection_value, list) and len(collection_value) > 0:
                items = []
                for value in collection_value[:3]:  # 최대 3개
                    item_content = self._extract_text_content(element)
                    # item 파라미터 치환
                    item_content = re.sub(rf'#\{{{re.escape(item)}[^}}]*\}}', f"'{value}'", item_content)
                    item_content = re.sub(rf'\${{{re.escape(item)}[^}}]*\}}', str(value), item_content)
                    items.append(item_content.strip())
                
                result_text = f"{open_char}{separator.join(items)}{close_char}"
                self._replace_element_with_text(element, result_text)
                return
        
        # 기본값 처리
        default_items = []
        for i in range(3):
            item_content = self._extract_text_content(element)
            item_content = re.sub(rf'#\{{{re.escape(item)}[^}}]*\}}', "'DEFAULT'", item_content)
            item_content = re.sub(rf'\${{{re.escape(item)}[^}}]*\}}', "DEFAULT", item_content)
            default_items.append(item_content.strip())
            
        result_text = f"{open_char}{separator.join(default_items)}{close_char}"
        self._replace_element_with_text(element, result_text)
    
    def _process_where_element(self, element: ET.Element):
        """where 요소 처리"""
        
        inner_content = self._extract_text_content(element).strip()
        
        if not inner_content:
            self._replace_element_with_text(element, "WHERE 1=1")
            return
            
        # 앞의 AND/OR 제거
        inner_content = re.sub(r'^\s*(AND|OR)\s+', '', inner_content, flags=re.IGNORECASE)
        
        self._replace_element_with_text(element, f"WHERE {inner_content}")
    
    def _process_set_element(self, element: ET.Element):
        """set 요소 처리"""
        
        inner_content = self._extract_text_content(element).strip()
        
        if not inner_content:
            self._replace_element_with_text(element, "SET ")
            return
            
        # 마지막 쉼표 제거
        inner_content = re.sub(r',\s*$', '', inner_content)
        
        self._replace_element_with_text(element, f"SET {inner_content}")
    
    def _process_trim_element(self, element: ET.Element):
        """trim 요소 처리"""
        
        prefix = element.get('prefix', '')
        suffix = element.get('suffix', '')
        prefix_overrides = element.get('prefixOverrides', '').split('|')
        suffix_overrides = element.get('suffixOverrides', '').split('|')
        
        inner_content = self._extract_text_content(element).strip()
        
        # prefix overrides 적용
        for override in prefix_overrides:
            if override.strip():
                pattern = rf'^\s*{re.escape(override.strip())}\s*'
                inner_content = re.sub(pattern, '', inner_content, flags=re.IGNORECASE)
                
        # suffix overrides 적용
        for override in suffix_overrides:
            if override.strip():
                pattern = rf'\s*{re.escape(override.strip())}\s*$'
                inner_content = re.sub(pattern, '', inner_content, flags=re.IGNORECASE)
        
        self._replace_element_with_text(element, f"{prefix}{inner_content}{suffix}")
    
    def _process_include_element(self, element: ET.Element):
        """include 요소 처리"""
        
        # include는 단순히 제거
        self._remove_element(element)
    
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
    
    def _extract_text_content(self, element: ET.Element) -> str:
        """요소의 텍스트 내용 추출"""
        
        def extract_recursive(elem):
            text = elem.text or ''
            for child in elem:
                text += extract_recursive(child)
                text += child.tail or ''
            return text
        
        return extract_recursive(element)
    
    def _replace_element_with_content(self, element: ET.Element):
        """요소를 내용으로 교체"""
        
        parent = element.getparent()
        if parent is not None:
            content = self._extract_text_content(element)
            element.text = content
            element.tag = 'processed'  # 임시 태그로 변경
            element.clear()  # 자식 요소들 제거
    
    def _replace_element_with_child_content(self, element: ET.Element, child: ET.Element):
        """요소를 특정 자식의 내용으로 교체"""
        
        content = self._extract_text_content(child)
        element.text = content
        element.tag = 'processed'
        element.clear()
    
    def _replace_element_with_text(self, element: ET.Element, text: str):
        """요소를 텍스트로 교체"""
        
        element.text = text
        element.tag = 'processed'
        element.clear()
    
    def _remove_element(self, element: ET.Element):
        """요소 제거"""
        
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    
    def _fallback_regex_processing(self, content: str) -> str:
        """XML 파싱 실패시 정규식 방식으로 fallback"""
        
        # 기존 정규식 방식 사용
        result = content
        
        # 간단한 if 태그 처리
        def replace_if(match):
            full_tag = match.group(0)
            test_match = re.search(r'test\s*=\s*"([^"]*)"', full_tag)
            if test_match:
                test_condition = test_match.group(1)
                content_match = re.search(r'<if[^>]*>(.*?)</if>', full_tag, re.DOTALL)
                if content_match and self._evaluate_condition(test_condition):
                    return content_match.group(1)
            return ""
        
        result = re.sub(r'<if\s[^>]*>.*?</if>', replace_if, result, flags=re.DOTALL | re.IGNORECASE)
        
        # 파라미터 치환
        result = self.param_processor.substitute_parameters_comprehensive(result)
        
        return self._final_cleanup(result)
    
    def _final_cleanup(self, content: str) -> str:
        """최종 정리"""
        
        # processed 태그 제거
        content = re.sub(r'</?processed[^>]*>', '', content)
        
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

def test_xml_based_processor():
    """XML 기반 처리기 테스트"""
    
    processor = XmlBasedDynamicProcessor()
    
    test_case = """
        <where>
            <if test="agtCd != null and agtCd != ''">
                AND AGT_CD = #{agtCd,jdbcType=VARCHAR}
            </if>
            <if test="payTl != null">
                AND PAY_TL = #{payTl,jdbcType=VARCHAR}
            </if>
            <if test="listIds != null and listIds.size() > 0">
                AND ID IN
                <foreach collection="listIds" item="id" open="(" separator="," close=")">
                    #{id,jdbcType=INTEGER}
                </foreach>
            </if>
        </where>
        <choose>
            <when test="orderby != null">
                ORDER BY ${orderby}
            </when>
            <otherwise>
                ORDER BY ID DESC
            </otherwise>
        </choose>
    """
    
    print("=== XML 기반 동적 처리기 테스트 ===")
    print("입력:")
    print(test_case.strip())
    print("\n출력:")
    result = processor.process_dynamic_conditions(test_case)
    print(result)

if __name__ == '__main__':
    test_xml_based_processor()
