# MyBatis XML Test Program

A Java program that analyzes and executes SQL from MyBatis XML files.

## Core Scripts

### 1. bulk_prepare.sh
Bulk extracts parameters from XML files and automatically collects sample values from the database.

```bash
./bulk_prepare.sh <directory_path>
```

**Features:**
- Automatically extract `#{}`, `${}` parameters from all XML files
- Collect sample values from actual DB columns matching parameter names
- Automatically generate `parameters.properties` file

**Example:**
```bash
# Basic parameter extraction only
./bulk_prepare.sh /path/to/mapper

# With Oracle DB sample value collection (automatic when ORACLE_SVC_USER is set)
./bulk_prepare.sh /path/to/mapper
```

### 2. run_bind_generator.sh
Oracle dictionary-based bind variable generator that matches parameters with actual database columns.

```bash
./run_bind_generator.sh [mapper_directory]
```

**Features:**
- Extract bind variables from mapper files
- Match with Oracle dictionary information
- Generate `parameters.properties` with actual sample values
- Create detailed matching reports

### 3. run_oracle.sh
Execute MyBatis SQL against Oracle database.

```bash
./run_oracle.sh <directory_path> [options]
```

**Features:**
- Automatically recognize Oracle environment variables (`ORACLE_SVC_USER`, `ORACLE_SVC_PASSWORD`, `ORACLE_SVC_CONNECT_STRING`)
- Dynamic SQL processing through MyBatis engine
- Generate execution results and statistical reports
- SQL result comparison with PostgreSQL/MySQL

### 4. run_postgresql.sh
Execute MyBatis SQL against PostgreSQL database.

```bash
./run_postgresql.sh <directory_path> [options]
```

**Features:**
- Automatically recognize PostgreSQL environment variables (`PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE`)
- Use PostgreSQL-specific JDBC driver
- Generate execution results and statistical reports
- SQL result comparison with Oracle

### 5. run_mysql.sh
Execute MyBatis SQL against MySQL database.

```bash
./run_mysql.sh <directory_path> [options]
```

**Features:**
- Automatically recognize MySQL environment variables (`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_TCP_PORT`, `MYSQL_DATABASE`)
- Use MySQL-specific JDBC driver
- Generate execution results and statistical reports

### 6. analyze_results.sh
Analyze test results and provide SQL conversion suggestions.

```bash
./analyze_results.sh
```

**Features:**
- Analyze test result files
- Generate analysis reports
- Automatic SQL conversion suggestions through Amazon Q
- Fix sorting differences automatically

## Common Options

All execution scripts support the following options:

- `--select-only`: Execute SELECT statements only (default, safe)
- `--all`: Execute all SQL statements (including INSERT/UPDATE/DELETE)
- `--summary`: Output summary information only
- `--verbose`: Output detailed information
- `--json`: Generate JSON result file (`out/bulk_test_result_YYYYMMDD_HHMMSS.json`)
- `--compare`: Enable SQL result comparison between databases

## Usage Workflow

### Step 1: Parameter Preparation
```bash
# Extract parameters with DB sample values
./bulk_prepare.sh /path/to/mapper

# Or use bind variable generator for more accurate matching
./run_bind_generator.sh /path/to/mapper
```

### Step 2: Edit Parameter File (Optional)
Modify values in the generated `parameters.properties` file if needed.

### Step 3: SQL Execution
```bash
# Safely execute SELECT only on Oracle
./run_oracle.sh /path/to/mapper --select-only --summary

# Execute all SQL on PostgreSQL (caution!)
./run_postgresql.sh /path/to/mapper --all --verbose

# Execute on MySQL and save JSON results
./run_mysql.sh /path/to/mapper --json

# Compare results between Oracle and PostgreSQL
./run_oracle.sh /path/to/mapper --compare --verbose
```

### Step 4: Result Analysis
```bash
# Analyze test results and get conversion suggestions
./analyze_results.sh
```

## Environment Variable Setup

### Oracle
```bash
export ORACLE_SVC_USER="username"
export ORACLE_SVC_PASSWORD="password"
export ORACLE_SVC_CONNECT_STRING="host:port:sid"
# For bind variable generator
export ORACLE_HOST="hostname"
export ORACLE_SID="sid"
```

### PostgreSQL
```bash
export PGUSER="username"
export PGPASSWORD="password"
export PGHOST="localhost"
export PGPORT="5432"
export PGDATABASE="dbname"
```

### MySQL
```bash
export MYSQL_USER="username"
export MYSQL_PASSWORD="password"
export MYSQL_HOST="localhost"
export MYSQL_TCP_PORT="3306"
export MYSQL_DATABASE="dbname"
```

## Key Features

1. **Utilize Actual DB Sample Values**: Automatic sample value collection through parameter-column name matching
2. **MyBatis Engine Usage**: Automatic dynamic condition processing, guaranteed accurate operation
3. **Multi-DB Support**: Full support for Oracle, PostgreSQL, MySQL
4. **Safe Execution**: Execute SELECT only by default, data modification requires explicit options
5. **Detailed Reports**: Success/failure statistics, error information, JSON tracking functionality
6. **Cross-DB Comparison**: Compare SQL execution results between different databases
7. **AI-Powered Analysis**: Automatic SQL conversion suggestions through Amazon Q integration

## Output Example

```
=== MyBatis Bulk Test Started ===
Search Directory: /path/to/mapper
XML Files Found: 25
Total SQL IDs: 147

=== Test Execution Results ===
✓ UserMapper.xml - selectUser: Success (3 records)
✓ UserMapper.xml - selectUserList: Success (15 records)
✗ OrderMapper.xml - selectOrder: Failed (Missing parameter: orderId)

=== Final Statistics ===
Total Executed: 147
Success: 142 (96.6%)
Failed: 5 (3.4%)
Execution Time: 2 minutes 34 seconds
```

## File Structure

```
bin/test/
├── bulk_prepare.sh              # Parameter extraction with DB samples
├── run_bind_generator.sh        # Oracle dictionary-based parameter generation
├── run_oracle.sh               # Oracle test execution
├── run_postgresql.sh           # PostgreSQL test execution  
├── run_mysql.sh                # MySQL test execution
├── analyze_results.sh          # Result analysis and AI suggestions
├── mybatis-bulk-executor.properties  # Configuration file
├── parameters.properties       # Generated parameter file
├── lib/                        # JDBC drivers and dependencies
├── com/test/mybatis/          # Java source files
└── out/                       # Output files and reports
```
