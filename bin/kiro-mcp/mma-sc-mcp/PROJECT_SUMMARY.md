# MMA-SC-MCP Project Summary

## Overview

Created a new MCP (Model Context Protocol) server called `mma-sc-mcp` that analyzes AWS DMS Schema Conversion projects stored in S3.

## Project Structure

```
mma-sc-mcp/
├── pom.xml
├── README.md
├── PROJECT_SUMMARY.md
├── docs/
│   └── qcli-config.md
└── src/
    └── main/
        ├── java/com/example/
        │   ├── MmaScMcpServerApplication.java
        │   └── MmaScMcpTools.java
        └── resources/
            └── application.properties
```

## Key Features

### 1. analyze_dms_sc_project Tool

Downloads and analyzes DMS Schema Conversion project files from S3:

- **Downloads all project files** from S3 to local cache (`~/.mma-sc/<bucket>/<prefix>/`)
- **Extracts server details** (source/target database engines, versions)
- **Extracts mappings**:
  - Table mappings (source → target)
  - Function mappings
  - Procedure mappings
  - Package procedure mappings
  - Package function mappings
- **Saves DDL scripts** to organized directories:
  - `ddl/source/` - Source database object DDLs
  - `ddl/target/` - Target database object DDLs
  - Files named: `<schema>_<type>_<name>.sql`

### 2. cleanup_local_cache Tool

Cleans up local cache directories to free disk space.

## Implementation Details

### Data Extraction Logic

Based on the SQL functions provided, the tool implements:

1. **Server Details**: Parses `*-server` files to extract database vendor, engine, and version
2. **Table Mappings**: Matches source and target tables using `synchronization_object` references
3. **Function/Procedure Mappings**: Matches objects across source and target schemas
4. **Package Objects**: Extracts package procedures and functions with proper naming

### File Organization

- Uses S3 bucket and prefix to create unique local directories
- Avoids naming conflicts by preserving S3 path structure
- DDL files use sanitized names: `<schema>_<type>_<name>.sql`

## Technologies Used

- **Spring Boot 3.5.5**: Application framework
- **Spring AI MCP Server**: MCP protocol implementation
- **AWS SDK for Java 2.x**: S3 access
- **Jackson**: JSON parsing
- **Java 21**: Language version

## Build & Run

```bash
# Build
cd mma-sc-mcp
./mvnw clean package

# Run
java -jar target/mma-sc-mcp-server-1.0.0.jar
```

## Q CLI Integration

Add to `~/.aws/q/mcp-servers.json`:

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

## Example Usage

```
# In Q Chat
analyze_dms_sc_project("s3://mma-dms-sc-111709976242/dms-sc-migration-project/")

# Returns:
# - project_id
# - local_base path
# - files_processed count
# - servers (source/target details)
# - table_mappings
# - function_mappings
# - procedure_mappings
# - pkg_procedure_mappings
# - pkg_function_mappings

# Clean up when done
cleanup_local_cache("")
```

## Design Decisions

1. **Local caching**: Files are cached locally for faster subsequent analysis and to preserve data
2. **Unique project IDs**: Each analysis generates a UUID for tracking
3. **Organized DDL storage**: Separate directories for source/target with clear naming
4. **Minimal dependencies**: Only essential libraries to keep the JAR size manageable
5. **Pattern-based file matching**: Uses regex patterns to identify different object types (similar to SQL REGEXP_LIKE)

## Future Enhancements

Potential improvements:
- Add column-level analysis (using the `get_table_columns` function logic)
- Support incremental updates (only download changed files)
- Add data type mapping analysis
- Generate migration reports
- Support multiple project analysis and comparison
