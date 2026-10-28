"""寸法だけで分かる干渉。"""
from matrix_sim.checks import all_issues
from matrix_sim.params import DESIGN


def test_old_drawing_had_upper_deck_hitting_wheels_when_compressed():
    # 2026-10-28 以前の C3：上段の下面 32mm − 縮め量 10mm ＝ 22mm、タイヤの上端は 26mm → 4mm 当たっていた
    old = DESIGN.with_(upper_z=(32.0, 46.0))
    issues = all_issues(old)
    assert len(issues) == 4
    assert all(i.overlap_mm == 4 for i in issues)


def test_current_drawing_clears_wheels():
    # C3（上段を 6mm 上げた）：下面 38mm − 10mm ＝ 28mm > 26mm
    assert all_issues(DESIGN) == []


def test_wheels_outside_upper_deck_footprint_are_ignored():
    narrow = DESIGN.with_(width=40.0)
    assert all_issues(narrow) == []
