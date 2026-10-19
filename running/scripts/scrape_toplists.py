"""World Athletics season top lists, marathon + half, 2001-2025 (all performances not just PBs).
Pages get cached in data/raw/html so it can be re-run without hammering the site."""
import time
from pathlib import Path

import bs4
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "html"
CACHE.mkdir(parents=True, exist_ok=True)

EVENTS = {"marathon": "Marathon", "half-marathon": "Half marathon"}
SEXES = ["men", "women"]
YEARS = range(2001, 2026)
PAGES = 5  # 100 per page, so top 500
URL = ("https://worldathletics.org/records/toplists/road-running/{event}/all/{sex}/senior/{year}"
       "?regionType=world&page={page}&bestResultsOnly=false&timing=electronic")
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio research; polite scraper)"}


def fetch(event, sex, year, page):
    f = CACHE / f"{event}_{sex}_{year}_p{page}.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    r = requests.get(URL.format(event=event, sex=sex, year=year, page=page), headers=HEADERS, timeout=40)
    r.raise_for_status()
    f.write_text(r.text, encoding="utf-8")
    time.sleep(0.4)
    return r.text


def parse(html):
    t = bs4.BeautifulSoup(html, "html.parser").find("table")
    rows = []
    if t is None:
        return rows
    for tr in t.find_all("tr")[1:]:
        c = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(c) >= 10:
            rows.append({"rank": c[0], "mark": c[1], "competitor": c[3], "dob": c[4], "nat": c[5],
                         "pos": c[6], "venue": c[8], "date": c[9], "score": c[10] if len(c) > 10 else None})
    return rows


def main():
    out = []
    for event, label in EVENTS.items():
        for sex in SEXES:
            for year in YEARS:
                for page in range(1, PAGES + 1):
                    rows = parse(fetch(event, sex, year, page))
                    for r in rows:
                        r.update(event=label, sex=sex, season=year)
                    out += rows
                    if len(rows) < 100:
                        break
            print(f"{label} {sex}: done ({len(out)} rows so far)", flush=True)
    df = pd.DataFrame(out)
    df.to_csv(ROOT / "data" / "raw" / "season_toplists.csv", index=False)
    print("saved", len(df))


if __name__ == "__main__":
    main()
