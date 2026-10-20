# the small parsing functions that the scraped data depends on, tested on hand-made examples.
# each project has its own process.py, so they're loaded by path rather than imported by name

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def load(path):
    spec = importlib.util.spec_from_file_location(path.replace("/", "_").replace("-", "_"), ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


running = load("running/scripts/process.py")
ski = load("ski-jumping/scripts/process.py")


def test_marathon_and_half_marathon_times_to_seconds():
    assert running.to_seconds("2:01:09") == 7269
    assert running.to_seconds("59:30") == 3570


def test_running_eras_split_where_super_shoes_arrived():
    assert running.era(2016).startswith("Before")
    assert running.era(2017).startswith("Arrival")
    assert running.era(2020).startswith("Super-shoe")


def test_ski_jumping_race_header():
    city, country, hill, date = ski.parse_header("Sapporo (JPN) | Large Hill HS137 | January 18, 2025")
    assert (city, country, hill) == ("Sapporo", "JPN", "Large")
    assert date == pd.Timestamp("2025-01-18")


def test_ski_jumping_result_row_with_two_jumps():
    row = "ROW | 1 | 50 | 6288 | KOBAYASHI Ryoyu | 1996 | JPN | 2 | 1 | 135.5 | 140.2 | 1 | 2 | 130.0 | 132.0 | 2 | 272.2 | 0.0"
    result, jumps = ski.parse_row(row)
    assert result["name"] == "KOBAYASHI Ryoyu" and result["nation"] == "JPN" and result["birth_year"] == 1996
    assert result["total"] == 272.2
    assert jumps == [(1, 135.5, 140.2), (2, 130.0, 132.0)]


def test_ski_jumping_skips_rows_that_are_not_results():
    assert ski.parse_row("ROW | Rank | Bib | FIS Code | Name | Year | Nation") is None
