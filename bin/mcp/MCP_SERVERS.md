# MCP Servers - STREAMABLE HTTP

## pg-client-mcp (PostgreSQL)
- **URL**: http://localhost:8082/mcp
- **Protocol**: STREAMABLE HTTP
- **Tools**: 3 (executeSql, executeTestCaseReadOnly, executeTestCaseRollback)
- **Status**: ✅ Running

## oracle-client-mcp (Oracle)
- **URL**: http://localhost:8083/mcp
- **Protocol**: STREAMABLE HTTP (to be configured)
- **Status**: ⏳ Pending

## oma-mcp (S3 Schema Conversion)
- **URL**: http://localhost:8084/mcp
- **Protocol**: STREAMABLE HTTP (to be configured)
- **Status**: ⏳ Pending

## Testing
Use MCP Inspector or Spring AI MCP Client:
```
http://localhost:8082/mcp
http://localhost:8083/mcp
http://localhost:8084/mcp
```

## Bedrock Agent Integration
Configure Strands framework to use these endpoints with MCP client transport.
