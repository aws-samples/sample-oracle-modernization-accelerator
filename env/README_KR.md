# OMA Environment Configuration

OMA 프로젝트의 통합 환경 설정을 관리합니다.

## 개요

`env` 폴더는 OMA의 모든 컴포넌트(Schema 변환, App 변환, CloudFormation 배포)가 공통으로 사용하는 환경 설정을 제공합니다.

### 주요 파일

| 파일 | 용도 |
|------|------|
| `oma.properties` | **통합 환경 설정 파일** (단일 진실 공급원) |
| `setEnv.sh` | CloudFormation 배포용 환경 변수 로더 |
| `deploy-omabox.sh` | CloudFormation 스택 배포 스크립트 |
| `*.yaml` | CloudFormation 템플릿 파일들 |

---

## oma.properties

OMA 프로젝트의 **단일 환경 설정 파일**입니다.

### 구조

```properties
[COMMON]
# 모든 도구(env/schema/app)가 공통으로 사용하는 변수

[your application name]
# CloudFormation 배포 전용 변수
```

### [COMMON] 섹션

Schema 변환, App 변환, env 도구가 모두 읽는 공통 변수입니다.

#### 1. 기본 설정

```properties
OMA_BASE_DIR=/home/ec2-user/workspace/oma
LANGUAGE=en
AWS_REGION=ap-northeast-2
```

#### 2. Bedrock LLM 설정

```properties
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7
```

> **지원 모델**: opus-4-8, opus-4-7, opus-4-6, sonnet-4-6, haiku-4-5

#### 3. App 변환 설정

```properties
MAX_WORKERS=7
ORACLE_HOME=/home/ec2-user/oracle
SOURCE_WORKSPACE=/home/ec2-user/workspace/source
TARGET_WORKSPACE=/home/ec2-user/workspace/target
ORACLE_DICT_PATH=${OMA_BASE_DIR}/app/output/oracle_dictionary.json
MAPPER_WORK_DIR=${OMA_BASE_DIR}/app/mappers
```

#### 4. Oracle 연결 정보

```properties
ORACLE_HOST=10.0.X.X
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_CONN_TYPE=service
ORACLE_USER=username
ORACLE_PASSWORD=password
ORACLE_SCHEMA=SCHEMA_NAME
```

#### 5. PostgreSQL 연결 정보 (표준 변수명)

```properties
# PostgreSQL 표준 환경 변수 (psql 자동 인식)
PGHOST=your-cluster.cluster-xxxxx.region.rds.amazonaws.com
PGPORT=5432
PGDATABASE=dbname
PGSCHEMA=schema_name
PGUSER=username
PGPASSWORD=password
```

> **중요**: PostgreSQL은 `PGHOST`, `PGPORT` 등 **표준 변수명**을 사용합니다 (underscores 없음).

#### 6. MySQL 연결 정보

```properties
MYSQL_HOST=your-cluster.cluster-xxxxx.region.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_DATABASE=dbname
MYSQL_USER=username
MYSQL_PASSWORD=password
```

#### 7. Target DB 타입

```properties
# postgres 또는 mysql
TARGET_DB_TYPE=postgres
```

#### 8. DMS Schema Conversion 설정 (선택)

```properties
DMS_SC_S3_BUCKET=oma-dms-sc-YOUR_ACCOUNT_ID
DMS_MIGRATION_PROJECT_ARN=arn:aws:dms:region:account:migration-project:project-id
```

### [APPLICATION_NAME] 섹션

CloudFormation 배포 전용 변수입니다.

```properties
[your application name]
APPLICATION_NAME=${your application name}
```

---

## 환경 변수 표준

OMA는 각 데이터베이스의 표준 환경 변수명을 따릅니다.

### PostgreSQL 표준

| 변수 | 설명 | psql 자동 인식 |
|------|------|----------------|
| `PGHOST` | 호스트 | ✅ |
| `PGPORT` | 포트 | ✅ |
| `PGDATABASE` | 데이터베이스명 | ✅ |
| `PGUSER` | 사용자명 | ✅ |
| `PGPASSWORD` | 비밀번호 | ✅ |
| `PGSCHEMA` | 스키마명 | ❌ |

**장점**: `psql` 명령어가 자동으로 연결 정보를 인식합니다.

```bash
# oma.properties 로드 후
psql -c "SELECT version();"  # 별도 -h, -p, -U 옵션 불필요!
```

### MySQL 표준

| 변수 | 설명 |
|------|------|
| `MYSQL_HOST` | 호스트 |
| `MYSQL_PORT` | 포트 |
| `MYSQL_DATABASE` | 데이터베이스명 |
| `MYSQL_USER` | 사용자명 |
| `MYSQL_PASSWORD` | 비밀번호 |

### Oracle 표준

| 변수 | 설명 |
|------|------|
| `ORACLE_HOST` | 호스트 |
| `ORACLE_PORT` | 포트 |
| `ORACLE_SID` | SID 또는 Service Name |
| `ORACLE_USER` | 사용자명 |
| `ORACLE_PASSWORD` | 비밀번호 |
| `ORACLE_SCHEMA` | 스키마명 |
| `ORACLE_HOME` | Oracle Client 설치 경로 |

---

## 사용 방법

### Schema 변환

Schema 변환 프로그램이 자동으로 `oma.properties`를 읽습니다.

```bash
cd /home/ec2-user/workspace/oma/schema/postgresql/scripts
python3.11 run_migration.py

# 내부에서 자동으로:
# 1. oma.properties [COMMON] 섹션 로드
# 2. Secrets Manager fallback (optional)
# 3. 환경 변수로 export
```

### App 변환

App 변환 스킬이 자동으로 `oma.properties`를 읽습니다.

