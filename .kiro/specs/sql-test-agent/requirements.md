# Requirements Document

## Introduction

Oracle에서 PostgreSQL/MySQL로 변환된 SQL의 정확성을 검증하고 자동으로 수정하는 에이전트 시스템입니다. 이 시스템은 사전에 생성된 바인드 변수를 사용하여 SQL 실행 및 결과 비교, 차이 분석 및 자동 재변환의 프로세스를 자동화합니다. 바인드 변수 생성은 별도의 도구(bulk_prepare.sh, run_bind_generator.sh)를 통해 수행되며 사람의 검증을 거친 후 에이전트가 이를 활용합니다.

## Glossary

- **Agent**: SQL 테스트 및 변환 프로세스를 자동으로 수행하는 자율 시스템
- **MCP_Server**: Model Context Protocol 서버로, 데이터베이스 연결 및 SQL 실행을 담당하는 백엔드 서비스
- **Bind_Variable**: SQL 쿼리에서 동적으로 값이 할당되는 파라미터 (#{}, ${} 형식)
- **Source_DB**: 원본 데이터베이스 (Oracle)
- **Target_DB**: 변환 대상 데이터베이스 (PostgreSQL 또는 MySQL)
- **Result_Comparator**: 소스와 타겟 DB의 SQL 실행 결과를 비교하는 컴포넌트
- **SQL_Transformer**: 기존 bin/application의 SQL 변환 프로그램을 MCP/Agent 형태로 래핑한 컴포넌트
- **Validation_Loop**: 결과가 일치할 때까지 변환-테스트-분석을 반복하는 프로세스
- **MyBatis_Mapper**: SQL 쿼리가 정의된 XML 파일
- **Sample_Data_Analyzer**: 데이터베이스에서 유효한 샘플 데이터를 추출하고 분석하는 별도 도구 (bulk_prepare.sh, run_bind_generator.sh)
- **LLM_Analyzer**: 대형 언어 모델을 활용하여 SQL 차이를 분석하고 수정 방안을 제안하는 컴포넌트

## Requirements

### Requirement 1: 바인드 변수 파일 검증 및 로드

**User Story:** As a database migration engineer, I want the agent to validate and load pre-generated bind variable files, so that SQL tests can run with realistic and manually-verified data values.

#### Acceptance Criteria

1. WHEN the agent starts, THE Agent SHALL check for the existence of a parameters.properties file in the expected location
2. WHEN parameters.properties file is found, THE Agent SHALL parse and load all bind variable definitions
3. WHEN loading bind variables, THE Agent SHALL validate that all required parameters for the target SQL queries are present
4. IF any required parameter is missing, THEN THE Agent SHALL generate an error report listing missing parameters and halt execution
5. WHEN bind variables are loaded, THE Agent SHALL validate data types match expected SQL parameter types
6. WHEN validation is complete, THE Agent SHALL create a validation report showing parameter coverage and data type compatibility
7. IF the parameters.properties file does not exist, THEN THE Agent SHALL provide instructions to run the separate bind variable generation tool (bulk_prepare.sh or run_bind_generator.sh)

### Requirement 2: 다중 데이터베이스 SQL 실행 및 결과 저장

**User Story:** As a database migration engineer, I want the system to execute SQL queries on both source and target databases with identical bind variables, so that I can compare results accurately.

#### Acceptance Criteria

1. WHEN bind variables are validated, THE MCP_Server SHALL establish connections to Source_DB and Target_DB using environment variables
2. WHEN database connections are established, THE MCP_Server SHALL create result storage tables in Target_DB if they do not exist
3. WHEN SQL queries are executed, THE MCP_Server SHALL use identical bind variable values for both Source_DB and Target_DB
4. WHEN a query executes on Source_DB, THE MCP_Server SHALL capture the result set, execution time, and any errors
5. WHEN a query executes on Target_DB, THE MCP_Server SHALL capture the result set, execution time, and any errors
6. WHEN results are captured, THE MCP_Server SHALL store them in a structured format (JSON) with metadata including SQL ID, timestamp, and database type
7. WHEN all queries are executed, THE Agent SHALL generate an execution summary report with success/failure statistics
8. IF any query fails on either database, THEN THE Agent SHALL log detailed error information including SQL text, bind variables, and error messages

### Requirement 3: 결과 비교 및 차이 식별

**User Story:** As a database migration engineer, I want the system to automatically compare SQL results between source and target databases using string-level comparison, so that I can identify conversion issues clearly.

#### Acceptance Criteria

1. WHEN SQL execution is complete, THE Result_Comparator SHALL compare result sets from Source_DB and Target_DB for each SQL query
2. WHEN comparing results, THE Result_Comparator SHALL normalize data types and formats to account for database-specific differences (numeric precision, date formats, trailing spaces)
3. WHEN comparing results, THE Result_Comparator SHALL perform string-level comparison of normalized result sets
4. WHEN differences are detected, THE Result_Comparator SHALL categorize them as: data mismatch, row count mismatch, column order difference, or type conversion issue
5. WHEN differences are categorized, THE Result_Comparator SHALL generate a detailed comparison report showing exact string differences
6. WHEN the comparison report is generated, THE Agent SHALL prioritize issues by severity (critical data mismatches vs. minor formatting differences)
7. THE Result_Comparator SHALL provide clear before/after views of mismatched results for easy analysis

### Requirement 4: LLM 기반 차이 분석 및 SQL 변환 에이전트 호출

**User Story:** As a database migration engineer, I want the system to analyze SQL differences using LLM and invoke the existing SQL transformation agent with additional guidance, so that conversion issues can be automatically fixed.

#### Acceptance Criteria

1. WHEN differences are identified in the comparison report, THE LLM_Analyzer SHALL analyze the SQL syntax and result differences
2. WHEN analyzing differences, THE LLM_Analyzer SHALL identify the root cause (missing function conversion, incorrect syntax, data type mismatch, etc.)
3. WHEN root cause is identified, THE LLM_Analyzer SHALL generate specific transformation guidance describing what needs to be fixed
4. WHEN transformation guidance is generated, THE Agent SHALL invoke the SQL_Transformer agent (bin/application SQL transformation program wrapped as MCP/Agent)
5. WHEN invoking SQL_Transformer, THE Agent SHALL pass the original SQL, target database type, and additional transformation guidance
6. WHEN SQL_Transformer completes, THE Agent SHALL receive the transformed SQL and update the MyBatis mapper file
7. WHEN mapper files are updated, THE Agent SHALL trigger re-execution of the validation loop (execute SQL, compare results)
8. WHILE differences exist AND iteration count is less than maximum retries, THE Agent SHALL repeat the analysis-transformation-validation cycle
9. WHEN all SQL queries produce matching results OR maximum retries are reached, THE Agent SHALL terminate the validation loop
10. IF maximum retries are reached without convergence, THEN THE Agent SHALL flag problematic queries for manual review with detailed diagnostic information including all attempted transformations

### Requirement 5: MCP 서버 아키텍처 및 도구 제공

**User Story:** As a system architect, I want the agent to use MCP servers for database operations and integrate with the existing SQL transformation agent, so that the system is modular, maintainable, and can leverage existing tools.

#### Acceptance Criteria

1. THE MCP_Server SHALL provide tools for database connection management (connect, disconnect, test connection)
2. THE MCP_Server SHALL provide tools for SQL execution (execute_query, execute_batch, get_results)
3. THE MCP_Server SHALL provide tools for result comparison (compare_results, normalize_data, calculate_diff)
4. THE MCP_Server SHALL provide tools for metadata access (get_table_schema, get_column_info, get_sample_data)
5. THE MCP_Server SHALL provide an interface to invoke the SQL_Transformer agent (bin/application transformation program)
6. WHEN invoking SQL_Transformer, THE MCP_Server SHALL pass parameters including: source SQL, target database type, transformation guidance, and mapper file path
7. WHEN tools are invoked, THE MCP_Server SHALL handle errors gracefully and return structured error responses
8. WHEN database operations are performed, THE MCP_Server SHALL implement connection pooling and timeout management
9. WHEN the Agent requests LLM analysis, THE Agent SHALL provide context including SQL text, error messages, result differences, and schema information

### Requirement 6: 에이전트 자율 실행 및 의사결정

**User Story:** As a database migration engineer, I want the agent to make autonomous decisions during the validation process, so that the system can run without human intervention.

#### Acceptance Criteria

1. WHEN the agent starts, THE Agent SHALL load configuration from environment variables and property files
2. WHEN configuration is loaded, THE Agent SHALL validate all prerequisites (database connectivity, file access, LLM availability)
3. WHEN executing the workflow, THE Agent SHALL make decisions on retry strategies based on error types
4. WHEN SQL transformation fails, THE Agent SHALL try alternative transformation approaches before giving up
5. WHEN results are ambiguous, THE Agent SHALL use confidence scoring to determine if manual review is needed
6. WHEN the agent encounters unrecoverable errors, THE Agent SHALL save state and generate a detailed error report
7. WHEN the workflow completes, THE Agent SHALL provide actionable recommendations for any remaining issues

### Requirement 7: 진행 상황 추적 및 보고

**User Story:** As a database migration engineer, I want to monitor the agent's progress in real-time, so that I can understand what the system is doing and intervene if necessary.

#### Acceptance Criteria

1. WHEN the agent performs any operation, THE Agent SHALL log progress with timestamps and operation details
2. WHEN processing multiple SQL queries, THE Agent SHALL display a progress indicator showing completed/total queries
3. WHEN errors occur, THE Agent SHALL log them with full context (SQL ID, bind variables, error message, stack trace)
4. WHEN the validation loop iterates, THE Agent SHALL track convergence metrics (number of passing queries over time)
5. WHEN the workflow completes, THE Agent SHALL generate a comprehensive report in both human-readable and machine-readable formats
6. THE Agent SHALL provide real-time status updates through a structured logging interface
7. THE Agent SHALL maintain a history of all transformations and test results for audit purposes

### Requirement 8: 데이터 정규화 및 비교 정확성

**User Story:** As a database migration engineer, I want the system to accurately compare results despite database-specific formatting differences, so that false positives are minimized.

#### Acceptance Criteria

1. WHEN comparing numeric values, THE Result_Comparator SHALL normalize precision and scale differences
2. WHEN comparing date/time values, THE Result_Comparator SHALL normalize timezone and format differences
3. WHEN comparing string values, THE Result_Comparator SHALL handle trailing spaces and case sensitivity appropriately
4. WHEN comparing NULL values, THE Result_Comparator SHALL treat NULL, empty string, and zero consistently based on context
5. WHEN comparing result sets, THE Result_Comparator SHALL handle row ordering differences by sorting on primary key columns
6. WHEN column names differ, THE Result_Comparator SHALL match columns by position if names don't match exactly
7. WHEN data type conversions are detected, THE Result_Comparator SHALL validate that conversions are semantically equivalent

### Requirement 9: 설정 관리 및 확장성

**User Story:** As a system administrator, I want to configure the agent's behavior through configuration files, so that I can customize it for different migration scenarios.

#### Acceptance Criteria

1. THE Agent SHALL load configuration from a properties file or environment variables
2. THE Agent SHALL support configuration of database connection parameters for multiple database types
3. THE Agent SHALL support configuration of retry limits, timeout values, and batch sizes
4. THE Agent SHALL support configuration of comparison tolerance levels for numeric and date comparisons
5. THE Agent SHALL support configuration of LLM parameters (model, temperature, max tokens)
6. WHEN configuration is invalid, THE Agent SHALL fail fast with clear error messages
7. THE Agent SHALL support plugin architecture for adding new database types or transformation rules

### Requirement 10: 보안 및 자격 증명 관리

**User Story:** As a security administrator, I want database credentials to be handled securely, so that sensitive information is not exposed.

#### Acceptance Criteria

1. THE Agent SHALL read database credentials from environment variables, not hardcoded values
2. THE Agent SHALL support encrypted credential storage using industry-standard encryption
3. THE Agent SHALL not log or display credentials in plain text
4. WHEN connecting to databases, THE MCP_Server SHALL use secure connection protocols (SSL/TLS) when available
5. WHEN storing results, THE Agent SHALL not include sensitive data in log files or reports
6. THE Agent SHALL support role-based access control for different operations
7. WHEN errors occur, THE Agent SHALL sanitize error messages to remove credential information
