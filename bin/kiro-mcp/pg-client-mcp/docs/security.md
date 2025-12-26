### 1. Proposed mcp user

```sql
-- Create the user
CREATE USER mcp_pg WITH PASSWORD 'password';

-- Grant connect privilege
GRANT CONNECT ON DATABASE demodb TO mcp_pg;

-- Grant optional privileges to ease monitoring
GRANT pg_monitor TO mcp_pg;

-- Grant schema usage and creation
GRANT USAGE, CREATE ON SCHEMA public TO mcp_pg;
-- Grant all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mcp_pg;
-- Grant all privileges on all existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mcp_pg;
-- Grant all privileges on all existing functions
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO mcp_pg;

-- Grant schema usage and creation
GRANT USAGE, CREATE ON SCHEMA demo TO mcp_pg;
-- Grant all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA demo TO mcp_pg;
-- Grant all privileges on all existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA demo TO mcp_pg;
-- Grant all privileges on all existing functions
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA demo TO mcp_pg;


-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO mcp_pg;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO mcp_pg;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO mcp_pg;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA demo GRANT ALL PRIVILEGES ON TABLES TO mcp_pg;
ALTER DEFAULT PRIVILEGES IN SCHEMA demo GRANT ALL PRIVILEGES ON SEQUENCES TO mcp_pg;
ALTER DEFAULT PRIVILEGES IN SCHEMA demo GRANT ALL PRIVILEGES ON FUNCTIONS TO mcp_pg;
```