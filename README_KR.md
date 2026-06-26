# OMA (Oracle Migration Accelerator)

Oracle 데이터베이스를 PostgreSQL/MySQL로 자동 마이그레이션하는 AI 기반 도구입니다.

> 영어 버전: [README.md](README.md)  
> 빠른 시작: [QUICKSTART_KR.md](docs/QUICKSTART_KR.md)

---

## 개요

**OMA (Oracle Migration Accelerator)**는 Oracle 데이터베이스를 PostgreSQL 또는 MySQL로 전환하는 포괄적인 마이그레이션 솔루션입니다.

### 핵심 특징

- ✅ **완전 자동화**: 스키마 변환부터 애플리케이션 코드까지 자동 변환
- ✅ **AI 기반**: Bedrock Claude (Opus 4.7) + Strands Agents SDK 활용
- ✅ **대규모 처리**: AWS DMS로 TB급 데이터 마이그레이션
- ✅ **검증 시스템**: 데이터 무결성 및 SQL 정합성 자동 검증
- ✅ **프로덕션 레디**: 실제 프로젝트 검증 완료 (688개 테이블, 1.5만+ Row)

---

## 마이그레이션 범위

OMA는 3가지 영역의 마이그레이션을 지원합니다:

### 1. 📊 Schema Migration (스키마 변환)

**Oracle 데이터베이스 스키마를 PostgreSQL/MySQL로 변환합니다.**

```
Oracle DDL → PostgreSQL/MySQL DDL
- Tables (테이블)
- Indexes (인덱스)
- Constraints (제약조건)
- Sequences (시퀀스)
- Data Types (데이터 타입)
```

**주요 기능:**
- DMS Schema Conversion으로 95% 객체 자동 변환
- AI 에이전트가 나머지 5% (실패/미지원 객체) 처리
- NUMBER 타입 최적화 (Oracle PK NUMBER → PostgreSQL NUMERIC)
- Constraint 인식 데이터 로딩 (드롭 → 로드 → 재생성)
- AWS DMS Full Load Task로 대용량 데이터 이동
- 단일 절차적 스크립트 (`main.py`) - 복잡한 오케스트레이션 없음

**자세히 보기:** [schema/README.md](schema/README.md)

---

### 2. 💻 App Migration (애플리케이션 변환)

**MyBatis Mapper XML의 Oracle SQL을 PostgreSQL/MySQL SQL로 변환합니다.**

```
Oracle MyBatis Mapper → PostgreSQL/MySQL MyBatis Mapper
- SQL Syntax (Oracle → PostgreSQL/MySQL)
- Bind Variables (#{param} 추출 및 매핑)
- Test Cases (Validator용 테스트 케이스 자동 생성)
```

**주요 기능:**
- LLM이 SQL을 읽고 이해하고 변환 (정규식 사용 안 함)
- Oracle Dictionary 기반 테이블/컬럼 매핑
- 바인드 변수 자동 추출 및 데이터 타입 매핑
- Validator로 변환된 SQL 실제 DB 검증
- Extension 시스템 (프레임워크 변수 지원)

**자세히 보기:** [app/README_KR.md](app/README_KR.md)

---

### 3. 🛠️ Infrastructure (인프라 배포)

**AWS 인프라를 CloudFormation으로 자동 배포합니다.**

```
CloudFormation Templates
- Oracle RDS (Source)
- PostgreSQL/MySQL RDS (Target)
- DMS Replication Instance
- DMS Endpoints (Source/Target)
- Networking (VPC, Subnet, Security Groups)
```

**주요 기능:**
- 단일 명령어로 전체 인프라 배포
- oma.properties로 통합 환경 설정
- 멀티 환경 지원 (dev/stg/prod)

**자세히 보기:** [env/README_KR.md](env/README_KR.md)

---

## 프로젝트 구조

