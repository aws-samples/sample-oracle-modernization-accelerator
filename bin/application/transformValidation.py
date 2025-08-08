#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MyBatis 호환 XML Validation 도구

위치: /home/ec2-user/workspace/oracle-mod-ax/bin/application/transformValidation.py

transform 파라미터를 받아서 $APP_TRANSFORM_FOLDER/postCheck.csv에서 XML 리스트를 가져와 validation 수행
"""

import os
import sys
import csv
import glob
import logging
import argparse
import xml.etree.ElementTree as ET
import re
import subprocess
from datetime import datetime

def read_xml_files_from_postcheck(csv_file, logger):
    """postCheck.csv 파일에서 XML 파일들의 경로를 읽어옵니다."""
    xml_files = []
    
    if not os.path.exists(csv_file):
        logger.warning(f"postCheck.csv 파일이 존재하지 않습니다: {csv_file}")
        return xml_files
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get('XMLFile', '')
                if filename is not None:
                    filename = filename.strip()
                    if filename and filename.endswith('.xml'):
                        xml_files.append(filename)
        
        logger.info(f"postCheck.csv에서 XML 파일 {len(xml_files)}개 발견: {csv_file}")
        
    except Exception as e:
        logger.error(f"postCheck.csv 파일 읽기 오류: {csv_file}, 오류: {e}")
    
    return xml_files

def update_postcheck_csv(csv_file, validation_results, logger):
    """postCheck.csv 파일의 XMLValidation 컬럼을 validation 결과로 업데이트합니다."""
    if not os.path.exists(csv_file):
        logger.warning(f"postCheck.csv 파일이 존재하지 않습니다: {csv_file}")
        return
    
    try:
        # CSV 파일 읽기
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                rows.append(row)
        
        # validation 결과를 딕셔너리로 변환 (파일 경로를 키로 사용)
        result_dict = {}
        for result in validation_results:
            file_path = result[0]  # 첫 번째 요소가 파일 경로
            is_valid = result[1]   # 두 번째 요소가 validation 성공 여부
            result_dict[file_path] = '[O]' if is_valid else '[X]'
        
        # 각 행의 XMLValidation 컬럼 업데이트
        updated_count = 0
        for row in rows:
            xml_file = row.get('XMLFile', '')
            if xml_file is not None:
                xml_file = xml_file.strip()
                if xml_file in result_dict:
                    old_status = row.get('XMLValidation', '')
                    new_status = result_dict[xml_file]
                    row['XMLValidation'] = new_status
                    if old_status != new_status:
                        updated_count += 1
        
        # CSV 파일 쓰기
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"postCheck.csv 업데이트 완료: {updated_count}개 행이 변경되었습니다.")
        
    except Exception as e:
        logger.error(f"postCheck.csv 파일 업데이트 오류: {csv_file}, 오류: {e}")

def read_merge_xml_files(app_logs_folder, logger):
    """merge 폴더에서 XML 파일들을 읽어옵니다."""
    xml_files = []
    
    # merge 폴더 패턴: $APP_LOGS_FOLDER/mapper/**/merge/*.xml
    merge_pattern = os.path.join(app_logs_folder, 'mapper', '**', 'merge', '*.xml')
    xml_files = glob.glob(merge_pattern, recursive=True)
    
    logger.info(f"merge 폴더에서 XML 파일 {len(xml_files)}개 발견: {merge_pattern}")
    
    return xml_files

def validate_xml_with_parsing(xml_file_path, logger):
    """Python XML 파싱을 사용하여 XML 파일을 검증합니다. (MyBatis 호환)"""
    try:
        # XML 파싱 시도
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # 기본적인 MyBatis 매퍼 구조 확인
        if root.tag != 'mapper':
            return False, f"Error: Root element is not 'mapper': {root.tag}"
        
        # namespace 속성 확인
        if 'namespace' not in root.attrib:
            return False, "Error: Missing 'namespace' attribute in mapper"
        
        # 파일 내용 읽기
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 원본 파일 경로 찾기 (transform -> extract, tgt -> src)
        original_path = xml_file_path.replace('/transform/', '/extract/').replace('_tgt-', '_src-')
        original_content = ""
        if os.path.exists(original_path):
            with open(original_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        
        # XML 주석 내 문제 패턴 검사 함수
        def check_comment_issues(content_to_check):
            issues = []
            comment_pattern = r'<!--(.*?)-->'
            comments = re.findall(comment_pattern, content_to_check, re.DOTALL)
            for comment in comments:
                comment_content = comment.strip()
                # 이중 하이픈 검사
                if '--' in comment_content:
                    issues.append("double_hyphen")
                # 이스케이프되지 않은 앰퍼샌드 검사
                if '&' in comment_content and not any(entity in comment_content for entity in ['&amp;', '&lt;', '&gt;', '&quot;', '&apos;']):
                    issues.append("unescaped_ampersand")
                # CDATA 종료 마커 검사
                if ']]>' in comment_content:
                    issues.append("cdata_end_marker")
            return issues
        
        # CDATA 밖의 부등호 검사 함수
        def check_unescaped_chars(content_to_check):
            issues = []
            lines = content_to_check.split('\n')
            in_cdata = False
            
            # MyBatis 태그 패턴들
            mybatis_tags = ['if', 'choose', 'when', 'otherwise', 'foreach', 'where', 'set', 'trim', 'include', 'sql']
            mybatis_pattern = r'</?(' + '|'.join(mybatis_tags) + r')(\s[^>]*)?>|<(' + '|'.join(mybatis_tags) + r')\s[^>]*/>|<(' + '|'.join(mybatis_tags) + r')>'
            
            for line_num, line in enumerate(lines, 1):
                # CDATA 시작/끝 확인
                if '<![CDATA[' in line:
                    in_cdata = True
                if ']]>' in line:
                    in_cdata = False
                    continue
                
                # CDATA 내부라면 검사하지 않음
                if in_cdata:
                    continue
                
                # XML 태그로 시작하는 줄이나 주석은 제외
                if line.strip().startswith('<') or line.strip().startswith('<!--'):
                    continue
                    
                # MyBatis 태그가 포함된 경우는 제외
                if re.search(mybatis_pattern, line):
                    continue
                    
                # XML 태그 속성이 포함된 줄은 제외 (예: parameterType="..." >)
                if re.search(r'\w+\s*=\s*"[^"]*"\s*>', line):
                    continue
                    
                if '<' in line and not ('&lt;' in line or '</' in line or '<!' in line or '<=' in line or '<>' in line):
                    issues.append(f"unescaped_lt_{line_num}")
                if '>' in line and not ('&gt;' in line or '/>' in line or '-->' in line or '->' in line or '>=' in line or '<>' in line):
                    issues.append(f"unescaped_gt_{line_num}")
            return issues
        
        # 현재 파일과 원본 파일의 문제 비교
        if original_content:
            current_comment_issues = check_comment_issues(content)
            original_comment_issues = check_comment_issues(original_content)
            
            current_char_issues = check_unescaped_chars(content)
            original_char_issues = check_unescaped_chars(original_content)
            
            # 원본에 없던 새로운 문제만 감지
            new_comment_issues = [issue for issue in current_comment_issues if issue not in original_comment_issues]
            new_char_issues = [issue for issue in current_char_issues if issue not in original_char_issues]
            
            # 새로운 주석 문제 체크
            for issue in new_comment_issues:
                if issue == "double_hyphen":
                    return False, "Error: Double hyphen within comment is not allowed in XML (new in transform)"
                elif issue == "unescaped_ampersand":
                    return False, "Error: Unescaped ampersand (&) in XML comment - use &amp; instead (new in transform)"
                elif issue == "cdata_end_marker":
                    return False, "Error: CDATA end marker (]]>) found in XML comment (new in transform)"
            
            # 새로운 문자 이스케이프 문제 체크
            for issue in new_char_issues:
                if issue.startswith("unescaped_lt_"):
                    line_num = issue.split("_")[-1]
                    return False, f"Error: Unescaped less-than (<) found outside CDATA at line {line_num} (new in transform)"
                elif issue.startswith("unescaped_gt_"):
                    line_num = issue.split("_")[-1]
                    return False, f"Error: Unescaped greater-than (>) found outside CDATA at line {line_num} (new in transform)"
        else:
            # 원본 파일이 없는 경우 기존 로직 사용 (모든 문제 감지)
            comment_issues = check_comment_issues(content)
            char_issues = check_unescaped_chars(content)
            
            for issue in comment_issues:
                if issue == "double_hyphen":
                    return False, "Error: Double hyphen within comment is not allowed in XML"
                elif issue == "unescaped_ampersand":
                    return False, "Error: Unescaped ampersand (&) in XML comment - use &amp; instead"
                elif issue == "cdata_end_marker":
                    return False, "Error: CDATA end marker (]]>) found in XML comment"
            
            for issue in char_issues:
                if issue.startswith("unescaped_lt_"):
                    line_num = issue.split("_")[-1]
                    return False, f"Error: Unescaped less-than (<) found outside CDATA at line {line_num}"
                elif issue.startswith("unescaped_gt_"):
                    line_num = issue.split("_")[-1]
                    return False, f"Error: Unescaped greater-than (>) found outside CDATA at line {line_num}"
        
        # SQL 문장이 있는 엘리먼트들의 id 속성 확인
        sql_elements = ['select', 'insert', 'update', 'delete', 'sql', 'resultMap']
        missing_ids = []
        duplicate_ids = []
        # resultMap과 다른 요소들을 분리해서 관리 (MyBatis에서는 resultMap과 select가 같은 id를 가질 수 있음)
        resultmap_ids = set()
        other_ids = set()
        
        for child in root:
            if child.tag in sql_elements:
                element_id = child.get('id')
                if not element_id:
                    missing_ids.append(f"{child.tag}")
                else:
                    if child.tag == 'resultMap':
                        if element_id in resultmap_ids:
                            duplicate_ids.append(f"resultMap:{element_id}")
                        else:
                            resultmap_ids.add(element_id)
                    else:
                        if element_id in other_ids:
                            duplicate_ids.append(f"{child.tag}:{element_id}")
                        else:
                            other_ids.add(element_id)
        
        if missing_ids:
            return False, f"Error: Missing 'id' attribute in elements: {', '.join(missing_ids)}"
        
        if duplicate_ids:
            return False, f"Error: Duplicate 'id' attributes found: {', '.join(duplicate_ids)}"
        
        # resultMap 요소의 type 속성 확인
        for child in root:
            if child.tag == 'resultMap':
                if not child.get('type'):
                    return False, f"Error: resultMap '{child.get('id', 'unknown')}' must have 'type' attribute"
        
        # select 요소의 resultType 또는 resultMap 속성 확인
        for child in root:
            if child.tag == 'select':
                if not child.get('resultType') and not child.get('resultMap'):
                    return False, f"Error: Select '{child.get('id', 'unknown')}' must have either 'resultType' or 'resultMap' attribute"
        
        # xmllint로 XML 구조 최종 검증
        try:
            result = subprocess.run(['xmllint', '--noout', xml_file_path], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return False, f"Error: xmllint validation failed - {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return False, "Error: xmllint validation timeout"
        except FileNotFoundError:
            # xmllint가 없으면 건너뜀
            pass
        except Exception as e:
            return False, f"Error: xmllint validation error - {str(e)}"
        
        return True, "OK"
        
    except ET.ParseError as e:
        error_msg = f"XML Parse Error: {str(e)}"
        if "not well-formed" in str(e).lower():
            # 더 자세한 오류 정보 제공
            try:
                with open(xml_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if hasattr(e, 'lineno') and e.lineno <= len(lines):
                        problematic_line = lines[e.lineno - 1].strip()
                        error_msg += f" at line {e.lineno}: {problematic_line}"
            except:
                pass
            return False, f"Error: {error_msg}"
        else:
            return False, f"Error: {error_msg}"
        
    except Exception as e:
        return False, f"Error: Validation Error: {str(e)}"

def validate_xml_files_from_postcheck(postcheck_csv, target_sql_mapper_folder, origin_suffix, logger):
    """postCheck.csv에서 XML 파일들을 읽어와 검증하고 결과를 CSV에 업데이트합니다."""
    result_list = []
    validation_results = []  # CSV 업데이트용 결과 저장
    
    # postCheck.csv에서 XML 파일들 읽기
    xml_files = read_xml_files_from_postcheck(postcheck_csv, logger)
    
    logger.info(f"총 {len(xml_files)}개의 XML 파일을 검증합니다.")
    
    # 각 파일에 대해 그대로 검증 (경로 변환 없이)
    for xml_file_path in xml_files:
        # 파일이 존재하는지 확인
        if os.path.exists(xml_file_path):
            # XML 검증 수행
            valid, error_msg = validate_xml_with_parsing(xml_file_path, logger)
            
            result_list.append((
                os.path.dirname(xml_file_path),
                os.path.basename(xml_file_path),
                error_msg
            ))
            
            # CSV 업데이트용 결과 저장 (파일 경로, 성공 여부)
            validation_results.append((xml_file_path, valid))
            
            logger.debug(f"검증 완료: {xml_file_path} -> {error_msg}")
        else:
            logger.warning(f"파일이 존재하지 않습니다: {xml_file_path}")
            result_list.append((
                os.path.dirname(xml_file_path) if '/' in xml_file_path else '',
                os.path.basename(xml_file_path),
                f"Error: 파일이 존재하지 않음"
            ))
            
            # CSV 업데이트용 결과 저장 (파일이 없으면 실패로 처리)
            validation_results.append((xml_file_path, False))
    
    # postCheck.csv의 XMLValidation 컬럼 업데이트
    update_postcheck_csv(postcheck_csv, validation_results, logger)
    
    return result_list

def validate_merge_xml_files(app_logs_folder, logger):
    """merge 폴더의 XML 파일들을 검증합니다."""
    result_list = []
    
    # merge 폴더에서 XML 파일들 읽기
    xml_files = read_merge_xml_files(app_logs_folder, logger)
    
    logger.info(f"총 {len(xml_files)}개의 merge XML 파일을 검증합니다.")
    
    # 각 파일에 대해 검증 수행
    for xml_file_path in xml_files:
        # 파일이 존재하는지 확인
        if os.path.exists(xml_file_path):
            # XML 검증 수행
            valid, error_msg = validate_xml_with_parsing(xml_file_path, logger)
            
            result_list.append((
                os.path.dirname(xml_file_path),
                os.path.basename(xml_file_path),
                error_msg
            ))
            logger.debug(f"검증 완료: {xml_file_path} -> {error_msg}")
        else:
            logger.warning(f"파일이 존재하지 않습니다: {xml_file_path}")
            result_list.append((
                os.path.dirname(xml_file_path) if '/' in xml_file_path else '',
                os.path.basename(xml_file_path),
                f"Error: 파일이 존재하지 않음"
            ))
    
    return result_list

def save_results_to_csv(results, output_file, logger):
    """검증 결과를 CSV 파일로 저장합니다."""
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Directory', 'Filename', 'ValidationResult'])
            writer.writerows(results)
        
        logger.info(f"XML 검증 결과가 저장되었습니다: {output_file}")
        
    except Exception as e:
        logger.error(f"결과 저장 오류: {output_file}, 오류: {e}")

def main():
    # 환경 변수에서 경로 가져오기
    app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER', '/home/ec2-user/workspace/oracle-mod-ax/ibe-vof-trans/application/transform')
    app_logs_folder = os.environ.get('APP_LOGS_FOLDER', '/home/ec2-user/workspace/oracle-mod-ax/ibe-vof-trans/logs/application')
    target_sql_mapper_folder = os.environ.get('TARGET_SQL_MAPPER_FOLDER', '/home/ec2-user/workspace/topas/mysql-ibe-vof-trans/src/main/resources/config')
    origin_suffix = os.environ.get('ORIGIN_SUFFIX', '_origin')
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )
    logger = logging.getLogger(__name__)
    
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='XML Validation Tool')
    parser.add_argument('--merge', action='store_true', help='$APP_LOGS_FOLDER/mapper/**/merge/*.xml 패턴의 파일들 검증')
    args = parser.parse_args()
    
    logger.info("MyBatis 호환 XML Validation 시작")
    logger.info(f"Transform Folder: {app_transform_folder}")
    logger.info(f"Logs Folder: {app_logs_folder}")
    logger.info(f"Target Mapper Folder: {target_sql_mapper_folder}")
    logger.info(f"Origin Suffix: {origin_suffix}")
    
    if args.merge:
        # merge 모드: merge 폴더의 XML 파일들 검증
        logger.info("Merge 모드: $APP_LOGS_FOLDER/mapper/**/merge/*.xml 패턴의 파일들 검증")
        xmllint_results = validate_merge_xml_files(app_logs_folder, logger)
    else:
        # 기본 모드: postCheck.csv에서 XML 리스트 가져와서 validation
        postcheck_csv = os.path.join(app_transform_folder, 'postCheck.csv')
        logger.info(f"기본 모드 (Transform): postCheck.csv에서 XML 리스트 가져오기 - {postcheck_csv}")
        xmllint_results = validate_xml_files_from_postcheck(postcheck_csv, target_sql_mapper_folder, origin_suffix, logger)
    
    # 결과 저장
    output_file = os.path.join(app_transform_folder, 'mybatisValidationResult.csv')
    save_results_to_csv(xmllint_results, output_file, logger)
    
    # 결과 요약
    logger.info("Validation process completed")
    logger.info(f"Total files checked: {len(xmllint_results)}")
    
    # 실패한 파일 개수 계산
    failed_count = sum(1 for result in xmllint_results if result[2] != "OK")
    xmllint_failed_count = sum(1 for result in xmllint_results if result[2] != "OK" and "xmllint" in result[2])
    
    logger.info(f"XML validation failures: {failed_count}")
    if xmllint_failed_count > 0:
        logger.info(f"xmllint validation failures: {xmllint_failed_count}")
    else:
        logger.info("xmllint validation: All files passed")
    
    if failed_count == 0:
        logger.info("All validations passed successfully.")
        sys.exit(0)
    else:
        logger.warning("Validation found issues. Check the output files for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
