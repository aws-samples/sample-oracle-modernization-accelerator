#!/usr/bin/env python3
"""
Oracle Sequence Usage Extractor for MySQL Migration

Oracle의 SEQUENCE.NEXTVAL 사용처를 찾아서 테이블/컬럼을 식별하는 도구.
MySQL은 시퀀스가 없으므로 AUTO_INCREMENT로 변환해야 함.

사용법:
    python3 extract_sequence_usage.py <directory> [--output output.csv] [--workers 3]

예제:
    python3 extract_sequence_usage.py /path/to/mybatis/mappers --output sequences.csv
"""

import os
import sys
import re
import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Bedrock 클라이언트 (LLM 분석용) - lazy import
bedrock = None


def init_bedrock(region: str = "us-west-2"):
    """Bedrock 클라이언트 초기화"""
    global bedrock
    try:
        import boto3
        bedrock = boto3.client("bedrock-runtime", region_name=region)
    except ImportError:
        print("[ERROR] boto3가 설치되지 않았습니다. LLM 분석을 사용하려면 'pip install boto3'를 실행하세요.")
        sys.exit(1)


def scan_directory_for_nextval(directory: str) -> List[Dict]:
    """
    디렉토리를 재귀적으로 스캔하여 NEXTVAL 사용처를 찾음.

    Returns:
        List of dicts with keys: file_path, line_number, line_content, sequence_name
    """
    print(f"[SCAN] 디렉토리 스캔 시작: {directory}")

    findings = []
    # Oracle 패턴: SEQ_NAME.NEXTVAL
    oracle_pattern = re.compile(r'(\w+)\.NEXTVAL', re.IGNORECASE)
    # PostgreSQL 패턴: nextval('seq_name')
    pg_pattern = re.compile(r"nextval\s*\(\s*['\"](\w+)['\"]\s*\)", re.IGNORECASE)

    # 스캔할 파일 확장자
    target_extensions = {'.xml', '.sql', '.java', '.py', '.js', '.ts'}

    file_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in target_extensions:
                continue

            file_path = os.path.join(root, file)
            file_count += 1

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Oracle 패턴 검색
                        oracle_matches = oracle_pattern.findall(line)
                        for seq_name in oracle_matches:
                            findings.append({
                                'file_path': file_path,
                                'line_number': line_num,
                                'line_content': line.strip(),
                                'sequence_name': seq_name.upper(),
                                'pattern_type': 'oracle',
                            })

                        # PostgreSQL 패턴 검색
                        pg_matches = pg_pattern.findall(line)
                        for seq_name in pg_matches:
                            findings.append({
                                'file_path': file_path,
                                'line_number': line_num,
                                'line_content': line.strip(),
                                'sequence_name': seq_name.upper(),
                                'pattern_type': 'postgresql',
                            })
            except Exception as e:
                print(f"[WARN] 파일 읽기 실패 {file_path}: {e}")

    print(f"[SCAN] 완료: {file_count}개 파일 스캔, {len(findings)}개 NEXTVAL 발견")
    return findings


