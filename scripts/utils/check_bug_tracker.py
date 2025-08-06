"""
Quick script to check the contents of the bug tracker database.
"""
import sys
import sqlite3
from pathlib import Path

# Add the parent directory to the path
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Database path
db_path = parent_dir / "data_cleaned" / "streamlit_app.db"

# Connect to the database
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Query the database
cursor.execute("SELECT id, issue_type, priority, title, status FROM bug_tracker")
rows = cursor.fetchall()

# Print the results
print(f"Found {len(rows)} issues in the bug tracker database:")
print("\nID | Type | Priority | Status | Title")
print("-" * 80)

for row in rows:
    id, issue_type, priority, title, status = row
    # Convert priority number to text
    priority_text = {1: "High", 2: "Urgent", 3: "Regular", 4: "Low"}
    print(f"{id:2d} | {issue_type:14s} | {priority_text.get(priority, 'Unknown'):8s} | {status:8s} | {title}")

# Close the connection
conn.close()