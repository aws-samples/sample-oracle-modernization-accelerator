# Database MCP Server - Design Decision

## 기존 시스템 분석

### 현재 방식 (bin/test/run_*.sh)
- **실행 단위**: 디렉토리 전체 (모든 XML 파일)
- **처리 방식**: MyBatis 엔진을 통한 일괄 실행
- **결과**: JSON 파일로 전체 결과 저장
- **장점**:
  - 한 번에 모든 SQL 테스트 가능
  - MyBatis 동적 SQL 완벽 지원
  - 통계 리포트 자동 생성
- **단점**:
  - 특정 SQL만 재실행 불가
  - 실패한 SQL만 다시 테스트 어려움
  - 세밀한 제어 불가

## MCP 서버 설계 방향 결정

### 옵션 1: XML 파일 단위 실행
```
execute_mapper_file(mapper_file_path, bind_variables)
→ 하나의 XML 파일 내 모든 SQL 실행
```

**장점**:
- 기존 방식과 유사한 구조
- 파일 단위 관리 용이
- 배치 실행 효율적

**단점**:
- 특정 SQL만 재실행 불가
- 실패한 SQL 개별 처리 어려움
- 세밀한 제어 부족

### 옵션 2: 개별 SQL 단위 실행 ⭐ **추천**
```
execute_sql(sql_id, mapper_file, bind_variables)
→ 특정 SQL ID만 실행
```

**장점**:
- ✅ **세밀한 제어**: 특정 SQL만 선택 실행
- ✅ **재시도 최적화**: 실패한 SQL만 재실행
- ✅ **변환 후 즉시 테스트**: 변환된 SQL 바로 검증
- ✅ **병렬 처리**: 독립적인 SQL 동시 실행 가능
- ✅ **에이전트 워크플로우 최적화**: 분석-변환-재테스트 루프에 적합

**단점**:
- 전체 실행 시 호출 횟수 증가
- 배치 최적화 필요

### 옵션 3: 하이브리드 방식 ⭐⭐ **최종 추천**
```
# 개별 SQL 실행 (기본)
execute_sql(sql_id, mapper_file, bind_variables)

# 배치 실행 (효율성)
execute_sql_batch(sql_list, bind_variables)

# 전체 매퍼 실행 (편의성)
execute_mapper_file(mapper_file_path, bind_variables)
```

**장점**:
- ✅ 모든 사용 케이스 지원
- ✅ 유연성과 효율성 모두 확보
- ✅ 점진적 마이그레이션 가능

## 최종 설계 결정

### **하이브리드 방식 채택**

#### 이유:
1. **에이전트 워크플로우 최적화**
   - 개별 SQL: 변환 후 즉시 재테스트
   - 배치: 초기 전체 실행 시 효율성
   
2. **기존 기능 완벽 재현**
   - `execute_mapper_file()`: 기존 `run_oracle.sh` 방식
   - `execute_sql()`: 새로운 세밀한 제어
   
3. **확장성**
   - 향후 다양한 실행 패턴 지원
   - 성능 최적화 여지

## MCP Tools 설계

### 1. Connection Management

```python
@mcp_tool
def connect(db_type: str, credentials: dict) -> str:
    """
    데이터베이스 연결 생성
    
    Args:
        db_type: "oracle", "postgresql", "mysql"
        credentials: 연결 정보
        
    Returns:
        connection_id: 연결 식별자
    """
```

### 2. SQL Execution (개별)

```python
@mcp_tool
def execute_sql(
    connection_id: str,
    sql_id: str,
    mapper_file: str,
    bind_variables: dict,
    sql_type: str = "SELECT"
) -> dict:
    """
    개별 SQL 실행 (핵심 기능)
    
    Args:
        connection_id: 데이터베이스 연결 ID
        sql_id: SQL ID (예: "UserMapper.selectUser")
        mapper_file: MyBatis XML 파일 경로
        bind_variables: 바인드 변수
        sql_type: SQL 타입 (SELECT, INSERT, UPDATE, DELETE)
        
    Returns:
        {
            "sql_id": str,
            "status": "success" | "error",
            "result_set": List[dict],
            "row_count": int,
            "execution_time_ms": int,
            "error_message": str | None
        }
    """
```

### 3. SQL Execution (배치)

```python
@mcp_tool
def execute_sql_batch(
    connection_id: str,
    sql_list: List[dict],
    bind_variables: dict
) -> List[dict]:
    """
    여러 SQL 배치 실행
    
    Args:
        connection_id: 데이터베이스 연결 ID
        sql_list: [{"sql_id": str, "mapper_file": str}, ...]
        bind_variables: 공통 바인드 변수
        
    Returns:
        List of execution results
    """
```

