#!/usr/bin/env python3
"""Hand-pick each train's YouTube video by looking at frames from the candidates.

  python3 tools/video_picker.py find [train-id ...]
      → collects up to 8 candidates per train into tools/candidates/videos.json; compare them at
        http://localhost:8000/tools/video_review.html (each shows frames from the start, middle and end)
  python3 tools/video_picker.py set ktx:3 srt:0 ...
      → train-id:number picks that candidate (0 = keep the current video) and locks it
"""
import json
import sys
import time
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_media as fm  # noqa: E402

OUT = fm.ROOT / "tools" / "candidates" / "videos.json"
PER_TRAIN = 8


def embeddable(vid):
    try:
        o = json.loads(fm.get("https://www.youtube.com/oembed?format=json&url=" +
                              urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}")))
        return o.get("author_name", "")
    except urllib.error.HTTPError:
        return None


def find(trains):
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    media = json.loads(fm.MEDIA.read_text())
    for t in trains:
        scored = {}
        for q in t["videoQueries"]:
            try:
                results = fm.search_youtube(q)
            except Exception as e:
                print(f"   ! search failed: {e}")
                results = []
            for rank, v in enumerate(results):
                s = fm.score_video(t, v)
                if s is not None and v["youtube"] not in scored:
                    scored[v["youtube"]] = (s - rank * 0.5, v)
            time.sleep(1)
        current = (media.get(t["id"]) or {}).get("video") or {}
        picked = []
        for _, v in sorted(scored.values(), key=lambda x: -x[0]):
            if v["youtube"] == current.get("youtube"):
                continue
            channel = embeddable(v["youtube"])
            if channel is None:
                continue
            picked.append({**v, "channel": channel})
            if len(picked) >= PER_TRAIN:
                break
        current = {k: current[k] for k in ("youtube", "title", "seconds") if k in current}
        data[t["id"]] = {"name": t["name"], "candidates": [current] + picked}
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        print(f"{t['id']}: {len(picked)} candidates", flush=True)


def set_videos(picks):
    data = json.loads(OUT.read_text())
    media = json.loads(fm.MEDIA.read_text())
    for pick in picks:
        tid, n = pick.split(":")
        cands = data[tid]["candidates"]
        chosen = cands[int(n)]
        others = [c for i, c in enumerate(cands) if i != int(n) and c.get("youtube")]
        media.setdefault(tid, {})["video"] = {**chosen, "locked": True, "alternatives": others[:4]}
        print(f"{tid}: {chosen.get('title', '')}")
    fm.MEDIA.write_text(json.dumps(media, ensure_ascii=False, indent=2))


def main():
    cmd, *rest = sys.argv[1:]
    trains = json.loads(fm.TRAINS.read_text())["trains"]
    if cmd == "find":
        find([t for t in trains if not rest or t["id"] in rest])
    elif cmd == "set":
        set_videos(rest)


if __name__ == "__main__":
    main()
