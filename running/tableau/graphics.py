# track, shoe, bibs and the route for the running dashboard
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tableau_tools"))
from gfx import Canvas, bez, mix, path, shade  # noqa: E402,F401


def track_band(out, w, h, track, line="#FFFFFF", lanes=4):
    c = Canvas(w, h, track)
    rnd = random.Random(7)
    # speckle for the rubber crumb look
    tints = [mix(track, "#FFFFFF", 0.14), shade(track, 0.86)]
    for _ in range(w * h // 4):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        c.circle(x, y, rnd.uniform(0.25, 0.6), rnd.choice(tints))
    m = 6
    lane_h = (h - 2 * m) / lanes
    top, bottom = m, h - m
    for i in range(lanes + 1):
        c.rect(0, top + i * lane_h - 1, w, 2, line)
    edge = 60
    c.rect(edge, top, 3, bottom - top, line)
    for i in range(lanes):
        c.text(edge + 16, top + (i + 0.5) * lane_h, str(i + 1), lane_h * 0.7, line, anchor="lm")
    rows = 4
    sq = (bottom - top) / (rows * lanes) * 2
    fx = w - edge - 4 * sq
    for col in range(4):
        for row in range(int(round((bottom - top) / sq))):
            if (col + row) % 2 == 0:
                c.rect(fx + col * sq, top + row * sq, sq, sq, line)
    return c.save(out)


def shoe(out, ink, upper, foam, plate, muted, w=480, h=232):
    c = Canvas(w, h)
    ox, oy = 0, 6
    P = lambda x, y: (x + ox, y + oy)
    for y, x0 in ((120, 0), (140, 6), (160, 2)):
        c.line([P(x0, y), P(x0 + 18, y)], muted, 2)
    sole_bottom = path((P(38, 196), P(90, 206), P(190, 207), P(230, 205)),
                       (P(230, 205), P(280, 203), P(318, 192), P(334, 172)))
    toe_turn = bez(P(334, 172), P(340, 165), P(338, 158), P(330, 158))[1:]
    sole_top = path((P(330, 158), P(270, 152), P(190, 140), P(120, 130)),
                    (P(120, 130), P(80, 125), P(45, 126), P(30, 128)))[1:]
    heel_back = bez(P(30, 128), P(18, 150), P(20, 180), P(38, 196))[1:]
    midsole = sole_bottom + toe_turn + sole_top + heel_back
    upper_pts = path((P(30, 128), P(24, 100), P(28, 78), P(40, 62)),
                     (P(40, 62), P(60, 66), P(80, 74), P(100, 72)),
                     (P(100, 72), P(108, 58), P(118, 50), P(128, 50)),
                     (P(128, 50), P(170, 62), P(240, 100), P(290, 128)),
                     (P(290, 128), P(315, 138), P(332, 148), P(330, 158)))
    c.poly(upper_pts + sole_top, fill=upper)
    heel = path((P(30, 128), P(24, 100), P(28, 78), P(40, 62)), (P(40, 62), P(55, 80), P(70, 110), P(78, 128)))
    c.poly(heel, fill=shade(upper, 0.78))
    c.line(upper_pts, ink, 2)
    lace_path = bez(P(128, 50), P(170, 62), P(240, 100), P(290, 128))
    for t in (0.12, 0.27, 0.42, 0.57, 0.72):
        x, y = lace_path[int(t * 40)]
        c.line([(x - 9, y + 12), (x + 7, y - 4)], "#FFFFFF", 3)
    c.line([P(40, 62), P(30, 54), P(24, 60)], ink, 2.5)  # pull tab
    c.poly(midsole, fill=foam)
    for k in range(1, 4):
        pts = path((P(48, 128 + 16 * k), P(120, 140 + 13 * k), P(220, 150 + 10 * k), P(300, 160 + 6 * k)))
        c.line(pts, shade(foam, 0.93), 1.2)
    plate_pts = path((P(45, 170), P(120, 178), P(200, 184), P(250, 180)), (P(250, 180), P(290, 177), P(315, 168), P(328, 160)))
    c.line(plate_pts, plate, 4.5)
    c.line(midsole + midsole[:1], ink, 2)
    c.line(sole_bottom, ink, 5)

    def note(ax, ay, ty, head, sub):
        lx = 352
        c.circle(ax, ay, 3.2, ink)
        c.line([(ax, ay), (lx - 8, ty)], ink, 1.2)
        c.line([(lx - 8, ty), (lx - 2, ty)], ink, 1.2)
        c.text(lx, ty - 2, head, 12.5, ink, "Bold", anchor="ls")
        c.text(lx, ty + 15, sub, 11, muted, "Regular", anchor="ls")
    note(*P(170, 150), 40 + oy, "SPRINGY FOAM", "a stack up to 40 mm")
    note(*P(268, 178), 120 + oy, "CARBON PLATE", "a stiff, curved lever")
    note(*P(323, 182), 196 + oy, "ROCKER SOLE", "rolls the foot forward")
    return c.save(out)


def bib(out, w, h, stripe, label, paper="#FFFFFF", pin="#9AA0A6"):
    c = Canvas(w + 8, h + 8)
    c.rect(4, 6, w, h, (0, 0, 0, 30), radius=6)
    c.rect(2, 2, w, h, paper, radius=6)
    c.rect(2, 2, w, 26, stripe, radius=6)
    c.rect(2, 16, w, 12, stripe)
    c.text(16, 15, label, 11, "#FFFFFF", "Bold", anchor="lm")
    c.text(w - 12, 15, "2001-2025", 10, (255, 255, 255, 190), "Regular", anchor="rm")
    for x, y in ((14, 42), (w - 10, 42), (14, h - 10), (w - 10, h - 10)):
        c.circle(x, y, 4.2, "#FFFFFF", outline=pin, width=1.6)
        c.circle(x, y, 1.2, pin)
    return c.save(out)


def route(out, w, h, markers, track, ink, paper, muted):
    # markers: (y, km, label, kind) where kind is start / km / finish
    c = Canvas(w, h)
    cx = w / 2
    x_at = lambda y: cx + 14 * math.sin(y / 170)
    ys = [y for y, *_ in markers]
    pts = [(x_at(y), y) for y in range(int(ys[0]), int(ys[-1]) + 1, 2)]
    c.line(pts, track, 5)
    for (y0, k0, *_), (y1, k1, *_) in zip(markers, markers[1:]):
        for km in range(math.floor(k0) + 1, math.ceil(k1)):
            y = y0 + (y1 - y0) * (km - k0) / (k1 - k0)
            c.circle(x_at(y), y, 3.4, paper, outline=track, width=1.6)
    for y, km, label, kind in markers:
        x = x_at(y)
        if kind == "finish":
            s, n = 7, 6
            for i in range(n):
                for j in range(n):
                    c.rect(x - s * n / 2 + i * s, y - s * n / 2 + j * s, s, s, ink if (i + j) % 2 == 0 else paper)
            c.rect(x - s * n / 2, y - s * n / 2, s * n, s * n, None, outline=ink, width=1.5)
            c.text(x, y + s * n / 2 + 13, label, 11, ink, "Bold", anchor="mm")
        else:
            r = 25
            c.circle(x, y, r + 3, paper)
            c.circle(x, y, r, ink if kind == "start" else track)
            c.text(x, y + 1, label, 12.5 if len(label) <= 4 else 10.5, "#FFFFFF", "Bold", anchor="mm")
    return c.save(out)


def finish_strip(out, w, h, ink, paper):
    c = Canvas(w, h, paper)
    s = h / 2
    for i in range(int(w / s) + 1):
        for j in range(2):
            if (i + j) % 2 == 0:
                c.rect(i * s, j * s, s, s, ink)
    return c.save(out)
