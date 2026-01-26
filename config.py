"""Configuration settings for Forja VOD application"""

from datetime import datetime, timedelta

# ================== Multi-User Configuration ==================
# Each user has: username, password, max_connections, expiry_date, is_trial
USERS = {
    "test": {
        "password": "test",
        "status": "Active",
        "exp_date": "2524608000",  # ~2050 (timestamp)
        "is_trial": "0",
        "max_connections": "10",
        "allowed_output_formats": ["m3u8", "mp4", "mpd"]
    },
    "user1": {
        "password": "pass123",
        "status": "Active",
        "exp_date": str(int((datetime.now() + timedelta(days=30)).timestamp())),  # 30 days from now
        "is_trial": "0",
        "max_connections": "2",
        "allowed_output_formats": ["m3u8", "mp4", "mpd"]
    },
    "trial_user": {
        "password": "trial123",
        "status": "Active",
        "exp_date": str(int((datetime.now() + timedelta(days=7)).timestamp())),  # 7 days trial
        "is_trial": "1",
        "max_connections": "1",
        "allowed_output_formats": ["m3u8"]
    },
    "premium": {
        "password": "premium456",
        "status": "Active",
        "exp_date": str(int((datetime.now() + timedelta(days=365)).timestamp())),  # 1 year
        "is_trial": "0",
        "max_connections": "5",
        "allowed_output_formats": ["m3u8", "mp4", "mpd"]
    }
}

# Track active connections per user (in-memory, resets on server restart)
ACTIVE_CONNECTIONS = {}

# ================== Legacy Support ==================
USERNAME = "test"  # Default/legacy username
PASSWORD = "test"  # Default/legacy password
EXP_DATE = "2524608000"  # ~2050

# ================== Cache Configuration ==================
# Cache TTL in seconds - adjust based on your needs
# 60 = 1 minute (good for testing/development)
# 300 = 5 minutes (balanced)
# 600 = 10 minutes (production)
CACHE_TTL = 60  # Default 60 seconds

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