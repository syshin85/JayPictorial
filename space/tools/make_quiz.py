#!/usr/bin/env python3
"""Writes data/quiz.json for 우주 퀴즈 (same shape as train/data/quiz.json).

Photo questions (name, country, compare) come from data/space.json; the fact questions are
hand-written below from each item's story and fun fact. The random seed is fixed, so running it
again gives the same quiz unless the lists here change.

Usage: python3 tools/make_quiz.py
"""
import json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data/space.json").read_text())
items = {t["id"]: t for t in data["items"]}
rng = random.Random(7)
thumb = lambda i: f"assets/items/{i}/thumb.jpg"
out = []

def eun(name):
    """은/는 after a name."""
    ch = name[-1]
    return "은" if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 else "는"

def add(kind, question, image, choices, answer, explain, item):
    out.append({"id": f"q{len(out)+1:03d}", "kind": kind, "question": question, "image": image,
                "choices": choices, "answer": answer, "explain": explain, "item": item})

def text_choices(right, wrongs):
    c = [right] + wrongs
    rng.shuffle(c)
    return [{"text": x, "image": None} for x in c], c.index(right)

# ---------- 1. name: photo → name, wrong answers from the same section ----------
NAME = ["sun", "mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune",
        "moon", "pluto", "comet", "asteroid", "meteor", "europa", "titan",
        "milky-way", "andromeda", "black-hole", "orion-nebula", "pleiades",
        "saturn-v", "falcon-9", "starship", "nuri", "sls", "soyuz-rocket",
        "apollo-11", "space-shuttle", "iss", "crew-dragon", "soyuz-spacecraft", "tiangong", "lrv",
        "sputnik-1", "hubble", "jwst", "starlink",
        "curiosity", "ingenuity", "voyager-1", "lunokhod-1", "juno", "cassini"]
# pairs that look too much alike in a small photo are never offered together
LOOKALIKE = [{"uranus", "neptune"}, {"milky-way", "andromeda"}, {"curiosity", "perseverance"},
             {"space-shuttle", "buran"}, {"sls", "new-glenn"}, {"soyuz-rocket", "soyuz-spacecraft"},
             {"falcon-9", "new-glenn"}, {"crew-dragon", "orion"}]
for i in NAME:
    t = items[i]
    pool = [x for x in data["items"] if x["section"] == t["section"] and x["id"] != i
            and {i, x["id"]} not in LOOKALIKE]
    wrongs = [x["name"] for x in rng.sample(pool, 2)]
    choices, ans = text_choices(t["name"], wrongs)
    add("name", "이것의 이름은 무엇일까요?", thumb(i), choices, ans, f"{t['name']} — {t['subtitle']}!", i)

# ---------- 2. country: which country made it ----------
FLAGS = {"대한민국": "🇰🇷 한국", "미국": "🇺🇸 미국", "중국": "🇨🇳 중국", "일본": "🇯🇵 일본",
         "러시아": "🇷🇺 러시아", "유럽": "🇪🇺 유럽", "인도": "🇮🇳 인도", "뉴질랜드": "🇳🇿 뉴질랜드"}
KIND = {"rockets": "로켓", "spacecraft": "우주선", "satellites": "위성", "rovers": "탐사선"}
COUNTRY = {"nuri": "대한민국", "naro": "대한민국", "kitsat-1": "대한민국", "danuri": "대한민국",
           "chollian-2a": "대한민국", "long-march-5": "중국", "shenzhou": "중국", "yutu-2": "중국",
           "h-2a": "일본", "hayabusa2": "일본", "ariane-5": "유럽", "rosetta": "유럽",
           "chandrayaan-3": "인도", "electron": "뉴질랜드", "soyuz-rocket": "러시아",
           "saturn-v": "미국", "apollo-11": "미국", "curiosity": "미국"}
KIND_OVERRIDE = {"danuri": "탐사선", "yutu-2": "로봇", "curiosity": "로봇"}
MAIN = ["대한민국", "미국", "중국", "일본", "러시아", "유럽"]
for i, c in COUNTRY.items():
    t = items[i]
    kind = KIND_OVERRIDE.get(i, KIND[t["section"]])
    wrongs = rng.sample([x for x in MAIN if x != c], 2)
    choices, ans = text_choices(FLAGS[c], [FLAGS[w] for w in wrongs])
    josa = eun(t["name"])
    name = t["name"]
    add("country", f"{name}{josa} 어느 나라 {kind}일까요?", thumb(i), choices, ans,
        f"{name}{josa} {FLAGS[c].split(' ', 1)[1]}에서 만들었어요. {FLAGS[c].split(' ')[0]}", i)

# ---------- 3. compare: three pictures, pick the biggest / tallest / closest ----------
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

