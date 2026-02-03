"""Error handling utilities for SQL Test Agent."""

from enum import Enum
from typing import Optional

from models.enums import ErrorType
from .logger import get_logger

logger = get_logger(__name__)


class ErrorResolution(str, Enum):
    """Error resolution strategy."""
    ABORT = "abort"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SKIP_AND_CONTINUE = "skip_and_continue"
    TRY_ALTERNATIVE = "try_alternative"
    FLAG_FOR_MANUAL_REVIEW = "flag_for_manual_review"


class ErrorContext:
    """Context information for error handling."""
    
    def __init__(
        self,
        error_type: ErrorType,
        retry_count: int = 0,
        max_retries: int = 3,
        has_alternative: bool = False,
        sql_id: Optional[str] = None,
    ):
        self.error_type = error_type
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.has_alternative = has_alternative
        self.sql_id = sql_id
    
    def has_alternative_approach(self) -> bool:
        """Check if alternative approach is available."""
        return self.has_alternative


class ErrorHandler:
    """Centralized error handling logic."""
    
    MAX_CONNECTION_RETRIES = 3
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
    ) -> ErrorResolution:
        """
        Determine how to handle an error based on type and context.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            ErrorResolution strategy
        """
        self.logger.error(
            "handling_error",
            error_type=context.error_type,
            error_message=str(error),
            sql_id=context.sql_id,
            retry_count=context.retry_count,
        )
        
        if context.error_type == ErrorType.CONFIGURATION:
            # Fatal - cannot proceed
            self.logger.critical("configuration_error_abort", error=str(error))
            return ErrorResolution.ABORT
        
        elif context.error_type == ErrorType.CONNECTION:
            # Retry with backoff
            if context.retry_count < self.MAX_CONNECTION_RETRIES:
                self.logger.warning(
                    "connection_error_retry",
                    retry_count=context.retry_count,
                    max_retries=self.MAX_CONNECTION_RETRIES,
                )
                return ErrorResolution.RETRY_WITH_BACKOFF
            else:
                self.logger.error("connection_error_max_retries_reached")
                return ErrorResolution.ABORT
        
        elif context.error_type == ErrorType.EXECUTION:
            # Log and continue with next query
            self.logger.warning(
                "execution_error_skip",
                sql_id=context.sql_id,
                error=str(error),
            )
            return ErrorResolution.SKIP_AND_CONTINUE
        
        elif context.error_type == ErrorType.TRANSFORMATION:
            # Try alternative approach or flag for manual review
            if context.has_alternative_approach():
                self.logger.info("transformation_error_try_alternative")
                return ErrorResolution.TRY_ALTERNATIVE
            else:
                self.logger.warning("transformation_error_flag_manual_review")
                return ErrorResolution.FLAG_FOR_MANUAL_REVIEW
        
        elif context.error_type == ErrorType.COMPARISON:
            # Log and flag for review
            self.logger.warning("comparison_error_flag_manual_review")
            return ErrorResolution.FLAG_FOR_MANUAL_REVIEW
        
        elif context.error_type == ErrorType.SYSTEM:
            # Fatal system error
            self.logger.critical("system_error_abort", error=str(error))
            return ErrorResolution.ABORT
        
        else:
            # Unknown error - abort safely
            self.logger.critical("unknown_error_abort", error=str(error))
            return ErrorResolution.ABORT
    
    def log_error(self, error: Exception, context: ErrorContext) -> None:
        """
        Log error with full context.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
        """
        self.logger.error(
            "error_logged",
            error_type=context.error_type,
            error_message=str(error),
            error_class=error.__class__.__name__,
            sql_id=context.sql_id,
            retry_count=context.retry_count,
            has_alternative=context.has_alternative,
        )


class ConfigurationError(Exception):
    """Configuration error."""
    pass


class ConnectionError(Exception):
    """Database connection error."""
    pass


class ExecutionError(Exception):
    """SQL execution error."""
    pass


class ComparisonError(Exception):
    """Result comparison error."""
    pass


class TransformationError(Exception):
    """SQL transformation error."""
    pass
