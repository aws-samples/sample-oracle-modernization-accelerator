# SQL Functions to Java Implementation Mapping

This document shows how the PostgreSQL functions provided were translated into Java methods.

## Data Storage

### SQL
```sql
create table tbl_dms_sc_s3_files (
    project_id      uuid,
    zip_file        varchar(255),
    file_path       varchar(255),
    json_content    jsonb,
    upload_ts       timestamp,
    primary key (project_id, file_path)
);
```

### Java
Files are stored in local filesystem:
- Path: `~/.mma-sc/<bucket>/<prefix>/<file_path>`
- JSON content parsed using Jackson `JsonNode`
- Metadata tracked in analysis results

## Server Details Extraction

### SQL
```sql
CREATE OR REPLACE FUNCTION get_server_details(p_project_id UUID DEFAULT NULL)
RETURNS TABLE (
    project_id UUID,
    file_path TEXT,
    server_type TEXT,
    server_name TEXT,
    database_vendor TEXT,
    database_engine TEXT,
    engine_version TEXT,
    upload_ts TIMESTAMP
)
```

### Java
```java
private List<Map<String, Object>> extractServerDetails(Path basePath) throws IOException {
    return Files.walk(basePath)
        .filter(p -> p.toString().matches(".*[/\\\\][st]-server$"))
        .map(this::parseServerFile)
        .filter(Objects::nonNull)
        .collect(Collectors.toList());
}

private Map<String, Object> parseServerFile(Path file) {
    JsonNode server = json.at("/content/0/children/0");
    return Map.of(
        "server_type", file.toString().contains("/t-server") ? "target" : "source",
        "server_name", server.path("name").asText(),
        "vendor", server.at("/server_info/vendorName").asText(),
        "engine", server.at("/server_info/vendorEngine").asText(),
        "version", server.at("/server_info/vendorEngineVersion").asText()
    );
}
```

## Table Mappings

### SQL
```sql
CREATE OR REPLACE FUNCTION get_table_mapping_list(p_project_id UUID)
RETURNS TABLE (
    project_id UUID,
    src_server_type TEXT,
    src_schema_name TEXT,
    src_table_name TEXT,
    trg_server_type TEXT,
    trg_schema_name TEXT,
    trg_table_name TEXT
)
```

### Java
```java
private List<Map<String, Object>> extractTableMappings(Path basePath) throws IOException {
    Map<String, JsonNode> sourceTables = new HashMap<>();
    Map<String, JsonNode> targetTables = new HashMap<>();
    
    // Load source tables
    Files.walk(basePath)
        .filter(p -> p.toString().matches("(?i).*[/\\\\]s-[^/\\\\]+[/\\\\]Schemas\\.[^.]+\\.Tables$"))
        .forEach(p -> loadTables(p, sourceTables));
    
    // Load target tables
    Files.walk(basePath)
        .filter(p -> p.toString().matches("(?i).*[/\\\\]t-[^/\\\\]+[/\\\\]Schemas\\.[^.]+\\.Tables$"))
        .forEach(p -> loadTables(p, targetTables));
    
    return matchMappings(sourceTables, targetTables, "table");
}
```

## Function Mappings

### SQL
```sql
CREATE OR REPLACE FUNCTION get_function_mapping_list(p_project_id UUID)
-- Uses REGEXP_LIKE for pattern matching
AND REGEXP_LIKE(s.file_path, '/s-[^/]+/Schemas\.[^.]+\.Functions$', 'i')
```

### Java
```java
private List<Map<String, Object>> extractFunctionMappings(Path basePath) throws IOException {
    Map<String, JsonNode> sourceFunctions = new HashMap<>();
    Map<String, JsonNode> targetFunctions = new HashMap<>();
    
    Files.walk(basePath)
        .filter(p -> p.toString().matches("(?i).*[/\\\\]s-[^/\\\\]+[/\\\\]Schemas\\.[^.]+\\.Functions$"))
        .forEach(p -> loadObjects(p, sourceFunctions, "function"));
    
    Files.walk(basePath)
        .filter(p -> p.toString().matches("(?i).*[/\\\\]t-[^/\\\\]+[/\\\\]Schemas\\.[^.]+\\.Functions$"))
        .forEach(p -> loadObjects(p, targetFunctions, "function"));
    
    return matchMappings(sourceFunctions, targetFunctions, "function");
}
```

