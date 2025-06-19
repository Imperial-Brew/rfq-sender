# Find Vendors by Process Script Documentation

## Overview

The `find_vendors_by_process.py` script is a command-line tool that searches through the vendor_options.yaml file and returns all vendors that have a specific process capability. It can be used to find vendors for any process, not just 'SOL-EPOXY'.

## Usage

Run the script from the command line:

```
python scripts\find_vendors_by_process.py <process_name> [options]
```

### Arguments

- `process_name`: Name of the process to search for (case-insensitive by default)

### Options

- `--yaml-file PATH`: Path to the vendor_options.yaml file (default: docs/OS/vendor_options.yaml)
- `--exact-match`: Require exact match for process name (default: case-insensitive partial match)

### Examples

1. Find vendors that can handle 'SOL-EPOXY':
   ```
   python scripts\find_vendors_by_process.py "SOL-EPOXY"
   ```

2. Find vendors that can handle any process containing 'nickel':
   ```
   python scripts\find_vendors_by_process.py "nickel"
   ```

3. Find vendors that can handle exactly 'Nickel Plating':
   ```
   python scripts\find_vendors_by_process.py "Nickel Plating" --exact-match
   ```

4. Use a custom vendor options file:
   ```
   python scripts\find_vendors_by_process.py "SOL-EPOXY" --yaml-file path\to\custom_vendor_options.yaml
   ```

## Output

The script outputs information about vendors that have the specified process capability:

- Vendor name
- Location (if available)
- Website (if available)
- Process name
- Specifications for the process (if available)

If no vendors are found with the specified process capability, the script will indicate this.

## Requirements

- pyyaml package must be installed
- vendor_options.yaml file must exist at the specified path

## Implementation Details

The script performs the following steps:

1. Parse command-line arguments
2. Load vendor options from the YAML file
3. Find vendors that have the specified process capability
4. Print information about the matching vendors

The search is case-insensitive by default, meaning that searching for 'nickel' will match 'Nickel Plating', 'Bright Nickel', etc. If the `--exact-match` option is used, the search will only match processes with the exact name specified.

## Error Handling

The script includes error handling for:
- Missing YAML file
- Invalid YAML file
- Invalid command-line arguments

## Future Enhancements

Possible future enhancements for this script include:
- Support for searching by specification number
- Support for filtering vendors by location
- Support for outputting results in different formats (JSON, CSV, etc.)
- Integration with the email_from_list.py script to automatically select vendors for processes