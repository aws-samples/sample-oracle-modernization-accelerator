# ORACLE TO MYSQL SQL TRANSFORMATION RULES

## 🎯 MYSQL MIGRATION EXPERT MODE

**MIGRATION EXPERT MODE ACTIVATED**: This document operates in MySQL migration expert mode, applying comprehensive database expertise for Oracle to MySQL migrations.

**CORE MIGRATION PRINCIPLES**:
- **NO OPTIMIZATION**: Do not optimize or improve the source code structure
- **NO CODE CHANGES**: Do not modify logic, algorithms, or business rules
- **PRESERVE SOURCE STRUCTURE**: Maintain the exact same structure, flow, and organization as the original Oracle code
- **DIRECT CONVERSION ONLY**: Convert Oracle syntax to MySQL syntax while preserving identical functionality and behavior

**UNDOCUMENTED RULE HANDLING**: For Oracle constructs not explicitly documented in this guide, apply MySQL migration expert knowledge to provide semantically equivalent conversions while maintaining the exact source structure and functionality.

## 📋 OVERVIEW

This section provides complete Oracle to MySQL SQL conversion guidelines.
All MySQL-specific rules are embedded directly in this section.
**CRITICAL**: This processes MyBatis XML mapper files - XML structure and CDATA sections must be preserved.

## 🎯 PROCESSING METHODOLOGY

### Individual File Processing (MANDATORY)
- Process EXACTLY ONE file at a time
- Read each file completely before making any changes
- Apply conversion rules step by step for each individual file
- Validate each conversion before proceeding to the next file
- Treat each file as completely unique - never assume similarity
- **XML Structure Preservation**: Maintain all XML tags, attributes, and hierarchy
- **CDATA Protection**: Preserve CDATA sections while converting SQL content within

## 📄 XML TAG PROCESSING

### Target Tags for SQL Conversion
Apply conversions to SQL content within these tags:

#### Basic SQL Tags
- `<sql>`
- `<select>`
- `<insert>`
- `<update>`
- `<delete>`

#### Subquery and Key Tags
- `<include>`
- `<selectKey>`

#### Result Mapping Tags
- `<resultMap>`
  - `<id>`
  - `<r>`
  - `<constructor>`
  - `<collection>`
  - `<association>`
  - `<discriminator>`

#### Parameter Mapping Tags
- `<parameterMap>`
- `<parameter>`

#### Cache Tags
- `<cache>`
- `<cache-ref>`

### Protected Dynamic Tags (DO NOT MODIFY)
- Flow control: `<if>`, `<choose>`, `<when>`, `<otherwise>`
- Iteration: `<foreach>`
- Variable binding: `<bind>`
- Parameters: `#{variable_name}`, `${variable_name}`

### CDATA Processing
**CRITICAL**: Preserve CDATA structure while converting SQL content

#### XML Parsing Error Prevention Rules
**MANDATORY CDATA Usage**: To prevent XML parsing errors during SQL conversion, apply the following rules:

- **Comparison Operators**: Always wrap conditions containing `<`, `>`, `<=`, `>=` operators in CDATA sections
- **Recursive CTE Conditions**: Pay special attention when adding WHERE clauses with LEVEL or depth limiting conditions in recursive CTEs
- **Complex Expressions**: Use CDATA for any SQL containing XML-sensitive characters

#### CDATA Wrapping Examples
```xml
<!-- REQUIRED: Comparison operators in CDATA -->
<select id="getEmployeesByLevel">
    <![CDATA[
        WITH RECURSIVE emp_hierarchy AS (
            SELECT employee_id, manager_id, 1 as level
            FROM employees 
            WHERE manager_id IS NULL
            
            UNION ALL
            
            SELECT e.employee_id, e.manager_id, eh.level + 1
            FROM employees e
            JOIN emp_hierarchy eh ON e.manager_id = eh.employee_id
            WHERE eh.level < #{maxLevel}
        )
        SELECT * FROM emp_hierarchy
        WHERE level <= #{targetLevel}
    ]]>
</select>

<!-- REQUIRED: Multiple comparison operators -->
<select id="getRangeData">
    <![CDATA[
        SELECT * FROM sales 
        WHERE amount >= #{minAmount} 
        AND amount <= #{maxAmount}
        AND created_date > #{startDate}
    ]]>
</select>
```

