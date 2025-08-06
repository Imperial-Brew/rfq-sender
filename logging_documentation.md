# RFQ-Sender Logging Documentation

## Overview

The RFQ-Sender project uses a standardized logging approach to ensure consistent log formats, file locations, and rotation policies across all modules. This document explains how to use the logging system properly.

## Logging Configuration

All logging is configured through the `LoggingConfig` class in `core/config.py`. This class provides:

- Standardized log formats
- Consistent file locations
- Automatic log rotation
- Appropriate log levels

## How to Use Logging in Your Code

### Basic Usage

```python
from core.config import LoggingConfig

# Set up logging for your module
logger = LoggingConfig.setup_logging(__name__, "your_module.log")

# Use the logger
logger.info("Operation completed successfully")
logger.warning("Resource is running low")
logger.error("Failed to process request", exc_info=True)  # Include exception info
```

### Log Level Guidelines

Use the appropriate log level for your messages:

- **DEBUG**: Detailed information, typically useful only for diagnosing problems
  ```python
  logger.debug("Processing item 42 with parameters: x=5, y=10")
  ```

- **INFO**: Confirmation that things are working as expected
  ```python
  logger.info("User 'john_doe' logged in successfully")
  logger.info("Successfully processed 25 items in 3.2 seconds")
  ```

- **WARNING**: Indication that something unexpected happened, or may happen in the near future
  ```python
  logger.warning("Database connection pool running low (10% remaining)")
  logger.warning("User attempted to access restricted resource")
  ```

- **ERROR**: Due to a more serious problem, the software has not been able to perform a function
  ```python
  logger.error(f"Failed to process request: {str(e)}", exc_info=True)
  logger.error("Unable to connect to external service")
  ```

- **CRITICAL**: A serious error indicating the program itself may be unable to continue running
  ```python
  logger.critical("Database connection lost, application cannot function")
  logger.critical("Critical security breach detected")
  ```

### Including Context Information

Include relevant context in your log messages to make them more useful for debugging:

```python
# Good - includes context
logger.info(f"RFQ added to queue: {part_number} - {process}")

# Better - includes more detailed context
logger.info(
    f"RFQ added to queue: {part_number} - {process}",
    extra={
        "user": user_name,
        "part_number": part_number,
        "process": process,
        "spec": spec
    }
)
```

### Logging Exceptions

When logging exceptions, include the exception information:

```python
try:
    # Some code that might raise an exception
    process_data(data)
except Exception as e:
    logger.error(f"Error processing data: {str(e)}", exc_info=True)
    # Handle the exception appropriately
```

## Log File Locations

All log files are stored in the `logs` directory at the project root. Each module has its own log file, named after the module (e.g., `app.log`, `email.log`, etc.).

## Log Rotation

Log files are automatically rotated when they reach 10 MB in size. The system keeps 5 backup files, named with a suffix (e.g., `app.log.1`, `app.log.2`, etc.).

## Viewing Logs

You can view logs using any text editor or with command-line tools:

```bash
# View the most recent log entries
tail -f logs/app.log

# Search for specific text in logs
grep "error" logs/app.log

# View logs with timestamps in a specific time range
grep "2025-08-06" logs/app.log
```

## Best Practices

1. **Use the appropriate log level** - Don't log everything as INFO or ERROR
2. **Include context information** - Make logs useful for debugging
3. **Be concise but complete** - Include all relevant information without being verbose
4. **Use structured logging** when appropriate - Include extra parameters for machine parsing
5. **Log at module initialization** - Log when your module starts up
6. **Log entry and exit of important functions** - Especially for long-running operations
7. **Don't log sensitive information** - Avoid logging passwords, tokens, or personal data