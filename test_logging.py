#!/usr/bin/env python
"""
Test script for the standardized logging configuration.

This script tests the LoggingConfig class by creating loggers
and writing messages at different log levels.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import the logging configuration
from core.config import LoggingConfig, init_config

# Initialize configuration
init_config()

def test_logging():
    """Test the logging configuration."""
    # Create a logger for this module
    logger = LoggingConfig.setup_logging(__name__, "test_logging.log")
    
    print("Testing logging configuration...")
    print(f"Log files will be written to: {os.path.join(project_root, 'logs')}")
    
    # Log messages at different levels
    logger.debug("This is a DEBUG message - should only appear if debug is enabled")
    logger.info("This is an INFO message - normal operational information")
    logger.warning("This is a WARNING message - something unexpected happened")
    logger.error("This is an ERROR message - a more serious problem occurred")
    
    # Test exception logging
    try:
        # Deliberately cause an exception
        result = 1 / 0
    except Exception as e:
        logger.error(f"Caught an exception: {str(e)}", exc_info=True)
    
    # Test logging with context
    user = "test_user"
    action = "logging_test"
    logger.info(
        f"User '{user}' performed action: {action}",
        extra={"user": user, "action": action}
    )
    
    print("Logging test completed. Check the logs directory for test_logging.log")

if __name__ == "__main__":
    test_logging()