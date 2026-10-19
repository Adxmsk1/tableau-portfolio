# tables for the ski jumping workbook. 'competition' (Men/Women) is what the parameter filters on
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
P, OUT = ROOT / "data" / "processed", ROOT / "data" / "tableau"
OUT.mkdir(parents=True, exist_ok=True)
COMP = {"M": "Men", "W": "Women"}
NAMES = {"AUT": "Austria", "NOR": "Norway", "GER": "Germany", "POL": "Poland", "SLO": "Slovenia", "JPN": "Japan",
         "FIN": "Finland", "SUI": "Switzerland", "USA": "USA", "FRA": "France", "CAN": "Canada", "RUS": "Russia", "ITA": "Italy"}

r = pd.read_csv(P / "results.csv", parse_dates=["date"])
j = pd.read_csv(P / "jumps.csv")
r["competition"] = r["gender"].map(COMP)
j["competition"] = j["gender"].map(COMP)


def pretty(name):
    # FIS gives "SCHLIERENZAUER Gregor"
    parts = name.split()
    surname = [p for p in parts if p.isupper()]
    first = [p for p in parts if not p.isupper()]
    return " ".join(first + [s.title() for s in surname])


# keep the 7 biggest nations, lump the rest together
pod = r[r["rank"] <= 3]
top = {c: pod[pod.competition == c].nation.value_counts().head(7).index.tolist() for c in COMP.values()}
r["nation_group"] = [NAMES.get(n, n) if n in top[c] else "Other nations" for n, c in zip(r.nation, r.competition)]
pod = r[r["rank"] <= 3]

p = pod.groupby(["competition", "season", "nation_group"]).size().rename("podiums").reset_index()
full = (pod[["competition", "season"]].drop_duplicates().merge(p[["competition", "nation_group"]].drop_duplicates(), on="competition"))
p = full.merge(p, how="left").fillna({"podiums": 0})
p["share"] = p["podiums"] / p.groupby(["competition", "season"])["podiums"].transform("sum")
p.to_csv(OUT / "podiums.csv", index=False)

n = r[r["rank"] <= 30].groupby(["competition", "season"]).nation.nunique().rename("nations_top30").reset_index()
n.to_csv(OUT / "nations.csv", index=False)

w = r[r["rank"] == 1].groupby(["competition", "name", "nation_group"]).size().rename("wins").reset_index()
w["athlete"] = w["name"].map(pretty)
w = w.sort_values("wins", ascending=False).groupby("competition").head(10)
w["rank"] = w.groupby("competition")["wins"].rank(method="first", ascending=False).astype(int)
w.drop(columns="name").to_csv(OUT / "winners.csv", index=False)

f = j.loc[j.groupby(["competition", "season"]).distance.idxmax(), ["competition", "season", "distance", "name", "city"]]
f["athlete"] = f["name"].map(pretty)
f.drop(columns="name").rename(columns={"distance": "longest"}).to_csv(OUT / "flights.csv", index=False)

k = []
for c in COMP.values():
    pc = p[p.competition == c]
    by = pc.groupby("nation_group").podiums.sum().drop("Other nations", errors="ignore").sort_values(ascending=False)
    k.append({"competition": c, "metric": "top_nation", "label": f"{by.index[0]}",
              "blurb": f"more podium places than any other nation since {pc.season.min()} ({by.iloc[0] / pc.podiums.sum():.0%})"})
    # use real nations here, not the lumped 'Other'
    raw = r[(r["rank"] <= 3) & (r.competition == c)].groupby(["season", "nation"]).size().reset_index(name="n")
    leaders = raw.loc[raw.groupby("season").n.idxmax(), "nation"].nunique()
    k.append({"competition": c, "metric": "leaders", "label": f"{leaders}",
              "blurb": "different nations have finished a season on top of the podium table"})
    fc = f[f.competition == c].sort_values("distance").iloc[-1]
    k.append({"competition": c, "metric": "longest", "label": f"{fc.distance:g} m",
              "blurb": f"the longest jump: {fc.athlete}, {fc.city} {fc.season}"})
    wc = w[w.competition == c].iloc[0]
    k.append({"competition": c, "metric": "top_athlete", "label": f"{int(wc.wins)} wins",
              "blurb": f"{wc.athlete} ({wc.nation_group}), more than anyone since {pc.season.min()}"})
pd.DataFrame(k).to_csv(OUT / "kpis.csv", index=False)

r["athlete"] = r["name"].map(pretty)
season_label = lambda s: f"{s - 1}/{str(s)[2:]}"

