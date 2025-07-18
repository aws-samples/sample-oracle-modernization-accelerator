# Oracle to Multi-Database Migration Test Suite

이 프로젝트는 Oracle 데이터베이스에서 PostgreSQL 또는 MySQL로의 마이그레이션을 위한 자동화된 테스트 및 분석 도구입니다.

## 개요

Oracle SQL을 PostgreSQL 또는 MySQL로 변환하고 실행 결과를 비교하여 마이그레이션의 정확성을 검증하는 통합 테스트 시스템입니다.

## 주요 기능

- XML 파일에서 SQL 구문 자동 추출
- 바인드 변수 처리 및 매핑
- SQL 실행 결과 비교 및 분석
- 다중 데이터베이스 지원 (PostgreSQL, MySQL)
- 데이터베이스별 오류 유형 자동 분석
- 오류 구문 자동 수정 (선택적)

## 사전 요구사항

### 필수 요구사항
- Oracle 데이터베이스 (소스)
- 타겟 데이터베이스 (PostgreSQL 또는 MySQL)
- Python 3.x
- Oracle SQL*Plus 클라이언트

### 타겟 데이터베이스별 요구사항
- **PostgreSQL**: psql 클라이언트, psycopg2 Python 패키지
- **MySQL**: mysql 클라이언트, mysql-connector-python Python 패키지

### 환경 변수
- `TARGET_DBMS_TYPE`: 타겟 데이터베이스 타입 (postgres, postgresql, mysql)
- `TEST_FOLDER`: 테스트 작업 폴더 경로

## 사용 방법

### 전체 테스트 실행

```bash
./initTest.sh
```

### 환경 설정

#### PostgreSQL 사용 시
```bash
export TARGET_DBMS_TYPE=postgres
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=your_database
export PGUSER=your_username
export PGPASSWORD=your_password
export TEST_FOLDER=/path/to/test/folder
```

#### MySQL 사용 시
```bash
export TARGET_DBMS_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=your_database
export MYSQL_USER=your_username
export MYSQL_PASSWORD=your_password
export TEST_FOLDER=/path/to/test/folder
```

### 단계별 실행

1. **데이터베이스 초기화**
   ```bash
   # PostgreSQL인 경우
   psql -c "truncate table sqllist"
   
   # MySQL인 경우
   mysql -e "truncate table sqllist"
   ```

2. **작업 폴더 초기화**
   ```bash
   rm -rf $TEST_FOLDER/*
   ```

3. **XML에서 SQL 추출**
   ```bash
   ./XMLToSQL.py
   ```

4. **딕셔너리 파일 생성**
   ```bash
   ./GetDictionary.py
   ```

5. **바인드 변수 처리**
   ```bash
   ./BindSampler.py
   ./BindMapper.py
   ```

6. **SQL을 데이터베이스에 저장**
   ```bash
   ./SaveSQLToDB.py
   ```

7. **SQL 실행 및 결과 비교**
   ```bash
   ./ExecuteAndCompareSQL.py -t S
   ```

8. **타겟 데이터베이스 오류 분석**
   ```bash
   ./analyze_db_errors.py
   ```

9. **오류 구문 자동 수정 (선택적)**
   ```bash
   # 멀티 DB 지원 (권장)
   ./db_transform.py --type=05
   
   # PostgreSQL 전용 (기존)
   ./pg_transform.py --type=05
   ```

## 스크립트 설명

| 스크립트 | 기능 | 멀티 DB 지원 |
|---------|------|-------------|
| `XMLToSQL.py` | XML 파일에서 SQL 구문을 추출하여 개별 파일로 저장 | N/A |
| `GetDictionary.py` | SQL 분석을 위한 딕셔너리 파일 생성 | N/A |
| `BindSampler.py` | 바인드 변수 샘플링 및 분석 | N/A |
| `BindMapper.py` | 바인드 변수 매핑 처리 | N/A |
| `SaveSQLToDB.py` | 처리된 SQL을 sqllist 테이블에 저장 | ✅ PostgreSQL/MySQL |
| `ExecuteAndCompareSQL.py` | SQL 실행 및 결과 비교 분석 | ✅ PostgreSQL/MySQL |
| `analyze_db_errors.py` | 타겟 DB 오류 유형 분석 및 분류 | ✅ PostgreSQL/MySQL |
| `validateEnv.sh` | 환경 변수 및 시스템 요구사항 검증 | ✅ PostgreSQL/MySQL |
| `initTest.sh` | 전체 테스트 파이프라인 실행 | ✅ PostgreSQL/MySQL |
| `pg_transform.py` | PostgreSQL 오류 구문 자동 수정 도구 | ❌ PostgreSQL만 |
| `db_transform.py` | 다중 DB 오류 구문 자동 수정 도구 | ✅ PostgreSQL/MySQL |

## 환경 변수 검증

환경 설정이 올바른지 확인하려면:

```bash
./validateEnv.sh
```

## 데이터베이스 테이블

- `sqllist`: SQL 구문과 실행 결과를 저장하는 테이블
  - PostgreSQL과 MySQL 모두 지원
  - 스키마는 자동으로 생성됨

## 주의사항

- 모든 Python 스크립트는 실행 권한이 필요합니다
- `TARGET_DBMS_TYPE` 환경 변수가 올바르게 설정되어 있는지 확인하세요
- 타겟 데이터베이스별 클라이언트 도구가 설치되어 있어야 합니다
- 타겟 데이터베이스별 Python 패키지가 설치되어 있어야 합니다

## 결과 분석

테스트 완료 후 다음을 확인할 수 있습니다:
- SQL 변환 성공률
- 실행 결과 일치율
- 데이터베이스별 오류 유형 분류
- 자동 수정 가능한 오류 목록
- CSV 및 JSON 형태의 상세 분석 보고서

## 지원하는 데이터베이스

| 데이터베이스 | 지원 여부 | 클라이언트 도구 | Python 패키지 |
|-------------|----------|---------------|---------------|
| PostgreSQL | ✅ | psql | psycopg2-binary |
| MySQL | ✅ | mysql | mysql-connector-python |
| Oracle | ✅ (소스만) | sqlplus | cx_Oracle |

## 새로운 기능 (v2.0)

- 🆕 **다중 데이터베이스 지원**: PostgreSQL과 MySQL을 모두 지원
- 🆕 **통합 오류 분석**: 데이터베이스별 오류 패턴 분석
- 🆕 **환경 검증 도구**: 시스템 요구사항 자동 검증
- 🆕 **개선된 보고서**: JSON과 CSV 형태의 상세 분석 보고서