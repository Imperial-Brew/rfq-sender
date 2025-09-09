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
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv

# Try to import streamlit, but don't fail if it's not available
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    # Create a dummy st object to avoid errors
    class DummyStreamlit:
        secrets = {}
    st = DummyStreamlit()

# Set up a basic logger first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the project root directory
ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent)
logger.info(f"Using ROOT_DIR: {ROOT_DIR}")

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

    # Note: We don't create the directory here at class definition time
    # Instead, we'll create it when the logging is actually set up
    # This prevents errors when the class is imported but logging isn't used

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
        # Ensure logs directory exists before setting up logging
        try:
            os.makedirs(cls.LOGS_DIR, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create logs directory: {e}")
            # Continue with console logging only

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
        
        # Prevent double-logging via root handlers
        # When a module logger has its own handlers and propagate=True (default),
        # each record is handled twice: by this logger and again by the root.
        # Setting propagate=False ensures records are handled only once here.
        logger.propagate = False

        # Clear any existing handlers to avoid duplicates on repeated setup
        if logger.handlers:
            logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(cls.LOG_FORMAT, cls.DATE_FORMAT)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Create file handler with rotation if logs directory exists
        try:
            file_path = os.path.join(cls.LOGS_DIR, log_file)
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=cls.MAX_LOG_SIZE,
                backupCount=cls.BACKUP_COUNT
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}")
            # Continue with console logging only

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

        # Then try to load from Streamlit secrets if available
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and st.secrets:
            logger.info(f"Streamlit secrets found with keys: {list(st.secrets.keys())}")
            for key, value in st.secrets.items():
                if isinstance(value, dict):  # Handle nested secrets
                    for subkey, subvalue in value.items():
                        full_key = f"{key}_{subkey}".upper()
                        os.environ[full_key] = str(subvalue)
                        logger.debug(f"Set environment variable {full_key}")
                else:
                    os.environ[key.upper()] = str(value)
                    logger.debug(f"Set environment variable {key.upper()}")
            logger.info("Environment variables loaded from Streamlit secrets")
            
            # Log some key environment variables for debugging
            logger.info(f"EXCHANGE_USERNAME: {os.environ.get('EXCHANGE_USERNAME', 'Not set')}")
            logger.info(f"COMPANY_NAME: {os.environ.get('COMPANY_NAME', 'Not set')}")
            logger.info(f"SENDER_NAME: {os.environ.get('SENDER_NAME', 'Not set')}")
        else:
            logger.warning("Streamlit secrets not available")

        # Regardless of Streamlit availability, attempt to map [box].BOX_JWT_JSON from secrets file to env
        try:
            from core.secrets import get_section as _get_secret_section
            box_section = _get_secret_section("box") or {}
            if isinstance(box_section, dict):
                jwt_json = str(box_section.get("BOX_JWT_JSON", "") or "").strip()
                if jwt_json:
                    os.environ["BOX_JWT_JSON"] = jwt_json
                    logger.info("Set BOX_JWT_JSON from secrets [box].BOX_JWT_JSON")
        except Exception as map_e:
            logger.warning(f"Could not map secrets [box].BOX_JWT_JSON to env: {map_e}")
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

