# RFQ Sender Project Reorganization Plan

This document outlines a comprehensive plan for reorganizing and improving the RFQ Sender project according to best practices and guidelines.

## 1. Test Files Reorganization

### Current State
- 13 test files are located in the root directory
- The tests directory has an email subdirectory with 4 test files
- Tests should be organized by functionality

### Implementation Plan

#### 1.1 Create Subdirectories
Create the following subdirectories in the tests directory:
- tests/config/ - For configuration-related tests
- tests/queue/ - For queue-related tests
- tests/data/ - For data-related tests
- tests/logging/ - For logging-related tests
- tests/bug_tracker/ - For bug tracker-related tests
- tests/fixes/ - For fix-related tests
- tests/vendor/ - For vendor-related tests

#### 1.2 Move Test Files
Move the following test files from the root directory to the appropriate subdirectories:

**Email Tests (tests/email/)**
- test_06_send_emails.py → tests/email/test_send_emails.py
- test_06_send_emails_imports.py → tests/email/test_send_emails_imports.py
- test_exchange_connection.py → tests/email/test_exchange_connection.py

**Configuration Tests (tests/config/)**
- test_config_validation.py → tests/config/test_validation.py

**Queue Tests (tests/queue/)**
- test_queue_loading.py → tests/queue/test_loading.py
- test_view_queue.py → tests/queue/test_view.py

**Data Tests (tests/data/)**
- test_load_data.py → tests/data/test_load.py
- test_contacts_csv.py → tests/data/test_contacts_csv.py

**Logging Tests (tests/logging/)**
- test_logging.py → tests/logging/test_logging.py

**Bug Tracker Tests (tests/bug_tracker/)**
- test_bug_tracker.py → tests/bug_tracker/test_bug_tracker.py

**Fix Tests (tests/fixes/)**
- test_app_fix.py → tests/fixes/test_app_fix.py
- test_fix.py → tests/fixes/test_fix.py

**Vendor Tests (tests/vendor/)**
- test_vendor_options.py → tests/vendor/test_options.py

#### 1.3 Update Import Paths
Update import paths in the moved test files to reflect their new locations. This may involve:
- Changing relative imports to absolute imports
- Updating sys.path.append statements
- Ensuring imports use the correct package structure

#### 1.4 Verify Tests
Run the tests to ensure they still work after reorganization:
```powershell
cd C:\Users\ddrab\Documents\GitHub\rfq-sender
python -m pytest
```

## 2. Documentation Improvements

### Current State
- SCALING.md is in the .junie directory but referenced as docs/SCALING.md in README.md
- Some documentation files mentioned in DOCUMENTATION_INDEX.md are marked as "To Be Created"
- Documentation is somewhat fragmented across different directories

### Implementation Plan

#### 2.1 Resolve Documentation Inconsistencies
- Move .junie/SCALING.md to docs/SCALING.md to match the reference in README.md
- Alternatively, update the README.md reference to point to .junie/SCALING.md

#### 2.2 Update Documentation Index
- Update docs/DOCUMENTATION_INDEX.md to include all existing documentation files
- Remove "To Be Created" markers for documentation that now exists
- Add entries for documentation files that aren't currently listed

#### 2.3 Improve README.md
- Ensure README.md provides accurate navigation to all documentation files
- Update the project structure section to reflect the current structure
- Update the style guidelines overview to match docs/guidelines.md

#### 2.4 Standardize Documentation Format
- Ensure all documentation follows the markdown formatting rules in guidelines.md
- Standardize headings, code blocks, and other formatting elements
- Include file paths in document headings as specified in guidelines.md

## 3. Python Package Configuration Enhancements

### Current State
- pyproject.toml exists but has placeholder author information
- Dependencies section includes a comment suggesting it might not be complete
- Packages are explicitly listed rather than using find_packages
- No separate section for development dependencies

### Implementation Plan

#### 3.1 Update Metadata
- Update author information with actual project maintainer details
- Ensure all required metadata fields are complete and accurate

#### 3.2 Improve Package Discovery
- Consider using find_packages instead of explicitly listing packages
- Ensure all relevant packages are included

#### 3.3 Configure Development Dependencies
- Add a [project.optional-dependencies] section for development dependencies
- Include testing, linting, and documentation tools

#### 3.4 Ensure Consistent Dependency Management
- Review and update dependencies to ensure all required packages are listed
- Specify version ranges where appropriate
- Remove the comment about adding other dependencies

## 4. Code Style and Formatting

### Current State
- The project has configuration for black, isort, mypy, and pytest in pyproject.toml
- There may be inconsistencies in import ordering, type hints, docstrings, and line length

### Implementation Plan

#### 4.1 Verify Tool Configuration
- Ensure black, isort, mypy, and pytest configurations are correct and consistent
- Add configuration for flake8 if not already present

#### 4.2 Run Formatting Tools
- Run black to format all Python files
- Run isort to sort imports
- Run flake8 to check for style issues

#### 4.3 Check Type Hints and Docstrings
- Verify that all functions have appropriate type hints
- Ensure docstrings follow the format specified in guidelines.md
- Check that line lengths comply with the specified limits

## 5. Implementation Timeline

### Phase 1: Test Reorganization (1-2 days)
- Create subdirectories in tests directory
- Move test files to appropriate subdirectories
- Update import paths
- Verify tests still work

### Phase 2: Documentation Improvements (1-2 days)
- Resolve documentation inconsistencies
- Update documentation index
- Improve README.md
- Standardize documentation format

### Phase 3: Package Configuration (1 day)
- Update metadata
- Improve package discovery
- Configure development dependencies
- Ensure consistent dependency management

### Phase 4: Code Style and Formatting (1-2 days)
- Verify tool configuration
- Run formatting tools
- Check type hints and docstrings

## 6. Success Criteria

The reorganization will be considered successful when:

1. All tests are properly organized in the tests directory and pass
2. Documentation is consistent, complete, and follows the style guidelines
3. Python package configuration is complete and follows best practices
4. Code style and formatting are consistent throughout the project
5. The project adheres to all guidelines specified in docs/guidelines.md

## 7. Risks and Mitigation

### Risks
- Moving test files may break imports or test functionality
- Documentation updates may introduce inconsistencies
- Package configuration changes may affect build and installation

### Mitigation
- Run tests after each move to verify functionality
- Review documentation changes carefully for consistency
- Test package installation after configuration changes