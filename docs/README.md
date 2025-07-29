# Oracle Modernization Accelerator Documentation

이 디렉토리는 정적 HTML 파일들로 구성되어 있습니다.

## 파일 구조

- `*.html` - 변환된 문서 페이지들
- `template.html` - HTML 템플릿
- `convert_to_html.py` - Markdown → HTML 변환 스크립트
- `.nojekyll` - Jekyll 빌드 비활성화

## 접속 방법

GitHub Pages에서 직접 HTML 파일들이 서빙됩니다:
- 메인 페이지: `index.html`
- 빌드 과정 없음 (정적 파일 서빙)

## 업데이트 방법

1. Markdown 파일 수정
2. `python3 convert_to_html.py` 실행
3. 생성된 HTML 파일들을 git에 커밋/푸시
