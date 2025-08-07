"""
Populate the bug tracker with initial data from tasks.md and TODO.md.

This script extracts items from the existing task tracking files and adds them
to the bug tracker database.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import database utilities
from streamlit_app.utils.db import get_db_connection, add_issue
from utils.logging import get_logger

# Get module-specific logger
logger = get_logger(__name__, "populate_bug_tracker.log")

def extract_from_tasks_md():
    """
    Extract future enhancements from tasks.md and return them as a list of dictionaries.
    
    Returns:
        list: List of dictionaries with issue data
    """
    tasks_file = parent_dir / ".junie" / "tasks.md"
    issues = []
    
    try:
        with open(tasks_file, 'r') as f:
            lines = f.readlines()
        
        in_future_section = False
        for line in lines:
            line = line.strip()
            
            # Check if we're in the Future Enhancements section
            if line == "## Future Enhancements":
                in_future_section = True
                continue
            
            # Skip if not in Future Enhancements section or line is empty
            if not in_future_section or not line:
                continue
            
            # Check if line is a task
            if line.startswith("- [ ]"):
                # Extract task description
                description = line[5:].strip()
                
                # Add to issues list
                issues.append({
                    "issue_type": "Feature Request",
                    "priority": 3,  # Regular priority
                    "title": description,
                    "description": f"Future enhancement from tasks.md: {description}",
                    "details": "Migrated from tasks.md Future Enhancements section",
                    "created_by": "System"
                })
        
        logger.info(f"Extracted {len(issues)} issues from tasks.md")
        return issues
    
    except Exception as e:
        logger.error(f"Error extracting from tasks.md: {e}")
        return []

def extract_from_todo_md():
    """
    Extract tasks from TODO.md and return them as a list of dictionaries.
    
    Returns:
        list: List of dictionaries with issue data
    """
    todo_file = parent_dir / ".junie" / "TODO.md"
    issues = []
    
    try:
        with open(todo_file, 'r') as f:
            lines = f.readlines()
        
        current_priority = None
        current_title = None
        current_description = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                # If we have a title and we're moving to a new item, add the current one
                if current_title:
                    priority_value = 1 if current_priority == "high" else (3 if current_priority == "medium" else 4)
                    
                    issues.append({
                        "issue_type": "Feature Request",
                        "priority": priority_value,
                        "title": current_title,
                        "description": "\n".join(current_description) if current_description else current_title,
                        "details": f"Migrated from TODO.md {current_priority.capitalize()} Priority section",
                        "created_by": "System"
                    })
                    
                    # Reset for next item
                    current_title = None
                    current_description = []
                
                continue
            
            # Check for priority headers (text-based identifiers)
            if "High Priority" in line:
                current_priority = "high"
                continue
            elif "Medium Priority" in line:
                current_priority = "medium"
                continue
            elif "Low Priority" in line or "Low Priority / Future" in line:
                current_priority = "low"
                continue
            
            # Skip if we haven't found a priority section yet
            if not current_priority:
                continue
            
            # Check if this is a numbered item (potential title)
            if line[0].isdigit() and "." in line:
                # If we already have a title, save the current item before starting a new one
                if current_title:
                    priority_value = 1 if current_priority == "high" else (3 if current_priority == "medium" else 4)
                    
                    issues.append({
                        "issue_type": "Feature Request",
                        "priority": priority_value,
                        "title": current_title,
                        "description": "\n".join(current_description) if current_description else current_title,
                        "details": f"Migrated from TODO.md {current_priority.capitalize()} Priority section",
                        "created_by": "System"
                    })
                    
                    # Reset description for new item
                    current_description = []
                
                # Extract the title (remove the number and period)
                current_title = line.split(".", 1)[1].strip()
            elif current_title:
                # This is part of the description for the current item
                current_description.append(line)
        
        # Don't forget to add the last item if there is one
        if current_title:
            priority_value = 1 if current_priority == "high" else (3 if current_priority == "medium" else 4)
            
            issues.append({
                "issue_type": "Feature Request",
                "priority": priority_value,
                "title": current_title,
                "description": "\n".join(current_description) if current_description else current_title,
                "details": f"Migrated from TODO.md {current_priority.capitalize()} Priority section",
                "created_by": "System"
            })
        
        logger.info(f"Extracted {len(issues)} issues from TODO.md")
        return issues
    
    except Exception as e:
        logger.error(f"Error extracting from TODO.md: {e}")
        return []

def populate_bug_tracker():
    """
    Populate the bug tracker with initial data from tasks.md and TODO.md.
    """
    try:
        # Get database connection
        conn = get_db_connection()
        
        # Check if there are already issues in the database
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bug_tracker")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info(f"Database already contains {count} issues. Skipping population.")
            conn.close()
            return 0
        
        # Extract issues from tasks.md
        tasks_issues = extract_from_tasks_md()
        
        # Extract issues from TODO.md
        todo_issues = extract_from_todo_md()
        
        # Combine all issues
        all_issues = tasks_issues + todo_issues
        
        # Add issues to database
        for issue in all_issues:
            add_issue(
                conn=conn,
                issue_type=issue["issue_type"],
                priority=issue["priority"],
                title=issue["title"],
                description=issue["description"],
                created_by=issue["created_by"],
                details=issue["details"]
            )
        
        logger.info(f"Added {len(all_issues)} issues to the bug tracker")
        
        # Close database connection
        conn.close()
        
        return len(all_issues)
    
    except Exception as e:
        logger.error(f"Error populating bug tracker: {e}")
        return 0

if __name__ == "__main__":
    try:
        num_issues = populate_bug_tracker()
        print(f"Successfully added {num_issues} issues to the bug tracker")
    except Exception as e:
        logger.exception("Error running populate_bug_tracker.py")
        print(f"Error: {e}")