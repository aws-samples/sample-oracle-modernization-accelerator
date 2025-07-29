---
layout: default
title: OMA Introduction
nav_order: 2
description: "Oracle Modernization Accelerator 시스템 소개"
---

# OMA (Oracle Modernization Accelerator) 시스템 소개

## 목적

OMA는 Oracle 기반 시스템을 PostgreSQL/MySQL 등의 오픈소스 데이터베이스로 마이그레이션하기 위한 자동화 도구입니다.

### 주요 목적
- Oracle 데이터베이스를 PostgreSQL/MySQL로 변환
- MyBatis 기반 Java 애플리케이션의 SQL 자동 변환
- 마이그레이션 작업의 자동화 및 효율성 향상

## 범위

### 1. **데이터베이스 변환**
- **도구**: AWS Database Migration Service + Schema Conversion Tool 활용
- **대상**: Oracle 스키마, 테이블, 인덱스, 제약조건
- **결과**: PostgreSQL/MySQL 호환 스키마

### 2. **애플리케이션 변환**
- **도구**: OMA 스크립트 기반 자동 변환
- **대상**: MyBatis XML 파일 내 Oracle SQL
- **결과**: Target DBMS 호환 SQL

### 3. **지원 범위**
- **Source**: Oracle Database + Java Spring + MyBatis
- **Target**: PostgreSQL/MySQL + Java Spring + MyBatis
- **변환 대상**: SQL 구문, 함수, 데이터 타입

## OMA Structure

### 디렉토리 구조
```
sample-oracle-modernization-accelerator/          # OMA 루트 폴더
├── initOMA.sh                                    # 메인 실행 스크립트 (통합 진입점)
├── oma_env_[프로젝트명].sh                        # 프로젝트별 환경 변수 파일
├── config/                                       # 프로젝트 설정 파일 디렉토리
│   └── oma.properties                            # 환경 변수로 사용되는 설정 파일
├── [프로젝트명]/                                  # 분석 및 변환 단위 : 애플리케이션명으로 구분
│   ├── dbms/                                     # 데이터베이스 스키마 변환 결과
│   ├── logs/                                     # 전체 프로세스 로그 디렉토리
│   ├── application/                              # 애플리케이션 분석 및 변환 결과
│   │   ├── *.csv                                 # JNDI, Mapper 분석 결과 파일들
│   │   ├── Discovery-Report.html                 # 애플리케이션 분석 리포트
│   │   └── transform/                            # SQL 변환 결과 및 로그
│   └── test/                                     # Unit 테스트 수행 결과 및 도구
└── bin/                                          # OMA 실행 스크립트 및 템플릿
    ├── database/                                 # 데이터베이스 변환 템플릿
    ├── application/                              # 애플리케이션 변환 템플릿 및 도구
    ├── postTransform/                            # Post 변환 작업 스크립트 및 도구
    ├── test/                                     # 테스트 관련 스크립트 및 템플릿
    └── batch/                                    # 배치 처리 관련 스크립트
```

### 핵심 구성 요소

#### **1. 통합 제어 계층**
- **initOMA.sh**: 메뉴 기반 통합 실행 스크립트
- **환경 설정**: 프로젝트별 환경 변수 관리

#### **2. 분석 엔진**
- **애플리케이션 분석**: Java 소스 코드 및 MyBatis XML 파일 분석
- **SQL 추출**: 변환 대상 SQL 식별 및 분류

#### **3. 변환 엔진**
- **SQL 변환**: Oracle SQL을 Target DBMS SQL로 자동 변환
- **XML 처리**: MyBatis XML 파일 변환 및 병합

#### **4. 검증 엔진**
- **Unit 테스트**: 변환된 SQL 동작 검증
- **보고서 생성**: 변환 결과 분석 및 HTML 보고서 생성

## OMA.properties 설정 파일

### 개요
`config/oma.properties` 파일은 OMA 시스템의 모든 환경 변수와 설정을 정의하는 중앙 집중식 설정 파일입니다. setEnv.sh 스크립트에 의해 읽혀져서 프로젝트별 환경 변수 파일(`oma_env_[프로젝트명].sh`)로 변환됩니다.

### 설정 구조

