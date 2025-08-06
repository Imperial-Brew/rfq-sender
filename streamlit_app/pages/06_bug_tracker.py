"""
Bug Tracker page for the Streamlit app.

This page allows users to submit and view bug reports and feature requests.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import logging
from datetime import datetime

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import utility functions
from streamlit_app.utils.db import get_db_connection, add_issue, get_issues, update_issue_status
from utils.auth import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication

if not require_authentication():
    st.stop()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(parent_dir / "logs" / "bug_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_page():
    """Configure the page settings."""
    st.set_page_config(page_title="Bug Tracker", page_icon="🐛")
    st.title("🐛 Bug & Feature Request Tracker")
    st.markdown("""
    Use this page to submit bug reports or feature requests, and to view existing issues.
    """)

def display_submission_form(user):
    """Display the form for submitting a new bug or feature request."""
    st.subheader("Submit New Issue")
    
    with st.form("issue_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            issue_type = st.radio(
                "Issue Type",
                options=["Bug", "Feature Request"],
                horizontal=True,
                help="Select whether this is a bug report or a feature request"
            )
            
            title = st.text_input(
                "Title",
                help="Enter a brief, descriptive title for the issue"
            )
        
        with col2:
            priority_options = {
                1: "1 - App Breaking (Critical issue preventing core functionality)",
                2: "2 - Urgent (Serious issue requiring immediate attention)",
                3: "3 - Regular (Standard priority issue)",
                4: "4 - Low/Long Term (Minor issue or future enhancement)"
            }
            
            priority = st.selectbox(
                "Priority",
                options=list(priority_options.keys()),
                format_func=lambda x: priority_options[x],
                help="Select the priority level of the issue"
            )
        
        description = st.text_area(
            "Description",
            height=100,
            help="Provide a clear description of the bug or feature request"
        )
        
        details = st.text_area(
            "Details",
            height=150,
            help="Provide any additional details, steps to reproduce, expected behavior, etc."
        )
        
        submitted = st.form_submit_button("Submit Issue", use_container_width=True)
        
        if submitted:
            if not title or not description:
                st.warning("Title and description are required.")
                logger.warning(f"Submission failed: missing required fields")
            else:
                try:
                    # Get database connection
                    conn = get_db_connection()
                    
                    # Add issue to database
                    issue_id = add_issue(
                        conn=conn,
                        issue_type=issue_type,
                        priority=priority,
                        title=title.strip(),
                        description=description.strip(),
                        created_by=user["name"],
                        details=details.strip() if details else None
                    )
                    
                    # Close connection
                    conn.close()
                    
                    st.success(f"✅ Issue #{issue_id} submitted successfully!")
                    logger.info(f"Issue '{title}' submitted by {user['name']}")
                    
                    # Clear form (requires rerun)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error submitting issue: {str(e)}")
                    logger.error(f"Error submitting issue: {str(e)}")

def display_issues_table(user, role):
    """Display a table of existing issues with filtering options."""
    st.subheader("View Issues")
    
    # Filtering options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_type = st.selectbox(
            "Filter by Type",
            options=["All", "Bug", "Feature Request"],
            index=0
        )
    
    with col2:
        filter_priority = st.selectbox(
            "Filter by Priority",
            options=["All", "1 - App Breaking", "2 - Urgent", "3 - Regular", "4 - Low/Long Term"],
            index=0
        )
    
    with col3:
        filter_status = st.selectbox(
            "Filter by Status",
            options=["All", "Open", "In Progress", "Resolved", "Closed"],
            index=0
        )
    
    try:
        # Get database connection
        conn = get_db_connection()
        
        # Apply filters
        issue_type = None if filter_type == "All" else filter_type
        priority = None
        if filter_priority != "All":
            priority = int(filter_priority[0])
        status = None if filter_status == "All" else filter_status
        
        # Get issues from database
        issues = get_issues(conn, issue_type, priority, status)
        
        # Close connection
        conn.close()
        
        if not issues:
            st.info("No issues found matching the selected filters.")
            return
        
        # Convert to DataFrame for display
        df = pd.DataFrame(issues)
        
        # Format DataFrame for display
        if not df.empty:
            # Rename columns for display
            df = df.rename(columns={
                "id": "ID",
                "issue_type": "Type",
                "priority": "Priority",
                "title": "Title",
                "description": "Description",
                "created_by": "Created By",
                "created_at": "Created At",
                "last_updated_at": "Last Updated",
                "status": "Status"
            })
            
            # Format dates
            df["Created At"] = pd.to_datetime(df["Created At"]).dt.strftime("%Y-%m-%d %H:%M")
            df["Last Updated"] = pd.to_datetime(df["Last Updated"]).dt.strftime("%Y-%m-%d %H:%M")
            
            # Format priority
            priority_map = {
                1: "1 - App Breaking",
                2: "2 - Urgent",
                3: "3 - Regular",
                4: "4 - Low/Long Term"
            }
            df["Priority"] = df["Priority"].map(priority_map)
            
            # Select columns to display in the table
            display_cols = ["ID", "Type", "Priority", "Title", "Status", "Created By", "Created At"]
            
            # Display the table
            st.dataframe(df[display_cols], use_container_width=True)
            
            # Issue details
            st.subheader("Issue Details")
            selected_issue_id = st.selectbox("Select an issue to view details", df["ID"].tolist())
            
            if selected_issue_id:
                selected_issue = df[df["ID"] == selected_issue_id].iloc[0]
                
                # Display issue details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**ID:** {selected_issue['ID']}")
                    st.markdown(f"**Type:** {selected_issue['Type']}")
                    st.markdown(f"**Priority:** {selected_issue['Priority']}")
                    st.markdown(f"**Status:** {selected_issue['Status']}")
                
                with col2:
                    st.markdown(f"**Created By:** {selected_issue['Created By']}")
                    st.markdown(f"**Created At:** {selected_issue['Created At']}")
                    st.markdown(f"**Last Updated:** {selected_issue['Last Updated']}")
                
                st.markdown("---")
                st.markdown("### Title")
                st.markdown(f"**{selected_issue['Title']}**")
                
                st.markdown("### Description")
                st.markdown(selected_issue["Description"])
                
                if "details" in df.columns and not pd.isna(selected_issue["details"]):
                    st.markdown("### Details")
                    st.markdown(selected_issue["details"])
                
                # Status update (for admin users only)
                if role in ["admin", "manager"]:
                    st.markdown("---")
                    st.subheader("Update Status")
                    
                    new_status = st.selectbox(
                        "New Status",
                        options=["Open", "In Progress", "Resolved", "Closed"],
                        index=["Open", "In Progress", "Resolved", "Closed"].index(selected_issue["Status"])
                    )
                    
                    if st.button("Update Status"):
                        try:
                            # Get database connection
                            conn = get_db_connection()
                            
                            # Update issue status
                            success = update_issue_status(
                                conn=conn,
                                issue_id=selected_issue_id,
                                status=new_status,
                                updated_by=user["name"]
                            )
                            
                            # Close connection
                            conn.close()
                            
                            if success:
                                st.success(f"Status updated to {new_status}")
                                logger.info(f"Issue #{selected_issue_id} status updated to {new_status} by {user['name']}")
                                st.rerun()
                            else:
                                st.error("Failed to update status")
                                logger.error(f"Failed to update status for issue #{selected_issue_id}")
                        except Exception as e:
                            st.error(f"Error updating status: {str(e)}")
                            logger.error(f"Error updating status: {str(e)}")
        
    except Exception as e:
        st.error(f"Error loading issues: {str(e)}")
        logger.error(f"Error loading issues: {str(e)}")

def main():
    """Main function to run the page."""
    setup_page()
    
    # Get user from session state (set in main app)
    if "user" not in st.session_state:
        st.warning("Please select a user in the sidebar of the main page.")
        return
    
    user = st.session_state.user
    role = get_user_role(user)
    
    # Display user info
    st.sidebar.markdown(f"**User:** {user['name']}")
    st.sidebar.markdown(f"**Role:** {role}")
    
    # Create tabs for submission and viewing
    tab1, tab2 = st.tabs(["Submit New Issue", "View Issues"])
    
    with tab1:
        display_submission_form(user)
    
    with tab2:
        display_issues_table(user, role)

if __name__ == "__main__":
    main()