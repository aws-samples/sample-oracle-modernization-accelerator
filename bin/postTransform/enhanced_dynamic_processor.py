#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
강화된 동적 처리기 - 향상된 파라미터 처리기 사용
"""

import re
import logging
from typing import Dict, List, Optional
from enhanced_parameter_processor import EnhancedParameterProcessor

logger = logging.getLogger(__name__)

class EnhancedDynamicProcessor:
    def __init__(self):
        self.param_processor = EnhancedParameterProcessor()
        self.parameter_values = {}
        
    def process_dynamic_conditions(self, content: str) -> str:
        """강화된 동적 조건 처리"""
        
        # 1단계: 파라미터 추출 및 기본값 설정
        parameters = self.param_processor.extract_parameters_comprehensive(content)
        for param in parameters:
            self.parameter_values[param] = self.param_processor.get_smart_default_value(param)
            
        logger.info(f"설정된 파라미터 기본값: {len(self.parameter_values)}개")
        
        # 2단계: 동적 태그 처리 (중첩 순서 중요)
        result = content
        
        # include 태그 먼저 처리
        result = self._process_include_tags(result)
        
        # 중첩된 동적 태그를 안쪽부터 처리
        max_iterations = 10
        for i in range(max_iterations):
            old_result = result
            
            # foreach 처리
            result = self._process_foreach_tags(result)
            
            # if 태그 처리
            result = self._process_if_tags(result)
            
            # choose/when/otherwise 처리
            result = self._process_choose_tags(result)
            
            # where 태그 처리
            result = self._process_where_tags(result)
            
            # set 태그 처리
            result = self._process_set_tags(result)
            
            # trim 태그 처리
            result = self._process_trim_tags(result)
            
            if result == old_result:
                break  # 더 이상 변화가 없으면 종료
                
        # 3단계: 파라미터 치환
        result = self.param_processor.substitute_parameters_comprehensive(result)
        
        # 4단계: 최종 정리
        result = self._final_cleanup(result)
        
        return result
    
    def _process_include_tags(self, content: str) -> str:
        """include 태그 처리"""
        
        def replace_include(match):
            # include 태그는 단순히 제거 (실제로는 다른 SQL을 포함해야 하지만 테스트용으로는 제거)
            return ""
            
        pattern = r'<include[^>]*/?>'
        return re.sub(pattern, replace_include, content, flags=re.IGNORECASE)
    
    def _process_foreach_tags(self, content: str) -> str:
        """강화된 foreach 태그 처리"""
        
        def replace_foreach(match):
            full_tag = match.group(0)
            
            # 속성 추출
            attrs = self._extract_tag_attributes(full_tag)
            collection = attrs.get('collection', '')
            item = attrs.get('item', 'item')
            separator = attrs.get('separator', ',')
            open_char = attrs.get('open', '(')
            close_char = attrs.get('close', ')')
            
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
                        # item 파라미터 치환 (jdbcType 포함)
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
        
        pattern = r'<foreach[^>]*>.*?</foreach>'
        return re.sub(pattern, replace_foreach, content, flags=re.DOTALL | re.IGNORECASE)
    
    def _process_if_tags(self, content: str) -> str:
        """강화된 if 태그 처리"""
        
        def replace_if(match):
            full_tag = match.group(0)
            
            # test 조건 추출
            test_match = re.search(r'test="([^"]*)"', full_tag)
            if not test_match:
                test_match = re.search(r"test='([^']*)'", full_tag)
                
            if not test_match:
                return ""  # test 조건이 없으면 제거
                
            test_condition = test_match.group(1)
            
            # 내용 추출
            content_match = re.search(r'<if[^>]*>(.*?)</if>', full_tag, re.DOTALL)
            if not content_match:
                return ""
                
            inner_content = content_match.group(1)
            
            # 조건 평가
            if self._evaluate_condition(test_condition):
                return inner_content
            else:
                return ""
        
        pattern = r'<if[^>]*>.*?</if>'
        return re.sub(pattern, replace_if, content, flags=re.DOTALL | re.IGNORECASE)
    
    def _process_choose_tags(self, content: str) -> str:
        """강화된 choose/when/otherwise 태그 처리"""
        
        def replace_choose(match):
            full_tag = match.group(0)
            
            # when 태그들 찾기
            when_pattern = r'<when[^>]*test="([^"]*)"[^>]*>(.*?)</when>'
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
    
    def _process_trim_tags(self, content: str) -> str:
        """trim 태그 처리"""
        
        def replace_trim(match):
            full_tag = match.group(0)
            
            # 속성 추출
            attrs = self._extract_tag_attributes(full_tag)
            prefix = attrs.get('prefix', '')
            suffix = attrs.get('suffix', '')
            prefix_overrides = attrs.get('prefixOverrides', '').split('|')
            suffix_overrides = attrs.get('suffixOverrides', '').split('|')
            
            # 내용 추출
            content_match = re.search(r'<trim[^>]*>(.*?)</trim>', full_tag, re.DOTALL)
            if not content_match:
                return ""
                
            inner_content = content_match.group(1).strip()
            
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
            
            return f"{prefix}{inner_content}{suffix}"
        
        pattern = r'<trim[^>]*>.*?</trim>'
        return re.sub(pattern, replace_trim, content, flags=re.DOTALL | re.IGNORECASE)
    
    def _extract_tag_attributes(self, tag: str) -> Dict[str, str]:
        """태그 속성 추출"""
        
        attrs = {}
        
        # 속성 패턴 매칭
        attr_pattern = r'(\w+)="([^"]*)"'
        matches = re.findall(attr_pattern, tag)
        
        for attr_name, attr_value in matches:
            attrs[attr_name] = attr_value
            
        return attrs
    
    def _evaluate_condition(self, condition: str) -> bool:
        """강화된 조건 평가"""
        
        # 조건 정규화
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
            return True  # 기본적으로 true로 가정
            
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
        
        # 기본값
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

def test_enhanced_dynamic_processor():
    """강화된 동적 처리기 테스트"""
    
    processor = EnhancedDynamicProcessor()
    
    test_case = """
    <select id="testSelect">
        SELECT * FROM TB_TEST
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
    </select>
    """
    
    print("=== 강화된 동적 처리기 테스트 ===")
    print("입력:")
    print(test_case.strip())
    print("\n출력:")
    result = processor.process_dynamic_conditions(test_case)
    print(result)

if __name__ == '__main__':
    test_enhanced_dynamic_processor()
