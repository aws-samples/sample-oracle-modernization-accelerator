"""Data models for SQL Test Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import (
    DatabaseType,
    DifferenceCategory,
    DifferenceSeverity,
    FinalStatus,
    QueryStatus,
    SQLType,
    TransformationStatus,
    ValidationStatus,
)


@dataclass
class BindVariables:
    """Bind variables loaded from parameters.properties."""
    parameters: Dict[str, Any]
    source_file: str
    validation_status: ValidationStatus
    missing_parameters: List[str] = field(default_factory=list)
    type_mismatches: List[str] = field(default_factory=list)


@dataclass
class SQLQuery:
    """SQL query from MyBatis mapper."""
    sql_id: str
    mapper_file: str
    sql_text: str
    sql_type: SQLType
    bind_parameters: List[str]
    target_db_type: DatabaseType


@dataclass
class QueryResult:
    """Result of SQL query execution."""
    sql_id: str
    db_type: DatabaseType
    status: QueryStatus
    result_set: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: int
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Difference:
    """Difference between source and target results."""
    type: DifferenceCategory
    severity: DifferenceSeverity
    location: str
    source_value: str
    target_value: str
    description: str


@dataclass
class ComparisonResult:
    """Result of comparing source and target query results."""
    sql_id: str
    matches: bool
    difference_category: Optional[DifferenceCategory]
    differences: List[Difference]
    source_result: QueryResult
    target_result: QueryResult
    normalized_source: str
    normalized_target: str


@dataclass
class TransformationGuidance:
    """Guidance for SQL transformation."""
    sql_id: str
    target_db_type: DatabaseType
    specific_instructions: List[str]
    functions_to_replace: Dict[str, str]
    syntax_changes: List[str]
    expected_outcome: str
    alternative_approaches: List[str] = field(default_factory=list)


@dataclass
class Analysis:
    """LLM analysis of SQL differences."""
    sql_id: str
    root_cause: str
    confidence_score: float
    affected_components: List[str]
    explanation: str
    transformation_guidance: TransformationGuidance


@dataclass
class TransformationResult:
    """Result of SQL transformation."""
    sql_id: str
    status: TransformationStatus
    transformed_sql: str
    changes_made: List[str]
    warnings: List[str]
    error_message: Optional[str] = None
    mapper_file_updated: bool = False


@dataclass
class TransformationAttempt:
    """Single transformation attempt."""
    iteration: int
    guidance: TransformationGuidance
    result: TransformationResult
    comparison_after: Optional[ComparisonResult] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QueryValidationResult:
    """Validation result for a single query."""
    sql_id: str
    final_status: FinalStatus
    iterations: int
    transformation_attempts: List[TransformationAttempt]
    final_comparison: ComparisonResult
    resolution: Optional[str] = None


@dataclass
class ValidationReport:
    """Final validation report."""
    total_queries: int
    passed_queries: int
    failed_queries: int
    queries_requiring_manual_review: int
    convergence_achieved: bool
    iterations_performed: int
    execution_time_seconds: float
    query_results: List[QueryValidationResult]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Performance metrics for the validation process."""
    total_execution_time_seconds: float
    average_query_time_ms: float
    database_connection_time_ms: float
    comparison_time_ms: float
    transformation_time_ms: float
    llm_analysis_time_ms: float
    queries_per_second: float
    memory_usage_mb: float
