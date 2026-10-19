# scratch work - which measures actually show chess getting younger?
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parent.parent / "data" / "processed"
L = pd.read_parquet(P / "lists.parquet")
L["age"] = L["year"] - L["birth_year"]

# top 100 (active only)
act = L[~L["inactive"]].sort_values(["year", "rating"], ascending=[True, False])
top = act.groupby("year").head(100)
t = top.groupby("year").agg(avg_age=("age", "mean"), med_age=("age", "median"), under20=("age", lambda a: (a < 20).sum()),
                            under25=("age", lambda a: (a < 25).sum()), over35=("age", lambda a: (a >= 35).sum()))
t10 = act.groupby("year").head(10).groupby("year").age.mean().rename("top10_age")
print(t.join(t10).round(1).to_string())
no1 = act.groupby("year").head(1)[["year", "name", "rating", "age"]]
print(no1.to_string(index=False))

# new GMs
gm = L[L["title"] == "GM"].groupby("id").year.min().rename("first_gm_list")
gm = gm[gm > 2001]
new = L[L["year"] == L["id"].map(gm)].copy()
new["title_year"] = new["year"] - 1
new["title_age"] = new["title_year"] - new["birth_year"]
g = new.groupby("title_year").agg(n=("id", "size"), med=("title_age", "median"), mean=("title_age", "mean"),
                                  u18=("title_age", lambda a: (a < 18).sum()), p10=("title_age", lambda a: a.quantile(.1)))
print(g.round(1).to_string())
print(new.sort_values("title_age").head(15)[["title_year", "name", "fed", "title_age"]].to_string(index=False))
print("new GMs by fed (top 12):", new.fed.value_counts().head(12).to_dict())

# first time over 2700
r27 = L[L["rating"] >= 2700].groupby("id").year.min().rename("first2700")
r27 = r27[r27 > 2001]
f27 = L[L["year"] == L["id"].map(r27)][["year", "name", "fed", "age"]].sort_values("year")
print(f27.to_string(index=False))

# GMs per federation
gmf = L[L["title"] == "GM"].groupby(["year", "fed"]).size().unstack(fill_value=0)
print(gmf[gmf.loc[2026].sort_values(ascending=False).index[:8]].loc[[2001, 2006, 2011, 2016, 2021, 2026]].to_string())
