"""
Complete Oracle to MySQL Static Transformation Rules

This module defines ALL Oracle->MySQL conversion rules as structured data.
Based on oracle-mysql-rules.md reference document from .claude/rules/.

Rule Types:
- FUNCTION_MAPPINGS: Oracle function conversions
- DATA_TYPE_MAPPINGS: Data type conversions
- SYNTAX_RULES: Syntax pattern conversions
- JDBC_TYPE_MAPPINGS: JDBC type conversions for MyBatis
- MYBATIS_TYPE_MAPPINGS: MyBatis bind variable type conversions
- DATE_FORMAT_MAPPINGS: Date format string conversions
- CONNECT_BY_PATTERNS: Hierarchical query patterns
- SUBQUERY_ALIAS_PATTERNS: Mandatory subquery alias patterns
"""

from typing import Dict, Any, List, Tuple
import re

# ==============================================================================
# FUNCTION MAPPINGS - Oracle function conversions to MySQL
# ==============================================================================

FUNCTION_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # === Basic Functions ===
    "NVL": {
        "oracle": r"NVL\s*\(",
        "mysql": "IFNULL(",
        "type": "simple_replace",
        "description": "Convert NVL to IFNULL"
    },

    "SYSDATE": {
        "oracle": r"\bSYSDATE\b",
        "mysql": "NOW()",
        "type": "simple_replace",
        "description": "Convert SYSDATE to NOW()"
    },

    "SYSTIMESTAMP": {
        "oracle": r"\bSYSTIMESTAMP\b",
        "mysql": "NOW()",
        "type": "simple_replace",
        "description": "Convert SYSTIMESTAMP to NOW()"
    },

    "USER": {
        "oracle": r"\bUSER\b(?!\s*\()",
        "mysql": "USER()",
        "type": "simple_replace",
        "description": "Convert USER to USER()"
    },

    "SYS_GUID": {
        "oracle": r"SYS_GUID\s*\(\s*\)",
        "mysql": "UUID()",
        "type": "simple_replace",
        "description": "Convert SYS_GUID() to UUID()"
    },

    # === NVL2 - Conditional NULL handling ===
    "NVL2": {
        "oracle": r"NVL2\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "mysql": r"CASE WHEN \1 IS NOT NULL THEN \2 ELSE \3 END",
        "type": "regex_replace",
        "description": "Convert NVL2 to CASE expression"
    },

    # === DECODE - Handled by RuleEngine._convert_decode() ===
    "DECODE": {
        "oracle": r"DECODE\s*\(",
        "mysql": "CASE WHEN",
        "type": "engine_handled",
        "description": "Convert DECODE to CASE WHEN"
    },

    # === String Functions ===
    "SUBSTR": {
        "oracle": r"SUBSTR\s*\(\s*([^,]+?)\s*,\s*([^,]+?)(?:\s*,\s*([^)]+?))?\s*\)",
        "mysql": r"SUBSTRING(\1, GREATEST(\2, 1), \3)",
        "type": "regex_replace",
        "description": "Convert SUBSTR to SUBSTRING with GREATEST (Oracle 0 = MySQL 1)"
    },

    "INSTR": {
        "oracle": r"INSTR\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "mysql": r"LOCATE(\2, \1)",
        "type": "regex_replace",
        "description": "Convert INSTR(str, substr) to LOCATE(substr, str)"
    },

    "LENGTH": {
        "oracle": r"\bLENGTH\b",
        "mysql": "LENGTH",
        "type": "simple_replace",
        "description": "LENGTH is same in MySQL"
    },

    "LENGTHB": {
        "oracle": r"LENGTHB\s*\(",
        "mysql": "LENGTH(",
        "type": "simple_replace",
        "description": "LENGTHB → LENGTH (MySQL uses bytes by default)"
    },

    "LPAD": {
        "oracle": r"LPAD\s*\(",
        "mysql": "LPAD(",
        "type": "simple_replace",
        "description": "LPAD is same in MySQL"
    },

    "RPAD": {
        "oracle": r"RPAD\s*\(",
        "mysql": "RPAD(",
        "type": "simple_replace",
        "description": "RPAD is same in MySQL"
    },

    "LTRIM": {
        "oracle": r"LTRIM\s*\(",
        "mysql": "LTRIM(",
        "type": "simple_replace",
        "description": "LTRIM is same in MySQL"
    },

    "RTRIM": {
        "oracle": r"RTRIM\s*\(",
        "mysql": "RTRIM(",
        "type": "simple_replace",
        "description": "RTRIM is same in MySQL"
    },

    "TRIM": {
        "oracle": r"TRIM\s*\(",
        "mysql": "TRIM(",
        "type": "simple_replace",
        "description": "TRIM is same in MySQL"
    },

    "UPPER": {
        "oracle": r"UPPER\s*\(",
        "mysql": "UPPER(",
        "type": "simple_replace",
        "description": "UPPER is same in MySQL"
    },

    "LOWER": {
        "oracle": r"LOWER\s*\(",
        "mysql": "LOWER(",
        "type": "simple_replace",
        "description": "LOWER is same in MySQL"
    },

    "INITCAP": {
        "oracle": r"INITCAP\s*\(\s*([^)]+?)\s*\)",
        "mysql": r"CONCAT(UPPER(LEFT(\1, 1)), LOWER(SUBSTRING(\1, 2)))",
        "type": "regex_replace",
        "description": "Convert INITCAP to CONCAT+UPPER+LOWER"
    },

    # === String Concatenation (||) ===
    "STRING_CONCAT": {
        "oracle": r"\|\|",
        "mysql": "CONCAT",
        "type": "engine_handled",
        "description": "Convert || to CONCAT with IFNULL wrapping (handled by rule_engine)"
    },

    # === Numeric Functions ===
    "TRUNC_NUMBER": {
        "oracle": r"TRUNC\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "mysql": r"TRUNCATE(\1, \2)",
        "type": "regex_replace",
        "description": "Convert TRUNC(number, precision) to TRUNCATE"
    },

    "TRUNC_DATE": {
        "oracle": r"TRUNC\s*\(\s*([^)]+?)\s*\)",
        "mysql": r"DATE(\1)",
        "type": "regex_replace",
        "description": "Convert TRUNC(date) to DATE() - single arg = date"
    },

    "CEIL": {
        "oracle": r"CEIL\s*\(",
        "mysql": "CEILING(",
        "type": "simple_replace",
        "description": "Convert CEIL to CEILING"
    },

    "FLOOR": {
        "oracle": r"FLOOR\s*\(",
        "mysql": "FLOOR(",
        "type": "simple_replace",
        "description": "FLOOR is same in MySQL"
    },

    "ROUND": {
        "oracle": r"ROUND\s*\(",
        "mysql": "ROUND(",
        "type": "simple_replace",
        "description": "ROUND is same in MySQL"
    },

    "POWER": {
        "oracle": r"POWER\s*\(",
        "mysql": "POW(",
        "type": "simple_replace",
        "description": "Convert POWER to POW"
    },

    "MOD": {
        "oracle": r"MOD\s*\(",
        "mysql": "MOD(",
        "type": "simple_replace",
        "description": "MOD is same in MySQL"
    },

    # === Date Functions ===
    "ADD_MONTHS": {
        "oracle": r"ADD_MONTHS\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "mysql": r"DATE_ADD(\1, INTERVAL \2 MONTH)",
        "type": "regex_replace",
        "description": "Convert ADD_MONTHS to DATE_ADD"
    },

    "MONTHS_BETWEEN": {
        "oracle": r"MONTHS_BETWEEN\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "mysql": r"TIMESTAMPDIFF(MONTH, \2, \1)",
        "type": "regex_replace",
        "description": "Convert MONTHS_BETWEEN to TIMESTAMPDIFF"
    },

    "LAST_DAY": {
        "oracle": r"LAST_DAY\s*\(",
        "mysql": "LAST_DAY(",
        "type": "simple_replace",
        "description": "LAST_DAY is same in MySQL"
    },

    "EXTRACT_YEAR": {
        "oracle": r"EXTRACT\s*\(\s*YEAR\s+FROM\s+([^)]+?)\s*\)",
        "mysql": r"YEAR(\1)",
        "type": "regex_replace",
        "description": "Convert EXTRACT(YEAR FROM ...) to YEAR()"
    },

    "EXTRACT_MONTH": {
        "oracle": r"EXTRACT\s*\(\s*MONTH\s+FROM\s+([^)]+?)\s*\)",
        "mysql": r"MONTH(\1)",
        "type": "regex_replace",
        "description": "Convert EXTRACT(MONTH FROM ...) to MONTH()"
    },

    "EXTRACT_DAY": {
        "oracle": r"EXTRACT\s*\(\s*DAY\s+FROM\s+([^)]+?)\s*\)",
        "mysql": r"DAY(\1)",
        "type": "regex_replace",
        "description": "Convert EXTRACT(DAY FROM ...) to DAY()"
    },

    "TO_DATE": {
        "oracle": r"TO_DATE\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
        "mysql": r"STR_TO_DATE(\1, \2)",
        "type": "regex_replace",
        "description": "Convert TO_DATE to STR_TO_DATE (format string needs conversion)"
    },

    "TO_CHAR_NUMBER": {
        "oracle": r"TO_CHAR\s*\(\s*([0-9.]+)\s*\)",
        "mysql": r"CAST(\1 AS CHAR)",
        "type": "regex_replace",
        "description": "Convert TO_CHAR(number) to CAST AS CHAR"
    },

    "TO_NUMBER": {
        "oracle": r"TO_NUMBER\s*\(\s*([^)]+?)\s*\)",
        "mysql": r"CAST(\1 AS DECIMAL)",
        "type": "regex_replace",
        "description": "Convert TO_NUMBER to CAST AS DECIMAL"
    },

    # === Aggregate Functions ===
    "LISTAGG": {
        "oracle": r"LISTAGG\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)\s*WITHIN\s+GROUP\s*\([^)]*\)",
        "mysql": r"GROUP_CONCAT(\1 SEPARATOR \2)",
        "type": "regex_replace",
        "description": "Convert LISTAGG to GROUP_CONCAT (remove WITHIN GROUP)"
    },

    # === Type Conversion ===
    "TO_CLOB": {
        "oracle": r"TO_CLOB\s*\(\s*([^)]+?)\s*\)",
        "mysql": r"CAST(\1 AS CHAR)",
        "type": "regex_replace",
        "description": "Convert TO_CLOB to CAST AS CHAR"
    },

    # === Oracle System Functions ===
    "SYS_CONTEXT_SESSION_USER": {
        "oracle": r"SYS_CONTEXT\s*\(\s*'USERENV'\s*,\s*'SESSION_USER'\s*\)",
        "mysql": "USER()",
        "type": "simple_replace",
        "description": "Convert SYS_CONTEXT(...SESSION_USER...) to USER()"
    },

    "USERENV_SESSIONID": {
        "oracle": r"USERENV\s*\(\s*'SESSIONID'\s*\)",
        "mysql": "CONNECTION_ID()",
        "type": "simple_replace",
        "description": "Convert USERENV('SESSIONID') to CONNECTION_ID()"
    },
}

