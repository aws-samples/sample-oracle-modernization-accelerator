# Oracle to PostgreSQL Conversion Agent - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Oracle to PostgreSQL Agent (ora_to_pg_sc_agent.py)        │
│  • Python 3.11 + asyncio                                    │
│  • Single SSE session for all operations                    │
│  • Async workflow: Analyze → Extract → Convert → Save       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ oma-sc-mcp   │   │ pg-client    │   │ oracle-client│
│ Port 9080    │   │ Port 9081    │   │ Port 9082    │
│              │   │              │   │              │
│ Tools:       │   │ Tools:       │   │ Tools:       │
│ • analyze    │   │ • executeSql │   │ • executeSql │
│ • get_ddl    │   │ • testCase   │   │ • testCase   │
│ • convert    │   │              │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
            ┌──────────────┐  ┌──────────────┐
            │ AWS S3       │  │ Bedrock      │
            │ Secrets Mgr  │  │ Claude 3.5   │
            └──────────────┘  └──────────────┘
```

## Component Details

### 1. Agent (Python)

**File**: `ora_to_pg_sc_agent.py`

**Technology Stack**:
- Python 3.11
- asyncio for async/await
- MCP Python SDK (from GitHub)
- httpx for HTTP client

**Responsibilities**:
- Parse command-line arguments (S3 path)
- Open single SSE session to oma-sc-mcp
- Call MCP tools in sequence
- Save DDL files to `/workshop/pg-ddl/`
- Generate conversion report

**Key Functions**:
```python
async def call_tool(session, tool_name, params)
async def process_conversion(session, s3_path)
async def generate_report(s3_path)
async def main(s3_path)
```

**Configuration**:
```python
MCP_OMA_SC = "http://localhost:9080/sse"
OUTPUT_DIR = "/workshop/pg-ddl"
DMS_SC_SCHEMA_NAME = os.getenv("DMS_SC_SCHEMA_NAME", "DEMO")
```

### 2. oma-sc-mcp Server (Java)

**Port**: 9080  
**Transport**: SSE (Server-Sent Events)  
**Framework**: Spring Boot 4.0.1 + Spring AI MCP 2.0.0-M2

**Tools Provided**:

1. **analyze_dms_sc_project**
   - Downloads DMS SC project from S3
   - Extracts ZIP to local cache
   - Parses CSV files for action items
   - Returns list of objects with complexity

2. **get_offline_ddl**
   - Extracts Oracle DDL from local cache
   - No live database connection needed
   - Returns DDL text

3. **convert_ddl_to_pg**
   - Calls Bedrock Claude 3.5 Sonnet
   - Model: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
   - Converts Oracle DDL to PostgreSQL
   - Returns converted DDL

**Key Classes**:
```java
OmaScMcpServerApplication.java  // Main application
OmaScMcpTools.java              // MCP tool implementations
DatabaseConfig.java             // AWS Secrets Manager integration
```

**Dependencies**:
- AWS SDK (S3, Bedrock, Secrets Manager)
- Spring Boot Web
- Spring AI MCP Server WebMVC
- Jackson for JSON

### 3. pg-client-mcp Server (Java)

**Port**: 9081  
**Transport**: SSE  
**Framework**: Spring Boot 4.0.1 + Spring AI MCP 2.0.0-M2

**Tools Provided**:
1. **executeSql** - Execute SQL on PostgreSQL
2. **executeTestCase** - Test with rollback
3. **executeTestCaseReadOnly** - Read-only test

**Database Connection**:
- Via AWS Secrets Manager
- HikariCP connection pool
- PostgreSQL JDBC driver

**Note**: Currently unused by agent (no deployment/testing)

### 4. oracle-client-mcp Server (Java)

**Port**: 9082  
**Transport**: SSE  
**Framework**: Spring Boot 4.0.1 + Spring AI MCP 2.0.0-M2

**Tools Provided**:
1. **executeSql** - Execute SQL on Oracle
2. **executeTestCase** - Test with rollback
3. **executeTestCaseReadOnly** - Read-only test

**Database Connection**:
- Via AWS Secrets Manager
- HikariCP connection pool
- Oracle JDBC driver

**Note**: Currently unused by agent (uses offline DDL)

## Data Flow

### Conversion Workflow

```
1. Agent starts
   ↓
2. Open SSE session to oma-sc-mcp (port 9080)
   ↓
3. Call: analyze_dms_sc_project(s3_path)
   ↓ oma-sc-mcp downloads from S3
   ↓ oma-sc-mcp parses CSV files
   ↓ Returns: List of 17 objects
   ↓
4. For each object:
   ↓
   4a. Call: get_offline_ddl(s3_path, schema, object)
       ↓ oma-sc-mcp reads from local cache
       ↓ Returns: Oracle DDL text
   ↓
   4b. Call: convert_ddl_to_pg(oracle_ddl, type, complexity)
       ↓ oma-sc-mcp calls Bedrock
       ↓ Bedrock Claude 3.5 converts DDL
       ↓ Returns: PostgreSQL DDL text
   ↓
   4c. Agent saves to file
       ↓ /workshop/pg-ddl/Schemas_DEMO_....sql
   ↓
