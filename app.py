"""Main Flask application - Forja VOD IPTV Service"""

from flask import Flask, request, Response, jsonify
from config import USERNAME, PASSWORD, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_THREADED
from auth import require_auth
from data_loader import load_movies, load_series, load_channels, clear_cache
from web_pages import render_homepage, render_m3u_playlist
from api_routes import handle_player_api

app = Flask(__name__)


# ================== Stream Redirect Routes ==================
# Note: These routes are kept for backward compatibility
# but the API now returns direct URLs in the direct_source field

@app.route('/<any(live,movie,series):_type>/<username>/<password>/<int:stream_id>')
@app.route('/<any(live,movie,series):_type>/<username>/<password>/<int:stream_id>.<ext>')
@require_auth
def redirect_stream(_type, username, password, stream_id, ext=None):
    """Redirect to actual stream URL (backward compatibility)"""
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


# ================== Cache Management Routes ==================

@app.route("/api/cache/clear")
@app.route("/api/cache/clear/<cache_type>")
def clear_cache_endpoint(cache_type=None):
    """Clear cache - useful after updating M3U files or JSON sources
    
    Usage:
    - /api/cache/clear - Clear all caches
    - /api/cache/clear/movies - Clear only movies cache
    - /api/cache/clear/series - Clear only series cache
    - /api/cache/clear/channels - Clear only channels cache
    """
    valid_types = ['movies', 'series', 'channels']
    
    if cache_type and cache_type not in valid_types:
        return jsonify({
            "error": "Invalid cache type",
            "valid_types": valid_types
        }), 400
    
    clear_cache(cache_type)
    
    if cache_type:
        return jsonify({
            "status": "success",
            "message": f"{cache_type} cache cleared",
            "note": "New data will be loaded on next request"
        })
    else:
        return jsonify({
            "status": "success",
            "message": "All caches cleared",
            "note": "New data will be loaded on next request"
        })


@app.route("/api/cache/status")
def cache_status():
    """Check cache status"""
    from data_loader import _cache, is_cache_valid
    
    status = {}
    for cache_type in ['movies', 'series', 'channels']:
        cache_entry = _cache.get(cache_type, {})
        status[cache_type] = {
            "is_valid": is_cache_valid(cache_type),
            "has_data": cache_entry.get('data') is not None,
            "item_count": len(cache_entry.get('data', [])) if cache_entry.get('data') else 0,
            "timestamp": cache_entry.get('timestamp', 0)
        }
    
    return jsonify(status)


# ================== Export Routes ==================

@app.route("/api/export/m3u")
def export_m3u():
    """Export channels as M3U playlist with direct URLs"""
    # Get output format - 'direct' (default) or 'proxy'
    output_format = request.args.get("output_format", "direct")
    base_url = f"http://{request.host}"
    m3u_content = render_m3u_playlist(base_url, USERNAME, PASSWORD, output_format)
    return m3u_content, 200, {"Content-Type": "application/x-mpegURL"}


# ================== Homepage ==================

@app.route("/")
def index():
    """Homepage with content showcase"""
    return render_homepage()


# ================== Application Entry Point ==================

if __name__ == "__main__":
    print("=" * 60)
    print("🎬  Forja VOD - IPTV Service Starting")
    print("=" * 60)
    print(f"Server: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"API Endpoint: http://{FLASK_HOST}:{FLASK_PORT}/player_api.php")
    print(f"Username: {USERNAME}")
    print(f"Password: {PASSWORD}")
    print("=" * 60)
    print("Cache Management:")
    print(f"  Clear All: http://{FLASK_HOST}:{FLASK_PORT}/api/cache/clear")
    print(f"  Clear Movies: http://{FLASK_HOST}:{FLASK_PORT}/api/cache/clear/movies")
    print(f"  Clear Series: http://{FLASK_HOST}:{FLASK_PORT}/api/cache/clear/series")
    print(f"  Clear Channels: http://{FLASK_HOST}:{FLASK_PORT}/api/cache/clear/channels")
    print(f"  Cache Status: http://{FLASK_HOST}:{FLASK_PORT}/api/cache/status")
    print("=" * 60)
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        threaded=FLASK_THREADED
    )