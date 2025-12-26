# DMS Schema Conversion Analysis Summary

## Complete Object Mappings

### ✅ Fully Mapped Objects (Source → Target)

| Object Type | Count | Status |
|------------|-------|--------|
| **Tables** | 17 | ✅ All mapped |
| **Functions** | 9 | ✅ All mapped |
| **Procedures** | 8 | ✅ All mapped |
| **Package Procedures** | 11 | ✅ All mapped |
| **Package Functions** | 5 | ✅ All mapped |

### ⚠️ Unmapped Objects (Source Only - Target = NULL)

| Object Type | Count | Status |
|------------|-------|--------|
| **Materialized Views** | 4 | ⚠️ No target mapping |
| **Synonyms** | 1 | ⚠️ No target mapping |
| **Views** | 0 | N/A |

## Unmapped Objects Detail

### Materialized Views (4)
- `DEMO.MV_BOOK_SALES_ANALYTICS` → NULL
- `DEMO.MV_BOOK_INVENTORY_STATUS` → NULL
- `DEMO.MV_CUSTOMER_SHOPPING_PATTERNS` → NULL
- `DEMO.MV_BESTSELLERS` → NULL

### Synonyms (1)
- `DEMO.REMOTE_BOOKS` → NULL

## Analysis Results Structure

```json
{
  "servers": [
    {
      "server_type": "source",
      "server_name": "oracle-source",
      "vendor": "Oracle",
      "engine": "Oracle",
      "version": "19c"
    },
    {
      "server_type": "target",
      "server_name": "postgres-target",
      "vendor": "PostgreSQL",
      "engine": "PostgreSQL",
      "version": "15.3"
    }
  ],
  "table_mappings": [
    {
      "src_schema": "DEMO",
      "src_name": "ORDERS",
      "trg_schema": "demo",
      "trg_name": "orders"
    },
    ...
  ],
  "mview_mappings": [
    {
      "src_schema": "DEMO",
      "src_name": "MV_BESTSELLERS",
      "trg_schema": null,
      "trg_name": null
    },
    ...
  ]
}
```

## Object Type Coverage

### Extracted Object Types
- ✅ Tables
- ✅ Views
- ✅ Materialized Views
- ✅ Functions (standalone)
- ✅ Procedures (standalone)
- ✅ Package Functions
- ✅ Package Procedures
- ✅ Synonyms

### Not Extracted (Not in Project)
- Sequences (0 found)
- Triggers (not implemented)
- Indexes (not implemented)
- Constraints (not implemented)

## DDL Files Generated

- **Source DDLs**: 116 files
- **Target DDLs**: 130 files
- **Total**: 246 SQL files
- **NULL files**: 0 (all valid)

## Usage

### Load Analysis Results
```javascript
load_analysis_results("~/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project")
```

Returns all mappings including objects with NULL targets.

### Query Specific Mappings
```javascript
// Get all table mappings
analysis.table_mappings

// Get unmapped materialized views
analysis.mview_mappings.filter(m => m.trg_name === null)

// Get all mapped functions
analysis.function_mappings.filter(m => m.trg_name !== null)
```

## Migration Considerations

### Objects Requiring Manual Conversion

1. **Materialized Views (4)**
   - Oracle materialized views don't have direct PostgreSQL equivalents
   - May need to be converted to regular views or tables with refresh logic

2. **Synonyms (1)**
   - PostgreSQL doesn't support synonyms
   - May need to use views or schema search paths

### Successfully Mapped Objects

All other objects (50 total) have been successfully mapped:
- 17 tables
- 9 functions
- 8 procedures
- 11 package procedures
- 5 package functions

## File Locations

```
~/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project/
├── analysis_results.json          # Complete analysis (8.7KB)
├── ddl/
│   ├── source/                    # 116 Oracle DDL files
│   └── target/                    # 130 PostgreSQL DDL files
├── s-6HVMW5MQ5BCVJCWGMUJOYAS6OQ/  # Source metadata
└── t-YQRENWSQSRAJRFLWHGVX4NGDKM/  # Target metadata
```
