#!/usr/bin/env python3
import os
import re
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import logging
import argparse
from datetime import datetime

"""
GenSQLTransformTarget.py - XML 매퍼 파일에서 시작하여 부모 DAO 클래스를 찾는 스크립트

1. 프로그램 개요
   - XML 매퍼 파일의 네임스페이스에서 시작하여 TRANSFORM_CLASS에 도달할 때까지 부모 클래스 검색
   - 클래스 계층 구조를 분석하고 상속 관계 추적
   - TRANSFORM_RELATED_CLASS와의 관계 확인

2. 버전 정보
   V1.1
   변경사항:
   - DAO 매핑 오류 수정: XML 파일명과 네임스페이스 추가
   - 프로그램 초기화 개선: 결과 파일 경로 및 디렉토리 생성 로직 표준화

3. 사용법
   3.1 환경 변수:
       - TRANSFORM_RELATED_CLASS: 변환할 대상 클래스 목록 (쉼표로 구분)
       - JAVA_SOURCE_FOLDER: Java 소스 코드가 포함된 디렉토리
       - APPLICATION_FOLDER: 결과 파일을 저장할 디렉토리

   3.2 실행:
       python GenSQLTransformTarget.py [옵션]

   3.3 옵션:
       --xml-files: 처리할 XML 파일 경로 (여러 파일 지정 가능)
       --debug: 디버그 모드 활성화

   3.4 결과 파일:
       - discovery/MapperAndJndi.csv: 모든 매퍼 파일 및 JNDI 매핑 정보
       - Transform/SQLTransformTarget.csv: DBMS 변환이 필요한 SQL 매퍼 목록
"""

# =============================================================================
# 상수
# =============================================================================
# 환경 변수
TRANSFORM_CLASS = os.getenv('TRANSFORM_RELATED_CLASS')
TRANSFORM_CLASSES = [cls.strip() for cls in TRANSFORM_CLASS.split(',')] if TRANSFORM_CLASS else []
SOURCE_DIR = os.getenv('JAVA_SOURCE_FOLDER')
APPLICATION_FOLDER = os.getenv('APPLICATION_FOLDER')
APP_TRANSFORM_FOLDER = os.getenv('APP_TRANSFORM_FOLDER')
APP_LOGS_FOLDER = os.getenv('APP_LOGS_FOLDER')
MAPPER_DIR = os.getenv('SOURCE_SQL_MAPPER_FOLDER')

# 결과 파일 경로
MAPPER_AND_JNDI_CSV = os.path.join(APPLICATION_FOLDER, 'discovery', 'MapperAndJndi.csv')
SQL_TRANSFORM_TARGET_CSV = os.path.join(APP_TRANSFORM_FOLDER, 'SQLTransformTarget.csv')
SQL_TRANSFORM_TARGET_SELECTIVE_CSV = os.path.join(APP_TRANSFORM_FOLDER, 'SQLTransformTargetSelective.csv')
SAMPLE_TRANSFORM_TARGET_CSV = os.path.join(APP_TRANSFORM_FOLDER, 'SampleTransformTarget.csv')
SAMPLE_MAPPER_LIST_CSV = os.path.join(APPLICATION_FOLDER, 'discovery', 'SampleMapperlist.csv')

# =============================================================================
# 로깅 설정
# =============================================================================
def setup_logging():
    """로깅 설정을 초기화합니다."""
    log_dir = os.path.join(APP_LOGS_FOLDER, 'GenSQLTransformTarget')
    # 로그 디렉토리 생성
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'Find_ParentClasses.log')
    
    # 로그 형식 정의
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 설정
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # 로거 설정
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    logger.debug("Debug logging enabled")
    
    return logger

# 로거 초기화
logger = setup_logging()

# =============================================================================
# 유틸리티 함수
# =============================================================================
def check_required_env_vars():
    """필수 환경 변수가 설정되어 있는지 확인합니다."""
    missing_vars = []
    if not TRANSFORM_CLASSES:
        missing_vars.append('TRANSFORM_RELATED_CLASS')
    if not SOURCE_DIR:
        missing_vars.append('JAVA_SOURCE_FOLDER')
    if not APPLICATION_FOLDER:
        missing_vars.append('APPLICATION_FOLDER')
    if not MAPPER_DIR:
        missing_vars.append('SOURCE_SQL_MAPPER_FOLDER')

    if missing_vars:
        logger.error("The following environment variables are not set:")
        for var in missing_vars:
            logger.error(f"- {var}")
        logger.error("\nPlease set the environment variables using:")
        logger.error("source SetEnv.sh")
        sys.exit(1)
    else:
        logger.info("All required environment variables are set")

