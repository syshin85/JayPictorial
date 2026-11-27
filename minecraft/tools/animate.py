#!/usr/bin/env python3
"""Makes animated GIFs of mobs from their game textures, moving the way they move in the game.

  python3 tools/animate.py            → every mob in MOBS
  python3 tools/animate.py zombie     → just these

Each mob is rebuilt from boxes like the game's model (same sizes, pivots and texture offsets), posed
frame by frame with the game's own animation formulas, and drawn by tools/mobrender.py
→ assets/anim/<id>/1.gif and thumb.png. Use it in data/minecraft.json as the first photo "anim:<id>",
then run tools/fetch_media.py <id>. Needs Pillow and numpy; textures come from minecraft.wiki
(© Mojang, private use).
"""
import io
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_media import get, image_infos  # noqa: E402
from mobrender import Box, Part, render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "anim"
PI = math.pi


def tex(name):
    """A texture file on minecraft.wiki, downloaded once."""
    if name not in tex.cache:
        f = f"File:{name}"
        tex.cache[name] = Image.open(io.BytesIO(get(image_infos([f])[f]["url"]))).convert("RGBA")
    return tex.cache[name]
tex.cache = {}


def item(name, grip, rot):
    """A flat 16×16 item held in a hand, as a child Part of the arm. grip: the sprite pixel at the hand;
    the sprite's right points forward (-z) and its top up; rot turns it from there."""
    T = tex(name)
    if T.width != 16:
        T = T.resize((16, 16), Image.Resampling.NEAREST)
    gx, gy = grip
    plane = Box(0, 0, -0.05, -gy, gx - 16, 0.1, 16, 16, tex=T,
                uvs={"west": (0, 0, 16, 16), "east": (16, 0, 0, 16)})
    return Part((0, 10, 0), [plane], rot=rot)


def walk(t, steps=2):
    """limbSwing for loop position t, so cos(swing * 0.6662) runs `steps` times per loop."""
    return 2 * PI * t * steps / 0.6662


def quad_legs(s, amt):
    """QuadrupedModel: right hind, left hind, right front, left front xRot."""
    c = math.cos(s * 0.6662) * 1.4 * amt
    return c, -c, -c, c


def look(t, yaw=0.25, pitch=0.08):
    """A slow look around (head yRot/xRot), one swing per loop."""
    a = 2 * PI * t
    return pitch * math.sin(a), yaw * math.sin(a)


def arm_bob(t):
    """AnimationUtils.bobArms, stretched to one loop: (zRot, xRot) added to the right arm, minus to the left."""
    a = 2 * PI * t
    return math.cos(a) * 0.05 + 0.05, math.sin(a) * 0.05


# ---------- humanoids ----------

