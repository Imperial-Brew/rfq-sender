import sys
from pathlib import Path
import yaml

# Add the project root to the path
project_root = Path(".")  # Adjust if needed
sys.path.append(str(project_root))

from utils.auth import hash_password

# Get user input
email = input("Enter user email: ")
password = input("Enter password: ")

# Generate hash
password_hash = hash_password(password)

print(f"\nPassword hash for {email}:")
print(password_hash)