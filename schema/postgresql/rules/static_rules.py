"""
Complete Oracle to PostgreSQL Static Transformation Rules

This module defines ALL Oracle->PostgreSQL conversion rules as structured data.
Based on the comprehensive postgreRules.md reference document.

Rule Types:
- FUNCTION_MAPPINGS: Oracle function conversions
- DATA_TYPE_MAPPINGS: Data type conversions
- SYNTAX_RULES: Syntax pattern conversions
- JDBC_TYPE_MAPPINGS: JDBC type conversions for MyBatis
- MYBATIS_TYPE_MAPPINGS: MyBatis bind variable type conversions
- DATE_FORMAT_MAPPINGS: Date format string conversions
"""

from typing import Dict, Any, List, Tuple
import re

# ==============================================================================
# FUNCTION MAPPINGS - Oracle function conversions to PostgreSQL
# ==============================================================================

FUNCTION_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # === Basic Functions ===
    "NVL": {
        "oracle": r"NVL\s*\(",
        "pg": "COALESCE(",
        "type": "simple_replace",
        "description": "Convert NVL to COALESCE"
    },

    "SYSDATE": {
        "oracle": r"\bSYSDATE\b",
        "pg": "CURRENT_TIMESTAMP",
        "type": "simple_replace",
        "description": "Convert SYSDATE to CURRENT_TIMESTAMP"
    },

    "SYSTIMESTAMP": {
        "oracle": r"\bSYSTIMESTAMP\b",
        "pg": "CURRENT_TIMESTAMP",
        "type": "simple_replace",
        "description": "Convert SYSTIMESTAMP to CURRENT_TIMESTAMP"
    },

    "USER": {
        "oracle": r"\bUSER\b",
        "pg": "CURRENT_USER",
        "type": "simple_replace",
        "description": "Convert USER to CURRENT_USER"
    },

    "SYS_GUID": {
        "oracle": r"SYS_GUID\s*\(\s*\)",
        "pg": "gen_random_uuid()",
        "type": "simple_replace",
        "description": "Convert SYS_GUID() to gen_random_uuid()"
    },

    # === NVL2 - Conditional NULL handling ===
    "NVL2": {
        "oracle": r"NVL2\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "pg": r"CASE WHEN \1 IS NOT NULL THEN \2 ELSE \3 END",
        "type": "regex_replace",
        "description": "Convert NVL2 to CASE expression"
    },

    # === DECODE - Handled by RuleEngine._convert_decode() ===
    "DECODE": {
        "oracle": r"DECODE\s*\(",
        "pg": "CASE WHEN",
        "type": "engine_handled",
        "description": "Convert DECODE to CASE WHEN (parenthesis-aware parser in rule_engine.py)"
    },

    # === String Functions ===
    "SUBSTR": {
        "oracle": r"SUBSTR\s*\(",
        "pg": "SUBSTRING(",
        "type": "simple_replace",
        "description": "Convert SUBSTR to SUBSTRING"
    },

    "INSTR": {
        "oracle": r"INSTR\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "pg": r"POSITION(\2 IN \1)",
        "type": "regex_replace",
        "description": "Convert INSTR to POSITION"
    },

    "LENGTH": {
        "oracle": r"\bLENGTH\b",
        "pg": "LENGTH",
        "type": "simple_replace",
        "description": "LENGTH is same in PostgreSQL"
    },

    "LENGTHB": {
        "oracle": r"LENGTHB\s*\(",
        "pg": "OCTET_LENGTH(",
        "type": "simple_replace",
        "description": "Convert LENGTHB to OCTET_LENGTH"
    },

    "LPAD": {
        "oracle": r"LPAD\s*\(\s*([^,]+?)\s*,",
        "pg": r"LPAD(\1::text,",
        "type": "regex_replace",
        "description": "Convert LPAD with text cast"
    },

    "RPAD": {
        "oracle": r"RPAD\s*\(\s*([^,]+?)\s*,",
        "pg": r"RPAD(\1::text,",
        "type": "regex_replace",
        "description": "Convert RPAD with text cast"
    },

    "TRIM": {
        "oracle": r"\bTRIM\b",
        "pg": "TRIM",
        "type": "simple_replace",
        "description": "TRIM is same in PostgreSQL"
    },

    "LTRIM": {
        "oracle": r"\bLTRIM\b",
        "pg": "LTRIM",
        "type": "simple_replace",
        "description": "LTRIM is same in PostgreSQL"
    },

    "RTRIM": {
        "oracle": r"\bRTRIM\b",
        "pg": "RTRIM",
        "type": "simple_replace",
        "description": "RTRIM is same in PostgreSQL"
    },

    "REPLACE": {
        "oracle": r"\bREPLACE\b",
        "pg": "REPLACE",
        "type": "simple_replace",
        "description": "REPLACE is same in PostgreSQL"
    },

    "UPPER": {
        "oracle": r"\bUPPER\b",
        "pg": "UPPER",
        "type": "simple_replace",
        "description": "UPPER is same in PostgreSQL"
    },

    "LOWER": {
        "oracle": r"\bLOWER\b",
        "pg": "LOWER",
        "type": "simple_replace",
        "description": "LOWER is same in PostgreSQL"
    },

    "INITCAP": {
        "oracle": r"\bINITCAP\b",
        "pg": "INITCAP",
        "type": "simple_replace",
        "description": "INITCAP is same in PostgreSQL"
    },

    # === Aggregation Functions ===
    "LISTAGG": {
        "oracle": r"LISTAGG\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "pg": r"STRING_AGG(\1, \2)",
        "type": "regex_replace",
        "description": "Convert LISTAGG to STRING_AGG"
    },

    "WM_CONCAT": {
        "oracle": r"WM_CONCAT\s*\(",
        "pg": "STRING_AGG(",
        "type": "simple_replace",
        "description": "Convert WM_CONCAT to STRING_AGG"
    },

    # === Date Functions ===
    "TO_DATE": {
        "oracle": r"TO_DATE\s*\(",
        "pg": "TO_DATE(",  # Needs format conversion
        "type": "complex",
        "description": "Convert TO_DATE (needs format string handling)"
    },

    "TO_CHAR_DATE": {
        "oracle": r"TO_CHAR\s*\(",
        "pg": "TO_CHAR(",  # Needs format conversion
        "type": "complex",
        "description": "Convert TO_CHAR for dates (needs format string handling)"
    },

    "TO_NUMBER": {
        "oracle": r"TO_NUMBER\s*\(",
        "pg": "TO_NUMBER(",
        "type": "simple_replace",
        "description": "TO_NUMBER is same in PostgreSQL"
    },

    "ADD_MONTHS": {
        "oracle": r"ADD_MONTHS\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "pg": r"\1 + INTERVAL '\2 months'",
        "type": "regex_replace",
        "description": "Convert ADD_MONTHS to interval addition"
    },

    "MONTHS_BETWEEN": {
        "oracle": r"MONTHS_BETWEEN\s*\(",
        "pg": "AGE(",  # Requires adjustment
        "type": "complex",
        "description": "Convert MONTHS_BETWEEN to AGE (complex)"
    },

    "TRUNC_DATE": {
        "oracle": r"TRUNC\s*\(\s*([^,]+?)\s*,\s*'DD'\s*\)",
        "pg": r"DATE_TRUNC('day', \1)",
        "type": "regex_replace",
        "description": "Convert TRUNC(date, 'DD') to DATE_TRUNC"
    },

    "TRUNC_MONTH": {
        "oracle": r"TRUNC\s*\(\s*([^,]+?)\s*,\s*'MM'\s*\)",
        "pg": r"DATE_TRUNC('month', \1)",
        "type": "regex_replace",
        "description": "Convert TRUNC(date, 'MM') to DATE_TRUNC"
    },

    "TRUNC_YEAR": {
        "oracle": r"TRUNC\s*\(\s*([^,]+?)\s*,\s*'YY(?:YY)?'\s*\)",
        "pg": r"DATE_TRUNC('year', \1)",
        "type": "regex_replace",
        "description": "Convert TRUNC(date, 'YY') to DATE_TRUNC"
    },

    "NEXT_DAY": {
        "oracle": r"NEXT_DAY\s*\(",
        "pg": None,  # Complex - needs custom function
        "type": "complex",
        "description": "NEXT_DAY needs custom function in PostgreSQL"
    },

    "LAST_DAY": {
        "oracle": r"LAST_DAY\s*\(\s*([^)]+?)\s*\)",
        "pg": r"(DATE_TRUNC('month', \1) + INTERVAL '1 month' - INTERVAL '1 day')::date",
        "type": "regex_replace",
        "description": "Convert LAST_DAY to date arithmetic"
    },

    "EXTRACT": {
        "oracle": r"\bEXTRACT\b",
        "pg": "EXTRACT",
        "type": "simple_replace",
        "description": "EXTRACT is same in PostgreSQL"
    },

    # === Numeric Functions ===
    "ROUND": {
        "oracle": r"\bROUND\b",
        "pg": "ROUND",
        "type": "simple_replace",
        "description": "ROUND is same in PostgreSQL"
    },

    "TRUNC_NUMERIC": {
        "oracle": r"TRUNC\s*\(\s*([0-9.]+|[a-zA-Z_][a-zA-Z0-9_]*)\s*\)",
        "pg": r"TRUNC(\1)",
        "type": "simple_replace",
        "description": "TRUNC for numbers is same in PostgreSQL"
    },

    "CEIL": {
        "oracle": r"\bCEIL\b",
        "pg": "CEIL",
        "type": "simple_replace",
        "description": "CEIL is same in PostgreSQL"
    },

    "FLOOR": {
        "oracle": r"\bFLOOR\b",
        "pg": "FLOOR",
        "type": "simple_replace",
        "description": "FLOOR is same in PostgreSQL"
    },

    "ABS": {
        "oracle": r"\bABS\b",
        "pg": "ABS",
        "type": "simple_replace",
        "description": "ABS is same in PostgreSQL"
    },

    "MOD": {
        "oracle": r"\bMOD\b",
        "pg": "MOD",
        "type": "simple_replace",
        "description": "MOD is same in PostgreSQL"
    },

    "POWER": {
        "oracle": r"\bPOWER\b",
        "pg": "POWER",
        "type": "simple_replace",
        "description": "POWER is same in PostgreSQL"
    },

    "SQRT": {
        "oracle": r"\bSQRT\b",
        "pg": "SQRT",
        "type": "simple_replace",
        "description": "SQRT is same in PostgreSQL"
    },

    "SIGN": {
        "oracle": r"\bSIGN\b",
        "pg": "SIGN",
        "type": "simple_replace",
        "description": "SIGN is same in PostgreSQL"
    },

    # === Sequence Functions ===
    "NEXTVAL": {
        "oracle": r"([a-zA-Z_][a-zA-Z0-9_]*)\.NEXTVAL",
        "pg": r"nextval('\1')",
        "type": "regex_replace",
        "description": "Convert sequence.NEXTVAL to nextval('sequence')"
    },

    "CURRVAL": {
        "oracle": r"([a-zA-Z_][a-zA-Z0-9_]*)\.CURRVAL",
        "pg": r"currval('\1')",
        "type": "regex_replace",
        "description": "Convert sequence.CURRVAL to currval('sequence')"
    },

    # === Pagination ===
    "ROWNUM": {
        "oracle": r"\bROWNUM\b",
        "pg": None,  # Context-dependent: LIMIT or ROW_NUMBER()
        "type": "complex",
        "description": "ROWNUM needs context-aware conversion"
    },

    "ROWID": {
        "oracle": r"\bROWID\b",
        "pg": "ctid",
        "type": "simple_replace",
        "description": "Convert ROWID to ctid (use cautiously)"
    },

    # === Analytical Functions (mostly same) ===
    "ROW_NUMBER": {
        "oracle": r"\bROW_NUMBER\b",
        "pg": "ROW_NUMBER",
        "type": "simple_replace",
        "description": "ROW_NUMBER is same in PostgreSQL"
    },

    "RANK": {
        "oracle": r"\bRANK\b",
        "pg": "RANK",
        "type": "simple_replace",
        "description": "RANK is same in PostgreSQL"
    },

    "DENSE_RANK": {
        "oracle": r"\bDENSE_RANK\b",
        "pg": "DENSE_RANK",
        "type": "simple_replace",
        "description": "DENSE_RANK is same in PostgreSQL"
    },

    "LAG": {
        "oracle": r"\bLAG\b",
        "pg": "LAG",
        "type": "simple_replace",
        "description": "LAG is same in PostgreSQL"
    },

    "LEAD": {
        "oracle": r"\bLEAD\b",
        "pg": "LEAD",
        "type": "simple_replace",
        "description": "LEAD is same in PostgreSQL"
    },

    "FIRST_VALUE": {
        "oracle": r"\bFIRST_VALUE\b",
        "pg": "FIRST_VALUE",
        "type": "simple_replace",
        "description": "FIRST_VALUE is same in PostgreSQL"
    },

    "LAST_VALUE": {
        "oracle": r"\bLAST_VALUE\b",
        "pg": "LAST_VALUE",
        "type": "simple_replace",
        "description": "LAST_VALUE is same in PostgreSQL"
    },

    # === Conversion Functions ===
    "CAST": {
        "oracle": r"\bCAST\b",
        "pg": "CAST",
        "type": "simple_replace",
        "description": "CAST is same in PostgreSQL"
    },

    # === NULL Handling ===
    "COALESCE": {
        "oracle": r"\bCOALESCE\b",
        "pg": "COALESCE",
        "type": "simple_replace",
        "description": "COALESCE is same in PostgreSQL"
    },

    "NULLIF": {
        "oracle": r"\bNULLIF\b",
        "pg": "NULLIF",
        "type": "simple_replace",
        "description": "NULLIF is same in PostgreSQL"
    },
}


