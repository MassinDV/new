"""Web page templates and rendering"""

from data_loader import load_movies, load_series, load_channels, safe_strip


def render_homepage():
    """Generate HTML for the homepage"""
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
            margin: 5px;
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
        .info-box {{ background: rgba(0,119,255,0.2); padding: 20px; margin: 20px auto; max-width: 800px; border-radius: 10px; border-left: 4px solid #007bff; }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>🏔️ A Mountain of Entertainment</h1>
        <p>Thousands of movies, series, and live channels.</p>
        <a href="/player_api.php?username=test&password=test" class="btn">Try It Free</a>
    </div>

    <div class="section movies">
        <h2>🎬 Blockbuster Movies</h2>
        <p class="subtext">Big hits, new releases, fan favorites.</p>
        <div class="grid">
            {"".join(f'<div class="card"><img src="{m["cover"]}" alt="{m["title"]}"><p>{m["title"]}</p></div>' for m in featured_movies)}
        </div>
    </div>

    <div class="section series">
        <h2>📺 Premium Series</h2>
        <p class="subtext">Top-rated drama and thriller series.</p>
        <div class="grid">
            {"".join(f'<div class="card"><img src="{s["cover"]}" alt="{s["title"]}"><p>{s["title"]}</p></div>' for s in featured_series)}
        </div>
    </div>

    <div class="section channels">
        <h2>📡 Live Channels</h2>
        <p class="subtext">Watch your favorite channels live.</p>
        <div class="info-box">
            <h3>📥 M3U Playlist Formats</h3>
            <p><strong>Direct URLs (Recommended):</strong> Stream directly without server dependency</p>
            <a href="/api/export/m3u?output_format=direct" class="btn">Download Direct M3U</a>
            <p style="margin-top: 15px;"><strong>Proxy URLs:</strong> Stream through this server (requires server running)</p>
            <a href="/api/export/m3u?output_format=proxy" class="btn">Download Proxy M3U</a>
        </div>
        <div class="grid">
            {"".join(f'<div class="card"><img src="{c["logo"]}" alt="{c["name"]}" style="object-fit: contain; height: 150px;"><p>{c["name"]}</p></div>' for c in featured_channels)}
        </div>
    </div>

    <div class="section categories">
        <h2>📂 Browse by Category</h2>
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
            <a href="/player_api.php?username=test&password=test&action=get_live_streams">Live Streams</a>
        </p>
    </div>
</body>
</html>
    """
    return html


def render_m3u_playlist(base_url, username, password, output_format="direct"):
    """Generate M3U playlist for live channels
    
    Args:
        base_url: Server base URL
        username: Username for authentication
        password: Password for authentication
        output_format: 'direct' for original URLs, 'proxy' for server URLs
    """
    channels = load_channels()
    lines = ["#EXTM3U"]
    
    for c in channels:
        lines.append(f'#EXTINF:-1 tvg-id="{c.get("epg_channel_id", "")}" tvg-logo="{c.get("logo", "")}" group-title="{safe_strip(c.get("category", "General"))}",{safe_strip(c["name"])}')
        
        # Choose URL format
        if output_format == "proxy":
            # Use server proxy URL
            lines.append(f'{base_url}/live/{username}/{password}/{c["id"]}')
        else:
            # Use direct URL (default)
            direct_url = c.get("url", "")
            if direct_url:
                lines.append(direct_url)
            else:
                # Fallback to proxy if no direct URL
                lines.append(f'{base_url}/live/{username}/{password}/{c["id"]}')
    
    return "\n".join(lines)