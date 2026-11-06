#!/usr/bin/env python3
"""Writes data/quiz.json for 비행기 퀴즈 (same shape as the train and space quizzes).

Photo questions (country, compare) come from data/planes.json; the fact questions are hand-written
below from each item's story and fun fact. The random seed is fixed, so running it again gives
the same quiz unless the lists here change. No "what is this photo?" questions: the user found
them dull.

Usage: python3 tools/make_quiz.py
"""
import json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data/planes.json").read_text())
items = {t["id"]: t for t in data["items"]}
rng = random.Random(7)
thumb = lambda i: f"assets/items/{i}/thumb.jpg"
out = []

def eun(name):
    """은/는 after a name, also after a digit or a Latin letter read aloud (747 → 칠, R → 알)."""
    ch = name.rstrip(")").split(" (")[0][-1].upper()
    if ch.isdigit() or "A" <= ch <= "Z":
        return "은" if ch in "0136780LMNR" else "는"
    return "은" if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 else "는"

def add(kind, question, image, choices, answer, explain, item):
    out.append({"id": f"q{len(out)+1:03d}", "kind": kind, "question": question, "image": image,
                "choices": choices, "answer": answer, "explain": explain, "item": item})

def text_choices(right, wrongs):
    c = [right] + wrongs
    rng.shuffle(c)
    return [{"text": x, "image": None} for x in c], c.index(right)

# ---------- 1. country: which country made it ----------
FLAGS = {"대한민국": "🇰🇷 한국", "미국": "🇺🇸 미국", "독일": "🇩🇪 독일", "영국": "🇬🇧 영국", "프랑스": "🇫🇷 프랑스",
         "러시아": "🇷🇺 러시아", "스웨덴": "🇸🇪 스웨덴", "캐나다": "🇨🇦 캐나다", "브라질": "🇧🇷 브라질", "중국": "🇨🇳 중국",
         "스위스": "🇨🇭 스위스"}
COUNTRY = {"kf-21": "대한민국", "t-50": "대한민국", "surion": "대한민국", "buhwal": "대한민국",
           "boeing-747": "미국", "f-22": "미국", "wright-flyer": "미국", "chinook": "미국", "sr-71": "미국", "cessna-172": "미국",
           "rafale": "프랑스", "bleriot-xi": "프랑스", "as350": "프랑스",
           "spitfire": "영국", "harrier": "영국", "tiger-moth": "영국",
           "fokker-dr1": "독일", "graf-zeppelin": "독일",
           "su-27": "러시아", "mi-26": "러시아", "ka-32": "러시아",
           "gripen": "스웨덴", "cl-415": "캐나다", "twin-otter": "캐나다", "embraer-e190": "브라질",
           "comac-c919": "중국", "solar-impulse": "스위스"}
MAIN = ["대한민국", "미국", "프랑스", "영국", "독일", "러시아"]
for i, c in COUNTRY.items():
    name = items[i]["name"]
    wrongs = rng.sample([x for x in MAIN if x != c], 2)
    choices, ans = text_choices(FLAGS[c], [FLAGS[w] for w in wrongs])
    add("country", f"{name}{eun(name)} 어느 나라 비행기일까요?", thumb(i), choices, ans,
        f"{name}{eun(name)} {FLAGS[c].split(' ', 1)[1]}에서 만들었어요. {FLAGS[c].split(' ')[0]}", i)

# ---------- 2. compare: three pictures, pick the oldest / fastest / biggest ----------
def compare(question, values, pick_max, unit_text, n):
    ids = list(values)
    made = 0
    while made < n:
        three = rng.sample(ids, 3)
        vals = sorted(values[x] for x in three)
        # values must be clearly apart so the answer is not a coin flip
        if vals[1] - vals[0] < 0.25 * vals[2] or vals[2] - vals[1] < 0.25 * vals[2]:
            continue
        best = (max if pick_max else min)(three, key=lambda x: values[x])
        rng.shuffle(three)
        key = (question, tuple(sorted(three)))
        if any(q.get("_key") == key for q in out):
            continue
        add("compare", question, None,
            [{"text": items[x]["name"], "image": thumb(x)} for x in three], three.index(best),
            unit_text(best), best)
        out[-1]["_key"] = key
        made += 1

YEAR = {i: int(t["facts"][0][2]) for i, t in items.items()}
AGE = {i: 2026 - y for i, y in YEAR.items()
       if i in ("wright-flyer", "bleriot-xi", "fokker-dr1", "spirit-of-st-louis", "dc-3", "piper-cub", "bell-47",
                "boeing-707", "boeing-747", "concorde", "f-16", "airbus-a320", "boeing-787", "kf-21", "beluga-xl", "surion")}
