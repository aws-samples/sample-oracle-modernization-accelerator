# MyBatis 다중 데이터베이스 테스트 도구 분석

## 개요

이 프로젝트는 MyBatis XML 매퍼 파일들을 자동으로 스캔하여 Oracle, MySQL, PostgreSQL 데이터베이스에 대해 SQL을 실행하고 테스트하는 도구입니다. 대량의 SQL을 효율적으로 검증할 수 있는 완전한 테스트 프레임워크를 제공합니다.

## 프로젝트 구조

### 실행 스크립트들
- `run_oracle.sh` - Oracle 데이터베이스 테스트 실행
- `run_mysql.sh` - MySQL 데이터베이스 테스트 실행  
- `run_postgresql.sh` - PostgreSQL 데이터베이스 테스트 실행
- `download_drivers.sh` - JDBC 드라이버 자동 다운로드
- `bulk_prepare.sh` - 대량 파라미터 준비 스크립트
- `bulk_json.sh` - JSON 결과 생성 스크립트

### 핵심 Java 클래스들
- `MyBatisBulkExecutorWithJson.java` - 메인 실행 엔진 (다중 DB 지원)
- `MyBatisTestPreparator.java` - 단일 SQL 파라미터 추출
- `MyBatisSimpleExecutor.java` - 단일 SQL 실행
- `MyBatisBulkPreparator.java` - 대량 파라미터 추출

### 설정 파일들
- `mybatis-bulk-executor.properties` - 실행 엔진 설정
- `parameters.properties` - SQL 파라미터 값들
- `README_MultiDB.md` - 다중 DB 사용법 가이드

### 라이브러리 (lib/)
- `mybatis-3.5.13.jar` - MyBatis 프레임워크
- `ojdbc8-21.9.0.0.jar` - Oracle JDBC 드라이버
- `mysql-connector-j-8.2.0.jar` - MySQL JDBC 드라이버
- `postgresql-42.7.1.jar` - PostgreSQL JDBC 드라이버
- `jackson-*.jar` - JSON 처리 라이브러리들

## 실행 스크립트 분석

### 1. run_oracle.sh
```bash
#!/bin/bash
# Oracle MyBatis 테스트 실행 스크립트

# 환경변수 검증
- ORACLE_SVC_USER (필수)
- ORACLE_SVC_PASSWORD (필수)  
- ORACLE_SVC_CONNECT_STRING (선택사항)

# 컴파일 및 실행
- Jackson JSON 라이브러리 포함
- MyBatisBulkExecutorWithJson 클래스 실행
- --db oracle 옵션 자동 추가
```

**특징:**
- Oracle TNS 연결 지원
- 환경변수 자동 검증
- 컴파일 실패 시 즉시 중단
- 모든 명령행 인수 전달 (`"$@"`)

### 2. run_mysql.sh  
```bash
#!/bin/bash
# MySQL MyBatis 테스트 실행 스크립트

# 환경변수 검증
- MYSQL_ADM_USER (필수)
- MYSQL_PASSWORD (필수)
- MYSQL_HOST (기본값: localhost)
- MYSQL_TCP_PORT (기본값: 3306)
- MYSQL_DB (기본값: test)

# JDBC 드라이버 확인
- mysql-connector-j-8.2.0.jar 존재 여부 체크
- 없으면 download_drivers.sh 실행 안내
```

**특징:**
- MySQL 8.0+ 지원
- 드라이버 자동 검증
- 기본값 제공으로 설정 간소화
- SSL 및 타임존 설정 자동 처리

### 3. run_postgresql.sh
```bash
#!/bin/bash  
# PostgreSQL MyBatis 테스트 실행 스크립트

# 환경변수 검증
- PGUSER (필수)
- PGPASSWORD (필수)
- PGHOST (기본값: localhost)
- PGPORT (기본값: 5432)
- PGDATABASE (기본값: postgres)

# PostgreSQL 표준 환경변수 사용
- PG* 접두사 사용으로 표준 준수
```

**특징:**
- PostgreSQL 표준 환경변수 사용
- 12+ 버전 지원
- 표준 포트 및 데이터베이스 기본값