def humanoid(t, T, amt=0.4, arms="walk", slim=False, separate=False, outer=None, head_boxes=None, ears=False, held=None):
    """HumanoidModel (zombie, skeleton, piglin…). arms: "walk" (swinging), "zombie" (held out), "item" (right hand holds something).
    slim: skeleton-thin 2×2 limbs. separate: 64×64 texture with own left limbs. outer: (texture, grow) clothes layer.
    held: an item() in the right hand."""
    s = walk(t)
    hx, hy = look(t)
    bz, bx = arm_bob(t)
    if arms == "zombie":
        ra = [-PI / 2.25 + bx, -0.1, bz]
        la = [-PI / 2.25 - bx, 0.1, -bz]
    else:
        ra = [math.cos(s * 0.6662 + PI) * amt + bx, 0, bz]
        la = [math.cos(s * 0.6662) * amt - bx, 0, -bz]
        if arms == "item":
            ra[0] = ra[0] * 0.5 - PI / 10
    leg = math.cos(s * 0.6662) * 1.4 * amt

    def limbs(T, grow=0.0, thin=False, sep=separate, hat=True):
        w = 2 if thin else 4
        ao, lo = (-1, -1) if thin else (-3, -1)
        head = [Box(0, 0, -4, -8, -4, 8, 8, 8, grow=grow, tex=T)]
        if hat:
            head.append(Box(32, 0, -4, -8, -4, 8, 8, 8, grow=grow + 0.5, tex=T))
        z = -1 if thin else -2
        return {
            "head": head,
            "body": [Box(16, 16, -4, 0, -2, 8, 12, 4, grow=grow, tex=T)],
            "ra": [Box(40, 16, ao, -2, z, w, 12, w, grow=grow, tex=T)],
            "la": [Box(32, 48, -1, -2, z, w, 12, w, grow=grow, tex=T) if sep else
                   Box(40, 16, -1, -2, z, w, 12, w, mirror=True, grow=grow, tex=T)],
            "rl": [Box(0, 16, -w / 2, 0, z, w, 12, w, grow=grow, tex=T)],
            "ll": [Box(16, 48, -w / 2, 0, z, w, 12, w, grow=grow, tex=T) if sep else
                   Box(0, 16, -w / 2, 0, z, w, 12, w, mirror=True, grow=grow, tex=T)],
        }
    b = limbs(T, thin=slim)
    if head_boxes is not None:
        b["head"] = head_boxes
    if outer:
        o = limbs(outer[0], outer[1], thin=False, sep=outer[2] if len(outer) > 2 else separate)
        for k in b:
            b[k] = b[k] + o[k]
    leg_x = 2 if slim else 1.9
    head = Part((0, 0, 0), b["head"], rot=(hx, hy, 0))
    if ears:
        f = 2 * PI * t * 2
        flap = 0.1 + amt * 0.25
        head.children += [Part((4.5, -6, 0), [Box(51, 6, 0, 0, -2, 1, 5, 4, tex=T)], rot=(0, 0, -PI / 6 - math.cos(f * 1.2) * flap)),
                          Part((-4.5, -6, 0), [Box(39, 6, -1, 0, -2, 1, 5, 4, tex=T)], rot=(0, 0, PI / 6 + math.cos(f) * flap))]
    return [head,
            Part((0, 0, 0), b["body"]),
            Part((-5, 2, 0), b["ra"], rot=ra, children=[held] if held else []),
            Part((5, 2, 0), b["la"], rot=la),
            Part((-leg_x, 12, 0), b["rl"], rot=(leg, 0, 0)),
            Part((leg_x, 12, 0), b["ll"], rot=(-leg, 0, 0))]


def piglin_head(T):
    """PiglinModel head: wide head, snout and tusks (ears are separate parts)."""
    return [Box(0, 0, -5, -8, -4, 10, 8, 8, tex=T), Box(31, 1, -2, -4, -5, 4, 4, 1, tex=T),
            Box(2, 4, 2, -2, -5, 1, 2, 1, tex=T), Box(2, 0, -3, -2, -5, 1, 2, 1, tex=T)]


def BOW():
    return item("Bow JE2 BE1.png", (8, 8), (0, 0, 0))


def zombie(t):
    return humanoid(t, tex("Zombie (texture).png"), arms="zombie")


def husk(t):
    return humanoid(t, tex("Husk (texture).png"), arms="zombie")


def drowned(t):
    return humanoid(t, tex("Drowned (texture).png"), arms="zombie", separate=True,
                    outer=(tex("Drowned Outer Layer (texture).png"), 0.25))


def skeleton(t):
    return humanoid(t, tex("Skeleton (texture) JE2 BE2.png"), arms="item", slim=True, held=BOW())


def stray(t):
    return humanoid(t, tex("Stray (texture).png"), arms="item", slim=True, held=BOW(),
                    outer=(tex("Stray Overlay (texture).png"), 0.25))


def bogged(t):
    return humanoid(t, tex("Bogged (texture).png"), arms="item", slim=True, held=BOW(),
                    outer=(tex("Bogged Overlay (texture).png"), 0.25))


def wither_skeleton(t):
    return humanoid(t, tex("Wither Skeleton (texture).png"), arms="item", slim=True,
                    held=item("Stone Sword JE2 BE2.png", (3, 13), (0, 0, 0)))


def zombified_piglin(t):
    return _piglin(t, tex("Zombified Piglin (texture).png"), "zombie")


def piglin_brute(t):
    return _piglin(t, tex("Piglin Brute (texture).png"), "item", item("Golden Axe JE3 BE2.png", (3, 13), (0, 0, 0)))


