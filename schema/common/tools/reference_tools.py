"""
Oracle-to-PostgreSQL Conversion Reference Tools

Provides agents with on-demand access to conversion rules, data type mappings,
function mappings, DDL patterns, and AWS best practices for Oracle→PostgreSQL migration.

These rules are distilled from:
- OMA postgreRules.md (SQL transformation rules)
- OMA ora_to_pg_prompt.md (DDL conversion rules)
- AWS DMS Oracle to Aurora PostgreSQL Migration Playbook
- AWS SCT conversion patterns
"""

import json
from strands import tool


# ---------------------------------------------------------------------------
# Reference data: Oracle→PostgreSQL conversion knowledge base
# ---------------------------------------------------------------------------

_DATA_TYPE_MAP = {
    "NUMBER": "INTEGER (whole numbers) or NUMERIC(p,s) (decimals)",
    "NUMBER(p)": "INTEGER (p<=9), BIGINT (p<=18), NUMERIC(p) (p>18)",
    "NUMBER(p,s)": "NUMERIC(p,s)",
    "VARCHAR2(n)": "VARCHAR(n)",
    "NVARCHAR2(n)": "VARCHAR(n)",
    "CHAR(n)": "CHAR(n)",
    "NCHAR(n)": "CHAR(n)",
    "CLOB": "TEXT",
    "NCLOB": "TEXT",
    "BLOB": "BYTEA",
    "RAW(n)": "BYTEA",
    "LONG": "TEXT",
    "LONG RAW": "BYTEA",
    "DATE": "TIMESTAMP (Oracle DATE includes time component)",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMPTZ",
    "TIMESTAMP WITH LOCAL TIME ZONE": "TIMESTAMPTZ",
    "INTERVAL YEAR TO MONTH": "INTERVAL",
    "INTERVAL DAY TO SECOND": "INTERVAL",
    "BINARY_FLOAT": "REAL",
    "BINARY_DOUBLE": "DOUBLE PRECISION",
    "FLOAT": "DOUBLE PRECISION",
    "XMLTYPE": "XML",
    "ROWID": "TEXT (no direct equivalent)",
    "UROWID": "TEXT (no direct equivalent)",
    "BOOLEAN": "BOOLEAN",
}

