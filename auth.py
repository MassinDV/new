"""Authentication management for Forja VOD"""

from functools import wraps
from flask import request, jsonify
from config import USERNAME, PASSWORD, EXP_DATE
from datetime import datetime


def check_credentials(username, password):
    """Verify user credentials"""
    return username == USERNAME and password == PASSWORD


def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = kwargs.get('username') or request.args.get('username', '')
        password = kwargs.get('password') or request.args.get('password', '')
        
        if not check_credentials(username, password):
            return jsonify({"error": "Invalid credentials"}), 401
        
        return f(*args, **kwargs)
    return decorated_function


def get_user_info(username):
    """Get user information for API responses"""
    return {
        "username": username,
        "password": PASSWORD,
        "status": "Active",
        "auth": 1,
        "exp_date": EXP_DATE,
        "is_trial": "0",
        "active_cons": "1",
        "max_connections": "10",
        "allowed_output_formats": ["m3u8", "mp4", "mpd"],
        "message": ""
    }


def get_unauthorized_response():
    """Return response for unauthorized access"""
    return jsonify({
        "user_info": {
            "auth": 0,
            "status": "Disabled"
        }
    })