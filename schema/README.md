# OMA Schema Conversion

Automatically convert Oracle database schemas to PostgreSQL/MySQL.

> Korean version: [README_KR.md](README_KR.md)

## Overview

The `schema` folder provides tools to automatically convert Oracle database schemas (tables, indexes, constraints, sequences, etc.) to PostgreSQL/MySQL and migrate data.

### Key Features

- **Automated Schema Conversion**: Oracle DDL → PostgreSQL/MySQL DDL automatic generation
- **AI-Powered Conversion**: Using Strands Agents SDK + Bedrock Claude
- **DMS Data Migration**: Large-scale data transfer via AWS DMS Full Load Task
- **Data Integrity Verification**: Compare data between Oracle vs Target DB
- **Checkpoint & Resume**: Resume interrupted migrations

---

## Folder Structure

```
schema/
├── postgresql/
│   ├── scripts/
│   │   └── run_migration.py     # PostgreSQL migration main script
│   ├── agents/                  # Strands Agents (analyze, convert, verify)
│   ├── tools/                   # PostgreSQL tools
│   └── rules/                   # Conversion rules
├── mysql/
│   ├── scripts/
│   │   └── run_migration.py     # MySQL migration main script
│   ├── agents/                  # Strands Agents
│   ├── tools/                   # MySQL tools
│   └── rules/                   # Conversion rules
├── common/
│   ├── orchestrator/            # Pipeline orchestration
│   ├── tools/
│   │   ├── oracle_tools.py      # Oracle connection/queries
│   │   ├── dms_sc_tools.py      # DMS Schema Conversion
│   │   ├── dms_full_load_tools.py  # DMS data migration
│   │   └── analysis_tools.py    # Schema analysis
│   └── rules/                   # Common conversion rules
├── tools/
│   └── extract_sequence_usage.py  # Extract sequence usage
├── migration-config.json        # Migration configuration (auto-generated)
└── results/                     # Migration outputs
```

---

## Prerequisites

### 1. Environment Setup

Configure environment variables in `/home/ec2-user/workspace/oma/env/oma.properties`:

```properties
[COMMON]
# Oracle Connection
ORACLE_HOST=10.0.X.X
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_CONN_TYPE=service
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

# MySQL Connection
MYSQL_HOST=cluster.xxxxx.region.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_DATABASE=dbname
MYSQL_USER=username
MYSQL_PASSWORD=password

# Bedrock LLM
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7

# Target DB Type
TARGET_DB_TYPE=postgres
```

> 📝 **Note**: See [env/README.md](../env/README.md) for detailed environment setup

### 2. DMS Infrastructure Setup (Optional)

**DMS is required for data migration:**

1. **DMS Replication Instance** creation
2. **DMS Source Endpoint** (Oracle)
3. **DMS Target Endpoint** (PostgreSQL/MySQL)

> 📝 **Auto-discovery**: If not in environment variables, automatically discovered from AWS

---

## Migration Process

### How to Run

```bash
# Migrate to PostgreSQL
cd /home/ec2-user/workspace/oma/schema/postgresql/scripts
python3.11 run_migration.py

# Migrate to MySQL
cd /home/ec2-user/workspace/oma/schema/mysql/scripts
python3.11 run_migration.py
```

### 4-Phase Pipeline

```
Phase 1: Schema Migration (AI-based DDL conversion)
   ↓
Phase 2: Data Migration (DMS Full Load Task)
   ↓
Phase 3: Data Integrity Verification
   ↓
Phase 4: Report Generation
```

---

### Phase 1: Schema Migration

**Automatically convert Oracle schema to PostgreSQL/MySQL DDL.**

#### How it works:

**1. Strands Agents SDK Graph Pipeline**
- AI agents collaborate to perform schema conversion
- Uses Bedrock Claude (Opus 4.7)
- Each agent has a specific role

**2. Key Agents:**

| Agent | Role |
|-------|------|
| **Discovery** | Explore Oracle schema (tables, indexes, constraints, sequences) |
| **Schema Architect** | Plan DDL conversion strategy |
| **Code Migrator** | Convert Oracle DDL → Target DDL |
| **QA Verifier** | Validate converted DDL |
| **Evaluator** | Overall quality assessment |

**3. Conversion Items:**

