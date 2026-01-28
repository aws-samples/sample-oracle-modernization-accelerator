# Oracle to PostgreSQL Conversion Agent

Automated schema conversion using AWS DMS Schema Conversion, Bedrock Claude 3.5, and MCP servers.

## Overview

Converts Oracle database objects to PostgreSQL by:
1. Analyzing DMS Schema Conversion project from S3
2. Extracting Oracle DDL for complex/medium objects
3. Converting to PostgreSQL using Bedrock Claude 3.5 Sonnet
4. Saving converted DDL files and generating report

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Oracle to PostgreSQL Agent (ora_to_pg_sc_agent.py)    │
│  • Single SSE session for all operations                │
│  • Async workflow: Analyze → Extract → Convert → Save   │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ oma-sc-mcp   │  │ pg-client    │  │ oracle-client│
│ Port 9080    │  │ Port 9081    │  │ Port 9082    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                  ┌───────┴────────┐
                  ▼                ▼
          ┌──────────────┐  ┌──────────────┐
          │ AWS S3       │  │ Bedrock      │
          │ Secrets Mgr  │  │ Claude 3.5   │
          └──────────────┘  └──────────────┘
```

## Workflow

### Step 1: Analyze Project
**Tool**: `analyze_dms_sc_project`
- Input: S3 path to DMS SC project zip
- Downloads and extracts project locally
- Parses CSV files for action items
- Filters: Only objects with complexity = Complex or Medium
- Output: List of objects to convert

### Step 2: Get DDL
**Tool**: `get_offline_ddl`
- Input: S3 path, schema name, object name
- Extracts Oracle DDL from DMS SC project
- Source: Offline DDL (no live Oracle connection needed)
- Output: Oracle DDL text

### Step 3: Convert to PostgreSQL
**Tool**: `convert_ddl_to_pg`
- Input: Oracle DDL, object type, complexity
- Calls Bedrock Claude 3.5 Sonnet via AWS SDK
- Model: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- Prompt includes conversion rules and best practices
- Output: PostgreSQL-compatible DDL

### Step 4: Save Files
- Saves each converted DDL to `/workshop/pg-ddl/`
- Filename format: `Schemas_SCHEMA_Type_OBJECT_NAME.sql`
- Includes header comment with object metadata
- Generates `CONVERSION_REPORT.md` with statistics

## Configuration

### Environment Variables
```bash
DMS_SC_SCHEMA_NAME="DEMO"  # Schema to convert
```

### MCP Endpoints
```python
MCP_OMA_SC = "http://localhost:9080/sse"      # DMS SC + Bedrock tools
MCP_POSTGRES = "http://localhost:9081/sse"    # PostgreSQL client (unused)
MCP_ORACLE = "http://localhost:9082/sse"      # Oracle client (unused)
```

### Output Directory
```python
OUTPUT_DIR = "/workshop/pg-ddl"
```

### Bedrock Model
- Model ID: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- Region: `us-east-1`
- Max tokens: 4096
- Called via MCP server (not directly from agent)

## MCP Tools Used

### oma-sc-mcp (3 tools)

1. **analyze_dms_sc_project**
   - Analyzes DMS SC project from S3
   - Downloads and caches locally
   - Returns action items with complexity
   - Parameters: `s3_path`

2. **get_offline_ddl**
   - Extracts Oracle DDL from project
   - No live database connection needed
   - Parameters: `s3_path`, `ddlType`, `schemaName`, `objectType`, `objectName`

3. **convert_ddl_to_pg**
   - Converts Oracle DDL to PostgreSQL
   - Uses Bedrock Claude 3.5 Sonnet
   - Parameters: `oracleDdl`, `objectType`, `complexity`

## Conversion Rules

### Data Types
| Oracle | PostgreSQL |
|--------|------------|
| VARCHAR2 | VARCHAR |
| NUMBER | NUMERIC |
| DATE | TIMESTAMP |
| CLOB | TEXT |
| BLOB | BYTEA |

### Built-in Functions
| Oracle | PostgreSQL |
|--------|------------|
| SYSDATE | CURRENT_TIMESTAMP |
| NVL(a,b) | COALESCE(a,b) |
| DECODE(x,a,b,c) | CASE WHEN x=a THEN b ELSE c END |

### PL/SQL → PL/pgSQL
- `IS/AS` → `AS $$`
- `END function_name;` → `END; $$;`
- Package procedures → Standalone functions
- Package functions → Standalone functions
- `RETURN` statements adapted for PL/pgSQL

## Usage

### Prerequisites
```bash
# 1. Validate and setup environment
cd /workshop/oma-mcp
./validate-setup.sh

