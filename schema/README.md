# OMA Schema2 - Simplified Migration Pipeline

**Simple, procedural, agent-minimal approach**

## Architecture

```
1. DMS SC Auto-Conversion (95%)
   ↓
2. Manual Object Conversion (5% - Agent-based)
   ↓
3. Drop Constraints
   ↓
4. DMS Full Load (Data)
   ↓
5. Recreate Constraints
```

## Directory Structure

```
schema2/
├── main.py                      # Main orchestrator
├── tools/
│   ├── dms_sc.py               # DMS Schema Conversion
│   ├── manual_converter.py     # Agent-based conversion (failed objects only)
│   ├── constraint_manager.py   # Drop/Recreate constraints
│   ├── dms_load.py             # DMS Full Load
│   ├── oracle_client.py        # Oracle DDL extraction
│   └── postgres_client.py      # PostgreSQL execution
└── README.md

```

## Usage

```bash
cd /home/ec2-user/workspace/oma/schema2
python3.11 main.py
```

## Steps

### Step 1: DMS SC Auto-Conversion
- Read oma.properties for DMS_MIGRATION_PROJECT_ARN
- Execute DMS SC project
- Wait for completion
- Download results from S3
- Create objects in target PostgreSQL

### Step 2: Manual Object Conversion (Agent-based)
- Parse DMS SC assessment report
- Find failed/unsupported objects
- For each failed object:
  - Get Oracle DDL
  - Use LLM agent to convert
  - Execute in PostgreSQL

### Step 3: Drop Constraints
- Query all FK constraints
- Generate DROP statements
- Execute and save for recreation

### Step 4: DMS Full Load
- Create DMS Full Load task
- Wait for ready state
- Start task
- Monitor progress
- Wait for completion

### Step 5: Recreate Constraints
- Execute saved constraint DDLs
- Verify constraint creation

## Key Differences from schema/

- **No multi-agent pipeline**: Single sequential script
- **No graph orchestration**: Simple procedural steps
- **No discovery agent**: DMS SC provides inventory
- **No design gate**: DMS SC creates objects directly
- **Agent only for failures**: 95% auto-converted, 5% agent-converted