```
oma/
├── schema/                    # Schema Migration (스키마 변환)
│   ├── main.py                # 메인 파이프라인 스크립트
│   ├── tools/
│   │   ├── dms_sc.py              # DMS Schema Conversion
│   │   ├── conversion_agent.py    # AI 에이전트 (실패 객체)
│   │   ├── number_type_optimizer.py  # NUMBER→NUMERIC 수정
│   │   ├── constraint_manager.py  # Constraint 드롭/재생성
│   │   └── dms_load.py           # DMS Full Load
│   └── README.md
│
├── app/                       # App Migration (애플리케이션 변환)
│   ├── tools/
│   │   ├── convert_sql.py     # SQL 변환 (LLM 기반)
│   │   ├── validator.py       # SQL 검증 (실제 DB)
│   │   ├── extract_dict.py    # Oracle Dictionary 추출
│   │   └── load_oma_env.sh    # 환경 로더
│   ├── skills/                # Claude Code 스킬
│   │   ├── convert            # 변환 스킬
│   │   ├── validate           # 검증 스킬
│   │   ├── scan-extension     # Extension 스캔
│   │   └── scan-ognl          # OGNL 스캔
│   ├── mappers/               # 변환 작업 폴더 (자동 생성)
│   ├── output/                # 출력 폴더
│   │   ├── oracle_dictionary.json         # Oracle 스키마 정보
│   │   ├── conversion-report.json         # 변환 리포트
│   │   ├── validation-report.json         # 검증 리포트
│   │   └── validation-performance.json    # 성능 비교
│   └── README_KR.md
│
├── env/                       # Infrastructure (인프라 배포)
│   ├── oma.properties         # 통합 환경 설정 (단일 진실 공급원)
│   ├── setEnv.sh              # 환경 변수 로더
│   ├── deploy-omabox.sh       # CloudFormation 배포
│   ├── *.yaml                 # CloudFormation 템플릿
│   └── README_KR.md
│
├── README_KR.md               # 이 파일
├── README.md                  # 영문 버전
└── docs/
    └── QUICKSTART_KR.md       # 빠른 시작 가이드
```

---

## 마이그레이션 워크플로우

OMA 마이그레이션은 3단계로 진행됩니다:

```
┌─────────────────────────────────────────────────────────────┐
│                     OMA Migration Flow                      │
└─────────────────────────────────────────────────────────────┘

Step 1: Infrastructure Setup (env/)
  │
  ├─→ CloudFormation으로 AWS 인프라 배포
  │    - Oracle RDS (Source)
  │    - PostgreSQL/MySQL RDS (Target)
  │    - DMS Replication Instance
  │    - DMS Endpoints
  │
  └─→ oma.properties 환경 설정
       - 데이터베이스 연결 정보
       - Bedrock LLM 설정
       - DMS 설정

       ↓

Step 2: Schema Migration (schema/)
  │
  ├─→ Step 1: DMS Schema Conversion (95% 자동)
  │    - DMS SC 프로젝트 실행
  │    - 변환된 DDL 다운로드 및 적용
  │    - AI 에이전트로 실패 객체 변환 (5%)
  │
  ├─→ Step 1.5: NUMBER 타입 최적화
  │    - Oracle PK NUMBER → PostgreSQL NUMERIC 수정
  │    - DMS의 BIGINT 삽입 오류 방지
  │
  ├─→ Step 2: FK Constraint 드롭
  │    - Constraint 정의 저장
  │    - 데이터 로딩을 위한 FK 전부 드롭
  │
  ├─→ Step 3: DMS Full Load (데이터)
  │    - DMS 인프라 자동 탐색
  │    - Full Load Task 생성 및 실행
  │    - 대용량 데이터 병렬 전송
  │
  └─→ Step 4: FK Constraint 재생성
       - 모든 FK Constraint 복원

       ↓

Step 3: Application Migration (app/)
  │
  ├─→ 사전 준비
  │    1. Oracle Dictionary 추출
  │    2. Extension 스캔 (프레임워크 변수)
  │    3. OGNL 스캔 (Java static method calls)
  │
  ├─→ SQL 변환 (LLM 기반)
  │    - MyBatis Mapper XML 파싱
  │    - LLM이 SQL 이해 및 변환
  │    - 바인드 변수 추출 및 매핑
  │    - Test Case 자동 생성
  │    - Extension 변수 치환
  │
  ├─→ SQL 검증 (Validator)
  │    - 원본 SQL 실행 (Oracle)
  │    - 변환 SQL 실행 (PostgreSQL/MySQL)
  │    - 결과 비교 (Row Count, Column Count)
  │    - 성능 비교 (실행 시간)
  │
  └─→ 리포팅
       - 변환 리포트 (파일별 통계)
       - 검증 리포트 (성공/실패)
       - 성능 리포트 (Oracle vs Target)

       ↓

✅ Migration Complete!
```

---

## 기술 스택

### AI & LLM

- **Bedrock Claude Opus 4.7**: 스키마 및 SQL 변환
- **Strands Agents SDK**: 실패 객체 AI 에이전트 변환
- **LLM-based Parsing**: 정규식 대신 LLM이 SQL 구조 이해