# 2. Build MCP servers
./build-all.sh

# 3. Start MCP servers
./start-servers.sh

# 4. Verify servers running
ps aux | grep "\.jar" | grep java
```

### Run Conversion
```bash
cd /workshop/oma-sc-agent

python3.11 ora_to_pg_sc_agent.py s3://BUCKET/dms-sc-migration-project/PROJECT.zip
```

### Output
```
============================================================
Oracle to PostgreSQL Schema Conversion Agent
============================================================

🔗 Opening MCP session...
✅ Session ready

🔍 Step 1: Analyzing project...
   Found 3 CSV files
   Found 17 complex/medium objects

📋 Processing 17 objects...

============================================================
Object 1/17: Schemas.DEMO.Packages.BOOK_PKG.Public procedures.GET_BOOK_DETAILS
============================================================
📝 Getting DDL...
   ✓ Got DDL (424 chars)
🔄 Converting to PostgreSQL...
   ✓ Converted (412 chars)
   💾 Saved to /workshop/pg-ddl/Schemas_DEMO_Packages_BOOK_PKG_Public_procedures_GET_BOOK_DETAILS.sql

...

============================================================
CONVERSION SUMMARY
============================================================
✅ Success: 15
❌ Failed: 0
⊘ Skipped: 2

📁 All DDL files saved to: /workshop/pg-ddl

📄 Report saved to: /workshop/pg-ddl/CONVERSION_REPORT.md
```

## Output Files

### Converted DDL Files
Location: `/workshop/pg-ddl/`

Format:
```sql
-- Schemas.DEMO.Packages.BOOK_PKG.Public functions.IS_IN_STOCK
-- Type: Package function | Complexity: Complex

CREATE OR REPLACE FUNCTION is_in_stock(p_book_id NUMERIC)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN CASE WHEN get_available_quantity(p_book_id) > 0 THEN 1 ELSE 0 END;
END;
$$;
```

### Conversion Report
Location: `/workshop/pg-ddl/CONVERSION_REPORT.md`

Contains:
- Executive summary with statistics
- Conversion success/failure rates
- Object-by-object details in tables
- Technology stack information
- Next steps guide

## Error Handling

### DDL Not Found
- Object skipped
- Logged as "⊘ DDL not found, skipping"
- Counted in skipped statistics

### Conversion Failed
- Error message displayed
- Object marked as failed
- Error details saved in report

### No Retry Logic
- Single attempt per object
- Failures logged but not retried
- Focus on batch processing speed

## Limitations

1. **DDL Availability**: Requires offline DDL in DMS SC project
2. **No Deployment**: Only generates DDL files, doesn't deploy
3. **No Testing**: Doesn't test converted objects
4. **Single Session**: Uses one MCP session for all operations
5. **No Dependency Resolution**: Converts in CSV order

## Best Practices

1. **Review Converted DDL**: Always review before deployment
2. **Test Thoroughly**: Test each function/procedure after deployment
3. **Handle Dependencies**: Deploy objects in dependency order
4. **Backup First**: Keep original Oracle DDL
5. **Incremental Deployment**: Deploy and test in batches

## Troubleshooting

### MCP Servers Not Running
```bash
cd /workshop/oma-mcp
./start-servers.sh

