# Logging System Documentation

## Overview

The RFQ-Sender application uses a centralized logging system to ensure consistent log formats, file locations, and rotation policies across all components. This document describes how to use the logging system in your code.

## Key Components

1. **LoggingConfig** (in `core/config.py`): Contains the base configuration for logging, including log formats, file paths, and rotation policies.
2. **Centralized Logging Module** (in `utils/logging.py`): Provides simple functions for obtaining configured loggers and setting up the root logger.

## How to Use

### Basic Usage

To use the logging system in your code, simply import the `get_logger` function from the `utils.logging` module:

```python
from utils.logging import get_logger

# Get a logger with default settings (uses the module name)
logger = get_logger(__name__)

# Log messages at appropriate levels
logger.info("Operation completed successfully")
logger.warning("Resource is running low")
logger.error("Failed to process request", exc_info=True)  # Include exception info
```

### Custom Log Files

If you want to use a specific log file name:

```python
from utils.logging import get_logger

# Get a logger that writes to a specific log file
logger = get_logger(__name__, "custom_process.log")
```

### Custom Log Levels

To use a different log level:

```python
import logging
from utils.logging import get_logger

# Get a logger with DEBUG level
logger = get_logger(__name__, level=logging.DEBUG)
```

### Application Startup

In the main application entry point, configure the root logger:

```python
from utils.logging import configure_root_logger

# Configure the root logger at application startup
configure_root_logger()
```

## Log File Location

All log files are stored in the `logs` directory at the project root. The directory is created automatically if it doesn't exist.

## Log Format

The standard log format is:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Example:
```
2025-08-07 10:30:45 - app - INFO - Application started
```

## Log Rotation

Log files are automatically rotated when they reach 10 MB in size. The system keeps 5 backup files.

## Log Levels

Use the appropriate log level for your messages:

- **DEBUG**: Detailed information, typically useful only for diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened, or may happen in the near future
- **ERROR**: Due to a more serious problem, the software has not been able to perform a function
- **CRITICAL**: A serious error indicating the program itself may be unable to continue running

## Best Practices

1. **Use module-level loggers**: Get a logger for each module using `__name__` to automatically use the module name.
2. **Include context in log messages**: Make sure log messages include relevant context information.
3. **Use appropriate log levels**: Don't log everything at INFO level; use the appropriate level for each message.
4. **Include exception info**: When logging exceptions, use `exc_info=True` to include the stack trace.
5. **Don't log sensitive information**: Never log passwords, tokens, or other sensitive information.

## Troubleshooting

If logs aren't being written:

1. Check that the `logs` directory exists at the project root
2. Verify that the application has write permissions to the directory
3. Ensure you're using the centralized logging module and not configuring logging directly