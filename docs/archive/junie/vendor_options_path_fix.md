# Vendor Options Path Fix

## Issue Description

The application was encountering the following error when trying to load the vendor options file:

```
Error loading data: Vendor options file not found: /mount/src/rfq-sender/config/vendor_options.yaml
```

This error occurred because the Streamlit pages were looking for the vendor_options.yaml file in the wrong directory (`config` instead of `docs/OS`).

## Root Cause

The issue was found in the following files:

1. `streamlit_app/pages/03_send_rfq_emails.py` - Line 546
2. `streamlit_app/pages/06_send_emails.py` - Line 45

Both files were using a hardcoded path to the vendor_options.yaml file:

```python
vendor_options_file = str(parent_dir / "config" / "vendor_options.yaml")
```

However, the actual location of the vendor_options.yaml file is in the `docs/OS` directory, as defined in the centralized configuration in `core/config.py`:

```python
VENDOR_OPTIONS_FILE = os.path.join(ROOT_DIR, "docs", "OS", "vendor_options.yaml")
```

## Fix Implementation

The fix involved updating the path in both Streamlit pages to use the centralized configuration from `core/config.py`:

1. In `streamlit_app/pages/03_send_rfq_emails.py`:
   ```python
   # Use the centralized path configuration for vendor_options.yaml
   # This ensures consistent path handling across the application
   vendor_options_file = str(Paths.VENDOR_OPTIONS_FILE)
   ```

2. In `streamlit_app/pages/06_send_emails.py`:
   ```python
   # Use the centralized path configuration for vendor_options.yaml
   # This ensures consistent path handling across the application
   vendor_options_file = str(Paths.VENDOR_OPTIONS_FILE)
   ```

## Verification

A test script was created to verify that the vendor_options.yaml file could be loaded correctly using the centralized configuration:

```python
# test_vendor_options.py
import os
import yaml
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import from project modules
from core.config import Paths, init_config

def test_load_vendor_options():
    """Test loading the vendor_options.yaml file."""
    # Initialize configuration
    init_config()
    
    # Get the path to the vendor_options.yaml file
    vendor_options_file = Paths.VENDOR_OPTIONS_FILE
    
    print(f"Vendor options file path: {vendor_options_file}")
    
    # Check if the file exists
    if not os.path.exists(vendor_options_file):
        print(f"Error: Vendor options file not found: {vendor_options_file}")
        return False
    
    # Try to load the file
    try:
        with open(vendor_options_file, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)
        
        # Check if the file has the expected structure
        if not vendor_options or 'vendors' not in vendor_options:
            print("Error: Vendor options file does not have the expected structure")
            return False
        
        # Print some information about the loaded data
        vendor_count = len(vendor_options['vendors'])
        print(f"Successfully loaded vendor options file with {vendor_count} vendors")
        
        # Print the first few vendors
        for i, vendor in enumerate(vendor_options['vendors'][:3], 1):
            print(f"Vendor {i}: {vendor['name']}")
        
        return True
    
    except Exception as e:
        print(f"Error loading vendor options file: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_load_vendor_options()
    if success:
        print("Test passed: Vendor options file loaded successfully")
    else:
        print("Test failed: Could not load vendor options file")
        sys.exit(1)
```

Running this test script confirmed that the vendor_options.yaml file could be loaded correctly using the centralized configuration.

## Best Practices

To avoid similar issues in the future, follow these best practices:

1. **Use centralized configuration**: Always use the centralized configuration in `core/config.py` for file paths instead of hardcoding them in individual files.

2. **Consistent path handling**: Use the `Paths` class for all file paths to ensure consistent path handling across the application.

3. **Cross-platform compatibility**: Use `os.path.join()` or `pathlib.Path` for constructing file paths to ensure cross-platform compatibility.

4. **Error handling**: Include comprehensive error handling when loading files, with clear error messages that indicate the file path that couldn't be found.

5. **Testing**: Create test scripts to verify that files can be loaded correctly, especially when making changes to file paths or configuration.

## Related Files

- `core/config.py` - Contains the centralized configuration for file paths
- `streamlit_app/pages/03_send_rfq_emails.py` - Main Streamlit page for sending RFQ emails
- `streamlit_app/pages/06_send_emails.py` - Secondary Streamlit page for sending emails
- `docs/OS/vendor_options.yaml` - The vendor options file with vendor capabilities and approvals