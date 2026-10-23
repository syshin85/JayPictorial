#!/usr/bin/env python3
"""Hand-pick a train's photos from Wikimedia Commons.

  python3 tools/photo_picker.py find <train-id> ["extra search" ...]
      → writes tools/candidates/<train-id>.json; view them numbered at
        http://localhost:8000/tools/candidates.html?id=<train-id>
  python3 tools/photo_picker.py set <train-id> 4 1 9 ...
      → downloads those candidates (first one = card thumbnail) and replaces the train's photos
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_media as fm  # noqa: E402

CANDIDATES = fm.ROOT / "tools" / "candidates"


def find(train, extra):
    queries = [train.get("photoQuery", train["wiki"])] + extra
    files = []
    for q in queries:
        for f in fm.commons_files(q):
            if f not in files:
                files.append(f)
    infos = [(f, ii) for f, ii in fm.image_infos(files, 330) if ii["width"] >= 800 and ii["width"] >= ii["height"]]
    out = [{"n": i + 1, "title": f, "thumb": ii.get("thumburl") or ii["url"]} for i, (f, ii) in enumerate(infos)]
    CANDIDATES.mkdir(exist_ok=True)
    (CANDIDATES / f"{train['id']}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{len(out)} candidates → http://localhost:8000/tools/candidates.html?id={train['id']}")


def set_photos(train, numbers):
    cands = {c["n"]: c["title"] for c in json.loads((CANDIDATES / f"{train['id']}.json").read_text())}
    files = [cands[n] for n in numbers]
    infos = dict(fm.image_infos(files, fm.PHOTO_WIDTH))
    # download everything first, so a rate-limit error never leaves the train without photos
    photos = []
    for f in files:
        ii = infos[f]
        photos.append(fm.get(fm.image_url(ii, fm.PHOTO_WIDTH)))
        time.sleep(1.5)
    thumb = fm.get(fm.image_url(infos[files[0]], fm.THUMB_WIDTH))

    out_dir = fm.ASSETS / train["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    (out_dir / "thumb.jpg").write_bytes(thumb)
    images = []
    for i, (f, data) in enumerate(zip(files, photos), 1):
        ii = infos[f]
        (out_dir / f"{i}.jpg").write_bytes(data)
        meta = ii.get("extmetadata", {})
        images.append({
            "src": f"assets/trains/{train['id']}/{i}.jpg",
            "credit": fm.strip_html(meta.get("Artist", {}).get("value")),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "source": ii["descriptionurl"],
        })

    media = json.loads(fm.MEDIA.read_text())
    media.setdefault(train["id"], {})["images"] = images
    media[train["id"]]["imagesPicked"] = True  # chosen by hand: fetch_media.py leaves these alone
    fm.MEDIA.write_text(json.dumps(media, ensure_ascii=False, indent=2))
    print(f"{train['id']}: {len(images)} photos set")


def main():
    cmd, train_id, *rest = sys.argv[1:]
    train = next(t for t in json.loads(fm.TRAINS.read_text())["trains"] if t["id"] == train_id)
    if cmd == "find":
        find(train, rest)
    elif cmd == "set":
        set_photos(train, [int(n) for n in rest])


if __name__ == "__main__":
    main()
