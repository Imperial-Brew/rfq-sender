# Email From List Script Documentation

## Overview

The `email_from_list.py` script automates the process of sending Request for Quote (RFQ) emails to vendors. It reads a queue of RFQ items from a CSV file, matches them with suitable vendors based on process capabilities, creates draft emails in Outlook for each process (creating separate emails for each process), attaches files, and logs the actions.

## Data Sources

The script uses the following data sources:

1. **Queue.csv** - Contains the RFQ items with part numbers, processes, and file paths
   - Located at: `data/Queue.csv`
   - Required columns: `quote_id`, `part_number`, `process`, `file_path`
   - Optional columns: `line`, `callout`, `spec`, `qty`

2. **contacts.csv** - Contains vendor contact information
   - Located at: `docs/OS/contacts.csv`
   - Used to get vendor email addresses and names
   - Filters to vendors with type = 'finishing'

3. **vendor_options.yaml** - Contains vendor capabilities and approvals
   - Located at: `docs/OS/vendor_options.yaml`
   - Used to match processes required for quotes with vendor capabilities

4. **cover_letter.j2** - Jinja2 template for email body
   - Located at: `docs/templates/cover_letter.j2`
   - Used to create a standardized email body

5. **Sample_Table(Empty)-OS.csv** - Template for quote table
   - Located at: `docs/templates/Sample_Table(Empty)-OS.csv`
   - Included in the email body for vendors to fill out

## Functionality

### Vendor Selection

The script matches quotes with suitable vendors by:

1. Extracting the processes needed for each quote
2. For each process, checking if spec information is available
3. If spec information is available:
   - Searching for all vendors that support that specific spec
   - If no vendors are found for the spec, falling back to searching by process
4. If no suitable vendors are found at all:
   - Logging an error about no suitable vendors being found
   - Skipping the item and moving to the next one
   - Recording the skip in the logs with status 'skipped_no_vendor_{process}'
5. For each suitable vendor found:
   - Creating a separate email for that vendor
   - This ensures that all capable vendors receive the RFQ, not just one

### Email Creation

For each process in a quote and for each suitable vendor, the script:

1. Creates a separate email with:
   - Addresses the email to the contact's first name from contacts.csv for a personalized greeting
   - Either a simple HTML email or a rendered Jinja2 template
   - Part information, including part number, quantity, process, spec, and callout
   - A formatted HTML table for the vendor to fill out (based on Sample_Table(Empty)-OS.csv)
   - Uses Outlook's general signature for a professional appearance
2. Attaches relevant files (validating file paths first)
3. Creates a draft email in Outlook with proper HTML formatting

This means that if three vendors can handle a particular process, three separate emails will be created - one for each vendor.

### Logging

The script logs all actions to:
- Console output
- Log file at `logs/email_from_list.log`
- CSV log at `logs.csv` (records quote_id, vendor_id, timestamp, and status)

## Usage

Run the script from the command line:

```
python scripts\email_from_list.py
```

## Requirements

- pandas package
- pywin32 package
- pyyaml package
- jinja2 package
- Outlook must be installed and configured
- Required files must exist at the specified paths

## Error Handling

The script includes comprehensive error handling for:
- Missing files
- Missing required columns
- Invalid file paths
- Outlook initialization failures
- Email creation issues
- Processes not listed in vendor_options.yaml

## Example

For a quote with processes "NICKEL PLATE" (spec: "AMS 2403") and "SOL-EPOXY", the script will:
1. Process "NICKEL PLATE":
   - First search for vendors that support spec "AMS 2403"
   - If found, for each vendor that supports this spec:
     - Create an email with details of parts requiring "NICKEL PLATE"
     - Include a sample table for the vendor to fill out
     - Attach the relevant files
     - Create a draft email in Outlook
   - If no vendors found for the spec, fall back to searching for vendors that can handle "NICKEL PLATE"
   - For each vendor that can handle "NICKEL PLATE":
     - Create an email with details of parts requiring "NICKEL PLATE"
     - Include a sample table for the vendor to fill out
     - Attach the relevant files
     - Create a draft email in Outlook
   - If no suitable vendors found at all, log an error and skip this process
2. Process "SOL-EPOXY":
   - If a spec is provided, search for vendors that support that spec
   - For each vendor that supports the spec:
     - Create an email with details of parts requiring "SOL-EPOXY"
     - Include a sample table for the vendor to fill out
     - Attach the relevant files
     - Create a draft email in Outlook
   - If no vendors found for the spec, search for vendors that can handle "SOL-EPOXY"
   - For each vendor that can handle "SOL-EPOXY":
     - Create an email with details of parts requiring "SOL-EPOXY"
     - Include a sample table for the vendor to fill out
     - Attach the relevant files
     - Create a draft email in Outlook
   - If no suitable vendors found at all, log an error and skip this process
3. Log all actions

This approach ensures that all vendors capable of handling a particular process receive an RFQ, maximizing the chances of getting competitive quotes.

## Customization

To customize the script for different environments:
1. Update file paths in the `main()` function
2. Modify column mappings in the `load_data()` function
3. Adjust email templates in the `create_email_body()` function
4. Customize the signature in the `main()` function (used as fallback if Outlook signature is not available)
5. Toggle HTML formatting with the `html_format` parameter in `create_email_body()` and `create_draft_email()`
6. Toggle Outlook signature usage with the `use_outlook_signature` parameter in `create_draft_email()`
7. Modify the vendor selection logic in the `process_queue()` function if needed
8. Adjust HTML table styling in the `create_sample_table()` function

## Future Enhancements

The following enhancements are planned for future updates:
1. Improved file retrieval and attachment handling
2. Support for interactive vendor selection for processes not in vendor_options.yaml
3. Ability to save vendor process capabilities back to vendor_options.yaml
4. Support for HTML email templates
