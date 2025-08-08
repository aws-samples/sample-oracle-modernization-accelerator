#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyBatis 스타일 파서 - SqlNode 트리 구조 구현
"""

import re
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class DynamicContext:
    """동적 SQL 생성 컨텍스트"""
    
    def __init__(self, parameters: Dict[str, Any]):
        self.sql_builder = []
        self.parameters = parameters
        self.bindings = parameters.copy()
        
    def append_sql(self, sql: str):
        """SQL 문자열 추가"""
        self.sql_builder.append(sql)
        
    def get_sql(self) -> str:
        """최종 SQL 반환"""
        return ''.join(self.sql_builder)
        
    def get_bindings(self) -> Dict[str, Any]:
        """파라미터 바인딩 반환"""
        return self.bindings

class SqlNode(ABC):
    """SqlNode 인터페이스"""
    
    @abstractmethod
    def apply(self, context: DynamicContext) -> bool:
        """동적 컨텍스트에 SQL 적용"""
        pass

class StaticTextSqlNode(SqlNode):
    """정적 텍스트 노드"""
    
    def __init__(self, text: str):
        self.text = text
        
    def apply(self, context: DynamicContext) -> bool:
        context.append_sql(self.text)
        return True

class MixedSqlNode(SqlNode):
    """혼합 노드 (여러 자식 노드 포함)"""
    
    def __init__(self, contents: List[SqlNode]):
        self.contents = contents
        
    def apply(self, context: DynamicContext) -> bool:
        for node in self.contents:
            node.apply(context)
        return True

class IfSqlNode(SqlNode):
    """IF 조건 노드"""
    
    def __init__(self, test: str, contents: SqlNode):
        self.test = test
        self.contents = contents
        
    def apply(self, context: DynamicContext) -> bool:
        if self._evaluate_condition(self.test, context.get_bindings()):
            self.contents.apply(context)
            return True
        return False
        
    def _evaluate_condition(self, condition: str, bindings: Dict[str, Any]) -> bool:
        """조건 평가 (간단한 OGNL 스타일)"""
        
        if not condition:
            return False
            
        condition = condition.strip()
        
        # null 체크
        if ' != null' in condition:
            param_name = condition.split(' != null')[0].strip()
            return param_name in bindings and bindings[param_name] is not None
            
        if ' == null' in condition:
            param_name = condition.split(' == null')[0].strip()
            return param_name not in bindings or bindings[param_name] is None
            
        # 빈 문자열 체크
        if ' != ""' in condition or " != ''" in condition:
            param_name = condition.split(' !=')[0].strip()
            return param_name in bindings and bindings[param_name] not in [None, '', 'null']
            
        if ' == ""' in condition or " == ''" in condition:
            param_name = condition.split(' ==')[0].strip()
            return param_name not in bindings or bindings[param_name] in [None, '', 'null']
        
        # 기본적으로 true 반환 (테스트용)
        return True

class ChooseSqlNode(SqlNode):
    """CHOOSE 노드"""
    
    def __init__(self, default_node: Optional[SqlNode], if_nodes: List[IfSqlNode]):
        self.default_node = default_node
        self.if_nodes = if_nodes
        
    def apply(self, context: DynamicContext) -> bool:
        for if_node in self.if_nodes:
            if if_node.apply(context):
                return True
                
        if self.default_node:
            self.default_node.apply(context)
            return True
            
        return False

class WhereSqlNode(SqlNode):
    """WHERE 노드"""
    
    def __init__(self, contents: SqlNode):
        self.contents = contents
        
    def apply(self, context: DynamicContext) -> bool:
        # 임시 컨텍스트로 내용 생성
        temp_context = DynamicContext(context.get_bindings())
        self.contents.apply(temp_context)
        
        sql = temp_context.get_sql().strip()
        if sql:
            # 앞의 AND/OR 제거
            sql = re.sub(r'^\s*(AND|OR)\s+', '', sql, flags=re.IGNORECASE)
            if sql:
                context.append_sql(f" WHERE {sql}")
                return True
                
        return False

class SetSqlNode(SqlNode):
    """SET 노드"""
    
    def __init__(self, contents: SqlNode):
        self.contents = contents
        
    def apply(self, context: DynamicContext) -> bool:
        # 임시 컨텍스트로 내용 생성
        temp_context = DynamicContext(context.get_bindings())
        self.contents.apply(temp_context)
        
        sql = temp_context.get_sql().strip()
        if sql:
            # 뒤의 쉼표 제거
            sql = re.sub(r',\s*$', '', sql)
            if sql:
                context.append_sql(f" SET {sql}")
                return True
                
        return False

class ForEachSqlNode(SqlNode):
    """FOREACH 노드"""
    
    def __init__(self, collection: str, item: str, separator: str, 
                 open_char: str, close_char: str, contents: SqlNode):
        self.collection = collection
        self.item = item
        self.separator = separator
        self.open_char = open_char
        self.close_char = close_char
        self.contents = contents
        
    def apply(self, context: DynamicContext) -> bool:
        collection_value = context.get_bindings().get(self.collection, ['DEFAULT1', 'DEFAULT2', 'DEFAULT3'])
        
        if not isinstance(collection_value, list):
            collection_value = [collection_value]
            
        if not collection_value:
            return False
            
        context.append_sql(self.open_char)
        
        for i, value in enumerate(collection_value[:3]):  # 최대 3개
            if i > 0:
                context.append_sql(self.separator)
                
            # item 파라미터를 현재 값으로 설정
            item_context = DynamicContext(context.get_bindings())
            item_context.bindings[self.item] = value
            
            self.contents.apply(item_context)
            context.append_sql(item_context.get_sql())
            
        context.append_sql(self.close_char)
        return True

class MyBatisParser:
    """MyBatis XML 파서"""
    
    def __init__(self):
        self.parameter_defaults = {
            'agtCd': 'TEST',
            'diFlag': 'Y', 
            'saletype': 'DEFAULT',
            'virtualrsvno': 'DEFAULT',
            'saledeptcd': 'TEST',
            'orderby': '1',
            'inicisjoinyn': 'Y'
        }
        
    def parse_xml_to_sqlnode(self, xml_content: str) -> SqlNode:
        """XML을 SqlNode 트리로 파싱"""
        
        try:
            # XML 파싱
            root = ET.fromstring(f"<root>{xml_content}</root>")
            return self._parse_element_to_sqlnode(root)
            
        except ET.ParseError as e:
            logger.warning(f"XML 파싱 실패: {e}")
            # fallback으로 정적 텍스트 노드 반환
            return StaticTextSqlNode(xml_content)
    
    def _parse_element_to_sqlnode(self, element: ET.Element) -> SqlNode:
        """XML 요소를 SqlNode로 변환"""
        
        nodes = []
        
        # 요소의 텍스트 추가
        if element.text:
            nodes.append(StaticTextSqlNode(element.text))
            
        # 자식 요소들 처리
        for child in element:
            if child.tag == 'if':
                test = child.get('test', '')
                contents = self._parse_element_to_sqlnode(child)
                nodes.append(IfSqlNode(test, contents))
                
            elif child.tag == 'choose':
                if_nodes = []
                default_node = None
                
                for when_or_otherwise in child:
                    if when_or_otherwise.tag == 'when':
                        test = when_or_otherwise.get('test', '')
                        contents = self._parse_element_to_sqlnode(when_or_otherwise)
                        if_nodes.append(IfSqlNode(test, contents))
                    elif when_or_otherwise.tag == 'otherwise':
                        default_node = self._parse_element_to_sqlnode(when_or_otherwise)
                        
                nodes.append(ChooseSqlNode(default_node, if_nodes))
                
            elif child.tag == 'where':
                contents = self._parse_element_to_sqlnode(child)
                nodes.append(WhereSqlNode(contents))
                
            elif child.tag == 'set':
                contents = self._parse_element_to_sqlnode(child)
                nodes.append(SetSqlNode(contents))
                
            elif child.tag == 'foreach':
                collection = child.get('collection', 'list')
                item = child.get('item', 'item')
                separator = child.get('separator', ',')
                open_char = child.get('open', '(')
                close_char = child.get('close', ')')
                contents = self._parse_element_to_sqlnode(child)
                nodes.append(ForEachSqlNode(collection, item, separator, open_char, close_char, contents))
                
            else:
                # 일반 요소는 재귀 처리
                nodes.append(self._parse_element_to_sqlnode(child))
                
            # tail 텍스트 추가
            if child.tail:
                nodes.append(StaticTextSqlNode(child.tail))
        
        if len(nodes) == 0:
            return StaticTextSqlNode("")
        elif len(nodes) == 1:
            return nodes[0]
        else:
            return MixedSqlNode(nodes)
    
    def generate_sql(self, xml_content: str, parameters: Dict[str, Any] = None) -> str:
        """XML에서 동적 SQL 생성"""
        
        if parameters is None:
            parameters = self.parameter_defaults.copy()
        else:
            # 기본값과 병합
            merged_params = self.parameter_defaults.copy()
            merged_params.update(parameters)
            parameters = merged_params
            
        # SqlNode 트리 생성
        root_node = self.parse_xml_to_sqlnode(xml_content)
        
        # 동적 SQL 생성
        context = DynamicContext(parameters)
        root_node.apply(context)
        
        sql = context.get_sql()
        
        # 파라미터 치환
        sql = self._substitute_parameters(sql, parameters)
        
        # 정리
        sql = re.sub(r'\s+', ' ', sql).strip()
        
        return sql
    
    def _substitute_parameters(self, sql: str, parameters: Dict[str, Any]) -> str:
        """파라미터 치환"""
        
        result = sql
        
        for param, value in parameters.items():
            # #{param} 패턴
            pattern1 = rf'#\{{{re.escape(param)}(?:,[^}}]*)?\}}'
            if isinstance(value, str):
                replacement1 = f"'{value}'"
            else:
                replacement1 = str(value)
            result = re.sub(pattern1, replacement1, result)
            
            # ${param} 패턴
            pattern2 = rf'\${{{re.escape(param)}(?:,[^}}]*)?\}}'
            replacement2 = str(value)
            result = re.sub(pattern2, replacement2, result)
            
        return result
