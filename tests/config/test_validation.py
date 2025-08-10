#!/usr/bin/env python
"""
Test script for configuration validation.

This script tests the enhanced validation in the init_config() function
by creating test scenarios with missing or invalid settings.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path (adjusted for new location in tests/config/)
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import the configuration module
from core.config import (
    Paths, 
    ExchangeConfig, 
    CompanyInfo, 
    SecurityConfig, 
    AppConfig, 
    init_config,
    validate_file_paths,
    validate_company_info,
    validate_security_settings
)

def test_validation():
    """Test the configuration validation."""
    print("Testing configuration validation...")
    
    # Create a list to collect validation issues
    validation_issues = []
    
    # Test file path validation
    print("\n1. Testing file path validation:")
    validate_file_paths(validation_issues)
    if validation_issues:
        print(f"  Found {len(validation_issues)} file path issues:")
        for issue in validation_issues:
            print(f"  - {issue}")
    else:
        print("  All file paths are valid.")
    
    # Clear the list for the next test
    validation_issues.clear()
    
    # Test company info validation
    print("\n2. Testing company info validation:")
    validate_company_info(validation_issues)
    if validation_issues:
        print(f"  Found {len(validation_issues)} company info issues:")
        for issue in validation_issues:
            print(f"  - {issue}")
    else:
        print("  All company info is valid.")
    
    # Clear the list for the next test
    validation_issues.clear()
    
    # Test security settings validation
    print("\n3. Testing security settings validation:")
    validate_security_settings(validation_issues)
    if validation_issues:
        print(f"  Found {len(validation_issues)} security setting issues:")
        for issue in validation_issues:
            print(f"  - {issue}")
    else:
        print("  All security settings are valid.")
    
    # Test the full init_config function
    print("\n4. Testing full init_config() function:")
    print("  Calling init_config()...")
    init_config()
    print("  init_config() completed. Check the logs for any validation warnings.")
    
    print("\nValidation testing completed.")

if __name__ == "__main__":
    test_validation()