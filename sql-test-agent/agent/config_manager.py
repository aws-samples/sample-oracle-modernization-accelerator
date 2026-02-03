"""Configuration management for SQL Test Agent."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from models.enums import DatabaseType, ValidationStatus
from utils.logger import get_logger, sanitize_credentials
from utils.error_handler import ConfigurationError

logger = get_logger(__name__)


class DatabaseCredentials:
    """Database connection credentials."""
    
    def __init__(self, db_type: DatabaseType):
        self.db_type = db_type
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.database: Optional[str] = None
        self.connect_string: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if credentials are valid."""
        if self.db_type == DatabaseType.ORACLE:
            return all([self.username, self.password, self.connect_string])
        elif self.db_type == DatabaseType.POSTGRESQL:
            return all([self.username, self.password, self.host, self.port, self.database])
        elif self.db_type == DatabaseType.MYSQL:
            return all([self.username, self.password, self.host, self.port, self.database])
        return False
    
    def __repr__(self) -> str:
        """String representation with masked password."""
        return f"DatabaseCredentials(db_type={self.db_type}, username={self.username}, password=***)"


class RetryConfig:
    """Retry configuration."""
    
    def __init__(self):
        self.max_retries: int = 3
        self.retry_delay_seconds: int = 2
        self.min_confidence_threshold: float = 0.7


class ComparisonConfig:
    """Comparison configuration."""
    
    def __init__(self):
        self.acceptable_pass_rate: float = 0.95
        self.timeout_seconds: int = 30
        self.normalize_numeric_precision: bool = True
        self.normalize_datetime_format: bool = True
        self.normalize_string_trim: bool = True
        self.normalize_string_case_sensitive: bool = False


class ExecutionConfig:
    """Execution configuration."""
    
    def __init__(self):
        self.batch_size: int = 10
        self.connection_pool_size: int = 5
        self.query_timeout_seconds: int = 60
        self.enable_parallel_execution: bool = True


class LLMConfig:
    """LLM configuration."""
    
    def __init__(self):
        self.provider: str = "anthropic"  # or "openai"
        self.api_key: Optional[str] = None
        self.model: str = "claude-3-5-sonnet-20241022"
        self.temperature: float = 0.1
        self.max_tokens: int = 4096


class PathConfig:
    """File path configuration."""
    
    def __init__(self):
        # OMA Base Configuration
        self.oma_base_dir: Optional[Path] = None
        self.application_name: Optional[str] = None
        self.language: str = "en"
        
        # Source and Target DBMS Types
        self.source_dbms_type: str = "orcl"
        self.target_dbms_type: str = "postgres"
        
        # Mapper Directories
        self.source_mapper_directory: Optional[Path] = None
        self.target_mapper_directory: Optional[Path] = None
        self.mapper_directory: Optional[Path] = None  # Default to source
        
        # Test and Transform Folders
        self.test_folder: Optional[Path] = None
        self.parameters_file: Optional[Path] = None
        self.sql_transformer_path: Optional[Path] = None
        
        # Logs and Reports
        self.log_file_path: Path = Path("./logs/agent.log")
        self.report_output_directory: Path = Path("./reports")


class LoggingConfig:
    """Logging configuration."""
    
    def __init__(self):
        self.log_level: str = "INFO"
        self.log_file_path: Path = Path("./logs/agent.log")
        self.include_sql: bool = True
        self.include_bind_variables: bool = False
        self.max_file_size_mb: int = 100
        self.max_backup_count: int = 10


class ReportConfig:
    """Report configuration."""
    
    def __init__(self):
        self.output_directory: Path = Path("./reports")
        self.formats: list = ["json", "html"]
        self.include_transformation_history: bool = True
        self.include_performance_metrics: bool = True


class SecurityConfig:
    """Security configuration."""
    
    def __init__(self):
        self.enable_ssl_connections: bool = True
        self.sanitize_error_messages: bool = True
        self.encrypt_credentials: bool = False