5. Agent generates report
   ↓ /workshop/pg-ddl/CONVERSION_REPORT.md
   ↓
6. Done
```

### MCP Communication

**Protocol**: Model Context Protocol (MCP)  
**Transport**: Server-Sent Events (SSE)  
**Format**: JSON-RPC 2.0

**Request Example**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "convert_ddl_to_pg",
    "arguments": {
      "arg0": "CREATE FUNCTION...",
      "arg1": "Package function",
      "arg2": "Complex"
    }
  }
}
```

**Response Example**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"success\":true,\"postgresql_ddl\":\"CREATE OR REPLACE FUNCTION...\"}"
    }]
  }
}
```

## AWS Integration

### S3 (DMS Schema Conversion Project)

**Bucket**: `mma-dms-sc-147671602580`  
**Path**: `dms-sc-migration-project/`  
**Format**: ZIP file containing:
- CSV files (action items, summary)
- DDL files (Oracle source DDL)
- Metadata files

**Access**: Via IAM role attached to EC2 instance

### Secrets Manager (Database Credentials)

**PostgreSQL Secret**:
```json
{
  "username": "postgres",
  "password": "...",
  "host": "aurora.mma.internal",
  "port": 5432,
  "dbname": "demodb"
}
```

**Oracle Secret**:
```json
{
  "username": "admin",
  "password": "...",
  "host": "oracledb.mma.internal",
  "port": 1521,
  "dbname": "ORCL"
}
```

**Access**: Via IAM role

### Bedrock (AI Model)

**Model**: Claude 3.5 Sonnet v2  
**Model ID**: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`  
**Region**: us-east-1  
**API**: InvokeModel

**Request**:
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 4096,
  "messages": [{
    "role": "user",
    "content": "Convert this Oracle DDL to PostgreSQL..."
  }]
}
```

**Access**: Via IAM role with `bedrock:InvokeModel` permission

## Security

### Authentication
- **No OAuth2**: Removed for simplicity
- **Localhost Only**: MCP servers only listen on 127.0.0.1
- **No External Access**: Not exposed to internet

### Authorization
- **IAM Role**: EC2 instance role for AWS services
- **Secrets Manager**: Database credentials never in code
- **S3 Access**: Read-only access to DMS SC bucket

### Network
- **MCP Servers**: localhost:9080-9082
- **No TLS**: Not needed for localhost
- **Firewall**: No external ports open

## File System

### Local Cache
**Location**: `~/.oma-sc/`  
**Contents**: Downloaded DMS SC projects  
**Cleanup**: Manual or via cleanup tool

### Output Directory
**Location**: `/workshop/pg-ddl/`  
**Contents**:
- Converted DDL files (*.sql)
- Conversion report (CONVERSION_REPORT.md)

### Logs
**MCP Servers**:
- `/tmp/oma-sc.log`
- `/tmp/pg-client.log`
- `/tmp/oracle-client.log`

## Performance

### Typical Conversion (15 objects)
- Analysis: 2-3 seconds
- DDL extraction: 1 second per object
- Bedrock conversion: 2-4 seconds per object
- File save: < 1 second per object
- **Total**: 1-2 minutes

### Bottlenecks
1. Bedrock API calls (rate limited)
2. S3 download (first time only)
3. Network latency

### Optimization
- Single SSE session (no reconnection overhead)
- Local cache for DMS SC projects
- Async/await for non-blocking I/O

## Error Handling

### Agent Level
- Try/catch around each object conversion
- Continue on failure (don't stop batch)
- Track statistics (success/failed/skipped)
- Generate report with all results

### MCP Server Level
- Return `{"success": false, "error": "..."}` on failure
- Log errors to server log files
- Don't crash on individual tool failures

### AWS Level
- Retry with exponential backoff (AWS SDK default)
- Handle throttling (Bedrock rate limits)
- Graceful degradation on service errors

## Deployment

### Prerequisites
1. Java 21 (Amazon Corretto)
2. Maven 3.6+
3. Python 3.11
4. AWS CLI v2

### Setup Steps
```bash
# 1. Configure environment
cd /workshop/oma-mcp
cp env.sh.template env.sh
vi env.sh
source env.sh

# 2. Validate and auto-install
./validate-setup.sh

# 3. Build MCP servers
./build-all.sh

# 4. Start MCP servers
./start-servers.sh

# 5. Run agent
cd /workshop/oma-sc-agent
python3.11 ora_to_pg_sc_agent.py s3://BUCKET/PROJECT.zip
```

## Monitoring

### Health Checks
```bash
# Check MCP servers running
ps aux | grep "\.jar" | grep java

# Check ports listening
lsof -i :9080
lsof -i :9081
lsof -i :9082

# Check logs
tail -f /tmp/oma-sc.log
```

### Metrics
- Objects processed
- Success/failure rate
- Average conversion time
- Bedrock API calls

## Future Enhancements

1. **Deployment**: Add PostgreSQL deployment step
2. **Testing**: Add automated testing of converted objects
3. **Validation**: Compare Oracle vs PostgreSQL results
4. **Parallel Processing**: Convert multiple objects concurrently
5. **Retry Logic**: Retry failed conversions with error context
6. **Dependency Resolution**: Analyze and order by dependencies
