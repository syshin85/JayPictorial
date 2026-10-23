# JayPictorial — 신재하의 도감

Picture-book web apps (도감) for the user's son (6 years old, good memory). Vanilla HTML/CSS/JS, no build tools or frameworks.
Moved here from `~/Desktop/jayTrain` (old Netlify copy, left as is — don't edit it).

**Always reply to the user in Korean.**

## Layout
- `index.html` — top page: pick a pictorial (cards). `sw.js` here only caches the top page.
- `train/` — 신재하의 기차 도감 (see `train/README.md`). Home has a 📚 button back to `../`.
- New pictorial → its own folder with `tools/build_web.py` (`main(out_dir)`), a card in `index.html`, and an entry in `PICTORIALS` in `tools/build_site.py`.

## Publish (GitHub Pages)
- Push to `main` → `.github/workflows/pages.yml` runs `python3 tools/build_site.py` → `_site/` → Pages.
- Not yet pushed: the user is creating the GitHub repo (no `gh` CLI installed). Free plan needs a public repo — the user was warned the code, photos and the child's name become public.
- Local: `python3 tools/build_site.py && cd _site && python3 -m http.server 8000`, or serve `train/` directly while working on it (service worker is skipped on localhost).

## Rules the user set
- Must look good on iPad and on iPhone portrait (390px).
- No read-aloud / TTS (removed on request; don't re-add).
- Spelling: "기찻길", not "기차길".
- Kid-safe: YouTube videos are hand-picked by viewing frame captures and locked; they must show trains running from outside (no announcements, display boards, interiors, cab views). The player sits under a tap shield so kids can't leave for youtube.com.
- No Google image scraping. Non-free photos are OK for this private use.
- Never ask the user to paste API keys in chat.
- Quiz keeps no records. Memory game keeps best times (`jaytrain.memory.best.v2.<level>`). No "기록 지우기" button.

## Train pictorial notes
- Home buttons (in order): 기차 알아보기, 기차 퀴즈, 기찻길 만들기, 카드 뒤집기, 객차 연결하기, 틀린그림찾기, 기차 음악.
- New game files must be added to `FILES` in `train/tools/build_web.py` and to `train/index.html`.
- `train/sw.js`: code/data in a per-version cache; photos/sounds in a long-lived `jaytrain-media` cache keyed by content hash (`HASHES`, stamped by the build), so a deploy only re-downloads changed media.
- 틀린그림찾기 (`diff.js`, `data/diffs.json`): the user makes edited photos by hand in ChatGPT → `train/diff_work/<id>/changed.png` (gitignored; prompt in `diff_work/안내.txt`). `composeRight()` uses the original everywhere except each answer's `area`, feathered outward, so unlisted ChatGPT changes disappear. For every picture, verify each spot by viewing cropped original/changed pairs (a pixel diff alone once gave a wrong key), pick 5 big, separated changes, make each `area` cover the whole changed object, then copy `a.jpg`/`b.jpg` (sips jpeg 85) to `assets/diff/<id>/` and test taps in the browser.