def _piglin(t, T, arms, held=None):
    """PlayerModel body with jacket/sleeves/pants layers (same texture, lower half), piglin head and flapping ears."""
    parts = humanoid(t, T, arms=arms, separate=True, head_boxes=piglin_head(T), ears=True, held=held)
    extra = {1: Box(16, 32, -4, 0, -2, 8, 12, 4, grow=0.25, tex=T), 2: Box(40, 32, -3, -2, -2, 4, 12, 4, grow=0.25, tex=T),
             3: Box(48, 48, -1, -2, -2, 4, 12, 4, grow=0.25, tex=T), 4: Box(0, 32, -2, 0, -2, 4, 12, 4, grow=0.25, tex=T),
             5: Box(0, 48, -2, 0, -2, 4, 12, 4, grow=0.25, tex=T)}
    for i, b in extra.items():
        parts[i].boxes.append(b)
    return parts


def witch(t):
    """WitchModel (VillagerModel): arms crossed, long robe, hat with a bent tip, wobbling nose."""
    T = tex("Witch (texture).png")
    s = walk(t)
    hx, hy = look(t)
    a = 2 * PI * t
    leg = math.cos(s * 0.6662) * 1.4 * 0.5 * 0.5
    hat4 = Part((1.75, -2, 2), [Box(0, 95, 0, 0, 0, 1, 2, 1, grow=0.25)], rot=(-0.20943952, 0, 0.10471976))
    hat3 = Part((1.75, -4, 2), [Box(0, 87, 0, 0, 0, 4, 4, 4)], rot=(-0.10471976, 0, 0.05235988), children=[hat4])
    hat2 = Part((1.75, -4, 2), [Box(0, 76, 0, 0, 0, 7, 4, 7)], rot=(-0.05235988, 0, 0.02617994), children=[hat3])
    hat = Part((-5, -10.03125, -5), [Box(0, 64, 0, 0, 0, 10, 2, 10)], children=[hat2])
    nose = Part((0, -2, 0), [Box(24, 0, -1, -1, -6, 2, 4, 2)], rot=(math.sin(a * 2) * 0.08, 0, math.cos(a * 2) * 0.045),
                children=[Part((0, -2, 0), [Box(0, 0, 0, 3, -6.75, 1, 1, 1, grow=-0.25)])])
    return [
        Part((0, 0, 0), [Box(0, 0, -4, -10, -4, 8, 10, 8)], rot=(hx, hy, 0), children=[hat, nose]),
        Part((0, 0, 0), [Box(16, 20, -4, 0, -3, 8, 12, 6), Box(0, 38, -4, 0, -3, 8, 20, 6, grow=0.5)]),
        Part((0, 3, -1), [Box(44, 22, -8, -2, -2, 4, 8, 4), Box(44, 22, 4, -2, -2, 4, 8, 4, mirror=True),
                          Box(40, 38, -4, 2, -2, 8, 4, 4)], rot=(-0.75, 0, 0)),
        Part((-2, 12, 0), [Box(0, 22, -2, 0, -2, 4, 12, 4)], rot=(leg, 0, 0)),
        Part((2, 12, 0), [Box(0, 22, -2, 0, -2, 4, 12, 4, mirror=True)], rot=(-leg, 0, 0)),
    ], T


# ---------- four legs and more ----------

def creeper(t):
    T = tex("Creeper (texture) JE2.png")
    s = walk(t)
    hx, hy = look(t)
    rh, lh, rf, lf = quad_legs(s, 0.35)
    leg = lambda p, r: Part(p, [Box(0, 16, -2, 0, -2, 4, 6, 4)], rot=(r, 0, 0))
    return [Part((0, 6, 0), [Box(0, 0, -4, -8, -4, 8, 8, 8)], rot=(hx, hy, 0)),
            Part((0, 6, 0), [Box(16, 16, -4, 0, -2, 8, 12, 4)]),
            leg((-2, 18, 4), rh), leg((2, 18, 4), lh), leg((-2, 18, -4), rf), leg((2, 18, -4), lf)], T


