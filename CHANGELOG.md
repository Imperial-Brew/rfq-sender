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

### Changed
- Enhanced security measures for handling sensitive data
- Improved environment variable handling with dotenv
- Updated documentation with security best practices
- Improved logging configuration with absolute paths
- Replaced hardcoded company name with configurable setting
- Enhanced style guidelines with scalability and performance recommendations
- Updated README.md with scalability considerations
- Expanded testing guidelines to include performance and load testing

### Fixed
- Added missing environment variables in configuration
- Fixed logging directory creation to ensure logs are stored in the correct location

## [0.1.0] - 2023-10-01

### Added
- Initial release
