"""Enumerations for SQL Test Agent."""

from enum import Enum


class DatabaseType(str, Enum):
    """Database type enumeration."""
    ORACLE = "oracle"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class SQLType(str, Enum):
    """SQL statement type enumeration."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MERGE = "MERGE"
    UNKNOWN = "UNKNOWN"


class QueryStatus(str, Enum):
    """Query execution status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class DifferenceCategory(str, Enum):
    """Result difference category."""
    DATA_MISMATCH = "data_mismatch"
    ROW_COUNT_MISMATCH = "row_count_mismatch"
    COLUMN_ORDER = "column_order"
    TYPE_CONVERSION = "type_conversion"
    NULL_HANDLING = "null_handling"


class DifferenceSeverity(str, Enum):
    """Difference severity level."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class ValidationStatus(str, Enum):
    """Validation status for bind variables."""
    VALID = "valid"
    MISSING_PARAMETERS = "missing_parameters"
    TYPE_MISMATCH = "type_mismatch"
    INVALID_FORMAT = "invalid_format"


class ErrorType(str, Enum):
    """Error type classification."""
    CONFIGURATION = "configuration"
    CONNECTION = "connection"
    EXECUTION = "execution"
    COMPARISON = "comparison"
    TRANSFORMATION = "transformation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class TransformationStatus(str, Enum):
    """SQL transformation status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class FinalStatus(str, Enum):
    """Final validation status for a query."""
    PASSED = "passed"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
