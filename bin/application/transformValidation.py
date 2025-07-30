#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수정된 transformValidation.py
위치: /tmp/fixed_transformValidation.py

CSV 파일에서 Completed 상태인 파일들만 validation하도록 수정
"""

import csv
import os
import subprocess
import logging
from datetime import datetime

def read_completed_files_from_csv(csv_file, logger):
    """CSV 파일에서 Process=Completed인 파일들의 경로를 읽어옵니다."""
    completed_files = []
    
    if not os.path.exists(csv_file):
        logger.warning(f"CSV 파일이 존재하지 않습니다: {csv_file}")
        return completed_files
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Process', '').strip() == 'Completed':
                    filename = row.get('Filename', '').strip()
                    if filename:
                        completed_files.append(filename)
        
        logger.info(f"CSV에서 Completed 상태 파일 {len(completed_files)}개 발견: {csv_file}")
        
    except Exception as e:
        logger.error(f"CSV 파일 읽기 오류: {csv_file}, 오류: {e}")
    
    return completed_files

def validate_xml_with_xmllint(xml_file, logger):
    """xmllint를 사용하여 XML 파일을 검증합니다."""
    try:
        cmd = ["xmllint", "--noout", xml_file]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.debug(f"XML 검증 성공: {xml_file}")
            return True, "Success"
        else:
            error_msg = f"Error: {stderr.strip()}"
            logger.warning(f"XML 검증 실패: {xml_file}, 오류: {error_msg}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Error: 검증 중 예외 발생: {str(e)}"
        logger.error(f"XML 검증 예외: {xml_file}, 오류: {error_msg}")
        return False, error_msg

def validate_completed_xml_files(csv_files, target_sql_mapper_folder, origin_suffix, logger):
    """CSV 파일들에서 Completed 상태인 XML 파일들만 검증합니다."""
    result_list = []
    all_completed_files = []
    
    # 모든 CSV 파일에서 Completed 파일들 수집
    for csv_file in csv_files:
        completed_files = read_completed_files_from_csv(csv_file, logger)
        all_completed_files.extend(completed_files)
    
    logger.info(f"총 {len(all_completed_files)}개의 Completed 파일을 검증합니다.")
    
    # 각 파일에 대해 변환된 파일 경로 생성 및 검증
    for original_file in all_completed_files:
        # 원본 파일의 디렉토리 구조 파악
        # 예: /home/ec2-user/workspace/chalee/orcl-itsm/src/main/resources/sqlmap/com/AccessLoggingDao_sqlMap.xml
        # -> com/AccessLoggingDao_sqlMap.xml 부분 추출
        
        # sqlmap 이후의 상대 경로 추출
        if '/sqlmap/' in original_file:
            relative_path = original_file.split('/sqlmap/', 1)[1]
        else:
            # sqlmap이 없으면 파일명만 사용
            relative_path = os.path.basename(original_file)
        
        # origin_suffix가 있으면 제거하여 변환된 파일명 생성
        if origin_suffix and origin_suffix in relative_path:
            transformed_relative_path = relative_path.replace(origin_suffix, '')
        else:
            transformed_relative_path = relative_path
        
        # 변환된 파일의 전체 경로 생성 (디렉토리 구조 유지)
        transformed_file_path = os.path.join(target_sql_mapper_folder, transformed_relative_path)
        
        # 변환된 파일이 존재하는지 확인
        if os.path.exists(transformed_file_path):
            # XML 검증 수행
            valid, error_msg = validate_xml_with_xmllint(transformed_file_path, logger)
            
            result_list.append((
                os.path.dirname(transformed_file_path),
                os.path.basename(transformed_file_path),
                error_msg
            ))
        else:
            logger.warning(f"변환된 파일이 존재하지 않습니다: {transformed_file_path}")
            result_list.append((
                os.path.dirname(transformed_file_path) if '/' in transformed_file_path else target_sql_mapper_folder,
                os.path.basename(transformed_file_path) if '/' in transformed_file_path else transformed_relative_path,
                f"Error: 변환된 파일이 존재하지 않음"
            ))
    
    return result_list

def write_xmllint_result(results, output_file, logger):
    """xmllint 검증 결과를 CSV 파일에 기록합니다."""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Path', 'FileName', 'Message'])
            
            for path, filename, message in results:
                writer.writerow([path, filename, message])
        
        logger.info(f"XML 검증 결과가 저장되었습니다: {output_file}")
        
    except Exception as e:
        logger.error(f"결과 파일 저장 오류: {output_file}, 오류: {e}")

# 사용 예시
if __name__ == "__main__":
    # 로거 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 환경 변수에서 경로 가져오기
    app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER')
    target_sql_mapper_folder = os.environ.get('TARGET_SQL_MAPPER_FOLDER')
    origin_suffix = os.environ.get('ORIGIN_SUFFIX', '_origin')
    
    if not app_transform_folder or not target_sql_mapper_folder:
        logger.error("필수 환경 변수가 설정되지 않았습니다: APP_TRANSFORM_FOLDER, TARGET_SQL_MAPPER_FOLDER")
        exit(1)
    
    # CSV 파일들 경로
    csv_files = [
        os.path.join(app_transform_folder, 'SQLTransformTarget.csv'),
        os.path.join(app_transform_folder, 'SampleTransformTarget.csv')
    ]
    
    logger.info("수정된 XML Validation 시작")
    logger.info(f"Transform Folder: {app_transform_folder}")
    logger.info(f"Target Mapper Folder: {target_sql_mapper_folder}")
    logger.info(f"Origin Suffix: {origin_suffix}")
    
    # Completed 파일들만 검증
    xmllint_results = validate_completed_xml_files(csv_files, target_sql_mapper_folder, origin_suffix, logger)
    
    # 결과 저장
    xmllint_result_file = os.path.join(app_transform_folder, 'xmllintResult.csv')
    write_xmllint_result(xmllint_results, xmllint_result_file, logger)
    
    # 요약
    logger.info("Validation process completed")
    logger.info(f"Total files checked: {len(xmllint_results)}")
    
    xml_failures = sum(1 for _, _, msg in xmllint_results if msg.startswith('Error'))
    logger.info(f"XML validation failures: {xml_failures}")
    
    if xml_failures > 0:
        logger.warning("Validation found issues. Check the output files for details.")
        exit(1)
    else:
        logger.info("All validations passed successfully.")
        exit(0)
