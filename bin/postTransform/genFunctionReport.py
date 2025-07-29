#!/usr/bin/env python3
"""
Function 문법 테스트 결과 보고서 생성기
sqlTestResult.json 파일을 분석하여 HTML 보고서를 생성합니다.

사용법: python3 genFunctionReport.py
입력: sqlTestResult.json
출력: function_test_report.html
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
import os

def load_json_data(file_path):
    """JSON 파일을 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_success(item):
    """항목이 성공인지 판단합니다."""
    status = item.get('status', '')
    message = item.get('message', '')
    
    if status == 'success':
        return True
    
    if '함수를 찾을 수 없습니다' in message:
        return True
    
    return False

def extract_mysql_functions(sql):
    """SQL에서 MySQL 함수들을 추출합니다."""
    if not sql:
        return []
    
    mysql_functions = {
        'NOW': 'MySQL 현재 날짜/시간 반환',
        'DATE_FORMAT': 'MySQL 날짜 포맷팅',
        'DATE_SUB': 'MySQL 날짜 빼기',
        'DATE_ADD': 'MySQL 날짜 더하기',
        'CURDATE': 'MySQL 현재 날짜',
        'CURTIME': 'MySQL 현재 시간',
        'CONCAT': 'MySQL 문자열 연결',
        'SUBSTRING': 'MySQL 부분 문자열 추출',
        'LENGTH': 'MySQL 문자열 길이',
        'UPPER': 'MySQL 대문자 변환',
        'LOWER': 'MySQL 소문자 변환',
        'TRIM': 'MySQL 공백 제거',
        'REPLACE': 'MySQL 문자열 치환',
        'LEFT': 'MySQL 왼쪽 문자열',
        'RIGHT': 'MySQL 오른쪽 문자열',
        'LPAD': 'MySQL 왼쪽 패딩',
        'RPAD': 'MySQL 오른쪽 패딩',
        'GROUP_CONCAT': 'MySQL 그룹 문자열 연결',
        'COUNT': 'MySQL 개수 집계',
        'SUM': 'MySQL 합계',
        'AVG': 'MySQL 평균',
        'MIN': 'MySQL 최솟값',
        'MAX': 'MySQL 최댓값',
        'IF': 'MySQL 조건 함수',
        'IFNULL': 'MySQL NULL 처리',
        'CASE': 'MySQL CASE 문',
        'COALESCE': 'MySQL NULL 병합',
        'CAST': 'MySQL 타입 변환',
        'CONVERT': 'MySQL 변환',
        'NULLIF': 'MySQL NULL 비교'
    }
    
    found_functions = []
    
    for func_name in mysql_functions.keys():
        pattern = rf'\b{func_name}\s*\('
        matches = re.findall(pattern, sql, re.IGNORECASE)
        if matches:
            found_functions.extend([func_name.upper()] * len(matches))
    
    return found_functions

def get_oracle_compatibility(func_name):
    """Oracle과의 호환성 정보를 반환합니다."""
    oracle_compat = {
        'COUNT': '완전 호환',
        'SUM': '완전 호환',
        'AVG': '완전 호환',
        'MIN': '완전 호환',
        'MAX': '완전 호환',
        'UPPER': '완전 호환',
        'LOWER': '완전 호환',
        'TRIM': '완전 호환',
        'SUBSTRING': '완전 호환',
        'REPLACE': '완전 호환',
        'CASE': '완전 호환',
        'CAST': '완전 호환',
        'COALESCE': '완전 호환',
        'NULLIF': '완전 호환',
        'CONCAT': '부분 호환 (Oracle: ||)',
        'IFNULL': '부분 호환 (Oracle: NVL)',
        'IF': '부분 호환 (Oracle: DECODE)',
        'DATE_FORMAT': '부분 호환 (Oracle: TO_CHAR)',
        'LENGTH': '부분 호환',
        'LEFT': '부분 호환 (Oracle: SUBSTR)',
        'RIGHT': '부분 호환 (Oracle: SUBSTR)',
        'LPAD': '부분 호환',
        'RPAD': '부분 호환',
        'CONVERT': '부분 호환',
        'NOW': 'MySQL 전용 (Oracle: SYSDATE)',
        'CURDATE': 'MySQL 전용 (Oracle: TRUNC(SYSDATE))',
        'CURTIME': 'MySQL 전용',
        'DATE_SUB': 'MySQL 전용 (Oracle: - INTERVAL)',
        'DATE_ADD': 'MySQL 전용 (Oracle: + INTERVAL)',
        'GROUP_CONCAT': 'MySQL 전용 (Oracle: LISTAGG)'
    }
    
    return oracle_compat.get(func_name, '확인 필요')

