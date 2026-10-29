# JayPictorial — 신재하의 백과사전

Picture-book web apps (도감) for the user's son (6 years old, good memory). Vanilla HTML/CSS/JS, no build tools or frameworks.
Moved here from `~/Desktop/jayTrain` (old Netlify copy, left as is — don't edit it).

**Always reply to the user in Korean.**

## Layout
- `index.html` — top page: pick a pictorial (cards). `sw.js` here only caches the top page.
- `train/` — 기차 도감 (see `train/README.md`). Home has a 📚 button back to `../`.
- `space/` — 우주 도감: same structure as train (home → book with tabs → detail), night-sky theme. Home: 우주 알아보기 (`sky`: planets, moons, stars), 우주선 알아보기 (`ships`: rockets, spacecraft, satellites, rovers) and 카드 뒤집기 (`memory.js`/`memory.css`, copy of train's; best times under `jaypictorial.space.memory.best.<level>`) and 우주 퀴즈 (`quiz.js`/`quiz.css`, a copy of train's quiz; questions in `data/quiz.json` come from `tools/make_quiz.py`, which holds the hand-written fact questions — edit it and rerun rather than editing the JSON). `data/space.json` (books → sections → items, `facts` = 3 chips); photos via `space/tools/fetch_media.py` (Wikimedia, `photos` pins exact files, `photoSkip` drops some) → `data/media.json`, `assets/items/<id>/`. Videos: one per item, same kid-safe player as train; picked by viewing frames with `space/tools/video_picker.py find` + `tools/video_review.html`, then `set id:n`. They must show the thing itself — the planet, or the machine actually working (launch, landing, docking, driving, flying); no explosions/failures, news, talking heads.
- `car/` — 자동차 도감: copy of the space pictorial on a bright road theme. Home: 자동차 알아보기 (`cars`, one book), 자동차 퀴즈 and 카드 뒤집기 (`memory.js`/`memory.css`, best times under `jaypictorial.car.memory.best.<level>`; quiz is `quiz.js`/`quiz.css`, copy of space's on train's light colors; questions from `tools/make_quiz.py` — edit and rerun, never the JSON). The book has all sections as tabs: 승용차 (`family`), 스포츠카, 경주용 자동차, 버스와 트럭 (`buses`), 특수 자동차 (`special`: emergency, construction and other working cars) — the user asked for these merged groups and not to split off the working cars. 승용차 has no taxis (user asked) and mixes famous cars selling well now (Tesla, 그랜저, 쏘렌토…) with classics, balanced across countries (Korea, US, Germany, Japan, UK, Italy, France, Sweden, China). `data/cars.json` is the source (edit it directly); same tools as space (`tools/candidates.py`, `fetch_media.py`, `video_picker.py`). Videos show the car from outside doing its job (driving, lifting, digging…); no crashes, fires, chases, toys or cartoons. Released 2026-10-28 (blue card on the top page). After the last real card the top page keeps a dashed 🎁 "새 도감이 곧 와요!" box (`.book.soon`, not clickable) — the user wants it kept.
- New pictorial → its own folder with `tools/build_web.py` (`main(out_dir)`), a card in `index.html`, and an entry in `PICTORIALS` in `tools/build_site.py`.

## Publish (GitHub Pages)
- Push to `main` → `.github/workflows/pages.yml` runs `python3 tools/build_site.py` → `_site/` → Pages.
- Repo: https://github.com/syshin85/JayPictorial (public; Pages source = GitHub Actions). Live: https://syshin85.github.io/JayPictorial/ . No `gh` CLI; `git push` works with stored credentials. The user knows the code, photos and the child's name are public.
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
- Home buttons (in order): 기차 알아보기, 기차 퀴즈, 기찻길 만들기, 카드 뒤집기, 객차 연결하기, 기차 음악.
- New game files must be added to `FILES` in `train/tools/build_web.py` and to `train/index.html`.
- `train/sw.js`: code/data in a per-version cache; photos/sounds in a long-lived `jaytrain-media` cache keyed by content hash (`HASHES`, stamped by the build), so a deploy only re-downloads changed media.
