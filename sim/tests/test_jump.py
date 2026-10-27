"""その場ジャンプと落下（設計書② 7章・8章）。"""
from matrix_sim import scenarios
from matrix_sim.params import DESIGN


def test_design_jumps_at_least_40mm():
    # C4 の目標：跳躍高さ 4cm 以上（見積もり 4〜6cm）
    r = scenarios.jump_in_place(DESIGN)
    assert 40 <= r.lift_mm <= 60
    assert r.upright > 0.95


def test_tilt_trades_height_for_forward_speed():
    flat = scenarios.jump_in_place(DESIGN).lift_mm
    tilted = scenarios.jump_in_place(DESIGN.with_(tilt_deg=20)).lift_mm
    assert tilted < flat


def test_tilt_up_to_25_degrees_lands_upright():
    for tilt in (10, 20, 25):
        assert scenarios.jump_in_place(DESIGN.with_(tilt_deg=tilt)).upright > 0.9, tilt


def test_tilt_30_degrees_flips_over():
    # 見つかったこと：30° では前に回転してひっくり返る（前傾は 25° までにする）
    assert scenarios.jump_in_place(DESIGN.with_(tilt_deg=30)).upright < 0


def test_drop_from_300mm_lands_upright():
    # 設計書② 8章：30cm から落とす。加速度の基準値は 1-a の実測後に決める（今は記録だけ）
    r = scenarios.drop_test(DESIGN, 300)
    assert r.upright > 0.9
    assert 0 < r.peak_accel_g < 500