class ExchangeConfig:
    """Deprecated: retained for UPN+CC only. EWS credentials are ignored."""
    @classmethod
    def get_username(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'EXCHANGE_USERNAME' in st.secrets:
            return st.secrets['EXCHANGE_USERNAME']
        return os.environ.get("EXCHANGE_USERNAME", "")

    @classmethod
    def get_cc_email(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'EXCHANGE_CC_EMAIL' in st.secrets:
            return st.secrets['EXCHANGE_CC_EMAIL']
        return os.environ.get("EXCHANGE_CC_EMAIL", "")

    @classmethod
    def get_settings(cls) -> Dict[str, str]:
        return {
            "username": cls.get_username(),
            "from_email": cls.get_username(),  # UPN serves as mailbox address
            "cc": cls.get_cc_email(),
        }

    @classmethod
    def validate(cls) -> bool:
        if not cls.get_username():
            logger.warning("EXCHANGE_USERNAME (UPN) is not set")
            return False
        return True

# Company information
class CompanyInfo:
    """Container for company information used in emails."""
    
    @classmethod
    def get_name(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'COMPANY_NAME' in st.secrets:
            return st.secrets['COMPANY_NAME']
        return os.environ.get("COMPANY_NAME", "Your Company")
    
    @classmethod
    def get_logo_url(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'COMPANY_LOGO_URL' in st.secrets:
            return st.secrets['COMPANY_LOGO_URL']
        return os.environ.get("COMPANY_LOGO_URL", "")
    
    @classmethod
    def get_sender_name(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'SENDER_NAME' in st.secrets:
            return st.secrets['SENDER_NAME']
        return os.environ.get("SENDER_NAME", "")
    
    @classmethod
    def get_sender_title(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'SENDER_TITLE' in st.secrets:
            return st.secrets['SENDER_TITLE']
        return os.environ.get("SENDER_TITLE", "")
    
    @classmethod
    def get_sender_email(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'SENDER_EMAIL' in st.secrets:
            return st.secrets['SENDER_EMAIL']
        return os.environ.get("SENDER_EMAIL", "")
    
    @classmethod
    def get_sender_phone(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'SENDER_PHONE' in st.secrets:
            return st.secrets['SENDER_PHONE']
        return os.environ.get("SENDER_PHONE", "")
    
    @classmethod
    def get_address(cls):
        if STREAMLIT_AVAILABLE and hasattr(st, 'secrets') and 'COMPANY_ADDRESS' in st.secrets:
            return st.secrets['COMPANY_ADDRESS']
        return os.environ.get("COMPANY_ADDRESS", "")
    
    @classmethod
    def get_info(cls) -> Dict[str, str]:
        """
        Get company information as a dictionary.
        
        Returns:
            Dictionary with company information
        """
        return {
            "name": cls.get_name(),
            "logo_url": cls.get_logo_url(),
            "sender_name": cls.get_sender_name(),
            "sender_title": cls.get_sender_title(),
            "sender_email": cls.get_sender_email(),
            "sender_phone": cls.get_sender_phone(),
            "address": cls.get_address()
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
    
    # Check if specs path exists (skip if Box Familiar Specs is configured)
    box_spec_id = (
        os.environ.get("BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
        or os.environ.get("BOX_BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
    )
    if not box_spec_id and not os.path.exists(Paths.SPECS_PATH):
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
    if not CompanyInfo.get_name() or CompanyInfo.get_name() == "Your Company":
        validation_issues.append("Company name is not set or is using default value")
    
    # Check if sender email is set
    sender_email = CompanyInfo.get_sender_email()
    if not sender_email:
        validation_issues.append("Sender email is not set")
    elif "@" not in sender_email:
        validation_issues.append(f"Sender email is invalid: {sender_email}")
    
    # Check if sender name is set
    if not CompanyInfo.get_sender_name():
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
def _ensure_sender_defaults() -> None:
    """Infer and set sender identity defaults if missing.
    
    - SENDER_EMAIL: prefer EXCHANGE_FROM_EMAIL; else EXCHANGE_USERNAME.
    - SENDER_NAME: derive from email local-part (john.doe -> John Doe);
      else fall back to COMPANY_NAME; else 'RFQ Sender'.
    Also align EXCHANGE_FROM_EMAIL if we inferred SENDER_EMAIL.
    """
    try:
        sender_email = os.environ.get("SENDER_EMAIL", "").strip()
        exchange_from = os.environ.get("EXCHANGE_FROM_EMAIL", "").strip()
        exchange_user = os.environ.get("EXCHANGE_USERNAME", "").strip()

        # Infer sender email
        inferred_email = None
        if not sender_email:
            # Check company-scoped env first (may come from secrets flattening)
            company_sender_email = os.environ.get("COMPANY_SENDER_EMAIL", "").strip()
            if company_sender_email:
                inferred_email = company_sender_email
            elif exchange_from:
                inferred_email = exchange_from
            elif exchange_user and "@" in exchange_user:
                inferred_email = exchange_user

            if inferred_email:
                os.environ["SENDER_EMAIL"] = inferred_email
                logger.info(f"SENDER_EMAIL not set; inferred from environment: {inferred_email}")
                # If EXCHANGE_FROM_EMAIL missing, align it
                if not exchange_from:
                    os.environ["EXCHANGE_FROM_EMAIL"] = inferred_email
                    logger.info("EXCHANGE_FROM_EMAIL not set; aligned with inferred SENDER_EMAIL")

        # Infer sender name
        sender_name = os.environ.get("SENDER_NAME", "").strip()
        if not sender_name:
            email_for_name = os.environ.get("SENDER_EMAIL", "") or exchange_user
            inferred_name = None
            if email_for_name and "@" in email_for_name:
                local = email_for_name.split("@", 1)[0]
                # Split on common separators and build a title-cased name
                import re
                parts = [p for p in re.split(r"[._\-]+", local) if p]
                if len(parts) >= 2:
                    first = parts[-1].title()
                    last = parts[0].title()
                    inferred_name = f"{first} {last}"
                elif len(parts) == 1:
                    inferred_name = parts[0].title()
            # Fallback to company sender name or company name
            if not inferred_name:
                company_sender_name = os.environ.get("COMPANY_SENDER_NAME", "").strip()
                if company_sender_name:
                    inferred_name = company_sender_name
                else:
                    company = os.environ.get("COMPANY_NAME", "").strip()
                    if company:
                        inferred_name = company
                    else:
                        inferred_name = "RFQ Sender"
            os.environ["SENDER_NAME"] = inferred_name
            logger.info(f"SENDER_NAME not set; inferred as: {inferred_name}")
    except Exception as e:
        logger.warning(f"Failed to infer sender defaults: {e}")


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

    # Apply defaults for sender identity if missing
    _ensure_sender_defaults()
    
    # Track validation status
    validation_issues = []
    
    # Validate Exchange settings (deprecated: ExchangeConfig removed/unused)
    # if not ExchangeConfig.validate():
    #     validation_issues.append("Exchange configuration is incomplete")
    
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