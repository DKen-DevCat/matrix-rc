"""助走付きで 3cm の段差を越える（設計書② 1章：10 回中 8 回以上）。"""
from matrix_sim import scenarios
from matrix_sim.params import DESIGN
from matrix_sim.sweep import PASS, Option, evaluate


def test_old_300rpm_design_cannot_clear_step():
    # 設計書② 7章の計算どおり、前傾 0°・0.2m/s では前輪しか乗らない（2026-10-28 までの走行モーター）
    old = Option(0, "300rpm").params(DESIGN)
    for trigger in range(0, 61, 10):
        assert not scenarios.step_climb(old, trigger).success, trigger


def test_current_design_clears_step_without_variation():
    # ばらつきなし（seed 0）で、採用案は 40mm 手前の発射で 4 輪とも段差の上に乗る
    assert scenarios.step_climb(DESIGN, 40).outcome == "cleared"


def test_current_design_fails_when_fired_at_the_step_face():
    # 採用案でも、段差に当たってから（0mm）や遠すぎる位置（60mm 超）で発射すると越えられない
    assert not scenarios.step_climb(DESIGN, 0).success
    assert not scenarios.step_climb(DESIGN, 80).success


def test_current_design_clears_step_with_variation():
    # 採用案（前傾 0°・1000rpm 級、0.67m/s）：35〜45mm 手前で発射すれば 10 回中 8 回以上
    [w] = evaluate(DESIGN, [Option(0, "1000rpm")], [35, 45])
    assert w.rates[35] >= PASS and w.rates[45] >= PASS


def test_firing_at_the_step_face_fails():
    # 見つかったこと：段差に当たってから発射しても越えられない（鼻先が引っかかって止まるか、後ろにひっくり返る）
    r = scenarios.step_climb(DESIGN.with_(tilt_deg=20), 0)
    assert not r.success
    assert r.outcome in ("blocked", "flipped")


def test_tilt_20_with_500rpm_passes_with_variation():
    [w] = evaluate(DESIGN, [Option(20, "500rpm")], [25])
    assert w.rates[25] >= PASS


def test_tilt_20_with_300rpm_passes_with_variation():
    [w] = evaluate(DESIGN, [Option(20, "300rpm")], [15])
    assert w.rates[15] >= PASS
