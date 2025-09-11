# Oracle to PostgreSQL DDL Conversion

Convert the following Oracle DDL to PostgreSQL format using comprehensive migration expert rules.

**Object Name:** {OBJECT_NAME}
**Source DBMS:** {SOURCE_DBMS_TYPE}
**Target DBMS:** {TARGET_DBMS_TYPE}

## Original Oracle DDL:
```sql
{ORACLE_DDL}
```

## ⚠️ RDS/Aurora Managed Database 제약사항 사전 검토

변환을 시작하기 전에 다음 Oracle 기능들이 포함되어 있는지 확인하고, 해당하는 경우 사용자에게 알림:

### 🚫 RDS/Aurora에서 직접 구현 불가능한 기능들:
- **파일 시스템 접근**: `UTL_FILE`, `BFILE`, 외부 테이블, `DIRECTORY` 객체
- **네트워크 통신**: `UTL_HTTP`, `UTL_TCP`, `UTL_SMTP`, `UTL_URL`, `UTL_INADDR`
- **외부 프로세스 실행**: `DBMS_SCHEDULER` 외부 작업, OS 명령 실행, `HOST` 명령
- **Java 저장 프로시저**: `CREATE JAVA` 문, Java 클래스 로딩
- **C/C++ 외부 라이브러리**: `CREATE LIBRARY` 문, 외부 라이브러리 호출
- **데이터베이스 링크**: `CREATE DATABASE LINK` (Aurora는 제한적 지원)
- **시스템 패키지**: `DBMS_PIPE`, `DBMS_ALERT`, `DBMS_LOCK` 등 시스템 레벨 패키지

### 💡 대안 솔루션 필요:
위 기능들이 발견되면 다음과 같이 안내:
- **AWS Lambda 함수**로 외부 처리 로직 구현
- **Amazon S3**를 통한 파일 처리
- **Amazon SES**를 통한 이메일 발송
- **Amazon EventBridge**를 통한 스케줄링
- **AWS SDK**를 통한 외부 API 호출
- **RDS Proxy**를 통한 연결 관리

## ⚠️ CRITICAL: Object Type Preservation Rule

**MANDATORY REQUIREMENT**: Oracle object types MUST be preserved in PostgreSQL conversion:

- **Oracle PROCEDURE** → **PostgreSQL PROCEDURE ONLY** 
- **Oracle FUNCTION** → **PostgreSQL FUNCTION ONLY**
- **Oracle PACKAGE** → **PostgreSQL SCHEMA with functions/procedures**

### ✅ REQUIRED: Schema and Naming Conventions
- **Schema Prefix**: Always prefix object names with schema (e.g., `CREATE OR REPLACE PROCEDURE oma.sp_show_order_hierarchy`)
- **PostgreSQL Naming**: Use lowercase for all object names (procedures, functions, tables, columns)
- **Example**: `CREATE OR REPLACE PROCEDURE oma.sp_show_order_hierarchy` (not `SP_SHOW_ORDER_HIERARCHY`)

### ✅ ALLOWED: Suggestions and explanations
- You MAY explain differences between PROCEDURE and FUNCTION
- You MAY suggest when FUNCTION might be more appropriate
- You MAY provide recommendations for future considerations

### ❌ FORBIDDEN: Multiple conversion outputs
- Do NOT provide both PROCEDURE and FUNCTION conversion code
- Do NOT output alternative conversion versions
- The actual DDL conversion MUST match the original object type

### PostgreSQL Procedure Syntax (for Oracle PROCEDURE conversion):
```sql
CREATE OR REPLACE PROCEDURE schema_name.procedure_name(parameters)
LANGUAGE plpgsql
AS $$
DECLARE
    -- declarations
BEGIN
    -- procedure body
    -- Use COMMIT/ROLLBACK if needed
END;
$$;
```

### Key Differences:
- **PROCEDURE**: No RETURNS clause, can use COMMIT/ROLLBACK
- **FUNCTION**: Must have RETURNS clause, cannot use COMMIT/ROLLBACK

**ABSOLUTE RULE: Convert Oracle PROCEDURE to PostgreSQL PROCEDURE only with proper schema prefix and lowercase naming. Suggestions are welcome, but actual conversion must preserve object type.**

## PostgreSQL Migration Expert Conversion Rules

### 🔧 **Critical PostgreSQL Syntax Requirements**
1. **Function Structure**: Must follow exact PostgreSQL syntax
   ```sql
   CREATE OR REPLACE FUNCTION function_name(parameters)
   RETURNS return_type
   LANGUAGE plpgsql
   AS $$
   DECLARE
       -- declarations
   BEGIN
       -- function body
   END;
   $$;
   ```

2. **Loop Syntax**: PostgreSQL FOR loops require proper structure
   ```sql
   FOR record_var IN query_expression LOOP
       -- loop body
   END LOOP;
   ```

3. **Exception Handling**: Must be within BEGIN...END block
   ```sql
   BEGIN
       -- main logic
   EXCEPTION
       WHEN condition THEN
           -- error handling
   END;
   ```

