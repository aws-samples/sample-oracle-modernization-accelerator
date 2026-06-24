# OMA Schema Conversion

Oracle 데이터베이스 스키마를 PostgreSQL/MySQL로 자동 변환합니다.

> 영어 버전: [README.md](README.md)

## 개요

`schema` 폴더는 Oracle 데이터베이스 스키마(테이블, 인덱스, 제약조건, 시퀀스 등)를 PostgreSQL/MySQL로 자동 변환하고 데이터를 마이그레이션하는 도구를 제공합니다.

### 주요 기능

- **스키마 자동 변환**: Oracle DDL → PostgreSQL/MySQL DDL 자동 생성
- **AI 기반 변환**: Strands Agents SDK + Bedrock Claude 사용
- **DMS 데이터 마이그레이션**: AWS DMS Full Load Task로 대용량 데이터 이동
- **데이터 무결성 검증**: Oracle vs Target DB 데이터 비교
- **체크포인트 & 재개**: 중단된 작업 이어서 실행 가능

---

## 폴더 구조

```
schema/
├── postgresql/
│   ├── scripts/
│   │   └── run_migration.py     # PostgreSQL 마이그레이션 메인 스크립트
│   ├── agents/                  # Strands Agents (스키마 분석, 변환, 검증)
│   ├── tools/                   # PostgreSQL 도구
│   └── rules/                   # 변환 규칙
├── mysql/
│   ├── scripts/
│   │   └── run_migration.py     # MySQL 마이그레이션 메인 스크립트
│   ├── agents/                  # Strands Agents
│   ├── tools/                   # MySQL 도구
│   └── rules/                   # 변환 규칙
├── common/
│   ├── orchestrator/            # 파이프라인 오케스트레이션
│   ├── tools/
│   │   ├── oracle_tools.py      # Oracle 연결/쿼리
│   │   ├── dms_sc_tools.py      # DMS Schema Conversion
│   │   ├── dms_full_load_tools.py  # DMS 데이터 마이그레이션
│   │   └── analysis_tools.py    # 스키마 분석
│   └── rules/                   # 공통 변환 규칙
├── tools/
│   └── extract_sequence_usage.py  # 시퀀스 사용처 추출
├── migration-config.json        # 마이그레이션 설정 (자동 생성)
└── results/                     # 마이그레이션 결과물
```

---

## 사전 준비

### 1. 환경 설정

`/home/ec2-user/workspace/oma/env/oma.properties`에서 환경 변수 설정:

```properties
[COMMON]
# Oracle Connection
ORACLE_HOST=10.0.X.X
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_CONN_TYPE=service
ORACLE_USER=username
ORACLE_PASSWORD=password
ORACLE_SCHEMA=SCHEMA_NAME
ORACLE_HOME=/home/ec2-user/oracle

# PostgreSQL Connection (Standard Variables)
PGHOST=cluster.xxxxx.region.rds.amazonaws.com
PGPORT=5432
PGDATABASE=dbname
PGSCHEMA=schema_name
PGUSER=username
PGPASSWORD=password

# MySQL Connection
MYSQL_HOST=cluster.xxxxx.region.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_DATABASE=dbname
MYSQL_USER=username
MYSQL_PASSWORD=password

# Bedrock LLM
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7

# Target DB Type
TARGET_DB_TYPE=postgres
```

> 📝 **참고**: 자세한 환경 설정은 [env/README_KR.md](../env/README_KR.md) 참고

### 2. DMS 인프라 준비 (선택사항)

**데이터 마이그레이션을 위해 DMS가 필요합니다:**

1. **DMS Replication Instance** 생성
2. **DMS Source Endpoint** (Oracle)
3. **DMS Target Endpoint** (PostgreSQL/MySQL)

> 📝 **자동 탐지**: 환경 변수에 없으면 자동으로 AWS에서 탐지

---

## 마이그레이션 프로세스

### 실행 방법

