"""M3U file parser for channels, movies, and series"""

import re
import os
import requests


def parse_m3u_line(extinf_line):
    """Parse #EXTINF line to extract metadata"""
    metadata = {
        'cuid': None,
        'name': '',
        'logo': '',
        'group': '',
        'tvg_id': '',
        'tvg_chno': '',
        'tvg_type': ''
    }
    
    # Extract CUID
    cuid_match = re.search(r'CUID="(\d+)"', extinf_line)
    if cuid_match:
        metadata['cuid'] = int(cuid_match.group(1))
    
    # Extract tvg-name
    name_match = re.search(r'tvg-name="([^"]*)"', extinf_line)
    if name_match:
        metadata['name'] = name_match.group(1)
    
    # Extract tvg-logo
    logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line)
    if logo_match:
        metadata['logo'] = logo_match.group(1)
    
    # Extract group-title
    group_match = re.search(r'group-title="([^"]*)"', extinf_line)
    if group_match:
        metadata['group'] = group_match.group(1)
    
    # Extract tvg-id
    id_match = re.search(r'tvg-id="([^"]*)"', extinf_line)
    if id_match:
        metadata['tvg_id'] = id_match.group(1)
    
    # Extract tvg-chno
    chno_match = re.search(r'tvg-chno="([^"]*)"', extinf_line)
    if chno_match:
        metadata['tvg_chno'] = chno_match.group(1)
    
    # Extract tvg-type
    type_match = re.search(r'tvg-type="([^"]*)"', extinf_line)
    if type_match:
        metadata['tvg_type'] = type_match.group(1)
    
    # If no tvg-name, get name from end of line (after last comma)
    if not metadata['name']:
        name_match = re.search(r',(.+)$', extinf_line)
        if name_match:
            metadata['name'] = name_match.group(1).strip()
    
    return metadata


def extract_season_episode(name):
    """Extract season and episode numbers from name"""
    # Match patterns like "S01 E01", "S1E1", etc.
    pattern = r'S(\d+)\s*E(\d+)'
    match = re.search(pattern, name, re.IGNORECASE)
    
    if match:
        season = int(match.group(1))
        episode = int(match.group(2))
        # Remove season/episode info from name
        clean_name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
        return season, episode, clean_name
    
    return None, None, name


def load_m3u_file(source):
    """Load M3U file from local path or URL"""
    try:
        if source["type"] == "local":
            if not os.path.exists(source["path"]):
                print(f"[M3U] File not found: {source['path']}")
                return None
            with open(source["path"], 'r', encoding='utf-8') as f:
                content = f.read()
        elif source["type"] == "remote":
            resp = requests.get(source["url"], timeout=20)
            resp.raise_for_status()
            content = resp.text
        else:
            return None
        
        return content
    except Exception as e:
        print(f"[M3U] Error loading {source}: {e}")
        return None


def parse_m3u_channels(content):
    """Parse M3U content and extract live channels"""
    channels = []
    lines = content.split('\n')
    channel_id = 1
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for #EXTINF lines
        if line.startswith('#EXTINF'):
            metadata = parse_m3u_line(line)
            
            # Get the next non-empty line (should be the stream URL)
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith('#EXTVLCOPT')):
                i += 1
            
            if i < len(lines):
                stream_url = lines[i].strip()
                
                if stream_url and not stream_url.startswith('#'):
                    channels.append({
                        'id': metadata['cuid'] or channel_id,
                        'name': metadata['name'],
                        'logo': metadata['logo'],
                        'url': stream_url,
                        'category': metadata['group'] or 'General',
                        'epg_channel_id': metadata['tvg_id'],
                        'channel_number': metadata['tvg_chno'],
                        'added': '',
                        'category_id': ''
                    })
                    channel_id += 1
        
        i += 1
    
    return channels


