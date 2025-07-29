# Oracle Modernization Accelerator (OMA)

## 목적

Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 솔루션입니다.
AI 기반 코드 분석, 자동화된 스키마 변환, 애플리케이션 코드 변환을 통해 효율적인 데이터베이스 현대화를 지원합니다.

## 📖 상세 문서

**전체 매뉴얼과 가이드는 GitHub Pages에서 확인하세요:**

🔗 **[Oracle Modernization Accelerator 매뉴얼](https://aws-samples.github.io/sample-oracle-modernization-accelerator/)**

## 📁 디렉토리 구조

```
oma/
├── README.md                                     # 프로젝트 개요 (현재 파일)
├── initOMA.sh                                    # 메인 실행 스크립트
├── bin/                                          # 실행 스크립트 및 도구
│   ├── application/                              # 애플리케이션 분석 도구
│   ├── postTransform/                            # 변환 후 처리 도구
│   └── sqlTransform/                             # SQL 변환 도구
├── config/                                       # 설정 파일
├── docs/                                         # 상세 문서 디렉토리
│   ├── index.md                                  # 문서 홈페이지
│   ├── Pre-Requisites.md                        # 사전 요구사항
│   ├── OMA-Introduction.md                      # 시스템 소개
│   ├── 0-*.md                                   # 환경 설정
│   ├── 1-*.md                                   # 애플리케이션 분석
│   ├── 2-*.md                                   # 코드 변환
│   ├── 3-*.md                                   # SQL 단위 테스트
│   └── 4-*.md                                   # 결과 통합
└── [기타 프로젝트 파일들]
```

## ⚡ 빠른 시작

```bash
# 메인 실행 스크립트 실행
./initOMA.sh
```

---

**자세한 설치 가이드, 사용법, 단계별 매뉴얼은 [공식 문서 사이트](https://aws-samples.github.io/sample-oracle-modernization-accelerator/)에서 확인하세요.**