```bash
# PostgreSQL로 마이그레이션
cd /home/ec2-user/workspace/oma/schema/postgresql/scripts
python3.11 run_migration.py

# MySQL로 마이그레이션
cd /home/ec2-user/workspace/oma/schema/mysql/scripts
python3.11 run_migration.py
```

### 4단계 파이프라인

```
Phase 1: Schema Migration (AI 기반 DDL 변환)
   ↓
Phase 2: Data Migration (DMS Full Load Task)
   ↓
Phase 3: Data Integrity Verification
   ↓
Phase 4: Report Generation
```

---

### Phase 1: Schema Migration (스키마 변환)

**Oracle 스키마를 PostgreSQL/MySQL DDL로 자동 변환합니다.**

#### 작동 방식:

**1. Strands Agents SDK Graph 파이프라인**
- AI 에이전트들이 협업하여 스키마 변환 수행
- Bedrock Claude (Opus 4.7) 사용
- 각 에이전트가 특정 역할 담당

**2. 주요 에이전트:**

| 에이전트 | 역할 |
|---------|------|
| **Discovery** | Oracle 스키마 탐색 (테이블, 인덱스, 제약조건, 시퀀스) |
| **Schema Architect** | DDL 변환 전략 수립 |
| **Code Migrator** | Oracle DDL → Target DDL 변환 |
| **QA Verifier** | 변환된 DDL 검증 |
| **Evaluator** | 전체 품질 평가 |

**3. 변환 항목:**

```sql
-- Tables (테이블)
Oracle: CREATE TABLE TB_USER (USER_ID NUMBER(10), ...)
→ PostgreSQL: CREATE TABLE tb_user (user_id INTEGER, ...)

-- Indexes (인덱스)
Oracle: CREATE INDEX IDX_USER_NAME ON TB_USER(USER_NAME)
→ PostgreSQL: CREATE INDEX idx_user_name ON tb_user(user_name)

-- Primary Keys (기본키)
Oracle: CONSTRAINT PK_USER PRIMARY KEY (USER_ID)
→ PostgreSQL: CONSTRAINT pk_user PRIMARY KEY (user_id)

-- Foreign Keys (외래키)
Oracle: CONSTRAINT FK_ORDER_USER FOREIGN KEY (USER_ID) REFERENCES TB_USER(USER_ID)
→ PostgreSQL: CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES tb_user(user_id)

-- Sequences (시퀀스)
Oracle: CREATE SEQUENCE SEQ_USER START WITH 1
→ PostgreSQL: CREATE SEQUENCE seq_user START WITH 1

-- Data Types (데이터 타입)
Oracle: NUMBER(10,2) → PostgreSQL: NUMERIC(10,2)
Oracle: VARCHAR2(100) → PostgreSQL: VARCHAR(100)
Oracle: DATE → PostgreSQL: TIMESTAMP
Oracle: CLOB → PostgreSQL: TEXT
Oracle: BLOB → PostgreSQL: BYTEA
```

**4. 출력:**

```
results/
├── ddl_output.sql              # 변환된 DDL
├── migration-report.json       # 변환 상세 리포트
└── checkpoints/                # 체크포인트 (재개용)
    └── {migration_id}/
```

**5. 실행 로그 예시:**

```
[INFO] PHASE 1: Schema Migration Pipeline
[INFO] Discovering Oracle schema: WMSON
[INFO] Found 688 tables, 2450 indexes, 1230 constraints
[INFO] Agent 'Schema Architect': Planning conversion strategy
[INFO] Agent 'Code Migrator': Converting DDL (batch 1/10)
[INFO] Agent 'QA Verifier': Validating converted DDL
[INFO] Schema status: COMPLETED (245.3s)
```

---

### Phase 2: Data Migration (데이터 마이그레이션)

**AWS DMS Full Load Task로 대용량 데이터를 마이그레이션합니다.**

#### 작동 방식:

