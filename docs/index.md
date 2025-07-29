---
layout: home
title: "Oracle Modernization Accelerator (OMA)"
---

# Oracle Modernization Accelerator (OMA)

Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 솔루션입니다.

AI 기반 코드 분석, 자동화된 스키마 변환, 애플리케이션 코드 변환을 통해 효율적인 데이터베이스 현대화를 지원합니다.

## 🚀 빠른 시작

```bash
# 메인 실행 스크립트 실행
./initOMA.sh
```

## 📁 주요 구성 요소

### 1. 🔍 애플리케이션 분석
Java 소스 코드 및 MyBatis XML 파일을 자동으로 분석하여 변환 대상 SQL을 식별합니다.

### 2. ⚡ 자동 변환
Oracle SQL을 PostgreSQL/MySQL로 자동 변환하고 MyBatis XML 파일을 처리합니다.

### 3. ✅ 검증 및 테스트
변환된 SQL의 동작을 검증하고 상세한 분석 보고서를 생성합니다.

### 4. 📊 통합 제어 계층
- **initOMA.sh**: 메뉴 기반 통합 실행 스크립트
- **환경 설정**: 프로젝트별 환경 변수 관리

## 📖 문서 구조

### 📋 사전 준비
- **[OMA Introduction](OMA-Introduction.md)**: 프로젝트 개요 및 아키텍처
- **[Pre-Requisites](Pre-Requisites.md)**: 인프라 구성 및 환경 설정

### ⚙️ 환경 설정 (0단계)
- **[0-1. 환경 설정 수행](0-1.setEnv.md)**: 환경 변수 설정
- **[0-2. 환경 설정 확인](0-2.checkEnv.md)**: 환경 설정 확인

### 🔍 애플리케이션 분석 (1단계)
- **[1-1. 애플리케이션 분석](1-1.processAppAnalysis.md)**: 애플리케이션 코드 분석
- **[1-2. 분석 보고서 작성](1-2.processAppReporting.md)**: 분석 결과 리포팅
- **[1-3. 메타데이터 생성](1-3.genPostgreSqlMeta.md)**: PostgreSQL/MySQL 메타데이터 생성

### 🔄 코드 변환 (2단계)
- **[2-1. SQL 변환 처리](2-1.processSqlTransform.md)**: SQL 변환 처리
- **[2-2. 변환 후 처리](2-2.processPostTransform.md)**: 변환 후 처리

### 🧪 SQL Unit Test (3단계)
- **[3-1. SQL Unit Test](3-1.sqlUnitTest.md)**: 변환된 SQL 구문의 단위 테스트

### 📊 결과 통합 (4단계)
- **[4-1. 변환 결과 병합](4-1.processSqlTransformMerge.md)**: 변환 결과 병합
- **[4-2. 최종 리포트 생성](4-2.processSqlTransformReport.md)**: 최종 리포트 생성
- **[4-3. Java Source 변환](4-3.processJavaTransform.md)**: 애플리케이션 Java Source 변환 작업

### 🔧 유용한 툴들
- **[유용한 툴들](useful-tools.md)**: OMA 프로젝트에서 활용할 수 있는 도구들

---

## 🌟 주요 특징

- ✨ **자동화된 인프라 구성**: CloudFormation을 통한 AWS 리소스 자동 배포
- 🤖 **AI 기반 코드 분석**: Amazon Q를 활용한 코드 분석 및 변환
- 🔄 **데이터베이스 스키마 변환**: DMS Schema Conversion을 통한 자동 변환
- ☕ **애플리케이션 코드 변환**: Java/MyBatis 코드 자동 변환

## 🎯 지원 환경

- **소스 데이터베이스**: Oracle Database
- **타겟 데이터베이스**: Aurora PostgreSQL, Aurora MySQL
- **애플리케이션**: Java, Spring Boot, MyBatis

---

**자세한 설치 가이드, 사용법, 단계별 매뉴얼은 각 문서에서 확인하세요.**

[GitHub에서 보기](https://github.com/aws-samples/sample-oracle-modernization-accelerator){: .btn .btn-primary}