compare("이 중에서 가장 먼저 하늘을 난 비행기는 무엇일까요?", AGE, True,
        lambda b: f"{items[b]['name']}{eun(items[b]['name'])} {YEAR[b]}년에 처음 날았어요. 셋 중에 가장 먼저예요! 🎂", 6)
SPEED_KMH = {"sr-71": 3540, "concorde": 2180, "f-15": 2650, "harrier": 1180, "p-51": 703, "spitfire": 595,
             "piper-cub": 140, "boeing-747": 990, "atr-72": 510, "robinson-r44": 240, "chinook": 315, "bell-x1": 1541}
compare("이 중에서 가장 빠른 비행기는 무엇일까요?", SPEED_KMH, True,
        lambda b: f"{items[b]['name']}{eun(items[b]['name'])} 시속 약 {SPEED_KMH[b]:,}km까지 날 수 있어요. 셋 중에 가장 빨라요! 🚀", 6)
SEATS = {"airbus-a380": 853, "boeing-747": 416, "boeing-737": 189, "airbus-a220": 130, "atr-72": 72,
         "dc-3": 32, "cessna-172": 4, "robinson-r44": 4, "boeing-777x": 426, "embraer-e190": 100}
compare("이 중에서 사람을 가장 많이 태울 수 있는 비행기는 무엇일까요?", SEATS, True,
        lambda b: f"{items[b]['name']}에는 {SEATS[b]}명까지 탈 수 있어요. 셋 중에 가장 많아요! 👥", 5)

