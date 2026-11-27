"""Tiny Minecraft-style box-model renderer: textured cuboids, orthographic camera, depth buffer.
Geometry and UV layout follow the game's ModelPart.Cube (y down, front = -z in model space).
Like the game's entity "cutout" render types: no back-face culling, texels with alpha are either drawn or skipped."""
import math

import numpy as np
from PIL import Image

FACES = {  # name: (vertex indices, outward normal in model space)
    "down": ((5, 4, 0, 1), (0, -1, 0)),
    "up": ((2, 3, 7, 6), (0, 1, 0)),
    "west": ((0, 4, 7, 3), (-1, 0, 0)),
    "north": ((1, 0, 3, 2), (0, 0, -1)),
    "east": ((5, 1, 2, 6), (1, 0, 0)),
    "south": ((4, 5, 6, 7), (0, 0, 1)),
}


def rot(v, xr, yr, zr):
    """ZYX like PoseStack.mulPose(rotationZYX): v' = Rz * Ry * Rx * v."""
    x, y, z = v
    c, s = math.cos(xr), math.sin(xr); y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(yr), math.sin(yr); x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(zr), math.sin(zr); x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


class Box:
    """addBox(x, y, z, w, h, d) at texOffs(u, v); grow = CubeDeformation; tex = another texture (outer layers);
    uvs = only these faces, with their own texture rectangles (flat items)."""
    def __init__(self, u, v, x, y, z, w, h, d, mirror=False, grow=0.0, tex=None, uvs=None):
        self.u, self.v, self.w, self.h, self.d, self.mirror, self.tex, self.uvs = u, v, w, h, d, mirror, tex, uvs
        x0, y0, z0, x1, y1, z1 = x - grow, y - grow, z - grow, x + w + grow, y + h + grow, z + d + grow
        if mirror:
            x0, x1 = x1, x0
        self.verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                      (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]

    def uv(self, name):
        if self.uvs is not None:
            return self.uvs.get(name)
        u, v, w, h, d = self.u, self.v, self.w, self.h, self.d
        f4, f5, f6, f7, f8, f9 = u, u + d, u + d + w, u + d + w + w, u + d + w + d, u + d + w + d + w
        f10, f11, f12 = v, v + d, v + d + h
        return {"down": (f5, f10, f6, f11), "up": (f6, f11, f7, f10), "west": (f4, f11, f5, f12),
                "north": (f5, f11, f6, f12), "east": (f6, f11, f8, f12), "south": (f8, f11, f9, f12)}[name]


class Part:
    """A ModelPart: pivot (PartPose offset), boxes, rotation (x, y, z radians), children, scale."""
    def __init__(self, pivot, boxes, rot=(0, 0, 0), children=(), scale=1.0):
        self.pivot, self.boxes, self.rot, self.children, self.scale = pivot, boxes, list(rot), list(children), scale


def collect(part, parent=lambda p: p, out=None):
    out = [] if out is None else out

    def xf(p, part=part):
        p = rot(tuple(a * part.scale for a in p), *part.rot)
        return parent(tuple(a + b for a, b in zip(part.pivot, p)))
    for b in part.boxes:
        out.append((b, xf))
    for c in part.children:
        collect(c, xf, out)
    return out


def render(parts, tex, size, scale, yaw, pitch, center, light=(-0.45, 0.8, 0.4), shade=(0.5, 0.5)):
    """parts: Parts in model space. Camera yaw/pitch in degrees (world = model x, -y, -z)."""
    W, H = size
    cyw, syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    L = np.array(light) / np.linalg.norm(light)
    cx, cy = center

    def cam(p):  # model → world (x, -y, -z) → camera (x right, y up, z toward the viewer)
        x, y, z = p[0], -p[1], -p[2]
        x, z = x * cyw + z * syw, -x * syw + z * cyw
        y, z = y * cp - z * sp, y * sp + z * cp
        return x, y, z

    color = np.zeros((H, W, 3), np.float32)
    alpha = np.zeros((H, W), bool)
    depth = np.full((H, W), -np.inf, np.float32)
    texels = {}
    for box, xf in [bx for part in parts for bx in collect(part)]:
        t = box.tex or tex
        if id(t) not in texels:
            texels[id(t)] = np.asarray(t.convert("RGBA"), np.float32)
        arr = texels[id(t)]
        pts = [cam(xf(v)) for v in box.verts]
        o = np.array(cam(xf((0, 0, 0))))
        for name, (idx, n) in FACES.items():
            rect = box.uv(name)
            if rect is None:
                continue
            u1, v1, u2, v2 = rect
            du, dv = u2 - u1, v2 - v1
            if abs(du) < 1e-6 or abs(dv) < 1e-6:
                continue
            if box.mirror and n[0]:
                n = (-n[0], 0, 0)
            nn = np.array(cam(xf(n))) - o
            nn /= np.linalg.norm(nn) or 1
            if nn[2] < 0:
                nn = -nn  # inside of a face seen through a gap: light it like its outside
            bright = min(1.0, shade[0] + shade[1] * max(0.0, float(nn @ L)))
            q = [pts[i] for i in idx]
            P = [(cx + p[0] * scale, cy - p[1] * scale, p[2]) for p in q]
            ax, ay = P[0][0] - P[1][0], P[0][1] - P[1][1]
            bx, by = P[2][0] - P[1][0], P[2][1] - P[1][1]
            det = ax * by - ay * bx
            if abs(det) < 1e-9:
                continue
            xs = [p[0] for p in P] + [P[0][0] + bx]
            ys = [p[1] for p in P] + [P[0][1] + by]
            x0, x1 = max(0, int(math.floor(min(xs)))), min(W, int(math.ceil(max(xs))) + 1)
            y0, y1 = max(0, int(math.floor(min(ys)))), min(H, int(math.ceil(max(ys))) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            X, Y = np.meshgrid(np.arange(x0, x1) + 0.5 - P[1][0], np.arange(y0, y1) + 0.5 - P[1][1])
            s = (by * X - bx * Y) / det
            tt = (-ay * X + ax * Y) / det
            inside = (s >= 0) & (s < 1) & (tt >= 0) & (tt < 1)
            if not inside.any():
                continue
            z = P[1][2] + s * (P[0][2] - P[1][2]) + tt * (P[2][2] - P[1][2])
            tu = np.where(du > 0, u1 + np.floor(s * abs(du)), u1 - 1 - np.floor(s * abs(du))).astype(int)
            tv = np.where(dv > 0, v1 + np.floor(tt * abs(dv)), v1 - 1 - np.floor(tt * abs(dv))).astype(int)
            tu = np.clip(tu, 0, arr.shape[1] - 1)
            tv = np.clip(tv, 0, arr.shape[0] - 1)
            px = arr[tv, tu]
            win = inside & (px[..., 3] > 25) & (z > depth[y0:y1, x0:x1])
            depth[y0:y1, x0:x1][win] = z[win]
            color[y0:y1, x0:x1][win] = px[..., :3][win] * bright
            alpha[y0:y1, x0:x1][win] = True
    out = np.dstack([np.clip(color, 0, 255), alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")
