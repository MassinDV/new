"""Data loading and processing for movies, series, and channels"""

import json
import os
import re
import requests
import urllib3
from functools import lru_cache
from urllib.parse import quote
from config import SOURCE_CONFIG_URLS, TMDB_API_KEY, M3U_SOURCES

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def safe_strip(value):
    """Safely strip whitespace from strings"""
    return (value or "").strip()


def clean_category_name(name):
    """Clean category names for better display"""
    if not name:
        return "General"
    name = name.replace('_', ' ')
    name = re.sub(r'\.(json|JSON)$', '', name)
    return name.strip().title()


def get_category_from_source(source_dict, data=None):
    """Extract and clean category name from source or data"""
    if data and isinstance(data, dict):
        if "Category" in data:
            return clean_category_name(data["Category"])
    
    if data and isinstance(data, list) and len(data) > 0:
        first_item = data[0]
        if isinstance(first_item, dict) and "Category" in first_item:
            return clean_category_name(first_item["Category"])
    
    if data and isinstance(data, dict):
        if "channels" in data and isinstance(data["channels"], list) and len(data["channels"]) > 0:
            first_channel = data["channels"][0]
            if "category" in first_channel:
                return clean_category_name(first_channel["category"])
    
    filename = source_dict.get("path") or source_dict.get("url", "")
    base = os.path.basename(filename)
    if '?' in base:
        base = base.split('?')[0]
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


def load_sources_from_config():
    """Load source URLs from external configuration files"""
    movie_sources = []
    series_sources = []
    channel_sources = []
    
    try:
        resp = requests.get(SOURCE_CONFIG_URLS["json"], timeout=20)
        resp.raise_for_status()
        config = resp.json()
        
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
    
    try:
        resp = requests.get(SOURCE_CONFIG_URLS["txt"], timeout=20)
        resp.raise_for_status()
        content = resp.text
        
        current_section = None
        for line in content.split('\n'):
            line = line.strip()
            
            if "MOVIE SOURCES" in line.upper():
                current_section = "movies"
                continue
            elif "SERIES" in line.upper() and "SOURCES" in line.upper():
                current_section = "series"
                continue
            elif "CHANNEL SOURCES" in line.upper():
                current_section = "channels"
                continue
            
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
    
    print("[CONFIG] Warning: Could not load any sources from config files")
    return [], [], []


MOVIE_SOURCES, SERIES_SOURCES, CHANNEL_SOURCES = load_sources_from_config()


@lru_cache(maxsize=500)
def fetch_tmdb_details(tmdb_id=None, title=None, is_movie=True):
    """Fetch additional metadata from TMDb API"""
    media_type = "movie" if is_movie else "tv"
    http = urllib3.PoolManager()
    
    try:
        if tmdb_id and str(tmdb_id).isdigit():
            details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_API_KEY}"
            details_resp = http.request('GET', details_url, timeout=5.0)
            
            if details_resp.status != 200:
                print(f"[TMDb] Failed to fetch {media_type} {tmdb_id}: HTTP {details_resp.status}")
                return None
                
            details = json.loads(details_resp.data.decode('utf-8'))
            
            credits = {}
            credits_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/credits?api_key={TMDB_API_KEY}"
            credits_resp = http.request('GET', credits_url, timeout=5.0)
            if credits_resp.status == 200:
                credits = json.loads(credits_resp.data.decode('utf-8'))
            
            print(f"[TMDb] Fetched {media_type} {tmdb_id}: {details.get('title') or details.get('name')}")
            
            return {
                'tmdb_id': tmdb_id,
                'details': details,
                'credits': credits
            }
        
        if not title:
            return None
            
        search_url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={TMDB_API_KEY}&query={quote(title)}"
        resp = http.request('GET', search_url, timeout=5.0)
        
        if resp.status != 200:
            return None
        
        data = json.loads(resp.data.decode('utf-8'))
        if not data.get('results'):
            print(f"[TMDb] No results found for '{title}'")
            return None
        
        first = data['results'][0]
        found_tmdb_id = first['id']
        
        return fetch_tmdb_details(tmdb_id=found_tmdb_id, is_movie=is_movie)
        
    except Exception as e:
        print(f"[TMDb] Error for '{title or tmdb_id}': {e}")
        return None