# ==============================================================================
# DATA TYPE MAPPINGS
# ==============================================================================

DATA_TYPE_MAPPINGS: Dict[str, str] = {
    # String types
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "CHAR": "CHAR",
    "NCHAR": "CHAR",
    "CLOB": "LONGTEXT",
    "NCLOB": "LONGTEXT",

    # Numeric types
    "NUMBER": "DECIMAL",
    "INTEGER": "INT",
    "INT": "INT",
    "FLOAT": "FLOAT",
    "BINARY_FLOAT": "FLOAT",
    "BINARY_DOUBLE": "DOUBLE",

    # Date/Time types
    "DATE": "DATETIME",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMP",
    "TIMESTAMP WITH LOCAL TIME ZONE": "TIMESTAMP",

    # Binary types
    "BLOB": "LONGBLOB",
    "RAW": "VARBINARY",
    "LONG RAW": "LONGBLOB",

    # Special types
    "ROWID": "VARCHAR(18)",
    "XMLTYPE": "LONGTEXT",
}

# ==============================================================================
# SYNTAX RULES - Ordered by priority
# ==============================================================================

SYNTAX_RULES: List[Dict[str, Any]] = [
    # === DUAL table removal ===
    {
        "pattern": r"\s+FROM\s+DUAL\b",
        "replacement": "",
        "description": "Remove FROM DUAL"
    },

    # === ROWNUM conversions ===
    {
        "pattern": r"WHERE\s+ROWNUM\s*<=\s*(\d+)",
        "replacement": r"LIMIT \1",
        "description": "Convert ROWNUM <= N to LIMIT N"
    },
    {
        "pattern": r"WHERE\s+ROWNUM\s*=\s*1\b",
        "replacement": "LIMIT 1",
        "description": "Convert ROWNUM = 1 to LIMIT 1"
    },

    # === Sequence conversions ===
    {
        "pattern": r"(\w+)\.NEXTVAL\b",
        "replacement": r"LAST_INSERT_ID()",
        "description": "Convert sequence.NEXTVAL to LAST_INSERT_ID() - requires AUTO_INCREMENT column"
    },
    {
        "pattern": r"(\w+)\.CURRVAL\b",
        "replacement": r"LAST_INSERT_ID()",
        "description": "Convert sequence.CURRVAL to LAST_INSERT_ID()"
    },

    # === Stored procedure call ===
    {
        "pattern": r"\{\s*call\s+",
        "replacement": "CALL ",
        "description": "Remove curly braces from CALL statement"
    },

    # === MINUS to EXCEPT ===
    {
        "pattern": r"\bMINUS\b",
        "replacement": "EXCEPT",
        "description": "Convert MINUS to EXCEPT"
    },

    # === DELETE FROM (FROM is mandatory in MySQL) ===
    {
        "pattern": r"\bDELETE\s+(\w+)\s+WHERE\b",
        "replacement": r"DELETE FROM \1 WHERE",
        "description": "Add FROM keyword to DELETE statement"
    },

    # === Date literals ===
    {
        "pattern": r"DATE\s+'([^']+)'",
        "replacement": r"'\1'",
        "description": "Remove DATE literal prefix"
    },
    {
        "pattern": r"TIMESTAMP\s+'([^']+)'",
        "replacement": r"'\1'",
        "description": "Remove TIMESTAMP literal prefix"
    },

    # === Outer Join (+) - Warning only, manual conversion needed ===
    {
        "pattern": r"\(\+\)",
        "replacement": "/* (+) OUTER JOIN - MANUAL CONVERSION NEEDED */",
        "description": "Mark Oracle (+) outer join for manual conversion"
    },
]

