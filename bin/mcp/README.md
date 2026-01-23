# MCP Servers - Production Deployment Guide

Oracle Modernization Accelerator (OMA) MCP Servers with STREAMABLE HTTP transport for Bedrock Agent integration.

## Overview

Three MCP servers providing database migration tools:
- **pg-client-mcp**: PostgreSQL/Aurora database operations
- **oracle-client-mcp**: Oracle database operations  
- **oma-mcp**: S3-based schema conversion tools

## Prerequisites

- Java 21+
- Maven 3.6+
- AWS credentials configured (for Secrets Manager access)
- Network access to:
  - Aurora PostgreSQL (aurora.mma.internal:5432)
  - Oracle Database (oracledb.mma.internal:1521)
  - S3 bucket (mma-dms-sc-*)

## Quick Start

### 1. Extract Package
```bash
unzip mcp-deployment.zip
cd mcp-deployment
```

### 2. Build All Servers
```bash
./build-all.sh
```

This builds:
- `pg-client-mcp/target/postgresql-mcp-server-1.0.0.jar`
- `oracle-client-mcp/target/oracle-mcp-server-1.0.0.jar`
- `oma-mcp/target/oma-mcp-server-1.0.0.jar`

### 3. Configure (Optional)

Edit configuration files if needed:
- `pg-client-mcp/application-secretsmanager.properties`
- `oracle-client-mcp/application-secretsmanager.properties`
- `oma-mcp/application-s3.properties`

**Key settings:**
```properties
# Server port (default: 8082, 8083, 8084)
server.port=8082

# AWS Secrets Manager ARN
mcp.db.connection.detail=arn:aws:secretsmanager:...

# S3 path for schema conversion
mma.sc.default.s3path=s3://bucket-name/path/
```

### 4. Run Servers

#### Option A: Individual Servers
```bash
# PostgreSQL MCP (port 8082)
cd pg-client-mcp
java -jar target/postgresql-mcp-server-1.0.0.jar \
  --spring.config.location=application-secretsmanager.properties

# Oracle MCP (port 8083)
cd oracle-client-mcp
java -jar target/oracle-mcp-server-1.0.0.jar \
  --spring.config.location=application-secretsmanager.properties

# OMA MCP (port 8084)
cd oma-mcp
java -jar target/oma-mcp-server-1.0.0.jar \
  --spring.config.location=application-s3.properties
```

#### Option B: Background Execution
```bash
# Start all servers in background
nohup java -jar pg-client-mcp/target/postgresql-mcp-server-1.0.0.jar \
  --spring.config.location=pg-client-mcp/application-secretsmanager.properties \
  > /var/log/pg-client-mcp.log 2>&1 &

nohup java -jar oracle-client-mcp/target/oracle-mcp-server-1.0.0.jar \
  --spring.config.location=oracle-client-mcp/application-secretsmanager.properties \
  > /var/log/oracle-client-mcp.log 2>&1 &

nohup java -jar oma-mcp/target/oma-mcp-server-1.0.0.jar \
  --spring.config.location=oma-mcp/application-s3.properties \
  > /var/log/oma-mcp.log 2>&1 &
```

### 5. Verify

Check server logs:
```bash
tail -f /var/log/pg-client-mcp.log
# Look for: "Started PostgreSQLMcpServerApplication"
# Look for: "Registered tools: 3"
```

Check endpoints are accessible:
```bash
curl http://localhost:8082/mcp  # Should return 400 (expected without MCP client)
curl http://localhost:8083/mcp
curl http://localhost:8084/mcp
```

## MCP Endpoints

| Server | Port | Endpoint | Tools |
|--------|------|----------|-------|
| pg-client-mcp | 8082 | http://localhost:8082/mcp | executeSql, executeTestCaseReadOnly, executeTestCaseRollback |
| oracle-client-mcp | 8083 | http://localhost:8083/mcp | executeSql, executeTestCaseReadOnly, executeTestCaseRollback |
| oma-mcp | 8084 | http://localhost:8084/mcp | listSchemaConversionReports, getSchemaConversionReport, etc. |

## Bedrock Agent Integration

### Using Strands Framework

```python
from strands import McpClient

# Connect to MCP server
client = McpClient(
    transport="streamable_http",
    url="http://localhost:8082/mcp"
)

# List available tools
tools = await client.list_tools()

# Call a tool
result = await client.call_tool(
    name="executeSql",
    arguments={"query": "SELECT 1"}
)
```

### Using AgentCore

Configure MCP server URL in AgentCore:
```
http://<ec2-instance>:8082/mcp
http://<ec2-instance>:8083/mcp
http://<ec2-instance>:8084/mcp
```

## Production Deployment

### Docker (Recommended)

Create `Dockerfile`:
```dockerfile
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY pg-client-mcp/target/postgresql-mcp-server-1.0.0.jar app.jar
COPY pg-client-mcp/application-secretsmanager.properties application.properties
EXPOSE 8082
CMD ["java", "-jar", "app.jar", "--spring.config.location=application.properties"]
```

