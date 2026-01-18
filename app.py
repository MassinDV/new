from flask import Flask, request, jsonify, Response
import json
import os
import urllib3
import re
from functools import lru_cache
from urllib.parse import quote
import requests
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

USERNAME = "test"
PASSWORD = "test"
EXP_DATE = "2524608000"  # ~2050

# ================== Dynamic Source Configuration ==================
# URLs for source configuration files
SOURCE_CONFIG_URLS = {
    "json": "https://dl.dropboxusercontent.com/scl/fi/y1ouv76258xw02uiwo5nb/Forja-data.json?rlkey=ob5wfl9mimu6plb89jx371phc&st=18256iva&dl=0",
    "txt": "https://dl.dropboxusercontent.com/scl/fi/tlm6qn8ur3rwd5geueg5v/Forja-data.txt?rlkey=7vxduuzdz93b3h0bwq0i0tukh&st=awypp6ds&dl=0"
}

def load_sources_from_config():
    """Load source URLs from external configuration files"""
    movie_sources = []
    series_sources = []
    channel_sources = []
    
    # Try JSON format first
    try:
        resp = requests.get(SOURCE_CONFIG_URLS["json"], timeout=20)
        resp.raise_for_status()
        config = resp.json()
        
        # Extract sources from JSON structure
        if "movie_sources" in config:
            movie_sources = [{"type": "remote", "url": url} for url in config["movie_sources"]]
        if "series_sources" in config:
            series_sources = [{"type": "remote", "url": url} for url in config["series_sources"]]
        if "channel_sources" in config:
            channel_sources = [{"type": "remote", "url": url} for url in config["channel_sources"]]
        
        print(f"[CONFIG] Loaded from JSON: {len(movie_sources)} movies, {len(series_sources)} series, {len(channel_sources)} channels")
        return movie_sources, series_sources, channel_sources
    except Exception as e:
        print(f"[CONFIG] JSON load failed: {e}, trying TXT format...")
    
    # Fallback to TXT format
    try:
        resp = requests.get(SOURCE_CONFIG_URLS["txt"], timeout=20)
        resp.raise_for_status()
        content = resp.text
        
        # Parse text file by sections
        current_section = None
        for line in content.split('\n'):
            line = line.strip()
            
            # Identify sections
            if "MOVIE SOURCES" in line.upper():
                current_section = "movies"
                continue
            elif "SERIES" in line.upper() and "SOURCES" in line.upper():
                current_section = "series"
                continue
            elif "CHANNEL SOURCES" in line.upper():
                current_section = "channels"
                continue
            
            # Extract URLs (lines starting with http)
            if line.startswith("http"):
                source_entry = {"type": "remote", "url": line}
                
                if current_section == "movies":
                    movie_sources.append(source_entry)
                elif current_section == "series":
                    series_sources.append(source_entry)
                elif current_section == "channels":
                    channel_sources.append(source_entry)
        
        print(f"[CONFIG] Loaded from TXT: {len(movie_sources)} movies, {len(series_sources)} series, {len(channel_sources)} channels")
        return movie_sources, series_sources, channel_sources
    except Exception as e:
        print(f"[CONFIG] TXT load failed: {e}")
    
    # Return empty lists if both fail
    print("[CONFIG] Warning: Could not load any sources from config files")
    return [], [], []

# Load sources dynamically at startup
MOVIE_SOURCES, SERIES_SOURCES, CHANNEL_SOURCES = load_sources_from_config()

def safe_strip(value):
    """Safely strip whitespace from strings"""
    return (value or "").strip()

def clean_category_name(name):
    """Clean category names for better display"""
    if not name:
        return "General"
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    # Remove file extensions
    name = re.sub(r'\.(json|JSON)$', '', name)
    # Keep "Movies" or "Series" suffix but ensure proper spacing
    # Capitalize properly
    return name.strip().title()

