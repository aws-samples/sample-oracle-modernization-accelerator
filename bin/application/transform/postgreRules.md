# ORACLE TO POSTGRESQL SQL TRANSFORMATION RULES

## 🎯 POSTGRESQL MIGRATION EXPERT MODE

**MIGRATION EXPERT MODE ACTIVATED**: This document operates in PostgreSQL migration expert mode, applying comprehensive database expertise for Oracle to PostgreSQL migrations.

**CORE MIGRATION PRINCIPLES**:
- **NO OPTIMIZATION**: Do not optimize or improve the source code structure
- **NO CODE CHANGES**: Do not modify logic, algorithms, or business rules
- **PRESERVE SOURCE STRUCTURE**: Maintain the exact same structure, flow, and organization as the original Oracle code
- **DIRECT CONVERSION ONLY**: Convert Oracle syntax to PostgreSQL syntax while preserving identical functionality and behavior

**UNDOCUMENTED RULE HANDLING**: For Oracle constructs not explicitly documented in this guide, apply PostgreSQL migration expert knowledge to provide semantically equivalent conversions while maintaining the exact source structure and functionality.

## 📋 OVERVIEW

This section provides complete Oracle to PostgreSQL SQL conversion guidelines.
All PostgreSQL-specific rules are embedded directly in this section.
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

## 🔄 CONVERSION PROCESSING ORDER (MANDATORY)

### STEP 1: STRING CONCATENATION (FIRST - ABSOLUTE PRIORITY)
**UNIVERSAL RULE**: Convert ALL `||` operators to `CONCAT()` function - NO EXCEPTIONS

#### Detection and Conversion
- **Pattern**: `expr1 || expr2 || ... || exprN` → `CONCAT(expr1, expr2, ..., exprN)`
- **Scope**: ALL contexts (SELECT, WHERE, HAVING, ORDER BY, inside functions, CDATA sections)
- **Nested Functions**: Process inner-to-outer
  - `UPPER(col1 || ' ' || col2)` → `UPPER(CONCAT(col1, ' ', col2))`
  - `LIKE '%' || #{param} || '%'` → `LIKE CONCAT('%', #{param}, '%')`

#### Critical Patterns (MUST HANDLE ALL)
```sql
-- Simple concatenation
col1 || col2 → CONCAT(col1, col2)

-- Multi-operand concatenation  
a || b || c || d → CONCAT(a, b, c, d)

-- Function-wrapped concatenation
UPPER(a || ' ' || b) → UPPER(CONCAT(a, ' ', b))

-- Parameter mixed concatenation
col || #{param} || 'suffix' → CONCAT(col, #{param}, 'suffix')

-- CDATA section concatenation
<![CDATA[ col1 || col2 ]]> → <![CDATA[ CONCAT(col1, col2) ]]>
```

### STEP 2: ORACLE FUNCTION CONVERSIONS (SECOND)

#### Basic Function Mappings
- `NVL(a, b)` → `COALESCE(a, b)`
- `SYSDATE` → `CURRENT_TIMESTAMP`
- `SUBSTR(str, pos, len)` → `SUBSTRING(str, pos, len)`
- `DECODE(expr, val1, res1, val2, res2, default)` → `CASE WHEN expr = val1 THEN res1 WHEN expr = val2 THEN res2 ELSE default END`
- `USER` → `CURRENT_USER`
- `SYS_GUID()` → `gen_random_uuid()`

#### Date Functions
- `TO_DATE(date_str, 'YYYY-MM-DD')` → `date_str::date`
- `TO_DATE(datetime_str, 'YYYY-MM-DD HH24:MI:SS')` → `to_timestamp(datetime_str, 'YYYY-MM-DD HH24:MI:SS')`
- `ADD_MONTHS(date, n)` → `date + INTERVAL 'n months'`
- `TRUNC(date, 'DD')` → `DATE_TRUNC('day', date)`
- `TRUNC(date, 'MM')` → `DATE_TRUNC('month', date)`

#### Sequence Functions
- `SEQ_NAME.NEXTVAL` → `nextval('seq_name')` (always lowercase)
- `SEQ_NAME.CURRVAL` → `currval('seq_name')` (always lowercase)

