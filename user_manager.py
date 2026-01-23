"""User management utilities"""

from datetime import datetime, timedelta
from config import USERS


def add_user(username, password, days=30, max_connections=2, is_trial=False):
    """
    Add a new user to the system
    
    Args:
        username: User's username
        password: User's password
        days: Number of days until expiration
        max_connections: Maximum concurrent connections
        is_trial: Whether this is a trial account
    """
    exp_date = int((datetime.now() + timedelta(days=days)).timestamp())
    
    USERS[username] = {
        "password": password,
        "status": "Active",
        "exp_date": str(exp_date),
        "is_trial": "1" if is_trial else "0",
        "max_connections": str(max_connections),
        "allowed_output_formats": ["m3u8", "mp4", "mpd"]
    }
    
    print(f"[USER] Added user '{username}' - Expires in {days} days")
    return USERS[username]


def remove_user(username):
    """Remove a user from the system"""
    if username in USERS:
        del USERS[username]
        print(f"[USER] Removed user '{username}'")
        return True
    return False


def update_user_expiry(username, days):
    """Update user's expiration date"""
    if username in USERS:
        exp_date = int((datetime.now() + timedelta(days=days)).timestamp())
        USERS[username]["exp_date"] = str(exp_date)
        print(f"[USER] Updated '{username}' expiry to {days} days from now")
        return True
    return False


def update_user_connections(username, max_connections):
    """Update user's maximum connections"""
    if username in USERS:
        USERS[username]["max_connections"] = str(max_connections)
        print(f"[USER] Updated '{username}' max connections to {max_connections}")
        return True
    return False


def disable_user(username):
    """Disable a user account"""
    if username in USERS:
        USERS[username]["status"] = "Disabled"
        print(f"[USER] Disabled user '{username}'")
        return True
    return False


def enable_user(username):
    """Enable a user account"""
    if username in USERS:
        USERS[username]["status"] = "Active"
        print(f"[USER] Enabled user '{username}'")
        return True
    return False


def list_all_users():
    """List all users with their details"""
    print("\n" + "="*80)
    print(f"{'Username':<15} {'Status':<10} {'Expiry Date':<20} {'Max Conn':<10} {'Trial':<8}")
    print("="*80)
    
    for username, data in USERS.items():
        exp_timestamp = int(data.get("exp_date", 0))
        exp_date = datetime.fromtimestamp(exp_timestamp).strftime("%Y-%m-%d %H:%M")
        
        # Check if expired
        status = data.get("status", "Active")
        if exp_timestamp < int(datetime.now().timestamp()):
            status = "Expired"
        
        print(f"{username:<15} {status:<10} {exp_date:<20} {data.get('max_connections', '1'):<10} {data.get('is_trial', '0'):<8}")
    
    print("="*80 + "\n")


def get_user_stats(username):
    """Get detailed statistics for a user"""
    if username not in USERS:
        return None
    
    user_data = USERS[username]
    exp_timestamp = int(user_data.get("exp_date", 0))
    current_time = int(datetime.now().timestamp())
    
    days_remaining = (exp_timestamp - current_time) / 86400  # seconds in a day
    
    return {
        "username": username,
        "status": user_data.get("status"),
        "is_trial": user_data.get("is_trial") == "1",
        "max_connections": int(user_data.get("max_connections", 1)),
        "expiry_date": datetime.fromtimestamp(exp_timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        "days_remaining": max(0, int(days_remaining)),
        "is_expired": current_time > exp_timestamp
    }


# Example usage functions
if __name__ == "__main__":
    print("\n🔧 User Management System\n")
    
    # List all users
    list_all_users()
    
    # Example: Add a new user
    # add_user("newuser", "newpass123", days=30, max_connections=2, is_trial=False)
    
    # Example: Get user stats
    # stats = get_user_stats("test")
    # if stats:
    #     print(f"\nUser: {stats['username']}")
    #     print(f"Status: {stats['status']}")
    #     print(f"Days Remaining: {stats['days_remaining']}")
    #     print(f"Max Connections: {stats['max_connections']}")