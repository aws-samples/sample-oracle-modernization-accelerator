# ASCT (AWS Schema Conversion Tool) Helper

ASCT는 DMS Schema Conversion이 자동으로 변환하지 못한 Oracle 스키마 객체를 Amazon Q를 사용하여 PostgreSQL 호환 구문으로 변환하는 도구입니다.

## 개요

이 프로그램은 Oracle에서 PostgreSQL로의 데이터베이스 마이그레이션 과정에서 DMS Schema Conversion이 자동으로 변환하지 못한 복잡한 객체(Medium 또는 Complex 복잡도)를 Amazon Q를 활용하여 변환합니다. 변환된 코드는 PostgreSQL 데이터베이스에 직접 배포할 수 있습니다.

## 디렉토리 구조

```
./Database/
├── asct.py                      # 메인 스크립트
├── README.md                    # 이 파일
├── log/                         # 로그 파일 디렉토리
│   ├── asct.log                 # 로그 파일
│   └── debug_*.txt              # 디버그 파일들
├── prompt/                      # 프롬프트 파일 디렉토리
│   ├── prompt.txt               # 메인 프롬프트
│   └── oracle_to_postgres_prompt.txt  # 변환 프롬프트
└── work/                        # 작업 디렉토리
    ├── ORACLE_AURORA_POSTGRESQL_*.zip  # 압축 파일
    ├── extracted_csv/           # 압축 해제된 CSV 파일 디렉토리
    ├── incompatible.lst         # 변환 대상 객체 목록
    ├── oracle/                  # 원본 Oracle DDL 파일 디렉토리
    └── transform/               # 변환된 PostgreSQL 코드 디렉토리
```

## 필요 환경 변수

프로그램 실행을 위해 다음 환경 변수를 설정해야 합니다:

### Oracle 연결 정보
- `ORACLE_ADM_USER`: Oracle 관리자 사용자
- `ORACLE_ADM_PASSWORD`: Oracle 관리자 비밀번호
- `ORACLE_SVC_USER`: Oracle 서비스 사용자
- `ORACLE_HOST`: Oracle 호스트
- `ORACLE_PORT`: Oracle 포트
- `ORACLE_SID`: Oracle SID

### PostgreSQL 연결 정보
- `PGHOST`: PostgreSQL 호스트
- `PGUSER`: PostgreSQL 사용자
- `PGPORT`: PostgreSQL 포트 (기본값: 5432)
- `PGDATABASE`: PostgreSQL 데이터베이스
- `PGPASSWORD`: PostgreSQL 비밀번호

## 사용 방법

### 기본 실행

DMS SCT Project화일 ( ORACLE_AURORA_POSTGRESQL*zip ) 을 work 디렉토리에 복사하고 다음의 프로그램을 실행합니다.

```bash
python3 asct.py
```

이 명령은 다음 작업을 수행합니다:
1. work 디렉토리에서 ORACLE_AURORA_POSTGRESQL로 시작하는 zip 파일을 찾아 압축을 풉니다.
2. CSV 파일에서 Medium 또는 Complex 복잡도를 가진 객체를 추출합니다.
3. Oracle에서 해당 객체의 DDL을 추출합니다.
4. Amazon Q를 사용하여 Oracle DDL을 PostgreSQL 호환 구문으로 변환합니다.
5. 변환된 코드를 PostgreSQL 데이터베이스에 배포합니다.

### 배포만 실행

```bash
python3 asct.py --deploy-only
```

이 명령은 변환 과정 없이 이미 변환된 SQL 파일을 PostgreSQL 데이터베이스에 배포합니다.

## 주요 기능

1. **객체 추출**: DMS Schema Conversion CSV 파일에서 변환이 필요한 객체를 추출합니다.
2. **Oracle DDL 추출**: Oracle 데이터베이스에서 객체의 DDL을 추출합니다.
3. **Amazon Q 변환**: Amazon Q를 사용하여 Oracle DDL을 PostgreSQL 호환 구문으로 변환합니다.
4. **자동 오류 처리**: PostgreSQL 배포 중 발생하는 오류를 자동으로 처리합니다.
5. **종속성 관리**: 객체 간 종속성을 고려하여 올바른 순서로 배포합니다.
6. **오류 분석**: 배포 후 오류 분석 보고서를 생성합니다.

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
