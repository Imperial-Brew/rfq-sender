# RFQ Sender System - Documentation Index

## Overview
This document serves as an index to the documentation available for the RFQ Sender System. It provides links to all relevant documentation and a brief description of each document's purpose.

## Core Documentation

### [README.md](../README.md)
The main project documentation that provides an overview of the system, its purpose, setup instructions, and basic usage examples.

### [CHANGELOG.md](../CHANGELOG.md)
A chronological record of all notable changes made to the project, including new features, changes, and fixes.

### [CONTRIBUTING.md](../CONTRIBUTING.md)
Guidelines for contributing to the project, including coding standards, pull request process, and development workflow.

### [LICENSE](../LICENSE)
The license under which the project is distributed.

## Project Status and Planning

### [Project Status Report](PROJECT_STATUS.md)
A comprehensive report on the current state of the project, including functionality, development status, test status, and outstanding issues.

### [Test Fix Plan](TEST_FIX_PLAN.md)
A detailed plan for addressing the failing tests in the system, including analysis of the issues and implementation strategies.

### [Development Roadmap](DEVELOPMENT_ROADMAP.md)
A structured plan for future development of the RFQ Sender System, outlining phases, goals, tasks, and success metrics.

### [Session Summary](SESSION_SUMMARY.md)
A summary of work completed during development sessions, including project status assessment, documentation creation, and next steps.

## User Guides

### [Email From List](email_from_list.md)
Documentation for the `email_from_list.py` script that processes RFQs from CSV files and creates draft emails in Outlook.

### [Email From List Changes](email_from_list_changes.md)
Detailed changelog of modifications made to the `email_from_list.py` script.

### [Find Vendors By Process](find_vendors_by_process.md)
Documentation for the script that finds vendors based on their process capabilities.

### [Find Vendors By Spec](find_vendors_by_spec.md)
Documentation for the script that finds vendors based on their specification capabilities.

### [RFQ Sender Guide](rfq_sender_guide.md) (To Be Created)
A guide for using the core `rfq_sender.py` script to send RFQ emails to vendors.

### [Response Handling Guide](response_handling.md)
A guide for parsing, storing, and analyzing vendor responses to RFQs using the response handling functionality.

## Technical Documentation

### [API Documentation](api_documentation.md) (To Be Created)
Technical documentation of the system's API, including function signatures, parameters, and return values.

### [Box Integration](BOX_INTEGRATION.md)
Documentation of the Box integration for file sharing, including implementation details, credentials management, and workflow.

### [Box Hybrid Structure](box_hybrid_structure.md)
Detailed documentation on the hybrid folder structure used in Box for organizing RFQ documentation.

### [Database Schema](database_schema.md) (To Be Created)
Documentation of the database schema used for tracking RFQs.

### [Configuration Guide](configuration_guide.md) (To Be Created)
A guide for configuring the RFQ Sender System, including environment variables, YAML configuration files, and templates.

### [Scaling Guide](SCALING.md)
Recommendations for scaling the RFQ Sender system to handle larger volumes of RFQs, vendors, and attachments.

### [Code Style Verification](code_style_verification.md)
Documentation of code style and formatting configurations, including black, isort, mypy, pytest, and flake8 settings and recommendations for maintaining code style consistency.

## Implementation and Bug Fixes

### [Bug Tracker Implementation](bug_tracker_implementation.md)
Implementation details for the bug tracking system.

### [Comprehensive Queue Fix](comprehensive_queue_fix.md)
Documentation for fixes related to queue handling and processing.

### [Comprehensive Type Fix](comprehensive_type_fix.md)
Documentation for fixes related to type handling and validation.

### [Documentation Consistency Fix](documentation_consistency_fix.md)
Documentation of changes made to resolve documentation inconsistencies and recommendations for maintaining consistency.

### [Date Comparison Fix](date_comparison_fix.md)
Documentation for fixes related to date comparison functionality.

### [Type Comparison Fix](type_comparison_fix.md)
Documentation for fixes related to type comparison functionality.

### [Fix View Queue Type Error](fix_view_queue_type_error.md)
Documentation for fixes related to type errors in the view queue functionality.

## Specialized Documentation

### [HDWE](HDWE/)
Documentation related to hardware specifications and processes.

### [Material](Material/)
Documentation related to material specifications and processes.

### [OS](OS/)
Documentation related to operating system requirements and configurations.

### [Vendor Approvals](Vendor%20approvals/)
Documentation related to vendor approval processes and requirements.

## Next Steps for Documentation

Based on the current state of the project and the development roadmap, the following documentation should be created next:

1. **Email From List Guide**: A comprehensive guide for using the new `email_from_list.py` script.
2. **RFQ Sender Guide**: A detailed guide for using the core `rfq_sender.py` script.
3. **Configuration Guide**: Documentation on how to configure the system for different environments.
4. **Database Schema**: Documentation of the database schema for developers and administrators.
5. **Response Parser Guide**: A detailed guide for using the advanced features of the response parsing functionality.

## Maintenance

This index should be updated whenever new documentation is added or existing documentation is significantly modified. The goal is to maintain a comprehensive and up-to-date reference for all aspects of the RFQ Sender System.

Last Updated: August 10, 2025