@lru_cache(maxsize=1)
def load_movies(_cache_key=None):
    """Load and process all movie data"""
    from m3u_parser import load_m3u_movies
    
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

            category = get_category_from_source(source, raw_data)
            movie_list = raw_data if isinstance(raw_data, list) else raw_data.get("movies", raw_data.get("data", []))

            for item in movie_list:
                if "Episodes" in item:
                    continue
                if "Movie" not in item:
                    continue

                info = item.get("Info", {}) or {}
                movie_data = item.get("Movie", {})

                cuid = movie_data.get("CUID") or info.get("CUID") or item.get("CUID")
                if not cuid or not str(cuid).isdigit():
                    continue

                movie_id = int(cuid)
                if movie_id in seen_ids:
                    continue
                seen_ids.add(movie_id)

                item_category = item.get("Category")
                if item_category:
                    item_category = clean_category_name(item_category)
                final_category = item_category or category

                title = safe_strip(item.get("Title") or item.get("Name") or "Untitled")
                
                tmdb_id = info.get("tmdb_id")
                needs_tmdb = not info.get("Year") or not info.get("Genres") or not info.get("Rating")
                
                if tmdb_id and needs_tmdb:
                    tmdb_data = fetch_tmdb_details(tmdb_id=tmdb_id, is_movie=True)
                    if tmdb_data:
                        details = tmdb_data.get('details', {})
                        credits = tmdb_data.get('credits', {})
                        
                        if not info.get("Year"):
                            release_date = details.get('release_date', '')
                            if release_date:
                                info['Year'] = release_date.split('-')[0]
                        
                        if not info.get("Genres"):
                            genres = details.get('genres', [])
                            if genres:
                                info['Genres'] = ', '.join([g['name'] for g in genres])
                        
                        if not info.get("Rating"):
                            rating = details.get('vote_average', 0)
                            if rating:
                                info['Rating'] = str(rating)
                        
                        if not item.get("Synopsis"):
                            overview = details.get('overview', '')
                            if overview:
                                item['Synopsis'] = overview
                        
                        if not info.get("Cast"):
                            cast_list = credits.get('cast', [])[:5]
                            if cast_list:
                                info['Cast'] = ', '.join([actor['name'] for actor in cast_list])
                        
                        if not info.get("Director"):
                            crew = credits.get('crew', [])
                            directors = [person['name'] for person in crew if person.get('job') == 'Director']
                            if directors:
                                info['Director'] = directors[0]
                        
                        if not item.get("VerticalImage"):
                            poster_path = details.get('poster_path')
                            if poster_path:
                                item['VerticalImage'] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                        
                        if not item.get("PosterImage"):
                            backdrop_path = details.get('backdrop_path')
                            if backdrop_path:
                                item['PosterImage'] = f"https://image.tmdb.org/t/p/original{backdrop_path}"
                        
                        if not info.get("Duration"):
                            runtime = details.get('runtime')
                            if runtime:
                                info['Duration'] = f"{runtime} min"

                plot = safe_strip(item.get("Synopsis") or info.get("Overview") or "No description available.")
                cover = safe_strip(item.get("VerticalImage") or item.get("PosterImage") or "")
                banner = safe_strip(item.get("PosterImage") or item.get("VerticalImage") or cover)
                stream_url = safe_strip(movie_data.get("streamUrl") or info.get("streamUrl") or info.get("stream_url") or "")

                year = str(info.get("Year") or "").strip()
                if not year and '(' in title and ')' in title:
                    m = re.search(r'\((\d{4})\)', title)
                    if m:
                        year = m.group(1)

                genres = normalize_genre(info.get("Genres") or info.get("Genre"))
                if not genres and final_category:
                    genres = [final_category]

                cast = clean_cast(info.get("Cast") or info.get("Actors"))
                director = safe_strip(info.get("Director") or "Unknown")

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
                    "category": final_category,
                    "tmdb_id": tmdb_id
                })

        except Exception as e:
            print(f"[MOVIES] Error loading source {source}: {e}")

    try:
        m3u_sources = M3U_SOURCES.get("movies", [])
        if m3u_sources:
            m3u_movies = load_m3u_movies(m3u_sources)
            
            for m3u_movie in m3u_movies:
                movie_id = m3u_movie.get('id')
                if movie_id not in seen_ids:
                    movies.append(m3u_movie)
                    seen_ids.add(movie_id)
    except Exception as e:
        print(f"[MOVIES] Error loading M3U sources: {e}")

    print(f"[MOVIES] Loaded {len(movies)} unique entries")
    return movies


