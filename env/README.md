# OMA Environment Configuration

Unified environment configuration for the OMA project.

> 한국어 버전: [README_KR.md](README_KR.md)

## Overview

The `env` folder provides centralized environment configuration for all OMA components (Schema Conversion, App Conversion, CloudFormation Deployment).

### Key Files

| File | Purpose |
|------|---------|
| `oma.properties` | **Unified configuration file** (single source of truth) |
| `setEnv.sh` | Environment variable loader for CloudFormation deployment |
| `deploy-omabox.sh` | CloudFormation stack deployment script |
| `*.yaml` | CloudFormation template files |

---

## oma.properties

The **single configuration file** for the entire OMA project.

### Structure

```properties
[COMMON]
# Variables shared by all tools (env/schema/app)

[your application name]
# CloudFormation deployment specific variables
```

### [COMMON] Section

Common variables used by Schema Conversion, App Conversion, and env tools.

#### 1. Base Configuration

```properties
OMA_BASE_DIR=/home/ec2-user/workspace/oma
LANGUAGE=en
AWS_REGION=ap-northeast-2
```

#### 2. Bedrock LLM Configuration

```properties
BEDROCK_REGION=ap-northeast-2
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7
```

> **Supported models**: opus-4-8, opus-4-7, opus-4-6, sonnet-4-6, haiku-4-5

#### 3. App Conversion Settings

```properties
MAX_WORKERS=7
ORACLE_HOME=/home/ec2-user/oracle
SOURCE_WORKSPACE=/home/ec2-user/workspace/source
TARGET_WORKSPACE=/home/ec2-user/workspace/target
ORACLE_DICT_PATH=${OMA_BASE_DIR}/app/output/oracle_dictionary.json
MAPPER_WORK_DIR=${OMA_BASE_DIR}/app/mappers
```

#### 4. Oracle Connection

```properties
ORACLE_HOST=10.0.X.X
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_CONN_TYPE=service
ORACLE_USER=username
ORACLE_PASSWORD=password
ORACLE_SCHEMA=SCHEMA_NAME
```

#### 5. PostgreSQL Connection (Standard Variables)

```properties
# PostgreSQL standard environment variables (auto-recognized by psql)
PGHOST=your-cluster.cluster-xxxxx.region.rds.amazonaws.com
PGPORT=5432
PGDATABASE=dbname
PGSCHEMA=schema_name
PGUSER=username
PGPASSWORD=password
```

> **Important**: PostgreSQL uses **standard variable names** (`PGHOST`, `PGPORT`, etc.) without underscores.

#### 6. MySQL Connection

```properties
MYSQL_HOST=your-cluster.cluster-xxxxx.region.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_DATABASE=dbname
MYSQL_USER=username
MYSQL_PASSWORD=password
```

#### 7. Target DB Type

```properties
# postgres or mysql
TARGET_DB_TYPE=postgres
```

#### 8. DMS Schema Conversion (Optional)

```properties
DMS_SC_S3_BUCKET=oma-dms-sc-YOUR_ACCOUNT_ID
DMS_MIGRATION_PROJECT_ARN=arn:aws:dms:region:account:migration-project:project-id
```

### [APPLICATION_NAME] Section

CloudFormation deployment specific variables.

```properties
[your application name]
APPLICATION_NAME=${your application name}
```

---

## Environment Variable Standards

OMA follows standard environment variable naming conventions for each database.

### PostgreSQL Standard

| Variable | Description | Auto-recognized by psql |
|----------|-------------|-------------------------|
| `PGHOST` | Host | ✅ |
| `PGPORT` | Port | ✅ |
| `PGDATABASE` | Database name | ✅ |
| `PGUSER` | Username | ✅ |
| `PGPASSWORD` | Password | ✅ |
| `PGSCHEMA` | Schema name | ❌ |

**Benefit**: `psql` command automatically recognizes connection info.

```bash
# After loading oma.properties
psql -c "SELECT version();"  # No need for -h, -p, -U options!
```

### MySQL Standard

| Variable | Description |
|----------|-------------|
| `MYSQL_HOST` | Host |
| `MYSQL_PORT` | Port |
| `MYSQL_DATABASE` | Database name |
| `MYSQL_USER` | Username |
| `MYSQL_PASSWORD` | Password |

### Oracle Standard

| Variable | Description |
|----------|-------------|
| `ORACLE_HOST` | Host |
| `ORACLE_PORT` | Port |
| `ORACLE_SID` | SID or Service Name |
| `ORACLE_USER` | Username |
| `ORACLE_PASSWORD` | Password |
| `ORACLE_SCHEMA` | Schema name |
| `ORACLE_HOME` | Oracle Client installation path |

---

## Usage

### Schema Conversion

The schema conversion program automatically reads `oma.properties`.

```bash
cd /home/ec2-user/workspace/oma/schema/postgresql/scripts
python3.11 run_migration.py

# Internally:
# 1. Load oma.properties [COMMON] section
# 2. Secrets Manager fallback (optional)
# 3. Export as environment variables
```

### App Conversion

App conversion skills automatically read `oma.properties`.