**1. DMS 인프라 자동 탐지**
```python
# 환경 변수에서 읽거나, 없으면 AWS API로 자동 탐지
- DMS Replication Instance
- Source Endpoint (Oracle)
- Target Endpoint (PostgreSQL/MySQL)
```

**2. DMS Full Load Task 생성**
```python
# Table Mappings 설정
{
  "rules": [
    {
      "rule-type": "selection",
      "schema-name": "WMSON",
      "table-name": "%"
    },
    {
      "rule-type": "transformation",
      "rule-action": "convert-lowercase"  # 소문자 변환
    }
  ]
}

# Task Settings
{
  "TargetMetadata": {
    "TargetTablePrepMode": "TRUNCATE_BEFORE_LOAD"  # 기존 데이터 삭제
  },
  "FullLoadSettings": {
    "MaxFullLoadSubTasks": 8,  # 병렬 처리
    "CommitRate": 10000
  }
}
```

**3. Task 실행 및 모니터링**
```
→ Task 생성: oma-full-load-wmson-1234567890
→ Task 시작
→ 진행 상황 모니터링 (30초마다 체크)
  - 진행률: 45%
  - 완료된 테이블: 310/688
  - 로드된 Row: 15,234,567
→ 완료 대기 (최대 8시간)
```

**4. 장점:**

✅ **AWS 관리형 서비스**
- 터미널 종료해도 백그라운드 실행
- CloudWatch에서 모니터링 가능
- 병렬 처리로 빠른 속도

✅ **대용량 데이터 처리**
- 수백 GB ~ TB 급 데이터 처리 가능
- 자동 재시도 및 에러 핸들링

✅ **데이터 무결성**
- TRUNCATE_BEFORE_LOAD로 깨끗한 로드
- 트랜잭션 일관성 보장

**5. 실행 로그 예시:**

```
[INFO] PHASE 2: Data Migration via DMS Full Load Task
[INFO] Discovering DMS infrastructure...
[INFO] Found DMS instance: oma-replication-instance
[INFO] Found source endpoint: oracle-wmson
[INFO] Found target endpoint: postgres-wmson
[INFO] Creating DMS Full Load task for schema: WMSON
[INFO] DMS task created: oma-full-load-wmson-1719876543
[INFO] Starting DMS Full Load task...
[INFO] DMS task started. Waiting for completion...
[INFO] DMS task progress: 25% (status=running, tables=172, rows=3,456,789)
[INFO] DMS task progress: 50% (status=running, tables=344, rows=7,891,234)
[INFO] DMS task progress: 75% (status=running, tables=516, rows=12,345,678)
[INFO] DMS task progress: 100% (status=stopped, tables=688, rows=15,234,567)
[INFO] Data migration completed in 1834.2s
[INFO] Statistics: {
  "total_tables": 688,
  "full_load_completed": 688,
  "full_load_rows": 15234567,
  "inserts": 15234567
}
```

---

### Phase 3: Data Integrity Verification (데이터 무결성 검증)

**Oracle과 Target DB의 데이터를 비교하여 무결성을 검증합니다.**

#### 검증 항목:

**1. Row Count 비교**
```sql
-- Oracle
SELECT COUNT(*) FROM WMSON.TB_USER;
-- Result: 150,234

-- PostgreSQL
SELECT COUNT(*) FROM wmson.tb_user;
-- Result: 150,234

✓ Row count matches
```

**2. Sample Data 비교**
```sql
-- Oracle
SELECT * FROM WMSON.TB_USER WHERE ROWNUM <= 10;

-- PostgreSQL
SELECT * FROM wmson.tb_user LIMIT 10;

-- 데이터 값 비교 (컬럼별)
✓ USER_ID matches
✓ USER_NAME matches
✓ REG_DT matches
```

**3. 검증 리포트**
```json
{
  "total_tables": 688,
  "verified_tables": 688,
  "mismatches": 0,
  "tables": [
    {
      "table": "tb_user",
      "oracle_count": 150234,
      "postgres_count": 150234,
      "status": "MATCH"
    },
    {
      "table": "tb_order",
      "oracle_count": 523456,
      "postgres_count": 523456,
      "status": "MATCH"
    }
  ]
}
```

