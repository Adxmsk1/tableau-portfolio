# grabs the January standard lists 2001-2026 from ratings.fide.com and unzips each into data/raw/fide/<year>
# skips years already downloaded
import zipfile
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "fide"
H = {"User-Agent": "Mozilla/5.0 (portfolio research)"}


def name(year):
    yy = f"{year % 100:02d}"
    return f"jan{yy}frl.zip" if year <= 2012 else f"standard_jan{yy}frl.zip"


for year in range(2001, 2027):
    folder = RAW / str(year)
    if folder.exists() and any(folder.iterdir()):
        continue
    folder.mkdir(parents=True, exist_ok=True)
    url = f"https://ratings.fide.com/download/{name(year)}"
    r = requests.get(url, headers=H, timeout=180)
    r.raise_for_status()
    zpath = folder / name(year)
    zpath.write_bytes(r.content)
    with zipfile.ZipFile(zpath) as z:
        for member in z.namelist():
            target = (folder / Path(member).name).resolve()
            if folder.resolve() not in target.parents:      # ignore odd paths inside the archive
                continue
            target.write_bytes(z.read(member))
    print(year, url, len(r.content), [p.name for p in folder.iterdir()])
