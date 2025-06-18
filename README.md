# RFQ Sender System

A system for managing and sending Request for Quote (RFQ) emails to multiple vendors for finishing, material, and hardware quotes.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Development](#development)
- [Scalability](#scalability)
- [Contributing](#contributing)
- [License](#license)

## Problem Statement

- Need to manage quotes for finishing/material/hardware
- Working with multiple vendors, each with multiple contacts
- Dealing with various processes with different industry names and specifications
- Managing customers with their own internal naming conventions
- Handling file sharing with security requirements (CUI/ITAR)

## Solution

The RFQ Sender System provides:

- Secure file sharing within security requirements (CUI/ITAR)
- Accurate process specifications to vendors with all relevant data
- Price and lead time comparison capabilities
- File preparation based on BOM (Bill of Materials)
- Individual emails to multiple vendors (no BCC)
- Automated form population from vendor responses
- Integration with Paperless API (including file attachments)

## Project Structure

```
rfq-sender/
├── config/           # Configuration files (vendors, email settings)
├── data/             # Database and data files
├── docs/             # Documentation
├── scripts/          # Python scripts
├── templates/        # Jinja2 templates for emails and forms
└── tests/            # Test files
```

## Setup

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Edit `.env` with your actual configuration values
5. Configure vendor and email settings in the config directory

## Environment Variables

The application uses environment variables for sensitive configuration such as email credentials. These are stored in a `.env` file which is not committed to the repository for security reasons.

Required environment variables:

- `SMTP_SERVER`: SMTP server address
- `SMTP_PORT`: SMTP server port (usually 587 for TLS)
- `SMTP_USE_TLS`: Whether to use TLS for SMTP (true/false)
- `SMTP_USERNAME`: SMTP username
- `SMTP_PASSWORD`: SMTP password
- `SMTP_FROM_EMAIL`: Email address to send from
- `SMTP_FROM_NAME`: Display name for the sender

Optional environment variables:

- `SUBJECT_PREFIX`: Prefix for email subjects (default: [RFQ])
- `CC_EMAILS`: Comma-separated list of email addresses to CC
- `BCC_EMAILS`: Comma-separated list of email addresses to BCC
- `MAX_ATTACHMENT_SIZE_MB`: Maximum attachment size in MB (default: 10)
- `COMPANY_NAME`: Your company name for email templates (default: "Your Company")

If using Exchange instead of SMTP:

- `USE_EXCHANGE`: Whether to use Exchange instead of SMTP (true/false)
- `EXCHANGE_SERVER`: Exchange server address
- `EXCHANGE_USERNAME`: Exchange username
- `EXCHANGE_PASSWORD`: Exchange password
- `EXCHANGE_EMAIL`: Exchange email address
- `EXCHANGE_FROM_NAME`: Display name for the sender

Security settings:

- `ENABLE_CUI_PROTECTION`: Whether to enable CUI protection (true/false)
- `CUI_WARNING_TEXT`: Warning text to include in emails with CUI data

## Usage

Basic usage:

```
python scripts\rfq_sender.py --part_no "0250-20000" --process "cleaning" --quantities "1,2,5,10" --file_location "path\to\files"
```

For more options:

```
python scripts\rfq_sender.py --help
```

### Test Email

To create a test email draft in Outlook without sending it:

```
python scripts\create_test_email.py
```

This will create a draft email in Outlook with a test subject and body, allowing you to verify your email configuration before sending actual RFQs.

## Development

This project follows the style guidelines outlined in the [Project Style Guidelines](.junie/guidelines.md).

### Style Guidelines Overview

- **Python Code Style**: Use type hints, follow PEP 8, use docstrings with Args/Returns sections
- **Markdown Formatting**: Use GitHub Flavored Markdown, task lists, code blocks with language identifiers
- **Commit Messages**: Use the format `<scope>(<module>): <short summary>`
- **Documentation**: Maintain comprehensive README.md, document classes and methods
- **Project Structure**: Place scripts in scripts/ directory, use modular components
- **Testing and Quality**: Write tests using pytest, use pre-commit hooks
- **Logging**: Use appropriate log levels (info, warning, error) with context
- **Security**: Store sensitive information in environment variables, never in code

## Scalability

The RFQ Sender system is designed to handle a moderate volume of RFQs, vendors, and attachments. For larger scale operations, consider the following:

- **Database**: SQLite is suitable for development and small deployments. For production with high concurrency, consider migrating to PostgreSQL or MySQL.
- **Email Processing**: For large batches of emails, implement batch processing and rate limiting to avoid overwhelming SMTP servers.
- **File Handling**: Large attachments should be handled with care, potentially implementing streaming or compression.
- **Asynchronous Processing**: Consider refactoring to use async/await for improved performance with I/O-bound operations.

For detailed recommendations on scaling the RFQ Sender system, see [Scaling Guide](docs/SCALING.md).

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
