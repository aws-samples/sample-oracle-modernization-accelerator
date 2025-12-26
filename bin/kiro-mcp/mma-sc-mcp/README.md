# MMA Schema Conversion MCP Server

MCP server for analyzing AWS DMS Schema Conversion projects from S3.

## Features

- **analyze_dms_sc_project**: Analyzes DMS SC project from S3 (auto-loads from cache if exists)
- **report_dms_sc_project**: Gets analysis report with flexible filtering (type, schema, name)
- **cleanup_local_cache**: Cleans up local cache using S3 path

## Build

```bash
mvn clean package
```

## Test Without MCP Server

```bash
# Analyze a project
./test.sh analyze s3://bucket/prefix/

# Get full report
./test.sh report s3://bucket/prefix/

# Filter by object type
./test.sh report s3://bucket/prefix/ table
./test.sh report s3://bucket/prefix/ function
./test.sh report s3://bucket/prefix/ mview

# Filter by type and schema
./test.sh report s3://bucket/prefix/ table DEMO

# Filter by type, schema, and name
./test.sh report s3://bucket/prefix/ table DEMO ORDERS

# Cleanup
./test.sh cleanup s3://bucket/prefix/
```

## Run as MCP Server

### Q CLI Integration

Configure in `~/.aws/amazonq/cli-agents/mma-agent.json`:

```json
{
  "mcpServers": {
    "mma-sc-mcp": {
      "type": "stdio",
      "command": "java",
      "args": ["-jar", "/absolute/path/to/mma-sc-mcp/target/mma-sc-mcp-server-1.0.0.jar"],
      "timeout": 300000
    }
  }
}
```

## MCP Protocol

Uses stdio (standard input/output) protocol for stable, reliable communication.

## MCP Tools

### 1. analyze_dms_sc_project(s3Path)

Analyzes DMS SC project. Auto-loads from cache if analysis exists.

**Parameters:**
- `s3Path`: S3 path to DMS SC project

**Example:**
```
analyze_dms_sc_project("s3://bucket/prefix/")
```

### 2. report_dms_sc_project(s3Path, objectType, schemaName, objectName)

Gets cached analysis report with flexible filtering. All filters are case-insensitive.

**Parameters:**
- `s3Path`: S3 path to DMS SC project (required)
- `objectType`: Filter by object type - table, view, mview, function, procedure, synonym, pkg_function, pkg_procedure (optional)
- `schemaName`: Filter by source schema name (optional)
- `objectName`: Filter by source object name (optional)

**Examples:**
```
# All mappings
report_dms_sc_project("s3://bucket/prefix/")

# Only tables
report_dms_sc_project("s3://bucket/prefix/", "table")

# Tables in DEMO schema
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO")

# Specific table
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO", "ORDERS")

# Case insensitive
report_dms_sc_project("s3://bucket/prefix/", "TABLE", "demo", "orders")
```

### 3. cleanup_local_cache(s3Path)

Cleans cache using S3 path. Empty string cleans all cache.

**Parameters:**
- `s3Path`: S3 path (empty for all cache)

**Examples:**
```
cleanup_local_cache("s3://bucket/prefix/")  # Specific project
cleanup_local_cache("")  # All cache
```

## Analysis Results

Returns comprehensive object mappings:

- `servers`: Source/target database info
- `table_mappings`: Tables
- `view_mappings`: Views
- `mview_mappings`: Materialized views
- `function_mappings`: Functions
- `procedure_mappings`: Procedures
- `pkg_function_mappings`: Package functions
- `pkg_procedure_mappings`: Package procedures
- `synonym_mappings`: Synonyms

Objects without target show `null` for `trg_schema` and `trg_name`.
