# MyBatis XML 테스트 프로그램

MyBatis XML 파일의 SQL을 분석하고 실행하는 Java 프로그램입니다.

## 핵심 스크립트

### 1. bulk_prepare.sh
XML 파일들에서 파라미터를 일괄 추출하고 DB에서 샘플 값을 자동 수집합니다.

```bash
./bulk_prepare.sh <디렉토리경로> [--db <데이터베이스타입>] [--date-format <포맷>]
```

**기능:**
- 모든 XML 파일에서 `#{}`, `${}` 파라미터 자동 추출
- 실제 DB에서 파라미터명과 매칭되는 컬럼의 샘플 값 수집
- `parameters.properties` 파일 자동 생성

**예시:**
```bash
# 기본 파라미터 추출만
./bulk_prepare.sh /path/to/mapper

# Oracle DB에서 샘플 값 수집
./bulk_prepare.sh /path/to/mapper --db oracle

# PostgreSQL DB에서 샘플 값 수집 (커스텀 날짜 포맷)
./bulk_prepare.sh /path/to/mapper --db postgresql --date-format YYYY/MM/DD
```

### 2. run_oracle.sh
Oracle 데이터베이스에 대해 MyBatis SQL을 실행합니다.

```bash
./run_oracle.sh <디렉토리경로> [옵션]
```

**기능:**
- Oracle 환경변수 자동 인식 (`ORACLE_SVC_USER`, `ORACLE_SVC_PASSWORD`, `ORACLE_SVC_CONNECT_STRING`)
- MyBatis 엔진을 통한 동적 SQL 처리
- 실행 결과 및 통계 리포트 생성

### 3. run_postgresql.sh
PostgreSQL 데이터베이스에 대해 MyBatis SQL을 실행합니다.

```bash
./run_postgresql.sh <디렉토리경로> [옵션]
```

**기능:**
- PostgreSQL 환경변수 자동 인식 (`PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE`)
- PostgreSQL 전용 JDBC 드라이버 사용
- 실행 결과 및 통계 리포트 생성

### 4. run_mysql.sh
MySQL 데이터베이스에 대해 MyBatis SQL을 실행합니다.

```bash
./run_mysql.sh <디렉토리경로> [옵션]
```

**기능:**
- MySQL 환경변수 자동 인식 (`MYSQL_ADM_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_TCP_PORT`, `MYSQL_DB`)
- MySQL 전용 JDBC 드라이버 사용
- 실행 결과 및 통계 리포트 생성

## 공통 옵션

모든 실행 스크립트는 다음 옵션을 지원합니다:

- `--select-only`: SELECT 구문만 실행 (기본값, 안전)
- `--all`: 모든 SQL 구문 실행 (INSERT/UPDATE/DELETE 포함)
- `--summary`: 요약 정보만 출력
- `--verbose`: 상세 정보 출력
- `--json`: JSON 결과 파일 생성 (`out/bulk_test_result_YYYYMMDD_HHMMSS.json`)

## 사용 워크플로우

### 1단계: 파라미터 준비
```bash
# DB 샘플 값과 함께 파라미터 추출
./bulk_prepare.sh /path/to/mapper --db oracle
```

### 2단계: 파라미터 파일 편집 (선택사항)
생성된 `parameters.properties` 파일에서 필요시 값을 수정합니다.

### 3단계: SQL 실행
```bash
# Oracle에서 SELECT만 안전하게 실행
./run_oracle.sh /path/to/mapper --select-only --summary

# PostgreSQL에서 모든 SQL 실행 (주의!)
./run_postgresql.sh /path/to/mapper --all --verbose

# MySQL에서 실행하고 JSON 결과 저장
./run_mysql.sh /path/to/mapper --json
```

## 환경변수 설정

### Oracle
```bash
export ORACLE_SVC_USER="username"
export ORACLE_SVC_PASSWORD="password"
export ORACLE_SVC_CONNECT_STRING="host:port:sid"
```

### PostgreSQL
```bash
export PGUSER="username"
export PGPASSWORD="password"
export PGHOST="localhost"
export PGPORT="5432"
export PGDATABASE="dbname"
```

### MySQL
```bash
export MYSQL_ADM_USER="username"
export MYSQL_PASSWORD="password"
export MYSQL_HOST="localhost"
export MYSQL_TCP_PORT="3306"
export MYSQL_DB="dbname"
```

## 주요 특징

1. **실제 DB 샘플 값 활용**: 파라미터-컬럼명 매칭을 통한 자동 샘플 값 수집
2. **MyBatis 엔진 사용**: 동적 조건 자동 처리, 정확한 동작 보장
3. **다중 DB 지원**: Oracle, PostgreSQL, MySQL 모두 지원
4. **안전한 실행**: 기본적으로 SELECT만 실행, 데이터 변경은 명시적 옵션 필요
5. **상세한 리포트**: 성공/실패 통계, 오류 정보, JSON 추적 기능

## 출력 예시

```
=== MyBatis 대량 테스트 시작 ===
검색 디렉토리: /path/to/mapper
발견된 XML 파일 수: 25
총 SQL ID 수: 147

=== 테스트 실행 결과 ===
✓ UserMapper.xml - selectUser: 성공 (3건)
✓ UserMapper.xml - selectUserList: 성공 (15건)
✗ OrderMapper.xml - selectOrder: 실패 (파라미터 부족: orderId)

=== 최종 통계 ===
총 실행: 147개
성공: 142개 (96.6%)
실패: 5개 (3.4%)
실행 시간: 2분 34초
```