#### **[COMMON] 섹션**
모든 프로젝트에서 공통으로 사용되는 기본 설정들을 정의합니다.

```properties
# OMA 시스템 루트 디렉토리
OMA_BASE_DIR=/path/to/oma

# 데이터베이스 변환 관련 폴더
DBMS_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/database
DBMS_LOGS_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/logs/database

# 애플리케이션 변환 관련 폴더
APPLICATION_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/application
APP_TOOLS_FOLDER=${OMA_BASE_DIR}/bin/application
APP_TRANSFORM_FOLDER=${APPLICATION_FOLDER}/transform
APP_LOGS_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/logs/application

# 테스트 관련 폴더
TEST_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/test
TEST_LOGS_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/logs/test
```

#### **[프로젝트명] 섹션**
각 프로젝트마다 고유한 설정들을 정의합니다.

```properties
[itsm-2nd]
# 애플리케이션 소스 경로
JAVA_SOURCE_FOLDER=/path/to/java/source
SOURCE_SQL_MAPPER_FOLDER=${JAVA_SOURCE_FOLDER}/main/resources/sqlmap
TARGET_SQL_MAPPER_FOLDER=/path/to/target/sqlmap

# 프로젝트 정보
APPLICATION_NAME=itsm-2nd

# 변환 대상 필터링 설정
TRANSFORM_JNDI=jdbc
TRANSFORM_RELATED_CLASS=_ALL_

# 데이터베이스 타입
SOURCE_DBMS_TYPE=orcl
TARGET_DBMS_TYPE=postgres

# Oracle 연결 정보 (Source DB)
ORACLE_HOST=hostname
ORACLE_PORT=1522
ORACLE_SVC_USER=username
ORACLE_SVC_PASSWORD=password

# PostgreSQL 연결 정보 (Target DB)
PGHOST=hostname
PGPORT=5432
PGUSER=username
PGPASSWORD=password
```

### 주요 설정 항목

#### **경로 설정**
- **JAVA_SOURCE_FOLDER**: Java 소스 코드 루트 디렉토리
- **SOURCE_SQL_MAPPER_FOLDER**: 원본 MyBatis XML 파일 위치
- **TARGET_SQL_MAPPER_FOLDER**: 변환된 XML 파일 저장 위치
- **APP_TOOLS_FOLDER**: 변환 도구 및 스크립트 위치

#### **변환 대상 필터링 설정**
- **TRANSFORM_JNDI**: 변환 대상 JNDI를 선별할 때 사용하는 필터
  - 예: `jdbc` - jdbc라는 JNDI를 사용하는 SQL만 변환 대상으로 선별
  - 쉼표(,)로 구분하여 여러 JNDI 지정 가능: `jdbc,jdbc/primary,jdbc/secondary`
  
- **TRANSFORM_RELATED_CLASS**: 변환 대상 클래스를 선별할 때 사용하는 필터
  - `_ALL_`: 모든 클래스의 SQL을 변환 대상으로 설정
  - 특정 클래스명: 해당 클래스와 관련된 SQL만 변환 대상으로 선별
  - 예: `com.example.UserDao` - UserDao 클래스 관련 SQL만 변환

#### **변환 설정**
- **SOURCE_DBMS_TYPE**: 원본 데이터베이스 타입 (orcl)
- **TARGET_DBMS_TYPE**: 대상 데이터베이스 타입 (postgres/mysql)

#### **데이터베이스 연결**
- **Oracle 설정**: ORACLE_HOST, ORACLE_PORT, ORACLE_SVC_USER 등
- **PostgreSQL 설정**: PGHOST, PGPORT, PGUSER 등
- **MySQL 설정**: MYSQL_HOST, MYSQL_PORT, MYSQL_USER 등 (필요시)

### 사용 방법
1. **프로젝트 설정**: [프로젝트명] 섹션에 해당 프로젝트 정보 입력
2. **환경 변수 생성**: `setEnv.sh` 실행으로 `oma_env_[프로젝트명].sh` 파일 생성
3. **환경 변수 로딩**: `source oma_env_[프로젝트명].sh`로 환경 변수 활성화
4. **OMA 실행**: `initOMA.sh` 실행으로 변환 작업 수행
