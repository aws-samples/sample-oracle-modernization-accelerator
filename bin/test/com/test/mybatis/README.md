# MyBatis Bulk Executor (개선된 버전)

MyBatis XML 파일들을 재귀적으로 검색하여 모든 SQL ID를 자동으로 테스트하는 프로그램입니다.

## 주요 개선사항

### 1. 리소스 관리 개선
- try-with-resources 패턴 사용
- 명시적 임시 파일 삭제
- 예외 발생 시에도 안전한 리소스 정리

### 2. JSON 라이브러리 사용
- Jackson 라이브러리를 사용한 안전한 JSON 생성
- 수동 문자열 조작 대신 객체 기반 JSON 생성

### 3. XML 파싱 개선
- DOM 파서를 사용한 안전한 XML 처리
- 정규식 방식을 fallback으로 유지
- 더 정확한 SQL ID 추출

### 4. 설정 파일 외부화
- `mybatis-bulk-executor.properties` 파일로 설정 분리
- 런타임 설정 변경 가능
- 기본값 제공으로 설정 파일 없이도 실행 가능

## 파일 구조

```
├── MyBatisBulkExecutorWithJson.java             # 개선된 메인 클래스
├── MyBatisBulkExecutorWithJson_archive.java     # 기존 버전 (백업)
├── mybatis-bulk-executor.properties             # 설정 파일
├── parameters.properties                        # SQL 파라미터 파일 (선택사항)
├── pom.xml                                      # Maven 의존성 설정
└── README.md                                    # 이 파일
```

## 환경 설정

### 필수 환경변수

#### Oracle
```bash
export ORACLE_SVC_CONNECT_STRING="서비스명"
export ORACLE_SVC_USER="사용자명"
export ORACLE_SVC_PASSWORD="비밀번호"
export ORACLE_HOME="/path/to/oracle/home"
# TNS_ADMIN은 자동으로 $ORACLE_HOME/network/admin으로 설정됨
```

#### MySQL (현재 환경 설정됨)
```bash
export MYSQL_HOST="d-gds-cluster-my-8.cluster-cfk2cceasiqp.ap-northeast-2.rds.amazonaws.com"
export MYSQL_TCP_PORT="3306"
export MYSQL_DB="OAFS"
export MYSQL_ADM_USER="root"
export MYSQL_PASSWORD="testmysql21#!"
```

#### PostgreSQL
```bash
export PGHOST="localhost"
export PGPORT="5432"
export PGDATABASE="postgres"
export PGUSER="사용자명"
export PGPASSWORD="비밀번호"
```

## 빌드 및 실행

### 1. Maven 빌드
```bash
mvn clean package
```

### 2. 실행
```bash
# 기본 실행 (SELECT만)
java -jar target/mybatis-bulk-executor-1.0.0-shaded.jar /path/to/mappers --db mysql

# 모든 SQL 실행
java -jar target/mybatis-bulk-executor-1.0.0-shaded.jar /path/to/mappers --db mysql --all

# JSON 결과 파일 생성
java -jar target/mybatis-bulk-executor-1.0.0-shaded.jar /path/to/mappers --db mysql --json

# 상세 출력
java -jar target/mybatis-bulk-executor-1.0.0-shaded.jar /path/to/mappers --db mysql --verbose

# 요약만 출력
java -jar target/mybatis-bulk-executor-1.0.0-shaded.jar /path/to/mappers --db mysql --summary
```

### 3. 개발 환경에서 직접 실행
```bash
# 컴파일
javac -cp "lib/*" MyBatisBulkExecutorWithJson.java

# 실행
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson /path/to/mappers --db mysql --json
```

## 명령행 옵션

| 옵션 | 설명 | 필수 |
|------|------|------|
| `--db <type>` | 데이터베이스 타입 (oracle, mysql, postgresql) | ✅ |
| `--select-only` | SELECT 구문만 실행 (기본값) | ❌ |
| `--all` | 모든 SQL 구문 실행 (INSERT/UPDATE/DELETE 포함) | ❌ |
| `--summary` | 요약 정보만 출력 | ❌ |
| `--verbose` | 상세 정보 출력 | ❌ |
| `--json` | JSON 결과 파일 생성 | ❌ |

