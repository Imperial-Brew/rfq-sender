CSV Upload Implementation Plan
This document outlines the implementation plan for adding CSV upload functionality to the RFQ Sender application for both queue and familiar specs data.

Overview
Currently, the RFQ Sender application allows users to download CSV files for queue and familiar specs data, but lacks the ability to upload modified CSV files back into the system. This implementation will add upload functionality to complete the workflow.

File Locations
Queue data: docs/queue.csv
Familiar Specs data: docs/OS/spec_lists/FamiliarSpecs.csv
Implementation Tasks
1. Backend Utility Functions
Create validation functions for uploaded CSV files

Implement schema validation for queue CSV
Implement schema validation for familiar specs CSV
Add data type conversion and cleaning
Add CSV import functions to utility modules

Create import_queue_csv() function in utils/queue.py
Create import_specs_csv() function in utils/specs.py
Implement error handling for malformed CSV files
Add merge/replace options for data handling

Implement logic to either replace existing data or merge with it
Add duplicate detection and resolution strategies
2. Frontend Implementation
Update Queue page (streamlit_app/pages/02_view_queue.py)

Add file uploader component with appropriate help text
Add radio buttons for merge/replace options
Implement validation feedback and error messages
Add success confirmation after upload
Update Familiar Specs page (streamlit_app/pages/04_view_familiar_specs.py)

Add file uploader component with appropriate help text
Add radio buttons for merge/replace options
Implement validation feedback and error messages
Add success confirmation after upload
Add user role-based permissions

Restrict upload functionality to admin users
Show/hide upload controls based on user role
3. Git Integration (Optional Phase)
Create Git utility module (utils/git.py)

Implement function to commit changes after successful upload
Add configuration for Git credentials
Implement error handling for Git operations
Update frontend to include Git options

Add checkbox to enable/disable Git commit after upload
Add commit message input field
Display Git operation status and feedback
4. Testing
Create test CSV files with valid data
Create test CSV files with invalid data
Test upload functionality with various scenarios:
Valid CSV with new data (merge mode)
Valid CSV with new data (replace mode)
Valid CSV with duplicate data
Invalid CSV format
CSV with missing required columns
CSV with incorrect data types
5. Documentation
Update application documentation

Add instructions for CSV upload in README.md
Document CSV format requirements
Document merge/replace behavior
Update CHANGELOG.md

Add entry for CSV upload feature
Implementation Details
Queue CSV Upload
# Example implementation for queue.py
def import_queue_csv(file_path, merge=True):
    """
    Import queue data from CSV file.
    
    Args:
        file_path: Path to the CSV file
        merge: If True, merge with existing data; if False, replace existing data
        
    Returns:
        DataFrame with imported data
    """
    # Load the CSV file
    new_df = pd.read_csv(file_path)
    
    # Validate required columns
    required_columns = ["part_number", "process", "spec"]
    missing_columns = [col for col in required_columns if col not in new_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Clean and standardize data
    # [Implementation details...]
    
    if merge:
        # Merge with existing data
        existing_df = load_queue()
        # [Merge logic...]
        result_df = pd.concat([existing_df, new_df]).drop_duplicates()
    else:
        # Replace existing data
        result_df = new_df
    
    # Save the result
    result_df.to_csv(QUEUE_PATH, index=False)
    
    return result_df
Familiar Specs CSV Upload
# Example implementation for specs.py
def import_specs_csv(file_path, merge=True):
    """
    Import familiar specs data from CSV file.
    
    Args:
        file_path: Path to the CSV file
        merge: If True, merge with existing data; if False, replace existing data
        
    Returns:
        DataFrame with imported data
    """
    # Load the CSV file
    new_df = pd.read_csv(file_path)
    
    # Validate required columns
    required_columns = ["process", "spec"]
    missing_columns = [col for col in required_columns if col not in new_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Clean and standardize data
    # [Implementation details...]
    
    if merge:
        # Merge with existing data
        existing_df = load_familiar_specs()
        # [Merge logic...]
        result_df = pd.concat([existing_df, new_df]).drop_duplicates()
    else:
        # Replace existing data
        result_df = new_df
    
    # Save the result
    result_df.to_csv(SPECS_PATH, index=False)
    
    return result_df
Timeline
Backend utility functions: 2 days
Frontend implementation: 2 days
Testing: 1 day
Documentation: 1 day
Git integration (optional): 2 days
Total estimated time: 6-8 days

Security Considerations
Validate all uploaded CSV files thoroughly to prevent security issues
Implement role-based permissions for the upload functionality
Consider adding file size limits to prevent denial of service
If implementing Git integration, ensure secure handling of credentials