_FUNCTION_MAP = {
    # NULL handling
    "NVL(a, b)": "COALESCE(a, b)",
    "NVL2(a, b, c)": "CASE WHEN a IS NOT NULL THEN b ELSE c END",
    "DECODE(expr, v1, r1, ..., default)": "CASE WHEN expr=v1 THEN r1 ... ELSE default END",
    # Date/Time
    "SYSDATE": "CURRENT_TIMESTAMP",
    "SYSTIMESTAMP": "CLOCK_TIMESTAMP()",
    "TO_DATE(str, fmt)": "TO_TIMESTAMP(str, fmt) or str::date",
    "TO_CHAR(date, fmt)": "TO_CHAR(date, fmt) -- mostly compatible",
    "ADD_MONTHS(date, n)": "date + INTERVAL 'n months'  -- use make_interval(months => n) for variable",
    "MONTHS_BETWEEN(d1, d2)": "EXTRACT(YEAR FROM age(d1,d2))*12 + EXTRACT(MONTH FROM age(d1,d2))",
    "LAST_DAY(date)": "(DATE_TRUNC('month', date) + INTERVAL '1 month - 1 day')::date",
    "NEXT_DAY(date, day)": "Use date + (dow - EXTRACT(DOW FROM date) + 7) % 7",
    "TRUNC(date)": "DATE_TRUNC('day', date)",
    "TRUNC(date, 'MM')": "DATE_TRUNC('month', date)",
    "TRUNC(date, 'YYYY')": "DATE_TRUNC('year', date)",
    "TRUNC(date, 'DD')": "DATE_TRUNC('day', date)",
    # String
    "SUBSTR(str, pos, len)": "SUBSTRING(str FROM pos FOR len)",
    "INSTR(str, sub)": "POSITION(sub IN str)",
    "INSTR(str, sub, start, occurrence)": "Use regexp_instr or custom function",
    "LENGTHB(str)": "OCTET_LENGTH(str)",
    "LENGTH(str)": "LENGTH(str) -- compatible",
    "LPAD(str, n, pad)": "LPAD(str::text, n, pad)",
    "RPAD(str, n, pad)": "RPAD(str::text, n, pad)",
    "LISTAGG(col, delim)": "STRING_AGG(col::text, delim)",
    "WM_CONCAT(col)": "STRING_AGG(col::text, ',')",
    "REPLACE(str, from, to)": "REPLACE(str, from, to) -- compatible",
    "TRIM(str)": "TRIM(str) -- compatible",
    "REGEXP_LIKE(str, pattern)": "str ~ pattern",
    "REGEXP_SUBSTR(str, pattern)": "SUBSTRING(str FROM pattern)",
    "REGEXP_REPLACE(str, pattern, rep)": "REGEXP_REPLACE(str, pattern, rep)",
    "REGEXP_COUNT(str, pattern)": "Use array_length(regexp_matches(str,pattern,'g'),1)",
    # Conversion
    "TO_NUMBER(str)": "str::numeric",
    "TO_NUMBER(str, fmt)": "TO_NUMBER(str, fmt) -- compatible",
    "CAST(expr AS type)": "CAST(expr AS pg_type) or expr::pg_type",
    # Sequence
    "SEQ.NEXTVAL": "nextval('seq')",
    "SEQ.CURRVAL": "currval('seq')",
    # System
    "USER": "CURRENT_USER",
    "SYS_GUID()": "gen_random_uuid()",
    "ROWNUM": "ROW_NUMBER() OVER() or LIMIT",
    "ROWID": "ctid (not recommended for application use)",
    # Aggregate/Analytic
    "ROW_NUMBER() OVER(...)": "ROW_NUMBER() OVER(...) -- compatible",
    "RANK() OVER(...)": "RANK() OVER(...) -- compatible",
    "DENSE_RANK() OVER(...)": "DENSE_RANK() OVER(...) -- compatible",
    "LAG(col, n) OVER(...)": "LAG(col, n) OVER(...) -- compatible",
    "LEAD(col, n) OVER(...)": "LEAD(col, n) OVER(...) -- compatible",
    # PL/SQL
    "RAISE_APPLICATION_ERROR(-n, msg)": "RAISE EXCEPTION '%', msg",
    "DBMS_OUTPUT.PUT_LINE(msg)": "RAISE NOTICE '%', msg",
    "EXECUTE IMMEDIATE sql": "EXECUTE sql",
    "EMPTY_CLOB()": "''",
    "EMPTY_BLOB()": "'\\x'::bytea",
}

