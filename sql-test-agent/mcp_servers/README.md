# MCP Servers

Unified Database MCP Server for SQL Test Agent.

## Database MCP Server

Single server that handles all database types: **Oracle, PostgreSQL, and MySQL**.

### Tools

1. **connect** - Create database connection (any type)
2. **disconnect** - Close connection
3. **test_connection** - Test connection status
4. **execute_sql** - Execute individual SQL from MyBatis mapper
5. **execute_sql_batch** - Execute multiple SQLs in batch
6. **execute_mapper_file** - Execute all SQLs in a mapper file
7. **get_mapper_sql_list** - Get list of SQLs in a mapper file
8. **get_execution_result** - Retrieve cached execution result
9. **list_connections** - List all active connections

### Usage

```bash
# Run Database MCP Server
python database_mcp_server.py
```

### Configuration

Set environment variables:
```bash
# Java executor path
export JAVA_EXECUTOR_PATH=/path/to/bin/test

# Database credentials (set as needed)
# Oracle
export ORACLE_SVC_USER=username
export ORACLE_SVC_PASSWORD=password
export ORACLE_SVC_CONNECT_STRING=host:port:sid

# PostgreSQL
export PGUSER=username
export PGPASSWORD=password
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=dbname

# MySQL
export MYSQL_USER=username
export MYSQL_PASSWORD=password
export MYSQL_HOST=localhost
export MYSQL_TCP_PORT=3306
export MYSQL_DATABASE=dbname
```

## Architecture

The unified server uses the existing Java MyBatis executor (`bin/test`) for SQL execution:

```
Unified MCP Server (Python)
    ↓
Java MyBatis Executor
    ↓
Database (Oracle/PostgreSQL/MySQL)
```

### Connection Examples

#### Oracle Connection
```python
connect(
    db_type="oracle",
    credentials={
        "username": "user",
        "password": "pass",
        "connect_string": "host:1521:sid"
    }
)
```

#### PostgreSQL Connection
```python
connect(
    db_type="postgresql",
    credentials={
        "username": "user",
        "password": "pass",
        "host": "localhost",
        "port": 5432,
        "database": "mydb"
    }
)
```

#### MySQL Connection
```python
connect(
    db_type="mysql",
    credentials={
        "username": "user",
        "password": "pass",
        "host": "localhost",
        "port": 3306,
        "database": "mydb"
    }
)
```

### Execution Flow

1. **Connect**: Create connection with db_type and credentials
2. **Execute**: 
   - Create temporary parameters.properties file
   - Set database-specific environment variables
   - Call Java executor with appropriate --db flag
   - Parse JSON output
   - Cache results
3. **Retrieve**: Get cached results by ID

### Supported Execution Modes

#### 1. Individual SQL Execution
```python
execute_sql(
    connection_id="conn-123",
    sql_id="UserMapper.selectUser",
    mapper_file="/path/to/UserMapper.xml",
    bind_variables={"userId": 1}
)
```

#### 2. Batch Execution
```python
execute_sql_batch(
    connection_id="conn-123",
    sql_list=[
        {"sql_id": "UserMapper.selectUser", "mapper_file": "UserMapper.xml"},
        {"sql_id": "UserMapper.selectUserList", "mapper_file": "UserMapper.xml"}
    ],
    bind_variables={"userId": 1}
)
```

#### 3. Full Mapper Execution
```python
execute_mapper_file(
    connection_id="conn-123",
    mapper_file="/path/to/UserMapper.xml",
    bind_variables={"userId": 1}
)
```

## Benefits of Unified Server

✅ **No Code Duplication**: Single implementation for all databases
✅ **Easy Maintenance**: Fix bugs once, applies to all databases
✅ **Consistent Interface**: Same tools for all database types
✅ **Single Process**: One server handles all database operations
✅ **Flexible**: Easy to add new database types

## Testing

### Manual Test

```bash
# 1. Start MCP server
python database_mcp_server.py

# 2. In another terminal, test with MCP client
# (Use MCP inspector or custom client)
```

### Integration Test

```bash
# Run integration tests
pytest tests/integration/test_database_mcp_server.py
```

## Error Handling

- Connection errors: Returned as error in response
- Execution errors: Captured from Java executor
- Timeout: 5 minutes per execution
- Invalid parameters: Validation error
- Unsupported database type: ValueError

## Performance

- **Connection Pooling**: Connections stored in memory
- **Result Caching**: Results cached by ID
- **Batch Optimization**: Multiple SQLs executed in single Java process
- **Timeout Management**: 5-minute timeout per execution

## Limitations

- Requires Java 11+ and MyBatis executor
- Temporary files created for parameters
- JSON output parsing depends on Java executor format
- No connection pooling to database (handled by Java)

## Future Enhancements

- [ ] Direct JDBC connection (no Java dependency)
- [ ] Connection pooling
- [ ] Streaming results for large datasets
- [ ] Async execution
- [ ] Result pagination
- [ ] Connection health checks
- [ ] Automatic reconnection