SIZE = {"mercury": 0.4, "mars": 0.5, "earth": 1, "uranus": 4, "saturn": 9, "jupiter": 11, "sun": 109}
compare("이 중에서 누가 가장 클까요?", SIZE, True,
        lambda b: f"{items[b]['name']}{eun(items[b]['name'])} 지구보다 {SIZE[b]:g}배 커요. 셋 중에 가장 커요! 🌟", 5)
ORDER = {"mercury": 1, "venus": 2, "earth": 3, "mars": 4, "jupiter": 5, "saturn": 6, "uranus": 7, "neptune": 8}
compare("이 중에서 태양에 가장 가까운 행성은 무엇일까요?", ORDER, False,
        lambda b: f"{items[b]['name']}{eun(items[b]['name'])} 태양에서 {ORDER[b]}번째 행성이에요. ☀️", 4)
HEIGHT = {"starship": 120, "saturn-v": 111, "sls": 98, "falcon-9": 70, "long-march-5": 57,
          "ariane-5": 52, "nuri": 47, "soyuz-rocket": 46, "naro": 33, "electron": 18}
compare("이 중에서 가장 키가 큰 로켓은 무엇일까요?", HEIGHT, True,
        lambda b: f"{items[b]['name']}의 높이는 약 {HEIGHT[b]}m예요. 셋 중에 가장 커요! 🚀", 6)

