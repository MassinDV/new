"""API route handlers for IPTV player interface"""

from flask import request, jsonify
from datetime import datetime
from data_loader import load_movies, load_series, load_channels
from auth import check_credentials, get_user_info


def handle_player_api():
    """Main API endpoint for IPTV player apps"""
    username = request.args.get("username", "")
    password = request.args.get("password", "")
    action = request.args.get("action", "")

    if not check_credentials(username, password):
        return jsonify({"user_info": {"auth": 0, "status": "Disabled"}})

    user_info = get_user_info(username)

    if not action:
        return jsonify({
            "user_info": user_info,
            "server_info": {"timestamp_now": int(datetime.now().timestamp())}
        })

    # VOD Categories
    if action == "get_vod_categories":
        movies = load_movies()
        unique_cats = sorted(set(m["category"] for m in movies))
        return jsonify([
            {"category_id": str(i + 1), "category_name": cat, "parent_id": 0}
            for i, cat in enumerate(unique_cats)
        ])

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
                        "releasedate": m["year"],
                        "year": m["year"],
                        "rating": str(m["rating"]),
                        "duration": m.get("duration", ""),
                        "country": m.get("country", "Morocco"),
                        "tmdb_id": str(m.get("tmdb_id") or m["id"])
                    },
                    "movie_data": {
                        "stream_id": m["id"],
                        "name": m["title"],
                        "container_extension": "mp4",
                        "custom_sid": str(m["id"])
                    }
                })

        return jsonify({"info": {}, "movie_data": {}})

    # Series Categories
    if action == "get_series_categories":
        series_list = load_series()
        unique_cats = sorted(set(s["category"] for s in series_list))
        return jsonify([
            {"category_id": str(i + 1000), "category_name": cat, "parent_id": 0}
            for i, cat in enumerate(unique_cats)
        ])

    # Series List
    if action == "get_series":
        series_list = load_series()
        unique_cats = sorted(set(s["category"] for s in series_list))
        cat_map = {cat: str(i + 1000) for i, cat in enumerate(unique_cats)}
        result = []

        for s in series_list:
            genre_str = ", ".join(s["genre"]) if isinstance(s["genre"], list) else ""
            cast_str = ", ".join(s["cast"]) if isinstance(s["cast"], list) else ""

            result.append({
                "series_id": s["id"],
                "num": s["id"],
                "name": s["title"],
                "title": s["title"],
                "cover": s["cover"],
                "cover_big": s["banner"],
                "backdrop_path": [s["banner"]] if s["banner"] else [],
                "plot": s["plot"],
                "overview": s["plot"],
                "cast": cast_str,
                "director": s.get("director", ""),
                "genre": genre_str,
                "releaseDate": s["year"],
                "year": s["year"],
                "rating": s["rating"],
                "rating_5based": str(float(s["rating"]) / 2) if s["rating"] != "0" else "0.0",
                "category_id": cat_map.get(s["category"], "1000"),
                "last_modified": "0",
                "tmdb_id": str(s.get("tmdb_id") or s["id"])
            })

        return jsonify(result)

    # Series Info
    if action == "get_series_info":
        try:
            series_id = int(request.args.get("series_id", 0))
        except:
            return jsonify({"info": {}, "episodes": {}, "seasons": []})

        series_list = load_series()
        for s in series_list:
            if s.get("id") == series_id:
                episodes_by_season = {}

                for season in s.get("seasons", []):
                    season_num = str(season.get("season", 1))
                    eps = []

                    for ep in season.get("episodes", []):
                        ep_id = ep.get("id")
                        thumb = ep.get("thumbnail", "")

                        eps.append({
                            "id": str(ep_id),
                            "episode_num": ep["episode"],
                            "title": ep["title"],
                            "name": ep["title"],
                            "container_extension": "mp4",
                            "info": {
                                "name": ep["title"],
                                "overview": ep.get("plot", ""),
                                "plot": ep.get("plot", ""),
                                "movie_image": thumb,
                                "cover": thumb
                            },
                            "custom_sid": str(ep_id),
                            "season": season_num,
                            "direct_source": ""
                        })

                    episodes_by_season[season_num] = eps

                genre_str = ", ".join(s["genre"]) if isinstance(s["genre"], list) else ""
                cast_str = ", ".join(s["cast"]) if isinstance(s["cast"], list) else ""

                return jsonify({
                    "seasons": [
                        {"season_number": int(sn), "name": f"Season {sn}", "episode_count": len(eps)}
                        for sn, eps in episodes_by_season.items()
                    ],
                    "info": {
                        "name": s["title"],
                        "cover": s["cover"],
                        "cover_big": s["banner"],
                        "backdrop_path": [s["banner"]] if s["banner"] else [],
                        "plot": s["plot"],
                        "overview": s["plot"],
                        "cast": cast_str,
                        "director": s.get("director", ""),
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
        return jsonify([
            {"category_id": str(i + 2000), "category_name": cat, "parent_id": 0}
            for i, cat in enumerate(unique_cats)
        ])

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