### AWS Services

- **Amazon Bedrock**: LLM 호스팅
- **AWS DMS**: 대규모 데이터 마이그레이션
- **Amazon RDS**: Oracle, PostgreSQL, MySQL
- **CloudFormation**: 인프라 as Code
- **AWS Secrets Manager**: 크레덴셜 관리
- **CloudWatch**: 로깅 및 모니터링

### Languages & Frameworks

- **Python 3.11**: 주요 개발 언어
- **MyBatis**: ORM 프레임워크 (변환 대상)
- **Bash**: 스크립트 자동화
- **CloudFormation YAML**: 인프라 정의

### Databases

- **Oracle 19c+**: Source DB
- **PostgreSQL 15+**: Target DB (Primary)
- **MySQL 8.0+**: Target DB (Alternative)

---

## 시작하기

### 사전 요구사항

1. **AWS 계정**
   - Bedrock 접근 권한
   - DMS 사용 권한
   - RDS 생성 권한

2. **환경**
   - EC2 인스턴스 (Amazon Linux 2023 권장)
   - Python 3.11+
   - Oracle Instant Client (Oracle 연결용)

3. **소스 데이터**
   - Oracle 데이터베이스 (접근 가능)
   - MyBatis Mapper XML 파일들

### 빠른 시작

**1. 환경 설정**

```bash
cd /home/ec2-user/workspace/oma/env
vi oma.properties  # 데이터베이스 연결 정보 입력
```

**2. Schema 마이그레이션**

```bash
cd /home/ec2-user/workspace/oma/schema
python3.11 main.py
```

**3. App 마이그레이션**

```bash
cd /home/ec2-user/workspace/oma/app

# Claude Code에서 스킬 실행
/scan-extension    # Extension 스캔
/scan-ognl         # OGNL 스캔
/convert           # SQL 변환
/validate          # SQL 검증
```

**자세한 가이드:** [QUICKSTART_KR.md](docs/QUICKSTART_KR.md)

---

## 주요 개념

### 1. Oracle Dictionary

**Oracle 스키마 메타데이터를 JSON으로 추출한 파일입니다.**

```json
{
  "schema": "WMSON",
  "tables": {
    "TB_USER": {
      "columns": {
        "USER_ID": {
          "data_type": "NUMBER",
          "data_length": 10,
          "nullable": "N",
          "sample_data": "12345"
        }
      }
    }
  }
}
```

**용도:**
- SQL 변환 시 테이블/컬럼 정보 제공
- 바인드 변수 데이터 타입 매핑
- Test Case 생성 시 샘플 데이터 제공

**생성:** `python3.11 tools/extract_dict.py`

---

### 2. Test Case (TC 파일)

**Validator가 사용하는 SQL 테스트 케이스입니다.**

```json
{
  "file": "selectUser.xml",
  "bind_variables": {
    "#{userId}": "TB_USER.USER_ID",
    "#{userName}": "TB_USER.USER_NAME"
  },
  "test_cases": [
    {
      "description": "기본 조회",
      "parameters": {
        "userId": "12345",
        "userName": "홍길동"
      }
    }
  ]
}
```

**용도:**
- 변환된 SQL을 실제 DB에서 검증
- 여러 시나리오 자동 테스트
- Oracle vs Target DB 결과 비교

**생성:** SQL 변환 시 자동 생성

---

### 3. Extension System

**고객 프레임워크의 바인드 변수를 지원하는 시스템입니다.**

```xml
<!-- 원본 TC 파일 (Extension 전) -->
<select id="selectList">
  #{GRIDPAGING_ROWNUMTYPE_TOP}
  SELECT * FROM TB_USER
  WHERE USER_ID = #{userId}
  #{GRIDPAGING_ROWNUMTYPE_BOTTOM}
</select>
```

```json
// Extension 정의
{
  "GRIDPAGING_ROWNUMTYPE_TOP": {
    "grid": "SELECT * FROM (",
    "combo": ""
  },
  "GRIDPAGING_ROWNUMTYPE_BOTTOM": {
    "grid": ") WHERE ROWNUM <= 10",
    "combo": ""
  }
}
```

```xml
<!-- TC 파일 (Extension 적용 후) -->
<select id="selectList">
  SELECT * FROM (
  SELECT * FROM TB_USER
  WHERE USER_ID = #{userId}
  ) WHERE ROWNUM <= 10
</select>
```

**중요:** Extension은 TC 파일에만 적용되며, 타겟 매퍼는 수정하지 않습니다.

