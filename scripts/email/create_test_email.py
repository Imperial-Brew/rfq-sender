"""
Create Test Email Script

This script creates a draft email using Exchange Web Services with a test subject and body.
It creates a draft email in the user's drafts folder.

Usage:
    python scripts\create_test_email.py

Requirements:
    - exchangelib package must be installed (pip install exchangelib)
    - .env file with email configuration (see .env.example)

Environment Variables:
    - SMTP_FROM_EMAIL: Email address to use as sender
    - SMTP_FROM_NAME: Name to use as sender
    - EXCHANGE_USERNAME: Username for Exchange account
    - EXCHANGE_PASSWORD: Password for Exchange account
    - EXCHANGE_SERVER: Exchange server address (default: outlook.office365.com)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import Paths, ExchangeConfig, LoggingConfig, init_config

# Initialize configuration
init_config()

from exchangelib import Credentials, Account, Configuration, DELEGATE, Message, Mailbox
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter
import urllib3

# Disable insecure request warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional: Add this for self-signed certificates
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter


def setup_logging() -> logging.Logger:
    """
    Set up logging configuration using the centralized LoggingConfig.

    Returns:
        Logger object configured for this script
    """
    return LoggingConfig.setup_logging(__name__, "create_test_email.log")


def initialize_exchange(username: str, password: str, server: str, logger: logging.Logger) -> Optional[Account]:
    """
    Initialize connection to Exchange server.
    
    Args:
        username: Exchange username (email address)
        password: Exchange password
        server: Exchange server address
        logger: Logger object for logging messages
        
    Returns:
        Exchange account object or None if initialization fails
    """
    try:
        logger.info("Initializing Exchange connection")
        
        # Create credentials object
        credentials = Credentials(username=username, password=password)
        
        # Create configuration
        config = Configuration(server=server, credentials=credentials)
        
        # Connect to the account
        account = Account(
            primary_smtp_address=username,
            config=config,
            autodiscover=False,
            access_type=DELEGATE
        )
        
        logger.info("Exchange connection initialized successfully")
        return account
    except Exception as e:
        logger.error(f"Failed to initialize Exchange connection: {str(e)}")
        return None


def create_exchange_draft(account: Account, to_email: str, subject: str, body: str, logger: logging.Logger) -> bool:
    """
    Create a draft email using Exchange Web Services.

    Args:
        account: Exchange account object
        to_email: Recipient email address
        subject: Email subject
        body: Email body
        logger: Logger object for logging messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create message
        m = Message(
            account=account,
            folder=account.drafts,
            subject=subject,
            body=body,
            body_type='Text',
            to_recipients=[Mailbox(email_address=to_email)]
        )
        
        # Save the draft
        m.save()
        
        logger.info(f"Created draft email to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to create draft email: {str(e)}")
        return False


def get_env_variable(var_name: str, default: Optional[str] = None, logger: logging.Logger = None) -> str:
    """
    Get environment variable with validation.

    Args:
        var_name: Name of the environment variable
        default: Default value if environment variable is not set
        logger: Logger object for logging messages

    Returns:
        Value of the environment variable or default

    Raises:
        ValueError: If environment variable is not set and no default is provided
    """
    value = os.environ.get(var_name, default)

    if value is None:
        error_msg = f"Environment variable {var_name} is not set and no default provided"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg)

    return value


def main() -> None:
    """Main entry point for the script."""
    try:
        # Get the project root directory (parent of scripts directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(project_root, "logs")

        # Set up logging using the centralized LoggingConfig
        logger = setup_logging()

        # Environment variables already loaded by init_config()
        logger.info("Environment variables loaded by init_config()")

        # Get email configuration from environment variables with validation
        try:
            from_email = get_env_variable("SMTP_FROM_EMAIL", "your_email@example.com", logger)
            from_name = get_env_variable("SMTP_FROM_NAME", "RFQ System", logger)
            
            # Get Exchange credentials
            exchange_username = get_env_variable("EXCHANGE_USERNAME", from_email, logger)
            exchange_password = get_env_variable("EXCHANGE_PASSWORD", "", logger)
            exchange_server = get_env_variable("EXCHANGE_SERVER", "outlook.office365.com", logger)
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            sys.exit(1)

        # Log environment variable values
        logger.info(f"Using sender email: {from_email}")
        logger.info(f"Using sender name: {from_name}")
        logger.info(f"Using Exchange server: {exchange_server}")

        # Initialize Exchange connection
        account = initialize_exchange(exchange_username, exchange_password, exchange_server, logger)
        if not account:
            logger.error("Failed to initialize Exchange connection")
            sys.exit(1)

        # Create test email
        to_email = "example@example.com"
        subject = "TEST"
        body = f"""TEST EMAIL

From: {from_name} <{from_email}>

This is a test email created using the RFQ Sender system.
No action is required.
        """

        logger.info(f"Creating test email from {from_email} to {to_email}")

        success = create_exchange_draft(account, to_email, subject, body, logger)

        if success:
            logger.info("Test email draft created successfully in your Exchange drafts folder.")
        else:
            logger.error("Failed to create test email draft.")
            sys.exit(1)

    except Exception as e:
        # Catch any unexpected exceptions
        print(f"Script failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
