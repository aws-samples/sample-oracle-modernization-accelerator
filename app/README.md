# OMA App Conversion

Automatically converts Oracle MyBatis Mapper to PostgreSQL/MySQL.

> Korean version: [README_KR.md](README_KR.md)

## Overview

The `app` folder provides tools for converting Oracle MyBatis Mapper XML files to PostgreSQL/MySQL compatible format.

### Key Features

- **Oracle Dictionary Generation**: Extract Oracle schema metadata
- **SQL Conversion**: Automatic Oracle SQL → PostgreSQL/MySQL conversion (LLM-based)
- **Mapper Split/Merge**: Manage large XML files
- **Extension Detection**: Scan customer framework bind variables
- **OGNL Detection**: Scan Java static method calls
- **Validator**: Verify converted SQL (actual DB execution)

---

## Folder Structure

```
app/
├── .claude/
│   └── skills/           # Claude Code skills (automation commands)
│       ├── verify-env.sh         # Environment verification (auto-scans Extension/OGNL)
│       ├── build-oracle-dict.sh  # Oracle Dictionary generation
│       ├── split-mappers.sh      # Mapper splitting
│       ├── convert-sql.sh        # SQL conversion (single file)
│       ├── merge-mappers.sh      # Mapper merging
│       └── run-validator.sh      # SQL validation
├── tools/                # Python conversion scripts
│   ├── load_oma_env.sh           # oma.properties loader
│   ├── oracle_dictionary.py      # Oracle metadata extraction
│   ├── split_mapper.py           # Mapper splitting
│   ├── convert_sql.py            # SQL conversion (LLM)
│   ├── merge_mapper.py           # Mapper merging
│   ├── scan_extension_variables.py   # Extension scanning
│   ├── scan_ognl.py              # OGNL scanning
│   └── validator/        # Java Validator
│       ├── src/
│       └── target/mapper-validator-1.0.0.jar
├── extensions/           # Extension configuration
│   └── extension.json
├── output/               # Execution results
│   ├── oracle_dictionary.json
│   ├── validation-report.json
│   └── validation.log
├── mappers/              # Conversion workspace (intermediate output)
└── setup.sh              # Initial setup script
```

---

## Prerequisites

### 1. Environment Configuration

Configure environment variables in `/home/ec2-user/workspace/oma/env/oma.properties`:

```properties
[COMMON]
# Oracle Connection
ORACLE_HOST=10.0.X.X
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_USER=username
ORACLE_PASSWORD=password
ORACLE_SCHEMA=SCHEMA_NAME
ORACLE_HOME=/home/ec2-user/oracle

# PostgreSQL Connection (Standard Variables)
PGHOST=cluster.xxxxx.region.rds.amazonaws.com
PGPORT=5432
PGDATABASE=dbname
PGSCHEMA=schema_name
PGUSER=username
PGPASSWORD=password

# App Conversion Settings
SOURCE_WORKSPACE=/home/ec2-user/workspace/source    # Source mapper location
TARGET_WORKSPACE=/home/ec2-user/workspace/target    # Conversion result location
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7
MAX_WORKERS=7
TARGET_DB_TYPE=postgres
```

> 📝 **Reference**: See [env/README.md](../env/README.md) for detailed environment setup

### 2. Source Mapper Preparation

Place original Oracle Mapper files in SOURCE_WORKSPACE:

```bash
SOURCE_WORKSPACE/
└── my-project/
    └── mappers/
        ├── UserMapper.xml
        ├── OrderMapper.xml
        └── ProductMapper.xml
```

### 3. Extension Keyword Configuration (Customer Agreement)

**What is Extension?**
- Special bind variables provided by customer framework
- Example: `#{GRIDPAGING_START}`, `#{FRAMEWORK_SESSION_ID}`

**Pre-project Agreement:**
1. Confirm Extension variable list with customer
2. Identify naming conventions (e.g., GRIDPAGING_*, EGOVFRAME_*)
3. Update `tools/scan_extension_variables.py` keywords:

```python
# Line 63-65 modification
is_extension = (
    var.isupper() and '_' in var
    or 'GRIDPAGING' in var.upper()    # ← Change to customer keyword
    or 'FRAMEWORK' in var.upper()     # ← Change to customer keyword
    or 'EGOVFRAME' in var.upper()     # ← Add additional keyword
)
```

---

## Conversion Process

**Important**: All work must be done in the **app folder** by running **Claude Code** and using **skills**.

```bash
# 1. Navigate to app folder
cd /home/ec2-user/workspace/oma/app

# 2. Launch Claude Code
claude
```

---

### Step 0: Environment Verification (Required)

Verify environment and automatically scan Extension/OGNL before conversion.

**Execute in Claude Code:**
```
/verify-env
```

**Verification Items:**
1. ✅ Python 3.11+ installed
2. ✅ Environment variables loaded (oma.properties)
3. ✅ Oracle Client (sqlplus) available
4. ✅ PostgreSQL/MySQL Client available
5. ✅ Oracle DB connection
6. ✅ Target DB connection
7. ✅ SOURCE_WORKSPACE check
8. ✅ Mapper directory check
9. ✅ Bedrock LLM connection
10. ✅ **Extension variables auto-scan**
11. ✅ **OGNL expressions auto-scan**

**Example Output:**
```
-------------------------------------------
10. Extension Variable Detection
-------------------------------------------
Scanning for Extension variables...
✓ Extension scan completed
  → Found 3 Extension variables
  → Configuration: extensions/extension.json

-------------------------------------------
11. OGNL Expression Detection
-------------------------------------------
Scanning for OGNL expressions (@Class@method patterns)...
✓ OGNL implementation guide generated
  → Found OGNL expressions requiring implementation
  → Implementation guide: docs/OGNL_IMPLEMENTATION_GUIDE.md

===========================================
Environment Verification Summary
===========================================
  Extension Variables:
    → 3 variables found
    → Review: extensions/extension.json

  OGNL Expressions:
    → FOUND - Implementation required
    → Read guide: docs/OGNL_IMPLEMENTATION_GUIDE.md
```

**If Extension Found:**
```bash
# 1. Review results
cat extensions/extension.json

# 2. Manual review (remove false positives)
vi extensions/extension.json

# 3. Fill in Oracle/PostgreSQL values
{
  "enabled": true,
  "variables": {
    "GRIDPAGING_START": {
      "oracle": "...",
      "postgres": "..."
    }
  }
}
```

**If OGNL Found:**
```bash
# 1. Review guide
cat docs/OGNL_IMPLEMENTATION_GUIDE.md

# 2. Request Java library (.jar) from customer
# 3. Register in CLASSPATH when running Validator (see Step 4)
```

---

### Step 1: Oracle Dictionary Generation

Extract metadata from Oracle schema.

**Execute in Claude Code:**
```
/build-oracle-dict 10
```

**Generated Output:**
- `output/oracle_dictionary.json` (approx. 5MB)

**Dictionary Contents:**
- 688 tables metadata
- Column types, length, precision, scale
- Primary Key, Foreign Key
- Sample data for each column (10 samples)
- Row Count

**Lookup Methods:**
```bash
# Lookup specific column
python3.11 tools/oracle_dictionary.py --lookup TB_USER.USER_ID

# Lookup entire table
python3.11 tools/oracle_dictionary.py --table TB_USER
```

---

### Step 2: Mapper Splitting (Optional)

Split large Mapper XML files by SQL ID.

**Execute in Claude Code:**
```
/split-mappers my-project
```

**Input:**
```
SOURCE_WORKSPACE/
└── my-project/
    └── mappers/
        └── UserMapper.xml  (10,000 lines)
```

**Output:**
```
mappers/
└── my-project/
    └── oracle/
        └── UserMapper/
            ├── selectUser.xml
            ├── insertUser.xml
            ├── updateUser.xml
            └── deleteUser.xml
```