### 4. Mapper File Execution (전체)

```python
@mcp_tool
def execute_mapper_file(
    connection_id: str,
    mapper_file: str,
    bind_variables: dict,
    sql_type_filter: str = "SELECT"
) -> dict:
    """
    XML 파일 전체 실행 (기존 방식 호환)
    
    Args:
        connection_id: 데이터베이스 연결 ID
        mapper_file: MyBatis XML 파일 경로
        bind_variables: 바인드 변수
        sql_type_filter: 실행할 SQL 타입 필터
        
    Returns:
        {
            "total": int,
            "success": int,
            "failed": int,
            "results": List[dict]
        }
    """
```

### 5. Result Retrieval

```python
@mcp_tool
def get_execution_result(result_id: str) -> dict:
    """
    저장된 실행 결과 조회
    
    Args:
        result_id: 결과 식별자
        
    Returns:
        Execution result
    """
```

### 6. Metadata Access

```python
@mcp_tool
def get_mapper_sql_list(mapper_file: str) -> List[dict]:
    """
    매퍼 파일의 SQL 목록 조회
    
    Args:
        mapper_file: MyBatis XML 파일 경로
        
    Returns:
        [{"sql_id": str, "sql_type": str, "parameters": List[str]}, ...]
    """

@mcp_tool
def get_table_schema(connection_id: str, table_name: str) -> dict:
    """
    테이블 스키마 정보 조회
    """
```

## 에이전트 워크플로우 통합

### 초기 실행 (전체 테스트)
```python
# 1. 연결 생성
oracle_conn = connect("oracle", oracle_creds)
postgres_conn = connect("postgresql", pg_creds)

# 2. 전체 매퍼 실행 (효율적)
oracle_results = execute_mapper_file(oracle_conn, "UserMapper.xml", bind_vars)
postgres_results = execute_mapper_file(postgres_conn, "UserMapper.xml", bind_vars)

# 3. 결과 비교
differences = compare_results(oracle_results, postgres_results)
```

### 재시도 루프 (개별 SQL)
```python
for diff in differences:
    # 1. LLM 분석
    analysis = llm_analyze(diff)
    
    # 2. SQL 변환
    transformed_sql = transform_sql(diff.sql_id, analysis.guidance)
    
    # 3. 개별 재실행 (빠름!)
    new_result = execute_sql(
        postgres_conn,
        diff.sql_id,
        "UserMapper.xml",
        bind_vars
    )
    
    # 4. 재비교
    if compare_single(oracle_result, new_result):
        mark_as_passed(diff.sql_id)
    else:
        retry_count += 1
```

## MyBatis 엔진 통합

### Java 프로그램 재사용
- 기존 `com.test.mybatis.MyBatisBulkExecutorWithJson` 활용
- Python에서 Java 프로세스 호출
- 표준 입출력으로 통신

### 대안: Python MyBatis 구현
- `lxml`로 XML 파싱
- 동적 SQL 처리 로직 구현
- 장점: 순수 Python, 의존성 감소
- 단점: MyBatis 기능 완벽 재현 어려움

### **결정: Java 프로그램 재사용** ⭐
- 기존 검증된 코드 활용
- MyBatis 동적 SQL 완벽 지원
- 빠른 구현

## 구현 우선순위

### Phase 1: 핵심 기능
1. ✅ `connect()` - 연결 관리
2. ✅ `execute_sql()` - 개별 SQL 실행
3. ✅ `get_mapper_sql_list()` - SQL 목록 조회

### Phase 2: 배치 기능
4. ✅ `execute_sql_batch()` - 배치 실행
5. ✅ `execute_mapper_file()` - 전체 실행

### Phase 3: 고급 기능
6. ✅ `get_table_schema()` - 메타데이터
7. ✅ Result caching
8. ✅ Connection pooling

## 성능 고려사항

### Connection Pooling
- 연결 재사용으로 오버헤드 감소
- 최대 연결 수 제한

### Result Caching
- 동일 SQL 재실행 시 캐시 활용
- 메모리 관리 필요

### Parallel Execution
- 독립적인 SQL 병렬 실행
- 데이터베이스 부하 고려

## 결론

**하이브리드 방식**을 채택하여:
1. **개별 SQL 실행**으로 에이전트 워크플로우 최적화
2. **배치 실행**으로 초기 전체 테스트 효율성 확보
3. **기존 Java 프로그램 재사용**으로 빠른 구현과 안정성 확보

이 설계는 기존 기능을 완벽히 재현하면서도 에이전트의 자동화된 재시도 루프에 최적화되어 있습니다.
