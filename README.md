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
├── .devcontainer/    # Development container configuration
├── .github/          # GitHub workflows and templates
├── .junie/           # Project task tracking and documentation
├── .streamlit/       # Streamlit configuration
├── cli/              # Command-line interface tools
├── config/           # Configuration files (vendors, email settings)
├── core/             # Core application modules
├── data_raw/         # Raw data files (CSV, input files)
├── data_cleaned/     # Processed data files (databases, cleaned data)
├── docs/             # Documentation
│   ├── Material/     # Material-related documentation
│   ├── OS/           # Operating system specific documentation
│   └── templates/    # Documentation templates
├── logs/             # Application logs
├── scripts/          # Python scripts
│   ├── box/          # Box integration scripts
│   ├── email/        # Email-related scripts
│   ├── utils/        # Utility scripts
│   └── vendor/       # Vendor-related scripts
├── streamlit_app/    # Streamlit web application
│   ├── app.py        # Main Streamlit application
│   ├── components/   # Reusable UI components
│   ├── utils/        # Streamlit-specific utilities
│   └── pages/        # Multi-page Streamlit app pages
│       ├── 00_login.py                  # Login page
│       ├── 01_queue_management.py       # Queue management
│       ├── 02_specifications_management.py # Specifications management
│       ├── 03_send_rfq_emails.py        # Send RFQ emails
│       ├── 04_bug_tracker.py            # Bug tracking system
│       ├── 05_vendors.py                # Vendor management
│       └── 06_send_emails.py            # Alternative email sending
├── templates/        # Jinja2 templates for emails and forms
├── tests/            # Test files
│   ├── bug_tracker/  # Bug tracker tests
│   ├── config/       # Configuration tests
│   ├── data/         # Data loading tests
│   ├── email/        # Email functionality tests
│   ├── fixes/        # Bug fix tests
│   ├── logging/      # Logging tests
│   ├── queue/        # Queue tests
│   └── vendor/       # Vendor tests
└── utils/            # Utility modules (specs, queue, email, auth)
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

## Mail backend (Microsoft Graph)

The app now uses Microsoft Graph exclusively to create Draft emails. EWS/SMTP settings are no longer used by the mail code paths.

- Configure your mailbox UPN and optional default CC under .streamlit/secrets.toml → [exchange].
- Configure your Azure app credentials under .streamlit/secrets.toml → [azure].
- Company information used in email templates is under .streamlit/secrets.toml → [company].
- Subject prefix is under .streamlit/secrets.toml → [app].

Sample .streamlit/secrets.toml:

[exchange]
username = "user@yourdomain.com"
cc       = "quotes@yourdomain.com"

[azure]
tenant_id     = "<tenant-guid>"
client_id     = "<app-client-id>"
client_secret = "<app-client-secret>"

[company]
name         = "Your Company"
sender_name  = "Your Name"
sender_email = "user@yourdomain.com"
sender_title = "Estimating Manager"
sender_phone = "555-555-5555"

[app]
subject_prefix = "[RFQ-]"

Quick smoke test (creates a Draft in the configured mailbox):

PowerShell:

python .\scripts\smoke_graph.py

See docs/implementation/graph_migration.md for details.

## Environment Variables

Note: For email, the Graph backend uses .streamlit/secrets.toml (see section above). The SMTP/Exchange env vars below are legacy and retained for historical reference.

The application uses environment variables for other sensitive configuration. These may be stored in a `.env` file which is not committed to the repository for security reasons.

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

## Box Integration

The RFQ Sender System uses Box for secure file sharing, allowing you to upload attachments to Box and include share links in emails instead of attaching files directly. This is especially useful for large files or when dealing with sensitive information.

### Box Configuration

Box integration uses JWT authentication for secure server-to-server communication. To set up Box integration:

1. Create a Box developer account and create a Custom App with "Server Authentication (with JWT)" access type
2. Download the JSON configuration file with your credentials
3. Save the configuration file as `scripts/box/0__config.json`

The configuration file should include:
- Client ID and Client Secret
- Public Key ID and Private Key
- Enterprise ID

No environment variables are needed for Box integration as all credentials are stored in the `0__config.json` file.

### Hybrid Folder Structure

The RFQ Sender System uses a hybrid folder structure in Box to organize RFQ documentation:

```
/Box/FinishingRFQs/QT57267/
├── PN-001/
├── PN-002/
├── PN-003/
├── PN-004/
├── PN-005/
└── vendor_links/
    ├── HeatTreatCo/
    ├── AnodizePro/
    └── NickelWorks/
```

This structure:
- Organizes files first by quote/order number, then by part number
- Creates vendor-specific folders in a subfolder
- Shares only relevant parts with each vendor via Box links
- Minimizes file duplication while maintaining security

For more details on the hybrid folder structure, see [Box Hybrid Structure](.junie/mds/box_hybrid_structure.md).

## Usage

### Streamlit Web Interface

The recommended way to use the RFQ Sender System is through the Streamlit web interface:

```
streamlit run streamlit_app\app.py
```

This will start the Streamlit server and open the application in your default web browser. The web interface provides the following features:

1. **Add to Queue**: Add new parts to the RFQ queue
2. **View Queue**: View and filter the current queue
3. **Add Spec/Process**: Add new specifications and processes to the database
4. **View Familiar Specs**: View and search familiar specifications
5. **Send RFQ Emails**: Send RFQ emails to vendors for parts in the queue

### Bug Tracker

The system includes a bug tracking page that allows users to submit and track bug reports and feature requests. To access the bug tracker:

```
streamlit run streamlit_app\app.py
```

Or use the provided batch script:

```
Start_streamlit_app.bat
```

The bug tracker will appear as a page in the sidebar navigation. For more information, see [Bug Tracker Documentation](.junie/mds/bug_tracker.md).

### Command Line Scripts

For automation and batch processing, you can also use the command line scripts:

```
python scripts\rfq_sender.py --part_no "0250-20000" --process "cleaning" --quantities "1,2,5,10" --file_location "path\to\files"
```

For more options:

```
python scripts\rfq_sender.py --help
```

### Email Processing

To process the queue and send emails from the command line:

```
python scripts\email_from_list.py
```

### Test Email

To create a test email draft in Outlook without sending it:

```
python scripts\create_test_email.py
```

This will create a draft email in Outlook with a test subject and body, allowing you to verify your email configuration before sending actual RFQs.

## Development

This project follows the style guidelines outlined in the [Project Style Guidelines](.junie/mds/guidelines.md). For a comprehensive index of all documentation files, see the [Documentation Index](.junie/mds/DOCUMENTATION_INDEX.md).

### Style Guidelines Overview
- **Python Code Style**: Use type hints for all function parameters and return values, follow PEP 8 with exceptions noted in .flake8, use docstrings with Args/Returns sections
- **Markdown Formatting**: Use GitHub Flavored Markdown, task lists, code blocks with language identifiers, keep lines <= 80 characters
- **Commit Messages**: Use the format `<scope>(<module>): <short summary>`
- **Documentation**: Maintain comprehensive README.md, document classes and methods with detailed docstrings, update CHANGELOG.md
- **Project Structure**: Place scripts in scripts/ directory with subdirectories for specific functionality, use modular components
- **Testing and Quality**: Write unit and integration tests using pytest, use pre-commit hooks, run flake8 for linting
- **Logging**: Use appropriate log levels (info, warning, error) with context, configure log rotation
- **Security**: Store sensitive information in environment variables, never in code, use pre-commit hooks to prevent committing secrets
- **Scalability and Performance**: Design for horizontal scaling, implement caching, use asynchronous processing for I/O-bound operations
- **Deployment and Operations**: Use containerization (Docker), implement CI/CD pipelines, have a rollback strategy

## Scalability

The RFQ Sender system is designed to handle a moderate volume of RFQs, vendors, and attachments. For larger scale operations, consider the following:

- **Database**: SQLite is suitable for development and small deployments. For production with high concurrency, consider migrating to PostgreSQL or MySQL.
- **Email Processing**: For large batches of emails, implement batch processing and rate limiting to avoid overwhelming SMTP servers.
- **File Handling**: Large attachments should be handled with care, potentially implementing streaming or compression.
- **Asynchronous Processing**: Consider refactoring to use async/await for improved performance with I/O-bound operations.

