# Test Fix Plan

## Overview
This document outlines the plan to address the failing tests in the RFQ Sender System. Currently, 2 out of 5 tests are failing:

1. `test_get_attachments`: Expected 2 attachments but got 4
2. `test_cli_argument_parsing`: TypeError in the mocked `parse_args` method

## Test Failure Analysis

### 1. `test_get_attachments`

#### Issue
The test expects to find 2 matching files based on part number and process, but it's finding 4 files. This suggests that either:
- The test setup is creating more matching files than intended
- The `get_attachments` function is using a broader matching pattern than expected

#### Fix Strategy
1. Review the `get_attachments` function in `rfq_sender.py` to understand its file matching logic
2. Check the test setup to ensure it's creating only the intended matching files
3. Update either the test expectations or the function implementation to align them
4. Consider adding more specific assertions about which files should be matched

### 2. `test_cli_argument_parsing`

#### Issue
The test is failing with a TypeError in the mocked `parse_args` method. This suggests that:
- The mock setup is incorrect
- The function signature may have changed since the test was written

#### Fix Strategy
1. Review the current implementation of `parse_args` in `rfq_sender.py`
2. Check how the mock is set up in the test
3. Update the mock to match the current function signature
4. Consider using a simpler approach to testing argument parsing

## Implementation Plan

### Step 1: Fix `test_get_attachments`
1. Examine the current implementation of `get_attachments` in `rfq_sender.py`
2. Review the test setup to understand what files are being created
3. Update the test to either:
   - Expect 4 attachments if that's the correct behavior
   - Modify the test setup to create only 2 matching files
   - Add a more specific filter to the `get_attachments` function

### Step 2: Fix `test_cli_argument_parsing`
1. Review the current implementation of `parse_args` in `rfq_sender.py`
2. Update the mock setup in the test to correctly handle the function signature
3. Consider simplifying the test by:
   - Using `patch.object` instead of `patch` with `wraps`
   - Testing the parser configuration rather than the parsing itself
   - Breaking the test into smaller, more focused tests

### Step 3: Add Tests for New Functionality
1. Create tests for the new `email_from_list.py` script
2. Focus on testing:
   - CSV file loading and validation
   - Email body generation
   - Vendor information processing
   - Error handling

### Step 4: Improve Test Coverage
1. Run tests with coverage reporting to identify untested code
2. Add tests for any uncovered code paths
3. Focus on edge cases and error handling

## Timeline
- Day 1: Fix `test_get_attachments`
- Day 2: Fix `test_cli_argument_parsing`
- Day 3-4: Add tests for new functionality
- Day 5: Improve overall test coverage

## Success Criteria
- All tests pass
- Test coverage is at least 80% for core functionality
- New functionality has adequate test coverage
- Tests run without warnings or errors