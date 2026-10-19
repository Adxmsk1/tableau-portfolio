# background art for the ski jumping dashboard (sky, mountains, the jump, cards, pines)
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tableau_tools"))
from PIL import Image, ImageDraw  # noqa: E402
from gfx import DRAW, Canvas, mix, path  # noqa: E402

SNOW, SHADOW_SNOW = "#FBFDFF", "#DCE7F0"


def ridge(x0, x1, ymin, ymax, seed, rough=0.55, n=256, base=402, fade=320):
    # midpoint displacement, fades in from the left so it doesn't start as a cliff
    rnd = random.Random(seed)
    h = [0.0] * (n + 1)
    h[0], h[n] = rnd.random(), rnd.random()
    step, amp = n, 1.0
    while step > 1:
        half = step // 2
        for i in range(half, n, step):
            h[i] = (h[i - half] + h[i + half]) / 2 + rnd.uniform(-amp, amp) * 0.5
        step, amp = half, amp * rough
    lo, hi = min(h), max(h)
    pts = []
    for i, v in enumerate(h):
        x = x0 + (x1 - x0) * i / n
        t = min(1.0, (x - x0) / fade)
        taper = t * t * (3 - 2 * t)
        top = ymax - (ymax - ymin) * (v - lo) / (hi - lo)
        pts.append((x, base - (base - top) * taper))
    return pts


def mountain(c, pts, base, colour, snowline, snow=SNOW, seed=0):
    c.poly(pts + [(pts[-1][0], base), (pts[0][0], base)], fill=colour)
    rnd = random.Random(seed)
    lower = []
    for x, y in pts:
        depth = max(0.0, snowline - y) * 0.55
        if depth:
            depth = max(0.0, depth + rnd.uniform(-6, 6))
        lower.append((x, y + depth))
    c.poly(pts + lower[::-1], fill=snow)


def pine(c, x, y, h, colour, snow=SNOW):
    c.rect(x - h * 0.04, y - h * 0.12, h * 0.08, h * 0.12, mix(colour, "#000000", 0.25))
    for k, (w, top, bottom) in enumerate(((0.42, 0.45, 0.0), (0.33, 0.72, 0.30), (0.22, 1.0, 0.58))):
        c.poly([(x - h * w, y - h * bottom - h * 0.08), (x, y - h * top), (x + h * w, y - h * bottom - h * 0.08)], fill=colour)
        c.poly([(x - h * w * 0.35, y - h * top + h * (top - bottom) * 0.38), (x, y - h * top),
                (x + h * w * 0.35, y - h * top + h * (top - bottom) * 0.38)], fill=snow)


def flake(c, x, y, r, colour, width=1.2):
    for k in range(6):
        a = math.pi / 3 * k + math.pi / 6
        ex, ey = x + r * math.cos(a), y + r * math.sin(a)
        c.line([(x, y), (ex, ey)], colour, width)
        for side in (-1, 1):
            bx, by = x + r * 0.6 * math.cos(a), y + r * 0.6 * math.sin(a)
            c.line([(bx, by), (bx + r * 0.3 * math.cos(a + side * 0.9), by + r * 0.3 * math.sin(a + side * 0.9))], colour, width)


def ski_jump(c, ink, accent, red):
    terrain = path(((820, 402), (900, 372), (952, 230), (995, 168)),
                   ((995, 168), (1050, 180), (1120, 228), (1155, 250)),
                   ((1155, 250), (1200, 272), (1240, 318), (1300, 350)),
                   ((1300, 350), (1360, 382), (1420, 392), (1600, 394)))
    c.poly(terrain + [(1600, 402), (820, 402)], fill=SNOW)
    shade_pts = path(((820, 402), (900, 372), (952, 230), (995, 168)))
    c.poly(shade_pts + [(975, 250), (950, 340), (930, 402)], fill=SHADOW_SNOW)
    land = path(((1155, 250), (1200, 272), (1240, 318), (1300, 350)), ((1300, 350), (1360, 382), (1420, 392), (1600, 394)))
    for off in (10, 22, 36):
        c.line([(x + off * 0.3, y + off) for x, y in land[:60] if y + off < 400], "#E6EEF5", 1.2)
    # K point
    for (x, y), col, w in (((1262, 324), red, 2.4), ((1222, 296), "#9DB6CD", 1.2), ((1300, 350), "#9DB6CD", 1.2)):
        c.line([(x - 9, y - 6), (x + 9, y + 6)], col, w)
    # inrun
    ramp = [(992, 130), (1060, 175), (1122, 216), (1153, 233)]
    for x in (1005, 1035, 1065, 1095):
        t = (x - 992) / (1153 - 992)
        ry = 130 + (233 - 130) * t
        ground = min(y for gx, y in terrain if abs(gx - x) < 3) if any(abs(gx - x) < 3 for gx, _ in terrain) else 400
        c.line([(x, ry), (x, ground)], mix(ink, "#FFFFFF", 0.35), 2)
    c.line(ramp, ink, 5)
    c.line(ramp, mix(ink, "#FFFFFF", 0.55), 1.2)
    c.rect(978, 106, 26, 24, ink, radius=2)
    c.poly([(974, 108), (991, 96), (1008, 108)], fill=red)
    # jumper, V style
    jx, jy = 1232, 214
    c.line([(jx - 4, jy + 6), (jx + 46, jy - 16)], mix(ink, "#FFFFFF", 0.45), 2.2)
    c.line([(jx + 2, jy + 12), (jx + 18, jy + 6), (jx + 34, jy - 1)], ink, 5.5)
    c.line([(jx + 16, jy + 9), (jx + 26, jy + 13)], ink, 2.4)
    c.circle(jx + 39, jy - 3.5, 4.8, red)
    c.line([(jx - 4, jy + 8), (jx + 50, jy + 4)], ink, 2.4)
    c.circle(jx + 36, jy + 104, 6, "#E3ECF4")  # shadow


