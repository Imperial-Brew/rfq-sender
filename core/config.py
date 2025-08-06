"""
Configuration module for the RFQ-Sender application.

This module centralizes all configuration settings, including:
1. Environment variables
2. File paths
3. Application constants

All configuration values should be accessed through this module
rather than being scattered throughout the codebase.
"""

import os
import logging
import logging.handlers
import sys
from pathlib import Path
import streamlit as st
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent

# Logging configuration
class LoggingConfig:
    """
    Container for logging configuration settings.
    
    This class provides standardized logging configuration for the entire application.
    It ensures consistent log formats, file locations, and rotation policies.
    
    Log Level Usage Guidelines:
    - DEBUG: Detailed information, typically useful only for diagnosing problems
    - INFO: Confirmation that things are working as expected
    - WARNING: Indication that something unexpected happened, or may happen in the near future
    - ERROR: Due to a more serious problem, the software has not been able to perform a function
    - CRITICAL: A serious error indicating the program itself may be unable to continue running
    
    Example Usage:
    ```python
    from core.config import LoggingConfig
    
    # Get a logger with default settings
    logger = LoggingConfig.setup_logging(__name__)
    
    # Log messages at appropriate levels
    logger.info("Operation completed successfully")
    logger.warning("Resource is running low")
    logger.error("Failed to process request", exc_info=True)  # Include exception info
    ```
    """
    
    # Default log levels
    DEFAULT_LEVEL = logging.INFO
    DEBUG_LEVEL = logging.DEBUG
    
    # Log format
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Log directory
    LOGS_DIR = os.path.join(ROOT_DIR, "logs")
    
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Maximum log file size (10 MB)
    MAX_LOG_SIZE = 10 * 1024 * 1024
    
    # Number of backup log files to keep
    BACKUP_COUNT = 5
    
    @classmethod
    def setup_logging(cls, 
                      logger_name: Optional[str] = None, 
                      log_file: Optional[str] = None,
                      level: Optional[int] = None) -> logging.Logger:
        """
        Set up logging with standardized configuration.
        
        Args:
            logger_name: Name of the logger (defaults to module name if None)
            log_file: Name of the log file (defaults to logger_name.log if None)
            level: Logging level (defaults to DEFAULT_LEVEL if None)
            
        Returns:
            Configured logger instance
        """
        # Get the caller's module name if logger_name is not provided
        if logger_name is None:
            import inspect
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            logger_name = module.__name__ if module else "__main__"
        
        # Default log file name based on logger name
        if log_file is None:
            # Extract the last part of the logger name (after the last dot)
            module_name = logger_name.split('.')[-1]
            log_file = f"{module_name}.log"
        
        # Use default level if not specified
        if level is None:
            level = cls.DEFAULT_LEVEL
        
        # Create logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
        # Clear any existing handlers to avoid duplicates
        if logger.handlers:
            logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Create file handler with rotation
        file_path = os.path.join(cls.LOGS_DIR, log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=cls.MAX_LOG_SIZE,
            backupCount=cls.BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

# Set up the config module's logger
logger = LoggingConfig.setup_logging(__name__, "config.log")

# Load environment variables from .env file
def load_environment(env_file: Optional[str] = None) -> None:
    try:
        # First try to load from .env file
        dotenv_path = env_file or os.path.join(ROOT_DIR, ".env")
        logger.info(f"Looking for .env file at: {dotenv_path}")
        if os.path.exists(dotenv_path):
            logger.info(f".env file found at {dotenv_path}")
            load_dotenv(dotenv_path=dotenv_path)
            logger.info(f"Environment variables loaded from {dotenv_path}")
        else:
            logger.warning(f".env file not found at {dotenv_path}")

        # Then try to load from Streamlit secrets
        if hasattr(st, 'secrets'):
            for key, value in st.secrets.items():
                if isinstance(value, dict):  # Handle nested secrets
                    for subkey, subvalue in value.items():
                        full_key = f"{key}_{subkey}".upper()
                        os.environ[full_key] = str(subvalue)
                else:
                    os.environ[key.upper()] = str(value)
            logger.info("Environment variables loaded from Streamlit secrets")
    except Exception as e:
        logger.warning(f"Failed to load environment variables: {str(e)}")

# Load environment variables on module import
load_environment()

# File paths
class Paths:
    """Container for all file paths used in the application."""
    
    # Vendor-related paths
    VENDOR_FILE = os.path.join(ROOT_DIR, "config", "vendors.json")
    VENDOR_OPTIONS_FILE = os.path.join(ROOT_DIR, "docs", "OS", "vendor_options.yaml")
    
    # Queue-related paths
    QUEUE_PATH = os.path.join(ROOT_DIR, "docs", "queue.csv")
    
    # Specs-related paths
    SPECS_PATH = os.path.join(ROOT_DIR, "docs", "OS", "spec_lists", "FamiliarSpecs.csv")
    
    # Email template paths
    EMAIL_TEMPLATE_PATH = os.path.join(ROOT_DIR, "templates", "rfq_email_template.html")
    if not os.path.exists(EMAIL_TEMPLATE_PATH):
        EMAIL_TEMPLATE_PATH = os.path.join(ROOT_DIR, "config", "templates", "rfq_email_template.html")
    
    # Logs directory
    LOGS_DIR = os.path.join(ROOT_DIR, "logs")
    
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)

