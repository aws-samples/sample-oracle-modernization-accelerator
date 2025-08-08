#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLTransformTarget.py - MyBatis XML 변환 대상 처리 프로그램 (V3.0 개선 버전)

    V3.0 배치 상태 관리 및 체크포인트 기능 추가
         - XML별 고유 배치 ID (xmlname000001 형식)
         - Extract 완료 여부 체크로 중복 작업 방지
         - 배치별 상태 관리로 중단된 지점부터 재시작 가능
         - 세밀한 진행 상황 추적 및 로깅
    V2.0 Q Develiper 효율을 위한 XML Extract, Merge 기능 별도 구성
    V1.0 FileBased 변환 대상 처리 프로그램

개선 사항:
- 배치별 상태 관리로 중단된 지점부터 재시작 가능
- Extract 완료 여부 체크로 중복 작업 방지
- XML별 고유 배치 ID로 충돌 방지
- 세밀한 진행 상황 추적 및 로깅
- 실패한 배치만 선별적으로 재처리

이 프로그램은 MyBatis XML 파일을 변환하는 프로세스를 수행합니다:
1. 변환 대상 목록 CSV 파일에서 대상 파일 읽기
2. 각 XML 파일을 추출, 변환, 병합하는 과정 수행
    - 추출 : xmlExtractor.py (체크포인트 지원)
    - 변환 : 배치별 q chat 실행 (상태 관리)
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
    --mode {all,extract,transform,merge}
                                실행 모드 선택:
                                  all: 전체 프로세스 (추출→변환→병합) (기본값)
                                  extract: XML 추출만 수행
                                  transform: SQL 변환만 수행 (추출 완료 필요)
                                  merge: XML 병합만 수행 (변환 완료 필요)
    --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                로그 레벨 설정 (기본값: INFO)
    --batch-size                배치 크기 설정 (기본값: 10)
    --cleanup-batch             완료 후 배치 관리 파일 정리

예제:
    # 전체 프로세스 실행
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv
    
    # 중단된 지점부터 재시작
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv --mode transform
    
    # 배치 크기 조정
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv --batch-size 5
    
    # 특정 단계만 실행
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv --mode extract    # 추출만
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv --mode transform  # 변환만
    python3 SQLTransformTarget.py -f /path/to/SQLTransformTarget.csv --mode merge      # 병합만
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
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime

class BatchManager:
    """배치 상태 관리 클래스 - XML별 고유 배치 ID 지원"""
    
    def __init__(self, xmlwork_folder, batch_size=10, logger=None, xml_basename=None):
        self.xmlwork_folder = xmlwork_folder
        self.batch_size = batch_size
        self.logger = logger
        self.xml_basename = xml_basename or "Unknown"
        
        # 상태 파일 경로
        self.extract_flag_file = os.path.join(xmlwork_folder, "extract_completed.flag")
        self.batch_groups_file = os.path.join(xmlwork_folder, "batch_groups.csv")
        self.batch_status_file = os.path.join(xmlwork_folder, "batch_status.txt")
        self.progress_file = os.path.join(xmlwork_folder, "transform_progress.json")
        
        # 폴더 경로
        self.extract_folder = os.path.join(xmlwork_folder, "extract")
        self.transform_folder = os.path.join(xmlwork_folder, "transform")
    
    def log(self, message, level='info'):
        """로깅 헬퍼 메서드"""
        if self.logger:
            getattr(self.logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def is_extract_completed(self):
        """Extract 작업이 완료되었는지 확인"""
        if not os.path.exists(self.extract_flag_file):
            return False
        
        if not os.path.exists(self.extract_folder):
            return False
        
        xml_files = [f for f in os.listdir(self.extract_folder) if f.lower().endswith('.xml')]
        if not xml_files:
            return False
        
        self.log(f"Extract already completed: {len(xml_files)} files found")
        return True
    
    def mark_extract_completed(self, file_count=None):
        """Extract 완료 플래그 생성"""
        if file_count is None:
            xml_files = [f for f in os.listdir(self.extract_folder) if f.lower().endswith('.xml')]
            file_count = len(xml_files)
        
        with open(self.extract_flag_file, 'w', encoding='utf-8') as f:
            f.write(f"Extract completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total files: {file_count}\n")
            f.write(f"XML basename: {self.xml_basename}\n")
        
        self.log(f"Extract completion flag created: {file_count} files for {self.xml_basename}")
    
    def create_batch_groups(self, max_batch_size_kb=150, large_file_threshold_kb=50):
        """배치 그룹 생성 - 파일 크기를 고려한 동적 그룹핑 (50KB 이상 파일은 단독 그룹)"""
        if not os.path.exists(self.extract_folder):
            self.log("Extract folder not found", 'error')
            return False
        
        # Extract된 파일 목록 가져오기
        xml_files = [f for f in os.listdir(self.extract_folder) if f.lower().endswith('.xml')]
        
        if not xml_files:
            self.log("No XML files found in extract folder", 'error')
            return False
        
        # 파일명에서 번호 추출하여 정렬
        def extract_number(filename):
            import re
            # 파일명에서 숫자 패턴 찾기 (예: tgt-01-, tgt-145- 등)
            match = re.search(r'tgt-(\d+)-', filename)
            if match:
                return int(match.group(1))
            # 숫자가 없으면 파일명으로 정렬
            return float('inf')
        
        # 번호순으로 정렬
        xml_files = sorted(xml_files, key=extract_number)
        self.log(f"Files sorted by number: {[f'{f} ({extract_number(f)})' for f in xml_files[:5]]}{'...' if len(xml_files) > 5 else ''}")
        
        # 파일 크기 정보 수집
        file_sizes = {}
        large_files = []
        small_files = []
        
        for xml_file in xml_files:
            file_path = os.path.join(self.extract_folder, xml_file)
            try:
                size_kb = os.path.getsize(file_path) / 1024  # KB 단위
                file_sizes[xml_file] = size_kb
                
                # 50KB 이상 파일은 대용량 파일로 분류
                if size_kb >= large_file_threshold_kb:
                    large_files.append(xml_file)
                else:
                    small_files.append(xml_file)
                    
            except OSError:
                file_sizes[xml_file] = 0
                small_files.append(xml_file)
                self.log(f"Could not get size for file: {xml_file}", 'warning')
        
        self.log(f"File classification: Large files (≥{large_file_threshold_kb}KB): {len(large_files)}, Small files (<{large_file_threshold_kb}KB): {len(small_files)}")
        
        # 배치 그룹 생성
        batch_groups = []
        group_counter = 1
        
        # 1. 대용량 파일들을 각각 단독 그룹으로 생성
        for xml_file in large_files:
            file_size = file_sizes[xml_file]
            group_id = f"{self.xml_basename}{group_counter:06d}"
            batch_groups.append({
                'GroupID': group_id,
                'Files': xml_file,  # 단일 파일
                'FileCount': 1,
                'TotalSizeKB': round(file_size, 2),
                'Type': 'Large'
            })
            group_counter += 1
            self.log(f"Created large file group: {group_id} for {xml_file} ({file_size:.2f}KB)")
        
        # 2. 소용량 파일들을 동적 그룹핑
        current_batch = []
        current_size = 0
        
        for xml_file in small_files:
            file_size = file_sizes[xml_file]
            
            # 현재 배치에 추가했을 때의 크기 확인
            if (current_size + file_size <= max_batch_size_kb and 
                len(current_batch) < self.batch_size):
                # 배치에 추가
                current_batch.append(xml_file)
                current_size += file_size
            else:
                # 현재 배치 완료 및 새 배치 시작
                if current_batch:
                    group_id = f"{self.xml_basename}{group_counter:06d}"
                    batch_groups.append({
                        'GroupID': group_id,
                        'Files': ','.join(current_batch),
                        'FileCount': len(current_batch),
                        'TotalSizeKB': round(current_size, 2),
                        'Type': 'Small'
                    })
                    group_counter += 1
                
                # 새 배치 시작
                current_batch = [xml_file]
                current_size = file_size
        
        # 마지막 소용량 배치 처리
        if current_batch:
            group_id = f"{self.xml_basename}{group_counter:06d}"
            batch_groups.append({
                'GroupID': group_id,
                'Files': ','.join(current_batch),
                'FileCount': len(current_batch),
                'TotalSizeKB': round(current_size, 2),
                'Type': 'Small'
            })
        
        # CSV 파일로 저장 (Type 필드 추가)
        with open(self.batch_groups_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['GroupID', 'Files', 'FileCount', 'TotalSizeKB', 'Type'])
            writer.writeheader()
            writer.writerows(batch_groups)
        
        # 초기 상태 파일 생성
        with open(self.batch_status_file, 'w', encoding='utf-8') as f:
            for group in batch_groups:
                f.write(f"[ ]{group['GroupID']}\n")
        
        # 로그 출력 (크기 정보 및 분류 포함)
        total_size = sum(group['TotalSizeKB'] for group in batch_groups)
        large_groups = [g for g in batch_groups if g.get('Type') == 'Large']
        small_groups = [g for g in batch_groups if g.get('Type') == 'Small']
        
        self.log(f"Created {len(batch_groups)} batch groups from {len(xml_files)} files for {self.xml_basename}")
        self.log(f"  - Large file groups (≥{large_file_threshold_kb}KB): {len(large_groups)}")
        self.log(f"  - Small file groups (<{large_file_threshold_kb}KB): {len(small_groups)}")
        self.log(f"Total size: {total_size:.2f} KB, Max small batch size limit: {max_batch_size_kb} KB")
        
        # 각 배치 정보 로그
        for group in batch_groups:
            files_in_group = group['Files'].split(',') if ',' in group['Files'] else [group['Files']]
            if len(files_in_group) == 1:
                # 단일 파일 (대용량 파일)
                file_numbers = [extract_number(files_in_group[0])]
                self.log(f"  {group['GroupID']}: {group['FileCount']} file (#{file_numbers[0]}) [{group.get('Type', 'Unknown')}], {group['TotalSizeKB']} KB")
            else:
                # 다중 파일 (소용량 파일들)
                file_numbers = [extract_number(f) for f in files_in_group]
                self.log(f"  {group['GroupID']}: {group['FileCount']} files (#{min(file_numbers)}-#{max(file_numbers)}) [{group.get('Type', 'Unknown')}], {group['TotalSizeKB']} KB")
        
        return True
    
    def load_batch_groups(self):
        """배치 그룹 정보 로드"""
        if not os.path.exists(self.batch_groups_file):
            return []
        
        batch_groups = []
        with open(self.batch_groups_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                group_info = {
                    'GroupID': row['GroupID'],
                    'Files': row['Files'].split(',') if ',' in row['Files'] else [row['Files']],
                    'FileCount': int(row['FileCount'])
                }
                # TotalSizeKB 필드가 있으면 추가 (하위 호환성)
                if 'TotalSizeKB' in row:
                    group_info['TotalSizeKB'] = float(row['TotalSizeKB'])
                # Type 필드가 있으면 추가 (하위 호환성)
                if 'Type' in row:
                    group_info['Type'] = row['Type']
                batch_groups.append(group_info)
        
        return batch_groups
    
    def load_batch_status(self):
        """배치 상태 정보 로드"""
        if not os.path.exists(self.batch_status_file):
            return {}
        
        status_map = {}
        with open(self.batch_status_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    if line.startswith('[o]'):
                        group_id = line[3:]
                        status_map[group_id] = 'completed'
                    elif line.startswith('[x]'):
                        group_id = line[3:]
                        status_map[group_id] = 'failed'
                    elif line.startswith('[ ]'):
                        group_id = line[3:]
                        status_map[group_id] = 'pending'
        
        return status_map
    
    def update_batch_status(self, group_id, status):
        """배치 상태 업데이트"""
        if not os.path.exists(self.batch_status_file):
            self.log("Batch status file not found", 'error')
            return False
        
        # 현재 상태 읽기
        lines = []
        with open(self.batch_status_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 상태 업데이트
        updated = False
        for i, line in enumerate(lines):
            if group_id in line:
                if status == 'completed':
                    lines[i] = f"[o]{group_id}\n"
                elif status == 'failed':
                    lines[i] = f"[x]{group_id}\n"
                elif status == 'pending':
                    lines[i] = f"[ ]{group_id}\n"
                updated = True
                break
        
        if updated:
            # 파일에 쓰기
            with open(self.batch_status_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            self.log(f"Updated batch status: {group_id} → {status}")
            
            # 진행 상황 업데이트
            self.update_progress()
            return True
        else:
            self.log(f"Group ID not found for status update: {group_id}", 'warning')
            return False
    
    def get_pending_batches(self):
        """처리 대기 중인 배치 목록 반환"""
        batch_groups = self.load_batch_groups()
        batch_status = self.load_batch_status()
        
        pending_batches = []
        for group in batch_groups:
            group_id = group['GroupID']
            status = batch_status.get(group_id, 'pending')
            
            if status in ['pending', 'failed']:
                pending_batches.append({
                    'GroupID': group_id,
                    'Files': group['Files'],
                    'FileCount': group['FileCount'],
                    'Status': status
                })
        
        return pending_batches
    
    def get_batch_summary(self):
        """배치 처리 요약 정보 반환"""
        batch_groups = self.load_batch_groups()
        batch_status = self.load_batch_status()
        
        total = len(batch_groups)
        completed = sum(1 for status in batch_status.values() if status == 'completed')
        failed = sum(1 for status in batch_status.values() if status == 'failed')
        pending = total - completed - failed
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'completion_rate': (completed / total * 100) if total > 0 else 0
        }
    
    def update_progress(self):
        """진행 상황을 JSON 파일에 저장"""
        summary = self.get_batch_summary()
        progress_data = {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'xml_basename': self.xml_basename,
            'summary': summary,
            'xmlwork_folder': self.xmlwork_folder
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
    
    def is_transform_completed(self):
        """Transform 작업이 완전히 완료되었는지 확인"""
        summary = self.get_batch_summary()
        return summary['pending'] == 0 and summary['failed'] == 0
    
    def cleanup_batch_files(self):
        """배치 관련 임시 파일들 정리"""
        files_to_remove = [
            self.batch_groups_file,
            self.batch_status_file,
            self.progress_file
        ]
        
        removed_count = 0
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                removed_count += 1
        
        self.log(f"Cleaned up {removed_count} batch management files for {self.xml_basename}")
        return removed_count


class ColoredFormatter(logging.Formatter):
    """색깔이 있는 로그 포맷터 - 중요한 로그만 색깔 적용"""
    
    # ANSI 색깔 코드 (INFO, DEBUG는 색깔 없음)
    COLORS = {
        'DEBUG': '',              # 색깔 없음
        'INFO': '',               # 색깔 없음
        'WARNING': '\033[33m',    # 노란색 (Yellow)
        'ERROR': '\033[91m',      # 밝은 빨간색 (Bright Red)
        'CRITICAL': '\033[95m',   # 밝은 자주색 (Bright Magenta)
        'RESET': '\033[0m'        # 색깔 리셋
    }
    
    # 굵게 표시할 레벨
    BOLD_LEVELS = {'ERROR', 'CRITICAL'}
    
    def format(self, record):
        # 원본 포맷 적용
        log_message = super().format(record)
        
        # 터미널에서만 색깔 적용 (파일 로그에는 색깔 코드 제외)
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            
            # 색깔이 설정된 레벨만 색깔 적용
            if color:
                # ERROR와 CRITICAL은 굵게 표시
                if record.levelname in self.BOLD_LEVELS:
                    bold = '\033[1m'
                    return f"{bold}{color}{log_message}{reset}"
                else:
                    return f"{color}{log_message}{reset}"
        
        return log_message

# 로깅 설정
def setup_logger(log_file=None, log_level=logging.INFO):
    """색깔이 있는 로깅 설정을 초기화합니다."""
    logger = logging.getLogger('SQLTransformTarget')
    logger.setLevel(logging.DEBUG)
    
    # 기존 핸들러 제거
    if logger.handlers:
        logger.handlers.clear()
    
    # 콘솔 핸들러 설정 (색깔 포함)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 설정 (색깔 코드 없음)
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
                elif line.startswith("CRITICAL:"):
                    logger.critical(f"SUBPROCESS: {line[9:].strip()}")
                else:
                    logger.info(f"SUBPROCESS: {line}")
        
        # 오류 출력 처리
        for line in process.stderr:
            line = line.strip()
            if line:
                # Python logging 형식 파싱 (예: "2025-07-30 00:11:26,023 - INFO - 메시지")
                if " - INFO - " in line:
                    logger.info(f"SUBPROCESS: {line.split(' - INFO - ', 1)[1]}")
                elif " - WARNING - " in line:
                    logger.warning(f"SUBPROCESS: {line.split(' - WARNING - ', 1)[1]}")
                elif " - ERROR - " in line:
                    logger.error(f"SUBPROCESS: {line.split(' - ERROR - ', 1)[1]}")
                elif " - DEBUG - " in line:
                    logger.debug(f"SUBPROCESS: {line.split(' - DEBUG - ', 1)[1]}")
                elif " - CRITICAL - " in line:
                    logger.critical(f"SUBPROCESS: {line.split(' - CRITICAL - ', 1)[1]}")
                # 기존 형식도 지원 (하위 호환성)
                elif line.startswith("INFO:"):
                    logger.info(f"SUBPROCESS: {line[5:].strip()}")
                elif line.startswith("WARNING:"):
                    logger.warning(f"SUBPROCESS: {line[8:].strip()}")
                elif line.startswith("ERROR:"):
                    logger.error(f"SUBPROCESS: {line[6:].strip()}")
                elif line.startswith("DEBUG:"):
                    logger.debug(f"SUBPROCESS: {line[6:].strip()}")
                elif line.startswith("CRITICAL:"):
                    logger.critical(f"SUBPROCESS: {line[9:].strip()}")
                else:
                    # 실제 오류가 아닌 경우 DEBUG 레벨로 처리
                    logger.debug(f"SUBPROCESS STDERR: {line}")
        
        process.wait()
        return process.returncode
    
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return -1

def ensure_directory(directory, logger, use_sudo=False):
    """디렉토리가 존재하는지 확인하고, 없으면 생성합니다."""
    try:
        if os.path.exists(directory):
            logger.debug(f"Directory already exists: {directory}")
            return True
            
        if not use_sudo:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"Directory created: {directory}")
                return True
            except PermissionError as pe:
                logger.warning(f"Permission denied for normal mkdir, trying with sudo: {pe}")
                return ensure_directory(directory, logger, use_sudo=True)
        else:
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
    """파일을 복사합니다."""
    try:
        dest_dir = os.path.dirname(destination)
        if not ensure_directory(dest_dir, logger, use_sudo):
            return False
        
        if not use_sudo:
            try:
                shutil.copy2(source, destination)
                logger.debug(f"Copied file from {source} to {destination}")
                return True
            except PermissionError as pe:
                logger.warning(f"Permission denied for normal copy, trying with sudo: {pe}")
                return copy_file(source, destination, logger, use_sudo=True)
        else:
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

def update_csv_process_status(csv_file_path, xml_file_path, new_status, logger):
    """CSV 파일의 Process 컬럼을 업데이트합니다."""
    try:
        rows = []
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            rows = list(csv_reader)
        
        if not rows:
            logger.error(f"CSV file is empty: {csv_file_path}")
            return False
        
        header = rows[0]
        if len(header) < 7:
            logger.error(f"CSV file does not have enough columns: {csv_file_path}")
            return False
        
        updated = False
        for i, row in enumerate(rows[1:], start=1):
            if len(row) > 1 and row[1].strip() == xml_file_path.strip():
                if len(row) > 6:
                    old_status = row[6].strip()
                    row[6] = new_status
                    logger.info(f"Updated CSV: {xml_file_path} Process: '{old_status}' → '{new_status}'")
                    updated = True
                    break
                else:
                    logger.error(f"Row {i} does not have Process column: {row}")
        
        if not updated:
            logger.warning(f"File not found in CSV for status update: {xml_file_path}")
            return False
        
        with open(csv_file_path, 'w', encoding='utf-8', newline='') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerows(rows)
        
        logger.debug(f"Successfully updated CSV file: {csv_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update CSV file {csv_file_path}: {e}")
        return False

def read_transform_target_list(file_path, logger, mode='all'):
    """변환 대상 목록 CSV 파일을 읽습니다."""
    target_list = []
    
    # merge 모드인 경우 세 개의 CSV 파일을 모두 확인
    if mode == 'merge':
        csv_files = [file_path]
        
        # APP_TRANSFORM_FOLDER에서 추가 파일들 확인
        app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER')
        if app_transform_folder:
            # SampleTransformTarget.csv 추가
            sample_csv = os.path.join(app_transform_folder, 'SampleTransformTarget.csv')
            if os.path.exists(sample_csv):
                csv_files.append(sample_csv)
                logger.info(f"Including SampleTransformTarget.csv for merge mode")
            
            # SQLTransformTargetSelective.csv 추가
            selective_csv = os.path.join(app_transform_folder, 'SQLTransformTargetSelective.csv')
            if os.path.exists(selective_csv):
                csv_files.append(selective_csv)
                logger.info(f"Including SQLTransformTargetSelective.csv for merge mode")
    else:
        csv_files = [file_path]
    
    try:
        for csv_file in csv_files:
            logger.debug(f"Reading CSV file: {csv_file}")
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                header = next(csv_reader, None)
                
                for row_num, row in enumerate(csv_reader, start=2):
                    if not row or len(row) < 7:
                        continue
                    
                    filename = row[1].strip() if len(row) > 1 else ""
                    transform_target = row[5].strip() if len(row) > 5 else ""
                    process_status = row[6].strip() if len(row) > 6 else ""
                    
                    # merge 모드와 다른 모드의 선정 기준 분리
                    if mode == 'merge':
                        # merge 모드: Completed 상태인 파일들만
                        condition = (filename and
                                   not filename.startswith('#') and
                                   transform_target.upper() == 'Y' and
                                   process_status == 'Completed')
                        skip_reason = "Not completed" if process_status != 'Completed' else None
                    else:
                        # 기존 모드: Sampled, Completed가 아닌 파일들
                        condition = (filename and
                                   not filename.startswith('#') and
                                   transform_target.upper() == 'Y' and
                                   process_status not in ['Sampled', 'Completed'])
                        skip_reason = f"Already processed: {process_status}" if process_status in ['Sampled', 'Completed'] else None
                    
                    if condition:
                        if filename not in target_list:  # 중복 제거
                            target_list.append(filename)
                            logger.debug(f"Row {row_num}: Added {filename} (Process: '{process_status}') from {os.path.basename(csv_file)}")
                    else:
                        if not filename:
                            logger.debug(f"Row {row_num}: Skipped - Empty filename")
                        elif filename.startswith('#'):
                            logger.debug(f"Row {row_num}: Skipped - Commented out: {filename}")
                        elif transform_target.upper() != 'Y':
                            logger.debug(f"Row {row_num}: Skipped - Transform Target not Y: {filename}")
                        elif skip_reason:
                            logger.debug(f"Row {row_num}: Skipped - {skip_reason}: {filename}")
        
        logger.info(f"Read {len(target_list)} targets from {len(csv_files)} CSV file(s) for {mode} mode")
        logger.debug(f"Target list: {target_list}")
        return target_list
    
    except Exception as e:
        logger.error(f"Failed to read transform target list from {file_path}: {e}")
        return []

def record_transform_result(xml_basename, merge_file, final_file, logger, original_file_path=None):
    """변환 결과를 SQLTransformResult.csv에 기록 (중복 방지 및 원본 경로 포함)"""
    try:
        # APP_TRANSFORM_FOLDER 환경변수 가져오기
        app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER')
        if not app_transform_folder:
            logger.warning("APP_TRANSFORM_FOLDER environment variable not set")
            return False
        
        result_csv_path = os.path.join(app_transform_folder, 'SQLTransformResult.csv')
        
        # CSV 헤더 정의
        fieldnames = ['XMLBasename', 'OriginalFilePath', 'MergeFilePath', 'FinalFilePath', 'CompletedTime', 'Status']
        
        # 기존 데이터 읽기 (중복 확인용)
        existing_data = []
        file_exists = os.path.exists(result_csv_path)
        
        if file_exists:
            try:
                with open(result_csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_data = list(reader)
            except Exception as e:
                logger.warning(f"Could not read existing CSV data: {e}")
        
        # 중복 제거 (같은 XMLBasename이 있으면 제거)
        filtered_data = [row for row in existing_data if row.get('XMLBasename') != xml_basename]
        
        # 새 데이터 추가
        new_record = {
            'XMLBasename': xml_basename,
            'OriginalFilePath': original_file_path or '',
            'MergeFilePath': merge_file,
            'FinalFilePath': final_file,
            'CompletedTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Status': 'Completed'
        }
        filtered_data.append(new_record)
        
        # 전체 파일 다시 쓰기
        with open(result_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_data)
        
        if xml_basename in [row.get('XMLBasename') for row in existing_data]:
            logger.info(f"Transform result updated (duplicate removed) in {result_csv_path}")
        else:
            logger.info(f"Transform result recorded in {result_csv_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to record transform result: {e}")
        return False

def process_single_batch(group_id, batch_files, extract_folder, transform_folder, prompt_template, origin_suffix, transform_suffix, xmlwork_folder, qlog_folder, qprompt_folder, logger):
    """단일 배치 처리 - 파일 개수 검증 포함"""
    try:
        # 원래 처리해야 할 파일 개수 저장
        expected_file_count = len(batch_files)
        logger.info(f"Batch {group_id}: Expected to process {expected_file_count} files")
        
        # 임시 작업 공간 생성 (그룹ID 기반)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        temp_dir = f"/tmp/batch_{group_id}_{timestamp}"
        batch_input_dir = os.path.join(temp_dir, "input")
        batch_output_dir = os.path.join(temp_dir, "output")
        
        os.makedirs(batch_input_dir, exist_ok=True)
        os.makedirs(batch_output_dir, exist_ok=True)
        
        logger.debug(f"Created temporary workspace for batch {group_id}: {temp_dir}")
        
        # 배치 파일들을 임시 input 폴더로 복사
        copied_files = 0
        missing_files = []
        for filename in batch_files:
            src_path = os.path.join(extract_folder, filename)
            dst_path = os.path.join(batch_input_dir, filename)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                copied_files += 1
            else:
                logger.warning(f"Source file not found for batch {group_id}: {src_path}")
                missing_files.append(filename)
        
        logger.debug(f"Copied {copied_files}/{len(batch_files)} files to batch input for {group_id}")
        
        # 입력 파일이 부족하면 실패 처리
        if copied_files != expected_file_count:
            logger.error(f"Batch {group_id}: Input file count mismatch. Expected: {expected_file_count}, Found: {copied_files}")
            if missing_files:
                logger.error(f"Batch {group_id}: Missing files: {missing_files}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"Input files missing: {missing_files}"
        
        # 배치별 프롬프트 생성
        batch_prompt = prompt_template.replace("{L1FolderName}", xmlwork_folder)
        batch_prompt = batch_prompt.replace("{MAPPER_SRCL1_DIR}", batch_input_dir)
        batch_prompt = batch_prompt.replace("{MAPPER_TGTL1_DIR}", batch_output_dir)
        batch_prompt = batch_prompt.replace("{ORIGIN_SUFFIX}", origin_suffix)
        batch_prompt = batch_prompt.replace("{TRANSFORM_SUFFIX}", transform_suffix)
        batch_prompt = batch_prompt.replace("{BATCH_FILE_COUNT}", str(len(batch_files)))
        
        # 프롬프트 파일 생성 (그룹ID 기반 파일명)
        batch_prompt_file = os.path.join(qprompt_folder, f"{group_id}.prompt")
        with open(batch_prompt_file, 'w', encoding='utf-8') as f:
            f.write(batch_prompt)
        
        logger.debug(f"Created prompt file for batch {group_id}: {batch_prompt_file}")
        
        # Q Chat 실행
        batch_log_file = os.path.join(qlog_folder, f"{group_id}.log")
        cmd = f"q chat --trust-all-tools --no-interactive < {batch_prompt_file} > {batch_log_file}"
        
        # 명령어 히스토리 저장
        cmd_history_file = os.path.join(qprompt_folder, "qchat_command_history.log")
        with open(cmd_history_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {group_id} - {cmd}\n")
        
        logger.info(f"Executing batch {group_id}: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Batch {group_id} execution failed: {result.stderr}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"Q Chat execution failed: {result.stderr}"
        
        # 결과 파일들을 transform 폴더로 복사 및 개수 검증
        copied_count = 0
        output_files = []
        if os.path.exists(batch_output_dir):
            for filename in os.listdir(batch_output_dir):
                if filename.lower().endswith('.xml'):
                    src_path = os.path.join(batch_output_dir, filename)
                    dst_path = os.path.join(transform_folder, filename)
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    output_files.append(filename)
        
        # 파일 개수 검증
        success = (copied_count == expected_file_count)
        
        if success:
            logger.info(f"Batch {group_id} ✓ SUCCESS: {copied_count}/{expected_file_count} files processed correctly")
        else:
            logger.error(f"Batch {group_id} ✗ FAILED: File count mismatch. Expected: {expected_file_count}, Generated: {copied_count}")
            
            # 상세한 파일 비교 로깅
            logger.error(f"Batch {group_id}: Input files: {batch_files}")
            logger.error(f"Batch {group_id}: Output files: {output_files}")
            
            # 누락된 파일 찾기
            input_basenames = [os.path.splitext(f)[0].replace(origin_suffix, transform_suffix) for f in batch_files]
            output_basenames = [os.path.splitext(f)[0] for f in output_files]
            missing_outputs = [f for f in input_basenames if f not in output_basenames]
            
            if missing_outputs:
                logger.error(f"Batch {group_id}: Missing output files: {missing_outputs}")
        
        # 임시 폴더 정리
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug(f"Cleaned up temporary workspace for batch {group_id}")
        
        # 성공 여부와 상세 메시지 반환
        if success:
            return True, f"All {copied_count} files processed successfully"
        else:
            return False, f"File count mismatch: expected {expected_file_count}, got {copied_count}"
        
    except Exception as e:
        logger.error(f"Error processing batch {group_id}: {e}")
        # 임시 폴더 정리
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False, f"Exception occurred: {str(e)}"

def process_xml_file(xml_file, origin_suffix, transform_suffix, mapper_folder, source_sql_mapper_folder, target_sql_mapper_folder, prompt_file, qlog_folder, qprompt_folder, log_level, logger, java_source_folder, use_sudo=False, mode='all', batch_size=10):
    """개선된 XML 파일 처리 함수 - 배치 상태 관리 포함"""
    try:
        # 1. 파일 경로 분석
        xml_path = Path(xml_file)
        xml_name = xml_path.name
        xml_stem = xml_path.stem
        
        # XML 베이스명 추출 (suffix 제거)
        xml_basename = xml_stem.replace(origin_suffix, "")
        logger.info(f"Processing XML: {xml_name} (basename: {xml_basename})")
        
        # 매퍼 폴더 내 상대 경로 구성
        xml_parent_path = str(xml_path.parent)
        source_mapper_path = os.path.abspath(source_sql_mapper_folder)
        
        if xml_parent_path.startswith(source_mapper_path):
            relative_path = os.path.relpath(xml_parent_path, source_mapper_path)
            transform_subfolderstructure = "" if relative_path == "." else relative_path
        else:
            if source_mapper_path in xml_parent_path:
                after_source_mapper = xml_parent_path.replace(source_mapper_path, "").strip("/\\")
                transform_subfolderstructure = after_source_mapper
            else:
                transform_subfolderstructure = ""
        
        # 2. 작업 폴더 구성
        xml_file_basename = Path(xml_file).stem
        xmlwork_folder = os.path.join(mapper_folder, transform_subfolderstructure, xml_file_basename)
        
        # 3. BatchManager 초기화 (xml_basename 전달)
        batch_manager = BatchManager(xmlwork_folder, batch_size=batch_size, logger=logger, xml_basename=xml_basename)
        
        # 4. 폴더 생성
        origin_folder = os.path.join(xmlwork_folder, "origin")
        extract_folder = os.path.join(xmlwork_folder, "extract")
        transform_folder = os.path.join(xmlwork_folder, "transform")
        merge_folder = os.path.join(xmlwork_folder, "merge")
        
        for folder in [origin_folder, extract_folder, transform_folder, merge_folder]:
            ensure_directory(folder, logger)
        
        # 5. 원본 파일 복사
        origin_file_name = f"{xml_stem}{origin_suffix}{xml_path.suffix}"
        origin_file_path = os.path.join(origin_folder, origin_file_name)
        if not copy_file(xml_file, origin_file_path, logger, use_sudo):
            logger.error(f"Failed to copy file to origin folder: {origin_file_path}")
            return False, None, False
        
        # ========== EXTRACT 단계 ==========
        if mode in ['all', 'extract']:
            logger.info(f"[{mode.upper()} MODE] Starting EXTRACT phase for {xml_basename}")
            
            # Extract 완료 여부 확인
            if batch_manager.is_extract_completed():
                logger.info(f"[{mode.upper()} MODE] Extract already completed for {xml_basename}, skipping extraction")
            else:
                # xmlExtractor.py 호출
                extractor_cmd = [
                    "python3",
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "xmlExtractor.py"),
                    "--input", origin_file_path,
                    "--output", extract_folder,
                    f"--log-level={log_level}"
                ]
                
                if run_command(extractor_cmd, logger) != 0:
                    logger.error(f"[{mode.upper()} MODE] xmlExtractor.py failed for {origin_file_path}")
                    return False, None, False
                
                # Extract 완료 플래그 생성
                batch_manager.mark_extract_completed()
                logger.info(f"[{mode.upper()} MODE] Successfully completed extraction for {xml_basename}")
            
            # extract 모드에서는 여기서 종료
            if mode == 'extract':
                logger.info(f"[EXTRACT MODE] Extract phase completed for {xml_basename}")
                return True, f"Extract completed: {extract_folder}", False

        # ========== TRANSFORM 단계 ==========
        if mode in ['all', 'transform']:
            logger.info(f"[{mode.upper()} MODE] Starting TRANSFORM phase for {xml_basename}")
            
            # Extract 완료 여부 확인
            if not batch_manager.is_extract_completed():
                logger.error(f"[{mode.upper()} MODE] Extract not completed for {xml_basename}. Please run extract first.")
                return False, None, False
            
            # 배치 그룹 생성 또는 로드
            if not os.path.exists(batch_manager.batch_groups_file):
                logger.info(f"[{mode.upper()} MODE] Creating batch groups for {xml_basename}...")
                if not batch_manager.create_batch_groups():
                    logger.error(f"[{mode.upper()} MODE] Failed to create batch groups for {xml_basename}")
                    return False, None, False
            
            # 처리 대기 중인 배치 가져오기
            pending_batches = batch_manager.get_pending_batches()
            summary = batch_manager.get_batch_summary()
            
            logger.info(f"[{mode.upper()} MODE] {xml_basename} Batch Summary - Total: {summary['total']}, "
                       f"Completed: {summary['completed']}, Failed: {summary['failed']}, "
                       f"Pending: {summary['pending']} (Success Rate: {summary['completion_rate']:.1f}%)")
            
            if not pending_batches:
                logger.info(f"[{mode.upper()} MODE] All batches already completed for {xml_basename}")
            else:
                logger.info(f"[{mode.upper()} MODE] Processing {len(pending_batches)} pending batches for {xml_basename}")
                
                # 프롬프트 템플릿 읽기
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_template = f.read()
                
                # 각 배치 처리
                for batch_info in pending_batches:
                    group_id = batch_info['GroupID']
                    batch_files = batch_info['Files']
                    
                    logger.info(f"[{mode.upper()} MODE] Processing batch {group_id} ({len(batch_files)} files)")
                    
                    # 배치 처리 결과 (개선된 반환값)
                    batch_success, batch_message = process_single_batch(
                        group_id, batch_files, extract_folder, transform_folder,
                        prompt_template, origin_suffix, transform_suffix,
                        xmlwork_folder, qlog_folder, qprompt_folder, logger
                    )
                    
                    # 상태 업데이트 (파일 개수 검증 결과 기반)
                    if batch_success:
                        batch_manager.update_batch_status(group_id, 'completed')
                        logger.info(f"[{mode.upper()} MODE] ✓ Batch {group_id} completed successfully: {batch_message}")
                    else:
                        batch_manager.update_batch_status(group_id, 'failed')
                        logger.error(f"[{mode.upper()} MODE] ✗ Batch {group_id} failed: {batch_message}")
            
            # transform 모드에서는 여기서 종료
            if mode == 'transform':
                final_summary = batch_manager.get_batch_summary()
                logger.info(f"[TRANSFORM MODE] Transform phase completed for {xml_basename}. "
                           f"Success rate: {final_summary['completion_rate']:.1f}%")
                return True, f"Transform completed: {transform_folder}", batch_manager.is_transform_completed()

        # ========== 파일 개수 검증 및 완료 처리 ==========
        if mode in ['all']:
            logger.info(f"[{mode.upper()} MODE] Starting file count validation for {xml_basename}")
            
            # Transform 완료 여부 확인
            if not os.path.exists(transform_folder) or not os.listdir(transform_folder):
                logger.error(f"[{mode.upper()} MODE] Transform folder is empty for {xml_basename}. Transform not completed.")
                return False, None, False
            
            # 파일 수 검증
            extract_files = [f for f in os.listdir(extract_folder) if f.lower().endswith('.xml')]
            transform_files = [f for f in os.listdir(transform_folder) if f.lower().endswith('.xml')]
            
            files_match = len(extract_files) > 0 and len(extract_files) == len(transform_files)
            logger.info(f"[{mode.upper()} MODE] {xml_basename} File count validation: Extract({len(extract_files)}) vs Transform({len(transform_files)}) - {'✓' if files_match else '✗'}")
            
            # 파일 개수가 일치하면 완료 처리
            if files_match:
                logger.info(f"[{mode.upper()} MODE] {xml_basename} Process completed successfully - file counts match")
                final_transform_file = f"Transform completed: {transform_folder}"
                return True, final_transform_file, True
            else:
                logger.error(f"[{mode.upper()} MODE] {xml_basename} Process incomplete - file count mismatch")
                return True, f"Transform completed but file count mismatch: {transform_folder}", False

        # ========== MERGE 단계 ==========
        if mode in ['merge']:
            logger.info(f"[{mode.upper()} MODE] Starting MERGE phase for {xml_basename}")
            
            # Transform 완료 여부 확인
            if not os.path.exists(transform_folder) or not os.listdir(transform_folder):
                logger.error(f"[{mode.upper()} MODE] Transform folder is empty for {xml_basename}. Please run transform first.")
                return False, None, False
            
            # 파일 수 검증
            extract_files = [f for f in os.listdir(extract_folder) if f.lower().endswith('.xml')]
            transform_files = [f for f in os.listdir(transform_folder) if f.lower().endswith('.xml')]
            
            files_match = len(extract_files) > 0 and len(extract_files) == len(transform_files)
            logger.info(f"[{mode.upper()} MODE] {xml_basename} File count validation: Extract({len(extract_files)}) vs Transform({len(transform_files)}) - {'✓' if files_match else '✗'}")
            
            # 병합 파일 생성
            xmlmerge_file = os.path.join(merge_folder, xml_stem.replace(origin_suffix, transform_suffix) + xml_path.suffix)
            
            # xmlMerger.py 호출
            merger_cmd = [
                "python3",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "xmlMerger.py"),
                "--input", transform_folder,
                "--output", xmlmerge_file,
                f"--log-level={log_level}"
            ]
            
            if run_command(merger_cmd, logger) != 0:
                logger.error(f"[{mode.upper()} MODE] xmlMerger.py failed for {xml_basename}")
                return False, None, False
            
            # 최종 파일 복사
            cp_target_folder_structure = transform_subfolderstructure
            cp_target_folder = os.path.join(target_sql_mapper_folder, cp_target_folder_structure)
            ensure_directory(cp_target_folder, logger)
            
            final_transform_file = os.path.join(cp_target_folder, xml_stem.replace(origin_suffix, "") + xml_path.suffix)
            
            if not copy_file(xmlmerge_file, final_transform_file, logger, use_sudo):
                logger.error(f"[{mode.upper()} MODE] Failed to copy final transformed file for {xml_basename}")
                return False, None, False
            
            # 프로세스 완료 여부 결정
            merge_success = os.path.exists(xmlmerge_file)
            process_completed = files_match and merge_success
            
            logger.info(f"[{mode.upper()} MODE] {xml_basename} Merge completed: {xmlmerge_file}")
            logger.info(f"[{mode.upper()} MODE] {xml_basename} Final file: {final_transform_file}")
            logger.info(f"[{mode.upper()} MODE] {xml_basename} Process completed: {'✓' if process_completed else '✗'}")
            
            # SQLTransformResult.csv에 결과 기록
            if merge_success:
                record_transform_result(xml_basename, xmlmerge_file, final_transform_file, logger, xml_file)
            
            return True, final_transform_file, process_completed
    
    except Exception as e:
        logger.error(f"Error processing XML file {xml_file}: {e}")
        return False, None, False


def main():
    """메인 함수 - 개선된 배치 상태 관리 포함"""
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
    parser = argparse.ArgumentParser(description='MyBatis XML 변환 대상 처리 프로그램 (V3.0 개선 버전)')
    parser.add_argument('-f', '--file', dest='transform_target_list', help='변환 대상 목록 CSV 파일 경로')
    parser.add_argument('-o', '--origin-suffix', dest='origin_suffix', default='_src', help='원본 파일 접미사 (기본값: _src)')
    parser.add_argument('-s', '--transform-suffix', dest='transform_suffix', default='_tgt', help='변환 파일 접미사 (기본값: _tgt)')
    parser.add_argument('-l', '--log', help='로그 파일 경로', default=None)
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로깅 활성화 (--log-level DEBUG와 동일)')
    parser.add_argument('--log-level', choices=log_level_choices, default='INFO',
                        help='로그 레벨 설정 (기본값: INFO)')
    parser.add_argument('-t', '--test', action='store_true', help='테스트 모드 활성화')
    parser.add_argument('--use-sudo', action='store_true', help='파일 복사 시 sudo 사용 (권한 이슈 해결)')
    parser.add_argument('--mode', choices=['all', 'extract', 'transform', 'merge'], default='all',
                        help='실행 모드 선택: all(전체), extract(추출만), transform(변환만), merge(병합만) (기본값: all)')
    parser.add_argument('--batch-size', type=int, default=10, help='배치 크기 설정 (기본값: 10)')
    parser.add_argument('--cleanup-batch', action='store_true', help='완료 후 배치 관리 파일 정리')
    
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
        
        log_level_str = 'DEBUG'
        java_source_folder = '/Users/changik//workspace/oracle-modernization-accelerator/SampleApp/jpetstore-6/src'
        source_sql_mapper_folder = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Transform/mapper'
        target_sql_mapper_folder = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Transform/mapper_target'
        app_logs_folder = '/Users/changik//workspace/oracle-modernization-accelerator//Application/bnd_b2eg/Logs'
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
    log_folder = app_logs_folder
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
    
    logger.info("Starting sqlTransformTarget.py V3.0 (Improved with Batch Management)")
    logger.info(f"Execution Mode: {args.mode.upper()}")
    logger.info(f"Batch Size: {args.batch_size}")
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
    
    # 2. 변환 대상 목록 파일 존재 확인
    if not os.path.exists(transform_target_list):
        logger.error(f"Transform target list file not found: {transform_target_list}")
        sys.exit(1)
    
    # 3. 변환 대상 목록 읽기
    target_files = read_transform_target_list(transform_target_list, logger, args.mode)
    
    if not target_files:
        logger.info(f"All rows are completed, no targets to process in {transform_target_list}")
        logger.info("Processing criteria: Transform Target = 'Y' and Process is not 'Sampled' or 'Completed'")
        sys.exit(0)
    
    # 4. 각 대상 파일 처리 (멀티스레드)
    # 결과를 저장할 딕셔너리 (스레드 안전을 위해 락 사용)
    results_lock = threading.Lock()
    results = {
        'successful': 0,
        'failed': 0,
        'total': len(target_files),
        'completed': 0
    }
    
    # 파일 처리 함수 (스레드에서 실행)
    def process_file(target_file):
        thread_name = threading.current_thread().name
        logger.info(f"[{thread_name}] Processing target file: {target_file}")
        
        success, transformed_file, process_completed = process_xml_file(
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
            args.use_sudo,
            args.mode,
            args.batch_size
        )
        
        # CSV 업데이트 (all 또는 merge 모드에서 프로세스가 완료된 경우)
        if success and process_completed and args.mode in ['all', 'merge']:
            csv_updated = update_csv_process_status(transform_target_list, target_file, 'Completed', logger)
            if csv_updated:
                logger.info(f"[{thread_name}] ✓ CSV updated: {target_file} marked as Completed")
            else:
                logger.warning(f"[{thread_name}] ✗ Failed to update CSV for: {target_file}")
        
        # 결과 업데이트 (락 사용)
        with results_lock:
            if success:
                logger.info(f"[{thread_name}] Successfully processed {target_file}")
                if transformed_file:
                    logger.info(f"[{thread_name}] Result: {transformed_file}")
                results['successful'] += 1
                if process_completed:
                    results['completed'] += 1
            else:
                logger.error(f"[{thread_name}] Failed to process {target_file}")
                results['failed'] += 1
    
    # ThreadPoolExecutor를 사용하여 멀티스레드 처리
    logger.info(f"Starting transformation with {thread_count} threads")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        # 모든 파일에 대해 작업 제출
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
    
    # 5. 검증 프로세스 호출 (merge 모드에서만)
    if args.mode == 'merge':
        logger.info("Starting validation process...")
        validation_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transformValidation.py")

        try:
            # transformValidation.py는 파라미터를 사용하지 않고 환경변수만 사용함
            validation_cmd = [
                "python3", 
                validation_script
            ]
            
            logger.info(f"Running validation with command: {' '.join(validation_cmd)}")
            logger.info("Note: transformValidation.py uses environment variables (APP_TRANSFORM_FOLDER, TARGET_SQL_MAPPER_FOLDER)")
            
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
    else:
        logger.info(f"Skipping validation process for {args.mode.upper()} mode")
    
    logger.info(f"XML validation process {'executed' if args.mode == 'merge' else 'skipped'} for {args.mode.upper()} mode")

    # 6. 결과 요약
    logger.info("="*80)
    logger.info("TRANSFORM PROCESS COMPLETED")
    logger.info("="*80)
    logger.info(f"Total target files: {len(target_files)}")
    logger.info(f"Total files processed: {results['total']}")
    logger.info(f"Successful processes: {results['successful']}")
    logger.info(f"Failed processes: {results['failed']}")
    logger.info(f"Fully completed (marked as Completed): {results['completed']}")
    logger.info(f"Total execution time: {execution_time:.2f} seconds")
    logger.info(f"Average time per file: {execution_time/len(target_files):.2f} seconds")
    
    # 배치 관리 파일 정리 (옵션)
    if args.cleanup_batch:
        logger.info("Cleaning up batch management files...")
        cleanup_count = 0
        for target_file in target_files:
            xml_path = Path(target_file)
            xml_stem = xml_path.stem
            xml_basename = xml_stem.replace(origin_suffix, "")
            xml_file_basename = Path(target_file).stem
            xmlwork_folder = os.path.join(mapper_processing_folder, xml_file_basename)
            
            if os.path.exists(xmlwork_folder):
                batch_manager = BatchManager(xmlwork_folder, logger=logger, xml_basename=xml_basename)
                cleanup_count += batch_manager.cleanup_batch_files()
        
        logger.info(f"Cleaned up batch files for {cleanup_count} XML files")
    
    # 실패한 변환이 있으면 경고 메시지 출력
    if results['failed'] > 0:
        logger.warning("Some processes failed. Check the log for details.")
        sys.exit(1)

    # 7. 검증 결과 리포팅 (merge 모드에서만) - XML validation 결과 리포팅 주석처리
    if args.mode == 'merge':
        # Check SQLTransformTargetSelective.csv
        failure_csv = os.path.join(app_transform_folder, 'SQLTransformTargetSelective.csv')
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

        # XML validation 결과 리포팅 주석처리
        # Check xmllintResult.csv
        # xmllint_csv = os.path.join(app_transform_folder, 'xmllintResult.csv')
        # if os.path.exists(xmllint_csv):
        #     with open(xmllint_csv, 'r', encoding='utf-8') as f:
        #         reader = csv.DictReader(f)
        #         xml_failures = [row for row in reader if row['Message'].startswith('Error')]
        #         if xml_failures:
        #             logger.warning("\n" + "="*80)
        #             logger.warning("XML VALIDATION FAILURES DETECTED:")
        #             logger.warning("="*80)
        #             for failure in xml_failures:
        #                 logger.warning(f"File: {failure['FileName']}")
        #                 logger.warning(f"Path: {failure['Path']}")
        #                 logger.warning(f"Error: {failure['Message']}")
        #                 logger.warning("-"*80)
        #             logger.warning(f"Total XML validation failures: {len(xml_failures)}")
        #             logger.warning("="*80 + "\n")
    
    logger.info("="*80)
    logger.info(f"All {args.mode.upper()} operations completed successfully")
    logger.info("="*80)

if __name__ == "__main__":
    main()
