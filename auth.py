"""Authentication management for Forja VOD"""

from functools import wraps
from flask import request, jsonify
from config import USERS, ACTIVE_CONNECTIONS
from datetime import datetime


def get_user_data(username):
    """Get user data from configuration"""
    return USERS.get(username)


def check_credentials(username, password):
    """Verify user credentials"""
    user_data = get_user_data(username)
    if not user_data:
        return False
    
    # Check password
    if user_data.get("password") != password:
        return False
    
    # Check if account is active
    if user_data.get("status") != "Active":
        return False
    
    # Check expiry date
    exp_date = int(user_data.get("exp_date", 0))
    current_time = int(datetime.now().timestamp())
    if current_time > exp_date:
        return False
    
    return True


def check_connection_limit(username):
    """Check if user has exceeded connection limit"""
    user_data = get_user_data(username)
    if not user_data:
        return False
    
    max_connections = int(user_data.get("max_connections", 1))
    active_cons = ACTIVE_CONNECTIONS.get(username, 0)
    
    return active_cons < max_connections


def increment_connection(username):
    """Increment active connection count for user"""
    if username not in ACTIVE_CONNECTIONS:
        ACTIVE_CONNECTIONS[username] = 0
    ACTIVE_CONNECTIONS[username] += 1


def decrement_connection(username):
    """Decrement active connection count for user"""
    if username in ACTIVE_CONNECTIONS and ACTIVE_CONNECTIONS[username] > 0:
        ACTIVE_CONNECTIONS[username] -= 1


def get_active_connections(username):
    """Get current active connection count"""
    return ACTIVE_CONNECTIONS.get(username, 0)


def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = kwargs.get('username') or request.args.get('username', '')
        password = kwargs.get('password') or request.args.get('password', '')
        
        if not check_credentials(username, password):
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Check connection limit for streaming routes
        if 'stream' in request.path or 'live' in request.path or 'movie' in request.path or 'series' in request.path:
            if not check_connection_limit(username):
                return jsonify({"error": "Maximum connections reached"}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def get_user_info(username):
    """Get user information for API responses"""
    user_data = get_user_data(username)
    
    if not user_data:
        return {
            "auth": 0,
            "status": "Disabled",
            "message": "User not found"
        }
    
    # Check if account is expired
    exp_date = int(user_data.get("exp_date", 0))
    current_time = int(datetime.now().timestamp())
    
    if current_time > exp_date:
        return {
            "username": username,
            "auth": 0,
            "status": "Expired",
            "exp_date": user_data.get("exp_date"),
            "message": "Account has expired"
        }
    
    return {
        "username": username,
        "password": user_data.get("password"),
        "status": user_data.get("status", "Active"),
        "auth": 1,
        "exp_date": user_data.get("exp_date"),
        "is_trial": user_data.get("is_trial", "0"),
        "active_cons": str(get_active_connections(username)),
        "max_connections": user_data.get("max_connections", "1"),
        "allowed_output_formats": user_data.get("allowed_output_formats", ["m3u8"]),
        "message": ""
    }


def get_unauthorized_response():
    """Return response for unauthorized access"""
    return jsonify({
        "user_info": {
            "auth": 0,
            "status": "Disabled",
            "message": "Invalid credentials"
        }
    })