# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Duplicate Part Numbers with Different Processes: Fixed an issue where drafting emails or creating Box folders for a part with multiple required finishes (e.g., Chromate and Anodize) would always select the first entry in the queue. The system now uniquely identifies queue items using both part number and process name. Added robust whitespace handling and enhanced logging for row identification.
- ITAR/CUI RFQ password drafts: Improved reliability of password retrieval when drafting emails. Now explicitly checks and recovers passwords from the queue data if they are missing or "nan" in the request body, ensuring the second email is always drafted for ITAR/CUI requests with a password.
- ITAR/CUI Password Auto-fix: Added logic to automatically generate a password and update the Box folder share link if a password is missing for ITAR/CUI parts when drafting emails. This ensures compliance even if the folder was initially shared without protection.
- Personalized salutations: Updated email drafting to use the contact's first name only instead of their full name. Added fallbacks to the vendor name or a generic "Team" if no contact name is available.

### Changed
- Familiar Specs now load from Box when `[box].BOX_FAMILIAR_SPECS_FILE_ID` is
  configured; falls back to local CSV if Box is unavailable. Updated
  SpecManager and Streamlit Specifications page to be Box-aware.
- Migrated Streamlit deprecations: replaced `use_container_width` with
  `width` API (using `width='stretch'` where applicable) across Queue and
  Specifications pages to silence warnings before 2025-12-31 removal.
- Added UI guard in Queue Management to avoid loading specs when no process
  is selected.
- Specifications Management: selection widgets (Process/Issuer) moved outside
  the form for live reload on interaction (Option 2). The form contains only
  free-text inputs and submit, providing immediate feedback while typing.
- utils.specs now rebuilds SpecManager on each call (no module-level singleton)
  so the current Box file ID and credentials are always respected across reruns.

### Fixed
- Suppress config warning for missing local FamiliarSpecs.csv when
  `BOX_FAMILIAR_SPECS_FILE_ID` is set.
- Prevented AttributeError when no process is selected in Streamlit Queue
  Management by making load_specs_for_process handle None/empty safely in
  core/specs/spec_manager.py. Added Optional[str] typing and docstrings in
  utils/specs.py. Introduced regression tests in tests/specs/ to guard this
  behavior.
- Streamlit Vendors page: avoid calling load_specs_for_process with a None/empty
  process selection; added UI guard and improved empty-state messaging in
  06_vendors.py to prevent AttributeError and guide the user.
- Box Familiar Specs save now uses a BytesIO stream when calling
  `update_contents_with_stream` (removed unsupported `file_size` kwarg for
  boxsdk==3.14.0), preventing silent fallback to local path. Added exception
  logging in Box load/save paths to surface underlying issues.
- BoxIntegration authentication now falls back to reading `.streamlit/secrets.toml`
  when running outside Streamlit (e.g., local scripts/tests). This resolves
  `AttributeError: 'NoneType' object has no attribute 'file'` in test.py by
  sourcing `[box].BOX_JWT_JSON` without requiring Streamlit or pre-set env.
- Add Specification writes are verified by an immediate readback; the UI only
  shows success when the new row is observed in FamiliarSpecs. Otherwise, a
  clear error is shown and logs contain the underlying cause.

## [0.2.1] - 2025-08-25

### Added
- Implemented Box hybrid folder structure for RFQ documentation organization
  - Added create_rfq_structure method to create master/part/vendor folders
  - Added upload_part_files method to organize files by part number
  - Added link_files_to_vendor method to create links in vendor folders
  - Added test scripts for hybrid folder structure verification
  - Added comprehensive documentation in docs/box_hybrid_structure.md
- Mail backend switched to Microsoft Graph for Draft creation
  - Config via .streamlit/secrets.toml ([exchange], [azure], [company], [app])
  - Smoke script (scripts/smoke_graph.py) to verify Graph connectivity
- Reorganized project structure and documentation
  - data_raw/ and data_cleaned/ directories
  - scripts/ organized into email/, box/, utils/, vendor/
  - README updates, Release Checklist, CONTRIBUTING and testing guidance

### Changed
- Email flow to use Graph + updated templates and company metadata
- Improved Box vendor-specific sharing and folder organization by part number
- Enhanced logging, environment handling, and documentation clarity

### Fixed
- Packaging coverage via MANIFEST.in so templates/config/docs ship in sdist/wheel
- Template rendering and minor path/cross-platform issues

## [0.1.0] - 2023-10-01

- Initial release

### Added
- Implemented Box hybrid folder structure for RFQ documentation organization
  - Added create_rfq_structure method to create master/part/vendor folders
  - Added upload_part_files method to organize files by part number
  - Added link_files_to_vendor method to create links in vendor folders
  - Added test scripts for hybrid folder structure verification
  - Added comprehensive documentation in docs/box_hybrid_structure.md
- Mail backend switched to Microsoft Graph for Draft creation
  - Config via .streamlit/secrets.toml ([exchange], [azure], [company], [app])
  - Smoke script (scripts/smoke_graph.py) to verify Graph connectivity
- Reorganized project structure and documentation
  - data_raw/ and data_cleaned/ directories
  - scripts/ organized into email/, box/, utils/, vendor/
  - README updates, Release Checklist, CONTRIBUTING and testing guidance
- Created tasks.md in .junie directory for tracking project tasks
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
- Test fix plan for addressing failing tests
- Development roadmap for future enhancements
- Documentation index for easier navigation
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
- HTML table formatting for better display in emails
- Integration with Outlook's general signature
- Box integration for secure file sharing (box_integration.py)
- JWT authentication for Box integration
- Retry logic with exponential backoff for failed Box operations
- Comprehensive Box integration documentation (BOX_INTEGRATION.md)
- Test scripts for Box integration (test_box_integration.py, test_email_with_box.py)

### Changed
- Updated Box integration to use hybrid folder structure for better organization
  - Modified create_draft_email function to use the new folder structure
  - Enhanced file organization by part number in Box folders
  - Improved vendor-specific sharing with dedicated folders
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
- Fixed Box authentication issue by switching from OAuth2 to JWT authentication
- Updated Box integration documentation with troubleshooting information for authentication errors

## [0.1.0] - 2023-10-01

### Added
- Initial release
