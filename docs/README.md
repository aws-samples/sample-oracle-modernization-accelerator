# OMA Documentation

이 디렉토리는 Oracle Modernization Accelerator (OMA)의 문서를 포함하고 있습니다.

## GitHub Pages

문서는 GitHub Pages를 통해 자동으로 배포됩니다:
- **URL**: https://aws-samples.github.io/sample-oracle-modernization-accelerator/
- **자동 배포**: main/master 브랜치에 push할 때마다 자동으로 업데이트됩니다.

## 로컬 개발

로컬에서 문서를 미리보기하려면:

```bash
# 의존성 설치 및 서버 실행
./serve.sh

# 또는 수동으로
bundle install
bundle exec jekyll serve --livereload
```

서버가 실행되면 http://localhost:4000 에서 확인할 수 있습니다.

## 파일 구조

- `_config.yml`: Jekyll 설정 파일
- `Gemfile`: Ruby 의존성 정의
- `*.md`: Markdown 문서 파일들
- `.nojekyll`: GitHub Pages Jekyll 처리 비활성화 (우리는 GitHub Actions 사용)
