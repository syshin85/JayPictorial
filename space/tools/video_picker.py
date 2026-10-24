#!/usr/bin/env python3
"""Hand-pick each item's YouTube video by looking at frames from the candidates.
(Same idea as train/tools/video_picker.py.)

  python3 tools/video_picker.py find [id ...]
      → collects up to 8 candidates per item into tools/videos.json; compare them at
        http://localhost:8000/tools/video_review.html (each shows frames from the start, middle and end)
  python3 tools/video_picker.py set mars:3 iss:0 ...
      → id:number picks that candidate and locks it into data/media.json

Videos must show the thing itself (the planet, or the machine working: launching, landing,
docking, driving, flying). Explosions, accidents, scary or conspiracy clips are filtered out.
"""
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_media as fm  # noqa: E402

OUT = Path(__file__).resolve().parent / "videos.json"
PER_ITEM = 8
MIN_SECONDS, MAX_SECONDS, IDEAL_SECONDS = 20, 300, 100

# never for a 6-year-old
UNSAFE_WORDS = ("explosion", "explode", "exploding", "explodes", "blow up", "blows up", "blew up", "rud", "boom",
                "fail", "failure", "fails", "crash", "crashes", "crashing", "충돌", "부딪", "disaster", "accident", "tragedy", "dead", "death",
                "died", "dies", "kill", "killed", "challenger", "columbia disaster", "scary", "creepy", "terrifying",
                "horror", "nightmare", "doom", "apocalypse", "end of the world", "destroy", "destroyed", "danger",
                "dangerous", "warning", "alien", "ufo", "hoax", "fake", "flat earth", "conspiracy", "secret",
                "폭발", "사고", "실패", "추락", "참사", "공포", "무서운", "외계인", "음모", "종말", "위험", "경고")
# not the thing itself (talk shows, news, games, toys, AI-made clips…)
OFF_TOPIC_WORDS = ("news", "뉴스", "interview", "인터뷰", "podcast", "reaction", "react", "review", "리뷰", "unboxing",
                   "lego", "레고", "toy", "장난감", "minecraft", "game", "게임", "kerbal", "ksp", "simulator", "roblox",
                   "drawing", "그리기", "song", "노래", "cartoon", "만화", "#shorts", "shorts", "ai generated",
                   "debate", "lecture", "강의", "explained", "theory", "documentary", "다큐", "live", "라이브",
                   "생중계", "ytn", "sbs", "kbs", "mbc", "mbn", "jtbc", "연합뉴스", "full broadcast", "replay", "webcast", "q&a", "press conference", "브리핑", "회견",
                   "asmr", "meditation", "music video", "1 hour", "10 hours", "sleep", "relaxing", "lofi", "ranking",
                   "top 10", "top 5", "vs", "comparison", "size comparison", "크기 비교", "what if", "만약", "could",
                   "명상", "수면", "funny", "prank", "meme", "tiktok", "trailer", "movie", "영화", "scene")
GOOD_CHANNELS = ("nasa", "jet propulsion", "jpl", "esa", "european space agency", "spacex", "kari", "항공우주연구원",
                 "jaxa", "space telescope science", "hubble", "webb", "eso", "goddard", "johnson space")


def has_word(text, word):
    """Substring match, but ASCII words must not be glued to other letters ("rud" ≠ "rudder")."""
    word = word.lower()
    if not word.isascii():
        return word in text
    return re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text) is not None


def search_youtube(query):
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query, "hl": "ko"})
    html = fm.get(url).decode("utf-8", "ignore")
    results = []
    for chunk in html.split('"videoRenderer":{"videoId":"')[1:]:
        vid = chunk[:11]
        title = re.search(r'"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"', chunk)
        length = re.search(r'"lengthText":\{.*?"simpleText":"([\d:]+)"', chunk[:20000])
        views = re.search(r'"viewCountText":\{"simpleText":"([^"]*)"', chunk[:20000])
        channel = re.search(r'"ownerText":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"', chunk[:20000])
        if title and length:
            secs = 0
            for p in length.group(1).split(":"):
                secs = secs * 60 + int(p)
            results.append({"youtube": vid, "title": json.loads(f'"{title.group(1)}"'), "seconds": secs,
                            "views": int(re.sub(r"\D", "", views.group(1)) or 0) if views else 0,
                            "channel": json.loads(f'"{channel.group(1)}"') if channel else ""})
    return results


def score_video(item, v):
    """None if the clip is unsuitable, otherwise higher = better."""
    title = v["title"].lower()
    if any(has_word(title, w) for w in UNSAFE_WORDS + OFF_TOPIC_WORDS):
        return None
    if not MIN_SECONDS <= v["seconds"] <= MAX_SECONDS:
        return None
    if not any(has_word(title, k) for k in item["videoMatch"]):
        return None
    score = -abs(v["seconds"] - IDEAL_SECONDS) / 30
    score += 2 * math.log10(v["views"] + 1)
    if any(c in v["channel"].lower() for c in GOOD_CHANNELS):
        score += 6
    return score


def embeddable(vid):
    try:
        fm.get("https://www.youtube.com/oembed?format=json&url=" +
               urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}"))
        return True
    except urllib.error.HTTPError:
        return False


def find(items):
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    for item in items:
        scored = {}
        for q in item["videoQueries"]:
            try:
                results = search_youtube(q)
            except Exception as e:
                print(f"   ! search failed: {e}")
                results = []
            for rank, v in enumerate(results):
                s = score_video(item, v)
                if s is not None and v["youtube"] not in scored:
                    scored[v["youtube"]] = (s - rank * 0.5, v)
            time.sleep(1)
        picked = []
        for _, v in sorted(scored.values(), key=lambda x: -x[0]):
            if embeddable(v["youtube"]):
                picked.append(v)
            if len(picked) >= PER_ITEM:
                break
        data[item["id"]] = {"name": item["name"], "candidates": picked}
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        print(f"{item['id']}: {len(picked)} candidates", flush=True)


def set_videos(picks):
    data = json.loads(OUT.read_text())
    media = json.loads(fm.MEDIA.read_text())
    for pick in picks:
        iid, n = pick.split(":")
        chosen = data[iid]["candidates"][int(n)]
        media.setdefault(iid, {})["video"] = {k: chosen[k] for k in ("youtube", "title", "seconds", "channel")}
        print(f"{iid}: {chosen['title']}")
    fm.MEDIA.write_text(json.dumps(media, ensure_ascii=False, indent=2) + "\n")


def main():
    cmd, *rest = sys.argv[1:]
    items = json.loads(fm.DATA.read_text())["items"]
    if cmd == "find":
        find([t for t in items if not rest or t["id"] in rest])
    elif cmd == "set":
        set_videos(rest)


if __name__ == "__main__":
    main()
