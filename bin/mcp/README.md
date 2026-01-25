# OMA MCP Servers

Model Context Protocol (MCP) servers for Oracle Migration Assistant (OMA) tools.

## Servers

- **oma-sc-mcp**: DMS Schema Conversion tools
- **pg-client-mcp**: PostgreSQL database client tools
- **oracle-client-mcp**: Oracle database client tools

## Quick Start

### Build All Servers

```bash
./build-all.sh
```

### Run Locally (All 3 Servers)

```bash
# Start all servers
cd oma-sc-mcp && java -jar target/oma-sc-mcp-server-1.0.0.jar &
cd ../pg-client-mcp && java -jar target/postgresql-mcp-server-1.0.0.jar &
cd ../oracle-client-mcp && java -jar target/oracle-mcp-server-1.0.0.jar &

# Servers run on ports 9080, 9081, 9082
```

### Test with OAuth

```bash
# Get token
TOKEN=$(curl -s -X POST https://YOUR_COGNITO_DOMAIN/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&scope=oma-mcp/mcp.access" | jq -r '.access_token')

# Test servers
curl http://localhost:9080/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
curl http://localhost:9081/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
curl http://localhost:9082/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Deployment

**Recommended: Unified Deployment (All 3 servers on 1 infrastructure)**

See [UNIFIED_DEPLOYMENT.md](UNIFIED_DEPLOYMENT.md) for complete setup:
- 1 EC2 instance running all 3 servers
- 1 ALB with path-based routing (/oma-sc, /pg, /oracle)
- 1 CloudFront distribution
- 1 Cognito User Pool for OAuth2
- 1 Bedrock AgentCore Gateway with 3 targets

**Alternative: Individual Deployment**

See [DEPLOYMENT.md](DEPLOYMENT.md) for deploying servers separately.

## Server Details

### oma-sc-mcp

DMS Schema Conversion project analysis tools.

**Tools:**
- `analyze_dms_sc_project`: Analyze DMS SC project and return assessment report
- `report_dms_sc_project`: Generate detailed report from DMS SC project
- `get_offline_ddl`: Get offline DDL from DMS SC project
- `cleanup_local_cache`: Clean up local cache of downloaded projects

**Configuration:** `oma-sc-mcp/src/main/resources/application.properties`

### pg-client-mcp

PostgreSQL database client tools (to be implemented).

### oracle-client-mcp

Oracle database client tools (to be implemented).

## Architecture

```
Client → CloudFront (HTTPS) → ALB → EC2 → MCP Server
                                            ↓
                                     Cognito OAuth2
```

## Development

### Prerequisites
- Java 21
- Maven 3.6+
- Spring Boot 3.5.5
- Spring AI MCP 1.1.0-M2

### Project Structure

```
oma-mcp/
├── oma-sc-mcp/
│   ├── src/main/java/com/example/
│   │   ├── OmaScMcpServerApplication.java
│   │   ├── OmaScMcpTools.java
│   │   ├── StandardMcpController.java  # HTTP MCP endpoint
│   │   └── SecurityConfig.java         # OAuth2 configuration
│   ├── src/main/resources/
│   │   └── application.properties
│   └── pom.xml
├── pg-client-mcp/
└── oracle-client-mcp/
```

### Adding OAuth2 Security

1. Add dependency to `pom.xml`:
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-oauth2-resource-server</artifactId>
</dependency>
```

2. Configure `application.properties`:
```properties
spring.security.oauth2.resourceserver.jwt.issuer-uri=https://cognito-idp.us-east-1.amazonaws.com/YOUR_USER_POOL_ID
spring.security.oauth2.resourceserver.jwt.jwk-set-uri=https://cognito-idp.us-east-1.amazonaws.com/YOUR_USER_POOL_ID/.well-known/jwks.json
```

3. Create `SecurityConfig.java`:
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/mcp").authenticated()
                .anyRequest().permitAll()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> {}))
            .csrf(csrf -> csrf.disable());
        return http.build();
    }
}
```

## Testing

### Get OAuth Token

```bash
TOKEN=$(curl -s -X POST https://YOUR_DOMAIN.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&scope=oma-mcp/mcp.access" | jq -r '.access_token')
```

### Test MCP Endpoint

```bash
# Initialize
curl https://YOUR_CLOUDFRONT_DOMAIN/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# List tools
curl https://YOUR_CLOUDFRONT_DOMAIN/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'
```

## License

Proprietary - Oracle Migration Assistant