# Check status
ps aux | grep "\.jar" | grep java
```

### Bedrock Access Denied
```bash
# Add IAM permission
aws iam put-role-policy --role-name YOUR-ROLE --policy-name BedrockInvokeModel --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel"],
    "Resource": "arn:aws:bedrock:*:*:inference-profile/*"
  }]
}'
```

### Python Dependencies Missing
```bash
# Install Python 3.11
sudo yum install -y python3.11 python3.11-pip

# Install MCP SDK
python3.11 -m pip install git+https://github.com/modelcontextprotocol/python-sdk.git --user

# Install other dependencies
python3.11 -m pip install -r requirements.txt --user
```

### S3 Access Denied
```bash
# Check AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://YOUR-BUCKET/dms-sc-migration-project/
```

## Performance

- **Typical object**: 2-5 seconds (extract + convert + save)
- **Complex function**: 5-10 seconds
- **Batch of 15 objects**: 1-2 minutes
- **Bottleneck**: Bedrock API calls

## Security

- **No Authentication**: MCP servers run on localhost only
- **Database Credentials**: Via AWS Secrets Manager
- **S3 Access**: Via IAM role
- **Bedrock Access**: Via IAM role
- **Output Files**: Saved to local filesystem

## Key Differences from Previous Design

1. **No OAuth2**: Removed Cognito authentication
2. **No Deployment**: Only generates DDL files
3. **No Testing**: Doesn't test converted objects
4. **Single Session**: Uses one SSE session for all operations
5. **Simplified**: Focus on conversion, not deployment
6. **Report Generation**: Automatic markdown report

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Conversion Agent                       │
│  (oracle_to_postgresql_agent.py)                       │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  oma-sc-mcp  │  │ pg-client-mcp│  │   Bedrock    │
│   (9080)     │  │   (9081)     │  │   Claude     │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│  DMS SC      │  │  PostgreSQL  │
│  Project     │  │  Database    │
└──────────────┘  └──────────────┘
```

## Workflow

### Step 1: Analyze Project
**Tool**: `oma-sc-mcp.analyze_dms_sc_project`
- Input: S3 path to DMS SC project zip
- Output: List of Complex/Medium objects
- Filters: Only objects with complexity = Complex or Medium
- Sorts: Storage objects (Table, Index) → Code objects (Function, Procedure)

### Step 2: Get DDL
**Tool**: `oma-sc-mcp.get_offline_ddl`
- Input: Schema name, Object name
- Output: Oracle DDL
- Source: Offline DDL from DMS SC project

### Step 3: Convert to PostgreSQL
**Service**: Bedrock Claude 3.5 Sonnet
- Input: Oracle DDL + object metadata
- Output: PostgreSQL-compatible DDL
- Rules:
  - Follow Aurora PostgreSQL best practices
  - Convert PL/SQL → PL/pgSQL
  - Map Oracle types → PostgreSQL types
  - Preserve business logic exactly
  - Handle Oracle built-ins (SYSDATE, NVL, DECODE)

### Step 4: Deploy
**Tool**: `pg-client-mcp.executeSql`
- Backup existing object (if exists)
- Drop existing object (CASCADE)
- Create new object
- Save DDL to `/tmp/oma-conversion/`

### Step 5: Test
**Tool**: `pg-client-mcp.executeTestCaseRollback`
- Only for functions/procedures
- Execute with NULL parameters
- Rollback after test
- Verify no syntax errors

### Retry Logic
- Max 3 attempts per object
- On failure: Re-convert with error context
- Track: Success, Failed, Skipped

## Configuration

### S3 Project Location
```python
S3_BUCKET = "mma-dms-sc-775881734961"
S3_PREFIX = "dms-sc-migration-project/"
```

### OAuth2 (Cognito)
```python
COGNITO_DOMAIN = "https://agentcore-8e9e317c.auth.us-east-1.amazoncognito.com"
CLIENT_ID = "5p5b2k57kq43tmodn9otpm451s"
CLIENT_SECRET = "uo5ge7vlk2350kehra92196lrh20p1aiutki9flsfrltccji4lb"
SCOPE = "oma-mcp/mcp.access"
```

