# OMA (Oracle Modernization Accelerator) 프로젝트 실행 가이드

## 프로젝트 개요
OMA는 Oracle 데이터베이스와 애플리케이션을 PostgreSQL로 현대화하는 도구입니다.
AWS 환경에서 사전 구성된 상태에서 DB/Application 변환을 수행합니다.

## 디렉토리 구조
```
sample-oracle-modernization-accelerator/          # OMA 루트 폴더 (OMA_BASE_DIR)
├── initOMA.sh                                    # 메인 실행 스크립트 (통합 진입점)
├── oma_env_[프로젝트명].sh                        # 프로젝트별 환경 변수 파일
├── config/                                       # 프로젝트 설정 파일 디렉토리
│   └── oma.properties                            # 환경 변수로 사용되는 설정 파일
├── [프로젝트명]/                                   # 분석 및 변환 단위 (애플리케이션명으로 구분)
│   ├── database/                                 # 데이터베이스 스키마 변환 결과
│   ├── logs/                                     # 전체 프로세스 로그 디렉토리
│   ├── application/                              # 애플리케이션 분석 및 변환 결과
│   │   ├── *.csv                                 # JNDI, Mapper 분석 결과 파일들
│   │   ├── Discovery-Report.html                 # 애플리케이션 분석 리포트
│   │   └── transform/                            # SQL 변환 결과 및 로그
│   └── test/                                     # Unit 테스트 수행 결과 및 도구
└── bin/                                          # OMA 실행 스크립트 및 템플릿
    ├── setEnv.sh                                 # 환경 설정 스크립트
    ├── checkEnv.sh                               # 환경 변수 확인 스크립트
    ├── processDBSchema.sh                        # DB Schema 변환 스크립트
    ├── processAppDiscovery.sh                    # 애플리케이션 Discovery 스크립트
    ├── processSQLTransform.sh                    # SQL 변환 스크립트
    ├── processSQLTest.sh                         # SQL Unit Test 스크립트
    ├── database/                                 # 데이터베이스 변환 템플릿
    ├── application/                              # 애플리케이션 변환 템플릿
    ├── promptTemplate/                           # AI 프롬프트 템플릿
    └── test/                                     # 테스트 템플릿
```

## 실행 순서 및 의미

### 1. 환경 설정 (사전 준비)
```bash
# 통합 실행 스크립트로 환경 설정 (권장)
./initOMA.sh
# → 메뉴에서 "0. 환경 설정 및 확인" 선택
# → "1. 환경 설정 다시 수행 (setEnv.sh)" 선택

# 또는 직접 환경 설정
./bin/setEnv.sh

# 환경 변수 로드 (생성된 파일 사용)
source ./oma_env_프로젝트명.sh

# 환경 변수 확인
./bin/checkEnv.sh
```

### 2. 통합 실행 (권장)
```bash
# 메인 실행 스크립트 - 메뉴 기반 단계별 선택 실행
./initOMA.sh

# 메뉴 구조:
# 0. 환경 설정 및 확인
#    1. 환경 설정 다시 수행 (setEnv.sh)
#    2. 현재 환경 변수 확인 (checkEnv.sh)
# 1. 데이터베이스 변환
#    1. DB Schema 변환
# 2. 애플리케이션 변환
#    1. 애플리케이션 분석 및 SQL변환 대상 추출
#    2. 애플리케이션 SQL 변환 작업
#    3. 애플리케이션 Java Source 변환 작업 (미구현)
# 3. SQL 테스트 수행
#    1. 애플리케이션 SQL Unit Test
```

### 3. 개별 단계 실행 (선택사항)
```bash
# Step 1: DB Schema 변환 (Oracle → PostgreSQL)
./bin/processDBSchema.sh

# Step 2: 애플리케이션 Discovery (JNDI, Mapper 분석)
./bin/processAppDiscovery.sh

# Step 3: SQL 변환 (Oracle SQL → PostgreSQL SQL)
./bin/processSQLTransform.sh

# Step 4: SQL Unit Test (변환된 SQL 테스트)
./bin/processSQLTest.sh
```