#### Basic CDATA Conversion Example
```xml
<!-- Original -->
<select id="getEmployee">
    <![CDATA[
        SELECT * FROM emp
        WHERE rownum <= 10  /* Requires conversion */
    ]]>
</select>

<!-- Convert to -->
<select id="getEmployee">
    <![CDATA[
        SELECT * FROM emp
        LIMIT 10
    ]]>
</select>
```

## 🗺️ RESULTMAP PROCESSING

### Java Type Conversions
- `javaType="java.math.BigDecimal"` → `javaType="java.math.BigDecimal"` (keep as is)
- `javaType="oracle.sql.TIMESTAMP"` → `javaType="java.sql.Timestamp"`
- `javaType="oracle.sql.CLOB"` → `javaType="java.lang.String"`
- `javaType="oracle.sql.BLOB"` → `javaType="byte[]"`

### JDBC Type Conversions (MySQL Compatible)
#### **Numeric Types**
- `jdbcType="NUMBER"` → `jdbcType="DECIMAL"`
- `jdbcType="INTEGER"` → `jdbcType="INTEGER"`
- `jdbcType="BIGINT"` → `jdbcType="BIGINT"`
- `jdbcType="SMALLINT"` → `jdbcType="SMALLINT"`
- `jdbcType="TINYINT"` → `jdbcType="TINYINT"`
- `jdbcType="FLOAT"` → `jdbcType="FLOAT"`
- `jdbcType="DOUBLE"` → `jdbcType="DOUBLE"`

#### **String Types**
- `jdbcType="VARCHAR2"` → `jdbcType="VARCHAR"`
- `jdbcType="CHAR"` → `jdbcType="CHAR"`
- `jdbcType="NVARCHAR2"` → `jdbcType="VARCHAR"`
- `jdbcType="NCHAR"` → `jdbcType="CHAR"`
- `jdbcType="CLOB"` → `jdbcType="LONGVARCHAR"`
- `jdbcType="NCLOB"` → `jdbcType="LONGVARCHAR"`

#### **Date/Time Types**
- `jdbcType="DATE"` → `jdbcType="DATE"`
- `jdbcType="TIMESTAMP"` → `jdbcType="TIMESTAMP"`
- `jdbcType="TIMESTAMP_WITH_TIME_ZONE"` → `jdbcType="TIMESTAMP"`
- `jdbcType="TIMESTAMP_WITH_LOCAL_TIME_ZONE"` → `jdbcType="TIMESTAMP"`

#### **Binary Types**
- `jdbcType="BLOB"` → `jdbcType="LONGVARBINARY"`
- `jdbcType="RAW"` → `jdbcType="VARBINARY"`
- `jdbcType="LONG_RAW"` → `jdbcType="LONGVARBINARY"`

#### **Special Types**
- `jdbcType="ROWID"` → `jdbcType="VARCHAR"` (convert to string representation)
- `jdbcType="XMLTYPE"` → `jdbcType="LONGVARCHAR"`

### Column Mapping Verification (MySQL Specific)
- Check column names match MySQL case sensitivity rules
- Verify column data types are compatible with MySQL
- Ensure property names in resultMap match Java entity fields
- **MySQL Case Sensitivity**: Depends on `lower_case_table_names` setting
  - `lower_case_table_names=0`: Case sensitive (Linux default)
  - `lower_case_table_names=1`: Case insensitive (Windows/macOS default)
  - `lower_case_table_names=2`: Case insensitive storage, case sensitive comparison (macOS default)