**When to Use:**
- Mapper file > 5,000 lines
- SQL IDs > 50
- Need parallel conversion for speed

**When to Skip:**
- Small mapper files (< 3,000 lines)
- Can convert directly

---

### Step 3: SQL Conversion (Core)

Automatically convert Oracle SQL to PostgreSQL/MySQL. This is **OMA's core functionality**.

**Core Principle: LLM reads, understands, and converts SQL.**
- No regex usage (regex cannot parse complex SQL)
- LLM performs all tasks: table extraction, bind variable mapping, TC generation
- Handles any complex SQL perfectly (comma syntax, subqueries, CTE, UNION, etc.)

#### Execution Methods

**Single File Conversion (Claude Code):**
```
/convert-sql mappers/my-project/oracle/UserMapper/selectUser.xml
```

**Full Project Conversion (Shell - Parallel):**
```bash
# Exit Claude Code (Ctrl+D)
cd /home/ec2-user/workspace/oma/app

# Parallel conversion (MAX_WORKERS=7)
find mappers/my-project/oracle -name "*.xml" | \
  xargs -P 7 -I {} bash .claude/skills/convert-sql.sh "{}"
```

#### Detailed Conversion Process (3-Phase LLM Processing)

**Overall Flow:**
```
Split XML File → [LLM 1st: Table Extraction] → Dictionary Lookup → [LLM 2nd: SQL Conversion] → TC File Generation → Save
```

Each Mapper file is converted individually:

---

**Phase 1: XML Parsing (Python)**

```python
# Input: mappers/my-project/oracle/UserMapper/selectUser.xml
# (Already split by SQL ID in Step 2)

<?xml version="1.0" encoding="UTF-8"?>
<mapper namespace="com.example.UserMapper">
  <select id="selectUser" resultType="User">
    SELECT USER_ID, USER_NAME, SYSDATE AS REG_DT
    FROM TB_USER
    WHERE USER_ID = #{userId}
      AND REG_DT >= #{startDate}
  </select>
</mapper>

# Parse with Python ElementTree:
# - Extract SQL body
# - Extract metadata: namespace, resultType, etc.
# - Detect <include refid="..."/> references
```

---

**Phase 2: LLM 1st Call - Table Name Extraction**

```python
# Ask LLM to extract table list from SQL
Prompt to LLM:
"""
Analyze this SQL and extract all table names:

<select id="selectUser">
  SELECT USER_ID, USER_NAME, SYSDATE AS REG_DT
  FROM TB_USER
  WHERE USER_ID = #{userId}
    AND REG_DT >= #{startDate}
</select>

Output ONLY a JSON array: ["TABLE1", "TABLE2", ...]
Include tables from:
- FROM clause
- JOIN clauses
- Subqueries
- Comma-separated lists (FROM A, B, C)
"""

# LLM Response:
["TB_USER"]

# Output:
→ Step 1: LLM extracts table names from SQL
→ LLM found 1 tables: TB_USER
```

**Why Use LLM?**
- ✅ Regex cannot parse complex SQL
- ✅ `FROM A, B, C` (comma syntax) → Regex finds only A, LLM finds all
- ✅ Subqueries, CTE, UNION → Regex fails, LLM perfect
- ✅ Nested subqueries → Regex impossible, LLM capable

**All Patterns LLM Can Find:**
```sql
-- 1. FROM comma syntax
FROM TB_USER A, TB_ORDER B, TB_PRODUCT C  → Finds all 3

-- 2. Subqueries (all positions)
SELECT (SELECT COUNT(*) FROM TB_COUNT) FROM TB_USER  → Finds 2
WHERE ID IN (SELECT ID FROM TB_LIST)                 → Finds 2

-- 3. CTE (WITH)
WITH TEMP AS (SELECT * FROM TB_TEMP) 
SELECT * FROM TEMP                                   → Finds TB_TEMP

-- 4. UNION
SELECT * FROM TB_A UNION SELECT * FROM TB_B          → Finds 2

-- 5. Nested subqueries
FROM (SELECT * FROM (SELECT * FROM TB_DEEP))         → Finds TB_DEEP
```

