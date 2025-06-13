#!/usr/bin/env python3
#############################################################################
# Script: DB02.FindXMLFiles.py
# Description: This script searches for XML files in a specified directory
#              and creates a list file containing their paths.
#
# Functionality:
# - Recursively searches through directories to find XML files
# - Can filter for specific XML types:
#   * PostgreSQL XML files (*pg.xml) using the --pg flag
#   * Oracle XML files (*orcl.xml) using the --orcl flag
# - Saves the list of found XML files to an output file:
#   * Default: xml.lst
#   * For PostgreSQL: pg_xml.lst
#   * For Oracle: orcl_xml.lst
#
# Usage:
#   python3 DB02.FindXMLFiles.py /path/to/search [--pg | --orcl]
#
# Example:
#   python3 DB02.FindXMLFiles.py /data/xml_files --pg
#############################################################################

import os
import sys
import glob
import argparse

def find_xml_files(directory, file_type=None):
    """
    주어진 디렉토리 아래의 XML 파일을 찾아 리스트로 반환합니다.
    file_type이 'pg'이면 *pg.xml 파일만, 'orcl'이면 *orcl.xml 파일만 찾습니다.
    file_type이 None이면 모든 XML 파일을 찾습니다.
    """
    if not os.path.isdir(directory):
        print(f"오류: '{directory}'는 유효한 디렉토리가 아닙니다.")
        sys.exit(1)

    # 디렉토리 내의 XML 파일 경로를 찾습니다 (대소문자 구분 없이)
    xml_files = []
    for root, _, _ in os.walk(directory):
        if file_type == 'pg':
            xml_files.extend(glob.glob(os.path.join(root, "*pg.xml")))
            xml_files.extend(glob.glob(os.path.join(root, "*pg.XML")))
        elif file_type == 'orcl':
            xml_files.extend(glob.glob(os.path.join(root, "*orcl.xml")))
            xml_files.extend(glob.glob(os.path.join(root, "*orcl.XML")))
        else:
            xml_files.extend(glob.glob(os.path.join(root, "*.xml")))
            xml_files.extend(glob.glob(os.path.join(root, "*.XML")))

    return xml_files

def save_to_file(file_list, output_file="xml.lst"):
    """
    파일 목록을 지정된 출력 파일에 저장합니다.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for file_path in file_list:
            f.write(f"{file_path}\n")

    print(f"총 {len(file_list)}개의 XML 파일 목록이 '{output_file}'에 저장되었습니다.")

def main():
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(description='XML 파일을 찾아 목록을 생성합니다.')
    parser.add_argument('directory', help='검색할 디렉토리 경로')
    parser.add_argument('--pg', action='store_true', help='*pg.xml 파일만 검색')
    parser.add_argument('--orcl', action='store_true', help='*orcl.xml 파일만 검색')
    
    args = parser.parse_args()
    
    # 파일 타입 결정
    file_type = None
    if args.pg:
        file_type = 'pg'
    elif args.orcl:
        file_type = 'orcl'
    
    # 파일 검색
    xml_files = find_xml_files(args.directory, file_type)

    if not xml_files:
        print(f"'{args.directory}' 디렉토리 아래에서 조건에 맞는 XML 파일을 찾을 수 없습니다.")
    else:
        # 출력 파일명 결정
        output_file = "xml.lst"
        if file_type:
            output_file = f"{file_type}_xml.lst"
        
        save_to_file(xml_files, output_file)

if __name__ == "__main__":
    main()
