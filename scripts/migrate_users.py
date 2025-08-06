# scripts/migrate_users.py
import yaml
import getpass
from pathlib import Path
import sys

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from utils.auth import hash_password


def migrate_users():
    """Migrate existing users to new schema with password hashing."""
    users_path = parent_dir / "users.yaml"

    # Load existing users
    with open(users_path, "r") as f:
        data = yaml.safe_load(f)

    users = data["users"]

    # Add authentication fields to each user
    for user in users:
        if "password_hash" not in user:
            print(f"Setting password for {user['name']} ({user['email']})")
            password = getpass.getpass("Enter password: ")
            user["password_hash"] = hash_password(password)
            user["last_login"] = None
            user["session_token"] = None

    # Save updated users
    with open(users_path, "w") as f:
        yaml.dump(data, f)

    print(f"Successfully migrated {len(users)} users")


if __name__ == "__main__":
    migrate_users()