```bash
cd /home/ec2-user/workspace/oma/app
bash .claude/skills/convert-sql.sh <mapper-file>

# Internally:
# 1. Call tools/load_oma_env.sh
# 2. Parse oma.properties [COMMON] section
# 3. Export as environment variables
```

**All skills work the same way:**
- `build-oracle-dict.sh`
- `convert-sql.sh`
- `merge-mappers.sh`
- `scan-extension.sh`
- `split-mappers.sh`
- `run-validator.sh`
- `verify-env.sh`

### CloudFormation Deployment

```bash
cd /home/ec2-user/workspace/oma/env

# 1. Create credentials in Secrets Manager
bash deploy-omabox.sh -o 1

# 2. Deploy CloudFormation stack
bash deploy-omabox.sh -o 2

# setEnv.sh automatically:
# 1. Read oma.properties
# 2. Include [APPLICATION_NAME] section
# 3. Generate environment variable file
```

---

## Environment Variable Priority

### Schema Conversion

```
1. oma.properties [COMMON] (highest priority)
2. Secrets Manager (fallback)
3. Default values
```

### App Conversion

```
1. oma.properties [COMMON] (single source)
2. Default values
```

### CloudFormation Deployment

```
1. oma.properties [COMMON] + [APPLICATION_NAME]
2. Default values
```

---

## Modifying Configuration

### Changing Database Connection Info

```bash
vi oma.properties

# Modify Oracle info
ORACLE_HOST=10.0.X.X
ORACLE_USER=new_user
ORACLE_PASSWORD=new_password

# Modify PostgreSQL info
PGHOST=new-cluster.cluster-xxxxx.region.rds.amazonaws.com
PGUSER=new_user
PGPASSWORD=new_password
```

**No restart required**: Changes are automatically applied on next execution.

### Changing Bedrock Model

```bash
vi oma.properties

# Opus 4.7 → Opus 4.8
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-8
```

---

## Validation

### Test Environment Variable Loading

```bash
# Test App skills
cd /home/ec2-user/workspace/oma/app
bash .claude/skills/verify-env.sh

# Output:
# ✓ ORACLE_HOST=10.0.X.X
# ✓ PGHOST=your-cluster...
# ✓ BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7
```

### Test Database Connection

```bash
# PostgreSQL (standard variables auto-recognized)
source <(grep -v '^\[' oma.properties | grep -v '^#' | grep '=')
psql -c "SELECT version();"

# Oracle
sqlplus ${ORACLE_USER}/${ORACLE_PASSWORD}@//${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}
```

---

## Variable Expansion

`oma.properties` supports variable expansion.

```properties
OMA_BASE_DIR=/home/ec2-user/workspace/oma
ORACLE_DICT_PATH=${OMA_BASE_DIR}/app/output/oracle_dictionary.json
MAPPER_WORK_DIR=${OMA_BASE_DIR}/app/mappers
```

**Expansion timing**: Variables are automatically expanded when each tool reads the file.

---

## Security

### Managing Sensitive Information

**Option 1: Store directly in oma.properties (Development)**
- Simple but be careful not to commit to Git

**Option 2: Use Secrets Manager (Recommended for Production)**

```bash
# Oracle credentials
aws secretsmanager create-secret \
  --name oma-secret-oracle-service \
  --secret-string '{
    "host": "10.0.X.X",
    "port": 1521,
    "username": "user",
    "password": "pass",
    "sid": "ORCLPDB1"
  }'

# PostgreSQL credentials
aws secretsmanager create-secret \
  --name oma-secret-postgres-service \
  --secret-string '{
    "host": "cluster.xxxxx.region.rds.amazonaws.com",
    "port": 5432,
    "username": "user",
    "password": "pass",
    "database": "dbname"
  }'
```

**Automatic Fallback**: 
- Variables not found in oma.properties are automatically loaded from Secrets Manager.

---

## Troubleshooting

### Environment Variables Not Loading

**Symptom**: "Missing credentials" error when running programs

**Solution**:
```bash
# 1. Check oma.properties path
ls -la /home/ec2-user/workspace/oma/env/oma.properties

# 2. Check file format (section headers, key=value)
cat oma.properties

# 3. Check permissions
chmod 644 oma.properties
```

### PostgreSQL Connection Failed

**Symptom**: `psql: connection refused`

**Solution**:
```bash
# 1. Check environment variables
echo $PGHOST
echo $PGPORT

# 2. Check network connectivity
telnet $PGHOST $PGPORT

# 3. Check Security Group (port 5432 open?)
```

### Oracle Connection Failed

**Symptom**: `ORA-12170: TNS:Connect timeout occurred`

**Solution**:
```bash
# 1. Check VPN connection (for on-premises Oracle)
# 2. Check Security Group (port 1521 open?)
# 3. Check ORACLE_HOME
echo $ORACLE_HOME
ls $ORACLE_HOME/bin/sqlplus
```

---

## Reference

- **Single Source of Truth**: Manage only `oma.properties`
- **Standards Compliance**: Uses PostgreSQL/MySQL/Oracle standard environment variables
- **Auto Discovery**: DMS infrastructure automatically discovered during schema conversion
- **Secrets Manager Integration**: Sensitive information can use Secrets Manager

---

**Created**: 2026-06-18  
**OMA Version**: 2.0
