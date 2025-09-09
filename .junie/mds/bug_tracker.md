# docs/bug_tracker.md - Bug Tracker Documentation

## Overview
The Bug Tracker is a feature of the RFQ Sender application that allows users to submit and track bug reports and feature requests. This document explains how to access and use the Bug Tracker.

## Accessing the Bug Tracker

### Important Note
The Bug Tracker is only available when running the application from the `streamlit_app` directory, not from the root `app.py`.

To access the Bug Tracker:

1. Use the provided `Start_streamlit_app.bat` script in the project root directory
2. Or run the following command from the project root:
   ```
   streamlit run streamlit_app/app.py
   ```

The Bug Tracker will appear as a page in the sidebar navigation.

## Using the Bug Tracker

The Bug Tracker has two main tabs:

1. **Submit New Issue**: Use this tab to submit new bug reports or feature requests
   - Select the issue type (Bug or Feature Request)
   - Enter a title and description
   - Set the priority level
   - Provide additional details if needed

2. **View Issues**: Use this tab to view and filter existing issues
   - Filter by type, priority, and status
   - Select an issue to view its details
   - Administrators can update the status of issues

## Issue Priorities

- **1 - App Breaking**: Critical issues preventing core functionality
- **2 - Urgent**: Serious issues requiring immediate attention
- **3 - Regular**: Standard priority issues
- **4 - Low/Long Term**: Minor issues or future enhancements

## Issue Statuses

- **Open**: New issues that have not been addressed
- **In Progress**: Issues currently being worked on
- **Resolved**: Issues that have been fixed or implemented
- **Closed**: Issues that have been completed and verified