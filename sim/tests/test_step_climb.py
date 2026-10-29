"""助走付きで 3cm の段差を越える（設計書② 1章：10 回中 8 回以上）。"""
from matrix_sim import scenarios
from matrix_sim.params import DESIGN
from matrix_sim.sweep import PASS, Option, adopted_option, evaluate


def test_old_300rpm_design_cannot_clear_step():
    # 設計書② 7章の計算どおり、前傾 0°・N20 300rpm（φ32・デューティ 0.8 で 0.25m/s）では越えられない（1-a の走行モーター）
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
    # 採用案（前傾 0°・Pololu 136:1、0.52m/s）を箱と円柱の近似で見ると、25〜30mm 手前で 10 回中 8 回以上。
    # 部品モデルでは 25〜45mm（test_model.test_detailed_model_clears_the_step_with_margin）。レポートは部品モデルが正
    [w] = evaluate(DESIGN, [adopted_option(DESIGN)], [25, 30])
    assert w.rates[25] >= PASS and w.rates[30] >= PASS


def test_firing_at_the_step_face_fails():
    # 見つかったこと：段差に当たってから発射しても越えられない（鼻先が引っかかって止まるか、後ろにひっくり返る）
    r = scenarios.step_climb(DESIGN.with_(tilt_deg=20), 0)
    assert not r.success
    assert r.outcome in ("blocked", "flipped")
