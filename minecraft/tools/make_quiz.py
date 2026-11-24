#!/usr/bin/env python3
"""Writes data/quiz.json for 마인크래프트 퀴즈 (same shape as the train, space, car and plane quizzes).

Questions come from data/minecraft.json (what a mob drops, where it lives, who has the most hearts,
what a recipe needs) plus the hand-written fact questions below. The random seed is fixed, so running
it again gives the same quiz unless the lists here change. No "what is this picture?" questions:
the user found them dull.

Usage: python3 tools/make_quiz.py
"""
import json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data/minecraft.json").read_text())
media = json.loads((ROOT / "data/media.json").read_text())
items = {t["id"]: t for t in data["items"]}
book = {s["id"]: s["book"] for s in data["sections"]}
icons = data["icons"]
rng = random.Random(7)
thumb = lambda i: media[i]["images"][0].get("thumb") or media[i]["images"][0]["src"]
out = []

def eun(name):
    """은/는 after a name."""
    ch = name[-1]
    return "은" if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 else "는"

def eul(name):
    ch = name[-1]
    return "을" if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 else "를"

def add(kind, question, image, choices, answer, explain, item):
    out.append({"id": f"q{len(out)+1:03d}", "kind": kind, "question": question, "image": image,
                "choices": choices, "answer": answer, "explain": explain, "item": item})

def text_choices(right, wrongs):
    c = [right] + wrongs
    rng.shuffle(c)
    return [{"text": x, "image": None} for x in c], c.index(right)

def fact(t, k):
    return next((f[2] for f in t["facts"] if f[1] == k), None)

mobs = [t for t in data["items"] if book[t["section"]] == "mobs"]

# ---------- 1. drops: what does it drop ----------
drops = {t["id"]: fact(t, "떨어뜨리는 것") for t in mobs}
drops = {i: d for i, d in drops.items() if d and d != "없음"}
for i in rng.sample(sorted(drops), 16):
    name = items[i]["name"]
    words = set(drops[i].replace(",", " ").replace("와", " ").split())
    wrongs = rng.sample(sorted({d for d in drops.values() if not words & set(d.replace(",", " ").replace("와", " ").split())}), 2)
    choices, ans = text_choices(drops[i], wrongs)
    add("drop", f"{name}{eul(name)} 물리치면 무엇을 떨어뜨릴까요?", thumb(i), choices, ans,
        f"{name}{eun(name)} {drops[i]}{eul(drops[i])} 떨어뜨려요.", i)

# ---------- 2. where does it live ----------
where = {t["id"]: fact(t, "나오는 곳") for t in mobs}
# only real places (not "직접 만들어요", "알에서 태어나요"…), and not ones that fit almost any mob
where = {i: w for i, w in where.items() if not any(x in w for x in ("직접", "에서", "던진 곳", "어디든"))}
special = [i for i, w in where.items() if w not in ("어두운 곳", "풀밭")]
for i in rng.sample(special, 14):
    name = items[i]["name"]
    # wrong places must share no word with the right one ("마을" vs "사막 마을" would be unfair)
    words = set(where[i].replace(",", " ").split())
    wrongs = rng.sample(sorted({w for w in where.values() if not words & set(w.replace(",", " ").split())}), 2)
    choices, ans = text_choices(where[i], wrongs)
    add("where", f"{name}{eun(name)} 어디에서 만날 수 있을까요?", thumb(i), choices, ans,
        f"{name}{eun(name)} {where[i]}에서 만날 수 있어요.", i)

# ---------- 3. most hearts (picture choices) ----------
hearts = {t["id"]: int(fact(t, "체력")) for t in mobs if fact(t, "체력").isdigit()}
done = 0
while done < 10:
    trio = rng.sample(sorted(hearts), 3)
    v = sorted(hearts[i] for i in trio)
    if v[2] < 2 * v[1]:  # clearly apart, so it is not a coin flip
        continue
    best = max(trio, key=hearts.get)
    add("compare", "셋 중에서 체력이 가장 많은 것은?", None,
        [{"text": items[i]["name"], "image": thumb(i)} for i in trio], trio.index(best),
        f"{items[best]['name']}의 체력은 하트 {hearts[best]}칸이에요. ❤️", best)
    done += 1

# ---------- 4. recipes: what do you need ----------
def needs(t):
    r = t["recipe"]
    count = {}
    for row in r["craft"]:
        for c in row:
            if c != " ":
                count[r["key"][c]] = count.get(r["key"][c], 0) + 1
    return " + ".join(f"{icons[k]['name']} {n}개" for k, n in count.items())