#### Pagination
- `ROWNUM <= n` → `LIMIT n`
- `ROWNUM = 1` → `LIMIT 1`

#### String Functions
- `INSTR(str, substr)` → `POSITION(substr IN str)`
- `LPAD(str, len, pad)` → `LPAD(str::text, len, pad)`
- `LISTAGG(col, delim)` → `STRING_AGG(col, delim)`

### STEP 3: SYNTAX CONVERSIONS (THIRD)

#### DUAL Table Removal
- `FROM DUAL` → remove completely
- `SELECT 'Hello' FROM DUAL` → `SELECT 'Hello'`
- `SELECT #{variable} FROM DUAL` → `SELECT #{variable}`

#### Oracle Hint Removal
- Remove ALL Oracle optimizer hints: `/*+ ... */`
- `SELECT /*+ FIRST_ROWS(10) */ * FROM table` → `SELECT * FROM table`

#### Stored Procedure Calls
- `{call PROC()}` → `CALL PROC()`
- Remove curly braces from stored procedure calls

#### Outer Join Conversion
- `(+)` outer join → `LEFT JOIN` or `RIGHT JOIN`
- Convert Oracle (+) syntax to explicit JOIN syntax

#### Subquery Alias Requirements (CRITICAL - MANDATORY)
**ALL FROM clause subqueries MUST have alias in PostgreSQL**

##### Mandatory Alias Patterns
- `FROM (SELECT...)` → `FROM (SELECT...) AS sub1`
- `JOIN (SELECT...)` → `JOIN (SELECT...) AS join_sub1`
- `FROM (SELECT ... UNION SELECT ...)` → `FROM (SELECT ... UNION SELECT ...) AS union_sub1`

##### Systematic Alias Naming
- **Level 1**: `AS sub1`, `AS sub2`, `AS sub3`
- **JOIN subqueries**: `AS join_sub1`, `AS join_sub2`
- **UNION subqueries**: `AS union_sub1`, `AS union_sub2`
- **Nested subqueries**: Each level requires unique alias

### STEP 4: PARAMETER CASTING (FINAL STEP - METADATA-DRIVEN)

#### Metadata Lookup Process (MANDATORY)
1. **File**: `$APP_TRANSFORM_FOLDER/oma_metadata.txt`
2. **Format**: `schema | table | column | data_type`
3. **Case Handling**: Convert SQL column references to lowercase for metadata lookup
   - `o.TOTAL_AMOUNT` → lookup `orders.total_amount`
   - `u.FIRST_NAME` → lookup `users.first_name`
4. **Table Alias Resolution**: Resolve alias to table name before lookup

#### Cast Decision Rules (DEFINITIVE)
```
PostgreSQL Data Type → Cast Syntax
integer, int4 → #{param}::integer
bigint, int8 → #{param}::bigint
numeric, decimal → #{param}::numeric
double precision → #{param}::double precision
real, float4 → #{param}::real
date → #{param}::date
timestamp, timestamp without time zone → #{param}::timestamp
timestamp with time zone, timestamptz → #{param}::timestamptz
boolean → #{param}::boolean
character varying, varchar, char, text → NO CAST (string types)
```

#### Application Contexts (COMPREHENSIVE)
Apply casting to parameters in these contexts:
- **Comparison Operators**: `=`, `!=`, `<>`, `<`, `>`, `<=`, `>=`
- **BETWEEN Clauses**: `BETWEEN #{param1} AND #{param2}` → `BETWEEN #{param1}::type AND #{param2}::type`
- **IN Clauses**: `IN (#{p1}, #{p2}, #{p3})` → `IN (#{p1}::type, #{p2}::type, #{p3}::type)`
- **CASE Conditions**: `WHEN col = #{param}` → `WHEN col = #{param}::type`

#### CDATA Section Processing
Apply casting rules INSIDE CDATA sections with same logic:
```xml
<!-- Input -->
<![CDATA[ AND o.TOTAL_AMOUNT >= #{minAmount} ]]>

<!-- Output (if TOTAL_AMOUNT is double precision) -->
<![CDATA[ AND o.TOTAL_AMOUNT >= #{minAmount}::double precision ]]>
```

