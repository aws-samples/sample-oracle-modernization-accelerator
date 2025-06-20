#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TransformValidation.py - MyBatis XML 변환 검증 프로세스

이 프로그램은 MyBatis XML 파일의 변환을 다음과 같이 검증합니다:
1. 모든 파일이 올바르게 변환되었는지 확인 (각 원본 파일에 대응하는 변환된 파일이 있어야 함)
2. xmllint를 사용하여 모든 파일의 XML 구문 검증

사용법:
    python3 TransformValidation.py [옵션]

옵션:
    -h, --help                  도움말 표시
    -m, --mapper-folder         검증할 매퍼 파일이 있는 디렉토리
    -o, --origin-suffix         원본 파일의 접미사 (기본값: _orcl)
    -f, --transform-folder      변환 폴더 경로
    -l, --log                   로그 파일 경로 지정
    -v, --verbose               상세 로깅 활성화 (--log-level DEBUG와 동일)
    -t, --test                  기본 설정으로 테스트 모드 실행
    --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                로그 레벨 설정 (기본값: INFO)

예제:
    python3 TransformValidation.py -m /path/to/mapper -f /path/to/transform
    python3 TransformValidation.py --mapper-folder /path/to/mapper --origin-suffix _orcl --transform-folder /path/to/transform
