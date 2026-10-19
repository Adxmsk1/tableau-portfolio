# builds chess/tableau/Is Chess Getting Younger.twb
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "tableau_tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import graphics as g  # noqa: E402
from twb import (Dashboard, Datasource, Parameters, Sheet, bool_filter, f, member_filter, theme_rules,  # noqa: E402
                 workbook)

DATA = ROOT / "data" / "tableau"
IMG = ROOT / "tableau" / "img"
OUT = ROOT / "tableau" / "Is Chess Getting Younger.twb"

LIGHT, DARK = "#F1E5CB", "#CDAE80"
CARD, INK, MUTED, GRID, RULE = "#FFFDF8", "#231F1A", "#6B6157", "#EFE8DC", "#D8CBB4"
WALNUT, GOLD, GREEN, BEIGE = "#7A4A2A", "#C08A2E", "#2F6E4F", "#D8CCB8"
SHADOW = "#C9B48E"
FAINT = "#E4D6BD"
NATION_COL = {"India": "#E07A1F", "USA": "#2D5DA8", "Russia": "#B23A3A", "China": "#C9A227", "Ukraine": "#3B8EA5",
              "Germany": "#4A4A4A", "Other": BEIGE}
LENSES = ["All nations", "India", "USA", "Russia", "China", "Ukraine", "Germany"]

S = 205   # one square of the board
BX, BY = 60, 36
W, H = BX + 8 * S + 36, 1880

params = Parameters({"Nation": LENSES})
NATION = "[Parameters].[Nation]"
INT = "n#,##0;-#,##0"


def ds(key, csv, caption, calcs=None, colors=None, formats=None, roles=None):
    d = Datasource(key, DATA / csv, caption, calcs=calcs or {}, colors=colors or {}, roles=roles or {})
    d.formats = formats or {}
    return d


def highlight(older_label, young_test):
    # 'All nations' colours by age, otherwise it's the chosen nation vs everyone else
    return (f'IF {NATION} = "All nations" THEN (IF {young_test} THEN "Young" ELSE "{older_label}" END) '
            f'ELSEIF [nation] = {NATION} THEN "Selected nation" ELSE "Other nations" END')


gms = ds("gms", "new_gms.csv", "New grandmasters", calcs={
    "Dot": ('IF [kind] = "Median" THEN "Median age" ELSE ' + highlight("Grandmaster", "[title_age] < 18") + " END", "string", "dimension", "nominal"),
    "Show": (f'[kind] = "Grandmaster" OR [lens] = {NATION}', "boolean", "dimension", "nominal"),
    "Dot size": (f'IF [kind] = "Median" THEN 5 ELSEIF [nation] = {NATION} THEN 2.5 ELSE 1 END', "real", "measure", "quantitative"),
    "Tip": ('IF [kind] = "Median" THEN "Typical age of a new grandmaster in " + [era] + ": " + STR(INT([title_age])) '
            'ELSE "Became a grandmaster in " + STR(INT([title_year])) + ", aged about " + STR(INT([title_age])) END',
            "string", "dimension", "nominal")},
    colors={"[none:Dot:nk]": {"Median age": INK, "Young": GOLD, "Grandmaster": BEIGE, "Selected nation": GREEN, "Other nations": BEIGE}},
    formats={"x": "n0;-0", "y": "n0;-0"})
records = ds("records", "records.csv", "Youngest grandmaster record", calcs={
    "Holder": ('IF [year] = 2021 THEN "Current record" ELSE "Former record" END', "string", "dimension", "nominal")},
    colors={"[none:Holder:nk]": {"Current record": GOLD, "Former record": WALNUT}}, formats={"held_for": INT, "x": "n0;-0", "age": "n0;-0"})