```sql
-- Tables
Oracle: CREATE TABLE TB_USER (USER_ID NUMBER(10), ...)
→ PostgreSQL: CREATE TABLE tb_user (user_id INTEGER, ...)

-- Indexes
Oracle: CREATE INDEX IDX_USER_NAME ON TB_USER(USER_NAME)
→ PostgreSQL: CREATE INDEX idx_user_name ON tb_user(user_name)

-- Primary Keys
Oracle: CONSTRAINT PK_USER PRIMARY KEY (USER_ID)
→ PostgreSQL: CONSTRAINT pk_user PRIMARY KEY (user_id)

-- Foreign Keys
Oracle: CONSTRAINT FK_ORDER_USER FOREIGN KEY (USER_ID) REFERENCES TB_USER(USER_ID)
→ PostgreSQL: CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES tb_user(user_id)

-- Sequences
Oracle: CREATE SEQUENCE SEQ_USER START WITH 1
→ PostgreSQL: CREATE SEQUENCE seq_user START WITH 1

-- Data Types
Oracle: NUMBER(10,2) → PostgreSQL: NUMERIC(10,2)
Oracle: VARCHAR2(100) → PostgreSQL: VARCHAR(100)
Oracle: DATE → PostgreSQL: TIMESTAMP
Oracle: CLOB → PostgreSQL: TEXT
Oracle: BLOB → PostgreSQL: BYTEA
```

**4. Output:**

```
results/
├── ddl_output.sql              # Converted DDL
├── migration-report.json       # Detailed conversion report
└── checkpoints/                # Checkpoints (for resume)
    └── {migration_id}/
```

**5. Execution Log Example:**

```
[INFO] PHASE 1: Schema Migration Pipeline
[INFO] Discovering Oracle schema: WMSON
[INFO] Found 688 tables, 2450 indexes, 1230 constraints
[INFO] Agent 'Schema Architect': Planning conversion strategy
[INFO] Agent 'Code Migrator': Converting DDL (batch 1/10)
[INFO] Agent 'QA Verifier': Validating converted DDL
[INFO] Schema status: COMPLETED (245.3s)
```

---

### Phase 2: Data Migration

**Migrate large-scale data using AWS DMS Full Load Task.**

#### How it works:

**1. DMS Infrastructure Auto-discovery**
```python
# Read from environment variables or auto-discover via AWS API
- DMS Replication Instance
- Source Endpoint (Oracle)
- Target Endpoint (PostgreSQL/MySQL)
```

**2. DMS Full Load Task Creation**
```python
# Table Mappings Configuration
{
  "rules": [
    {
      "rule-type": "selection",
      "schema-name": "WMSON",
      "table-name": "%"
    },
    {
      "rule-type": "transformation",
      "rule-action": "convert-lowercase"  # Convert to lowercase
    }
  ]
}

# Task Settings
{
  "TargetMetadata": {
    "TargetTablePrepMode": "TRUNCATE_BEFORE_LOAD"  # Clear existing data
  },
  "FullLoadSettings": {
    "MaxFullLoadSubTasks": 8,  # Parallel processing
    "CommitRate": 10000
  }
}
```

**3. Task Execution & Monitoring**
```
→ Task created: oma-full-load-wmson-1234567890
→ Task started
→ Progress monitoring (check every 30 seconds)
  - Progress: 45%
  - Completed tables: 310/688
  - Rows loaded: 15,234,567
→ Wait for completion (max 8 hours)
```

**4. Benefits:**

✅ **AWS Managed Service**
- Runs in background even if terminal disconnects
- Monitor via CloudWatch
- Fast performance with parallel processing

✅ **Large-Scale Data Handling**
- Can handle hundreds of GB ~ TB of data
- Automatic retry and error handling

✅ **Data Integrity**
- Clean load with TRUNCATE_BEFORE_LOAD
- Transaction consistency guaranteed

**5. Execution Log Example:**

```
[INFO] PHASE 2: Data Migration via DMS Full Load Task
[INFO] Discovering DMS infrastructure...
[INFO] Found DMS instance: oma-replication-instance
[INFO] Found source endpoint: oracle-wmson
[INFO] Found target endpoint: postgres-wmson
[INFO] Creating DMS Full Load task for schema: WMSON
[INFO] DMS task created: oma-full-load-wmson-1719876543
[INFO] Starting DMS Full Load task...
[INFO] DMS task started. Waiting for completion...
[INFO] DMS task progress: 25% (status=running, tables=172, rows=3,456,789)
[INFO] DMS task progress: 50% (status=running, tables=344, rows=7,891,234)
[INFO] DMS task progress: 75% (status=running, tables=516, rows=12,345,678)
[INFO] DMS task progress: 100% (status=stopped, tables=688, rows=15,234,567)
[INFO] Data migration completed in 1834.2s
[INFO] Statistics: {
  "total_tables": 688,
  "full_load_completed": 688,
  "full_load_rows": 15234567,
  "inserts": 15234567
}
```

