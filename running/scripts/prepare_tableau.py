# Builds the csvs the tableau workbook reads (data/tableau). Everything keeps a sex column
# so the Men/Women parameter can filter it.
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "data" / "processed"
OUT = ROOT / "data" / "tableau"
OUT.mkdir(parents=True, exist_ok=True)

SEX = {"men": "Men", "women": "Women"}


def era(season):
    return "Before super shoes" if season <= 2016 else ("Arrival (2017-19)" if season <= 2019 else "Super-shoe era")


def hms(s):
    s = int(round(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def ms(s):
    s = int(round(abs(s)))
    return f"{s // 60}:{s % 60:02d}"


depth = pd.read_csv(P / "season_depth.csv")
perf = pd.read_csv(P / "performances.csv")
venue = pd.read_csv(P / "venue_season.csv")
nation = pd.read_csv(P / "nation_season.csv")
for d in (depth, perf, venue, nation):
    d["sex"] = d["sex"].map(SEX)

e = depth[["event", "sex", "season", "elite_performances", "elite_athletes"]].copy()
e["era"] = e["season"].map(era)
e.to_csv(OUT / "elite_by_season.csv", index=False)

# depth = how fast the 10th and 100th best marathons were each year
m = depth[depth["event"] == "Marathon"]
rows = []
for _, r in m.iterrows():
    for k, lab in ((10, "10th fastest"), (100, "100th fastest")):
        rows.append({"sex": r["sex"], "season": r["season"], "depth": lab, "minutes": r[f"rank_{k}_s"] / 60,
                     "time_label": hms(r[f"rank_{k}_s"])})
dl = pd.DataFrame(rows)
# minutes quicker than the same rank in 2001
base = dl[dl["season"] == 2001].set_index(["sex", "depth"])["minutes"]
dl["faster_than_2001"] = [base[(s, d)] - m for s, d, m in zip(dl["sex"], dl["depth"], dl["minutes"])]
dl.to_csv(OUT / "depth_long.csv", index=False)

# top 8 marathon venues for each sex
vm = venue[venue["event"] == "Marathon"].copy()
vm["venue_city"] = vm["venue_city"].str.replace(", IL", "", regex=False)
top = (vm.groupby(["sex", "venue_city"])["elite_performances"].sum().reset_index()
         .sort_values("elite_performances", ascending=False).groupby("sex").head(8))
vt = vm.merge(top[["sex", "venue_city"]], on=["sex", "venue_city"])
full = (pd.MultiIndex.from_product([vt["sex"].unique(), range(2001, 2026)], names=["sex", "season"]).to_frame(index=False)
          .merge(top[["sex", "venue_city"]], on="sex"))
vt = full.merge(vt, on=["sex", "season", "venue_city"], how="left").fillna({"elite_performances": 0})
vt.rename(columns={"venue_city": "venue"}).to_csv(OUT / "venues.csv", index=False)

nm = nation[nation["event"] == "Marathon"].copy()
nm["nation_group"] = nm["nat"].map({"KEN": "Kenya", "ETH": "Ethiopia", "JPN": "Japan"}).fillna("Rest of world")
ng = nm.groupby(["sex", "season", "nation_group"])["elite_performances"].sum().reset_index()
ng["share"] = ng["elite_performances"] / ng.groupby(["sex", "season"])["elite_performances"].transform("sum")
ng.to_csv(OUT / "nations.csv", index=False)
# by era rather than by season - early seasons only have a handful of elite runs
ERA_LABEL = {"Before super shoes": "2001-16  before", "Arrival (2017-19)": "2017-19  arrival", "Super-shoe era": "2020-25  super shoes"}
nm["era_label"] = nm["season"].map(era).map(ERA_LABEL)
ne = nm.groupby(["sex", "era_label", "nation_group"])["elite_performances"].sum().reset_index()
ne["share"] = ne["elite_performances"] / ne.groupby(["sex", "era_label"])["elite_performances"].transform("sum")
ne.to_csv(OUT / "nations_era.csv", index=False)
print(ne.pivot_table(index=["sex", "era_label"], columns="nation_group", values="share").round(2))


def person(n):
    # KIPTUM -> Kiptum
    return " ".join(w.title() if w.isupper() and len(w) > 1 else w for w in str(n).split())


perf["runner"] = perf["competitor"].map(person)
perf["venue_city"] = perf["venue_city"].str.replace(", IL", "", regex=False)
perf["time"] = perf["seconds"].map(hms)
best = perf.loc[perf.groupby(["event", "sex", "season"])["seconds"].idxmin(), ["event", "sex", "season", "runner", "time", "venue_city"]]
e = e.merge(best.rename(columns={"runner": "fastest_runner", "time": "fastest_time", "venue_city": "fastest_venue"}),
            on=["event", "sex", "season"], how="left")
# index against the 2001-16 average so marathon and half can go on one chart
pre_avg = e[e["season"] <= 2016].groupby(["event", "sex"])["elite_performances"].mean().rename("pre_avg")
e = e.merge(pre_avg.reset_index(), on=["event", "sex"])
e["vs_pre"] = e["elite_performances"] / e["pre_avg"]
e.to_csv(OUT / "elite_by_season.csv", index=False)

dl["gain_label"] = [f"{int(abs(m))} min {round(abs(m) % 1 * 60):02d} s" for m in dl["faster_than_2001"]]
dl.to_csv(OUT / "depth_long.csv", index=False)

pm = perf[(perf["event"] == "Marathon") & perf["elite"]]
vbest = pm.loc[pm.groupby(["sex", "season", "venue_city"])["seconds"].idxmin(), ["sex", "season", "venue_city", "runner", "time"]]
vt = vt.rename(columns={"venue_city": "venue"}).merge(vbest.rename(columns={"venue_city": "venue","runner": "fastest_runner", "time": "fastest_time"}),
              on=["sex", "season", "venue"], how="left")
season_total = pm.groupby(["sex", "season"]).size().rename("season_total").reset_index()
vt = vt.merge(season_total, on=["sex", "season"], how="left")
vt["share_of_season"] = (vt["elite_performances"] / vt["season_total"]).fillna(0)
vt.to_csv(OUT / "venues.csv", index=False)

pm = pm.assign(nation_group=pm["nat"].map({"KEN": "Kenya", "ETH": "Ethiopia", "JPN": "Japan"}).fillna("Rest of world"),
               era_label=pm["season"].map(era).map(ERA_LABEL))
lead = (pm.groupby(["sex", "era_label", "nation_group", "runner"]).size().rename("runs").reset_index()
          .sort_values("runs", ascending=False).drop_duplicates(["sex", "era_label", "nation_group"]))
ne = ne.merge(lead.rename(columns={"runner": "busiest_runner", "runs": "busiest_runs"}), on=["sex", "era_label", "nation_group"], how="left")
ne["runners"] = ne.merge(pm.groupby(["sex", "era_label", "nation_group"]).runner.nunique().rename("n").reset_index(),
                         on=["sex", "era_label", "nation_group"], how="left")["n"]
ne.to_csv(OUT / "nations_era.csv", index=False)

# first ever elite marathon for each runner (well, first since 2001)
debut = pm.sort_values("date").drop_duplicates(["sex", "competitor", "dob"])
nf = debut.groupby(["sex", "season"]).size().rename("newcomers").reset_index()
nf = (pd.MultiIndex.from_product([["Men", "Women"], range(2001, 2026)], names=["sex", "season"]).to_frame(index=False)
        .merge(nf, how="left").fillna({"newcomers": 0}))
fast_debut = debut.loc[debut.groupby(["sex", "season"])["seconds"].idxmin(), ["sex", "season", "runner", "time", "venue_city"]]
nf = nf.merge(fast_debut.rename(columns={"runner": "best_newcomer", "time": "newcomer_time", "venue_city": "newcomer_venue"}),
              on=["sex", "season"], how="left")
nf["era"] = nf["season"].map(era)
nf.to_csv(OUT / "newfaces.csv", index=False)
print(nf.groupby(["sex", "era"]).newcomers.mean().round(1))

# kpi cards
k = []
for sex in ("Men", "Women"):
    d = depth[(depth["event"] == "Marathon") & (depth["sex"] == sex)].set_index("season")
    pre = d.loc[2001:2016, "elite_performances"].mean()
    post = d.loc[2020:2025, "elite_performances"].mean()
    k.append({"sex": sex, "metric": "multiple", "value": post / pre, "label": f"{post / pre:.0f}x"})
    gain = d.loc[2015, "rank_100_s"] - d.loc[2025, "rank_100_s"]
    k.append({"sex": sex, "metric": "depth_gain", "value": gain, "label": ms(gain)})
    t25 = d.loc[2025, "rank_100_s"]
    p15 = perf[(perf["event"] == "Marathon") & (perf["sex"] == sex) & (perf["season"] == 2015)]["seconds"]
    rank_then = int((p15 < t25).sum()) + 1
    k.append({"sex": sex, "metric": "rank_then", "value": rank_then, "label": f"{rank_then}{'th' if 10 < rank_then % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(rank_then % 10, 'th')}"})
    k.append({"sex": sex, "metric": "time_100_2025", "value": t25, "label": hms(t25)})
    a16, a25 = d.loc[2016, "elite_athletes"], d.loc[2025, "elite_athletes"]
    k.append({"sex": sex, "metric": "athletes", "value": a25 / a16, "label": f"{a16} to {a25}"})
    vv = vm[(vm["sex"] == sex) & (vm["season"] >= 2020)].groupby("venue_city")["elite_performances"].sum().sort_values(ascending=False)
    k.append({"sex": sex, "metric": "top_venue", "value": vv.iloc[0], "label": f"{vv.index[0]}"})
kp = pd.DataFrame(k)
thr = {"Men": "2:07", "Women": "2:24"}
val_pre = {s: int(vm[(vm["sex"] == s) & (vm["season"] <= 2018) & (vm["venue_city"] == "Valencia")]["elite_performances"].sum()) for s in SEX.values()}
desc = {
    "multiple": lambda s: f"as many sub-{thr[s]} marathons a year in 2020-25 as in 2001-16",
    "rank_then": lambda s: f"where 2025's 100th-fastest time ({kp[(kp.sex == s) & (kp.metric == 'time_100_2025')].label.iloc[0]}) would have ranked in 2015",
    "athletes": lambda s: f"different athletes under {thr[s]}: 2016 vs 2025",
    "top_venue": lambda s: f"No. 1 for elite marathons since 2020: {int(kp[(kp.sex == s) & (kp.metric == 'top_venue')].value.iloc[0])}, up from {val_pre[s]} before 2019",
}
kp["blurb"] = [desc[m](s) if m in desc else "" for m, s in zip(kp["metric"], kp["sex"])]
kp.to_csv(OUT / "kpis.csv", index=False)
print("Valencia elite performances before 2019:", val_pre)
print(kp.to_string())
h = depth[depth["event"] == "Half marathon"].groupby("sex").apply(
    lambda g: (g.loc[g.season >= 2020, "elite_performances"].mean() / g.loc[g.season <= 2016, "elite_performances"].mean()))
print("half marathon multiple:", h.round(1).to_dict())