top100 = ds("top100", "top100.csv", "World top 100 by age", formats={"players": INT, "avg_age_top100": "n#,##0.0;-#,##0.0"})
top100.ramps = {"[sum:players:qk]": "brown_10_0"}
feds = ds("feds", "feds.csv", "Grandmasters by nation", calcs={
    "Line": (f'IF {NATION} = "All nations" OR [nation] = {NATION} THEN [nation] ELSE "Other" END', "string", "dimension", "nominal")},
    colors={"[none:Line:nk]": NATION_COL}, formats={"gms": INT, "median_age": INT})
r2700 = ds("r2700", "r2700_long.csv", "First time at 2700", calcs={
    "Bar": (highlight("Older", "[age] <= 20"), "string", "dimension", "nominal")},
    colors={"[none:Bar:nk]": {"Young": GOLD, "Older": "#B79B78", "Selected nation": GREEN, "Other nations": BEIGE}},
    formats={"age": INT, "birth_year": "n0;-0", "first_year": "n0;-0", "point_year": "n0;-0"})
kpis = ds("kpis", "kpis.csv", "Headline numbers")
text = ds("text", "text.csv", "Commentary", calcs={
    "Lens match": (f'[lens] = {NATION} OR [lens] = "Any"', "boolean", "dimension", "nominal")})

sheets = []
HEAD = {"fontsize": "12", "fontcolor": WALNUT, "fontname": "Georgia", "bold": "true"}
BOLD = {"fontname": "Tableau Bold"}
BIG = {"fontsize": "12", "fontname": "Tableau Bold"}


def styled(s, hide=(), grid=None, fixed=(), bg=CARD, params_used=True):
    s.uses_params = params_used
    s.style_rules = theme_rules(bg, INK, MUTED, grid=grid, hide_axis_titles=[(s.ref(x), sc) for x, sc in hide],
                                fixed_axes=[(s.ref(x), lo, hi) for x, lo, hi in fixed])
    sheets.append(s)
    return s


def tip_fields(s, *flds):
    s.enc.setdefault("tooltip", []).extend(flds)


for metric in ("champion", "youngest", "since2018", "top10"):
    s = Sheet(f"BAN {metric}", kpis, "Text")
    s.enc = {"text": [f("none", "label", "nk"), f("none", "blurb", "nk")]}
    s.filters.append(member_filter(f("none", "metric", "nk"), metric))
    s.label = [(f("none", "label", "nk"), {"fontname": "Georgia", "bold": "true", "fontsize": "30", "fontcolor": WALNUT if metric == "champion" else INK}),
               "\n", (f("none", "blurb", "nk"), {"fontsize": "10", "fontcolor": MUTED})]
    styled(s, params_used=False)

s = Sheet("New grandmasters", gms, "Circle")
s.cols, s.rows = [f("sum", "x")], [f("sum", "y")]
s.enc = {"color": [f("none", "Dot", "nk")], "size": [f("sum", "Dot size")], "detail": [f("none", "player", "nk"), f("none", "era", "nk")]}
s.filters.append(bool_filter(f("none", "Show", "nk")))
tip = f("min", "Tip", "nk")
tip_fields(s, tip, f("min", "fed", "nk"))
s.tooltip = [(f("none", "player", "nk"), HEAD), " (", (f("min", "fed", "nk"), {"fontcolor": MUTED}), ")\n", (tip, {})]
styled(s, hide=[(f("sum", "x"), "cols"), (f("sum", "y"), "rows")], grid=GRID, fixed=[(f("sum", "y"), 10, 50)])
s.style_rules += [f"<style-rule element='axis'><encoding attr='space' class='0' field='{s.ref(f('sum', 'x'))}' field-type='quantitative' "
                  "max='2025.6' min='2000.4' range-type='fixed' scope='cols' type='space' /></style-rule>"]
s.mark_size = 0.6

s = Sheet("Record", records, "Bar")
s.cols, s.rows = [f("sum", "x")], [f("sum", "age")]
s.enc = {"color": [f("none", "Holder", "nk")], "detail": [f("none", "player", "nk")],
         "text": [f("none", "label_name", "nk"), f("none", "label_age", "nk")]}
