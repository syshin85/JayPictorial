#!/usr/bin/env python3
"""Downloads the pictures pinned in data/minecraft.json from the Minecraft Wiki (minecraft.wiki).

  python3 tools/fetch_media.py            → items whose pinned "photos" changed, plus missing recipe icons
  python3 tools/fetch_media.py creeper …  → just these items (again)

Each item's "photos" lists exact wiki file titles; the first one is the card picture.
Renders with a transparent background stay PNG (GIFs stay animated); screenshots become JPEG.
"icons" (recipe ingredients) go to assets/icons/<key>.png. Pictures are © Mojang, used here privately.
Needs only macOS `sips`.
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "minecraft.json"
MEDIA = ROOT / "data" / "media.json"
ASSETS = ROOT / "assets" / "items"
ICONS = ROOT / "assets" / "icons"

UA = "JayPictorial/0.1 (https://github.com/syshin85/JayPictorial; kids encyclopedia)"
API = "https://minecraft.wiki/api.php"
RENDER_MAX, PHOTO_MAX, THUMB_MAX, ICON_MAX = 800, 1280, 400, 160


def get(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(10 * (attempt + 1))


def image_infos(files):
    out = {}
    for i in range(0, len(files), 40):
        q = urllib.parse.urlencode({"action": "query", "titles": "|".join(files[i:i + 40]), "prop": "imageinfo",
                                    "iiprop": "url|size", "format": "json", "formatversion": "2"})
        for p in json.loads(get(f"{API}?{q}"))["query"]["pages"]:
            if p.get("imageinfo"):
                out[p["title"]] = p["imageinfo"][0]
        time.sleep(0.5)
    return out


def sips(src, dst, fmt, max_px):
    """Converts to fmt, shrinking to max_px but never enlarging (that would blur pixel art)."""
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(src)], capture_output=True, text=True).stdout
    size = max(int(line.split()[-1]) for line in out.splitlines() if "pixel" in line)
    resize = ["-Z", str(max_px)] if size > max_px else []
    subprocess.run(["sips", "-s", "format", fmt, *resize, str(src), "--out", str(dst)], check=True, capture_output=True)


def has_alpha(path):
    out = subprocess.run(["sips", "-g", "hasAlpha", str(path)], capture_output=True, text=True).stdout
    return "yes" in out


def save_picture(data, name, out_dir, stem):
    """Writes one picture; returns its file name inside out_dir."""
    ext = name.rsplit(".", 1)[-1].lower()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in.{ext}"
        src.write_bytes(data)
        if ext == "gif" and len(data) < 1_500_000:
            (out_dir / f"{stem}.gif").write_bytes(data)  # animated: keep as is
            return f"{stem}.gif"
        if has_alpha(src):
            sips(src, out_dir / f"{stem}.png", "png", RENDER_MAX)
            return f"{stem}.png"
        sips(src, out_dir / f"{stem}.jpg", "jpeg", PHOTO_MAX)
        return f"{stem}.jpg"


def fetch_item(item, infos):
    out_dir = ASSETS / item["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.iterdir():
        old.unlink()
    images = []
    for n, f in enumerate(item.get("photos", []), 1):
        ii = infos.get(f)
        if not ii:
            print(f"{item['id']}: missing {f}")
            continue
        data = get(ii["url"])
        name = save_picture(data, f, out_dir, str(n))
        images.append({"src": f"assets/items/{item['id']}/{name}", "credit": "Mojang Studios",
                       "license": "Minecraft Wiki", "source": ii["descriptionurl"], "file": f})
        time.sleep(0.5)
    if images:  # card picture: a small still PNG/JPEG, from a still render when the first one is animated
        first = images[0]["src"]
        if first.endswith(".gif"):
            first = next((img["src"] for img in images if img["src"].endswith(".png")), first)
        name = first.rsplit("/", 1)[1]
        thumb = "thumb.png" if name.endswith((".png", ".gif")) else "thumb.jpg"
        sips(out_dir / name, out_dir / thumb, "png" if thumb.endswith("png") else "jpeg", THUMB_MAX)
        images[0]["thumb"] = f"assets/items/{item['id']}/{thumb}"
    return images


def fetch_icons(icons, force=False):
    ICONS.mkdir(parents=True, exist_ok=True)
    todo = {k: v for k, v in icons.items() if v.get("file") and (force or not (ICONS / f"{k}.png").exists())}
    infos = image_infos([v["file"] for v in todo.values()])
    for k, v in todo.items():
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / ("in." + v["file"].rsplit(".", 1)[-1].lower())
            src.write_bytes(get(infos[v["file"]]["url"]))
            sips(src, ICONS / f"{k}.png", "png", ICON_MAX)
        print(f"icon {k}")
        time.sleep(0.5)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data = json.loads(DATA.read_text())
    media = json.loads(MEDIA.read_text()) if MEDIA.exists() else {}
    todo = [i for i in data["items"] if i.get("photos") and (
        i["id"] in args if args else [img.get("file") for img in media.get(i["id"], {}).get("images", [])] != i["photos"])]
    infos = image_infos(sorted({f for i in todo for f in i["photos"]}))
    for item in todo:
        try:
            images = fetch_item(item, infos)
        except Exception as e:  # keep going; one bad file shouldn't stop the rest
            print(f"{item['id']}: failed ({e})")
            continue
        media.setdefault(item["id"], {})["images"] = images  # keeps a hand-picked video
        print(f"{item['id']}: {len(images)} pictures")
        MEDIA.write_text(json.dumps(media, ensure_ascii=False, indent=2) + "\n")
    fetch_icons(data.get("icons", {}), force="--icons" in sys.argv)


if __name__ == "__main__":
    main()