---

**Phase 3: Dictionary Lookup (Python)**

```python
# Lookup oracle_dictionary.json with tables found by LLM
for table in ["TB_USER"]:
    table_info = oracle_dict['tables'][table]
    
# Result:
TB_USER:
  - USER_ID: VARCHAR2(20), NOT NULL, sample="USER001"
  - USER_NAME: VARCHAR2(50), NULLABLE, sample="John Doe"
  - REG_DT: DATE, NOT NULL, sample="2024-01-15"
  - STATUS: VARCHAR2(1), NOT NULL, sample="Y"

# Format schema info as text:
=== Oracle Schema Information ===
Table: TB_USER
  USER_ID: VARCHAR2(20) NOT NULL (sample: USER001)
  USER_NAME: VARCHAR2(50) (sample: John Doe)
  REG_DT: DATE NOT NULL (sample: 2024-01-15)
  STATUS: VARCHAR2(1) NOT NULL (sample: Y)

# Output:
→ Step 2: Schema information built for 1 tables
```

---

**Phase 4: LLM 2nd Call - SQL Conversion**

```python
# Pass Oracle SQL + Schema info to LLM, request PostgreSQL conversion
Prompt to LLM:
"""
Convert this Oracle SQL to PostgreSQL:

<select id="selectUser" resultType="User">
  SELECT USER_ID, USER_NAME, SYSDATE AS REG_DT
  FROM TB_USER
  WHERE USER_ID = #{userId}
    AND REG_DT >= #{startDate}
</select>

=== Oracle Schema Information ===
Table: TB_USER
  USER_ID: VARCHAR2(20) NOT NULL (sample: USER001)
  REG_DT: DATE NOT NULL (sample: 2024-01-15)

Requirements:
1. Convert Oracle syntax to PostgreSQL
2. Add explicit type casting (::DATE, ::INTEGER) using schema info
3. Map bind variables to TABLE.COLUMN
4. Generate test cases respecting column constraints:
   - VARCHAR2(20) → max 20 characters
   - DATE → valid date format
   - NOT NULL → no null values

Output JSON:
{
  "converted_xml": "...",
  "bind_variables": {"#{var}": "TABLE.COLUMN"},
  "test_cases": [{"description": "...", "parameters": {...}}]
}
"""

# LLM Response:
{
  "converted_xml": "<select id=\"selectUser\" resultType=\"User\">\n  SELECT user_id, user_name, CURRENT_TIMESTAMP AS reg_dt\n  FROM tb_user\n  WHERE user_id = #{userId}\n    AND reg_dt >= #{startDate}::DATE\n</select>",
  
  "bind_variables": {
    "#{userId}": "TB_USER.USER_ID",
    "#{startDate}": "TB_USER.REG_DT"
  },
  
  "test_cases": [
    {
      "description": "Normal user query with date filter",
      "parameters": {
        "userId": "USER001",
        "startDate": "2024-01-01"
      }
    },
    {
      "description": "Recent user query",
      "parameters": {
        "userId": "USER999",
        "startDate": "2024-12-01"
      }
    }
  ]
}

# Output:
→ Step 3: LLM converts SQL to postgres
✓ selectUser.xml - 2 bind vars
```

**JSON Parsing Failure Recovery:**
```python
# If LLM returns invalid JSON
try:
    result = json.loads(llm_response)
except JSONDecodeError:
    # Ask LLM to fix JSON (no regex!)
    fixed = call_bedrock("Fix this malformed JSON: ...")
    result = json.loads(fixed)
```

---

**Phase 5: TC File Generation (Python)**

```python
# Combine bind_variables and test_cases from LLM
# with data_types from Dictionary to generate TC file
```

