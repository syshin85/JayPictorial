# 기차 도감 (jayTrain)

아이패드용 어린이 기차 도감. 같은 데이터(`data/`, `assets/`)로 두 가지 버전이 있어요.

- **웹앱 (메인)** — Netlify에 올려서 아이패드 홈 화면에 추가해서 사용
- **아이패드 앱 (SwiftUI)** — `ios/JayTrain.xcodeproj` (유료 개발자 계정이 생기면 사용)

## Netlify에 올리기

1. 배포용 폴더 만들기: `python3 tools/build_web.py` → `dist/` 폴더가 생겨요.
2. **처음 한 번:** https://app.netlify.com 로그인 → Sites → **Add new site → Deploy manually** →
   `dist` 폴더를 끌어다 놓기.
   Site configuration → **Change site name**에서 주소를 바꿀 수 있어요 (예: `jay-train.netlify.app`).
3. **고친 뒤 다시 올리기:** 1번 실행 → Netlify의 사이트 → **Deploys** 탭 → `dist` 폴더를 끌어다 놓기.
   주소는 그대로이고, 아이패드는 앱을 다시 열면 새 버전으로 바뀌어요.

### 아이패드에 설치

Safari로 사이트 주소 열기 → 공유 버튼 → **홈 화면에 추가**.
한 번 열고 나면 도감과 사진은 인터넷 없이도 보여요(사진은 처음 열 때 와이파이에서 몇 분간 받아요). 영상은 인터넷이 필요해요.

## 아이패드 앱

1. `ios/JayTrain.xcodeproj`를 Xcode로 열어요.
2. 처음 한 번: 왼쪽 JayTrain 프로젝트 → Signing & Capabilities → **Team**에서 본인 Apple ID 선택
   (번들 ID가 이미 쓰이고 있다고 나오면 `com.heat.jaytrain`을 다른 이름으로 바꾸기)
3. 아이패드를 USB로 연결 → 상단에서 아이패드 선택 → ▶︎ 실행
4. 아이패드에서 처음 한 번: 설정 → 일반 → VPN 및 기기 관리 → 개발자 앱 신뢰,
   설정 → 개인정보 보호 및 보안 → **개발자 모드** 켜기

무료 Apple ID로 설치하면 **7일마다** Xcode에서 다시 실행해 설치해야 해요 (유료 개발자 계정은 1년).
`data/`, `assets/`는 앱에 그대로 포함되므로, 기차를 추가하거나 영상을 바꾼 뒤 다시 실행하면 앱에도 반영돼요.

## 내 Mac에서 확인하기

```sh
cd jayTrain
python3 -m http.server 8000
```

- Mac에서: http://localhost:8000
- 아이패드에서: 같은 Wi-Fi에 연결 후 `http://<Mac IP>:8000` (Mac IP는 `ipconfig getifaddr en0`)
- Safari 공유 버튼 → **홈 화면에 추가** 하면 주소창 없이 앱처럼 전체화면으로 열립니다.

## 구조

| 파일 | 설명 |
|---|---|
| `data/trains.json` | 지역, 기차 정보(이름·설명·속도·연도·알고 있니?) — 직접 편집 |
| `data/media.json` | 사진 목록·저작권 정보·유튜브 영상 ID — 스크립트가 생성 |
| `assets/trains/<id>/` | 사진 `1~5.jpg` + 카드용 `thumb.jpg` |
| `tools/fetch_media.py` | 위키미디어 사진 다운로드 + 유튜브 영상 선택 |
| `app.js` / `styles.css` | 화면: 홈 → 도감(`#/book/<지역>`) → 상세(`#/train/<id>`) |

## 기차 추가하기

1. `data/trains.json`의 `trains`에 항목 추가 (`wiki`는 영어 위키백과 문서 제목, `photoMatch`는 사진 파일명에 들어가야 하는 키워드)
2. `python3 tools/fetch_media.py <id>` 실행

## 영상

영상은 유튜브에서 자동으로 고릅니다. 길이 20초~4분, 제목에 기차 이름이 있고 "통과·주행" 같은 달리는 장면을 우선하며,
사고·뉴스·운전실·차창·탑승기·장난감 영상은 제외합니다.

- **한눈에 검토:** 서버를 켠 상태에서 http://localhost:8000/tools/review.html (초록 테두리 = 현재 영상, 옆은 후보)
- **유튜브 영상 바꾸기:** `data/media.json`에서 해당 기차의 `video`를 아래처럼 바꿔요. `"locked": true`가 있으면 스크립트가 덮어쓰지 않아요.
  ```json
  "video": { "youtube": "영상ID11자리", "title": "메모용 제목", "locked": true }
  ```
- **로컬 영상(mp4) 쓰기:** 파일을 `assets/videos/`에 넣고 이렇게 적어요. 인터넷 없이도 재생됩니다.
  ```json
  "video": { "file": "assets/videos/ktx.mp4" }
  ```
  아이패드에서 재생되려면 **mp4(H.264)** 형식이어야 해요. 아이폰으로 찍은 영상은 "호환성 우선" 설정이면 그대로 쓸 수 있어요.
- **자동으로 다시 고르기:** `python3 tools/fetch_media.py --videos` (고정·로컬 영상은 유지)

## 사진 저작권

사진은 위키미디어 공용(Wikimedia Commons)의 자유 라이선스 이미지이며, 상세 화면 아래 **사진 정보**에 작가와 라이선스가 표시됩니다.

## 소리 출처

기찻길 만들기의 소리는 위키미디어 공용(Wikimedia Commons)의 녹음을 잘라 반복 재생용으로 다듬었어요 (`assets/sounds/`).

- 칙칙폭폭 `chuff-loop.wav`: "Steam engine.ogg" — aradlaw, 퍼블릭 도메인
- 덜컹덜컹 `rail-loop.wav`: "Train passing by in the Wirikuta Desert (Mexico, SLP).wav" — felix.blume, CC0
- 기적 `whistle.wav`: "WWS SteamWhistle.ogg" — Work With Sounds / Konrad Gutkowski, CC BY 4.0