# ==============================================================================
# DATA TYPE MAPPINGS - Oracle to PostgreSQL data type conversions
# ==============================================================================

DATA_TYPE_MAPPINGS: Dict[str, str] = {
    # String types
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "NCHAR": "CHAR",
    "CHAR": "CHAR",
    "CLOB": "TEXT",
    "NCLOB": "TEXT",
    "LONG": "TEXT",

    # Numeric types
    "NUMBER": "NUMERIC",
    "INTEGER": "INTEGER",
    "INT": "INTEGER",
    "SMALLINT": "SMALLINT",
    "FLOAT": "DOUBLE PRECISION",
    "BINARY_FLOAT": "REAL",
    "BINARY_DOUBLE": "DOUBLE PRECISION",
    "DECIMAL": "DECIMAL",

    # Date/Time types
    "DATE": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP WITH LOCAL TIME ZONE": "TIMESTAMP WITH TIME ZONE",
    "INTERVAL YEAR TO MONTH": "INTERVAL",
    "INTERVAL DAY TO SECOND": "INTERVAL",

    # Binary types
    "RAW": "BYTEA",
    "LONG RAW": "BYTEA",
    "BLOB": "BYTEA",
    "BFILE": "BYTEA",

    # Other types
    "ROWID": "TEXT",  # or OID, context-dependent
    "UROWID": "TEXT",
    "XMLTYPE": "XML",
    "BOOLEAN": "BOOLEAN",
}


