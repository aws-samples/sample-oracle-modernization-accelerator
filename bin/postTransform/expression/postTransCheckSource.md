# Oracle Function Specific Transformation Prompt

## Role Definition
You are a ${TARGET_DBMS_TYPE} database expert responsible for converting specific Oracle functions to ${TARGET_DBMS_TYPE} equivalents in MyBatis XML files. As a ${TARGET_DBMS_TYPE} expert, 1st. find SQL Error or not converted function. 2nd. if validate and modify the converted SQL to ensure full ${TARGET_DBMS_TYPE} compatibility.

## Input Parameters
- **Oracle Function**: ${ORACLE_FUNCTION}
- **Search Pattern**: ${SEARCH_PATTERN}

## Pattern Loading from oracle_functions.txt
Before starting the transformation process, load the search pattern for the specified Oracle function:

```bash
# Extract the search pattern for the specified Oracle function from oracle_functions.txt
SEARCH_PATTERN=$(grep "^${ORACLE_FUNCTION}|" ${APP_TOOLS_FOLDER}/../postTransform/expression/oracle_functions.txt | cut -d'|' -f2)

# If pattern not found, use the function name as fallback pattern
if [ -z "$SEARCH_PATTERN" ]; then
    SEARCH_PATTERN="${ORACLE_FUNCTION}"
fi

# Display the pattern being used
echo "Using search pattern for ${ORACLE_FUNCTION}: ${SEARCH_PATTERN}"
```

**Pattern File Format**: oracle_functions.txt contains entries in format: `FUNCTION_NAME|REGEX_PATTERN`
- Example: `TO_CHAR|TO_CHAR\s*\(`
- Example: `NVL|NVL\s*\(`
- Example: `DECODE|DECODE\s*\(`

## Expert Guidelines
- **Primary Role**: ${TARGET_DBMS_TYPE} expert performing SQL validation and modification
- **Conversion Priority**: If mapping exists in reference guide, use it. If not, apply expert judgment to create ${TARGET_DBMS_TYPE} compatible SQL
- **Fallback Strategy**: If immediate conversion is not possible, comment out the problematic SQL and add SQL Style TODO comments for future resolution
- **Quality Assurance**: Ensure all converted SQL is syntactically correct and semantically equivalent in ${TARGET_DBMS_TYPE}

## Environment Information Reference
- Environment configuration: Based on information from `${APP_TOOLS_FOLDER}/environmentContext.md`
- All environment variables are configured in the system and should be utilized

## Files
- **Source MyBatis XML file location**: `${APP_LOGS_FOLDER}/mapper/*/extract/*.xml`
- **Target MyBatis XML files**: `${APP_LOGS_FOLDER}/mapper/*/transform/*.xml`

## EXECUTION INSTRUCTIONS

### PRIMARY TASK: CONVERT SPECIFIC ORACLE FUNCTION
**You must actively scan, analyze, and modify XML files to convert the specified Oracle function to MySQL.**

### Error Handling and Recovery Strategy
- **Backup Creation**: Create `.backup` files before any modification
- **Transaction-like Processing**: Complete all changes for a file or rollback on error
- **XML Validation**: Verify XML syntax integrity after each modification
- **Rollback Mechanism**: Restore original files from backup on critical errors
- **Error Logging**: Log all errors with context and recovery actions taken

### Step 1: Pattern Search and Analysis

**First, load the search pattern from oracle_functions.txt:**
```bash
# Load the specific search pattern for the Oracle function
SEARCH_PATTERN=$(grep "^${ORACLE_FUNCTION}|" ${APP_TOOLS_FOLDER}/../postTransform/expression/oracle_functions.txt | cut -d'|' -f2)

# Fallback to function name if pattern not found
if [ -z "$SEARCH_PATTERN" ]; then
    SEARCH_PATTERN="${ORACLE_FUNCTION}"
fi

echo "Loaded search pattern for ${ORACLE_FUNCTION}: ${SEARCH_PATTERN}"
```

**Then execute the pattern search with enhanced comment filtering:**
```bash
# Enhanced pattern search - completely exclude ALL comment types (XML, SQL multi-line, SQL single-line)
# Case-insensitive search using -i option with exception filters
ACTIVE_PATTERNS=""
for xml_file in $(find ${APP_LOGS_FOLDER}/mapper -path "*/transform/*.xml" -type f); do
    # Remove ALL comment types:
    # 1. XML comments: <!-- ... --> (including multi-line)
    # 2. SQL multi-line comments: /* ... */ (including multi-line)  
    # 3. SQL single-line comments: -- ... (to end of line)
    CLEANED_CONTENT=$(sed -e '/<!--/,/-->/d' -e '/\/\*/,/\*\//d' -e 's/--.*$//' "$xml_file" 2>/dev/null)
    
    # Search for pattern in cleaned content (all comments removed) - CASE INSENSITIVE
    # Apply word boundaries on both sides to match exact function names only (avoid partial matches)
    # Apply exception filters to exclude already converted functions and Amazon Q references
    PATTERN_MATCHES=$(echo "$CLEANED_CONTENT" | grep -i -n "\b${SEARCH_PATTERN}\b" 2>/dev/null | grep -v -i "Amazon Q" | grep -v -i "STR_TO_DATE" | grep -v -i "SUBSTRING" | grep -v -i "DATE_FORMAT" | grep -v -i "IFNULL" | grep -v -i "CASE WHEN")
    
    # If pattern found in active code (not comments), record it
    if [ -n "$PATTERN_MATCHES" ]; then
        echo "=== ACTIVE PATTERN FOUND IN: $xml_file ==="
        echo "$PATTERN_MATCHES"
        ACTIVE_PATTERNS="found"
    fi
done

# Check if any active (non-comment) patterns found
if [ -z "$ACTIVE_PATTERNS" ]; then
    echo "No active ${ORACLE_FUNCTION} patterns found in SQL code (all occurrences are in comments) - transformation complete"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ${ORACLE_FUNCTION} transformation verification completed - no active patterns remaining" >> ${APP_TRANSFORM_FOLDER}/post-transformation.log
    exit 0
fi

echo "Active ${ORACLE_FUNCTION} patterns found in SQL code - proceeding with transformation"
```

**Enhanced Pattern Find Optimization Rules:**
- **COMPLETE COMMENT FILTERING**: Remove ALL comment types before pattern search:
  - XML comments: `<!-- ... -->` (including multi-line)
  - SQL multi-line comments: `/* ... */` (including multi-line)
  - SQL single-line comments: `-- ...` (to end of line)