```bash
cd /home/ec2-user/workspace/oma/app
bash .claude/skills/convert-sql.sh <mapper-file>

# 내부에서 자동으로:
# 1. tools/load_oma_env.sh 호출
# 2. oma.properties [COMMON] 섹션 파싱
# 3. 환경 변수로 export
```

**모든 스킬이 동일한 방식으로 동작합니다:**
- `build-oracle-dict.sh`
- `convert-sql.sh`
- `merge-mappers.sh`
- `scan-extension.sh`
- `split-mappers.sh`
- `run-validator.sh`
- `verify-env.sh`

### CloudFormation 배포

```bash
cd /home/ec2-user/workspace/oma/env

# 1. Secrets Manager에 크레덴셜 생성
bash deploy-omabox.sh -o 1

# 2. CloudFormation 스택 배포
bash deploy-omabox.sh -o 2

# setEnv.sh가 자동으로:
# 1. oma.properties 읽기
# 2. [APPLICATION_NAME] 섹션 포함
# 3. 환경 변수 파일 생성
```

---

## 환경 변수 우선순위

### Schema 변환

```
1. oma.properties [COMMON] (최우선)
2. Secrets Manager (fallback)
3. Default values
```

### App 변환

```
1. oma.properties [COMMON] (단일 소스)
2. Default values
```

### CloudFormation 배포

```
1. oma.properties [COMMON] + [APPLICATION_NAME]
2. Default values
```

---

## 설정 파일 수정

### 데이터베이스 연결 정보 변경

```bash
vi oma.properties

# Oracle 정보 수정
ORACLE_HOST=10.0.X.X
ORACLE_USER=new_user
ORACLE_PASSWORD=new_password

# PostgreSQL 정보 수정
PGHOST=new-cluster.cluster-xxxxx.region.rds.amazonaws.com
PGUSER=new_user
PGPASSWORD=new_password
```

**별도 재시작 불필요**: 다음 실행 시 자동 반영됩니다.

### Bedrock 모델 변경

```bash
vi oma.properties

# Opus 4.7 → Opus 4.8
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-8
```

---

## 검증

### 환경 변수 로딩 테스트

```bash
# App 스킬 테스트
cd /home/ec2-user/workspace/oma/app
bash .claude/skills/verify-env.sh

# 출력:
# ✓ ORACLE_HOST=10.0.X.X
# ✓ PGHOST=your-cluster...
# ✓ BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7
```

### 데이터베이스 연결 테스트

```bash
# PostgreSQL (표준 변수 자동 인식)
source <(grep -v '^\[' oma.properties | grep -v '^#' | grep '=')
psql -c "SELECT version();"

# Oracle
sqlplus ${ORACLE_USER}/${ORACLE_PASSWORD}@//${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}
```

---

## 변수 확장

`oma.properties`는 변수 확장을 지원합니다.

```properties
OMA_BASE_DIR=/home/ec2-user/workspace/oma
ORACLE_DICT_PATH=${OMA_BASE_DIR}/app/output/oracle_dictionary.json
MAPPER_WORK_DIR=${OMA_BASE_DIR}/app/mappers
```

**확장 시점**: 각 도구가 파일을 읽을 때 자동으로 확장됩니다.

---

## 보안

### 민감 정보 관리

**Option 1: oma.properties에 직접 저장 (개발 환경)**
- 간단하지만 Git에 커밋하지 않도록 주의

**Option 2: Secrets Manager 사용 (운영 환경 권장)**

```bash
# Oracle 크레덴셜
aws secretsmanager create-secret \
  --name oma-secret-oracle-service \
  --secret-string '{
    "host": "10.0.X.X",
    "port": 1521,
    "username": "user",
    "password": "pass",
    "sid": "ORCLPDB1"
  }'

# PostgreSQL 크레덴셜
aws secretsmanager create-secret \
  --name oma-secret-postgres-service \
  --secret-string '{
    "host": "cluster.xxxxx.region.rds.amazonaws.com",
    "port": 5432,
    "username": "user",
    "password": "pass",
    "database": "dbname"
  }'
```

**자동 Fallback**: 
- oma.properties에 없는 변수는 Secrets Manager에서 자동으로 로드됩니다.

---

## 문제 해결

### 환경 변수가 로드되지 않음

**증상**: 프로그램 실행 시 "Missing credentials" 에러

**해결**:
```bash
# 1. oma.properties 경로 확인
ls -la /home/ec2-user/workspace/oma/env/oma.properties

# 2. 파일 형식 확인 (섹션 헤더, key=value)
cat oma.properties

# 3. 권한 확인
chmod 644 oma.properties
```

### PostgreSQL 연결 실패

**증상**: `psql: connection refused`

**해결**:
```bash
# 1. 환경 변수 확인
echo $PGHOST
echo $PGPORT

# 2. 네트워크 연결 확인
telnet $PGHOST $PGPORT

# 3. Security Group 확인 (5432 포트 열림?)
```

### Oracle 연결 실패

**증상**: `ORA-12170: TNS:Connect timeout occurred`

**해결**:
```bash
# 1. VPN 연결 확인 (온프레미스 Oracle의 경우)
# 2. Security Group 확인 (1521 포트 열림?)
# 3. ORACLE_HOME 확인
echo $ORACLE_HOME
ls $ORACLE_HOME/bin/sqlplus
```

---

## 참고

- **단일 진실 공급원**: `oma.properties` 하나만 관리
- **표준 준수**: PostgreSQL/MySQL/Oracle 표준 환경 변수 사용
- **자동 Discovery**: Schema 변환 시 DMS 인프라 자동 탐지
- **Secrets Manager 통합**: 민감 정보는 Secrets Manager 사용 가능

---

**작성일**: 2026-06-18  
**OMA Version**: 2.0
