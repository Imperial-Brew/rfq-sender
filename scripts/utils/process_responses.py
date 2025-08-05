#!/usr/bin/env python
"""
Process Responses - Demo script for processing RFQ responses

This script demonstrates how to use the response_parser module
to process RFQ responses from the docs/OS/Responses directory.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path to allow importing from scripts
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from scripts.response_parser import (
    process_response_directory,
    compare_quotes,
    generate_response_report,
)


def main():
    """
    Main function to demonstrate response processing.
    """
    # Path to the responses directory
    responses_dir = os.path.join(project_root, "docs", "OS", "Responses")
    
    # Check if the directory exists
    if not os.path.isdir(responses_dir):
        print(f"Error: Responses directory not found at {responses_dir}")
        return
    
    print(f"Processing responses in {responses_dir}...")
    
    # Process all responses in the directory
    responses = process_response_directory(responses_dir)
    
    print(f"\nProcessed {len(responses)} response files:")
    for resp in responses:
        print(f"- {os.path.basename(resp['file_path'])}: {resp['vendor_name']}")
    
    # Example of generating a report for all responses
    print("\nGenerating report of all responses:")
    all_responses = generate_response_report()
    
    if all_responses:
        print(f"Found {len(all_responses)} total responses in database")
        
        # Display a simple table of responses
        print("\n{:<5} {:<20} {:<15} {:<10} {:<15}".format(
            "ID", "Vendor", "Part No", "Price", "Lead Time"
        ))
        print("-" * 70)
        
        for resp in all_responses:
            print("{:<5} {:<20} {:<15} ${:<9.2f} {:<15}".format(
                resp['id'],
                resp['vendor_name'][:20],
                resp['part_no'][:15],
                resp['price'] or 0.0,
                resp['lead_time'][:15]
            ))
    else:
        print("No responses found in database")
    
    # Example of comparing quotes (if we had real part numbers)
    # This is just a placeholder since we don't have real data yet
    print("\nNote: To compare quotes for a specific part and process, use:")
    print("python scripts/response_parser.py --compare --part_no PART123 --process \"ANODIZE TYPE II\"")
    
    print("\nNote: For a filtered report, use:")
    print("python scripts/response_parser.py --report --part_no PART123 --process \"ANODIZE TYPE II\"")


if __name__ == "__main__":
    main()