#!/usr/bin/env python3
"""Builds _site/ — the whole JayPictorial website — for GitHub Pages.

The top page (pick a pictorial) is copied as is; each pictorial is built by its own
build script into _site/<name>/. GitHub Actions runs this on every push
(.github/workflows/pages.yml); run it locally to try the site: python3 tools/build_site.py

Usage: python3 tools/build_site.py
"""
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"

TOP_FILES = ["index.html", "sw.js", "manifest.webmanifest", ".nojekyll"]
TOP_DIRS = ["assets"]
PICTORIALS = ["train"]  # each has tools/build_web.py with main(out_dir)


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    for name in TOP_FILES:
        shutil.copy2(ROOT / name, SITE / name)
    for name in TOP_DIRS:
        shutil.copytree(ROOT / name, SITE / name, ignore=shutil.ignore_patterns(".DS_Store"))

    for name in PICTORIALS:
        spec = importlib.util.spec_from_file_location(f"build_{name}", ROOT / name / "tools" / "build_web.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main(SITE / name)

    print("_site/ ready")


if __name__ == "__main__":
    main()
