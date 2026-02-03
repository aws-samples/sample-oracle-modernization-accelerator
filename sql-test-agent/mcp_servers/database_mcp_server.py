#!/usr/bin/env python3
"""
Unified Database MCP Server

Provides MCP tools for all database operations (Oracle, PostgreSQL, MySQL).
Single server handles all database types with unified interface.
"""

import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from utils.logger import get_logger

logger = get_logger(__name__)

# Global connection pool
_connections: Dict[str, Dict[str, Any]] = {}

# Global result cache
_results_cache: Dict[str, Dict[str, Any]] = {}


class DatabaseMCPServer:
    """Unified Database MCP Server for Oracle, PostgreSQL, and MySQL."""
    
    # Database type mapping for Java executor
    DB_TYPE_MAP = {
        "oracle": "oracle",
        "postgresql": "postgres",
        "mysql": "mysql"
    }
    
    def __init__(self):
        self.server = Server("database-mcp-server")
        self.logger = get_logger(__name__)
        self.java_executor_path = self._find_java_executor()
        
        # Register tools
        self._register_tools()
    
    def _find_java_executor(self) -> Path:
        """Find Java executor path."""
        executor_path = os.getenv("JAVA_EXECUTOR_PATH")
        if executor_path:
            return Path(executor_path)
        
        # Default to bin/test directory
        default_path = Path(__file__).parent.parent.parent / "bin" / "test"
        if default_path.exists():
            return default_path
        
        raise RuntimeError("Java executor not found. Set JAVA_EXECUTOR_PATH environment variable.")
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="connect",
                    description="Create database connection (Oracle, PostgreSQL, or MySQL)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "db_type": {
                                "type": "string",
                                "enum": ["oracle", "postgresql", "mysql"],
                                "description": "Database type"
                            },
                            "credentials": {
                                "type": "object",
                                "description": "Database credentials (structure varies by db_type)",
                                "properties": {
                                    # Oracle
                                    "username": {"type": "string"},
                                    "password": {"type": "string"},
                                    "connect_string": {"type": "string", "description": "Oracle: host:port:sid or TNS name"},
                                    # PostgreSQL/MySQL
                                    "host": {"type": "string"},
                                    "port": {"type": "integer"},
                                    "database": {"type": "string"}
                                }
                            }
                        },
                        "required": ["db_type", "credentials"]
                    }
                ),
                Tool(
                    name="disconnect",
                    description="Close database connection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "Connection identifier"},
                        },
                        "required": ["connection_id"]
                    }
                ),
                Tool(
                    name="test_connection",
                    description="Test database connection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "Connection identifier"},
                        },
                        "required": ["connection_id"]
                    }
                ),
                Tool(
                    name="execute_sql",
                    description="Execute individual SQL from MyBatis mapper",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "Connection identifier"},
                            "sql_id": {"type": "string", "description": "SQL ID (e.g., 'UserMapper.selectUser')"},
                            "mapper_file": {"type": "string", "description": "Path to MyBatis XML file"},
                            "bind_variables": {"type": "object", "description": "Bind variables as key-value pairs"},
                            "sql_type": {"type": "string", "description": "SQL type filter (SELECT, INSERT, UPDATE, DELETE)", "default": "SELECT"},
                        },
                        "required": ["connection_id", "sql_id", "mapper_file", "bind_variables"]
                    }
                ),
                Tool(
                    name="execute_sql_batch",
                    description="Execute multiple SQLs in batch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "Connection identifier"},
                            "sql_list": {
                                "type": "array",
                                "description": "List of SQLs to execute",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "sql_id": {"type": "string"},
                                        "mapper_file": {"type": "string"}
                                    }
                                }
                            },
                            "bind_variables": {"type": "object", "description": "Common bind variables"},
                            "sql_type": {"type": "string", "description": "SQL type filter", "default": "SELECT"},
                        },
                        "required": ["connection_id", "sql_list", "bind_variables"]
                    }
                ),
                Tool(
                    name="execute_mapper_file",
                    description="Execute all SQLs in a MyBatis mapper file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "Connection identifier"},
                            "mapper_file": {"type": "string", "description": "Path to MyBatis XML file"},
                            "bind_variables": {"type": "object", "description": "Bind variables"},
                            "sql_type": {"type": "string", "description": "SQL type filter", "default": "SELECT"},
                        },
                        "required": ["connection_id", "mapper_file", "bind_variables"]
                    }
                ),
                Tool(
                    name="get_mapper_sql_list",
                    description="Get list of SQLs in a mapper file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mapper_file": {"type": "string", "description": "Path to MyBatis XML file"},
                        },
                        "required": ["mapper_file"]
                    }
                ),
                Tool(
                    name="get_execution_result",
                    description="Retrieve cached execution result",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "result_id": {"type": "string", "description": "Result identifier"},
                        },
                        "required": ["result_id"]
                    }
                ),
                Tool(
                    name="list_connections",
                    description="List all active connections",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "connect":
                    result = await self._connect(arguments)
                elif name == "disconnect":
                    result = await self._disconnect(arguments)
                elif name == "test_connection":
                    result = await self._test_connection(arguments)
                elif name == "execute_sql":
                    result = await self._execute_sql(arguments)
                elif name == "execute_sql_batch":
                    result = await self._execute_sql_batch(arguments)
                elif name == "execute_mapper_file":
                    result = await self._execute_mapper_file(arguments)
                elif name == "get_mapper_sql_list":
                    result = await self._get_mapper_sql_list(arguments)
                elif name == "get_execution_result":
                    result = await self._get_execution_result(arguments)
                elif name == "list_connections":
                    result = await self._list_connections(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            except Exception as e:
                self.logger.error(f"Tool execution failed: {name}", error=str(e))
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e), "tool": name}, indent=2)
                )]
    
    async def _connect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create database connection."""
        db_type = args["db_type"]
        credentials = args["credentials"]
        
        if db_type not in self.DB_TYPE_MAP:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        connection_id = str(uuid.uuid4())
        
        connection_info = {
            "connection_id": connection_id,
            "db_type": db_type,
            "credentials": credentials,
            "created_at": datetime.now().isoformat(),
        }
        
        # Validate credentials based on db_type
        self._validate_credentials(db_type, credentials)
        
        _connections[connection_id] = connection_info
        
        self.logger.info(
            "database_connection_created",
            connection_id=connection_id,
            db_type=db_type,
            username=credentials.get("username")
        )
        
        return {
            "connection_id": connection_id,
            "status": "connected",
            "db_type": db_type,
            "username": credentials.get("username")
        }
    
    async def _disconnect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Close database connection."""
        connection_id = args["connection_id"]
        
        if connection_id in _connections:
            connection = _connections[connection_id]
            del _connections[connection_id]
            self.logger.info(
                "database_connection_closed",
                connection_id=connection_id,
                db_type=connection["db_type"]
            )
            return {"status": "disconnected", "connection_id": connection_id}
        else:
            raise ValueError(f"Connection not found: {connection_id}")
    
    async def _test_connection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Test database connection."""
        connection_id = args["connection_id"]
        
        if connection_id not in _connections:
            raise ValueError(f"Connection not found: {connection_id}")
        
        connection = _connections[connection_id]
        
        # Simple test - connection exists and has valid credentials
        return {
            "connection_id": connection_id,
            "status": "active",
            "db_type": connection["db_type"],
            "created_at": connection["created_at"]
        }
    
    async def _execute_sql(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute individual SQL."""
        connection_id = args["connection_id"]
        sql_id = args["sql_id"]
        mapper_file = args["mapper_file"]
        bind_variables = args["bind_variables"]
        sql_type = args.get("sql_type", "SELECT")
        
        if connection_id not in _connections:
            raise ValueError(f"Connection not found: {connection_id}")
        
        connection = _connections[connection_id]
        
        self.logger.info(
            "executing_sql",
            connection_id=connection_id,
            db_type=connection["db_type"],
            sql_id=sql_id,
            mapper_file=mapper_file
        )
        
        # Execute via Java
        result = self._execute_via_java(
            connection=connection,
            mapper_file=mapper_file,
            bind_variables=bind_variables,
            sql_id_filter=sql_id,
            sql_type=sql_type
        )
        
        # Cache result
        result_id = str(uuid.uuid4())
        _results_cache[result_id] = result
        result["result_id"] = result_id
        
        return result
    
    async def _execute_sql_batch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple SQLs in batch."""
        connection_id = args["connection_id"]
        sql_list = args["sql_list"]
        bind_variables = args["bind_variables"]
        sql_type = args.get("sql_type", "SELECT")
        
        if connection_id not in _connections:
            raise ValueError(f"Connection not found: {connection_id}")
        
        connection = _connections[connection_id]
        
        self.logger.info(
            "executing_sql_batch",
            connection_id=connection_id,
            db_type=connection["db_type"],
            sql_count=len(sql_list)
        )
        
        results = []
        for sql_item in sql_list:
            try:
                result = self._execute_via_java(
                    connection=connection,
                    mapper_file=sql_item["mapper_file"],
                    bind_variables=bind_variables,
                    sql_id_filter=sql_item["sql_id"],
                    sql_type=sql_type
                )
                results.append(result)
            except Exception as e:
                self.logger.error(
                    "batch_sql_failed",
                    sql_id=sql_item["sql_id"],
                    error=str(e)
                )
                results.append({
                    "sql_id": sql_item["sql_id"],
                    "status": "error",
                    "error_message": str(e)
                })
        
        return {
            "total": len(sql_list),
            "success": sum(1 for r in results if r.get("status") == "success"),
            "failed": sum(1 for r in results if r.get("status") == "error"),
            "results": results
        }
    
    async def _execute_mapper_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all SQLs in a mapper file."""
        connection_id = args["connection_id"]
        mapper_file = args["mapper_file"]
        bind_variables = args["bind_variables"]
        sql_type = args.get("sql_type", "SELECT")
        
        if connection_id not in _connections:
            raise ValueError(f"Connection not found: {connection_id}")
        
        connection = _connections[connection_id]
        
        self.logger.info(
            "executing_mapper_file",
            connection_id=connection_id,
            db_type=connection["db_type"],
            mapper_file=mapper_file
        )
        
        # Execute entire mapper file via Java
        result = self._execute_via_java(
            connection=connection,
            mapper_file=mapper_file,
            bind_variables=bind_variables,
            sql_id_filter=None,  # Execute all
            sql_type=sql_type
        )
        
        return result
    
    async def _get_mapper_sql_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of SQLs in a mapper file."""
        mapper_file = args["mapper_file"]
        
        # Parse XML to extract SQL IDs
        sql_list = self._parse_mapper_file(mapper_file)
        
        return {
            "mapper_file": mapper_file,
            "sql_count": len(sql_list),
            "sql_list": sql_list
        }
    
    async def _get_execution_result(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve cached execution result."""
        result_id = args["result_id"]
        
        if result_id in _results_cache:
            return _results_cache[result_id]
        else:
            raise ValueError(f"Result not found: {result_id}")
    
    async def _list_connections(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all active connections."""
        connections = []
        for conn_id, conn_info in _connections.items():
            connections.append({
                "connection_id": conn_id,
                "db_type": conn_info["db_type"],
                "username": conn_info["credentials"].get("username"),
                "created_at": conn_info["created_at"]
            })
        
        return {
            "total_connections": len(connections),
            "connections": connections
        }
    
    def _validate_credentials(self, db_type: str, credentials: Dict[str, Any]):
        """Validate credentials based on database type."""
        if db_type == "oracle":
            required = ["username", "password", "connect_string"]
            missing = [f for f in required if f not in credentials]
            if missing:
                raise ValueError(f"Missing Oracle credentials: {', '.join(missing)}")
        
        elif db_type in ["postgresql", "mysql"]:
            required = ["username", "password", "database"]
            missing = [f for f in required if f not in credentials]
            if missing:
                raise ValueError(f"Missing {db_type} credentials: {', '.join(missing)}")
    
    def _execute_via_java(
        self,
        connection: Dict[str, Any],
        mapper_file: str,
        bind_variables: Dict[str, Any],
        sql_id_filter: Optional[str] = None,
        sql_type: str = "SELECT"
    ) -> Dict[str, Any]:
        """Execute SQL via Java MyBatis executor."""
        
        db_type = connection["db_type"]
        credentials = connection["credentials"]
        
        # Create temporary parameters file
        params_file = self._create_params_file(bind_variables)
        
        try:
            # Set environment variables based on db_type
            env = os.environ.copy()
            env = self._set_db_env_vars(env, db_type, credentials)
            
            # Build command
            java_db_type = self.DB_TYPE_MAP[db_type]
            cmd = [
                "java",
                "-cp", ".:lib/*",
                "com.test.mybatis.MyBatisBulkExecutorWithJson",
                mapper_file,
                "--db", java_db_type,
                "--json",
                "--select-only" if sql_type == "SELECT" else "--all"
            ]
            
            if sql_id_filter:
                cmd.extend(["--sql-id", sql_id_filter])
            
            # Execute
            self.logger.debug("executing_java_command", cmd=" ".join(cmd))
            
            result = subprocess.run(
                cmd,
                cwd=str(self.java_executor_path),
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Java execution failed: {result.stderr}")
            
            # Parse JSON output
            output_file = self._find_latest_json_output()
            if output_file:
                with open(output_file, 'r') as f:
                    return json.load(f)
            else:
                # Parse stdout
                return self._parse_java_output(result.stdout)
        
        finally:
            # Cleanup temp file
            if params_file.exists():
                params_file.unlink()
    
    def _set_db_env_vars(self, env: Dict[str, str], db_type: str, credentials: Dict[str, Any]) -> Dict[str, str]:
        """Set database-specific environment variables."""
        if db_type == "oracle":
            env["ORACLE_SVC_USER"] = credentials["username"]
            env["ORACLE_SVC_PASSWORD"] = credentials["password"]
            env["ORACLE_SVC_CONNECT_STRING"] = credentials["connect_string"]
        
        elif db_type == "postgresql":
            env["PGUSER"] = credentials["username"]
            env["PGPASSWORD"] = credentials["password"]
            env["PGHOST"] = credentials.get("host", "localhost")
            env["PGPORT"] = str(credentials.get("port", 5432))
            env["PGDATABASE"] = credentials["database"]
            env["TARGET_DBMS_TYPE"] = "postgresql"
        
        elif db_type == "mysql":
            env["MYSQL_USER"] = credentials["username"]
            env["MYSQL_PASSWORD"] = credentials["password"]
            env["MYSQL_HOST"] = credentials.get("host", "localhost")
            env["MYSQL_TCP_PORT"] = str(credentials.get("port", 3306))
            env["MYSQL_DATABASE"] = credentials["database"]
            env["TARGET_DBMS_TYPE"] = "mysql"
        
        return env
    
    def _create_params_file(self, bind_variables: Dict[str, Any]) -> Path:
        """Create temporary parameters.properties file."""
        temp_file = Path(tempfile.mktemp(suffix=".properties"))
        
        with open(temp_file, 'w') as f:
            for key, value in bind_variables.items():
                f.write(f"{key}={value}\n")
        
        return temp_file
    
    def _find_latest_json_output(self) -> Optional[Path]:
        """Find latest JSON output file."""
        out_dir = self.java_executor_path / "out"
        if not out_dir.exists():
            return None
        
        json_files = list(out_dir.glob("bulk_test_result_*.json"))
        if not json_files:
            return None
        
        # Return most recent
        return max(json_files, key=lambda p: p.stat().st_mtime)
    
    def _parse_java_output(self, output: str) -> Dict[str, Any]:
        """Parse Java stdout output."""
        lines = output.split('\n')
        
        result = {
            "status": "success",
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        # Extract statistics
        for line in lines:
            if "Total Executed:" in line:
                result["total"] = int(line.split(':')[1].strip())
            elif "Success:" in line:
                parts = line.split(':')[1].strip().split()
                result["success"] = int(parts[0])
            elif "Failed:" in line:
                parts = line.split(':')[1].strip().split()
                result["failed"] = int(parts[0])
        
        return result
    
    def _parse_mapper_file(self, mapper_file: str) -> List[Dict[str, Any]]:
        """Parse MyBatis mapper XML to extract SQL list."""
        from lxml import etree
        
        tree = etree.parse(mapper_file)
        root = tree.getroot()
        
        sql_list = []
        
        # Find all SQL statements
        for element in root:
            if element.tag in ['select', 'insert', 'update', 'delete']:
                sql_id = element.get('id')
                sql_type = element.tag.upper()
                
                # Extract parameters
                parameters = []
                sql_text = etree.tostring(element, encoding='unicode', method='text')
                
                # Simple parameter extraction (#{param} and ${param})
                import re
                param_pattern = r'[#$]\{(\w+)\}'
                parameters = list(set(re.findall(param_pattern, sql_text)))
                
                sql_list.append({
                    "sql_id": sql_id,
                    "sql_type": sql_type,
                    "parameters": parameters
                })
        
        return sql_list
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    server = DatabaseMCPServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