s.label = [(f("none", "label_name", "nk"), {"fontsize": "8", "fontname": "Tableau Bold", "fontcolor": INK}), "\n",
           (f("none", "label_age", "nk"), {"fontsize": "8", "fontcolor": MUTED})]
tip_fields(s, f("min", "country", "nk"), f("sum", "year"), f("sum", "held_for"), f("min", "age_label", "nk"))
s.tooltip = [(f("none", "player", "nk"), HEAD), " (", (f("min", "country", "nk"), {"fontcolor": MUTED}), ")\n",
             "Youngest grandmaster ever in ", (f("sum", "year"), BOLD), ", aged ", (f("min", "age_label", "nk"), BOLD), "\n",
             "The record stood for ", (f("sum", "held_for"), {}), " years"]
s.mark_size = 0.4
styled(s, hide=[(f("sum", "x"), "cols"), (f("sum", "age"), "rows")], grid=GRID, fixed=[(f("sum", "age"), 0, 30)], params_used=False)
s.style_rules += [f"<style-rule element='axis'><encoding attr='space' class='0' field='{s.ref(f('sum', 'x'))}' field-type='quantitative' "
                  "max='2026' min='1946' range-type='fixed' scope='cols' type='space' /></style-rule>"]
records.formats["year"] = "n0;-0"

s = Sheet("Top 100 ages", top100, "Square")
s.rows, s.cols = [f("none", "year", "ok")], [f("none", "band", "nk")]
s.enc = {"color": [f("sum", "players")]}
s.sort = (f("none", "band", "nk"), f("sum", "band_order"), "ASC")
lp, a100 = f("min", "leading_players", "nk"), f("avg", "avg_age_top100")
tip_fields(s, lp, a100)
s.tooltip = [(f("none", "year", "ok"), HEAD), " · ", (f("none", "band", "nk"), {"fontcolor": MUTED}), "\n",
             (f("sum", "players"), BIG), " of the world top 100\n", "Highest rated: ", (lp, BOLD), "\n",
             "Top-100 average age that year: ", (a100, {})]
styled(s, hide=[(f("none", "year", "ok"), "cols"), (f("none", "band", "nk"), "rows")], params_used=False)
s.mark_size = 5

s = Sheet("Nations", feds, "Line")
s.cols, s.rows = [f("none", "year", "ok")], [f("sum", "gms")]
s.enc = {"color": [f("none", "Line", "nk")], "detail": [f("none", "nation", "nk")]}
tip_fields(s, f("sum", "median_age"))
s.tooltip = [(f("none", "nation", "nk"), HEAD), " · ", (f("none", "year", "ok"), {"fontcolor": MUTED}), "\n",
             (f("sum", "gms"), BIG), " grandmasters on the list\n", "Half of them were ", (f("sum", "median_age"), BOLD), " or older"]
styled(s, hide=[(f("sum", "gms"), "rows"), (f("none", "year", "ok"), "cols")], grid=GRID)

s = Sheet("2700 lifelines", r2700, "Line")
s.cols, s.rows = [f("sum", "point_year")], [f("sum", "row")]
s.enc = {"color": [f("none", "Bar", "nk")], "detail": [f("none", "player", "nk")], "path": [f("none", "point", "nk")]}
tip_fields(s, f("min", "fed", "nk"), f("min", "first_year"), f("min", "birth_year"), f("min", "age"))
s.tooltip = [(f("none", "player", "nk"), HEAD), " (", (f("min", "fed", "nk"), {"fontcolor": MUTED}), ")\n",
             "Born ", (f("min", "birth_year"), {}), " · first rated 2700+ in January ", (f("min", "first_year"), BOLD), "\n",
             "Aged about ", (f("min", "age"), BIG)]
styled(s, hide=[(f("sum", "point_year"), "cols"), (f("sum", "row"), "rows")], fixed=[(f("sum", "row"), 0, 98)])
s.style_rules += [f"<style-rule element='axis'><encoding attr='space' class='0' field='{s.ref(f('sum', 'point_year'))}' field-type='quantitative' "
                  "max='2027' min='1962' range-type='fixed' scope='cols' type='space' /></style-rule>",
                  f"<style-rule element='axis'><format attr='display' class='0' field='{s.ref(f('sum', 'row'))}' scope='rows' value='false' /></style-rule>"]