### MySQL-Specific ResultMap Considerations
#### **Column Name Handling**
```xml
<!-- Oracle style (may need adjustment) -->
<result column="EMP_ID" property="empId" jdbcType="NUMBER"/>

<!-- MySQL compatible (recommended) -->
<result column="emp_id" property="empId" jdbcType="DECIMAL"/>
```

#### **Auto-Generated Keys**
```xml
<!-- Oracle sequence style -->
<selectKey keyProperty="id" resultType="long" order="BEFORE">
    SELECT SEQ_EMP_ID.NEXTVAL FROM DUAL
</selectKey>

<!-- MySQL AUTO_INCREMENT style -->
<selectKey keyProperty="id" resultType="long" order="AFTER">
    SELECT LAST_INSERT_ID()
</selectKey>
```

### Implementation Example
```xml
<!-- Original -->
<resultMap id="empMap" type="Employee">
    <result property="salary" column="SALARY" javaType="java.math.BigDecimal" jdbcType="NUMBER"/>
    <result property="description" column="DESCRIPTION" javaType="oracle.sql.CLOB" jdbcType="CLOB"/>
</resultMap>

<!-- Convert to -->
<resultMap id="empMap" type="Employee">
    <result property="salary" column="SALARY" javaType="java.math.BigDecimal" jdbcType="DECIMAL"/>
    <result property="description" column="DESCRIPTION" javaType="java.lang.String" jdbcType="LONGVARCHAR"/>
</resultMap>
```

## 🔧 MYSQL CONVERSION RULES

### Basic Functions
- `NVL(a, b)` → `IFNULL(a, b)`
- `SYSDATE` → `NOW()`
- `SUBSTR(str, pos, len)` → `SUBSTRING(str, GREATEST(pos, 1), len)`
- `DECODE(...)` → `CASE WHEN ... END`
- `USER` → `USER()`
- `SYS_GUID()` → `UUID()`

### Pagination and Row Limiting
- `ROWNUM <= n` → `LIMIT n`
- `ROWNUM = 1` → `LIMIT 1`

### DUAL Table Removal
- `FROM DUAL` → remove completely
- `SELECT 'Hello' FROM DUAL` → `SELECT 'Hello'`
- `SELECT #{variable} FROM DUAL` → `SELECT #{variable}`

### Oracle Outer Join Conversion
- `(+)` outer join → `LEFT JOIN` or `RIGHT JOIN`
- Convert Oracle (+) syntax to explicit JOIN syntax

### Stored Procedure Calls
- `{call PROC()}` → `CALL PROC()`
- Remove curly braces from stored procedure calls

### Aggregate Functions
- `LISTAGG(col, delim)` → `GROUP_CONCAT(col SEPARATOR delim)`

### Date Functions
- `ADD_MONTHS(date, n)` → `DATE_ADD(date, INTERVAL n MONTH)`
- `MONTHS_BETWEEN(d1, d2)` → `TIMESTAMPDIFF(MONTH, d2, d1)`
- `LAST_DAY(date)` → `LAST_DAY(date)`
- `TRUNC(date, 'DD')` → `DATE(date)`
- `TRUNC(date, 'MM')` → `DATE_FORMAT(date, '%Y-%m-01')`
- `TRUNC(date, 'YYYY')` → `DATE_FORMAT(date, '%Y-01-01')`
- `EXTRACT(YEAR FROM date)` → `YEAR(date)`
- `EXTRACT(MONTH FROM date)` → `MONTH(date)`
- `EXTRACT(DAY FROM date)` → `DAY(date)`

### Sequence Handling
- `SEQ_NAME.NEXTVAL` → `AUTO_INCREMENT` or `LAST_INSERT_ID()`
- `SEQ_NAME.CURRVAL` → `LAST_INSERT_ID()`

#### SelectKey Pattern Processing
```xml
<!-- Original -->
<selectKey keyProperty="id" resultType="long" order="BEFORE">
    SELECT SEQ_EMPLOYEE_ID.NEXTVAL FROM DUAL
</selectKey>

<!-- Convert to -->
<selectKey keyProperty="id" resultType="long" order="AFTER">
    SELECT LAST_INSERT_ID()
</selectKey>
```

