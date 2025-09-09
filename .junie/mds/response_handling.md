# Response Handling Guide

## Overview

This document describes the response handling functionality for the RFQ Sender system. It covers how to parse, store, and analyze vendor responses to RFQs.

## Features

The response handling system provides the following features:

- Parse vendor responses from different file formats (PDF, MSG)
- Store response data in a structured database
- Compare quotes from different vendors for the same part/process
- Generate reports of responses with filtering options

## Database Schema

Responses are stored in the `response_log` table with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| rfq_id | INTEGER | Foreign key to rfq_log table (the original RFQ) |
| vendor_name | TEXT | Name of the vendor |
| vendor_email | TEXT | Email of the vendor |
| part_no | TEXT | Part number |
| process | TEXT | Process name |
| price | REAL | Quoted price |
| quantity | INTEGER | Quantity |
| lead_time | TEXT | Lead time (e.g., "2 weeks") |
| response_date | TIMESTAMP | When the response was received |
| notes | TEXT | Additional notes or comments |
| file_path | TEXT | Path to the original response file |

## Scripts

### response_parser.py

This is the core module for response handling. It provides functions for:

- Parsing response files (PDF, MSG)
- Storing responses in the database
- Comparing quotes
- Generating reports

#### Command-line Usage

Process all responses in a directory:
```bash
python scripts/response_parser.py --directory docs/OS/Responses
```

Compare quotes for a specific part and process:
```bash
python scripts/response_parser.py --compare --part_no "PART123" --process "ANODIZE TYPE II"
```

Generate a report of responses:
```bash
python scripts/response_parser.py --report
```

Filter the report:
```bash
python scripts/response_parser.py --report --part_no "PART123" --process "ANODIZE TYPE II" --start_date "2025-01-01" --end_date "2025-12-31"
```

### process_responses.py

This is a demonstration script that shows how to use the response_parser module to process responses and generate reports.

#### Usage

```bash
python scripts/process_responses.py
```

## Python API

### Parsing Responses

```python
from scripts.response_parser import process_response_directory

# Process all responses in a directory
responses = process_response_directory("path/to/responses")

# Each response is a dictionary with the following keys:
# - id: Database ID
# - vendor_name: Name of the vendor
# - vendor_email: Email of the vendor
# - part_no: Part number
# - process: Process name
# - price: Quoted price
# - quantity: Quantity
# - lead_time: Lead time
# - response_date: When the response was received
# - notes: Additional notes
# - file_path: Path to the original file
```

### Comparing Quotes

```python
from scripts.response_parser import compare_quotes

# Compare quotes for a specific part and process
quotes = compare_quotes("PART123", "ANODIZE TYPE II")

# Quotes are sorted by price (lowest first)
for quote in quotes:
    print(f"Vendor: {quote['vendor_name']}, Price: ${quote['price']}, Lead Time: {quote['lead_time']}")
```

### Generating Reports

```python
from scripts.response_parser import generate_response_report

# Generate a report of all responses
all_responses = generate_response_report()

# Filter by part number
part_responses = generate_response_report(part_no="PART123")

# Filter by process
process_responses = generate_response_report(process="ANODIZE TYPE II")

# Filter by date range
date_responses = generate_response_report(
    start_date="2025-01-01T00:00:00",
    end_date="2025-12-31T23:59:59"
)
```

## Current Implementation

The current implementation extracts information from response files using the following methods:

### PDF Parsing
- Extracts vendor information, part numbers, and prices from PDF filenames
- Identifies specific document types (e.g., Quote Forms) and extracts relevant information
- Generates reasonable estimates for prices and lead times based on available information

### MSG Parsing
- Extracts RFQ numbers from email subjects to generate part numbers
- Identifies vendor names from email subjects and sender information
- Recognizes specific processes mentioned in email subjects
- Handles different email formats (forwards, replies, portal notifications)

### Limitations
- The current implementation does not use specialized libraries for PDF or MSG parsing
- Information extraction is primarily based on filenames and basic patterns
- For accurate parsing, specialized libraries like PyPDF2 (for PDFs) and extract_msg (for MSG files) would be needed

## Future Enhancements

The current implementation provides basic functionality for response handling. Future enhancements may include:

1. **Improved Parsing**: Integrate specialized libraries for PDF and MSG parsing to extract more accurate information
2. **OCR Integration**: Add OCR capabilities for processing scanned documents
3. **Email Integration**: Automatically process responses received via email
4. **Web Interface**: Add a web interface for viewing and managing responses
5. **Notification System**: Send notifications when new responses are received
6. **Analytics**: Add analytics for tracking vendor performance over time

## Troubleshooting

### Common Issues

#### "No responses found in database"

This usually means that either:
- No response files have been processed yet
- The response files couldn't be parsed correctly

Try processing the response files again with more verbose logging:

```bash
python -m logging -v DEBUG scripts/response_parser.py --directory docs/OS/Responses
```

#### "Error: Responses directory not found"

Make sure the path to the responses directory is correct. The default path is:

```
docs/OS/Responses
```

If your responses are stored elsewhere, specify the full path:

```bash
python scripts/response_parser.py --directory /path/to/your/responses
```

## Conclusion

The response handling system provides a foundation for managing vendor responses to RFQs. It can be extended and enhanced as needed to meet specific requirements.
