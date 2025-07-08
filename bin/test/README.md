# Oracle to PostgreSQL Migration Test Suite

이 프로젝트는 Oracle 데이터베이스에서 PostgreSQL로의 마이그레이션을 위한 자동화된 테스트 및 분석 도구입니다.

## 개요

Oracle SQL을 PostgreSQL로 변환하고 실행 결과를 비교하여 마이그레이션의 정확성을 검증하는 통합 테스트 시스템입니다.

## 주요 기능

- XML 파일에서 SQL 구문 자동 추출
- 바인드 변수 처리 및 매핑
- SQL 실행 결과 비교 및 분석
- PostgreSQL 오류 유형 자동 분석
- 오류 구문 자동 수정 (선택적)

## 사전 요구사항

- PostgreSQL 데이터베이스
- Python 3.x
- psql 클라이언트
- 환경 변수 `TEST_FOLDER` 설정

## 사용 방법

### 전체 테스트 실행

```bash
./initTest.sh
```

### 단계별 실행

1. **데이터베이스 초기화**
   ```bash
   psql -c "truncate table sqllist"
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

8. **PostgreSQL 오류 분석**
   ```bash
   ./analyze_pg_errors.py
   ```

9. **오류 구문 자동 수정 (선택적)**
   ```bash
   ./pg_transform.py
   ```

## 스크립트 설명

| 스크립트 | 기능 |
|---------|------|
| `XMLToSQL.py` | XML 파일에서 SQL 구문을 추출하여 개별 파일로 저장 |
| `GetDictionary.py` | SQL 분석을 위한 딕셔너리 파일 생성 |
| `BindSampler.py` | 바인드 변수 샘플링 및 분석 |
| `BindMapper.py` | 바인드 변수 매핑 처리 |
| `SaveSQLToDB.py` | 처리된 SQL을 sqllist 테이블에 저장 |
| `ExecuteAndCompareSQL.py` | SQL 실행 및 결과 비교 분석 |
| `analyze_pg_errors.py` | PostgreSQL 오류 유형 분석 및 분류 |
| `pg_transform.py` | 오류 구문 자동 수정 도구 |

## 환경 설정

테스트 실행 전 다음 환경 변수를 설정해야 합니다:

```bash
export TEST_FOLDER=/path/to/test/folder
```

## 데이터베이스 테이블

- `sqllist`: SQL 구문과 실행 결과를 저장하는 테이블

## 주의사항

- 모든 Python 스크립트는 실행 권한이 필요합니다
- PostgreSQL 데이터베이스 연결이 사전에 설정되어 있어야 합니다
- `TEST_FOLDER` 환경 변수가 올바르게 설정되어 있는지 확인하세요

## 결과 분석

테스트 완료 후 다음을 확인할 수 있습니다:
- SQL 변환 성공률
- 실행 결과 일치율
- 오류 유형별 분류
- 자동 수정 가능한 오류 목록