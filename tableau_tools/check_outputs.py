"""Checks the CSVs in each project's data/tableau folder before they go into a workbook.

    python tableau_tools/check_outputs.py

Prints pass/FAIL for each rule and exits with 1 if anything fails.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# files each dashboard reads
EXPECTED = {
    "chess": ["feds", "kpis", "lens", "new_gms", "r2700", "r2700_long", "records", "text", "top100"],
    "running": ["depth_long", "elite_by_season", "kpis", "nations", "nations_era", "newfaces", "text", "venues"],
    "ski-jumping": ["ages", "dominance", "flights", "home", "kpis", "nations", "podiums", "text", "winners"],
}

# every year/season that should be there, per group
COVERAGE = [
    ("chess", "top100", ["band"], "year", range(2001, 2027)),
    ("chess", "feds", ["nation"], "year", range(2001, 2027)),
    ("running", "elite_by_season", ["event", "sex"], "season", range(2001, 2026)),
    ("ski-jumping", "dominance", ["competition"], "season", None),  # women's world cup starts later, so just no gaps
]

# columns that are proportions, so must sit between 0 and 1
PROPORTIONS = ["share", "share_of_season", "podium_rate"]


def load(project, name):
    return pd.read_csv(ROOT / project / "data" / "tableau" / f"{name}.csv")


def check_files():
    problems = []
    for project, names in EXPECTED.items():
        for name in names:
            path = ROOT / project / "data" / "tableau" / f"{name}.csv"
            if not path.exists():
                problems.append(f"{project}/{name}.csv is missing")
                continue
            df = pd.read_csv(path)
            if df.empty:
                problems.append(f"{project}/{name}.csv has no rows")
            if df.duplicated().any():
                problems.append(f"{project}/{name}.csv has {df.duplicated().sum()} duplicate rows")
    return problems


def check_coverage():
    problems = []
    for project, name, group_cols, col, expected in COVERAGE:
        for key, g in load(project, name).groupby(group_cols):
            got = sorted(g[col].unique())
            want = list(expected) if expected else list(range(got[0], got[-1] + 1))
            missing = sorted(set(want) - set(got))
            if missing:
                problems.append(f"{project}/{name} {key}: missing {col} {missing}")
    return problems


def check_proportions():
    problems = []
    for project, names in EXPECTED.items():
        for name in names:
            df = load(project, name)
            for col in PROPORTIONS:
                if col in df and not df[col].dropna().between(0, 1).all():
                    problems.append(f"{project}/{name}.{col} has values outside 0-1")
    return problems


def check_text():
    # the commentary is switched by a parameter in tableau, so a blank title shows up as an empty heading
    problems = []
    for project in EXPECTED:
        df = load(project, "text")
        if df["title"].isna().any():
            problems.append(f"{project}/text.csv has rows with no title")
    return problems


def main():
    failed = 0
    for check in (check_files, check_coverage, check_proportions, check_text):
        problems = check()
        print(f"  {'pass' if not problems else 'FAIL'}  {check.__name__}")
        for p in problems:
            print(f"        {p}")
        failed += bool(problems)
    if failed:
        print(f"\n{failed} check(s) failed")
        sys.exit(1)
    print("\nall checks passed")


if __name__ == "__main__":
    main()