# ==============================================================================
# SYNTAX RULES - Oracle syntax pattern conversions
# ==============================================================================

SYNTAX_RULES: Dict[str, Dict[str, Any]] = {
    # === String Concatenation ===
    # NOTE: PostgreSQL natively supports || for string concatenation.
    # No conversion needed. Oracle || and PG || are semantically identical
    # (both return NULL if any operand is NULL).
    # Do NOT convert to CONCAT() — CONCAT treats NULL as empty string,
    # which changes Oracle semantics.

    # === DUAL Table ===
    "dual_removal": {
        "oracle": r"\s+FROM\s+DUAL\b",
        "pg": "",
        "type": "regex_replace",
        "priority": 2,
        "description": "Remove FROM DUAL"
    },

    # === Oracle Hints ===
    "hint_removal": {
        "oracle": r"/\*\+[^*]*\*/",
        "pg": "",
        "type": "regex_replace",
        "priority": 3,
        "description": "Remove Oracle optimizer hints"
    },

    # === Outer Join ===
    "outer_join": {
        "oracle": r"\(\+\)",
        "pg": None,  # Must be converted to LEFT/RIGHT JOIN
        "type": "complex",
        "priority": 4,
        "description": "Convert (+) to LEFT/RIGHT JOIN"
    },

    # === Subquery Aliases (MANDATORY in PostgreSQL) ===
    "subquery_alias": {
        "oracle": r"FROM\s*\(\s*SELECT",
        "pg": "FROM (SELECT ... ) AS sub",
        "type": "complex",
        "priority": 5,
        "description": "Ensure all subqueries have aliases"
    },

    # === Empty String vs NULL ===
    "empty_string_null": {
        "oracle": "''",
        "pg": "NULL",  # Context-dependent
        "type": "complex",
        "priority": 6,
        "description": "Oracle treats '' as NULL"
    },

    # === Connect By (Hierarchical Queries) ===
    "connect_by": {
        "oracle": r"\bCONNECT\s+BY\b",
        "pg": None,  # Convert to WITH RECURSIVE
        "type": "complex",
        "priority": 7,
        "description": "Convert CONNECT BY to WITH RECURSIVE"
    },

    "start_with": {
        "oracle": r"\bSTART\s+WITH\b",
        "pg": None,  # Part of CONNECT BY conversion
        "type": "complex",
        "priority": 7,
        "description": "Part of hierarchical query conversion"
    },

    # === MERGE Statement ===
    "merge": {
        "oracle": r"\bMERGE\s+INTO\b",
        "pg": None,  # Convert to INSERT ... ON CONFLICT or CTE
        "type": "complex",
        "priority": 8,
        "description": "Convert MERGE to INSERT ON CONFLICT"
    },

    # === Stored Procedure Calls ===
    "procedure_call": {
        "oracle": r"\{\s*call\s+",
        "pg": "CALL ",
        "type": "regex_replace",
        "priority": 9,
        "description": "Convert {call PROC()} to CALL PROC()"
    },

    # === ROWNUM Pagination ===
    "rownum_limit": {
        "oracle": r"ROWNUM\s*<=\s*(\d+)",
        "pg": r"LIMIT \1",
        "type": "regex_replace",
        "priority": 10,
        "description": "Convert ROWNUM <= n to LIMIT n"
    },

    "rownum_equal": {
        "oracle": r"ROWNUM\s*=\s*1\b",
        "pg": "LIMIT 1",
        "type": "regex_replace",
        "priority": 10,
        "description": "Convert ROWNUM = 1 to LIMIT 1"
    },

    # === Date Arithmetic ===
    "sysdate_arithmetic": {
        "oracle": r"SYSDATE\s*([+-])\s*(\d+)",
        "pg": r"CURRENT_TIMESTAMP \1 INTERVAL '\2 days'",
        "type": "regex_replace",
        "priority": 11,
        "description": "Convert SYSDATE +/- days to INTERVAL"
    },

    # === System Context ===
    "sys_context": {
        "oracle": r"SYS_CONTEXT\s*\(",
        "pg": None,  # Needs custom function or session variables
        "type": "complex",
        "priority": 12,
        "description": "SYS_CONTEXT needs custom implementation"
    },

    # === DBMS Packages ===
    "dbms_output": {
        "oracle": r"DBMS_OUTPUT\.",
        "pg": None,  # Use RAISE NOTICE
        "type": "complex",
        "priority": 13,
        "description": "DBMS_OUTPUT -> RAISE NOTICE"
    },

    "dbms_lob": {
        "oracle": r"DBMS_LOB\.",
        "pg": None,  # Convert to bytea operations
        "type": "complex",
        "priority": 13,
        "description": "DBMS_LOB needs conversion"
    },

    "dbms_sql": {
        "oracle": r"DBMS_SQL\.",
        "pg": None,  # Convert to EXECUTE or plpgsql dynamic SQL
        "type": "complex",
        "priority": 13,
        "description": "DBMS_SQL needs conversion"
    },

    # === UTL Packages ===
    "utl_file": {
        "oracle": r"UTL_FILE\.",
        "pg": None,  # Use COPY or custom functions
        "type": "complex",
        "priority": 14,
        "description": "UTL_FILE needs conversion"
    },

    "utl_http": {
        "oracle": r"UTL_HTTP\.",
        "pg": None,  # Use extensions like http or plpython
        "type": "complex",
        "priority": 14,
        "description": "UTL_HTTP needs conversion"
    },

    # === Exception Handling ===
    "exception_no_data_found": {
        "oracle": r"NO_DATA_FOUND",
        "pg": "NO_DATA_FOUND",  # Same in plpgsql
        "type": "simple_replace",
        "priority": 15,
        "description": "NO_DATA_FOUND is same"
    },

    "exception_too_many_rows": {
        "oracle": r"TOO_MANY_ROWS",
        "pg": "TOO_MANY_ROWS",  # Same in plpgsql
        "type": "simple_replace",
        "priority": 15,
        "description": "TOO_MANY_ROWS is same"
    },
}