---

### 4. OGNL Expression

**MyBatis에서 Java static method를 호출하는 표현식입니다.**

```xml
<if test="@com.example.Util@isNotEmpty(value)">
  AND USER_NAME = #{value}
</if>
```

**OMA 처리:**
- 스캔하여 사용 현황 파악
- 변환은 하지 않음 (고객이 직접 처리)
- 리포트에 사용처 기록

---

### 5. LLM-based SQL Parsing

**정규식 대신 LLM이 SQL을 읽고 이해합니다.**

**왜 LLM을 사용하는가?**

```sql
-- 정규식으로 찾기 어려운 케이스들:

-- 1. Comma-separated tables
SELECT * FROM A, B, C WHERE A.ID = B.ID

-- 2. Nested subqueries
SELECT * FROM (
  SELECT * FROM (
    SELECT * FROM TB_USER
  ) INNER_QUERY
) OUTER_QUERY

-- 3. CTE (Common Table Expression)
WITH TEMP AS (SELECT * FROM TB_USER)
SELECT * FROM TEMP

-- 4. UNION queries
SELECT * FROM TB_USER
UNION
SELECT * FROM TB_ADMIN
```

**LLM 장점:**
- 어떤 복잡한 SQL도 정확히 파싱
- 테이블명, 컬럼명, 바인드 변수 완벽 추출
- 컨텍스트 이해 (서브쿼리 안 테이블도 찾음)

---

## 리포팅

OMA는 각 단계마다 상세한 리포트를 생성합니다.

### Schema Migration Reports

```
schema/results/
├── migration-report.json             # 전체 마이그레이션 리포트
└── conversion_agent.log              # AI 에이전트 변환 로그
```

### App Migration Reports

```
app/output/
├── oracle_dictionary.json            # Oracle 스키마 정보
├── conversion-report.json            # 변환 상세 리포트
│   ├── conversion_summary
│   ├── llm_calls (table_extraction, sql_conversion, json_fix)
│   ├── tables_discovered/matched/not_found
│   ├── bind_variables & test_cases
│   └── file_details (per-file 통계)
├── validation-report.json            # 검증 리포트
│   ├── summary (total/success/failed)
│   ├── failed_queries (실패 상세)
│   └── timing (Oracle vs Target)
└── validation-performance.json       # 성능 비교
    ├── execution_time (Oracle vs Target)
    ├── faster/slower breakdown
    └── performance_summary
```

---

## 고급 기능

### 1. 체크포인트 & 재개

**Schema 마이그레이션을 중단된 지점부터 재개할 수 있습니다.**

```bash
# main.py는 각 단계별 진행 상황을 로깅합니다
# 중단 시 단순히 다시 실행:
cd /home/ec2-user/workspace/oma/schema
python3.11 main.py
```

### 2. 병렬 처리

**App 변환을 병렬로 처리하여 속도를 높입니다.**

```bash
# 4개 워커로 병렬 변환
python3.11 tools/convert_sql.py --parallel 4

# 검증도 병렬 처리
python3.11 tools/validator.py --parallel 4
```

### 3. Fragment 재사용

**MyBatis의 `<sql>` Fragment를 자동으로 인라인합니다.**

```xml
<!-- 원본 -->
<sql id="userColumns">
  USER_ID, USER_NAME, REG_DT
</sql>

<select id="selectUser">
  SELECT <include refid="userColumns"/>
  FROM TB_USER
</select>

<!-- 변환 후 -->
<select id="selectUser">
  SELECT USER_ID, USER_NAME, REG_DT
  FROM tb_user
</select>
```

### 4. DMS Schema Conversion

**main.py에서 DMS SC를 기본으로 사용합니다. oma.properties에서 설정:**

```properties
# oma.properties
DMS_SC_S3_BUCKET=oma-dms-sc-896586841913
DMS_MIGRATION_PROJECT_ARN=arn:aws:dms:...
```

---

## 제약사항

### 1. MyBatis Dynamic SQL

**완전 자동 변환은 어렵습니다. 부분 지원:**

- ✅ `<if>`, `<choose>`, `<when>` → LLM이 이해하고 Test Case 생성
- ⚠️ 복잡한 중첩 조건 → 수동 검토 필요
- ⚠️ OGNL 표현식 → 스캔만, 변환 안 함

### 2. Oracle 전용 기능

**Target DB에 없는 기능은 수동 처리:**

