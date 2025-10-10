# MyBatis Oracle Modernization Testing Framework

A comprehensive Java testing framework for Oracle database modernization projects, providing automated SQL testing, parameter generation, and result comparison across Oracle, MySQL, and PostgreSQL databases.

## Overview

This framework helps modernize Oracle applications by automatically testing MyBatis XML files against multiple database platforms, generating bind variables, and analyzing execution results to ensure compatibility during database migration.

## Core Components

### 1. MyBatisBulkExecutorWithJson.java
**Main bulk SQL execution engine with JSON reporting**

- Recursively searches MyBatis XML files and executes all SQL statements
- Supports Oracle, MySQL, and PostgreSQL databases
- Generates detailed JSON reports with execution statistics
- Provides cross-database result comparison capabilities
- Automatic parameter extraction and binding

**Key Features:**
- Resource management with try-with-resources pattern
- Jackson library for safe JSON generation
- DOM parser for accurate XML processing
- External configuration file support
- Automatic example pattern skipping

### 2. MyBatisBulkPreparator.java
**Intelligent parameter extraction and database sample value collection**

- Extracts bind variables from MyBatis XML files
- Connects to Oracle database to collect sample values
- Matches parameters with actual database columns
- Generates comprehensive parameters.properties files

**Key Features:**
- Oracle dictionary integration
- Smart parameter-column matching
- Automatic sample value collection
- Fallback value generation
- Metadata-driven parameter suggestions

### 3. SimpleBindVariableGenerator.java
**Oracle dictionary-based bind variable generator**

- Reliable bind variable generation using Oracle system tables
- Advanced parameter matching algorithms
- Comprehensive mismatch reporting
- Production-ready parameter file generation

**Key Features:**
- Oracle ALL_TAB_COLUMNS integration
- Multiple matching strategies (exact, partial, camelCase)
- Automatic data type-based value generation
- Detailed mismatch location tracking

### 4. SqlPlusBindVariableGeneratorSimple.java
**AI-powered bind variable generator using Amazon Q**

- Uses Amazon Q Chat for intelligent parameter value generation
- Fast timeout-based execution for production environments
- Fallback mechanisms for reliability
- Context-aware value suggestions

**Key Features:**
- Amazon Q Chat integration
- Intelligent parameter analysis
- Configurable timeout settings
- Automatic fallback value generation

### 5. SqlListRepository.java
**Advanced SQL comparison and verification system**

- Stores and compares SQL execution results between databases
- Supports Oracle ↔ MySQL/PostgreSQL comparisons
- Normalized JSON result storage for accurate comparison
- Comprehensive statistics and reporting

**Key Features:**
- Cross-database result comparison
- Normalized JSON storage
- Automatic table creation
- Statistical analysis and reporting

### 6. TestResultAnalyzer.java
**Intelligent test result analysis and automatic fixing**

- Analyzes PostgreSQL execution failures
- Categorizes errors by type for targeted fixes
- Identifies sorting differences vs actual data differences
- Automatic ORDER BY clause insertion for sorting fixes

**Key Features:**
- Error categorization and analysis
- Sorting difference detection
- Automatic SQL fixing capabilities
- Comprehensive failure reporting

### 7. MyBatisSimpleExecutor.java
**Single SQL execution utility**

- Execute individual SQL statements from MyBatis XML files
- Parameter file integration
- Oracle TNS configuration support
- Development and testing utility

### 8. MyBatisTestPreparator.java
**SQL analysis and test preparation utility**

- Extracts SQL content from MyBatis XML files
- Analyzes dynamic conditions and parameters
- Generates parameter files for testing
- Development support tool

### 9. ResultNormalizer.java
**Database result normalization utility**

- Normalizes differences between Oracle and PostgreSQL results
- Handles numeric precision differences
- Standardizes NULL value representation
- Ensures consistent comparison results

## Environment Setup

### Required Environment Variables

#### Oracle Database
```bash
export ORACLE_SVC_USER="username"
export ORACLE_SVC_PASSWORD="password"
export ORACLE_SVC_CONNECT_STRING="host:port:sid"
export ORACLE_HOME="/path/to/oracle/home"
export TNS_ADMIN="$ORACLE_HOME/network/admin"
```

#### MySQL Database
```bash
export MYSQL_HOST="hostname"
export MYSQL_TCP_PORT="3306"
export MYSQL_DATABASE="database_name"
export MYSQL_USER="username"
export MYSQL_PASSWORD="password"
```

#### PostgreSQL Database
```bash
export PGHOST="hostname"
export PGPORT="5432"
export PGDATABASE="database_name"
export PGUSER="username"
export PGPASSWORD="password"
```

