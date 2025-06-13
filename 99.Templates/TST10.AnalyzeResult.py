#!/usr/bin/env python3
#############################################################################
# Script: DB10.AnalyzeResult.py
# Description: This script analyzes differences between Oracle and PostgreSQL
#              query results from the sqllist table.
#
# Functionality:
# - Identifies SQL statements where Oracle and PostgreSQL results differ (same='N')
# - Analyzes the differences and categorizes them by type
# - Generates a detailed report of the differences
# - Provides recommendations for resolving compatibility issues
#
# Usage:
#   python3 DB10.AnalyzeResult.py [options]
#
# Options:
#   -t, --type TYPE     Filter by SQL statement type (S: Select, I: Insert, etc.)
#   -a, --app APP       Filter by application name
#   -l, --limit N       Limit the number of results to analyze (default: 100)
#   -o, --output FILE   Output file for the report (default: difference_analysis.html)
#############################################################################

"""
Oracle과 PostgreSQL 쿼리 결과 차이를 분석하는 프로그램

이 프로그램은 sqllist 테이블에서 same='N'인 레코드를 찾아
Oracle과 PostgreSQL 결과의 차이를 분석하고 보고서를 생성합니다.

사용법:
    python3 DB10.AnalyzeResult.py [옵션]

옵션:
    -t, --type TYPE     SQL 문 타입으로 필터링 (S: Select, I: Insert 등)
    -a, --app APP       애플리케이션 이름으로 필터링
    -l, --limit N       분석할 결과 수 제한 (기본값: 100)
    -o, --output FILE   보고서 출력 파일 (기본값: difference_analysis.html)
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
import difflib
import re
import json
from datetime import datetime
import html
from collections import Counter

# SQL 문 타입 매핑
STMT_TYPES = {
    'S': 'Select',
    'I': 'Insert',
    'U': 'Update',
    'D': 'Delete',
    'P': 'PL/SQL Block',
    'O': 'Other'
}

# 차이 유형 정의
DIFFERENCE_TYPES = {
    'data_type': '데이터 타입 차이',
    'date_format': '날짜 형식 차이',
    'null_handling': 'NULL 처리 차이',
    'case_sensitivity': '대소문자 구분 차이',
    'whitespace': '공백 차이',
    'order': '결과 순서 차이',
    'function': '함수 동작 차이',
    'syntax': '구문 차이',
    'error': '오류 발생',
    'other': '기타 차이'
}

def get_db_connection():
    """
    PostgreSQL 데이터베이스 연결을 생성합니다.
    환경 변수에서 연결 정보를 가져옵니다.
    """
    try:
        # 환경 변수에서 연결 정보 가져오기
        pg_user = os.environ.get('PGUSER')
        pg_password = os.environ.get('PGPASSWORD')
        pg_host = os.environ.get('PGHOST')
        pg_port = os.environ.get('PGPORT')
        pg_database = os.environ.get('PGDATABASE')
        
        # 연결 정보 확인
        if not all([pg_host, pg_port, pg_database, pg_user, pg_password]):
            print("오류: PostgreSQL 연결 정보가 환경 변수에 설정되어 있지 않습니다.")
            print(f"PGHOST: {pg_host}, PGPORT: {pg_port}, PGDATABASE: {pg_database}, PGUSER: {pg_user}")
            sys.exit(1)
        
        # 데이터베이스 연결
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=pg_database,
            user=pg_user,
            password=pg_password
        )
        
        return conn
    except Exception as e:
        print(f"데이터베이스 연결 오류: {e}")
        sys.exit(1)

def fetch_different_results(conn, stmt_type=None, app_name=None, limit=100):
    """
    Oracle과 PostgreSQL 결과가 다른 SQL 문을 조회합니다.
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT sql_id, app_name, stmt_type, orcl_file_path, pg_file_path, 
                       orcl, pg, orcl_result, pg_result
                FROM sqllist
                WHERE same = 'N'
                AND orcl_result IS NOT NULL
                AND pg_result IS NOT NULL
            """
            
            params = []
            
            # 타입 필터링
            if stmt_type:
                query += " AND stmt_type = %s"
                params.append(stmt_type)
            
            # 애플리케이션 필터링
            if app_name:
                query += " AND app_name = %s"
                params.append(app_name)
            
            query += " ORDER BY sql_id, app_name LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            return rows
    except Exception as e:
        print(f"데이터 조회 중 오류 발생: {e}")
        return []

def analyze_difference(orcl_result, pg_result):
    """
    Oracle과 PostgreSQL 결과의 차이를 분석합니다.
    """
    # 결과가 오류인 경우 확인
    if orcl_result.startswith('ORA-') or pg_result.startswith('ERROR:'):
        return {
            'type': 'error',
            'description': '한쪽 또는 양쪽에서 오류 발생',
            'oracle_error': orcl_result if orcl_result.startswith('ORA-') else None,
            'postgres_error': pg_result if pg_result.startswith('ERROR:') else None
        }
    
    # 결과를 줄 단위로 분리
    orcl_lines = orcl_result.strip().split('\n')
    pg_lines = pg_result.strip().split('\n')
    
    # 줄 수 차이 확인
    if len(orcl_lines) != len(pg_lines):
        return {
            'type': 'other',
            'description': '결과 행 수 차이',
            'oracle_count': len(orcl_lines),
            'postgres_count': len(pg_lines)
        }
    
    # 날짜 형식 차이 확인
    date_pattern = r'\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?'
    if (re.search(date_pattern, orcl_result) or re.search(date_pattern, pg_result)):
        if re.search(date_pattern, orcl_result) != re.search(date_pattern, pg_result):
            return {
                'type': 'date_format',
                'description': '날짜 형식 차이',
                'oracle_sample': re.search(date_pattern, orcl_result).group(0) if re.search(date_pattern, orcl_result) else None,
                'postgres_sample': re.search(date_pattern, pg_result).group(0) if re.search(date_pattern, pg_result) else None
            }
    
    # NULL 처리 차이 확인
    if ('NULL' in orcl_result or 'NULL' in pg_result):
        if orcl_result.count('NULL') != pg_result.count('NULL'):
            return {
                'type': 'null_handling',
                'description': 'NULL 처리 차이',
                'oracle_null_count': orcl_result.count('NULL'),
                'postgres_null_count': pg_result.count('NULL')
            }
    
    # 대소문자 구분 차이 확인
    if orcl_result.lower() == pg_result.lower() and orcl_result != pg_result:
        return {
            'type': 'case_sensitivity',
            'description': '대소문자 구분 차이',
            'diff': get_diff_html(orcl_result, pg_result)
        }
    
    # 공백 차이 확인
    orcl_no_space = re.sub(r'\s+', '', orcl_result)
    pg_no_space = re.sub(r'\s+', '', pg_result)
    if orcl_no_space == pg_no_space and orcl_result != pg_result:
        return {
            'type': 'whitespace',
            'description': '공백 차이',
            'diff': get_diff_html(orcl_result, pg_result)
        }
    
    # 결과 순서 차이 확인
    if sorted(orcl_lines) == sorted(pg_lines) and orcl_lines != pg_lines:
        return {
            'type': 'order',
            'description': '결과 순서 차이',
            'diff': get_diff_html('\n'.join(orcl_lines), '\n'.join(pg_lines))
        }
    
    # 데이터 타입 차이 확인 (숫자 vs 문자열)
    orcl_has_quotes = bool(re.search(r'"[^"]*"', orcl_result))
    pg_has_quotes = bool(re.search(r'"[^"]*"', pg_result))
    if orcl_has_quotes != pg_has_quotes:
        return {
            'type': 'data_type',
            'description': '데이터 타입 차이 (숫자 vs 문자열)',
            'diff': get_diff_html(orcl_result, pg_result)
        }
    
    # 함수 동작 차이 (예: TO_CHAR, NVL 등)
    if any(func in orcl_result or func in pg_result for func in ['TO_CHAR', 'TO_DATE', 'NVL', 'COALESCE']):
        return {
            'type': 'function',
            'description': '함수 동작 차이',
            'diff': get_diff_html(orcl_result, pg_result)
        }
    
    # 기타 차이
    return {
        'type': 'other',
        'description': '기타 차이',
        'diff': get_diff_html(orcl_result, pg_result)
    }

def get_diff_html(text1, text2):
    """
    두 텍스트의 차이를 HTML 형식으로 반환합니다.
    """
    diff = difflib.HtmlDiff()
    return diff.make_table(
        text1.splitlines(),
        text2.splitlines(),
        'Oracle',
        'PostgreSQL',
        True
    )

def generate_html_report(results, output_file, args):
    """
    분석 결과를 HTML 보고서로 생성합니다.
    """
    # 차이 유형별 통계
    diff_types = Counter([r['analysis']['type'] for r in results])
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Oracle vs PostgreSQL 결과 차이 분석</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .sql-item {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
        .sql-header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 10px; }}
        .sql-code {{ background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; overflow-x: auto; font-family: monospace; }}
        .diff-type {{ font-weight: bold; color: #c00; }}
        .result-diff {{ margin-top: 10px; overflow-x: auto; }}
        table.diff {{ font-family: monospace; border-collapse: collapse; }}
        table.diff td {{ padding: 1px 5px; }}
        .diff_add {{ background-color: #aaffaa; }}
        .diff_chg {{ background-color: #ffff77; }}
        .diff_sub {{ background-color: #ffaaaa; }}
        .chart-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .chart {{ width: 600px; height: 300px; }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>Oracle vs PostgreSQL 결과 차이 분석</h1>
    
    <div class="summary">
        <h2>분석 요약</h2>
        <p>분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>총 분석 항목: {len(results)}개</p>
        
        <h3>필터 조건</h3>
        <ul>
            <li>SQL 타입: {STMT_TYPES.get(args.type, '모든 타입') if args.type else '모든 타입'}</li>
            <li>애플리케이션: {args.app if args.app else '모든 애플리케이션'}</li>
            <li>결과 제한: {args.limit}개</li>
        </ul>
        
        <h3>차이 유형별 통계</h3>
        <div class="chart-container">
            <canvas id="diffTypeChart" class="chart"></canvas>
        </div>
    </div>
    
    <h2>상세 분석 결과</h2>
"""
    
    # 각 SQL 항목에 대한 상세 분석 결과 추가
    for i, result in enumerate(results, 1):
        sql_id = result['sql_id']
        app_name = result['app_name']
        stmt_type = result['stmt_type']
        orcl_sql = result['orcl']
        pg_sql = result['pg']
        analysis = result['analysis']
        
        html_content += f"""
    <div class="sql-item">
        <div class="sql-header">
            <h3>#{i} SQL ID: {sql_id} (애플리케이션: {app_name}, 타입: {STMT_TYPES.get(stmt_type, stmt_type)})</h3>
            <p class="diff-type">차이 유형: {DIFFERENCE_TYPES.get(analysis['type'], analysis['type'])} - {analysis['description']}</p>
        </div>
        
        <h4>Oracle SQL</h4>
        <div class="sql-code">{html.escape(orcl_sql)}</div>
        
        <h4>PostgreSQL SQL</h4>
        <div class="sql-code">{html.escape(pg_sql)}</div>
        
        <h4>결과 차이</h4>
"""
        
        # 차이 유형에 따라 다른 정보 표시
        if analysis['type'] == 'error':
            html_content += f"""
        <p>Oracle 오류: {analysis.get('oracle_error', '없음')}</p>
        <p>PostgreSQL 오류: {analysis.get('postgres_error', '없음')}</p>
"""
        elif analysis['type'] in ['other', 'date_format', 'null_handling', 'data_type']:
            if 'diff' in analysis:
                html_content += f"""
        <div class="result-diff">{analysis['diff']}</div>
"""
            else:
                # 특정 정보 표시
                for key, value in analysis.items():
                    if key not in ['type', 'description']:
                        html_content += f"""
        <p>{key}: {value}</p>
"""
        else:
            # 기본적으로 diff 표시
            if 'diff' in analysis:
                html_content += f"""
        <div class="result-diff">{analysis['diff']}</div>
"""
        
        # 각 SQL 항목의 닫는 div 태그 추가
        html_content += """
    </div>
"""
    
    # 차트 스크립트 추가
    html_content += """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const ctx = document.getElementById('diffTypeChart').getContext('2d');
            const diffTypeChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: [
"""
    
    # 차트 라벨 추가
    for diff_type in diff_types:
        html_content += f"                        '{DIFFERENCE_TYPES.get(diff_type, diff_type)}',\n"
    
    html_content += """
                    ],
                    datasets: [{
                        label: '차이 유형별 개수',
                        data: [
"""
    
    # 차트 데이터 추가
    for diff_type in diff_types:
        html_content += f"                        {diff_types[diff_type]},\n"
    
    html_content += """
                        ],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.2)',
                            'rgba(54, 162, 235, 0.2)',
                            'rgba(255, 206, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)',
                            'rgba(153, 102, 255, 0.2)',
                            'rgba(255, 159, 64, 0.2)',
                            'rgba(199, 199, 199, 0.2)',
                            'rgba(83, 102, 255, 0.2)',
                            'rgba(40, 159, 64, 0.2)',
                            'rgba(210, 199, 199, 0.2)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)',
                            'rgba(255, 159, 64, 1)',
                            'rgba(199, 199, 199, 1)',
                            'rgba(83, 102, 255, 1)',
                            'rgba(40, 159, 64, 1)',
                            'rgba(210, 199, 199, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        });
    </script>
</body>
</html>
"""
    
    # HTML 파일 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML 보고서가 {output_file}에 생성되었습니다.")

