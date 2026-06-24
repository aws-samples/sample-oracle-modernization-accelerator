# OMA Quick Start Guide

Start migrating from Oracle to PostgreSQL/MySQL in 30 minutes.

> Korean version: [QUICKSTART_KR.md](QUICKSTART_KR.md)  
> Full documentation: [README.md](README.md)

---

## Prerequisites

### 1. Environment

- ✅ EC2 instance (Amazon Linux 2023)
- ✅ Python 3.11+
- ✅ Oracle Instant Client installed
- ✅ AWS permissions (Bedrock, DMS, RDS)

### 2. Source Data

- ✅ Oracle database accessible
- ✅ MyBatis Mapper XML files

### 3. Expected Duration

| Step | Duration |
|------|----------|
| Step 1: Infrastructure Setup | 5 minutes |
| Step 2: Schema Migration | 10-60 minutes (depends on data size) |
| Step 3: App Migration | 10-30 minutes (depends on file count) |

---

## Step 1: Infrastructure Deployment (15-30 minutes)

### 1.1. Download OMA

```bash
cd /home/ec2-user/workspace
git clone <oma-repository> oma
cd oma
```

### 1.2. Configure oma.properties

```bash
cd env
vi oma.properties
```

**Minimum configuration (before deployment):**

```properties
[COMMON]
# AWS Settings
AWS_REGION=ap-northeast-2

# Bedrock LLM
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7

# Target DB Type
TARGET_DB_TYPE=postgres   # or mysql

[your-application-name]
APPLICATION_NAME=${your-application-name}
```

### 1.3. Deploy AWS Infrastructure

**Automatically deploy entire infrastructure via CloudFormation:**
- Oracle RDS (Source)
- PostgreSQL Aurora or MySQL Aurora (Target)
- DMS Replication Instance
- DMS Endpoints (Source/Target)
- VPC, Subnet, Security Groups

#### 1.3.1. Setup Secrets Manager (Option 1)

```bash
bash deploy-omabox.sh -o 1
```

**Respond to prompts:**
```
1. Oracle Admin Credentials:
Enter Oracle Admin Username: admin
Enter Oracle Admin Password: ********
Enter Oracle Host (e.g., oracle.example.com): your-oracle-host
Enter Oracle Port [1521]: 1521
Enter Oracle SID/Service Name: ORCLPDB1

2. Oracle Service Credentials:
Enter Oracle Service Username: app_user
Enter Oracle Service Password: ********

3. PostgreSQL Credentials (for Aurora PostgreSQL):
Enter PostgreSQL Admin Username [postgres]: postgres
Enter PostgreSQL Admin Password: ********
Enter PostgreSQL Database Name [postgres]: postgres

4. PostgreSQL Service Credentials:
Enter PostgreSQL Service Username [pguser]: app_user
Enter PostgreSQL Service Password: ********
```

**Created Secrets:**
- `oma-secret-oracle-admin`
- `oma-secret-oracle-service`
- `oma-secret-postgres-admin` (or mysql-admin)
- `oma-secret-postgres-service` (or mysql-service)

#### 1.3.2. Deploy CloudFormation Stack (Option 2)

```bash
bash deploy-omabox.sh -o 2
```

**Deployment starts:**
```
[INFO] === CloudFormation Stack Deployment ===
[INFO] Stack Name: oma-your-application-name
[INFO] Target DB: PostgreSQL
[INFO] Region: ap-northeast-2
[INFO] Deploying CloudFormation stack...
```

**Deployment progress (15-30 minutes):**
```
[INFO] Stack Status: CREATE_IN_PROGRESS
[INFO] Creating VPC...
[INFO] Creating Subnets...
[INFO] Creating Security Groups...
[INFO] Creating Oracle RDS...
[INFO] Creating PostgreSQL Aurora...
[INFO] Creating DMS Replication Instance...
[INFO] Stack Status: CREATE_COMPLETE
```

