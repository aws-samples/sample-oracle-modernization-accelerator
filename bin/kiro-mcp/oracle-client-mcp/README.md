# Oracle MCP Server

A Model Context Protocol (MCP) server for Oracle database operations.

## Features

- Execute SQL statements on Oracle databases
- Test case execution with read-only and rollback modes
- Support for both password and AWS Secrets Manager authentication

## Security Recommendation

For production use, it's recommended to create a dedicated read-only database user for the MCP server connection to prevent accidental data modifications:

```sql
-- Create read-only user
CREATE USER mcp_readonly IDENTIFIED BY "your_secure_password";

-- Grant minimal required privileges
GRANT CONNECT TO mcp_readonly;
GRANT SELECT ANY TABLE TO mcp_readonly;
GRANT SELECT ANY DICTIONARY TO mcp_readonly;

-- Optional: Grant access to specific schemas only
-- GRANT SELECT ON schema_name.* TO mcp_readonly;
```

## Configuration

Update `src/main/resources/application.properties`:

```properties
# MCP Server Configuration
spring.ai.mcp.server.protocol=STDIO

# Database connection (password mode)
mcp.db.connection.type=password
mcp.db.connection.detail=mcp_readonly:your_secure_password@hostname:port/service

# Database connection (secrets manager mode)
mcp.db.connection.type=secretsmanager
mcp.db.connection.detail=arn:aws:secretsmanager:region:account:secret:name
```

## Build and Run

```bash
./mvnw clean package
```

## Q CLI Integration

Configure in `~/.aws/amazonq/cli-agents/mma-agent.json`:

```json
{
  "mcpServers": {
    "oracle-client-mcp": {
      "type": "stdio",
      "command": "java",
      "args": ["-jar", "/absolute/path/to/oracle-client-mcp/target/oracle-mcp-server-1.0.0.jar"],
      "timeout": 300000
    }
  }
}
```

## Available Tools

- `oracle_execute_sql`: Execute SQL statements
- `oracle_execute_testcase_readonly`: Execute test cases with read-only guarantee
- `oracle_execute_testcase_rollback`: Execute test cases with rollback guarantee

## MCP Protocol

Uses stdio (standard input/output) protocol for stable, reliable communication.
