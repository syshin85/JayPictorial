#!/usr/bin/env python3
"""Writes data/quiz.json for 자동차 퀴즈 (same shape as the train and space quizzes).

Photo questions (country, compare) come from data/cars.json; the fact questions are hand-written
below from each item's story and fun fact. The random seed is fixed, so running it again gives
the same quiz unless the lists here change. No "what is this photo?" questions: the user found
them dull.

Usage: python3 tools/make_quiz.py
"""
import json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data/cars.json").read_text())
items = {t["id"]: t for t in data["items"]}
rng = random.Random(7)
thumb = lambda i: f"assets/items/{i}/thumb.jpg"
out = []

def eun(name):
    """은/는 after a name, also after a digit or a Latin letter read aloud (911 → 일, R → 알)."""
    ch = name[-1].upper()
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
FLAGS = {"대한민국": "🇰🇷 한국", "미국": "🇺🇸 미국", "독일": "🇩🇪 독일", "일본": "🇯🇵 일본", "영국": "🇬🇧 영국",
         "이탈리아": "🇮🇹 이탈리아", "프랑스": "🇫🇷 프랑스", "스웨덴": "🇸🇪 스웨덴", "중국": "🇨🇳 중국"}
COUNTRY = {"pony": "대한민국", "ioniq-5": "대한민국", "hyundai-grandeur": "대한민국", "kia-sorento": "대한민국",
           "tesla-model-3": "미국", "jeep-wrangler": "미국", "ford-mustang": "미국", "tesla-cybertruck": "미국",
           "beetle": "독일", "porsche-911": "독일", "mercedes-g-class": "독일", "bmw-5-series": "독일",
           "prius": "일본", "toyota-corolla": "일본", "nissan-gt-r": "일본",
           "mini": "영국", "range-rover": "영국", "aston-martin-db5": "영국",
           "fiat-500": "이탈리아", "ferrari-f40": "이탈리아", "lamborghini-aventador": "이탈리아",
           "citroen-2cv": "프랑스", "bugatti-chiron": "프랑스", "volvo-xc90": "스웨덴",
           "byd-atto-3": "중국", "xiaomi-su7": "중국"}
MAIN = ["대한민국", "미국", "독일", "일본", "영국", "이탈리아"]
for i, c in COUNTRY.items():
    name = items[i]["name"]
    wrongs = rng.sample([x for x in MAIN if x != c], 2)
    choices, ans = text_choices(FLAGS[c], [FLAGS[w] for w in wrongs])
    add("country", f"{name}{eun(name)} 어느 나라 자동차일까요?", thumb(i), choices, ans,
        f"{name}{eun(name)} {FLAGS[c].split(' ', 1)[1]}에서 만들었어요. {FLAGS[c].split(' ')[0]}", i)

# ---------- 2. compare: three pictures, pick the oldest / longest ----------
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

YEAR = {"ford-model-t": 1908, "beetle": 1938, "citroen-2cv": 1948, "fiat-500": 1957, "mini": 1959,
        "porsche-911": 1964, "vw-golf": 1974, "pony": 1975, "prius": 1997, "tesla-model-3": 2017,
        "ioniq-5": 2021, "tesla-cybertruck": 2023, "xiaomi-su7": 2024}
AGE = {i: 2026 - y for i, y in YEAR.items()}
compare("이 중에서 가장 먼저 나온 자동차는 무엇일까요?", AGE, True,
        lambda b: f"{items[b]['name']}{eun(items[b]['name'])} {YEAR[b]}년에 처음 나왔어요. 셋 중에 가장 먼저예요! 🎂", 6)
LENGTH = {"kart": 1.8, "mini": 3, "sonata": 4.9, "carnival": 5.2, "city-bus": 11, "semi-truck": 16,
          "articulated-bus": 18, "road-train": 53}
compare("이 중에서 가장 긴 자동차는 무엇일까요?", LENGTH, True,
        lambda b: f"{items[b]['name']}의 길이는 약 {LENGTH[b]:g}m예요. 셋 중에 가장 길어요! 📏", 6)

