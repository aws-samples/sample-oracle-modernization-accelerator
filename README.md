# OMA (Oracle Migration Accelerator)

AI-powered automation tool for migrating Oracle databases to PostgreSQL/MySQL.

> Korean version: [README_KR.md](README_KR.md)  
> Quick Start: [QUICKSTART.md](docs/QUICKSTART.md)

---

## Overview

**OMA (Oracle Migration Accelerator)** is a comprehensive migration solution for transitioning from Oracle databases to PostgreSQL or MySQL.

### Key Features

- ✅ **Fully Automated**: From schema conversion to application code transformation
- ✅ **AI-Powered**: Leveraging Bedrock Claude (Opus 4.7) + Strands Agents SDK
- ✅ **Large-Scale Processing**: TB-scale data migration via AWS DMS
- ✅ **Validation System**: Automatic data integrity and SQL correctness verification
- ✅ **Production Ready**: Validated on real projects (688 tables, 15M+ rows)

---

## Migration Scope

OMA supports migration across 3 areas:

### 1. 📊 Schema Migration

**Convert Oracle database schema to PostgreSQL/MySQL.**

```
Oracle DDL → PostgreSQL/MySQL DDL
- Tables
- Indexes
- Constraints
- Sequences
- Data Types
```

**Key Features:**
- DMS Schema Conversion auto-converts 95% of objects
- AI agent handles remaining 5% (failed/unsupported objects)
- NUMBER type optimization (Oracle PK NUMBER → PostgreSQL NUMERIC)
- Constraint-aware data loading (drop → load → recreate)
- Large-scale data transfer via AWS DMS Full Load Task
- Single procedural script (`main.py`) - no complex orchestration

**Learn More:** [schema/README.md](schema/README.md)

---

### 2. 💻 App Migration

**Convert Oracle SQL in MyBatis Mapper XML to PostgreSQL/MySQL SQL.**

```
Oracle MyBatis Mapper → PostgreSQL/MySQL MyBatis Mapper
- SQL Syntax (Oracle → PostgreSQL/MySQL)
- Bind Variables (#{param} extraction and mapping)
- Test Cases (Auto-generate test cases for Validator)
```

**Key Features:**
- LLM reads, understands, and converts SQL (no regex usage)
- Table/column mapping based on Oracle Dictionary
- Automatic bind variable extraction and data type mapping
- Validator verifies converted SQL against actual DB
- Extension system (framework variable support)

**Learn More:** [app/README.md](app/README.md)

---

### 3. 🛠️ Infrastructure

**Automatically deploy AWS infrastructure via CloudFormation.**

```
CloudFormation Templates
- Oracle RDS (Source)
- PostgreSQL/MySQL RDS (Target)
- DMS Replication Instance
- DMS Endpoints (Source/Target)
- Networking (VPC, Subnet, Security Groups)
```

**Key Features:**
- Deploy entire infrastructure with single command
- Unified configuration via oma.properties
- Multi-environment support (dev/stg/prod)

**Learn More:** [env/README.md](env/README.md)

---

## Project Structure

