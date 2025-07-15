#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLTransformTarget.py - MyBatis XML 변환 대상 처리 프로그램

    V2.0 Q Develiper 효율을 위한 XML Extract, Merge 기능 별도 구성
    V1.0 FileBased 변환 대상 처리 프로그램. ZZ.Temp/V1 폴더에 있음

이 프로그램은 MyBatis XML 파일을 변환하는 프로세스를 수행합니다:
1. 변환 대상 목록 CSV 파일에서 대상 파일 읽기
2. 각 XML 파일을 추출, 변환, 병합하는 과정 수행
    - 추출 : xmlExtractor.py
    - 변환 : q chat --trust-all-tools --no-interactive < {temp_prompt_file} > {log_file}
    - 병합 : xmlMerger.py
3. 변환 결과 검증
    - xmllint 유효성 검사
    

사용법:
    python3 SQLTransformTarget.py [옵션]

옵션:
    -h, --help                  도움말 표시
    -f, --file                  변환 대상 목록 CSV 파일 경로
    -o, --origin-suffix         원본 파일 접미사 (기본값: _src)
    -s, --transform-suffix      변환 파일 접미사 (기본값: _tgt)
    -l, --log                   로그 파일 경로
    -v, --verbose               상세 로깅 활성화 (--log-level DEBUG와 동일)
    -t, --test                  테스트 모드 활성화
    --use-sudo                  파일 복사 시 sudo 사용 (권한 이슈 해결)
    --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                로그 레벨 설정 (기본값: INFO)

