# Quick Start Guide

## 1. Build the Project

```bash
cd mma-sc-mcp
./mvnw clean package
```

## 2. Test Without MCP Configuration (Recommended First)

Test the tools directly to verify everything works:

```bash
# Show usage
./test.sh

# Analyze a DMS SC project
./test.sh analyze s3://mma-dms-sc-111709976242/dms-sc-migration-project/

# View results in ~/.mma-sc/<bucket>/<prefix>/

# Cleanup when done
./test.sh cleanup
```

## 3. Configure Q CLI (Optional)

Edit `~/.aws/q/mcp-servers.json`:

```json
{
  "mcpServers": {
    "mma-sc-mcp": {
      "command": "java",
      "args": [
        "-jar",
        "/Users/donghual/AWS/Code/Java/MMA-Samples/mma-sc-mcp/target/mma-sc-mcp-server-1.0.0.jar"
      ]
    }
  }
}
```

## 4. Restart Q CLI

```bash
# Exit and restart Q chat to load the new MCP server
q chat
```

## 5. Use in Q Chat

```
# Analyze a DMS SC project
analyze_dms_sc_project("s3://mma-dms-sc-111709976242/dms-sc-migration-project/")

# Ask questions about the analysis
What are the source and target databases?
Show me the table mappings
How many functions need to be migrated?

# View DDL files
The DDL files are saved in ~/.mma-sc/<bucket>/<prefix>/ddl/

# Clean up when done
cleanup_local_cache("")
```

## Output Location

All files are stored in: `~/.mma-sc/<bucket>/<prefix>/`

DDL scripts:
- Source: `~/.mma-sc/<bucket>/<prefix>/ddl/source/`
- Target: `~/.mma-sc/<bucket>/<prefix>/ddl/target/`

## Requirements

- Java 21+
- AWS credentials with S3 read access
- Q CLI installed (only for MCP integration)

## Troubleshooting

**Server not starting?**
- Check Java version: `java -version` (should be 21+)
- Verify JAR exists: `ls -lh target/mma-sc-mcp-server-1.0.0.jar`

**S3 access denied?**
- Verify AWS credentials: `aws s3 ls s3://your-bucket/`
- Check IAM permissions for S3 read access

**Tools not appearing in Q?**
- Restart Q CLI after configuration changes
- Check MCP server logs for errors
- Server runs on port 8085
