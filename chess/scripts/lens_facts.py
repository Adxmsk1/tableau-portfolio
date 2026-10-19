# numbers for each nation's commentary - text.py quotes these
from pathlib import Path

import pandas as pd

T = Path(__file__).resolve().parent.parent / "data" / "tableau"
g = pd.read_csv(T / "new_gms.csv")
g = g[g["kind"] == "Grandmaster"]
f = pd.read_csv(T / "feds.csv")
r = pd.read_csv(T / "r2700.csv")
for lens in ["All nations", "India", "USA", "Russia", "China", "Ukraine", "Germany"]:
    gg = g if lens == "All nations" else g[g["nation"] == lens]
    a, b = gg[gg.title_year <= 2012], gg[gg.title_year >= 2013]
    y = gg.sort_values(["title_age", "title_year"]).head(4)
    print(f"\n== {lens}: new GMs {len(gg)} (2001-12 {len(a)}, 2013-25 {len(b)}); median {a.title_age.median()} -> {b.title_age.median()}; "
          f"under-16s {int((gg.title_age < 16).sum())} (since 2013: {int((b.title_age < 16).sum())})")
    print("   youngest:", [(p, int(yr), int(ag)) for p, yr, ag in y[["player", "title_year", "title_age"]].values])
    if lens != "All nations":
        ff = f[f.nation == lens].set_index("year")
        print("   GMs on list 2001/2011/2021/2026:", [int(ff.gms.get(yy, 0)) for yy in (2001, 2011, 2021, 2026)],
              "peak", int(ff.gms.idxmax()), int(ff.gms.max()), "| median age 2001/2026:", ff.median_age.get(2001), ff.median_age.get(2026))
        rr = r[r.nation == lens]
    else:
        rr = r
        tot = f.groupby("year").gms.sum()
    print("   2700 first-timers:", len(rr), "| since 2018:", int((rr.first_year >= 2018).sum()),
          "| aged <=20 since 2018:", rr[(rr.first_year >= 2018) & (rr.age <= 20)][["player", "first_year", "age"]].values.tolist())
    print("   youngest 2700s:", rr.sort_values("age").head(4)[["player", "first_year", "age"]].values.tolist())
print("\nmedian age at first 2700 by period:", r.groupby(pd.cut(r.first_year, [2001, 2009, 2017, 2026])).age.median().to_dict())