```json
// selectUser.tc.json
{
  "file": "selectUser.xml",
  
  // Bind variable mapping generated by LLM
  "bind_variables": {
    "#{userId}": "TB_USER.USER_ID",
    "#{startDate}": "TB_USER.REG_DT"
  },
  
  // Data type info from Dictionary
  "data_types": {
    "TB_USER.USER_ID": {
      "type": "VARCHAR2",
      "length": 20,
      "nullable": false,
      "sample": "USER001"
    },
    "TB_USER.REG_DT": {
      "type": "DATE",
      "nullable": false,
      "sample": "2024-01-15"
    }
  },
  
  // Test cases generated by LLM (respecting constraints)
  "test_cases": [
    {
      "description": "Normal user query with date filter",
      "parameters": {
        "userId": "USER001",         // Within 20 chars (respects constraint)
        "startDate": "2024-01-01"    // DATE format
      }
    },
    {
      "description": "Recent user query",
      "parameters": {
        "userId": "USER999",
        "startDate": "2024-12-01"
      }
    }
  ]
}
```

**TC File Purpose:**
- Provides bind variable values when Validator executes SQL
- Actual database verification (Oracle vs PostgreSQL result comparison)
- Multiple test cases for various scenarios
- **Uses realistic test data generated by LLM**

---

**Phase 6: File Saving (Python)**

```xml
<!-- Output: mappers/my-project/target/UserMapper/selectUser.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" 
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.UserMapper">
  <select id="selectUser" resultType="User">
    SELECT user_id, user_name, CURRENT_TIMESTAMP AS reg_dt
    FROM tb_user
    WHERE user_id = #{userId}
      AND reg_dt >= #{startDate}::DATE
  </select>
</mapper>
```

```json
// Output: mappers/my-project/target/UserMapper/selectUser.tc.json
{TC file contents above}
```

#### Output Files

**Directory Structure After Conversion:**
```
mappers/
└── my-project/
    └── target/            # PostgreSQL/MySQL conversion results
        └── UserMapper/
            ├── selectUser.xml        # Converted Mapper
            ├── selectUser.tc.json    # Test cases
            ├── insertUser.xml
            ├── insertUser.tc.json
            ├── updateUser.xml
            └── updateUser.tc.json
```

#### LLM Conversion Tasks

**1. Syntax Conversion:**

| Oracle | PostgreSQL | MySQL |
|--------|-----------|-------|
| `SYSDATE` | `CURRENT_TIMESTAMP` | `NOW()` |
| `DECODE(col, 'A', 1, 2)` | `CASE WHEN col = 'A' THEN 1 ELSE 2 END` | Same |
| `NVL(col, 0)` | `COALESCE(col, 0)` | Same |
| `col(+) = val` | `LEFT JOIN` | Same |
| `ROWNUM <= 10` | `LIMIT 10` | Same |
| `TO_CHAR(date, 'YYYYMMDD')` | `TO_CHAR(date, 'YYYYMMDD')` | `DATE_FORMAT(date, '%Y%m%d')` |
| `SEQ_USER.NEXTVAL` | `NEXTVAL('seq_user')` | `AUTO_INCREMENT` |
| `DUAL` | Removed | Removed |

**2. Explicit Type Casting:**

```sql
-- Oracle (implicit type conversion)
WHERE REG_DT >= #{startDate}
  AND USER_LEVEL + 1 = #{nextLevel}
  AND CLOSE_DATE >= '20240101'

-- PostgreSQL (explicit type casting)
WHERE reg_dt >= #{startDate}::DATE
  AND user_level::INTEGER + 1 = #{nextLevel}::INTEGER
  AND close_date::DATE >= '20240101'::DATE
```

**Why Needed?**
- PostgreSQL has limited implicit type conversion
- VARCHAR to NUMBER comparison causes errors
- Explicit casting prevents errors

**3. Bind Variable Mapping:**

```python
# LLM identifies bind variable source using SQL context and Dictionary
#{userId} → TB_USER.USER_ID (VARCHAR2)
#{startDate} → TB_USER.REG_DT (DATE)
#{status} → TB_USER.STATUS (VARCHAR2)
#{level} → TB_USER.USER_LEVEL (NUMBER)
```

