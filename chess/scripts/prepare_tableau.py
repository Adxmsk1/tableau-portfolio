# csvs for the chess workbook. age = year - birth year (fide only gives the year) so ages can be off by one.
# 'new GM' = first january list with the title on it, so the title year is the year before
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
P, OUT = ROOT / "data" / "processed", ROOT / "data" / "tableau"
OUT.mkdir(parents=True, exist_ok=True)

FEDS = {"IND": "India", "USA": "USA", "RUS": "Russia", "CHN": "China", "UKR": "Ukraine", "GER": "Germany"}
LENSES = ["All nations"] + list(FEDS.values())


def person(n):
    # 'Carlsen, Magnus' -> 'Magnus Carlsen'
    n = str(n).replace("(GM)", "").strip()
    if "," in n:
        last, first = [x.strip() for x in n.split(",", 1)]
        return f"{first} {last}".strip()
    return n


L = pd.read_parquet(P / "lists.parquet")
L["age"] = L["year"] - L["birth_year"]
L["player"] = L["name"].map(person)
L["nation"] = L["fed"].map(FEDS).fillna("Other")

first_gm = L[L["title"] == "GM"].groupby("id").year.min()
first_gm = first_gm[first_gm > 2001]
g = L[L["year"] == L["id"].map(first_gm)].dropna(subset=["birth_year"]).copy()
g["title_year"] = g["year"] - 1
g["title_age"] = g["title_year"] - g["birth_year"]
rnd = random.Random(42)
g["x"] = g["title_year"] + [rnd.uniform(-0.36, 0.36) for _ in range(len(g))]      # spread each year's dots sideways
g["y"] = g["title_age"] + [rnd.uniform(-0.35, 0.35) for _ in range(len(g))]
g["kind"] = "Grandmaster"
g["lens"] = ""
g["era"] = pd.cut(g["title_year"], [2000, 2005, 2010, 2015, 2020, 2025], labels=["2001-05", "2006-10", "2011-15", "2016-20", "2021-25"])
# medians in 5 year blocks, for the world and each nation option
med = []
for lens in LENSES:
    sub = g if lens == "All nations" else g[g["nation"] == lens]
    for era, d in sub.groupby("era", observed=True):
        lo = int(str(era)[:4])
        med.append({"kind": "Median", "lens": lens, "era": str(era), "x": lo + 2, "y": d["title_age"].median(),
                    "title_age": d["title_age"].median(), "title_year": lo + 2, "player": f"Median, {era}", "n_era": len(d)})
cols = ["kind", "lens", "id", "player", "fed", "nation", "title_year", "title_age", "x", "y", "rating", "era"]
gms = pd.concat([g[cols], pd.DataFrame(med)], ignore_index=True)
gms.to_csv(OUT / "new_gms.csv", index=False)

records = pd.DataFrame([
    (1950.0, "David Bronstein", "USSR", 26, 0, 0), (1952.0, "Tigran Petrosian", "USSR", 23, 0, 0),
    (1955.0, "Boris Spassky", "USSR", 18, 0, 0), (1958.0, "Bobby Fischer", "USA", 15, 6, 1),
    (1991.0, "Judit Polgar", "Hungary", 15, 4, 28), (1994.0, "Peter Leko", "Hungary", 14, 4, 22),
    (1997.0, "Etienne Bacrot", "France", 14, 2, 0), (1997.9, "Ruslan Ponomariov", "Ukraine", 14, 0, 17),
    (1999.0, "Bu Xiangzhi", "China", 13, 10, 13), (2002.0, "Sergey Karjakin", "Ukraine", 12, 7, 0),
    (2021.0, "Abhimanyu Mishra", "USA", 12, 4, 25)],
    columns=["x", "player", "country", "years", "months", "days"])
records["age"] = records["years"] + records["months"] / 12 + records["days"] / 365.25
records["year"] = records["x"].astype(int)
records["age_label"] = [f"{y}y {m}m" if m or d else f"{y}" for y, m, d in zip(records.years, records.months, records.days)]
records["surname"] = records["player"].str.split().str[-1].replace("Xiangzhi", "Bu")
records["held_until"] = records["year"].shift(-1).fillna(2026).astype(int)
records["held_for"] = records["held_until"] - records["year"]
# only label some of them, the 90s ones overlap
key = records["surname"].isin(["Bronstein", "Fischer", "Polgar", "Karjakin", "Mishra"])
records["label_name"] = records["surname"].where(key, "")
records["label_age"] = records["age_label"].where(key, "")
# labels are centred on the bar, so pad fischer and karjakin with nbsp to push them clear of the bar before
nudge = records["surname"].isin(["Fischer", "Karjakin"])
for col in ["label_name", "label_age"]:
    records.loc[nudge, col] = [" " * (2 * len(s) + 3) + s for s in records.loc[nudge, col]]
