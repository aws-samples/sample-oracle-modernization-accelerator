#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XMLExtractor - MyBatis XML Mapper 파일에서 Level1 요소 추출

이 도구는 MyBatis XML Mapper 파일에서 모든 Level1 요소(select, update, insert, delete, sql 등)를
추출하여 개별 XML 파일로 저장합니다.

기능:
- MyBatis XML Mapper 파일에서 모든 Level1 요소 추출
- 주석과 중첩된 태그 구조 보존
- 각 요소를 개별 XML 파일로 저장
- 상세 로깅 기능

사용법:
    python3 XMLExtractor.py [옵션]

옵션:
    -h, --help                  도움말 표시
    -i, --input                 XML 파일 경로
    -o, --output                출력 폴더 경로
    -l, --log                   로그 파일 경로 지정
    -v, --verbose               상세 로깅 활성화 (DEBUG 레벨과 동일)
    --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                로그 레벨 설정 (기본값: INFO)

출력 파일 형식:
    {원본파일명}-{순번}-{요소타입}-{요소ID}.xml

예시:
    AuthPayDAO-01-update-updateAuthStatus.xml
    AuthPayDAO-02-sql-selectAuthPayDefaultQuery.xml

예제:
    python3 XMLExtractor.py --input /path/to/file.xml --output /path/to/output/folder
    python3 XMLExtractor.py -i /path/to/file.xml -o /path/to/output/folder --log-level=DEBUG
