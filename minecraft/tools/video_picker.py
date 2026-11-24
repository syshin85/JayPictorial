#!/usr/bin/env python3
"""Hand-pick each build's YouTube video by looking at frames from the candidates.
(Same idea as train/tools/video_picker.py.)

  python3 tools/video_picker.py find [id ...]
      → collects up to 8 candidates per item (items with "videoQueries") into tools/videos.json; compare them at
        http://localhost:8000/tools/video_review.html (each shows frames from the start, middle and end)
  python3 tools/video_picker.py set castle:3 ...
      → id:number picks that candidate and locks it into data/media.json

Videos show a build in the game: a build tutorial or timelapse, ideally with music and no talking.
Horror, pranks, trolling, PvP, challenges, mods, other games, toys and real-life clips are filtered out.
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
MIN_SECONDS, MAX_SECONDS, IDEAL_SECONDS = 60, 1500, 480

# never for a 6-year-old
UNSAFE_WORDS = ("horror", "scary", "creepy", "terrifying", "nightmare", "cursed", "herobrine", "entity", "303", "haunted",
                "ghost", "zombie apocalypse", "kill", "killed", "killing", "dead", "death", "dies", "died", "blood", "gun", "guns",
                "war", "bomb", "tnt", "explode", "explosion", "destroy", "destroyed", "griefing", "grief", "troll", "trolling",
                "prank", "revenge", "hacker", "scam", "sus", "skibidi", "rage", "angry", "fight", "pvp", "hardcore", "hell",
                "jail", "prison", "공포", "무서운", "저주", "죽", "킬", "전쟁", "복수", "몰래카메라", "트롤", "해킹", "감옥")
# not a build to look at (let's plays, challenges, other games, toys, songs…)
OFF_TOPIC_WORDS = ("#shorts", "shorts", "reaction", "react", "lego", "레고", "toy", "장난감", "roblox", "로블록스", "fortnite",
                   "terraria", "mod", "mods", "modded", "addon", "add-on", "datapack", "texture pack", "shader", "shaders", "rtx",
                   "song", "노래", "parody", "animation", "애니메이션", "movie", "영화", "trailer", "live", "stream", "라이브",
                   "100 days", "100일", "let.s play", "challenge", "챌린지", "vs", "noob", "pro vs", "build battle",
                   "competition", "contest", "speedrun", "update", "snapshot", "news", "seed", "seeds", "server", "서버",
                   "real life", "irl", "in real life", "ai", "free download", "download", "map download", "world download",
                   "podcast", "vlog", "unboxing", "ranking", "top 10", "top 5", "tier list", "1 hour", "asmr", "sleep",
                   "girlfriend", "boyfriend", "secret base", "hidden base", "who", "guess", "quiz", "퀴즈")
GOOD_CHANNELS = ("bluenerd", "rizzial", "tsmc", "goldrobin", "folli", "zaypixel", "bigtonymc", "fuzzlecraft", "mythical sausage",
                 "typical gamer builds", "dragnoz", "silentwisperer", "dedel", "kelpie", "minecraft")


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
    if any(has_word(title, w) for w in ("tutorial", "how to build", "timelapse", "time lapse", "만들기", "건축")):
        score += 2
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
        find([t for t in items if t.get("videoQueries") and (not rest or t["id"] in rest)])
    elif cmd == "set":
        set_videos(rest)


if __name__ == "__main__":
    main()