def spider_parts(t, T):
    """SpiderModel: eight legs, each set lifting and swinging a quarter beat after the last."""
    s = walk(t)
    hx, hy = look(t, 0.2, 0.05)
    k = s * 0.6662
    sw = [-(math.cos(k * 2 + p) * 0.4) * 0.6 for p in (0, PI, PI / 2, PI * 1.5)]
    up = [abs(math.sin(k + p) * 0.4) * 0.6 for p in (0, PI, PI / 2, PI * 1.5)]
    f, g, m = PI / 4, PI / 8, 0.58119464
    legs = []
    for i, (z, zr, yr) in enumerate([(2, f, 2 * g), (1, m, g), (0, m, -g), (-1, f, -2 * g)]):
        legs.append(Part((-4, 15, z), [Box(18, 0, -15, -1, -1, 16, 2, 2)], rot=(0, yr + sw[i], -zr + up[i])))
        legs.append(Part((4, 15, z), [Box(18, 0, -1, -1, -1, 16, 2, 2)], rot=(0, -yr - sw[i], zr - up[i])))
    return [Part((0, 15, -3), [Box(32, 4, -4, -4, -8, 8, 8, 8)], rot=(hx, hy, 0)),
            Part((0, 15, 0), [Box(0, 0, -3, -3, -3, 6, 6, 6)]),
            Part((0, 15, 9), [Box(0, 12, -5, -4, -6, 10, 8, 12)])] + legs


def spider(t):
    T = tex("Spider (texture).png")
    return spider_parts(t, T), T


def cave_spider(t):
    T = tex("Cave Spider (texture).png")
    return spider_parts(t, T), T


def cow(t):
    T = tex("Cow (texture).png")
    s = walk(t)
    hx, hy = look(t)
    rh, lh, rf, lf = quad_legs(s, 0.35)
    leg = lambda p, r, m: Part(p, [Box(0, 16, -2, 0, -2, 4, 12, 4, mirror=m)], rot=(r, 0, 0))
    return [Part((0, 4, -8), [Box(0, 0, -4, -4, -6, 8, 8, 6), Box(22, 0, -5, -5, -4, 1, 3, 1), Box(22, 0, 4, -5, -4, 1, 3, 1)],
                 rot=(hx, hy, 0)),
            Part((0, 5, 2), [Box(18, 4, -6, -10, -7, 12, 18, 10), Box(52, 0, -2, 2, -8, 4, 6, 1)], rot=(PI / 2, 0, 0)),
            leg((-4, 12, 7), rh, False), leg((4, 12, 7), lh, True), leg((-4, 12, -6), rf, False), leg((4, 12, -6), lf, True)], T


def llama(t):
    T = tex("Brown Llama (texture).png")
    s = walk(t)
    hx, hy = look(t)
    rh, lh, rf, lf = quad_legs(s, 0.35)
    leg = lambda p, r: Part(p, [Box(29, 29, -2, 0, -2, 4, 14, 4)], rot=(r, 0, 0))
    return [Part((0, 7, -6), [Box(0, 0, -2, -14, -10, 4, 4, 9), Box(0, 14, -4, -16, -6, 8, 18, 6),
                              Box(17, 0, -4, -19, -4, 3, 3, 2), Box(17, 0, 1, -19, -4, 3, 3, 2)], rot=(hx, hy, 0)),
            Part((0, 5, 2), [Box(29, 0, -6, -10, -7, 12, 18, 10)], rot=(PI / 2, 0, 0)),
            leg((-3.5, 10, 6), rh), leg((3.5, 10, 6), lh), leg((-3.5, 10, -5), rf), leg((3.5, 10, -5), lf)], T


def goat(t):
    T = tex("Goat (texture).png")
    s = walk(t)
    hx, hy = look(t)
    rh, lh, rf, lf = quad_legs(s, 0.35)
    head = Part((1, 14, 0), [Box(2, 61, -6, -11, -10, 3, 2, 1), Box(2, 61, 2, -11, -10, 3, 2, 1, mirror=True),
                             Box(23, 52, -0.5, -3, -14, 0, 7, 5)], rot=(hx, hy, 0), children=[
        Part((0, 0, 0), [Box(12, 55, -0.01, -16, -10, 2, 7, 2)]),
        Part((0, 0, 0), [Box(12, 55, -2.99, -16, -10, 2, 7, 2)]),
        Part((0, -8, -8), [Box(34, 46, -3, -4, -8, 5, 7, 10)], rot=(0.9599, 0, 0))])
    return [head,
            Part((0, 24, 0), [Box(1, 1, -4, -17, -7, 9, 11, 16), Box(0, 28, -5, -18, -8, 11, 14, 11)]),
            Part((1, 14, 4), [Box(36, 29, 0, 4, 0, 3, 6, 3)], rot=(lh, 0, 0)),
            Part((-3, 14, 4), [Box(49, 29, 0, 4, 0, 3, 6, 3)], rot=(rh, 0, 0)),
            Part((1, 14, -6), [Box(49, 2, 0, 0, 0, 3, 10, 3)], rot=(lf, 0, 0)),
            Part((-3, 14, -6), [Box(35, 2, 0, 0, 0, 3, 10, 3)], rot=(rf, 0, 0))], T


