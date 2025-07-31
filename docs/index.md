---
layout: default
title: Home
nav_order: 1
description: "Oracle Modernization Accelerator - Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 솔루션"
permalink: /
---

# Oracle Modernization Accelerator (OMA)
{: .fs-9 }

Oracle에서 PostgreSQL/MySQL로의 데이터베이스 마이그레이션을 위한 종합 솔루션
{: .fs-6 .fw-300 }

[빠른 시작하기](#주요-기능){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[GitHub에서 보기](https://github.com/aws-samples/sample-oracle-modernization-accelerator){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## 주요 기능

- **🚀 자동화된 인프라 구성**: CloudFormation을 통한 AWS 리소스 자동 배포
- **🤖 AI 기반 코드 분석**: Amazon Q를 활용한 코드 분석 및 변환
- **🔄 데이터베이스 스키마 변환**: DMS Schema Conversion을 통한 자동 변환
- **⚡ 애플리케이션 코드 변환**: Java/MyBatis 코드 자동 변환

## 지원 환경

| 구분 | 지원 기술 |
|:-----|:----------|
| **소스 데이터베이스** | Oracle Database |
| **타겟 데이터베이스** | Aurora PostgreSQL, Aurora MySQL |
| **애플리케이션** | Java, Spring Boot, MyBatis |

---

## 📚 문서 구조

### 사전 준비
{: .text-delta }

- [**OMA Introduction**](OMA-Introduction.md): 프로젝트 개요 및 아키텍처
- [**Pre-Requisites**](Pre-Requisites.md): 인프라 구성 및 환경 설정

### 단계별 가이드
{: .text-delta }

#### ⚙️ 환경 설정 (0단계)
- [**0-1. 환경 설정 수행**](0-1.setEnv.md): 환경 변수 설정
- [**0-2. 환경 설정 확인**](0-2.checkEnv.md): 환경 설정 확인

#### 🔍 애플리케이션 분석 (1단계)
- [**1-1. 애플리케이션 분석**](1-1.processAppAnalysis.md): 애플리케이션 코드 분석
- [**1-2. 분석 보고서 작성**](1-2.processAppReporting.md): 분석 결과 리포팅
- [**1-3. 메타데이터 생성**](1-3.genPostgreSqlMeta.md): PostgreSQL/MySQL 메타데이터 생성

#### 🔄 코드 변환 (2단계)
- [**2-1. SQL 변환 처리**](2-1.processSqlTransform.md): SQL 변환 처리
- [**2-2. 변환 후 처리**](2-2.processPostTransform.md): 변환 후 처리

#### 🧪 SQL Unit Test (3단계)
- [**3-1. SQL Unit Test**](3-1.sqlUnitTest.md): 변환된 SQL 구문의 단위 테스트

#### 📊 결과 통합 (4단계)
- [**4-1. 변환 결과 병합**](4-1.processSqlTransformMerge.md): 변환 결과 병합
- [**4-2. 최종 리포트 생성**](4-2.processSqlTransformReport.md): 최종 리포트 생성
- [**4-3. Java Source 변환**](4-3.processJavaTransform.md): 애플리케이션 Java Source 변환 작업

#### 🔧 UI 오류 수정 (5단계)
- [**5-1. UI 오류-XML 재수정**](5-1.processUIErrorXMLFix.md): UI 관련 XML 오류 재수정 작업

### 추가 리소스
{: .text-delta }

- [**유용한 툴들**](useful-tools.md): OMA 프로젝트에서 활용할 수 있는 도구들

---

## 🎯 시작하기

{: .highlight }
> **시작하기 전에**: [Pre-Requisites](Pre-Requisites.md) 문서를 먼저 확인하여 필요한 인프라와 환경을 구성하세요.

1. **인프라 구성**: AWS 리소스 배포
2. **환경 설정**: 프로젝트별 환경 변수 설정
3. **애플리케이션 분석**: 기존 Oracle 기반 애플리케이션 분석
4. **코드 변환**: SQL 및 애플리케이션 코드 변환
5. **테스트 및 검증**: 변환된 코드의 정확성 검증

---

## 🤝 지원 및 기여

문제가 발생하거나 개선 사항이 있으시면 [GitHub Issues](https://github.com/aws-samples/sample-oracle-modernization-accelerator/issues)를 통해 알려주세요.
