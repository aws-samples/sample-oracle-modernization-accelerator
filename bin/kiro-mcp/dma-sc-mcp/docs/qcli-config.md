# Q CLI Configuration for MMA-SC-MCP

## Add MCP Server to Q CLI

Add the following to your Q CLI configuration file (`~/.aws/q/mcp-servers.json`):

```json
{
  "mcpServers": {
    "mma-sc-mcp": {
      "command": "java",
      "args": [
        "-jar",
        "/Users/donghual/AWS/Code/Java/MMA-Samples/mma-sc-mcp/target/mma-sc-mcp-server-1.0.0.jar"
      ]
    }
  }
}
```

## Available Tools

### 1. analyze_dms_sc_project

Analyzes DMS Schema Conversion project from S3 and extracts all metadata and DDL scripts.

**Parameters:**
- `s3Path` (string): S3 path to DMS SC project (e.g., "s3://mma-dms-sc-111709976242/dms-sc-migration-project/")

**Returns:**
- `project_id`: Generated UUID for the project
- `local_base`: Local directory where files are stored
- `files_processed`: Number of files downloaded
- `servers`: Source and target server details
- `table_mappings`: Source to target table mappings
- `function_mappings`: Function mappings
- `procedure_mappings`: Procedure mappings
- `pkg_procedure_mappings`: Package procedure mappings
- `pkg_function_mappings`: Package function mappings

**Example:**
```
analyze_dms_sc_project("s3://mma-dms-sc-111709976242/dms-sc-migration-project/")
```

### 2. cleanup_local_cache

Cleans up local cache directory for DMS SC projects.

**Parameters:**
- `path` (string, optional): Path to clean up. If empty, cleans `~/.mma-sc/`

**Returns:**
- `deleted_items`: Number of items deleted
- `path`: Path that was cleaned

**Example:**
```
cleanup_local_cache("")
cleanup_local_cache("/Users/donghual/.mma-sc/mma-dms-sc-111709976242")
```

## Local Storage Structure

Files are stored in: `~/.mma-sc/<bucket>/<prefix>/`

DDL scripts are saved in:
- `~/.mma-sc/<bucket>/<prefix>/ddl/source/` - Source database DDLs
- `~/.mma-sc/<bucket>/<prefix>/ddl/target/` - Target database DDLs

DDL files are named: `<schema>_<type>_<name>.sql`

## Usage in Q Chat

Once configured, you can use these tools in Q chat:

```
Q: Analyze the DMS SC project at s3://mma-dms-sc-111709976242/dms-sc-migration-project/

Q: Show me the table mappings from the analysis

Q: What are the source and target database engines?

Q: Clean up the local cache
```

## Requirements

- Java 21 or higher
- AWS credentials configured with S3 read access
- Q CLI installed and configured