---

### Phase 3: Data Integrity Verification

**Compare data between Oracle and Target DB to verify integrity.**

#### Verification Items:

**1. Row Count Comparison**
```sql
-- Oracle
SELECT COUNT(*) FROM WMSON.TB_USER;
-- Result: 150,234

-- PostgreSQL
SELECT COUNT(*) FROM wmson.tb_user;
-- Result: 150,234

✓ Row count matches
```

**2. Sample Data Comparison**
```sql
-- Oracle
SELECT * FROM WMSON.TB_USER WHERE ROWNUM <= 10;

-- PostgreSQL
SELECT * FROM wmson.tb_user LIMIT 10;

-- Compare data values (per column)
✓ USER_ID matches
✓ USER_NAME matches
✓ REG_DT matches
```

**3. Verification Report**
```json
{
  "total_tables": 688,
  "verified_tables": 688,
  "mismatches": 0,
  "tables": [
    {
      "table": "tb_user",
      "oracle_count": 150234,
      "postgres_count": 150234,
      "status": "MATCH"
    },
    {
      "table": "tb_order",
      "oracle_count": 523456,
      "postgres_count": 523456,
      "status": "MATCH"
    }
  ]
}
```

**4. Execution Log Example:**

```
[INFO] PHASE 3: Data Integrity Verification (Oracle vs PG)
[INFO] Verifying data integrity for schema: wmson
[INFO] Comparing row counts for 688 tables...
[INFO] Progress: 100/688 tables verified
[INFO] Progress: 200/688 tables verified
[INFO] Progress: 688/688 tables verified
[INFO] Verification completed: 688 matches, 0 mismatches
[INFO] All tables verified successfully!
```

---

### Phase 4: Report Generation

**Generate comprehensive report of entire migration.**

#### Report Contents:

```json
{
  "migration_summary": {
    "migration_id": "oma-migration-1719876543",
    "source_schema": "WMSON",
    "target_schema": "wmson",
    "target_db_type": "postgres",
    "start_time": "2026-06-23T10:00:00",
    "end_time": "2026-06-23T11:30:45",
    "total_duration_seconds": 5445
  },
  
  "phase1_schema": {
    "status": "COMPLETED",
    "duration_seconds": 245,
    "tables_converted": 688,
    "indexes_converted": 2450,
    "constraints_converted": 1230,
    "sequences_converted": 45,
    "output_file": "results/ddl_output.sql"
  },
  
  "phase2_data": {
    "status": "COMPLETED",
    "duration_seconds": 1834,
    "dms_task_arn": "arn:aws:dms:...",
    "tables_loaded": 688,
    "total_rows": 15234567,
    "full_load_completed": 688
  },
  
  "phase3_verification": {
    "status": "COMPLETED",
    "duration_seconds": 3366,
    "total_tables": 688,
    "verified_tables": 688,
    "mismatches": 0,
    "all_verified": true
  },
  
  "recommendations": [
    "✓ Schema conversion completed successfully",
    "✓ All 688 tables migrated (15.2M rows)",
    "✓ Data integrity verified - no mismatches",
    "→ Ready for application migration (App Conversion)"
  ]
}
```

---

## Checkpoint & Resume

**Resume interrupted migrations.**

### Checkpoint Save Points:

1. ✅ After Phase 1 completion
2. ✅ After Phase 2 completion
3. ✅ On Phase 2 failure
4. ✅ After Phase 3 completion

### How to Resume:

```bash
# 1. Check interrupted migration_id
ls results/checkpoints/

# 2. Resume with migration_id
python3.11 run_migration.py --resume oma-migration-1719876543

# Resume behavior:
# - Skip completed phases
# - Restart from failed phase
# - Keep same migration_id
```

**Resume Log Example:**

```
[INFO] Resuming migration: oma-migration-1719876543
[INFO] Phase 1: COMPLETED - Skipping
[INFO] Phase 2: FAILED - Restarting
[INFO] PHASE 2: Data Migration via DMS Full Load Task
[INFO] Creating new DMS task...
```