### Subquery Alias Requirements (CRITICAL - MySQL Mandatory)
- **ALL FROM clause subqueries MUST have alias in MySQL**
- **NO EXCEPTIONS**: Every `(SELECT ...)` in FROM clause requires alias
- **SCAN RULE**: Search for ALL occurrences of `FROM (` and `JOIN (` patterns

#### Mandatory Alias Patterns
1. **Simple Subquery**: `FROM (SELECT...)` → `FROM (SELECT...) AS sub`
2. **Multiple Subqueries**: Use sequential numbering `AS sub1`, `AS sub2`, `AS sub3`
3. **Nested Subqueries**: Each nesting level gets unique alias
4. **JOIN Subqueries**: `JOIN (SELECT...)` → `JOIN (SELECT...) AS join_sub`
5. **UNION Subqueries**: `FROM (SELECT ... UNION SELECT ...)` → `FROM (SELECT ... UNION SELECT ...) AS union_sub`

#### Systematic Alias Naming Convention
- **Level 1**: `AS sub1`, `AS sub2`, `AS sub3` (sequential)
- **Level 2 (nested)**: `AS inner1`, `AS inner2`, `AS inner3`
- **Level 3 (deep nested)**: `AS deep1`, `AS deep2`, `AS deep3`
- **JOIN subqueries**: `AS join_sub1`, `AS join_sub2`
- **UNION subqueries**: `AS union_sub1`, `AS union_sub2`

#### Detection and Conversion Rules
**CRITICAL SCAN PATTERNS** (Must check ALL):
1. `FROM (SELECT` → `FROM (SELECT ... ) AS sub1`
2. `FROM ( SELECT` → `FROM ( SELECT ... ) AS sub1` (with spaces)
3. `JOIN (SELECT` → `JOIN (SELECT ... ) AS join_sub1`
4. `LEFT JOIN (SELECT` → `LEFT JOIN (SELECT ... ) AS left_sub1`
5. `RIGHT JOIN (SELECT` → `RIGHT JOIN (SELECT ... ) AS right_sub1`
6. `INNER JOIN (SELECT` → `INNER JOIN (SELECT ... ) AS inner_sub1`
7. `FROM (SELECT ... UNION` → `FROM (SELECT ... UNION ... ) AS union_sub1`

#### Conversion Examples
```sql
-- Pattern 1: Simple subquery (COMMON MISS)
-- Oracle
SELECT * FROM (SELECT emp_id FROM employees)
-- MySQL
SELECT * FROM (SELECT emp_id FROM employees) AS sub1

-- Pattern 2: UNION subquery (FREQUENTLY MISSED)
-- Oracle
SELECT * FROM (
    SELECT emp_id, 'A' as type FROM employees_a
    UNION
    SELECT emp_id, 'B' as type FROM employees_b
)
-- MySQL
SELECT * FROM (
    SELECT emp_id, 'A' as type FROM employees_a
    UNION
    SELECT emp_id, 'B' as type FROM employees_b
) AS union_sub1

-- Pattern 3: Nested subqueries (FREQUENT ERROR)
-- Oracle
SELECT * FROM (
    SELECT * FROM (
        SELECT emp_id FROM employees WHERE active = 'Y'
    ) WHERE dept_id = 10
)
-- MySQL
SELECT * FROM (
    SELECT * FROM (
        SELECT emp_id FROM employees WHERE active = 'Y'
    ) AS inner1 WHERE dept_id = 10
) AS sub1

-- Pattern 4: Nested UNION (HIGH ERROR RATE)
-- Oracle
SELECT * FROM (
    SELECT * FROM (
        SELECT emp_id FROM dept_a
        UNION
        SELECT emp_id FROM dept_b
    ) WHERE emp_id > 100
)
-- MySQL
SELECT * FROM (
    SELECT * FROM (
        SELECT emp_id FROM dept_a
        UNION
        SELECT emp_id FROM dept_b
    ) AS inner_union WHERE emp_id > 100
) AS sub1
```