**Deployment completed:**
```
[SUCCESS] CloudFormation stack deployed successfully!
[INFO] Stack Outputs:
  - OracleEndpoint: oracle-oma.xxxxx.ap-northeast-2.rds.amazonaws.com:1521
  - PostgreSQLEndpoint: postgres-oma.cluster-xxxxx.ap-northeast-2.rds.amazonaws.com:5432
  - DMSReplicationInstanceArn: arn:aws:dms:...
  - DMSSourceEndpointArn: arn:aws:dms:...
  - DMSTargetEndpointArn: arn:aws:dms:...
```

### 1.4. Update oma.properties

**After deployment, add CloudFormation Outputs to oma.properties:**

```bash
vi oma.properties
```

```properties
[COMMON]
# Oracle Connection (copy from CloudFormation Output)
ORACLE_HOST=oracle-oma.xxxxx.ap-northeast-2.rds.amazonaws.com
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_CONN_TYPE=service
ORACLE_USER=app_user
ORACLE_PASSWORD=your_password
ORACLE_SCHEMA=YOUR_SCHEMA
ORACLE_HOME=/home/ec2-user/oracle

# PostgreSQL Connection (copy from CloudFormation Output)
PGHOST=postgres-oma.cluster-xxxxx.ap-northeast-2.rds.amazonaws.com
PGPORT=5432
PGDATABASE=postgres
PGSCHEMA=public
PGUSER=app_user
PGPASSWORD=your_password

# DMS Settings (copy from CloudFormation Output)
DMS_REPLICATION_INSTANCE_ARN=arn:aws:dms:ap-northeast-2:123456789012:rep:XXX
DMS_SOURCE_ENDPOINT_ARN=arn:aws:dms:ap-northeast-2:123456789012:endpoint:XXX
DMS_TARGET_ENDPOINT_ARN=arn:aws:dms:ap-northeast-2:123456789012:endpoint:XXX

# Bedrock LLM
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7

# Target DB
TARGET_DB_TYPE=postgres
```

### 1.5. Verify Environment

```bash
# Test Oracle connection
sqlplus $ORACLE_USER/$ORACLE_PASSWORD@//$ORACLE_HOST:$ORACLE_PORT/$ORACLE_SID

# Test PostgreSQL connection
psql  # Automatically recognizes PGHOST and other PG* variables

# Verify DMS infrastructure
aws dms describe-replication-instances --region ap-northeast-2
aws dms describe-endpoints --region ap-northeast-2

# Check Python version
python3.11 --version
```

✅ **Step 1 Complete!** AWS infrastructure is deployed and oma.properties is configured.

---

## Step 2: Schema Migration (10-60 minutes)

### 2.1. Run Schema Migration

```bash
cd /home/ec2-user/workspace/oma/schema/postgresql/scripts
python3.11 run_migration.py
```

**Output during execution:**

```
[INFO] PHASE 1: Schema Migration Pipeline
[INFO] Discovering Oracle schema: YOUR_SCHEMA
[INFO] Found 688 tables, 2450 indexes, 1230 constraints
[INFO] Agent 'Code Migrator': Converting DDL...
[INFO] Schema status: COMPLETED (245.3s)

[INFO] PHASE 2: Data Migration via DMS Full Load Task
[INFO] Creating DMS Full Load task...
[INFO] DMS task progress: 25% (tables=172, rows=3,456,789)
[INFO] DMS task progress: 50% (tables=344, rows=7,891,234)
[INFO] Data migration completed in 1834.2s

[INFO] PHASE 3: Data Integrity Verification
[INFO] Verification completed: 688 matches, 0 mismatches

[INFO] PHASE 4: Report Generation
✓ Migration report saved to: results/migration-report.json
```

### 2.2. Check Results

```bash
# Check converted DDL
cat results/ddl_output.sql | head -50

# Check migration report
cat results/migration-report.json | jq '.'

# Check data verification report
cat results/verification-report.json | jq '.summary'
```

### 2.3. (Optional) Resume Interrupted Migration

```bash
# Check interrupted migration_id
ls results/checkpoints/

# Resume
python3.11 run_migration.py --resume oma-migration-1719876543
```

✅ **Step 2 Complete!** Schema and data have been migrated.

---

## Step 3: App Migration (10-30 minutes)

**⚠️ Important: App conversion must be executed using Claude Code with skills!**

### 3.1. Prepare Source Mappers