### MCP Endpoints
```python
MCP_OMA_SC = "http://localhost:9080/mcp"      # DMS SC tools
MCP_POSTGRES = "http://localhost:9081/mcp"    # PostgreSQL tools
```

### Bedrock Model
```python
BEDROCK_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

## MCP Tools Used

### oma-sc-mcp (2 tools)
1. **analyze_dms_sc_project**
   - Analyzes DMS SC project from S3
   - Returns action items with complexity
   - Replaces: S3 download + ZIP extraction + CSV parsing

2. **get_offline_ddl**
   - Extracts Oracle DDL from project
   - Faster than live Oracle connection
   - Replaces: Oracle DBMS_METADATA.GET_DDL

### pg-client-mcp (2 tools)
1. **executeSql**
   - Executes SQL on PostgreSQL
   - Used for: Backup, Drop, Create, Query

2. **executeTestCaseRollback**
   - Tests function/procedure
   - Auto-rollback after execution
   - Verifies syntax correctness

## Conversion Rules

### Data Types
| Oracle | PostgreSQL |
|--------|------------|
| VARCHAR2 | VARCHAR |
| NUMBER | NUMERIC |
| DATE | TIMESTAMP |
| CLOB | TEXT |
| BLOB | BYTEA |

### Built-in Functions
| Oracle | PostgreSQL |
|--------|------------|
| SYSDATE | CURRENT_TIMESTAMP |
| NVL(a,b) | COALESCE(a,b) |
| DECODE(x,a,b,c) | CASE WHEN x=a THEN b ELSE c END |
| TO_CHAR(d,'YYYY-MM-DD') | TO_CHAR(d,'YYYY-MM-DD') |
| SUBSTR(s,1,10) | SUBSTRING(s,1,10) |

### PL/SQL → PL/pgSQL
- `BEGIN...END` → `BEGIN...END`
- `EXCEPTION WHEN...THEN` → `EXCEPTION WHEN...THEN`
- `RAISE_APPLICATION_ERROR` → `RAISE EXCEPTION`
- `%TYPE` → `%TYPE` (supported)
- `%ROWTYPE` → `%ROWTYPE` (supported)
- Package procedures → Standalone functions

### Object Types
- **Table**: Constraints, indexes, triggers
- **Index**: B-tree, unique, partial
- **View**: Simple and materialized
- **Function**: Return value required
- **Procedure**: Convert to function returning VOID
- **Package**: Split into individual functions

## Usage

### Prerequisites
```bash
# 1. Start MCP servers
cd /workshop/oma-mcp
source env.sh
./build-all.sh

cd oma-sc-mcp && java -jar target/oma-sc-mcp-server-1.0.0.jar &
cd ../pg-client-mcp && java -jar target/postgresql-mcp-server-1.0.0.jar &

# 2. Configure AWS
aws configure

# 3. Install dependencies
pip install boto3 requests
```

### Run Conversion
```bash
python3 oracle_to_postgresql_agent.py s3://mma-dms-sc-775881734961/dms-sc-migration-project/ORACLE_AURORA_POSTGRESQL_2026-01-21T05-30-08.123Z.zip
```

### Output
```
============================================================
Oracle to PostgreSQL Schema Conversion Agent
============================================================

🔍 Step 1: Analyzing DMS SC project via MCP...
   S3 Path: s3://...
   Found 15 complex/medium objects

📋 Processing 15 objects...

============================================================
Object 1/15: Schemas.DEMO.Packages.ORDER_PKG.UPDATE_ORDER_STATUS
Category: Package procedure | Complexity: Medium
============================================================
📝 Step 2: Getting DDL for UPDATE_ORDER_STATUS...
   ✓ Found DDL