#### Error Handling (Conservative)
- **Metadata File Not Found**: Skip CAST processing, log warning
- **Column Not Found**: Skip CAST processing, log warning
- **String Types**: NO casting required
- **Policy**: Never apply CAST without metadata confirmation

## 📄 XML TAG PROCESSING

### Target Tags for SQL Conversion
Apply conversions to SQL content within these tags:
- `<sql>`, `<select>`, `<insert>`, `<update>`, `<delete>`
- `<include>`, `<selectKey>`
- `<resultMap>` (for column mappings)

### Protected Dynamic Tags (DO NOT MODIFY)
- Flow control: `<if>`, `<choose>`, `<when>`, `<otherwise>`
- Iteration: `<foreach>`
- Variable binding: `<bind>`
- Parameters: `#{variable_name}`, `${variable_name}`

### CDATA Processing
**CRITICAL**: Preserve CDATA structure while converting SQL content
- Apply ALL conversion rules within CDATA sections
- Maintain `<![CDATA[` and `]]>` structure
- Convert SQL content inside CDATA following same rules

## 🗺️ RESULTMAP PROCESSING

### Java Type Conversions
- `javaType="oracle.sql.TIMESTAMP"` → `javaType="java.sql.Timestamp"`
- `javaType="oracle.sql.CLOB"` → `javaType="java.lang.String"`
- `javaType="oracle.sql.BLOB"` → `javaType="byte[]"`

### JDBC Type Conversions
- `jdbcType="NUMBER"` → `jdbcType="NUMERIC"`
- `jdbcType="VARCHAR2"` → `jdbcType="VARCHAR"`
- `jdbcType="CLOB"` → `jdbcType="LONGVARCHAR"`
- `jdbcType="BLOB"` → `jdbcType="LONGVARBINARY"`

### MyBatis Bind Variable Type Conversion
When bind variables have type specifications:
- `#{param:CLOB}` → `#{param:LONGVARCHAR}`
- `#{param:NUMBER}` → `#{param:NUMERIC}`
- `#{param:VARCHAR2}` → `#{param:VARCHAR}`
- `#{param,mode=IN,jdbcType=CLOB}` → `#{param,mode=IN,jdbcType=LONGVARCHAR}`

## 🔧 PL/SQL DECLARE SECTION PROCESSING

### Basic Structure Conversion
- `DECLARE` → `DO $$\nDECLARE`
- Add `$$ LANGUAGE plpgsql;` at end of block

### Variable Declaration Rules
- **%TYPE References**: Convert to lowercase: `table.column%TYPE`
- **Data Type Mapping**: `VARCHAR2(n)` → `VARCHAR`, `NUMBER` → `NUMERIC`, `DATE` → `TIMESTAMP`
- **NO Initializations**: Move ALL initializations from DECLARE to BEGIN section

### Variable Management
- Maintain MyBatis bind variable syntax: `#{variable_name}`
- Move bind variable assignments to BEGIN section
- For %TYPE variables: NO type casts to bind variables
- For explicit types: Add appropriate type casts

## ⚙️ PROCESSING INSTRUCTIONS

### Comment Requirements
Add conversion comment inside `<mapper>` tag:
```xml
<!-- YYYY-MM-DD Amazon Q Developer : PostgreSQL conversion applied -->
```

### Logging Requirements
- "METADATA LOOKUP: table.column → data_type"
- "Applied CAST: #{param} → #{param}::{pg_type}"
- "Skipped CAST: #{param} (string type/metadata not found)"

### Final Validation Checklist
- ✅ **String Concatenation**: ALL `||` converted to `CONCAT()`
- ✅ **Function Conversion**: Oracle functions converted to PostgreSQL
- ✅ **Subquery Aliases**: ALL subqueries have aliases
- ✅ **Parameter Casting**: Applied based on metadata lookup
- ✅ **XML Structure**: Preserved completely
- ✅ **CDATA Sections**: SQL converted while structure preserved
- ✅ **MyBatis Syntax**: Dynamic tags and parameters intact

**Note**: Metadata file location is `$APP_TRANSFORM_FOLDER/oma_metadata.txt`
