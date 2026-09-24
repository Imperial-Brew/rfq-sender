Recommended Refactoring and Consolidation for RFQ Sender
After reviewing the codebase, I've identified several opportunities for refactoring and consolidation that would improve maintainability, reduce duplication, and streamline the application architecture.

Email Handling Consolidation
Complete the Exchange Migration

Remove all remaining SMTP code from streamlit_app/pages/05_send_rfq_emails.py as outlined in the streamlit_app_changes.md file
Create a unified email module that abstracts the email backend (Exchange) from the business logic
Consolidate email template rendering into a single function used by all email-sending components
Standardize Email Settings

Create a consistent approach to email settings across all files
Use environment variables exclusively for sensitive information
Add a configuration file for non-sensitive email settings (signature, company info)
Vendor Data Management
Create a Unified Vendor Data Access Layer

Develop a VendorRepository class that handles loading and merging data from all three sources:
class VendorRepository:
    def __init__(self, vendors_json_path, vendor_options_yaml_path, contacts_csv_path):
        # Load and merge data from all sources
        
    def get_vendors_for_process(self, process):
        # Return vendors supporting a process
        
    def get_vendors_for_process_and_spec(self, process, spec):
        # Return vendors supporting a process and spec
This would replace the current approach of loading and processing vendor data in multiple places
Normalize Process and Spec Handling

Move the SpecProcessValidator and normalization functions to a dedicated module
Create a unified API for process/spec validation and normalization
Ensure consistent normalization across all components
Code Structure Improvements
Consolidate Duplicate Code

Extract common functionality from app.py, streamlit_app/pages/05_send_rfq_emails.py, and scripts/email/email_from_list.py into shared utility modules
Create a shared module for file attachment handling
Standardize error handling and logging across all components
Implement a Service Layer

Create service classes that encapsulate business logic:
class RfqEmailService:
    def __init__(self, vendor_repository, email_client, template_renderer):
        self.vendor_repository = vendor_repository
        self.email_client = email_client
        self.template_renderer = template_renderer
        
    def create_draft_emails_for_queue_item(self, queue_item):
        # Business logic for creating draft emails
This would separate business logic from UI and data access concerns
UI Improvements
Streamline the Streamlit Interface
Consolidate the main app.py and streamlit_app/pages/* into a more cohesive structure
Create reusable Streamlit components for common UI elements
Implement a more consistent state management approach using Streamlit's session state
Testing and Documentation
Improve Testability

Add dependency injection to make components more testable
Create mock implementations of external dependencies (Exchange, file system)
Add unit tests for core business logic
Enhance Documentation

Add comprehensive docstrings to all modules, classes, and functions
Create a project architecture document explaining the relationships between components
Document the data flow from queue to email creation
Specific Implementation Recommendations
Create a Unified Configuration System

Implement a centralized configuration system that loads settings from:
Environment variables (.env file)
Configuration files (YAML/JSON)
Command-line arguments
Use this system consistently across all components
Standardize Logging

Implement a consistent logging approach across all components
Use structured logging for better searchability
Add context information to all log messages
Refactor File Handling

Create a dedicated file access layer for handling attachments and other files
Implement proper error handling for file operations
Use pathlib consistently instead of mixing os.path and string manipulation
Implementation Plan
To implement these changes effectively, I recommend the following phased approach:

Phase 1: Complete Exchange Migration

Remove all SMTP code
Update streamlit_app/pages/05_send_rfq_emails.py
Create a unified email client class
Phase 2: Vendor Data Consolidation

Implement the VendorRepository class
Update all components to use this class
Add tests for vendor data access
Phase 3: Service Layer Implementation

Create service classes for core business logic
Refactor UI components to use these services
Add tests for service classes
Phase 4: UI Improvements

Consolidate Streamlit components
Improve state management
Enhance user experience
This approach allows for incremental improvements while maintaining a working application throughout the refactoring process.