🔄 Step 3: Converting to PostgreSQL...
   ✓ Converted to PostgreSQL
   Saved to /tmp/oma-conversion/Schemas_DEMO_Packages_ORDER_PKG_UPDATE_ORDER_STATUS.sql
🚀 Step 4: Deploying to PostgreSQL...
   ✓ Backed up to /tmp/oma-conversion/UPDATE_ORDER_STATUS_backup.sql
   ✓ Dropped existing object
   ✅ Deployed successfully
🧪 Step 5: Testing object...
   Function signature: update_order_status(order_id integer, status varchar)
   ✅ Test passed

============================================================
CONVERSION SUMMARY
============================================================
✅ Success: 12
❌ Failed: 2
⊘ Skipped: 1

Failed objects:
  - Schemas.DEMO.Functions.COMPLEX_CALC (Function)
  - Schemas.DEMO.Procedures.DATA_MIGRATION (Procedure)

📁 All DDL files saved to: /tmp/oma-conversion
```

## Output Files

### Converted DDL
Location: `/tmp/oma-conversion/`

Format:
```sql
-- Schemas.DEMO.Packages.ORDER_PKG.UPDATE_ORDER_STATUS
-- Category: Package procedure
-- Complexity: Medium

CREATE OR REPLACE FUNCTION demo.update_order_status(
    p_order_id INTEGER,
    p_status VARCHAR
) RETURNS VOID AS $$
BEGIN
    UPDATE orders 
    SET status = p_status,
        updated_at = CURRENT_TIMESTAMP
    WHERE order_id = p_order_id;
END;
$$ LANGUAGE plpgsql;
```

### Backup Files
Location: `/tmp/oma-conversion/*_backup.sql`

Contains existing PostgreSQL object DDL before replacement.

## Error Handling

### DDL Not Found
- Object skipped
- Logged in summary

### Conversion Failed
- Retry with error context (max 3 attempts)
- Save last attempt to file
- Mark as failed in summary

### Deployment Failed
- Retry conversion (max 3 attempts)
- Keep backup file
- Mark as failed in summary

### Test Failed
- Retry conversion (max 3 attempts)
- Object deployed but marked as failed
- Manual verification required

## Limitations

1. **DDL Availability**: Requires offline DDL in DMS SC project
2. **Complex Logic**: Very complex PL/SQL may need manual review
3. **Oracle-specific Features**: Some features have no PostgreSQL equivalent
4. **Testing**: Only basic NULL parameter testing
5. **Dependencies**: Objects must be converted in dependency order

## Best Practices

1. **Review Converted DDL**: Always review before production deployment
2. **Test Thoroughly**: Run comprehensive tests after conversion
3. **Backup First**: Keep Oracle DDL and PostgreSQL backups
4. **Incremental Conversion**: Convert in batches, not all at once
5. **Monitor Logs**: Check for warnings and errors
6. **Validate Business Logic**: Ensure logic is preserved exactly

## Troubleshooting

### MCP Connection Failed
```bash
# Check servers running
ps aux | grep java

# Check OAuth token
curl -X POST https://agentcore-8e9e317c.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=xxx&client_secret=xxx&scope=oma-mcp/mcp.access"
```

### Bedrock Access Denied
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1 | grep claude-3-5-sonnet

# Check IAM permissions
aws sts get-caller-identity
```

### PostgreSQL Connection Failed
```bash
# Check database connectivity
psql -h hostname -U username -d database

# Check MCP server logs
tail -f /tmp/pg-client-mcp.log
```

## Performance

- **Typical object**: 5-10 seconds (analyze + convert + deploy + test)
- **Complex function**: 15-30 seconds (multiple retry attempts)
- **Batch of 50 objects**: 10-15 minutes
- **Bottleneck**: Bedrock API calls (rate limited)

## Security

- OAuth2 tokens auto-refreshed
- Database credentials via MCP (not exposed)
- Backup files contain sensitive data (secure `/tmp/`)
- S3 access via IAM role (no hardcoded credentials)
