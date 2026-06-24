# OMA 빠른 시작 가이드

Oracle에서 PostgreSQL/MySQL로 30분 안에 마이그레이션을 시작하세요.

> 영어 버전: [QUICKSTART.md](QUICKSTART.md)  
> 전체 문서: [README_KR.md](README_KR.md)

---

## 사전 요구사항

### 1. 환경

- ✅ EC2 인스턴스 (Amazon Linux 2023)
- ✅ Python 3.11+
- ✅ Oracle Instant Client 설치됨
- ✅ AWS 권한 (Bedrock, DMS, RDS)

### 2. 소스 데이터

- ✅ Oracle 데이터베이스 접근 가능
- ✅ MyBatis Mapper XML 파일들

### 3. 예상 소요 시간

| 단계 | 소요 시간 |
|------|----------|
| Step 1: 환경 설정 | 5분 |
| Step 2: Schema 마이그레이션 | 10-60분 (데이터 크기에 따라) |
| Step 3: App 마이그레이션 | 10-30분 (파일 수에 따라) |

---

## Step 1: 인프라 배포 (15-30분)

### 1.1. OMA 다운로드

```bash
cd /home/ec2-user/workspace
git clone <oma-repository> oma
cd oma
```

### 1.2. oma.properties 설정

```bash
cd env
vi oma.properties
```

**최소 설정 항목 (배포 전):**

```properties
[COMMON]
# AWS 설정
AWS_REGION=ap-northeast-2

# Bedrock LLM
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7

# Target DB 타입
TARGET_DB_TYPE=postgres   # 또는 mysql

[your-application-name]
APPLICATION_NAME=${your-application-name}
```

### 1.3. AWS 인프라 배포

**CloudFormation으로 전체 인프라를 자동 배포합니다:**
- Oracle RDS (Source)
- PostgreSQL Aurora 또는 MySQL Aurora (Target)
- DMS Replication Instance
- DMS Endpoints (Source/Target)
- VPC, Subnet, Security Groups

#### 1.3.1. Secrets Manager 설정 (Option 1)

```bash
bash deploy-omabox.sh -o 1
```

**프롬프트에 응답:**
```
1. Oracle Admin Credentials:
Enter Oracle Admin Username: admin
Enter Oracle Admin Password: ********
Enter Oracle Host (e.g., oracle.example.com): your-oracle-host
Enter Oracle Port [1521]: 1521
Enter Oracle SID/Service Name: ORCLPDB1

2. Oracle Service Credentials:
Enter Oracle Service Username: app_user
Enter Oracle Service Password: ********

3. PostgreSQL Credentials (for Aurora PostgreSQL):
Enter PostgreSQL Admin Username [postgres]: postgres
Enter PostgreSQL Admin Password: ********
Enter PostgreSQL Database Name [postgres]: postgres

4. PostgreSQL Service Credentials:
Enter PostgreSQL Service Username [pguser]: app_user
Enter PostgreSQL Service Password: ********
```

**생성되는 Secrets:**
- `oma-secret-oracle-admin`
- `oma-secret-oracle-service`
- `oma-secret-postgres-admin` (또는 mysql-admin)
- `oma-secret-postgres-service` (또는 mysql-service)

#### 1.3.2. CloudFormation 스택 배포 (Option 2)

```bash
bash deploy-omabox.sh -o 2
```

**배포 시작:**
```
[INFO] === CloudFormation Stack Deployment ===
[INFO] Stack Name: oma-your-application-name
[INFO] Target DB: PostgreSQL
[INFO] Region: ap-northeast-2
[INFO] Deploying CloudFormation stack...
```

**배포 진행 (15-30분):**
```
[INFO] Stack Status: CREATE_IN_PROGRESS
[INFO] Creating VPC...
[INFO] Creating Subnets...
[INFO] Creating Security Groups...
[INFO] Creating Oracle RDS...
[INFO] Creating PostgreSQL Aurora...
[INFO] Creating DMS Replication Instance...
[INFO] Stack Status: CREATE_COMPLETE
```

**배포 완료 확인:**
```
[SUCCESS] CloudFormation stack deployed successfully!
[INFO] Stack Outputs:
  - OracleEndpoint: oracle-oma.xxxxx.ap-northeast-2.rds.amazonaws.com:1521
  - PostgreSQLEndpoint: postgres-oma.cluster-xxxxx.ap-northeast-2.rds.amazonaws.com:5432
  - DMSReplicationInstanceArn: arn:aws:dms:...
  - DMSSourceEndpointArn: arn:aws:dms:...
  - DMSTargetEndpointArn: arn:aws:dms:...
```

