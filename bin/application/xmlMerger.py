#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
xmlMerger.py - XML 파일 병합 도구

이 프로그램은 지정된 입력 폴더에 있는 모든 XML 파일을 이름 순서대로 정렬하여
하나의 XML 파일로 병합합니다. 병합 시 각 XML 파일의 내부 구조는 변경하지 않고
그대로 유지합니다.

기능:
- 입력 폴더의 XML 파일들을 이름 순서대로 정렬하여 병합
- XML 헤더, DOCTYPE, 네임스페이스 보존
- 각 요소의 주석과 내부 구조 보존
- 상세 로깅 기능

사용법:
    python3 xmlMerger.py [옵션]

옵션:
    -h, --help                  도움말 표시
    -i, --input                 병합할 XML 파일들이 있는 폴더 경로
    -o, --output                출력 XML 파일 경로
    -l, --log                   로그 파일 경로 지정
    -v, --verbose               상세 로깅 활성화 (DEBUG 레벨과 동일)
    --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                로그 레벨 설정 (기본값: INFO)

실행 예시:
    # 기본 사용법
    python3 xmlMerger.py --input /path/to/input/folder --output /path/to/output.xml
    
    # 상세 로깅 활성화
    python3 xmlMerger.py -v -i /path/to/input/folder -o /path/to/output.xml
    
    # 로그 파일 지정 및 로그 레벨 설정
    python3 xmlMerger.py -l /path/to/merge.log --log-level WARNING -i /path/to/input/folder -o /path/to/output.xml
"""

import os
import re
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

# 로깅 설정
def setup_logger(log_file=None, log_level=logging.INFO):
    """로깅 설정을 초기화합니다.
    
    Args:
        log_file (str): 로그 파일 경로 (선택사항)
        log_level (int): 콘솔 출력용 로깅 레벨
        
    Returns:
        logger: 설정된 로거 인스턴스
    """
    logger = logging.getLogger('XMLMerger')
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

def extract_xml_parts(xml_file_path, logger):
    """
    XML 파일에서 헤더, DOCTYPE, 네임스페이스, mapper 내용을 추출합니다.
    
    Args:
        xml_file_path (str): XML 파일 경로
        logger: 로거 인스턴스
        
    Returns:
        tuple: (xml_header, xml_doctype, namespace, mapper_content)
    """
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()
        logger.debug(f"Successfully read XML file: {xml_file_path}")
    except Exception as e:
        logger.error(f"Failed to read XML file {xml_file_path}: {str(e)}")
        return None, None, None, None
    
    # XML 헤더 추출
    header_match = re.search(r'(<\?xml.*?\?>)', xml_content, re.DOTALL)
    xml_header = header_match.group(1) if header_match else '<?xml version="1.0" encoding="UTF-8"?>'
    
    # DOCTYPE 추출
    doctype_match = re.search(r'(<!DOCTYPE.*?>)', xml_content, re.DOTALL)
    xml_doctype = doctype_match.group(1) if doctype_match else '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">'
    
    # 네임스페이스 추출
    namespace_pattern = re.compile(r'<mapper\s+namespace\s*=\s*["\']([^"\']+)["\']')
    namespace_match = namespace_pattern.search(xml_content)
    namespace = namespace_match.group(1) if namespace_match else "Unknown"
    
    # mapper 내용 추출 (<mapper>와 </mapper> 사이의 모든 내용)
    mapper_start_match = re.search(r'<mapper\s+namespace\s*=\s*["\'][^"\']+["\'][^>]*>', xml_content)
    mapper_end_match = re.search(r'</mapper>\s*$', xml_content)
    
    if not mapper_start_match or not mapper_end_match:
        logger.error(f"Could not find mapper tags in {xml_file_path}")
        return xml_header, xml_doctype, namespace, None
    
    mapper_content = xml_content[mapper_start_match.end():mapper_end_match.start()]
    
    return xml_header, xml_doctype, namespace, mapper_content

def merge_xml_files(input_folder, output_file, logger):
    """
    입력 폴더의 XML 파일들을 하나의 출력 파일로 병합합니다.
    
    Args:
        input_folder (str): XML 파일들이 있는 폴더 경로
        output_file (str): 출력 XML 파일 경로
        logger: 로거 인스턴스
        
    Returns:
        bool: 성공 시 True, 실패 시 False
    """
    start_time = datetime.now()
    logger.info(f"Starting XML merge process from {input_folder} to {output_file}")
    
    # 입력 폴더의 XML 파일 목록 가져오기
    try:
        xml_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.xml')]
        xml_files.sort()  # 파일을 이름 순서대로 정렬
        logger.info(f"Found {len(xml_files)} XML files to merge")
        logger.debug(f"Files to merge: {', '.join(xml_files)}")
    except Exception as e:
        logger.error(f"Failed to list files in {input_folder}: {str(e)}")
        return False
    
    if not xml_files:
        logger.warning(f"No XML files found in {input_folder}")
        return False
    
    # 첫 번째 파일에서 헤더, DOCTYPE, 네임스페이스 가져오기
    first_file = os.path.join(input_folder, xml_files[0])
    xml_header, xml_doctype, namespace, _ = extract_xml_parts(first_file, logger)
    
    if not namespace:
        logger.error(f"Could not determine namespace from {first_file}")
        return False
    
    logger.info(f"Using namespace: {namespace}")
    
    # 병합된 내용 준비
    merged_content = []
    
    # 각 XML 파일 처리
    for xml_file in xml_files:
        file_path = os.path.join(input_folder, xml_file)
        logger.debug(f"Processing file: {xml_file}")
        
        _, _, _, mapper_content = extract_xml_parts(file_path, logger)
        
        if mapper_content is None:
            logger.warning(f"Skipping file {xml_file} due to parsing errors")
            continue
        
        # 병합 결과에 내용 추가
        merged_content.append(mapper_content)
        logger.debug(f"Added content from {xml_file}")
    
    # 최종 병합 XML 생성
    final_xml = f"""{xml_header}
{xml_doctype}
<mapper namespace="{namespace}">
{"".join(merged_content)}
</mapper>
"""
    
    # 병합된 XML을 출력 파일에 쓰기
    try:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            out_file.write(final_xml)
        logger.info(f"Successfully wrote merged XML to {output_file}")
    except Exception as e:
        logger.error(f"Failed to write output file {output_file}: {str(e)}")
        return False
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"XML merge completed in {duration:.2f} seconds")
    
    return True

def main():
    """
    명령줄 인수를 파싱하고 병합 함수를 호출하는 메인 함수입니다.
    """
    # 로그 레벨 선택 정의
    log_level_choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    parser = argparse.ArgumentParser(description='폴더의 XML 파일들을 하나의 XML 파일로 병합')
    parser.add_argument('-i', '--input', dest='input_folder', help='병합할 XML 파일들이 있는 폴더 경로')
    parser.add_argument('-o', '--output', dest='output_file', help='출력 XML 파일 경로')
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
    
    # 입력 폴더 존재 확인
    if not os.path.isdir(args.input_folder):
        logger.error(f"Error: Input folder '{args.input_folder}' does not exist.")
        sys.exit(1)
    
    # 출력 디렉토리가 없으면 생성
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logger.debug(f"Created output directory: {output_dir}")
        except Exception as e:
            logger.error(f"Failed to create output directory {output_dir}: {str(e)}")
            sys.exit(1)
    
    # XML 파일 병합
    success = merge_xml_files(args.input_folder, args.output_file, logger)
    
    if not success:
        logger.error("XML merge process failed")
        sys.exit(1)
    
    logger.info("XML merge process completed successfully")

if __name__ == "__main__":
    main()