def cat(t):
    """OcelotModel/CatModel walking: legs out of step, tail swaying."""
    T = tex("Red Cat (texture).png")
    s = walk(t)
    hx, hy = look(t)
    k, amt = s * 0.6662, 0.6
    return [Part((0, 15, -9), [Box(0, 0, -2.5, -2, -3, 5, 4, 5), Box(0, 24, -1.5, -0.001, -4, 3, 2, 2),
                               Box(0, 10, -2, -3, 1, 1, 1, 2), Box(6, 10, 1, -3, 1, 1, 1, 2)], rot=(hx, hy, 0)),
            Part((0, 12, -10), [Box(20, 0, -2, 3, -8, 4, 16, 6)], rot=(PI / 2, 0, 0)),
            Part((0, 15, 8), [Box(0, 15, -0.5, 0, 0, 1, 8, 1)], rot=(0.9, 0, 0)),
            Part((0, 20, 14), [Box(4, 15, -0.5, 0, 0, 1, 8, 1)], rot=(1.7278761 + 0.31415927 * math.cos(s) * amt, 0, 0)),
            Part((1.1, 18, 5), [Box(8, 13, -1, 0, 1, 2, 6, 2)], rot=(math.cos(k) * amt, 0, 0)),
            Part((-1.1, 18, 5), [Box(8, 13, -1, 0, 1, 2, 6, 2)], rot=(math.cos(k + 0.3) * amt, 0, 0)),
            Part((1.2, 14.1, -5), [Box(40, 0, -1, 0, 0, 2, 10, 2)], rot=(math.cos(k + PI + 0.3) * amt, 0, 0)),
            Part((-1.2, 14.1, -5), [Box(40, 0, -1, 0, 0, 2, 10, 2)], rot=(math.cos(k + PI) * amt, 0, 0))], T


def turtle(t):
    """TurtleModel on land: flippers paddling slowly."""
    T = tex("Turtle (texture).png")
    hx, hy = look(t, 0.2, 0.05)
    k, amt = 2 * PI * t, 0.8  # one slow paddle per loop
    return [Part((0, 19, -10), [Box(3, 0, -3, -1, -3, 6, 5, 6)], rot=(hx, hy, 0)),
            Part((0, 11, -10), [Box(7, 37, -9.5, 3, -10, 19, 20, 6), Box(31, 1, -5.5, 3, -13, 11, 18, 3)], rot=(PI / 2, 0, 0)),
            Part((-3.5, 22, 11), [Box(1, 23, -2, 0, 0, 4, 1, 10)], rot=(math.cos(k) * 0.5 * amt, 0, 0)),
            Part((3.5, 22, 11), [Box(1, 12, -2, 0, 0, 4, 1, 10)], rot=(math.cos(k + PI) * 0.5 * amt, 0, 0)),
            Part((-5, 21, -4), [Box(27, 30, -13, 0, -2, 13, 1, 5)],
                 rot=(0, math.cos(k + PI) * 0.4 * amt, math.cos(k + PI) * 0.5 * amt)),
            Part((5, 21, -4), [Box(27, 24, 0, 0, -2, 13, 1, 5)],
                 rot=(0, math.cos(k) * 0.4 * amt, math.cos(k) * 0.5 * amt))], T


