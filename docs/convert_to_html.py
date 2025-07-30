#!/usr/bin/env python3
"""
Markdown to HTML Converter for OMA Documentation
Oracle Modernization Accelerator 문서를 HTML로 변환하는 스크립트
"""

import os
import re
import markdown
from pathlib import Path

# 페이지 정보 매핑
PAGE_INFO = {
    'index.md': {
        'title': 'Oracle Modernization Accelerator',
        'description': 'Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 솔루션',
        'breadcrumb': '홈'
    },
    'Pre-Requisites.md': {
        'title': '사전 요구사항',
        'description': 'OMA 프로젝트 시작 전 필요한 사전 요구사항과 환경 설정',
        'breadcrumb': '사전 요구사항'
    },
    'OMA-Introduction.md': {
        'title': 'OMA 소개',
        'description': 'Oracle Modernization Accelerator의 개요와 핵심 구성 요소',
        'breadcrumb': 'OMA 소개'
    },
    '0-1.setEnv.md': {
        'title': '환경 변수 설정',
        'description': '프로젝트별 환경 변수 설정 및 관리',
        'breadcrumb': '환경 설정 > 환경 변수 설정'
    },
    '0-2.checkEnv.md': {
        'title': '환경 검증',
        'description': '설정된 환경의 유효성 검증 및 문제 해결',
        'breadcrumb': '환경 설정 > 환경 검증'
    },
    '1-1.processAppAnalysis.md': {
        'title': '애플리케이션 분석',
        'description': 'Java 애플리케이션 코드 분석 및 변환 대상 추출',
        'breadcrumb': '애플리케이션 분석 > 앱 분석'
    },
    '1-2.processAppReporting.md': {
        'title': '애플리케이션 리포팅',
        'description': '분석 결과 리포트 생성 및 통계 정보 제공',
        'breadcrumb': '애플리케이션 분석 > 앱 리포팅'
    },
    '1-3.genPostgreSqlMeta.md': {
        'title': 'PostgreSQL 메타데이터 생성',
        'description': 'PostgreSQL 데이터베이스 메타데이터 생성 및 관리',
        'breadcrumb': '애플리케이션 분석 > PostgreSQL 메타'
    },
    '2-1.processSqlTransform.md': {
        'title': 'SQL 변환',
        'description': 'Oracle SQL을 PostgreSQL/MySQL로 자동 변환',
        'breadcrumb': '코드 변환 > SQL 변환'
    },
    '2-2.processPostTransform.md': {
        'title': '후처리 변환',
        'description': 'SQL 변환 후 추가 처리 및 최적화',
        'breadcrumb': '코드 변환 > 후처리 변환'
    },
    '3-1.sqlUnitTest.md': {
        'title': 'SQL 단위 테스트',
        'description': 'Oracle Migration Accelerator 테스트 프로그램들의 기능과 사용법',
        'breadcrumb': 'SQL 단위 테스트'
    },
    '4-1.processSqlTransformMerge.md': {
        'title': 'SQL 변환 병합',
        'description': '변환된 SQL 파일들의 병합 및 통합 관리',
        'breadcrumb': '결과 통합 > SQL 변환 병합'
    },
    '4-2.processSqlTransformReport.md': {
        'title': 'SQL 변환 리포트',
        'description': 'SQL 변환 결과 분석 및 리포트 생성',
        'breadcrumb': '결과 통합 > SQL 변환 리포트'
    },
    '4-3.processJavaTransform.md': {
        'title': 'Java 변환',
        'description': 'Java 애플리케이션 코드 변환 및 최적화',
        'breadcrumb': '결과 통합 > Java 변환'
    },
    '5-1.processUIErrorXMLFix.md': {
        'title': 'UI 오류-XML 재수정',
        'description': 'UI 관련 XML 오류 재수정 작업',
        'breadcrumb': 'UI 오류 수정 > UI 오류-XML 재수정'
    },
    'ui-error-fix.md': {
        'title': 'UI 오류 수정',
        'description': 'UI 관련 XML 오류 수정 작업',
        'breadcrumb': 'UI 오류 수정'
    },
    'useful-tools.md': {
        'title': '유용한 툴들',
        'description': 'OMA 프로젝트에서 활용할 수 있는 유용한 도구들',
        'breadcrumb': '유용한 툴들'
    }
}