# ==============================================================================
# SUBQUERY ALIAS PATTERNS (MySQL Mandatory)
# ==============================================================================

SUBQUERY_ALIAS_PATTERNS: List[Dict[str, Any]] = [
    {
        "pattern": r"FROM\s*\(\s*SELECT",
        "description": "All FROM (SELECT...) subqueries need ) AS alias",
        "mandatory": True
    },
    {
        "pattern": r"JOIN\s*\(\s*SELECT",
        "description": "All JOIN (SELECT...) subqueries need ) AS alias",
        "mandatory": True
    },
    {
        "pattern": r"LEFT\s+JOIN\s*\(\s*SELECT",
        "description": "All LEFT JOIN (SELECT...) subqueries need ) AS alias",
        "mandatory": True
    },
    {
        "pattern": r"RIGHT\s+JOIN\s*\(\s*SELECT",
        "description": "All RIGHT JOIN (SELECT...) subqueries need ) AS alias",
        "mandatory": True
    },
    {
        "pattern": r"INNER\s+JOIN\s*\(\s*SELECT",
        "description": "All INNER JOIN (SELECT...) subqueries need ) AS alias",
        "mandatory": True
    },
]

# ==============================================================================
# JDBC TYPE MAPPINGS (for MyBatis resultMap/parameterMap)
# ==============================================================================

