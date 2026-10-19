# do some countries make their GMs younger than others?
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parent.parent / "data" / "processed"
L = pd.read_parquet(P / "lists.parquet")
L["age"] = L["year"] - L["birth_year"]
gm = L[L["title"] == "GM"].groupby("id").year.min()
gm = gm[gm > 2001]
new = L[L["year"] == L["id"].map(gm)].copy()
new["title_year"] = new["year"] - 1
new["title_age"] = new["title_year"] - new["birth_year"]
new["era"] = pd.cut(new["title_year"], [2000, 2012, 2025], labels=["2001-12", "2013-25"])
feds = new.fed.value_counts().head(14).index
s = new[new.fed.isin(feds)].groupby(["fed", "era"], observed=True).title_age.agg(["median", "count"]).unstack()
s["gm2001"] = L[(L.year == 2001) & (L.title == "GM")].fed.value_counts()
s["gm2026"] = L[(L.year == 2026) & (L.title == "GM")].fed.value_counts()
print(s.sort_values(("count", "2013-25"), ascending=False).to_string())
print("world", new.groupby("era", observed=True).title_age.median().to_dict())
for f in ("IND", "USA", "RUS", "CHN", "UZB", "UKR", "GER", "IRI"):
    d = new[new.fed == f].sort_values("title_age").head(3)
    print(f, d[["name", "title_year", "title_age"]].values.tolist())
# under 20s rated 2500+
a = L[(L.year == 2026) & (~L.inactive) & (L.rating >= 2500) & (L.age < 20)]
print("2500+ under-20 2026 by fed:", a.fed.value_counts().head(10).to_dict(), "total", len(a))
b = L[(L.year == 2011) & (~L.inactive) & (L.rating >= 2500) & (L.age < 20)]
print("2500+ under-20 2011 by fed:", b.fed.value_counts().head(10).to_dict(), "total", len(b))
