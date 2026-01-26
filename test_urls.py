"""Test script to verify direct URLs are being returned correctly"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:5000"
USERNAME = "test"
PASSWORD = "test"

def test_api_endpoint(action, params=None):
    """Test an API endpoint and print results"""
    url = f"{BASE_URL}/player_api.php"
    params = params or {}
    params.update({
        "username": USERNAME,
        "password": PASSWORD,
        "action": action
    })
    
    print(f"\n{'='*80}")
    print(f"Testing: {action}")
    print(f"{'='*80}")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            # Show first 3 items
            for i, item in enumerate(data[:3]):
                print(f"\nItem {i+1}:")
                print(f"  Name: {item.get('name') or item.get('title', 'N/A')}")
                
                # Check for direct URLs
                direct_source = item.get('direct_source', 'NOT FOUND')
                stream_url = item.get('stream_url', 'NOT FOUND')
                
                print(f"  direct_source: {direct_source[:100]}..." if len(direct_source) > 100 else f"  direct_source: {direct_source}")
                print(f"  stream_url: {stream_url[:100]}..." if len(stream_url) > 100 else f"  stream_url: {stream_url}")
                
                # Verify it's a direct URL (starts with http/https)
                if direct_source.startswith('http'):
                    print(f"  ✅ DIRECT URL FOUND")
                elif direct_source.startswith('/live') or direct_source.startswith('/movie'):
                    print(f"  ❌ SERVER REDIRECT URL (should be direct)")
                else:
                    print(f"  ⚠️  NO URL FOUND")
        
        elif isinstance(data, dict):
            print(json.dumps(data, indent=2)[:500])
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_m3u_export():
    """Test M3U export"""
    print(f"\n{'='*80}")
    print(f"Testing: M3U Export (Direct URLs)")
    print(f"{'='*80}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/export/m3u?output_format=direct")
        response.raise_for_status()
        content = response.text
        
        lines = content.split('\n')
        print(f"\nTotal lines: {len(lines)}")
        
        # Show first 10 lines
        print("\nFirst 10 lines:")
        for i, line in enumerate(lines[:10]):
            if line.startswith('http'):
                print(f"  ✅ Line {i+1}: {line[:80]}...")
            else:
                print(f"  Line {i+1}: {line[:80]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     FORJA VOD - Direct URL Verification                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Test live streams
    test_api_endpoint("get_live_streams")
    
    # Test movies
    test_api_endpoint("get_vod_streams")
    
    # Test specific movie info
    test_api_endpoint("get_vod_info", {"vod_id": "14607"})
    
    # Test series info
    test_api_endpoint("get_series_info", {"series_id": "10000"})
    
    # Test M3U export
    test_m3u_export()
    
    print(f"\n{'='*80}")
    print("✅ Testing complete!")
    print(f"{'='*80}\n")
    
    print("""
HOW TO USE:
-----------
1. IPTV Players will now receive direct URLs automatically
2. No need to keep the server running for playback
3. The URLs look like:
   - Movies: https://clvod.itworkscdn.net/smcvod/drm/pd/smc/...mp4
   - Channels: https://stream-lb.livemedia.ma/aflam/hls/master.m3u8

TROUBLESHOOTING:
----------------
- If you see "/live/test/test/1.ts" in logs, the player is using old cached data
- Clear your IPTV app cache or re-add the playlist
- Or use: http://localhost:5000/api/cache/clear to force refresh
    """)


if __name__ == "__main__":
    main()