```
oma/
├── schema/                    # Schema Migration
│   ├── main.py                # Main pipeline script
│   ├── tools/
│   │   ├── dms_sc.py              # DMS Schema Conversion
│   │   ├── conversion_agent.py    # AI agent (failed objects)
│   │   ├── number_type_optimizer.py  # NUMBER→NUMERIC fix
│   │   ├── constraint_manager.py  # Drop/Recreate constraints
│   │   └── dms_load.py           # DMS Full Load
│   └── README.md
│
├── app/                       # App Migration
│   ├── tools/
│   │   ├── convert_sql.py     # SQL conversion (LLM-based)
│   │   ├── validator.py       # SQL validation (actual DB)
│   │   ├── extract_dict.py    # Oracle Dictionary extraction
│   │   └── load_oma_env.sh    # Environment loader
│   ├── skills/                # Claude Code skills
│   │   ├── convert            # Conversion skill
│   │   ├── validate           # Validation skill
│   │   ├── scan-extension     # Extension scan
│   │   └── scan-ognl          # OGNL scan
│   ├── mappers/               # Conversion workspace (auto-created)
│   ├── output/                # Output folder
│   │   ├── oracle_dictionary.json         # Oracle schema info
│   │   ├── conversion-report.json         # Conversion report
│   │   ├── validation-report.json         # Validation report
│   │   └── validation-performance.json    # Performance comparison
│   └── README.md
│
├── env/                       # Infrastructure
│   ├── oma.properties         # Unified configuration (single source of truth)
│   ├── setEnv.sh              # Environment variable loader
│   ├── deploy-omabox.sh       # CloudFormation deployment
│   ├── *.yaml                 # CloudFormation templates
│   └── README.md
│
├── README.md                  # This file
├── README_KR.md               # Korean version
└── docs/
    └── QUICKSTART.md          # Quick start guide
```

---

## Migration Workflow

OMA migration proceeds in 3 steps:

```
┌─────────────────────────────────────────────────────────────┐
│                     OMA Migration Flow                      │
└─────────────────────────────────────────────────────────────┘

Step 1: Infrastructure Setup (env/)
  │
  ├─→ Deploy AWS infrastructure via CloudFormation
  │    - Oracle RDS (Source)
  │    - PostgreSQL/MySQL RDS (Target)
  │    - DMS Replication Instance
  │    - DMS Endpoints
  │
  └─→ Configure oma.properties
       - Database connection info
       - Bedrock LLM settings
       - DMS settings

       ↓

Step 2: Schema Migration (schema/)
  │
  ├─→ Step 1: DMS Schema Conversion (95% auto)
  │    - Execute DMS SC project
  │    - Download and apply converted DDL
  │    - AI agent converts failed objects (5%)
  │
  ├─→ Step 1.5: NUMBER Type Optimization
  │    - Fix Oracle PK NUMBER → PostgreSQL NUMERIC
  │    - Prevent BIGINT insertion errors from DMS
  │
  ├─→ Step 2: Drop FK Constraints
  │    - Save constraint definitions
  │    - Drop all FK constraints for data loading
  │
  ├─→ Step 3: DMS Full Load (Data)
  │    - Auto-discover DMS infrastructure
  │    - Create and run Full Load task
  │    - Transfer large-scale data (parallel)
  │
  └─→ Step 4: Recreate FK Constraints
       - Restore all FK constraints

       ↓

Step 3: Application Migration (app/)
  │
  ├─→ Preparation
  │    1. Extract Oracle Dictionary
  │    2. Scan Extensions (framework variables)
  │    3. Scan OGNL (Java static method calls)
  │
  ├─→ SQL Conversion (LLM-based)
  │    - Parse MyBatis Mapper XML
  │    - LLM understands and converts SQL
  │    - Extract and map bind variables
  │    - Auto-generate test cases
  │    - Apply Extension variables
  │
  ├─→ SQL Validation (Validator)
  │    - Execute original SQL (Oracle)
  │    - Execute converted SQL (PostgreSQL/MySQL)
  │    - Compare results (row count, column count)
  │    - Compare performance (execution time)
  │
  └─→ Reporting
       - Conversion report (per-file statistics)
       - Validation report (success/failure)
       - Performance report (Oracle vs Target)

       ↓

✅ Migration Complete!
```

---

## Technology Stack

### AI & LLM

- **Bedrock Claude Opus 4.7**: Schema and SQL conversion
- **Strands Agents SDK**: AI agent for failed object conversion
- **LLM-based Parsing**: LLM understands SQL structure instead of regex

### AWS Services

- **Amazon Bedrock**: LLM hosting
- **AWS DMS**: Large-scale data migration
- **Amazon RDS**: Oracle, PostgreSQL, MySQL
- **CloudFormation**: Infrastructure as Code
- **AWS Secrets Manager**: Credential management
- **CloudWatch**: Logging and monitoring

