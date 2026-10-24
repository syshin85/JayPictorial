#!/usr/bin/env python3
"""Lists photo candidates for each item (no downloads) into tools/candidates.json,
for picking photos by eye in tools/candidates.html. Then pin the chosen files with
"photos": [...] in data/space.json and run fetch_media.py <id>.

Usage: python3 tools/candidates.py [ids…]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fetch_media as fm  # noqa: E402

OUT = Path(__file__).parent / "candidates.json"


def main():
    ids = sys.argv[1:]
    items = json.loads(fm.DATA.read_text())["items"]
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for item in items:
        if ids and item["id"] not in ids:
            continue
        files = [f for f in fm.candidate_files(item["wiki"]) if fm.matches(item, f)]
        files += [f for f in fm.commons_files(item.get("photoQuery", item["wiki"])) if f not in files and fm.matches(item, f)]
        infos = [(f, ii) for f, ii in fm.image_infos(files, 330)
                 if min(ii["width"], ii["height"]) >= 600 and ii["height"] <= 2 * ii["width"]]
        out[item["id"]] = [{"file": f, "thumb": fm.image_url(ii, 330)} for f, ii in infos[:24]]
        print(f"{item['id']}: {len(out[item['id']])}", flush=True)
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
