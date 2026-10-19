"""Small Pillow helpers for the dashboard graphics. Draws at 4x, saves at 2x for retina screens."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DRAW, SAVE = 4, 2
FONT = "C:/Windows/Fonts/bahnschrift.ttf"


def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, int(size * DRAW))
    try:
        f.set_variation_by_name(weight)
    except (OSError, ValueError):
        pass
    return f


class Canvas:
    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (int(w * DRAW), int(h * DRAW)), bg)
        self.d = ImageDraw.Draw(self.im)

    @staticmethod
    def s(pts):
        return [(x * DRAW, y * DRAW) for x, y in pts]

    def poly(self, pts, fill=None, outline=None, width=0):
        self.d.polygon(self.s(pts), fill=fill)
        if outline and width:
            self.line(pts + pts[:1], outline, width)

    def line(self, pts, fill, width):
        self.d.line(self.s(pts), fill=fill, width=int(width * DRAW), joint="curve")
        r = width * DRAW / 2
        for x, y in (self.s(pts)[0], self.s(pts)[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def rect(self, x, y, w, h, fill, radius=0, outline=None, width=0):
        self.d.rounded_rectangle([x * DRAW, y * DRAW, (x + w) * DRAW, (y + h) * DRAW], radius=radius * DRAW, fill=fill,
                                 outline=outline, width=int(width * DRAW))

    def circle(self, cx, cy, r, fill, outline=None, width=0):
        self.d.ellipse([(cx - r) * DRAW, (cy - r) * DRAW, (cx + r) * DRAW, (cy + r) * DRAW], fill=fill, outline=outline,
                       width=int(width * DRAW))

    def text(self, x, y, s, size, fill, weight="Bold", anchor="la"):
        self.d.text((x * DRAW, y * DRAW), s, font=font(size, weight), fill=fill, anchor=anchor)

    def vgradient(self, y0, y1, top, bottom):
        a, b = rgb(top), rgb(bottom)
        for py in range(int(y0 * DRAW), int(y1 * DRAW)):
            t = (py - y0 * DRAW) / max(1, (y1 - y0) * DRAW)
            self.d.line([(0, py), (self.im.width, py)], fill=tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.im.resize((int(self.w * SAVE), int(self.h * SAVE)), Image.LANCZOS).save(path)
        return path


def rgb(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def shade(hex_colour, k):
    # pillow overwrites pixels instead of blending, so use solid darker colours rather than alpha
    return "#" + "".join(f"{int(c * k):02X}" for c in rgb(hex_colour))


def mix(c1, c2, t):
    a, b = rgb(c1), rgb(c2)
    return "#" + "".join(f"{round(a[i] + (b[i] - a[i]) * t):02X}" for i in range(3))


def bez(p0, p1, p2, p3, n=40):
    return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0],
             (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1])
            for t in (i / n for i in range(n + 1))]


def path(*segs):
    # chain of cubic bezier segments (p0, c1, c2, p3) -> one list of points
    pts = []
    for seg in segs:
        pts += bez(*seg)[(1 if pts else 0):]
    return pts