def get_file_context(file_path: str, line_number: int, context_lines: int = 50) -> str:
    """
    파일에서 특정 라인 주변의 컨텍스트를 추출.

    Args:
        file_path: 파일 경로
        line_number: 중심 라인 번호
        context_lines: 전후 라인 수 (기본 50줄 - INSERT/UPDATE 전체를 보기 위해)

    Returns:
        컨텍스트 문자열
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        context = ''.join(lines[start:end])
        return context
    except Exception as e:
        return f"[ERROR] 컨텍스트 추출 실패: {e}"


def parse_sql_static(context: str, sequence_name: str) -> Dict:
    """
    SQL을 정적으로 파싱하여 테이블/컬럼 추출 (LLM 없이).

    INSERT/UPDATE 문에서 시퀀스 사용 위치를 정확히 찾음.
    """
    result = {
        "table_name": None,
        "column_name": None,
        "operation": None,
        "confidence": "low",
        "reasoning": "정적 파싱 실패"
    }

    # 1. INSERT 문 파싱
    # INSERT INTO table (col1, col2, ...) VALUES (seq.nextval, ...)
    insert_pattern = re.compile(
        r'INSERT\s+INTO\s+(\w+)\s*\(([\s\S]*?)\)\s*VALUES\s*\(([\s\S]*?)\)',
        re.IGNORECASE
    )

    for match in insert_pattern.finditer(context):
        table = match.group(1)
        columns_str = match.group(2)
        values_str = match.group(3)

        # 컬럼 리스트 파싱
        columns = [c.strip() for c in re.split(r',', columns_str) if c.strip()]

        # VALUES에서 시퀀스 위치 찾기
        # nextval('seq_name') 또는 SEQ_NAME.NEXTVAL 패턴
        seq_patterns = [
            rf"nextval\s*\(\s*['\"]?{sequence_name}['\"]?\s*\)",
            rf"{sequence_name}\.NEXTVAL"
        ]

        for seq_pat in seq_patterns:
            if re.search(seq_pat, values_str, re.IGNORECASE):
                # VALUES를 토큰으로 분리 (괄호 안의 항목들)
                # 간단한 방법: , 로 split (함수 안의 쉼표도 split되지만 시퀀스는 첫 번째일 가능성 높음)
                value_tokens = []
                depth = 0
                current = []
                for char in values_str:
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        depth -= 1
                    elif char == ',' and depth == 0:
                        value_tokens.append(''.join(current).strip())
                        current = []
                        continue
                    current.append(char)
                if current:
                    value_tokens.append(''.join(current).strip())

                # 시퀀스가 몇 번째 값인지 찾기
                for idx, token in enumerate(value_tokens):
                    if re.search(seq_pat, token, re.IGNORECASE):
                        if idx < len(columns):
                            result = {
                                "table_name": table.upper(),
                                "column_name": columns[idx].strip().upper(),
                                "operation": "INSERT",
                                "confidence": "high",
                                "reasoning": f"INSERT 문 파싱: {table}.{columns[idx]} = {sequence_name}"
                            }
                            return result
                        break

    # 2. UPDATE 문 파싱
    # UPDATE table SET col = seq.nextval WHERE ...
    update_pattern = re.compile(
        r'UPDATE\s+(\w+)(?:\s+\w+)?\s+SET\s+([\s\S]*?)(?:WHERE|$)',
        re.IGNORECASE
    )

    for match in update_pattern.finditer(context):
        table = match.group(1)
        set_clause = match.group(2)

        # SET 절에서 시퀀스 사용 찾기
        seq_patterns = [
            rf"(\w+)\s*=\s*nextval\s*\(\s*['\"]?{sequence_name}['\"]?\s*\)",
            rf"(\w+)\s*=\s*{sequence_name}\.NEXTVAL"
        ]

        for seq_pat in seq_patterns:
            col_match = re.search(seq_pat, set_clause, re.IGNORECASE)
            if col_match:
                column = col_match.group(1)
                result = {
                    "table_name": table.upper(),
                    "column_name": column.strip().upper(),
                    "operation": "UPDATE",
                    "confidence": "high",
                    "reasoning": f"UPDATE 문 파싱: {table}.{column} = {sequence_name}"
                }
                return result

    # 3. 정적 파싱 실패 - 패턴 추론
    # 테이블명이 시퀀스명에 포함되어 있으면 추론
    table_match = re.search(r'(?:INSERT\s+INTO|UPDATE)\s+(\w+)', context, re.IGNORECASE)
    if table_match:
        table = table_match.group(1)
        result = {
            "table_name": table.upper(),
            "column_name": None,
            "operation": None,
            "confidence": "medium",
            "reasoning": f"테이블 {table} 발견, 컬럼 파싱 실패"
        }

    return result


def analyze_with_llm(file_path: str, sequence_name: str, context: str, model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0") -> Dict:
    """
    LLM을 사용하여 시퀀스 사용 컨텍스트를 분석.

    Returns:
        Dict with keys: table_name, column_name, query_id, operation, confidence
    """
    prompt = f"""다음 코드에서 Oracle 시퀀스 `{sequence_name}.NEXTVAL`이 사용되고 있습니다.