def read_template():
    """HTML 템플릿 파일 읽기"""
    template_path = Path(__file__).parent / 'template.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

def convert_markdown_to_html(md_content):
    """Markdown을 HTML로 변환"""
    # Markdown 확장 기능 설정
    extensions = [
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'markdown.extensions.attr_list',
        'markdown.extensions.def_list',
        'markdown.extensions.abbr',
        'markdown.extensions.footnotes'
    ]
    
    # Markdown 변환
    md = markdown.Markdown(extensions=extensions)
    html_content = md.convert(md_content)
    
    return html_content

def clean_markdown_content(content):
    """Markdown 내용 정리 (Jekyll front matter 제거 등)"""
    # Jekyll front matter 제거
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL | re.MULTILINE)
    
    # 상대 링크를 HTML 확장자로 변경
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\.md\)', r'[\1](\2.html)', content)
    
    return content

def add_bootstrap_classes(html_content):
    """Bootstrap 클래스 추가"""
    # 테이블에 Bootstrap 클래스 추가
    html_content = re.sub(r'<table>', r'<table class="table table-striped table-hover">', html_content)
    
    # 알림 박스 스타일 추가
    html_content = re.sub(r'<blockquote>', r'<div class="alert alert-info">', html_content)
    html_content = re.sub(r'</blockquote>', r'</div>', html_content)
    
    # 코드 블록 개선
    html_content = re.sub(r'<pre><code class="language-(\w+)">', r'<pre><code class="language-\1">', html_content)
    
    # 버튼 스타일 추가
    html_content = re.sub(r'<a href="([^"]+)" class="btn">([^<]+)</a>', 
                         r'<a href="\1" class="btn btn-primary">\2</a>', html_content)
    
    return html_content

def convert_file(md_file_path, template):
    """개별 Markdown 파일을 HTML로 변환"""
    md_file = Path(md_file_path)
    
    # Markdown 파일 읽기
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 내용 정리
    md_content = clean_markdown_content(md_content)
    
    # HTML로 변환
    html_content = convert_markdown_to_html(md_content)
    
    # Bootstrap 클래스 추가
    html_content = add_bootstrap_classes(html_content)
    
    # 페이지 정보 가져오기
    page_info = PAGE_INFO.get(md_file.name, {
        'title': md_file.stem.replace('-', ' ').title(),
        'description': f'{md_file.stem} 문서',
        'breadcrumb': md_file.stem.replace('-', ' ').title()
    })
    
    # 템플릿에 내용 삽입
    final_html = template.replace('{{TITLE}}', page_info['title'])
    final_html = final_html.replace('{{DESCRIPTION}}', page_info['description'])
    final_html = final_html.replace('{{BREADCRUMB}}', page_info['breadcrumb'])
    final_html = final_html.replace('{{CONTENT}}', html_content)
    
    # HTML 파일로 저장
    html_file = md_file.with_suffix('.html')
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"✅ 변환 완료: {md_file.name} → {html_file.name}")

def main():
    """메인 함수"""
    print("🚀 OMA 문서 HTML 변환 시작...")
    
    # 현재 디렉토리
    docs_dir = Path(__file__).parent
    
    # 템플릿 읽기
    template = read_template()
    
    # 모든 Markdown 파일 찾기
    md_files = list(docs_dir.glob('*.md'))
    
    # 변환할 파일 필터링 (특정 파일 제외)
    exclude_files = {'README.md', 'template.md'}
    md_files = [f for f in md_files if f.name not in exclude_files]
    
    print(f"📄 변환할 파일 수: {len(md_files)}개")
    
    # 각 파일 변환
    for md_file in md_files:
        try:
            convert_file(md_file, template)
        except Exception as e:
            print(f"❌ 변환 실패: {md_file.name} - {str(e)}")
    
    print("\n🎉 HTML 변환 완료!")
    print("📁 생성된 HTML 파일들:")
    
    # 생성된 HTML 파일 목록 출력
    html_files = list(docs_dir.glob('*.html'))
    html_files = [f for f in html_files if f.name != 'template.html']
    
    for html_file in sorted(html_files):
        print(f"   - {html_file.name}")
    
    print(f"\n💡 총 {len(html_files)}개의 HTML 파일이 생성되었습니다.")
    print("🌐 index.html 파일을 브라우저에서 열어보세요!")

if __name__ == '__main__':
    main()