# ---------- 4. fact: hand-written from the stories and fun facts ----------
FACTS = [
    ("sun", "태양은 무엇일까요?", "스스로 빛을 내는 별", ["행성", "지구의 달"], "태양은 스스로 빛을 내는 별이에요. ☀️"),
    ("mercury", "태양에서 가장 가까운 행성은 무엇일까요?", "수성", ["화성", "토성"], "수성은 태양에서 1번째 행성이에요."),
    ("venus", "'샛별'이라고도 부르는 아주 밝은 행성은 무엇일까요?", "금성", ["목성", "해왕성"], "금성은 새벽과 저녁 하늘에서 아주 밝게 빛나요. ✨"),
    ("earth", "지구가 우주에서 파랗게 보이는 까닭은 무엇일까요?", "바다가 많아서", ["파란 페인트를 칠해서", "파란 별이라서"], "지구 표면의 약 70%가 바다예요. 🌊"),
    ("mars", "'붉은 행성'이라고 부르는 행성은 무엇일까요?", "화성", ["금성", "천왕성"], "화성의 땅은 녹슨 쇠처럼 붉어요."),
    ("jupiter", "목성의 빨간 점 '대적점'은 무엇일까요?", "아주 큰 폭풍", ["커다란 화산", "빨간 바다"], "대적점은 지구보다 큰 폭풍이에요. 🌀"),
    ("saturn", "커다란 고리로 유명한 행성은 무엇일까요?", "토성", ["화성", "수성"], "토성의 고리는 얼음과 돌 조각들로 되어 있어요. 🪐"),
    ("uranus", "옆으로 누운 채로 태양 주위를 도는 행성은 무엇일까요?", "천왕성", ["지구", "목성"], "천왕성은 옛날에 크게 부딪혀서 옆으로 누웠대요."),
    ("neptune", "태양에서 가장 먼 행성은 무엇일까요?", "해왕성", ["토성", "금성"], "해왕성은 태양에서 8번째, 가장 먼 행성이에요."),
    ("moon", "달에 가면 몸무게는 어떻게 될까요?", "가벼워져요", ["무거워져요", "똑같아요"], "달에서는 몸무게가 지구의 6분의 1이 돼요. 깡충깡충! 🌙"),
    ("moon", "달은 어떻게 빛날까요?", "햇빛을 받아서", ["스스로 불을 내서", "전기를 켜서"], "달은 스스로 빛을 내지 않고 햇빛을 받아서 빛나요."),
    ("pluto", "명왕성에서 발견한 커다란 무늬는 무슨 모양일까요?", "하트 모양", ["별 모양", "네모 모양"], "뉴호라이즌스가 명왕성의 하트 무늬를 찍었어요. 💗"),
    ("comet", "혜성의 꼬리는 어느 쪽을 향할까요?", "태양의 반대쪽", ["태양 쪽", "언제나 아래쪽"], "태양에서 나오는 바람이 꼬리를 밀어내요. ☄️"),
    ("asteroid", "소행성이 많이 모여 있는 곳은 어디일까요?", "화성과 목성 사이", ["지구와 달 사이", "태양 안"], "그곳을 '소행성대'라고 해요."),
    ("meteor", "별똥별은 무엇일까요?", "작은 돌이 타는 빛", ["떨어지는 진짜 별", "비행기 불빛"], "우주의 작은 돌 부스러기가 공기 속에서 타는 빛이에요. 🌠"),
    ("europa", "유로파의 얼음 아래에는 무엇이 있을까요?", "커다란 바다", ["뜨거운 용암", "커다란 동굴 도시"], "유로파의 얼음 아래에는 큰 바다가 숨어 있을 거래요."),
    ("milky-way", "우리 태양계가 사는 은하의 이름은 무엇일까요?", "우리은하", ["안드로메다 은하", "오리온 성운"], "깜깜한 밤하늘의 은하수가 우리은하예요. 🌌"),
    ("black-hole", "빛도 빠져나올 수 없는 곳은 어디일까요?", "블랙홀", ["태양", "달"], "블랙홀은 끌어당기는 힘이 너무 세요."),
    ("orion-nebula", "오리온 성운에서는 무슨 일이 일어날까요?", "아기 별이 태어나요", ["로켓이 발사돼요", "비가 내려요"], "오리온 성운은 아기 별 놀이터예요. ⭐"),
    ("sirius", "밤하늘에서 가장 밝은 별은 무엇일까요?", "시리우스", ["북극성", "안드로메다 은하"], "시리우스는 큰개자리에 있는 가장 밝은 별이에요."),
    ("saturn-v", "사람을 달에 보낸 로켓은 무엇일까요?", "새턴 V", ["누리호", "일렉트론"], "새턴 V가 아폴로 우주인들을 달까지 보냈어요. 🌕"),
    ("falcon-9", "다시 돌아와 똑바로 서서 착륙하는 로켓은 무엇일까요?", "팰컨 9", ["나로호", "새턴 V"], "팰컨 9은 돌아와서 또 날아가요!"),
    ("nuri", "우리나라 기술로 만든 첫 우주 로켓은 무엇일까요?", "누리호", ["새턴 V", "스타십"], "누리호는 고흥 나로우주센터에서 발사해요. 🇰🇷"),
    ("starship", "발사탑의 '젓가락 팔'이 공중에서 붙잡은 로켓은 무엇일까요?", "스타십", ["소유즈 로켓", "나로호"], "2024년에 젓가락 팔이 스타십 로켓을 붙잡았어요!"),
    ("ariane-5", "제임스 웹 우주망원경을 쏘아 올린 로켓은 무엇일까요?", "아리안 5", ["누리호", "일렉트론"], "2021년 크리스마스에 쏘아 올렸어요. 🎄"),
    ("vostok-1", "처음으로 우주에 간 사람은 누구일까요?", "유리 가가린", ["닐 암스트롱", "이소연"], "가가린은 1961년 보스토크 1호를 타고 우주에 갔어요."),
    ("apollo-11", "처음으로 달 위를 걸은 사람은 누구일까요?", "닐 암스트롱", ["유리 가가린", "존 글렌"], "1969년 아폴로 11호 때 달 위를 걸었어요. 👣"),
    ("space-shuttle", "돌아올 때 비행기처럼 활주로에 내려앉은 우주선은 무엇일까요?", "우주왕복선", ["보스토크 1호", "크루 드래건"], "우주왕복선은 여러 번 다시 쓸 수 있었어요. ✈️"),
    ("iss", "우주정거장의 우주인은 잠잘 때 어떻게 할까요?", "침낭을 벽에 묶고 자요", ["침대에 누워 자요", "의자에 앉아 자요"], "몸이 둥둥 떠다녀서 침낭을 묶어 놓아요. 😴"),
    ("crew-dragon", "크루 드래건 안에는 버튼 대신 무엇이 있을까요?", "커다란 터치스크린", ["운전대", "피아노 건반"], "스마트폰처럼 눌러서 조종해요. 📱"),
    ("soyuz-spacecraft", "우리나라 첫 우주인 이소연이 탄 우주선은 무엇일까요?", "소유즈 우주선", ["아폴로 11호", "우주왕복선"], "2008년에 소유즈를 타고 우주정거장에 다녀왔어요."),
    ("tiangong", "'하늘의 궁전'이라는 뜻의 우주정거장은 무엇일까요?", "톈궁", ["국제우주정거장", "부란"], "톈궁은 중국의 우주정거장이에요."),
    ("buran", "사람 없이 컴퓨터가 혼자 조종해서 착륙한 우주왕복선은 무엇일까요?", "부란", ["크루 드래건", "아폴로 11호"], "부란은 1988년에 딱 한 번 우주에 다녀왔어요."),
    ("sputnik-1", "세계 최초의 인공위성은 무엇일까요?", "스푸트니크 1호", ["허블 우주망원경", "스타링크"], "비치볼만 한 이 위성으로 우주 시대가 시작됐어요."),
    ("hubble", "허블 우주망원경이 고장 났을 때 어떻게 했을까요?", "우주인이 고치러 갔어요", ["새로 다시 만들었어요", "그냥 두었어요"], "우주왕복선을 타고 5번이나 고치러 갔어요. 🔧"),
    ("jwst", "제임스 웹 우주망원경의 거울은 무슨 색일까요?", "금색", ["까만색", "빨간색"], "금으로 얇게 덮은 거울 18개가 벌집처럼 모여 있어요. ✨"),
    ("gps", "GPS 위성은 무슨 일을 할까요?", "길을 알려 줘요", ["비를 내려 줘요", "별을 만들어요"], "내비게이션과 휴대폰 지도가 GPS 신호를 써요. 🗺️"),
    ("danuri", "우리나라가 처음으로 달에 보낸 탐사선은 무엇일까요?", "다누리", ["우리별 1호", "천리안 2A호"], "다누리는 달 둘레를 돌며 사진을 찍었어요. 🌕"),
    ("chollian-2a", "천리안 2A호는 무슨 일을 할까요?", "날씨를 알려 줘요", ["인터넷을 보내 줘요", "달에 착륙해요"], "일기예보의 구름 사진을 천리안이 찍어요. ⛅"),
    ("starlink", "줄지어 날아가서 '우주 기차'처럼 보이는 위성은 무엇일까요?", "스타링크", ["허블 우주망원경", "다누리"], "스타링크는 인터넷 신호를 보내 주는 위성이에요. 🚂"),
    ("kitsat-1", "우리나라 첫 번째 인공위성은 무엇일까요?", "우리별 1호", ["스푸트니크 1호", "다누리"], "1992년에 발사했어요. 🇰🇷"),
    ("curiosity", "큐리오시티는 돌을 조사할 때 무엇을 쏠까요?", "레이저", ["물총", "화살"], "레이저로 돌을 쏘아 무엇으로 되어 있는지 알아내요."),
    ("perseverance", "화성의 바람 소리를 처음 녹음한 로봇은 무엇일까요?", "퍼서비어런스", ["소저너", "루노호트 1호"], "마이크로 화성의 바람 소리를 녹음했어요. 🎤"),
    ("ingenuity", "화성 하늘을 난 헬리콥터는 무엇일까요?", "인저뉴어티", ["큐리오시티", "주노"], "인저뉴어티는 72번이나 날았어요! 🚁"),
    ("voyager-1", "사람이 만든 물건 중에 가장 멀리 간 것은 무엇일까요?", "보이저 1호", ["국제우주정거장", "다누리"], "보이저 1호는 태양계 바깥까지 날아갔어요."),
    ("new-horizons", "명왕성을 처음 가까이에서 본 탐사선은 무엇일까요?", "뉴호라이즌스", ["보이저 1호", "주노"], "2015년에 명왕성 옆을 지나가며 사진을 찍었어요."),
    ("lrv", "아폴로 우주인들이 달에서 운전한 자동차는 무엇일까요?", "월면차", ["큐리오시티", "위투 2호"], "지금도 달 위에 월면차 3대가 세워져 있어요. 🚙"),
    ("yutu-2", "'옥토끼'라는 이름을 가진 달 로봇은 무엇일까요?", "위투 2호", ["루노호트 1호", "소저너"], "위투 2호는 달의 뒷면을 달렸어요. 🐰"),
    ("hayabusa2", "소행성의 흙을 지구로 가져온 탐사선은 무엇일까요?", "하야부사2", ["카시니", "보이저 1호"], "흙이 든 캡슐이 낙하산을 타고 돌아왔어요."),
    ("rosetta", "처음으로 혜성 위에 내려앉은 착륙선은 무엇일까요?", "필레", ["위투 2호", "인저뉴어티"], "로제타가 데려간 필레가 통통 튀다가 내려앉았어요. ☄️"),
    ("cassini", "카시니는 어느 행성을 13년 동안 돌았을까요?", "토성", ["화성", "지구"], "카시니는 토성 사진을 45만 장 넘게 보냈어요. 🪐"),
    ("juno", "주노는 어느 행성을 조사하는 탐사선일까요?", "목성", ["수성", "해왕성"], "주노는 목성의 소용돌이 구름을 가까이에서 찍었어요."),
]
for i, q, right, wrongs, explain in FACTS:
    choices, ans = text_choices(right, wrongs)
    add("fact", q, None if right == items[i]["name"] else thumb(i),
        choices, ans, explain, i)

for q in out:
    q.pop("_key", None)
    if q["item"] == "naro" and q["kind"] == "country":
        q["explain"] = "나로호는 한국이 러시아의 도움을 받아 만들었어요. 🇰🇷"
(ROOT / "data/quiz.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
import collections
print(len(out), collections.Counter(q["kind"] for q in out))
