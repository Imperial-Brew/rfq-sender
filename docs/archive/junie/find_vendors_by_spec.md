# Find Vendors by Spec Script Documentation

## Overview

The `find_vendors_by_spec.py` script is a command-line tool that searches through the vendor_options.yaml file and returns all vendors that support a specific specification. It can be used to find vendors for any specification, not just a specific one.

## Usage

Run the script from the command line:

```
python scripts\find_vendors_by_spec.py <spec_number> [options]
```

### Arguments

- `spec_number`: Number of the specification to search for (case-insensitive by default)

### Options

- `--yaml-file PATH`: Path to the vendor_options.yaml file (default: docs/OS/vendor_options.yaml)
- `--exact-match`: Require exact match for spec number (default: case-insensitive partial match)
- `--familiar-only`: Only show vendors that are familiar with the spec (have familiar: true)

### Examples

1. Find vendors that support 'ASTM B 912':
   ```
   python scripts\find_vendors_by_spec.py "ASTM B 912"
   ```

2. Find vendors that support any specification containing 'ASTM':
   ```
   python scripts\find_vendors_by_spec.py "ASTM"
   ```

3. Find vendors that support exactly 'MIL-A-8625':
   ```
   python scripts\find_vendors_by_spec.py "MIL-A-8625" --exact-match
   ```

4. Find vendors that are familiar with 'ASTM A 967':
   ```
   python scripts\find_vendors_by_spec.py "ASTM A 967" --familiar-only
   ```

5. Use a custom vendor options file:
   ```
   python scripts\find_vendors_by_spec.py "ASTM B 912" --yaml-file path\to\custom_vendor_options.yaml
   ```

## Output

The script outputs information about vendors that support the specified specification:

- Vendor name
- Location (if available)
- Website (if available)
- Processes that support the specification
- Specification details, including whether the vendor is familiar with it

If no vendors are found supporting the specified specification, the script will indicate this.

## Requirements

- pyyaml package must be installed
- vendor_options.yaml file must exist at the specified path

## Implementation Details

The script performs the following steps:

1. Parse command-line arguments
2. Load vendor options from the YAML file
3. Find vendors that support the specified specification
4. Group the results by vendor
5. Print information about the matching vendors

The search is case-insensitive by default, meaning that searching for 'astm' will match 'ASTM B 912', 'ASTM A 967', etc. If the `--exact-match` option is used, the search will only match specifications with the exact number specified.

The `--familiar-only` option filters the results to only include vendors that have marked themselves as familiar with the specification (have `familiar: true` in the YAML file).

## Error Handling

The script includes error handling for:
- Missing YAML file
- Invalid YAML file
- Invalid command-line arguments

## Comparison with find_vendors_by_process.py

While `find_vendors_by_process.py` searches for vendors based on the processes they can perform (like "Anodize" or "Electropolish"), `find_vendors_by_spec.py` searches for vendors based on the specifications they support (like "ASTM B 912" or "MIL-A-8625").

This allows for more precise matching when you have a specific specification requirement, rather than just a general process requirement.

## Future Enhancements

Possible future enhancements for this script include:
- Support for searching by both specification and process
- Support for filtering vendors by location
- Support for outputting results in different formats (JSON, CSV, etc.)
- Integration with the email_from_list.py script to automatically select vendors for specifications