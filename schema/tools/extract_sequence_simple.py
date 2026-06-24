#!/usr/bin/env python3
"""
Oracle Sequence Usage Extractor - Simple Version

1. nextval이 사용된 파일 목록만 추출
2. 파일 전체를 LLM에게 주고 테이블/컬럼 매핑 추출
3. 결과를 두괄식으로 출력

사용법:
    python3 extract_sequence_simple.py <directory> [--output output.txt] [--region ap-northeast-2]
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

bedrock = None


def init_bedrock(region: str):
    """Bedrock 클라이언트 초기화"""
    global bedrock
    try:
        import boto3
        bedrock = boto3.client("bedrock-runtime", region_name=region)
    except ImportError:
        print("[ERROR] boto3가 설치되지 않았습니다. 'pip install boto3'를 실행하세요.")
        sys.exit(1)


def scan_files_with_nextval(directory: str) -> List[str]:
    """
    nextval이 포함된 파일 목록 추출.

    Returns:
        파일 경로 리스트
    """
    print(f"[SCAN] 디렉토리 스캔: {directory}")

    target_extensions = {'.xml', '.sql', '.java'}
    files_with_nextval = []

    # Oracle 패턴: SEQ_NAME.NEXTVAL
    # PostgreSQL 패턴: nextval('seq_name')
    nextval_pattern = re.compile(r'nextval|NEXTVAL', re.IGNORECASE)

    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in target_extensions:
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if nextval_pattern.search(content):
                        files_with_nextval.append(file_path)
            except Exception as e:
                print(f"[WARN] 파일 읽기 실패 {file_path}: {e}")

    print(f"[SCAN] 완료: {len(files_with_nextval)}개 파일에서 NEXTVAL 발견")
    return files_with_nextval


def analyze_file_with_llm(file_path: str, model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0") -> Dict:
    """
    파일 전체를 LLM에게 주고 시퀀스 사용처 분석.

    Returns:
        {
            "file_path": str,
            "mappings": [
                {"table": "TABLE_NAME", "column": "COLUMN_NAME", "sequence": "SEQ_NAME"},
                ...
            ]
        }
    """
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 파일이 너무 크면 자르기 (Bedrock 제한)
        max_chars = 100000  # ~25K tokens
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n... (파일이 잘림)"

        prompt = f"""다음 파일에서 Oracle 시퀀스(NEXTVAL)가 사용되는 모든 위치를 찾아서 테이블명과 컬럼명을 추출해주세요.

파일: {os.path.basename(file_path)}

내용:
```
{content}
```

다음 JSON 형식으로만 답변해주세요 (다른 설명 없이):
{{
  "mappings": [
    {{
      "table": "테이블명 (대문자)",
      "column": "컬럼명 (대문자)",
      "sequence": "시퀀스명 (대문자)",
      "operation": "INSERT 또는 UPDATE"
    }}
  ]
}}

분석 규칙:
- INSERT INTO table (col1, col2) VALUES (seq.nextval, ...) → col1이 시퀀스 사용
- UPDATE table SET col = seq.nextval → col이 시퀀스 사용
- nextval('seq_name') 또는 SEQ_NAME.NEXTVAL 패턴 모두 찾기
- 찾을 수 없으면 빈 배열 반환