## 변환 작업 단계별 의미

### Step 1: DB Schema 변환
- **목적**: Oracle 데이터베이스 스키마를 PostgreSQL로 변환
- **입력**: Oracle 데이터베이스 연결 정보
- **출력**: `[프로젝트명]/database/` 디렉토리에 변환된 스키마 파일
- **요구사항**: Source Oracle 시스템과의 연결 필요

### Step 2: 애플리케이션 Discovery
- **목적**: Java 애플리케이션에서 SQL 사용 패턴 분석 및 SQL변환 대상 추출
- **분석 대상**: JNDI 설정, MyBatis Mapper 파일 등
- **출력**: 
  - `[프로젝트명]/application/*.csv` - 분석 결과 데이터
  - `[프로젝트명]/application/Discovery-Report.html` - 분석 리포트
- **요구사항**: 애플리케이션 소스 코드 경로 설정

### Step 3: 애플리케이션 SQL 변환
- **목적**: Oracle SQL을 PostgreSQL SQL로 변환
- **입력**: Step 2에서 추출된 SQL 목록
- **출력**: `[프로젝트명]/application/transform/` 디렉토리에 변환 결과
- **특징**: AI 기반 변환, 전체/재시도 모드 지원

### Step 4: 애플리케이션 Java Source 변환 (미구현)
- **목적**: Java 소스 코드의 Oracle 관련 코드를 PostgreSQL용으로 변환
- **상태**: 현재 미구현 상태

### Step 5: SQL Unit Test
- **목적**: 변환된 SQL의 정확성 검증
- **테스트 방법**: 원본 Oracle과 변환된 PostgreSQL 결과 비교
- **출력**: `[프로젝트명]/test/` 디렉토리에 테스트 결과
- **요구사항**: Oracle 및 PostgreSQL 데이터베이스 연결 필요

## 주요 특징

### 환경 변수 기반 설정
- `OMA_BASE_DIR`: OMA 프로젝트 루트 디렉토리
- `APPLICATION_NAME`: 변환 대상 애플리케이션명
- 프로젝트별 독립적인 환경 설정 지원

### AWS 환경 통합
- AWS 서비스와 연동된 변환 작업
- 클라우드 기반 AI 모델 활용
- 확장 가능한 아키텍처

### 단계별 실행 지원
- 전체 프로세스 통합 실행
- 개별 단계별 실행 가능
- 실패 지점부터 재시작 지원

## 설정 파일 (oma.properties)

### 파일 위치 및 역할
- **경로**: `config/oma.properties`
- **역할**: OMA 프로젝트의 모든 환경 변수와 설정값을 중앙 관리
- **사용**: `setEnv.sh` 실행 시 이 파일을 기반으로 프로젝트별 환경 변수 파일 생성

### 주요 설정 섹션

#### [COMMON] - 공통 설정
```properties
OMA_BASE_DIR=/Users/changik/workspace/sample-oracle-modernization-accelerator

# 프로젝트별 디렉토리 구조 정의
DBMS_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/database
APPLICATION_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/application
TEST_FOLDER=${OMA_BASE_DIR}/${APPLICATION_NAME}/test
```

#### [프로젝트명] - 프로젝트별 설정 (예: [example])

**애플리케이션 설정**
```properties
APPLICATION_NAME=example                    # 프로젝트명 (디렉토리명으로 사용)
JAVA_SOURCE_FOLDER=/path/to/java/source    # Java 소스 코드 경로
SOURCE_SQL_MAPPER_FOLDER=/path/to/mapper   # MyBatis Mapper 파일 경로
TARGET_SQL_MAPPER_FOLDER=/path/to/target   # 변환된 xml 위치 (변환된 Mapper 저장 경로)
TRANSFORM_JNDI=jdbc                        # JNDI 변환 대상
TRANSFORM_RELATED_CLASS=_ALL_              # 변환 대상 클래스 (_ALL_ 또는 특정 클래스명)
```