## Procedure Mappings

### SQL
```sql
CREATE OR REPLACE FUNCTION get_procedure_mapping_list(p_project_id UUID)
AND REGEXP_LIKE(s.file_path, '/s-[^/]+/Schemas\.[^.]+\.Procedures$', 'i')
```

### Java
```java
private List<Map<String, Object>> extractProcedureMappings(Path basePath) throws IOException {
    // Similar pattern to functions, but filters for "procedure" type
    Files.walk(basePath)
        .filter(p -> p.toString().matches("(?i).*[/\\\\]s-[^/\\\\]+[/\\\\]Schemas\\.[^.]+\\.Procedures$"))
        .forEach(p -> loadObjects(p, sourceProcedures, "procedure"));
}
```

## Package Procedure Mappings

### SQL
```sql
CREATE OR REPLACE FUNCTION get_pkg_procedure_mapping_list(p_project_id UUID)
WHERE s.file_path LIKE '%/s-%/%.Packages.%!22Public!20procedures!%'
AND s.json_content->'content'->0->>'type' = 'procedure'
```

### Java
```java
private List<Map<String, Object>> extractPkgProcedureMappings(Path basePath) throws IOException {
    return Files.walk(basePath)
        .filter(p -> p.toString().contains("/s-") && 
                    p.toString().contains(".Packages.") && 
                    p.toString().contains("!22Public!20procedures!"))
        .map(this::parsePkgObject)
        .filter(Objects::nonNull)
        .collect(Collectors.toList());
}
```

## Package Function Mappings

### SQL
```sql
CREATE OR REPLACE FUNCTION get_pkg_function_mapping_list(p_project_id UUID)
WHERE s.file_path LIKE '%/s-%/%.Packages.%!22Public!20functions!%'
```

### Java
```java
private List<Map<String, Object>> extractPkgFunctionMappings(Path basePath) throws IOException {
    return Files.walk(basePath)
        .filter(p -> p.toString().contains("/s-") && 
                    p.toString().contains(".Packages.") && 
                    p.toString().contains("!22Public!20functions!"))
        .map(this::parsePkgObject)
        .filter(Objects::nonNull)
        .collect(Collectors.toList());
}
```

## DDL Extraction

### Implementation
```java
private void extractAndSaveDDLs(Path basePath) throws IOException {
    Path sourceDdlDir = basePath.resolve("ddl/source");
    Path targetDdlDir = basePath.resolve("ddl/target");
    Files.createDirectories(sourceDdlDir);
    Files.createDirectories(targetDdlDir);
    
    Files.walk(basePath)
        .filter(p -> p.toString().endsWith(".json") || p.toString().matches(".*[^.]+$"))
        .forEach(p -> extractDDL(p, sourceDdlDir, targetDdlDir));
}

private void extractDDL(Path file, Path sourceDdlDir, Path targetDdlDir) {
    JsonNode content = json.at("/content/0");
    String ddl = content.path("ddl").asText();
    
    boolean isSource = file.toString().contains("/s-");
    Path ddlDir = isSource ? sourceDdlDir : targetDdlDir;
    String filename = String.format("%s_%s_%s.sql", schema, type, name)
                        .replaceAll("[^a-zA-Z0-9_.-]", "_");
    
    Files.writeString(ddlDir.resolve(filename), ddl);
}
```

## Key Differences

1. **Storage**: SQL uses PostgreSQL JSONB, Java uses local filesystem + Jackson
2. **Pattern Matching**: SQL uses `REGEXP_LIKE`, Java uses `String.matches()` with regex
3. **JSON Navigation**: SQL uses `->` and `->>`, Java uses Jackson's `at()` and `path()`
4. **Filtering**: SQL uses `WHERE` clauses, Java uses Stream `filter()`
5. **Joining**: SQL uses `LEFT JOIN`, Java uses `HashMap` lookups with `synchronization_object` keys

## Benefits of Java Implementation

- **No database required**: Files stored locally, easier to distribute
- **Portable**: Works anywhere Java 21+ is available
- **MCP integration**: Direct integration with Q CLI
- **File-based**: Easy to inspect and debug intermediate results
- **DDL extraction**: Automatically saves DDL scripts for review