# Exchange settings
class ExchangeConfig:
    """Container for Exchange email configuration."""
    
    USERNAME = os.environ.get("EXCHANGE_USERNAME", "")
    PASSWORD = os.environ.get("EXCHANGE_PASSWORD", "")
    SERVER = os.environ.get("EXCHANGE_SERVER", "outlook.office365.com")
    FROM_EMAIL = os.environ.get("EXCHANGE_FROM_EMAIL", "")
    CC_EMAIL = os.environ.get("EXCHANGE_CC_EMAIL", "")
    
    @classmethod
    def get_settings(cls) -> Dict[str, str]:
        """
        Get Exchange settings as a dictionary.
        
        Returns:
            Dictionary with Exchange settings
        """
        return {
            "username": cls.USERNAME,
            "from_email": cls.FROM_EMAIL,
            "cc": cls.CC_EMAIL
        }
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required Exchange settings are present.
        
        Returns:
            True if all required settings are present, False otherwise
        """
        if not cls.USERNAME:
            logger.warning("EXCHANGE_USERNAME is not set")
            return False
        if not cls.PASSWORD:
            logger.warning("EXCHANGE_PASSWORD is not set")
            return False
        return True

# Company information
class CompanyInfo:
    """Container for company information used in emails."""
    
    NAME = os.environ.get("COMPANY_NAME", "Your Company")
    LOGO_URL = os.environ.get("COMPANY_LOGO_URL", "")
    SENDER_NAME = os.environ.get("SENDER_NAME", "")
    SENDER_TITLE = os.environ.get("SENDER_TITLE", "")
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
    SENDER_PHONE = os.environ.get("SENDER_PHONE", "")
    ADDRESS = os.environ.get("COMPANY_ADDRESS", "")
    
    @classmethod
    def get_info(cls) -> Dict[str, str]:
        """
        Get company information as a dictionary.
        
        Returns:
            Dictionary with company information
        """
        return {
            "name": cls.NAME,
            "logo_url": cls.LOGO_URL,
            "sender_name": cls.SENDER_NAME,
            "sender_title": cls.SENDER_TITLE,
            "sender_email": cls.SENDER_EMAIL,
            "sender_phone": cls.SENDER_PHONE,
            "address": cls.ADDRESS
        }

# Security settings
class SecurityConfig:
    """Container for security-related configuration."""
    
    ENABLE_CUI_PROTECTION = os.environ.get("ENABLE_CUI_PROTECTION", "true").lower() == "true"
    CUI_WARNING = os.environ.get(
        "CUI_WARNING",
        "CONTROLLED UNCLASSIFIED INFORMATION (CUI)"
    )

# Application settings
class AppConfig:
    """Container for application-specific settings."""
    
    # Default number of items to display per page
    ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", "10"))
    
    # Debug mode
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Validation helper functions
def validate_file_paths(validation_issues: list) -> None:
    """
    Validate that critical file paths exist or can be created.
    
    Args:
        validation_issues: List to append validation issues to
    """
    # Check if vendor file exists
    if not os.path.exists(Paths.VENDOR_FILE):
        validation_issues.append(f"Vendor file not found: {Paths.VENDOR_FILE}")
    
    # Check if vendor options file exists
    if not os.path.exists(Paths.VENDOR_OPTIONS_FILE):
        validation_issues.append(f"Vendor options file not found: {Paths.VENDOR_OPTIONS_FILE}")
    
    # Check if specs path exists
    if not os.path.exists(Paths.SPECS_PATH):
        validation_issues.append(f"Specs file not found: {Paths.SPECS_PATH}")
    
    # Check if email template exists
    if not os.path.exists(Paths.EMAIL_TEMPLATE_PATH):
        validation_issues.append(f"Email template not found: {Paths.EMAIL_TEMPLATE_PATH}")
    
    # Queue path is created if it doesn't exist, so we don't validate it here
    # But we do check if its parent directory exists
    queue_dir = os.path.dirname(Paths.QUEUE_PATH)
    if not os.path.exists(queue_dir):
        validation_issues.append(f"Queue directory not found: {queue_dir}")

def validate_company_info(validation_issues: list) -> None:
    """
    Validate that critical company information is set.
    
    Args:
        validation_issues: List to append validation issues to
    """
    # Check if company name is set
    if not CompanyInfo.NAME or CompanyInfo.NAME == "Your Company":
        validation_issues.append("Company name is not set or is using default value")
    
    # Check if sender email is set
    if not CompanyInfo.SENDER_EMAIL:
        validation_issues.append("Sender email is not set")
    elif "@" not in CompanyInfo.SENDER_EMAIL:
        validation_issues.append(f"Sender email is invalid: {CompanyInfo.SENDER_EMAIL}")
    
    # Check if sender name is set
    if not CompanyInfo.SENDER_NAME:
        validation_issues.append("Sender name is not set")

def validate_security_settings(validation_issues: list) -> None:
    """
    Validate security settings.
    
    Args:
        validation_issues: List to append validation issues to
    """
    # Check if CUI protection is enabled but warning text is empty
    if SecurityConfig.ENABLE_CUI_PROTECTION and not SecurityConfig.CUI_WARNING:
        validation_issues.append("CUI protection is enabled but warning text is empty")

# Initialize configuration
def init_config() -> None:
    """
    Initialize configuration and validate settings.
    
    This function should be called at application startup.
    It sets up logging and loads environment variables.
    It validates critical settings and logs warnings for missing or invalid settings.
    
    Returns:
        None
    
    Raises:
        FileNotFoundError: If critical file paths don't exist and create_missing=False
    """
    # Load environment variables
    load_environment()
    
    # Track validation status
    validation_issues = []
    
    # Validate Exchange settings
    if not ExchangeConfig.validate():
        validation_issues.append("Exchange configuration is incomplete")
    
    # Validate file paths
    validate_file_paths(validation_issues)
    
    # Validate company information
    validate_company_info(validation_issues)
    
    # Validate security settings
    validate_security_settings(validation_issues)
    
    # Log validation results
    if validation_issues:
        logger.warning(f"Configuration validation found {len(validation_issues)} issues:")
        for i, issue in enumerate(validation_issues, 1):
            logger.warning(f"  {i}. {issue}")
        logger.warning("Application may not function correctly until these issues are resolved")
    else:
        logger.info("All critical settings validated successfully")
    
    # Log configuration status
    logger.info("Configuration initialized")
    
    # Log paths for debugging
    if AppConfig.DEBUG:
        logger.debug(f"VENDOR_FILE: {Paths.VENDOR_FILE}")
        logger.debug(f"VENDOR_OPTIONS_FILE: {Paths.VENDOR_OPTIONS_FILE}")
        logger.debug(f"QUEUE_PATH: {Paths.QUEUE_PATH}")
        logger.debug(f"SPECS_PATH: {Paths.SPECS_PATH}")
        logger.debug(f"EMAIL_TEMPLATE_PATH: {Paths.EMAIL_TEMPLATE_PATH}")
    
    return None

# Call init_config if this module is run directly
if __name__ == "__main__":
    init_config()