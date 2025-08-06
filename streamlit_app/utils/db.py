"""
Database utilities for the Streamlit app.

This module provides functions for connecting to and initializing the SQLite database
used by the Streamlit app.
"""
import sqlite3
from pathlib import Path
import logging
from typing import Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def get_db_connection() -> sqlite3.Connection:
    """
    Get a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    # Get the project root directory
    root_dir = Path(__file__).parent.parent.parent
    
    # Create data directory if it doesn't exist
    data_dir = root_dir / "data_cleaned"
    data_dir.mkdir(exist_ok=True)
    
    # Connect to database
    db_path = data_dir / "streamlit_app.db"
    conn = sqlite3.connect(str(db_path))
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Initialize database tables
    init_database(conn)
    
    return conn

def init_database(conn: sqlite3.Connection) -> None:
    """
    Initialize the database tables if they don't exist.
    
    Args:
        conn (sqlite3.Connection): Database connection
    """
    cursor = conn.cursor()
    
    # Create bug_tracker table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bug_tracker (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_type TEXT NOT NULL,  -- 'Bug' or 'Feature Request'
        priority INTEGER NOT NULL, -- 1-4 (1: app breaking, 2: urgent, 3: regular, 4: long term/low)
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        details TEXT,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        last_updated_at TIMESTAMP NOT NULL,
        status TEXT NOT NULL DEFAULT 'Open' -- Open, In Progress, Resolved, Closed
    )
    ''')
    
    conn.commit()

def add_issue(
    conn: sqlite3.Connection,
    issue_type: str,
    priority: int,
    title: str,
    description: str,
    created_by: str,
    details: Optional[str] = None
) -> int:
    """
    Add a new issue to the bug tracker.
    
    Args:
        conn (sqlite3.Connection): Database connection
        issue_type (str): Type of issue ('Bug' or 'Feature Request')
        priority (int): Priority level (1-4)
        title (str): Issue title
        description (str): Issue description
        created_by (str): Name of the user who created the issue
        details (Optional[str], optional): Additional details. Defaults to None.
    
    Returns:
        int: ID of the inserted issue
    """
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute(
        '''
        INSERT INTO bug_tracker (
            issue_type, priority, title, description, details, 
            created_by, created_at, last_updated_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            issue_type,
            priority,
            title,
            description,
            details,
            created_by,
            now,
            now,
            'Open'
        )
    )
    
    conn.commit()
    return cursor.lastrowid

def get_issues(
    conn: sqlite3.Connection,
    issue_type: Optional[str] = None,
    priority: Optional[int] = None,
    status: Optional[str] = None
) -> list:
    """
    Get issues from the bug tracker with optional filtering.
    
    Args:
        conn (sqlite3.Connection): Database connection
        issue_type (Optional[str], optional): Filter by issue type. Defaults to None.
        priority (Optional[int], optional): Filter by priority. Defaults to None.
        status (Optional[str], optional): Filter by status. Defaults to None.
    
    Returns:
        list: List of issues as dictionaries
    """
    cursor = conn.cursor()
    
    query = "SELECT * FROM bug_tracker"
    params = []
    
    # Add filters if provided
    filters = []
    if issue_type:
        filters.append("issue_type = ?")
        params.append(issue_type)
    
    if priority:
        filters.append("priority = ?")
        params.append(priority)
    
    if status:
        filters.append("status = ?")
        params.append(status)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += " ORDER BY priority ASC, created_at DESC"
    
    cursor.execute(query, params)
    
    # Convert to list of dictionaries
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def update_issue_status(
    conn: sqlite3.Connection,
    issue_id: int,
    status: str,
    updated_by: str
) -> bool:
    """
    Update the status of an issue.
    
    Args:
        conn (sqlite3.Connection): Database connection
        issue_id (int): ID of the issue to update
        status (str): New status
        updated_by (str): Name of the user who updated the issue
    
    Returns:
        bool: True if successful, False otherwise
    """
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        cursor.execute(
            '''
            UPDATE bug_tracker
            SET status = ?, last_updated_at = ?
            WHERE id = ?
            ''',
            (status, now, issue_id)
        )
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating issue status: {e}")
        return False