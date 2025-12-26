# Amazon Q CLI Integration Guide

This guide explains how to configure Amazon Q CLI to use the Oracle MCP Server for database operations.

## Prerequisites

### 1. Java Environment
- Java 21 or higher
- Maven 3.6+ for building from source

### 2. Amazon Q CLI
- Install Amazon Q CLI: [Installation Guide](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/q-cli-install.html)
- Verify installation: `q --version`

### 3. Oracle Database
- Oracle database server accessible from your machine
- Database credentials or AWS Secrets Manager configuration

### 4. AWS Credentials (if using Secrets Manager)
- AWS CLI configured: `aws configure`
- IAM permissions for `secretsmanager:GetSecretValue`

## Build and Start MCP Server

### 1. Build the Server
```bash
cd oracle-client-mcp
mvn clean package
```

### 2. Configure Database Connection
Edit `src/main/resources/application.properties`:

**For direct credentials:**
```properties
mcp.db.connection.type=password
mcp.db.connection.detail=username:password@hostname:1521/servicename
mcp.db.connection.readonly=false
mcp.db.testcase.readonly=true
server.port=8082
```

**For AWS Secrets Manager:**
```properties
mcp.db.connection.type=secretsmanager
mcp.db.connection.detail=arn:aws:secretsmanager:region:account:secret:name
mcp.db.connection.readonly=false
mcp.db.testcase.readonly=true
server.port=8082
```

### 3. Start the MCP Server
```bash
java -jar target/oracle-mcp-server-1.0.0.jar
```

The server will start on `http://localhost:8082/oracle-client-mcp/sse`

You shall observe similar information during application startup:

```java
[restartedMain] INFO org.springframework.ai.mcp.server.common.autoconfigure.McpServerAutoConfiguration - Enable tools capabilities, notification: true
[restartedMain] INFO org.springframework.ai.mcp.server.common.autoconfigure.McpServerAutoConfiguration - Registered tools: 4
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
    "oracle-client-mcp": {
      "type": "http",
      "url": "http://localhost:8082/oracle-client-mcp/sse",
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
    "@oracle-client-mcp"
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

### 2. Start Q CLI Chat with Agent
```bash
q chat --agent mma-agent
```

The Oracle MCP server will be automatically loaded when you start the chat session with this agent.


## Verify Configuration

### 1. Check Available Tools
Start a Q CLI chat session and run:
```
/tools
```

You should see Oracle tools:

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

oracle-client-mcp (MCP):
- oracle_execute_sql                  * not trusted
- oracle_execute_testcase_readonly    * not trusted
- oracle_execute_testcase_rollback    * not trusted

```


### 2. Test Database Connection
In Q CLI chat, try a simple query:
```
Execute this SQL query: SELECT * FROM v$version;
```

### 3. Test Case Execution
```
Run this as a test case: SELECT COUNT(*) FROM all_tables;
```

## Usage Examples

### Execute SQL Queries
```
Run this query: SELECT table_name FROM all_tables WHERE ROWNUM <= 5;
```

### Performance Testing
```
Test the performance of: SELECT * FROM large_table WHERE ROWNUM <= 1000;
```

## Troubleshooting

### MCP Server Not Starting
- Check Java version: `java --version`
- Verify port 8082 is available: `netstat -an | grep 8082`
- Check application logs for database connection errors

### Q CLI Cannot Connect to MCP Server
- Verify server is running: `curl http://localhost:8082/oracle-client-mcp/sse`
- Check firewall settings
- Ensure correct URL in Q CLI configuration

### Database Connection Issues
- Test database connectivity: `sqlplus username/password@hostname:1521/servicename`
- Verify AWS credentials if using Secrets Manager: `aws sts get-caller-identity`
- Check database permissions for the configured user

### MCP Tools Not Available in Q CLI
- Restart Q CLI after adding MCP server
- Verify MCP server registration: `q mcp list `
- Check MCP server logs for tool registration errors

## Advanced Configuration

### Custom Configuration File
```bash
java -jar target/oracle-mcp-server-1.0.0.jar \
  --spring.config.location=file:./custom-config.properties
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
- Run MCP server in secure network environment
- Monitor database access logs
