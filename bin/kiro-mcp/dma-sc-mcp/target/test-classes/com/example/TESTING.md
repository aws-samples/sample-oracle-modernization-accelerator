# Testing Guide

## Quick Test (No MCP Configuration Required)

Test the tools directly without setting up MCP server configuration.

### Prerequisites

- Java 21+
- AWS credentials configured
- Built JAR: `./mvnw clean package`

### Run Tests

```bash
# Show usage
./test.sh

# Analyze a DMS SC project
./test.sh analyze s3://mma-dms-sc-111709976242/dms-sc-migration-project/

# Cleanup cache
./test.sh cleanup

# Cleanup specific path
./test.sh cleanup /path/to/cache
```

### Example Output

```bash
$ ./test.sh analyze s3://mma-dms-sc-111709976242/dms-sc-migration-project/

Analyzing: s3://mma-dms-sc-111709976242/dms-sc-migration-project/

=== Result ===
success: true
project_id: 550e8400-e29b-41d4-a716-446655440000
local_base: /Users/donghual/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project
files_processed: 150
servers: [{server_type=source, server_name=oracle-source, ...}, ...]
table_mappings: [{src_schema=HR, src_name=EMPLOYEES, trg_schema=hr, trg_name=employees}, ...]
function_mappings: [...]
procedure_mappings: [...]
pkg_procedure_mappings: [...]
pkg_function_mappings: [...]
```

### Verify Results

Check the local cache directory:

```bash
# View downloaded files
ls -la ~/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project/

# View DDL scripts
ls -la ~/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project/ddl/source/
ls -la ~/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project/ddl/target/

# View a DDL file
cat ~/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project/ddl/source/HR_table_EMPLOYEES.sql
```

## How It Works

The `test.sh` script:
1. Uses the original (non-repackaged) JAR from Maven build
2. Compiles `TestRunner.java` on first run
3. Runs the test with proper classpath including all dependencies
4. Suppresses SLF4J warnings for cleaner output

## Troubleshooting

**Compilation errors?**
- Ensure you've run `./mvnw clean package` first
- Check Java version: `java -version` (must be 21+)

**S3 access errors?**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check S3 access: `aws s3 ls s3://your-bucket/`

**No output?**
- Check if Maven dependencies are downloaded
- Try running: `./mvnw dependency:resolve`

## Alternative: Direct Java Execution

You can also run the test directly:

```bash
# Get classpath
CP=$(./mvnw dependency:build-classpath -q -DincludeScope=runtime -Dmdep.outputFile=/dev/stdout)

# Compile
javac -cp "target/mma-sc-mcp-server-1.0.0.jar.original:$CP" TestRunner.java

# Run
java -cp ".:target/mma-sc-mcp-server-1.0.0.jar.original:$CP" TestRunner analyze s3://bucket/prefix/
```

```bash
cd /Users/donghual/AWS/Code/Java/MMA-Samples/mma-sc-mcp
./src/test/java/com/example/test.sh report s3://mma-dms-sc-111709976242/dms-sc-migration-project/ table DEMO ORDERS
```
```bash
(aws) donghual@ac0775032b9f mma-sc-mcp % ./src/test/java/com/example/test.sh report s3://mma-dms-sc-111709976242/dms-sc-migration-project/ table DEMO ORDERS
Getting report for: s3://mma-dms-sc-111709976242/dms-sc-migration-project/ [type=table] [schema=DEMO] [name=ORDERS]

=== Result ===
table_mappings: 1 items
success: true
local_base: /Users/donghual/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project
analysis_file: /Users/donghual/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project/analysis_results.json
(aws) donghual@ac0775032b9f mma-sc-mcp %
(aws) donghual@ac0775032b9f mma-sc-mcp %
```