이 시퀀스가 어느 테이블의 어느 컬럼에 INSERT되는지 분석해주세요.

파일: {file_path}

코드:
```
{context}
```

다음 JSON 형식으로만 답변해주세요 (다른 설명 없이 JSON만):
{{
  "table_name": "테이블명 (대문자)",
  "column_name": "컬럼명 (대문자)",
  "query_id": "MyBatis XML의 경우 쿼리 ID, 아니면 null",
  "operation": "INSERT 또는 UPDATE",
  "confidence": "high, medium, low 중 하나",
  "reasoning": "판단 근거 (짧게)"
}}

분석이 불가능하면:
{{
  "table_name": null,
  "column_name": null,
  "query_id": null,
  "operation": null,
  "confidence": "low",
  "reasoning": "분석 불가 사유"
}}
"""

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )

        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']

        # JSON 추출 (코드 블록 안에 있을 수 있음)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            return {
                "table_name": None,
                "column_name": None,
                "query_id": None,
                "operation": None,
                "confidence": "low",
                "reasoning": "JSON 파싱 실패"
            }

    except Exception as e:
        print(f"[ERROR] LLM 분석 실패: {e}")
        return {
            "table_name": None,
            "column_name": None,
            "query_id": None,
            "operation": None,
            "confidence": "low",
            "reasoning": f"LLM 호출 에러: {str(e)}"
        }


def process_finding(finding: Dict, context_lines: int = 50) -> Dict:
    """
    단일 발견 항목을 처리하여 테이블/컬럼 정보 추출.

    1차: 정적 SQL 파싱으로 정확히 추출
    2차: 실패 시 LLM 분석
    """
    file_path = finding['file_path']
    line_number = finding['line_number']
    sequence_name = finding['sequence_name']

    print(f"[ANALYZE] {file_path}:{line_number} - {sequence_name}")

    # 컨텍스트 추출
    context = get_file_context(file_path, line_number, context_lines)

    # 1차: 정적 파싱
    static_result = parse_sql_static(context, sequence_name)

    # 정적 파싱 성공 시 LLM 생략
    if static_result['confidence'] == 'high':
        result = {
            **finding,
            **static_result,
            'analyzed_at': datetime.now().isoformat(),
            'method': 'static_parse'
        }
        return result

    # 2차: LLM 분석 (정적 파싱 실패 시)
    llm_result = analyze_with_llm(file_path, sequence_name, context)

    # 결과 병합 (LLM 결과 우선)
    result = {
        **finding,
        **llm_result,
        'analyzed_at': datetime.now().isoformat(),
        'method': 'llm'
    }

    return result


def save_results(results: List[Dict], output_file: str, format: str = 'csv'):
    """
    분석 결과를 파일로 저장.

    Args:
        results: 분석 결과 리스트
        output_file: 출력 파일 경로
        format: 'csv' 또는 'json'
    """
    if format == 'csv':
        fieldnames = [
            'file_path', 'line_number', 'sequence_name', 'pattern_type',
            'table_name', 'column_name', 'query_id', 'operation',
            'confidence', 'reasoning', 'analyzed_at'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in results:
                # line_content 제외 (너무 길어서)
                row = {k: result.get(k, '') for k in fieldnames}
                writer.writerow(row)

        print(f"[SAVE] CSV 저장 완료: {output_file}")

    elif format == 'json':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"[SAVE] JSON 저장 완료: {output_file}")


def print_summary(results: List[Dict]):
    """분석 결과 요약 출력"""
    print("\n" + "=" * 70)
    print("분석 결과 요약")
    print("=" * 70)

    total = len(results)
    high_conf = sum(1 for r in results if r.get('confidence') == 'high')
    medium_conf = sum(1 for r in results if r.get('confidence') == 'medium')
    low_conf = sum(1 for r in results if r.get('confidence') == 'low')

    print(f"총 발견: {total}개")
    print(f"  - High Confidence: {high_conf}개")
    print(f"  - Medium Confidence: {medium_conf}개")
    print(f"  - Low Confidence: {low_conf}개")
    print()

    # 시퀀스별 집계
    seq_usage = {}
    for r in results:
        seq_name = r['sequence_name']
        if seq_name not in seq_usage:
            seq_usage[seq_name] = []

        table = r.get('table_name')
        column = r.get('column_name')
        if table and column:
            seq_usage[seq_name].append(f"{table}.{column}")

    print("시퀀스별 사용처:")
    for seq_name, usages in sorted(seq_usage.items()):
        unique_usages = list(set(usages))
        print(f"  {seq_name}:")
        for usage in unique_usages:
            print(f"    → {usage}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Oracle 시퀀스 사용처를 찾아서 테이블/컬럼을 추출',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 기본 사용
  python3 extract_sequence_usage.py /path/to/mappers

  # CSV 출력 지정
  python3 extract_sequence_usage.py /path/to/mappers --output sequences.csv

  # JSON 형식 + 병렬 처리
  python3 extract_sequence_usage.py /path/to/mappers --output sequences.json --format json --workers 5

  # Bedrock 리전 지정
  python3 extract_sequence_usage.py /path/to/mappers --region us-east-1
        """
    )

    parser.add_argument('directory', help='스캔할 디렉토리 경로')
    parser.add_argument('--output', '-o', default='sequence_usage.csv',
                        help='출력 파일 경로 (기본: sequence_usage.csv)')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='csv',
                        help='출력 형식 (기본: csv)')
    parser.add_argument('--workers', '-w', type=int, default=3,
                        help='병렬 처리 워커 수 (기본: 3)')
    parser.add_argument('--context-lines', '-c', type=int, default=10,
                        help='LLM에게 보낼 컨텍스트 라인 수 (기본: 10)')
    parser.add_argument('--region', '-r', default='us-west-2',
                        help='Bedrock 리전 (기본: us-west-2)')
    parser.add_argument('--no-llm', action='store_true',
                        help='LLM 분석 생략 (NEXTVAL 위치만 수집)')

    args = parser.parse_args()

    # 디렉토리 존재 확인
    if not os.path.isdir(args.directory):
        print(f"[ERROR] 디렉토리가 존재하지 않습니다: {args.directory}")
        sys.exit(1)

    print("=" * 70)
    print("Oracle Sequence Usage Extractor")
    print("=" * 70)
    print(f"디렉토리: {args.directory}")
    print(f"출력 파일: {args.output}")
    print(f"출력 형식: {args.format}")
    print(f"워커 수: {args.workers}")
    print(f"LLM 분석: {'비활성화' if args.no_llm else '활성화'}")
    print("=" * 70)
    print()

    # 1단계: NEXTVAL 스캔
    findings = scan_directory_for_nextval(args.directory)

    if not findings:
        print("[INFO] NEXTVAL 사용처를 찾지 못했습니다.")
        return

    # 2단계: LLM 분석 (옵션)
    if args.no_llm:
        results = findings
        print(f"[INFO] LLM 분석 생략, {len(results)}개 발견 항목만 저장")
    else:
        # Bedrock 초기화
        init_bedrock(args.region)

        print(f"\n[ANALYZE] LLM 분석 시작 ({args.workers}개 워커)")
        results = []

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(process_finding, finding, args.context_lines): finding
                for finding in findings
            }

            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                results.append(result)

                # 진행 상황 표시
                if i % 5 == 0 or i == len(findings):
                    print(f"  진행: {i}/{len(findings)} ({i/len(findings)*100:.1f}%)")

    # 3단계: 결과 저장
    save_results(results, args.output, args.format)

    # 4단계: 요약 출력
    if not args.no_llm:
        print_summary(results)

    print("\n완료!")


if __name__ == '__main__':
    main()