#### Comparison Testing
```bash
export SOURCE_DBMS_TYPE="oracle"
export TARGET_DBMS_TYPE="postgresql"  # or "mysql"
```

## Usage Examples

### 1. Bulk SQL Testing
```bash
# Test all SQL against Oracle (SELECT only)
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson /path/to/mappers --db oracle --select-only

# Test all SQL against PostgreSQL with JSON output
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson /path/to/mappers --db postgresql --json --verbose

# Cross-database comparison testing
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson /path/to/mappers --db oracle --compare
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson /path/to/mappers --db postgresql --compare
```

### 2. Parameter Generation
```bash
# Extract parameters with Oracle database samples
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkPreparator /path/to/mappers --db oracle

# Generate bind variables using Oracle dictionary
java -cp ".:lib/*" com.test.mybatis.SimpleBindVariableGenerator /path/to/mappers

# AI-powered parameter generation
java -cp ".:lib/*" com.test.mybatis.SqlPlusBindVariableGeneratorSimple
```

### 3. Result Analysis
```bash
# Analyze test results and categorize errors
java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer

# Automatic sorting difference fixes
java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer --fix-sorting
```

### 4. Single SQL Testing
```bash
# Test individual SQL statement
java -cp ".:lib/*" com.test.mybatis.MyBatisSimpleExecutor /path/to/mapper.xml selectUserById

# Prepare test for specific SQL
java -cp ".:lib/*" com.test.mybatis.MyBatisTestPreparator /path/to/mapper.xml selectUserById
```

## Command Line Options

### MyBatisBulkExecutorWithJson Options
| Option | Description |
|--------|-------------|
| `--db <type>` | Database type (oracle, mysql, postgresql) - **required** |
| `--select-only` | Execute SELECT statements only (default) |
| `--all` | Execute all SQL statements including DML |
| `--summary` | Output summary information only |
| `--verbose` | Output detailed information |
| `--json` | Generate JSON result file |
| `--json-file <name>` | Specify custom JSON filename |
| `--compare` | Enable cross-database result comparison |
| `--show-data` | Output SQL result data |
| `--include <pattern>` | Filter directories by pattern |

### MyBatisBulkPreparator Options
| Option | Description |
|--------|-------------|
| `--db <type>` | Database type for sample collection |
| `--date-format <fmt>` | Date format (default: YYYY-MM-DD) |

## Configuration Files

### mybatis-bulk-executor.properties
```properties
# Temporary file settings
temp.config.prefix=mybatis-config-
temp.mapper.prefix=mapper-
temp.file.suffix=.xml

# SQL pattern settings
sql.pattern.regex=<(select|insert|update|delete)\\s+id="([^"]+)"
example.patterns=byexample,example,selectByExample,selectByExampleWithRowbounds

# MyBatis settings
mybatis.mapUnderscoreToCamelCase=true
mybatis.transactionManager=JDBC
mybatis.dataSource=POOLED

# Output settings
output.json.prefix=bulk_test_result_
output.json.suffix=.json
output.timestamp.format=yyyyMMdd_HHmmss
output.datetime.format=yyyy-MM-dd HH:mm:ss

# Database driver settings
db.oracle.driver=oracle.jdbc.driver.OracleDriver
db.mysql.driver=com.mysql.cj.jdbc.Driver
db.postgresql.driver=org.postgresql.Driver
```

### parameters.properties (Generated)
```properties
# MyBatis parameter configuration file
# Generated: 2024-12-01 14:30:22
# Priority: DB sample values > default values > manual values

# Matched variables (matched with Oracle DB columns)
# USERS.USER_ID (NUMBER)
userId=1

# USERS.EMAIL (VARCHAR2)
email=test@example.com

# Unmatched variables (please set values manually)
customParameter=DEFAULT_VALUE
```

## Output Examples

### Console Output
```
=== MyBatis Bulk SQL Execution Test (Enhanced Version) ===
Search Directory: /path/to/mappers
Database Type: POSTGRESQL
Execution Mode: SELECT only
Output Mode: Detailed
Comparison Feature: Enabled

XML Files Found: 25
SQL Count to Execute: 147

=== SQL Test Execution Started ===
Progress: 100.0% [147/147] UserMapper.xml:selectUser

=== Execution Results Summary ===
Total Tests: 147
Actually Executed: 142
Skipped: 5 (Example patterns)
Success: 138
Failed: 4
Actual Success Rate: 97.2% (excluding skipped)

📄 JSON Result File Generated: bulk_test_result_20241201_143022.json
```