## 설정 파일 (mybatis-bulk-executor.properties)

```properties
# 임시 파일 설정
temp.config.prefix=mybatis-config-
temp.mapper.prefix=mapper-
temp.file.suffix=.xml

# SQL 패턴 설정
sql.pattern.regex=<(select|insert|update|delete)\\s+id="([^"]+)"
example.patterns=byexample,example,selectByExample,selectByExampleWithRowbounds

# MyBatis 설정
mybatis.mapUnderscoreToCamelCase=true
mybatis.transactionManager=JDBC
mybatis.dataSource=POOLED

# 출력 설정
output.json.prefix=bulk_test_result_
output.json.suffix=.json
output.timestamp.format=yyyyMMdd_HHmmss
output.datetime.format=yyyy-MM-dd HH:mm:ss

# 데이터베이스 드라이버 설정
db.oracle.driver=oracle.jdbc.driver.OracleDriver
db.mysql.driver=com.mysql.cj.jdbc.Driver
db.postgresql.driver=org.postgresql.Driver
```

## 출력 결과

### 콘솔 출력
```
=== MyBatis 대량 SQL 실행 테스트 (개선된 버전) ===
검색 디렉토리: /path/to/mappers
데이터베이스 타입: MYSQL
실행 모드: SELECT만
출력 모드: 일반
JSON 출력: 활성화

발견된 XML 파일 수: 15
실행할 SQL 수: 127

=== SQL 실행 테스트 시작 ===
진행률: 100.0% [127/127] UserMapper.xml:selectUserById

=== 실행 결과 요약 ===
총 테스트 수: 127
실제 실행: 115개
스킵됨: 12개 (Example 패턴)
성공: 110개
실패: 5개
실제 성공률: 95.7% (스킵 제외)

📄 JSON 결과 파일 생성: bulk_test_result_20241201_143022.json
```

### JSON 출력 예시
```json
{
  "testInfo": {
    "timestamp": "2024-12-01 14:30:22",
    "directory": "/path/to/mappers",
    "databaseType": "MYSQL",
    "totalTests": 127,
    "successCount": 110,
    "failureCount": 5,
    "successRate": "95.7"
  },
  "successfulTests": [
    {
      "xmlFile": "UserMapper.xml",
      "sqlId": "selectUserById",
      "sqlType": "SELECT",
      "rowCount": 1
    }
  ],
  "failedTests": [
    {
      "xmlFile": "OrderMapper.xml",
      "sqlId": "selectOrderWithDetails",
      "sqlType": "SELECT",
      "errorMessage": "Table 'test.order_details' doesn't exist"
    }
  ],
  "fileStatistics": [
    {
      "fileName": "UserMapper.xml",
      "totalTests": 15,
      "successCount": 14,
      "failureCount": 1,
      "successRate": "93.3"
    }
  ]
}
```

## 주요 특징

1. **자동 Example 패턴 스킵**: `selectByExample` 등 실행 불가능한 SQL 자동 감지
2. **진행률 표시**: 실시간 진행률 및 현재 처리 중인 파일 표시
3. **파일별 통계**: 각 XML 파일별 성공/실패 통계 제공
4. **안전한 리소스 관리**: 임시 파일 자동 정리 및 예외 안전성
5. **유연한 설정**: 외부 설정 파일을 통한 동작 커스터마이징

## 문제 해결

### 1. Jackson 라이브러리 없음
```bash
# Maven으로 의존성 설치
mvn dependency:copy-dependencies
```

### 2. 데이터베이스 드라이버 없음
```bash
# pom.xml에서 필요한 드라이버만 활성화하거나
# 수동으로 JDBC 드라이버 JAR 파일을 classpath에 추가
```

### 3. 설정 파일 없음
- 프로그램이 기본 설정으로 자동 실행됨
- 필요시 `mybatis-bulk-executor.properties` 파일 생성

### 4. 환경변수 미설정
```bash
# 각 데이터베이스별 필수 환경변수 확인 후 설정
# 프로그램 실행 시 오류 메시지에서 필요한 변수 확인 가능
```

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.
