---
layout: home
title: Oracle Modernization Accelerator
---

# Oracle Modernization Accelerator (OMA)

Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 솔루션입니다.

## 주요 기능

- **자동화된 인프라 구성**: CloudFormation을 통한 AWS 리소스 자동 배포
- **AI 기반 코드 분석**: Amazon Q를 활용한 코드 분석 및 변환
- **데이터베이스 스키마 변환**: DMS Schema Conversion을 통한 자동 변환
- **애플리케이션 코드 변환**: Java/MyBatis 코드 자동 변환

## 지원 환경

| 구분 | 지원 기술 |
|:-----|:----------|
| **소스 데이터베이스** | Oracle Database |
| **타겟 데이터베이스** | Aurora PostgreSQL, Aurora MySQL |
| **애플리케이션** | Java, Spring Boot, MyBatis |

## 시작하기

1. [**OMA Introduction**](OMA-Introduction.md): 프로젝트 개요 및 아키텍처
2. [**Pre-Requisites**](Pre-Requisites.md): 인프라 구성 및 환경 설정

## 단계별 가이드

### 환경 설정 (0단계)
- [0-1. 환경 설정 수행](0-1.setEnv.md)
- [0-2. 환경 설정 확인](0-2.checkEnv.md)

### 애플리케이션 분석 (1단계)
- [1-1. 애플리케이션 분석](1-1.processAppAnalysis.md)
- [1-2. 분석 보고서 작성](1-2.processAppReporting.md)
- [1-3. 메타데이터 생성](1-3.genPostgreSqlMeta.md)

### 코드 변환 (2단계)
- [2-1. SQL 변환 처리](2-1.processSqlTransform.md)
- [2-2. 변환 후 처리](2-2.processPostTransform.md)

### SQL Unit Test (3단계)
- [3-1. SQL Unit Test](3-1.sqlUnitTest.md)

### 결과 통합 (4단계)
- [4-1. 변환 결과 병합](4-1.processSqlTransformMerge.md)
- [4-2. 최종 리포트 생성](4-2.processSqlTransformReport.md)
- [4-3. Java Source 변환](4-3.processJavaTransform.md)

### UI 오류 수정 (5단계)
- [5-1. UI 오류-XML 재수정](5-1.processUIErrorXMLFix.md)

## 추가 리소스

- [유용한 툴들](useful-tools.md)

## 지원 및 기여

문제가 발생하거나 개선 사항이 있으시면 [GitHub Issues](https://github.com/aws-samples/sample-oracle-modernization-accelerator/issues)를 통해 알려주세요.
