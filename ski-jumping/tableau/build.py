# builds ski-jumping/tableau/Who Rules the Skies.twb
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "tableau_tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import graphics as g  # noqa: E402
from twb import (Dashboard, Datasource, Parameters, Sheet, bool_filter, f, member_filter, theme_rules,  # noqa: E402
                 workbook)

DATA = ROOT / "data" / "tableau"
OUT = ROOT / "tableau" / "Who Rules the Skies.twb"
IMG = ROOT / "tableau" / "img"

BG, PANEL, INK, MUTED, GRID, RULE = "#EEF3F7", "#FFFFFF", "#0B1F33", "#4F6275", "#E3E9EF", "#C9D4DE"
ACCENT, RED, ICE, ABROAD = "#1F5FAD", "#D62828", "#9DB3C8", "#7F9AB5"
W, H = 1900, 1600   # landscape on purpose, reads left to right
NATION = {"Austria": "#D62828", "Norway": "#1D4E89", "Germany": "#2F3E46", "Poland": "#F28C38", "Slovenia": "#2A9D8F",
          "Japan": "#E9B949", "Finland": "#7FB3D5", "USA": "#7B5EA7", "Switzerland": "#B5838D", "Canada": "#B07D62",
          "Italy": "#6A994E", "Russia": "#9A8C98", "France": "#5DA5DA", "Other nations": "#CBD3DB"}
NG = "[none:nation_group:nk]"

params = Parameters({"Competition": ["Men", "Women"]})
CALC = {"Competition match": ("[competition] = [Parameters].[Competition]", "boolean", "dimension", "nominal")}


def ds(key, csv, caption, colors=None, formats=None):
    d = Datasource(key, DATA / csv, caption, calcs=dict(CALC), colors=colors or {})
    d.formats = formats or {}
    return d


INT = "n#,##0;-#,##0"
podiums = ds("podiums", "podiums.csv", "Podiums", {NG: NATION}, {"share": "p0%", "podiums": INT, "lead_podiums": INT, "seasons_total": INT})
dominance = ds("dominance", "dominance.csv", "One-jumper seasons", {NG: NATION}, {"share": "p0%", "wins": INT, "events": INT, "different_winners": INT})
dominance.calcs["Yr"] = ("\"'\" + RIGHT(STR([season]), 2)", "string", "dimension", "ordinal")
dominance.ramps = {"[sum:different_winners:qk]": "blue_10_0"}
winners = ds("winners", "winners.csv", "Winners", {NG: NATION}, {"wins": INT, "podiums": INT, "starts": INT})
ages = ds("ages", "ages.csv", "Podium ages", formats={"avg_age": "n#,##0.0;-#,##0.0", "youngest_age": INT, "oldest_age": INT})
home = ds("home", "home.csv", "Home hill", {"[none:where:nk]": {"At home": RED, "Abroad": ABROAD}},
          {"podium_rate": "p0%", "home_lift": "n#,##0.0;-#,##0.0", "podiums": INT, "starts": INT})
flights = ds("flights", "flights.csv", "Flights", formats={"longest": "n#,##0.0;-#,##0.0"})
kpis = ds("kpis", "kpis.csv", "Headline numbers")
text = ds("text", "text.csv", "Commentary")

MATCH = bool_filter(f("none", "Competition match", "nk"))
sheets = []
TIP_HEAD = {"fontsize": "12", "fontcolor": ACCENT, "fontname": "Tableau Bold"}
BIG = {"fontsize": "12", "fontname": "Tableau Bold"}
SOFT = {"fontcolor": MUTED}


def styled(s, hide=(), grid=None, fixed=()):
    s.uses_params = True
    s.filters.append(MATCH)
    s.style_rules = theme_rules(PANEL, INK, MUTED, grid=grid, hide_axis_titles=[(s.ref(x), sc) for x, sc in hide],
                                fixed_axes=[(s.ref(x), lo, hi) for x, lo, hi in fixed])
    sheets.append(s)
    return s


def tip_fields(s, *flds):
    s.enc.setdefault("tooltip", []).extend(flds)


for metric in ("top_nation", "leaders", "top_athlete", "longest"):
    s = Sheet(f"BAN {metric}", kpis, "Text")
    s.enc = {"text": [f("none", "label", "nk"), f("none", "blurb", "nk")]}
    s.filters.append(member_filter(f("none", "metric", "nk"), metric))
    s.label = [((f("none", "label", "nk")), {"fontname": "Tableau Bold", "fontsize": "28", "fontcolor": ACCENT if metric == "longest" else INK}),
               "\n", ((f("none", "blurb", "nk")), {"fontname": "Tableau Book", "fontsize": "10", "fontcolor": MUTED})]
    styled(s)