```bash
# Copy original MyBatis Mapper files to SOURCE_WORKSPACE
mkdir -p /home/ec2-user/workspace/source/your-project-name
cp -r /path/to/your/mybatis/mappers \
     /home/ec2-user/workspace/source/your-project-name/src/main/resources/mybatis/mapper/
```

### 3.2. Start Claude Code

```bash
# Navigate to app folder
cd /home/ec2-user/workspace/oma/app

# Launch Claude Code
claude
```

**Claude Code will start with app folder as working directory.**

---

### 3.3. Execute Skills in Order

#### Skill 1: Verify Environment (/verify-env)

**Claude Code prompt:**

```
/verify-env
```

**Automatically performs:**
1. Check Python 3.11+
2. Load oma.properties environment variables
3. Test Oracle connection
4. Test PostgreSQL/MySQL connection
5. Detect source workspace
6. **Scan Extensions** (GRIDPAGING_*, FRAMEWORK_* patterns)
7. **Scan OGNL** (@Class@method patterns)
8. Test Bedrock LLM connection

**Output example:**

```
[INFO] ═══════════════════════════════════════════════════════════════
[INFO]           OMA Environment Verification Report
[INFO] ═══════════════════════════════════════════════════════════════

✓ Python: 3.11.9
✓ Environment variables loaded from: /home/ec2-user/workspace/oma/env/oma.properties

✓ Oracle Client: sqlplus available
✓ Oracle Connection: WMSON@oracle-oma.xxxxx:1521/ORCLPDB1
  - Schema exists: WMSON
  - Tables found: 688

✓ PostgreSQL Client: psql available
✓ PostgreSQL Connection: postgres-oma.cluster-xxxxx:5432/postgres
  - Schema exists: public

✓ Source Workspace: /home/ec2-user/workspace/source
  - Projects detected: your-project-name
  - Mapper files: 150 files found

✓ Extension Scan:
  - GRIDPAGING_ROWNUMTYPE_TOP: 45 files
  - GRIDPAGING_ROWNUMTYPE_BOTTOM: 45 files
  - FRAMEWORK_USER_ID: 12 files

✓ OGNL Scan:
  - @com.kns.framework.util.StringUtil@isEmpty: 68 usages
  - @com.kns.framework.util.StringUtil@isNotEmpty: 574 usages
  - @com.example.util.DateUtil@now: 23 usages

✓ Bedrock LLM: global.anthropic.claude-opus-4-7
  - Region: ap-northeast-2
  - Connection: OK

[SUCCESS] ✓ All checks passed! Environment is ready for migration.

Reports saved:
  - output/extension-scan-report.json
  - output/ognl-scan-report.json
```

---

#### Skill 2: Build Oracle Dictionary (/build-oracle-dict)

**Claude Code prompt:**

```
/build-oracle-dict
```

**Automatically performs:**
1. Extract Oracle schema metadata
2. Tables, columns, data types, constraints
3. Primary Keys, Foreign Keys
4. Collect sample data per column
5. Calculate row counts
6. Save in JSON format

**Output example:**

```
[INFO] Connecting to Oracle: WMSON@oracle-oma.xxxxx:1521/ORCLPDB1
[INFO] Extracting schema metadata...
[INFO] Found 688 tables

[INFO] Extracting columns...
[INFO] Progress: 100/688 tables
[INFO] Progress: 200/688 tables
[INFO] Progress: 688/688 tables

[INFO] Collecting sample data...
[INFO] Progress: 688/688 tables

✓ Oracle Dictionary saved to: output/oracle_dictionary.json

Dictionary stats:
  - Total tables: 688
  - Total columns: 5,432
  - Tables with sample data: 688
```

---

#### Skill 3: Split Mappers (/split-mappers)

**Claude Code prompt:**

```
/split-mappers your-project-name
```

**Automatically performs:**
1. Load source mapper files
2. Split by SQL ID (select, insert, update, delete)
3. Include resultMap and sql fragments in all files
4. Create project-based directories

**Output example:**