**4. Test Case Generation:**

LLM generates realistic test data respecting column constraints:

```python
# Constraints:
USER_ID: VARCHAR2(20) NOT NULL
REG_DT: DATE NOT NULL
STATUS: VARCHAR2(1) NOT NULL
USER_LEVEL: NUMBER(2) NOT NULL

# LLM Generated Test Cases:
Test Case 1: "Normal active user"
  userId: "USER001"          # Within 20 chars
  startDate: "2024-01-01"    # DATE format
  status: "Y"                # 1 char
  level: 5                   # NUMBER(2) range

Test Case 2: "Inactive user with high level"
  userId: "ADMIN999"
  startDate: "2023-12-31"
  status: "N"
  level: 10

# Invalid Examples (LLM does NOT generate):
  userId: "VERYLONGUSERNAMEEXCEEDING20CHARS"  # ✗ Length exceeded
  startDate: null                             # ✗ NOT NULL violation
  status: "ACTIVE"                            # ✗ Exceeds 1 char
  level: 999                                  # ✗ Exceeds NUMBER(2)
```

#### Conversion Example

**Complex Oracle SQL:**
```sql
<select id="selectOrderList" resultType="Order">
  SELECT 
    O.ORDER_ID,
    O.ORDER_DATE,
    NVL(O.TOTAL_AMT, 0) AS TOTAL_AMT,
    DECODE(O.STATUS, 'Y', 'Active', 'Inactive') AS STATUS_NAME,
    U.USER_NAME,
    TO_CHAR(O.CREATE_DT, 'YYYY-MM-DD') AS CREATE_DATE,
    SEQ_ORDER.NEXTVAL AS NEXT_SEQ
  FROM TB_ORDER O, TB_USER U
  WHERE O.USER_ID = U.USER_ID(+)
    AND O.ORDER_DATE >= #{startDate}
    AND O.TOTAL_AMT + #{discount} <= #{maxAmt}
    AND ROWNUM <= #{limit}
  ORDER BY O.ORDER_DATE DESC
</select>
```

**PostgreSQL Conversion Result:**
```sql
<select id="selectOrderList" resultType="Order">
  SELECT 
    o.order_id,
    o.order_date,
    COALESCE(o.total_amt, 0) AS total_amt,
    CASE WHEN o.status = 'Y' THEN 'Active' ELSE 'Inactive' END AS status_name,
    u.user_name,
    TO_CHAR(o.create_dt, 'YYYY-MM-DD') AS create_date,
    NEXTVAL('seq_order') AS next_seq
  FROM tb_order o
  LEFT JOIN tb_user u ON o.user_id = u.user_id
  WHERE o.order_date >= #{startDate}::DATE
    AND o.total_amt::NUMERIC + #{discount}::NUMERIC <= #{maxAmt}::NUMERIC
  ORDER BY o.order_date DESC
  LIMIT #{limit}::INTEGER
</select>
```

**Changes:**
1. ✅ `NVL` → `COALESCE`
2. ✅ `DECODE` → `CASE WHEN`
3. ✅ `(+)` → `LEFT JOIN`
4. ✅ `SEQ.NEXTVAL` → `NEXTVAL('seq')`
5. ✅ `ROWNUM` → `LIMIT`
6. ✅ Lowercase conversion (table/column names)
7. ✅ Type casting (`::DATE`, `::NUMERIC`, `::INTEGER`)

**Generated TC File:**
```json
{
  "file": "selectOrderList.xml",
  "bind_variables": {
    "#{startDate}": "TB_ORDER.ORDER_DATE",
    "#{discount}": "TB_ORDER.TOTAL_AMT",
    "#{maxAmt}": "TB_ORDER.TOTAL_AMT",
    "#{limit}": "ROWNUM"
  },
  "test_cases": [
    {
      "description": "Recent orders with small discount",
      "parameters": {
        "startDate": "2024-01-01",
        "discount": 1000,
        "maxAmt": 50000,
        "limit": 10
      }
    },
    {
      "description": "All-time orders with no discount",
      "parameters": {
        "startDate": "2020-01-01",
        "discount": 0,
        "maxAmt": 999999,
        "limit": 100
      }
    }
  ]
}
```