def get_category_from_source(source_dict, data=None):
    """Extract and clean category name from source or data"""
    # First check if data has a Category field
    if data and isinstance(data, dict):
        if "Category" in data:
            return clean_category_name(data["Category"])
        # Check in channels array
        if "channels" in data and isinstance(data["channels"], list) and len(data["channels"]) > 0:
            first_channel = data["channels"][0]
            if "category" in first_channel:
                return clean_category_name(first_channel["category"])
    
    # Fall back to filename extraction
    filename = source_dict.get("path") or source_dict.get("url", "")
    base = os.path.basename(filename)
    # Remove query parameters
    if '?' in base:
        base = base.split('?')[0]
    # Remove extension
    base = re.sub(r'\.(json|JSON)$', '', base)
    return clean_category_name(base)

def clean_cast(cast_value):
    """Clean and normalize cast data"""
    if not cast_value:
        return []
    if isinstance(cast_value, list):
        return [str(a).strip() for a in cast_value if a and str(a).strip()]
    if isinstance(cast_value, str):
        cleaned = re.sub(r'\s*\n\s*,?\s*', ',', cast_value)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return [a.strip() for a in cleaned.split(',') if a.strip()]
    return []

def normalize_genre(genre_value):
    """Normalize genre field to list"""
    if not genre_value:
        return []
    if isinstance(genre_value, list):
        return [g.strip() for g in genre_value if g and str(g).strip()]
    if isinstance(genre_value, str):
        return [g.strip() for g in re.split(r'[,/|]\s*', genre_value) if g.strip()]
    return []

# ================== TMDb Fetch ==================
@lru_cache(maxsize=100)
def fetch_tmdb_details(title, is_movie=True):
    """Fetch additional metadata from TMDb API"""
    api_key = "d9ae1980a7b9c6f43cd97e95f8d464c5"
    media_type = "movie" if is_movie else "tv"
    http = urllib3.PoolManager()

    try:
        search_url = f"https://api.themovedb.org/3/search/{media_type}?api_key={api_key}&query={quote(title)}"
        resp = http.request('GET', search_url, timeout=5.0)
        if resp.status != 200:
            return None

        data = json.loads(resp.data.decode('utf-8'))
        if not data.get('results'):
            return None

        first = data['results'][0]
        tmdb_id = first['id']

        details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key}"
        details_resp = http.request('GET', details_url, timeout=5.0)
        if details_resp.status != 200:
            return None
        details = json.loads(details_resp.data.decode('utf-8'))

        credits = {}
        credits_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/credits?api_key={api_key}"
        credits_resp = http.request('GET', credits_url, timeout=5.0)
        if credits_resp.status == 200:
            credits = json.loads(credits_resp.data.decode('utf-8'))

        return {
            'tmdb_id': tmdb_id,
            'details': details,
            'credits': credits
        }
    except Exception as e:
        print(f"TMDb error for '{title}': {e}")
        return None