s.mark_size = 0.25

ALIGN = "<style-rule element='cell'><format attr='text-align' value='left' /><format attr='vertical-align' value='top' /></style-rule>"


def story(chapter, key=None, title_size=16, body_size=11, body_color=MUTED, title_color=INK):
    s = Sheet(f"Text {chapter}", text, "Text")
    t, p1 = f("none", "title", "nk"), f("none", "p1", "nk")
    s.enc = {"text": [t, p1]}
    s.filters += [member_filter(f("none", "chapter", "nk"), chapter), bool_filter(f("none", "Lens match", "nk"))]
    s.label = [(t, {"fontname": "Georgia", "bold": "true", "fontsize": str(title_size), "fontcolor": title_color}), "\n"]
    if key:
        # little squares as the colour key, trailing spaces so tableau keeps them apart
        s.label += [("\u25a0 " + tx + "    ", {"fontname": "Tableau Semibold", "fontsize": str(body_size - 1), "fontcolor": col})
                    for tx, col in key] + ["\n"]
    s.label += [(p1, {"fontsize": str(body_size), "fontcolor": body_color})]
    styled(s)
    s.style_rules = theme_rules(CARD, INK, MUTED) + [ALIGN]
    return s


story("newgms", key=[("median age", INK), ("before 18", GOLD), ("chosen nation", GREEN)])
story("record", key=[("former record", WALNUT), ("current record", GOLD)])
story("top100", key=[("few players", "#E3B07E"), ("lots", "#9A3324")])
story("nations", key=[(n, NATION_COL[n]) for n in ("India", "USA", "Russia", "China", "Ukraine", "Germany")])
story("r2700", key=[("there by 20", GOLD), ("older", "#B79B78"), ("chosen nation", GREEN)])
story("verdict", title_size=10, body_size=13, body_color=INK, title_color=WALNUT)

d = Dashboard("Is Chess Getting Younger", W, H, CARD)
T = lambda txt, size, color=INK, font="Tableau Book": (txt, {"fontname": font, "fontsize": str(size), "fontcolor": color})
GAP = 15


def block(col, row, w, h):
    # card for a block of squares, rows counted from the top of the board
    return BX + col * S + GAP, BY + row * S + GAP, w * S - 2 * GAP, h * S - 2 * GAP


HEADER, HERO = block(0, 0, 4, 2), block(0, 2, 8, 2)
KPI = [block(4, 0, 2, 1), block(6, 0, 2, 1), block(4, 1, 2, 1), block(6, 1, 2, 1)]
CH = {"record": block(0, 4, 4, 2), "top100": block(4, 4, 4, 2), "nations": block(0, 6, 4, 2), "r2700": block(4, 6, 4, 2)}
VERDICT = (BX, BY + 8 * S + 46, 8 * S, 96)
cards = [HEADER, HERO, VERDICT] + KPI + list(CH.values())

glyphs = []
for (x, y, w, h), p in zip(KPI, "KPNQ"):
    glyphs.append((p, x + 58, y + h - 40, 86, FAINT))
kick = {"newgms": ("P", HERO), "record": ("N", CH["record"]), "top100": ("B", CH["top100"]),
        "nations": ("R", CH["nations"]), "r2700": ("Q", CH["r2700"])}
for p, (x, y, w, h) in kick.values():
    glyphs.append((p, x + 28, y + 40, 26, WALNUT))
glyphs.append(("K", VERDICT[0] + 34, VERDICT[1] + 64, 40, WALNUT))
# pawn -> king along the bottom of the header
hx, hy, hw, hh = HEADER
for i, (p, size) in enumerate(zip("PNBRQK", (34, 42, 50, 58, 66, 76))):
    glyphs.append((p, hx + 420 + i * 60 + size / 4, hy + hh - 22, size, FAINT if i < 5 else WALNUT))

