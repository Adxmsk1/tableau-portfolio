# builds running/tableau/The Fastest Decade.twb
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
OUT = ROOT / "tableau" / "The Fastest Decade.twb"

BG, PANEL, INK, MUTED, GRID, RULE = "#F5F1EA", "#FFFFFF", "#1F2328", "#6A645C", "#ECE6DC", "#D9D0C2"
TRACK, AMBER, STONE, GREEN, NAVY = "#C4462B", "#E39B2D", "#A39A8E", "#2F7D57", "#2B4C6F"
W, H = 1400, 3856
X0, X1 = 130, 1360   # left gutter is for the route
CW = X1 - X0
ERA = {"Before super shoes": STONE, "Arrival (2017-19)": AMBER, "Super-shoe era": TRACK}

params = Parameters({"Runners": ["Men", "Women"]})
SEXCALC = {"Sex match": ("[sex] = [Parameters].[Runners]", "boolean", "dimension", "nominal")}


def ds(key, csv, caption, colors=None, extra_calcs=None, formats=None):
    c = dict(SEXCALC)
    c.update(extra_calcs or {})
    d = Datasource(key, DATA / csv, caption, calcs=c, colors=colors or {})
    d.formats = formats or {}
    return d


INT = "n#,##0;-#,##0"  # some counts come through as floats
elite = ds("elite", "elite_by_season.csv", "Elite performances", {"[none:era:nk]": ERA, "[none:event:nk]": {"Marathon": TRACK, "Half marathon": NAVY}},
           formats={"elite_performances": INT, "elite_athletes": INT, "vs_pre": "n#,##0.0;-#,##0.0"})
depth = ds("depth", "depth_long.csv", "Depth", {"[none:depth:nk]": {"10th fastest": AMBER, "100th fastest": TRACK}})
venues = ds("venues", "venues.csv", "Venues", extra_calcs={"Yr": ("\"'\" + RIGHT(STR([season]), 2)", "string", "dimension", "ordinal")},
            formats={"share_of_season": "p0%", "elite_performances": INT})
nations = ds("nations", "nations_era.csv", "Nations",
             {"[none:nation_group:nk]": {"Kenya": TRACK, "Ethiopia": GREEN, "Japan": NAVY, "Rest of world": STONE}},
             formats={"elite_performances": INT, "busiest_runs": INT, "runners": INT})
newfaces = ds("newfaces", "newfaces.csv", "New faces", {"[none:era:nk]": ERA}, formats={"newcomers": INT})
kpis = ds("kpis", "kpis.csv", "Headline numbers")
text = ds("text", "text.csv", "Commentary")

SEX = bool_filter(f("none", "Sex match", "nk"))
sheets = []
HEAD = {"fontsize": "12", "fontcolor": TRACK, "fontname": "Tableau Bold"}
BOLD = {"fontname": "Tableau Bold"}
BIG = {"fontsize": "12", "fontname": "Tableau Bold"}


def styled(s, hide=(), grid=None, free=()):
    s.uses_params = True
    s.filters.append(SEX)
    s.style_rules = theme_rules(PANEL, INK, MUTED, grid=grid, hide_axis_titles=[(s.ref(x), sc) for x, sc in hide],
                                free_axes=[s.ref(x) for x in free])
    sheets.append(s)
    return s


def tip_fields(s, *flds):
    # fields that are only in the tooltip still need to be on the sheet
    s.enc.setdefault("tooltip", []).extend(flds)


BIBS = {"multiple": "MORE FAST RACES", "rank_then": "DEEPER FIELDS", "athletes": "MORE ELITE RUNNERS", "top_venue": "FASTEST COURSE"}
for metric in BIBS:
    s = Sheet(f"BAN {metric}", kpis, "Text")
    s.enc = {"text": [f("none", "label", "nk"), f("none", "blurb", "nk")]}
    s.filters.append(member_filter(f("none", "metric", "nk"), metric))
    s.label = [((f("none", "label", "nk")), {"fontname": "Tableau Bold", "fontsize": "30", "fontcolor": TRACK if metric == "multiple" else INK}),
               "\n", ((f("none", "blurb", "nk")), {"fontname": "Tableau Book", "fontsize": "10", "fontcolor": MUTED})]
    styled(s)