# ================== LOAD MOVIES ==================
@lru_cache(maxsize=1)
def load_movies(_cache_key=None):
    """Load and process all movie data"""
    movies = []
    seen_ids = set()

    for source in MOVIE_SOURCES:
        try:
            if source["type"] == "local":
                if not os.path.exists(source["path"]):
                    print(f"[MOVIES] File not found: {source['path']}")
                    continue
                with open(source["path"], 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
            elif source["type"] == "remote":
                resp = requests.get(source["url"], timeout=20)
                resp.raise_for_status()
                raw_data = resp.json()
            else:
                continue

            # Get category from source or data
            category = get_category_from_source(source, raw_data)

            # Handle both list and dict with Category field
            movie_list = raw_data if isinstance(raw_data, list) else raw_data.get("movies", raw_data.get("data", []))

            for item in movie_list:
                # Skip items with Episodes field (those are series)
                if "Episodes" in item:
                    continue

                # Must have Movie field to be a movie
                if "Movie" not in item:
                    continue

                info = item.get("Info", {}) or {}
                movie_data = item.get("Movie", {})

                # Get unique ID
                cuid = movie_data.get("CUID") or info.get("CUID") or item.get("CUID")
                if not cuid or not str(cuid).isdigit():
                    continue

                movie_id = int(cuid)
                if movie_id in seen_ids:
                    continue
                seen_ids.add(movie_id)

                # Basic fields
                title = safe_strip(item.get("Title") or item.get("Name") or "Untitled")
                plot = safe_strip(item.get("Synopsis") or info.get("Overview") or "No description available.")

                cover = safe_strip(item.get("VerticalImage") or item.get("PosterImage") or "")
                banner = safe_strip(item.get("PosterImage") or item.get("VerticalImage") or cover)

                stream_url = safe_strip(movie_data.get("streamUrl") or info.get("streamUrl") or info.get("stream_url") or "")

                # Extract year
                year = str(info.get("Year") or "").strip()
                if not year and '(' in title and ')' in title:
                    m = re.search(r'\((\d{4})\)', title)
                    if m:
                        year = m.group(1)

                # Process genres
                genres = normalize_genre(info.get("Genres") or info.get("Genre"))
                if not genres and category:
                    genres = [category]

                # Cast and crew
                cast = clean_cast(info.get("Cast") or info.get("Actors"))
                director = safe_strip(info.get("Director") or "Unknown")

                # Optional TMDb enrichment
                tmdb_id = info.get("tmdb_id")

                movies.append({
                    "id": movie_id,
                    "title": title,
                    "plot": plot,
                    "cover": cover,
                    "banner": banner,
                    "year": year,
                    "genre": genres,
                    "cast": cast,
                    "director": director,
                    "rating": str(info.get("Rating") or "0.0"),
                    "duration": str(info.get("Duration") or ""),
                    "country": safe_strip(info.get("Country") or "Morocco"),
                    "url": stream_url,
                    "category": category,
                    "tmdb_id": tmdb_id
                })

        except Exception as e:
            print(f"[MOVIES] Error loading source {source}: {e}")

    print(f"[MOVIES] Loaded {len(movies)} unique entries")
    return movies

# ================== LOAD SERIES ==================
@lru_cache(maxsize=1)
def load_series(_cache_key=None):
    """Load and process all series data"""
    series_list = []
    series_id_counter = 10000
    seen_titles = {}

    for source in SERIES_SOURCES:
        try:
            if source["type"] == "local":
                if not os.path.exists(source["path"]):
                    print(f"[SERIES] File not found: {source['path']}")
                    continue
                with open(source["path"], 'r', encoding='utf-8') as f:
                    raw = json.load(f)
            elif source["type"] == "remote":
                r = requests.get(source["url"], timeout=20)
                r.raise_for_status()
                raw = r.json()
            else:
                continue

            # Get category from source or data
            category = get_category_from_source(source, raw)

            # Handle both list and dict formats
            series_data = raw if isinstance(raw, list) else raw.get("series", raw.get("data", []))

            for item in series_data:
                # Must have Episodes field to be a series
                episodes = item.get("Episodes", [])
                if not episodes:
                    continue

                # Must NOT have Movie field
                if "Movie" in item:
                    continue

                info = item.get("Info", {}) or {}

                title = safe_strip(item.get("Title") or item.get("Name") or "Unknown Series")

                # Avoid duplicate series
                if title in seen_titles:
                    continue
                seen_titles[title] = True

                plot = safe_strip(item.get("Synopsis") or info.get("Overview") or "")
                cover = safe_strip(item.get("VerticalImage") or "")
                banner = safe_strip(item.get("PosterImage") or "")

                # Process metadata
                cast = clean_cast(info.get("Cast"))
                genres = normalize_genre(info.get("Genres") or info.get("Genre"))
                if not genres and category:
                    genres = [category]

                year = str(info.get("Year") or "").strip()

                series_obj = {
                    'id': series_id_counter,
                    'title': title,
                    'cover': cover,
                    'banner': banner,
                    'plot': plot,
                    'year': year,
                    'genre': genres,
                    'cast': cast,
                    'director': safe_strip(info.get("Director") or ""),
                    'rating': str(info.get("Rating") or "0.0"),
                    'category': category,
                    'seasons': [],
                    'tmdb_id': info.get("tmdb_id")
                }
                series_id_counter += 1

                # Process episodes
                season_map = {}
                for ep in episodes:
                    # Extract episode number
                    ep_num_str = ep.get("Episode", "")
                    match = re.search(r'E(\d+)', ep_num_str, re.I)
                    ep_num = int(match.group(1)) if match else None

                    # Extract season number
                    season_str = ep.get("Season", "S01")
                    season_match = re.search(r'S(\d+)', season_str, re.I)
                    season_num = int(season_match.group(1)) if season_match else 1

                    if season_num not in season_map:
                        season_map[season_num] = []

                    thumb = safe_strip(ep.get("imageUrl") or series_obj['banner'])
                    ep_title = safe_strip(ep.get("Episode_Title") or f"Episode {ep_num or '?'}")
                    ep_plot = safe_strip(ep.get("Episode_Overview") or ep.get("plot") or "")
                    ep_url = safe_strip(ep.get("streamUrl") or "")

                    ep_cuid = ep.get("CUID")
                    if ep_cuid and str(ep_cuid).isdigit():
                        ep_id = int(ep_cuid)
                    else:
                        if ep_num is not None:
                            ep_id = series_obj['id'] * 10000 + season_num * 100 + ep_num
                        else:
                            ep_id = series_obj['id'] * 10000 + season_num * 100 + len(season_map[season_num]) + 1

                    episode_data = {
                        'id': ep_id,
                        'episode': ep_num if ep_num is not None else len(season_map[season_num]) + 1,
                        'title': ep_title,
                        'plot': ep_plot,
                        'thumbnail': thumb,
                        'url': ep_url
                    }
                    season_map[season_num].append(episode_data)

                # Sort and structure seasons
                for sn in sorted(season_map.keys()):
                    season_map[sn].sort(key=lambda x: x['episode'])
                    series_obj['seasons'].append({
                        'season': sn,
                        'episode_count': len(season_map[sn]),
                        'episodes': season_map[sn]
                    })

                series_list.append(series_obj)

        except Exception as e:
            print(f"[SERIES] Error loading source {source}: {e}")

    print(f"[SERIES] Loaded {len(series_list)} series")
    return series_list

# ================== LOAD CHANNELS ==================
@lru_cache(maxsize=1)
def load_channels(_cache_key=None):
    """Load and process all channel data"""
    channels = []
    channel_id_counter = 1

    for source in CHANNEL_SOURCES:
        try:
            if source["type"] == "local":
                if not os.path.exists(source["path"]):
                    print(f"[CHANNELS] File not found: {source['path']}")
                    continue
                with open(source["path"], 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
            elif source["type"] == "remote":
                resp = requests.get(source["url"], timeout=20)
                resp.raise_for_status()
                raw_data = resp.json()
            else:
                continue

            # Handle both array and object formats
            channel_list = raw_data if isinstance(raw_data, list) else raw_data.get("channels", [])

            for ch in channel_list:
                name = safe_strip(ch.get("name") or ch.get("channel_name") or "Unknown Channel")
                logo = safe_strip(ch.get("logo") or ch.get("stream_icon") or "")
                stream_url = safe_strip(ch.get("stream_url") or ch.get("url") or "")
                
                # Clean category name
                raw_category = ch.get("category") or ch.get("category_name") or "General"
                category = clean_category_name(raw_category)

                # Use existing ID or generate new one
                ch_id = ch.get("id") or ch.get("stream_id") or channel_id_counter

                channels.append({
                    "id": ch_id,
                    "name": name,
                    "logo": logo,
                    "url": stream_url,
                    "category": category,
                    "epg_channel_id": ch.get("epg_channel_id", ""),
                    "added": ch.get("added", ""),
                    "category_id": ch.get("category_id", "")
                })

                channel_id_counter += 1

        except Exception as e:
            print(f"[CHANNELS] Error loading source {source}: {e}")

    print(f"[CHANNELS] Loaded {len(channels)} channels")
    return channels

# ================== ROUTES ==================

@app.route('/<any(live,movie,series):_type>/<username>/<password>/<int:stream_id>')
@app.route('/<any(live,movie,series):_type>/<username>/<password>/<int:stream_id>.<ext>')
def redirect_stream(_type, username, password, stream_id, ext=None):
    """Redirect to actual stream URL"""
    if username != USERNAME or password != PASSWORD:
        return jsonify({"error": "Invalid credentials"}), 401

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

@app.route("/player_api.php")
def player_api():
    """Main API endpoint for IPTV player apps"""
    username = request.args.get("username", "")
    password = request.args.get("password", "")
    action = request.args.get("action", "")

    if username != USERNAME or password != PASSWORD:
        return jsonify({"user_info": {"auth": 0, "status": "Disabled"}})

    user_info = {
        "username": username,
        "password": password,
        "status": "Active",
        "auth": 1,
        "exp_date": EXP_DATE,
        "is_trial": "0",
        "active_cons": "1",
        "max_connections": "10",
        "allowed_output_formats": ["m3u8", "mp4", "mpd"],
        "message": ""
    }

    if not action:
        return jsonify({"user_info": user_info, "server_info": {"timestamp_now": int(datetime.now().timestamp())}})

    # VOD Categories
    if action == "get_vod_categories":
        movies = load_movies()
        unique_cats = sorted(set(m["category"] for m in movies))
        return jsonify([{"category_id": str(i + 1), "category_name": cat, "parent_id": 0} 
                       for i, cat in enumerate(unique_cats)])

    # VOD Streams
    if action == "get_vod_streams":
        movies = load_movies()
        unique_cats = sorted(set(m["category"] for m in movies))
        cat_map = {cat: str(i + 1) for i, cat in enumerate(unique_cats)}
        result = []
        category_id = request.args.get("category_id")

        for m in movies:
            if category_id and cat_map.get(m["category"]) != category_id:
                continue

            genre_str = ", ".join(m["genre"]) if isinstance(m["genre"], list) else str(m["genre"] or "")
            cast_str = ", ".join(m["cast"]) if isinstance(m["cast"], list) else str(m["cast"] or "")

            movie_entry = {
                "stream_id": m["id"],
                "num": m["id"],
                "name": m["title"],
                "title": m["title"],
                "stream_icon": m["cover"],
                "cover": m["cover"],
                "cover_big": m["banner"],
                "backdrop_path": [m["banner"]] if m["banner"] else [],
                "rating": str(m["rating"]),
                "rating_5based": str(float(m["rating"]) / 2) if m["rating"] != "0.0" else "0.0",
                "plot": m["plot"],
                "overview": m["plot"],
                "cast": cast_str,
                "director": str(m["director"]),
                "genre": genre_str,
                "releasedate": m["year"],
                "year": m["year"],
                "duration": m.get("duration", ""),
                "country": m.get("country", "Morocco"),
                "category_id": cat_map.get(m["category"], "1"),
                "container_extension": "mp4",
                "stream_type": "movie",
                "tmdb_id": str(m.get("tmdb_id") or m["id"])
            }
            result.append(movie_entry)

        return jsonify(result)

    # VOD Info
    if action == "get_vod_info":
        try:
            vod_id = int(request.args.get("vod_id", 0))
        except:
            return jsonify({"info": {}, "movie_data": {}})

        movies = load_movies()
        for m in movies:
            if m.get("id") == vod_id:
                genre_str = ", ".join(m["genre"]) if isinstance(m["genre"], list) else ""
                cast_str = ", ".join(m["cast"]) if isinstance(m["cast"], list) else ""

                return jsonify({
                    "info": {
                        "name": m["title"],
                        "cover": m["cover"],
                        "cover_big": m["banner"],
                        "backdrop_path": [m["banner"]] if m["banner"] else [],
                        "plot": m["plot"],
                        "overview": m["plot"],
                        "cast": cast_str,
                        "director": str(m["director"]),
                        "genre": genre_str,
                        "releaseDate": s["year"],
                        "year": s["year"],
                        "rating": s["rating"],
                        "tmdb_id": str(s.get("tmdb_id") or s["id"])
                    },
                    "episodes": episodes_by_season
                })

        return jsonify({"info": {}, "episodes": {}, "seasons": []})

    # Live Categories
    if action == "get_live_categories":
        channels = load_channels()
        unique_cats = sorted(set(ch["category"] for ch in channels))
        return jsonify([{"category_id": str(i + 2000), "category_name": cat, "parent_id": 0} 
                       for i, cat in enumerate(unique_cats)])

    # Live Streams
    if action == "get_live_streams":
        channels = load_channels()
        unique_cats = sorted(set(ch["category"] for ch in channels))
        cat_map = {cat: str(i + 2000) for i, cat in enumerate(unique_cats)}
        result = []
        category_id = request.args.get("category_id")

        for ch in channels:
            if category_id and cat_map.get(ch["category"]) != category_id:
                continue

            result.append({
                "num": ch["id"],
                "name": ch["name"],
                "stream_type": "live",
                "stream_id": ch["id"],
                "stream_icon": ch["logo"],
                "epg_channel_id": ch.get("epg_channel_id", ""),
                "added": ch.get("added", ""),
                "category_id": cat_map.get(ch["category"], "2000"),
                "custom_sid": "",
                "tv_archive": 0,
                "direct_source": "",
                "tv_archive_duration": 0
            })

        return jsonify(result)

    return jsonify([])

# ================== RELOAD ENDPOINT ==================
@app.route("/api/reload")
def reload_sources():
    """Reload sources from configuration files"""
    global MOVIE_SOURCES, SERIES_SOURCES, CHANNEL_SOURCES
    
    MOVIE_SOURCES, SERIES_SOURCES, CHANNEL_SOURCES = load_sources_from_config()
    
    # Clear caches to force reload
    load_movies.cache_clear()
    load_series.cache_clear()
    load_channels.cache_clear()
    
    return jsonify({
        "status": "success",
        "movies": len(MOVIE_SOURCES),
        "series": len(SERIES_SOURCES),
        "channels": len(CHANNEL_SOURCES)
    })

# ================== M3U & HOME ==================
@app.route("/api/export/m3u")
def export_m3u():
    """Export channels as M3U playlist"""
    channels = load_channels()
    base_url = f"http://{request.host}"
    lines = ["#EXTM3U"]
    for c in channels:
        lines.append(f'#EXTINF:-1 tvg-id="{c.get("epg_channel_id", "")}" tvg-logo="{c.get("logo", "")}" group-title="{safe_strip(c.get("category", "General"))}",{safe_strip(c["name"])}')
        lines.append(f'{base_url}/live/{USERNAME}/{PASSWORD}/{c["id"]}')
    return "\n".join(lines), 200, {"Content-Type": "application/x-mpegURL"}

@app.route("/")
def index():
    """Homepage with content showcase"""
    hero_background = "https://i.etsystatic.com/48715412/r/il/0a1d6c/6945520988/il_fullxfull.6945520988_ivg3.jpg"

    # Get sample content
    movies = load_movies()[:8]
    series = load_series()[:8]
    channels = load_channels()[:8]

    featured_movies = [{"title": m["title"], "cover": m["cover"]} for m in movies]
    featured_series = [{"title": s["title"], "cover": s["cover"]} for s in series]
    featured_channels = [{"name": ch["name"], "logo": ch["logo"]} for ch in channels]

    movie_categories = sorted(set(m["category"] for m in load_movies()))
    series_categories = sorted(set(s["category"] for s in load_series()))
    channel_categories = sorted(set(ch["category"] for ch in load_channels()))

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forja VOD - Premium Moroccan & Arabic Entertainment</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 0; 
            background: #0a0a1f; 
            color: white; 
        }}
        .hero {{ 
            background: linear-gradient(to bottom, rgba(0,0,0,0.7), rgba(0,0,0,0.3)), url('{hero_background}') center/cover; 
            text-align: center; 
            padding: 150px 20px; 
        }}
        .hero h1 {{ font-size: 4em; margin: 0; }}
        .hero p {{ font-size: 1.8em; margin: 10px 0; }}
        .btn {{ 
            background: #007bff; 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 1.2em; 
            text-decoration: none; 
            display: inline-block;
        }}
        .section {{ padding: 60px 20px; text-align: center; }}
        .section h2 {{ font-size: 3em; margin-bottom: 20px; }}
        .section p.subtext {{ font-size: 1.2em; margin-bottom: 30px; }}
        .grid {{ 
            display: flex; 
            flex-wrap: wrap; 
            justify-content: center; 
            gap: 15px; 
        }}
        .card {{ 
            width: 150px; 
            background: rgba(255,255,255,0.1); 
            border-radius: 8px; 
            overflow: hidden; 
            transition: transform 0.3s; 
        }}
        .card:hover {{ transform: scale(1.05); }}
        .card img {{ width: 100%; height: auto; }}
        .card p {{ padding: 10px; margin: 0; font-size: 0.9em; }}
        .movies {{ background: #ff851b; color: #001f3f; }}
        .series {{ background: #001f3f; }}
        .channels {{ background: linear-gradient(to bottom, #0074d9, #001f3f); }}
        .categories {{ background: #001f3f; }}
        .cat-list {{ list-style: none; padding: 0; display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; }}
        .cat-list li {{ background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 20px; }}
        .footer {{ background: #000; padding: 40px 20px; text-align: center; }}
        .footer a {{ color: white; text-decoration: none; margin: 0 10px; }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>A Mountain of Entertainment</h1>
        <p>Thousands of movies, series, and live channels.</p>
        <a href="/player_api.php?username=test&password=test" class="btn">Try It Free</a>
    </div>

    <div class="section movies">
        <h2>Blockbuster Movies</h2>
        <p class="subtext">Big hits, new releases, fan favorites.</p>
        <div class="grid">
            {"".join(f'<div class="card"><img src="{m["cover"]}" alt="{m["title"]}"><p>{m["title"]}</p></div>' for m in featured_movies)}
        </div>
    </div>

    <div class="section series">
        <h2>Premium Series</h2>
        <p class="subtext">Top-rated drama and thriller series.</p>
        <div class="grid">
            {"".join(f'<div class="card"><img src="{s["cover"]}" alt="{s["title"]}"><p>{s["title"]}</p></div>' for s in featured_series)}
        </div>
    </div>

    <div class="section channels">
        <h2>Live Channels</h2>
        <p class="subtext">Watch your favorite channels live.</p>
        <div class="grid">
            {"".join(f'<div class="card"><img src="{c["logo"]}" alt="{c["name"]}" style="object-fit: contain; height: 150px;"><p>{c["name"]}</p></div>' for c in featured_channels)}
        </div>
        <a href="/api/export/m3u" class="btn" style="margin-top: 20px;">Download M3U Playlist</a>
    </div>

    <div class="section categories">
        <h2>Browse by Category</h2>
        <p class="subtext">Explore our content by categories.</p>
        <h3>Movies</h3>
        <ul class="cat-list">
            {"".join(f'<li>{cat}</li>' for cat in movie_categories)}
        </ul>
        <h3>Series</h3>
        <ul class="cat-list">
            {"".join(f'<li>{cat}</li>' for cat in series_categories)}
        </ul>
        <h3>Live Channels</h3>
        <ul class="cat-list">
            {"".join(f'<li>{cat}</li>' for cat in channel_categories)}
        </ul>
    </div>

    <div class="footer">
        <p>&copy; 2026 Forja VOD. All rights reserved.</p>
        <p>
            <a href="/player_api.php?username=test&password=test&action=get_vod_categories">VOD Categories</a> | 
            <a href="/player_api.php?username=test&password=test&action=get_vod_streams">VOD Streams</a> | 
            <a href="/player_api.php?username=test&password=test&action=get_series_categories">Series Categories</a> | 
            <a href="/player_api.php?username=test&password=test&action=get_series">Series List</a> | 
            <a href="/player_api.php?username=test&password=test&action=get_live_categories">Live Categories</a> | 
            <a href="/player_api.php?username=test&password=test&action=get_live_streams">Live Streams</a> | 
            <a href="/api/reload">Reload Sources</a>
        </p>
    </div>
</body>
</html>
    """
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
