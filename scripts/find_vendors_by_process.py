"""
Find Vendors by Process Script

This script searches through the vendor_options.yaml file and returns all vendors
that have a specific process capability. It can be used to find vendors for any
process, not just 'SOL-EPOXY'.

Usage:
    python scripts\find_vendors_by_process.py <process_name>

Example:
    python scripts\find_vendors_by_process.py "SOL-EPOXY"

Requirements:
    - pyyaml package must be installed
    - vendor_options.yaml file must exist at the specified path
"""

import argparse
import os
import sys
from typing import Dict, List, Any, Optional

import yaml


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Set up the argument parser for the script.

    Returns:
        ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Find vendors with a specific process capability"
    )
    parser.add_argument(
        "process_name",
        help="Name of the process to search for (case-insensitive)",
    )
    parser.add_argument(
        "--yaml-file",
        default=None,
        help="Path to the vendor_options.yaml file (default: docs/OS/vendor_options.yaml)",
    )
    parser.add_argument(
        "--exact-match",
        action="store_true",
        help="Require exact match for process name (default: case-insensitive partial match)",
    )
    return parser


def load_vendor_options(file_path: str) -> Dict[str, Any]:
    """
    Load vendor options from YAML file.

    Args:
        file_path: Path to the vendor_options.yaml file

    Returns:
        Dictionary containing vendor options data

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Vendor options file not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)
        return vendor_options
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {str(e)}")


def find_vendors_by_process(
    vendor_options: Dict[str, Any],
    process_name: str,
    exact_match: bool = False
) -> List[Dict[str, Any]]:
    """
    Find vendors that have a specific process capability.

    Args:
        vendor_options: Dictionary containing vendor options data
        process_name: Name of the process to search for
        exact_match: Whether to require an exact match for the process name

    Returns:
        List of vendors that have the specified process capability
    """
    matching_vendors = []

    if 'vendors' not in vendor_options:
        return matching_vendors

    for vendor in vendor_options['vendors']:
        if 'processes' not in vendor:
            continue

        for process in vendor['processes']:
            if 'name' not in process:
                continue

            if exact_match:
                if process['name'] == process_name:
                    matching_vendors.append(vendor)
                    break
            else:
                if process_name.lower() in process['name'].lower():
                    matching_vendors.append(vendor)
                    break

    return matching_vendors


def print_vendor_info(vendors: List[Dict[str, Any]], process_name: str) -> None:
    """
    Print information about vendors that have a specific process capability.

    Args:
        vendors: List of vendors that have the specified process capability
        process_name: Name of the process that was searched for
    """
    if not vendors:
        print(f"No vendors found with process capability: {process_name}")
        return

    print(f"Found {len(vendors)} vendor(s) with process capability: {process_name}")
    print("-" * 80)

    for vendor in vendors:
        print(f"Vendor: {vendor['name']}")
        if 'location' in vendor and vendor['location']:
            print(f"Location: {vendor['location']}")
        if 'website' in vendor and vendor['website']:
            print(f"Website: {vendor['website']}")
        
        # Find the matching process to show its specs
        for process in vendor['processes']:
            if (process_name.lower() in process['name'].lower()):
                print(f"Process: {process['name']}")
                if 'specs' in process and process['specs']:
                    print("Specifications:")
                    for spec in process['specs']:
                        familiar = "Yes" if spec.get('familiar', False) else "No"
                        print(f"  - {spec['number']} (Familiar: {familiar})")
                break
        print("-" * 80)


def main() -> None:
    """Main entry point for the script."""
    try:
        # Parse command line arguments
        parser = setup_argument_parser()
        args = parser.parse_args()

        # Determine the path to the vendor_options.yaml file
        if args.yaml_file:
            yaml_file = args.yaml_file
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            yaml_file = os.path.join(project_root, 'docs', 'OS', 'vendor_options.yaml')

        # Load vendor options
        vendor_options = load_vendor_options(yaml_file)

        # Find vendors by process
        vendors = find_vendors_by_process(
            vendor_options,
            args.process_name,
            args.exact_match
        )

        # Print vendor information
        print_vendor_info(vendors, args.process_name)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()