```
[INFO] Project: your-project-name
[INFO] Source: /home/ec2-user/workspace/source/your-project-name/.../mapper/
[INFO] Target: mappers/your-project-name/source/

[INFO] Processing: CommonMapper.xml
  - selectUser → CommonMapper_selectUser.xml
  - insertUser → CommonMapper_insertUser.xml
  - updateUser → CommonMapper_updateUser.xml
  - deleteUser → CommonMapper_deleteUser.xml

[INFO] Progress: 50/150 files processed
[INFO] Progress: 100/150 files processed
[INFO] Progress: 150/150 files processed

✓ Split completed: 150 files → 450 split files
✓ Output: mappers/your-project-name/source/
```

---

#### Skill 4: Convert SQL (/convert-sql)

**Claude Code prompt:**

```
/convert-sql your-project-name
```

**Automatically performs:**
1. Load split mapper files
2. LLM understands and converts SQL
3. Type casting based on Oracle Dictionary
4. Extract and map bind variables
5. Auto-generate test cases
6. Apply Extension variables (TC files only)

**Output example:**

```
[INFO] Project: your-project-name
[INFO] Source: mappers/your-project-name/source/
[INFO] Target: mappers/your-project-name/target/
[INFO] Parallel workers: 10

[INFO] Converting: CommonMapper_selectUser.xml
  → Phase 1: XML parsing
  → Phase 2: LLM extracts table names
    - Found tables: TB_USER, TB_ROLE
  → Phase 3: Oracle Dictionary lookup
    - Matched: TB_USER (12 columns)
    - Matched: TB_ROLE (5 columns)
  → Phase 4: LLM converts SQL (Oracle → PostgreSQL)
    - VARCHAR: no casting
    - NUMBER(10,0) → ::INTEGER
    - DATE → ::TIMESTAMP
  → Phase 5: Generate Test Cases (5 cases)
  → Phase 6: Save outputs
  ✓ CommonMapper_selectUser.xml - 8 bind vars, 5 test cases

[INFO] Progress: 150/450 files converted
[INFO] Progress: 300/450 files converted
[INFO] Progress: 450/450 files converted

✓ Conversion completed!
✓ Output: mappers/your-project-name/target/
✓ Conversion report saved to: output/conversion-report.json

Summary:
  Total files: 450
  Converted: 448 (99.6%)
  Failed: 2 (0.4%)
  Tables discovered: 45
  Bind variables: 3,234
  Test cases: 2,245
  LLM calls: 900 (table_extraction: 450, sql_conversion: 448, json_fix: 2)
```

---

#### Skill 5: Merge Mappers (/merge-mappers)

**Claude Code prompt:**

```
/merge-mappers your-project-name
```

**Automatically performs:**
1. Merge split files back to original structure
2. Copy to TARGET_WORKSPACE
3. Preserve directory structure

**Output example:**

```
[INFO] Project: your-project-name
[INFO] Source: mappers/your-project-name/target/
[INFO] Target: /home/ec2-user/workspace/target/your-project-name/.../mapper/

[INFO] Merging: CommonMapper_*.xml → CommonMapper.xml
[INFO] Merging: UserMapper_*.xml → UserMapper.xml

[INFO] Progress: 50/150 files merged
[INFO] Progress: 100/150 files merged
[INFO] Progress: 150/150 files merged

✓ Merge completed: 450 files → 150 merged files
✓ Output: /home/ec2-user/workspace/target/your-project-name/.../mapper/
```

---

#### Skill 6: Validate SQL (/validate)

**Claude Code prompt:**

```
/validate your-project-name
```

**Automatically performs:**
1. Load TC files
2. For each test case:
   - Execute Oracle SQL
   - Execute Target SQL
   - Compare results
   - Measure performance
3. Generate reports

**Output example:**

