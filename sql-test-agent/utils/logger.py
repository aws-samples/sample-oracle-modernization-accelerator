"""Logging configuration for SQL Test Agent."""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    include_sql: bool = True,
    include_bind_variables: bool = False,
) -> None:
    """
    Set up structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        include_sql: Whether to include SQL in logs
        include_bind_variables: Whether to include bind variables in logs
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        logging.root.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if sys.stdout.isatty() else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def sanitize_sql(sql: str, max_length: int = 200) -> str:
    """
    Sanitize SQL for logging.
    
    Args:
        sql: SQL query string
        max_length: Maximum length to log
        
    Returns:
        Sanitized SQL string
    """
    if len(sql) > max_length:
        return sql[:max_length] + "..."
    return sql


def sanitize_credentials(text: str, credentials: list) -> str:
    """
    Remove credentials from text.
    
    Args:
        text: Text that may contain credentials
        credentials: List of credential strings to remove
        
    Returns:
        Sanitized text
    """
    sanitized = text
    for cred in credentials:
        if cred:
            sanitized = sanitized.replace(str(cred), "***")
    return sanitized