### 1.4. oma.properties 업데이트

**배포 완료 후 CloudFormation Outputs를 oma.properties에 추가합니다:**

```bash
vi oma.properties
```

```properties
[COMMON]
# Oracle Connection (CloudFormation Output에서 복사)
ORACLE_HOST=oracle-oma.xxxxx.ap-northeast-2.rds.amazonaws.com
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_CONN_TYPE=service
ORACLE_USER=app_user
ORACLE_PASSWORD=your_password
ORACLE_SCHEMA=YOUR_SCHEMA
ORACLE_HOME=/home/ec2-user/oracle

# PostgreSQL Connection (CloudFormation Output에서 복사)
PGHOST=postgres-oma.cluster-xxxxx.ap-northeast-2.rds.amazonaws.com
PGPORT=5432
PGDATABASE=postgres
PGSCHEMA=public
PGUSER=app_user
PGPASSWORD=your_password

# DMS 설정 (CloudFormation Output에서 복사)
DMS_REPLICATION_INSTANCE_ARN=arn:aws:dms:ap-northeast-2:123456789012:rep:XXX
DMS_SOURCE_ENDPOINT_ARN=arn:aws:dms:ap-northeast-2:123456789012:endpoint:XXX
DMS_TARGET_ENDPOINT_ARN=arn:aws:dms:ap-northeast-2:123456789012:endpoint:XXX

# Bedrock LLM
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7

# Target DB
TARGET_DB_TYPE=postgres
```

### 1.5. 환경 검증

```bash
# Oracle 연결 테스트
sqlplus $ORACLE_USER/$ORACLE_PASSWORD@//$ORACLE_HOST:$ORACLE_PORT/$ORACLE_SID

# PostgreSQL 연결 테스트
psql  # PGHOST 등 환경 변수 자동 인식

# DMS 인프라 확인
aws dms describe-replication-instances --region ap-northeast-2
aws dms describe-endpoints --region ap-northeast-2

# Python 버전 확인
python3.11 --version
```

✅ **Step 1 완료!** AWS 인프라가 배포되고 oma.properties 설정이 완료되었습니다.

---

## Step 2: Schema Migration (10-60분)

### 2.1. Schema 마이그레이션 실행

```bash
cd /home/ec2-user/workspace/oma/schema/postgresql/scripts
python3.11 run_migration.py
```

**실행 중 출력 예시:**

```
[INFO] PHASE 1: Schema Migration Pipeline
[INFO] Discovering Oracle schema: YOUR_SCHEMA
[INFO] Found 688 tables, 2450 indexes, 1230 constraints
[INFO] Agent 'Code Migrator': Converting DDL...
[INFO] Schema status: COMPLETED (245.3s)

[INFO] PHASE 2: Data Migration via DMS Full Load Task
[INFO] Creating DMS Full Load task...
[INFO] DMS task progress: 25% (tables=172, rows=3,456,789)
[INFO] DMS task progress: 50% (tables=344, rows=7,891,234)
[INFO] Data migration completed in 1834.2s

[INFO] PHASE 3: Data Integrity Verification
[INFO] Verification completed: 688 matches, 0 mismatches

[INFO] PHASE 4: Report Generation
✓ Migration report saved to: results/migration-report.json
```

### 2.2. 결과 확인

```bash
# 변환된 DDL 확인
cat results/ddl_output.sql | head -50

# 마이그레이션 리포트 확인
cat results/migration-report.json | jq '.'

# 데이터 검증 리포트
cat results/verification-report.json | jq '.summary'
```

### 2.3. (선택사항) 중단된 마이그레이션 재개

```bash
# 중단된 migration_id 확인
ls results/checkpoints/

# 재개
python3.11 run_migration.py --resume oma-migration-1719876543
```

✅ **Step 2 완료!** Schema와 데이터가 모두 마이그레이션되었습니다.

---

## Step 3: App Migration (10-30분)

**⚠️ 중요: App 변환은 반드시 Claude Code를 사용하여 스킬로 실행합니다!**

### 3.1. Source 매퍼 준비

```bash
# 원본 MyBatis Mapper 파일들을 SOURCE_WORKSPACE에 복사
mkdir -p /home/ec2-user/workspace/source/your-project-name
cp -r /path/to/your/mybatis/mappers \
     /home/ec2-user/workspace/source/your-project-name/src/main/resources/mybatis/mapper/
```

