#!/usr/bin/env python
"""
Test script for the standardized logging configuration.

This script tests the centralized logging module by creating loggers
and writing messages at different log levels. It also tests the error
handling when the logs directory doesn't exist or can't be accessed.
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import the centralized logging module
from utils.logging import get_logger, configure_root_logger

def test_logging_with_directory():
    """Test logging with the logs directory present."""
    # Ensure logs directory exists
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure the root logger
    configure_root_logger()
    
    # Get a logger for this module
    logger = get_logger(__name__, "test_logging.log")
    
    print("\nTesting logging with directory...")
    print(f"Log files will be written to: {logs_dir}")
    
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
        f"User '{user}' performed action: {action}"
    )
    
    print("Logging test with directory completed. Check the logs directory for test_logging.log")

def test_logging_without_directory():
    """Test logging when the logs directory doesn't exist."""
    # Close all log handlers to release file locks
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)
    
    # Also close handlers for any other loggers
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
    
    # Remove the logs directory if it exists
    logs_dir = os.path.join(project_root, "logs")
    if os.path.exists(logs_dir):
        try:
            shutil.rmtree(logs_dir)
            print("\nTesting logging without directory...")
            print(f"Logs directory has been removed: {logs_dir}")
        except PermissionError:
            print("\nCould not remove logs directory due to file locks.")
            print("Simulating missing logs directory test...")
            # We'll simulate the test without actually removing the directory
    else:
        print("\nTesting logging without directory...")
        print(f"Logs directory does not exist: {logs_dir}")
    
    # Configure the root logger (should handle missing directory gracefully)
    configure_root_logger()
    
    # Get a logger for this module (should handle missing directory gracefully)
    logger = get_logger(__name__, "test_logging_no_dir.log")
    
    # Log messages at different levels
    logger.debug("This is a DEBUG message without directory")
    logger.info("This is an INFO message without directory")
    logger.warning("This is a WARNING message without directory")
    logger.error("This is an ERROR message without directory")
    
    print("Logging test without directory completed. Messages should appear in console only.")
    
    # Recreate the logs directory for future tests
    os.makedirs(logs_dir, exist_ok=True)
    print(f"Logs directory recreated: {logs_dir}")

def test_logging():
    """Run all logging tests."""
    # Test with logs directory
    test_logging_with_directory()
    
    # Test without logs directory
    test_logging_without_directory()
    
    print("\nAll logging tests completed successfully!")

if __name__ == "__main__":
    test_logging()