# FIS world cup individual results, men 2001-25 and women 2012-25.
# calendar -> events -> race pages, all cached in data/raw/html.
# keeps the raw cell text so process.py can be changed without scraping again
import re
import time
from pathlib import Path

import bs4
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "html"
CACHE.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (portfolio research; polite scraper)"}
CAL = ("https://www.fis-ski.com/DB/ski-jumping/calendar-results.html"
       "?eventselection=results&seasoncode={season}&categorycode=WC&gendercode={g}")
EVENT = "https://www.fis-ski.com/DB/general/event-details.html?sectorcode=JP&eventid={eid}"
RACE = "https://www.fis-ski.com/DB/general/results.html?sectorcode=JP&raceid={rid}"


def get(url, name):
    f = CACHE / name
    if f.exists():
        return f.read_text(encoding="utf-8")
    for attempt in range(3):
        try:
            r = requests.get(url, headers=H, timeout=40)
            r.raise_for_status()
            f.write_text(r.text, encoding="utf-8")
            time.sleep(0.35)
            return r.text
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
    return ""


def races_in_event(eid):
    s = bs4.BeautifulSoup(get(EVENT.format(eid=eid), f"event_{eid}.html"), "html.parser")
    texts = {}
    for a in s.select('a[href*="raceid="]'):
        rid = re.search(r"raceid=(\d+)", a["href"]).group(1)
        texts.setdefault(rid, []).append(a.get_text(" ", strip=True))
    return {rid: " | ".join(t for t in ts if t) for rid, ts in texts.items()}


def parse_race(rid):
    s = bs4.BeautifulSoup(get(RACE.format(rid=rid), f"race_{rid}.html"), "html.parser")
    hdr = s.select_one(".event-header")
    header = hdr.get_text(" | ", strip=True) if hdr else ""
    rows = []
    for a in s.select("#events-info-results a.table-row"):
        cells = [d.get_text(" ", strip=True) for d in a.select(".g-row > div")]
        rows.append({"raceid": rid, "cells": " | ".join(cells)})
    return header, rows


def main():
    races, results = [], []
    for g, seasons in (("M", range(2001, 2026)), ("W", range(2012, 2026))):
        for season in seasons:
            cal = get(CAL.format(season=season, g=g), f"cal_{g}_{season}.html")
            for eid in dict.fromkeys(re.findall(r"eventid=(\d+)", cal)):
                for rid, label in races_in_event(eid).items():
                    # 4th field is the race type; checking the whole label threw out races from the 2010 'Team Tour'
                    kind = label.split(" | ")[3] if label.count(" | ") >= 3 else ""
                    keep = ("| WC |" in label and kind.startswith("Individual")
                            and not any(x in kind for x in ("Qualification", "Training", "Trial")))
                    if not keep:
                        continue
                    header, rows = parse_race(rid)
                    races.append({"raceid": rid, "eventid": eid, "gender": g, "season": season,
                                  "label": label, "header": header, "n": len(rows)})
                    results += rows
            print(f"{g} {season}: {len(races)} races, {len(results)} result rows", flush=True)
    pd.DataFrame(races).drop_duplicates("raceid").to_csv(ROOT / "data" / "raw" / "races.csv", index=False)
    pd.DataFrame(results).to_csv(ROOT / "data" / "raw" / "results_raw.csv", index=False)
    print("saved")


if __name__ == "__main__":
    main()