### 3.2. Claude Code 시작

```bash
# app 폴더로 이동
cd /home/ec2-user/workspace/oma/app

# Claude Code 실행
claude
```

**Claude Code가 시작되면 app 폴더가 작업 디렉토리로 설정됩니다.**

---

### 3.3. 스킬 실행 순서

#### 스킬 1: 환경 검증 (/verify-env)

**Claude Code 프롬프트:**

```
/verify-env
```

**자동으로 수행하는 작업:**
1. Python 3.11+ 확인
2. oma.properties 환경 변수 로드
3. Oracle 연결 테스트
4. PostgreSQL/MySQL 연결 테스트
5. Source workspace 탐지
6. **Extension 스캔** (GRIDPAGING_*, FRAMEWORK_* 패턴)
7. **OGNL 스캔** (@Class@method 패턴)
8. Bedrock LLM 연결 테스트

**출력 예시:**

```
[INFO] ═══════════════════════════════════════════════════════════════
[INFO]           OMA Environment Verification Report
[INFO] ═══════════════════════════════════════════════════════════════

✓ Python: 3.11.9
✓ Environment variables loaded from: /home/ec2-user/workspace/oma/env/oma.properties

✓ Oracle Client: sqlplus available
✓ Oracle Connection: WMSON@oracle-oma.xxxxx:1521/ORCLPDB1
  - Schema exists: WMSON
  - Tables found: 688

✓ PostgreSQL Client: psql available
✓ PostgreSQL Connection: postgres-oma.cluster-xxxxx:5432/postgres
  - Schema exists: public

✓ Source Workspace: /home/ec2-user/workspace/source
  - Projects detected: your-project-name
  - Mapper files: 150 files found

✓ Extension Scan:
  - GRIDPAGING_ROWNUMTYPE_TOP: 45 files
  - GRIDPAGING_ROWNUMTYPE_BOTTOM: 45 files
  - FRAMEWORK_USER_ID: 12 files

✓ OGNL Scan:
  - @com.kns.framework.util.StringUtil@isEmpty: 68 usages
  - @com.kns.framework.util.StringUtil@isNotEmpty: 574 usages
  - @com.example.util.DateUtil@now: 23 usages

✓ Bedrock LLM: global.anthropic.claude-opus-4-7
  - Region: ap-northeast-2
  - Connection: OK

[SUCCESS] ✓ All checks passed! Environment is ready for migration.

Reports saved:
  - output/extension-scan-report.json
  - output/ognl-scan-report.json
```

---

#### 스킬 2: Oracle Dictionary 생성 (/build-oracle-dict)

**Claude Code 프롬프트:**

```
/build-oracle-dict
```

**자동으로 수행하는 작업:**
1. Oracle 스키마 메타데이터 추출
2. 테이블, 컬럼, 데이터 타입, 제약조건
3. Primary Keys, Foreign Keys
4. 컬럼별 샘플 데이터 수집
5. Row Count 계산
6. JSON 형식으로 저장

**출력 예시:**

```
[INFO] Connecting to Oracle: WMSON@oracle-oma.xxxxx:1521/ORCLPDB1
[INFO] Extracting schema metadata...
[INFO] Found 688 tables

[INFO] Extracting columns...
[INFO] Progress: 100/688 tables
[INFO] Progress: 200/688 tables
[INFO] Progress: 688/688 tables

[INFO] Collecting sample data...
[INFO] Progress: 688/688 tables

✓ Oracle Dictionary saved to: output/oracle_dictionary.json

Dictionary stats:
  - Total tables: 688
  - Total columns: 5,432
  - Tables with sample data: 688
```

---

#### 스킬 3: 매퍼 분리 (/split-mappers)

**Claude Code 프롬프트:**

```
/split-mappers your-project-name
```

**자동으로 수행하는 작업:**
1. Source 매퍼 파일 로드
2. SQL ID별로 분리 (select, insert, update, delete)
3. resultMap과 sql fragment는 모든 파일에 포함
4. 프로젝트별 디렉토리 생성

**출력 예시:**