예제:
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv
    python3 SQLTransformTarget.py --file /path/to/SQLTransformTarget.csv --origin-suffix _src --transform-suffix _tgt
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv --use-sudo
"""

import os
import sys
import csv
import logging
import argparse
import shutil
import subprocess
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime

# 로깅 설정
def setup_logger(log_file=None, log_level=logging.INFO):
    """로깅 설정을 초기화합니다."""
    logger = logging.getLogger('SQLTransformTarget')
    logger.setLevel(logging.DEBUG)
    
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
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def run_command(cmd, logger, cwd=None):
    """외부 명령을 실행하고 출력을 로깅합니다."""
    logger.debug(f"Running command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=cwd
        )
        
        # 실시간으로 출력 처리
        for line in process.stdout:
            line = line.strip()
            if line:
                # 하위 프로세스의 로그 레벨을 유지하면서 출력
                if line.startswith("INFO:"):
                    logger.info(f"SUBPROCESS: {line[5:].strip()}")
                elif line.startswith("WARNING:"):
                    logger.warning(f"SUBPROCESS: {line[8:].strip()}")
                elif line.startswith("ERROR:"):
                    logger.error(f"SUBPROCESS: {line[6:].strip()}")
                elif line.startswith("DEBUG:"):
                    logger.debug(f"SUBPROCESS: {line[6:].strip()}")
                else:
                    logger.info(f"SUBPROCESS: {line}")
        
        # 오류 출력 처리
        for line in process.stderr:
            line = line.strip()
            if line:
                if line.startswith("INFO:"):
                    logger.info(f"SUBPROCESS: {line[5:].strip()}")
                elif line.startswith("WARNING:"):
                    logger.warning(f"SUBPROCESS: {line[8:].strip()}")
                elif line.startswith("ERROR:"):
                    logger.error(f"SUBPROCESS: {line[6:].strip()}")
                elif line.startswith("DEBUG:"):
                    logger.debug(f"SUBPROCESS: {line[6:].strip()}")
                else:
                    logger.warning(f"SUBPROCESS ERROR: {line}")
        
        process.wait()
        return process.returncode
    
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return -1

def ensure_directory(directory, logger, use_sudo=False):
    """디렉토리가 존재하는지 확인하고, 없으면 생성합니다. 권한 이슈 시 sudo를 사용할 수 있습니다."""
    try:
        # 디렉토리가 이미 존재하는지 확인
        if os.path.exists(directory):
            logger.debug(f"Directory already exists: {directory}")
            return True
            
        # 일반 생성 시도
        if not use_sudo:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"Directory created: {directory}")
                return True
            except PermissionError as pe:
                logger.warning(f"Permission denied for normal mkdir, trying with sudo: {pe}")
                # 권한 오류 시 sudo로 재시도
                return ensure_directory(directory, logger, use_sudo=True)
        else:
            # sudo를 사용한 디렉토리 생성
            cmd = ["sudo", "mkdir", "-p", directory]
            result = run_command(cmd, logger)
            if result == 0:
                logger.debug(f"Directory created with sudo: {directory}")
                return True
            else:
                logger.error(f"Failed to create directory with sudo: {directory}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        if not use_sudo:
            logger.info("Retrying directory creation with sudo...")
            return ensure_directory(directory, logger, use_sudo=True)
        return False

def copy_file(source, destination, logger, use_sudo=False):
    """파일을 복사합니다. 권한 이슈 시 sudo를 사용할 수 있습니다."""
    try:
        # 대상 디렉토리가 없으면 생성
        dest_dir = os.path.dirname(destination)
        if not ensure_directory(dest_dir, logger, use_sudo):
            return False
        
        # 일반 복사 시도
        if not use_sudo:
            try:
                shutil.copy2(source, destination)
                logger.debug(f"Copied file from {source} to {destination}")
                return True
            except PermissionError as pe:
                logger.warning(f"Permission denied for normal copy, trying with sudo: {pe}")
                # 권한 오류 시 sudo로 재시도
                return copy_file(source, destination, logger, use_sudo=True)
        else:
            # sudo를 사용한 복사
            cmd = ["sudo", "cp", "-p", source, destination]
            result = run_command(cmd, logger)
            if result == 0:
                logger.debug(f"Copied file with sudo from {source} to {destination}")
                return True
            else:
                logger.error(f"Failed to copy file with sudo from {source} to {destination}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to copy file from {source} to {destination}: {e}")
        if not use_sudo:
            logger.info("Retrying with sudo...")
            return copy_file(source, destination, logger, use_sudo=True)
        return False

def read_transform_target_list(file_path, logger):
    """변환 대상 목록 CSV 파일을 읽습니다."""
    target_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            header = next(csv_reader, None)  # 헤더 행 건너뛰기
            for row in csv_reader:
                if row and len(row) > 1 and row[1].strip() and not row[1].startswith('#'):
                    target_list.append(row[1].strip())
        
        logger.info(f"Read {len(target_list)} targets from {file_path}")
        logger.debug(f"Target list: {target_list}")
        return target_list
    
    except Exception as e:
        logger.error(f"Failed to read transform target list from {file_path}: {e}")
        return []

def process_xml_file(xml_file, origin_suffix, transform_suffix, mapper_folder, source_sql_mapper_folder, target_sql_mapper_folder, prompt_file, qlog_folder, qprompt_folder, log_level, logger, java_source_folder, use_sudo=False):
    """XML 파일을 처리합니다 (추출, 변환, 병합)."""
    try:
        # 1. 파일 경로 분석
        xml_path = Path(xml_file)
        xml_name = xml_path.name
        xml_stem = xml_path.stem
        
        # 원본 파일이 이미 접미사를 가지고 있는지 확인
        if origin_suffix in xml_stem:
            logger.warning(f"File {xml_name} already has origin suffix {origin_suffix}")
        
        # 매퍼 폴더 내 상대 경로 구성 (SOURCE_SQL_MAPPER_FOLDER 환경변수 기준)
        logger.info(f"XML parent path: {str(xml_path.parent)}")
        logger.info(f"Source SQL mapper folder: {source_sql_mapper_folder}")
        
        # SOURCE_SQL_MAPPER_FOLDER를 기준으로 상대 경로 추출
        xml_parent_path = str(xml_path.parent)
        source_mapper_path = os.path.abspath(source_sql_mapper_folder)
        
        # XML 파일이 SOURCE_SQL_MAPPER_FOLDER 하위에 있는지 확인
        if xml_parent_path.startswith(source_mapper_path):
            # SOURCE_SQL_MAPPER_FOLDER 이후의 상대 경로 추출
            relative_path = os.path.relpath(xml_parent_path, source_mapper_path)
            if relative_path == ".":
                transform_subfolderstructure = ""
            else:
                transform_subfolderstructure = relative_path
            logger.info(f"Extracted subfolder structure from SOURCE_SQL_MAPPER_FOLDER: {transform_subfolderstructure}")
        else:
            # XML 파일이 SOURCE_SQL_MAPPER_FOLDER 하위에 없는 경우, SOURCE_SQL_MAPPER_FOLDER 이후 경로를 직접 추출
            logger.warning(f"XML file is not under SOURCE_SQL_MAPPER_FOLDER. Extracting path after SOURCE_SQL_MAPPER_FOLDER.")
            
            # SOURCE_SQL_MAPPER_FOLDER 경로 이후의 경로 추출
            if source_mapper_path in xml_parent_path:
                # SOURCE_SQL_MAPPER_FOLDER 이후의 경로 추출
                after_source_mapper = xml_parent_path.replace(source_mapper_path, "").strip("/\\")
                transform_subfolderstructure = after_source_mapper
                logger.info(f"Extracted subfolder structure after SOURCE_SQL_MAPPER_FOLDER: {transform_subfolderstructure}")
            else:
                transform_subfolderstructure = ""
                logger.warning("Could not find SOURCE_SQL_MAPPER_FOLDER in path, using empty string")
        
        # 2. 복사 대상 폴더 구조 생성
        cp_target_folder_structure = transform_subfolderstructure
        cp_targetfile_name = f"{xml_stem}{origin_suffix}{xml_path.suffix}"
        
        # 복사 대상 경로 구성 (TARGET_SQL_MAPPER_FOLDER 기준)
        cp_target_folder = os.path.join(target_sql_mapper_folder, cp_target_folder_structure)
        cp_target_path = os.path.join(cp_target_folder, cp_targetfile_name)
        
        # 폴더 생성 (권한 이슈 시 자동으로 sudo 재시도)
        if not ensure_directory(cp_target_folder, logger):
            logger.error(f"Failed to create target folder: {cp_target_folder}")
            return False, None
        logger.info(f"Created folder structure: {cp_target_folder}")
        
        # 3. 파일 복사 - origin 폴더에 복사
        # xmlExtractor.py 호출을 위한 출력 폴더 구성
        xml_file_basename = Path(xml_file).stem
        logger.debug(f"XML file basename: {xml_file_basename}")
        xmlwork_folder = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename)
        origin_folder = os.path.join(xmlwork_folder, "origin")
        
        # origin 폴더 생성
        if not ensure_directory(origin_folder, logger):
            logger.error(f"Failed to create origin folder: {origin_folder}")
            return False, None
        logger.info(f"Created origin folder: {origin_folder}")
        
        # origin 폴더에 파일 복사 (source prefix 추가)
        origin_file_name = f"{xml_stem}{origin_suffix}{xml_path.suffix}"
        origin_file_path = os.path.join(origin_folder, origin_file_name)
        if not copy_file(xml_file, origin_file_path, logger, use_sudo):
            logger.error(f"Failed to copy file to origin folder: {origin_file_path}")
            return False, None
        logger.info(f"Copied {xml_file} to {origin_file_path}")
        
        # 복사된 파일 목록
        cp_targetfiles = [origin_file_path]
        logger.debug(f"Target files list: {cp_targetfiles}")
        
        # 4. xmlExtractor.py 호출을 위한 출력 폴더 구성 (이미 위에서 설정됨)
        xmlwork_folder = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename)    # 추출, 변환, 병합 의 Root 폴더 구조 생성
        xmlextract_folder = os.path.join(xmlwork_folder, "extract")                                         # 추출 폴더 구조 생성
        ensure_directory(xmlextract_folder, logger)
        
        # 5. xmlExtractor.py 호출 전제 조건 : 폴더가 이미 존재하면 삭제
        extract_folder = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename, "extract")
        app_transform_folder = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename, "transform")
        merge_folder = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename, "merge")
        status_file = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename, "status.txt")

        # 폴더 삭제
        for folder in [extract_folder, app_transform_folder, merge_folder]:
            if os.path.exists(folder):
                logger.info(f"Removing existing folder: {folder}")
                shutil.rmtree(folder)

        # status.txt 파일 삭제
        if os.path.exists(status_file):
            logger.info(f"Removing existing status file: {status_file}")
            os.remove(status_file)

        # 5. xmlExtractor.py 호출 - 로그 레벨 전달 (복사된 파일 사용)
        extractor_cmd = [
            "python3",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "xmlExtractor.py"),
            "--input", origin_file_path,  # 복사된 파일 사용
            "--output", xmlextract_folder,
            f"--log-level={log_level}"
        ]
        
        if run_command(extractor_cmd, logger) != 0:
            logger.error(f"xmlExtractor.py failed for {origin_file_path}")
            return False, None
        
        logger.info(f"Successfully extracted Level1 elements from {origin_file_path}")
        
        # 6. 추출된 파일 목록 구성
        xmlextract_l1list = [os.path.join(xmlextract_folder, f) for f in os.listdir(xmlextract_folder) if f.endswith('.xml')]
        logger.debug(f"Extracted {len(xmlextract_l1list)} Level1 elements")
        
        # 7. 변환 폴더 구성
        xmltransform_folder = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename, "transform")
        ensure_directory(xmltransform_folder, logger)
        
        # 8. 추출된 파일 변환 (파일명 패턴 변경) 
        try:
            # Prmpt 화일 구성
            # Read prompt template
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
                logger.info(f"Read prompt template from {prompt_file}")
            
            # Prompt 파라미터 조정
            prompt = prompt_template.replace("{L1FolderName}", xmlwork_folder)
            logger.debug(f"Prompt template processed for folder: {xmlwork_folder}")

            prompt = prompt.replace("{MAPPER_SRCL1_DIR}", extract_folder)
            logger.debug(f"Replaced MAPPER_SRCL1_DIR with {extract_folder} in prompt")
            
            # Replace target folder name in prompt with processed_folder/MAPPER_TGTL1_DIR
            prompt = prompt.replace("{MAPPER_TGTL1_DIR}", xmltransform_folder)
            logger.debug(f"Replaced MAPPER_TGTL1_DIR with {xmltransform_folder} in prompt")
            
            # Replace ORIGIN_SUFFIX in prompt with origin_suffix
            prompt = prompt.replace("{ORIGIN_SUFFIX}", origin_suffix)
            logger.debug(f"Replaced ORIGIN_SUFFIX with {origin_suffix} in prompt")

            prompt = prompt.replace("{TRANSFORM_SUFFIX}", transform_suffix)
            logger.debug(f"Replaced TRANSFORM_SUFFIX with {transform_suffix} in prompt")


            prompt_filename = xml_file_basename + ".prompt"
            temp_prompt_file = os.path.join(qprompt_folder, prompt_filename)
            with open(temp_prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
                logger.info(f"Created temporary prompt file: {temp_prompt_file}")

            # Q Transfrom 수행
            log_file = os.path.join(qlog_folder, f"{xml_file_basename}.log")

            logger.info(f"Executing command: q chat --trust-all-tools --no-interactive < {temp_prompt_file} > {log_file}")        
            cmd = f"q chat --trust-all-tools --no-interactive < {temp_prompt_file} > {log_file}"

            cmd_history_file = os.path.join(qprompt_folder, "qchat_command_history.log")
            with open(cmd_history_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {cmd}\n")
                logger.info(f"Command saved to history: {cmd_history_file}")
                
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Command execution failed for {xmlwork_folder}. Error: {result.stderr}")
                return False, f"Command execution failed for {xmlwork_folder}. Error: {result.stderr}"
            else:
                logger.info(f"Command executed successfully for {xmlwork_folder}")
                logger.debug(f"Command output: {result.stdout}")

        except Exception as e:
            logger.error(f"Error processing {xmlwork_folder}: {str(e)}", exc_info=True)
            return False, f"Error processing {xmlwork_folder}: {str(e)}"

        
        # 9. 병합 폴더 구성
        xmlmerge_folder = os.path.join(mapper_folder, cp_target_folder_structure, xml_file_basename, "merge")
        ensure_directory(xmlmerge_folder, logger)
        
        # 10. 병합 파일명 구성
        xmlmerge_file = os.path.join(xmlmerge_folder, xml_stem.replace(origin_suffix, transform_suffix) + xml_path.suffix)
        logger.info(f"Merge file will be created at: {xmlmerge_file}")
        
        # 11. xmlMerger.py 호출 - 로그 레벨 전달
        merger_cmd = [
            "python3",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "xmlMerger.py"),
            "--input", xmltransform_folder,
            "--output", xmlmerge_file,
            f"--log-level={log_level}"
        ]
        
        if run_command(merger_cmd, logger) != 0:
            logger.error(f"xmlMerger.py failed for {xmltransform_folder}")
            return False, None
        
        logger.info(f"Successfully merged transformed files to {xmlmerge_file}")
        
        # 12. 최종 변환 결과 파일 경로 구성
        final_transform_file = os.path.join(
            cp_target_folder,
            xml_stem.replace(origin_suffix, "") + xml_path.suffix
        )

        # 13. 변환 결과 파일 복사 (sudo 옵션 적용)
        if not copy_file(xmlmerge_file, final_transform_file, logger, use_sudo):
            logger.error(f"Failed to copy final transformed file to {final_transform_file}")
            return False, None
        
        logger.info(f"Successfully copied final transformed file to {final_transform_file}")
        
        return True, final_transform_file
    
    except Exception as e:
        logger.error(f"Error processing XML file {xml_file}: {e}")
        return False, None



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
    parser = argparse.ArgumentParser(description='MyBatis XML 변환 대상 처리 프로그램')
    parser.add_argument('-f', '--file', dest='transform_target_list', help='변환 대상 목록 CSV 파일 경로')
    parser.add_argument('-o', '--origin-suffix', dest='origin_suffix', default='_src', help='원본 파일 접미사 (기본값: _src)')
    parser.add_argument('-s', '--transform-suffix', dest='transform_suffix', default='_tgt', help='변환 파일 접미사 (기본값: _tgt)')
    parser.add_argument('-l', '--log', help='로그 파일 경로', default=None)
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로깅 활성화 (--log-level DEBUG와 동일)')
    parser.add_argument('--log-level', choices=log_level_choices, default='INFO',
                        help='로그 레벨 설정 (기본값: INFO)')
    parser.add_argument('-t', '--test', action='store_true', help='테스트 모드 활성화')
    parser.add_argument('--use-sudo', action='store_true', help='파일 복사 시 sudo 사용 (권한 이슈 해결)')
    
    args = parser.parse_args()
    
    # 로그 레벨 결정
    if args.verbose:
        log_level = logging.DEBUG
        log_level_str = 'DEBUG'
    else:
        log_level = log_level_map[args.log_level]
        log_level_str = args.log_level
    
    # 1. 기초 변수 설정 
    # 환경 변수 설정
    if args.test:
        # 테스트 모드 기본값 설정
        application_name = 'bnd_b2eg'
        oma_base_dir = '/Users/changik//workspace/oracle-modernization-accelerator/'
        app_assessment_folder = '/Users/changik//workspace/oracle-modernization-accelerator/Application/bnd_b2eg/Assessments'
        app_transform_folder = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Transform'
        transform_target_list = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Transform/SQLTransformTarget.csv'
        app_tools_folder = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Tools'
        
        # TARGET_DBMS_TYPE에 따른 프롬프트 파일 선택
        target_dbms_type = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
        if target_dbms_type == 'postgres':
            prompt_file = os.path.join(app_tools_folder, "sqlTransformTargetPgRules.md")
        elif target_dbms_type == 'mysql':
            prompt_file = os.path.join(app_tools_folder, "sqlTransformTargetMysqlRules.md")
        else:
            # 기본값으로 postgres 사용
            prompt_file = os.path.join(app_tools_folder, "sqlTransformTargetPgRules.md")
            logger.warning(f"Unknown TARGET_DBMS_TYPE: {target_dbms_type}, using postgres rules")
        
        log_level_str = 'DEBUG'
        java_source_folder = '/Users/changik//workspace/oracle-modernization-accelerator/SampleApp/jpetstore-6/src'
        source_sql_mapper_folder = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Transform/mapper'
        target_sql_mapper_folder = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Transform/mapper_target'
    else:
        # 환경 변수에서 값 가져오기
        application_name = os.environ.get('APPLICATION_NAME')
        oma_base_dir = os.environ.get('OMA_BASE_DIR')
        app_assessment_folder = os.environ.get('APPLICATION_FOLDER')
        app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER')
        app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
        app_logs_folder = os.environ.get('APP_LOGS_FOLDER')
        
        # TARGET_DBMS_TYPE에 따른 프롬프트 파일 선택
        target_dbms_type = os.environ.get('TARGET_DBMS_TYPE', 'postgres').lower()
        if target_dbms_type == 'postgres':
            prompt_file = os.path.join(app_tools_folder, "sqlTransformTargetPgRules.md")
        elif target_dbms_type == 'mysql':
            prompt_file = os.path.join(app_tools_folder, "sqlTransformTargetMysqlRules.md")
        else:
            # 기본값으로 postgres 사용
            prompt_file = os.path.join(app_tools_folder, "sqlTransformTargetPgRules.md")
        
        java_source_folder = os.environ.get('JAVA_SOURCE_FOLDER')
        source_sql_mapper_folder = os.environ.get('SOURCE_SQL_MAPPER_FOLDER')
        target_sql_mapper_folder = os.environ.get('TARGET_SQL_MAPPER_FOLDER')
        
        # 환경 변수 확인
        if not all([application_name, oma_base_dir, app_assessment_folder, app_transform_folder, source_sql_mapper_folder, target_sql_mapper_folder]):
            print("Error: Required environment variables are not set.")
            print("Please set APPLICATION_NAME, OMA_BASE_DIR, APPLICATION_FOLDER, APP_TRANSFORM_FOLDER, SOURCE_SQL_MAPPER_FOLDER, and TARGET_SQL_MAPPER_FOLDER.")
            sys.exit(1)
    
    # 스레드 수 설정
    thread_count = int(os.environ.get('THREAD_COUNT', 1))
    
    # 파라미터값 변수 설정
    transform_target_list = args.transform_target_list
    if not transform_target_list:
        transform_target_list = os.path.join(app_transform_folder, 'SQLTransformTarget.csv')
    
    origin_suffix = args.origin_suffix
    if not origin_suffix:
        print("Error: ORIGIN_SUFFIX parameter is required.")
        sys.exit(1)
    
    transform_suffix = args.transform_suffix
    if not transform_suffix:
        print("Error: TRANSFORM_SUFFIX parameter is required.")
        sys.exit(1)
    
    # 폴더 구조 생성 및 변수 설정
    log_folder = os.path.join(app_logs_folder, 'SQLTransformTarget')
    qlog_folder = os.path.join(log_folder, 'qlogs')
    qprompt_folder = os.path.join(log_folder, 'prompts')
    pylog_folder = os.path.join(log_folder, 'pylogs')
    mapper_processing_folder = os.path.join(log_folder, 'mapper')
    
    # 필요한 폴더 생성
    for folder in [log_folder, qlog_folder, qprompt_folder, pylog_folder, mapper_processing_folder, source_sql_mapper_folder, target_sql_mapper_folder]:
        os.makedirs(folder, exist_ok=True)
    
    # 로그 파일 경로 설정
    if not args.log:
        log_file = os.path.join(pylog_folder, f"sqlTransformTarget_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    else:
        log_file = args.log
    
    # 로거 설정
    logger = setup_logger(log_file, log_level)
    
    logger.info("Starting sqlTransformTarget.py")
    logger.info(f"Application Name: {application_name}")
    logger.info(f"OMA Base Directory: {oma_base_dir}")
    logger.info(f"Assessment Folder: {app_assessment_folder}")
    logger.info(f"Transform Folder: {app_transform_folder}")
    logger.info(f"Transform Target List: {transform_target_list}")
    logger.info(f"Target DBMS Type: {os.environ.get('TARGET_DBMS_TYPE', 'postgres')}")
    logger.info(f"Prompt File: {prompt_file}")
    
    # 프롬프트 파일 존재 여부 확인
    if not os.path.exists(prompt_file):
        logger.error(f"Prompt file not found: {prompt_file}")
        logger.error("Please ensure the appropriate transformation rules file exists:")
        logger.error("- For PostgreSQL: sqlTransformTargetPgRules.md")
        logger.error("- For MySQL: sqlTransformTargetMysqlRules.md")
        sys.exit(1)
    else:
        logger.info(f"Using transformation rules file: {os.path.basename(prompt_file)}")
    
    logger.info(f"Origin Suffix: {origin_suffix}")
    logger.info(f"Transform Suffix: {transform_suffix}")
    logger.info(f"Test Mode: {args.test}")
    logger.info(f"Thread Count: {thread_count}")
    logger.info(f"Application Source Folder: {java_source_folder}")    
    
    # 2. 변환 대상 목록 읽기
    target_files = read_transform_target_list(transform_target_list, logger)
    
    if not target_files:
        logger.error(f"No target files found in {transform_target_list}")
        sys.exit(1)
    
    # 3. 각 대상 파일 처리 (멀티스레드)
    # 결과를 저장할 딕셔너리 (스레드 안전을 위해 락 사용)
    results_lock = threading.Lock()
    results = {
        'successful': 0,
        'failed': 0,
        'total': len(target_files)
    }
    
    # 파일 처리 함수 (스레드에서 실행)
    def process_file(target_file):
        thread_name = threading.current_thread().name
        logger.info(f"[{thread_name}] Processing target file: {target_file}")
        
        success, transformed_file = process_xml_file(
            target_file,
            origin_suffix,
            transform_suffix,
            mapper_processing_folder,
            source_sql_mapper_folder,
            target_sql_mapper_folder,
            prompt_file,
            qlog_folder,
            qprompt_folder,
            log_level_str,
            logger,
            java_source_folder,
            args.use_sudo
        )
        
        # 결과 업데이트 (락 사용)
        with results_lock:
            if success:
                logger.info(f"[{thread_name}] Successfully transformed {target_file} to {transformed_file}")
                results['successful'] += 1
            else:
                logger.error(f"[{thread_name}] Failed to transform {target_file}")
                results['failed'] += 1
    
    # ThreadPoolExecutor를 사용하여 멀티스레드 처리
    logger.info(f"Starting transformation with {thread_count} threads")
    start_time = time.time()
    processing_count = 0
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        # 모든 파일에 대해 작업 제출
        processing_count = processing_count + 1
        logger.info(f"Processing {processing_count}/{len(target_files)} files")
        futures = [executor.submit(process_file, target_file) for target_file in target_files]
        
        # 모든 작업이 완료될 때까지 대기
        for future in futures:
            try:
                future.result()  # 예외가 발생하면 여기서 처리됨
            except Exception as e:
                logger.error(f"Thread execution error: {e}")
                with results_lock:
                    results['failed'] += 1
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 5. 검증 프로세스 호출
    logger.info("Starting validation process...")
    validation_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TransformValidation.py")

    try:
        validation_cmd = [
            "python3", 
            validation_script,
            "--mapper-folder", target_sql_mapper_folder,
            "--origin-suffix", origin_suffix,
            "--app-transform-folder", app_transform_folder,
            "--app-log-folder", pylog_folder,
            f"--log-level={log_level_str}"  # 로그 레벨 전달
        ]
        
        # 로그 파일 경로 구성 (검증 프로세스용)
        validation_log_file = os.path.join(pylog_folder, f"TransformValidation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        validation_cmd.extend(["-l", validation_log_file])
        
        logger.info(f"Running validation with command: {' '.join(validation_cmd)}")
        
        # 하위 프로세스 실행 및 출력 캡처
        result = run_command(validation_cmd, logger)
        
        if result == 0:
            logger.info("Validation process completed successfully")
        else:
            logger.error(f"Validation process failed with exit code: {result}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to run validation process: {e}")
        sys.exit(1)

    # 6. 결과 요약
    logger.info("Transform process completed")
    logger.info("Total target files : {len(target_files)}")
    logger.info(f"Total files processed: {results['total']}")
    logger.info(f"Successful transforms: {results['successful']}")
    logger.info(f"Failed transforms: {results['failed']}")
    logger.info(f"Total execution time: {execution_time:.2f} seconds")
    
    # 실패한 변환이 있으면 경고 메시지 출력
    if results['failed'] > 0:
        logger.warning("Some transforms failed. Check the log for details.")
        sys.exit(1)

    # 7. 검증 결과 리포팅
    # Check SQLTransformTargetFailure.csv
    failure_csv = os.path.join(app_transform_folder, 'SQLTransformTargetFailure.csv')
    if os.path.exists(failure_csv):
        with open(failure_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            failures = list(reader)
            if failures:
                logger.warning("\n" + "="*80)
                logger.warning("TRANSFORMATION FAILURES DETECTED:")
                logger.warning("="*80)
                for failure in failures:
                    logger.warning(f"File: {failure['FileName']}")
                logger.warning(f"Total failures: {len(failures)}")
                logger.warning("="*80 + "\n")

    # Check xmllintResult.csv
    xmllint_csv = os.path.join(app_transform_folder, 'xmllintResult.csv')
    if os.path.exists(xmllint_csv):
        with open(xmllint_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            xml_failures = [row for row in reader if row['Message'].startswith('Error')]
            if xml_failures:
                logger.warning("\n" + "="*80)
                logger.warning("XML VALIDATION FAILURES DETECTED:")
                logger.warning("="*80)
                for failure in xml_failures:
                    logger.warning(f"File: {failure['FileName']}")
                    logger.warning(f"Path: {failure['Path']}")
                    logger.warning(f"Error: {failure['Message']}")
                    logger.warning("-"*80)
                logger.warning(f"Total XML validation failures: {len(xml_failures)}")
                logger.warning("="*80 + "\n")
    

    logger.info("All transforms completed successfully")

if __name__ == "__main__":
    main()