"""

import os
import sys
import csv
import logging
import argparse
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# 로깅 설정
def setup_logger(log_file=None, log_level=logging.INFO):
    """로깅 구성을 초기화합니다.
    
    매개변수:
        log_file (str): 로그 파일 경로 (선택 사항)
        log_level (int): 콘솔 출력 로그 레벨
        
    반환값:
        logger: 구성된 로거 인스턴스
    """
    logger = logging.getLogger('TransformValidation')
    logger.setLevel(logging.DEBUG)  # 모든 정보를 캡처하기 위해 항상 로거를 DEBUG로 설정
    
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
        file_handler.setLevel(logging.DEBUG)  # 항상 모든 내용을 파일에 기록
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def validate_xml_with_xmllint(xml_file, logger):
    """xmllint를 사용하여 XML 파일을 검증합니다.
    
    매개변수:
        xml_file (str): 검증할 XML 파일 경로
        logger: 로거 인스턴스
        
    반환값:
        tuple: (유효성 상태, 오류 메시지)
    """
    try:
        # xmllint 명령 실행
        cmd = ["xmllint", "--noout", xml_file]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            # SQL 비교 연산자와 관련된 오류를 무시하도록 필터링
            filtered_errors = []
            for line in stderr.split('\n'):
                if not line.strip():
                    continue
                # SQL 비교 연산자 관련 오류 무시
                if 'StartTag: invalid element name' in line:
                    try:
                        # 오류가 발생한 라인 번호를 가져옴
                        line_num = int(line.split(':')[1].split()[0])
                        # 해당 라인의 내용을 읽어서 SQL 비교 연산자가 있는지 확인
                        with open(xml_file, 'r') as f:
                            content = f.readlines()
                            if line_num <= len(content):
                                error_line = content[line_num - 1].strip()
                                if any(op in error_line for op in ['<=', '>=', '<>', '!=', '<', '>', '=']):
                                    # 오류 라인과 다음 라인만 출력
                                    next_line = content[line_num].strip() if line_num < len(content) else ""
                                    logger.warning(f"Error in {os.path.basename(xml_file)} at line {line_num}:")
                                    logger.warning(f"  {error_line}")
                                    if next_line:
                                        logger.warning(f"  {next_line}")
                                    continue
                    except (ValueError, IndexError):
                        # 라인 번호 파싱 실패 시 해당 오류를 그대로 포함
                        pass
                filtered_errors.append(line)
            
            error_msg = '\n'.join(filtered_errors)
            if error_msg:
                logger.debug(f"Validation failed for {xml_file}: {error_msg}")
            return False, error_msg.strip()
        
        logger.debug(f"Validation successful for {xml_file}")
        return True, ""
    except Exception as e:
        logger.error(f"Error validating {xml_file}: {str(e)}")
        return False, str(e)


def check_transformation_completeness(mapper_folder, origin_suffix, logger):
    """모든 파일이 올바르게 변환되었는지 확인합니다.
    
    매개변수:
        mapper_folder (str): 매퍼 파일이 있는 디렉토리
        origin_suffix (str): 원본 파일의 접미사
        logger: 로거 인스턴스
        
    반환값:
        list: 변환에 실패한 파일 목록 (경로, 파일명, 오류 메시지)
    """
    failure_list = []
    
    try:
        # 매퍼 폴더에서 모든 XML 파일 찾기
        xml_files = []
        for root, _, files in os.walk(mapper_folder):
            for file in files:
                if file.endswith('.xml'):
                    xml_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(xml_files)} XML files in {mapper_folder}")
        
        # 기본 이름별로 파일 그룹화 (origin_suffix 제거)
        base_names = {}
        for xml_file in xml_files:
            file_name = os.path.basename(xml_file)
            if origin_suffix in file_name:
                base_name = file_name.replace(origin_suffix + '.xml', '.xml')
            else:
                base_name = file_name
            
            if base_name not in base_names:
                base_names[base_name] = []
            base_names[base_name].append(xml_file)
        
        logger.debug(f"Grouped files into {len(base_names)} base names")
        
        # 각 기본 이름에 정확히 2개의 파일(원본 및 변환된 파일)이 있는지 확인
        for base_name, files in base_names.items():
            if len(files) != 2:  # 원본 및 변환된 파일이 있어야 함
                for file_path in files:
                    if origin_suffix in os.path.basename(file_path):  # 실패 목록에 원본 파일만 추가
                        failure_list.append((
                            os.path.dirname(file_path),
                            os.path.basename(file_path),
                            "XML transformation failed"
                        ))
                        logger.warning(f"Transformation failure detected for {file_path}")
        
        logger.info(f"Found {len(failure_list)} files with transformation failures")
        return failure_list
    
    except Exception as e:
        logger.error(f"Error checking transformation completeness: {e}")
        return []

def validate_xml_files(mapper_folder, origin_suffix, logger):
    """xmllint를 사용하여 매퍼 폴더의 모든 XML 파일을 검증합니다.
    
    매개변수:
        mapper_folder (str): 매퍼 파일이 있는 디렉토리
        logger: 로거 인스턴스
        
    반환값:
        list: 검증 결과 목록 (경로, 파일명, 메시지)
    """
    result_list = []
    
    try:
        # 매퍼 폴더에서 origin_suffix가 없는 XML 파일만 찾기
        for root, _, files in os.walk(mapper_folder):
            files = [f for f in files if f.endswith('.xml') and origin_suffix not in f]
            for file in files:
                if file.endswith('.xml'):
                    xml_file = os.path.join(root, file)
                    valid, error_msg = validate_xml_with_xmllint(xml_file, logger)
                    
                    if valid:
                        result_list.append((
                            root,
                            file,
                            "Success"  # 성공
                        ))
                        logger.debug(f"XML validation successful for {file}")
                    else:
                        # 오류 메시지가 너무 길면 간소화
                        short_error = error_msg.split('\n')[0] if error_msg else "Unknown error"
                        result_list.append((
                            root,
                            file,
                            f"Error: {short_error}"  # 오류 메시지와 함께 실패
                        ))
                        logger.warning(f"XML validation failed for {file}: {short_error}")
        
        logger.info(f"Validated {len(result_list)} XML files")
        return result_list
    
    except Exception as e:
        logger.error(f"Error validating XML files: {e}")
        return []

def write_xmllint_result(results, output_file, logger):
    """xmllint 검증 결과를 CSV 파일에 기록합니다.
    
    매개변수:
        results (list): 검증 결과 목록 (경로, 파일명, 메시지)
        output_file (str): 출력 파일 경로
        logger: 로거 인스턴스
        
    반환값:
        bool: 성공 상태
    """
    try:
        # 기존 파일이 있으면 삭제
        if os.path.exists(output_file):
            os.remove(output_file)
            logger.debug(f"Removed existing file: {output_file}")
        
        # 결과를 CSV 파일에 기록
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(['Path', 'FileName', 'Message'])
            csv_writer.writerows(results)
        
        logger.info(f"XML validation results written to {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error writing XML validation results: {e}")
        return False

def create_failure_csv(failure_list, app_transform_folder, logger, origin_suffix='_orcl'):
    """변환 실패 목록으로 CSV 파일을 생성합니다.
    
    매개변수:
        failure_list (list): 변환에 실패한 파일 목록
        app_transform_folder (str): 변환 폴더 경로
        logger: 로거 인스턴스
        origin_suffix (str): 원본 파일의 접미사 (기본값: _orcl)
        
    반환값:
        bool: 성공 상태
    """
    try:
        # 경로 정의
        source_csv = os.path.join(app_transform_folder, 'SQLTransformTarget.csv')
        output_file = os.path.join(app_transform_folder, 'SQLTransformTargetFailure.csv')
        
        # 기존 파일이 있으면 삭제
        if os.path.exists(output_file):
            os.remove(output_file)
            logger.debug(f"Removed existing file: {output_file}")
        
        # 소스 CSV 읽기
        if os.path.exists(source_csv):
            with open(source_csv, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                header = next(csv_reader)
                rows = list(csv_reader)
            
            # 출력 CSV 작성
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                csv_writer = csv.writer(f)
                csv_writer.writerow(header)
                
                # 실패가 있으면 소스 CSV에서 일치하는 행 찾기
                if failure_list:
                    # 실패한 파일 이름에서 origin_suffix를 제거하여 기본 이름 추출
                    failed_base_names = []
                    for _, file_name, _ in failure_list:
                        base_name = os.path.basename(file_name)
                        if origin_suffix in base_name:
                            # origin_suffix와 .xml 확장자 제거
                            base_name = base_name.replace(origin_suffix, '')
                        failed_base_names.append(base_name)
                    
                    logger.debug(f"Failed base names (without suffix): {failed_base_names}")
                    
                    # 실패 항목 카운터
                    failure_count = 0
                    
                    for row in rows:
                        if row and len(row) > 1:
                            file_path = row[1].strip()
                            file_name = os.path.basename(file_path)
                            
                            # 파일 이름에서 확장자 제거
                            file_base_name = file_name
                            if file_base_name.endswith('.xml'):
                                file_base_name = file_base_name[:-4]  # .xml 제거
                            
                            for failed_name in failed_base_names:
                                # 확장자 제거
                                if failed_name.endswith('.xml'):
                                    failed_name = failed_name[:-4]  # .xml 제거
                                
                                # 정확한 이름 비교
                                if file_base_name == failed_name:
                                    csv_writer.writerow(row)
                                    failure_count += 1
                                    logger.debug(f"Match found: {file_name} matches {failed_name}")
                                    break
                    
                    logger.info(f"Failure CSV created at {output_file} with {failure_count} entries")
                else:
                    logger.info(f"Empty failure CSV (header only) created at {output_file}")
            
            return True
        else:
            logger.error(f"Source CSV file not found: {source_csv}")
            return False
    
    except Exception as e:
        logger.error(f"Error creating failure CSV: {e}")
        return False

def main():
    """메인 함수"""
    # 로그 레벨 선택 정의
    log_level_choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(description='MyBatis XML 변환 검증 프로세스')
    parser.add_argument('-m', '--mapper-folder', dest='mapper_folder', help='검증할 매퍼 파일이 있는 디렉토리')
    parser.add_argument('-o', '--origin-suffix', dest='origin_suffix', default='_orcl', help='원본 파일의 접미사 (기본값: _orcl)')
    parser.add_argument('-f', '--app-transform-folder', dest='app_transform_folder', help='변환 폴더 경로')
    parser.add_argument('-g', '--app-log-folder', dest='app_log_folder', help='log 폴더 경로')
    parser.add_argument('-l', '--log', help='로그 파일 경로 지정', default=None)
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로깅 활성화 (--log-level DEBUG와 동일)')
    parser.add_argument('-t', '--test', action='store_true', help='기본 설정으로 테스트 모드 실행')
    parser.add_argument('--log-level', choices=log_level_choices, default='INFO', help='로그 레벨 설정 (기본값: INFO)')
    
    args = parser.parse_args()
    
    # 로그 레벨 결정
    if args.verbose:
        log_level = logging.DEBUG
        log_level_str = 'DEBUG'
    else:
        log_level = log_level_map[args.log_level]
        log_level_str = args.log_level
    
    # 1. 기본 변수 설정
    test_mode = args.test
    
    if test_mode:
        # 테스트 모드의 기본값
        app_transform_folder = '$APP_TRANSFORM_FOLDER'
        mapper_folder = '$APP_TRANSFORM_FOLDER/mapper'
        log_level = logging.DEBUG
        log_level_str = 'DEBUG'
    else:
        # 명령줄 인수 또는 환경 변수에서 값 가져오기
        mapper_folder = args.mapper_folder or os.environ.get('MAPPER_FOLDER')
        app_transform_folder = args.app_transform_folder or os.environ.get('APP_TRANSFORM_FOLDER')
    
    app_log_folder = args.app_log_folder or os.environ.get('APP_LOGS_FOLDER')
    origin_suffix = args.origin_suffix
    
    # 먼저 콘솔 로깅만 설정 (필수 매개변수 검증용)
    logger = setup_logger(None, log_level)
    
    # 필수 매개변수가 설정되었는지 확인
    if not mapper_folder:
        logger.error("오류: MAPPER_FOLDER가 지정되지 않았습니다.")
        logger.error("매개변수로 제공하거나 MAPPER_FOLDER 환경 변수를 설정하세요.")
        sys.exit(1)
    
    if not app_transform_folder:
        logger.error("오류: APP_TRANSFORM_FOLDER가 지정되지 않았습니다.")
        logger.error("매개변수로 제공하거나 APP_TRANSFORM_FOLDER 환경 변수를 설정하세요.")
        sys.exit(1)
    
    # 로그 폴더 설정
    log_folder = app_log_folder
    os.makedirs(log_folder, exist_ok=True)
    
    # 로그 파일 설정
    if not args.log:
        log_file = os.path.join(log_folder, f"TransformValidation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    else:
        log_file = args.log
    
    # 파일 로깅 추가 (기존 로거 업데이트)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # 항상 모든 내용을 파일에 기록
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.debug(f"로그 파일이 설정되었습니다: {log_file}")
    
    logger.info("Starting TransformValidation.py")
    logger.info(f"Mapper Folder: {mapper_folder}")
    logger.info(f"Origin Suffix: {origin_suffix}")
    logger.info(f"Transform Folder: {app_transform_folder}")
    logger.info(f"Test Mode: {test_mode}")
    logger.info(f"Log Level: {log_level_str}")
    
    # 2. 검증 1: 변환 완전성 확인
    logger.info("Starting validation : Checking transformation completeness")
    failure_list = check_transformation_completeness(mapper_folder, origin_suffix, logger)
    
    # SQLTransformTargetFailure.csv 생성
    create_failure_csv(failure_list, app_transform_folder, logger, origin_suffix)
    
    # 3. 검증 2: XML 구문 검증
    logger.info("Starting validation : Validating XML syntax")
    xmllint_results = validate_xml_files(mapper_folder, origin_suffix, logger)
    
    # xmllintResult.csv 생성
    xmllint_result_file = os.path.join(app_transform_folder, 'xmllintResult.csv')
    write_xmllint_result(xmllint_results, xmllint_result_file, logger)
    
    # 4. 요약
    logger.info("Validation process completed")
    logger.info(f"Total files checked: {len(xmllint_results)}")
    logger.info(f"Transformation failures: {len(failure_list)}")
    
    # XML 검증 실패 수 계산
    xml_failures = sum(1 for _, _, msg in xmllint_results if msg.startswith('Error'))
    logger.info(f"XML validation failures: {xml_failures}")
    
    if failure_list or xml_failures > 0:
        logger.warning("Validation found issues. Check the output files for details.")
        sys.exit(1)
    
    logger.info("All validations completed successfully")

if __name__ == "__main__":
    main()