4. **Recursive CTE**: Proper WITH RECURSIVE syntax
   ```sql
   WITH RECURSIVE cte_name AS (
       -- base case (non-recursive term)
       SELECT ...
       UNION ALL
       -- recursive case (recursive term)
       SELECT ... FROM cte_name WHERE ...
   )
   SELECT ... FROM cte_name;
   ```

### 📋 **Mandatory Conversion Rules**

### PHASE 1: STRING CONCATENATION (FIRST - ABSOLUTE PRIORITY)
- Convert ALL `||` operators to `CONCAT()` function - NO EXCEPTIONS
- Pattern: `expr1 || expr2 || ... || exprN` → `CONCAT(expr1, expr2, ..., exprN)`
- Nested Functions: `UPPER(col1 || ' ' || col2)` → `UPPER(CONCAT(col1, ' ', col2))`
- Parameter mixed: `col || #{param} || 'suffix'` → `CONCAT(col, #{param}, 'suffix')`

### PHASE 2: ORACLE FUNCTION CONVERSIONS
#### Basic Function Mappings
- `NVL(a, b)` → `COALESCE(a, b)`
- `SYSDATE` → `CURRENT_TIMESTAMP`
- `SUBSTR(str, pos, len)` → `SUBSTRING(str, pos, len)`
- `DECODE(expr, val1, res1, val2, res2, default)` → `CASE WHEN expr = val1 THEN res1 WHEN expr = val2 THEN res2 ELSE default END`
- `USER` → `CURRENT_USER`
- `SYS_GUID()` → `gen_random_uuid()`
- `INSTR(str, substr)` → `POSITION(substr IN str)`
- `LISTAGG(col, delim)` → `STRING_AGG(col, delim)`

#### Date/Time Functions
- `TO_DATE(date_str, 'YYYY-MM-DD')` → `date_str::date`
- `TO_DATE(datetime_str, 'YYYY-MM-DD HH24:MI:SS')` → `to_timestamp(datetime_str, 'YYYY-MM-DD HH24:MI:SS')`
- `ADD_MONTHS(date, n)` → `date + INTERVAL 'n months'`
- `TRUNC(date, 'DD')` → `DATE_TRUNC('day', date)`
- `TRUNC(date, 'MM')` → `DATE_TRUNC('month', date)`

#### Oracle Date Arithmetic → PostgreSQL Native
- `TRUNC(SYSDATE) - TRUNC(date_col)` → `(CURRENT_DATE - date_col::date)`
- `SYSDATE - date_col` → `(CURRENT_DATE - date_col::date)`
- `date1 - date2` → `(date1::date - date2::date)`
- `NVL(SYSDATE - date_col, default)` → `COALESCE((CURRENT_DATE - date_col::date), default)`

#### Oracle Data Type Conversions
- `NUMBER` → `INTEGER` (for whole numbers)
- `NUMBER(p,s)` → `NUMERIC(p,s)` (for decimals)
- `VARCHAR2(n)` → `VARCHAR(n)`
- `DATE` → `TIMESTAMP` or `DATE`
- `CLOB` → `TEXT`
- `BLOB` → `BYTEA`

**CRITICAL**: Always use consistent data types to avoid procedure overloading issues.

#### Pagination
- `ROWNUM <= n` → `LIMIT n`
- `ROWNUM = 1` → `LIMIT 1`

### PHASE 3: SYNTAX CONVERSIONS
#### DUAL Table and Hints
- `FROM DUAL` → remove completely
- `SELECT 'Hello' FROM DUAL` → `SELECT 'Hello'`
- Remove ALL Oracle optimizer hints: `/*+ ... */`

#### Stored Procedure Calls
- `{call PROC()}` → `CALL PROC()`
- Remove curly braces from stored procedure calls

#### Outer Join Conversion
- `(+)` outer join → `LEFT JOIN` or `RIGHT JOIN`
- Convert Oracle (+) syntax to explicit JOIN syntax

#### Subquery Alias Requirements (CRITICAL)
- `FROM (SELECT...)` → `FROM (SELECT...) AS sub1` (only if no existing alias)
- `JOIN (SELECT...)` → `JOIN (SELECT...) AS join_sub1` (only if no existing alias)
- Preserve existing aliases - DO NOT CHANGE

### PHASE 4: ORACLE HIERARCHICAL QUERIES → POSTGRESQL CONVERSION

#### Oracle CONNECT BY → PostgreSQL Best Practices

**CRITICAL: Analyze the business logic first, then choose the appropriate PostgreSQL pattern:**

#### Pattern 1: Simple Parent-Child Hierarchy (RECOMMENDED)
For most Oracle CONNECT BY queries, use simple UNION ALL instead of WITH RECURSIVE:

**Oracle Pattern:**
```sql
SELECT LPAD(' ', 2*(LEVEL-1)) || data_column
FROM table
START WITH condition
CONNECT BY PRIOR parent_id = child_id
```

