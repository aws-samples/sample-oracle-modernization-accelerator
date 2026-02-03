# SQL Test Agent

An autonomous system that validates SQL conversion accuracy between Oracle and PostgreSQL/MySQL databases.

## Features

- 🔄 **Automated SQL Testing**: Execute and compare SQL queries across multiple databases
- 🤖 **AI-Powered Analysis**: LLM-based difference analysis and transformation guidance
- 🔁 **Automatic Retry**: Intelligent retry logic with convergence detection
- 📊 **Comprehensive Reports**: Detailed validation reports with transformation history
- 🔒 **Secure**: Credential management and sanitized logging
- ⚡ **Performance**: Connection pooling, parallel execution, and result caching

## Architecture

The system consists of three main layers:

1. **Agent Layer**: Orchestrator, LLM Analyzer, Configuration Manager, Result Comparator
2. **MCP Server Layer**: Database MCP Server, Transformer MCP Server
3. **External Tools**: SQL Transformation Agent (bin/application wrapper)

See [architecture diagrams](../.kiro/specs/sql-test-agent/diagrams.html) for detailed visualization.

## Prerequisites

- Python 3.9+
- Java 11+ (for SQL Transformer)
- JDBC drivers (Oracle, PostgreSQL, MySQL)
- Access to LLM API (Claude or GPT)
- Database credentials and network access

## Installation

### 1. Clone and Setup

```bash
cd sql-test-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example configuration
cp config/.env.example config/.env

# Edit configuration with your credentials
nano config/.env
```

### 3. Configure Databases

Set up your database connection parameters in `config/.env`:

```bash
# Oracle
ORACLE_SVC_USER=your_username
ORACLE_SVC_PASSWORD=your_password
ORACLE_SVC_CONNECT_STRING=host:port:sid

# PostgreSQL
PGUSER=your_username
PGPASSWORD=your_password
PGHOST=localhost
PGPORT=5432
PGDATABASE=your_database

# MySQL
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_TCP_PORT=3306
MYSQL_DATABASE=your_database
```

### 4. Configure LLM API

```bash
# For Anthropic Claude
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key
LLM_MODEL=claude-3-5-sonnet-20241022

# Or for OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
LLM_MODEL=gpt-4-turbo-preview
```

## Usage

### 1. Prepare Bind Variables

First, generate bind variables using the existing tools:

```bash
cd ../bin/test

# Extract parameters with DB sample values
./bulk_prepare.sh /path/to/mapper

# Or use bind variable generator
./run_bind_generator.sh /path/to/mapper
```

### 2. Run SQL Test Agent

```bash
cd sql-test-agent

# Run with default configuration
python -m agent.orchestrator

# Run with custom config
python -m agent.orchestrator --config config/agent_config.properties

# Run with specific mapper directory
python -m agent.orchestrator --mapper-dir /path/to/mappers

# Run in verbose mode
python -m agent.orchestrator --verbose
```

### 3. View Reports

Reports are generated in the `reports/` directory:

```bash
# View latest report
open reports/validation_report_latest.html

# View JSON report
cat reports/validation_report_latest.json
```

## Configuration

### Agent Configuration

Edit `config/agent_config.properties`:

```properties
# Retry Configuration
max.retries=3
min.confidence.threshold=0.7

# Comparison Configuration
acceptable.pass.rate=0.95
normalize.numeric.precision=true

# Execution Configuration
batch.size=10
connection.pool.size=5
```

### MCP Server Configuration

Edit `config/mcp_config.json` to configure MCP servers:

```json
{
  "mcpServers": {
    "sql-test-database": {
      "command": "python",
      "args": ["mcp_servers/database_server.py"]
    }
  }
}
```

## Project Structure

```
sql-test-agent/
├── agent/                  # Agent components
│   ├── orchestrator.py     # Main workflow controller
│   ├── llm_analyzer.py     # LLM-based analysis
│   ├── config_manager.py   # Configuration management
│   └── result_comparator.py # Result comparison
├── mcp_servers/            # MCP servers
│   ├── database_server.py  # Database operations
│   └── transformer_server.py # SQL transformation
├── models/                 # Data models
│   ├── data_models.py      # Core data structures
│   └── enums.py            # Enumerations
├── utils/                  # Utilities
│   ├── logger.py           # Logging
│   ├── error_handler.py    # Error handling
│   └── performance_monitor.py # Performance tracking
├── tests/                  # Test suites
├── config/                 # Configuration files
├── logs/                   # Log files
└── reports/                # Validation reports
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agent --cov=mcp_servers --cov=utils

# Run specific test
pytest tests/unit/test_config_manager.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy agent/ mcp_servers/ utils/
```

## Troubleshooting

### Database Connection Issues

```bash
# Test Oracle connection
python -c "import cx_Oracle; print('Oracle driver OK')"

# Test PostgreSQL connection
python -c "import psycopg2; print('PostgreSQL driver OK')"

# Test MySQL connection
python -c "import mysql.connector; print('MySQL driver OK')"
```

### LLM API Issues

```bash
# Test Anthropic API
python -c "import anthropic; client = anthropic.Anthropic(); print('Anthropic OK')"

# Test OpenAI API
python -c "import openai; client = openai.OpenAI(); print('OpenAI OK')"
```

### Common Errors

**Error: Missing parameters.properties**
- Run `bulk_prepare.sh` or `run_bind_generator.sh` first

**Error: Database connection timeout**
- Check network connectivity
- Verify credentials in `.env`
- Check firewall settings

**Error: LLM rate limit exceeded**
- Reduce batch size in config
- Add delays between requests
- Check API quota

## Documentation

- [Requirements](../.kiro/specs/sql-test-agent/requirements.md)
- [Design](../.kiro/specs/sql-test-agent/design.md)
- [Architecture Diagrams](../.kiro/specs/sql-test-agent/diagrams.html)
- [Implementation Plan](../.kiro/specs/sql-test-agent/implementation-plan.md)

## License

See [LICENSES.md](../LICENSES.md)

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md)