```
[INFO] Project: your-project-name
[INFO] TC Directory: mappers/your-project-name/target/
[INFO] Found 2,245 test cases in 448 files
[INFO] Parallel workers: 4

[INFO] Validating: CommonMapper_selectUser.xml (TC 1/5)
  [Oracle] Executed in 0.023s → 150 rows, 8 columns
  [PostgreSQL] Executed in 0.019s → 150 rows, 8 columns
  ✓ PASS - Results match, PostgreSQL faster by 17%

[INFO] Validating: CommonMapper_selectUser.xml (TC 2/5)
  [Oracle] Executed in 0.031s → 1 row, 8 columns
  [PostgreSQL] Executed in 0.015s → 1 row, 8 columns
  ✓ PASS - Results match, PostgreSQL faster by 52%

[INFO] Progress: 500/2245 test cases validated
[INFO] Progress: 1000/2245 test cases validated
[INFO] Progress: 1500/2245 test cases validated
[INFO] Progress: 2000/2245 test cases validated
[INFO] Progress: 2245/2245 test cases validated

✓ Validation completed!
✓ Validation report saved to: output/validation-report.json
✓ Performance report saved to: output/validation-performance.json

Summary:
  Total queries: 2,245
  Passed: 2,223 (99.0%)
  Failed: 22 (1.0%)
  
Performance:
  PostgreSQL faster: 1,893 queries (84.3%)
  Oracle faster: 352 queries (15.7%)
  Average PostgreSQL speedup: 28%
```

---

### 3.4. Check Results

```bash
# Check conversion report
cat output/conversion-report.json | jq '.conversion_summary'

# Check validation summary
cat output/validation-report.json | jq '.summary'

# Check failed queries
cat output/validation-report.json | jq '.failed_queries[] | {file, query_id, error}'

# Check performance comparison
cat output/validation-performance.json | jq '.performance_summary'

# Check Extension scan results
cat output/extension-scan-report.json | jq '.'

# Check OGNL scan results
cat output/ognl-scan-report.json | jq '.'
```

---

### 3.5. (Optional) Fix Failed SQL Manually

```bash
# 1. Analyze failure causes
cat output/validation-report.json | jq '.failed_queries[] | {file, error}'

# 2. Edit mapper
vi mappers/your-project-name/target/CommonMapper_selectUser.xml

# 3. Re-validate (in Claude Code)
/validate your-project-name
```

---

✅ **Step 3 Complete!** 

**Generated files:**
```
app/
├── mappers/your-project-name/
│   ├── source/                       # Split original
│   │   ├── CommonMapper_selectUser.xml
│   │   └── ...
│   └── target/                       # Converted result
│       ├── CommonMapper_selectUser.xml
│       ├── CommonMapper_selectUser.tc.json
│       └── ...
├── output/
│   ├── oracle_dictionary.json        # Oracle schema
│   ├── extension-scan-report.json    # Extension scan
│   ├── ognl-scan-report.json         # OGNL scan
│   ├── conversion-report.json        # Conversion report
│   ├── validation-report.json        # Validation report
│   └── validation-performance.json   # Performance comparison
└── /home/ec2-user/workspace/target/your-project-name/
    └── .../mapper/                   # Final merged mappers
        ├── CommonMapper.xml
        └── ...
```

---

## Next Steps

### 1. Production Preparation

```bash
# 1. Integrate converted mappers into application
cp -r /home/ec2-user/workspace/target/your-project-name/src/main/resources/mybatis/mapper/* \
     /path/to/your/app/src/main/resources/mybatis/mapper/

# 2. Build application
cd /path/to/your/app
mvn clean package

# 3. Run tests
mvn test
```

### 2. Fix Failed SQL Manually

```bash
# 1. Analyze failure causes
cat output/validation-report.json | jq '.failed_queries[] | {file, query_id, error}'

# 2. Edit manually
vi mappers/your-project-name/target/CommonMapper.xml

# 3. Re-validate
# In Claude Code:
/validate your-project-name
```

### 3. Handle Extensions (if needed)

```bash
# Check Extension scan results
cat output/extension-scan-report.json | jq '.'

# Create customer framework variable definition file
vi output/extensions.json

# Re-run conversion with Extensions applied
# In Claude Code:
/convert-sql your-project-name
```

### 4. Handle OGNL (if needed)

```bash
# Check OGNL scan results
cat output/ognl-scan-report.json | jq '.'

# Manually migrate Java classes
# - Check @com.example.Util@method() calls
# - Replace with equivalent PostgreSQL/MySQL functions
```

---

## Troubleshooting

### Issue 1: Oracle Connection Failed

**Symptom:**
```
ORA-12170: TNS:Connect timeout occurred
```