JDBC_TYPE_MAPPINGS: Dict[str, str] = {
    # Numeric types
    "NUMBER": "DECIMAL",
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "SMALLINT": "SMALLINT",
    "TINYINT": "TINYINT",
    "FLOAT": "FLOAT",
    "DOUBLE": "DOUBLE",

    # String types
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "CHAR": "CHAR",
    "NCHAR": "CHAR",
    "CLOB": "LONGVARCHAR",
    "NCLOB": "LONGVARCHAR",

    # Date/Time types
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP_WITH_TIME_ZONE": "TIMESTAMP",
    "TIMESTAMP_WITH_LOCAL_TIME_ZONE": "TIMESTAMP",

    # Binary types
    "BLOB": "LONGVARBINARY",
    "RAW": "VARBINARY",
    "LONG_RAW": "LONGVARBINARY",

    # Special types
    "ROWID": "VARCHAR",
    "XMLTYPE": "LONGVARCHAR",
}

# ==============================================================================
# MYBATIS TYPE MAPPINGS (Java types for MyBatis)
# ==============================================================================

MYBATIS_TYPE_MAPPINGS: Dict[str, str] = {
    # Oracle-specific Java types → MySQL-compatible
    "oracle.sql.TIMESTAMP": "java.sql.Timestamp",
    "oracle.sql.DATE": "java.sql.Timestamp",
    "oracle.sql.CLOB": "java.lang.String",
    "oracle.sql.BLOB": "byte[]",
    "oracle.sql.ROWID": "java.lang.String",
}

