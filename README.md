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
- **출력**: `[프로젝트명]/dbms/` 디렉토리에 변환된 스키마 파일
- **요구사항**: Source Oracle 시스템과의 연결 필요

### Step 2: 애플리케이션 Discovery
- **목적**: Java 애플리케이션에서 SQL 사용 패턴 분석
- **분석 대상**: JNDI 설정, MyBatis Mapper 파일 등
- **출력**: 
  - `[프로젝트명]/application/*.csv` - 분석 결과 데이터
  - `[프로젝트명]/application/Discovery-Report.html` - 분석 리포트
- **요구사항**: 애플리케이션 소스 코드 경로 설정

### Step 3: SQL 변환
- **목적**: Oracle SQL을 PostgreSQL SQL로 변환
- **입력**: Step 2에서 추출된 SQL 목록
- **출력**: `[프로젝트명]/application/transform/` 디렉토리에 변환 결과
- **특징**: AI 기반 변환, 전체/재시도 모드 지원

### Step 4: SQL Unit Test
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

## 주의사항

### 사전 요구사항
- AWS 환경 구성 (DB 연결 관련 작업 시)
- Oracle 및 PostgreSQL 데이터베이스 연결 정보
- Java 애플리케이션 소스 코드 경로

### 데이터베이스 연결이 필요한 작업
- **Step 1**: DB Schema 변환 - Oracle 연결 필요
- **Step 4**: SQL Unit Test - Oracle 및 PostgreSQL 연결 필요

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