JSON만 출력하세요:"""

        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
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

        # JSON 추출
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "file_path": file_path,
                "mappings": result.get("mappings", [])
            }
        else:
            return {
                "file_path": file_path,
                "mappings": [],
                "error": "JSON 파싱 실패"
            }

    except Exception as e:
        return {
            "file_path": file_path,
            "mappings": [],
            "error": str(e)
        }


def format_output(results: List[Dict], output_file: str):
    """
    결과를 두괄식으로 정리하여 파일에 저장.

    형식:
    # 시퀀스 사용 매핑
    TABLE_NAME.COLUMN_NAME = SEQUENCE_NAME (INSERT)
    ...

    ## 상세
    파일: ...
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Oracle Sequence 사용 매핑 분석 결과\n")
        f.write("=" * 80 + "\n\n")

        # 1. 매핑 요약 (두괄식)
        f.write("## 시퀀스 매핑\n\n")

        all_mappings = []
        for result in results:
            for mapping in result.get("mappings", []):
                if mapping.get("table") and mapping.get("column") and mapping.get("sequence"):
                    all_mappings.append(mapping)

        if all_mappings:
            # 시퀀스별로 그룹화
            by_sequence = {}
            for m in all_mappings:
                seq = m["sequence"]
                if seq not in by_sequence:
                    by_sequence[seq] = []
                by_sequence[seq].append(m)

            for seq, mappings in sorted(by_sequence.items()):
                f.write(f"\n### {seq}\n")
                for m in mappings:
                    f.write(f"  {m['table']}.{m['column']} ({m.get('operation', 'UNKNOWN')})\n")
        else:
            f.write("(매핑 없음)\n")

        # 2. 파일별 상세
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("## 파일별 상세\n")
        f.write("=" * 80 + "\n\n")

        for result in results:
            file_path = result["file_path"]
            mappings = result.get("mappings", [])
            error = result.get("error")

            f.write(f"\n### {os.path.basename(file_path)}\n")
            f.write(f"경로: {file_path}\n\n")

            if error:
                f.write(f"⚠️ 에러: {error}\n")
            elif mappings:
                for m in mappings:
                    f.write(f"- {m.get('table', '?')}.{m.get('column', '?')} = {m.get('sequence', '?')} ({m.get('operation', '?')})\n")
            else:
                f.write("(매핑 발견 안됨)\n")

    print(f"\n[SAVE] 결과 저장: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Oracle 시퀀스 사용처 추출 - Simple Version',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('directory', help='스캔할 디렉토리 경로')
    parser.add_argument('--output', '-o', default='sequence_mapping.txt',
                        help='출력 파일 (기본: sequence_mapping.txt)')
    parser.add_argument('--workers', '-w', type=int, default=3,
                        help='병렬 처리 워커 수 (기본: 3)')
    parser.add_argument('--region', '-r', default='ap-northeast-2',
                        help='Bedrock 리전 (기본: ap-northeast-2)')

    args = parser.parse_args()

    # 디렉토리 확인
    if not os.path.isdir(args.directory):
        print(f"[ERROR] 디렉토리가 존재하지 않습니다: {args.directory}")
        sys.exit(1)

    print("=" * 80)
    print("Oracle Sequence Usage Extractor - Simple Version")
    print("=" * 80)
    print(f"디렉토리: {args.directory}")
    print(f"출력 파일: {args.output}")
    print(f"워커 수: {args.workers}")
    print("=" * 80)
    print()

    # 1단계: nextval 파일 스캔
    files = scan_files_with_nextval(args.directory)

    if not files:
        print("[INFO] NEXTVAL 사용 파일을 찾지 못했습니다.")
        return

    # 2단계: Bedrock 초기화
    init_bedrock(args.region)

    # 3단계: LLM 분석 (병렬)
    print(f"\n[ANALYZE] LLM 분석 시작 ({args.workers}개 워커)")
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(analyze_file_with_llm, file_path): file_path
            for file_path in files
        }

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)

            file_name = os.path.basename(result["file_path"])
            mapping_count = len(result.get("mappings", []))
            print(f"  [{i}/{len(files)}] {file_name}: {mapping_count}개 매핑")

    # 4단계: 결과 저장
    format_output(results, args.output)

    # 5단계: 요약 출력
    total_mappings = sum(len(r.get("mappings", [])) for r in results)
    print(f"\n완료! 총 {total_mappings}개 매핑 발견")
    print(f"결과 파일: {args.output}")


if __name__ == '__main__':
    main()