_DDL_RULES = """## DDL Conversion Rules (Oracle → PostgreSQL)

### Table Creation
- Remove storage clauses: TABLESPACE, PCTFREE, INITRANS, STORAGE(...)
- Remove LOGGING/NOLOGGING
- Convert data types per type mapping
- Oracle DATE → TIMESTAMP (Oracle DATE includes time)
- NUMBER without precision → INTEGER or NUMERIC based on context
- VARCHAR2 → VARCHAR
- CLOB → TEXT, BLOB → BYTEA

### Constraints
- PRIMARY KEY: Syntax compatible, convert inline to named
- FOREIGN KEY: Syntax mostly compatible
  - ON DELETE CASCADE / SET NULL: Compatible
  - ENABLE/DISABLE → Don't add / use ALTER TABLE ... DISABLE TRIGGER
- CHECK: Mostly compatible, remove ENABLE/DISABLE/VALIDATE/NOVALIDATE
- UNIQUE: Compatible
- NOT NULL: Compatible

### Indexes
- B-tree indexes: CREATE INDEX compatible
- Remove TABLESPACE, PCTFREE, INITRANS
- Function-based indexes: CREATE INDEX ... ON table(LOWER(col)) → compatible
- Bitmap indexes: No direct equivalent, use regular B-tree or GIN
- Reverse key indexes: No equivalent, use hash index or regular B-tree
- Index-organized tables (IOT): Use CLUSTER or regular table with index

### Sequences
- CREATE SEQUENCE mostly compatible
- Remove NOCACHE (PG default), NOORDER
- MINVALUE, MAXVALUE, INCREMENT BY, START WITH: Compatible
- CYCLE/NOCYCLE: Compatible
- CACHE n: Compatible

### Partitioning
- RANGE partitioning: Use PARTITION BY RANGE
  - Oracle: PARTITION BY RANGE (col) (PARTITION p1 VALUES LESS THAN (val))
  - PG: CREATE TABLE ... PARTITION BY RANGE (col); CREATE TABLE p1 PARTITION OF ... FOR VALUES FROM (lo) TO (hi)
- LIST partitioning: PARTITION BY LIST compatible
- HASH partitioning: PARTITION BY HASH compatible (PG 11+)
- Sub-partitioning: PG supports multi-level partitioning (PG 13+)
- Interval partitioning: No direct equivalent, use pg_partman or cron-based

### Stored Procedures / Functions
- Oracle PROCEDURE → PostgreSQL PROCEDURE (PG 11+)
- Oracle FUNCTION → PostgreSQL FUNCTION
- Oracle PACKAGE → PostgreSQL SCHEMA with individual functions/procedures
- PL/SQL → PL/pgSQL:
  - DECLARE block: Compatible (add $$ delimiters)
  - %TYPE: Compatible
  - %ROWTYPE: Compatible
  - CURSOR: Compatible with minor syntax changes
  - EXCEPTION: Compatible (WHEN OTHERS THEN, WHEN NO_DATA_FOUND THEN)
  - BULK COLLECT: No direct equivalent, use arrays or temp tables
  - FORALL: No direct equivalent, use standard FOR loop
  - AUTONOMOUS_TRANSACTION: No direct equivalent, use dblink or separate connection
  - RETURNING INTO: Compatible

### Triggers
- BEFORE/AFTER INSERT/UPDATE/DELETE: Compatible
- FOR EACH ROW: Compatible
- :NEW/:OLD → NEW/OLD
- INSTEAD OF triggers (on views): Compatible
- Compound triggers: Split into individual triggers
- System triggers (LOGON/LOGOFF): Not available in PG

### Views
- CREATE OR REPLACE VIEW: Compatible
- Materialized Views: CREATE MATERIALIZED VIEW compatible
  - No automatic refresh in PG, use pg_cron or application-level refresh
  - REFRESH FAST/COMPLETE → REFRESH MATERIALIZED VIEW [CONCURRENTLY]

### Synonyms
- No direct equivalent in PostgreSQL
- Use search_path, views, or schema qualification instead
"""

