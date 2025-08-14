"""
Centralized logging module for the RFQ-Sender application.

This module provides standardized logging configuration for the entire application.
It ensures consistent log formats, file locations, and rotation policies.

Example Usage:
```python
from utils.logging import get_logger

# Get a logger with default settings
logger = get_logger(__name__)

# Log messages at appropriate levels
logger.info("Operation completed successfully")
logger.warning("Resource is running low")
logger.error("Failed to process request", exc_info=True)  # Include exception info
```
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

from core.config import LoggingConfig

# Re-export the LoggingConfig class for direct access
__all__ = ["get_logger", "configure_root_logger", "LoggingConfig"]


def get_logger(
    logger_name: Optional[str] = None,
    log_file: Optional[str] = None,
    level: Optional[int] = None
) -> logging.Logger:
    """
    Get a configured logger instance using the standardized configuration.
    
    This is the primary function to use when obtaining a logger in any module.
    
    Args:
        logger_name: Name of the logger (defaults to module name if None)
        log_file: Name of the log file (defaults to logger_name.log if None)
        level: Logging level (defaults to LoggingConfig.DEFAULT_LEVEL if None)
        
    Returns:
        Configured logger instance
    """
    return LoggingConfig.setup_logging(logger_name, log_file, level)


def configure_root_logger(level: int = logging.INFO) -> None:
    """
    Configure the root logger with standardized settings.
    
    This function should be called once at application startup.
    
    Args:
        level: Logging level for the root logger
        
    Returns:
        None
    """
    # Ensure logs directory exists
    logs_dir = Path(LoggingConfig.LOGS_DIR)
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        LoggingConfig.LOG_FORMAT, 
        LoggingConfig.DATE_FORMAT
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler with rotation
    file_path = os.path.join(LoggingConfig.LOGS_DIR, "app.log")
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=LoggingConfig.MAX_LOG_SIZE,
        backupCount=LoggingConfig.BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)