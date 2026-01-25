# OMA MCP Servers - All Configured

## Server Details

### 1. oma-sc-mcp (Port 9080)
**DMS Schema Conversion Tools**

Tools:
- `analyze_dms_sc_project`: Analyze DMS SC project
- `report_dms_sc_project`: Generate detailed report
- `get_offline_ddl`: Get offline DDL
- `cleanup_local_cache`: Clean up cache

### 2. pg-client-mcp (Port 9081)
**PostgreSQL Database Client**

Tools:
- `executeSql`: Execute SQL query on PostgreSQL
- `executeTestCaseReadOnly`: Execute test in read-only mode
- `executeTestCaseRollback`: Execute test with rollback

Database: Aurora PostgreSQL (via Secrets Manager)

### 3. oracle-client-mcp (Port 9082)
**Oracle Database Client**

Tools:
- `executeSql`: Execute SQL query on Oracle
- `executeTestCaseReadOnly`: Execute test in read-only mode
- `executeTestCaseRollback`: Execute test with rollback

Database: Oracle RDS (mma-oracle-source.cv45sdrp6rtb.us-east-1.rds.amazonaws.com)

## Common Configuration

All servers include:
- ✅ HTTP POST /mcp endpoint
- ✅ OAuth2 JWT validation (Cognito)
- ✅ MCP Protocol 2025-06-18
- ✅ JSON-RPC 2.0
- ✅ Spring Boot 3.5.5
- ✅ Spring AI MCP 1.1.0-M2

## Build All

```bash
./build-all.sh
```

Output:
- `oma-sc-mcp/target/oma-sc-mcp-server-1.0.0.jar`
- `pg-client-mcp/target/pg-client-mcp-server-1.0.0.jar`
- `oracle-client-mcp/target/oracle-client-mcp-server-1.0.0.jar`

## Deploy

**Unified Deployment (Recommended):**
```
1 EC2 → 3 servers (ports 9080, 9081, 9082)
1 ALB → Path routing (/oma-sc, /pg, /oracle)
1 CloudFront → HTTPS
1 Gateway → 3 targets
```

See [UNIFIED_DEPLOYMENT.md](UNIFIED_DEPLOYMENT.md) for step-by-step guide.

**Individual Deployment:**
Each server can be deployed independently following [DEPLOYMENT.md](DEPLOYMENT.md).

## Test

```bash
# Get token
TOKEN=$(curl -s -X POST https://agentcore-8e9e317c.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=5p5b2k57kq43tmodn9otpm451s&client_secret=uo5ge7vlk2350kehra92196lrh20p1aiutki9flsfrltccji4lb&scope=oma-mcp/mcp.access" | jq -r '.access_token')

# Test each server
curl http://localhost:9080/mcp -H "Authorization: Bearer $TOKEN" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
curl http://localhost:9081/mcp -H "Authorization: Bearer $TOKEN" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
curl http://localhost:9082/mcp -H "Authorization: Bearer $TOKEN" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```
