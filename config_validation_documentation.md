# Configuration Validation Documentation

## Overview

The RFQ-Sender application now includes comprehensive configuration validation that runs at application startup. This validation ensures that all critical settings are properly configured before the application attempts to use them, reducing runtime errors and providing clear guidance on what needs to be fixed.

## Validation Process

The validation process is implemented in the `init_config()` function in `core/config.py`. This function:

1. Loads environment variables from the `.env` file
2. Validates Exchange settings (username, password)
3. Validates file paths (vendor file, vendor options file, specs file, email template)
4. Validates company information (company name, sender email, sender name)
5. Validates security settings (CUI protection)
6. Logs any validation issues found

## Critical Settings

The following settings are considered critical and are validated at startup:

### File Paths
- `Paths.VENDOR_FILE`: Path to the vendor JSON file
- `Paths.VENDOR_OPTIONS_FILE`: Path to the vendor options YAML file
- `Paths.SPECS_PATH`: Path to the specs CSV file
- `Paths.EMAIL_TEMPLATE_PATH`: Path to the email template HTML file

### Exchange Settings
- `ExchangeConfig.USERNAME`: Exchange username/email
- `ExchangeConfig.PASSWORD`: Exchange password

### Company Information
- `CompanyInfo.NAME`: Company name (should not be the default "Your Company")
- `CompanyInfo.SENDER_EMAIL`: Email address of the sender (must be a valid email)
- `CompanyInfo.SENDER_NAME`: Name of the sender

### Security Settings
- If `SecurityConfig.ENABLE_CUI_PROTECTION` is enabled, `SecurityConfig.CUI_WARNING` must not be empty

## Validation Behavior

When validation issues are found:
1. Each issue is logged as a warning
2. A summary warning is logged indicating the total number of issues
3. A warning is logged that the application may not function correctly

The application will continue to run even with validation issues, but certain functionality may not work correctly. This allows the application to start even with partial configuration, which can be useful during development or when only certain features are needed.

## How to Fix Validation Issues

### Missing Files
- Ensure the file exists at the specified path
- If the file should be in a different location, update the path in `core/config.py`
- For templates, you may need to create the file if it doesn't exist

### Exchange Settings
- Add the following to your `.env` file:
  ```
  EXCHANGE_USERNAME=your.email@example.com
  EXCHANGE_PASSWORD=your_password
  EXCHANGE_SERVER=outlook.office365.com
  ```

### Company Information
- Add the following to your `.env` file:
  ```
  COMPANY_NAME=Your Actual Company Name
  SENDER_NAME=Your Name
  SENDER_EMAIL=your.email@example.com
  ```

### Security Settings
- If you enable CUI protection, ensure you provide a warning text:
  ```
  ENABLE_CUI_PROTECTION=true
  CUI_WARNING=This email contains Controlled Unclassified Information (CUI)
  ```

## Testing Validation

You can test the validation by running:

```
python test_config_validation.py
```

This script will:
1. Test file path validation
2. Test company info validation
3. Test security settings validation
4. Test the full `init_config()` function

The script will print any validation issues found and also log them to the logs directory.

## Implementation Details

The validation is implemented using three helper functions:

1. `validate_file_paths(validation_issues)`: Validates that critical file paths exist
2. `validate_company_info(validation_issues)`: Validates that company information is set
3. `validate_security_settings(validation_issues)`: Validates security settings

These functions append any issues found to the `validation_issues` list, which is then processed by `init_config()`.

## Best Practices

1. Always call `init_config()` at application startup
2. Check the logs for validation warnings when starting the application
3. Fix validation issues as soon as possible
4. Add new validation checks when adding new critical settings
5. Use environment variables for sensitive or environment-specific settings