# ---------- 3. fact: hand-written from the stories and fun facts ----------
FACTS = [
    ("pony", "우리나라가 처음으로 만든 자동차는 무엇일까요?", "현대 포니", ["기아 카니발", "현대 그랜저"], "포니는 1975년에 나왔어요. 이름은 '조랑말'이라는 뜻이에요. 🐴"),
    ("carnival", "카니발의 옆문은 어떻게 열릴까요?", "옆으로 미끄러지듯 열려요", ["위로 열려요", "뒤로 떨어져요"], "미닫이문이라서 버튼만 누르면 혼자서 열리고 닫혀요."),
    ("ioniq-5", "아이오닉 5는 무엇으로 달릴까요?", "전기", ["휘발유", "수소"], "아이오닉 5는 전기 자동차예요. 캠핑장에서 전등을 켤 수도 있어요. 🔋"),
    ("prius", "프리우스는 브레이크를 밟을 때 무슨 일을 할까요?", "배터리를 다시 채워요", ["불꽃이 튀어요", "음악이 나와요"], "멈추는 힘으로 전기를 만들어 배터리를 채워요."),
    ("beetle", "폭스바겐 비틀은 어떤 곤충을 닮았을까요?", "딱정벌레", ["나비", "개미"], "'비틀'은 영어로 딱정벌레라는 뜻이에요. 🐞"),
    ("ford-model-t", "포드 모델 T는 한동안 무슨 색으로만 만들었을까요?", "검은색", ["빨간색", "하얀색"], "검은 페인트가 가장 빨리 말라서 더 빨리 만들 수 있었대요."),
    ("citroen-2cv", "시트로엥 2CV를 만들 때 깨지면 안 됐던 것은 무엇일까요?", "바구니 속 달걀", ["유리창", "자동차 열쇠"], "달걀 바구니를 싣고 밭을 가로질러도 안 깨져야 했대요! 🥚"),
    ("fiat-500", "옛날 피아트 500의 지붕은 무엇으로 되어 있었을까요?", "천", ["유리", "나무"], "천 지붕을 둘둘 말아 열면 하늘이 보였어요."),
    ("volvo-xc90", "어깨까지 오는 안전벨트를 처음 만든 회사는 어디일까요?", "볼보", ["페라리", "테슬라"], "볼보는 다른 회사들도 공짜로 쓰게 했어요. 모두의 안전을 위해서요!"),
    ("honda-n-box", "일본의 작은 경차는 무슨 색 번호판을 달까요?", "노란색", ["빨간색", "보라색"], "혼다 N-BOX 같은 경차는 노란 번호판을 달아요."),
    ("tesla-model-y", "2023년에 세계에서 가장 많이 팔린 자동차는 무엇일까요?", "테슬라 모델 Y", ["포드 모델 T", "피아트 500"], "전기차인 모델 Y가 모든 자동차 가운데 1등을 했어요."),
    ("tesla-cybertruck", "사이버트럭의 겉면은 무엇으로 되어 있을까요?", "은색 스테인리스 강철", ["나무", "플라스틱"], "칠하지 않아서 반짝반짝 은색이에요. ✨"),
    ("genesis-gv80", "제네시스 자동차의 불빛은 어떤 모양일까요?", "두 줄", ["동그라미 하나", "별 모양"], "앞과 뒤의 불빛이 두 줄로 나란히 빛나요."),
    ("bmw-5-series", "BMW 앞 그릴은 무엇을 닮았을까요?", "콩팥 두 개", ["하트 두 개", "별 다섯 개"], "그래서 '키드니(콩팥) 그릴'이라고 불러요."),
    ("mercedes-e-class", "벤츠 로고는 무슨 모양일까요?", "세 꼭지 별", ["달리는 말", "황소"], "땅, 바다, 하늘에서 쓰는 엔진을 만들겠다는 뜻이래요. ⭐"),
    ("toyota-corolla", "한 이름으로 세계에서 가장 많이 팔린 자동차는 무엇일까요?", "토요타 코롤라", ["부가티 시론", "레인지로버"], "코롤라는 5000만 대 넘게 팔렸어요."),
    ("honda-cr-v", "처음 혼다 CR-V 뒷자리 바닥에는 무엇이 들어 있었을까요?", "피크닉 테이블", ["작은 수영장", "피아노"], "꺼내서 펼치면 소풍 식탁이 됐어요! 🧺"),
    ("range-rover", "처음 나온 레인지로버가 전시된 박물관은 어디일까요?", "루브르 박물관", ["공룡 박물관", "기차 박물관"], "아주 멋져서 '예술 작품'처럼 전시됐어요. 🖼️"),
    ("xiaomi-su7", "샤오미는 원래 무엇을 만들던 회사일까요?", "휴대폰", ["비행기", "장난감 블록"], "휴대폰 회사가 처음 만든 전기 자동차가 SU7이에요. 📱"),
    ("byd-atto-3", "BYD는 원래 무엇을 만들던 회사일까요?", "휴대폰 배터리", ["자전거", "운동화"], "지금은 세계에서 전기차를 가장 많이 만드는 회사 중 하나예요."),
    ("ferrari-f40", "1987년에 나왔을 때 세계에서 가장 빨랐던 빨간 차는 무엇일까요?", "페라리 F40", ["피아트 500", "미니"], "F40은 시속 324km까지 달려요. 🏎️"),
    ("lamborghini-aventador", "람보르기니 자동차 이름은 대부분 무엇에서 따왔을까요?", "유명한 투우 소", ["유명한 산", "유명한 노래"], "그래서 람보르기니 로고에도 황소가 있어요. 🐂"),
    ("lamborghini-countach", "'쿤타치'는 무슨 뜻의 말일까요?", "'우와!' 하고 놀랄 때 하는 말", ["'안녕!' 하는 인사", "'잘 자!' 하는 말"], "이탈리아 어느 지방 말로 놀랄 때 하는 말이에요. 😲"),
    ("mercedes-300sl", "300 SL의 문은 무엇처럼 열릴까요?", "갈매기 날개", ["미닫이 창문", "서랍"], "문이 위로 열려서 '걸윙(갈매기 날개)'이라고 불러요. 🕊️"),
    ("ford-mustang", "머스탱의 로고는 무엇일까요?", "달리는 말", ["세 꼭지 별", "황소"], "머스탱은 미국의 야생마예요. 🐎"),
    ("mclaren-f1", "맥라렌 F1의 운전석은 어디에 있을까요?", "가운데", ["왼쪽 뒤", "지붕 위"], "운전석이 가운데에 있고, 양옆에 자리가 하나씩 있어요."),
    ("aston-martin-db5", "애스턴 마틴 DB5는 어느 영화에 나왔을까요?", "007", ["아이언맨", "토이 스토리"], "비밀 요원 007의 자동차예요. 번호판이 빙글 돌아 바뀌어요! 🕵️"),
    ("nissan-gt-r", "닛산 GT-R의 별명은 무엇일까요?", "고질라", ["거북이", "나비"], "경주에서 다른 차들을 모두 이겨서 '고질라'가 되었어요. 🦖"),
    ("audi-r8", "영화 '아이언맨'에서 토니 스타크가 탄 자동차는 무엇일까요?", "아우디 R8", ["현대 포터", "미니"], "엔진이 운전석 뒤에 있는 슈퍼카예요."),
    ("koenigsegg-agera", "코닉세그 공장은 옛날에 무엇이었을까요?", "전투기 비행장", ["초콜릿 공장", "기차역"], "그래서 비행 부대의 '유령' 그림을 자동차에 붙여요. 👻"),
    ("rimac-nevera", "리막 네베라는 무엇으로 달릴까요?", "전기", ["휘발유", "장작"], "바퀴마다 모터가 하나씩, 모두 네 개 있어요. ⚡"),
    ("hyundai-n-vision-74", "N 비전 74는 어떤 자동차를 닮았을까요?", "포니 쿠페", ["버스", "트랙터"], "1974년 포니 쿠페 디자인을 닮았어요."),
    ("f1", "F1 경주 중에 바퀴 네 개를 바꾸는 데 얼마나 걸릴까요?", "약 2초", ["약 1시간", "하루"], "정비하는 사람들이 눈 깜짝할 새 바꿔 끼워요! ⏱️"),
    ("indycar", "인디 500에서 이긴 선수는 무엇을 마실까요?", "우유", ["콜라", "주스"], "우유를 마시며 축하하는 게 전통이에요. 🥛"),
    ("le-mans", "르망 경주는 몇 시간 동안 달릴까요?", "24시간", ["1시간", "10분"], "선수 3명이 번갈아 하루 종일 달려요. 🌙"),
    ("nascar", "나스카 선수는 어디로 차에 타고 내릴까요?", "창문", ["지붕 문", "트렁크"], "무게를 줄이려고 문이 열리지 않아요."),
    ("dragster", "드래그스터는 멈출 때 무엇을 펼칠까요?", "낙하산", ["우산", "날개"], "너무 빨라서 낙하산으로 속도를 줄여요. 🪂"),
    ("formula-e", "포뮬러 E 경주차는 무엇으로 달릴까요?", "전기", ["휘발유", "수소"], "2022년에는 서울에서도 경주가 열렸어요."),
    ("double-decker", "2층 버스로 유명한 도시는 어디일까요?", "런던", ["파리", "도쿄"], "런던의 빨간 2층 버스가 유명해요. 🚌"),
    ("articulated-bus", "굴절 버스는 어디가 꺾일까요?", "가운데", ["지붕", "바퀴"], "가운데 관절이 있어서 긴 버스도 길을 잘 돌아요."),
    ("school-bus", "미국 스쿨버스는 무슨 색일까요?", "노란색", ["빨간색", "검은색"], "멀리서도 잘 보이게 노랗게 칠해요. 💛"),
    ("trolleybus", "트롤리버스는 어디에서 전기를 받을까요?", "위쪽 전깃줄", ["바퀴 밑 땅", "햇빛"], "지붕 위 막대 두 개가 전깃줄에 닿아 있어요."),
    ("semi-truck", "미국에서 트레일러 트럭을 바퀴 수로 부르는 이름은 무엇일까요?", "18 휠러", ["4 휠러", "100 휠러"], "바퀴가 18개라서 '18 휠러'예요."),
    ("monster-truck", "첫 몬스터 트럭의 이름은 무엇일까요?", "빅풋", ["작은 발", "고질라"], "'빅풋'은 큰 발이라는 뜻이에요. 🦶"),
    ("road-train", "로드 트레인은 어느 나라에서 달릴까요?", "오스트레일리아", ["일본", "영국"], "넓은 사막길에서 짐칸 여러 개를 끌고 달려요. 🦘"),
    ("fire-engine", "불이 났을 때 부르는 번호는 무엇일까요?", "119", ["112", "114"], "119에 전화하면 소방차가 달려와요. 🚒"),
    ("police-car", "경찰을 부르는 번호는 무엇일까요?", "112", ["119", "365"], "112에 전화하면 경찰이 도와줘요. 🚓"),
    ("ambulance", "구급차 앞에 'AMBULANCE' 글자를 거꾸로 쓴 까닭은 무엇일까요?", "앞차 거울로 보면 바르게 보여서", ["멋있어 보이려고", "실수로"], "거울에 비치면 글자가 바르게 읽혀요. 🪞"),
    ("ladder-truck", "사다리 소방차는 사다리를 뻗기 전에 무엇을 할까요?", "다리를 내려 땅을 짚어요", ["바퀴를 빼요", "노래를 틀어요"], "그래야 넘어지지 않아요."),
    ("excavator", "굴착기의 윗몸은 몇 도까지 돌 수 있을까요?", "360도 빙글", ["조금도 못 돌아요", "반 바퀴만"], "윗몸이 한 바퀴 빙글 돌아요."),
    ("mixer", "레미콘이 통을 쉬지 않고 돌리는 까닭은 무엇일까요?", "콘크리트가 굳지 않게", ["재미있어서", "소리를 내려고"], "가만두면 돌처럼 굳어 버려요."),
    ("mining-truck", "거대 덤프트럭 운전석에는 어떻게 올라갈까요?", "계단으로", ["사다리차로", "점프해서"], "트럭에 달린 계단을 한참 올라가야 해요."),
    ("forklift", "지게차 뒤에 무거운 쇳덩어리가 달린 까닭은 무엇일까요?", "앞으로 넘어지지 않게", ["더 빨리 달리려고", "장식이라서"], "무거운 짐을 들어도 균형을 잡아 줘요. ⚖️"),
    ("bulldozer", "불도저 앞에 달린 커다란 날은 무엇을 할까요?", "흙을 밀어요", ["물을 뿌려요", "노래를 불러요"], "흙을 밀어서 땅을 평평하게 만들어요."),
    ("garbage-truck", "쓰레기 수거차는 주로 언제 일할까요?", "새벽", ["점심때", "저녁 먹을 때"], "우리가 자는 동안 동네를 깨끗하게 해 줘요. 🌅"),
    ("snowplow", "제설차가 뒤에서 뿌리는 것은 무엇일까요?", "염화칼슘", ["꽃씨", "설탕"], "눈과 얼음을 녹여 줘요. ❄️"),
    ("tractor", "요즘 트랙터는 무엇으로 길을 찾을까요?", "위성 신호", ["별자리", "냄새"], "운전대를 잡지 않아도 밭을 반듯하게 갈아요. 🛰️"),
    ("combine", "콤바인은 무슨 일을 할까요?", "곡식을 거둬요", ["눈을 치워요", "불을 꺼요"], "벼와 밀을 베고 낟알까지 털어 줘요. 🌾"),
    ("ladder-lift", "사다리차는 이삿짐을 어디로 옮길까요?", "창문으로", ["굴뚝으로", "지하로"], "높은 아파트 창문까지 짐판이 오르락내리락해요."),
]
for i, q, right, wrongs, explain in FACTS:
    choices, ans = text_choices(right, wrongs)
    add("fact", q, None if right == items[i]["name"] else thumb(i), choices, ans, explain, i)

for q in out:
    q.pop("_key", None)
(ROOT / "data/quiz.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
import collections
print(len(out), collections.Counter(q["kind"] for q in out))
