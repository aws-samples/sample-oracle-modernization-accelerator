# Oracle to Aurora Migration Skills

This directory contains skills for Oracle to Aurora database migration.

## Available Skills

### 1. verify-env
Verifies the Oracle and Aurora database connectivity and environment setup.

**Usage:**
```bash
./.claude/skills/verify-env.sh
```

**Checks:**
1. Python 3.11+ auto-detection
2. Environment variables (ORACLE_HOME, DB credentials, etc.)
3. Oracle client (sqlplus) availability
4. Target database client (psql/mysql) availability
5. Oracle database connectivity and schema existence
6. Target database connectivity and schema existence
7. Source workspace and project detection
8. Mapper directory structure auto-creation
9. Bedrock LLM connectivity test

**Exit codes:**
- 0: All checks passed
- 1: One or more checks failed

---

### 2. build-oracle-dict
Builds Oracle database dictionary with complete metadata and sample data.

**Usage:**
```bash
./.claude/skills/build-oracle-dict.sh [sample-size]
```

**Features:**
- Extracts all tables, columns, data types, constraints
- Captures column length, precision, scale information
- Collects primary keys, foreign keys (optional)
- Captures table and column comments
- Gathers sample data for each column (configurable sample size)
- Calculates row counts
- Exports to JSON format

**Output:**
Dictionary saved to `./oracle_dictionary.json`

**Dictionary Structure:**
```json
{
  "schema": "WMSON",
  "generated_at": "2026-06-10T12:00:00",
  "total_tables": 688,
  "tables": {
    "TABLE_NAME": {
      "row_count": 1000,
      "columns": [
        {
          "column_name": "ID",
          "data_type": "NUMBER",
          "data_length": 22,
          "data_precision": 10,
          "data_scale": 0,
          "nullable": false,
          "sample_value": "12345"
        }
      ]
    }
  }
}
```

**Lookup Functions:**
```bash
# Lookup specific column
python3.11 tools/oracle_dictionary.py --lookup TABLE_NAME.COLUMN_NAME

# Get table info
python3.11 tools/oracle_dictionary.py --table TABLE_NAME
```

---

### 3. split-mappers
Splits MyBatis mapper XML files into individual SQL statement files.

**Usage:**
```bash
./.claude/skills/split-mappers.sh [project-name]
```

**Features:**
- Splits by SQL ID (select/insert/update/delete)
- Preserves resultMap and sql fragments in ALL split files
- Maintains namespace and structure
- Creates project-based directory structure

**Example:**
```
Input:  mappers/daiso-oms/original/CommonMapper.xml
Output: mappers/daiso-oms/source/CommonMapper_selectUser.xml
        mappers/daiso-oms/source/CommonMapper_insertUser.xml
        (each file includes all resultMap and sql fragments)
```

---

### 4. convert-sql
Converts Oracle SQL to target database using Bedrock LLM with explicit type casting and test case generation.

**Usage:**
```bash
./.claude/skills/convert-sql.sh <project-name>
```

**Features:**
- Oracle → PostgreSQL/MySQL syntax conversion
- **Explicit type casting** based on Oracle dictionary
  - NUMBER(precision, 0) → ::INTEGER or ::BIGINT
  - NUMBER with decimals → ::NUMERIC or ::DECIMAL
  - VARCHAR/CHAR → NO CASTING (automatic)
  - DATE/TIMESTAMP → ::TIMESTAMP
- Preserves resultMap and sql fragments
- Parallel processing (10 workers by default)
- Automatic test case generation with column constraints

**Example Conversion:**
```xml
<!-- Oracle -->
<insert id="insertOrder">
  INSERT INTO ORDERS (ORDER_ID, AMOUNT, ORDER_DATE)
  VALUES (#{orderId}, #{amount}, #{orderDate})
</insert>

<!-- PostgreSQL (converted) -->
<insert id="insertOrder">
  INSERT INTO ORDERS (ORDER_ID, AMOUNT, ORDER_DATE)
  VALUES (#{orderId}::INTEGER, #{amount}::NUMERIC, #{orderDate}::TIMESTAMP)
</insert>
```