---

## Output Files

### 1. DDL Output

```sql
-- results/ddl_output.sql

-- Tables
CREATE TABLE wmson.tb_user (
    user_id INTEGER NOT NULL,
    user_name VARCHAR(50),
    reg_dt TIMESTAMP NOT NULL,
    CONSTRAINT pk_user PRIMARY KEY (user_id)
);

-- Indexes
CREATE INDEX idx_user_name ON wmson.tb_user(user_name);

-- Sequences
CREATE SEQUENCE wmson.seq_user START WITH 1 INCREMENT BY 1;

-- Foreign Keys
ALTER TABLE wmson.tb_order
ADD CONSTRAINT fk_order_user
FOREIGN KEY (user_id) REFERENCES wmson.tb_user(user_id);
```

### 2. Migration Reports

```
results/
├── ddl_output.sql                     # Converted DDL
├── migration-report.json              # Overall migration report
├── schema-conversion-report.json      # Phase 1 detailed report
├── data-migration-report.json         # Phase 2 detailed report
├── verification-report.json           # Phase 3 verification report
└── checkpoints/                       # Checkpoints
    └── oma-migration-1719876543/
        ├── schema_completed.json
        ├── data_completed.json
        └── verify_completed.json
```

---

## Advanced Features

### 1. Using DMS Schema Conversion (Optional)

**You can also use AWS DMS Schema Conversion (DMS SC):**

```properties
# Add to oma.properties
DMS_SC_S3_BUCKET=oma-dms-sc-896586841913
DMS_MIGRATION_PROJECT_ARN=arn:aws:dms:ap-northeast-2:896586841913:migration-project:XXX
```

**Benefits:**
- AWS managed schema conversion
- Complex PL/SQL conversion support
- Conversion assessment reports

**Phase 1 automatically uses DMS SC:**
```python
# If DMS SC configuration exists, use it automatically
if os.environ.get("DMS_SC_S3_BUCKET"):
    use_dms_sc_conversion()
else:
    use_ai_agent_conversion()
```

### 2. Partial Migration

**Run specific phases only:**

```bash
# Run Phase 2 only (data migration only)
python3.11 run_data_migration_only.py

# Run Phase 3 only (verification only)
python3.11 run_migration.py --resume <id> --skip-phase1 --skip-phase2
```

### 3. Extract Sequence Usage

**Find where Oracle sequences are used:**

```bash
cd /home/ec2-user/workspace/oma/schema/tools
python3.11 extract_sequence_usage.py --schema WMSON

# Output: sequence-usage-report.json
{
  "SEQ_USER": {
    "tables": ["TB_USER"],
    "trigger": "TRG_USER_ID",
    "current_value": 150234
  }
}
```

---

## Troubleshooting

### DMS Task Creation Failed

**Symptom**: "Failed to create DMS task"

**Solution:**
```bash
# 1. Check DMS infrastructure
aws dms describe-replication-instances
aws dms describe-endpoints

# 2. Test Source/Target Endpoints
aws dms test-connection \
  --replication-instance-arn <arn> \
  --endpoint-arn <endpoint-arn>

# 3. Check permissions (IAM Role)
# DMS needs S3, CloudWatch access permissions
```

### Data Verification Failed

**Symptom**: "Mismatch found: tb_user (Oracle: 150234, PG: 150230)"

**Solution:**
```bash
# 1. Check DMS Task status
aws dms describe-table-statistics \
  --replication-task-arn <task-arn>

# 2. Check error logs (CloudWatch)
# Log Group: /aws/dms/tasks/<task-id>

# 3. Manually compare row counts
sqlplus user/pass@oracle
SELECT COUNT(*) FROM WMSON.TB_USER;

psql -h host -d dbname
SELECT COUNT(*) FROM wmson.tb_user;
```

### Checkpoint Resume Failed

**Symptom**: "Checkpoint not found"

**Solution:**
```bash
# 1. Check checkpoint directory
ls -la results/checkpoints/

# 2. Check migration-config.json
cat migration-config.json

# 3. Start fresh (without --resume)
python3.11 run_migration.py
```

---

## References

- **Environment Setup**: [env/README.md](../env/README.md)
- **App Conversion**: [app/README.md](../app/README.md)
- **AWS DMS Documentation**: https://docs.aws.amazon.com/dms/

---

**Created**: 2026-06-23  
**OMA Version**: 2.0