def create_required_directories():
    """프로그램 실행에 필요한 디렉토리를 생성합니다."""
    try:
        os.makedirs(os.path.join(APPLICATION_FOLDER), exist_ok=True)
        os.makedirs(os.path.join(APP_LOGS_FOLDER, 'GenSQLTransformTarget'), exist_ok=True)
        os.makedirs(os.path.join(APP_TRANSFORM_FOLDER), exist_ok=True)
        logger.info(f"Created required directories: {APP_LOGS_FOLDER}/GenSQLTransformTarget")
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        sys.exit(1)

# =============================================================================
# 클래스 정의
# =============================================================================
class ClassHierarchy:
    """클래스 계층 구조를 관리하는 클래스"""
    def __init__(self):
        self.parents = defaultdict(set)  # 자식 클래스 -> 부모 클래스 매핑
        self.children = defaultdict(set)  # 부모 클래스 -> 자식 클래스 매핑
        self.class_files = {}  # 클래스 이름 -> 파일 경로 매핑
        self.mapper_files = {}  # 클래스 이름 -> 매퍼 파일 경로 매핑
        self.class_info = {}  # 클래스 이름 -> 클래스 정보 매핑

    def add_relationship(self, child, parent, file_path):
        """클래스 관계를 추가합니다."""
        self.parents[child].add(parent)
        self.children[parent].add(child)
        self.class_files[child] = file_path
        if child not in self.class_info:
            self.class_info[child] = {
                'file_path': file_path,
                'mapper_path': None,
                'package': None
            }

    def add_mapper(self, class_name, mapper_path):
        """매퍼 파일 정보를 추가합니다."""
        self.mapper_files[class_name] = mapper_path
        if class_name in self.class_info:
            self.class_info[class_name]['mapper_path'] = mapper_path

    def get_all_ancestors(self, class_name):
        """지정된 클래스의 모든 상위 클래스를 찾습니다."""
        ancestors = set()
        to_process = {class_name}
        
        while to_process:
            current = to_process.pop()
            for parent in self.parents[current]:
                if parent not in ancestors:
                    ancestors.add(parent)
                    to_process.add(parent)
        
        return ancestors

    def get_inheritance_chain(self, class_name):
        """클래스의 상속 체인을 반환합니다."""
        chain = []
        current = class_name
        while current in self.parents and self.parents[current]:
            current = next(iter(self.parents[current]))
            chain.append(current)
        return chain

    def print_tree(self, node, prefix="", is_last=True):
        """클래스 계층 구조를 트리 형태로 출력합니다."""
        if not prefix:
            logger.debug(f"클래스 계층 구조:")
        
        branch = "└── " if is_last else "├── "
        logger.debug(f"{prefix}{branch}{node}")
        
        children = sorted(self.children[node])
        for i, child in enumerate(children):
            new_prefix = prefix + ("    " if is_last else "│   ")
            self.print_tree(child, new_prefix, i == len(children) - 1)

    def print_hierarchy(self):
        """최상위 클래스부터 계층 구조를 출력합니다."""
        # 최상위 클래스(부모가 없는 클래스) 찾기
        top_level = set(self.children.keys()) - set(self.parents.keys())
        for root in sorted(top_level):
            self.print_tree(root)

# =============================================================================
# XML 및 Java 파일 처리 함수
# =============================================================================
def extract_namespace_from_xml(xml_file):
    """XML 파일에서 네임스페이스를 추출합니다."""
    try:
        logger.debug(f"Attempting to parse XML file: {xml_file}")
        tree = ET.parse(xml_file)
        root = tree.getroot()
        namespace = root.get('namespace')
        
        logger.debug(f"Extracted namespace: {namespace}")
        return namespace
    except Exception as e:
        logger.error(f"XML parsing error in {xml_file}: {e}")
        return None

