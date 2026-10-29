"""寸法だけで分かる干渉。"""
from matrix_sim.checks import all_issues
from matrix_sim.params import DESIGN


def test_old_heights_hit_the_32mm_wheels_when_compressed():
    # 2026-10-28 の C3（上段の下面 38mm）のまま φ32 にすると、縮めた下面 28mm がタイヤの上端 32mm に 4mm 当たる
    old = DESIGN.with_(upper_z=(38.0, 52.0))
    issues = all_issues(old)
    assert len(issues) == 4
    assert all(i.overlap_mm == 4 for i in issues)


def test_current_drawing_clears_wheels():
    # C3（2026-10-29、φ32 に合わせて上段の下面を 44mm に）：44 − 10 ＝ 34mm > 32mm
    assert all_issues(DESIGN) == []


def test_wheels_outside_upper_deck_footprint_are_ignored():
    narrow = DESIGN.with_(width=40.0)
    assert all_issues(narrow) == []
