# Kiro-MCP

## 1. oracle-client-mcp

The Oracle MCP server provides direct access to Oracle database operations through Kiro CLI.

**Key Capabilities:**
- Execute SQL queries on Oracle databases
- Run test cases with read-only mode (guaranteed no side effects)
- Run test cases with rollback mode (automatic transaction rollback)
- Support for both password and AWS Secrets Manager authentication

**Available Tools:**
- `oracle_execute_sql` - Execute SQL statements and return results
- `oracle_execute_testcase_readonly` - Execute test cases with read-only connection
- `oracle_execute_testcase_rollback` - Execute test cases with automatic rollback

## 2. pg-client-mcp

The PostgreSQL MCP server provides equivalent functionalities for PostgreSQL databases, following Spring AI MCP best practices.

**Key Capabilities:**
- Execute SQL queries against PostgreSQL databases
- Run test cases with read-only mode (guaranteed no side effects)
- Run test cases with rollback mode (automatic transaction rollback)
- Support for both password and AWS Secrets Manager authentication
- Execution timing for performance analysis

**Available Tools:**
- `postgresql_execute_sql` - Execute SQL statements and return results
- `postgresql_execute_testcase_readonly` - Execute test cases with read-only connection
- `postgresql_execute_testcase_rollback` - Execute test cases with automatic rollback

**Architecture:** Built on Spring Boot 3.5.5 with Spring AI MCP 1.0.2 for standards compliance and reliability.

## 3. mma-sc-mcp

The MMA Schema Conversion MCP server analyzes AWS DMS Schema Conversion projects stored in S3, providing detailed object mapping information.

**Key Capabilities:**
- Analyze DMS Schema Conversion projects in S3
- Generate comprehensive object mapping reports
- Filter results by object type, schema, and object name
- Cache analysis results for faster subsequent queries
- Support for all database object types (tables, views, functions, procedures, etc.)

**Available Tools:**
- `analyze_dms_sc_project` - Analyze DMS SC project from S3 (auto-loads from cache if exists)
- `report_dms_sc_project` - Get analysis report with flexible filtering (type, schema, name)
- `cleanup_local_cache` - Clean up local cache using S3 path
- `get_offlinle_ddl` - Get DDL(Data Definition Language) without requiring Oracle access

**Supported Object Types:**
- Tables, Views, Materialized Views
- Functions, Procedures
- Package Functions, Package Procedures
- Synonyms

**Filtering Examples:**
:::code{showCopyAction=false}
# All mappings
report_dms_sc_project("s3://bucket/prefix/")

# Only tables
report_dms_sc_project("s3://bucket/prefix/", "table")

# Tables in specific schema
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO")

# Specific table
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO", "ORDERS")
:::

## Communication Protocol

All three MCP servers use the **stdio (standard input/output) protocol** for communication with Kiro CLI. It provides:

- **Stability** - No HTTP connection issues or timeouts
- **Simplicity** - Direct process communication via stdin/stdout
- **Reliability** - More robust than SSE for long-running operations
- **Compatibility** - Standard MCP protocol supported by Kiro CLI

## Integration with Kiro CLI

These MCP servers are configured in the Kiro CLI agent configuration file (`~/.kiro/agents/mma-agent.json`), allowing Kiro to invoke their tools as needed during migration tasks. The tools are automatically discovered and made available to Kiro's reasoning engine.

:::code{showCopyAction=false}
kiro-cli --agent mma-agent
:::