#### Validation Checklist (MANDATORY)
**Before completing conversion, verify:**
1. ✅ **Every `FROM (SELECT` has corresponding `) AS alias`**
2. ✅ **Every `JOIN (SELECT` has corresponding `) AS alias`**  
3. ✅ **Every `FROM (SELECT ... UNION` has corresponding `) AS alias`**
4. ✅ **Nested subqueries have unique aliases at each level**
5. ✅ **No duplicate alias names within same query scope**
6. ✅ **All parentheses are properly balanced**

### String Functions
- `INSTR(str, substr)` → `LOCATE(substr, str)`
- `LPAD(str, len, pad)` → `LPAD(str, len, pad)` (same syntax)
- `TO_CHAR(num)` → `CAST(num AS CHAR)`
- `TO_NUMBER(str)` → `CAST(str AS DECIMAL)`
- `INITCAP(str)` → `CONCAT(UPPER(LEFT(str,1)), LOWER(SUBSTRING(str,2)))`

### String Concatenation
- `str1 || str2` → `CONCAT(IFNULL(str1, ''), IFNULL(str2, ''))`
- **Multiple concatenation**: `str1 || str2 || str3` → `CONCAT(IFNULL(str1, ''), IFNULL(str2, ''), IFNULL(str3, ''))`

### Numeric Functions
- `POWER(n, m)` → `POW(n, m)`
- `CEIL(n)` → `CEILING(n)`
- `TRUNC(n, d)` → `TRUNCATE(n, d)`

### Date Conversion Functions
- `TO_DATE('20250424', 'YYYYMMDD')` → `STR_TO_DATE('20250424', '%Y%m%d')`
- `TO_DATE('2025-04-24 13:45:00', 'YYYY-MM-DD HH24:MI:SS')` → `STR_TO_DATE('2025-04-24 13:45:00', '%Y-%m-%d %H:%i:%s')`

### Date Format Patterns
- Oracle `YYYY` → MySQL `%Y`
- Oracle `MM` → MySQL `%m`
- Oracle `DD` → MySQL `%d`
- Oracle `HH24` → MySQL `%H`
- Oracle `MI` → MySQL `%i`
- Oracle `SS` → MySQL `%s`

### Oracle System Functions
- `USER` → `USER()`
- `SYS_CONTEXT('USERENV', 'SESSION_USER')` → `USER()`
- `USERENV('SESSIONID')` → `CONNECTION_ID()`
- `SYS_GUID()` → `UUID()`

### Advanced NULL Handling
- `NVL2(expr1, expr2, expr3)` → `CASE WHEN (expr1 IS NOT NULL AND expr1 != '') THEN expr2 ELSE expr3 END`
- Mixed type COALESCE: `COALESCE(employee_id, 'N/A')` → `CASE WHEN (employee_id IS NULL OR employee_id = '') THEN 'N/A' ELSE CAST(employee_id AS CHAR) END`

### IS NULL / IS NOT NULL Processing
- `column IS NULL` → `column IS NULL` (same syntax, but behavior may differ)
- `column IS NOT NULL` → `column IS NOT NULL` (same syntax)
- **Empty String vs NULL**:
  - Oracle: `'' IS NULL` returns TRUE
  - MySQL: `'' IS NULL` returns FALSE
  - **Conversion**: `column IS NULL` → `(column IS NULL OR column = '')` (if Oracle empty string behavior needed)

### Stored Procedure Enhancement
- **MySQL Procedure Conversion**: Always use `CALL` format
- `{call PROC()}` → `CALL PROC()`

### Oracle Date Literals
- `DATE '2023-01-01'` → `'2023-01-01'`
- `TIMESTAMP '2023-01-01 12:00:00'` → `'2023-01-01 12:00:00'`

