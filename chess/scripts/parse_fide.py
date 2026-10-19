# parse the fide txt lists into one table: data/processed/lists.parquet (one row per player per january)
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "fide"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

OLD_TITLES = {"g": "GM", "m": "IM", "f": "FM", "c": "CM", "wg": "WGM", "wm": "WIM", "wf": "WFM", "wc": "WCM"}


def field_map(header):
    """Map each header label to a canonical field name and its [start, end) column slice."""
    tokens = [(m.start(), m.group()) for m in re.finditer(r"\S+(?: (?:number|NUMBER|Number))?", header)]
    out = {}
    for i, (start, tok) in enumerate(tokens):
        end = tokens[i + 1][0] if i + 1 < len(tokens) else None
        t = tok.lower()
        if t.startswith("id"):
            key = "id"
        elif t == "name":
            key = "name"
        elif t in ("title", "tit", "titl"):
            key = "title"
        elif t.startswith("titlfed"):      # 2010-12 run the two labels together: 'TitlFed'
            out["title"] = (start, start + 4)
            out["fed"] = (start + 4, end)
            continue
        elif t in ("country", "fed"):
            key = "fed"
        elif re.fullmatch(r"[a-z]{3}\d{2}", t):
            key = "rating"
        elif t in ("games", "gms"):
            key = "games"
        elif t.startswith("gamesborn"):     # 'GamesBorn' (2010-12)
            out["games"] = (start, start + 5)
            out["born"] = (start + 5, end)
            continue
        elif t in ("birthday", "born", "b-day"):
            key = "born"
        elif t == "flag":
            key = "flag"
        else:
            continue                          # Sex, WTit, OTit, FOA, K - not needed
        out[key] = (start, end)
    return out


# the old files (to 2012) are a mess - 2004 has no header, 2003 doesn't line up with its header,
# 2010-12 glue 'TitlFed' together - so for those just regex each row
OLD_ROW = re.compile(r"^\s*(?P<id>\d+)\s+(?P<name>.+?)\s+(?:(?P<title>wg|wm|wf|wc|g|m|f|c)\s+)?(?P<fed>[A-Z]{3})\s+"
                     r"(?P<rating>\d{3,4})\s+(?P<games>\d+)(?P<rest>.*)$")


def parse_old(lines):
    rows = []
    for ln in lines:
        m = OLD_ROW.match(ln)
        if not m:
            continue
        rest = m.group("rest").strip()
        born = re.match(r"(\d{2}\.\d{2}\.\d{2}|\d{4})", rest)
        flag = rest[born.end():].strip() if born else re.sub(r"^[\s.]+", "", rest)
        rows.append({"id": m.group("id"), "name": m.group("name").strip(), "title": m.group("title") or "",
                     "fed": m.group("fed"), "rating": m.group("rating"), "games": m.group("games"),
                     "born": born.group(1) if born else "", "flag": flag})
    return pd.DataFrame(rows)


def parse_new(lines):
    fm = field_map(lines[0])
    # numbers sometimes start a char or two left of their header
    rows = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        rows.append({k: ln[max(0, s - 2 if k in ("rating", "games", "born") else s):e].strip() if e else ln[s:].strip()
                     for k, (s, e) in fm.items()})
    return pd.DataFrame(rows)


def parse_year(year):
    folder = RAW / str(year)
    path = next(p for p in folder.iterdir() if p.suffix.lower() == ".txt")
    lines = path.read_text(encoding="latin-1").splitlines()
    df = parse_old(lines) if year <= 2012 else parse_new(lines)
    df["year"] = year
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"].str.extract(r"(\d{3,4})$")[0], errors="coerce")
    df["games"] = pd.to_numeric(df.get("games", pd.Series(dtype=str)).str.extract(r"(\d+)$")[0], errors="coerce")
    t = df.get("title", pd.Series("", index=df.index)).fillna("").str.strip()
    df["title"] = t.map(lambda x: OLD_TITLES.get(x, x.upper()))
    born = df.get("born", pd.Series("", index=df.index)).fillna("")
    yyyy = born.str.extract(r"(\d{4})$")[0]
    yy = born.str.extract(r"\d{2}\.\d{2}\.(\d{2})$")[0]           # 2005-09 style dd.mm.yy
    yy_full = yy.dropna().astype(int).map(lambda v: 2000 + v if v <= year % 100 else 1900 + v)
    df["birth_year"] = pd.to_numeric(yyyy, errors="coerce")
    df.loc[yy_full.index, "birth_year"] = yy_full
    df.loc[(df["birth_year"] < 1900) | (df["birth_year"] > year), "birth_year"] = pd.NA
    df["inactive"] = df.get("flag", pd.Series("", index=df.index)).fillna("").str.contains("i")
    return df[["year", "id", "name", "fed", "title", "rating", "games", "birth_year", "inactive"]].dropna(subset=["id", "rating"])


frames = []
for year in range(2001, 2027):
    d = parse_year(year)
    frames.append(d)
    gm = (d["title"] == "GM").sum()
    print(year, len(d), "GMs", gm, "birth coverage", round(d["birth_year"].notna().mean(), 3),
          "top rating", int(d["rating"].max()), d.loc[d["rating"].idxmax(), "name"])
lists = pd.concat(frames, ignore_index=True)
lists["id"] = lists["id"].astype("int64")
# 2001-04 have no birth years, borrow them from later lists via the FIDE id
by = lists.dropna(subset=["birth_year"]).groupby("id")["birth_year"].agg(lambda s: s.mode().iloc[0])
lists["birth_year"] = lists["birth_year"].fillna(lists["id"].map(by))
lists.to_parquet(OUT / "lists.parquet", index=False)
print("rows", len(lists))
print(lists.groupby("year").apply(lambda g: round(g.loc[g.rating >= 2500, "birth_year"].notna().mean(), 3)).to_string())