def iron_golem(t):
    """IronGolemModel: heavy steps (triangle wave), arms swinging opposite the legs."""
    T = tex("Iron Golem (texture).png")
    s = walk(t) * 13 / (2 * PI / 0.6662)  # one triangle-wave period (13) per step
    hx, hy = look(t)
    tri = lambda x, y: (abs(x % y - y * 0.5) - y * 0.25) / (y * 0.25)
    amt = 0.25
    w = tri(s, 13)
    return [Part((0, -7, -2), [Box(0, 0, -4, -12, -5.5, 8, 10, 8), Box(24, 0, -1, -5, -7.5, 2, 4, 2)], rot=(hx, hy, 0)),
            Part((0, -7, 0), [Box(0, 40, -9, -2, -6, 18, 12, 11), Box(0, 70, -4.5, 10, -3, 9, 5, 6, grow=0.5)]),
            Part((0, -7, 0), [Box(60, 21, -13, -2.5, -3, 4, 30, 6)], rot=((-0.2 + 1.5 * w) * amt, 0, 0)),
            Part((0, -7, 0), [Box(60, 58, 9, -2.5, -3, 4, 30, 6)], rot=((-0.2 - 1.5 * w) * amt, 0, 0)),
            Part((-4, 11, 0), [Box(37, 0, -3.5, -3, -3, 6, 16, 5)], rot=(-1.5 * w * amt, 0, 0)),
            Part((5, 11, 0), [Box(60, 0, -3.5, -3, -3, 6, 16, 5, mirror=True)], rot=(1.5 * w * amt, 0, 0))], T


def wither(t):
    """WitherModel: floating, ribcage and tail breathing in and out, side heads looking around."""
    T = tex("Wither (texture).png")
    a = 2 * PI * t
    f = math.cos(a)
    rib = (0.065 + 0.05 * f) * PI
    bob = math.sin(a) * 1.5
    hx, hy = look(t, 0.2, 0.05)
    return [Part((0, bob, 0), [Box(0, 16, -10, 3.9, -0.5, 20, 3, 3)], children=[
        Part((0, 0, 0), [Box(0, 0, -4, -4, -4, 8, 8, 8)], rot=(hx, hy, 0)),
        Part((-8, 4, 0), [Box(32, 0, -4, -4, -4, 6, 6, 6)], rot=(-hx, 0.35 * math.sin(a + 1), 0)),
        Part((10, 4, 0), [Box(32, 0, -4, -4, -4, 6, 6, 6)], rot=(hx, -0.35 * math.sin(a + 2), 0)),
        Part((-2, 6.9, -0.5), [Box(0, 22, 0, 0, 0, 3, 10, 3), Box(24, 22, -4, 1.5, 0.5, 11, 2, 2),
                               Box(24, 22, -4, 4, 0.5, 11, 2, 2), Box(24, 22, -4, 6.5, 0.5, 11, 2, 2)], rot=(rib, 0, 0)),
        Part((-2, 6.9 + math.cos(rib) * 10, -0.5 + math.sin(rib) * 10), [Box(12, 22, 0, 0, 0, 3, 6, 3)],
             rot=((0.265 + 0.1 * f) * PI, 0, 0)),
    ])], T


def pig(t):
    T = tex("Pig (texture) JE4 BE2.png")
    s = walk(t)
    hx, hy = look(t)
    rh, lh, rf, lf = quad_legs(s, 0.35)
    leg = lambda p, r: Part(p, [Box(0, 16, -2, 0, -2, 4, 6, 4)], rot=(r, 0, 0))
    return [Part((0, 12, -6), [Box(0, 0, -4, -4, -8, 8, 8, 8), Box(16, 16, -2, 0, -9, 4, 3, 1)], rot=(hx, hy, 0)),
            Part((0, 11, 2), [Box(28, 8, -5, -10, -7, 10, 16, 8)], rot=(PI / 2, 0, 0)),
            leg((-3, 18, 7), rh), leg((3, 18, 7), lh), leg((-3, 18, -5), rf), leg((3, 18, -5), lf)], T


def sheep(t):
    """SheepModel with the wool layer (SheepFurModel) around it."""
    T, F = tex("Sheep (texture).png"), tex("Sheep Fur (texture).png")
    s = walk(t)
    hx, hy = look(t)
    rh, lh, rf, lf = quad_legs(s, 0.35)
    leg = lambda p, r: Part(p, [Box(0, 16, -2, 0, -2, 4, 12, 4), Box(0, 16, -2, 0, -2, 4, 6, 4, grow=0.5, tex=F)], rot=(r, 0, 0))
    return [Part((0, 6, -8), [Box(0, 0, -3, -4, -6, 6, 6, 8), Box(0, 0, -3, -4, -4, 6, 6, 6, grow=0.6, tex=F)], rot=(hx, hy, 0)),
            Part((0, 5, 2), [Box(28, 8, -4, -10, -7, 8, 16, 6), Box(28, 8, -4, -10, -7, 8, 16, 6, grow=1.75, tex=F)],
                 rot=(PI / 2, 0, 0)),
            leg((-3, 12, 7), rh), leg((3, 12, 7), lh), leg((-3, 12, -5), rf), leg((3, 12, -5), lf)], T


