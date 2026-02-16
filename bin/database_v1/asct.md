# ASCT (AWS Schema Conversion Tool) Helper

ASCT는 DMS Schema Conversion이 자동으로 변환하지 못한 Oracle 스키마 객체를 Amazon Q를 사용하여 PostgreSQL 호환 구문으로 변환하는 도구입니다.

## 개요

이 프로그램은 Oracle에서 PostgreSQL로의 데이터베이스 마이그레이션 과정에서 DMS Schema Conversion이 자동으로 변환하지 못한 복잡한 객체(Medium 또는 Complex 복잡도)를 Amazon Q를 활용하여 변환합니다. 변환된 코드는 PostgreSQL 데이터베이스에 직접 배포할 수 있습니다.

## 디렉토리 구조

```
./Database/
├── asct.py                      # 메인 스크립트
├── asct.md                      # 이 파일
├── oracle_to_postgres_prompt.txt # 변환 프롬프트 템플릿
└── $DBMS_FOLDER/                # 평가 및 변환 작업 디렉토리
    ├── ORACLE_AURORA_POSTGRESQL_*.zip  # DMS SCT 평가 결과 파일 (필수)
    ├── extracted_csv/           # 압축 해제된 CSV 파일 디렉토리
    ├── incompatible.lst         # 변환 대상 객체 목록
    ├── oracle/                  # 원본 Oracle DDL 파일 디렉토리
    ├── transform/               # 변환된 PostgreSQL 코드 디렉토리
    └── failed_conversions/      # 변환 실패한 객체들
└── $DBMS_LOGS_FOLDER/           # 로그 파일 디렉토리
    ├── asct.log                 # 메인 로그 파일
    ├── debug_*.txt              # 디버그 파일들
    ├── postgres_errors.log      # PostgreSQL 실행 오류 로그
    └── postgres_error_report.txt # 오류 분석 보고서
```

## 필수 환경 변수

프로그램 실행을 위해 다음 환경 변수를 **반드시** 설정해야 합니다:

### 디렉토리 설정 (필수)
- `DBMS_FOLDER`: 평가 및 변환 작업 디렉토리 경로
- `DBMS_LOGS_FOLDER`: 로그 파일 디렉토리 경로

### Oracle 연결 정보 (필수)
- `ORACLE_ADM_USER`: Oracle 관리자 사용자
- `ORACLE_ADM_PASSWORD`: Oracle 관리자 비밀번호
- `ORACLE_SVC_USER`: Oracle 서비스 사용자
- `ORACLE_HOST`: Oracle 호스트
- `ORACLE_PORT`: Oracle 포트
- `ORACLE_SID`: Oracle SID

### PostgreSQL 연결 정보 (배포 시 필요)
- `PGHOST`: PostgreSQL 호스트
- `PGUSER`: PostgreSQL 사용자
- `PGPORT`: PostgreSQL 포트 (기본값: 5432)
- `PGDATABASE`: PostgreSQL 데이터베이스
- `PGPASSWORD`: PostgreSQL 비밀번호

## 환경 변수 설정 예시

```bash
# 디렉토리 설정
export DBMS_FOLDER="/path/to/assessments"
export DBMS_LOGS_FOLDER="/path/to/logs"

# Oracle 연결 정보
export ORACLE_ADM_USER="system"
export ORACLE_ADM_PASSWORD="password"
export ORACLE_SVC_USER="hr"
export ORACLE_HOST="oracle.example.com"
export ORACLE_PORT="1521"
export ORACLE_SID="ORCL"

# PostgreSQL 연결 정보 (선택사항)
export PGHOST="postgres.example.com"
export PGUSER="postgres"
export PGPORT="5432"
export PGDATABASE="mydb"
export PGPASSWORD="password"
```

## 사전 준비

1. **DMS Schema Conversion 평가 파일 준비**:
   - DMS Schema Conversion Tool에서 생성된 `ORACLE_AURORA_POSTGRESQL*.zip` 파일을 `$DBMS_FOLDER`에 복사

2. **디렉토리 생성**:
   ```bash
   mkdir -p $DBMS_FOLDER
   mkdir -p $DBMS_LOGS_FOLDER
   ```

