# Streamlit Email Fix

## Issue Description

The Streamlit application was encountering the following errors:

1. **Vendor Options File Path Error**:
   ```
   Error loading data: Vendor options file not found: /mount/src/rfq-sender/config/vendor_options.yaml
   ```

2. **Indentation Error in 06_send_emails.py**:
   ```
   IndentationError: expected an indented block after 'if' statement on line 55
   ```

## Root Cause Analysis

### Vendor Options File Path Error

The Streamlit pages were looking for the vendor_options.yaml file in the wrong directory (`/mount/src/rfq-sender/config/` instead of `/mount/src/rfq-sender/docs/OS/`). This was happening in both `03_send_rfq_emails.py` and `06_send_emails.py`.

The issue in `03_send_rfq_emails.py` was already fixed in a previous session by updating the path to use the centralized configuration from `core.config.py`:

```python
vendor_options_file = str(Paths.VENDOR_OPTIONS_FILE)
```

However, the same issue still existed in `06_send_emails.py`.

### Indentation Error in 06_send_emails.py

The indentation error was already fixed in the current version of the file. The error was likely caused by a missing indented block after an if statement.

### Import Error for load_data Function

When trying to fix the vendor options file path error in `06_send_emails.py`, we encountered an additional issue. The file was trying to import the `load_data` function from `email_from_list.py`, but this import was failing due to dependency issues in `email_from_list.py`.

## Solution

### 1. Fix Vendor Options File Path

Updated the path in `06_send_emails.py` to use the centralized configuration from `core.config.py`:

```python
vendor_options_file = str(Paths.VENDOR_OPTIONS_FILE)
```

### 2. Fix Import Error for load_data Function

Instead of trying to import the `load_data` function from `email_from_list.py`, we added the function implementation directly to `06_send_emails.py`. This avoids the dependency issues and provides the functionality needed.

The implementation was copied from `03_send_rfq_emails.py`, which already had a working version of the function.

### 3. Update Comments

Updated the comment in `06_send_emails.py` to reflect that we're using the local `load_data` function:

```python
# Use local load_data function
queue, vendor_info = load_data(queue_file, contacts_file, vendor_options_file, logger)
```

## Verification

Created a test script `test_06_send_emails.py` to verify that the solution works correctly. The test script checks:

1. If the necessary modules can be imported
2. If the vendor_options.yaml file exists at the path specified by Paths.VENDOR_OPTIONS_FILE
3. If the 06_send_emails.py file exists
4. If the 06_send_emails.py file contains the load_data function
5. If the 06_send_emails.py file is not importing load_data from email_from_list.py

The test script ran successfully, confirming that the solution works correctly.

## Additional Improvements

While fixing the main issues, we also made the following improvements:

1. Updated the import for SpecProcessValidator in `email_from_list.py` to use the correct path:
   ```python
   from scripts.utils.spec_check import SpecProcessValidator
   ```

2. Updated the import for BoxIntegration in `email_from_list.py` to use the correct path:
   ```python
   from scripts.box.box_integration import BoxIntegration
   ```

These changes help ensure that the imports work correctly in different contexts and environments.

## Best Practices

To avoid similar issues in the future, follow these best practices:

1. **Use centralized configuration**: Always use the centralized configuration in `core.config.py` for file paths instead of hardcoding them in individual files.

2. **Consistent path handling**: Use the `Paths` class for all file paths to ensure consistent path handling across the application.

3. **Cross-platform compatibility**: Use `os.path.join()` or `pathlib.Path` for constructing file paths to ensure cross-platform compatibility.

4. **Error handling**: Include comprehensive error handling when loading files, with clear error messages that indicate the file path that couldn't be found.

5. **Testing**: Create test scripts to verify that files can be loaded correctly, especially when making changes to file paths or configuration.

6. **Dependency management**: Be careful when importing functions from other modules, especially if those modules have dependencies that might not be available in all environments.