def horse(t):
    """HorseModel (AbstractEquineModel): long head and neck, mane, swishing tail."""
    T = tex("Horse Brown (texture).png")
    s = walk(t)
    hx, hy = look(t, 0.15, 0.05)
    rh, lh, rf, lf = quad_legs(s, 0.35)
    a = 2 * PI * t
    tail = Part((0, -5, 2), [Box(42, 36, -1.5, 0, 0, 3, 14, 4)], rot=(PI / 6 + 0.1 * math.sin(a * 2), 0.3 * math.sin(a), 0))
    head = Part((0, 0, 0), [Box(0, 13, -3, -11, -2, 6, 5, 7)], children=[
        Part((0, 0, 0), [Box(19, 16, 0.55, -13, 4, 2, 3, 1, grow=-0.001), Box(19, 16, -2.55, -13, 4, 2, 3, 1, grow=-0.001)])])
    return [Part((0, 11, 5), [Box(0, 32, -5, -8, -17, 10, 10, 22, grow=0.05)], children=[tail]),
            Part((0, 4, -12), [Box(0, 35, -2.05, -6, -2, 4, 12, 7)], rot=(PI / 6 + hx, hy, 0), children=[
                head, Part((0, 0, 0), [Box(56, 36, -1, -11, 5.01, 2, 16, 2)]),
                Part((0, 0, 0), [Box(0, 25, -2, -11, -7, 4, 5, 5)])]),
            Part((4, 14, 7), [Box(48, 21, -3, -1.01, -1, 4, 11, 4, mirror=True)], rot=(lh, 0, 0)),
            Part((-4, 14, 7), [Box(48, 21, -1, -1.01, -1, 4, 11, 4)], rot=(rh, 0, 0)),
            Part((4, 14, -12), [Box(48, 21, -3, -1.01, -1.9, 4, 11, 4, mirror=True)], rot=(lf, 0, 0)),
            Part((-4, 14, -12), [Box(48, 21, -1, -1.01, -1.9, 4, 11, 4)], rot=(rf, 0, 0))], T


def snow_golem(t):
    """SnowGolemModel: three snowballs and a carved pumpkin; the top turns with the head, arms follow."""
    T = tex("Snow Golem (texture).png")
    face = tex("Carved Pumpkin (texture) JE3 BE2.png")
    side, top = tex("Pumpkin (side texture) JE2 BE2.png"), tex("Pumpkin (top texture) JE2 BE2.png")
    P = Image.new("RGBA", (48, 16))
    for i, im in enumerate((face, side, top)):
        P.paste(im.resize((16, 16), Image.Resampling.NEAREST), (16 * i, 0))
    pumpkin = Box(0, 0, -5, -10.5, -5, 10, 10, 10, tex=P, uvs={
        "north": (0, 0, 16, 16), "south": (16, 0, 32, 16), "west": (16, 0, 32, 16), "east": (16, 0, 32, 16),
        "down": (32, 0, 48, 16), "up": (32, 0, 48, 16)})
    a = 2 * PI * t
    yaw = 0.6 * math.sin(a)
    up = yaw * 0.25
    f, f1 = math.sin(up), math.cos(up)
    return [Part((0, 4, 0), [Box(0, 0, -4, -8, -4, 8, 8, 8, grow=-0.5), pumpkin], rot=(0.06 * math.sin(2 * a), yaw, 0)),
            Part((0, 13, 0), [Box(0, 16, -5, -10, -5, 10, 10, 10, grow=-0.5)], rot=(0, up, 0)),
            Part((0, 24, 0), [Box(0, 36, -6, -12, -6, 12, 12, 12, grow=-0.5)]),
            Part((f1 * 5, 6, -f * 5), [Box(32, 0, -1, 0, -1, 12, 2, 2, grow=-0.5)], rot=(0, up, 1.0 + 0.15 * math.sin(2 * a))),
            Part((-f1 * 5, 6, f * 5), [Box(32, 0, -1, 0, -1, 12, 2, 2, grow=-0.5)], rot=(0, up + PI, -1.0 - 0.15 * math.sin(2 * a)))], T