### Languages & Frameworks

- **Python 3.11**: Primary development language
- **MyBatis**: ORM framework (conversion target)
- **Bash**: Script automation
- **CloudFormation YAML**: Infrastructure definition

### Databases

- **Oracle 19c+**: Source DB
- **PostgreSQL 15+**: Target DB (Primary)
- **MySQL 8.0+**: Target DB (Alternative)

---

## Getting Started

### Prerequisites

1. **AWS Account**
   - Bedrock access permissions
   - DMS usage permissions
   - RDS creation permissions

2. **Environment**
   - EC2 instance (Amazon Linux 2023 recommended)
   - Python 3.11+
   - Oracle Instant Client (for Oracle connection)

3. **Source Data**
   - Oracle database (accessible)
   - MyBatis Mapper XML files

### Quick Start

**1. Environment Setup**

```bash
cd /home/ec2-user/workspace/oma/env
vi oma.properties  # Enter database connection info
```

**2. Schema Migration**

```bash
cd /home/ec2-user/workspace/oma/schema
python3.11 main.py
```

**3. App Migration**

```bash
cd /home/ec2-user/workspace/oma/app

# Run skills in Claude Code
/scan-extension    # Scan extensions
/scan-ognl         # Scan OGNL
/convert           # Convert SQL
/validate          # Validate SQL
```

**Detailed Guide:** [QUICKSTART.md](docs/QUICKSTART.md)

---

## Key Concepts

### 1. Oracle Dictionary

**JSON file extracted from Oracle schema metadata.**

```json
{
  "schema": "WMSON",
  "tables": {
    "TB_USER": {
      "columns": {
        "USER_ID": {
          "data_type": "NUMBER",
          "data_length": 10,
          "nullable": "N",
          "sample_data": "12345"
        }
      }
    }
  }
}
```

**Purpose:**
- Provide table/column info during SQL conversion
- Map bind variable data types
- Provide sample data for test case generation

**Generation:** `python3.11 tools/extract_dict.py`

---

### 2. Test Case (TC File)

**SQL test cases used by Validator.**

```json
{
  "file": "selectUser.xml",
  "bind_variables": {
    "#{userId}": "TB_USER.USER_ID",
    "#{userName}": "TB_USER.USER_NAME"
  },
  "test_cases": [
    {
      "description": "Basic query",
      "parameters": {
        "userId": "12345",
        "userName": "John Doe"
      }
    }
  ]
}
```

**Purpose:**
- Validate converted SQL against actual DB
- Auto-test multiple scenarios
- Compare results: Oracle vs Target DB

**Generation:** Auto-generated during SQL conversion

---

### 3. Extension System

**System supporting customer framework bind variables.**

```xml
<!-- Original TC file (before Extension) -->
<select id="selectList">
  #{GRIDPAGING_ROWNUMTYPE_TOP}
  SELECT * FROM TB_USER
  WHERE USER_ID = #{userId}
  #{GRIDPAGING_ROWNUMTYPE_BOTTOM}
</select>
```

```json
// Extension definition
{
  "GRIDPAGING_ROWNUMTYPE_TOP": {
    "grid": "SELECT * FROM (",
    "combo": ""
  },
  "GRIDPAGING_ROWNUMTYPE_BOTTOM": {
    "grid": ") WHERE ROWNUM <= 10",
    "combo": ""
  }
}
```

```xml
<!-- TC file (after Extension applied) -->
<select id="selectList">
  SELECT * FROM (
  SELECT * FROM TB_USER
  WHERE USER_ID = #{userId}
  ) WHERE ROWNUM <= 10
</select>
```

**Important:** Extensions only apply to TC files; target mappers are not modified.

---

### 4. OGNL Expression

**Expression calling Java static methods in MyBatis.**