### JSON Output Structure
```json
{
  "testInfo": {
    "timestamp": "2024-12-01 14:30:22",
    "directory": "/path/to/mappers",
    "databaseType": "POSTGRESQL",
    "totalTests": 147,
    "successCount": 138,
    "failureCount": 4,
    "successRate": "97.2"
  },
  "successfulTests": [
    {
      "xmlFile": "UserMapper.xml",
      "sqlId": "selectUser",
      "sqlType": "SELECT",
      "rowCount": 3
    }
  ],
  "failedTests": [
    {
      "xmlFile": "OrderMapper.xml",
      "sqlId": "selectOrder",
      "sqlType": "SELECT",
      "errorMessage": "relation \"orders\" does not exist"
    }
  ],
  "fileStatistics": [
    {
      "fileName": "UserMapper.xml",
      "totalTests": 15,
      "successCount": 14,
      "failureCount": 1,
      "successRate": "93.3"
    }
  ]
}
```

## Key Features

### 1. Intelligent Parameter Generation
- **Database Integration**: Connects to Oracle to extract actual column samples
- **Smart Matching**: Multiple algorithms for parameter-column matching
- **AI Enhancement**: Amazon Q integration for context-aware suggestions
- **Fallback Mechanisms**: Reliable default value generation

### 2. Cross-Database Testing
- **Multi-Platform Support**: Oracle, MySQL, PostgreSQL
- **Result Comparison**: Normalized comparison across databases
- **Difference Analysis**: Distinguishes sorting vs data differences
- **Automatic Fixes**: ORDER BY insertion for sorting issues

### 3. Comprehensive Reporting
- **JSON Output**: Structured result files for automation
- **Statistical Analysis**: Success rates, error categorization
- **Progress Tracking**: Real-time execution progress
- **Error Classification**: Categorized failure analysis

### 4. Production Ready
- **Resource Management**: Safe cleanup and error handling
- **Configuration**: External configuration file support
- **Scalability**: Handles large XML file collections
- **Reliability**: Timeout handling and fallback mechanisms

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Verify environment variables
echo $ORACLE_SVC_USER $ORACLE_SVC_PASSWORD $ORACLE_SVC_CONNECT_STRING

# Test Oracle connectivity
sqlplus $ORACLE_SVC_USER/$ORACLE_SVC_PASSWORD@$ORACLE_SVC_CONNECT_STRING
```

#### 2. Missing JDBC Drivers
```bash
# Ensure JDBC drivers are in classpath
ls -la lib/ojdbc*.jar lib/mysql-connector*.jar lib/postgresql*.jar
```

#### 3. Parameter File Issues
```bash
# Generate fresh parameter file
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkPreparator /path/to/mappers --db oracle
```

#### 4. JSON Output Problems
```bash
# Check output directory permissions
ls -la out/
mkdir -p out
chmod 755 out
```

### Performance Optimization

#### 1. Large XML Collections
- Use `--include` option to filter directories
- Run with `--summary` for faster execution
- Consider parallel execution for independent mapper groups

#### 2. Database Performance
- Ensure proper database connection pooling
- Use `--select-only` for read-only testing
- Monitor database connection limits

#### 3. Memory Management
- Increase JVM heap size for large result sets: `-Xmx4g`
- Use streaming for very large XML files
- Consider batch processing for massive collections

## Integration Examples

### CI/CD Pipeline Integration
```bash
#!/bin/bash
# Automated testing pipeline

# 1. Generate parameters
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkPreparator $MAPPER_DIR --db oracle

# 2. Test Oracle compatibility
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $MAPPER_DIR --db oracle --json --compare

# 3. Test PostgreSQL migration
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $MAPPER_DIR --db postgresql --json --compare

# 4. Analyze results
java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer

# 5. Auto-fix sorting issues
java -cp ".:lib/*" com.test.mybatis.TestResultAnalyzer --fix-sorting
```

### Development Workflow
```bash
# 1. Quick single SQL test
java -cp ".:lib/*" com.test.mybatis.MyBatisSimpleExecutor UserMapper.xml selectUserById

# 2. Prepare comprehensive test
java -cp ".:lib/*" com.test.mybatis.MyBatisTestPreparator UserMapper.xml selectUserById

# 3. Full mapper testing
java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson /path/to/mappers --db oracle --verbose
```

## License

This project is distributed under the MIT License.

## Contributing

1. Follow existing code patterns and naming conventions
2. Add comprehensive JavaDoc comments for new methods
3. Include unit tests for new functionality
4. Update this README for new features or changes
5. Ensure all Korean text is translated to English