def parse_m3u_movies(content):
    """Parse M3U content and extract movies"""
    movies = []
    lines = content.split('\n')
    movie_id = 1
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            metadata = parse_m3u_line(line)
            
            # Get the stream URL
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith('#EXTVLCOPT')):
                i += 1
            
            if i < len(lines):
                stream_url = lines[i].strip()
                
                if stream_url and not stream_url.startswith('#'):
                    # Extract year from name if present
                    year_match = re.search(r'\((\d{4})\)', metadata['name'])
                    year = year_match.group(1) if year_match else ''
                    
                    movies.append({
                        'id': metadata['cuid'] or movie_id,
                        'title': metadata['name'],
                        'plot': '',
                        'cover': metadata['logo'],
                        'banner': metadata['logo'],
                        'year': year,
                        'genre': [metadata['group']] if metadata['group'] else [],
                        'cast': [],
                        'director': '',
                        'rating': '0.0',
                        'duration': '',
                        'country': '',
                        'url': stream_url,
                        'category': metadata['group'] or 'Movies',
                        'tmdb_id': None
                    })
                    movie_id += 1
        
        i += 1
    
    return movies


def parse_m3u_series(content):
    """Parse M3U content and extract series with episodes"""
    series_dict = {}
    lines = content.split('\n')
    episode_id = 100000
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            metadata = parse_m3u_line(line)
            
            # Extract season and episode info
            season, episode, series_name = extract_season_episode(metadata['name'])
            
            if season is not None and episode is not None:
                # Get the stream URL
                i += 1
                while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith('#EXTVLCOPT')):
                    i += 1
                
                if i < len(lines):
                    stream_url = lines[i].strip()
                    
                    if stream_url and not stream_url.startswith('#'):
                        # Use series name as key
                        if series_name not in series_dict:
                            series_dict[series_name] = {
                                'id': len(series_dict) + 10000,
                                'title': series_name,
                                'cover': metadata['logo'],
                                'banner': metadata['logo'],
                                'plot': '',
                                'year': '',
                                'genre': [metadata['group']] if metadata['group'] else [],
                                'cast': [],
                                'director': '',
                                'rating': '0.0',
                                'category': metadata['group'] or 'Series',
                                'seasons': {},
                                'tmdb_id': None
                            }
                        
                        # Add episode to the series
                        series = series_dict[series_name]
                        if season not in series['seasons']:
                            series['seasons'][season] = []
                        
                        series['seasons'][season].append({
                            'id': metadata['cuid'] or episode_id,
                            'episode': episode,
                            'title': metadata['name'],
                            'plot': '',
                            'thumbnail': metadata['logo'],
                            'url': stream_url
                        })
                        episode_id += 1
        
        i += 1
    
    # Convert seasons dict to list format
    series_list = []
    for series in series_dict.values():
        seasons_list = []
        for season_num in sorted(series['seasons'].keys()):
            episodes = sorted(series['seasons'][season_num], key=lambda x: x['episode'])
            seasons_list.append({
                'season': season_num,
                'episode_count': len(episodes),
                'episodes': episodes
            })
        series['seasons'] = seasons_list
        series_list.append(series)
    
    return series_list


def load_m3u_channels(sources):
    """Load channels from multiple M3U sources"""
    channels = []
    
    for source in sources:
        content = load_m3u_file(source)
        if content:
            parsed_channels = parse_m3u_channels(content)
            channels.extend(parsed_channels)
            print(f"[M3U] Loaded {len(parsed_channels)} channels from {source.get('path') or source.get('url')}")
    
    print(f"[M3U] Total channels loaded: {len(channels)}")
    return channels


def load_m3u_movies(sources):
    """Load movies from multiple M3U sources"""
    movies = []
    
    for source in sources:
        content = load_m3u_file(source)
        if content:
            parsed_movies = parse_m3u_movies(content)
            movies.extend(parsed_movies)
            print(f"[M3U] Loaded {len(parsed_movies)} movies from {source.get('path') or source.get('url')}")
    
    print(f"[M3U] Total movies loaded: {len(movies)}")
    return movies


def load_m3u_series(sources):
    """Load series from multiple M3U sources"""
    series = []
    
    for source in sources:
        content = load_m3u_file(source)
        if content:
            parsed_series = parse_m3u_series(content)
            series.extend(parsed_series)
            print(f"[M3U] Loaded {len(parsed_series)} series from {source.get('path') or source.get('url')}")
    
    print(f"[M3U] Total series loaded: {len(series)}")
    return series