def format_sql_for_display(sql):
    """SQL을 보기 좋게 포맷팅합니다."""
    if not sql:
        return ""
    
    # 기본 포맷팅 (줄바꿈과 들여쓰기)
    formatted_sql = sql
    
    # 주요 키워드 앞에서 줄바꿈
    for keyword in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING']:
        formatted_sql = formatted_sql.replace(f' {keyword} ', f'\n{keyword} ')
    
    # CASE 문 포맷팅
    formatted_sql = formatted_sql.replace('CASE WHEN', '\nCASE WHEN')
    formatted_sql = formatted_sql.replace(' WHEN ', '\n    WHEN ')
    formatted_sql = formatted_sql.replace(' THEN ', ' THEN ')
    formatted_sql = formatted_sql.replace(' ELSE ', '\n    ELSE ')
    formatted_sql = formatted_sql.replace(' END', '\nEND')
    
    # 콤마 뒤 줄바꿈 (SELECT 절에서)
    lines = formatted_sql.split('\n')
    formatted_lines = []
    
    for line in lines:
        if line.strip().startswith('SELECT'):
            # SELECT 절의 콤마 처리
            parts = line.split(',')
            if len(parts) > 1:
                formatted_lines.append(parts[0])
                for part in parts[1:]:
                    formatted_lines.append('    ,' + part.strip())
            else:
                formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def get_css_styles():
    """CSS 스타일을 반환합니다."""
    return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            font-size: 1.2em;
        }
        .stat-card .number {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .success-card {
            background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
        }
        .error-card {
            background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        }
        .info-card {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .status-success {
            color: #27ae60;
            font-weight: bold;
        }
        .status-error {
            color: #e74c3c;
            font-weight: bold;
        }
        .status-completed {
            color: #f39c12;
            font-weight: bold;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #56ab2f 0%, #a8e6cf 100%);
            border-radius: 15px;
            transition: width 0.3s ease;
        }
        .note {
            background-color: #e8f4fd;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .principle-note {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .principle-note ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .principle-note li {
            margin: 8px 0;
            font-weight: 500;
        }
        .sql-sample {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin: 20px 0;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .sql-header {
            background: linear-gradient(135deg, #495057 0%, #6c757d 100%);
            color: white;
            padding: 12px 20px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.9em;
            font-weight: 600;
            border-bottom: 1px solid #dee2e6;
        }
        .sql-content {
            padding: 20px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.85em;
            line-height: 1.5;
            background-color: #ffffff;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #2d3748;
        }
        .compatibility-full {
            color: #28a745;
            font-weight: bold;
        }
        .compatibility-partial {
            color: #ffc107;
            font-weight: bold;
        }
        .compatibility-mysql {
            color: #dc3545;
            font-weight: bold;
        }
        .compatibility-check {
            color: #6c757d;
            font-style: italic;
        }
    """

def analyze_data(data):
    """데이터를 분석하여 통계를 생성합니다."""
    stats = {
        'total_files': len(data),
        'status_counts': Counter(),
        'success_types': Counter(),
        'functions_stats': {
            'total_functions': 0,
            'total_unique_functions': 0,
            'avg_functions_per_file': 0,
            'avg_unique_functions_per_file': 0
        },
        'mapper_types': Counter(),
        'success_rate': 0,
        'files_by_status': defaultdict(list),
        'timestamp_range': {'earliest': None, 'latest': None},
        'sql_samples': [],
        'function_usage': Counter()
    }
    
    total_functions = 0
    total_unique_functions = 0
    timestamps = []
    success_count = 0
    
    for item in data:
        if is_success(item):
            success_count += 1
            if item.get('status') == 'success':
                stats['success_types']['함수 검증 성공'] += 1
            elif '함수를 찾을 수 없습니다' in item.get('message', ''):
                stats['success_types']['대상 아님 (함수 없음)'] += 1
        
        status = item.get('status', 'unknown')
        stats['status_counts'][status] += 1
        stats['files_by_status'][status].append(item)
        
        functions_count = item.get('functions_count', 0)
        unique_functions_count = item.get('unique_functions_count', 0)
        total_functions += functions_count
        total_unique_functions += unique_functions_count
        
        if item.get('status') == 'success' and item.get('sql'):
            sql = item.get('sql', '')
            if sql and len(sql) > 50:
                stats['sql_samples'].append({
                    'file': item.get('file', '').split('/')[-1],
                    'sql': sql,
                    'functions_count': functions_count,
                    'unique_functions_count': unique_functions_count
                })
        
        if item.get('sql'):
            functions_in_sql = extract_mysql_functions(item.get('sql', ''))
            stats['function_usage'].update(functions_in_sql)
        
        file_path = item.get('file', '')
        if 'mapper' in file_path.lower():
            parts = file_path.split('/')
            for part in parts:
                if 'Mapper' in part:
                    stats['mapper_types'][part] += 1
                    break
        
        timestamp = item.get('timestamp')
        if timestamp:
            timestamps.append(timestamp)
    
    stats['functions_stats']['total_functions'] = total_functions
    stats['functions_stats']['total_unique_functions'] = total_unique_functions
    if stats['total_files'] > 0:
        stats['functions_stats']['avg_functions_per_file'] = total_functions / stats['total_files']
        stats['functions_stats']['avg_unique_functions_per_file'] = total_unique_functions / stats['total_files']
    
    stats['success_count'] = success_count
    stats['success_rate'] = (success_count / stats['total_files']) * 100 if stats['total_files'] > 0 else 0
    
    if timestamps:
        timestamps.sort()
        stats['timestamp_range']['earliest'] = timestamps[0]
        stats['timestamp_range']['latest'] = timestamps[-1]
    
    stats['sql_samples'].sort(key=lambda x: x['functions_count'], reverse=True)
    
    return stats

def generate_html_report(stats, data):
    """HTML 보고서를 생성합니다."""
    
    css_styles = get_css_styles()
    
    # SQL 샘플 생성 (상위 5개)
    sql_samples_html = ""
    for i, sample in enumerate(stats['sql_samples'][:5], 1):
        formatted_sql = format_sql_for_display(sample['sql'])
        if len(formatted_sql) > 800:
            formatted_sql = formatted_sql[:800] + "\n..."
        
        sql_samples_html += f"""
        <div class="sql-sample">
            <div class="sql-header">
                Sample {i}: {sample['file']} (함수 {sample['functions_count']}개, 고유 {sample['unique_functions_count']}개)
            </div>
            <div class="sql-content">{formatted_sql}</div>
        </div>
        """
    
    # 함수 사용 통계 테이블 생성
    function_stats_rows = ""
    func_descriptions = {
        'IFNULL': 'NULL 값을 다른 값으로 대체',
        'CONCAT': '문자열 연결',
        'SUM': '합계 계산',
        'MIN': '최솟값 반환',
        'MAX': '최댓값 반환',
        'COUNT': '행 개수 계산',
        'CASE': '조건부 값 반환',
        'GROUP_CONCAT': '그룹별 문자열 연결',
        'DATE_FORMAT': '날짜 포맷팅',
        'NOW': '현재 날짜/시간',
        'DATE_SUB': '날짜에서 시간 빼기',
        'AVG': '평균값 계산',
        'UPPER': '대문자 변환',
        'LOWER': '소문자 변환',
        'TRIM': '공백 제거',
        'SUBSTRING': '부분 문자열 추출',
        'LENGTH': '문자열 길이',
        'REPLACE': '문자열 치환',
        'LEFT': '왼쪽 문자열 추출',
        'RIGHT': '오른쪽 문자열 추출',
        'LPAD': '왼쪽 패딩',
        'RPAD': '오른쪽 패딩',
        'CAST': '타입 변환',
        'CONVERT': '데이터 변환',
        'COALESCE': 'NULL 병합',
        'NULLIF': 'NULL 비교',
        'IF': '조건 함수'
    }
    
    for func_name, count in stats['function_usage'].most_common():
        description = func_descriptions.get(func_name, f'{func_name} 함수')
        compatibility = get_oracle_compatibility(func_name)
        
        compat_class = ""
        if "완전 호환" in compatibility:
            compat_class = "compatibility-full"
        elif "부분 호환" in compatibility:
            compat_class = "compatibility-partial"
        elif "MySQL 전용" in compatibility:
            compat_class = "compatibility-mysql"
        else:
            compat_class = "compatibility-check"
        
        function_stats_rows += f"""
        <tr>
            <td><strong>{func_name}</strong></td>
            <td>{description}</td>
            <td>{count}</td>
            <td class="{compat_class}">{compatibility}</td>
        </tr>
        """
    
    # 성공 유형별 분석 테이블
    success_type_rows = ""
    for success_type, count in stats['success_types'].most_common():
        percentage = (count / stats['success_count']) * 100 if stats['success_count'] > 0 else 0
        success_type_rows += f"""
        <tr>
            <td class="status-success">{success_type}</td>
            <td>{count}</td>
            <td>{percentage:.1f}%</td>
        </tr>
        """
    
    # 원본 상태별 통계 테이블
    status_rows = ""
    for status, count in stats['status_counts'].most_common():
        percentage = (count / stats['total_files']) * 100
        status_class = f"status-{status}" if status in ['success', 'error', 'completed'] else ""
        status_rows += f"""
        <tr>
            <td class="{status_class}">{status}</td>
            <td>{count}</td>
            <td>{percentage:.1f}%</td>
        </tr>
        """
    
    # 매퍼 타입별 통계 테이블
    mapper_rows = ""
    for mapper_type, count in stats['mapper_types'].most_common(10):
        mapper_rows += f"""
        <tr>
            <td>{mapper_type}</td>
            <td>{count}</td>
        </tr>
        """
    
    def format_timestamp(ts):
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return ts
        return 'N/A'
    
    # HTML 생성
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Function 문법 테스트 결과</title>
    <style>
        {css_styles}
    </style>
</head>
<body>
    <div class="container">
        <h1>Function 문법 테스트 결과</h1>
        
        <div class="note">
            <strong>성공 기준:</strong> 
            <ul>
                <li>함수 검증 성공: 실제 SQL 함수가 검증된 경우</li>
                <li>대상 아님: "함수를 찾을 수 없습니다" - 변환 대상이 아닌 파일</li>
            </ul>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card info-card">
                <h3>총 파일 수</h3>
                <div class="number">{stats['total_files']}</div>
            </div>
            <div class="stat-card success-card">
                <h3>성공한 파일</h3>
                <div class="number">{stats['success_count']}</div>
            </div>
            <div class="stat-card error-card">
                <h3>실패한 파일</h3>
                <div class="number">{stats['total_files'] - stats['success_count']}</div>
            </div>
            <div class="stat-card info-card">
                <h3>성공률</h3>
                <div class="number">{stats['success_rate']:.1f}%</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card info-card">
                <h3>총 함수 수</h3>
                <div class="number">{stats['functions_stats']['total_functions']}</div>
            </div>
            <div class="stat-card info-card">
                <h3>고유 함수 수</h3>
                <div class="number">{stats['functions_stats']['total_unique_functions']}</div>
            </div>
            <div class="stat-card info-card">
                <h3>파일당 평균 함수</h3>
                <div class="number">{stats['functions_stats']['avg_functions_per_file']:.1f}</div>
            </div>
            <div class="stat-card info-card">
                <h3>파일당 평균 고유 함수</h3>
                <div class="number">{stats['functions_stats']['avg_unique_functions_per_file']:.1f}</div>
            </div>
        </div>

        <h2>성공률 시각화</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {stats['success_rate']}%"></div>
        </div>
        <p style="text-align: center; margin-top: 10px;">
            <strong>{stats['success_rate']:.1f}%</strong> ({stats['success_count']}/{stats['total_files']} 파일)
        </p>

        <h2>성공 유형별 분석</h2>
        <table>
            <thead>
                <tr>
                    <th>성공 유형</th>
                    <th>파일 수</th>
                    <th>성공 중 비율</th>
                </tr>
            </thead>
            <tbody>
                {success_type_rows}
            </tbody>
        </table>

        <h2>원본 상태별 통계 (참고용)</h2>
        <table>
            <thead>
                <tr>
                    <th>원본 상태</th>
                    <th>파일 수</th>
                    <th>비율</th>
                </tr>
            </thead>
            <tbody>
                {status_rows}
            </tbody>
        </table>

        <h2>주요 매퍼 타입별 통계</h2>
        <table>
            <thead>
                <tr>
                    <th>매퍼 타입</th>
                    <th>파일 수</th>
                </tr>
            </thead>
            <tbody>
                {mapper_rows}
            </tbody>
        </table>

        <h2>SQL Example</h2>
        <p>다음은 Function 검증이 성공한 SQL 샘플들입니다:</p>
        
        <div class="principle-note">
            <strong>Function 검증 원칙:</strong> SQL Function 변환의 문법 검증(DBMS 실행여부)<br><br>
            <strong>세부 변환 기준:</strong>
            <ul>
                <li>SQL Function 및 구문 유지</li>
                <li>Literal 유지</li>
                <li>Column은 1로 대체</li>
                <li>조회 조건 무시</li>
            </ul>
        </div>
        
        {sql_samples_html}

        <h2>MySQL Function 사용 통계</h2>
        <p>검증된 SQL에서 사용된 MySQL 함수들의 빈도수와 Oracle 호환성 분석:</p>
        <table>
            <thead>
                <tr>
                    <th>Function</th>
                    <th>Description</th>
                    <th>빈도수</th>
                    <th>Oracle 기능 동일성 여부</th>
                </tr>
            </thead>
            <tbody>
                {function_stats_rows}
            </tbody>
        </table>

        <h2>실행 시간 정보</h2>
        <div class="stats-grid">
            <div class="stat-card info-card">
                <h3>시작 시간</h3>
                <div style="font-size: 1.2em; margin-top: 10px;">{format_timestamp(stats['timestamp_range']['earliest'])}</div>
            </div>
            <div class="stat-card info-card">
                <h3>종료 시간</h3>
                <div style="font-size: 1.2em; margin-top: 10px;">{format_timestamp(stats['timestamp_range']['latest'])}</div>
            </div>
        </div>

        <div style="margin-top: 40px; text-align: center; color: #7f8c8d;">
            <p>보고서 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def main():
    """메인 함수"""
    json_file = 'sqlTestResult.json'
    output_file = 'function_test_report.html'
    
    print("=" * 60)
    print("Function 문법 테스트 결과 보고서 생성기")
    print("=" * 60)
    
    if not os.path.exists(json_file):
        print(f"❌ Error: {json_file} 파일을 찾을 수 없습니다.")
        print(f"현재 디렉토리: {os.getcwd()}")
        return
    
    try:
        print(f"📁 JSON 데이터를 로드하는 중... ({json_file})")
        data = load_json_data(json_file)
        print(f"✅ {len(data)}개의 테스트 결과를 로드했습니다.")
        
        print("📊 데이터를 분석하는 중...")
        stats = analyze_data(data)
        
        print("🎨 HTML 보고서를 생성하는 중...")
        html_content = generate_html_report(stats, data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("=" * 60)
        print("✅ Function 문법 테스트 결과 보고서 생성 완료!")
        print("=" * 60)
        print(f"📄 출력 파일: {output_file}")
        print(f"📈 총 파일 수: {stats['total_files']:,}개")
        print(f"🎯 성공한 파일: {stats['success_count']:,}개")
        print(f"📊 성공률: {stats['success_rate']:.1f}%")
        print(f"🔧 발견된 MySQL 함수: {len(stats['function_usage'])}종류")
        print(f"📝 SQL 샘플: {len(stats['sql_samples'])}개")
        print("=" * 60)
        print("성공 유형별 분석:")
        for success_type, count in stats['success_types'].items():
            print(f"  - {success_type}: {count:,}개")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