**Solution:**
```bash
# 1. Check network connectivity
ping $ORACLE_HOST

# 2. Check firewall/Security Group
telnet $ORACLE_HOST 1521

# 3. Check Oracle Instant Client
echo $ORACLE_HOME
ls -l $ORACLE_HOME
```

---

### Issue 2: DMS Task Creation Failed

**Symptom:**
```
Failed to create DMS task: ReplicationInstance not found
```

**Solution:**
```bash
# 1. Verify DMS infrastructure
aws dms describe-replication-instances
aws dms describe-endpoints

# 2. Set environment variables
export DMS_REPLICATION_INSTANCE_ARN="arn:aws:dms:..."
export DMS_SOURCE_ENDPOINT_ARN="arn:aws:dms:..."
export DMS_TARGET_ENDPOINT_ARN="arn:aws:dms:..."

# 3. Re-run
python3.11 run_migration.py
```

---

### Issue 3: Table not found in dictionary

**Symptom:**
```
[WARNING] Table TB_NEW_TABLE not found in dictionary
```

**Solution:**
```bash
# In Claude Code:
/build-oracle-dict

# If specific table needs to be added, rebuild dictionary
```

---

### Issue 4: SQL Validation Failed

**Symptom:**
```
[FAIL] selectUser - Row count mismatch (Oracle: 150, Postgres: 0)
```

**Solution:**
```bash
# 1. Check TC file
cat mappers/your-project-name/target/CommonMapper_selectUser.tc.json | jq '.'

# 2. Check bind variables
cat mappers/your-project-name/target/CommonMapper_selectUser.tc.json | jq '.test_cases[0].parameters'

# 3. Test SQL manually
psql -h $PGHOST -U $PGUSER -d $PGDATABASE
=> SELECT * FROM tb_user WHERE user_id = '12345';

# 4. Edit mapper manually
vi mappers/your-project-name/target/CommonMapper.xml

# 5. Re-validate (in Claude Code)
/validate your-project-name
```

---

### Issue 5: LLM Call Failed

**Symptom:**
```
ValidationException: Model not found
```

**Solution:**
```bash
# 1. Check Bedrock model access
aws bedrock list-foundation-models --region ap-northeast-2 | grep opus-4-7

# 2. Request model access (AWS Console)
# Bedrock > Model access > Request access to Claude Opus 4.7

# 3. Check environment variables
echo $BEDROCK_MODEL_ID
echo $BEDROCK_REGION

# 4. Re-run (in Claude Code)
/convert-sql your-project-name
```

---

## Useful Commands

### Schema Migration

```bash
# Data migration only (Phase 2 only)
python3.11 run_data_migration_only.py

# Extract sequence usage
cd schema/tools
python3.11 extract_sequence_usage.py --schema YOUR_SCHEMA
```

### App Migration

```bash
# Check conversion statistics
cat output/conversion-report.json | jq '.conversion_details'

# Check LLM call counts
cat output/conversion-report.json | jq '.conversion_performance.llm_calls'

# Check slowest files
cat output/conversion-report.json | jq '.file_details | sort_by(.conversion_time) | reverse | .[0:10]'

# Check performance comparison (Oracle vs Postgres)
cat output/validation-performance.json | jq '.performance_summary'
```

### Environment Management

```bash
# Load environment variables
source tools/load_oma_env.sh

# Check environment variables
env | grep ORACLE
env | grep PG
env | grep BEDROCK

# Check logs
tail -f logs/conversion.log
tail -f logs/validation.log
```

---

## References

- **Full Documentation**: [README.md](README.md)
- **Schema Guide**: [schema/README.md](schema/README.md)
- **App Guide**: [app/README.md](app/README.md)
- **Environment Setup**: [env/README.md](env/README.md)

---

## Support

If issues persist:

1. Check log files (`logs/`)
2. Analyze report files (`output/`, `results/`)
3. Verify environment settings (`env/oma.properties`)
4. Check AWS service status (DMS, RDS, Bedrock)

---

**Created**: 2026-06-23  
**OMA Version**: 2.0  
**Expected Completion Time**: 30-90 minutes (depends on data size)