# ==============================================================================
# JDBC TYPE MAPPINGS - For MyBatis resultMap conversions
# ==============================================================================

JDBC_TYPE_MAPPINGS: Dict[str, str] = {
    "NUMBER": "NUMERIC",
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "CLOB": "LONGVARCHAR",
    "NCLOB": "LONGVARCHAR",
    "BLOB": "LONGVARBINARY",
    "DATE": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "RAW": "VARBINARY",
    "LONG": "LONGVARCHAR",
    "LONG RAW": "LONGVARBINARY",
    "ROWID": "VARCHAR",
    "UROWID": "VARCHAR",
}


# ==============================================================================
# MYBATIS TYPE MAPPINGS - For MyBatis bind variable type conversions
# ==============================================================================

MYBATIS_TYPE_MAPPINGS: Dict[str, str] = {
    "CLOB": "LONGVARCHAR",
    "NUMBER": "NUMERIC",
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "BLOB": "LONGVARBINARY",
    "DATE": "TIMESTAMP",
    "RAW": "VARBINARY",
    "LONG": "LONGVARCHAR",
    "LONG RAW": "LONGVARBINARY",
}


# ==============================================================================
# DATE FORMAT MAPPINGS - Oracle to PostgreSQL date format conversions
# ==============================================================================

DATE_FORMAT_MAPPINGS: Dict[str, str] = {
    # Year formats
    "YYYY": "YYYY",
    "YY": "YY",
    "RRRR": "YYYY",
    "RR": "YY",
    "YEAR": "YEAR",
    "Y,YYY": "Y,YYY",

    # Month formats
    "MM": "MM",
    "MON": "Mon",
    "MONTH": "Month",
    "RM": "RM",  # Roman numeral month

    # Day formats
    "DD": "DD",
    "DDD": "DDD",  # Day of year
    "D": "D",      # Day of week
    "DAY": "Day",
    "DY": "Dy",

    # Week formats
    "WW": "WW",  # Week of year
    "W": "W",    # Week of month
    "IW": "IW",  # ISO week

    # Time formats
    "HH": "HH12",
    "HH12": "HH12",
    "HH24": "HH24",
    "MI": "MI",
    "SS": "SS",
    "SSSSS": "SSSS",  # Seconds since midnight
    "FF": "MS",       # Fractional seconds
    "FF1": "MS",
    "FF2": "MS",
    "FF3": "MS",
    "FF4": "MS",
    "FF5": "MS",
    "FF6": "US",

    # AM/PM markers
    "AM": "AM",
    "PM": "PM",
    "A.M.": "A.M.",
    "P.M.": "P.M.",

    # Time zone
    "TZH": "TZH",
    "TZM": "TZM",
    "TZ": "TZ",
}