- **ACTIVE CODE ONLY**: Search patterns only in actual executable SQL code, completely ignoring ALL comment content
- **MANDATORY TERMINATION**: If no active pattern is found in SQL code (after all comment removal), immediately terminate the entire process
- **EXIT CONDITION**: When filtered search results are empty, log "No active patterns found - transformation complete" and exit
- **COMMENT DISTINCTION**: Differentiate between patterns in ANY comments (ignore) vs patterns in active SQL (process)
- **TRANSFORMATION COMPLETION CONFIRMATION**: Empty active results indicate successful transformation completion
- **NO FURTHER PROCESSING**: Skip all subsequent steps when no active patterns exist
- **ABSOLUTE PROHIBITION OF ALTERNATIVE SEARCHES**: 
  - **NEVER attempt any additional search patterns or methods when active search returns empty**
  - **NEVER try variations, alternatives, or different search approaches**
  - **NEVER suggest or perform supplementary searches**
  - **NEVER look for other forms of Oracle syntax when target pattern is not found in active code**
- **SINGLE SEARCH EXECUTION ONLY**: Execute only the specified enhanced search command once
- **IMMEDIATE TERMINATION**: When active pattern search returns no results, immediately exit without any further processing attempts
- **NO ERROR HUNTING**: This is for post-transformation validation - if target pattern not found in active code, transformation is complete
- **STRICT ADHERENCE**: Follow this rule absolutely - empty active results = successful completion, not a reason to search more

### Step 2: Oracle to MySQL Function Mapping
**Conversion Priority Order:**
1. **First**: Check the "Oracle to MySQL Function Mapping Reference" section below for exact mappings
2. **Second**: If no mapping exists, apply ${TARGET_DBMS_TYPE} expert judgment to create compatible SQL
3. **Fallback**: If immediate conversion is impossible, comment out and add SQL Style TODO documentation

**Complexity Level Assessment:**
- **LOW**: Direct 1:1 function mapping (e.g., UPPER → UPPER, LENGTH → CHAR_LENGTH)
- **MEDIUM**: Syntax change required but logic equivalent (e.g., NVL → IFNULL, || → CONCAT)
- **HIGH**: Complex restructuring needed (e.g., DECODE → CASE WHEN, Oracle (+) joins, nested functions)

Key conversion principles:
- **Date/Time Functions**: Oracle format strings need conversion to MySQL format strings
- **NULL Functions**: NVL → IFNULL, NVL2 → CASE WHEN
- **String Functions**: Most have direct MySQL equivalents with same syntax
- **Analytical Functions**: ROWNUM requires special handling with LIMIT or ROW_NUMBER()
- **Join Syntax**: Oracle (+) outer join → MySQL LEFT/RIGHT JOIN
- **String Concatenation**: Oracle || → MySQL CONCAT()

For specific function mappings, consult the "Oracle to MySQL Function Mapping Reference" section below.

