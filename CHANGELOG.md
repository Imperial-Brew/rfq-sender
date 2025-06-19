# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Core functionality for sending RFQ emails to vendors
- Command-line interface for managing RFQs
- SQLite database for RFQ tracking
- Email template rendering with Jinja2
- File attachment handling
- Vendor configuration in YAML format
- Email settings configuration with environment variable support
- Basic error handling and logging
- Unit tests for key functions
- CUI/ITAR compliance features for secure handling of controlled information
- Environment variable loading with python-dotenv
- Comprehensive .env.example template
- GitHub Actions workflow for continuous integration
- GitHub issue and pull request templates
- Test email script for creating draft emails in Outlook
- Detailed scaling guide with recommendations for production use
- Scalability and performance guidelines
- Deployment and operations guidelines
- Comprehensive project review summary
- Email from list script for processing RFQs from CSV files
- Comprehensive project status report
- Test fix plan for addressing failing tests
- Development roadmap for future enhancements
- Documentation index for easier navigation
- Session summary documenting completed work
- Vendor capability matching in email_from_list.py script
- Integration with vendor_options.yaml for process capabilities
- Support for contacts.csv for vendor contact information
- Support for creating separate emails for each process in email_from_list.py
- Integration with cover_letter.j2 template for email body
- Support for including Sample_Table(Empty)-OS.csv in email body
- Mechanism to handle processes not listed in vendor_options.yaml
- Support for including user's signature in emails
- Comprehensive documentation for email_from_list.py script
- Script for finding vendors by process capability (find_vendors_by_process.py)
- Script for finding vendors by specification (find_vendors_by_spec.py)
- Support for addressing emails to the first name from contacts.csv
- HTML table formatting for better display in emails
- Integration with Outlook's general signature

### Changed
- Enhanced security measures for handling sensitive data
- Improved environment variable handling with dotenv
- Updated documentation with security best practices
- Improved logging configuration with absolute paths
- Replaced hardcoded company name with configurable setting
- Enhanced style guidelines with scalability and performance recommendations
- Updated README.md with scalability considerations
- Expanded testing guidelines to include performance and load testing
- Corrected project structure in README.md to show templates directory in correct location
- Removed CSV/Excel to YAML conversion scripts that are no longer needed
- Updated email_from_list.py to use contacts.csv and vendor_options.yaml instead of Vendor_Quotes.csv
- Improved vendor selection in email_from_list.py to match processes with vendor capabilities
- Enhanced email body creation with proper formatting for callout information
- Improved file path validation and attachment handling in email_from_list.py
- Modified email_from_list.py to create separate emails for each process
- Updated email_from_list.py to use Jinja2 templates for email body
- Enhanced email_from_list.py to include sample table in email body
- Updated email_from_list.py to add processes to vendor capabilities when not found
- Modified email_from_list.py to prioritize matching vendors by spec over process
- Removed hardcoded default vendor from email_from_list.py to allow more vendor diversity
- Updated email_from_list.py to skip items with no suitable vendors instead of using fallback vendors
- Modified email_from_list.py to use first name from contacts.csv for personalized greetings
- Updated email_from_list.py to use HTML formatting for better email presentation
- Enhanced email_from_list.py to use formatted HTML tables instead of plain text
- Updated email_from_list.py to integrate with Outlook's general signature
- Enhanced email_from_list.py to create emails for all suitable vendors, not just the first one
- Removed additional information displayed below the table in email_from_list.py

### Fixed
- Added missing environment variables in configuration
- Fixed logging directory creation to ensure logs are stored in the correct location
- Fixed issue with backslashes in f-strings in email_from_list.py for Python 3.10 compatibility
- Fixed template rendering issue in cover_letter.j2 with missing if statement for sample_table
- Fixed table field mapping in email_from_list.py to use 'callout' field for 'Print Callout'
- Enhanced file attachment logic to search folders and sub-folders for files containing the part number
- Added proper line breaks in email template for better readability
- Enhanced file attachment logic to ignore Excel and Word documents
- Improved table population to include Process, Spec, and QTYs fields from the queue
- Fixed table styling to ensure proper grid outlines for all cells

## [0.1.0] - 2023-10-01

### Added
- Initial release