s = Sheet("Empires", podiums, "Area")
s.cols, s.rows = [f("none", "season", "ok")], [f("sum", "share")]
s.enc = {"color": [f("none", "nation_group", "nk")]}
lead, lead_n, label, total = f("min", "lead_athlete", "nk"), f("sum", "lead_podiums"), f("min", "season_label", "nk"), f("sum", "seasons_total")
tip_fields(s, lead, lead_n, label, total, f("sum", "podiums"))
s.tooltip = [(f("none", "nation_group", "nk"), TIP_HEAD), " · ", (label, SOFT), "\n",
             (f("sum", "share"), BIG), " of the season's podium places (", (f("sum", "podiums"), {}), " of ", (total, {}), ")\n",
             "Leading the way: ", (lead, {"fontname": "Tableau Bold"}), " with ", (lead_n, {}), " podiums"]
styled(s, hide=[(f("sum", "share"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID)
s.style_rules += ["<style-rule element='cell'><format attr='text-format' field='[federated.podiums].[sum:share:qk]' value='p0%' /></style-rule>",
                  "<style-rule element='axis'><format attr='width' field='[federated.podiums].[sum:share:qk]' value='48' /></style-rule>"]

s = Sheet("Dominance", dominance, "Bar")
s.cols, s.rows = [f("none", "season", "ok")], [f("sum", "share")]
surname = f("min", "surname", "nk")
s.enc = {"color": [f("none", "nation_group", "nk")], "text": [surname]}
s.label = [(surname, {"fontsize": "8", "fontcolor": MUTED})]
ath, lab, ev, dw = f("min", "athlete", "nk"), f("min", "season_label", "nk"), f("sum", "events"), f("sum", "different_winners")
tip_fields(s, ath, lab, ev, dw, f("sum", "wins"))
s.tooltip = [(lab, TIP_HEAD), "\n", (ath, BIG), " (", (f("none", "nation_group", "nk"), {}), ") won ", (f("sum", "wins"), {"fontname": "Tableau Bold"}),
             " of ", (ev, {}), " events – ", (f("sum", "share"), {"fontname": "Tableau Bold"}), " of the season\n",
             (dw, {}), " different jumpers won at least once", ]
styled(s, hide=[(f("sum", "share"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID, fixed=[(f("sum", "share"), 0, 1)])
s.style_rules += ["<style-rule element='axis'><format attr='width' field='[federated.dominance].[sum:share:qk]' value='44' /></style-rule>"]

# heat strip of how many different winners
s = Sheet("Open field", dominance, "Square")
s.cols = [f("none", "Yr", "ok")]
s.enc = {"color": [f("sum", "different_winners")], "text": [f("sum", "different_winners")]}
s.label = [(f("sum", "different_winners"), {"fontsize": "9", "fontcolor": "#FFFFFF", "fontname": "Tableau Bold"})]
s.mark_size = 5
tip_fields(s, lab)
s.tooltip = [(lab, TIP_HEAD), "\n", (f("sum", "different_winners"), BIG), " different jumpers won a World Cup event this season"]
styled(s, hide=[(f("none", "Yr", "ok"), "cols")])

s = Sheet("Legends", winners, "Bar")
s.rows, s.cols = [f("none", "athlete", "nk")], [f("sum", "wins")]
s.enc = {"color": [f("none", "nation_group", "nk")], "text": [f("sum", "wins")]}
s.label_show = True
s.sort = (f("none", "athlete", "nk"), f("sum", "wins"), "DESC")
fw, lw, pods, starts = f("min", "first_win", "nk"), f("min", "last_win", "nk"), f("sum", "podiums"), f("sum", "starts")
tip_fields(s, fw, lw, pods, starts)
s.tooltip = [(f("none", "athlete", "nk"), TIP_HEAD), " · ", (f("none", "nation_group", "nk"), SOFT), "\n",
             (f("sum", "wins"), BIG), " wins and ", (pods, {"fontname": "Tableau Bold"}), " podiums from ", (starts, {}), " starts\n",
             "First win ", (fw, {}), ", last win ", (lw, {})]
styled(s, hide=[(f("sum", "wins"), "cols"), (f("none", "athlete", "nk"), "rows")])

s = Sheet("Podium age", ages, "Line")
s.cols, s.rows = [f("none", "season", "ok")], [f("sum", "avg_age")]
s.mark_color = ACCENT
yn, ya, on, oa = f("min", "youngest", "nk"), f("sum", "youngest_age"), f("min", "oldest", "nk"), f("sum", "oldest_age")
tip_fields(s, yn, ya, on, oa, lab := f("min", "season_label", "nk"))
s.tooltip = [(lab, TIP_HEAD), "\n", "Average age on the podium: ", (f("sum", "avg_age"), BIG), "\n",
             "Youngest: ", (yn, {"fontname": "Tableau Bold"}), " (", (ya, {}), ")\n", "Oldest: ", (on, {"fontname": "Tableau Bold"}), " (", (oa, {}), ")"]
styled(s, hide=[(f("sum", "avg_age"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID, fixed=[(f("sum", "avg_age"), 18, 30)])

s = Sheet("Home hill", home, "Circle")
s.rows, s.cols = [f("none", "nation_name", "nk")], [f("sum", "podium_rate")]
s.enc = {"color": [f("none", "where", "nk")]}
s.mark_size = 3
s.sort = (f("none", "nation_name", "nk"), f("avg", "home_lift"), "DESC")
hills = f("min", "home_hills", "nk")
tip_fields(s, hills, f("sum", "podiums"), f("sum", "starts"))
s.tooltip = [(f("none", "nation_name", "nk"), TIP_HEAD), " · ", (f("none", "where", "nk"), SOFT), "\n",
             "On the podium in ", (f("sum", "podium_rate"), BIG), " of starts (", (f("sum", "podiums"), {}), " of ", (f("sum", "starts"), {}), ")\n",
             "Main home hills: ", (hills, {})]
styled(s, hide=[(f("sum", "podium_rate"), "cols"), (f("none", "nation_name", "nk"), "rows")], grid=GRID)

s = Sheet("Flights", flights, "Line")
s.cols, s.rows = [f("none", "season", "ok")], [f("sum", "longest")]
s.mark_color = ACCENT
who, city = f("min", "athlete", "nk"), f("min", "city", "nk")
tip_fields(s, who, city, lab)
s.tooltip = [(lab, TIP_HEAD), "\n", "Longest jump of the season: ", (f("sum", "longest"), BIG), " m\n",
             (who, {"fontname": "Tableau Bold"}), " at ", (city, {})]
# 120-260 fits both men and women
styled(s, hide=[(f("sum", "longest"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID, fixed=[(f("sum", "longest"), 120, 260)])

ALIGN = "<style-rule element='cell'><format attr='text-align' value='left' /><format attr='vertical-align' value='top' /></style-rule>"


def story(chapter, key=None, title_size=17, body_size=11, body_color=MUTED, title_color=INK, bg=BG):
    s = Sheet(f"Text {chapter}", text, "Text")
    t, p1 = f("none", "title", "nk"), f("none", "p1", "nk")
    s.enc = {"text": [t, p1]}
    s.filters.append(member_filter(f("none", "chapter", "nk"), chapter))
    s.label = [(t, {"fontname": "Tableau Bold", "fontsize": str(title_size), "fontcolor": title_color}), "\n"]
    if key:
        s.label += [(tx, {"fontname": "Tableau Bold", "fontsize": str(body_size), "fontcolor": col}) for tx, col in key] + ["\n"]
    s.label += [(p1, {"fontsize": str(body_size), "fontcolor": body_color})]
    styled(s)
    s.style_rules = theme_rules(bg, INK, MUTED) + [ALIGN]
    return s


for ch in ("empires", "dominance", "legends", "age", "flights"):
    story(ch)
story("home", key=[("\u25cf At home     ", RED), ("\u25cf Abroad", ABROAD)])
story("verdict", title_size=10, body_size=13, body_color=INK, title_color=ACCENT, bg=BG)

d = Dashboard("Who Rules the Skies", W, H, BG)
T = lambda txt, size, color=INK, font="Tableau Book": (txt, {"fontname": font, "fontsize": str(size), "fontcolor": color})

# header 0-360, then a row of 2 chapters and a row of 4
HORIZON = 360
KPI_X, KPI_Y, KPI_W, KPI_H = 640, 64, 280, 124
R1, R1_H = 384, 480
R2, R2_TEXT, R2_CARD = 892, 156, 262
COLS = [48 + i * 458 for i in range(4)]
C1_TEXT_W, C1_CARD = 340, (410, 740)
C2_X, C2_W = 1190, 662
C2_TEXT_H = 148

kpi_pos = [(KPI_X + (i % 2) * (KPI_W + 15), KPI_Y + (i // 2) * (KPI_H + 14)) for i in range(4)]
cards = [(x, y, KPI_W, KPI_H, "kpi") for x, y in kpi_pos]
cards += [(C1_CARD[0], R1, C1_CARD[1], R1_H, "chart"), (C2_X, R1 + C2_TEXT_H + 14, C2_W, R1_H - C2_TEXT_H - 14, "chart")]
cards += [(x, R2 + 22 + R2_TEXT, 430, R2_CARD, "chart") for x in COLS]
scene_w = W - (KPI_X + 2 * KPI_W + 15) + 30
d.image(g.background(IMG / "background.png", W, H, cards, INK, ACCENT, RED, scene_box=(W - scene_w, HORIZON, scene_w),
                     horizon=HORIZON), 0, 0, W, H)

d.text([T("FIS Ski Jumping World Cup – men since 2001, women since 2012", 11, ACCENT, "Tableau Medium")], 48, 46, 580, 24, padding=0)
d.text([T("Who rules the skies?", 38, INK, "Tableau Bold")], 48, 72, 590, 72, padding=0)
d.text([T("Every winter a few dozen athletes launch themselves off a ramp at around 90 km/h and try to stay in the air for longer "
          "than a football pitch. A handful of nations have made a habit of winning. None of them stays on top for long.",
          13, MUTED)], 48, 150, 560, 110, padding=0)
d.param_control(params.ref("Competition"), 48, 268, 212, 78, mode="list")
d.text([T("Pick a competition – the charts and the writing both switch over. Hover the charts for the jumpers behind them.", 10, MUTED)],
       270, 282, 340, 62, padding=0)
for (x, y), m in zip(kpi_pos, ("top_nation", "leaders", "top_athlete", "longest")):
    d.sheet(f"BAN {m}", x + 10, y + 14, KPI_W - 46, KPI_H - 22, bg=PANEL, padding=4)


def kicker(x, y, num, label):
    d.text([T(f"{num}.  ", 12, ACCENT, "Tableau Bold"), T(label, 12, ACCENT, "Tableau Medium")], x, y, 420, 22, padding=0)


kicker(48, R1, "I", "Empires rise and fall")
d.sheet("Text empires", 44, R1 + 24, C1_TEXT_W + 8, R1_H - 24, bg=BG, padding=0)
d.sheet("Empires", C1_CARD[0] + 6, R1 + 6, C1_CARD[1] - 140, R1_H - 12, bg=PANEL, padding=6)
d.legend("Empires", f"[federated.podiums].{NG}", C1_CARD[0] + C1_CARD[1] - 128, R1 + 24, 120, 330, horizontal=False)

kicker(C2_X, R1, "II", "One-jumper seasons")
d.sheet("Text dominance", C2_X - 4, R1 + 24, C2_W + 8, C2_TEXT_H - 24, bg=BG, padding=0)
card_y = R1 + C2_TEXT_H + 14
card_h = R1_H - C2_TEXT_H - 14
d.sheet("Dominance", C2_X + 6, card_y + 6, C2_W - 12, card_h - 92, bg=PANEL, padding=6)
d.text([T("Different winners each season", 9, MUTED, "Tableau Semibold")], C2_X + 16, card_y + card_h - 84, 300, 16, padding=0)
d.sheet("Open field", C2_X + 6, card_y + card_h - 66, C2_W - 12, 60, bg=PANEL, padding=4)

for x, (num, label, chapter, sheet) in zip(COLS, (("III", "The legends", "legends", "Legends"),
                                                  ("IV", "Older and wiser", "age", "Podium age"),
                                                  ("V", "Home hill", "home", "Home hill"),
                                                  ("VI", "Further than ever", "flights", "Flights"))):
    kicker(x, R2, num, label)
    d.sheet(f"Text {chapter}", x - 4, R2 + 22, 438, R2_TEXT, bg=BG, padding=0)
    d.sheet(sheet, x + 6, R2 + 22 + R2_TEXT + 6, 418, R2_CARD - 12, bg=PANEL, padding=6)

y = R2 + 22 + R2_TEXT + R2_CARD + 20
d.blank(48, y, W - 96, 1, RULE)
d.sheet("Text verdict", 44, y + 8, W - 88, 66, bg=BG, padding=0)
d.text([T("Results from fis-ski.com (individual World Cup events only, no team events, qualifying or trial rounds) – 668 men's and "
          "261 women's events, collected October 2026. One men's race is missing from FIS's own listing. A season is named by the "
          "year it ends, so 2025 means 2024/25. Jump distances only go back to 2015. Ages are worked out from birth year alone, so "
          "might be a year out. Home hill only includes nations with 150+ starts at home.", 9, MUTED)],
       48, y + 78, W - 96, 34, padding=0)

workbook([params, podiums, dominance, winners, ages, home, flights, kpis, text], sheets, [d], OUT)
print("written", OUT, "height used", y + 112, "of", H)