records.to_csv(OUT / "records.csv", index=False)

act = L[~L["inactive"]].sort_values(["year", "rating"], ascending=[True, False])
top = act.groupby("year").head(100).copy()
bands = [(0, 20, "Under 20"), (20, 25, "20-24"), (25, 30, "25-29"), (30, 35, "30-34"), (35, 40, "35-39"), (40, 99, "40 and over")]
top["band"] = pd.cut(top["age"], [b[0] for b in bands] + [99], right=False, labels=[b[2] for b in bands])
top["band_order"] = top["band"].cat.codes
names = (top.sort_values("rating", ascending=False).groupby(["year", "band"], observed=True)
            .player.apply(lambda s: ", ".join(s.head(3))).rename("leading_players"))
h = top.groupby(["year", "band", "band_order"], observed=True).size().rename("players").reset_index()
full = pd.MultiIndex.from_product([range(2001, 2027), [b[2] for b in bands]], names=["year", "band"]).to_frame(index=False)
full["band_order"] = full["band"].map({b[2]: i for i, b in enumerate(bands)})
h = full.merge(h, how="left", on=["year", "band", "band_order"]).fillna({"players": 0})
h = h.merge(names.reset_index(), how="left", on=["year", "band"]).fillna({"leading_players": "-"})
h = h.merge(top.groupby("year").age.mean().rename("avg_age_top100").reset_index())
h = h.merge(act.groupby("year").head(10).groupby("year").age.mean().rename("avg_age_top10").reset_index())
h.to_csv(OUT / "top100.csv", index=False)

gl = L[(L["title"] == "GM")]
f = gl.groupby(["year", "nation"]).agg(gms=("id", "size"), median_age=("age", "median")).reset_index()
f = f[f["nation"] != "Other"]
f.to_csv(OUT / "feds.csv", index=False)

first27 = L[L["rating"] >= 2700].groupby("id").year.min()
first27 = first27[first27 > 2001]                      # anyone already 2700+ in January 2001 is left out
r = L[L["year"] == L["id"].map(first27)].dropna(subset=["birth_year"]).copy()
r = r.sort_values(["year", "age"], ascending=[True, False]).reset_index(drop=True)
r["row"] = range(len(r), 0, -1)                         # earliest at the top of the chart
r["first_year"] = r["year"]
r = r[["row", "player", "fed", "nation", "birth_year", "first_year", "age", "rating"]]
r.to_csv(OUT / "r2700.csv", index=False)
# two rows per player (born / first 2700) so tableau can draw a line between them
born = r.assign(point="Born", point_year=r["birth_year"])
arrived = r.assign(point="First 2700", point_year=r["first_year"])
pd.concat([born, arrived]).to_csv(OUT / "r2700_long.csv", index=False)

t10 = h.drop_duplicates("year").set_index("year")["avg_age_top10"]
kpis = pd.DataFrame([
    {"metric": "champion", "label": "18", "blurb": "Gukesh's age when he became the youngest undisputed world champion, December 2024"},
    {"metric": "youngest", "label": "12y 4m", "blurb": "Abhimanyu Mishra, the youngest grandmaster in history (2021)"},
    {"metric": "since2018", "label": "7 of 10", "blurb": "of the ten youngest grandmasters ever qualified in 2018 or later"},
    {"metric": "top10", "label": f"{t10.loc[2026]:.1f}", "blurb": f"average age of the world top 10, January 2026 - the youngest since at least 2001 "
                                                           f"(oldest: {t10.max():.1f} in {int(t10.idxmax())})"},
])
kpis.to_csv(OUT / "kpis.csv", index=False)
pd.DataFrame({"lens": LENSES}).to_csv(OUT / "lens.csv", index=False)

print("new GMs", len(g), "| medians", len(med), "| top100 cells", len(h), "| 2700 first-timers", len(r))
print("top10 avg age min/max:", round(t10.min(), 1), int(t10.idxmin()), round(t10.max(), 1), int(t10.idxmax()))
print(pd.DataFrame(med).pivot_table(index="lens", columns="era", values="y").to_string())