def find_java_class(class_name, source_dir):
    """클래스 이름으로 Java 파일을 찾습니다."""
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".java") and file[:-5] == class_name:
                return os.path.join(root, file)
    return None

def analyze_java_file(file_path):
    """Java 파일을 분석하여 클래스 정보를 추출합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            package_match = re.search(r'package\s+([\w.]+);', content)
            return {'package': package_match.group(1) if package_match else None}
    except Exception as e:
        logger.error(f"Java file analysis error in {file_path}: {e}")
        return None

def build_class_hierarchy(source_dir):
    """Java 소스 파일을 분석하여 클래스 계층 구조를 구축합니다."""
    hierarchy = ClassHierarchy()
    pattern = re.compile(
        r'class\s+(\w+)\s+(?:extends\s+([\w<>,\s]+)|implements\s+([\w<>,\s]+))',
        re.MULTILINE | re.DOTALL
    )
    package_pattern = re.compile(r'package\s+([\w.]+);')
    
    logger.info(f"Starting to search for class hierarchy in: {source_dir}")
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        package_match = package_pattern.search(content)
                        package_name = package_match.group(1) if package_match else None
                        
                        logger.debug(f"Analyzing file: {file_path}")
                        logger.debug(f"Package: {package_name}")
                        
                        content = re.sub(r'//.*?$|/\*.*?\*/', '', content, flags=re.MULTILINE | re.DOTALL)
                        matches = pattern.findall(content)
                        
                        if matches:
                            for class_name, extends, implements in matches:
                                logger.debug(f"Class found: {class_name}")
                                if extends:
                                    parents = [p.strip() for p in extends.split(',')]
                                    logger.debug(f"Inheritance relationship: {class_name} -> {parents}")
                                    for parent in parents:
                                        hierarchy.add_relationship(class_name, parent, file_path)
                                        if package_name:
                                            hierarchy.class_info[class_name]['package'] = package_name
                                
                                if implements:
                                    interfaces = [i.strip() for i in implements.split(',')]
                                    logger.debug(f"Interface implementation: {class_name} -> {interfaces}")
                                    for interface in interfaces:
                                        hierarchy.add_relationship(class_name, interface, file_path)
                                        if package_name:
                                            hierarchy.class_info[class_name]['package'] = package_name
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
    
    logger.info("Class hierarchy structure built")
    logger.debug(f"Total {len(hierarchy.parents)} class relationships found")
    hierarchy.print_hierarchy()
    return hierarchy

# =============================================================================
# 매퍼 파일 처리 함수
# =============================================================================
def find_parent_classes_recursive(start_class, hierarchy, current_level=1, max_level=5):
    """TRANSFORM_RELATED_CLASS에 도달할 때까지 재귀적으로 부모 클래스를 검색합니다."""
    if current_level > max_level:
        logger.debug(f"Max search level ({max_level}) reached")
        return False, []
    
    logger.info(f"[Inheritance information - Level {current_level}] Child class: {start_class}")
    
    if start_class in hierarchy.parents and hierarchy.parents[start_class]:
        parents = hierarchy.parents[start_class]
        logger.info(f"Parent classes: {', '.join(parents)}")
        
        for parent in parents:
            if parent in TRANSFORM_CLASSES:
                logger.info(f"TRANSFORM_RELATED_CLASS({parent}) found at level {current_level}!")
                return True, parents
            
            found, _ = find_parent_classes_recursive(parent, hierarchy, current_level + 1, max_level)
            if found:
                return True, parents
    else:
        logger.info("Parent class: None")
    
    return False, []

def process_mapper_file(xml_file, hierarchy):
    """목록에서 전달된 매퍼 파일을 처리합니다."""
    if not os.path.exists(xml_file):
        logger.error(f"File does not exist: {xml_file}")
        return None, None, False
    
    file_name = os.path.basename(xml_file)
    logger.info(f"[Processing file] : {file_name}")
    
    # TRANSFORM_CLASS가 '_ALL_'인 경우 모든 XML 파일을 대상으로 포함
    if TRANSFORM_CLASS == '_ALL_':
        logger.info(f"TRANSFORM_CLASS is '_ALL_', including all XML files: {file_name}")
        namespace_class = extract_namespace_from_xml(xml_file)
        file_name_without_ext = os.path.splitext(file_name)[0]
        start_class_candidates = [file_name_without_ext]
        
        if namespace_class:
            start_class_candidates.append(namespace_class)
        
        return xml_file, start_class_candidates, True
    
    # 기존 로직: TRANSFORM_CLASS가 '_ALL_'이 아닌 경우
    namespace_class = extract_namespace_from_xml(xml_file)
    file_name_without_ext = os.path.splitext(file_name)[0]
    start_class_candidates = [file_name_without_ext]
    
    if namespace_class:
        start_class_candidates.append(namespace_class)
    
    logger.info(f"Starting class candidate list: {', '.join(start_class_candidates)}")
    
    found = False
    for start_class in start_class_candidates:
        if not start_class:
            continue
        found, _ = find_parent_classes_recursive(start_class, hierarchy)
        if found:
            logger.info(f"TRANSFORM_RELATED_CLASS({', '.join(TRANSFORM_CLASSES)}) found: {file_name} (Starting class: {start_class})")
            break
    
    if not found:
        logger.info(f"TRANSFORM_RELATED_CLASS({', '.join(TRANSFORM_CLASSES)}) not found: {file_name}")
    
    return xml_file, start_class_candidates, found

def read_mapper_list(mapper_list_file):
    """Mapperlist.csv에서 처리할 파일 목록을 읽습니다."""
    if not os.path.exists(mapper_list_file):
        logger.error(f"Mapperlist.csv file does not exist: {mapper_list_file}")
        return []
    
    try:
        with open(mapper_list_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            file_list = []
            for row in reader:
                if row['FileName'].strip():
                    full_filename = row['FileName'].strip()
                    # 파일 경로에서 실제 파일명만 추출
                    filename = os.path.basename(full_filename)
                    
                    # MAPPER_DIR 하위에서 재귀적으로 파일 찾기
                    found_path = None
                    for root, dirs, files in os.walk(MAPPER_DIR):
                        if filename in files:
                            found_path = os.path.join(root, filename)
                            break
                    
                    if found_path:
                        file_list.append(found_path)
                    else:
                        logger.warning(f"XML file not found in MAPPER_DIR: {full_filename} (looking for: {filename})")
            
            logger.info(f"Found {len(file_list)} XML files out of total entries in Mapperlist.csv")
            return file_list
    except Exception as e:
        logger.error(f"Error reading Mapperlist.csv file: {e}")
        return []


def create_sample_transform_target():
    """SampleMapperlist.csv를 읽어서 SQLTransformTarget.csv에서 일치하는 파일명을 찾아 SampleTransformTarget.csv를 생성합니다.
    동시에 원본 SQLTransformTarget.csv의 해당 항목들의 Process 값을 'Sampled'로 업데이트합니다."""
    try:
        # SampleMapperlist.csv 파일 존재 확인
        if not os.path.exists(SAMPLE_MAPPER_LIST_CSV):
            logger.warning(f"SampleMapperlist.csv file does not exist: {SAMPLE_MAPPER_LIST_CSV}")
            return
        
        # SQLTransformTarget.csv 파일 존재 확인
        if not os.path.exists(SQL_TRANSFORM_TARGET_CSV):
            logger.warning(f"SQLTransformTarget.csv file does not exist: {SQL_TRANSFORM_TARGET_CSV}")
            return
        
        logger.info(f"Creating SampleTransformTarget.csv from SampleMapperlist.csv")
        
        # SampleMapperlist.csv에서 파일명 목록 읽기
        sample_filenames = set()
        with open(SAMPLE_MAPPER_LIST_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get('FileName', '').strip()
                if filename:
                    # 파일명만 추출 (경로 제거)
                    filename = os.path.basename(filename)
                    sample_filenames.add(filename)
        
        logger.info(f"Found {len(sample_filenames)} sample files in SampleMapperlist.csv")
        logger.debug(f"Sample filenames: {sample_filenames}")
        
        # SQLTransformTarget.csv에서 일치하는 행 찾기 및 Process 값 업데이트
        matching_rows = []
        all_rows = []
        header = None
        
        with open(SQL_TRANSFORM_TARGET_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 헤더 읽기
            
            for row in reader:
                if len(row) >= 2:  # 최소 2개 컬럼 필요 (No., Filename)
                    filename = row[1].strip()  # Filename 컬럼
                    # 파일명만 추출 (경로 제거)
                    filename = os.path.basename(filename)
                    
                    # Process 컬럼이 없는 경우 추가
                    if len(row) < 7:
                        row.append('Not yet')
                    
                    if filename in sample_filenames:
                        # 샘플 파일인 경우 원본에서는 Process를 'Sampled'로 설정
                        row[6] = 'Sampled'  # Process 컬럼 (7번째 컬럼, 인덱스 6)
                        # 복사본을 위해 Process를 'Not Yet'으로 변경한 행 생성
                        sample_row = row.copy()
                        sample_row[6] = 'Not Yet'
                        matching_rows.append(sample_row)
                        logger.debug(f"Matching file found: {filename}")
                
                all_rows.append(row)
        
        logger.info(f"Found {len(matching_rows)} matching transform targets")
        
        # 원본 SQLTransformTarget.csv 업데이트 (Process 값을 'Sampled'로 변경)
        with open(SQL_TRANSFORM_TARGET_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)  # 헤더 작성
            writer.writerows(all_rows)  # 업데이트된 모든 행 작성
        
        logger.info(f"Updated SQLTransformTarget.csv with 'Sampled' status for {len(matching_rows)} items")
        
        # SampleTransformTarget.csv 생성
        with open(SAMPLE_TRANSFORM_TARGET_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)  # 헤더 작성
            
            # 일치하는 행들을 원래 순번 그대로 작성
            for row in matching_rows:
                writer.writerow(row)
        
        logger.info(f"SampleTransformTarget.csv created successfully: {SAMPLE_TRANSFORM_TARGET_CSV}")
        logger.info(f"Total {len(matching_rows)} sample transform targets saved")
        
    except Exception as e:
        logger.error(f"Error creating SampleTransformTarget.csv: {e}")
        raise


def create_sql_transform_target_selective():
    """SQLTransformTargetSelective.csv 파일을 생성합니다. 파일이 이미 존재하면 건너뜁니다."""
    try:
        # 파일이 이미 존재하는지 확인
        if os.path.exists(SQL_TRANSFORM_TARGET_SELECTIVE_CSV):
            logger.info(f"SQLTransformTargetSelective.csv already exists, skipping creation: {SQL_TRANSFORM_TARGET_SELECTIVE_CSV}")
            return
        
        logger.info(f"Creating SQLTransformTargetSelective.csv: {SQL_TRANSFORM_TARGET_SELECTIVE_CSV}")
        
        # 헤더만 있는 CSV 파일 생성
        with open(SQL_TRANSFORM_TARGET_SELECTIVE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['No.', 'Filename', 'Namespace', 'DAO Class', 'Parent DAO Class', 'Transform Target', 'Process'])
        
        logger.info(f"SQLTransformTargetSelective.csv created successfully with header only")
        
    except Exception as e:
        logger.error(f"Error creating SQLTransformTargetSelective.csv: {e}")
        raise

def write_results_to_csv(results, output_file, hierarchy, only_transform_target=False):
    """결과를 CSV 파일로 저장합니다.
    
    Args:
        results: 처리 결과 목록
        output_file: 출력 파일 경로
        hierarchy: 클래스 계층 구조
        only_transform_target: True인 경우 변환 대상만 저장
    """
    try:
        logger.info(f"Writing results to CSV file: {output_file}")
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['No.', 'Filename', 'Namespace', 'DAO Class', 'Parent DAO Class', 'Transform Target', 'Process'])
            
            # 변환 대상 상태에 따라 필터링
            targets = [(idx, result) for idx, result in enumerate(results, 1) 
                      if not only_transform_target or result[2]]
            
            row_count = 0
            for idx, (mapper_file, dao_classes, is_target) in targets:
                # dao_classes가 None인 경우 빈 리스트로 처리
                if dao_classes is None:
                    dao_classes = []
                
                # 부모 DAO 정보 가져오기
                parent_dao = ''
                for dao_class in dao_classes:
                    if dao_class in hierarchy.parents and hierarchy.parents[dao_class]:
                        parent_dao = ', '.join(hierarchy.parents[dao_class])
                        break
                
                # dao_classes에서 네임스페이스와 DAO 클래스 추출
                namespace = dao_classes[1] if len(dao_classes) > 1 else ''
                dao_class = dao_classes[0] if dao_classes else ''
                
                # CSV 행 작성
                row = [
                    idx,                    # No.
                    mapper_file,            # Filename
                    namespace,              # Namespace
                    dao_class,              # DAO Class
                    parent_dao,             # Parent DAO Class
                    'Y' if is_target else 'N',  # Transform Target
                    'Not yet'               # Process
                ]
                logger.debug(f"Writing row: {row}")
                writer.writerow(row)
                row_count += 1
        
        # 개선된 로그 메시지
        target_type = "Transformation targets" if only_transform_target else "All results"
        logger.info(f"{target_type} saved to CSV file: {output_file}")
        logger.info(f"Total {row_count} items saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error while saving CSV file: {e}")
        raise

# =============================================================================
# 메인 함수
# =============================================================================
def main(xml_files=None):
    """메인 함수"""
    logger.info(f"\n")
    logger.info(f"{'=' * 100}")
    logger.info("Program started")
    logger.info(f"{'=' * 100}")
    logger.info(f"TRANSFORM_RELATED_CLASS: {TRANSFORM_CLASSES}")
    logger.info(f"SOURCE_DIR: {SOURCE_DIR}")
    logger.info(f"MAPPER_DIR: {MAPPER_DIR}")
    logger.info(f"APPLICATION_FOLDER: {APPLICATION_FOLDER}")
    
    # 필수 환경 변수 및 디렉토리 확인
    check_required_env_vars()
    create_required_directories()
    
    # 클래스 계층 구조 구축
    logger.info(f"{'=' * 100}")
    logger.info(f"Building class hierarchy in: {SOURCE_DIR}")
    logger.info(f"{'=' * 100}")
    hierarchy = build_class_hierarchy(SOURCE_DIR)
    logger.info(f"\n")
    logger.info(f"{'=' * 100}")    
    
    # 매퍼 파일 처리
    results = []
    if xml_files:
        logger.info(f"\n")
        logger.info(f"{'=' * 100}")
        logger.info(f"Processing {len(xml_files)} files specified in command line")
        logger.info(f"{'=' * 100}")
        for xml_file in xml_files:
            result = process_mapper_file(xml_file, hierarchy)
            if result:
                results.append(result)
    else:
        mapper_list_file = os.path.join(APPLICATION_FOLDER, 'discovery', 'Mapperlist.csv')
        logger.info(f"\n")
        logger.info(f"{'=' * 100}")
        logger.info(f"Reading file list from: {mapper_list_file}")
        logger.info(f"{'=' * 100}")
        xml_files = read_mapper_list(mapper_list_file)
        
        if not xml_files:
            logger.warning("No files to process")
            return
        
        logger.info(f"Processing {len(xml_files)} files")
        for xml_file in xml_files:
            result = process_mapper_file(xml_file, hierarchy)
            if result:
                results.append(result)
    
    # 결과 저장
    if results:
        # 모든 결과 저장
        write_results_to_csv(results, MAPPER_AND_JNDI_CSV, hierarchy, only_transform_target=False)
        
        # 변환 대상만 저장
        write_results_to_csv(results, SQL_TRANSFORM_TARGET_CSV, hierarchy, only_transform_target=True)
        
        # SQLTransformTargetSelective.csv 생성 (헤더만)
        create_sql_transform_target_selective()
        
        # SampleTransformTarget.csv 생성
        create_sample_transform_target()
        
        logger.info(f"Total {len(results)} files processed")
    else:
        logger.warning("No results processed")
    
    logger.info(f"{'=' * 100}")
    logger.info("Program ended")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='XML 매퍼 파일에서 시작하여 부모 DAO 클래스를 찾는 스크립트')
    parser.add_argument('--xml-files', nargs='+', help='처리할 XML 파일 경로 (여러 파일 지정 가능)')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    main(args.xml_files) 