fr, ft, fv = f("min", "fastest_runner", "nk"), f("min", "fastest_time", "nk"), f("min", "fastest_venue", "nk")
s = Sheet("Elite per season", elite, "Bar")
s.cols, s.rows = [f("none", "season", "ok")], [f("sum", "elite_performances")]
s.enc = {"color": [f("none", "era", "nk")]}
tip_fields(s, fr, ft, fv, f("sum", "elite_athletes"))
s.filters.append(member_filter(f("none", "event", "nk"), "Marathon"))
s.tooltip = [(f("none", "season", "ok"), HEAD), "\n",
             (f("sum", "elite_performances"), BIG), " elite marathons, run by ", (f("sum", "elite_athletes"), BOLD), " different athletes\n",
             "Fastest of the year: ", (fr, BOLD), ", ", (ft, {}), " in ", (fv, {})]
styled(s, hide=[(f("sum", "elite_performances"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID)

s = Sheet("Depth", depth, "Line")
s.cols, s.rows = [f("none", "season", "ok")], [f("avg", "faster_than_2001")]
s.enc = {"color": [f("none", "depth", "nk")]}
tl, gl = f("min", "time_label", "nk"), f("min", "gain_label", "nk")
tip_fields(s, tl, gl)
s.tooltip = [(f("none", "season", "ok"), HEAD), "\n", "The ", (f("none", "depth", "nk"), {}), " marathon of the year: ", (tl, BIG), "\n",
             (gl, BOLD), " quicker than the same place on the list in 2001"]
styled(s, hide=[(f("avg", "faster_than_2001"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID)

s = Sheet("Venues", venues, "Circle")
s.cols, s.rows = [f("none", "Yr", "ok")], [f("none", "venue", "nk")]
s.enc = {"size": [f("sum", "elite_performances")]}
s.mark_size = 2.5
s.mark_color = TRACK
s.sort = (f("none", "venue", "nk"), f("sum", "elite_performances"), "DESC")
vr, vt_ = f("min", "fastest_runner", "nk"), f("min", "fastest_time", "nk")
s.enc["detail"] = [f("none", "season", "ok")]
tip_fields(s, vr, vt_, f("sum", "share_of_season"))
s.tooltip = [(f("none", "venue", "nk"), HEAD), " · ", (f("none", "season", "ok"), {"fontcolor": MUTED}), "\n",
             (f("sum", "elite_performances"), BIG), " elite marathons - ", (f("sum", "share_of_season"), BOLD), " of the year's total\n",
             "Fastest here: ", (vr, BOLD), ", ", (vt_, {})]
styled(s, hide=[(f("none", "Yr", "ok"), "cols")])

s = Sheet("Nations", nations, "Bar")
s.rows, s.cols = [f("none", "era_label", "ok")], [f("sum", "share")]
s.enc = {"color": [f("none", "nation_group", "nk")], "text": [f("none", "nation_group", "nk"), f("sum", "share")]}
s.label = [((f("none", "nation_group", "nk")), {"fontsize": "9", "fontcolor": "#FFFFFF"}), "\n",
           ((f("sum", "share")), {"fontsize": "11", "fontcolor": "#FFFFFF", "fontname": "Tableau Bold"})]
br, bn, nr = f("min", "busiest_runner", "nk"), f("sum", "busiest_runs"), f("sum", "runners")
tip_fields(s, br, bn, nr, f("sum", "elite_performances"))
s.tooltip = [(f("none", "nation_group", "nk"), HEAD), " · ", (f("none", "era_label", "ok"), {"fontcolor": MUTED}), "\n",
             (f("sum", "share"), BIG), " of the era's elite marathons (", (f("sum", "elite_performances"), {}), "), by ", (nr, BOLD), " different runners\n",
             "Most elite marathons: ", (br, BOLD), " (", (bn, {}), ")"]
s.label_cull = True
styled(s, hide=[(f("sum", "share"), "cols")])
s.style_rules += ["<style-rule element='cell'><format attr='text-format' field='[federated.nations].[sum:share:qk]' value='p0%' /></style-rule>",
                  "<style-rule element='label'><format attr='text-format' field='[federated.nations].[sum:share:qk]' value='p0%' /></style-rule>"]

s = Sheet("New faces", newfaces, "Area")
s.cols, s.rows = [f("none", "season", "ok")], [f("sum", "newcomers")]
s.mark_color = TRACK
nb, nt, nv = f("min", "best_newcomer", "nk"), f("min", "newcomer_time", "nk"), f("min", "newcomer_venue", "nk")
tip_fields(s, nb, nt, nv)
s.tooltip = [(f("none", "season", "ok"), HEAD), "\n", (f("sum", "newcomers"), BIG), " runners joined the elite club for the first time\n",
             "Fastest newcomer: ", (nb, BOLD), ", ", (nt, {}), " in ", (nv, {})]
styled(s, hide=[(f("sum", "newcomers"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID)

s = Sheet("Marathon vs half", elite, "Line")
s.cols, s.rows = [f("none", "season", "ok")], [f("sum", "vs_pre")]
s.enc = {"color": [f("none", "event", "nk")]}
tip_fields(s, fr, ft, fv, f("sum", "elite_performances"))
s.tooltip = [(f("none", "event", "nk"), HEAD), " · ", (f("none", "season", "ok"), {"fontcolor": MUTED}), "\n",
             (f("sum", "vs_pre"), BIG), " times the 2001-16 average (", (f("sum", "elite_performances"), {}), " elite runs)\n",
             "Fastest of the year: ", (fr, BOLD), ", ", (ft, {}), " in ", (fv, {})]
styled(s, hide=[(f("sum", "vs_pre"), "rows"), (f("none", "season", "ok"), "cols")], grid=GRID)

ALIGN = "<style-rule element='cell'><format attr='text-align' value='left' /><format attr='vertical-align' value='top' /></style-rule>"


def story(chapter, key=None, title_size=17, body_size=11, body_color=MUTED, title_color=INK, bg=BG):
    # text worksheet so the words change with the Men/Women switch
    s = Sheet(f"Text {chapter}", text, "Text")
    t, p1, p2 = f("none", "title", "nk"), f("none", "p1", "nk"), f("none", "p2", "nk")
    s.enc = {"text": [t, p1, p2]}
    s.filters.append(member_filter(f("none", "chapter", "nk"), chapter))
    s.label = [(t, {"fontname": "Tableau Bold", "fontsize": str(title_size), "fontcolor": title_color}), "\n"]
    if key:
        s.label += [(tx, {"fontname": "Tableau Bold", "fontsize": str(body_size), "fontcolor": col}) for tx, col in key] + ["\n"]
    s.label += ["\n", (p1, {"fontsize": str(body_size), "fontcolor": body_color}), "\n", "\n",
                (p2, {"fontsize": str(body_size), "fontcolor": body_color})]
    styled(s)
    s.style_rules = theme_rules(bg, INK, MUTED) + [ALIGN]
    return s


SLASH = ("  /  ", MUTED)
story("shoes", key=[("Before super shoes", STONE), SLASH, ("Arrival 2017-19", AMBER), SLASH, ("Super-shoe era", TRACK)])
story("depth", key=[("10th-fastest", AMBER), SLASH, ("100th-fastest", TRACK)])
story("courses")
story("runners", key=[("Kenya", TRACK), SLASH, ("Ethiopia", GREEN), SLASH, ("Japan", NAVY), SLASH, ("Rest of world", STONE)])
story("newfaces")
story("proof", key=[("Marathon", TRACK), SLASH, ("Half marathon", NAVY)])
story("verdict", title_size=10, body_size=13, body_color=INK, title_color=TRACK, bg=PANEL)

d = Dashboard("The Fastest Decade", W, H, BG)
T = lambda txt, size, color=INK, font="Tableau Book": (txt, {"fontname": font, "fontsize": str(size), "fontcolor": color})

d.image(g.track_band(IMG / "track.png", W, 64, TRACK), 0, 0, W, 64)
d.text([("Road running, 2001 to 2025", {"fontname": "Tableau Medium", "fontsize": "12", "fontcolor": TRACK, "italic": "true"})],
       X0, 82, 760, 24, padding=0)
d.text([T("The fastest decade\nin marathon history", 32, INK, "Tableau Bold")], X0, 108, 740, 132, padding=0)
d.text([T("In 2017 Nike put a carbon plate and a thick layer of springy foam into a racing shoe. Within a few years, elite "
          "marathon running looked like a different sport. The shoes got the headlines, but they aren't the only reason times fell.",
          13, MUTED)], X0, 240, 700, 72, padding=0)
d.param_control(params.ref("Runners"), X0, 316, 240, 76, mode="list")
d.text([("Switch between men and women and everything below changes with it.\nHover over the charts for names and times.",
         {"fontname": "Tableau Book", "fontsize": "10", "fontcolor": MUTED, "italic": "true"})], X0 + 250, 334, 470, 44, padding=0)
d.image(g.shoe(IMG / "shoe.png", INK, TRACK, "#FBF6EC", INK, MUTED), 880, 110, 480, 232)

BY, BW, BH = 404, 297, 150
gap = (CW - 4 * BW) / 3
for i, (m, label) in enumerate(BIBS.items()):
    x = X0 + i * (BW + gap)
    d.image(g.bib(IMG / f"bib_{m}.png", BW, BH, TRACK, label), x - 2, BY - 2, BW + 8, BH + 8)
    d.sheet(f"BAN {m}", x + 22, BY + 36, BW - 44, BH - 50, bg=PANEL)

markers = [(BY + BH / 2, 0, "START", "start")]


def chapter(km, mark, kicker, y, text_sheet, sheet, h=430):
    markers.append((y + 11, km, mark, "km"))
    d.text([T(kicker, 12, TRACK, "Tableau Semibold")], X0, y, 340, 22, padding=0)
    d.sheet(f"Text {text_sheet}", X0 - 4, y + 22, 364, h - 22, bg=BG, padding=0)
    d.sheet(sheet, 510, y, X1 - 510, h, bg=PANEL, padding=12)
    d.blank(X0, y + h + 24, CW, 1, RULE)


y = 610
chapter(5, "5K", "5 km · the shoes", y, "shoes", "Elite per season", h=510)
y += 560
chapter(10, "10K", "10 km · how deep it goes", y, "depth", "Depth", h=470)
y += 520
chapter(21.1, "HALF", "halfway · the courses", y, "courses", "Venues", h=460)
y += 510
chapter(30, "30K", "30 km · the runners", y, "runners", "Nations", h=420)
y += 470
chapter(35, "35K", "35 km · new faces", y, "newfaces", "New faces", h=400)
y += 450
chapter(40, "40K", "40 km · the half marathon check", y, "proof", "Marathon vs half", h=440)
y += 490

d.image(g.finish_strip(IMG / "finish.png", CW, 12, INK, PANEL), X0, y, CW, 12)
d.blank(X0, y + 12, CW, 146, PANEL)
d.sheet("Text verdict", X0 + 14, y + 22, CW - 28, 128, bg=PANEL, padding=0)
markers.append((y + 56, 42.195, "FINISH", "finish"))
y += 178
d.text([T("Source: World Athletics season top lists (every performance, top 500 a season), scraped October 2026. Elite means "
          "under 2:07 / 2:24 in the marathon and 60:00 / 67:00 in the half. 'New faces' counts a runner's first elite marathon "
          "since 2001, so the first few years include some who'd done it before. 2026 left out as it isn't finished. The course "
          "down the side is just for fun, it isn't a real route.", 9, MUTED)],
       X0, y, CW, 44, padding=0)

top = markers[0][0] - 40
bottom = markers[-1][0] + 60
d.image(g.route(IMG / "route.png", 110, int(bottom - top), [(my - top, km, lab, kind) for my, km, lab, kind in markers],
                TRACK, INK, BG, MUTED), 10, top, 110, int(bottom - top))

workbook([params, elite, depth, venues, nations, newfaces, kpis, text], sheets, [d], OUT)
print("written", OUT, "height used", y + 44, "of", H)
