# MCP Deployment Package - Summary

## Changes Applied

### 1. All Three Servers Updated
- ✅ pg-client-mcp (PostgreSQL) - Port 8082
- ✅ oracle-client-mcp (Oracle) - Port 8083  
- ✅ oma-mcp (S3 Schema Conversion) - Port 8084

### 2. Configuration Changes
**From**: stdio (local process communication)
**To**: STREAMABLE HTTP (network-based MCP protocol)

**Key Changes**:
- Spring AI MCP starter: `mcp-server` → `mcp-server-webflux`
- Web framework: Spring MVC → Spring WebFlux (Reactive)
- Transport: stdio → STREAMABLE HTTP
- Ports: Added 8082, 8083, 8084
- Capabilities: Explicitly enabled (tool, resource, prompt)

### 3. Files Removed
- ❌ `mcp_api_server.py` (FastAPI wrapper - no longer needed)
- ❌ `requirements.txt` (Python dependencies)
- ❌ `init.sh` (old initialization script)
- ❌ `deploy.sh` (old deployment script)
- ❌ `mcp-config.json` (kiro-cli config)
- ❌ `__pycache__/` (Python cache)

### 4. Files Added/Updated
- ✅ `README.md` - Complete production deployment guide
- ✅ `MCP_SERVERS.md` - Server endpoints documentation
- ✅ `build-all.sh` - Build script (kept)
- ✅ All `application-*.properties` - Updated for STREAMABLE HTTP

### 5. Package Created
- 📦 `mcp-deployment.tar.gz` (118MB)
- Ready for production deployment

## Deployment Package Contents

```
mcp-deployment/
├── README.md                    # Production deployment guide
├── MCP_SERVERS.md              # Endpoints documentation
├── build-all.sh                # Build all servers
├── pg-client-mcp/
│   ├── pom.xml                 # Updated: webflux starter
│   ├── application-secretsmanager.properties  # STREAMABLE config
│   ├── src/                    # Source code
│   └── target/
│       └── postgresql-mcp-server-1.0.0.jar
├── oracle-client-mcp/
│   ├── pom.xml                 # Updated: webflux starter
│   ├── application-secretsmanager.properties  # STREAMABLE config
│   ├── src/                    # Source code
│   └── target/
│       └── oracle-mcp-server-1.0.0.jar
└── oma-mcp/
    ├── pom.xml                 # Updated: webflux starter
    ├── application-s3.properties  # STREAMABLE config
    ├── src/                    # Source code
    └── target/
        └── oma-mcp-server-1.0.0.jar
```

## Quick Start (Production)

```bash
# 1. Extract
tar -xzf mcp-deployment.tar.gz
cd mcp-deployment

# 2. Build (if needed)
./build-all.sh

# 3. Run
java -jar pg-client-mcp/target/postgresql-mcp-server-1.0.0.jar \
  --spring.config.location=pg-client-mcp/application-secretsmanager.properties

# 4. Connect from Bedrock Agent
# URL: http://<host>:8082/mcp
```

## Integration with Bedrock Agent

Use MCP client library (not curl):
```python
from strands import McpClient

client = McpClient(
    transport="streamable_http",
    url="http://your-server:8082/mcp"
)

tools = await client.list_tools()
result = await client.call_tool("executeSql", {"query": "SELECT 1"})
```

## Next Steps

1. Deploy to EC2/ECS/Fargate
2. Configure ALB for HTTPS
3. Set up CloudWatch logging
4. Connect from Bedrock Agent/Strands
5. Test with MCP Inspector

## Support

See README.md for:
- Detailed deployment instructions
- Docker/ECS deployment
- Troubleshooting guide
- Configuration reference