### 4. download_drivers.sh
```bash
#!/bin/bash
# JDBC 드라이버 자동 다운로드

# Maven Central에서 다운로드
- MySQL: mysql-connector-j-8.2.0.jar
- PostgreSQL: postgresql-42.7.1.jar
- 중복 다운로드 방지
- 다운로드 상태 확인
```

**특징:**
- Maven Central Repository 사용
- 중복 다운로드 방지
- 실패 시 명확한 오류 메시지
- 현재 드라이버 목록 표시

## 핵심 Java 클래스 분석

### MyBatisBulkExecutorWithJson.java (메인 엔진)

**주요 기능:**
1. **다중 데이터베이스 지원**
   - Oracle: TNS 및 직접 연결
   - MySQL: 8.0+ 완전 지원
   - PostgreSQL: 표준 연결

2. **지능적인 SQL 검색**
   ```java
   // SQL 패턴 매칭
   Pattern sqlIdPattern = Pattern.compile("<(select|insert|update|delete)\\s+id=\"([^\"]+)\"");
   ```

3. **동적 MyBatis 설정 생성**
   ```java
   // 데이터베이스별 JDBC URL 생성
   Oracle: "jdbc:oracle:thin:@" + connectString
   MySQL: "jdbc:mysql://host:port/db?options"
   PostgreSQL: "jdbc:postgresql://host:port/db"
   ```

4. **JSON 결과 출력**
   - Jackson 라이브러리 사용
   - 상세한 테스트 결과 추적
   - 파일별 통계 제공

**명령행 옵션:**
- `--db <type>`: 데이터베이스 타입 (필수)
- `--select-only`: SELECT만 실행 (기본값)
- `--all`: 모든 SQL 실행
- `--summary`: 요약만 출력
- `--verbose`: 상세 출력
- `--json`: JSON 파일 생성

### MyBatisTestPreparator.java (파라미터 추출)

**기능:**
- 단일 XML 파일에서 특정 SQL ID의 파라미터 추출
- `#{}`, `${}` 파라미터 모두 지원
- parameters.properties 파일 생성

**사용법:**
```bash
java MyBatisTestPreparator <XML파일경로> <SQLID>
```

### MyBatisSimpleExecutor.java (단일 실행)

**기능:**
- 단일 SQL 실행 및 결과 출력
- Oracle 전용 (환경변수 기반)
- MyBatis 엔진 직접 사용

**특징:**
- 동적 조건 자동 처리
- resultType을 Map으로 임시 변경
- 테이블 형태 결과 출력

## 설정 파일 분석

### mybatis-bulk-executor.properties

**주요 설정:**
```properties
# SQL 패턴 설정
sql.pattern.regex=<(select|insert|update|delete)\\s+id="([^"]+)"
example.patterns=byexample,example,selectByExample,selectByExampleWithRowbounds

# 데이터베이스 드라이버
db.oracle.driver=oracle.jdbc.driver.OracleDriver
db.mysql.driver=com.mysql.cj.jdbc.Driver  
db.postgresql.driver=org.postgresql.Driver

# 기본값 설정
mysql.default.options=useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC
oracle.default.service=orcl
```

**특징:**
- 외부 설정으로 유연성 제공
- 데이터베이스별 기본값 설정
- 정규식 패턴 커스터마이징 가능

## 환경변수 요구사항

### Oracle
```bash
export ORACLE_SVC_USER=username
export ORACLE_SVC_PASSWORD=password
export ORACLE_SVC_CONNECT_STRING=tns_name  # 선택사항
export TNS_ADMIN=/path/to/tns/admin        # 선택사항
```

### MySQL  
```bash
export MYSQL_ADM_USER=root
export MYSQL_PASSWORD=password
export MYSQL_HOST=localhost                # 기본값
export MYSQL_TCP_PORT=3306                 # 기본값
export MYSQL_DB=test                       # 기본값
```

### PostgreSQL
```bash
export PGUSER=postgres
export PGPASSWORD=password
export PGHOST=localhost                    # 기본값
export PGPORT=5432                         # 기본값
export PGDATABASE=postgres                 # 기본값
```

## 실행 흐름

### 1. 준비 단계
```bash
# 1. JDBC 드라이버 다운로드
./download_drivers.sh

# 2. 환경변수 설정
export ORACLE_SVC_USER=testuser
export ORACLE_SVC_PASSWORD=testpass

# 3. 파라미터 파일 준비 (선택사항)
# parameters.properties 편집
```

