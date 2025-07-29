#!/usr/bin/env python3
"""
SQL 함수 파서 - 복잡한 중첩 구조 정확 처리
Version: 1.0
Author: Amazon Q Developer
Date: 2025-07-19
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Union

class TokenType(Enum):
    FUNCTION = "FUNCTION"
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    OPERATOR = "OPERATOR"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"
    WHITESPACE = "WHITESPACE"
    COMMENT = "COMMENT"
    EOF = "EOF"

@dataclass
class Token:
    type: TokenType
    value: str
    position: int

class SQLTokenizer:
    def __init__(self):
        # SQL 함수명 리스트 (MySQL, Oracle, PostgreSQL)
        self.functions = {
            'CONCAT', 'SUBSTRING', 'SUBSTR', 'UPPER', 'LOWER', 'TRIM', 'LTRIM', 'RTRIM',
            'REPLACE', 'LENGTH', 'CHAR_LENGTH', 'LEFT', 'RIGHT', 'REVERSE',
            'LOCATE', 'INSTR', 'POSITION', 'LPAD', 'RPAD', 'REPEAT', 'SPACE',
            'INITCAP', 'TRANSLATE', 'ASCII', 'CHR', 'SOUNDEX', 'REGEXP_REPLACE',
            'SUM', 'COUNT', 'AVG', 'MAX', 'MIN', 'ROUND', 'CEIL', 'CEILING', 'FLOOR',
            'GROUP_CONCAT',
            'ABS', 'MOD', 'POWER', 'SQRT', 'SIGN', 'GREATEST', 'LEAST',
            'DATE_FORMAT', 'STR_TO_DATE', 'DATE_ADD', 'DATE_SUB', 'DATEDIFF',
            'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'DAYOFWEEK',
            'UNIX_TIMESTAMP', 'FROM_UNIXTIME', 'TIME_FORMAT', 'NOW', 'CURDATE',
            'IFNULL', 'ISNULL', 'COALESCE', 'NULLIF', 'NVL', 'NVL2',
            'CAST', 'CONVERT', 'TO_NUMBER', 'TO_CHAR', 'TO_DATE'
        }
        
        # SQL 키워드
        self.keywords = {
            'SELECT', 'FROM', 'WHERE', 'GROUP', 'ORDER', 'BY', 'HAVING',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'AND', 'OR', 'NOT',
            'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'TRUE', 'FALSE',
            'DISTINCT', 'ALL', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'JOIN', 'ON',
            'UNION', 'INTERSECT', 'EXCEPT', 'INTERVAL',
            'LEADING', 'TRAILING', 'BOTH'  # TRIM 함수용 키워드 추가
        }
        
        # 토큰 패턴들
        self.patterns = [
            (r'/\*.*?\*/', TokenType.COMMENT),           # /* 주석 */
            (r'--.*?$', TokenType.COMMENT),              # -- 주석
            (r"'(?:[^']|'')*'", TokenType.STRING),       # '문자열'
            (r'"(?:[^"]|"")*"', TokenType.STRING),       # "문자열"
            (r'\d+\.?\d*', TokenType.NUMBER),            # 숫자
            (r'[A-Za-z_][A-Za-z0-9_]*', TokenType.IDENTIFIER),  # 식별자
            (r'\(', TokenType.LPAREN),                   # (
            (r'\)', TokenType.RPAREN),                   # )
            (r',', TokenType.COMMA),                     # ,
            (r'\.', TokenType.OPERATOR),                 # . (점 연산자)
            (r'[+\-*/=<>!]+', TokenType.OPERATOR),       # 연산자
            (r'\s+', TokenType.WHITESPACE),              # 공백
        ]
        
        self.compiled_patterns = [(re.compile(pattern, re.MULTILINE | re.DOTALL), token_type) 
                                 for pattern, token_type in self.patterns]
    
    def tokenize(self, text: str) -> List[Token]:
        """텍스트를 토큰으로 분리"""
        tokens = []
        position = 0
        
        while position < len(text):
            matched = False
            
            for pattern, token_type in self.compiled_patterns:
                match = pattern.match(text, position)
                if match:
                    value = match.group(0)
                    
                    # 토큰 타입 세분화
                    if token_type == TokenType.IDENTIFIER:
                        upper_value = value.upper()
                        if upper_value in self.functions:
                            token_type = TokenType.FUNCTION
                        elif upper_value in self.keywords:
                            token_type = TokenType.KEYWORD
                    
                    # 공백과 주석은 건너뛰기 (선택적)
                    if token_type not in [TokenType.WHITESPACE, TokenType.COMMENT]:
                        tokens.append(Token(token_type, value, position))
                    
                    position = match.end()
                    matched = True
                    break
            
            if not matched:
                # 매칭되지 않은 문자는 건너뛰기
                position += 1
        
        tokens.append(Token(TokenType.EOF, '', position))
        return tokens

class SQLFunctionParser:
    def __init__(self):
        self.tokenizer = SQLTokenizer()
        self.tokens = []
        self.position = 0
        self.current_token = None
    
    def parse(self, text: str) -> List[str]:
        """SQL 텍스트에서 완전한 함수들을 추출"""
        self.tokens = self.tokenizer.tokenize(text)
        self.position = 0
        self.current_token = self.tokens[0] if self.tokens else None
        self.set_original_text(text)  # 원본 텍스트 설정 추가
        
        functions = []
        
        while not self.is_at_end():
            if self.current_token.type == TokenType.FUNCTION:
                func = self.parse_function()
                if func:
                    functions.append(func)
            elif self.current_token.type == TokenType.KEYWORD and self.current_token.value.upper() == 'CASE':
                case_stmt = self.parse_case_statement()
                if case_stmt:
                    functions.append(case_stmt)
            else:
                self.advance()
        
        return functions
    
    def advance(self):
        """다음 토큰으로 이동"""
        if not self.is_at_end():
            self.position += 1
            if self.position < len(self.tokens):
                self.current_token = self.tokens[self.position]
    
    def is_at_end(self):
        """토큰 끝에 도달했는지 확인"""
        return self.current_token is None or self.current_token.type == TokenType.EOF
    
    def peek(self, offset=1):
        """앞의 토큰을 미리 보기"""
        peek_pos = self.position + offset
        if peek_pos < len(self.tokens):
            return self.tokens[peek_pos]
        return None
    
    def parse_function(self):
        """함수를 파싱 (중첩 구조 포함) - TRIM, CAST 함수 특별 처리"""
        if self.current_token.type != TokenType.FUNCTION:
            return None
        
        start_pos = self.current_token.position
        func_name = self.current_token.value.upper()
        self.advance()
        
        # 함수 뒤에 괄호가 있는지 확인
        if self.current_token.type != TokenType.LPAREN:
            return None
        
        # TRIM 함수 특별 처리
        if func_name == 'TRIM':
            return self.parse_trim_function(start_pos)
        
        # 모든 함수를 일반 함수로 처리 (CAST 특별 처리 제거)
        return self.parse_regular_function(start_pos)
    
    def parse_cast_function(self, start_pos):
        """CAST 함수 전용 파싱 - AS 절을 정확히 구분"""
        paren_count = 0
        as_positions = []
        current_pos = self.position
        
        while not self.is_at_end():
            if self.current_token.type == TokenType.LPAREN:
                paren_count += 1
            elif self.current_token.type == TokenType.RPAREN:
                paren_count -= 1
                if paren_count == 0:
                    # CAST 함수의 닫는 괄호 찾음
                    end_pos = self.current_token.position + len(self.current_token.value)
                    self.advance()
                    
                    # 원본 텍스트에서 CAST 함수 추출
                    original_text = self.get_original_text()
                    if start_pos < len(original_text) and end_pos <= len(original_text):
                        cast_function = original_text[start_pos:end_pos].strip()
                        
                        # CAST 함수 내부 구조 정리
                        return self.clean_cast_function(cast_function)
                    break
            elif (self.current_token.type == TokenType.KEYWORD and 
                  self.current_token.value.upper() == 'AS'):
                # AS 절 위치 기록 (괄호 레벨과 함께)
                as_positions.append((self.current_token.position, paren_count))
            
            self.advance()
        
        return None
    
    def clean_cast_function(self, cast_func):
        """CAST 함수 내부 구조 정리"""
        # CAST(expression AS datatype) 형태로 정리
        
        # 1. CAST( 부분 추출
        cast_start = cast_func.find('(')
        if cast_start == -1:
            return cast_func
        
        inner_content = cast_func[cast_start + 1:-1]  # 괄호 내부 내용
        
        # 2. 가장 바깥쪽 AS 절 찾기
        as_pos = self.find_outermost_as(inner_content)
        
        if as_pos == -1:
            # AS 절이 없으면 추가
            return f"CAST({inner_content} AS CHAR(255))"
        
        # 3. AS 절 기준으로 분리
        expression = inner_content[:as_pos].strip()
        datatype = inner_content[as_pos + 2:].strip()  # AS 이후 부분
        
        # 4. expression 내부의 잘못된 AS 절 제거
        expression = self.remove_inner_as_clauses(expression)
        
        return f"CAST({expression} AS {datatype})"
    
    def find_outermost_as(self, text):
        """가장 바깥쪽 AS 절의 위치 찾기"""
        paren_count = 0
        i = 0
        
        while i < len(text) - 1:
            if text[i] == '(':
                paren_count += 1
            elif text[i] == ')':
                paren_count -= 1
            elif (paren_count == 0 and 
                  text[i:i+2].upper() == 'AS' and 
                  (i == 0 or not text[i-1].isalnum()) and
                  (i+2 >= len(text) or not text[i+2].isalnum())):
                return i
            i += 1
        
        return -1
    
    def remove_inner_as_clauses(self, expression):
        """함수 내부의 잘못된 AS 절 제거"""
        # SUBSTRING(col, pos, len AS datatype) → SUBSTRING(col, pos, len)
        # 함수 내부의 AS 절만 제거하고 함수 구조는 유지
        
        result = expression
        
        # 함수 내부 AS 절 패턴 제거
        # 3개 파라미터 함수: func(a, b, c AS type) → func(a, b, c)
        result = re.sub(r'(\w+\s*\([^)]*,\s*[^)]*,\s*[^)]+)\s+AS\s+[^)]+(\))', 
                       r'\1\2', result, flags=re.IGNORECASE)
        
        # 2개 파라미터 함수: func(a, b AS type) → func(a, b)  
        result = re.sub(r'(\w+\s*\([^)]*,\s*[^)]+)\s+AS\s+[^)]+(\))', 
                       r'\1\2', result, flags=re.IGNORECASE)
        
        return result
    
    def parse_regular_function(self, start_pos):
        """일반 함수 파싱 (기존 로직)"""
        # 현재 토큰이 여는 괄호인지 확인
        if self.current_token.type != TokenType.LPAREN:
            return None
            
        # 괄호 매칭으로 함수 전체 추출
        paren_count = 0
        end_pos = start_pos
        
        while not self.is_at_end():
            if self.current_token.type == TokenType.LPAREN:
                paren_count += 1
            elif self.current_token.type == TokenType.RPAREN:
                paren_count -= 1
                if paren_count == 0:
                    end_pos = self.current_token.position + len(self.current_token.value)
                    self.advance()
                    break
            
            self.advance()
        
        # AS 절은 함수 추출에 포함하지 않음 (별도 처리)
        # AS 별칭이 있어도 함수 부분만 추출
        
        # 원본 텍스트에서 함수 추출
        original_text = self.get_original_text()
        if start_pos < len(original_text) and end_pos <= len(original_text):
            return original_text[start_pos:end_pos].strip()
        
        return None
    
    def parse_case_statement(self):
        """CASE 문을 파싱 - 원본 텍스트 기반 추출"""
        if (self.current_token.type != TokenType.KEYWORD or 
            self.current_token.value.upper() != 'CASE'):
            return None
        
        # CASE 문 시작 위치 기록
        start_pos = self.current_token.position
        self._case_start_pos = start_pos
        
        case_count = 1
        tokens_in_case = [self.current_token]  # CASE 토큰 포함
        self.advance()
        
        # 디버그: 토큰 수집 과정 로그
        debug_tokens = []
        
        while not self.is_at_end() and case_count > 0:
            if (self.current_token.type == TokenType.KEYWORD and 
                self.current_token.value.upper() == 'CASE'):
                case_count += 1
            elif (self.current_token.type == TokenType.KEYWORD and 
                  self.current_token.value.upper() == 'END'):
                case_count -= 1
                
            tokens_in_case.append(self.current_token)
            debug_tokens.append(f"{self.current_token.type.value}:{self.current_token.value}")
            
            if case_count == 0:
                # CASE 문 끝 위치 기록
                end_pos = self.current_token.position + len(self.current_token.value)
                self._case_end_pos = end_pos
                
                self.advance()
                
                # AS 절 확인
                if (not self.is_at_end() and 
                    self.current_token.type == TokenType.KEYWORD and 
                    self.current_token.value.upper() == 'AS'):
                    
                    tokens_in_case.append(self.current_token)  # AS 추가
                    debug_tokens.append(f"{self.current_token.type.value}:{self.current_token.value}")
                    self.advance()  # AS 건너뛰기
                    
                    # 별칭 확인
                    if (not self.is_at_end() and 
                        self.current_token.type in [TokenType.IDENTIFIER, TokenType.STRING]):
                        tokens_in_case.append(self.current_token)  # 별칭 추가
                        debug_tokens.append(f"{self.current_token.type.value}:{self.current_token.value}")
                        # AS 절까지 포함하여 끝 위치 업데이트
                        self._case_end_pos = self.current_token.position + len(self.current_token.value)
                        self.advance()
                
                # 디버그 로그 출력
                print(f"🔍 CASE 문 토큰 수집: {len(tokens_in_case)}개")
                print(f"🔍 토큰 목록: {debug_tokens[:20]}...")  # 처음 20개만 출력
                
                # 토큰들을 다시 조합해서 CASE 문 생성 - 순차적 처리로 누락 방지
                case_text = ""
                prev_token_type = None
                
                for i, token in enumerate(tokens_in_case):
                    # 공백 토큰은 건너뛰되, 필요한 곳에 공백 추가
                    if token.type == TokenType.WHITESPACE:
                        continue
                    
                    # 첫 번째 토큰
                    if i == 0 or not case_text:
                        case_text += token.value
                    else:
                        # 토큰 사이에 공백이 필요한지 판단
                        need_space = True
                        
                        # 점 연산자 처리: 앞뒤 공백 없음
                        if token.value == '.' or (prev_token_type == TokenType.OPERATOR and tokens_in_case[i-1].value == '.'):
                            need_space = False
                        # 여는 괄호: 앞에만 공백
                        elif token.value == '(':
                            need_space = True
                        # 닫는 괄호: 뒤에만 공백 (다음 토큰에서 처리)
                        elif token.value == ')':
                            need_space = False
                        # 쉼표: 뒤에만 공백
                        elif prev_token_type == TokenType.COMMA:
                            need_space = True
                        elif token.type == TokenType.COMMA:
                            need_space = False
                        
                        # 공백 추가
                        if need_space and not case_text.endswith(' '):
                            case_text += " "
                        
                        # 토큰 값 추가
                        case_text += token.value
                        
                        # 연산자나 쉼표 뒤에는 공백 추가
                        if token.type in [TokenType.OPERATOR, TokenType.COMMA] and token.value != '.':
                            case_text += " "
                    
                    prev_token_type = token.type
                
                # 디버그: 최종 CASE 문 결과 확인
                print(f"🔍 CASE 문 재조합 완료: {len(case_text)}자")
                print(f"🔍 CASE 문 결과 샘플: {case_text[:200]}...")
                
                # 원본 텍스트에서 직접 추출하는 방식으로 변경 (토큰 누락 방지)
                original_text = self.get_original_text()
                if original_text and hasattr(self, '_case_start_pos'):
                    # 균형 잡힌 CASE...END 추출
                    start_pos = self._case_start_pos
                    pos = start_pos
                    case_count = 0
                    paren_count = 0
                    
                    while pos < len(original_text):
                        char = original_text[pos]
                        
                        # 괄호 균형 추적
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                        
                        # CASE/END 키워드 확인 (괄호 밖에서만)
                        if paren_count == 0:
                            # CASE 키워드 확인
                            if (pos + 4 <= len(original_text) and 
                                original_text[pos:pos+4].upper() == 'CASE' and
                                (pos == 0 or not original_text[pos-1].isalnum()) and
                                (pos+4 >= len(original_text) or not original_text[pos+4].isalnum())):
                                case_count += 1
                                pos += 4
                                continue
                            
                            # END 키워드 확인
                            if (pos + 3 <= len(original_text) and 
                                original_text[pos:pos+3].upper() == 'END' and
                                (pos == 0 or not original_text[pos-1].isalnum()) and
                                (pos+3 >= len(original_text) or not original_text[pos+3].isalnum())):
                                case_count -= 1
                                if case_count == 0:
                                    end_pos = pos + 3
                                    
                                    # AS 절 확인
                                    remaining = original_text[end_pos:end_pos+50]
                                    as_match = re.match(r'\s*AS\s+([A-Za-z_][A-Za-z0-9_]*)', remaining, re.IGNORECASE)
                                    if as_match:
                                        end_pos += as_match.end()
                                    
                                    case_from_original = original_text[start_pos:end_pos].strip()
                                    print(f"🔍 균형 잡힌 CASE 문 추출: {case_from_original[:200]}...")
                                    
                                    # 연산자 개수 확인
                                    operator_count = case_from_original.count('>') + case_from_original.count('<') + case_from_original.count('=')
                                    print(f"🔍 균형 추출 연산자 개수: > {case_from_original.count('>')}, < {case_from_original.count('<')}, = {case_from_original.count('=')}")
                                    
                                    return case_from_original
                                pos += 3
                                continue
                        
                        pos += 1
                    
                    # 기존 방식 fallback
                    if hasattr(self, '_case_end_pos'):
                        case_from_original = original_text[self._case_start_pos:self._case_end_pos].strip()
                        if case_from_original:
                            print(f"🔍 원본에서 추출한 CASE 문: {case_from_original[:200]}...")
                            return case_from_original
                
                return case_text
            else:
                self.advance()
        
        return None
    
    def get_original_text(self):
        """원본 텍스트 반환 (토크나이저에서 설정)"""
        return getattr(self, '_original_text', '')
    
    def set_original_text(self, text):
        """원본 텍스트 설정"""
        self._original_text = text
    
    def replace_subqueries_with_parser(self, text: str) -> str:
        """파서를 사용해서 서브쿼리를 1로 대체"""
        self.tokens = self.tokenizer.tokenize(text)
        self.position = 0
        self.current_token = self.tokens[0] if self.tokens else None
        self._original_text = text
        
        # 서브쿼리 위치들을 찾아서 저장
        subquery_ranges = []
        
        while not self.is_at_end():
            if self.current_token.type == TokenType.LPAREN:
                # 괄호 시작 위치
                start_pos = self.current_token.position
                self.advance()
                
                # 다음 토큰이 SELECT인지 확인
                if (not self.is_at_end() and 
                    self.current_token.type == TokenType.KEYWORD and 
                    self.current_token.value.upper() == 'SELECT'):
                    
                    # 서브쿼리 시작 - 매칭되는 괄호까지 찾기
                    paren_count = 1
                    
                    while not self.is_at_end() and paren_count > 0:
                        if self.current_token.type == TokenType.LPAREN:
                            paren_count += 1
                        elif self.current_token.type == TokenType.RPAREN:
                            paren_count -= 1
                            if paren_count == 0:
                                # 서브쿼리 끝 위치
                                end_pos = self.current_token.position + len(self.current_token.value)
                                subquery_ranges.append((start_pos, end_pos))
                                break
                        self.advance()
            else:
                self.advance()
        
        # 뒤에서부터 대체 (위치가 변경되지 않도록)
        result = text
        for start_pos, end_pos in reversed(subquery_ranges):
            result = result[:start_pos] + '1' + result[end_pos:]
        
        return result
    
    def remove_as_aliases(self, text: str) -> str:
        """파서를 사용해서 AS 별칭을 제거"""
        self.tokens = self.tokenizer.tokenize(text)
        self.position = 0
        self.current_token = self.tokens[0] if self.tokens else None
        self._original_text = text
        
        # AS 절 위치들을 찾아서 저장
        as_ranges = []
        
        while not self.is_at_end():
            if (self.current_token.type == TokenType.KEYWORD and 
                self.current_token.value.upper() == 'AS'):
                
                # AS 시작 위치
                start_pos = self.current_token.position
                self.advance()
                
                # 별칭 확인
                if (not self.is_at_end() and 
                    self.current_token.type in [TokenType.IDENTIFIER, TokenType.STRING]):
                    # AS 별칭 끝 위치
                    end_pos = self.current_token.position + len(self.current_token.value)
                    as_ranges.append((start_pos, end_pos))
                    self.advance()
            else:
                self.advance()
        
        # 뒤에서부터 제거 (위치가 변경되지 않도록)
        result = text
        for start_pos, end_pos in reversed(as_ranges):
            result = result[:start_pos] + result[end_pos:]
        
        # 연속된 공백 정리
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\s*,\s*', ', ', result)
        
        return result.strip()
    
    def fix_special_functions(self, text: str) -> str:
        """CAST 함수와 윈도우 함수 특별 처리 (PARTITION BY 절 처리 개선)"""
        result = text
        
        # 1. CAST 함수 개선된 처리
        result = self.fix_cast_functions(result)
        
        # 2. PARTITION BY 보호: 1 BY → PARTITION BY
        result = re.sub(r'\b1\s+BY\b', 'PARTITION BY', result, flags=re.IGNORECASE)
        
        # 3. Oracle 함수를 MySQL 호환 함수로 대체
        # RATIO_TO_REPORT(값) OVER(...) → (값 / SUM(값) OVER(...))
        result = re.sub(r'RATIO_TO_REPORT\s*\(\s*([^)]+)\s*\)\s*(OVER\s*\([^)]*\))', 
                       r'(\1 / SUM(\1) \2)', result, flags=re.IGNORECASE)
        
        # GROUPING(컬럼) → 0 (MySQL에서는 GROUPING 함수가 없으므로 0으로 대체)
        result = re.sub(r'GROUPING\s*\([^)]*\)', '0', result, flags=re.IGNORECASE)
        
        # 4. 윈도우 함수 처리 개선
        # ROW_NUMBER() 함수가 잘못된 컨텍스트에 있는 경우 1로 대체
        result = re.sub(r'ROW_NUMBER\s*\(\s*\)\s*OVER\s*\([^)]*\)', '1', result, flags=re.IGNORECASE)
        
        # PARTITION BY 절에서 1 처리: PARTITION BY (SELECT NULL), 1 → PARTITION BY (SELECT NULL)
        result = re.sub(r'PARTITION\s+BY\s+\(SELECT\s+NULL\)\s*,\s*1\b', 'PARTITION BY (SELECT NULL)', result, flags=re.IGNORECASE)
        
        # ORDER BY 절에서 1이 여러 개 있는 경우 → ORDER BY (SELECT NULL)
        result = re.sub(r'ORDER\s+BY\s+(?:\(SELECT\s+NULL\)\s*,\s*)*1(?:\s*,\s*1)*\b', 
                       'ORDER BY (SELECT NULL)', result, flags=re.IGNORECASE)
        
        # ORDER BY 별칭 처리: ORDER BY YEAR → ORDER BY (SELECT NULL)
        result = re.sub(r'ORDER\s+BY\s+[A-Z_][A-Z0-9_]*\b', 'ORDER BY (SELECT NULL)', result, flags=re.IGNORECASE)
        
        # 기본 ORDER BY 1 → ORDER BY (SELECT NULL)
        result = re.sub(r'ORDER\s+BY\s+1\b', 'ORDER BY (SELECT NULL)', result, flags=re.IGNORECASE)
        
        # 5. PARTITION BY 1 → PARTITION BY (SELECT NULL)  
        result = re.sub(r'PARTITION\s+BY\s+1\b', 'PARTITION BY (SELECT NULL)', result, flags=re.IGNORECASE)
        
        return result
    
    def fix_cast_functions(self, text: str) -> str:
        """CAST 함수 전용 개선된 파싱 처리"""
        result = text
        
        # CAST 함수 패턴 매칭 및 올바른 구문 생성
        # 패턴: CAST(expression AS datatype) 형태 유지
        
        # 1. 이미 AS 절이 있는 CAST 함수는 그대로 유지
        cast_with_as_pattern = r'CAST\s*\(\s*([^)]+?)\s+AS\s+[^)]+\s*\)'
        cast_matches_with_as = re.findall(cast_with_as_pattern, result, flags=re.IGNORECASE)
        
        # 2. AS 절이 없는 CAST 함수에만 AS CHAR(255) 추가
        # 단, 내부 함수의 AS 절과 혼동하지 않도록 주의
        def fix_cast_without_as(match):
            inner_expr = match.group(1).strip()
            # 내부에 이미 AS가 있는지 확인 (SUBSTRING(..., ... AS ...) 같은 경우)
            if ' AS ' in inner_expr.upper():
                # 내부 AS 절을 제거하고 외부에 AS CHAR(255) 추가
                # SUBSTRING(1, 16, 3 AS CHAR(255)) → SUBSTRING(1, 16, 3)
                inner_expr = re.sub(r'\s+AS\s+[^,)]+', '', inner_expr, flags=re.IGNORECASE)
            return f'CAST({inner_expr} AS CHAR(255))'
        
        # AS 절이 없는 CAST 함수 처리
        cast_without_as_pattern = r'CAST\s*\(\s*([^)]+?)\s*\)(?!\s+AS)'
        result = re.sub(cast_without_as_pattern, fix_cast_without_as, result, flags=re.IGNORECASE)
        
        return result
    
    def fix_other_special_functions(self, text: str) -> str:
        """CAST 함수 외의 특별 함수 처리 (윈도우 함수, Oracle 함수)"""
        result = text
        
        # 2. PARTITION BY 보호: 1 BY → PARTITION BY
        result = re.sub(r'\b1\s+BY\b', 'PARTITION BY', result, flags=re.IGNORECASE)
        
        # 3. ORDER BY 보호: 1 BY → ORDER BY  
        result = re.sub(r'\bORDER\s+1\b', 'ORDER BY', result, flags=re.IGNORECASE)
        
        # 4. Oracle 함수 변환
        result = re.sub(r'\bNVL\s*\(', 'IFNULL(', result, flags=re.IGNORECASE)
        result = re.sub(r'\bTO_CHAR\s*\(', 'CAST(', result, flags=re.IGNORECASE)
        result = re.sub(r'\bTO_NUMBER\s*\(', 'CAST(', result, flags=re.IGNORECASE)
        
        # 5. PARTITION BY 1 → PARTITION BY (SELECT NULL)  
        result = re.sub(r'PARTITION\s+BY\s+1\b', 'PARTITION BY (SELECT NULL)', result, flags=re.IGNORECASE)
        
        return result
    
    def parse_trim_function(self, start_pos):
        """TRIM 함수 전용 파싱 - LEADING/TRAILING/BOTH FROM 구조 보존"""
        paren_count = 0
        
        while not self.is_at_end():
            if self.current_token.type == TokenType.LPAREN:
                paren_count += 1
            elif self.current_token.type == TokenType.RPAREN:
                paren_count -= 1
                if paren_count == 0:
                    # TRIM 함수의 닫는 괄호 찾음
                    end_pos = self.current_token.position + len(self.current_token.value)
                    self.advance()
                    
                    # 원본 텍스트에서 TRIM 함수 추출
                    original_text = self.get_original_text()
                    if start_pos < len(original_text) and end_pos <= len(original_text):
                        trim_function = original_text[start_pos:end_pos].strip()
                        return trim_function
                    break
            
            self.advance()
        
        return None
    
    def fix_cast_and_window_functions(self, text: str) -> str:
        """CAST 함수와 윈도우 함수 특별 처리"""
        result = text
        
        # 1. CAST 함수 수정: CAST(값 ) → CAST(값 AS VARCHAR(255))
        result = re.sub(r'CAST\s*\(\s*([^)]+?)\s*\)', r'CAST(\1 AS VARCHAR(255))', result, flags=re.IGNORECASE)
        
        # 2. 윈도우 함수 ORDER BY 수정: ORDER BY 1 → ORDER BY NULL
        result = re.sub(r'ORDER\s+BY\s+1\b', 'ORDER BY NULL', result, flags=re.IGNORECASE)
        
        # 3. PARTITION BY 수정: PARTITION BY 1 → PARTITION BY NULL  
        result = re.sub(r'PARTITION\s+BY\s+1\b', 'PARTITION BY NULL', result, flags=re.IGNORECASE)
        
        return result

# 테스트 함수
def test_parser():
    """파서 테스트"""
    parser = SQLFunctionParser()
    
    test_sql = """
    SELECT 
        IFNULL(
            (SELECT X.BPLC_NM FROM TB_COM_CD320 X WHERE X.AGT_CD = A.AGT_CD),
            CASE 
                WHEN A.AGT_CD = 'SELK138AX' 
                THEN (SELECT TB320.BPLC_NM FROM TB_COM_CD320 TB320)
                ELSE IFNULL(A.BPLC_CD,'-')
            END
        ) AS BPLC_NM,
        COUNT(*) AS CNT,
        MAX(DATE_FORMAT(NOW(), '%Y%m%d')) AS MAX_DATE
    """
    
    parser.set_original_text(test_sql)
    functions = parser.parse(test_sql)
    
    print("=== 파서 테스트 결과 ===")
    for i, func in enumerate(functions, 1):
        print(f"{i}. {func}")
    
    return functions

def extract_case_statements_from_xml(xml_content):
    """XML에서 직접 CASE 문들을 추출 - 중첩 함수 처리 방식 적용"""
    case_statements = []
    
    # CDATA 섹션에서 SQL 추출
    cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'
    cdata_matches = re.findall(cdata_pattern, xml_content, re.DOTALL)
    
    for cdata_content in cdata_matches:
        # 각 CDATA에서 CASE 문 찾기
        pos = 0
        while pos < len(cdata_content):
            # CASE 키워드 찾기
            case_match = re.search(r'\bCASE\b', cdata_content[pos:], re.IGNORECASE)
            if not case_match:
                break
            
            case_start = pos + case_match.start()
            
            # CASE 문 파싱 - 중첩 함수 처리 방식 적용
            case_statement = parse_case_statement_recursive(cdata_content, case_start)
            
            if case_statement:
                case_statements.append(case_statement)
                print(f"🔍 완전한 CASE 문 추출: {case_statement[:200]}...")
                operator_count = case_statement.count('>') + case_statement.count('<') + case_statement.count('=')
                print(f"🔍 연산자 개수: > {case_statement.count('>')}, < {case_statement.count('<')}, = {case_statement.count('=')}")
                
                pos = case_start + len(case_statement)
            else:
                pos = case_start + 4  # CASE 길이만큼 건너뛰기
    
    return case_statements

def parse_case_statement_recursive(text, start_pos):
    """재귀적으로 CASE 문 파싱 - THEN 키워드 기반 중첩 CASE 인식"""
    
    # CASE...END 매칭을 위한 스택 기반 파서
    pos = start_pos
    case_stack = []  # (type, start_pos) 튜플 저장
    paren_count = 0
    in_string = False
    string_char = None
    then_positions = []  # THEN 위치 추적
    
    # 첫 번째 CASE 추가
    case_stack.append(('CASE', start_pos))
    pos += 4  # 'CASE' 길이
    
    # 디버그: 시작 부분 확인
    debug_start = text[start_pos:start_pos+150]
    if 'FARE_SEASN_END' in debug_start:
        print(f"🔍 FARE_SEASN_END CASE 파싱 시작: position {start_pos}")
        print(f"🔍 내용: {debug_start}...")
    
    while pos < len(text) and case_stack:
        char = text[pos]
        
        # 문자열 처리
        if not in_string and char in ["'", '"']:
            in_string = True
            string_char = char
        elif in_string and char == string_char:
            # 이스케이프된 따옴표 확인
            if pos + 1 < len(text) and text[pos + 1] == string_char:
                pos += 1  # 이스케이프된 따옴표 건너뛰기
            else:
                in_string = False
                string_char = None
        elif in_string:
            pos += 1
            continue
        
        # 괄호 균형 추적 (문자열 밖에서만)
        if not in_string:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            
            # 키워드 확인 (괄호 밖에서만)
            if paren_count == 0:
                # THEN 키워드 확인 - 중첩 CASE 예측
                if (pos + 4 <= len(text) and 
                    text[pos:pos+4].upper() == 'THEN' and
                    (pos == 0 or not text[pos-1].isalnum()) and
                    (pos+4 >= len(text) or not text[pos+4].isalnum())):
                    
                    then_positions.append(pos)
                    if 'FARE_SEASN_END' in text[start_pos:pos+100]:
                        print(f"🔍 THEN 발견: position {pos}, depth {len(case_stack)}")
                    
                    # THEN 다음에 CASE가 올 수 있는지 확인
                    next_pos = pos + 4
                    while next_pos < len(text) and text[next_pos].isspace():
                        next_pos += 1
                    
                    if (next_pos + 4 <= len(text) and 
                        text[next_pos:next_pos+4].upper() == 'CASE'):
                        if 'FARE_SEASN_END' in text[start_pos:next_pos+50]:
                            print(f"🔍 THEN 다음에 중첩 CASE 예상: position {next_pos}")
                    
                    pos += 4
                    continue
                
                # CASE 키워드 확인 (중첩 CASE)
                if (pos + 4 <= len(text) and 
                    text[pos:pos+4].upper() == 'CASE' and
                    (pos == 0 or not text[pos-1].isalnum()) and
                    (pos+4 >= len(text) or not text[pos+4].isalnum())):
                    
                    case_stack.append(('CASE', pos))
                    if 'FARE_SEASN_END' in text[start_pos:pos+100]:
                        print(f"🔍 중첩 CASE 발견: depth {len(case_stack)}, position {pos}")
                    pos += 4
                    continue
                
                # END 키워드 확인 - 단어 경계 엄격 확인
                if (pos + 3 <= len(text) and 
                    text[pos:pos+3].upper() == 'END'):
                    
                    # 앞 문자 확인 - 알파벳/숫자/언더스코어가 아니어야 함
                    prev_char_ok = (pos == 0 or not (text[pos-1].isalnum() or text[pos-1] == '_'))
                    # 뒤 문자 확인 - 알파벳/숫자/언더스코어가 아니어야 함
                    next_char_ok = (pos+3 >= len(text) or not (text[pos+3].isalnum() or text[pos+3] == '_'))
                    
                    if prev_char_ok and next_char_ok:
                        if case_stack:
                            case_type, case_pos = case_stack.pop()
                            
                            if 'FARE_SEASN_END' in text[start_pos:pos+50]:
                                print(f"🔍 진짜 END 발견: depth {len(case_stack)}, position {pos}, matching {case_type} at {case_pos}")
                                print(f"🔍 END 주변: ...{text[max(0,pos-10):pos+10]}...")
                            
                            if not case_stack:  # 모든 CASE가 닫힘
                                end_pos = pos + 3
                                
                                # AS 절 확인
                                remaining = text[end_pos:end_pos+50]
                                as_match = re.match(r'\s*AS\s+([A-Za-z_][A-Za-z0-9_]*)', remaining, re.IGNORECASE)
                                if as_match:
                                    end_pos += as_match.end()
                                    if 'FARE_SEASN_END' in text[start_pos:end_pos]:
                                        print(f"🔍 AS 절 발견: {as_match.group()}")
                                
                                case_statement = text[start_pos:end_pos].strip()
                                
                                # 디버그: FARE_SEASN_END 관련 CASE 문인지 확인
                                if 'FARE_SEASN_END' in case_statement:
                                    print(f"🔍 FARE_SEASN_END CASE 문 완료!")
                                    print(f"🔍 길이: {len(case_statement)} 문자")
                                    print(f"🔍 CASE 개수: {case_statement.count('CASE')}")
                                    print(f"🔍 END 개수: {case_statement.count('END')}")
                                    print(f"🔍 THEN 개수: {case_statement.count('THEN')}")
                                    print(f"🔍 WHEN 개수: {case_statement.count('WHEN')}")
                                    print(f"🔍 내용 (처음 300자): {case_statement[:300]}...")
                                    
                                    # 완전한 중첩 CASE인지 검증
                                    if case_statement.count('CASE') > 1 and case_statement.count('THEN') > 0:
                                        print(f"🔍 ✅ 완전한 중첩 CASE 문 추출 성공!")
                                    else:
                                        print(f"🔍 ❌ 불완전한 CASE 문 - 중첩 구조 누락")
                                
                                return case_statement
                            else:
                                # 중첩 CASE의 END인 경우
                                if 'FARE_SEASN_END' in text[start_pos:pos+50]:
                                    print(f"🔍 중첩 CASE의 END: depth {len(case_stack)} 남음")
                        
                        pos += 3
                        continue
                    else:
                        # END가 단어의 일부인 경우 (예: FARE_SEASN_END_DATE1)
                        if 'FARE_SEASN_END' in text[start_pos:pos+50]:
                            print(f"🔍 가짜 END 무시: position {pos}, 주변: ...{text[max(0,pos-10):pos+10]}...")
                        pos += 1
                        continue
                
                # WHEN 키워드 확인 (외부 CASE의 추가 WHEN 절)
                if (pos + 4 <= len(text) and 
                    text[pos:pos+4].upper() == 'WHEN' and
                    (pos == 0 or not text[pos-1].isalnum()) and
                    (pos+4 >= len(text) or not text[pos+4].isalnum())):
                    
                    if 'FARE_SEASN_END' in text[start_pos:pos+100]:
                        print(f"🔍 WHEN 발견: position {pos}, depth {len(case_stack)}")
                    pos += 4
                    continue
        
        pos += 1
        
        # 디버그: 너무 길어지면 중단
        if pos - start_pos > 20000:  # 20KB 제한
            print(f"🔍 CASE 문이 너무 길어서 중단: {pos - start_pos} 문자")
            break
    
    # 매칭되지 않은 CASE
    if case_stack:
        print(f"🔍 매칭되지 않은 CASE: {len(case_stack)}개 남음")
        if 'FARE_SEASN_END' in text[start_pos:pos]:
            print(f"🔍 FARE_SEASN_END CASE 문 중단: position {pos}, 길이 {pos - start_pos}")
            print(f"🔍 중단 지점 주변: {text[max(0, pos-100):pos+100]}")
        return None
    
    return None

if __name__ == "__main__":
    test_parser()
