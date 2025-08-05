"""
Find Vendors by Spec Script

This script searches through the vendor_options.yaml file and returns all vendors
that support a specific specification. It can be used to find vendors for any
spec, not just a specific one.

Usage:
    python scripts\find_vendors_by_spec.py <spec_number>

Example:
    python scripts\find_vendors_by_spec.py "ASTM B 912"

Requirements:
    - pyyaml package must be installed
    - vendor_options.yaml file must exist at the specified path
"""

import argparse
import os
import sys
from typing import Dict, List, Any, Optional, Tuple

import yaml


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Set up the argument parser for the script.

    Returns:
        ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Find vendors that support a specific specification"
    )
    parser.add_argument(
        "spec_number",
        help="Number of the specification to search for (case-insensitive)",
    )
    parser.add_argument(
        "--yaml-file",
        default=None,
        help="Path to the vendor_options.yaml file (default: docs/OS/vendor_options.yaml)",
    )
    parser.add_argument(
        "--exact-match",
        action="store_true",
        help="Require exact match for spec number (default: case-insensitive partial match)",
    )
    parser.add_argument(
        "--familiar-only",
        action="store_true",
        help="Only show vendors that are familiar with the spec (have familiar: true)",
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


def find_vendors_by_spec(
    vendor_options: Dict[str, Any],
    spec_number: str,
    exact_match: bool = False,
    familiar_only: bool = False
) -> List[Tuple[Dict[str, Any], str, Dict[str, Any]]]:
    """
    Find vendors that support a specific specification.

    Args:
        vendor_options: Dictionary containing vendor options data
        spec_number: Number of the specification to search for
        exact_match: Whether to require an exact match for the spec number
        familiar_only: Whether to only include vendors familiar with the spec

    Returns:
        List of tuples containing (vendor, process_name, spec) for each match
    """
    matching_vendors = []

    if 'vendors' not in vendor_options:
        return matching_vendors

    for vendor in vendor_options['vendors']:
        if 'processes' not in vendor:
            continue

        for process in vendor['processes']:
            if 'specs' not in process or not process['specs']:
                continue

            for spec in process['specs']:
                if 'number' not in spec:
                    continue

                # Skip if we only want familiar specs and this one isn't
                if familiar_only and not spec.get('familiar', False):
                    continue

                # Check if the spec matches
                if exact_match:
                    if spec['number'] == spec_number:
                        matching_vendors.append((vendor, process['name'], spec))
                else:
                    if spec_number.lower() in spec['number'].lower():
                        matching_vendors.append((vendor, process['name'], spec))

    return matching_vendors


def print_vendor_info(matches: List[Tuple[Dict[str, Any], str, Dict[str, Any]]], spec_number: str) -> None:
    """
    Print information about vendors that support a specific specification.

    Args:
        matches: List of tuples containing (vendor, process_name, spec) for each match
        spec_number: Number of the specification that was searched for
    """
    if not matches:
        print(f"No vendors found supporting specification: {spec_number}")
        return

    # Group matches by vendor
    vendor_matches = {}
    for vendor, process_name, spec in matches:
        vendor_name = vendor['name']
        if vendor_name not in vendor_matches:
            vendor_matches[vendor_name] = {
                'vendor': vendor,
                'processes': []
            }
        vendor_matches[vendor_name]['processes'].append({
            'name': process_name,
            'spec': spec
        })

    print(f"Found {len(vendor_matches)} vendor(s) supporting specification: {spec_number}")
    print("-" * 80)

    for vendor_name, data in vendor_matches.items():
        vendor = data['vendor']
        print(f"Vendor: {vendor_name}")
        if 'location' in vendor and vendor['location']:
            print(f"Location: {vendor['location']}")
        if 'website' in vendor and vendor['website']:
            print(f"Website: {vendor['website']}")
        
        print("Processes:")
        for process_data in data['processes']:
            process_name = process_data['name']
            spec = process_data['spec']
            familiar = "Yes" if spec.get('familiar', False) else "No"
            print(f"  - {process_name}")
            print(f"    Specification: {spec['number']} (Familiar: {familiar})")
        
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

        # Find vendors by spec
        matches = find_vendors_by_spec(
            vendor_options,
            args.spec_number,
            args.exact_match,
            args.familiar_only
        )

        # Print vendor information
        print_vendor_info(matches, args.spec_number)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()