### 2. 실행 단계
```bash
# Oracle 테스트 (SELECT만)
./run_oracle.sh /path/to/mappers --json --summary

# MySQL 테스트 (모든 SQL)
./run_mysql.sh /path/to/mappers --all --verbose

# PostgreSQL 테스트 (JSON 출력)
./run_postgresql.sh /path/to/mappers --json
```

### 3. 결과 확인
- 콘솔 출력: 실시간 진행 상황
- JSON 파일: `bulk_test_result_YYYYMMDD_HHMMSS.json`

## 출력 결과 분석

### 콘솔 출력 예시
```
=== MyBatis 대량 SQL 실행 테스트 ===
검색 디렉토리: /path/to/mappers
데이터베이스 타입: ORACLE
실행 모드: SELECT만
출력 모드: 요약만

발견된 XML 파일 수: 25
실행할 SQL 수: 147

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

### JSON 출력 구조
```json
{
  "testInfo": {
    "timestamp": "2025-08-21 13:20:50",
    "directory": "/path/to/mappers",
    "dbType": "oracle",
    "totalTests": 147,
    "successCount": 142,
    "failureCount": 5,
    "successRate": 96.6
  },
  "successfulTests": [...],
  "failedTests": [...],
  "fileStatistics": [...]
}
```

## 장점 및 특징

### 1. **완전 자동화**
- XML 파일 재귀 검색
- SQL ID 자동 추출
- 파라미터 자동 인식
- 결과 자동 분석

### 2. **다중 데이터베이스 지원**
- Oracle, MySQL, PostgreSQL 완전 지원
- 데이터베이스별 최적화된 연결
- 표준 환경변수 사용

### 3. **안전한 실행**
- 기본적으로 SELECT만 실행
- INSERT/UPDATE/DELETE는 명시적 옵션 필요
- 환경변수 검증

### 4. **상세한 결과 추적**
- JSON 형태 결과 저장
- 파일별 성공률 분석
- 오류 메시지 상세 기록

### 5. **유연한 설정**
- 외부 설정 파일 지원
- 정규식 패턴 커스터마이징
- 데이터베이스별 기본값 설정

## 사용 시나리오

### 1. 개발 환경 검증
```bash
# 새로운 매퍼 파일들이 제대로 작동하는지 확인
./run_mysql.sh ./src/main/resources/mappers --json
```

### 2. 데이터베이스 마이그레이션 검증
```bash
# Oracle에서 PostgreSQL로 마이그레이션 시 호환성 확인
./run_oracle.sh ./mappers --summary
./run_postgresql.sh ./mappers --summary
```

### 3. 대량 SQL 품질 검사
```bash
# 수백 개의 SQL을 한 번에 검증
./run_oracle.sh ./all-mappers --json --verbose
```

### 4. CI/CD 파이프라인 통합
```bash
# 자동화된 테스트로 품질 보장
./run_mysql.sh ./mappers --summary --json
# JSON 결과를 파싱하여 성공률 확인
```

## 개선 사항 및 특징

### 기존 버전 대비 개선점
1. **리소스 관리 개선**: try-with-resources 패턴 사용
2. **JSON 라이브러리 도입**: Jackson 사용으로 안정적인 JSON 처리
3. **XML 파싱 개선**: DOM 파서로 안정성 향상
4. **설정 외부화**: properties 파일로 유연성 증대
5. **다중 DB 지원**: 단일 코드베이스로 3개 DB 지원

### 확장 가능성
- 새로운 데이터베이스 추가 용이
- 커스텀 SQL 패턴 지원
- 플러그인 아키텍처 가능
- 웹 인터페이스 추가 가능

## 결론

이 도구는 MyBatis 기반 프로젝트에서 대량의 SQL을 효율적으로 테스트할 수 있는 완전한 솔루션을 제공합니다. 다중 데이터베이스 지원, 자동화된 실행, 상세한 결과 추적 등의 기능을 통해 개발 생산성과 코드 품질을 크게 향상시킬 수 있습니다.

특히 대규모 프로젝트나 데이터베이스 마이그레이션 시나리오에서 매우 유용하며, CI/CD 파이프라인에 통합하여 지속적인 품질 보장도 가능합니다.
