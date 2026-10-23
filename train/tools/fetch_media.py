#!/usr/bin/env python3
"""Downloads train photos from Wikipedia/Wikimedia Commons and picks a YouTube
video for each train in data/trains.json. Writes data/media.json.

Usage:
  python3 tools/fetch_media.py            # only trains missing from media.json
  python3 tools/fetch_media.py --force    # refetch everything
  python3 tools/fetch_media.py ktx srt    # refetch specific train ids
  python3 tools/fetch_media.py --videos   # only re-pick YouTube videos (all, or the given ids)
  python3 tools/fetch_media.py --images   # only re-download photos

A video entry with "file" (a local mp4 under assets/videos/) or "locked": true is never replaced.
"""
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAINS = ROOT / "data" / "trains.json"
MEDIA = ROOT / "data" / "media.json"
ASSETS = ROOT / "assets" / "trains"

UA = "jayTrain/0.1 (kids train encyclopedia; personal use)"
API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
IMAGES_PER_TRAIN = 5
PHOTO_WIDTH = 1280
THUMB_WIDTH = 500
SKIP_WORDS = ("map", "logo", "diagram", "route", "flag", "icon", "symbol",
              "schematic", "plan", "chart", "graph", "seat", "commons-", "wikidata")


def get(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko,en"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries - 1:
                time.sleep(20 * (attempt + 1))  # Wikimedia rate limit: back off properly
                continue
            raise


def api(endpoint=API, **params):
    params.update(format="json", formatversion="2")
    time.sleep(0.5)
    return json.loads(get(endpoint + "?" + urllib.parse.urlencode(params)))


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def candidate_files(title):
    data = api(action="query", titles=title, redirects=1,
               prop="pageimages|images", piprop="name", imlimit=200)
    page = data["query"]["pages"][0]
    if page.get("missing"):
        raise RuntimeError(f"Wikipedia page not found: {title}")
    files = []
    if page.get("pageimage"):
        files.append("File:" + page["pageimage"].replace("_", " "))
    for img in page.get("images", []):
        files.append(img["title"])
    seen, out = set(), []
    for f in files:
        name = f.lower()
        if f in seen or not name.endswith((".jpg", ".jpeg")):
            continue
        if any(w in name for w in SKIP_WORDS):
            continue
        seen.add(f)
        out.append(f)
    return out


def commons_files(query):
    data = api(COMMONS_API, action="query", list="search", srnamespace=6, srlimit=40,
               srsearch=f"{query} filetype:bitmap")
    return [r["title"] for r in data["query"]["search"]
            if r["title"].lower().endswith((".jpg", ".jpeg"))
            and not any(w in r["title"].lower() for w in SKIP_WORDS)]


def image_infos(files, width):
    infos = {}
    for i in range(0, len(files), 40):
        chunk = files[i:i + 40]
        data = api(COMMONS_API, action="query", titles="|".join(chunk), prop="imageinfo",
                   iiprop="url|size|extmetadata", iiurlwidth=width)
        for p in data["query"]["pages"]:
            ii = (p.get("imageinfo") or [None])[0]
            if ii:
                infos[p["title"]] = ii
    # keep the API's normalized titles in the original order
    return [(f, infos[f]) for f in files if f in infos]


INTERIOR_WORDS = ("interior", "class", "klasse", "executive", "business", "inside", "cabin", "green car", "restaurant", "sleeping", "seat", "車内")
MAX_INTERIORS = 1


def matches(train, f):
    """A file is kept only if its name mentions the train (photoMatch keywords)."""
    keys = train.get("photoMatch")
    name = f.lower().replace("_", " ")
    return not keys or any(k.lower() in name for k in keys)


def is_interior(f):
    name = f.lower().replace("_", " ")
    return any(w in name for w in INTERIOR_WORDS)


STANDARD_WIDTHS = (250, 330, 500, 960, 1280)


def image_url(ii, width):
    """A thumbnail URL in one of Wikimedia's standard widths, never the original file.

    When the original is narrower than the requested width the API hands back the original
    file's URL, and downloads of originals are what Wikimedia rate-limits (HTTP 429).
    """
    w = max([s for s in STANDARD_WIDTHS if s <= min(width, ii["width"] - 1)] or [STANDARD_WIDTHS[0]])
    url = ii["url"].split("?")[0]  # https://upload.wikimedia.org/wikipedia/commons/a/ab/Name.jpg
    head, _, name = url.rpartition("/")
    if "/commons/" not in head:
        return ii.get("thumburl") or url
    return head.replace("/commons/", "/commons/thumb/", 1) + f"/{name}/{w}px-{name}"


def fetch_images(train):
    files = [f for f in candidate_files(train["wiki"]) if matches(train, f)]
    if len(files) < IMAGES_PER_TRAIN + 3:
        files += [f for f in commons_files(train.get("photoQuery", train["wiki"]))
                  if f not in files and matches(train, f)]
    infos = [(f, ii) for f, ii in image_infos(files, PHOTO_WIDTH)
             if ii["width"] >= 800 and ii["width"] >= ii["height"]]
    # Exterior shots first (the first one becomes the grid card), at most one interior.
    exterior = [x for x in infos if not is_interior(x[0])]
    interior = [x for x in infos if is_interior(x[0])][:MAX_INTERIORS]
    infos = exterior[:IMAGES_PER_TRAIN - len(interior[:1])] + interior
    infos = (infos + exterior[len(infos):])[:IMAGES_PER_TRAIN]
    out_dir = ASSETS / train["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    images = []
    for f, ii in infos[:IMAGES_PER_TRAIN]:
        n = len(images) + 1
        path = out_dir / f"{n}.jpg"
        path.write_bytes(get(image_url(ii, PHOTO_WIDTH)))
        meta = ii.get("extmetadata", {})
        images.append({
            "src": f"assets/trains/{train['id']}/{n}.jpg",
            "credit": strip_html(meta.get("Artist", {}).get("value")),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "source": ii["descriptionurl"],
        })
        time.sleep(1.5)
    if infos:
        (out_dir / "thumb.jpg").write_bytes(get(image_url(infos[0][1], THUMB_WIDTH)))
    return images


# Titles containing these are skipped so a kid never lands on accident/news footage.
UNSAFE_WORDS = ("사고", "쾅", "충돌", "탈선", "사망", "부상", "화재", "뉴스", "news", "sbs", "kbs", "mbc", "jtbc", "ytn",
                "crash", "accident", "derail", "collision", "collide", "collided", "smash", "fire", "killed", "dead", "事故", "衝突", "脱線",
                "fail", "fails", "near miss", "horror", "scary", "아찔", "참사", "déraillement", "accident", "unfall",
                "incidente", "emergency", "긴급", "위험", "danger", "dangerous", "危険", "緊急",
                "危ない", "急停止", "非常", "ヒヤリ", "급브레이크", "급정거", "급제동", "опасно", "авария", "crashes", "붕괴", "돌진", "崩壊", "collapse", "death", "dies", "died", "escapes", "insane", "terrifying", "close call", "hit by", "incendio", "incendie", "fuego", "feuer", "fire")


def is_safe(title):
    t = title.lower()
    return not any(w in t for w in UNSAFE_WORDS)


# Clips that don't show the train running from outside (cab views, window views, reviews...).
OFF_TOPIC_WORDS = ("cab view", "cabview", "driver", "운전실", "전망", "차창", "탑승기", "타봤", "타보", "리뷰", "review",
                   "vlog", "브이로그", "여행", "trip", "journey", "tour", "前面展望", "車窓", "乗車", "車内", "ride",
                   "onboard", "on board", "inside", "class", "first class", "asmr", "모음", "compilation",
                   "まとめ", "シーン集", "ranking", "랭킹", "timelapse", "타임랩스", "toy", "장난감", "プラレール",
                   "lego", "레고", "minecraft", "game", "게임", "simulator", "시뮬", "model", "모형", "模型",
                   "n gauge", "nゲージ", "ho scale", "drawing", "그리기", "cartoon", "만화", "#shorts",
                   "銀行", "貯金", "おもちゃ", "音サンプル", "メロディ", "melody", "甲種", "輸送", "transport",
                   "envoyé spécial", "france 2", "reportage", "documentary", "다큐", "trop", "too fast", "과속",
                   # announcements, display boards and riding along instead of watching the train go by
                   "안내방송", "방송", "안내", "전면", "전광판", "진입음", "도착음", "lcd", "행선", "발차멜로디", "멜로디", "放送", "車内", "チャイム",
                   "chime", "announcement", "탑승", "타고", "후기", "walk around", "walkaround", "inside", "interior",
                   "실내", "객실", "좌석", "seat", "seats", "sleeper", "suite", "room tour", "hotel", "luxury", "luxurious", "price", "cost",
                   "ticket", "티켓", "how to", "guide", "explained", "history of", "역사", "news")
ACTION_WORDS = ("통과", "주행", "질주", "달리", "진입", "출발", "발차", "通過", "走行", "発車", "入線", "passing",
                "at speed", "high speed", "speeding", "departing", "departure", "arriving", "arrival",
                "durchfahrt", "passage", "passaggio", "vitesse", "velocità", "viaduct", "flies", "flying through")
MIN_SECONDS, MAX_SECONDS, IDEAL_SECONDS = 20, 240, 90
NO_ACTION_PENALTY = 15  # a title that never says the train runs/passes is rarely what we want


def seconds(text):
    parts = [int(p) for p in text.split(":") if p.isdigit()]
    total = 0
    for p in parts:
        total = total * 60 + p
    return total


def search_youtube(query):
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query, "hl": "ko"})
    html = get(url).decode("utf-8", "ignore")
    results = []
    for chunk in html.split('"videoRenderer":{"videoId":"')[1:]:
        vid = chunk[:11]
        title = re.search(r'"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"', chunk)
        length = re.search(r'"lengthText":\{.*?"simpleText":"([\d:]+)"', chunk[:20000])
        views = re.search(r'"viewCountText":\{"simpleText":"([^"]*)"', chunk[:20000])
        if title and length:
            results.append({"youtube": vid, "title": json.loads(f'"{title.group(1)}"'),
                            "seconds": seconds(length.group(1)),
                            "views": int(re.sub(r"\D", "", views.group(1)) or 0) if views else 0})
    return results


