import os
import re
import csv
import sys
from pathlib import Path

def find_sql_patterns(java_file_path):
    results = []
    try:
        with open(java_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # 파일 내용 라인 번호 추적을 위한 처리
            lines = content.split('\n')
            
            # SQL 쿼리 패턴 (문자열 내부의 SQL 구문)
            sql_patterns = [
                r'(?:executeQuery|execute|prepareStatement|createQuery)\s*\(\s*["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP)[^"\']*)["\']',
                r'(?:sql|query|SQL|QUERY)\s*=\s*["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP)[^"\']*)["\']',
                r'(?:HQL|hql)\s*=\s*["\']([^"\']*(?:FROM|JOIN|WHERE|GROUP BY|ORDER BY)[^"\']*)["\']'
            ]
            
            # 컬럼 참조 패턴
            column_patterns = [
                r'\.get(?:String|Int|Long|Double|Boolean|Date|Timestamp|Object)\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
                r'\.set(?:String|Int|Long|Double|Boolean|Date|Timestamp|Object)\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
                r'\.put\s*\(\s*["\']([A-Z_][A-Z0-9_]*)["\']',
                r'@Column\s*\(\s*name\s*=\s*["\']([A-Z_][A-Z0-9_]*)["\']'
            ]
            
            # 모든 패턴에 대해 검색
            for pattern_type, patterns in [("SQL", sql_patterns), ("COLUMN", column_patterns)]:
                for pattern in patterns:
                    for i, line in enumerate(lines):
                        for match in re.finditer(pattern, line):
                            matched_text = match.group(1)
                            # 대문자 포함 여부 확인
                            has_uppercase = bool(re.search(r'[A-Z]', matched_text))
                            
                            results.append({
                                'file_path': java_file_path,
                                'line_number': i + 1,
                                'pattern_type': pattern_type,
                                'matched_text': matched_text,
                                'has_uppercase': has_uppercase,
                                'lowercase_version': matched_text.lower() if has_uppercase else matched_text
                            })
        
        return results
    except Exception as e:
        print(f"Error processing {java_file_path}: {str(e)}", file=sys.stderr)
        return []

def process_java_files(java_files_list, output_csv):
    all_results = []
    
    with open(java_files_list, 'r') as file_list:
        for line in file_list:
            java_file = line.strip()
            if java_file and os.path.exists(java_file):
                results = find_sql_patterns(java_file)
                all_results.extend(results)
    
    # CSV 파일로 결과 저장
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['file_path', 'line_number', 'pattern_type', 'matched_text', 'has_uppercase', 'lowercase_version']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in all_results:
            writer.writerow(result)
    
    print(f"분석 완료: {len(all_results)}개의 패턴이 발견되었습니다.")
    print(f"결과가 {output_csv}에 저장되었습니다.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python script.py <java_files_list.txt> <output_csv>")
        sys.exit(1)
    
    java_files_list = sys.argv[1]
    output_csv = sys.argv[2]
    
    process_java_files(java_files_list, output_csv)