**데이터베이스 타입 설정**
```properties
SOURCE_DBMS_TYPE=orcl                      # 소스 DB 타입 (orcl, mysql 등)
TARGET_DBMS_TYPE=pg                        # 타겟 DB 타입 (Target DB유형에 따라서 변환 프롬프트 가변 실행)
```

**Oracle 데이터베이스 연결 설정**
```properties
# 관리자 계정 (스키마 변환용)
ORACLE_ADM_USER=system
ORACLE_ADM_PASSWORD=password
ORACLE_HOST=oracle-host.com
ORACLE_PORT=1521
ORACLE_SID=ORCL

# 서비스 계정 (애플리케이션용)
ORACLE_SVC_USER=app_user
ORACLE_SVC_PASSWORD=app_password
ORACLE_SVC_CONNECT_STRING=orcl

# 변환 대상 스키마 목록
ORACLE_SVC_USER_LIST="SCHEMA1,SCHEMA2,SCHEMA3"
```

**PostgreSQL 데이터베이스 연결 설정**
```properties
# 관리자 계정
PG_ADM_USER=postgres
PG_ADM_PASSWORD=postgres_password
PGHOST=postgres-host.com
PGPORT=5432
PGDATABASE=postgresdb

# 서비스 계정
PG_SVC_USER=app_user
PG_SVC_PASSWORD=app_password
PGUSER=postgres
PGPASSWORD=postgres_password
```

### 설정 파일 사용 방법

1. **초기 설정**
   ```bash
   # config/oma.properties 파일 편집
   vi config/oma.properties
   
   # 프로젝트별 섹션 추가 또는 수정
   [your_project_name]
   APPLICATION_NAME=your_project_name
   # ... 기타 설정값들
   ```

2. **환경 변수 생성**
   ```bash
   # setEnv.sh 실행하여 환경 변수 파일 생성
   ./bin/setEnv.sh
   # → oma_env_your_project_name.sh 파일 생성됨
   ```

3. **환경 변수 로드**
   ```bash
   # 생성된 환경 변수 파일 로드
   source ./oma_env_your_project_name.sh
   ```

### 주의사항
- **보안**: 데이터베이스 패스워드 등 민감한 정보 포함
- **권한**: 파일 권한 설정 주의 (`chmod 600 config/oma.properties` 권장)
- **백업**: 설정 변경 전 백업 필수
- **프로젝트별 구분**: `[프로젝트명]` 섹션으로 여러 프로젝트 관리 가능
- **TARGET_DBMS_TYPE 중요성**: 타겟 DB 유형에 따라 AI 변환 프롬프트가 다르게 적용됨
- **TARGET_SQL_MAPPER_FOLDER**: 변환된 MyBatis XML 파일이 저장되는 최종 위치

## 주의사항

### 사전 요구사항
- AWS 환경 구성 (DB 연결 관련 작업 시)
- Oracle 및 PostgreSQL 데이터베이스 연결 정보
- Java 애플리케이션 소스 코드 경로

### 데이터베이스 연결이 필요한 작업
- **Step 1**: DB Schema 변환 - Oracle 연결 필요
- **Step 5**: SQL Unit Test - Oracle 및 PostgreSQL 연결 필요

### 실행 권한
- 모든 `.sh` 스크립트에 실행 권한 필요
- `chmod +x *.sh` 명령으로 권한 설정

## 문제 해결

### 환경 변수 미설정 오류
```bash
# 환경 변수 파일 확인
ls -la oma_env_*.sh

# 환경 변수 로드
source ./oma_env_프로젝트명.sh
```

### 스크립트 실행 오류
```bash
# 실행 권한 확인 및 설정
chmod +x initOMA.sh
chmod +x bin/*.sh
```

### 로그 확인
```bash
# 프로젝트별 로그 디렉토리 확인
ls -la [프로젝트명]/logs/
```