# who got most of each nation's podiums that season (tooltip)
lead = (r[r["rank"] <= 3].groupby(["competition", "season", "nation_group", "athlete"]).size().rename("lead_podiums").reset_index()
          .sort_values("lead_podiums", ascending=False).drop_duplicates(["competition", "season", "nation_group"]))
p = p.merge(lead.rename(columns={"athlete": "lead_athlete"}), on=["competition", "season", "nation_group"], how="left")
p["season_label"] = p["season"].map(season_label)
p["seasons_total"] = p.groupby(["competition", "season"])["podiums"].transform("sum")
p.to_csv(OUT / "podiums.csv", index=False)

# best jumper each season + how many different winners
wins = r[r["rank"] == 1]
events = r.drop_duplicates("raceid").groupby(["competition", "season"]).size().rename("events")
tw = wins.groupby(["competition", "season", "athlete", "nation_group"]).size().rename("wins").reset_index()
dom = tw.sort_values("wins", ascending=False).drop_duplicates(["competition", "season"]).merge(events.reset_index())
dom["share"] = dom["wins"] / dom["events"]
dom = dom.merge(wins.groupby(["competition", "season"]).athlete.nunique().rename("different_winners").reset_index())
dom["surname"] = dom["athlete"].str.split().str[-1]
dom["season_label"] = dom["season"].map(season_label)
dom.sort_values(["competition", "season"]).to_csv(OUT / "dominance.csv", index=False)
print(dom[["competition", "season", "athlete", "wins", "events", "share", "different_winners"]].to_string())

car = r.groupby(["competition", "athlete"]).agg(podiums=("rank", lambda x: int((x <= 3).sum())), starts=("rank", "size"))
span = wins.groupby(["competition", "athlete"]).season.agg(first_win="min", last_win="max")
wtab = pd.read_csv(OUT / "winners.csv").merge(car.reset_index(), how="left").merge(span.reset_index(), how="left")
wtab["first_win"] = wtab["first_win"].map(season_label)
wtab["last_win"] = wtab["last_win"].map(season_label)
wtab.to_csv(OUT / "winners.csv", index=False)

# podium ages. only have birth year so these can be 1 out
pod_r = r[r["rank"] <= 3]
ages = pod_r.groupby(["competition", "season"]).age.mean().rename("avg_age").reset_index()
yng = pod_r.loc[pod_r.groupby(["competition", "season"]).age.idxmin(), ["competition", "season", "athlete", "age"]]
old = pod_r.loc[pod_r.groupby(["competition", "season"]).age.idxmax(), ["competition", "season", "athlete", "age"]]
ages = (ages.merge(yng.rename(columns={"athlete": "youngest", "age": "youngest_age"}))
            .merge(old.rename(columns={"athlete": "oldest", "age": "oldest_age"})))
ages["season_label"] = ages["season"].map(season_label)
ages.to_csv(OUT / "ages.csv", index=False)
print(ages.to_string())

# home vs away. 150 home starts minimum, below that it's mostly noise
r["where"] = (r["nation"] == r["country"]).map({True: "At home", False: "Abroad"})
h = r.groupby(["competition", "nation", "where"]).agg(starts=("rank", "size"), podiums=("rank", lambda x: int((x <= 3).sum()))).reset_index()
home_starts = h[h["where"] == "At home"].set_index(["competition", "nation"])["starts"]
keep = home_starts[home_starts >= 150].index
h = h[h.set_index(["competition", "nation"]).index.isin(keep)].copy()
h["podium_rate"] = h["podiums"] / h["starts"]
h["nation_name"] = h["nation"].map(lambda n: NAMES.get(n, n))
hosts = (r[r["where"] == "At home"].drop_duplicates("raceid").groupby(["competition", "nation"]).city
           .agg(lambda c: ", ".join(c.value_counts().index[:2])).rename("home_hills").reset_index())
h = h.merge(hosts, how="left")
ratio = h.pivot_table(index=["competition", "nation"], columns="where", values="podium_rate")
h = h.merge((ratio["At home"] / ratio["Abroad"]).rename("home_lift").reset_index())
h.to_csv(OUT / "home.csv", index=False)
print(h.to_string())

f2 = pd.read_csv(OUT / "flights.csv")
f2["season_label"] = f2["season"].map(season_label)
f2.to_csv(OUT / "flights.csv", index=False)
print(pd.DataFrame(k).to_string())
print(f.to_string())
aut = p[(p.competition == "Men") & (p.nation_group == "Austria")].set_index("season").share.round(2)
print("Austria men podium share:", aut.to_dict())