---

### Step 4: Mapper Merging (If Split)

Merge split files back into a single Mapper XML.

**Execute in Claude Code:**
```
/merge-mappers my-project
```

**Input:**
```
mappers/
└── my-project/
    └── target/
        └── UserMapper/
            ├── selectUser.xml
            ├── insertUser.xml
            └── ...
```

**Output:**
```
TARGET_WORKSPACE/
└── my-project/
    └── mappers/
        └── UserMapper.xml  (merged file)
```

**Merge Logic:**
- Remove duplicate resultMap, sql fragments
- Sort by SQL ID
- Preserve namespace

---

### Step 5: Validator Execution (Verification)

Verify converted SQL on actual database.

**Execute in Claude Code:**
```
/run-validator my-project
```

**Verification Method:**
1. Execute Oracle Mapper + Oracle DB
2. Execute Target Mapper + Target DB
3. Compare results (structure, data types, sample data)

**Include OGNL Library (if found):**
```bash
# Outside Claude Code
export CLASSPATH=/path/to/customer-lib.jar:/path/to/another-lib.jar
cd /home/ec2-user/workspace/oma/app
claude

# Then
/run-validator my-project
```

**Validation Reports:**
```
output/
├── validation-report.json      # Detailed validation results
├── validation.log              # Execution log
└── validation-performance.json # Performance comparison
```

**Report Structure:**
```json
{
  "summary": {
    "total": 150,
    "passed": 145,
    "failed": 5,
    "success_rate": "96.67%",
    "execution_time": "45.2s"
  },
  "failures": [
    {
      "mapper": "UserMapper",
      "sql_id": "selectUserList",
      "error": "Column type mismatch: reg_dt (Oracle: DATE, PG: TIMESTAMP)",
      "oracle_result": {...},
      "target_result": {...}
    }
  ]
}
```

**Re-convert Failed SQL:**
```bash
# Extract failed files from validation-report.json
jq -r '.failures[].file_path' output/validation-report.json | \
  while read file; do
    # In Claude Code
    /convert-sql "$file"
  done

# Re-validate
/run-validator my-project
```

---

## Understanding Extension and OGNL

### Extension Variables

**Automatic Detection (verify-env):**
- Auto-scan when running `verify-env` skill
- Results saved in `extensions/extension.json`

**Manual Review Required:**
```bash
# 1. Review results
cat extensions/extension.json

# 2. Remove false positives (normal column names misclassified as Extension)
vi extensions/extension.json

# 3. Fill in Oracle/PostgreSQL values
{
  "enabled": true,
  "variables": {
    "GRIDPAGING_ROWNUMTYPE_TOP": {
      "oracle": "SELECT GRID_PAGING.*, 1 AS PAGING_CURRENT, 1000 AS PAGING_LIMIT FROM (",
      "postgres": "SELECT GRID_PAGING.*, 1 AS PAGING_CURRENT, 1000 AS PAGING_LIMIT FROM ("
    },
    "GRIDPAGING_ROWNUMTYPE_BOTTOM": {
      "oracle": ") GRID_PAGING WHERE ROWNUM <= 1000",
      "postgres": ") GRID_PAGING LIMIT '1000'::int OFFSET ('1'::int - 1) * '1000'::int"
    }
  }
}
```

**Important Notes:**
- Extension variables are substituted **in TC files only**
- **Target Mapper (PostgreSQL SQL) is NOT modified**
- `#{GRIDPAGING_START}` format maintained as-is (substituted at runtime)

**Detection Criteria (Heuristic):**
- Hardcoded keywords: `GRIDPAGING`, `FRAMEWORK`, `PAGING`
- Uppercase + underscore pattern: `USER_SESSION_ID`
- **Requires customer agreement for keyword modification**

