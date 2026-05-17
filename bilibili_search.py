#!/usr/bin/env python3
"""Search Bilibili for cooking tutorial videos matching a dish name."""
import requests
import time
import os
import threading

BASE_URL = "https://api.bilibili.com/x/web-interface/search/type"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

PROXY = os.environ.get("http_proxy") or "http://127.0.0.1:7890"
PROXIES = {"http": PROXY, "https": PROXY}

# Session singleton with cookie auto-init
_session = None
_session_lock = threading.Lock()


def _get_session():
    global _session
    if _session is not None:
        return _session
    with _session_lock:
        if _session is not None:
            return _session
        _session = requests.Session()
        _session.proxies = PROXIES
        try:
            _session.get("https://www.bilibili.com/", headers=HEADERS, timeout=15)
        except Exception:
            pass
        return _session


def search_video(dish_name, max_results=8):
    """
    Search Bilibili for cooking tutorial videos.
    Returns list of {bvid, title, play_count, duration, author, url, cover}.
    """
    query = f"{dish_name} 做法"
    params = {
        "search_type": "video",
        "keyword": query,
        "page": 1,
        "order": "totalrank",
    }

    try:
        s = _get_session()
        resp = s.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        data = resp.json()
    except Exception as e:
        print(f"  Bilibili API error: {e}")
        return []

    if data.get("code") != 0:
        print(f"  Bilibili code {data.get('code')}: {data.get('message')}")
        return []

    results = []
    for item in data.get("data", {}).get("result", [])[:max_results]:
        bvid = item.get("bvid", "")
        title_raw = (
            item.get("title", "")
            .replace('<em class="keyword">', "")
            .replace("</em>", "")
        )
        results.append(
            {
                "bvid": bvid,
                "title": title_raw,
                "play_count": item.get("play", 0),
                "duration": item.get("duration", ""),
                "author": item.get("author", ""),
                "url": f"https://www.bilibili.com/video/{bvid}",
                "cover": item.get("pic", ""),
                "description": item.get("description", ""),
            }
        )
        time.sleep(0.05)

    return results


def find_best_video(dish_name):
    """
    Find the best cooking tutorial video.
    Prefers: high views, 3-30 min duration, known food creators.
    """
    results = search_video(dish_name, max_results=8)
    if not results:
        return None

    candidates = []
    for r in results:
        play = r["play_count"]
        dur = r["duration"]
        parts = dur.split(":")
        total_seconds = 0
        if len(parts) == 2:
            total_seconds = int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            total_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

        score = play
        # Penalize very short (< 2 min) or very long (> 40 min)
        if total_seconds < 120:
            score *= 0.1
        elif total_seconds > 2400:
            score *= 0.3
        # Bonus for "教程" or "教学" in title
        title = r.get("title", "")
        if "教程" in title or "教学" in title or "家常" in title:
            score *= 1.5
        # Bonus for high quality
        if play > 100000:
            score *= 1.3

        candidates.append((score, r))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates else results[0]


if __name__ == "__main__":
    import sys, json
    dish = sys.argv[1] if len(sys.argv) > 1 else "宫保鸡丁"
    print(f"Searching: {dish}")
    video = find_best_video(dish)
    if video:
        print(json.dumps(video, ensure_ascii=False, indent=2))
    else:
        print("  No results")