Build and run:
```bash
docker build -t pg-client-mcp .
docker run -d -p 8082:8082 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=xxx \
  pg-client-mcp
```

### ECS/Fargate

1. Push Docker images to ECR
2. Create ECS task definitions with:
   - Container port: 8082/8083/8084
   - Environment variables: AWS credentials
   - Health check: HTTP GET /actuator/health (if enabled)
3. Deploy as ECS service with ALB

### Systemd Service

Create `/etc/systemd/system/pg-client-mcp.service`:
```ini
[Unit]
Description=PostgreSQL MCP Server
After=network.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp-deployment/pg-client-mcp
ExecStart=/usr/bin/java -jar target/postgresql-mcp-server-1.0.0.jar --spring.config.location=application-secretsmanager.properties
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable pg-client-mcp
sudo systemctl start pg-client-mcp
sudo systemctl status pg-client-mcp
```

## Troubleshooting

### Server won't start
```bash
# Check Java version
java -version  # Must be 21+

# Check logs
tail -100 /var/log/pg-client-mcp.log

# Common issues:
# - AWS credentials not configured
# - Secrets Manager access denied
# - Port already in use
```

### 400 Bad Request
This is **expected** when testing with curl. MCP protocol requires:
- MCP client library (not raw HTTP)
- Session management
- Proper headers (Mcp-Session-Id)

Use MCP Inspector or Bedrock Agent to test properly.

### Database connection failed
```bash
# Check Secrets Manager access
aws secretsmanager get-secret-value \
  --secret-id arn:aws:secretsmanager:us-east-1:775881734961:secret:MMA-secret-aurora-admin-Zi7ao5

# Check network connectivity
telnet aurora.mma.internal 5432
telnet oracledb.mma.internal 1521
```

### Tools not registered
Check logs for:
```
INFO - Registered tools: 3
```

If 0 tools, check:
- `@Tool` annotations in source code
- `spring.ai.mcp.server.annotation-scanner.base-packages=com.example`
- `spring.ai.mcp.server.capabilities.tool=true`

## Architecture

```
Bedrock Agent / Strands
    ↓ (MCP Client)
HTTP POST /mcp
    ↓
Spring AI MCP Server (WebFlux)
    ↓
@Tool annotated methods
    ↓
Database / S3
```

**Transport**: STREAMABLE HTTP (MCP protocol over HTTP)
**Framework**: Spring AI MCP 1.1.0-M2
**Runtime**: Spring Boot 3.5.5 + WebFlux (Reactive)

## Configuration Reference

### Server Properties
```properties
# MCP Protocol
spring.ai.mcp.server.protocol=STREAMABLE
spring.ai.mcp.server.type=SYNC

# Capabilities
spring.ai.mcp.server.capabilities.tool=true
spring.ai.mcp.server.capabilities.resource=true
spring.ai.mcp.server.capabilities.prompt=true

# HTTP Settings
spring.ai.mcp.server.streamable-http.mcp-endpoint=/mcp
spring.ai.mcp.server.streamable-http.keep-alive-interval=30s
spring.ai.mcp.server.streamable-http.response-mime-type=text/plain+stream

# Server
server.port=8082
spring.main.web-application-type=reactive
```

### Database Connection
```properties
# Secrets Manager
mcp.db.connection.type=secretsmanager
mcp.db.connection.detail=arn:aws:secretsmanager:region:account:secret:name

# Direct (not recommended for production)
mcp.db.connection.type=direct
spring.datasource.url=jdbc:postgresql://host:5432/db
spring.datasource.username=user
spring.datasource.password=pass
```

## Security

- **Secrets Manager**: Database credentials stored in AWS Secrets Manager
- **IAM Roles**: Use EC2 instance roles instead of access keys
- **Network**: Deploy in private subnet, expose via ALB
- **TLS**: Enable HTTPS in production (ALB termination or Spring Boot SSL)

## Monitoring

### Health Check
Enable Spring Boot Actuator:
```properties
management.endpoints.web.exposure.include=health,info
management.endpoint.health.show-details=always
```

Check: `http://localhost:8082/actuator/health`

### Logs
- Application logs: `/var/log/*-mcp.log`
- Spring logs: Configure `logging.file.name`
- CloudWatch: Use CloudWatch agent for centralized logging

### Metrics
- JVM metrics: Enable Micrometer
- MCP metrics: Tool invocation counts, latency
- Database metrics: Connection pool stats

## Support

For issues or questions:
- Check logs with DEBUG level: `logging.level.org.springframework.ai.mcp=DEBUG`
- Review Spring AI MCP documentation: https://docs.spring.io/spring-ai/reference/api/mcp/
- GitHub issues: Spring AI MCP project

## License

See individual MCP server directories for license information.
