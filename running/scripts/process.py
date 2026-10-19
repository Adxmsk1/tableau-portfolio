"""clean up the scraped top lists -> data/processed"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "html"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# "elite" cut-offs - quick enough to be world class but still gives a decent sample in the early years
ELITE = {("Marathon", "men"): 2 * 3600 + 7 * 60, ("Marathon", "women"): 2 * 3600 + 24 * 60,
         ("Half marathon", "men"): 60 * 60, ("Half marathon", "women"): 67 * 60}


def to_seconds(mark):
    parts = [float(p) for p in str(mark).replace("h", "").split(":")]
    s = 0.0
    for p in parts:
        s = s * 60 + p
    return s


def load():
    df = pd.read_csv(ROOT / "data" / "raw" / "season_toplists.csv")
    df["seconds"] = df["mark"].map(to_seconds)
    df["date"] = pd.to_datetime(df["date"], format="%d %b %Y", errors="coerce")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["venue_city"] = df["venue"].str.replace(r"\s*\(.*\)$", "", regex=True)
    df["venue_country"] = df["venue"].str.extract(r"\((\w+)\)$")
    return df.sort_values(["event", "sex", "season", "seconds"])


def era(season):
    if season <= 2016:
        return "Before super shoes (2001-16)"
    if season <= 2019:
        return "Arrival (2017-19)"
    return "Super-shoe era (2020-25)"


def main():
    df = load()
    df["elite"] = [s < ELITE[(e, x)] for s, e, x in zip(df["seconds"], df["event"], df["sex"])]
    df["era"] = df["season"].map(era)
    df.to_csv(OUT / "performances.csv", index=False)

    elite = df[df["elite"]]
    venue = elite.groupby(["event", "sex", "season", "venue_city"]).size().rename("elite_performances").reset_index()
    venue.to_csv(OUT / "venue_season.csv", index=False)
    nation = elite.groupby(["event", "sex", "season", "nat"]).size().rename("elite_performances").reset_index()
    nation.to_csv(OUT / "nation_season.csv", index=False)

    m = elite[elite["event"] == "Marathon"]
    for sex in ("men", "women"):
        g = m[m["sex"] == sex]
        print(f"\n== Marathon {sex}: elite performances by era\n", g.groupby("era").size() / g.groupby("era")["season"].nunique())
        print("top venues 2001-16:", g[g["season"] <= 2016]["venue_city"].value_counts().head(5).to_dict())
        print("top venues 2020-25:", g[g["season"] >= 2020]["venue_city"].value_counts().head(5).to_dict())
        print("nations 2001-16:", g[g["season"] <= 2016]["nat"].value_counts(normalize=True).head(4).round(2).to_dict())
        print("nations 2020-25:", g[g["season"] >= 2020]["nat"].value_counts(normalize=True).head(4).round(2).to_dict())

    depth = []
    for (event, sex, season), g in df.groupby(["event", "sex", "season"]):
        t = g["seconds"].sort_values().reset_index(drop=True)
        rec = {"event": event, "sex": sex, "season": season, "performances_listed": len(t)}
        for k in (1, 10, 50, 100, 500):
            rec[f"rank_{k}_s"] = t.iloc[k - 1] if len(t) >= k else None
        thr = ELITE[(event, sex)]
        rec["elite_threshold_s"] = thr
        rec["elite_performances"] = int((t < thr).sum())
        rec["elite_athletes"] = g.loc[g["seconds"] < thr, "competitor"].nunique()
        depth.append(rec)
    pd.DataFrame(depth).to_csv(OUT / "season_depth.csv", index=False)
    print(pd.DataFrame(depth).query("event == 'Marathon'")[["sex", "season", "rank_1_s", "rank_10_s", "rank_100_s", "elite_performances", "elite_athletes"]].to_string())


if __name__ == "__main__":
    main()