def _humanoid_mob(fn):
    """Humanoid pose functions return parts only; the texture is the first box's (or default)."""
    def wrap(t):
        parts = fn(t)
        return parts, None
    return wrap


# id: (pose function, frames, ms per frame, card frame 0..1, camera yaw)
MOBS = {
    "zombie": (_humanoid_mob(zombie), 48, 50, 0.125, -35),
    "husk": (_humanoid_mob(husk), 48, 50, 0.125, -35),
    "drowned": (_humanoid_mob(drowned), 48, 50, 0.125, -35),
    "skeleton": (_humanoid_mob(skeleton), 48, 50, 0.125, -35),
    "stray": (_humanoid_mob(stray), 48, 50, 0.125, -35),
    "bogged": (_humanoid_mob(bogged), 48, 50, 0.125, -35),
    "wither-skeleton": (_humanoid_mob(wither_skeleton), 48, 50, 0.125, -35),
    "zombified-piglin": (_humanoid_mob(zombified_piglin), 48, 50, 0.125, -35),
    "piglin-brute": (_humanoid_mob(piglin_brute), 48, 50, 0.125, -35),
    "witch": (witch, 48, 60, 0.125, -35),
    "creeper": (creeper, 48, 50, 0.125, -35),
    "spider": (spider, 48, 40, 0.0, -35),
    "cave-spider": (cave_spider, 48, 40, 0.0, -35),
    "cow": (cow, 48, 50, 0.125, -55),
    "llama": (llama, 48, 50, 0.125, -55),
    "goat": (goat, 48, 50, 0.125, -55),
    "cat": (cat, 48, 45, 0.125, -55),
    "turtle": (turtle, 48, 70, 0.0, -40),
    "iron-golem": (iron_golem, 48, 60, 0.125, -35),
    "wither": (wither, 48, 60, 0.0, -30),
    "pig": (pig, 48, 50, 0.125, -55),
    "sheep": (sheep, 48, 50, 0.125, -55),
    "horse": (horse, 48, 50, 0.125, -55),
    "snow-golem": (snow_golem, 48, 60, 0.0, -35),
}
PITCH, TARGET = 25, 440  # camera tilt; longest side of the picture in pixels


def to_palette(frame):
    """One GIF frame: crisp pixels, fully transparent background (index 255)."""
    clear = frame.getchannel("A").point(lambda v: 0 if v > 127 else 255)
    p = frame.convert("RGB").quantize(255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    p.paste(255, mask=clear)
    return p


def frames_for(mob_id):
    pose, n, ms, still, yaw = MOBS[mob_id]
    posed = [pose(i / n) for i in range(n)]
    T = next((b.tex for p in posed[0][0] for b in p.boxes if b.tex), None) or posed[0][1]
    posed = [(parts, t or T) for parts, t in posed]
    # first pass, small: find the bounds over the whole loop, then scale to TARGET
    big = (1200, 1200)
    boxes = [render(parts, t, big, 8, yaw, PITCH, (600, 600)).getbbox() for parts, t in posed[::6]]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    k = TARGET / max(x1 - x0, y1 - y0)
    size = (int((x1 - x0) * k) + 16, int((y1 - y0) * k) + 16)
    center = ((600 - x0) * k + 8, (600 - y0) * k + 8)
    return [render(parts, t, size, 8 * k, yaw, PITCH, center) for parts, t in posed], ms, still


def make(mob_id):
    frames, ms, still = frames_for(mob_id)
    out = OUT / mob_id
    out.mkdir(parents=True, exist_ok=True)
    pal = [to_palette(f) for f in frames]
    pal[0].save(out / "1.gif", save_all=True, append_images=pal[1:], duration=ms, loop=0,
                transparency=255, disposal=2)
    thumb = frames[int(still * len(frames))].copy()
    thumb.thumbnail((400, 400), Image.Resampling.NEAREST)
    thumb.save(out / "thumb.png")
    print(f"{mob_id}: {len(frames)} frames, {(out / '1.gif').stat().st_size // 1000} KB")


if __name__ == "__main__":
    for mob_id in sys.argv[1:] or MOBS:
        make(mob_id)
