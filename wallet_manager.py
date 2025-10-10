import json
import os
from config import USERS_FILE

def _load_users():
    """Load users from JSON file"""
    if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_users(data):
    """Save users to JSON file"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def register_user(user_id, username):
    """Register a user if not exists"""
    users = _load_users()
    key = str(user_id)
    if key not in users:
        users[key] = {"username": username, "wallet": None}
    else:
        users[key]["username"] = username
    _save_users(users)

def set_user_wallet(user_id, wallet):
    """Set wallet address for a user"""
    users = _load_users()
    key = str(user_id)
    if key not in users:
        return False
    users[key]["wallet"] = wallet
    _save_users(users)
    return True

def get_user_wallet(user_id):
    """Get wallet address for a user"""
    return _load_users().get(str(user_id), {}).get("wallet")

def get_user_data(user_id):
    """Get full user data"""
    return _load_users().get(str(user_id))