```
[INFO] Project: your-project-name
[INFO] Source: /home/ec2-user/workspace/source/your-project-name/.../mapper/
[INFO] Target: mappers/your-project-name/source/

[INFO] Processing: CommonMapper.xml
  - selectUser → CommonMapper_selectUser.xml
  - insertUser → CommonMapper_insertUser.xml
  - updateUser → CommonMapper_updateUser.xml
  - deleteUser → CommonMapper_deleteUser.xml

[INFO] Progress: 50/150 files processed
[INFO] Progress: 100/150 files processed
[INFO] Progress: 150/150 files processed

✓ Split completed: 150 files → 450 split files
✓ Output: mappers/your-project-name/source/
```

---

#### 스킬 4: SQL 변환 (/convert-sql)

**Claude Code 프롬프트:**

```
/convert-sql your-project-name
```

**자동으로 수행하는 작업:**
1. 분리된 매퍼 파일 로드
2. LLM이 SQL 이해 및 변환
3. Oracle Dictionary 기반 타입 캐스팅
4. 바인드 변수 추출 및 매핑
5. Test Case 자동 생성
6. Extension 변수 치환 (TC 파일에만)

**출력 예시:**

```
[INFO] Project: your-project-name
[INFO] Source: mappers/your-project-name/source/
[INFO] Target: mappers/your-project-name/target/
[INFO] Parallel workers: 10

[INFO] Converting: CommonMapper_selectUser.xml
  → Phase 1: XML parsing
  → Phase 2: LLM extracts table names
    - Found tables: TB_USER, TB_ROLE
  → Phase 3: Oracle Dictionary lookup
    - Matched: TB_USER (12 columns)
    - Matched: TB_ROLE (5 columns)
  → Phase 4: LLM converts SQL (Oracle → PostgreSQL)
    - VARCHAR: no casting
    - NUMBER(10,0) → ::INTEGER
    - DATE → ::TIMESTAMP
  → Phase 5: Generate Test Cases (5 cases)
  → Phase 6: Save outputs
  ✓ CommonMapper_selectUser.xml - 8 bind vars, 5 test cases

[INFO] Progress: 150/450 files converted
[INFO] Progress: 300/450 files converted
[INFO] Progress: 450/450 files converted

✓ Conversion completed!
✓ Output: mappers/your-project-name/target/
✓ Conversion report saved to: output/conversion-report.json

Summary:
  Total files: 450
  Converted: 448 (99.6%)
  Failed: 2 (0.4%)
  Tables discovered: 45
  Bind variables: 3,234
  Test cases: 2,245
  LLM calls: 900 (table_extraction: 450, sql_conversion: 448, json_fix: 2)
```

---

#### 스킬 5: 매퍼 합치기 (/merge-mappers)

**Claude Code 프롬프트:**

```
/merge-mappers your-project-name
```

**자동으로 수행하는 작업:**
1. 분리된 파일들을 원본 구조로 병합
2. TARGET_WORKSPACE에 복사
3. 디렉토리 구조 유지

**출력 예시:**

```
[INFO] Project: your-project-name
[INFO] Source: mappers/your-project-name/target/
[INFO] Target: /home/ec2-user/workspace/target/your-project-name/.../mapper/

[INFO] Merging: CommonMapper_*.xml → CommonMapper.xml
[INFO] Merging: UserMapper_*.xml → UserMapper.xml

[INFO] Progress: 50/150 files merged
[INFO] Progress: 100/150 files merged
[INFO] Progress: 150/150 files merged

✓ Merge completed: 450 files → 150 merged files
✓ Output: /home/ec2-user/workspace/target/your-project-name/.../mapper/
```

---

#### 스킬 6: SQL 검증 (/validate)

**Claude Code 프롬프트:**

```
/validate your-project-name
```

**자동으로 수행하는 작업:**
1. TC 파일 로드
2. 각 Test Case 실행:
   - Oracle SQL 실행
   - Target SQL 실행
   - 결과 비교
   - 성능 측정
3. 리포트 생성

**출력 예시:**