def parse_arguments():
    """
    명령줄 인수를 파싱합니다.
    """
    parser = argparse.ArgumentParser(description='Oracle과 PostgreSQL 쿼리 결과 차이를 분석합니다.')
    parser.add_argument('-t', '--type', help='SQL 문 타입으로 필터링 (S: Select, I: Insert 등)')
    parser.add_argument('-a', '--app', help='애플리케이션 이름으로 필터링')
    parser.add_argument('-l', '--limit', type=int, default=100, help='분석할 결과 수 제한 (기본값: 100)')
    parser.add_argument('-o', '--output', default='difference_analysis.html', help='보고서 출력 파일 (기본값: difference_analysis.html)')
    return parser.parse_args()

def main():
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 데이터베이스 연결
    conn = get_db_connection()
    
    try:
        # 다른 결과를 가진 SQL 문 조회
        print(f"Oracle과 PostgreSQL 결과가 다른 SQL 문을 조회합니다...")
        rows = fetch_different_results(conn, args.type, args.app, args.limit)
        
        if not rows:
            print("조건에 맞는 SQL 문이 없습니다.")
            return
        
        print(f"총 {len(rows)}개의 SQL 문을 분석합니다.")
        
        # 결과 분석
        results = []
        for i, row in enumerate(rows, 1):
            print(f"[{i}/{len(rows)}] SQL ID: {row['sql_id']}, App: {row['app_name']} 분석 중...")
            
            # 결과 차이 분석
            analysis = analyze_difference(row['orcl_result'], row['pg_result'])
            
            # 분석 결과 저장
            results.append({
                'sql_id': row['sql_id'],
                'app_name': row['app_name'],
                'stmt_type': row['stmt_type'],
                'orcl': row['orcl'],
                'pg': row['pg'],
                'orcl_result': row['orcl_result'],
                'pg_result': row['pg_result'],
                'analysis': analysis
            })
        
        # HTML 보고서 생성
        generate_html_report(results, args.output, args)
        
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
