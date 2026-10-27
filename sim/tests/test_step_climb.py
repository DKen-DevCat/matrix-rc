"""助走付きで 3cm の段差を越える（設計書② 1章：10 回中 8 回以上）。"""
from matrix_sim import scenarios
from matrix_sim.params import DESIGN
from matrix_sim.sweep import PASS, Option, evaluate


def test_current_design_cannot_clear_step():
    # 設計書② 7章の計算どおり、前傾 0°・0.2m/s では前輪しか乗らない
    for trigger in range(0, 61, 10):
        assert not scenarios.step_climb(DESIGN, trigger).success, trigger


def test_firing_at_the_step_face_flips_backward():
    # 見つかったこと：段差に当たってから発射すると、鼻先が引っかかって後ろにひっくり返る
    r = scenarios.step_climb(DESIGN.with_(tilt_deg=20), 0)
    assert r.outcome == "flipped"


def test_tilt_20_with_500rpm_passes_with_variation():
    [w] = evaluate(DESIGN, [Option(20, "500rpm")], [25])
    assert w.rates[25] >= PASS


def test_tilt_20_with_300rpm_passes_with_variation():
    [w] = evaluate(DESIGN, [Option(20, "300rpm")], [15])
    assert w.rates[15] >= PASS