```
[INFO] Project: your-project-name
[INFO] TC Directory: mappers/your-project-name/target/
[INFO] Found 2,245 test cases in 448 files
[INFO] Parallel workers: 4

[INFO] Validating: CommonMapper_selectUser.xml (TC 1/5)
  [Oracle] Executed in 0.023s → 150 rows, 8 columns
  [PostgreSQL] Executed in 0.019s → 150 rows, 8 columns
  ✓ PASS - Results match, PostgreSQL faster by 17%

[INFO] Validating: CommonMapper_selectUser.xml (TC 2/5)
  [Oracle] Executed in 0.031s → 1 row, 8 columns
  [PostgreSQL] Executed in 0.015s → 1 row, 8 columns
  ✓ PASS - Results match, PostgreSQL faster by 52%

[INFO] Progress: 500/2245 test cases validated
[INFO] Progress: 1000/2245 test cases validated
[INFO] Progress: 1500/2245 test cases validated
[INFO] Progress: 2000/2245 test cases validated
[INFO] Progress: 2245/2245 test cases validated

✓ Validation completed!
✓ Validation report saved to: output/validation-report.json
✓ Performance report saved to: output/validation-performance.json

Summary:
  Total queries: 2,245
  Passed: 2,223 (99.0%)
  Failed: 22 (1.0%)
  
Performance:
  PostgreSQL faster: 1,893 queries (84.3%)
  Oracle faster: 352 queries (15.7%)
  Average PostgreSQL speedup: 28%
```

---

### 3.4. 결과 확인

```bash
# 변환 리포트 확인
cat output/conversion-report.json | jq '.conversion_summary'

# 검증 요약
cat output/validation-report.json | jq '.summary'

# 실패한 쿼리 확인
cat output/validation-report.json | jq '.failed_queries[] | {file, query_id, error}'

# 성능 비교
cat output/validation-performance.json | jq '.performance_summary'

# Extension 스캔 결과
cat output/extension-scan-report.json | jq '.'

# OGNL 스캔 결과
cat output/ognl-scan-report.json | jq '.'
```

---

### 3.5. (선택사항) 실패한 SQL 수동 수정

```bash
# 1. 실패 원인 분석
cat output/validation-report.json | jq '.failed_queries[] | {file, error}'

# 2. 매퍼 수정
vi mappers/your-project-name/target/CommonMapper_selectUser.xml

# 3. 재검증 (Claude Code에서)
/validate your-project-name
```

---

✅ **Step 3 완료!** 

**생성된 파일:**
```
app/
├── mappers/your-project-name/
│   ├── source/                       # 분리된 원본
│   │   ├── CommonMapper_selectUser.xml
│   │   └── ...
│   └── target/                       # 변환된 결과
│       ├── CommonMapper_selectUser.xml
│       ├── CommonMapper_selectUser.tc.json
│       └── ...
├── output/
│   ├── oracle_dictionary.json        # Oracle 스키마
│   ├── extension-scan-report.json    # Extension 스캔
│   ├── ognl-scan-report.json         # OGNL 스캔
│   ├── conversion-report.json        # 변환 리포트
│   ├── validation-report.json        # 검증 리포트
│   └── validation-performance.json   # 성능 비교
└── /home/ec2-user/workspace/target/your-project-name/
    └── .../mapper/                   # 병합된 최종 매퍼
        ├── CommonMapper.xml
        └── ...
```
## 다음 단계

### 1. 프로덕션 준비

```bash
# 1. 변환된 매퍼를 애플리케이션에 통합
cp -r mappers/* /path/to/your/app/src/main/resources/mybatis/mapper/

# 2. 애플리케이션 빌드
cd /path/to/your/app
mvn clean package

# 3. 테스트 실행
mvn test
```

### 2. 실패한 SQL 수동 수정

```bash
# 1. 실패 원인 분석
cat output/validation-report.json | jq '.failed_queries[] | {file, query_id, error}'

# 2. 수동 수정
vi mappers/user-mapper.xml

# 3. 재검증
python3.11 tools/validator.py \
  --tc-dir mappers \
  --files user-mapper.xml
```

### 3. Extension 수동 처리 (필요시)

```bash
# Extension 스캔 결과 확인
cat output/extension-scan-report.json | jq '.'

# 고객 프레임워크 변수 정의 파일 생성
vi output/extensions.json

# 변환 재실행 (Extension 적용)
/convert
```

### 4. OGNL 수동 처리 (필요시)

```bash
# OGNL 스캔 결과 확인
cat output/ognl-scan-report.json | jq '.'

# Java 클래스 수동 마이그레이션
# - @com.example.Util@method() 호출 확인
# - 동등한 PostgreSQL/MySQL 함수로 변경
```

---

## 문제 해결

### 문제 1: Oracle 연결 실패

**증상:**
```
ORA-12170: TNS:Connect timeout occurred
```

**해결:**
```bash
# 1. 네트워크 연결 확인
ping $ORACLE_HOST

# 2. 방화벽/Security Group 확인
telnet $ORACLE_HOST 1521

# 3. Oracle Instant Client 확인
echo $ORACLE_HOME
ls -l $ORACLE_HOME
```

