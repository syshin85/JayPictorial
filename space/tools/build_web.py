#!/usr/bin/env python3
"""Builds dist/ — only the files the space pictorial website needs.

Usage: python3 tools/build_web.py [output folder]   (default: dist/)
JayPictorial's tools/build_site.py calls main() with _site/space as the output.
"""
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

FILES = ["index.html", "app.js", "quiz.js", "quiz.css", "memory.js", "memory.css", "styles.css", "sw.js", "manifest.webmanifest", "_headers"]
DIRS = ["data", "assets"]
SKIP_NAMES = {".DS_Store", ".gitkeep"}


def main(DIST=DIST):
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for name in FILES:
        shutil.copy2(ROOT / name, DIST / name)
    for name in DIRS:
        shutil.copytree(ROOT / name, DIST / name, ignore=shutil.ignore_patterns(*SKIP_NAMES))

    files = sorted(p.relative_to(DIST).as_posix() for p in DIST.rglob("*") if p.is_file())
    core = ["./"] + [f for f in files
                     if not f.startswith("assets/")
                     or f.startswith("assets/icon")
                     or f.endswith("/thumb.jpg")]
    core = [f for f in core if f not in ("sw.js", "_headers")]
    extra = [f for f in files if f.startswith("assets/") and f not in core and not f.startswith("assets/videos/")]

    sw = (DIST / "sw.js").read_text()
    sw = re.sub(r'const VERSION = ".*?";', f'const VERSION = "{time.strftime("%Y%m%d-%H%M%S")}";', sw)
    sw = re.sub(r"const CORE = \[.*?\];", f"const CORE = {json.dumps(core)};", sw)
    sw = re.sub(r"const EXTRA = \[.*?\];", f"const EXTRA = {json.dumps(extra)};", sw)
    # photos and sounds are kept across deploys; the hash tells the iPad which ones changed
    hashes = {f: hashlib.md5((DIST / f).read_bytes()).hexdigest()[:10]
              for f in core + extra if f.startswith("assets/")}
    sw = re.sub(r"const HASHES = \{.*?\};", f"const HASHES = {json.dumps(hashes)};", sw)
    (DIST / "sw.js").write_text(sw)

    size = sum((DIST / f).stat().st_size for f in files) / 1e6
    print(f"{DIST.name}/ ready: {len(files)} files, {size:.1f} MB "
          f"({len(core)} cached on first open, {len(extra)} photos cached in the background)")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DIST)
