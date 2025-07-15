# Environment Context

## Application Information
- **Application Name**: `$APPLICATION_NAME`
- **Source DBMS**: `$SOURCE_DBMS_TYPE`
- **Target DBMS**: `$TARGET_DBMS_TYPE`

## Key Directory Paths
- **Application Folder**: `$APPLICATION_FOLDER`
- **Java Source Folder**: `$JAVA_SOURCE_FOLDER`
- **Transform Folder**: `$APP_TRANSFORM_FOLDER`
- **Test Folder**: `$TEST_FOLDER`
- **Tools Folder**: `$APP_TOOLS_FOLDER`
- **Temp Directory**: `/tmp`

## Database Configuration
### Source Database
- Host: `$ORACLE_HOST`
- Port: `$ORACLE_PORT`
- SID: `$ORACLE_SID`
- Service User: `$ORACLE_SVC_USER`
- Admin User: `$ORACLE_ADM_USER`
- Connect String: `$ORACLE_SVC_CONNECT_STRING`
- Password: Use `$ORACLE_SVC_PASSWORD` or `$ORACLE_ADM_PASSWORD`

### Target Database
- Type: `$TARGET_DBMS_TYPE`
- MySQL: Host `$MYSQL_HOST`, Port `$MYSQL_TCP_PORT`, Service User: `$MYSQL_SVC_USER`, Admin User: `$MYSQL_ADM_USER`, Password: Use `$MYSQL_SVC_PASSWORD` or `$MYSQL_ADM_PASSWORD`
- PostgreSQL: Host `$POSTGRES_HOST`, Port `$POSTGRES_PORT`, Service User: `$POSTGRES_SVC_USER`, Admin User: `$POSTGRES_ADM_USER`, Password: Use `$POSTGRES_SVC_PASSWORD` or `$POSTGRES_ADM_PASSWORD` (when applicable)

## SQL Mapper Folders
- **Source SQL Mapper**: `$SOURCE_SQL_MAPPER_FOLDER`
- **Target SQL Mapper**: `$TARGET_SQL_MAPPER_FOLDER`

## Logging
- **Application Logs**: `$APP_LOGS_FOLDER`
- **Test Logs**: `$TEST_LOGS_FOLDER`

## Principles
1. Use currently configured environment variables for required settings
2. Create new Output Directory if it doesn't exist
3. **Write all temporary files to `/tmp`** - unless explicitly specified otherwise
4. Database connection information is configured in environment variables
5. Available database clients: `sqlplus`, `psql`, `mysql`
6. Oracle service users: `$ORACLE_SVC_USER_LIST`
7. Always retrieve database passwords from environment variables when needed