**Output:**
- Converted XML files in `mappers/{project}/target/`
- Test case JSON files (*.tc.json) with:
  - Bind variable to table.column mapping
  - Data types with length/precision/scale
  - Test cases respecting column constraints

**Test Case Example:**
```json
{
  "file": "OrderMapper_insertOrder.xml",
  "bind_variables": {
    "#{orderId}": "ORDERS.ORDER_ID",
    "#{amount}": "ORDERS.AMOUNT"
  },
  "data_types": {
    "ORDERS.ORDER_ID": {
      "type": "NUMBER",
      "precision": 10,
      "scale": 0,
      "nullable": false
    },
    "ORDERS.AMOUNT": {
      "type": "NUMBER",
      "precision": 12,
      "scale": 2,
      "nullable": true
    }
  },
  "test_cases": [...]
}
```

---

### 5. merge-mappers
Merges split and converted mapper files back into original structure and copies to target workspace.

**Usage:**
```bash
./.claude/skills/merge-mappers.sh [project-name]
```

**Features:**
- Merges split files back to original mapper structure
- Copies to TARGET_WORKSPACE
- Preserves directory structure

**Example:**
```
Input:  mappers/daiso-oms/target/CommonMapper_*.xml
Output: /home/ec2-user/workspace/target/daiso-oms/.../CommonMapper.xml
```

---

### 6. scan-ognl
Scans MyBatis mapper files for OGNL expressions and generates handler library.

**Usage:**
```bash
# Scan specific project
./.claude/skills/scan-ognl.sh mappers/daiso-oms/source

# Scan and generate handlers
./.claude/skills/scan-ognl.sh mappers/daiso-oms/source --generate

# Scan all projects
./.claude/skills/scan-ognl.sh --all --generate
```

**Features:**
- Scans all mapper XML files for OGNL patterns
- Identifies classes, methods, and usage statistics
- **Generates handlers with original package names** (no XML modification)
- Creates JSON scan report
- Builds JAR file for deployment

**Output:**
```
lib/ognl_handlers/
├── oma-ognl-handlers.jar (2.1KB)
├── com/kns/framework/util/StringUtil.java
├── com/kns/framework/util/CmFunction.java
├── org/springframework/util/CollectionUtils.java
├── ognl_scan_report.json
└── README.md
```

**Scan Report Example:**
```json
{
  "total_classes": 3,
  "classes": {
    "com.kns.framework.util.StringUtil": {
      "isEmpty": {"usage_count": 68},
      "isNotEmpty": {"usage_count": 574}
    }
  }
}
```

**Deployment:**
```bash
# Tomcat
cp lib/ognl_handlers/oma-ognl-handlers.jar $CATALINA_HOME/lib/

# Spring Boot
java -cp lib/ognl_handlers/oma-ognl-handlers.jar:app.jar com.your.Main
```

---

## OGNL Handler Library

MyBatis mappers use OGNL expressions that require specific utility classes. The OGNL handler library provides these utilities without modifying source code.

### Scan OGNL Expressions
```bash
python3.11 tools/scan_ognl.py \
  --source-dir /path/to/mappers \
  --output-dir ./lib/ognl_handlers \
  --generate
```

**Features:**
- Scans all mapper files for OGNL expressions
- Generates handlers with **original package names** (no XML modification needed)
- Creates JSON report with usage statistics
- Builds JAR file for deployment

**Generated Library:**
```
lib/ognl_handlers/
├── oma-ognl-handlers.jar (2.1KB)
├── com/kns/framework/util/StringUtil.java
├── com/kns/framework/util/CmFunction.java
├── org/springframework/util/CollectionUtils.java
└── README.md
```

**Usage in Application:**
```bash
# Tomcat
cp lib/ognl_handlers/oma-ognl-handlers.jar $CATALINA_HOME/lib/

# Spring Boot
java -cp lib/ognl_handlers/oma-ognl-handlers.jar:app.jar com.your.Main
```

---

## Environment Variables

Required variables in `.env`:

### Oracle (Source)
- `ORACLE_HOME`: Oracle client installation directory
- `ORACLE_HOST`: Oracle database host
- `ORACLE_PORT`: Oracle database port (default: 1521)
- `ORACLE_SID`: Oracle SID or service name
- `ORACLE_CONN_TYPE`: Connection type (service or sid)
- `ORACLE_USER`: Oracle username
- `ORACLE_PASSWORD`: Oracle password
- `ORACLE_SCHEMA`: Oracle schema name

### Target Database
- `TARGET_DB_TYPE`: Target database type (postgres or mysql)

### PostgreSQL (if TARGET_DB_TYPE=postgres)
- `PG_HOST`: PostgreSQL host
- `PG_PORT`: PostgreSQL port (default: 5432)
- `PG_DATABASE`: PostgreSQL database name
- `PG_SCHEMA`: PostgreSQL schema name
- `PG_USER`: PostgreSQL username
- `PG_PASSWORD`: PostgreSQL password

### Migration Settings
- `SOURCE_WORKSPACE`: Source projects directory
- `TARGET_WORKSPACE`: Target projects directory
- `MAPPER_WORK_DIR`: Working directory for mapper files (default: ./mappers)
- `ORACLE_DICT_PATH`: Oracle dictionary JSON path (default: ./oracle_dictionary.json)
- `OMA_OGNL_JAR`: OGNL handler JAR path (default: ./lib/ognl_handlers/oma-ognl-handlers.jar)

### Bedrock LLM
- `BEDROCK_REGION`: AWS region (default: ap-northeast-2)
- `BEDROCK_MODEL_ID`: Bedrock model ID (default: anthropic.claude-3-5-sonnet-20240620-v1:0)

---

## Workflow

### Complete Migration Process
```bash
# 1. Verify environment
./.claude/skills/verify-env.sh

# 2. Build Oracle dictionary (688 tables)
./.claude/skills/build-oracle-dict.sh

# 3. Split mappers for a project
./.claude/skills/split-mappers.sh daiso-oms

# 4. Convert SQL with type casting
./.claude/skills/convert-sql.sh daiso-oms

# 5. Merge back to target workspace
./.claude/skills/merge-mappers.sh daiso-oms

# 6. Build OGNL handler library (one-time)
python3.11 tools/scan_ognl.py \
  --source-dir mappers/daiso-oms/source \
  --output-dir ./lib/ognl_handlers \
  --generate
```

### Projects
Current source workspace contains 7 projects:
- daiso-oms
- daiso-api
- daiso-wms
- daiso-batch
- daiso-ams
- daiso-wif
- daiso-report

---

## Key Features

### Type Casting Intelligence
- ✅ Uses Oracle dictionary for accurate type information
- ✅ VARCHAR/CHAR: No casting (PostgreSQL handles automatically)
- ✅ NUMBER integers: ::INTEGER or ::BIGINT
- ✅ NUMBER decimals: ::NUMERIC or ::DECIMAL
- ✅ DATE/TIMESTAMP: ::TIMESTAMP

### Test Case Quality
- ✅ Respects column length constraints (VARCHAR2(20))
- ✅ Respects NUMBER precision/scale (NUMBER(10,2))
- ✅ Respects NOT NULL constraints
- ✅ Generates realistic business values

### OGNL Support
- ✅ 650 OGNL expressions across 72 mapper files
- ✅ Original package names preserved
- ✅ No mapper XML modification needed
- ✅ Lightweight 2.1KB JAR file

---

## Troubleshooting

### Issue: Python not found
**Solution:** Run verify-env.sh - it auto-detects Python 3.11+

### Issue: Oracle connection failed
**Solution:** Check ORACLE_HOME and LD_LIBRARY_PATH, verify credentials

### Issue: Bedrock access denied
**Solution:** Verify AWS credentials and Bedrock model access in region

### Issue: Missing resultMap/sql fragments
**Solution:** Already fixed in current split_mapper.py - common elements included

### Issue: Type casting not applied
**Solution:** Ensure oracle_dictionary.json exists and convert_sql.py is latest version