### OGNL Expressions

**Automatic Detection (verify-env):**
- Auto-scan when running `verify-env` skill
- Guide generated at `docs/OGNL_IMPLEMENTATION_GUIDE.md`

**What is OGNL?**
- Java static method calls in MyBatis
- Example: `@com.util.StringUtil@isEmpty(#{name})`

**Handling Method:**
1. Review `docs/OGNL_IMPLEMENTATION_GUIDE.md`
2. Request Java library (.jar) from customer
3. Register CLASSPATH when running Validator
4. Actual verification (Validator tests method calls)

**OGNL NOT Converted:**
- OMA does NOT auto-convert OGNL
- Scan only
- Use customer library as-is

---

## Advanced Features

### Type Cast Error Auto-Fix

```bash
# Execute in Claude Code
/fix-type-errors my-project

# Internal operation:
# 1. Analyze validation-report.json
# 2. Auto-fix type cast errors (::VARCHAR, CAST())
# 3. Re-convert
```

### Partial Re-conversion

```bash
# Re-convert only failed Mappers
jq -r '.failures[].mapper' output/validation-report.json | sort -u | \
  while read mapper; do
    find mappers/my-project/oracle/${mapper} -name "*.xml" | \
      while read file; do
        # In Claude Code
        /convert-sql "$file"
      done
  done
```

---

## Troubleshooting

### Environment Variables Not Loading

**Symptom**: "Missing ORACLE_HOST" error

**Solution:**
```bash
# 1. Check oma.properties
cat ../env/oma.properties

# 2. Test manual loading
source tools/load_oma_env.sh
echo $ORACLE_HOST

# 3. Check permissions
chmod +x tools/load_oma_env.sh
```

### verify-env Fails

**Symptom**: "✗ Oracle database connection failed"

**Solution:**
```bash
# 1. Test Oracle connection directly
sqlplus ${ORACLE_USER}/${ORACLE_PASSWORD}@//${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}

# 2. Check schema
SELECT username FROM all_users WHERE username = 'WMSON';

# 3. Check VPN connection (for on-premises Oracle)
```

### SQL Conversion Too Slow

**Symptom**: > 30 seconds per file

**Solution:**
```bash
# 1. Increase MAX_WORKERS (parallel processing)
vi ../env/oma.properties
MAX_WORKERS=10

# 2. Use faster model
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6

# 3. Check LLM connection
aws bedrock-runtime invoke-model \
  --model-id global.anthropic.claude-opus-4-7 \
  --body '{"anthropic_version":"bedrock-2023-05-31","messages":[{"role":"user","content":"test"}],"max_tokens":10}' \
  /tmp/response.json
```

### Validator Execution Fails

**Symptom**: "java.lang.ClassNotFoundException: oracle.jdbc.OracleDriver"

**Solution:**
```bash
# 1. Check ORACLE_HOME
echo $ORACLE_HOME
ls $ORACLE_HOME/jdbc/lib/ojdbc8.jar

# 2. Rebuild Validator
cd tools/validator
mvn clean package

# 3. Check JAR file
ls -lh target/mapper-validator-1.0.0.jar
```

### Extension Variable Misclassification

**Symptom**: Normal column names classified as Extension

**Solution:**
```bash
# 1. Check extension.json
cat extensions/extension.json

# 2. Delete misclassified variables
vi extensions/extension.json

# Example: USER_ID is normal column → delete
{
  "enabled": true,
  "variables": {
    "GRIDPAGING_START": {...},  // ✅ Extension
    "USER_ID": {...}             // ❌ Delete (normal bind variable)
  }
}
```

---

## Reference

- **Environment Setup**: [env/README.md](../env/README.md)
- **Schema Conversion**: [schema/README.md](../schema/README.md)
- **Claude Code Skills**: [.claude/skills/README.md](.claude/skills/README.md)

---

**Created**: 2026-06-18  
**OMA Version**: 2.0
