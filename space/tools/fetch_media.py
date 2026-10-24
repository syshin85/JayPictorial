#!/usr/bin/env python3
"""Downloads photos from Wikipedia/Wikimedia Commons for each item in data/space.json.
Writes data/media.json. (Same idea as train/tools/fetch_media.py, photos only.)

Usage:
  python3 tools/fetch_media.py            # only items missing from media.json or whose "photos" changed
  python3 tools/fetch_media.py --force    # refetch everything
  python3 tools/fetch_media.py mars iss   # refetch specific item ids

An item can pin its photos with "photos": ["File:….jpg", …] (used in that order), and drop
unwanted ones with "photoSkip": ["word in file name", …]. A pinned .png (a cut-out render on a
white or transparent background) is put on a black sky by tools/on_black.swift.
"""
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "space.json"
MEDIA = ROOT / "data" / "media.json"
ASSETS = ROOT / "assets" / "items"

UA = "JayPictorial/0.1 (https://github.com/syshin85/JayPictorial; kids space encyclopedia)"
API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
IMAGES_PER_ITEM = 5
PHOTO_WIDTH = 1280
THUMB_WIDTH = 500
SKIP_WORDS = ("map", "logo", "diagram", "flag", "icon", "symbol", "schematic", "chart", "graph", "plot",
              "comparison", "compared", "size", "orbits", "patch", "insignia", "emblem", "infographic",
              "spectrum", "timeline", "cutaway", "drawing", "illustration", "stamp", "coin", "poster",
              "commons-", "wikidata", "signature", "portrait", "animation", "scale", "labeled",
              "annotated", "location", "sketch", "model", "replica", "mockup", "render")


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
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def usable(f):
    name = f.lower()
    return name.endswith((".jpg", ".jpeg")) and not any(w in name for w in SKIP_WORDS)


def candidate_files(title):
    data = api(action="query", titles=title, redirects=1,
               prop="pageimages|images", piprop="name", imlimit=200)
    page = data["query"]["pages"][0]
    if page.get("missing"):
        raise RuntimeError(f"Wikipedia page not found: {title}")
    files = []
    if page.get("pageimage"):
        files.append("File:" + page["pageimage"].replace("_", " "))
    files += [img["title"] for img in page.get("images", [])]
    return list(dict.fromkeys(f for f in files if usable(f)))


def commons_files(query):
    data = api(COMMONS_API, action="query", list="search", srnamespace=6, srlimit=40,
               srsearch=f"{query} filetype:bitmap")
    return [r["title"] for r in data["query"]["search"] if usable(r["title"])]


def image_infos(files, width):
    infos = {}
    # Commons first; files kept only on English Wikipedia (e.g. KITSAT-1's artwork) from there
    for endpoint in (COMMONS_API, API):
        missing = [f for f in files if f not in infos]
        for i in range(0, len(missing), 40):
            chunk = missing[i:i + 40]
            data = api(endpoint, action="query", titles="|".join(chunk), prop="imageinfo",
                       iiprop="url|size|extmetadata", iiurlwidth=width)
            for p in data["query"]["pages"]:
                ii = (p.get("imageinfo") or [None])[0]
                if ii:
                    infos[p["title"]] = ii
    return [(f, infos[f]) for f in files if f in infos]


def matches(item, f):
    """A file is kept only if its name mentions the item (photoMatch keywords)."""
    name = f.lower().replace("_", " ")
    if any(w.lower() in name for w in item.get("photoSkip", [])):
        return False
    keys = item.get("photoMatch")
    return not keys or any(k.lower() in name for k in keys)


STANDARD_WIDTHS = (250, 330, 500, 960, 1280)


def image_url(ii, width):
    """A thumbnail URL in one of Wikimedia's standard widths, never the original file."""
    w = max([s for s in STANDARD_WIDTHS if s <= min(width, ii["width"] - 1)] or [STANDARD_WIDTHS[0]])
    url = ii["url"].split("?")[0]
    head, _, name = url.rpartition("/")
    if "/commons/" not in head:
        return ii.get("thumburl") or url
    return head.replace("/commons/", "/commons/thumb/", 1) + f"/{name}/{w}px-{name}"


def download(f, ii, width):
    """JPEG bytes of a photo at about `width` pixels."""
    if not f.lower().endswith(".png"):
        return get(image_url(ii, width))
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "in.png", Path(tmp) / "out.jpg"
        src.write_bytes(get(ii["url"] if ii["width"] <= 1280 else image_url(ii, 1280)))
        subprocess.run(["swift", str(Path(__file__).parent / "on_black.swift"), str(src), str(out), str(width)], check=True)
        return out.read_bytes()


def fetch_images(item, old_images=()):
    if item.get("photos"):
        infos = image_infos(item["photos"], PHOTO_WIDTH)
    else:
        files = [f for f in candidate_files(item["wiki"]) if matches(item, f)]
        if len(files) < IMAGES_PER_ITEM + 3:
            files += [f for f in commons_files(item.get("photoQuery", item["wiki"]))
                      if f not in files and matches(item, f)]
        infos = [(f, ii) for f, ii in image_infos(files, PHOTO_WIDTH)
                 if min(ii["width"], ii["height"]) >= 600 and ii["height"] <= 2 * ii["width"]]
    out_dir = ASSETS / item["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    # photos already downloaded are kept, not fetched again
    have = {img["file"]: (ROOT / img["src"]).read_bytes() for img in old_images
            if img.get("file") and (ROOT / img["src"]).exists()}
    old_thumb = (out_dir / "thumb.jpg").read_bytes() if (out_dir / "thumb.jpg").exists() else None
    old_first = old_images[0].get("file") if old_images else None
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    images = []
    for f, ii in infos[:IMAGES_PER_ITEM]:
        n = len(images) + 1
        (out_dir / f"{n}.jpg").write_bytes(have[f] if f in have else download(f, ii, PHOTO_WIDTH))
        meta = ii.get("extmetadata", {})
        images.append({
            "src": f"assets/items/{item['id']}/{n}.jpg",
            "credit": strip_html(meta.get("Artist", {}).get("value")),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "source": ii["descriptionurl"],
            "file": f,
        })
        if f not in have:
            time.sleep(1.5)
    if infos and infos[0][0] == old_first and old_thumb:
        (out_dir / "thumb.jpg").write_bytes(old_thumb)
    elif infos:
        (out_dir / "thumb.jpg").write_bytes(download(*infos[0], THUMB_WIDTH))
    return images


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    items = json.loads(DATA.read_text())["items"]
    media = json.loads(MEDIA.read_text()) if MEDIA.exists() else {}
    for item in items:
        if args and item["id"] not in args:
            continue
        old = media.get(item["id"], {}).get("images", [])
        pinned_same = item.get("photos") == [img.get("file") for img in old]
        if not args and not force and old and (not item.get("photos") or pinned_same):
            continue
        try:
            images = fetch_images(item, old)
        except Exception as e:  # keep going; one bad page shouldn't stop the rest
            print(f"{item['id']}: failed ({e})")
            continue
        media.setdefault(item["id"], {})["images"] = images  # keeps the hand-picked video
        print(f"{item['id']}: {len(images)} photos")
        MEDIA.write_text(json.dumps(media, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
