# Amazon Q CLI Integration Guide

This guide explains how to configure Amazon Q CLI to use the PostgreSQL MCP Server via stdio protocol for database operations.

## Prerequisites

### 1. Java Environment
- Java 21 or higher
- Maven 3.6+ for building from source

### 2. Amazon Q CLI
- Install Amazon Q CLI: [Installation Guide](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/q-cli-install.html)
- Verify installation: `q --version`

### 3. PostgreSQL Database
- PostgreSQL server accessible from your machine
- Database credentials or AWS Secrets Manager configuration

### 4. AWS Credentials (if using Secrets Manager)
- AWS CLI configured: `aws configure`
- IAM permissions for `secretsmanager:GetSecretValue`

## Build and Start MCP Server

### 1. Build the Server
```bash
cd pg-client-mcp
mvn clean package
```

### 2. Configure Database Connection
Edit `src/main/resources/application.properties`:

**For direct credentials:**
```properties
mcp.db.connection.type=password
mcp.db.connection.detail=username:password@hostname:5432/database
mcp.db.connection.readonly=false
mcp.db.testcase.readonly=true
```

**For AWS Secrets Manager:**
```properties
mcp.db.connection.type=secretsmanager
mcp.db.connection.detail=arn:aws:secretsmanager:region:account:secret:name
mcp.db.connection.readonly=false
mcp.db.testcase.readonly=true
```

## Configure Amazon Q CLI

### 1. Create Agent Configuration File
Create or update `~/.aws/amazonq/cli-agents/mma-agent.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/aws/amazon-q-developer-cli/refs/heads/main/schemas/agent-v1.json",
  "name": "mma-agent",
  "description": "Agent with MMA MCP server for migration related database operations",
  "mcpServers": {
    "pg-client-mcp": {
      "type": "stdio",
      "command": "java",
      "args": ["-jar", "/absolute/path/to/pg-client-mcp/target/postgresql-mcp-server-1.0.0.jar"],
      "timeout": 300000,
      "disabled": false
    }
  },
  "tools": [
    "fs_read",
    "fs_write",
    "execute_bash",
    "use_aws",
    "gh_issue",
    "knowledge",
    "thinking",
    "todo_list",
    "@pg-client-mcp"
  ],
  "toolAliases": {},
  "allowedTools": [],
  "resources": [
    "file://AmazonQ.md",
    "file://AGENTS.md",
    "file://README.md",
    "file://.amazonq/rules/**/*.md"
  ],
  "hooks": {},
  "toolsSettings": {},
  "useLegacyMcpJson": true,
  "model": null
}
```

**Important**: Replace `/absolute/path/to/pg-client-mcp` with the actual absolute path to your project directory.

### 2. Start Q CLI Chat with Agent
```bash
q chat --agent mma-agent
```

The PostgreSQL MCP server will be automatically started as a subprocess when you start the chat session.


## Verify Configuration

### 1. Check Available Tools
Start a Q CLI chat session and run:
```
/tools
```

You should see PostgreSQL tools:

```bash
[mma-agent] > /tools


Tool                             Permission
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
Built-in:
- execute_bash                   * not trusted
- fs_read                        * trust working directory
- fs_write                       * not trusted
- report_issue                   * trusted
- use_aws                        * trust read-only commands

pg-client-mcp (MCP):
- postgresql_execute_sql                  * not trusted
- postgresql_execute_testcase_readonly    * not trusted
- postgresql_execute_testcase_rollback    * not trusted

```


### 2. Test Database Connection
In Q CLI chat, try a simple query:
```
Execute this SQL query: SELECT version();
```

### 3. Test Case Execution
```
Run this as a test case: SELECT COUNT(*) FROM information_schema.tables;
```

## Usage Examples

### Execute SQL Queries
```
Run this query: SELECT table_name FROM information_schema.tables LIMIT 5;
```

### Performance Testing
```
Test the performance of: SELECT * FROM large_table LIMIT 1000;
```

## Troubleshooting

### MCP Server Not Starting
- Check Java version: `java --version`
- Verify JAR file exists at the specified path
- Check application logs for database connection errors
- Ensure database credentials are correct

### Q CLI Cannot Connect to MCP Server
- Verify the absolute path in the agent configuration is correct
- Check that the JAR file is executable
- Review Q CLI logs for startup errors
- Ensure Java is in your system PATH

### Database Connection Issues
- Test database connectivity: `psql -h hostname -U username -d database`
- Verify AWS credentials if using Secrets Manager: `aws sts get-caller-identity`
- Check database permissions for the configured user
- Ensure database server is accessible from your machine

### MCP Tools Not Available in Q CLI
- Restart Q CLI after updating agent configuration
- Verify MCP server registration: `q mcp list`
- Check that the server starts successfully when invoked manually
- Review server logs for tool registration errors

## Advanced Configuration

### Custom Configuration File
You can specify a custom configuration file by modifying the `args` in the agent configuration:

```json
"args": ["-jar", "/path/to/postgresql-mcp-server-1.0.0.jar", "--spring.config.location=file:./custom-config.properties"]
```

### Read-Only Mode
Set `mcp.db.connection.readonly=true` for read-only database access.

### Test Case Safety
- `mcp.db.testcase.readonly=true`: Uses read-only connections
- `mcp.db.testcase.readonly=false`: Uses transactional rollback

## Security Considerations

- Use AWS Secrets Manager for production environments
- Configure read-only access when possible
- Restrict database user permissions appropriately
- The MCP server runs as a subprocess with your user permissions
- Monitor database access logs
