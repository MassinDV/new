"""Main Flask application - Forja VOD IPTV Service"""

from flask import Flask, request, Response
from config import USERNAME, PASSWORD, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_THREADED
from auth import require_auth
from data_loader import load_movies, load_series, load_channels
from web_pages import render_homepage, render_m3u_playlist
from api_routes import handle_player_api

app = Flask(__name__)


# ================== Stream Redirect Routes ==================

@app.route('/<any(live,movie,series):_type>/<username>/<password>/<int:stream_id>')
@app.route('/<any(live,movie,series):_type>/<username>/<password>/<int:stream_id>.<ext>')
@require_auth
def redirect_stream(_type, username, password, stream_id, ext=None):
    """Redirect to actual stream URL"""
    if _type == "movie":
        for m in load_movies():
            if m["id"] == stream_id:
                if url := m.get("url"):
                    return Response(status=302, headers={"Location": url})

    elif _type == "series":
        for s in load_series():
            for season in s.get("seasons", []):
                for ep in season.get("episodes", []):
                    if ep.get("id") == stream_id:
                        if url := ep.get("url"):
                            return Response(status=302, headers={"Location": url})

    elif _type == "live":
        for ch in load_channels():
            if ch["id"] == stream_id:
                if url := ch.get("url"):
                    return Response(status=302, headers={"Location": url})

    return "Stream not found", 404


# ================== API Routes ==================

@app.route("/player_api.php")
def player_api():
    """Main API endpoint for IPTV player apps"""
    return handle_player_api()


# ================== Export Routes ==================

@app.route("/api/export/m3u")
def export_m3u():
    """Export channels as M3U playlist"""
    base_url = f"http://{request.host}"
    m3u_content = render_m3u_playlist(base_url, USERNAME, PASSWORD)
    return m3u_content, 200, {"Content-Type": "application/x-mpegURL"}


# ================== Homepage ==================

@app.route("/")
def index():
    """Homepage with content showcase"""
    return render_homepage()


# ================== Application Entry Point ==================

if __name__ == "__main__":
    print("=" * 60)
    print("ðŸ”ï¸  Forja VOD - IPTV Service Starting")
    print("=" * 60)
    print(f"Server: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"API Endpoint: http://{FLASK_HOST}:{FLASK_PORT}/player_api.php")
    print(f"Username: {USERNAME}")
    print(f"Password: {PASSWORD}")
    print("=" * 60)
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        threaded=FLASK_THREADED
    )