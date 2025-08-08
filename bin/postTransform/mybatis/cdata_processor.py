#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDATA 처리기 - 분할된 CDATA 섹션 연결
"""

import re
import logging

logger = logging.getLogger(__name__)

def fix_cdata_sections(content: str) -> str:
    """분할된 CDATA 섹션들을 연결하여 수정"""
    
    # 1단계: 기본 CDATA 패턴 처리
    cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'
    
    def replace_cdata(match):
        cdata_content = match.group(1)
        # CDATA 내용을 그대로 반환 (마커만 제거)
        return cdata_content
    
    # CDATA 마커 제거
    result = re.sub(cdata_pattern, replace_cdata, content, flags=re.DOTALL)
    
    # 2단계: 분할된 CDATA 패턴 처리
    # 예: ]]> ... <![CDATA[ 형태로 분할된 경우
    split_pattern = r'\]\]>\s*<!\[CDATA\['
    result = re.sub(split_pattern, ' ', result)
    
    # 3단계: 남은 CDATA 마커들 정리
    result = re.sub(r'<!\[CDATA\[', '', result)
    result = re.sub(r'\]\]>', '', result)
    
    return result

def test_cdata_processor():
    """CDATA 처리기 테스트"""
    
    test_cases = [
        # 기본 CDATA
        """
        <![CDATA[
        SELECT * FROM TB_TEST WHERE ID = 1
        ]]>
        """,
        
        # 분할된 CDATA
        """
        <![CDATA[
        SELECT * FROM TB_TEST 
        ]]>
        WHERE ID = 1
        <![CDATA[
        AND STATUS = 'Y'
        ]]>
        """,
        
        # 복잡한 분할
        """
        <![CDATA[SELECT]]> * FROM <![CDATA[TB_TEST]]>
        """
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n=== CDATA 테스트 케이스 {i+1} ===")
        print("입력:")
        print(test_case.strip())
        print("\n출력:")
        result = fix_cdata_sections(test_case)
        print(result.strip())

if __name__ == '__main__':
    test_cdata_processor()