d.image(g.background(IMG / "board.png", W, H, (BX, BY, S), cards, glyphs, LIGHT, DARK, CARD, INK, MUTED, SHADOW), 0, 0, W, H)

d.text([("Twenty-five years of FIDE rating lists", {"fontname": "Georgia", "fontsize": "12", "fontcolor": WALNUT, "italic": "true"})],
       hx + 24, hy + 20, 500, 22, padding=0)
d.text([("Is chess getting younger?", {"fontname": "Georgia", "bold": "true", "fontsize": "33", "fontcolor": INK})],
       hx + 24, hy + 44, hw - 40, 60, padding=0)
d.text([T("In December 2024 an 18-year-old from Chennai became the youngest undisputed world champion in history. Was Gukesh "
          "a one-off, or part of something bigger? Twenty-five years of FIDE rating lists – every rated player's age, title "
          "and rating – are a good place to look.", 13, MUTED)], hx + 24, hy + 112, hw - 48, 110, padding=0)
d.text([T("Five moves, pawn to king: new grandmasters, record-breakers, the world top 100, the nations and the 2700 club. "
          "Hover over a dot, bar or line to see who it is.", 11, INK)], hx + 24, hy + 204, hw - 48, 44, padding=0)
d.param_control(params.ref("Nation"), hx + 24, hy + hh - 92, 230, 64, mode="compact")
d.text([("Pick a nation to follow its players through the story", {"fontname": "Georgia", "fontsize": "11", "fontcolor": WALNUT, "italic": "true"})],
       hx + 24, hy + hh - 112, 400, 20, padding=0)

for (x, y, w, h), m in zip(KPI, ("champion", "youngest", "since2018", "top10")):
    d.sheet(f"BAN {m}", x + 112, y + 18, w - 128, h - 30, bg=CARD, padding=4)


def kicker(x, y, move, label):
    d.text([("{}  ".format(move), {"fontname": "Georgia", "bold": "true", "fontsize": "12", "fontcolor": WALNUT}),
            (label, {"fontname": "Georgia", "italic": "true", "fontsize": "12", "fontcolor": WALNUT})], x + 48, y + 16, 420, 22, padding=0)


x, y, w, h = HERO
kicker(x, y, "1. e4", "the new grandmasters")
d.sheet("Text newgms", x + 18, y + 44, 360, h - 56, bg=CARD, padding=0)
d.sheet("New grandmasters", x + 392, y + 14, w - 406, h - 28, bg=CARD, padding=4)

for key, (label, sheet) in {"record": (("2. Nf3", "the record"), "Record"), "top100": (("3. Bb5", "the elite"), "Top 100 ages"),
                            "nations": (("4. O-O", "the nations"), "Nations"), "r2700": (("5. Qe2", "the 2700 club"), "2700 lifelines")}.items():
    x, y, w, h = CH[key]
    kicker(x, y, *label)
    d.sheet(f"Text {key}", x + 18, y + 44, 290, h - 56, bg=CARD, padding=0)
    d.sheet(sheet, x + 318, y + 14, w - 330, h - 28, bg=CARD, padding=4)

vx, vy, vw, vh = VERDICT
d.sheet("Text verdict", vx + 70, vy + 12, vw - 90, vh - 18, bg=CARD, padding=0)
d.text([T("Sources: FIDE standard rating lists, every January from 2001 to 2026 (ratings.fide.com), and Wikipedia's list of the "
          "youngest grandmasters for the record holders. FIDE only gives a birth year, so ages could be out by one. A 'new grandmaster' "
          "is someone whose GM title first shows up on a January list, so the title year is taken as the year before. The top 100 only "
          "counts active players. Nations are whichever federation a player was under on that list - anyone who switched counts for "
          "their new one.", 9, MUTED)], BX, vy + vh + 10, 8 * S, 44, padding=0)

workbook([params, gms, records, top100, feds, r2700, kpis, text], sheets, [d], OUT)
print("written", OUT, W, "x", H)
