# the chessboard background - squares, coordinates, cards and the piece glyphs
import sys
from pathlib import Path

from PIL import ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tableau_tools"))
from gfx import DRAW, Canvas, mix  # noqa: E402

PIECES = {"K": "\u265a", "Q": "\u265b", "R": "\u265c", "B": "\u265d", "N": "\u265e", "P": "\u265f",
          "k": "\u2654", "q": "\u2655", "r": "\u2656", "b": "\u2657", "n": "\u2658", "p": "\u2659"}
SYMBOL_FONT = "C:/Windows/Fonts/seguisym.ttf"


def piece(c, glyph, x, y, size, colour, anchor="ms"):
    f = ImageFont.truetype(SYMBOL_FONT, int(size * DRAW))
    c.d.text((x * DRAW, y * DRAW), PIECES[glyph], font=f, fill=colour, anchor=anchor)


def background(out, W, H, board, cards, glyphs, light, dark, card, ink, muted, shadow):
    bx, by, s = board
    c = Canvas(W, H, mix(light, dark, 0.35))
    for rank in range(8):
        for file in range(8):
            colour = light if (rank + file) % 2 == 0 else dark
            c.rect(bx + file * s, by + rank * s, s, s, colour)
    c.rect(bx - 3, by - 3, 8 * s + 6, 8 * s + 6, None, outline=mix(dark, ink, 0.35), width=2)
    for i in range(8):
        c.text(bx + (i + 0.5) * s, by + 8 * s + 22, "abcdefgh"[i], 15, muted, "SemiBold", anchor="mm")
        c.text(bx - 24, by + (i + 0.5) * s, str(8 - i), 15, muted, "SemiBold", anchor="mm")
    for x, y, w, h in cards:
        c.rect(x + 3, y + 3, w, h, shadow, radius=2)
        c.rect(x, y, w, h, card, radius=2, outline=mix(card, ink, 0.12), width=1)
    for g, x, y, size, colour in glyphs:
        piece(c, g, x, y, size, colour)
    return c.save(out)