For detailed recommendations on scaling the RFQ Sender system, see [Scaling Guide](.junie/mds/SCALING.md).

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

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
- [Testing](#testing)
- [Release Checklist](#release-checklist)
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
├── .devcontainer/    # Development container configuration
├── .github/          # GitHub workflows and templates
├── .junie/           # Project task tracking and documentation
├── .streamlit/       # Streamlit configuration
├── cli/              # Command-line interface tools
├── config/           # Configuration files (vendors, email settings)
├── core/             # Core application modules
├── data_raw/         # Raw data files (CSV, input files)
├── data_cleaned/     # Processed data files (databases, cleaned data)
├── docs/             # Documentation
│   ├── Material/     # Material-related documentation
│   ├── OS/           # Operating system specific documentation
│   └── templates/    # Documentation templates
├── logs/             # Application logs
├── scripts/          # Python scripts
│   ├── box/          # Box integration scripts
│   ├── email/        # Email-related scripts
│   ├── utils/        # Utility scripts
│   └── vendor/       # Vendor-related scripts
├── streamlit_app/    # Streamlit web application
│   ├── app.py        # Main Streamlit application
│   ├── components/   # Reusable UI components
│   ├── utils/        # Streamlit-specific utilities
│   └── pages/        # Multi-page Streamlit app pages
│       ├── 00_login.py                  # Login page
│       ├── 01_queue_management.py       # Queue management
│       ├── 02_specifications_management.py # Specifications management
│       ├── 03_send_rfq_emails.py        # Send RFQ emails
│       ├── 04_bug_tracker.py            # Bug tracking system
│       ├── 05_vendors.py                # Vendor management
│       └── 06_send_emails.py            # Alternative email sending
├── templates/        # Jinja2 templates for emails and forms
├── tests/            # Test files
│   ├── bug_tracker/  # Bug tracker tests
│   ├── config/       # Configuration tests
│   ├── data/         # Data loading tests
│   ├── email/        # Email functionality tests
│   ├── fixes/        # Bug fix tests
│   ├── logging/      # Logging tests
│   ├── queue/        # Queue tests
│   └── vendor/       # Vendor tests
└── utils/            # Utility modules (specs, queue, email, auth)
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

## Mail backend (Microsoft Graph)

The app now uses Microsoft Graph exclusively to create Draft emails. EWS/SMTP settings are no longer used by the mail code paths.

- Configure your mailbox UPN and optional default CC under .streamlit/secrets.toml → [exchange].
- Configure your Azure app credentials under .streamlit/secrets.toml → [azure].
- Company information used in email templates is under .streamlit/secrets.toml → [company].
- Subject prefix is under .streamlit/secrets.toml → [app].

Sample .streamlit/secrets.toml:

[exchange]
username = "user@yourdomain.com"
cc       = "quotes@yourdomain.com"

[azure]
tenant_id     = "<tenant-guid>"
client_id     = "<app-client-id>"
client_secret = "<app-client-secret>"

[company]
name         = "Your Company"
sender_name  = "Your Name"
sender_email = "user@yourdomain.com"
sender_title = "Estimating Manager"
sender_phone = "555-555-5555"

[app]
subject_prefix = "[RFQ-]"

Quick smoke test (creates a Draft in the configured mailbox):

PowerShell:

python .\scripts\smoke_graph.py

See docs/implementation/graph_migration.md for details.

## Environment Variables

Note: For email, the Graph backend uses .streamlit/secrets.toml (see section above). The SMTP/Exchange env vars below are legacy and retained for historical reference.

The application uses environment variables for other sensitive configuration. These may be stored in a `.env` file which is not committed to the repository for security reasons.

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

## Box Integration

The RFQ Sender System uses Box for secure file sharing, allowing you to upload attachments to Box and include share links in emails instead of attaching files directly. This is especially useful for large files or when dealing with sensitive information.

### Box Configuration

Box integration uses JWT authentication for secure server-to-server communication. To set up Box integration:

1. Create a Box developer account and create a Custom App with "Server Authentication (with JWT)" access type
2. Download the JSON configuration file with your credentials
3. Save the configuration file as `scripts/box/0__config.json`

The configuration file should include:
- Client ID and Client Secret
- Public Key ID and Private Key
- Enterprise ID

No environment variables are needed for Box integration as all credentials are stored in the `0__config.json` file.

### Hybrid Folder Structure

The RFQ Sender System uses a hybrid folder structure in Box to organize RFQ documentation:

```
/Box/FinishingRFQs/QT57267/
├── PN-001/
├── PN-002/
├── PN-003/
├── PN-004/
├── PN-005/
└── vendor_links/
    ├── HeatTreatCo/
    ├── AnodizePro/
    └── NickelWorks/
```

This structure:
- Organizes files first by quote/order number, then by part number
- Creates vendor-specific folders in a subfolder
- Shares only relevant parts with each vendor via Box links
- Minimizes file duplication while maintaining security

For more details on the hybrid folder structure, see [Box Hybrid Structure](.junie/mds/box_hybrid_structure.md).

## Usage

### Streamlit Web Interface

The recommended way to use the RFQ Sender System is through the Streamlit web interface:

```
streamlit run streamlit_app\app.py
```

This will start the Streamlit server and open the application in your default web browser. The web interface provides the following features:

1. **Add to Queue**: Add new parts to the RFQ queue
2. **View Queue**: View and filter the current queue
3. **Add Spec/Process**: Add new specifications and processes to the database
4. **View Familiar Specs**: View and search familiar specifications
5. **Send RFQ Emails**: Send RFQ emails to vendors for parts in the queue

### Bug Tracker

The system includes a bug tracking page that allows users to submit and track bug reports and feature requests. To access the bug tracker:

```
streamlit run streamlit_app\app.py
```

Or use the provided batch script:

```
Start_streamlit_app.bat
```

The bug tracker will appear as a page in the sidebar navigation. For more information, see [Bug Tracker Documentation](.junie/mds/bug_tracker.md).

### Command Line Scripts

For automation and batch processing, you can also use the command line scripts:

```
python scripts\rfq_sender.py --part_no "0250-20000" --process "cleaning" --quantities "1,2,5,10" --file_location "path\to\files"
```

For more options:

```
python scripts\rfq_sender.py --help
```

### Email Processing

To process the queue and send emails from the command line:

```
python scripts\email_from_list.py
```

### Test Email

To create a test email draft in Outlook without sending it:

```
python scripts\create_test_email.py
```

This will create a draft email in Outlook with a test subject and body, allowing you to verify your email configuration before sending actual RFQs.

## Development

This project follows the style guidelines outlined in the [Project Style Guidelines](.junie/mds/guidelines.md). For a comprehensive index of all documentation files, see the [Documentation Index](.junie/mds/DOCUMENTATION_INDEX.md).

### Style Guidelines Overview
- **Python Code Style**: Use type hints for all function parameters and return values, follow PEP 8 with exceptions noted in .flake8, use docstrings with Args/Returns sections
- **Markdown Formatting**: Use GitHub Flavored Markdown, task lists, code blocks with language identifiers, keep lines <= 80 characters
- **Commit Messages**: Use the format `<scope>(<module>): <short summary>`
- **Documentation**: Maintain comprehensive README.md, document classes and methods with detailed docstrings, update CHANGELOG.md
- **Project Structure**: Place scripts in scripts/ directory with subdirectories for specific functionality, use modular components
- **Testing and Quality**: Write unit and integration tests using pytest, use pre-commit hooks, run flake8 for linting
- **Logging**: Use appropriate log levels (info, warning, error) with context, configure log rotation
- **Security**: Store sensitive information in environment variables, never in code, use pre-commit hooks to prevent committing secrets
- **Scalability and Performance**: Design for horizontal scaling, implement caching, use asynchronous processing for I/O-bound operations
- **Deployment and Operations**: Use containerization (Docker), implement CI/CD pipelines, have a rollback strategy

## Scalability

The RFQ Sender system is designed to handle a moderate volume of RFQs, vendors, and attachments. For larger scale operations, consider the following:

- **Database**: SQLite is suitable for development and small deployments. For production with high concurrency, consider migrating to PostgreSQL or MySQL.
- **Email Processing**: For large batches of emails, implement batch processing and rate limiting to avoid overwhelming SMTP servers.
- **File Handling**: Large attachments should be handled with care, potentially implementing streaming or compression.
- **Asynchronous Processing**: Consider refactoring to use async/await for improved performance with I/O-bound operations.

For detailed recommendations on scaling the RFQ Sender system, see [Scaling Guide](.junie/mds/SCALING.md).

## Testing

Run the full test suite:

```
pytest -q
```

Recommended quality checks (optional but helpful):

```
flake8
black --check .
isort --check-only .
```

## Release Checklist

See the curated checklist for preparing a release:

- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
