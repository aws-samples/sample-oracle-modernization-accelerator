#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PostgreSQL 에러 자동 수정 도구
analyze_pg_errors.py에서 분석된 에러 유형별로 SQL 파일을 자동 수정합니다.

사용법:
  python3 pg_transform.py --type=05                # 05번 에러 유형 수정
  python3 pg_transform.py --type=06 --limit=10     # 06번 에러 유형 중 10개만 수정
  python3 pg_transform.py --type=05 --dry-run      # 실제 수정 없이 시뮬레이션만
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
import re
from datetime import datetime
from pathlib import Path

class PGTransformer:
    def __init__(self, error_type, limit=None, dry_run=False):
        self.error_type = error_type
        self.limit = limit
        self.dry_run = dry_run
        self.temp_dir = "/tmp"
        self.processed_files = []
        self.success_count = 0
        self.error_count = 0
        
        # 에러 유형 매핑
        self.error_type_mapping = {
            '01': 'Relation Not Found',
            '02': 'Schema Not Found', 
            '03': 'Function Not Found',
            '04': 'Operator Not Found',
            '05': 'Subquery Alias Missing',
            '06': 'Syntax Error',
            '07': 'Cross-Database Reference',
            '08': 'Type Mismatch (COALESCE)',
            '09': 'Invalid Input Syntax',
            '10': 'Invalid FROM Reference',
            '11': 'Recursive Query Type Mismatch',
            '12': 'Column Not Found',
            '13': 'Missing FROM Clause',
            '14': 'Procedure Not Found',
            '15': 'GROUP BY Clause Error',
            '16': 'Date Format Error',
            '99': 'Other Errors'
        }
    def get_sql_files_for_error_type(self):
        """지정된 에러 유형에 해당하는 SQL 파일 목록을 가져옵니다."""
        print(f"🔍 에러 유형 {self.error_type} ({self.error_type_mapping.get(self.error_type, 'Unknown')}) 파일 검색 중...")
        
        # analyze_pg_errors.py 실행하여 최신 분석 결과 생성
        try:
            result = subprocess.run(['python3', './analyze_pg_errors.py'], 
                                  capture_output=True, text=True, check=True)
            print("✅ 에러 분석 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ 에러 분석 실패: {e}")
            return []
        
        # 최신 분석 결과 파일 찾기
        analysis_files = []
        for file in os.listdir(self.temp_dir):
            if file.startswith('pg_error_analysis_') and file.endswith('.json'):
                file_path = os.path.join(self.temp_dir, file)
                analysis_files.append((file_path, os.path.getmtime(file_path)))
        
        if not analysis_files:
            print("❌ 분석 결과 파일을 찾을 수 없습니다.")
            return []
        
        # 가장 최신 파일 선택
        latest_file = max(analysis_files, key=lambda x: x[1])[0]
        print(f"📄 분석 결과 파일: {latest_file}")
        
        # JSON 파일 읽기
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
        except Exception as e:
            print(f"❌ 분석 결과 파일 읽기 실패: {e}")
            return []
        
        # 지정된 에러 유형의 파일 목록 추출
        sql_files = []
        error_categories = analysis_data.get('error_categories', {})
        
        for category, cat_data in error_categories.items():
            if cat_data.get('error_number') == self.error_type:
                files = cat_data.get('files', [])
                sql_files.extend(files)
                print(f"✅ {category}: {len(files)}개 파일 발견")
                break
        
        if not sql_files:
            print(f"❌ 에러 유형 {self.error_type}에 해당하는 파일이 없습니다.")
            return []
        
        # 중복 제거 및 정렬
        sql_files = sorted(list(set(sql_files)))
        
        # limit 적용
        if self.limit and len(sql_files) > self.limit:
            sql_files = sql_files[:self.limit]
            print(f"📊 처리 제한: {self.limit}개 파일만 선택")
        
        print(f"📋 총 {len(sql_files)}개 파일을 처리합니다.")
        return sql_files
    def extract_source_xml_path(self, sql_file_path):
        """SQL 파일에서 원본 XML 파일 경로를 추출합니다."""
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # -- Source XML: 패턴 찾기
            xml_match = re.search(r'--\s*Source\s+XML:\s*(.+)', content, re.IGNORECASE)
            if xml_match:
                xml_path = xml_match.group(1).strip()
                return xml_path
            
            return None
        except Exception as e:
            print(f"❌ XML 경로 추출 실패 ({sql_file_path}): {e}")
            return None
    
    def run_psql_and_capture_error(self, sql_file_path):
        """psql을 실행하여 에러를 캡처합니다."""
        try:
            # psql 실행
            result = subprocess.run(['psql', '-f', sql_file_path], 
                                  capture_output=True, text=True)
            
            # 에러 출력 반환 (stdout과 stderr 모두)
            error_output = result.stdout + result.stderr
            return error_output
        except Exception as e:
            return f"psql 실행 오류: {e}"
    
    def create_sql_fix_prompt(self, sql_file_path, error_output):
        """SQL 파일 수정을 위한 프롬프트를 생성합니다."""
        prompt_file = os.path.join(self.temp_dir, f"{os.path.basename(sql_file_path)}.prompt")
        
        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write("=== PostgreSQL 에러 발생 ===\n")
                f.write(f"파일: {sql_file_path}\n\n")
                f.write("에러 내용:\n")
                f.write(error_output)
                f.write("\n\n")
                f.write("이 SQL 파일을 PostgreSQL에서 동작하도록 수정해주세요.\n\n")
                f.write("중요한 주의사항:\n")
                f.write("1. 기존 SQL 구조를 최대한 유지해주세요\n")
                f.write("2. 바인드 변수나 하드코딩된 값은 변경하지 마세요\n")
                f.write("3. 테이블 조인 방식을 변경하지 마세요\n")
                f.write("4. 서브쿼리 별칭 누락 에러의 경우, 서브쿼리 끝에 'AS subquery' 또는 적절한 별칭만 추가해주세요\n")
                f.write("5. 다른 부분은 수정하지 말고 에러 해결에 필요한 최소한의 변경만 해주세요\n\n")
                f.write("에러의 원인과 수정 방법을 설명해주세요.\n")
            
            return prompt_file
        except Exception as e:
            print(f"❌ 프롬프트 파일 생성 실패: {e}")
            return None
    def run_q_chat_for_sql_fix(self, prompt_file, sql_file_path):
        """Q Chat을 실행하여 SQL 파일 수정 방법을 얻습니다."""
        fix_prompt_file = os.path.join(self.temp_dir, f"{os.path.basename(sql_file_path)}.fix.prompt")
        
        try:
            # q chat 실행
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            
            if self.dry_run:
                print(f"🔄 [DRY-RUN] Q Chat 실행 시뮬레이션: {sql_file_path}")
                # 시뮬레이션용 더미 응답
                fix_content = f"""
에러 분석:
- 파일: {sql_file_path}
- 에러 유형: {self.error_type_mapping.get(self.error_type, 'Unknown')}

수정 방법:
1. [시뮬레이션] 에러 원인 분석
2. [시뮬레이션] 수정 방법 제안
3. [시뮬레이션] 코드 수정 예시

이것은 dry-run 모드의 시뮬레이션 결과입니다.
"""
            else:
                # 실제 q chat 실행 - trust-all-tools 옵션 추가
                print("🤖 Q Chat 실행 중... (응답을 기다리는 중)")
                
                # 임시 스크립트 파일 생성
                temp_script = os.path.join(self.temp_dir, f"qchat_script_{os.getpid()}.txt")
                with open(temp_script, 'w', encoding='utf-8') as f:
                    f.write(prompt_content)
                    f.write("\n/quit\n")  # 자동 종료
                
                # q chat을 stdin으로 실행 (trust-all-tools 옵션 추가)
                result = subprocess.run(['q', 'chat', '--trust-all-tools'], 
                                      stdin=open(temp_script, 'r', encoding='utf-8'),
                                      capture_output=True, text=True, encoding='utf-8')
                
                # 임시 파일 삭제
                os.remove(temp_script)
                
                fix_content = result.stdout
                
                if result.returncode != 0 or not fix_content.strip():
                    print(f"⚠️  Q Chat 응답이 비어있거나 오류 발생")
                    print(f"Return code: {result.returncode}")
                    print(f"Stderr: {result.stderr}")
                    fix_content = f"Q Chat 실행 오류 또는 응답 없음\nReturn code: {result.returncode}\nStderr: {result.stderr}\nStdout: {result.stdout}"
                else:
                    print(f"✅ Q Chat 응답 수신 완료 ({len(fix_content)} 문자)")
            
            # 수정 방법을 파일에 저장
            with open(fix_prompt_file, 'w', encoding='utf-8') as f:
                f.write(fix_content)
            
            print(f"💾 SQL 수정 방법 저장: {fix_prompt_file}")
            return fix_prompt_file
        except Exception as e:
            print(f"❌ Q Chat 실행 실패: {e}")
            return None
    def create_xml_fix_prompt(self, fix_prompt_file, xml_file_path):
        """XML 파일 수정을 위한 프롬프트를 생성합니다."""
        if not xml_file_path:
            return None
        
        xml_fix_prompt_file = os.path.join(self.temp_dir, f"{os.path.basename(xml_file_path)}.xml.fix.prompt")
        
        try:
            # 기존 SQL 수정 내용 읽기
            with open(fix_prompt_file, 'r', encoding='utf-8') as f:
                sql_fix_content = f.read()
            
            # XML 수정 프롬프트 생성
            with open(xml_fix_prompt_file, 'w', encoding='utf-8') as f:
                f.write("=== XML 파일 수정 요청 ===\n")
                f.write(f"수정할 파일: {xml_file_path}\n\n")
                f.write("SQL 수정 분석 결과:\n")
                f.write(sql_fix_content)
                f.write("\n\n")
                f.write("위 SQL 수정 내용을 바탕으로 원본 XML 파일을 수정해주세요.\n\n")
                f.write("중요한 주의사항:\n")
                f.write("1. CDATA 섹션은 그대로 유지해주세요\n")
                f.write("2. IF, CHOOSE, WHEN 등의 MyBatis 태그들은 그대로 유지해주세요\n")
                f.write("3. #{바인드변수_이름} 형식의 바인드 변수들은 그대로 유지해주세요\n")
                f.write("4. XML 구조와 태그들은 변경하지 말고, SQL 쿼리 부분만 수정해주세요\n")
                f.write("5. 네임스페이스와 XML 선언부는 그대로 유지해주세요\n")
            
            return xml_fix_prompt_file
        except Exception as e:
            print(f"❌ XML 수정 프롬프트 생성 실패: {e}")
            return None
    
    def run_q_chat_for_xml_fix(self, xml_fix_prompt_file, xml_file_path):
        """Q Chat을 실행하여 XML 파일을 수정합니다."""
        try:
            with open(xml_fix_prompt_file, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            
            if self.dry_run:
                print(f"🔄 [DRY-RUN] XML 수정 시뮬레이션: {xml_file_path}")
                return True
            else:
                # 실제 q chat 실행 - trust-all-tools 옵션 추가
                print("🤖 XML 수정을 위한 Q Chat 실행 중...")
                
                # 임시 스크립트 파일 생성
                temp_script = os.path.join(self.temp_dir, f"qchat_xml_script_{os.getpid()}.txt")
                with open(temp_script, 'w', encoding='utf-8') as f:
                    f.write(prompt_content)
                    f.write("\n/quit\n")  # 자동 종료
                
                # q chat을 stdin으로 실행 (trust-all-tools 옵션 추가)
                result = subprocess.run(['q', 'chat', '--trust-all-tools'], 
                                      stdin=open(temp_script, 'r', encoding='utf-8'),
                                      capture_output=True, text=True, encoding='utf-8')
                
                # 임시 파일 삭제
                os.remove(temp_script)
                
                # XML 수정 결과 저장
                xml_result_file = os.path.join(self.temp_dir, f"{os.path.basename(xml_file_path)}.xml.result")
                with open(xml_result_file, 'w', encoding='utf-8') as f:
                    f.write(f"Q Chat XML 수정 결과:\n")
                    f.write(f"Return code: {result.returncode}\n")
                    f.write(f"Stdout:\n{result.stdout}\n")
                    f.write(f"Stderr:\n{result.stderr}\n")
                
                if result.returncode == 0 and result.stdout.strip():
                    print(f"✅ XML 파일 수정 Q Chat 응답 완료: {xml_file_path}")
                    print(f"💾 XML 수정 결과 저장: {xml_result_file}")
                    return xml_result_file
                else:
                    print(f"⚠️  XML 파일 수정 Q Chat 응답 문제")
                    print(f"Return code: {result.returncode}")
                    print(f"💾 XML 수정 결과 저장: {xml_result_file}")
                    return xml_result_file  # 실패해도 결과 파일은 반환
        except Exception as e:
            print(f"❌ XML 수정 Q Chat 실행 실패: {e}")
            return None
    def check_file_modification(self, file_path, original_content):
        """파일이 수정되었는지 확인합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            return current_content != original_content
        except Exception as e:
            print(f"❌ 파일 수정 확인 실패: {e}")
            return False
    
    def apply_sql_fix(self, sql_file_path, fix_prompt_file):
        """Q Chat의 수정 제안을 바탕으로 실제 SQL 파일을 수정합니다."""
        try:
            # 원본 SQL 파일 읽기
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                original_sql = f.read()
            
            if self.dry_run:
                print(f"🔄 [DRY-RUN] SQL 파일 수정 시뮬레이션: {sql_file_path}")
                return True
            
            # Q Chat이 이미 파일을 수정했는지 확인
            # (Q Chat 실행 전후 파일 내용 비교는 이미 process_single_file에서 처리)
            
            # 수정 후 검증을 위해 psql 실행
            verification_result = self.run_psql_and_capture_error(sql_file_path)
            if "ERROR:" not in verification_result:
                print(f"✅ SQL 파일이 성공적으로 수정되었습니다: {sql_file_path}")
                return True
            else:
                print(f"⚠️  SQL 파일 수정 후에도 에러가 남아있습니다")
                return False
                
        except Exception as e:
            print(f"❌ SQL 파일 수정 확인 실패: {e}")
            return False
    
    def apply_xml_fix(self, xml_file_path, xml_fix_result_file, original_xml_content):
        """Q Chat의 XML 수정 제안을 바탕으로 실제 XML 파일을 수정합니다."""
        try:
            if not os.path.exists(xml_file_path):
                print(f"⚠️  XML 파일이 존재하지 않습니다: {xml_file_path}")
                return False
            
            if self.dry_run:
                print(f"🔄 [DRY-RUN] XML 파일 수정 시뮬레이션: {xml_file_path}")
                return True
            
            # Q Chat이 XML 파일을 수정했는지 확인
            xml_modified = self.check_file_modification(xml_file_path, original_xml_content)
            
            if xml_modified:
                print(f"✅ XML 파일이 성공적으로 수정되었습니다: {xml_file_path}")
                return True
            else:
                # Q Chat 응답을 분석하여 수정이 필요없다고 판단했는지 확인
                if xml_fix_result_file and os.path.exists(xml_fix_result_file):
                    with open(xml_fix_result_file, 'r', encoding='utf-8') as f:
                        result_content = f.read()
                    
                    # Q Chat이 수정이 필요없다고 판단한 경우의 키워드들
                    no_fix_keywords = [
                        "수정이 필요하지 않습니다",
                        "이미 올바른 형태",
                        "추가 수정 없이",
                        "올바른 상태",
                        "수정 없이 그대로 사용",
                        "이미 적합한",
                        "문제가 없습니다"
                    ]
                    
                    if any(keyword in result_content for keyword in no_fix_keywords):
                        print(f"✅ XML 파일은 이미 올바른 상태입니다: {xml_file_path}")
                        return True
                
                print(f"⚠️  XML 파일이 수정되지 않았습니다: {xml_file_path}")
                return False
                
        except Exception as e:
            print(f"❌ XML 파일 수정 확인 실패: {e}")
            return False
    def process_single_file(self, sql_file_path):
        """단일 SQL 파일을 처리합니다."""
        print(f"\n🔧 처리 중: {sql_file_path}")
        
        max_retry_attempts = 3  # 최대 재시도 횟수
        
        try:
            # 0. 원본 파일 내용 저장 (수정 전후 비교용)
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                original_sql_content = f.read()
            
            # 1. SQL 파일에서 원본 XML 경로 추출
            xml_file_path = self.extract_source_xml_path(sql_file_path)
            original_xml_content = None
            if xml_file_path and os.path.exists(xml_file_path):
                print(f"📄 원본 XML: {xml_file_path}")
                with open(xml_file_path, 'r', encoding='utf-8') as f:
                    original_xml_content = f.read()
            else:
                print("⚠️  원본 XML 경로를 찾을 수 없거나 파일이 존재하지 않습니다.")
            
            # SQL 수정 반복 시도
            sql_fix_success = False
            attempt = 0
            
            while attempt < max_retry_attempts and not sql_fix_success:
                attempt += 1
                print(f"\n🔄 SQL 수정 시도 {attempt}/{max_retry_attempts}")
                
                # 2. psql 실행하여 에러 캡처
                print("🔍 PostgreSQL 에러 캡처 중...")
                error_output = self.run_psql_and_capture_error(sql_file_path)
                
                # 에러가 없으면 성공
                if "ERROR:" not in error_output:
                    print("✅ SQL 파일에 에러가 없습니다!")
                    sql_fix_success = True
                    break
                
                print(f"❌ 발견된 에러: {error_output[:200]}...")
                
                # 3. SQL 수정 프롬프트 생성
                prompt_file = self.create_sql_fix_prompt(sql_file_path, error_output)
                if not prompt_file:
                    break
                
                # 4. Q Chat으로 SQL 수정 방법 얻기 및 실제 파일 수정
                print("🤖 Q Chat으로 SQL 수정 중...")
                fix_prompt_file = self.run_q_chat_for_sql_fix(prompt_file, sql_file_path)
                if not fix_prompt_file:
                    break
                
                # 5. SQL 파일 수정 확인
                print("🔧 SQL 파일 수정 확인 중...")
                current_sql_content = ""
                with open(sql_file_path, 'r', encoding='utf-8') as f:
                    current_sql_content = f.read()
                
                sql_modified = current_sql_content != original_sql_content
                
                if sql_modified:
                    print("✅ SQL 파일이 수정되었습니다!")
                    # 수정 후 검증
                    verification_result = self.run_psql_and_capture_error(sql_file_path)
                    if "ERROR:" not in verification_result:
                        print("✅ SQL 수정 검증 성공!")
                        sql_fix_success = True
                        break
                    else:
                        print("⚠️  SQL 수정 후에도 에러가 남아있습니다. 다시 시도합니다...")
                        # 다음 시도를 위해 현재 내용을 원본으로 업데이트
                        original_sql_content = current_sql_content
                else:
                    print("⚠️  SQL 파일이 수정되지 않았습니다.")
                    break
            
            if not sql_fix_success:
                print(f"❌ {max_retry_attempts}번 시도 후에도 SQL 에러를 해결하지 못했습니다.")
            
            # 6. XML 파일이 있는 경우 XML 수정
            xml_fix_success = True
            if xml_file_path and os.path.exists(xml_file_path) and original_xml_content:
                xml_fix_prompt_file = self.create_xml_fix_prompt(fix_prompt_file if 'fix_prompt_file' in locals() else None, xml_file_path)
                if xml_fix_prompt_file:
                    # Q Chat으로 XML 수정
                    print("🤖 Q Chat으로 XML 수정 중...")
                    xml_result_file = self.run_q_chat_for_xml_fix(xml_fix_prompt_file, xml_file_path)
                    
                    # XML 파일 수정 확인
                    if xml_result_file:
                        print("🔧 XML 파일 수정 확인 중...")
                        xml_fix_success = self.apply_xml_fix(xml_file_path, xml_result_file, original_xml_content)
                    else:
                        xml_fix_success = False
                else:
                    xml_fix_success = False
            
            # 처리 완료
            self.processed_files.append({
                'sql_file': sql_file_path,
                'xml_file': xml_file_path,
                'prompt_file': prompt_file if 'prompt_file' in locals() else None,
                'fix_prompt_file': fix_prompt_file if 'fix_prompt_file' in locals() else None,
                'sql_fix_success': sql_fix_success,
                'xml_fix_success': xml_fix_success,
                'sql_modified': sql_modified if 'sql_modified' in locals() else False,
                'xml_modified': xml_fix_success if xml_file_path else None,
                'retry_attempts': attempt,
                'timestamp': datetime.now().isoformat()
            })
            
            overall_success = sql_fix_success and xml_fix_success
            if overall_success:
                print(f"✅ 전체 처리 완료: {sql_file_path}")
            else:
                print(f"⚠️  부분 처리 완료: {sql_file_path} (SQL: {'✅' if sql_fix_success else '❌'}, XML: {'✅' if xml_fix_success else '❌'})")
            
            return overall_success
            
        except Exception as e:
            print(f"❌ 파일 처리 실패 ({sql_file_path}): {e}")
            return False
    def process_all_files(self):
        """모든 SQL 파일을 처리합니다."""
        # 1. 에러 유형에 해당하는 SQL 파일 목록 가져오기
        sql_files = self.get_sql_files_for_error_type()
        
        if not sql_files:
            print("❌ 처리할 파일이 없습니다.")
            return
        
        print(f"\n🚀 {len(sql_files)}개 파일 처리 시작...")
        print(f"📋 에러 유형: {self.error_type} ({self.error_type_mapping.get(self.error_type, 'Unknown')})")
        
        if self.dry_run:
            print("🔄 DRY-RUN 모드: 실제 수정 없이 시뮬레이션만 실행합니다.")
        
        # 2. 각 파일 처리
        for i, sql_file in enumerate(sql_files, 1):
            print(f"\n{'='*60}")
            print(f"📁 [{i}/{len(sql_files)}] {sql_file}")
            print(f"{'='*60}")
            
            success = self.process_single_file(sql_file)
            
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
            
            # 진행률 표시
            progress = (i / len(sql_files)) * 100
            print(f"📊 진행률: {progress:.1f}% ({i}/{len(sql_files)})")
        
        # 3. 최종 결과 출력
        self.print_summary()
        
        # 4. 처리 결과를 JSON 파일로 저장
        self.save_processing_log()
    
    def print_summary(self):
        """처리 결과 요약을 출력합니다."""
        print(f"\n{'='*80}")
        print("🎯 처리 결과 요약")
        print(f"{'='*80}")
        
        total_files = self.success_count + self.error_count
        success_rate = (self.success_count / total_files * 100) if total_files > 0 else 0
        
        print(f"📊 전체 파일: {total_files}개")
        print(f"✅ 성공: {self.success_count}개")
        print(f"❌ 실패: {self.error_count}개")
        print(f"📈 성공률: {success_rate:.1f}%")
        print(f"🔧 에러 유형: {self.error_type} ({self.error_type_mapping.get(self.error_type, 'Unknown')})")
        
        if self.dry_run:
            print("🔄 모드: DRY-RUN (시뮬레이션)")
        else:
            print("🚀 모드: 실제 처리")
    
    def save_processing_log(self):
        """처리 결과를 JSON 로그 파일로 저장합니다."""
        log_data = {
            'processing_date': datetime.now().isoformat(),
            'error_type': self.error_type,
            'error_type_name': self.error_type_mapping.get(self.error_type, 'Unknown'),
            'dry_run': self.dry_run,
            'limit': self.limit,
            'total_files': len(self.processed_files),
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / len(self.processed_files) * 100) if self.processed_files else 0,
            'processed_files': self.processed_files
        }
        
        log_file = os.path.join(self.temp_dir, f"pg_transform_log_{self.error_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 처리 로그 저장: {log_file}")
        except Exception as e:
            print(f"❌ 로그 저장 실패: {e}")
def parse_arguments():
    """명령행 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(
        description='PostgreSQL 에러 자동 수정 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python3 pg_transform.py --type=05                # 05번 에러 유형 수정
  python3 pg_transform.py --type=06 --limit=10     # 06번 에러 유형 중 10개만 수정
  python3 pg_transform.py --type=05 --dry-run      # 실제 수정 없이 시뮬레이션만

에러 유형 번호:
  01: Relation Not Found          02: Schema Not Found
  03: Function Not Found          04: Operator Not Found
  05: Subquery Alias Missing      06: Syntax Error
  07: Cross-Database Reference    08: Type Mismatch (COALESCE)
  09: Invalid Input Syntax        10: Invalid FROM Reference
  11: Recursive Query Type        12: Column Not Found
  13: Missing FROM Clause         14: Procedure Not Found
  15: GROUP BY Clause Error       16: Date Format Error
  99: Other Errors
        """
    )
    
    parser.add_argument(
        '--type',
        required=True,
        help='처리할 에러 유형 번호 (01-16, 99)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='처리할 파일 개수 제한'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 수정 없이 시뮬레이션만 실행'
    )
    
    return parser.parse_args()

def main():
    """메인 실행 함수"""
    # 명령행 인수 파싱
    args = parse_arguments()
    
    # 에러 유형 검증
    valid_types = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', 
                   '11', '12', '13', '14', '15', '16', '99']
    
    if args.type not in valid_types:
        print(f"❌ 잘못된 에러 유형: {args.type}")
        print(f"✅ 유효한 에러 유형: {', '.join(valid_types)}")
        sys.exit(1)
    
    # PGTransformer 인스턴스 생성 및 실행
    transformer = PGTransformer(
        error_type=args.type,
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    print(f"🚀 PostgreSQL 에러 자동 수정 도구 시작")
    print(f"📋 에러 유형: {args.type} ({transformer.error_type_mapping.get(args.type, 'Unknown')})")
    
    if args.limit:
        print(f"📊 처리 제한: {args.limit}개 파일")
    
    if args.dry_run:
        print(f"🔄 DRY-RUN 모드: 시뮬레이션만 실행")
    
    # 처리 시작
    transformer.process_all_files()
    
    print(f"\n🎉 PostgreSQL 에러 자동 수정 완료!")

if __name__ == "__main__":
    main()