_PLSQL_RULES = """## PL/SQL → PL/pgSQL Conversion Rules

### Block Structure
- Oracle: CREATE OR REPLACE PROCEDURE/FUNCTION name ... IS/AS ... BEGIN ... END name;
- PG: CREATE OR REPLACE PROCEDURE/FUNCTION name ... LANGUAGE plpgsql AS $$ DECLARE ... BEGIN ... END; $$;

### Variable Declarations
- VARCHAR2(n) → VARCHAR(n)
- NUMBER → NUMERIC or INTEGER
- DATE → TIMESTAMP
- BOOLEAN → BOOLEAN (compatible)
- PLS_INTEGER → INTEGER
- BINARY_INTEGER → INTEGER
- TABLE OF → ARRAY or use temporary tables
- RECORD type → PG RECORD or custom TYPE

### Control Flow
- IF/THEN/ELSIF/ELSE/END IF: Compatible
- CASE WHEN/THEN/ELSE/END CASE: Compatible
- FOR i IN 1..10 LOOP ... END LOOP: Compatible
- WHILE condition LOOP ... END LOOP: Compatible
- LOOP ... EXIT WHEN condition; END LOOP: Compatible
- FOR rec IN (SELECT...) LOOP: Compatible
- GOTO: Not available in PL/pgSQL, refactor to loops/functions

### Cursor Operations
- CURSOR declaration: Compatible
- OPEN/FETCH/CLOSE: Compatible
- FOR rec IN cursor_name LOOP: Compatible
- %FOUND/%NOTFOUND: Use FOUND (boolean) → IF FOUND THEN / IF NOT FOUND THEN
- %ROWCOUNT: Use GET DIAGNOSTICS row_count = ROW_COUNT
- SYS_REFCURSOR: Use REFCURSOR
- CURSOR parameters: Compatible

### Exception Handling
- NO_DATA_FOUND: Compatible
- TOO_MANY_ROWS: Compatible
- DUP_VAL_ON_INDEX: Use UNIQUE_VIOLATION
- OTHERS → OTHERS (compatible)
- SQLCODE → SQLSTATE
- SQLERRM → SQLERRM (compatible)
- RAISE_APPLICATION_ERROR(-20001, 'msg') → RAISE EXCEPTION 'msg'
- Custom exceptions: Use RAISE EXCEPTION with ERRCODE

### Dynamic SQL
- EXECUTE IMMEDIATE sql → EXECUTE sql
- EXECUTE IMMEDIATE sql INTO var → EXECUTE sql INTO var
- EXECUTE IMMEDIATE sql USING params → EXECUTE sql USING params
- DBMS_SQL package: Not available, use EXECUTE

### Collections
- TABLE OF type INDEX BY: Use arrays or temporary tables
- BULK COLLECT INTO: Use array_agg() or direct query
- FORALL INSERT/UPDATE: Use INSERT ... SELECT or FOR loop
- .COUNT → array_length(arr, 1)
- .FIRST/.LAST → array_lower/array_upper
- .EXISTS(i) → arr[i] IS NOT NULL
- .DELETE → arr := ARRAY[]

### Transaction Control
- COMMIT/ROLLBACK in PROCEDURE: Compatible (PG 11+)
- COMMIT/ROLLBACK in FUNCTION: NOT allowed, use PROCEDURE
- SAVEPOINT: Compatible
- AUTONOMOUS_TRANSACTION: Not available, use dblink
"""

_HIERARCHICAL_RULES = """## Hierarchical Query Conversion (CONNECT BY → WITH RECURSIVE)

### Oracle Pattern
```sql
SELECT columns, LEVEL
FROM table
START WITH condition
CONNECT BY [NOCYCLE] PRIOR parent_col = child_col
[ORDER SIBLINGS BY col]
```

### PostgreSQL Pattern (WITH RECURSIVE)
```sql
WITH RECURSIVE cte AS (
  -- Anchor: root rows (START WITH equivalent)
  SELECT columns, 1 AS level
  FROM table
  WHERE start_condition

  UNION ALL

  -- Recursive: traverse children (CONNECT BY equivalent)
  SELECT t.columns, cte.level + 1
  FROM table t
  JOIN cte ON t.child_col = cte.parent_col
)
SELECT * FROM cte
ORDER BY level, sort_col;
```

### Pseudo-column Conversions
- LEVEL → Add computed `level` column (1 for root, increment in recursive part)
- SYS_CONNECT_BY_PATH(col, sep) → Build path string: `cte.path || sep || t.col`
- CONNECT_BY_ROOT col → Carry root value through: `cte.root_col`
- CONNECT_BY_ISLEAF → NOT EXISTS subquery check
- ROWNUM in hierarchical → ROW_NUMBER() OVER()

### NOCYCLE → CYCLE clause (PostgreSQL 14+)
```sql
WITH RECURSIVE cte AS (...)
CYCLE parent_col SET is_cycle USING cycle_path
```
For PG < 14, track visited nodes in an array:
```sql
WITH RECURSIVE cte AS (
  SELECT ..., ARRAY[id] AS visited
  ...
  UNION ALL
  SELECT ..., cte.visited || t.id
  FROM table t JOIN cte ON ... AND t.id != ALL(cte.visited)
)
```

### ORDER SIBLINGS BY
No direct equivalent. Approaches:
1. Compute a sort path: `cte.sort_path || '/' || LPAD(sort_col::text, 10, '0')`
2. Use array-based ordering
"""

