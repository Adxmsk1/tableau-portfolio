# the output checks pass on the real data, and actually fail when something is wrong

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tableau_tools"))
import check_outputs  # noqa: E402


def test_all_checks_pass_on_the_committed_data():
    for check in (check_outputs.check_files, check_outputs.check_coverage,
                  check_outputs.check_proportions, check_outputs.check_text):
        assert check() == [], check.__name__


def test_coverage_check_spots_a_missing_season(monkeypatch):
    real_load = check_outputs.load

    def load_without_2010(project, name):
        df = real_load(project, name)
        return df[df["season"] != 2010] if name == "elite_by_season" else df

    monkeypatch.setattr(check_outputs, "load", load_without_2010)
    problems = check_outputs.check_coverage()
    assert any("2010" in p for p in problems)


def test_proportion_check_spots_a_share_over_one(monkeypatch):
    real_load = check_outputs.load

    def load_with_bad_share(project, name):
        df = real_load(project, name)
        if name == "nations" and "share" in df:
            df = df.copy()
            df.loc[0, "share"] = 1.5
        return df

    monkeypatch.setattr(check_outputs, "load", load_with_bad_share)
    assert check_outputs.check_proportions() != []
