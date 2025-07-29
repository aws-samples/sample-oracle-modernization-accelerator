---
layout: default
title: Pre-Requisites
nav_order: 3
description: "OMA Infrastructure 구성"
---

# Pre-Requisites. OMA Infrastructure 구성

## 목적
OMA(Oracle Modernization Accelerator) 프로젝트 실행을 위한 필수 인프라 환경을 구성하고, 데이터베이스 마이그레이션 작업을 위한 기반 환경을 준비합니다.

## AWS CLI 환경 구성 (사전 요구사항)

인프라 구성 전에 AWS CLI 환경이 설정되어 있어야 합니다:

```bash
# AWS 자격증명 환경 변수 설정
export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
export AWS_SESSION_TOKEN="YOUR_SESSION_TOKEN"  # 임시 자격증명 사용 시
export AWS_DEFAULT_REGION="ap-northeast-2"

# 연결 테스트
aws sts get-caller-identity
```

## 실행 흐름
```
config/setup.sh 
  → setup/deploy-omabox.sh 
    → Secrets Manager 설정
    → CloudFormation 배포 (omabox-cloudformation.yaml)
      → initOMA.sh 실행 안내
```

## 상세 분석

### **인프라 구성**

#### **인프라 배포**
OMA 프로젝트에서 `config/setup.sh`를 실행하면, `setup/deploy-omabox.sh`를 통해 Secret Manager를 우선 생성하고, CloudFormation을 통해 필요한 인프라를 생성합니다.

```bash
# 실행 구조
config/setup.sh
├── setup/deploy-omabox.sh 호출
│   ├── 옵션 1: Secrets Manager 설정 - DBMS 관련한 Connection 정보를 설정
│   └── 옵션 2: CloudFormation 배포 - OMA Infrastructure 자원 배포
└── 완료 후 initOMA.sh 실행 안내
```

#### **생성되는 인프라 구성요소**

##### **🏗️ 네트워킹 인프라**
- **VPC**: OMA_VPC (10.255.255.0/24)
- **서브넷 구성**:
  - **Public Subnet 2개** (AZ-a, AZ-b): NAT Gateway용
  - **Private Subnet 2개** (AZ-a, AZ-b): EC2, Aurora, DMS용
- **네트워킹 구성요소**:
  - Internet Gateway
  - NAT Gateway (Public Subnet 1에 위치)
  - Route Tables (Public/Private 분리)

##### **🔐 보안 및 암호화**
- **KMS Key**: 모든 리소스 암호화용
- **Security Groups**:
  - OMABox용 (EC2 인스턴스)
  - VPC Endpoint용 (HTTPS 443 포트)
  - Database용 (PostgreSQL 5432, MySQL 3306, Oracle 1521 포트)
- **IAM Roles**:
  - EC2 인스턴스용 (SSM, CloudWatch, S3, Secrets Manager 권한)
  - DMS용 (VPC 관리, CloudWatch 로그)
  - DMS Schema Conversion용 (S3, Secrets Manager 접근)

##### **🔌 VPC Endpoints (Private 통신용)**
- **SSM Endpoint**: Session Manager 접속용
- **SSM Messages Endpoint**: Session Manager 메시징
- **EC2 Messages Endpoint**: EC2 메시징
- **Secrets Manager Endpoint**: 데이터베이스 자격증명 접근

##### **🗄️ 데이터베이스 인프라**
- **Aurora Database Cluster** (PostgreSQL 또는 MySQL 선택 가능):
  - Engine: aurora-postgresql 15.7 또는 aurora-mysql 8.0
  - Instance Class: db.r6g.large
  - 암호화 활성화 (KMS)
  - 백업 보존 기간: 7일
- **DB Subnet Group**: Private Subnet에서 Aurora 실행

##### **🔄 DMS (Database Migration Service)**
- **DMS Replication Instance**: dms.t3.medium (50GB 스토리지)
- **DMS Endpoints**:
  - Source: Oracle 데이터베이스 연결
  - Target: Aurora PostgreSQL 또는 MySQL 연결
- **DMS Schema Conversion**:
  - Migration Project 생성
  - S3 버킷 (변환 결과 저장)
  - Data Providers (Oracle ↔ PostgreSQL/MySQL)

##### **💻 EC2 인스턴스 (OMABox)**
- **Instance Type**: m6i.xlarge
- **OS**: Amazon Linux 2023
- **위치**: Private Subnet (인터넷 직접 접근 불가)
- **접속 방법**: AWS Systems Manager Session Manager

