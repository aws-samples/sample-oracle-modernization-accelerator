# PostgreSQL MCP Server - Enhanced Spring AI Implementation

This project provides a Model Context Protocol (MCP) server for PostgreSQL database operations, now enhanced to follow Spring AI MCP best practices and standards.

## Architecture

```
PostgreSQLMcpServerApplication (Main)
├── McpConfiguration (MCP Tool Registration)
├── PostgreSQLMcpTools (Business Logic)
└── DatabaseConfig (Database Connection)
```

## Available Tools

### 1. `postgresql_execute_sql`
Execute SQL statements and return results.

**Parameters:**
- `sql` (string, required): SQL statement to execute

**Example:**
```json
{
  "name": "postgresql_execute_sql",
  "arguments": {
    "sql": "SELECT * FROM users LIMIT 5"
  }
}
```

### 2. `postgresql_execute_testcase_readonly`
Execute test case SQL statements with execution timing and guaranteed no side effects through read-only connections.

**Parameters:**
- `sql` (string, required): SQL statement to execute as read-only test case

**Example:**
```json
{
  "name": "postgresql_execute_testcase_readonly",
  "arguments": {
    "sql": "SELECT COUNT(*) FROM users"
  }
}
```

### 3. `postgresql_execute_testcase_rollback`
Execute test case SQL statements with execution timing and guaranteed no side effects through transactional rollback.

**Parameters:**
- `sql` (string, required): SQL statement to execute as rollback test case

**Example:**
```json
{
  "name": "postgresql_execute_testcase_rollback",
  "arguments": {
    "sql": "INSERT INTO users (name) VALUES ('test')"
  }
}
```



## Configuration

### Application Properties
```properties
# Spring AI MCP Server Configuration
spring.ai.mcp.server.enabled=true
spring.ai.mcp.server.name=pg-client-mcp
spring.ai.mcp.server.version=1.0.0
spring.ai.mcp.server.protocol=STDIO
spring.ai.mcp.server.request-timeout=120

# MCP Tool Configuration
spring.ai.mcp.server.annotation-scanner.base-packages=com.example

# Database connection configuration
mcp.db.connection.type=password
mcp.db.connection.detail=username:password@hostname:port/database
mcp.db.connection.readonly=false
```

### Database Connection Types

#### Password Authentication
```properties
mcp.db.connection.type=password
mcp.db.connection.detail=donghual:Welcome123@localhost:5432/demodb
```

#### AWS Secrets Manager
```properties
mcp.db.connection.type=secretsmanager
mcp.db.connection.detail=arn:aws:secretsmanager:region:account:secret:name
```

## Building and Running

### Build
```bash
./mvnw clean package
```

### Run
```bash
java -jar target/postgresql-mcp-server-1.0.0.jar
```
Execute with custom settings
```bash
java -jar target/postgresql-mcp-server-1.0.0.jar --spring.config.location=./application-secretsmanager.properties
```
Execute with DEBUG logging
```bash
java -jar target/postgresql-mcp-server-1.0.0.jar --logging.level.com.example=DEBUG
```

### Development Mode
```bash
./mvnw spring-boot:run
```

## MCP Protocol

The Spring AI MCP server uses stdio (standard input/output) protocol for communication. This provides:

- **Stability**: No HTTP connection issues or timeouts
- **Simplicity**: Direct process communication via stdin/stdout
- **Reliability**: More robust than SSE for long-running operations
- **Compatibility**: Standard MCP protocol supported by Q CLI

The server communicates via JSON-RPC messages over stdio.


## Benefits of Spring AI MCP Approach

1. **Standards Compliance**: Follows official Spring AI MCP patterns
2. **Auto-Configuration**: Minimal boilerplate code required
3. **Multiple Transports**: Supports various MCP transport mechanisms
4. **Better Error Handling**: Standardized error responses
5. **JSON Schema Validation**: Automatic input validation
6. **Extensibility**: Easy to add new tools and capabilities
7. **Maintainability**: Follows Spring Boot conventions

## Development Notes

- Uses Spring Boot 3.5.5 with Java 21
- Spring AI MCP version 1.0.2
- PostgreSQL JDBC driver 42.7.1
- Supports AWS Secrets Manager for database credentials
- Includes proper logging and error handling
- Ready for production deployment

## Security Considerations

- Database connections support read-only mode
- SQL injection protection through parameterized queries
- AWS Secrets Manager integration for credential security
- Configurable connection timeouts and limits

This enhanced implementation provides a robust, standards-compliant MCP server that integrates seamlessly with Spring AI and follows best practices for production deployment.
