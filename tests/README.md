# RFQ Sender Test Suite

This directory contains the test suite for the RFQ Sender application. The tests are organized by functionality to improve maintainability and make it easier to find and run specific tests.

## Test Directory Structure

The tests are organized into the following subdirectories:

- **bug_tracker/**: Tests for the bug tracker functionality
- **config/**: Tests for configuration validation and loading
- **data/**: Tests for data loading and processing
- **email/**: Tests for email functionality and Exchange connection
- **fixes/**: Tests for specific bug fixes
- **logging/**: Tests for logging functionality
- **queue/**: Tests for queue loading and processing
- **vendor/**: Tests for vendor-related functionality

## Running Tests

### Running Individual Tests

To run an individual test, use the following command from the project root directory:

```powershell
python -m tests.<subdirectory>.<test_file_name_without_py>
```

For example, to run the vendor options test:

```powershell
python -m tests.vendor.test_options
```

### Running All Tests

To run all tests, use pytest from the project root directory:

```powershell
python -m pytest
```

To run tests in a specific subdirectory:

```powershell
python -m pytest tests/<subdirectory>
```

## Test Files

### Bug Tracker Tests
- **test_bug_tracker.py**: Verifies the bug tracker page is accessible and properly configured

### Configuration Tests
- **test_validation.py**: Tests the configuration validation functionality

### Data Tests
- **test_contacts_csv.py**: Verifies that contacts are loaded correctly from CSV
- **test_load.py**: Tests loading and mapping queue data columns

### Email Tests
- **test_exchange_connection.py**: Tests the Exchange connection with updated SSL verification settings
- **test_send_emails.py**: Verifies that the imports and functions in 06_send_emails.py work correctly
- **test_send_emails_imports.py**: Tests that the imports in 06_send_emails.py work correctly

### Fixes Tests
- **test_app_fix.py**: Verifies the app.py fixes to prevent the KeyError: 'streamlit_app' issue
- **test_fix.py**: Tests loading the queue data and processing it similar to the view_queue page

### Logging Tests
- **test_logging.py**: Tests the standardized logging configuration

### Queue Tests
- **test_loading.py**: Tests loading the queue data to ensure it works correctly
- **test_view.py**: Tests the safe date comparison function and dataframe processing

### Vendor Tests
- **test_options.py**: Verifies that the vendor_options.yaml file can be loaded correctly

## Test Reorganization

The test files were previously located in the root directory of the project. They have been moved to the appropriate subdirectories in the tests directory and their import paths have been updated to reflect their new locations.

This reorganization follows the project's organization guidelines and makes it easier to find and run specific tests. It also improves maintainability by grouping related tests together.

## Best Practices for Writing Tests

When writing new tests, please follow these guidelines:

1. Place the test file in the appropriate subdirectory based on its functionality
2. Use the naming convention `test_<functionality>.py` for test files
3. Update the import paths to account for the location of the test file in the tests directory
4. Add a docstring to the test file explaining what it tests
5. Add the test file to this README.md file in the appropriate section

## Running Tests in CI/CD

The tests are automatically run in the CI/CD pipeline when changes are pushed to the repository. The pipeline is configured to run all tests and report any failures.

If you need to run the tests locally before pushing changes, you can use the commands described above.