"""

import os
import re
import sys
import logging
from pathlib import Path
from datetime import datetime

# 로깅 설정
def setup_logger(log_file=None, log_level=logging.INFO):
    """로깅 설정을 초기화합니다.
    
    Args:
        log_file (str): 로그 파일 경로 (선택사항)
        log_level (int): 콘솔 출력용 로깅 레벨
        
    Returns:
        logger: 설정된 로거 인스턴스
    """
    logger = logging.getLogger('XMLExtractor')
    logger.setLevel(logging.DEBUG)  # 항상 로거를 DEBUG로 설정하여 모든 정보 캡처
    
    # 기존 핸들러 제거
    if logger.handlers:
        logger.handlers.clear()
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 설정 (로그 파일이 지정된 경우)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # 파일에는 항상 모든 로그 기록
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def extract_level1_elements(xml_file_path, output_folder, logger):
    """
    MyBatis XML Mapper 파일에서 모든 Level1 요소를 추출하여 개별 파일로 저장합니다.
    
    Args:
        xml_file_path (str): XML 파일 경로
        output_folder (str): 출력 폴더 경로
        logger: 로거 인스턴스
    """
    start_time = datetime.now()
    logger.info(f"Starting: Processing XML file '{os.path.basename(xml_file_path)}'")
    
    # 출력 폴더가 없으면 생성
    os.makedirs(output_folder, exist_ok=True)
    logger.debug(f"Created output folder: {output_folder}")
    
    # XML 파일 내용 읽기
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()
        logger.debug(f"Successfully read XML file: {len(xml_content)} bytes")
    except Exception as e:
        logger.error(f"Failed to read XML file: {str(e)}")
        return
    
    # XML 헤더와 DOCTYPE 추출
    header_match = re.search(r'(<\?xml.*?\?>)', xml_content, re.DOTALL)
    doctype_match = re.search(r'(<!DOCTYPE.*?>)', xml_content, re.DOTALL)
    
    xml_header = header_match.group(1) if header_match else '<?xml version="1.0" encoding="UTF-8"?>'
    xml_doctype = doctype_match.group(1) if doctype_match else '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">'
    logger.debug(f"XML header: {xml_header}")
    logger.debug(f"DOCTYPE: {xml_doctype}")
    
    # 네임스페이스 추출
    namespace_pattern = re.compile(r'<mapper\s+namespace\s*=\s*["\']([^"\']+)["\']')
    namespace_match = namespace_pattern.search(xml_content)
    namespace = namespace_match.group(1) if namespace_match else "Unknown"
    logger.info(f"Namespace: {namespace}")
    
    # mapper 태그 내용 찾기
    mapper_start_match = re.search(r'<mapper\s+namespace\s*=\s*["\'][^"\']+["\'][^>]*>', xml_content)
    mapper_end_match = re.search(r'</mapper>\s*$', xml_content)
    
    if not mapper_start_match or not mapper_end_match:
        logger.error("Error: Could not find mapper tags in the XML file.")
        return
    
    mapper_content = xml_content[mapper_start_match.end():mapper_end_match.start()]
    logger.debug(f"Extracted mapper content: {len(mapper_content)} bytes")
    
    # mapper 태그 사이의 내용 처리
    # 먼저 모든 주석과 위치 수집
    comments = []
    for comment_match in re.finditer(r'<!--.*?-->', mapper_content, re.DOTALL):
        comments.append((comment_match.start(), comment_match.end(), comment_match.group(0)))
    logger.debug(f"Found {len(comments)} comments")
    
    # 모든 Level1 요소를 적절한 태그 매칭으로 찾기
    level1_elements = []
    pos = 0
    
    # 시작 부분의 공백 건너뛰기
    while pos < len(mapper_content) and mapper_content[pos].isspace():
        pos += 1
    
    logger.debug("Starting Level1 element extraction")
    while pos < len(mapper_content):
        # 주석인지 확인
        is_comment = False
        comment_text = ""
        for comment_start, comment_end, comment in comments:
            if pos == comment_start:
                comment_text = comment
                pos = comment_end
                is_comment = True
                # 주석 이후 공백 건너뛰기
                while pos < len(mapper_content) and mapper_content[pos].isspace():
                    pos += 1
                break
        
        if is_comment:
            continue
        
        # 주석이 아니면 요소의 시작이어야 함
        if pos >= len(mapper_content) or mapper_content[pos] != '<' or (pos+1 < len(mapper_content) and mapper_content[pos+1] == '!'):
            # 텍스트 노드나 다른 내용 건너뛰기
            pos += 1
            continue
        
        # 태그 이름 찾기
        tag_end = mapper_content.find(' ', pos)
        if tag_end == -1:
            tag_end = mapper_content.find('>', pos)
        
        if tag_end == -1:
            # 잘못된 XML
            logger.warning(f"Malformed XML: Could not find tag end at position {pos}")
            pos += 1
            continue
        
        tag_name = mapper_content[pos+1:tag_end]
        logger.debug(f"Found tag: {tag_name}, position: {pos}")
        
        # 일치하는 닫는 태그 찾기
        # 같은 유형의 중첩 태그 처리 필요
        open_tag_pattern = f'<{tag_name}\\b'
        close_tag_pattern = f'</{tag_name}>'
        
        nesting_level = 1
        search_pos = tag_end
        
        while nesting_level > 0 and search_pos < len(mapper_content):
            open_match = mapper_content.find(f'<{tag_name}', search_pos)
            close_match = mapper_content.find(f'</{tag_name}>', search_pos)
            
            if close_match == -1:
                # 닫는 태그를 찾을 수 없음, 오류
                logger.warning(f"Could not find closing tag for: {tag_name}")
                break
            
            if open_match != -1 and open_match < close_match:
                # 닫는 태그 전에 다른 여는 태그 발견
                nesting_level += 1
                search_pos = open_match + len(tag_name) + 1
                logger.debug(f"Found nested tag: {tag_name}, nesting level: {nesting_level}")
            else:
                # 닫는 태그 발견
                nesting_level -= 1
                search_pos = close_match + len(tag_name) + 3
                logger.debug(f"Found closing tag: {tag_name}, nesting level: {nesting_level}")
        
        if nesting_level == 0:
            # 완전한 요소 발견
            element_end = search_pos
            element_content = mapper_content[pos:element_end]
            
            # 요소 앞의 주석 찾기
            preceding_comment = ""
            for comment_start, comment_end, comment in reversed(comments):
                if comment_end <= pos:
                    # 요소 앞의 가장 최근 주석
                    preceding_comment = comment
                    logger.debug(f"Found comment before element: {preceding_comment[:30]}...")
                    break
            
            # 요소 ID 추출
            id_match = re.search(r'id\s*=\s*["\']([^"\']+)["\']', element_content)
            element_id = id_match.group(1) if id_match else f"{tag_name}_{len(level1_elements) + 1}"
            logger.debug(f"Element ID: {element_id}")
            
            level1_elements.append((preceding_comment, element_content, tag_name, element_id))
            pos = element_end
        else:
            # 잘못된 XML 구조, 계속 진행
            logger.warning(f"Malformed XML structure: Missing closing tag for {tag_name}")
            pos += 1
    
    logger.info(f"Extracted {len(level1_elements)} Level1 elements")
    
    # 각 Level1 요소 처리 및 저장
    for i, (comment, element_content, element_type, element_id) in enumerate(level1_elements, 1):
        # 순번이 포함된 출력 파일 이름 생성
        base_name = os.path.basename(xml_file_path)
        file_name_without_ext = os.path.splitext(base_name)[0]
        output_file_name = f"{file_name_without_ext}-{i:02d}-{element_type}-{element_id}.xml"
        output_path = os.path.join(output_folder, output_file_name)
        
        # 헤더, 주석, 요소가 포함된 XML 내용 생성
        output_content = f"""{xml_header}
{xml_doctype}
<mapper namespace="{namespace}">
{comment}
{element_content}
</mapper>
"""
        
        # 출력 파일에 쓰기
        try:
            with open(output_path, 'w', encoding='utf-8') as out_file:
                out_file.write(output_content)
            logger.info(f"Created file: {output_file_name}")
        except Exception as e:
            logger.error(f"Failed to save file: {output_file_name}, error: {str(e)}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Completed: Extracted {len(level1_elements)} Level1 elements (time: {duration:.2f} seconds)")
    
    return len(level1_elements)

def main():
    """
    명령줄 인수를 파싱하고 추출 함수를 호출하는 메인 함수입니다.
    """
    import argparse
    
    # 로그 레벨 선택 정의
    log_level_choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    parser = argparse.ArgumentParser(description='MyBatis XML Mapper 파일에서 Level1 요소 추출')
    parser.add_argument('-i', '--input', dest='xml_file', help='XML 파일 경로')
    parser.add_argument('-o', '--output', dest='output_folder', help='출력 폴더 경로')
    parser.add_argument('-l', '--log', help='로그 파일 경로', default=None)
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로깅 활성화 (--log-level DEBUG와 동일)')
    parser.add_argument('--log-level', choices=log_level_choices, default='INFO',
                        help='로그 레벨 설정 (기본값: INFO)')
    
    args = parser.parse_args()
    
    # 로그 레벨 결정
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = log_level_map[args.log_level]
    
    # 로거 설정
    logger = setup_logger(args.log, log_level)
    
    # 파일 존재 확인
    if not os.path.isfile(args.xml_file):
        logger.error(f"Error: XML file '{args.xml_file}' does not exist.")
        sys.exit(1)
    
    # XML 파일 처리
    try:
        extract_level1_elements(args.xml_file, args.output_folder, logger)
    except Exception as e:
        logger.error(f"Error occurred during processing: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
