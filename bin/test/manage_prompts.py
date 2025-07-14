#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
프롬프트 템플릿 관리 유틸리티

사용법:
  python3 manage_prompts.py list                    # 프롬프트 목록 보기
  python3 manage_prompts.py show sql_fix            # 특정 프롬프트 내용 보기
  python3 manage_prompts.py edit sql_fix            # 프롬프트 편집
  python3 manage_prompts.py test sql_fix            # 프롬프트 테스트
"""

import os
import json
import sys
import argparse
import subprocess
from pathlib import Path

class PromptManager:
    def __init__(self):
        self.prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        self.config_path = os.path.join(self.prompts_dir, 'config.json')
        self.config = self.load_config()
    
    def load_config(self):
        """설정 파일을 로드합니다."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 설정 파일을 찾을 수 없습니다: {self.config_path}")
            return {}
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")
            return {}
    
    def list_prompts(self):
        """프롬프트 목록을 출력합니다."""
        print("📋 사용 가능한 프롬프트 템플릿:")
        print("=" * 60)
        
        prompts = self.config.get('prompts', {})
        if not prompts:
            print("❌ 설정된 프롬프트가 없습니다.")
            return
        
        for prompt_type, prompt_config in prompts.items():
            file_name = prompt_config.get('file', 'N/A')
            description = prompt_config.get('description', 'N/A')
            timeout = prompt_config.get('timeout', 'N/A')
            
            file_path = os.path.join(self.prompts_dir, file_name)
            exists = "✅" if os.path.exists(file_path) else "❌"
            
            print(f"{exists} {prompt_type}")
            print(f"   파일: {file_name}")
            print(f"   설명: {description}")
            print(f"   타임아웃: {timeout}초")
            print()
    
    def show_prompt(self, prompt_type):
        """특정 프롬프트의 내용을 출력합니다."""
        prompt_config = self.config.get('prompts', {}).get(prompt_type)
        if not prompt_config:
            print(f"❌ 프롬프트 타입 '{prompt_type}'을 찾을 수 없습니다.")
            return
        
        file_name = prompt_config.get('file')
        file_path = os.path.join(self.prompts_dir, file_name)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"📄 프롬프트 내용: {prompt_type} ({file_name})")
            print("=" * 60)
            print(content)
            print("=" * 60)
            
        except FileNotFoundError:
            print(f"❌ 프롬프트 파일을 찾을 수 없습니다: {file_path}")
        except Exception as e:
            print(f"❌ 프롬프트 파일 읽기 실패: {e}")
    
    def edit_prompt(self, prompt_type):
        """프롬프트를 편집합니다."""
        prompt_config = self.config.get('prompts', {}).get(prompt_type)
        if not prompt_config:
            print(f"❌ 프롬프트 타입 '{prompt_type}'을 찾을 수 없습니다.")
            return
        
        file_name = prompt_config.get('file')
        file_path = os.path.join(self.prompts_dir, file_name)
        
        # 기본 에디터 확인
        editor = os.environ.get('EDITOR', 'nano')
        
        try:
            subprocess.run([editor, file_path], check=True)
            print(f"✅ 프롬프트 편집 완료: {file_path}")
        except subprocess.CalledProcessError:
            print(f"❌ 에디터 실행 실패: {editor}")
        except FileNotFoundError:
            print(f"❌ 에디터를 찾을 수 없습니다: {editor}")
            print("EDITOR 환경변수를 설정하거나 nano, vim 등을 설치하세요.")
    
    def test_prompt(self, prompt_type):
        """프롬프트를 테스트합니다."""
        prompt_config = self.config.get('prompts', {}).get(prompt_type)
        if not prompt_config:
            print(f"❌ 프롬프트 타입 '{prompt_type}'을 찾을 수 없습니다.")
            return
        
        file_name = prompt_config.get('file')
        file_path = os.path.join(self.prompts_dir, file_name)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            print(f"🧪 프롬프트 테스트: {prompt_type}")
            print("=" * 60)
            
            # 템플릿 변수 찾기
            import re
            variables = re.findall(r'\{(\w+)\}', template_content)
            
            if variables:
                print(f"📝 발견된 변수: {', '.join(set(variables))}")
                
                # 테스트 데이터로 변수 치환
                test_data = {}
                for var in set(variables):
                    if var == 'sql_content':
                        test_data[var] = "SELECT * FROM test_table;"
                    elif var == 'error_output':
                        test_data[var] = "ERROR: relation 'test_table' does not exist"
                    elif var == 'xml_content':
                        test_data[var] = "<select id='test'>SELECT * FROM test_table</select>"
                    elif var == 'sql_original':
                        test_data[var] = "SELECT * FROM test_table;"
                    elif var == 'sql_fixed':
                        test_data[var] = "SELECT * FROM test_table_fixed;"
                    else:
                        test_data[var] = f"[TEST_{var.upper()}]"
                
                try:
                    formatted_prompt = template_content.format(**test_data)
                    print("\n✅ 변수 치환 성공!")
                    print("\n📄 치환된 프롬프트:")
                    print("-" * 40)
                    print(formatted_prompt)
                    print("-" * 40)
                    
                except KeyError as e:
                    print(f"❌ 변수 치환 실패: {e}")
                except Exception as e:
                    print(f"❌ 프롬프트 포맷팅 실패: {e}")
            else:
                print("📝 변수가 없는 정적 프롬프트입니다.")
                print("\n📄 프롬프트 내용:")
                print("-" * 40)
                print(template_content)
                print("-" * 40)
                
        except FileNotFoundError:
            print(f"❌ 프롬프트 파일을 찾을 수 없습니다: {file_path}")
        except Exception as e:
            print(f"❌ 프롬프트 테스트 실패: {e}")

def parse_arguments():
    """명령행 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(
        description='프롬프트 템플릿 관리 유틸리티',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python3 manage_prompts.py list                    # 프롬프트 목록 보기
  python3 manage_prompts.py show sql_fix            # 특정 프롬프트 내용 보기
  python3 manage_prompts.py edit sql_fix            # 프롬프트 편집
  python3 manage_prompts.py test sql_fix            # 프롬프트 테스트
        """
    )
    
    parser.add_argument(
        'command',
        choices=['list', 'show', 'edit', 'test'],
        help='실행할 명령'
    )
    
    parser.add_argument(
        'prompt_type',
        nargs='?',
        help='프롬프트 타입 (show, edit, test 명령에 필요)'
    )
    
    return parser.parse_args()

def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    manager = PromptManager()
    
    if args.command == 'list':
        manager.list_prompts()
    elif args.command == 'show':
        if not args.prompt_type:
            print("❌ 프롬프트 타입을 지정해주세요.")
            return
        manager.show_prompt(args.prompt_type)
    elif args.command == 'edit':
        if not args.prompt_type:
            print("❌ 프롬프트 타입을 지정해주세요.")
            return
        manager.edit_prompt(args.prompt_type)
    elif args.command == 'test':
        if not args.prompt_type:
            print("❌ 프롬프트 타입을 지정해주세요.")
            return
        manager.test_prompt(args.prompt_type)

if __name__ == "__main__":
    main()