# ==============================================================================
# POSTGRESQL CAST TYPE MAPPINGS - For parameter casting
# ==============================================================================

PG_CAST_TYPES: Dict[str, str] = {
    "integer": "::integer",
    "int4": "::integer",
    "bigint": "::bigint",
    "int8": "::bigint",
    "numeric": "::numeric",
    "decimal": "::numeric",
    "double precision": "::double precision",
    "real": "::real",
    "float4": "::real",
    "date": "::date",
    "timestamp": "::timestamp",
    "timestamp without time zone": "::timestamp",
    "timestamp with time zone": "::timestamptz",
    "timestamptz": "::timestamptz",
    "boolean": "::boolean",
    "bool": "::boolean",
    # String types - NO casting needed
    "character varying": None,
    "varchar": None,
    "char": None,
    "text": None,
    "character": None,
}


# ==============================================================================
# COMPLEX PATTERNS - Patterns that need LLM or Swarm conversion
# ==============================================================================

COMPLEX_PATTERNS: List[Tuple[str, str, str]] = [
    # (pattern, name, complexity_level)
    (r"\bCONNECT\s+BY\b", "CONNECT BY", "COMPLEX"),
    (r"\bSTART\s+WITH\b", "START WITH", "COMPLEX"),
    (r"\bMERGE\s+INTO\b", "MERGE", "COMPLEX"),
    (r"\bBULK\s+COLLECT\b", "BULK COLLECT", "COMPLEX"),
    (r"\bFORALL\b", "FORALL", "COMPLEX"),
    (r"\bEXECUTE\s+IMMEDIATE\b", "EXECUTE IMMEDIATE", "SIMPLE"),  # Handled by rule engine
    (r"\bDBMS_\w+\.", "DBMS Package", "COMPLEX"),
    (r"\bUTL_\w+\.", "UTL Package", "COMPLEX"),
    (r"\bSYS_CONTEXT\s*\(", "SYS_CONTEXT", "MODERATE"),
    (r"\(\+\)", "Outer Join (+)", "MODERATE"),
    (r"\bDECODE\s*\(", "DECODE", "SIMPLE"),  # Handled by rule engine
    (r"CREATE\s+OR\s+REPLACE\s+PACKAGE", "PL/SQL Package", "COMPLEX"),
    (r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+BODY", "PL/SQL Package Body", "COMPLEX"),
    (r"CREATE\s+OR\s+REPLACE\s+TYPE", "Object Type", "COMPLEX"),
    (r"%ROWTYPE\b", "Record Type", "MODERATE"),
    (r"%TYPE\b", "Type Attribute", "SIMPLE"),
]


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_function_mapping(func_name: str) -> Dict[str, Any]:
    """Get function mapping by name (case-insensitive)."""
    func_upper = func_name.upper()
    return FUNCTION_MAPPINGS.get(func_upper, {})


def get_data_type_mapping(oracle_type: str) -> str:
    """Get PostgreSQL data type for Oracle type (case-insensitive)."""
    type_upper = oracle_type.upper()
    return DATA_TYPE_MAPPINGS.get(type_upper, oracle_type)


def get_jdbc_type_mapping(oracle_jdbc_type: str) -> str:
    """Get PostgreSQL JDBC type for Oracle JDBC type."""
    type_upper = oracle_jdbc_type.upper()
    return JDBC_TYPE_MAPPINGS.get(type_upper, oracle_jdbc_type)


def get_mybatis_type_mapping(oracle_mybatis_type: str) -> str:
    """Get PostgreSQL MyBatis type for Oracle MyBatis type."""
    type_upper = oracle_mybatis_type.upper()
    return MYBATIS_TYPE_MAPPINGS.get(type_upper, oracle_mybatis_type)


def get_pg_cast_syntax(pg_data_type: str) -> str:
    """Get PostgreSQL cast syntax for data type, or None if no cast needed."""
    type_lower = pg_data_type.lower()
    return PG_CAST_TYPES.get(type_lower)