crafted = [t for t in data["items"] if t.get("recipe", {}).get("craft")]
recipes = {t["id"]: needs(t) for t in crafted}
for i in rng.sample(sorted(recipes), 14):
    name = items[i]["name"]
    wrongs = rng.sample(sorted({r for r in recipes.values() if r != recipes[i]}), 2)
    choices, ans = text_choices(recipes[i], wrongs)
    add("recipe", f"{name}{eul(name)} 만들려면 무엇이 필요할까요?", thumb(i), choices, ans,
        f"{name}{eun(name)} {recipes[i]}{eul(recipes[i][-1])} 써서 만들어요.", i)

# ---------- 5. facts (hand-written from the stories and tips) ----------
FACTS = [
    ("creeper", "크리퍼가 무서워해서 도망가는 동물은?", "고양이", ["돼지", "닭"], "크리퍼는 고양이를 무서워해요. 🐱"),
    ("enderman", "엔더맨이 화내는 건 언제일까요?", "눈을 마주칠 때", ["노래를 부를 때", "점프할 때"], "엔더맨은 눈을 똑바로 쳐다보면 화를 내요."),
    ("enderman", "엔더맨이 아주 싫어하는 것은?", "물", ["모래", "꽃"], "엔더맨은 물에 닿으면 아파해요. 💧"),
    ("zombie", "좀비가 햇빛을 받으면 어떻게 될까요?", "불이 붙어요", ["더 빨라져요", "잠을 자요"], "좀비와 스켈레톤은 햇빛을 받으면 불이 붙어요. ☀️"),
    ("husk", "햇빛을 받아도 불이 붙지 않는 사막 좀비는?", "허스크", ["드라운드", "스트레이"], "허스크는 사막에 살아서 햇빛에도 끄떡없어요."),
    ("phantom", "팬텀이 오지 않게 하려면 어떻게 해야 할까요?", "침대에서 잠을 자요", ["횃불을 꽂아요", "물을 부어요"], "사흘 밤 넘게 안 자면 팬텀이 와요. 잘 자요! 🛏️"),
    ("piglin", "피글린이 좋아해서 물건과 바꿔 주는 것은?", "금", ["다이아몬드", "흙"], "피글린은 금을 좋아해요. 금 갑옷을 입으면 공격하지 않아요."),
    ("wolf", "늑대를 강아지 친구로 만들려면 무엇을 줄까요?", "뼈", ["사과", "당근"], "뼈를 주면 늑대가 빨간 목걸이를 한 친구가 돼요. 🐶"),
    ("cat", "고양이를 길들이려면 무엇을 줄까요?", "날생선", ["밀", "뼈"], "고양이는 생선을 좋아해요. 🐟"),
    ("parrot", "앵무새에게 절대 주면 안 되는 음식은?", "쿠키", ["씨앗", "밀"], "앵무새는 쿠키를 먹으면 아파요."),
    ("cow", "소에게서 우유를 얻으려면 무엇을 들고 있어야 할까요?", "빈 양동이", ["가위", "그릇"], "빈 양동이를 들고 소를 누르면 우유를 받아요. 🥛"),
    ("sheep", "양의 털을 깎을 때 쓰는 도구는?", "가위", ["삽", "괭이"], "가위로 털을 깎으면 양털이 나와요."),
    ("axolotl", "아주 드물어서 보기 힘든 아홀로틀 색깔은?", "파란색", ["분홍색", "갈색"], "파란 아홀로틀은 1200마리 중 한 마리꼴로 태어나요."),
    ("iron-golem", "철 골렘을 만들려면 철 블록과 함께 무엇이 필요할까요?", "호박", ["수박", "눈 블록"], "철 블록 4개 위에 호박을 올리면 철 골렘이 태어나요."),
    ("snow-golem", "눈 골렘은 몬스터에게 무엇을 던질까요?", "눈덩이", ["화살", "돌"], "눈 골렘은 눈덩이를 던져요. ⛄"),
    ("ender-dragon", "엔더 드래곤을 치료해 주는 기둥 위의 물건은?", "엔드 수정", ["다이아몬드", "횃불"], "엔드 수정을 먼저 부숴야 드래곤을 물리칠 수 있어요."),
    ("warden", "눈이 없는 워든은 무엇으로 플레이어를 찾을까요?", "소리와 냄새", ["빛", "색깔"], "워든은 소리에 민감해서 웅크리고 살금살금 다녀야 해요."),
    ("wither", "위더의 머리는 몇 개일까요?", "3개", ["1개", "5개"], "위더는 머리가 셋인 보스예요."),
    ("ghast", "가스트가 쏘는 불덩이를 되받아칠 수 있을까요?", "칼이나 화살로 칠 수 있어요", ["절대 못 막아요", "물로만 막아요"], "불덩이를 쳐서 가스트에게 돌려보낼 수 있어요."),
    ("bed", "네더에서 침대에 누우면 어떻게 될까요?", "펑 터져요", ["아침이 돼요", "엔드로 가요"], "침대는 꼭 지상 세계에서만 써요!"),
    ("water-bucket", "높은 데서 떨어질 때 바닥에 무엇을 부으면 안 다칠까요?", "물", ["용암", "모래"], "물에 떨어지면 다치지 않아요. '물 양동이 착지'예요."),
    ("iron-pickaxe", "다이아몬드를 캐려면 적어도 어떤 곡괭이가 필요할까요?", "철 곡괭이", ["나무 곡괭이", "돌 곡괭이"], "다이아몬드는 철 곡괭이 이상으로 캐야 나와요."),
    ("diamond-pickaxe", "흑요석을 캘 수 있는 곡괭이는?", "다이아몬드 곡괭이", ["철 곡괭이", "금 곡괭이"], "흑요석은 다이아몬드나 네더라이트 곡괭이로만 캐요."),
    ("netherite-pickaxe", "용암에 빠져도 불타지 않는 물건은 무엇으로 만들었을까요?", "네더라이트", ["다이아몬드", "철"], "네더라이트 물건은 용암 위에 둥둥 떠요."),
    ("obsidian", "흑요석은 용암에 무엇이 닿으면 생길까요?", "물", ["모래", "눈"], "용암에 물이 닿으면 흑요석이 생겨요."),
    ("eye-of-ender", "엔더의 눈을 하늘로 던지면 어디를 알려 줄까요?", "요새", ["마을", "바다 신전"], "엔더의 눈은 엔드 차원문이 있는 요새 쪽으로 날아가요."),
    ("nether-portal", "네더 차원문을 만들 때 쓰는 블록은?", "흑요석", ["유리", "철 블록"], "흑요석 틀에 불을 붙이면 네더로 가는 문이 열려요."),
    ("torches", "몬스터가 생기지 않게 하려면 어떻게 할까요?", "횃불로 밝혀요", ["물을 부어요", "꽃을 심어요"], "몬스터는 어두운 곳에서 생겨요. 횃불로 밝게! 🔥"),
    ("stairs-down", "땅을 팔 때 절대 하면 안 되는 것은?", "발 바로 아래 파기", ["계단처럼 파기", "횃불 꽂기"], "발 아래를 파면 용암이나 동굴로 떨어질 수 있어요."),
    ("bone-meal", "뼛가루를 뿌리면 식물이 어떻게 될까요?", "쑥쑥 자라요", ["시들어요", "사라져요"], "뼛가루는 식물을 빨리 자라게 해요. 🌱"),
    ("glass", "화로에서 무엇을 구우면 유리가 될까요?", "모래", ["흙", "조약돌"], "모래를 구우면 유리가 돼요."),
    ("cake", "케이크는 몇 번 나눠 먹을 수 있을까요?", "7번", ["1번", "3번"], "케이크는 한 조각씩 7번 먹을 수 있어요. 🎂"),
    ("golden-apple", "황금 사과를 만들 때 사과를 둘러싸는 것은?", "금 주괴", ["다이아몬드", "철 주괴"], "사과를 금 주괴 8개로 둘러싸요."),
    ("sniffer", "스니퍼가 땅을 파서 찾아 주는 것은?", "옛날 씨앗", ["다이아몬드", "뼈"], "스니퍼는 다른 데 없는 옛날 꽃씨를 찾아 줘요."),
    ("trade-tip", "주민과 거래할 때 돈처럼 쓰는 보석은?", "에메랄드", ["다이아몬드", "청금석"], "주민은 에메랄드로 물건을 바꿔 줘요. 💚"),
]
# the picture would give the answer away
NO_PICTURE = {"husk", "iron-pickaxe", "diamond-pickaxe", "netherite-pickaxe", "nether-portal", "trade-tip"}
for i, q, right, wrongs, explain in FACTS:
    assert i in items, i
    choices, ans = text_choices(right, wrongs)
    add("fact", q, None if i in NO_PICTURE else thumb(i), choices, ans, explain, i)

(ROOT / "data/quiz.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
print(len(out), "questions")