# ---------- 3. fact: hand-written from the stories and fun facts ----------
FACTS = [
    ("boeing-747", "보잉 747의 별명은 무엇일까요?", "점보 제트", ["꼬마 제트", "번개 제트"], "커다래서 '점보'라고 불러요. 머리 부분이 2층이에요."),
    ("airbus-a380", "세계에서 가장 큰 여객기는 무엇일까요?", "에어버스 A380", ["보잉 737", "ATR 72"], "위층과 아래층 모두 손님 자리인 2층 비행기예요. ✈️"),
    ("boeing-787", "보잉 787 창문은 어떻게 어둡게 만들까요?", "버튼을 눌러요", ["커튼을 쳐요", "스티커를 붙여요"], "버튼을 누르면 유리 색이 스르르 어두워져요. 🪟"),
    ("boeing-777x", "보잉 777X는 공항에서 날개 끝을 어떻게 할까요?", "위로 접어요", ["떼어 내요", "물에 담가요"], "날개가 너무 길어서 땅에서는 접고, 날기 전에 다시 펴요."),
    ("airbus-a350", "에어버스 A350은 무엇을 쓴 것처럼 보일까요?", "선글라스", ["모자", "목도리"], "조종석 창문 둘레가 까맣게 칠해져 있어요. 🕶️"),
    ("airbus-a320", "A320 조종사는 무엇으로 조종할까요?", "작은 막대", ["커다란 운전대", "자전거 손잡이"], "게임기 같은 작은 막대로 조종해요. 🕹️"),
    ("atr-72", "ATR 72는 무엇을 돌려서 날까요?", "프로펠러", ["바퀴", "풍선"], "이름의 72는 탈 수 있는 손님 수예요."),
    ("boeing-737", "세계에서 가장 많이 만든 여객기는 무엇일까요?", "보잉 737", ["콩코드", "에어버스 A380"], "60년 가까이 계속 새 모습으로 만들어지고 있어요."),
    ("kf-21", "우리나라가 직접 만든 최신 전투기는 무엇일까요?", "KF-21 보라매", ["F-14 톰캣", "스핏파이어"], "2022년에 처음 하늘을 날았어요. 🇰🇷"),
    ("kf-21", "'보라매'는 어떤 새일까요?", "사냥을 배운 어린 매", ["펭귄", "참새"], "KF-21의 이름이 보라매예요. 🦅"),
    ("t-50", "우리 공군 곡예비행팀의 이름은 무엇일까요?", "블랙이글스", ["레드불스", "화이트타이거즈"], "T-50 비행기로 하늘에 하트를 그려요. 💙"),
    ("f-35", "F-35 같은 '스텔스' 비행기는 무엇을 잘할까요?", "레이더에 숨기", ["물에 뜨기", "노래 부르기"], "레이더에 잘 잡히지 않아서 숨바꼭질을 잘해요. 🙈"),
    ("fa-18", "슈퍼 호넷은 어디에서 뜨고 내릴까요?", "바다 위 항공모함", ["기찻길", "지붕 위"], "커다란 새총 같은 장치가 2초 만에 하늘로 밀어 줘요. 🚢"),
    ("f-14", "F-14 톰캣의 날개는 어떻게 될까요?", "앞뒤로 움직여요", ["떨어져요", "빙글빙글 돌아요"], "빨리 날 땐 접고, 천천히 날 땐 활짝 펴요."),
    ("rafale", "'라팔'은 무슨 뜻일까요?", "돌풍", ["무지개", "눈사람"], "갑자기 세게 부는 바람이라는 프랑스 말이에요. 💨"),
    ("gripen", "그리펜은 어떤 동물에서 따온 이름일까요?", "그리핀(독수리 머리, 사자 몸)", ["유니콘", "용"], "전설 속 동물 이름이에요."),
    ("su-27", "Su-27이 머리를 번쩍 드는 묘기의 이름은 무엇일까요?", "코브라 기동", ["토끼 기동", "거북이 기동"], "코브라처럼 고개를 들었다가 다시 날아가요. 🐍"),
    ("harrier", "해리어는 어떻게 떠오를까요?", "제자리에서 똑바로 위로", ["뒤로 달려서", "물속에서"], "엔진 바람을 아래로 돌려서 떠올라요."),
    ("surion", "우리나라가 만든 헬리콥터는 무엇일까요?", "수리온", ["치누크", "아파치"], "'수리'와 100을 뜻하는 '온'을 합친 이름이에요. 🚁"),
    ("chinook", "치누크에는 큰 회전 날개가 몇 개 있을까요?", "2개", ["1개", "5개"], "앞뒤 날개가 반대로 돌아서 꼬리 날개가 필요 없어요."),
    ("doctor-heli", "아픈 사람을 병원으로 빨리 데려가는 헬리콥터는 무엇일까요?", "닥터헬기", ["스카이크레인", "블랙버드"], "하늘을 나는 응급실이에요. 🏥"),
    ("skycrane", "스카이크레인은 산불이 나면 무엇을 할까요?", "물을 뿌려요", ["모래를 쌓아요", "노래를 불러요"], "욕조 50개만큼 물을 실어 날라요. 💧"),
    ("mi-26", "세계에서 가장 큰 헬리콥터는 무엇일까요?", "밀 Mi-26", ["로빈슨 R44", "벨 47"], "다른 헬리콥터를 매달고 날 만큼 힘이 세요."),
    ("osprey", "오스프리는 무엇과 무엇을 합친 비행기일까요?", "헬리콥터와 비행기", ["배와 자동차", "기차와 버스"], "프로펠러를 앞으로 기울이면 비행기처럼 날아요. 🔄"),
    ("ka-32", "카모프 Ka-32의 회전 날개는 어떻게 달려 있을까요?", "위아래 두 층", ["옆에 하나씩", "꼬리에만"], "우리나라 산림청이 산불을 끌 때 써요. 🌲"),
    ("as350", "에베레스트 꼭대기에 내려앉은 헬리콥터는 무엇일까요?", "에어버스 AS350", ["CH-47 치누크", "밀 Mi-26"], "2005년, 세상에서 가장 높은 산에 내려앉았어요. 🏔️"),
    ("wright-flyer", "세계에서 처음으로 엔진 비행기를 날린 사람은 누구일까요?", "라이트 형제", ["린드버그", "블레리오"], "1903년, 12초 동안 하늘을 날았어요."),
    ("wright-flyer", "라이트 플라이어의 첫 비행은 얼마나 길었을까요?", "12초", ["12시간", "12일"], "짧았지만 이것이 비행기 역사의 시작이에요. ⏱️"),
    ("fokker-dr1", "포커 Dr.I의 날개는 몇 겹일까요?", "3겹", ["1겹", "5겹"], "'붉은 남작'이 빨갛게 칠해 탄 비행기예요. 🔴"),
    ("spirit-of-st-louis", "스피릿 오브 세인트루이스에 없었던 것은 무엇일까요?", "앞 창문", ["날개", "프로펠러"], "앞에 커다란 기름통이 있어서 옆 창문으로 앞을 봤어요."),
    ("ford-trimotor", "포드 트라이모터의 별명은 무엇일까요?", "양철 거위", ["황금 독수리", "솜사탕"], "엔진 3개를 단 옛날 여객기예요. 🪿"),
    ("piper-cub", "파이퍼 컵은 무슨 색으로 유명할까요?", "노란색", ["보라색", "검은색"], "그 노란색 이름이 '컵 옐로'예요. 💛"),
    ("constellation", "록히드 컨스텔레이션의 꼬리 날개는 몇 개일까요?", "3개", ["1개", "10개"], "멀리서도 금방 알아볼 수 있어요."),
    ("concorde", "소리보다 빠르게 날던 여객기는 무엇일까요?", "콩코드", ["DC-3", "파이퍼 컵"], "런던에서 뉴욕까지 3시간 반이면 갔어요. 💨"),
    ("bell-x1", "벨 X-1은 어떻게 하늘로 올라갔을까요?", "큰 비행기 배에 매달려서", ["풍선에 묶여서", "새총으로"], "떨어지면서 로켓을 켜고 소리보다 빠르게 날았어요."),
    ("buhwal", "우리나라 사람들이 처음 만든 비행기의 이름은 무엇일까요?", "부활호", ["보라매", "수리온"], "1953년에 만들었어요. 🇰🇷"),
    ("graf-zeppelin", "그라프 체펠린은 무엇으로 하늘에 떴을까요?", "가스를 채운 커다란 풍선", ["프로펠러 날개 하나", "로켓"], "1929년에 지구를 한 바퀴 돌았어요. 🎈"),
    ("an-225", "'므리야'는 무슨 뜻일까요?", "꿈", ["바다", "구름"], "바퀴가 32개나 달린 거대한 비행기예요. 💭"),
    ("beluga-xl", "벨루가 XL은 어떤 동물을 닮았을까요?", "흰고래", ["코끼리", "기린"], "눈과 웃는 입이 그려져 있어요. 🐳"),
    ("cl-415", "소방 비행기 CL-415는 물을 어디에서 담을까요?", "호수나 바다", ["수영장 수도꼭지", "구름"], "물 위를 스치듯 날면서 12초 만에 가득 담아요."),
    ("e-3", "E-3 센트리가 등에 업고 있는 것은 무엇일까요?", "둥근 레이더", ["수영장", "작은 비행기"], "빙글빙글 돌며 멀리 있는 비행기를 찾아요. 📡"),
    ("air-force-one", "에어포스 원은 누가 타는 비행기일까요?", "미국 대통령", ["우주 비행사", "산타 할아버지"], "보잉 747을 특별하게 고쳐 만들었어요."),
    ("kc-330", "공중급유기는 무슨 일을 할까요?", "날면서 다른 비행기에 기름 넣기", ["구름 만들기", "사진 찍기"], "그래서 '하늘의 주유소'라고 불러요. ⛽"),
    ("solar-impulse", "솔라 임펄스는 무엇으로 날까요?", "햇빛", ["석탄", "바람개비"], "기름 한 방울 없이 지구를 한 바퀴 돌았어요. ☀️"),
    ("stratolaunch", "날개가 가장 긴 비행기는 무엇일까요?", "스트래토런치 로크", ["세스나 172", "파이퍼 J-3 컵"], "날개가 축구장 길이보다 길어요. ⚽"),
    ("sr-71", "사람이 타는 제트 비행기 중 가장 빠른 것은 무엇일까요?", "SR-71 블랙버드", ["보잉 747", "DC-3"], "너무 빨라서 몸이 뜨거워지고 조금 늘어나요. 🔥"),
    ("twin-otter", "수상비행기는 바퀴 대신 무엇을 달까요?", "플로트", ["스키", "썰매 날"], "배처럼 생긴 플로트로 물 위에 뜨고 내려요. 🌊"),
    ("cessna-172", "세계에서 가장 많이 만든 비행기는 무엇일까요?", "세스나 172", ["콩코드", "에어버스 A380"], "4만 대도 넘게 만들었어요."),
    ("global-hawk", "글로벌 호크에는 누가 탈까요?", "아무도 안 타요", ["조종사 10명", "강아지"], "땅에서 조종하는 무인 비행기예요."),
]
for i, q, right, wrongs, explain in FACTS:
    choices, ans = text_choices(right, wrongs)
    add("fact", q, None if right == items[i]["name"] else thumb(i), choices, ans, explain, i)

for q in out:
    q.pop("_key", None)
(ROOT / "data/quiz.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
import collections
print(len(out), collections.Counter(q["kind"] for q in out))
