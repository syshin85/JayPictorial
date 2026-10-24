# JayPictorial — 신재하의 백과사전

A collection of picture books (도감) for a 6-year-old, as one website on GitHub Pages.

- `index.html` — the top page: pick a pictorial.
- `train/` — 기차 도감 (trains). See `train/README.md`.
- `space/` — 우주 도감 (planets, stars, rockets, spacecraft).
- More pictorials go in their own folders and get a card on the top page
  and an entry in `PICTORIALS` in `tools/build_site.py`.

## Publish

Every push to `main` runs `.github/workflows/pages.yml`, which builds `_site/` with
`python3 tools/build_site.py` and publishes it to GitHub Pages.
(Repo settings → Pages → Source: **GitHub Actions**.)

Try it locally:

```
python3 tools/build_site.py
cd _site && python3 -m http.server 8000   # http://localhost:8000
```

While working on one pictorial, you can also serve its folder directly
(e.g. `cd train && python3 -m http.server 8000`).