def has_word(text, word):
    """Substring match, but ASCII words must not be glued to other letters ("ice" ≠ "service")."""
    word = word.lower()
    if not word.isascii():
        return word in text
    return re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text) is not None


def score_video(train, v):
    """None if the clip is unsuitable, otherwise higher = better."""
    title = v["title"].lower()
    match = [k.lower() for k in train.get("videoMatch", [])]
    # a filter word that is part of the train's own name (Darjeeling "toy train") doesn't count
    off_topic = [w for w in OFF_TOPIC_WORDS if not any(w in k for k in match)]
    if not is_safe(title) or any(has_word(title, w) for w in off_topic):
        return None
    if not MIN_SECONDS <= v["seconds"] <= MAX_SECONDS:
        return None
    if not any(has_word(title, k) for k in train.get("videoMatch", [])):
        return None
    if any(has_word(title, k) for k in train.get("videoExclude", [])):
        return None
    score = 10 if any(w in title for w in ACTION_WORDS) else -NO_ACTION_PENALTY
    score -= abs(v["seconds"] - IDEAL_SECONDS) / 20  # prefer ~1.5 minutes
    score += 2 * math.log10(v["views"] + 1)          # popular clips tend to be better shot
    return score


def fetch_video(train, alternatives=3):
    candidates = {}
    for q in train["videoQueries"]:
        for rank, v in enumerate(search_youtube(q)):
            s = score_video(train, v)
            if s is not None and v["youtube"] not in candidates:
                candidates[v["youtube"]] = (s - rank * 0.5, v)
        time.sleep(1)
    picked = []
    for _, v in sorted(candidates.values(), key=lambda x: -x[0]):
        try:
            o = json.loads(get("https://www.youtube.com/oembed?format=json&url=" +
                               urllib.parse.quote(f"https://www.youtube.com/watch?v={v['youtube']}")))
        except urllib.error.HTTPError:
            continue  # private / not embeddable
        picked.append({**v, "channel": o.get("author_name", "")})
        if len(picked) > alternatives:
            break
    if not picked:
        return None
    return {**picked[0], "alternatives": picked[1:]}


