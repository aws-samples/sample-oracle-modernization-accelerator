import csv
import sys
import os
import re
from pathlib import Path

def replace_in_file(file_path, line_number, old_text, new_text):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        if 1 <= line_number <= len(lines):
            # 해당 라인에서 old_text를 new_text로 대체
            lines[line_number - 1] = lines[line_number - 1].replace(old_text, new_text)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            return True
        else:
            print(f"라인 번호 오류: {file_path}의 {line_number}번 라인이 존재하지 않습니다.")
            return False
    except Exception as e:
        print(f"파일 수정 중 오류 발생: {file_path}, {str(e)}")
        return False

def convert_uppercase_to_lowercase(csv_file, backup_dir=None):
    if backup_dir and not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    modified_files = set()
    success_count = 0
    error_count = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['has_uppercase'].lower() == 'true':
                file_path = row['file_path']
                line_number = int(row['line_number'])
                old_text = row['matched_text']
                new_text = row['lowercase_version']
                
                # 파일 백업 (아직 백업되지 않은 경우)
                if backup_dir and file_path not in modified_files:
                    file_name = os.path.basename(file_path)
                    backup_path = os.path.join(backup_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                            dst.write(src.read())
                        modified_files.add(file_path)
                    except Exception as e:
                        print(f"백업 중 오류 발생: {file_path}, {str(e)}")
                
                # 파일 내용 변경
                if replace_in_file(file_path, line_number, old_text, new_text):
                    success_count += 1
                    print(f"변환 성공: {file_path}:{line_number} - '{old_text}' → '{new_text}'")
                else:
                    error_count += 1
    
    print(f"\n변환 작업 완료:")
    print(f"- 성공: {success_count}개")
    print(f"- 실패: {error_count}개")
    print(f"- 수정된 파일 수: {len(modified_files)}개")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python convert_case.py <analysis_csv> [backup_directory]")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    backup_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_uppercase_to_lowercase(csv_file, backup_dir)