_AWS_BEST_PRACTICES = """## AWS Migration Best Practices (SCT/DMS)

### AWS SCT Conversion Patterns
1. **Data Types**: SCT maps Oracle NUMBER→NUMERIC, DATE→TIMESTAMP, VARCHAR2→VARCHAR
2. **Sequences**: SCT creates sequences with same START/INCREMENT values
3. **Indexes**: SCT converts supported index types, flags unsupported ones
4. **Stored Code**: SCT converts ~80% automatically, remaining needs manual review

### AWS DMS Best Practices
1. **Full Load**: Use DMS for bulk data transfer with parallel threads
2. **LOB Handling**: Use limited LOB mode for better performance
3. **Table Mapping**: Map Oracle schema to PG schema (or public)
4. **Character Set**: Oracle AL32UTF8 → PostgreSQL UTF8
5. **Case Sensitivity**: Oracle uppercase → PostgreSQL lowercase

### Common Migration Pitfalls (AWS Prescriptive Guidance)
1. **Oracle DATE vs PG DATE**: Oracle DATE includes time; map to TIMESTAMP
2. **Empty string vs NULL**: Oracle treats '' as NULL; PG distinguishes them
   - Mitigation: Use COALESCE or NVL mappings carefully
3. **Implicit type conversion**: Oracle is more lenient; PG requires explicit casts
4. **Sequence gaps**: Oracle CACHE causes gaps; PG same behavior but different gap sizes
5. **NULL in indexes**: Oracle excludes all-NULL rows from indexes; PG includes them
   - Mitigation: Add WHERE clause to partial index
6. **ROWNUM ordering**: Oracle ROWNUM applied before ORDER BY; PG LIMIT after ORDER BY
   - Mitigation: Use subquery: SELECT * FROM (SELECT ... ORDER BY ...) LIMIT n
7. **Trigger execution order**: Oracle fires triggers in creation order; PG alphabetical
8. **Transaction isolation**: Oracle read-committed with consistent reads; PG read-committed
9. **Lock escalation**: Oracle row-level default; PG similar but different deadlock detection

### RDS/Aurora Specific Constraints
- No OS-level access (UTL_FILE, external tables)
- No DBMS_SCHEDULER for OS commands (use Lambda + EventBridge)
- No DBMS_PIPE/DBMS_ALERT (use SQS/SNS or pg_notify)
- Limited DBMS_LOCK (use advisory locks: pg_advisory_lock)
- No database links (use postgres_fdw or Lambda)
- No Java stored procedures (use Lambda)
- Parameter groups instead of ALTER SYSTEM
"""

# Category registry
_CATEGORIES = {
    "data_types": {
        "title": "Oracle to PostgreSQL Data Type Mappings",
        "content": _DATA_TYPE_MAP,
        "format": "dict",
    },
    "functions": {
        "title": "Oracle to PostgreSQL Function Mappings",
        "content": _FUNCTION_MAP,
        "format": "dict",
    },
    "ddl": {
        "title": "DDL Conversion Rules (Tables, Indexes, Constraints, Partitions)",
        "content": _DDL_RULES,
        "format": "text",
    },
    "plsql": {
        "title": "PL/SQL to PL/pgSQL Conversion Rules",
        "content": _PLSQL_RULES,
        "format": "text",
    },
    "hierarchical": {
        "title": "Hierarchical Query Conversion (CONNECT BY → WITH RECURSIVE)",
        "content": _HIERARCHICAL_RULES,
        "format": "text",
    },
    "aws_best_practices": {
        "title": "AWS Migration Best Practices (SCT/DMS/Prescriptive Guidance)",
        "content": _AWS_BEST_PRACTICES,
        "format": "text",
    },
}


