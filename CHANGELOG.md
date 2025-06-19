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

### Changed
- Enhanced security measures for handling sensitive data
- Improved environment variable handling with dotenv
- Updated documentation with security best practices
- Improved logging configuration with absolute paths
- Replaced hardcoded company name with configurable setting
- Enhanced style guidelines with scalability and performance recommendations
- Updated README.md with scalability considerations
- Expanded testing guidelines to include performance and load testing
- Removed CSV/Excel to YAML conversion scripts that are no longer needed
- Updated email_from_list.py to use contacts.csv and vendor_options.yaml instead of Vendor_Quotes.csv
- Improved vendor selection in email_from_list.py to match processes with vendor capabilities
- Enhanced email body creation with proper formatting for callout information
- Improved file path validation and attachment handling in email_from_list.py
- Modified email_from_list.py to create separate emails for each process
- Updated email_from_list.py to use Jinja2 templates for email body
- Enhanced email_from_list.py to include sample table in email body
- Updated email_from_list.py to add processes to vendor capabilities when not found

### Fixed
- Added missing environment variables in configuration
- Fixed logging directory creation to ensure logs are stored in the correct location

## [0.1.0] - 2023-10-01

### Added
- Initial release