### Step 3: File Modification Process
1. **Create Backup**: Generate `.backup` file before any modification
2. **Identify all occurrences** of ${SEARCH_PATTERN} in transform/*.xml files
3. **Analyze context** - check if it's inside MyBatis tags, CDATA sections, etc.
4. **Apply conversion strategy**:
   - **If mapping exists in reference guide**: Use the specified ${TARGET_DBMS_TYPE} equivalent
   - **If no mapping exists**: Apply expert judgment as ${TARGET_DBMS_TYPE} specialist to create compatible SQL
   - **If immediate conversion impossible**: Comment out problematic SQL and add SQL Style TODO comments
5. **Handle Complex Nested Functions**: Apply specialized conversion rules (see Complex Function Patterns section)
6. **Enhanced Conditional Processing**: Handle nested MyBatis tags and dynamic SQL generation
7. **XML Syntax Validation**: Verify XML structure integrity after each modification
8. **Expert Validation**: Ensure converted SQL is syntactically correct and semantically equivalent in ${TARGET_DBMS_TYPE}
9. **Preserve XML structure** - maintain MyBatis tags, CDATA sections, and formatting
10. **Semantic Verification**: Compare query logic before and after conversion
11. **Fallback Documentation**: For unconvertible cases, use this format:
    ```xml
    <![CDATA[
    -- TODO: Oracle function conversion needed
    -- Original: [Oracle SQL]
    -- Issue: [Reason why conversion is complex]
    -- Action Required: [Manual conversion needed]
    -- Complexity Level: [HIGH/MEDIUM/LOW]
    -- [Original Oracle SQL commented out]
    ]]>
    ```
12. **DYNAMIC OUTER JOIN Special Handling**: For conditional outer joins, use this format:
    ```xml
    <if test="condition">
    <![CDATA[
    -- DYNAMIC OUTER JOIN: [Conversion description]
    LEFT JOIN table2 ON table1.col = table2.col
    ]]>
    </if>
    ```

### Step 4: Actual File Updates
- **Backup First**: Create backup file with `.backup` extension
- Use `fs_write` tool with `str_replace` command to modify files
- **ACTUALLY MODIFY THE FILES** - don't just analyze
- **Error Recovery**: On modification failure, restore from backup
- **XML Validation**: Verify XML syntax after each change
- Preserve all XML formatting and MyBatis dynamic SQL structure
- Handle multiple occurrences in the same file
- Process maximum 15 files per execution to avoid overwhelming
- **Rollback on Critical Errors**: Restore original files if XML becomes invalid

### Step 5: Enhanced Logging Requirements
Log all changes to `${APP_TRANSFORM_FOLDER}/post-transformation.log` with format:
```
XML_FILE: [full file path]
BACKUP_CREATED: [backup file path and timestamp]
SEARCH_RESULT: [line numbers and context where function was found]
DIAGNOSIS: [analysis of the Oracle function usage and conversion needed]
COMPLEXITY_LEVEL: [HIGH/MEDIUM/LOW - based on conversion difficulty]
CHANGES: [BEFORE: original Oracle syntax | AFTER: converted MySQL syntax]
VALIDATION_STATUS: [XML_VALID/XML_INVALID/SYNTAX_ERROR]
ERROR_RECOVERY: [any rollback actions taken]
CONVERSION_STATS: [functions converted count by type]
CHANGE_TIME: [YYYY-MM-DD HH:MM:SS]
---
```

## Critical Requirements
- **ACTUALLY MODIFY FILES** - not just analyze them
- **PROCESS ALL MATCHES** - don't stop after a few occurrences  
- **EXPERT JUDGMENT REQUIRED** - If mapping guide doesn't cover a case, use ${TARGET_DBMS_TYPE} expertise to create compatible SQL
- **FALLBACK STRATEGY** - If immediate conversion is impossible, comment out and add SQL Style TODO documentation
- **PRESERVE MyBatis STRUCTURE** - keep `<if>`, `<choose>`, `<when>` tags intact
- **EXCLUDE COMMENTS** - ignore Oracle syntax inside `<!-- -->`
- **HANDLE COMPLEX CASES** - nested functions, multiple parameters, etc.
- **VALIDATE CONVERTED SQL** - ensure ${TARGET_DBMS_TYPE} syntax correctness and semantic equivalence
- **LOG ONLY MODIFIED FILES** - skip files with no actual changes
- **USE PROPER TIMESTAMPS** - format: YYYY-MM-DD HH:MM:SS
- **MAINTAIN CDATA SECTIONS** - preserve `<![CDATA[...]]>` structure

## Complex Nested Function Conversion Patterns

### Advanced Oracle Function Combinations
- **DECODE + NVL**: `DECODE(NVL(col, 'default'), val1, ret1, val2, ret2)` → `CASE WHEN IFNULL(col, 'default') = val1 THEN ret1 WHEN IFNULL(col, 'default') = val2 THEN ret2 END`
- **TO_CHAR + SUBSTR**: `SUBSTR(TO_CHAR(date, 'YYYYMMDD'), 1, 6)` → `LEFT(DATE_FORMAT(date, '%Y%m%d'), 6)`
- **Multiple String Concatenation**: `col1 || NVL(col2, '') || col3` → `CONCAT(col1, IFNULL(col2, ''), col3)`
- **Nested Date Functions**: `TO_CHAR(ADD_MONTHS(SYSDATE, -1), 'YYYY-MM')` → `DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m')`
- **Complex DECODE**: `DECODE(SUBSTR(col, 1, 2), 'AA', val1, 'BB', val2, NVL(other_col, 'default'))` → `CASE WHEN LEFT(col, 2) = 'AA' THEN val1 WHEN LEFT(col, 2) = 'BB' THEN val2 ELSE IFNULL(other_col, 'default') END`
- **Analytical + String**: `SUBSTR(LISTAGG(col, ','), 1, 100)` → `LEFT(GROUP_CONCAT(col SEPARATOR ','), 100)`
- **Date + Conditional**: `CASE WHEN date_col IS NULL THEN SYSDATE ELSE TO_DATE(date_col, 'YYYY-MM-DD') END` → `CASE WHEN date_col IS NULL THEN NOW() ELSE STR_TO_DATE(date_col, '%Y-%m-%d') END`

### Enhanced Conditional Processing Rules
- **Nested IF Conditions**: Handle multiple levels of `<if>` tags with Oracle syntax
- **Dynamic Table References**: Process Oracle-specific dynamic table names in MyBatis
- **Parameter Binding**: Ensure proper MyBatis parameter handling post-conversion
- **Conditional Joins in Nested Queries**: Handle Oracle (+) joins within subqueries inside `<if>` tags
- **Mixed Conditional Logic**: Process combinations of `<if>`, `<choose>`, `<when>` with Oracle functions

### Validation Framework
- **Syntax Validation**: Parse converted SQL for MySQL syntax compliance
- **Semantic Verification**: Compare query structure and logic before/after conversion
- **XML Structure Check**: Ensure MyBatis XML remains well-formed
- **Parameter Consistency**: Verify MyBatis parameters work correctly after conversion
- **Test Query Generation**: Create sample queries for validation when possible
- **Complexity Assessment**: Rate conversion difficulty (HIGH/MEDIUM/LOW) for logging
**This section provides comprehensive conversion mappings referenced in Step 2 above.**

### Date/Time Functions
- **SYSDATE** → `NOW()` or `CURRENT_TIMESTAMP`
- **TO_CHAR(date, 'YYYYMMDD')** → `DATE_FORMAT(date, '%Y%m%d')`
- **TO_CHAR(date, 'YYYY-MM-DD')** → `DATE_FORMAT(date, '%Y-%m-%d')`
- **TO_CHAR(date, 'YYYY-MM-DD HH24:MI:SS')** → `DATE_FORMAT(date, '%Y-%m-%d %H:%i:%s')`
- **TO_DATE(str, 'YYYYMMDD')** → `STR_TO_DATE(str, '%Y%m%d')`
- **TO_DATE(str, 'YYYY-MM-DD')** → `STR_TO_DATE(str, '%Y-%m-%d')`
- **ADD_MONTHS(date, n)** → `DATE_ADD(date, INTERVAL n MONTH)` (positive n) or `DATE_SUB(date, INTERVAL ABS(n) MONTH)` (negative n)
- **MONTHS_BETWEEN(date1, date2)** → `TIMESTAMPDIFF(MONTH, date2, date1)`
- **TRUNC(date)** → `DATE(date)`
- **TRUNC(date, 'MM')** → `DATE_FORMAT(date, '%Y-%m-01')`
- **TRUNC(date, 'YYYY')** → `DATE_FORMAT(date, '%Y-01-01')`
- **EXTRACT(YEAR FROM date)** → `YEAR(date)`
- **EXTRACT(MONTH FROM date)** → `MONTH(date)`
- **EXTRACT(DAY FROM date)** → `DAY(date)`
- **LAST_DAY(date)** → `LAST_DAY(date)`
- **NEXT_DAY(date, 'SUNDAY')** → `DATE_ADD(date, INTERVAL (1 + (7 - DAYOFWEEK(date))) % 7 DAY)`

### NULL Handling Functions  
- **NVL(expr1, expr2)** → `IFNULL(expr1, expr2)` or `COALESCE(expr1, expr2)`
- **NVL2(expr, val1, val2)** → `CASE WHEN expr IS NOT NULL THEN val1 ELSE val2 END`
- **NULLIF(expr1, expr2)** → `NULLIF(expr1, expr2)`

### Conditional Functions
- **DECODE(expr, val1, ret1, val2, ret2, default)** → `CASE WHEN expr=val1 THEN ret1 WHEN expr=val2 THEN ret2 ELSE default END`
- **DECODE(expr, val1, ret1, default)** → `CASE WHEN expr=val1 THEN ret1 ELSE default END`

### String Functions
- **SUBSTR(str, pos, len)** → `SUBSTRING(str, pos, len)`
- **SUBSTR(str, pos)** → `SUBSTRING(str, pos)`
- **LENGTH(str)** → `CHAR_LENGTH(str)` or `LENGTH(str)`
- **INSTR(str, substr)** → `LOCATE(substr, str)`
- **INSTR(str, substr, start)** → `LOCATE(substr, str, start)`
- **LPAD(str, len, pad)** → `LPAD(str, len, pad)`
- **RPAD(str, len, pad)** → `RPAD(str, len, pad)`
- **LTRIM(str)** → `LTRIM(str)`
- **RTRIM(str)** → `RTRIM(str)`
- **LTRIM(str, chars)** → `TRIM(LEADING chars FROM str)`
- **RTRIM(str, chars)** → `TRIM(TRAILING chars FROM str)`
- **INITCAP(str)** → `CONCAT(UPPER(LEFT(str,1)), LOWER(SUBSTRING(str,2)))`
- **UPPER(str)** → `UPPER(str)`
- **LOWER(str)** → `LOWER(str)`
- **TRANSLATE(str, from_chars, to_chars)** → `REPLACE()` functions (complex conversion needed)

### Numeric Functions
- **TO_NUMBER(str)** → `CAST(str AS DECIMAL)` or `CONVERT(str, DECIMAL)`
- **TO_NUMBER(str, format)** → `CAST(str AS DECIMAL)` (format ignored in MySQL)
- **ROUND(num, digits)** → `ROUND(num, digits)`
- **TRUNC(num, digits)** → `TRUNCATE(num, digits)`
- **CEIL(num)** → `CEILING(num)`
- **FLOOR(num)** → `FLOOR(num)`
- **MOD(num1, num2)** → `MOD(num1, num2)` or `num1 % num2`
- **POWER(base, exp)** → `POWER(base, exp)`
- **SQRT(num)** → `SQRT(num)`
- **ABS(num)** → `ABS(num)`
- **SIGN(num)** → `SIGN(num)`

### Analytical Functions
- **ROWNUM = 1** → `LIMIT 1` (in subqueries)
- **ROWNUM <= n** → `LIMIT n` (in subqueries)
- **ROWNUM** → `ROW_NUMBER() OVER (ORDER BY (SELECT NULL))`
- **ROW_NUMBER() OVER (...)** → `ROW_NUMBER() OVER (...)`
- **RANK() OVER (...)** → `RANK() OVER (...)`
- **DENSE_RANK() OVER (...)** → `DENSE_RANK() OVER (...)`

### Aggregate Functions
- **LISTAGG(col, delimiter)** → `GROUP_CONCAT(col SEPARATOR delimiter)`
- **LISTAGG(col, delimiter) WITHIN GROUP (ORDER BY ...)** → `GROUP_CONCAT(col ORDER BY ... SEPARATOR delimiter)`
- **WM_CONCAT(col)** → `GROUP_CONCAT(col)`

### Join Syntax
- **Oracle Outer Join (+)** → `LEFT JOIN` or `RIGHT JOIN`
- **table1.col = table2.col(+)** → `table1 LEFT JOIN table2 ON table1.col = table2.col`
- **table1.col(+) = table2.col** → `table1 RIGHT JOIN table2 ON table1.col = table2.col`

### Dynamic Join Syntax (MyBatis Conditional)
- **DYNAMIC OUTER JOIN**: Oracle (+) inside MyBatis `<if>` tags requires special handling
- **Pattern**: `<if test="condition">AND table1.col = table2.col(+)</if>`

#### **Enhanced Conversion Strategy (Based on sqlTransformTargetMysqlRules.md):**

**Level 1: Simple Single Condition (Recommended Approach)**
```xml
<!-- BEFORE (Oracle) -->
<if test="includeProject == 'Y'">
  AND E.EMP_ID = P.EMP_ID(+)
  AND P.STATUS = 'ACTIVE'
</if>

<!-- AFTER (MySQL) - Complete FROM clause branching -->
<if test="includeProject == null or includeProject != 'Y'">
FROM EMPLOYEE E
INNER JOIN DEPARTMENT D ON E.DEPT_ID = D.DEPT_ID
</if>
<if test="includeProject != null and includeProject == 'Y'">
FROM EMPLOYEE E
INNER JOIN DEPARTMENT D ON E.DEPT_ID = D.DEPT_ID
<![CDATA[
LEFT JOIN PROJECT P ON E.EMP_ID = P.EMP_ID AND P.STATUS = 'ACTIVE'
]]>
</if>
```

**Level 2: Multiple Conditions (Advanced Approach)**
```xml
<!-- BEFORE (Oracle) -->
<if test="includeProduct == 'Y'">
  AND OM.PROD_ID = P.PROD_ID(+)
</if>
<if test="includeCategory == 'Y'">
  AND P.CATEGORY_ID = CT.CATEGORY_ID(+)
</if>

<!-- AFTER (MySQL) - Complete condition matrix -->
<choose>
    <when test="includeProduct == 'Y' and includeCategory == 'Y'">
    FROM ORDER_MASTER OM
    INNER JOIN CUSTOMER C ON OM.CUST_ID = C.CUST_ID
    <![CDATA[
    LEFT JOIN PRODUCT P ON OM.PROD_ID = P.PROD_ID
    LEFT JOIN CATEGORY CT ON P.CATEGORY_ID = CT.CATEGORY_ID
    ]]>
    </when>
    <when test="includeProduct == 'Y' and includeCategory != 'Y'">
    FROM ORDER_MASTER OM
    INNER JOIN CUSTOMER C ON OM.CUST_ID = C.CUST_ID
    <![CDATA[
    LEFT JOIN PRODUCT P ON OM.PROD_ID = P.PROD_ID
    ]]>
    </when>
    <otherwise>
    FROM ORDER_MASTER OM
    INNER JOIN CUSTOMER C ON OM.CUST_ID = C.CUST_ID
    </otherwise>
</choose>
```

#### **Fallback Strategy - TODO Comments (For Complex Cases):**

**Simple Conversion Strategy:**
```xml
<!-- BEFORE (Oracle) -->
<if test="condition">
  AND A.ID = C.ID(+)
</if>

<!-- AFTER (MySQL) -->
<if test="condition">
<![CDATA[
-- TODO: DYNAMIC OUTER JOIN - Manual review required
-- Original: AND A.ID = C.ID(+)
-- Action: Move to FROM clause as LEFT JOIN
-- Recommended: LEFT JOIN TABLE_C C ON A.ID = C.ID
-- Alternative: Use complete FROM clause branching approach above
]]>
</if>
```

**Multiple Conditions:**
```xml
<!-- BEFORE (Oracle) -->
<if test="condition">
  AND A.ID = C.ID(+)
  AND B.COL = C.COL(+)
</if>

<!-- AFTER (MySQL) -->
<if test="condition">
<![CDATA[
-- TODO: DYNAMIC OUTER JOIN - Manual review required
-- Original: AND A.ID = C.ID(+) AND B.COL = C.COL(+)
-- Action: Consolidate into single LEFT JOIN in FROM clause
-- Recommended: LEFT JOIN TABLE_C C ON A.ID = C.ID AND B.COL = C.COL
-- Alternative: Use <choose><when> branching for complete FROM clause control
]]>
</if>
```

**Right Join Pattern:**
```xml
<!-- BEFORE (Oracle) -->
<if test="condition">
  AND A.ID(+) = C.ID
</if>

<!-- AFTER (MySQL) -->
<if test="condition">
<![CDATA[
-- TODO: DYNAMIC OUTER JOIN - Manual review required
-- Original: AND A.ID(+) = C.ID
-- Action: Move to FROM clause as RIGHT JOIN
-- Recommended: RIGHT JOIN TABLE_C C ON A.ID = C.ID
-- Note: Verify join direction - (+) on left side = RIGHT JOIN
]]>
</if>
```

**Complex Cases - Enhanced TODO Comments:**
```xml
<![CDATA[
-- TODO: DYNAMIC OUTER JOIN conversion needed
-- Original: <if test="condition">AND table1.col = table2.col(+)</if>
-- Issue: Complex conditional join logic requires manual review
-- Action Required: Convert to conditional LEFT/RIGHT JOIN in FROM clause
-- Complexity Level: HIGH
-- 
-- RECOMMENDED APPROACHES:
-- 1. Complete FROM clause branching with <if test="!condition"> and <if test="condition">
-- 2. Use <choose><when><otherwise> for multiple condition combinations
-- 3. Move JOIN conditions to ON clause, wrap in <![CDATA[]]>
-- 4. Preserve table aliases and maintain MyBatis parameter binding
-- 
-- REFERENCE: See sqlTransformTargetMysqlRules.md PHASE 1 - MyBatis Conditional OUTER JOIN
-- <if test="condition">AND table1.col = table2.col(+)</if>
]]>
```

#### **Key Guidelines (Enhanced from sqlTransformTargetMysqlRules.md):**
- **Conditional FROM clause branching**: Use `<if test="!condition">` to maintain base FROM clause
- **Complete FROM clause provision**: Provide complete FROM clause for each condition
- **Explicit JOIN specification**: Convert comma joins to explicit INNER JOINs
- **JOIN direction verification**: Determine LEFT/RIGHT JOIN based on `(+)` position
- **MyBatis structure preservation**: Maintain `<if>`, `<choose>`, `<when>` tags
- **WHERE → ON clause migration**: Move Oracle `(+)` conditions to MySQL ON clauses
- **CDATA block usage**: Place conditional JOINs inside `<![CDATA[]]>`
- **Table alias preservation**: Maintain all table aliases (B1, B2, B3, etc.)
- **Parameter binding preservation**: Keep MyBatis `#{...}` syntax intact

### String Concatenation
- **str1 || str2** → `CONCAT(str1, str2)`
- **str1 || str2 || str3** → `CONCAT(str1, str2, str3)`

### Special Tables and Operators
- **FROM DUAL** → Remove `FROM DUAL` or use `SELECT ... FROM (SELECT 1) AS dual`
- **MINUS** → `EXCEPT` (MySQL 8.0+) or `NOT EXISTS`
- **INTERSECT** → `INTERSECT` (MySQL 8.0+) or `EXISTS`

### Sequence Functions
- **sequence_name.NEXTVAL** → `AUTO_INCREMENT` or custom sequence table
- **sequence_name.CURRVAL** → `LAST_INSERT_ID()` or custom sequence table

**Note**: This mapping reference can be extended as needed. Refer to this section for comprehensive Oracle to MySQL function conversions.

**IMPORTANT**: 
- **IGNORE Oracle syntax found in XML comments** (`<!-- ... -->`)
- **Only process Oracle syntax in active SQL code**
- **Comments are preserved for reference and do not cause syntax errors**

**TRANSFORMATION MAPPING for ${TARGET_DBMS_TYPE}:**

##### A. Outer Join Structure
- **Oracle**: `(+)` syntax → **Target**: `LEFT/RIGHT/FULL OUTER JOIN` (Standard SQL)
- **Oracle**: `AA.PNR_SEQNO(+)=A.PNR_SEQNO` → **Target**: `LEFT JOIN ... ON AA.PNR_SEQNO=A.PNR_SEQNO`

**SPECIAL HANDLING FOR MyBatis CONDITIONAL OUTER JOINS:**

1. **Simple Outer Join (No Conditions)**:
   ```sql
   -- BEFORE (Oracle)
   FROM TABLE_A A, TABLE_B B
   WHERE A.ID = B.ID(+)
   
   -- AFTER (MySQL)
   FROM TABLE_A A
   LEFT JOIN TABLE_B B ON A.ID = B.ID
   ```

2. **Conditional Outer Join in MyBatis `<if>` Tags**:
   ```sql
   -- BEFORE (Oracle)
   FROM TABLE_A A, TABLE_B B
   <if test="condition">
     , (SELECT ... FROM TABLE_C) C
   </if>
   WHERE A.ID = B.ID(+)
   <if test="condition">
     AND A.ID = C.ID(+)
     AND B.COL = C.COL(+)
   </if>
   
   -- AFTER (MySQL)
   FROM TABLE_A A
   LEFT JOIN TABLE_B B ON A.ID = B.ID
   <if test="condition">
   <![CDATA[
   -- Conditional LEFT JOIN for TABLE_C
   LEFT JOIN (SELECT ... FROM TABLE_C) C ON A.ID = C.ID AND B.COL = C.COL
   ]]>
   </if>
   ```

3. **Right Outer Join Pattern**:
   ```sql
   -- BEFORE (Oracle)
   FROM SUBQUERY R, MAIN_TABLE T
   WHERE R.ID(+) = T.ID
   
   -- AFTER (MySQL)
   FROM SUBQUERY R
   RIGHT JOIN MAIN_TABLE T ON R.ID = T.ID
   ```

**CRITICAL RULES:**
- **Preserve MyBatis conditional structure**: Keep `<if>` tags intact
- **Move JOIN conditions**: Oracle `(+)` conditions in WHERE → MySQL ON clause
- **Conditional JOINs**: Place conditional LEFT/RIGHT JOIN inside `<![CDATA[]]>` within `<if>` tags
- **Maintain table aliases**: Preserve all table aliases (B1, B2, B3, etc.)
- **Check join direction**: `A.ID = B.ID(+)` = LEFT JOIN, `A.ID(+) = B.ID` = RIGHT JOIN

##### B. NULL Handling Functions
- **Oracle**: `NVL(expr1, expr2)` → 
  - **MySQL**: `IFNULL(expr1, expr2)`
  - **PostgreSQL**: `COALESCE(expr1, expr2)`
  - **SQL Server**: `ISNULL(expr1, expr2)`
- **Oracle**: `NVL2(expr1, expr2, expr3)` → 
  - **MySQL**: `IF(expr1 IS NOT NULL, expr2, expr3)`
  - **PostgreSQL/SQL Server**: `CASE WHEN expr1 IS NOT NULL THEN expr2 ELSE expr3 END`

##### C. Date/Time Functions
- **Oracle**: `SYSDATE` → 
  - **MySQL**: `NOW()`
  - **PostgreSQL**: `CURRENT_TIMESTAMP`
  - **SQL Server**: `GETDATE()`
- **Oracle**: `TO_DATE(str, fmt)` → 
  - **MySQL**: `STR_TO_DATE(str, fmt)`
  - **PostgreSQL**: `TO_DATE(str, fmt)` (same)
  - **SQL Server**: `CONVERT(datetime, str, style)`
- **Oracle**: `TO_CHAR(date, fmt)` → 
  - **MySQL**: `DATE_FORMAT(date, fmt)`
  - **PostgreSQL**: `TO_CHAR(date, fmt)` (same)
  - **SQL Server**: `FORMAT(date, fmt)`

##### D. String Functions
- **Oracle**: `SUBSTR(str, pos, len)` → 
  - **All Target DBMS**: `SUBSTRING(str, pos, len)`
- **Oracle**: `INSTR(str, substr)` → 
  - **MySQL**: `LOCATE(substr, str)`
  - **PostgreSQL**: `POSITION(substr IN str)`
  - **SQL Server**: `CHARINDEX(substr, str)`
- **Oracle**: `||` (concatenation) → 
  - **MySQL**: `CONCAT()`
  - **PostgreSQL**: `||` (same) or `CONCAT()`
  - **SQL Server**: `CONCAT()` or `+`

##### E. Conditional Functions
- **Oracle**: `DECODE(expr, val1, res1, val2, res2, default)` → 
  - **All Target DBMS**: `CASE WHEN expr=val1 THEN res1 WHEN expr=val2 THEN res2 ELSE default END`

##### F. Analytical Functions
- **Oracle**: `ROWNUM` → 
  - **All Target DBMS**: `ROW_NUMBER() OVER(ORDER BY ...)`
- **Oracle**: `DUAL` table → 
  - **MySQL**: Remove or use `SELECT ... FROM (SELECT 1) AS dual`
  - **PostgreSQL/SQL Server**: Remove or use `SELECT ...`

##### G. Aggregate Functions
- **Oracle**: `LISTAGG(expr, delimiter) WITHIN GROUP (ORDER BY ...)` → 
  - **MySQL**: `GROUP_CONCAT(expr ORDER BY ... SEPARATOR delimiter)`
  - **PostgreSQL**: `STRING_AGG(expr, delimiter ORDER BY ...)`
  - **SQL Server**: `STRING_AGG(expr, delimiter) WITHIN GROUP (ORDER BY ...)`

##### H. Numeric Functions
- **Oracle**: `TO_NUMBER(str)` → 
  - **MySQL**: `CAST(str AS DECIMAL)` or `CONVERT(str, DECIMAL)`
  - **PostgreSQL**: `CAST(str AS NUMERIC)` or `str::NUMERIC`
  - **SQL Server**: `CAST(str AS NUMERIC)` or `CONVERT(NUMERIC, str)`

**Note**: Apply transformations based on current `${TARGET_DBMS_TYPE}` environment variable value.

#### 2. Context Analysis Rule
**When Oracle syntax is detected, analyze the surrounding context to understand:**
- Overall SQL logic and query structure
- Interaction with MyBatis dynamic SQL tags (`<if>`, `<choose>`, etc.)
- Variable binding and parameter usage patterns
- Query intent and business logic

#### 3. Original Reference Validation
- **CHECK** original ${SOURCE_DBMS_TYPE} XML when transformation integrity verification is needed
- **ENSURE** logical consistency between original intent and transformation result
- **COMPARE** identical sections of original and transformed versions during context analysis

#### 4. MyBatis XML Structure Preservation
- **MAINTAIN** MyBatis tags such as `<select>`, `<insert>`, `<update>`, `<delete>`
- **PRESERVE** dynamic SQL tags like `<if>`, `<choose>`, `<foreach>`
- **KEEP** CDATA sections and XML namespaces intact

#### 5. SQL Semantic Accuracy
- **ENSURE** identical execution results before and after transformation
- **CONSIDER** data type compatibility
- **APPLY** optimal ${TARGET_DBMS_TYPE} syntax from performance optimization perspective

## Work Execution Method

1. **Initialize Log**: **APPEND** session timestamp to `${APP_TRANSFORM_FOLDER}/post-transformation.log`
2. **LOAD SEARCH PATTERN**: Extract the search pattern from oracle_functions.txt for the specified Oracle function
   ```bash
   # Load pattern from oracle_functions.txt
   SEARCH_PATTERN=$(grep "^${ORACLE_FUNCTION}|" ${APP_TOOLS_FOLDER}/../postTransform/expression/oracle_functions.txt | cut -d'|' -f2)
   if [ -z "$SEARCH_PATTERN" ]; then
       SEARCH_PATTERN="${ORACLE_FUNCTION}"
   fi
   echo "Using search pattern: ${SEARCH_PATTERN}"
   ```
3. **PATTERN SEARCH VALIDATION**: Execute Oracle syntax pattern detection command using the loaded pattern
   - **IMMEDIATE TERMINATION**: If search results are empty, log "No patterns found for ${SEARCH_PATTERN} - process terminated" and exit immediately
   - **Continue only if patterns found**: Proceed to comprehensive file scan only when search results exist
3. **COMPREHENSIVE File Scan**: Execute ALL Oracle syntax pattern detection commands **WITHOUT LIMITATIONS** (only when patterns exist)
   - **Process EVERY result** from each search command
   - **DO NOT use `head -N`** to limit results
   - **COMPLETE each Oracle syntax category** before moving to next
3. **Systematic Analysis**: For EACH Oracle syntax pattern found:
   - **Identify ALL occurrences** with line numbers
   - **Analyze context** and diagnose issues
   - **For Outer Joins**: Check if inside MyBatis `<if>` tags
   - **For Conditional JOINs**: Compare with original extract file to understand structure
   - **For Complex Queries**: Identify all table relationships before conversion
4. **COMPLETE FILE MODIFICATION**: **DIRECTLY MODIFY** ALL XML files to fix Oracle syntax
   - **Process EVERY file** that contains Oracle syntax
   - **Preserve MyBatis conditional logic**
   - **Convert ALL Oracle functions** to MySQL equivalents
   - **Move WHERE conditions to ON clauses** for joins
   - **Wrap conditional JOINs in `<![CDATA[]]>` blocks**
5. **Comprehensive Logging**: **APPEND** ALL modified files with: XML_FILE, SEARCH_RESULT, DIAGNOSIS, CHANGES, CHANGE_TIME
6. **Skip Clean Files**: Do not log files with no Oracle syntax issues
7. **Complete Session**: Mark session completion in log **ONLY AFTER ALL ORACLE SYNTAX IS PROCESSED**

**CRITICAL EXECUTION REQUIREMENTS:**
- **PROCESS ALL MATCHES** - Do not stop after processing a few files
- **COMPLETE TRANSFORMATION** - Ensure no Oracle syntax remains
- **SYSTEMATIC APPROACH** - Go through each Oracle syntax category completely
- **VERIFY COMPLETION** - Re-run searches to confirm no Oracle syntax remains

### LOGGING REQUIREMENTS (UPDATED)
**You must APPEND to the comprehensive transformation log at:**
`${APP_TRANSFORM_FOLDER}/post-transformation.log`

**IMPORTANT**: 
- **NEVER overwrite** existing log content
- **ALWAYS use APPEND mode** when writing to log file
- **Add timestamp** for each new log entry using `date '+%Y-%m-%d %H:%M:%S'` format
- **Preserve all previous log entries** from earlier transformations

**Enhanced Log Format - Record the following comprehensive information:**
```
=== TRANSFORMATION SESSION: [YYYY-MM-DD HH:MM:SS] ===
ORACLE_FUNCTION: [${ORACLE_FUNCTION} - the specific Oracle function being converted]
SEARCH_PATTERN: [${SEARCH_PATTERN} - the search pattern used]
XML_FILE: [Full file path]
BACKUP_CREATED: [Backup file path and creation timestamp]
SEARCH_RESULT: [Oracle syntax patterns found with line numbers]
DIAGNOSIS: [Context analysis and issue description]
COMPLEXITY_LEVEL: [HIGH/MEDIUM/LOW based on conversion difficulty]
CHANGES: [Before/After transformation details]
VALIDATION_STATUS: [XML_VALID/XML_INVALID/SYNTAX_ERROR]
ERROR_RECOVERY: [Any rollback or recovery actions taken]
CONVERSION_STATS: [Count of each function type converted]
CHANGE_TIME: [YYYY-MM-DD HH:MM:SS]
---
```

**Example Enhanced Log Entry:**
```
=== TRANSFORMATION SESSION: 2025-07-18 14:00:00 ===
ORACLE_FUNCTION: NVL
SEARCH_PATTERN: NVL(
XML_FILE: /path/to/mapper.xml
BACKUP_CREATED: /path/to/mapper.xml.backup at 2025-07-18 14:00:00
SEARCH_RESULT: Line 193: Oracle NVL function found
DIAGNOSIS: Found NVL(column, 'default') pattern requiring conversion to IFNULL
COMPLEXITY_LEVEL: MEDIUM
CHANGES: BEFORE: NVL(column, 'default') | AFTER: IFNULL(column, 'default')
VALIDATION_STATUS: XML_VALID
ERROR_RECOVERY: None required
CONVERSION_STATS: NVL functions: 1
CHANGE_TIME: 2025-07-18 14:00:01
---
```

**Session Summary Format:**
```
=== SESSION SUMMARY: [YYYY-MM-DD HH:MM:SS] ===
ORACLE_FUNCTION_PROCESSED: [${ORACLE_FUNCTION}]
SEARCH_PATTERN_USED: [${SEARCH_PATTERN}]
TOTAL_FILES_PROCESSED: [number]
TOTAL_FILES_MODIFIED: [number]
TOTAL_FUNCTIONS_CONVERTED: [number]
CONVERSION_BREAKDOWN: [function_type: count, ...]
HIGH_COMPLEXITY_CONVERSIONS: [number]
ERRORS_ENCOUNTERED: [number]
ROLLBACKS_PERFORMED: [number]
SESSION_DURATION: [start_time - end_time]
=== SESSION COMPLETED: [YYYY-MM-DD HH:MM:SS] ===
```

**Only log files that have actual changes - skip files with no Oracle syntax issues.**

## Output Requirements
- **List only modified files** with their full paths
- **Show Oracle syntax search results** with line numbers
- **Display diagnosis** of each Oracle syntax issue found
- **Show before/after transformation** for each modification
- **Confirm modification timestamp** for each changed file
- **Confirm log file APPEND status** at `${APP_TRANSFORM_FOLDER}/post-transformation.log`
- **Skip reporting files with no issues** - only report actual changes
- **NO summary or briefing required** - focus on actual work performed

## Critical Requirements
- **BACKUP BEFORE MODIFICATION** - Create .backup files before any changes
- **ERROR RECOVERY** - Implement rollback mechanism for failed conversions
- **XML VALIDATION** - Verify XML syntax integrity after each modification
- **YOU MUST ACTUALLY MODIFY THE FILES** - not just analyze them
- **PROCESS ALL ORACLE SYNTAX** - Do not stop after processing a few matches
- **COMPLETE TRANSFORMATION** - Ensure no Oracle syntax remains in any file
- **HANDLE COMPLEX NESTED FUNCTIONS** - Apply specialized conversion rules
- **ENHANCED CONDITIONAL PROCESSING** - Handle nested MyBatis tags properly
- **SEMANTIC VERIFICATION** - Ensure query logic equivalence before/after
- **IGNORE Oracle syntax in XML comments** (`<!-- ... -->`) - comments do not cause syntax errors
- **ONLY process Oracle syntax in active SQL code** (outside of comments)
- **PRESERVE MyBatis dynamic SQL structure** - Keep `<if>`, `<choose>`, `<when>` tags intact
- **HANDLE CONDITIONAL OUTER JOINS CAREFULLY** - Analyze original Oracle structure before converting
- **COMPREHENSIVE LOGGING** - Log all modifications with enhanced format including complexity levels
- **APPEND to existing log** (NEVER overwrite)
- **SKIP logging files with no Oracle syntax issues**
- **DO NOT provide summary or briefing** - just perform the requested tasks
- **All modifications must preserve XML structure integrity**
- **Save all changes back to the original file locations**
- **Use proper timestamp format: YYYY-MM-DD HH:MM:SS**
- **Verify JOIN direction**: Check if Oracle `(+)` should become LEFT JOIN or RIGHT JOIN
- **Maintain table alias consistency** throughout the transformation
- **EXHAUSTIVE PROCESSING**: Continue until ALL Oracle syntax patterns are eliminated
- **SESSION SUMMARY**: Generate comprehensive session statistics at completion

## Success Criteria
- **Backup files created** for all modified XML files
- **Error recovery implemented** with rollback capability
- All Oracle syntax remnants are identified and converted
- **Complex nested functions properly handled** using specialized conversion rules
- **XML syntax validation passed** for all modified files
- All XML files are properly modified and saved
- **Enhanced logging completed** with complexity levels, validation status, and conversion statistics
- Log is **APPENDED** to `${APP_TRANSFORM_FOLDER}/post-transformation.log`
- **Previous log entries are preserved**
- **Session summary generated** with comprehensive statistics
- No XML structure damage occurs
- All transformations maintain SQL semantic equivalence
- **Semantic verification completed** for all conversions
- **Session completion logged with comprehensive summary and timestamp**

---

## Oracle to MySQL Function Mapping Reference
**This section provides comprehensive conversion mappings referenced in Step 2 above.**

### Date/Time Functions
- **SYSDATE** → `NOW()` or `CURRENT_TIMESTAMP`
- **TO_CHAR(date, 'YYYYMMDD')** → `DATE_FORMAT(date, '%Y%m%d')`
- **TO_CHAR(date, 'YYYY-MM-DD')** → `DATE_FORMAT(date, '%Y-%m-%d')`
- **TO_CHAR(date, 'YYYY-MM-DD HH24:MI:SS')** → `DATE_FORMAT(date, '%Y-%m-%d %H:%i:%s')`
- **TO_DATE(str, 'YYYYMMDD')** → `STR_TO_DATE(str, '%Y%m%d')`
- **TO_DATE(str, 'YYYY-MM-DD')** → `STR_TO_DATE(str, '%Y-%m-%d')`
- **ADD_MONTHS(date, n)** → `DATE_ADD(date, INTERVAL n MONTH)` (positive n) or `DATE_SUB(date, INTERVAL ABS(n) MONTH)` (negative n)
- **MONTHS_BETWEEN(date1, date2)** → `TIMESTAMPDIFF(MONTH, date2, date1)`
- **TRUNC(date)** → `DATE(date)`
- **TRUNC(date, 'MM')** → `DATE_FORMAT(date, '%Y-%m-01')`
- **TRUNC(date, 'YYYY')** → `DATE_FORMAT(date, '%Y-01-01')`
- **EXTRACT(YEAR FROM date)** → `YEAR(date)`
- **EXTRACT(MONTH FROM date)** → `MONTH(date)`
- **EXTRACT(DAY FROM date)** → `DAY(date)`
- **LAST_DAY(date)** → `LAST_DAY(date)`
- **NEXT_DAY(date, 'SUNDAY')** → `DATE_ADD(date, INTERVAL (1 + (7 - DAYOFWEEK(date))) % 7 DAY)`

### NULL Handling Functions  
- **NVL(expr1, expr2)** → `IFNULL(expr1, expr2)` or `COALESCE(expr1, expr2)`
- **NVL2(expr, val1, val2)** → `CASE WHEN expr IS NOT NULL THEN val1 ELSE val2 END`
- **NULLIF(expr1, expr2)** → `NULLIF(expr1, expr2)`

### Conditional Functions
- **DECODE(expr, val1, ret1, val2, ret2, default)** → `CASE WHEN expr=val1 THEN ret1 WHEN expr=val2 THEN ret2 ELSE default END`
- **DECODE(expr, val1, ret1, default)** → `CASE WHEN expr=val1 THEN ret1 ELSE default END`

### String Functions
- **SUBSTR(str, pos, len)** → `SUBSTRING(str, pos, len)`
- **SUBSTR(str, pos)** → `SUBSTRING(str, pos)`
- **LENGTH(str)** → `CHAR_LENGTH(str)` or `LENGTH(str)`
- **INSTR(str, substr)** → `LOCATE(substr, str)`
- **INSTR(str, substr, start)** → `LOCATE(substr, str, start)`
- **LPAD(str, len, pad)** → `LPAD(str, len, pad)`
- **RPAD(str, len, pad)** → `RPAD(str, len, pad)`
- **LTRIM(str)** → `LTRIM(str)`
- **RTRIM(str)** → `RTRIM(str)`
- **LTRIM(str, chars)** → `TRIM(LEADING chars FROM str)`
- **RTRIM(str, chars)** → `TRIM(TRAILING chars FROM str)`
- **INITCAP(str)** → `CONCAT(UPPER(LEFT(str,1)), LOWER(SUBSTRING(str,2)))`
- **UPPER(str)** → `UPPER(str)`
- **LOWER(str)** → `LOWER(str)`
- **TRANSLATE(str, from_chars, to_chars)** → `REPLACE()` functions (complex conversion needed)

### Numeric Functions
- **TO_NUMBER(str)** → `CAST(str AS DECIMAL)` or `CONVERT(str, DECIMAL)`
- **TO_NUMBER(str, format)** → `CAST(str AS DECIMAL)` (format ignored in MySQL)
- **ROUND(num, digits)** → `ROUND(num, digits)`
- **TRUNC(num, digits)** → `TRUNCATE(num, digits)`
- **CEIL(num)** → `CEILING(num)`
- **FLOOR(num)** → `FLOOR(num)`
- **MOD(num1, num2)** → `MOD(num1, num2)` or `num1 % num2`
- **POWER(base, exp)** → `POWER(base, exp)`
- **SQRT(num)** → `SQRT(num)`
- **ABS(num)** → `ABS(num)`
- **SIGN(num)** → `SIGN(num)`

### Analytical Functions
- **ROWNUM = 1** → `LIMIT 1` (in subqueries)
- **ROWNUM <= n** → `LIMIT n` (in subqueries)
- **ROWNUM** → `ROW_NUMBER() OVER (ORDER BY (SELECT NULL))`
- **ROW_NUMBER() OVER (...)** → `ROW_NUMBER() OVER (...)`
- **RANK() OVER (...)** → `RANK() OVER (...)`
- **DENSE_RANK() OVER (...)** → `DENSE_RANK() OVER (...)`

### Aggregate Functions
- **LISTAGG(col, delimiter)** → `GROUP_CONCAT(col SEPARATOR delimiter)`
- **LISTAGG(col, delimiter) WITHIN GROUP (ORDER BY ...)** → `GROUP_CONCAT(col ORDER BY ... SEPARATOR delimiter)`
- **WM_CONCAT(col)** → `GROUP_CONCAT(col)`

### Join Syntax
- **Oracle Outer Join (+)** → `LEFT JOIN` or `RIGHT JOIN`
- **table1.col = table2.col(+)** → `table1 LEFT JOIN table2 ON table1.col = table2.col`
- **table1.col(+) = table2.col** → `table1 RIGHT JOIN table2 ON table1.col = table2.col`

### String Concatenation
- **str1 || str2** → `CONCAT(str1, str2)`
- **str1 || str2 || str3** → `CONCAT(str1, str2, str3)`

### Special Tables and Operators
- **FROM DUAL** → Remove `FROM DUAL` or use `SELECT ... FROM (SELECT 1) AS dual`
- **MINUS** → `EXCEPT` (MySQL 8.0+) or `NOT EXISTS`
- **INTERSECT** → `INTERSECT` (MySQL 8.0+) or `EXISTS`

### Sequence Functions
- **sequence_name.NEXTVAL** → `AUTO_INCREMENT` or custom sequence table
- **sequence_name.CURRVAL** → `LAST_INSERT_ID()` or custom sequence table

**Note**: This mapping reference can be extended as needed for ${TARGET_DBMS_TYPE} and other target DBMS types.