## 사용 방법

### 기본 실행

```bash
python3 asct.py
```

이 명령은 다음 작업을 수행합니다:
1. 필수 환경 변수 검증
2. `$DBMS_FOLDER`에서 ORACLE_AURORA_POSTGRESQL로 시작하는 zip 파일을 찾아 압축을 풉니다.
3. CSV 파일에서 Medium 또는 Complex 복잡도를 가진 객체를 추출합니다.
4. Oracle에서 해당 객체의 DDL을 추출합니다.
5. Amazon Q를 사용하여 Oracle DDL을 PostgreSQL 호환 구문으로 변환합니다.
6. 변환된 코드를 PostgreSQL 데이터베이스에 배포합니다 (PostgreSQL 연결 정보가 설정된 경우).

### 배포만 실행

```bash
python3 asct.py --deploy-only
```

이 명령은 변환 과정 없이 이미 변환된 SQL 파일을 PostgreSQL 데이터베이스에 배포합니다.

## 주요 기능

1. **환경 변수 검증**: 필수 환경 변수와 파일 존재 여부를 자동으로 확인합니다.
2. **객체 추출**: DMS Schema Conversion CSV 파일에서 변환이 필요한 객체를 추출합니다.
3. **Oracle DDL 추출**: Oracle 데이터베이스에서 객체의 DDL을 추출합니다.
4. **Amazon Q 변환**: Amazon Q를 사용하여 Oracle DDL을 PostgreSQL 호환 구문으로 변환합니다.
5. **자동 오류 처리**: PostgreSQL 배포 중 발생하는 오류를 자동으로 처리합니다.
6. **종속성 관리**: 객체 간 종속성을 고려하여 올바른 순서로 배포합니다.
7. **오류 분석**: 배포 후 오류 분석 보고서를 생성합니다.

## 변환 지원 객체 유형

- 사용자/스키마 (USERS/SCHEMAS)
- 테이블스페이스 (TABLESPACES)
- 테이블 (TABLES)
- 제약조건 (CONSTRAINTS)
- 인덱스 (INDEXES)
- 시퀀스 (SEQUENCES)
- 뷰 (VIEWS)
- 시노님 (SYNONYMS)
- 함수 (FUNCTIONS)
- 프로시저 (PROCEDURES)
- 패키지 (PACKAGES)
- 트리거 (TRIGGERS)
- 타입 (TYPES)
- 권한 (PRIVILEGES)
- 롤 (ROLES)

## 특별 처리 기능

- Oracle 패키지를 PostgreSQL 함수 집합으로 변환
- Oracle 특정 데이터 타입을 PostgreSQL 호환 데이터 타입으로 변환
- PIVOT, LISTAGG 등 Oracle 특정 기능을 PostgreSQL 대안으로 변환
- 자동 오류 복구 및 재시도 메커니즘

## 오류 처리

프로그램은 다음과 같은 오류 상황을 자동으로 처리합니다:

1. **구문 오류**: 변환된 SQL에 구문 오류가 있는 경우 재변환 시도
2. **객체 존재**: 이미 존재하는 객체에 대해 IF NOT EXISTS 또는 OR REPLACE 구문 추가
3. **종속성 오류**: 참조하는 객체가 없는 경우 종속성 큐에 추가하여 나중에 재시도
4. **스키마 누락**: 존재하지 않는 스키마 자동 생성
5. **식별자 문제**: 따옴표 관련 구문 오류 자동 수정

## 로그 및 출력 파일

- `$DBMS_LOGS_FOLDER/asct.log`: 전체 실행 로그
- `$DBMS_LOGS_FOLDER/debug_*.txt`: Amazon Q 응답 디버그 파일
- `$DBMS_LOGS_FOLDER/postgres_errors.log`: PostgreSQL 실행 오류
- `$DBMS_LOGS_FOLDER/postgres_error_report.txt`: 오류 분석 보고서
- `$DBMS_FOLDER/transform/*.sql`: 변환된 PostgreSQL DDL 파일들
- `$DBMS_FOLDER/oracle/*.sql`: 원본 Oracle DDL 파일들
- `$DBMS_FOLDER/failed_conversions/`: 변환 실패한 객체들
