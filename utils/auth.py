import yaml

def load_users(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)["users"]

def get_user_role(user):
    return user.get("role", "viewer")