## 🔬 ADVANCED CONVERSIONS

### Hierarchical Queries (CONNECT BY)
Convert to recursive CTEs with specific patterns:

```sql
-- Oracle CONNECT BY (Simple hierarchy)
SELECT employee_id, manager_id, level
FROM employees 
START WITH manager_id IS NULL 
CONNECT BY PRIOR employee_id = manager_id;

-- MySQL Recursive CTE (8.0+)
WITH RECURSIVE emp_hierarchy AS (
    -- Anchor: root nodes
    SELECT employee_id, manager_id, 1 as level
    FROM employees 
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive: child nodes
    SELECT e.employee_id, e.manager_id, eh.level + 1
    FROM employees e
    JOIN emp_hierarchy eh ON e.manager_id = eh.employee_id
)
SELECT employee_id, manager_id, level FROM emp_hierarchy;
```

### ROWNUM Conversion Patterns

#### Simple ROWNUM
- `WHERE ROWNUM <= n` → `LIMIT n`
- `WHERE ROWNUM = 1` → `LIMIT 1`

#### Complex ROWNUM (Pagination)
```sql
-- Oracle nested ROWNUM
SELECT * FROM (
    SELECT ROWNUM as rn, a.* FROM (
        SELECT * FROM table ORDER BY column
    ) a WHERE ROWNUM <= 20
) WHERE rn > 10;

-- MySQL LIMIT/OFFSET
SELECT * FROM table 
ORDER BY column 
LIMIT 10 OFFSET 10;
```

### MERGE Statements
Convert to INSERT ... ON DUPLICATE KEY UPDATE:
```sql
-- Oracle MERGE
MERGE INTO target USING source ON (condition)
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...

-- MySQL
INSERT INTO target SELECT ... FROM source
ON DUPLICATE KEY UPDATE 
    column = VALUES(column);
```

### Regular Expressions
- `REGEXP_LIKE(col, pattern)` → `col REGEXP pattern`
- `REGEXP_REPLACE(col, pattern, replacement)` → `REGEXP_REPLACE(col, pattern, replacement)`

## 🎯 MIGRATION EXPERT-LEVEL CONVERSION GUIDANCE

### Rule Application Priority (STRICT HIERARCHY)
**Priority 1 (HIGHEST)**: Explicit rules documented in this file
**Priority 2 (MEDIUM)**: Database migration expert knowledge for undocumented Oracle constructs

### For Oracle Constructs Not Explicitly Listed
**MySQL Migration Expert Mode**: When encountering Oracle SQL constructs, functions, or syntax patterns that are not explicitly documented in the above rules, apply MySQL migration expert knowledge to provide appropriate conversions while maintaining semantic equivalence and preserving the exact source structure.

**MIGRATION CONSTRAINTS**:
- **NO OPTIMIZATION**: Do not optimize queries, indexes, or performance
- **NO REFACTORING**: Do not restructure or reorganize code
- **PRESERVE LOGIC**: Maintain identical business logic and data flow
- **DIRECT SYNTAX CONVERSION**: Convert only the database-specific syntax elements

**ONLY apply expert knowledge when Priority 1 rules don't exist**

When encountering Oracle SQL constructs, functions, or syntax patterns that are not explicitly documented in the above rules:

#### **Step 1: Check Explicit Rules First**
- Scan all documented conversion rules in this file
- If explicit rule exists → Apply it (Priority 1)
- If no explicit rule exists → Proceed to Step 2

#### **Step 2: Apply Database Migration Expert Knowledge** (Priority 2)
Apply **database migration expert knowledge** to provide appropriate MySQL equivalents:

#### **Migration Conversion Principles:**
1. **Semantic Equivalence**: Ensure the MySQL conversion maintains the same logical behavior as the original Oracle construct
2. **Structure Preservation**: Maintain the exact same code structure, organization, and flow
3. **No Optimization**: Do not optimize performance, queries, or code structure - preserve original approach
4. **Direct Syntax Conversion**: Convert only Oracle-specific syntax to MySQL equivalents
5. **Standards Compliance**: Prefer ANSI SQL standard approaches when available in MySQL
6. **MySQL Compatibility**: Use MySQL-specific features only when required for functional equivalence

#### **Common Expert Conversion Patterns:**

**Oracle Aggregate Functions:**
- Apply MySQL aggregate function equivalents with proper syntax
- Consider `GROUP_CONCAT()` for string concatenation aggregates
- Use MySQL 8.0+ window functions for advanced aggregation

**Oracle Analytical Functions:**
- Most Oracle window functions have direct MySQL equivalents
- Maintain `OVER()` clause syntax and partitioning logic
- Convert Oracle-specific analytical functions to MySQL alternatives

**Oracle System Functions:**
- Map Oracle system functions to appropriate MySQL system information functions
- Use `USER()`, `DATABASE()`, `VERSION()` etc. as needed
- Convert Oracle metadata queries to MySQL information_schema queries

**Oracle Data Type Functions:**
- Convert Oracle type conversion functions to MySQL casting syntax
- Use `CAST(value AS type)` as appropriate
- Handle Oracle-specific data types with MySQL equivalents

## ⚙️ PROCESSING INSTRUCTIONS

### Step-by-Step Process
1. **Parse Input XML**: Extract ALL SQL content while preserving XML structure
2. **Apply Conversion Rules**: Execute all MySQL transformation rules
3. **Validate Results**: Ensure XML structure and MyBatis functionality preserved

### Comment Requirements

#### Comment Location
- Inside `<mapper>` tag
- Above SQL definition tags

#### Comment Format
```xml
<!-- YYYY-MM-DD Amazon Q Developer : MySQL [feature/function] applied -->

Example:
<mapper namespace="AuthListDAO">
    <!-- 2025-04-27 Amazon Q Developer : MySQL date formatting applied -->
    <sql id="selectAuthListQuery">
```

### Final Error Checks

#### Structure Checks
- **XML tag structure damage**: Verify all opening/closing tags match
- **CDATA section integrity**: Ensure `<![CDATA[` and `]]>` pairs are intact
- **Dynamic query tags**: Verify `<if>`, `<choose>`, `<foreach>` tags are preserved
- **Attribute preservation**: Maintain all XML attributes (id, parameterType, resultType, etc.)

#### Functional Checks
- **Dynamic query tags operation**: Ensure flow control tags work correctly
- **Variable binding syntax accuracy**: Verify `#{variable}` and `${variable}` patterns are intact
- **ResultMap integrity**: Check that resultMap references and column mappings are valid
- **Parameter mapping**: Ensure parameterMap and parameter tags function correctly

#### SQL Syntax Validation
- **MySQL compatibility**: Verify converted SQL is valid MySQL syntax
- **Bind variable preservation**: Ensure MyBatis bind variables are not corrupted
- **CDATA SQL conversion**: Confirm SQL within CDATA sections is properly converted

## 🚀 PERFORMANCE CONSIDERATIONS

- Use MySQL 8.0+ features for optimal performance
- Leverage window functions instead of complex subqueries
- Apply efficient pagination with LIMIT OFFSET
- Use AUTO_INCREMENT instead of sequences for better performance

## 🐛 COMMON ERROR PATTERNS TO FIX

- `Truncated incorrect INTEGER value` → Add `CAST(parameter AS SIGNED)` 
- `Incorrect datetime value` → Add `CAST(parameter AS DATETIME)`
- `invalid input syntax for type numeric` → Add null/empty checks before casting
- **NULL-related issues**:
  - Unexpected NULL results in string concatenation → Use `CONCAT()` or `IFNULL()`
  - Empty string vs NULL confusion → Check Oracle vs MySQL empty string behavior
  - `LENGTH('')` returning different values → Be aware of Oracle vs MySQL differences