**4. 실행 로그 예시:**

```
[INFO] PHASE 3: Data Integrity Verification (Oracle vs PG)
[INFO] Verifying data integrity for schema: wmson
[INFO] Comparing row counts for 688 tables...
[INFO] Progress: 100/688 tables verified
[INFO] Progress: 200/688 tables verified
[INFO] Progress: 688/688 tables verified
[INFO] Verification completed: 688 matches, 0 mismatches
[INFO] All tables verified successfully!
```

---

### Phase 4: Report Generation (리포트 생성)

**전체 마이그레이션 결과를 종합한 리포트를 생성합니다.**

#### 리포트 내용:

```json
{
  "migration_summary": {
    "migration_id": "oma-migration-1719876543",
    "source_schema": "WMSON",
    "target_schema": "wmson",
    "target_db_type": "postgres",
    "start_time": "2026-06-23T10:00:00",
    "end_time": "2026-06-23T11:30:45",
    "total_duration_seconds": 5445
  },
  
  "phase1_schema": {
    "status": "COMPLETED",
    "duration_seconds": 245,
    "tables_converted": 688,
    "indexes_converted": 2450,
    "constraints_converted": 1230,
    "sequences_converted": 45,
    "output_file": "results/ddl_output.sql"
  },
  
  "phase2_data": {
    "status": "COMPLETED",
    "duration_seconds": 1834,
    "dms_task_arn": "arn:aws:dms:...",
    "tables_loaded": 688,
    "total_rows": 15234567,
    "full_load_completed": 688
  },
  
  "phase3_verification": {
    "status": "COMPLETED",
    "duration_seconds": 3366,
    "total_tables": 688,
    "verified_tables": 688,
    "mismatches": 0,
    "all_verified": true
  },
  
  "recommendations": [
    "✓ Schema conversion completed successfully",
    "✓ All 688 tables migrated (15.2M rows)",
    "✓ Data integrity verified - no mismatches",
    "→ Ready for application migration (App Conversion)"
  ]
}
```

---

## 체크포인트 & 재개

**중단된 마이그레이션을 이어서 실행할 수 있습니다.**

### 체크포인트 저장 시점:

1. ✅ Phase 1 완료 시
2. ✅ Phase 2 완료 시
3. ✅ Phase 2 실패 시
4. ✅ Phase 3 완료 시

### 재개 방법:

```bash
# 1. 중단된 migration_id 확인
ls results/checkpoints/

# 2. migration_id로 재개
python3.11 run_migration.py --resume oma-migration-1719876543

# 재개 시 동작:
# - 완료된 Phase는 건너뜀
# - 실패한 Phase부터 재실행
# - 동일한 migration_id 유지
```

**재개 로그 예시:**

```
[INFO] Resuming migration: oma-migration-1719876543
[INFO] Phase 1: COMPLETED - Skipping
[INFO] Phase 2: FAILED - Restarting
[INFO] PHASE 2: Data Migration via DMS Full Load Task
[INFO] Creating new DMS task...
```

---

## 출력 파일

### 1. DDL 출력

```sql
-- results/ddl_output.sql

-- Tables
CREATE TABLE wmson.tb_user (
    user_id INTEGER NOT NULL,
    user_name VARCHAR(50),
    reg_dt TIMESTAMP NOT NULL,
    CONSTRAINT pk_user PRIMARY KEY (user_id)
);

-- Indexes
CREATE INDEX idx_user_name ON wmson.tb_user(user_name);

-- Sequences
CREATE SEQUENCE wmson.seq_user START WITH 1 INCREMENT BY 1;

-- Foreign Keys
ALTER TABLE wmson.tb_order
ADD CONSTRAINT fk_order_user
FOREIGN KEY (user_id) REFERENCES wmson.tb_user(user_id);
```

