"""寸法だけで分かる干渉。"""
from matrix_sim.checks import all_issues
from matrix_sim.params import DESIGN


def test_current_drawing_has_upper_deck_hitting_wheels_when_compressed():
    # C3：上段の下面 32mm − 縮め量 10mm ＝ 22mm、タイヤの上端は 26mm → 4mm 当たる（設計の未決として報告する）
    issues = all_issues(DESIGN)
    assert len(issues) == 4
    assert all(i.overlap_mm == 4 for i in issues)


def test_no_issue_when_upper_deck_clears_wheels():
    raised = DESIGN.with_(upper_z=(36.0, 50.0))
    assert all_issues(raised) == []


def test_wheels_outside_upper_deck_footprint_are_ignored():
    narrow = DESIGN.with_(width=40.0)
    assert all_issues(narrow) == []