```xml
<if test="@com.example.Util@isNotEmpty(value)">
  AND USER_NAME = #{value}
</if>
```

**OMA Handling:**
- Scan to identify usage
- No conversion (customer handles manually)
- Record usage in reports

---

### 5. LLM-based SQL Parsing

**LLM reads and understands SQL instead of regex.**

**Why use LLM?**

```sql
-- Cases difficult for regex:

-- 1. Comma-separated tables
SELECT * FROM A, B, C WHERE A.ID = B.ID

-- 2. Nested subqueries
SELECT * FROM (
  SELECT * FROM (
    SELECT * FROM TB_USER
  ) INNER_QUERY
) OUTER_QUERY

-- 3. CTE (Common Table Expression)
WITH TEMP AS (SELECT * FROM TB_USER)
SELECT * FROM TEMP

-- 4. UNION queries
SELECT * FROM TB_USER
UNION
SELECT * FROM TB_ADMIN
```

**LLM Advantages:**
- Accurately parses any complex SQL
- Perfect extraction of table names, column names, bind variables
- Understands context (finds tables in subqueries too)

---

## Reporting

OMA generates detailed reports for each stage.

### Schema Migration Reports

```
schema/results/
├── migration-report.json             # Overall migration report
└── conversion_agent.log              # AI agent conversion log
```

### App Migration Reports

```
app/output/
├── oracle_dictionary.json            # Oracle schema info
├── conversion-report.json            # Conversion detailed report
│   ├── conversion_summary
│   ├── llm_calls (table_extraction, sql_conversion, json_fix)
│   ├── tables_discovered/matched/not_found
│   ├── bind_variables & test_cases
│   └── file_details (per-file statistics)
├── validation-report.json            # Validation report
│   ├── summary (total/success/failed)
│   ├── failed_queries (failure details)
│   └── timing (Oracle vs Target)
└── validation-performance.json       # Performance comparison
    ├── execution_time (Oracle vs Target)
    ├── faster/slower breakdown
    └── performance_summary
```

---

## Advanced Features

### 1. Checkpoint & Resume

**Resume schema migration from interrupted point.**

```bash
# main.py logs progress at each step
# If interrupted, simply re-run:
cd /home/ec2-user/workspace/oma/schema
python3.11 main.py
```

### 2. Parallel Processing

**Speed up app conversion with parallel processing.**

```bash
# Parallel conversion with 4 workers
python3.11 tools/convert_sql.py --parallel 4

# Validation also parallel
python3.11 tools/validator.py --parallel 4
```

### 3. Fragment Reuse

**Automatically inline MyBatis `<sql>` Fragments.**

```xml
<!-- Original -->
<sql id="userColumns">
  USER_ID, USER_NAME, REG_DT
</sql>

<select id="selectUser">
  SELECT <include refid="userColumns"/>
  FROM TB_USER
</select>

<!-- After conversion -->
<select id="selectUser">
  SELECT USER_ID, USER_NAME, REG_DT
  FROM tb_user
</select>
```

### 4. DMS Schema Conversion

**DMS SC is used by default in main.py. Configure in oma.properties:**

```properties
# oma.properties
DMS_SC_S3_BUCKET=oma-dms-sc-896586841913
DMS_MIGRATION_PROJECT_ARN=arn:aws:dms:...
```

---

## Limitations

### 1. MyBatis Dynamic SQL

**Full automation is challenging. Partial support:**

- ✅ `<if>`, `<choose>`, `<when>` → LLM understands and generates test cases
- ⚠️ Complex nested conditions → Manual review needed
- ⚠️ OGNL expressions → Scan only, no conversion

### 2. Oracle-Specific Features

**Features not available in Target DB require manual handling:**

- ❌ PL/SQL (Stored Procedures, Functions, Packages)
- ❌ Oracle Materialized Views
- ❌ Oracle-specific Hints
- ⚠️ CONNECT BY (PostgreSQL: convertible to WITH RECURSIVE)

