#!/usr/bin/env python3
"""Hand-pick each item's YouTube video by looking at frames from the candidates.
(Same idea as train/tools/video_picker.py.)

  python3 tools/video_picker.py find [id ...]
      → collects up to 8 candidates per item into tools/videos.json; compare them at
        http://localhost:8000/tools/video_review.html (each shows frames from the start, middle and end)
  python3 tools/video_picker.py set f1:3 bus:0 ...
      → id:number picks that candidate and locks it into data/media.json

Videos must show the aircraft itself, from outside, flying (takeoff, landing, flyby, airshow, water drop…).
Crashes, emergencies, weapons and war, cockpit/cabin clips, games, toys and cartoons are filtered out.
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
                "폭발", "사고", "실패", "추락", "참사", "공포", "무서운", "외계인", "음모", "종말", "위험", "경고",
                "chase", "pursuit", "police chase", "추격", "도주", "burning", "burns", "on fire", "flames", "blaze", "화재", "불타",
                "rollover", "roll over", "flips", "flipped", "wreck", "wrecked", "smash", "jump fail", "전복", "충격", "블랙박스",
                "road rage", "angry", "fight", "drunk", "arrest", "체포", "음주",
                "missile", "missiles", "bomb", "bombs", "bombing", "bomber", "war", "wars", "warfare", "combat", "battle", "attack",
                "strike", "strikes", "shot down", "shoot", "shooting", "gun", "guns", "gunfire", "weapon", "weapons", "firing", "rocket attack",
                "ukraine", "russia vs", "invasion", "military power", "dogfight", "intercept", "미사일", "폭격", "폭탄", "전쟁", "전투 영상", "격추",
                "사격", "공격", "무기", "emergency", "비상", "비상착륙", "mayday", "turbulence", "난기류", "hard landing", "near miss",
                "close call", "engine failure", "bird strike", "storm", "typhoon landing", "태풍", "dramatic", "shocking", "insane", "crazy",
                "worst", "nervous", "abort", "aborted", "rejected takeoff", "go around", "go-around", "결항", "hijack", "terror", "incident",
                "mishap", "mh370", "9/11", "hindenburg", "taliban", "isis", "fires on", "in action", "flares", "insurgents", "enemy")
# not the thing itself (talk shows, news, games, toys, AI-made clips…)
OFF_TOPIC_WORDS = ("news", "뉴스", "interview", "인터뷰", "podcast", "reaction", "react", "review", "리뷰", "unboxing",
                   "lego", "레고", "toy", "장난감", "minecraft", "game", "게임", "kerbal", "ksp", "simulator", "roblox",
                   "drawing", "그리기", "song", "노래", "cartoon", "만화", "#shorts", "shorts", "ai generated",
                   "debate", "lecture", "강의", "explained", "theory", "documentary", "다큐", "live", "라이브",
                   "생중계", "ytn", "sbs", "kbs", "mbc", "mbn", "jtbc", "연합뉴스", "full broadcast", "replay", "webcast", "q&a", "press conference", "브리핑", "회견",
                   "asmr", "meditation", "music video", "1 hour", "10 hours", "sleep", "relaxing", "lofi", "ranking",
                   "top 10", "top 5", "vs", "comparison", "size comparison", "크기 비교", "what if", "만약", "could",
                   "명상", "수면", "funny", "prank", "meme", "tiktok", "trailer", "movie", "영화", "scene",
                   "tayo", "타요", "poli", "폴리", "pororo", "뽀로로", "cocomelon", "babybus", "kids", "nursery", "동요", "for children",
                   "diecast", "hot wheels", "matchbox", "bruder", "rc", "r/c", "remote control", "1:14", "1:16", "1:18", "1:24", "1:32", "1:43", "1:64",
                   "interior", "실내", "pov", "시승", "test drive", "price", "가격", "for sale", "auction", "경매", "수리", "repair",
                   "walkaround", "walk around", "사용법", "how to", "unbox", "coloring", "색칠", "beamng", "gta",
                   "cockpit", "조종석", "inside", "cabin", "business class", "first class", "economy", "비즈니스", "일등석", "이코노미",
                   "trip report", "flight review", "seat", "좌석", "기내", "기내식", "airline food", "lounge", "라운지", "boarding", "탑승기",
                   "flight simulator", "msfs", "x-plane", "xplane", "dcs", "war thunder", "ace combat", "infinite flight", "p3d", "fsx",
                   "paper airplane", "종이비행기", "model", "모형", "scale", "airfix", "rc plane", "rc helicopter", "arduino",
                   "atc", "radio", "교신", "pilot eye", "pilot view", "captain", "flight deck", "terrible", "goes wrong", "went wrong", "scary landing", "pilot reacts", "vlog", "브이로그", "history of", "역사", "facts", "why", "왜", "엔진 소리만")
GOOD_CHANNELS = ("airbus", "boeing", "embraer", "atr aircraft", "comac", "lockheed", "dassault", "saab", "kai", "한국항공우주",
                 "대한민국 공군", "공군", "rok air force", "republic of korea air force", "u.s. air force", "us air force", "u.s. navy",
                 "us navy", "royal air force", "nasa", "sikorsky", "bell flight", "leonardo", "robinson helicopter", "erickson",
                 "solar impulse", "stratolaunch", "sam chui", "smithsonian", "산림청", "british pathé", "british pathe")


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