**PostgreSQL Pattern (PREFERRED):**
```sql
WITH hierarchy AS (
    -- Level 1: Parent records
    SELECT 
        columns,
        1 AS level,
        LPAD('', 0) || data_column AS output
    FROM table 
    WHERE parent_condition
    
    UNION ALL
    
    -- Level 2: Child records  
    SELECT 
        columns,
        2 AS level,
        LPAD(' ', 2) || data_column AS output
    FROM table t1
    JOIN parent_table t2 ON t1.parent_id = t2.id
    WHERE child_condition
)
SELECT output FROM hierarchy ORDER BY level, sort_columns
```

#### Pattern 2: WITH RECURSIVE (Use only for true recursion)
Only use WITH RECURSIVE when you have unknown depth or true recursive relationships:

**PostgreSQL Pattern:**
```sql
WITH RECURSIVE hierarchy AS (
  -- Base case: NO self-reference allowed
  SELECT columns FROM table WHERE condition
  UNION ALL
  -- Recursive case: MUST reference the CTE name
  SELECT t.columns FROM table t 
  JOIN hierarchy h ON t.parent_column = h.child_column
)
SELECT columns FROM hierarchy
```

#### Conversion Strategy:
1. **Analyze Oracle CONNECT BY logic**
2. **If fixed levels (like Order → Items)**: Use Pattern 1 (UNION ALL)
3. **If unknown depth**: Use Pattern 2 (WITH RECURSIVE)
4. **Always prefer Pattern 1 when possible** - it's simpler, faster, and more maintainable

#### Key Improvements:
- **Avoid complex recursive joins** when simple UNION ALL works
- **Use fixed LPAD values** for known hierarchy levels
- **Separate CTEs** for better readability
- **Clear level indicators** (1, 2, 3, etc.)
- **Proper ordering** by level and business logic

### PHASE 5: POSTGRESQL-SPECIFIC OPTIMIZATIONS

#### Type Safety and Casting
- Always cast columns before date operations: `date_column::date`
- LIMIT/OFFSET parameters: `LIMIT #{param}::bigint`
- Interval construction (PostgreSQL 9.4+): `MAKE_INTERVAL(days => #{param}::integer)`

#### Error Prevention
- Ensure proper SQL clause ordering: `SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT → OFFSET`
- Separate base case from recursive case in CTEs
- Cast parameters to match column types for type safety

## Output Requirements:
1. **DO NOT use fs_write or any file writing tools** - Only provide the converted SQL as text output
2. **RDS/Aurora 제약사항 확인**: 먼저 위의 제약사항 목록을 확인하고, **실제 RDS/Aurora 관리형 데이터베이스에서만 제약이 있는 기능**이 발견되면 다음 형식으로 알림:
   ```
   ⚠️ RDS/Aurora 제약사항 발견:
   - [발견된 기능]: [대안 솔루션 제안]
   ```
   
   **주의**: 다음은 일반적인 Oracle→PostgreSQL 차이점이므로 RDS/Aurora 제약사항으로 표시하지 마세요:
   - `DBMS_OUTPUT` → `RAISE NOTICE` (일반적인 PostgreSQL 변환)
   - `CONNECT BY` → `WITH RECURSIVE` (일반적인 PostgreSQL 변환)
   - `||` → `CONCAT()` (일반적인 PostgreSQL 변환)
   - `ROWNUM` → `ROW_NUMBER()` (일반적인 PostgreSQL 변환)
   - `SYSDATE` → `CURRENT_TIMESTAMP` (일반적인 PostgreSQL 변환)
   - `NVL` → `COALESCE` (일반적인 PostgreSQL 변환)

2. **PostgreSQL 구문 검증**: 생성된 SQL이 다음 요구사항을 만족하는지 확인:
   - 모든 괄호가 올바르게 매칭되는지 확인
   - FOR 루프가 올바른 PostgreSQL 구문을 사용하는지 확인
   - EXCEPTION 블록이 적절한 BEGIN...END 내에 있는지 확인
   - WITH RECURSIVE 구문이 올바른 형태인지 확인
   - 함수 정의가 완전하고 실행 가능한지 확인

3. **Preserve Business Logic**: Maintain identical functionality and behavior
4. **Query Result Identity**: Converted queries MUST produce identical results to original Oracle queries
5. **Direct Conversion Only**: Convert Oracle syntax to PostgreSQL syntax without optimization
6. **Complete Conversion**: Apply ALL conversion rules systematically
7. **Valid PostgreSQL DDL**: Output should be executable PostgreSQL DDL

## Final Output:
**IMPORTANT: Provide ONLY the converted PostgreSQL DDL as plain text. Do NOT use any file writing tools.**

If RDS/Aurora limitations are found, provide the warning first, then provide the converted PostgreSQL DDL as plain text.

**Critical**: The output should be clean, executable PostgreSQL DDL without any formatting, line numbers, or metadata.