### 3. Data Type Conversion

**Some data types require attention:**

- ⚠️ `DATE` → `TIMESTAMP` (time information added)
- ⚠️ `NUMBER` → `NUMERIC` (precision verification needed)
- ⚠️ `VARCHAR2(4000)` → `VARCHAR(4000)` (max length may differ)

### 4. Extension System

**Customer framework variables require prior agreement:**

- Extension keywords defined through customer consultation
- Target mappers not modified (only TC files substituted)

---

## Troubleshooting

### Schema Migration Failed

**Symptom**: "DMS Task failed"

**Solution:**
```bash
# Check DMS Task logs
aws logs tail /aws/dms/tasks/<task-id> --follow

# Check task statistics
aws dms describe-table-statistics --replication-task-arn <arn>
```

### App Conversion Failed

**Symptom**: "Table not found in dictionary"

**Solution:**
```bash
# Regenerate Oracle Dictionary
cd app
python3.11 tools/extract_dict.py \
  --host $ORACLE_HOST \
  --schema $ORACLE_SCHEMA \
  --output output/oracle_dictionary.json

# Add specific tables only
python3.11 tools/extract_dict.py --tables TB_USER,TB_ORDER
```

### Validation Failed

**Symptom**: "Query execution failed"

**Solution:**
```bash
# Re-validate failed files only
python3.11 tools/validator.py \
  --failed-only \
  --tc-dir mappers

# Check detailed logs
python3.11 tools/validator.py --verbose
```

---

## Performance Optimization

### 1. Schema Migration

- **DMS Parallel Load**: `MaxFullLoadSubTasks: 8` (default)
- **CommitRate**: 10000 rows (adjustable)
- **Replication Instance**: r5.xlarge or higher recommended

### 2. App Conversion

- **Parallel Workers**: Adjust to CPU core count
  ```bash
  # 4-core CPU
  python3.11 tools/convert_sql.py --parallel 3
  
  # 8-core CPU
  python3.11 tools/convert_sql.py --parallel 6
  ```

- **Minimize LLM Calls**: Leverage dictionary caching

### 3. Validation

- **Batch Size**: Adjust number of files to validate at once
- **Timeout**: Increase timeout for complex queries
  ```bash
  python3.11 tools/validator.py --timeout 60
  ```

---

## Security

### 1. Credential Management

**Use Secrets Manager instead of plaintext in oma.properties:**

```bash
# Auto-load from Secrets Manager
export USE_SECRETS_MANAGER=true

# main.py automatically reads from Secrets Manager
python3.11 main.py
```

### 2. Network Security

- Deploy DMS Replication Instance in Private Subnet
- Access control via Security Groups
- Use VPC Peering or Transit Gateway

### 3. Data Security

- DMS encrypts in transit (TLS)
- RDS storage encryption (KMS)
- CloudWatch Logs log group encryption

---

## References

### Internal Documentation

- [Schema Migration Guide](schema/README.md)
- [App Migration Guide](app/README.md)
- [Environment Setup Guide](env/README.md)
- [Quick Start Guide](QUICKSTART.md)

### External Documentation

- [AWS DMS Official Docs](https://docs.aws.amazon.com/dms/)
- [Bedrock Official Docs](https://docs.aws.amazon.com/bedrock/)
- [PostgreSQL Official Docs](https://www.postgresql.org/docs/)
- [MyBatis Official Docs](https://mybatis.org/mybatis-3/)

---

## License

This project is for internal use only.

---

## Support

If issues occur, check the following:

1. **Log Files**: Check detailed logs for each tool
2. **Report Files**: Analyze failure causes
3. **Environment Config**: Verify oma.properties
4. **AWS Status**: Check DMS, RDS, Bedrock service status

---

**Created**: 2026-06-23  
**OMA Version**: 2.0  
**Supported DBs**: Oracle 19c+ → PostgreSQL 15+, MySQL 8.0+
