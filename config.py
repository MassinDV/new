"""Configuration settings for Forja VOD application"""

import json
import os
from datetime import datetime, timedelta

# ================== Load Users from JSON ==================
def load_users_from_json():
    """Load users from users.json file"""
    users_file = "users.json"
    
    print(f"[CONFIG] Looking for {users_file} in: {os.path.abspath('.')}")
    
    if os.path.exists(users_file):
        try:
            print(f"[CONFIG] Found {users_file}, loading...")
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            # Convert to the expected format
            users = {}
            for username, data in users_data.items():
                users[username] = {
                    "password": str(data.get("password", "")),
                    "status": "Active",
                    "exp_date": str(data.get("exp_date", "0")),
                    "is_trial": "1" if data.get("account_type") == "Trial" else "0",
                    "max_connections": str(data.get("max_connections", 1)),
                    "allowed_output_formats": ["m3u8", "mp4", "mpd"],
                    "account_type": data.get("account_type", "Standard")
                }
                print(f"[CONFIG]   ✓ Loaded user: {username} (Type: {data.get('account_type')}, MaxConn: {data.get('max_connections')})")
            
            print(f"[CONFIG] Successfully loaded {len(users)} users from {users_file}")
            return users
            
        except json.JSONDecodeError as e:
            print(f"[CONFIG] ✗ Error: Invalid JSON in {users_file}: {e}")
            print("[CONFIG] Using default test user only")
        except Exception as e:
            print(f"[CONFIG] ✗ Error loading {users_file}: {e}")
            print("[CONFIG] Using default test user only")
    else:
        print(f"[CONFIG] ✗ {users_file} not found at: {os.path.abspath(users_file)}")
        print("[CONFIG] Using default test user only")
    
    # Fallback to default user
    return {
        "test": {
            "password": "test",
            "status": "Active",
            "exp_date": "2524608000",
            "is_trial": "0",
            "max_connections": "10",
            "allowed_output_formats": ["m3u8", "mp4", "mpd"],
            "account_type": "Admin"
        }
    }

# Load users
USERS = load_users_from_json()

# Track active connections per user (in-memory, resets on server restart)
ACTIVE_CONNECTIONS = {}

# ================== Legacy Support ==================
USERNAME = "test"  # Default/legacy username
PASSWORD = "test"  # Default/legacy password
EXP_DATE = "2524608000"  # ~2050

# ================== TMDb API Configuration ==================
TMDB_API_KEY = "d9ae1980a7b9c6f43cd97e95f8d464c5"

# ================== Source Configuration URLs ==================
SOURCE_CONFIG_URLS = {
    "json": "https://dl.dropboxusercontent.com/scl/fi/y1ouv76258xw02uiwo5nb/Forja-data.json?rlkey=ob5wfl9mimu6plb89jx371phc&st=18256iva&dl=0",
    "txt": "https://dl.dropboxusercontent.com/scl/fi/tlm6qn8ur3rwd5geueg5v/Forja-data.txt?rlkey=7vxduuzdz93b3h0bwq0i0tukh&st=awypp6ds&dl=0"
}

# ================== M3U Source Configuration ==================
M3U_SOURCES = {
    "live": [
        # Local M3U files
        {"type": "local", "path": "forja-live.m3u"},
        # Remote M3U files
        {"type": "remote", "url": "https://dl.dropboxusercontent.com/scl/fi/2jvpsosqsshqr0941y0ba/forja-live.m3u?rlkey=5rdh0141gdppltge93byt0qhu&st=4wnbr52d&dl=0"}
    ],
    "movies": [
        {"type": "local", "path": "forja-movies.m3u"},
        # Add your movie M3U URLs here
    ],
    "series": [
        {"type": "local", "path": "forja-series.m3u"},
        # Add your series M3U URLs here
    ]
}

# ================== Flask Configuration ==================
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False
FLASK_THREADED = True


# ================== User Management Functions ==================
def save_users_to_json():
    """Save current users to users.json file"""
    users_file = "users.json"
    
    try:
        # Convert USERS format back to simple JSON format
        users_data = {}
        for username, data in USERS.items():
            users_data[username] = {
                "password": data.get("password"),
                "exp_date": data.get("exp_date"),
                "max_connections": int(data.get("max_connections", 1)),
                "account_type": data.get("account_type", "Standard")
            }
        
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2)
        
        print(f"[CONFIG] Saved {len(users_data)} users to {users_file}")
        return True
    except Exception as e:
        print(f"[CONFIG] Error saving users.json: {e}")
        return False


def add_user(username, password, days=30, max_connections=2, account_type="Standard"):
    """Add a new user and save to JSON"""
    exp_date = int((datetime.now() + timedelta(days=days)).timestamp())
    
    USERS[username] = {
        "password": password,
        "status": "Active",
        "exp_date": str(exp_date),
        "is_trial": "1" if account_type == "Trial" else "0",
        "max_connections": str(max_connections),
        "allowed_output_formats": ["m3u8", "mp4", "mpd"],
        "account_type": account_type
    }
    
    save_users_to_json()
    print(f"[USER] Added user '{username}' - Type: {account_type}, Expires in {days} days")
    return USERS[username]


def remove_user(username):
    """Remove a user and save to JSON"""
    if username in USERS:
        del USERS[username]
        save_users_to_json()
        print(f"[USER] Removed user '{username}'")
        return True
    return False


def update_user_expiry(username, days):
    """Update user's expiration date and save to JSON"""
    if username in USERS:
        exp_date = int((datetime.now() + timedelta(days=days)).timestamp())
        USERS[username]["exp_date"] = str(exp_date)
        save_users_to_json()
        print(f"[USER] Updated '{username}' expiry to {days} days from now")
        return True
    return False


def reload_users():
    """Reload users from users.json file"""
    global USERS
    USERS = load_users_from_json()
    print("[CONFIG] Users reloaded from users.json")
    return USERS