@lru_cache(maxsize=1)
def load_series(_cache_key=None):
    """Load and process all series data"""
    from m3u_parser import load_m3u_series
    
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

            category = get_category_from_source(source, raw)
            series_data = raw if isinstance(raw, list) else raw.get("series", raw.get("data", []))

            for item in series_data:
                episodes = item.get("Episodes", [])
                if not episodes:
                    continue
                if "Movie" in item:
                    continue

                info = item.get("Info", {}) or {}
                title = safe_strip(item.get("Title") or item.get("Name") or "Unknown Series")

                if title in seen_titles:
                    continue
                seen_titles[title] = True

                tmdb_id = info.get("tmdb_id")
                needs_tmdb = not info.get("Year") or not info.get("Genres") or not info.get("Rating")
                
                if tmdb_id and needs_tmdb:
                    tmdb_data = fetch_tmdb_details(tmdb_id=tmdb_id, is_movie=False)
                    if tmdb_data:
                        details = tmdb_data.get('details', {})
                        credits = tmdb_data.get('credits', {})
                        
                        if not info.get("Year"):
                            first_air = details.get('first_air_date', '')
                            if first_air:
                                info['Year'] = first_air.split('-')[0]
                        
                        if not info.get("Genres"):
                            genres = details.get('genres', [])
                            if genres:
                                info['Genres'] = ', '.join([g['name'] for g in genres])
                        
                        if not info.get("Rating"):
                            rating = details.get('vote_average', 0)
                            if rating:
                                info['Rating'] = str(rating)
                        
                        if not item.get("Synopsis"):
                            overview = details.get('overview', '')
                            if overview:
                                item['Synopsis'] = overview
                        
                        if not info.get("Cast"):
                            cast_list = credits.get('cast', [])[:5]
                            if cast_list:
                                info['Cast'] = ', '.join([actor['name'] for actor in cast_list])
                        
                        if not info.get("Director"):
                            crew = credits.get('crew', [])
                            creators = details.get('created_by', [])
                            if creators:
                                info['Director'] = creators[0]['name']
                        
                        if not item.get("VerticalImage"):
                            poster_path = details.get('poster_path')
                            if poster_path:
                                item['VerticalImage'] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                        
                        if not item.get("PosterImage"):
                            backdrop_path = details.get('backdrop_path')
                            if backdrop_path:
                                item['PosterImage'] = f"https://image.tmdb.org/t/p/original{backdrop_path}"

                plot = safe_strip(item.get("Synopsis") or info.get("Overview") or "")
                cover = safe_strip(item.get("VerticalImage") or "")
                banner = safe_strip(item.get("PosterImage") or "")

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
                    'tmdb_id': tmdb_id
                }
                series_id_counter += 1

                season_map = {}
                for ep in episodes:
                    ep_num_str = ep.get("Episode", "")
                    match = re.search(r'E(\d+)', ep_num_str, re.I)
                    ep_num = int(match.group(1)) if match else None

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

    try:
        m3u_sources = M3U_SOURCES.get("series", [])
        if m3u_sources:
            m3u_series = load_m3u_series(m3u_sources)
            
            for m3u_show in m3u_series:
                title = m3u_show.get('title')
                if title not in seen_titles:
                    series_list.append(m3u_show)
                    seen_titles[title] = True
    except Exception as e:
        print(f"[SERIES] Error loading M3U sources: {e}")

    print(f"[SERIES] Loaded {len(series_list)} series")
    return series_list


@lru_cache(maxsize=1)
def load_channels(_cache_key=None):
    """Load and process all channel data"""
    from m3u_parser import load_m3u_channels
    
    channels = []
    channel_id_counter = 1
    seen_ids = set()

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

            channel_list = raw_data if isinstance(raw_data, list) else raw_data.get("channels", [])

            for ch in channel_list:
                name = safe_strip(ch.get("name") or ch.get("channel_name") or "Unknown Channel")
                logo = safe_strip(ch.get("logo") or ch.get("stream_icon") or "")
                stream_url = safe_strip(ch.get("stream_url") or ch.get("url") or "")
                
                raw_category = ch.get("category") or ch.get("category_name") or "General"
                category = clean_category_name(raw_category)

                ch_id = ch.get("id") or ch.get("stream_id") or channel_id_counter
                
                if ch_id not in seen_ids:
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
                    seen_ids.add(ch_id)
                    channel_id_counter += 1

        except Exception as e:
            print(f"[CHANNELS] Error loading source {source}: {e}")

    try:
        m3u_sources = M3U_SOURCES.get("live", [])
        if m3u_sources:
            m3u_channels = load_m3u_channels(m3u_sources)
            
            for m3u_ch in m3u_channels:
                ch_id = m3u_ch.get('id')
                if ch_id not in seen_ids:
                    channels.append(m3u_ch)
                    seen_ids.add(ch_id)
    except Exception as e:
        print(f"[CHANNELS] Error loading M3U sources: {e}")

    print(f"[CHANNELS] Loaded {len(channels)} channels")
    return channels