@tool
def oracle_to_pg_reference(category: str, search_term: str = "") -> str:
    """
    Look up Oracle-to-PostgreSQL conversion reference rules.

    Provides comprehensive conversion rules distilled from AWS SCT, AWS DMS
    Best Practices, AWS Prescriptive Guidance, and OMA migration expertise.

    Use this tool BEFORE converting any Oracle object to get the correct
    PostgreSQL equivalent. This ensures accurate, standards-compliant conversions.

    Available categories:
    - "data_types": Oracle→PG data type mappings (NUMBER, VARCHAR2, DATE, CLOB, etc.)
    - "functions": Oracle→PG function mappings (NVL, SYSDATE, DECODE, SUBSTR, etc.)
    - "ddl": DDL conversion rules (tables, indexes, constraints, partitions, sequences, triggers, views)
    - "plsql": PL/SQL→PL/pgSQL conversion rules (block structure, cursors, exceptions, dynamic SQL)
    - "hierarchical": CONNECT BY → WITH RECURSIVE conversion patterns
    - "aws_best_practices": AWS SCT/DMS/Prescriptive Guidance migration pitfalls and patterns
    - "all": Return all categories (use sparingly - large response)

    Args:
        category: The reference category to look up. Use "all" for everything.
        search_term: Optional keyword to filter results (e.g., "DATE", "NVL", "sequence").
                     Case-insensitive. Filters within the selected category.

    Returns:
        JSON with the requested conversion reference information.

    Example:
        >>> oracle_to_pg_reference("data_types", "NUMBER")
        >>> oracle_to_pg_reference("functions", "SYSDATE")
        >>> oracle_to_pg_reference("ddl", "partition")
        >>> oracle_to_pg_reference("plsql", "cursor")
        >>> oracle_to_pg_reference("aws_best_practices")
    """
    try:
        category = category.lower().strip()

        if category == "all":
            # Return everything
            result = {}
            for cat_name, cat_data in _CATEGORIES.items():
                if cat_data["format"] == "dict":
                    content = cat_data["content"]
                    if search_term:
                        term = search_term.upper()
                        content = {
                            k: v for k, v in content.items()
                            if term in k.upper() or term in v.upper()
                        }
                    result[cat_name] = {
                        "title": cat_data["title"],
                        "entries": content,
                    }
                else:
                    text = cat_data["content"]
                    if search_term:
                        lines = text.split('\n')
                        term = search_term.lower()
                        # Return paragraphs containing the search term
                        filtered = []
                        for i, line in enumerate(lines):
                            if term in line.lower():
                                # Include context: 2 lines before/after
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                filtered.extend(lines[start:end])
                                filtered.append("---")
                        text = '\n'.join(filtered) if filtered else f"No matches for '{search_term}'"
                    result[cat_name] = {
                        "title": cat_data["title"],
                        "content": text,
                    }
            return json.dumps({"success": True, "results": result}, ensure_ascii=False)

        if category not in _CATEGORIES:
            return json.dumps({
                "success": False,
                "error": f"Unknown category: '{category}'",
                "available_categories": list(_CATEGORIES.keys()) + ["all"],
            })

        cat_data = _CATEGORIES[category]

        if cat_data["format"] == "dict":
            content = cat_data["content"]
            if search_term:
                term = search_term.upper()
                content = {
                    k: v for k, v in content.items()
                    if term in k.upper() or term in v.upper()
                }
            return json.dumps({
                "success": True,
                "category": category,
                "title": cat_data["title"],
                "entries": content,
                "count": len(content),
            }, ensure_ascii=False)
        else:
            text = cat_data["content"]
            if search_term:
                lines = text.split('\n')
                term = search_term.lower()
                filtered = []
                for i, line in enumerate(lines):
                    if term in line.lower():
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        filtered.extend(lines[start:end])
                        filtered.append("---")
                text = '\n'.join(filtered) if filtered else f"No matches for '{search_term}'"
            return json.dumps({
                "success": True,
                "category": category,
                "title": cat_data["title"],
                "content": text,
            }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        })