##### **📦 사전 설치 소프트웨어**
- **Oracle Client**: Instant Client 19.26 (SQLPlus, JDBC 포함)
- **PostgreSQL Client**: postgresql15
- **MySQL Client**: mysql-community-client
- **AWS CLI v2**
- **Amazon Q CLI**: AI 기반 개발 도구
- **기타 도구**: jq, wget, unzip, libaio, libnsl

##### **🌍 환경 변수 자동 설정**
- **Oracle 환경**:
  - ORACLE_HOME, ORACLE_SID, ORACLE_ADM_USER 등
  - Secrets Manager에서 자격증명 자동 로드
- **PostgreSQL/MySQL 환경**:
  - PGHOST (Aurora 엔드포인트), PGUSER, PGPASSWORD 등 (PostgreSQL용)
  - MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD 등 (MySQL용)
  - Aurora 연결 정보 자동 구성
- **OMA 환경**:
  - OMA_HOME, DB_ASSESSMENTS_FOLDER 등

### **OMA 환경 설정**

#### **OMA 프로젝트 초기화**
OMABox (EC2)가 생성되면 Application Source 코드를 준비하고 GitHub에서 OMA 프로젝트 코드를 동기화한 후 환경 설정을 진행합니다.

##### **Application Source 코드 Location**
마이그레이션 작업을 위해 Source와 Target용 두 개의 폴더에 동일한 애플리케이션 소스 코드를 복사합니다. 디렉토리명으로 Source/Target을 구분할 수 있도록 구성합니다.

```bash
# 애플리케이션 소스 코드 디렉토리 생성 (예시)
mkdir -p /home/ec2-user/workspace/chalee/orcl-itsm      # Oracle용 소스 코드
mkdir -p /home/ec2-user/workspace/chalee/postgres-itsm  # PostgreSQL용 소스 코드
mkdir -p /home/ec2-user/workspace/chalee/mysql-itsm     # MySQL용 소스 코드

# 원본 애플리케이션 소스를 두 디렉토리에 복사
# (실제 소스 코드 위치에 따라 경로 조정 필요)
cp -r /path/to/original/source/* /home/ec2-user/workspace/chalee/orcl-itsm/
cp -r /path/to/original/source/* /home/ec2-user/workspace/chalee/postgres-itsm/
```

##### **OMA 도구 설치**
```bash
# workspace 디렉토리 생성 및 이동
mkdir -p ~/workspace
cd ~/workspace

# GitHub에서 OMA 프로젝트 코드 동기화
git clone https://github.com/aws-samples/sample-oracle-modernization-accelerator.git oma

# 프로젝트 디렉토리로 이동
cd ~/workspace/oma
```

#### **설정 파일 (oma.properties) 구성**
⚠️ **중요**: initOMA.sh 실행 전에 반드시 설정 파일을 구성해야 합니다.

- **파일 위치**: `config/oma.properties`
- **역할**: OMA 프로젝트의 모든 환경 변수와 설정값을 중앙 관리
- **사용**: `setEnv.sh` 실행 시 이 파일을 기반으로 프로젝트별 환경 변수 파일 생성

#### **환경 설정 실행**
설정 파일 구성이 완료된 후 환경 설정을 실행합니다.

```bash
# 환경 설정 실행
./initOMA.sh
# 메뉴에서 "0. 환경설정 및 확인" 선택

# 또는 직접 환경 설정
./bin/setEnv.sh

# 환경 변수 로드 (생성된 파일 사용)
source ./oma_env_<project_name>.sh

# 환경 변수 확인
./bin/checkEnv.sh
```

### **타겟 데이터베이스 생성**

#### **타겟 데이터베이스 생성**
Aurora PostgreSQL 또는 MySQL에 타겟 DB `<target_database_name>`을 생성합니다.

⚠️ **MySQL 타겟 DB 사용 시 주의사항**
- Target DBMS가 MySQL인 경우, Parameter `lower_case_table_names`에 대한 원칙 수립이 필요합니다.
- Oracle에서 MySQL로 마이그레이션 시 테이블명/컬럼명의 대소문자 처리 방식이 다르므로 사전에 정책을 결정해야 합니다.
- `lower_case_table_names=0` (대소문자 구분) 또는 `lower_case_table_names=1` (소문자로 변환) 설정에 따라 마이그레이션 전략이 달라집니다.

```bash
# 타겟 DB 생성 실행
~/workspace/oma/bin/createDB.sh
```

