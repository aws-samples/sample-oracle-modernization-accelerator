---
layout: default
title: Home
nav_order: 1
description: "OMA (Oracle Modernization Accelerator) Manual - Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 가이드"
permalink: /
---

# OMA (Oracle Modernization Accelerator) Manual

Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 가이드

[빠른 시작](#빠른-시작) | [GitHub에서 보기](https://github.com/aws-samples/sample-oracle-modernization-accelerator)

---

## Getting started

### 빠른 시작

1. [사전 요구사항](documents/Pre-Requisites.md) - 인프라 구성 및 환경 설정
2. [OMA 소개](documents/OMA-Introduction.md) - OMA 프로젝트 개요
3. [환경 설정](documents/0-1.setEnv.md) - 프로젝트별 환경 변수 설정

### 주요 기능

- **자동화된 인프라 구성**: CloudFormation을 통한 AWS 리소스 자동 배포
- **AI 기반 코드 분석**: Amazon Q를 활용한 코드 분석 및 변환
- **데이터베이스 스키마 변환**: DMS Schema Conversion을 통한 자동 변환
- **애플리케이션 코드 변환**: Java/MyBatis 코드 자동 변환

### 지원 환경

- **소스 데이터베이스**: Oracle Database
- **타겟 데이터베이스**: Aurora PostgreSQL, Aurora MySQL
- **애플리케이션**: Java, Spring Boot, MyBatis

---

## 문서 구조

이 매뉴얼은 다음과 같이 구성되어 있습니다:

### 📋 사전 준비
- **[OMA Introduction](documents/OMA-Introduction.md)**: 프로젝트 개요 및 아키텍처
- **[Pre-Requisites](documents/Pre-Requisites.md)**: 인프라 구성 및 환경 설정

### ⚙️ 환경 설정 (0단계)
- **[0-1. 환경 설정 수행](documents/0-1.setEnv.md)**: 환경 변수 설정
- **[0-2. 환경 설정 확인](documents/0-2.checkEnv.md)**: 환경 설정 확인

### 🔍 애플리케이션 분석 (1단계)
- **[1-1. 애플리케이션 분석](documents/1-1.processAppAnalysis.md)**: 애플리케이션 코드 분석
- **[1-2. 분석 보고서 작성](documents/1-2.processAppReporting.md)**: 분석 결과 리포팅
- **[1-3. 메타데이터 생성](documents/1-3.genPostgreSqlMeta.md)**: PostgreSQL/MySQL 메타데이터 생성

### 🔄 코드 변환 (2단계)
- **[2-1. SQL 변환 처리](documents/2-1.processSqlTransform.md)**: SQL 변환 처리
- **[2-2. 변환 후 처리](documents/2-2.processPostTransform.md)**: 변환 후 처리

### 🧪 SQL Unit Test (3단계)
- **[3-1. SQL Unit Test](documents/3-1.sqlUnitTest.md)**: 변환된 SQL 구문의 단위 테스트

### 📊 결과 통합 (4단계)
- **[4-1. 변환 결과 병합](documents/4-1.processSqlTransformMerge.md)**: 변환 결과 병합
- **[4-2. 최종 리포트 생성](documents/4-2.processSqlTransformReport.md)**: 최종 리포트 생성
- **[4-3. Java Source 변환](documents/4-3.processJavaTransform.md)**: 애플리케이션 Java Source 변환 작업

### 🔧 유용한 툴들
- **[유용한 툴들](documents/useful-tools.md)**: OMA 프로젝트에서 활용할 수 있는 도구들

### 카테고리별 문서 인덱스
- **[환경 설정](documents/environment-setup.md)**
- **[애플리케이션 분석](documents/application-analysis.md)**
- **[코드 변환](documents/code-transformation.md)**
- **[SQL 단위 테스트](documents/sql-unit-test.md)**
- **[결과 통합](documents/result-integration.md)**

---

## 실행 가이드

### 통합 실행 스크립트
```bash
# 메인 실행 스크립트 - 메뉴 기반 단계별 선택 실행
./initOMA.sh
```

### 메뉴 구조
```
0. 환경 설정 및 확인
   1. 환경 설정 다시 수행 (setEnv.sh)
   2. 현재 환경 변수 확인 (checkEnv.sh)

1. 애플리케이션 분석
   1. 애플리케이션 분석
   2. 분석 보고서 작성 및 SQL변환 대상 추출
   3. (PostgreSQL Only) 데이터베이스 메타데이터 작성

2. 애플리케이션 변환
   1. 애플리케이션 SQL 변환 작업 : SQLID별 변환
   2. Post 변환 작업

3. SQL 테스트 수행
   1. XML List 생성
   2. 애플리케이션 SQL Unit Test

4. 변환 작업 완료
   1. XML Merge 작업 - SQLID to XML
   2. 변환 작업 보고서
   3. 애플리케이션 Java Source 변환 작업
```

### 개별 단계 실행
```bash
# Step 1: 환경 설정
./bin/setEnv.sh
source ./oma_env_프로젝트명.sh

# Step 2: DB Schema 변환
./bin/processDBSchema.sh

# Step 3: 애플리케이션 Discovery
./bin/processappDiscovery.sh

# Step 4: SQL 변환
./bin/processSQLTransform.sh

# Step 5: SQL Unit Test
./bin/processSQLTest.sh
```

---

## 디렉토리 구조

```
sample-oracle-modernization-accelerator/          # OMA 루트 폴더 (OMA_BASE_DIR)
├── initOMA.sh                                    # 메인 실행 스크립트 (통합 진입점)
├── oma_env_[프로젝트명].sh                        # 프로젝트별 환경 변수 파일
├── config/                                       # 프로젝트 설정 파일 디렉토리
│   └── oma.properties                            # 환경 변수로 사용되는 설정 파일
├── documents/                                    # 상세 문서 디렉토리
├── [프로젝트명]/                                   # 분석 및 변환 단위 (애플리케이션명으로 구분)
│   ├── database/                                 # 데이터베이스 스키마 변환 결과
│   ├── logs/                                     # 전체 프로세스 로그 디렉토리
│   ├── application/                              # 애플리케이션 분석 및 변환 결과
│   │   ├── *.csv                                 # JNDI, Mapper 분석 결과 파일들
│   │   ├── Discovery-Report.html                 # 애플리케이션 분석 리포트
│   │   └── transform/                            # SQL 변환 결과 및 로그
│   └── test/                                     # Unit 테스트 수행 결과 및 도구
└── bin/                                          # OMA 실행 스크립트 및 템플릿
    ├── setEnv.sh                                 # 환경 설정 스크립트
    ├── checkEnv.sh                               # 환경 변수 확인 스크립트
    ├── processDBSchema.sh                        # DB Schema 변환 스크립트
    ├── processappDiscovery.sh                    # 애플리케이션 Discovery 스크립트
    ├── processSQLTransform.sh                    # SQL 변환 스크립트
    ├── processSQLTest.sh                         # SQL Unit Test 스크립트
    ├── database/                                 # 데이터베이스 변환 템플릿
    ├── application/                              # 애플리케이션 변환 템플릿
    ├── promptTemplate/                           # AI 프롬프트 템플릿
    └── test/                                     # 테스트 템플릿
```

---

## 지원 및 기여

문제가 발생하거나 개선 사항이 있으시면 [GitHub Issues](https://github.com/aws-samples/sample-oracle-modernization-accelerator/issues)를 통해 알려주세요.
