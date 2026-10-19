# parse the raw FIS rows into races / results / jumps
#
# rows come in a few shapes, e.g.
#   rank | code | name | birth | nation | total | diff
#   rank | bib | code | name | birth | nation | runs | 1 | dist | pts | rk | 2 | dist | pts | rk | total | diff
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

NUM = re.compile(r"^-?\d+(\.\d+)?$")


def parse_header(h):
    parts = [p.strip() for p in str(h).split("|")]
    venue = parts[0] if parts else ""
    m = re.match(r"(.+?)\s*\((\w{3})\)", venue)
    city, country = (m.group(1), m.group(2)) if m else (venue, "")
    hill = next((p for p in parts if "Hill" in p), "")
    hill_type = "Flying" if "Flying" in hill else "Large" if "Large" in hill else "Normal" if "Normal" in hill else "Other"
    date = next((p for p in parts if re.match(r"[A-Z][a-z]+ \d{1,2}, \d{4}$", p)), None)
    return city, country, hill_type, pd.to_datetime(date, format="%B %d, %Y", errors="coerce")


def parse_row(cells):
    c = [x.strip() for x in cells.split(" | ")][1:]  # first cell is the whole row again
    if len(c) < 6 or not c[0].isdigit():
        return None
    rank = int(c[0])
    # find birth year then nation code, everything else hangs off that
    i = next((k for k in range(1, len(c) - 1) if re.fullmatch(r"(19|20)\d\d", c[k]) and re.fullmatch(r"[A-Z]{3}", c[k + 1])), None)
    if i is None:
        return None
    name, birth, nation = c[i - 1], int(c[i]), c[i + 1]
    code = c[i - 2] if i >= 2 else None
    rest = c[i + 2:]
    nums = [x for x in rest if NUM.match(x)]
    total = float(nums[-2]) if len(nums) >= 2 else (float(nums[-1]) if nums else None)
    jumps = []
    # round, distance, points, rank
    detail = rest[1:-2] if len(rest) > 3 else []
    k = 0
    while k + 3 < len(detail) + 1 and k + 2 < len(detail):
        if detail[k] in ("1", "2") and NUM.match(detail[k + 1]) and NUM.match(detail[k + 2]):
            dist = float(detail[k + 1])
            if 40 <= dist <= 260:
                jumps.append((int(detail[k]), dist, float(detail[k + 2])))
            k += 4
        else:
            k += 1
    return {"rank": rank, "code": code, "name": name, "birth_year": birth, "nation": nation, "total": total}, jumps


def main():
    races = pd.read_csv(RAW / "races.csv").drop_duplicates("raceid")
    # some events show up in both the men's and women's calendars, so go by the race title
    races["gender"] = races["header"].map(lambda h: "W" if "Women's" in str(h) else ("M" if "Men's" in str(h) else None))
    races = races[races["gender"].notna()]
    hdr = races["header"].map(parse_header)
    races["city"], races["country"], races["hill_type"], races["date"] = zip(*hdr)
    races["season_label"] = races["season"].map(lambda s: f"{s - 1}/{str(s)[2:]}")
    races.drop(columns=["header", "label"]).to_csv(OUT / "races.csv", index=False)

    raw = pd.read_csv(RAW / "results_raw.csv").drop_duplicates()
    res, jmp = [], []
    for rid, cells in zip(raw["raceid"], raw["cells"]):
        p = parse_row(cells)
        if not p:
            continue
        r, jumps = p
        r["raceid"] = rid
        res.append(r)
        for rnd, dist, pts in jumps:
            jmp.append({"raceid": rid, "code": r["code"], "name": r["name"], "nation": r["nation"], "round": rnd,
                        "distance": dist, "points": pts})
    res = pd.DataFrame(res).merge(races[["raceid", "gender", "season", "city", "country", "hill_type", "date"]], on="raceid")
    res["age"] = res["date"].dt.year - res["birth_year"]
    jmp = pd.DataFrame(jmp).merge(races[["raceid", "gender", "season", "city", "hill_type", "date"]], on="raceid")
    res.to_csv(OUT / "results.csv", index=False)
    jmp.to_csv(OUT / "jumps.csv", index=False)
    print("races", len(races), "results", len(res), "jumps", len(jmp))
    print("races with jump detail by season:")
    cov = jmp.groupby(["gender", "season"])["raceid"].nunique().unstack(0)
    allr = races.groupby(["gender", "season"]).size().unstack(0)
    print(pd.concat([cov.add_suffix("_detail"), allr.add_suffix("_all")], axis=1).fillna(0).astype(int).to_string())


if __name__ == "__main__":
    main()