---

### 문제 2: DMS Task 생성 실패

**증상:**
```
Failed to create DMS task: ReplicationInstance not found
```

**해결:**
```bash
# 1. DMS 인프라 확인
aws dms describe-replication-instances
aws dms describe-endpoints

# 2. 환경 변수 설정
export DMS_REPLICATION_INSTANCE_ARN="arn:aws:dms:..."
export DMS_SOURCE_ENDPOINT_ARN="arn:aws:dms:..."
export DMS_TARGET_ENDPOINT_ARN="arn:aws:dms:..."

# 3. 재실행
python3.11 run_migration.py
```

---

### 문제 3: Table not found in dictionary

**증상:**
```
[WARNING] Table TB_NEW_TABLE not found in dictionary
```

**해결:**
```bash
# 1. Dictionary 재추출
python3.11 tools/extract_dict.py \
  --host $ORACLE_HOST \
  --schema $ORACLE_SCHEMA \
  --output output/oracle_dictionary.json

# 2. 특정 테이블만 추가
python3.11 tools/extract_dict.py \
  --tables TB_NEW_TABLE,TB_ANOTHER_TABLE \
  --append

# 3. 변환 재실행
/convert
```

---

### 문제 4: SQL 검증 실패

**증상:**
```
[FAIL] selectUser - Row count mismatch (Oracle: 150, Postgres: 0)
```

**해결:**
```bash
# 1. TC 파일 확인
cat mappers/user-mapper_selectUser.tc.json | jq '.'

# 2. 바인드 변수 확인
cat mappers/user-mapper_selectUser.tc.json | jq '.test_cases[0].parameters'

# 3. 수동 SQL 실행 테스트
psql -h $PGHOST -U $PGUSER -d $PGDATABASE
=> SELECT * FROM tb_user WHERE user_id = '12345';

# 4. 매퍼 수동 수정
vi mappers/user-mapper.xml

# 5. 재검증
python3.11 tools/validator.py --files user-mapper.xml
```

---

### 문제 5: LLM 호출 실패

**증상:**
```
ValidationException: Model not found
```

**해결:**
```bash
# 1. Bedrock 모델 액세스 확인
aws bedrock list-foundation-models --region ap-northeast-2 | grep opus-4-7

# 2. 모델 액세스 요청 (AWS Console)
# Bedrock > Model access > Request access to Claude Opus 4.7

# 3. 환경 변수 확인
echo $BEDROCK_MODEL_ID
echo $BEDROCK_REGION

# 4. 재실행
/convert
```

---

## 유용한 명령어

### Schema Migration

```bash
# 데이터 마이그레이션만 (Phase 2만)
python3.11 run_data_migration_only.py

# 시퀀스 사용처 추출
cd schema/tools
python3.11 extract_sequence_usage.py --schema YOUR_SCHEMA
```

### App Migration

```bash
# 변환 통계 확인
cat output/conversion-report.json | jq '.conversion_details'

# LLM 호출 횟수 확인
cat output/conversion-report.json | jq '.conversion_performance.llm_calls'

# 가장 느린 파일 확인
cat output/conversion-report.json | jq '.file_details | sort_by(.conversion_time) | reverse | .[0:10]'

# 성능 비교 (Oracle vs Postgres)
cat output/validation-performance.json | jq '.performance_summary'
```

### 환경 관리

```bash
# 환경 변수 로드
source tools/load_oma_env.sh

# 환경 변수 확인
env | grep ORACLE
env | grep PG
env | grep BEDROCK

# 로그 확인
tail -f logs/conversion.log
tail -f logs/validation.log
```

---

## 참고 자료

- **전체 문서**: [README_KR.md](README_KR.md)
- **Schema 가이드**: [schema/README_KR.md](schema/README_KR.md)
- **App 가이드**: [app/README_KR.md](app/README_KR.md)
- **환경 설정**: [env/README_KR.md](env/README_KR.md)

---

## 지원

문제가 계속되면:

1. 로그 파일 확인 (`logs/`)
2. 리포트 파일 분석 (`output/`, `results/`)
3. 환경 설정 재확인 (`env/oma.properties`)
4. AWS 서비스 상태 확인 (DMS, RDS, Bedrock)

---

**작성일**: 2026-06-23  
**OMA Version**: 2.0  
**예상 완료 시간**: 30-90분 (데이터 크기에 따라)
