# Report Filtering Examples

## Overview

The `report_dms_sc_project` tool supports flexible filtering with up to 4 parameters:

1. **s3Path** (required): S3 path to project
2. **objectType** (optional): Filter by object type
3. **schemaName** (optional): Filter by source schema
4. **objectName** (optional): Filter by source object name

All filters are **case-insensitive**.

## Usage Patterns

### 1. All Mappings (No Filter)

```javascript
report_dms_sc_project("s3://bucket/prefix/")
```

Returns all 8 mapping types:
- table_mappings: 17 items
- function_mappings: 9 items
- procedure_mappings: 8 items
- mview_mappings: 4 items
- pkg_procedure_mappings: 11 items
- pkg_function_mappings: 5 items
- synonym_mappings: 1 item
- view_mappings: 0 items

### 2. Filter by Object Type

```javascript
// Tables only
report_dms_sc_project("s3://bucket/prefix/", "table")
// Returns: table_mappings: 17 items

// Materialized views only
report_dms_sc_project("s3://bucket/prefix/", "mview")
// Returns: mview_mappings: 4 items

// Functions only
report_dms_sc_project("s3://bucket/prefix/", "function")
// Returns: function_mappings: 9 items
```

**Supported Types:**
- `table`
- `view`
- `mview` (materialized views)
- `function`
- `procedure`
- `synonym`
- `pkg_function` (package functions)
- `pkg_procedure` (package procedures)

### 3. Filter by Type + Schema

```javascript
// All tables in DEMO schema
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO")
// Returns: table_mappings: 17 items (all in DEMO)

// All functions in DEMO schema
report_dms_sc_project("s3://bucket/prefix/", "function", "DEMO")
// Returns: function_mappings: 9 items
```

### 4. Filter by Type + Schema + Name

```javascript
// Specific table
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO", "ORDERS")
// Returns: table_mappings: 1 item
// {
//   "src_schema": "DEMO",
//   "src_name": "ORDERS",
//   "trg_schema": "demo",
//   "trg_name": "orders"
// }

// Specific function
report_dms_sc_project("s3://bucket/prefix/", "function", "DEMO", "GET_BOOK_STATUS_BY_YEAR")
// Returns: function_mappings: 1 item
```

### 5. Case Insensitive

All parameters are case-insensitive:

```javascript
// These are all equivalent:
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO", "ORDERS")
report_dms_sc_project("s3://bucket/prefix/", "TABLE", "demo", "orders")
report_dms_sc_project("s3://bucket/prefix/", "Table", "Demo", "Orders")
```

## CLI Examples

```bash
# All mappings
./test.sh report s3://bucket/prefix/

# By type
./test.sh report s3://bucket/prefix/ table
./test.sh report s3://bucket/prefix/ mview
./test.sh report s3://bucket/prefix/ function

# By type + schema
./test.sh report s3://bucket/prefix/ table DEMO
./test.sh report s3://bucket/prefix/ function DEMO

# By type + schema + name
./test.sh report s3://bucket/prefix/ table DEMO ORDERS
./test.sh report s3://bucket/prefix/ function DEMO GET_BOOK_STATUS_BY_YEAR

# Case insensitive
./test.sh report s3://bucket/prefix/ TABLE demo orders
```

## Use Cases

### Find All Unmapped Objects

```javascript
// Get materialized views (often unmapped)
report_dms_sc_project("s3://bucket/prefix/", "mview")
// Check for trg_name: null

// Get synonyms (often unmapped)
report_dms_sc_project("s3://bucket/prefix/", "synonym")
```

### Schema-Specific Analysis

```javascript
// All objects in specific schema
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO")
report_dms_sc_project("s3://bucket/prefix/", "function", "DEMO")
report_dms_sc_project("s3://bucket/prefix/", "procedure", "DEMO")
```

### Object-Specific Lookup

```javascript
// Find specific object mapping
report_dms_sc_project("s3://bucket/prefix/", "table", "DEMO", "ORDERS")
// Quick lookup of source → target mapping
```

## Response Format

Filtered responses always include:
- `success`: true/false
- `local_base`: Local cache path
- `analysis_file`: Path to analysis JSON
- `<type>_mappings`: Filtered mapping array

Example:
```json
{
  "success": true,
  "local_base": "/Users/user/.mma-sc/bucket/prefix",
  "analysis_file": "/Users/user/.mma-sc/bucket/prefix/analysis_results.json",
  "table_mappings": [
    {
      "src_schema": "DEMO",
      "src_name": "ORDERS",
      "trg_schema": "demo",
      "trg_name": "orders"
    }
  ]
}
```