- ❌ PL/SQL (Stored Procedures, Functions, Packages)
- ❌ Oracle Materialized Views
- ❌ Oracle-specific Hints
- ⚠️ CONNECT BY (PostgreSQL: WITH RECURSIVE로 변환 가능)

### 3. 데이터 타입 변환

**일부 데이터 타입은 주의 필요:**

- ⚠️ `DATE` → `TIMESTAMP` (시간 정보 추가됨)
- ⚠️ `NUMBER` → `NUMERIC` (정밀도 확인 필요)
- ⚠️ `VARCHAR2(4000)` → `VARCHAR(4000)` (최대 길이 다를 수 있음)

### 4. Extension 시스템

**고객 프레임워크 변수는 사전 협의 필요:**

- Extension 키워드는 고객과 협의하여 정의
- 타겟 매퍼는 수정하지 않음 (TC 파일만 치환)

---

## 문제 해결

### Schema 마이그레이션 실패

**증상**: "DMS Task failed"

**해결:**
```bash
# DMS Task 로그 확인
aws logs tail /aws/dms/tasks/<task-id> --follow

# Task 통계 확인
aws dms describe-table-statistics --replication-task-arn <arn>
```

### App 변환 실패

**증상**: "Table not found in dictionary"

**해결:**
```bash
# Oracle Dictionary 재생성
cd app
python3.11 tools/extract_dict.py \
  --host $ORACLE_HOST \
  --schema $ORACLE_SCHEMA \
  --output output/oracle_dictionary.json

# 특정 테이블만 추가
python3.11 tools/extract_dict.py --tables TB_USER,TB_ORDER
```

### Validation 실패

**증상**: "Query execution failed"

**해결:**
```bash
# 실패한 파일만 재검증
python3.11 tools/validator.py \
  --failed-only \
  --tc-dir mappers

# 상세 로그 확인
python3.11 tools/validator.py --verbose
```

---

## 성능 최적화

### 1. Schema 마이그레이션

- **DMS Parallel Load**: `MaxFullLoadSubTasks: 8` (기본값)
- **CommitRate**: 10000 rows (조정 가능)
- **Replication Instance**: r5.xlarge 이상 권장

### 2. App 변환

- **병렬 워커**: CPU 코어 수에 맞춰 조정
  ```bash
  # 4-core CPU
  python3.11 tools/convert_sql.py --parallel 3
  
  # 8-core CPU
  python3.11 tools/convert_sql.py --parallel 6
  ```

- **LLM 호출 최소화**: Dictionary 캐싱 활용

### 3. Validation

- **배치 크기**: 한 번에 검증할 파일 수 조정
- **타임아웃**: 복잡한 쿼리는 타임아웃 증가
  ```bash
  python3.11 tools/validator.py --timeout 60
  ```

---

## 보안

### 1. 크레덴셜 관리

**oma.properties에 평문 저장 대신 Secrets Manager 사용 가능:**

```bash
# Secrets Manager에서 자동 로드
export USE_SECRETS_MANAGER=true

# main.py가 자동으로 Secrets Manager에서 읽음
python3.11 main.py
```

### 2. 네트워크 보안

- DMS Replication Instance는 Private Subnet 배포
- Security Group으로 접근 제어
- VPC Peering 또는 Transit Gateway 사용

### 3. 데이터 보안

- DMS는 전송 중 암호화 (TLS)
- RDS는 저장 암호화 (KMS)
- CloudWatch Logs는 로그 그룹 암호화

---

## 참고 자료

### 내부 문서

- [Schema Migration 가이드](schema/README_KR.md)
- [App Migration 가이드](app/README_KR.md)
- [환경 설정 가이드](env/README_KR.md)
- [빠른 시작 가이드](QUICKSTART_KR.md)

### 외부 문서

- [AWS DMS 공식 문서](https://docs.aws.amazon.com/dms/)
- [Bedrock 공식 문서](https://docs.aws.amazon.com/bedrock/)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [MyBatis 공식 문서](https://mybatis.org/mybatis-3/)

---

## 라이선스

이 프로젝트는 내부 사용 전용입니다.

---

## 지원

문제가 발생하면 다음을 확인하세요:

1. **로그 파일**: 각 도구의 상세 로그 확인
2. **리포트 파일**: 실패 원인 분석
3. **환경 설정**: oma.properties 검증
4. **AWS 상태**: DMS, RDS, Bedrock 서비스 상태

---

**작성일**: 2026-06-23  
**OMA Version**: 2.0  
**지원 대상 DB**: Oracle 19c+ → PostgreSQL 15+, MySQL 8.0+