- ENCODING, LC_COLLATE, LC_CTYPE를 포함하여 DB를 생성합니다.

## 완료 체크리스트

### **인프라 구성 완료 확인**
- [ ] **CloudFormation 완료**: 모든 AWS 리소스가 정상적으로 생성됨
- [ ] **Target database cluster 생성**: Aurora PostgreSQL 또는 MySQL 클러스터 정상 동작
- [ ] **OMABox 인스턴스 생성**: EC2 인스턴스 생성 및 System Manager 로그인 가능
- [ ] **네트워크 구성**: OMA_VPC에서 소스DB VPC에 접속 가능한 네트워크 구성 (VPC Peering, Route table, Security Group 조정)

### **데이터베이스 연결 확인**
- [ ] **Oracle 연결**: OMABox에서 sqlplus를 사용하여 소스DB (Oracle) 접속 확인
- [ ] **타겟 DB 연결**: OMABox에서 psql(PostgreSQL) 또는 mysql(MySQL)을 이용하여 타겟DB (Aurora) <target_database_name> 접속 확인

### **DMS 구성 확인**
- [ ] **DMS Schema Conversion 프로젝트**: Launch 완료
- [ ] **DMS Endpoint 연결**: Replication Instance에서 소스/타겟 endpoint connection 확인

## 환경 변수 의존성

### **필수 환경변수**
- **AWS 설정**: `AWS_REGION`, `AWS_PROFILE`
- **프로젝트 설정**: `APPLICATION_NAME`, `OMA_HOME`
- **데이터베이스**: `ORACLE_HOME`, `PGHOST`, `PGUSER`

### **선택적 환경변수**
- **로깅**: `LOG_LEVEL`, `VERBOSE_MODE`
- **성능 튜닝**: `BATCH_SIZE`, `PARALLEL_JOBS`

## 다음 단계
인프라 구성이 완료되면 다음 단계들을 진행할 수 있습니다:
- **0-1. 환경 설정 수행**: 프로젝트별 환경 변수 설정
- **0-2. 환경 설정 확인**: 설정된 환경 변수 검증
- **1-1. 애플리케이션 분석**: Java 소스 코드 및 MyBatis 분석
- **1-2. 애플리케이션 리포팅**: 분석 결과 리포트 생성

## 주요 특징
- **완전 자동화**: CloudFormation을 통한 인프라 자동 구성
- **보안 강화**: Private Subnet 배치 및 VPC Endpoint 활용
- **확장성**: Multi-AZ 구성으로 고가용성 보장
- **암호화**: KMS를 통한 전체 데이터 암호화
- **모니터링**: CloudWatch를 통한 통합 모니터링
- **접근 제어**: IAM Role 기반 세밀한 권한 관리

## 중요 주의사항
⚠️ **Amazon Q Subscription 확보**
- OMA 프로젝트에서 AI 기반 코드 분석 및 변환 기능을 사용하기 위해 Amazon Q Developer Subscription이 필요합니다.
- Amazon Q CLI를 통한 코드 분석, 리팩토링, 데이터베이스 스키마 변환 등의 기능을 활용할 수 있습니다.
- 구독이 없는 경우 일부 AI 기반 기능이 제한될 수 있습니다.

⚠️ **네트워크 구성 확인**
- OMA_VPC와 소스 Oracle DB가 위치한 VPC 간의 네트워크 연결성을 반드시 확인해야 합니다.
- VPC Peering, Transit Gateway, 또는 Direct Connect를 통한 연결 구성이 필요할 수 있습니다.

⚠️ **보안 그룹 설정**
- 소스 Oracle DB의 보안 그룹에서 OMA_VPC의 Private Subnet CIDR 대역을 허용해야 합니다.
- 포트 1521(Oracle), 5432(PostgreSQL), 3306(MySQL)에 대한 접근 권한을 적절히 설정해야 합니다.

⚠️ **Secrets Manager 설정**
- Oracle, PostgreSQL 및 MySQL 데이터베이스 자격증명이 Secrets Manager에 올바르게 저장되어 있는지 확인해야 합니다.
- 자격증명 정보는 JSON 형태로 저장되며, 키 이름이 정확해야 합니다.

⚠️ **DMS 사전 요구사항**
- 소스 Oracle DB에서 Archive Log Mode가 활성화되어 있어야 합니다.
- 적절한 권한을 가진 DMS 전용 사용자가 생성되어 있어야 합니다.