# ==============================================================================
# DATE FORMAT MAPPINGS (Oracle format strings to MySQL)
# ==============================================================================

DATE_FORMAT_MAPPINGS: Dict[str, str] = {
    # Year
    "YYYY": "%Y",
    "YY": "%y",
    "RR": "%y",

    # Month
    "MM": "%m",
    "MON": "%b",
    "MONTH": "%M",

    # Day
    "DD": "%d",
    "DY": "%a",
    "DAY": "%W",

    # Time
    "HH24": "%H",
    "HH12": "%h",
    "HH": "%h",
    "MI": "%i",
    "SS": "%s",

    # AM/PM
    "AM": "%p",
    "PM": "%p",

    # Week/Quarter
    "WW": "%U",
    "Q": "",  # No direct equivalent in MySQL
    "D": "%w",
}

# ==============================================================================
# CONNECT BY PATTERNS (Hierarchical Queries)
# ==============================================================================

CONNECT_BY_PATTERNS: Dict[str, Any] = {
    "simple_hierarchy": {
        "description": "Simple START WITH...CONNECT BY PRIOR",
        "conversion_type": "recursive_cte",
        "template": """
WITH RECURSIVE hierarchy_cte AS (
    -- Anchor: root nodes
    SELECT {columns}, 1 as level
    FROM {table}
    WHERE {start_condition}

    UNION ALL

    -- Recursive: child nodes
    SELECT {child_columns}, h.level + 1
    FROM {table} child
    JOIN hierarchy_cte h ON {join_condition}
)
SELECT * FROM hierarchy_cte
"""
    }
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def convert_date_format(oracle_format: str) -> str:
    """Convert Oracle date format string to MySQL format string."""
    mysql_format = oracle_format
    # Sort by length descending to replace longer patterns first
    for oracle_token, mysql_token in sorted(DATE_FORMAT_MAPPINGS.items(), key=lambda x: -len(x[0])):
        mysql_format = mysql_format.replace(oracle_token, mysql_token)
    return mysql_format


def get_function_rule(function_name: str) -> Dict[str, Any]:
    """Get conversion rule for a specific Oracle function."""
    return FUNCTION_MAPPINGS.get(function_name.upper(), {})


def get_data_type_mapping(oracle_type: str) -> str:
    """Get MySQL equivalent for Oracle data type."""
    # Handle NUMBER(p,s) special cases
    if oracle_type.upper().startswith("NUMBER"):
        return "DECIMAL"
    return DATA_TYPE_MAPPINGS.get(oracle_type.upper(), oracle_type)


def get_jdbc_type_mapping(oracle_jdbc_type: str) -> str:
    """Get MySQL JDBC type for Oracle JDBC type."""
    return JDBC_TYPE_MAPPINGS.get(oracle_jdbc_type.upper(), oracle_jdbc_type)


def requires_subquery_alias(sql: str) -> bool:
    """Check if SQL contains subqueries that need aliases (MySQL mandatory)."""
    for pattern_rule in SUBQUERY_ALIAS_PATTERNS:
        if re.search(pattern_rule["pattern"], sql, re.IGNORECASE):
            return True
    return False