def scene(ink, accent, red):
    # drawn on its own transparent layer, then cropped + scaled into the header
    c = Canvas(1600, 402)
    far = ridge(600, 1600, 70, 250, seed=3)
    mountain(c, far, 402, "#B9CDE0", snowline=135, seed=1)
    mid = ridge(700, 1600, 150, 300, seed=8, rough=0.5, fade=380)
    mountain(c, mid, 402, "#8FA9C2", snowline=195, snow="#F2F7FB", seed=2)
    ski_jump(c, ink, accent, red)
    for x, y, h in ((838, 402, 44), (862, 404, 58), (888, 402, 40), (1500, 400, 36), (1526, 402, 50), (1556, 400, 40),
                    (1580, 403, 30)):
        pine(c, x, y, h, "#2E4F5E")
    return c.im.crop((560 * DRAW, 0, 1600 * DRAW, 402 * DRAW))


def background(out, W, H, cards, ink, accent, red, scene_box, bg="#EEF3F7", sky="#C6DAEA", horizon=380, pines=(26, 44)):
    # cards: (x, y, w, h, kind)   scene_box: (left, bottom, width) for the mountain scene
    c = Canvas(W, H, bg)
    c.vgradient(0, horizon + 20, sky, bg)
    rnd = random.Random(11)
    sx, sb, sw = scene_box
    for _ in range(int(170 * sw / 1040)):
        x, y = rnd.uniform(sx - 40, W - 8), rnd.uniform(6, sb - 120)
        c.circle(x, y, rnd.uniform(0.9, 2.3), "#FFFFFF")
    layer = scene(ink, accent, red)
    sh = round(402 * sw / 1040)
    layer = layer.resize((round(sw * DRAW), round(sh * DRAW)), Image.LANCZOS)
    c.im.alpha_composite(layer, (round(sx * DRAW), round((sb - sh) * DRAW)))
    c.d = ImageDraw.Draw(c.im)
    c.vgradient(sb - 4, sb + 12, "#F6F9FC", bg)
    for x, y, w, h, kind in cards:
        c.rect(x, y + 4, w, h, mix(bg, "#7F9AB5", 0.28), radius=10)
        c.rect(x, y, w, h, "#FFFFFF", radius=10)
        if kind == "kpi":
            c.rect(x, y, w, 6, accent, radius=3)
            c.rect(x, y + 3, w, 3, accent)
            flake(c, x + w - 22, y + 26, 9, mix(accent, "#FFFFFF", 0.55))
    # snowdrifts + trees along the bottom
    base = H - 90
    for k, (amp, col, off) in enumerate(((12, "#DCE7F0", 0), (9, "#F6F9FC", 20))):
        pts = [(x, base + off + amp * math.sin(x / (95 + 30 * k) + k)) for x in range(0, W + 8, 8)]
        c.poly(pts + [(W, H), (0, H)], fill=col)
    for i in range(int(W / 62)):
        x = 20 + i * 62 + rnd.uniform(-14, 14)
        y = base + 28 + 8 * math.sin(x / 95) + rnd.uniform(0, 8)
        pine(c, x, y, rnd.uniform(*pines), rnd.choice(["#2E4F5E", "#36596A", "#284655"]))
    c.poly([(x, H - 22 + 5 * math.sin(x / 70)) for x in range(0, W + 8, 8)] + [(W, H), (0, H)], fill=SNOW)
    return c.save(out)