class Config:
    """Main configuration container."""
    
    def __init__(self):
        self.oracle_credentials = DatabaseCredentials(DatabaseType.ORACLE)
        self.postgresql_credentials = DatabaseCredentials(DatabaseType.POSTGRESQL)
        self.mysql_credentials = DatabaseCredentials(DatabaseType.MYSQL)
        self.retry_config = RetryConfig()
        self.comparison_config = ComparisonConfig()
        self.execution_config = ExecutionConfig()
        self.llm_config = LLMConfig()
        self.path_config = PathConfig()
        self.logging_config = LoggingConfig()
        self.report_config = ReportConfig()
        self.security_config = SecurityConfig()


class ConfigManager:
    """Manages application configuration from OS environment variables."""
    
    def __init__(self):
        """
        Initialize configuration manager.
        Reads all configuration from OS environment variables.
        """
        self.logger = get_logger(__name__)
        self.config = Config()
        
    def load_config(self) -> Config:
        """
        Load configuration from OS environment variables.
        
        Returns:
            Loaded configuration
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.logger.info("loading_configuration_from_environment")
        
        # Load all configuration from environment variables
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info("configuration_loaded_successfully")
        return self.config
    
    def _load_from_environment(self) -> None:
        """Load configuration from OS environment variables."""
        
        # Oracle credentials (from oma.properties)
        self.config.oracle_credentials.username = os.getenv("ORACLE_SVC_USER")
        self.config.oracle_credentials.password = os.getenv("ORACLE_SVC_PASSWORD")
        self.config.oracle_credentials.connect_string = os.getenv("ORACLE_SVC_CONNECT_STRING")
        
        # Additional Oracle connection details
        oracle_host = os.getenv("ORACLE_HOST")
        oracle_port = os.getenv("ORACLE_PORT")
        oracle_sid = os.getenv("ORACLE_SID")
        
        if oracle_host and oracle_port and oracle_sid:
            self.config.oracle_credentials.host = oracle_host
            self.config.oracle_credentials.port = int(oracle_port)
            self.config.oracle_credentials.database = oracle_sid
        
        # PostgreSQL credentials (from oma.properties)
        self.config.postgresql_credentials.username = os.getenv("PGUSER") or os.getenv("PG_SVC_USER")
        self.config.postgresql_credentials.password = os.getenv("PGPASSWORD") or os.getenv("PG_SVC_PASSWORD")
        self.config.postgresql_credentials.host = os.getenv("PGHOST", "localhost")
        self.config.postgresql_credentials.port = int(os.getenv("PGPORT", "5432"))
        self.config.postgresql_credentials.database = os.getenv("PGDATABASE")
        
        # MySQL credentials (if configured)
        self.config.mysql_credentials.username = os.getenv("MYSQL_USER")
        self.config.mysql_credentials.password = os.getenv("MYSQL_PASSWORD")
        self.config.mysql_credentials.host = os.getenv("MYSQL_HOST", "localhost")
        self.config.mysql_credentials.port = int(os.getenv("MYSQL_TCP_PORT", "3306"))
        self.config.mysql_credentials.database = os.getenv("MYSQL_DATABASE")
        
        # OMA Base Configuration
        oma_base_dir = os.getenv("OMA_BASE_DIR")
        application_name = os.getenv("APPLICATION_NAME")
        
        if oma_base_dir:
            self.config.path_config.oma_base_dir = Path(oma_base_dir)
        
        if application_name:
            self.config.path_config.application_name = application_name
        
        # Source and Target DBMS Types
        source_dbms = os.getenv("SOURCE_DBMS_TYPE", "orcl")
        target_dbms = os.getenv("TARGET_DBMS_TYPE", "postgres")
        
        self.config.path_config.source_dbms_type = source_dbms
        self.config.path_config.target_dbms_type = target_dbms
        
        # Mapper Folders (from oma.properties)
        source_mapper = os.getenv("SOURCE_SQL_MAPPER_FOLDER")
        target_mapper = os.getenv("TARGET_SQL_MAPPER_FOLDER")
        
        if source_mapper:
            self.config.path_config.source_mapper_directory = Path(source_mapper)
        
        if target_mapper:
            self.config.path_config.target_mapper_directory = Path(target_mapper)
        
        # Use SOURCE_SQL_MAPPER_FOLDER as default mapper_directory
        if source_mapper:
            self.config.path_config.mapper_directory = Path(source_mapper)
        
        # Test Folder
        test_folder = os.getenv("TEST_FOLDER")
        if test_folder:
            self.config.path_config.test_folder = Path(test_folder)
            # Default parameters file location
            self.config.path_config.parameters_file = Path(test_folder) / "parameters.properties"
        
        # Application Transform Folder
        app_transform_folder = os.getenv("APP_TRANSFORM_FOLDER")
        if app_transform_folder:
            self.config.path_config.sql_transformer_path = Path(app_transform_folder)
        
        # Logs Folders
        test_logs = os.getenv("TEST_LOGS_FOLDER")
        if test_logs:
            self.config.logging_config.log_file_path = Path(test_logs) / "agent.log"
        
        app_logs = os.getenv("APP_LOGS_FOLDER")
        if app_logs:
            self.config.report_config.output_directory = Path(app_logs) / "reports"
        
        # Agent Configuration (with defaults)
        self.config.retry_config.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.config.retry_config.retry_delay_seconds = int(os.getenv("RETRY_DELAY_SECONDS", "2"))
        self.config.retry_config.min_confidence_threshold = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.7"))
        
        # Comparison Configuration
        self.config.comparison_config.acceptable_pass_rate = float(os.getenv("ACCEPTABLE_PASS_RATE", "0.95"))
        self.config.comparison_config.timeout_seconds = int(os.getenv("COMPARISON_TIMEOUT_SECONDS", "30"))
        self.config.comparison_config.normalize_numeric_precision = os.getenv("NORMALIZE_NUMERIC_PRECISION", "true").lower() == "true"
        self.config.comparison_config.normalize_datetime_format = os.getenv("NORMALIZE_DATETIME_FORMAT", "true").lower() == "true"
        self.config.comparison_config.normalize_string_trim = os.getenv("NORMALIZE_STRING_TRIM", "true").lower() == "true"
        self.config.comparison_config.normalize_string_case_sensitive = os.getenv("NORMALIZE_STRING_CASE_SENSITIVE", "false").lower() == "true"
        
        # Execution Configuration
        self.config.execution_config.batch_size = int(os.getenv("BATCH_SIZE", "10"))
        self.config.execution_config.connection_pool_size = int(os.getenv("CONNECTION_POOL_SIZE", "5"))
        self.config.execution_config.query_timeout_seconds = int(os.getenv("QUERY_TIMEOUT_SECONDS", "60"))
        self.config.execution_config.enable_parallel_execution = os.getenv("ENABLE_PARALLEL_EXECUTION", "true").lower() == "true"
        
        # LLM Configuration
        self.config.llm_config.provider = os.getenv("LLM_PROVIDER", "anthropic")
        self.config.llm_config.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.config.llm_config.model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
        self.config.llm_config.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.config.llm_config.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        
        # Logging Configuration
        self.config.logging_config.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.config.logging_config.include_sql = os.getenv("LOG_INCLUDE_SQL", "true").lower() == "true"
        self.config.logging_config.include_bind_variables = os.getenv("LOG_INCLUDE_BIND_VARIABLES", "false").lower() == "true"
        self.config.logging_config.max_file_size_mb = int(os.getenv("LOG_MAX_FILE_SIZE_MB", "100"))
        self.config.logging_config.max_backup_count = int(os.getenv("LOG_MAX_BACKUP_COUNT", "10"))
        
        # Report Configuration
        report_format = os.getenv("REPORT_FORMAT", "json,html")
        self.config.report_config.formats = [f.strip() for f in report_format.split(",")]
        self.config.report_config.include_transformation_history = os.getenv("REPORT_INCLUDE_TRANSFORMATION_HISTORY", "true").lower() == "true"
        self.config.report_config.include_performance_metrics = os.getenv("REPORT_INCLUDE_PERFORMANCE_METRICS", "true").lower() == "true"
        
        # Security Configuration
        self.config.security_config.enable_ssl_connections = os.getenv("ENABLE_SSL_CONNECTIONS", "true").lower() == "true"
        self.config.security_config.sanitize_error_messages = os.getenv("SANITIZE_ERROR_MESSAGES", "true").lower() == "true"
        self.config.security_config.encrypt_credentials = os.getenv("ENCRYPT_CREDENTIALS", "false").lower() == "true"
        
        # Language setting
        language = os.getenv("LANGUAGE", "en")
        self.config.path_config.language = language
        
        self.logger.debug("environment_variables_loaded")
    
    def _load_properties_file(self) -> None:
        """Deprecated: Configuration is now loaded from environment variables only."""
        pass
    
    def _validate_config(self) -> None:
        """
        Validate configuration completeness and correctness.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        errors = []
        
        # Validate at least one database is configured
        has_db = (
            self.config.oracle_credentials.is_valid() or
            self.config.postgresql_credentials.is_valid() or
            self.config.mysql_credentials.is_valid()
        )
        if not has_db:
            errors.append("At least one database must be configured")
        
        # Validate LLM configuration
        if not self.config.llm_config.api_key:
            errors.append("LLM API key is required (ANTHROPIC_API_KEY or OPENAI_API_KEY)")
        
        # Validate numeric ranges
        if self.config.retry_config.max_retries < 1:
            errors.append("max_retries must be >= 1")
        
        if not 0.0 <= self.config.retry_config.min_confidence_threshold <= 1.0:
            errors.append("min_confidence_threshold must be between 0.0 and 1.0")
        
        if not 0.0 <= self.config.comparison_config.acceptable_pass_rate <= 1.0:
            errors.append("acceptable_pass_rate must be between 0.0 and 1.0")
        
        if self.config.execution_config.batch_size < 1:
            errors.append("batch_size must be >= 1")
        
        if self.config.execution_config.connection_pool_size < 1:
            errors.append("connection_pool_size must be >= 1")
        
        # Log validation results
        if errors:
            for error in errors:
                self.logger.error("configuration_validation_error", error=error)
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
        
        self.logger.info("configuration_validated_successfully")
    
    def get_db_credentials(self, db_type: DatabaseType) -> DatabaseCredentials:
        """
        Get database credentials for specified type.
        
        Args:
            db_type: Database type
            
        Returns:
            Database credentials
            
        Raises:
            ConfigurationError: If credentials not configured
        """
        if db_type == DatabaseType.ORACLE:
            creds = self.config.oracle_credentials
        elif db_type == DatabaseType.POSTGRESQL:
            creds = self.config.postgresql_credentials
        elif db_type == DatabaseType.MYSQL:
            creds = self.config.mysql_credentials
        else:
            raise ConfigurationError(f"Unknown database type: {db_type}")
        
        if not creds.is_valid():
            raise ConfigurationError(f"Credentials for {db_type} are not configured")
        
        return creds
    
    def get_retry_config(self) -> RetryConfig:
        """Get retry configuration."""
        return self.config.retry_config
    
    def get_comparison_config(self) -> ComparisonConfig:
        """Get comparison configuration."""
        return self.config.comparison_config
    
    def get_execution_config(self) -> ExecutionConfig:
        """Get execution configuration."""
        return self.config.execution_config
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        return self.config.llm_config
    
    def get_path_config(self) -> PathConfig:
        """Get path configuration."""
        return self.config.path_config
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.config.logging_config
    
    def get_report_config(self) -> ReportConfig:
        """Get report configuration."""
        return self.config.report_config
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self.config.security_config