def main():
    args = sys.argv[1:]
    force = "--force" in args
    do_images = "--videos" not in args or "--images" in args
    do_videos = "--images" not in args or "--videos" in args
    only = [a for a in args if not a.startswith("--")]
    trains = json.loads(TRAINS.read_text())["trains"]
    media = json.loads(MEDIA.read_text()) if MEDIA.exists() else {}

    for t in trains:
        if only and t["id"] not in only:
            continue
        entry = media.setdefault(t["id"], {})
        explicit = bool(only) or force
        need_images = do_images and (explicit or not entry.get("images")) and "--videos" not in args
        if entry.get("imagesPicked"):
            need_images = False  # photos chosen by hand with photo_picker.py
        need_video = do_videos and (explicit or "--videos" in args or not entry.get("video"))
        current = entry.get("video") or {}
        if current.get("file") or current.get("locked"):
            need_video = False  # chosen by hand (local file or "locked": true); never replace it
        if not (need_images or need_video):
            continue
        print(f"→ {t['id']}", flush=True)
        if need_images:
            try:
                entry["images"] = fetch_images(t)
                print(f"   images: {len(entry['images'])}")
            except Exception as e:
                print(f"   ! images failed: {e}")
        if need_video:
            try:
                v = fetch_video(t)
                if v:
                    entry["video"] = v
                    print(f"   video: {v['youtube']} ({v['seconds']}s) {v['title']}")
                else:
                    print("   ! no suitable video found")
            except Exception as e:
                print(f"   ! video failed: {e}")
        MEDIA.write_text(json.dumps(media, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