### 2. 마이그레이션 리포트

```
results/
├── ddl_output.sql                     # 변환된 DDL
├── migration-report.json              # 전체 마이그레이션 리포트
├── schema-conversion-report.json      # Phase 1 상세 리포트
├── data-migration-report.json         # Phase 2 상세 리포트
├── verification-report.json           # Phase 3 검증 리포트
└── checkpoints/                       # 체크포인트
    └── oma-migration-1719876543/
        ├── schema_completed.json
        ├── data_completed.json
        └── verify_completed.json
```

---

## 고급 기능

### 1. DMS Schema Conversion 사용 (선택사항)

**AWS DMS Schema Conversion (DMS SC)을 사용할 수도 있습니다:**

```properties
# oma.properties에 설정 추가
DMS_SC_S3_BUCKET=oma-dms-sc-896586841913
DMS_MIGRATION_PROJECT_ARN=arn:aws:dms:ap-northeast-2:896586841913:migration-project:XXX
```

**장점:**
- AWS 관리형 스키마 변환
- 복잡한 PL/SQL 변환 지원
- 변환 평가 리포트 제공

**Phase 1에서 자동으로 DMS SC 사용:**
```python
# DMS SC 설정이 있으면 자동으로 사용
if os.environ.get("DMS_SC_S3_BUCKET"):
    use_dms_sc_conversion()
else:
    use_ai_agent_conversion()
```

### 2. 부분 마이그레이션

**특정 Phase만 실행:**

```bash
# Phase 2만 실행 (데이터 마이그레이션만)
python3.11 run_data_migration_only.py

# Phase 3만 실행 (검증만)
python3.11 run_migration.py --resume <id> --skip-phase1 --skip-phase2
```

### 3. 시퀀스 사용처 추출

**Oracle 시퀀스가 어디서 사용되는지 찾기:**

```bash
cd /home/ec2-user/workspace/oma/schema/tools
python3.11 extract_sequence_usage.py --schema WMSON

# 출력: sequence-usage-report.json
{
  "SEQ_USER": {
    "tables": ["TB_USER"],
    "trigger": "TRG_USER_ID",
    "current_value": 150234
  }
}
```

---

## 문제 해결

### DMS Task 생성 실패

**증상**: "Failed to create DMS task"

**해결:**
```bash
# 1. DMS 인프라 확인
aws dms describe-replication-instances
aws dms describe-endpoints

# 2. Source/Target Endpoint 테스트
aws dms test-connection \
  --replication-instance-arn <arn> \
  --endpoint-arn <endpoint-arn>

# 3. 권한 확인 (IAM Role)
# DMS가 S3, CloudWatch 접근 권한 필요
```

### 데이터 검증 실패

**증상**: "Mismatch found: tb_user (Oracle: 150234, PG: 150230)"

**해결:**
```bash
# 1. DMS Task 상태 확인
aws dms describe-table-statistics \
  --replication-task-arn <task-arn>

# 2. 에러 로그 확인 (CloudWatch)
# Log Group: /aws/dms/tasks/<task-id>

# 3. 수동으로 Row Count 비교
sqlplus user/pass@oracle
SELECT COUNT(*) FROM WMSON.TB_USER;

psql -h host -d dbname
SELECT COUNT(*) FROM wmson.tb_user;
```

### 체크포인트 재개 실패

**증상**: "Checkpoint not found"

**해결:**
```bash
# 1. 체크포인트 디렉토리 확인
ls -la results/checkpoints/

# 2. migration-config.json 확인
cat migration-config.json

# 3. 새로 시작 (--resume 없이)
python3.11 run_migration.py
```

---

## 참고

- **환경 설정**: [env/README_KR.md](../env/README_KR.md)
- **App 변환**: [app/README_KR.md](../app/README_KR.md)
- **AWS DMS 문서**: https://docs.aws.amazon.com/dms/

---

**작성일**: 2026-06-23  
**OMA Version**: 2.0
